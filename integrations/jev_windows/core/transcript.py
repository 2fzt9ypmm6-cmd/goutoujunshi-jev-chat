"""聊天记录窗口合并：把「当前可见的一段」并进累计记录，平台无关、可离线测试。"""
from __future__ import annotations

import difflib
import re


def similar(a: str, b: str) -> bool:
    """同一段像素挪个位置 OCR 会抖（「傻逼了」↔「傻逼」、「不好意思」↔「不好竟思」），按相似度判同一条。"""
    if a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75:
        return True
    return len(a) == len(b) >= 3 and sum(x != y for x, y in zip(a, b)) <= 1  # 短句错一个字


def looks_like_group_title(title: str) -> bool:
    """QQ 群聊：会话名带成员数后缀「（1835）」（面板头部/标题栏都带）；单聊一般没有这个后缀。
    当前只保留单聊，识别到群就整帧跳过（回退成单聊自动恢复）。"""
    return bool(re.search(r"[（(]\d+[)）]\s*$", str(title or "").strip()))


def same_row(a, b) -> bool:
    """Match overlapping OCR rows without merging two named group participants."""
    name_a = a[2] if len(a) > 2 else None
    name_b = b[2] if len(b) > 2 else None
    return a[0] == b[0] and name_a == name_b and similar(str(a[1]), str(b[1]))


def speaker_label(who, name) -> str:
    """给模型看的说话人标签：群里的对方带发言人名字（方便模型分辨谁说了什么），其余保持 her/me。"""
    return str(name) if who == "her" and name else who


def format_review_rows(rows: list) -> list[str]:
    """核对弹窗的文本行：我：… / 对方：… / 对方（发言人）：…（群聊里对方的消息带上发言人）。"""
    out = []
    for row in rows:
        who, text = row[0], row[1]
        name = row[2] if len(row) > 2 else None
        prefix = ("" if not who else "我：" if who == "me" else
                  f"对方（{name}）：" if (who == "her" and name) else "对方：")
        out.append(prefix + str(text))
    return out


def parse_review_rows(lines: list) -> list[tuple]:
    """核对弹窗文本行 → [(who, text, name)]；不以「我：/对方：/对方（名）：」开头的行 who 留空原样保留。"""
    import re
    parsed = []
    for row in lines:
        row = row.strip()
        if not row:
            continue
        if row.startswith("我："):
            parsed.append(("me", row[2:].strip(), None))
        elif row.startswith("对方（"):
            match = re.match(r"^对方（(.+?)）：(.*)$", row)
            if match:
                parsed.append(("her", match.group(2).strip(), match.group(1).strip()))
            else:
                parsed.append(("", row, None))
        elif row.startswith("对方："):
            parsed.append(("her", row[3:].strip(), None))
        else:
            parsed.append(("", row, None))
    return parsed


def is_scrollback(known_ys: list, unknown_rows: list) -> bool:
    """滑动回看检测：可见内容里出现了「已知消息上方」的未知行（翻上去露出来的旧消息），
    或者整屏都是没见过的（新会话刚打开）。命中时调用方按「重扫」处理，把整屏并进累计记录。
    known_ys：可见行里已认识行的 y；unknown_rows：可见行里未知行的 (who, name, text, y)。"""
    floor = max(known_ys) if known_ys else None
    return any(floor is None or y < floor for _w, _n, _t, y in unknown_rows)


def merge_transcript(old: list, scan: list, *, unmatched="older") -> list:
    """Merge overlapping, oldest-first windows; keep the engine's latest row last.

    Matching rows anchor the two windows in time. With no overlap a scan is
    treated as older scrollback unless the caller is resuming current capture.
    Only adjacent duplicate OCR rows are collapsed inside the scanned window.
    """
    old = [tuple(row) for row in old]
    scanned = []
    for row in scan:
        row = tuple(row)
        if not scanned or not same_row(row, scanned[-1]):
            scanned.append(row)
    n, m = len(old), len(scanned)
    lengths = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            lengths[i][j] = (1 + lengths[i + 1][j + 1] if same_row(old[i], scanned[j])
                             else max(lengths[i + 1][j], lengths[i][j + 1]))
    if not lengths[0][0]:
        return old + scanned if unmatched == "newer" else scanned + old
    merged, i, j = [], 0, 0
    while i < n and j < m:
        if same_row(old[i], scanned[j]):
            merged.append(old[i])  # retain the user's existing spelling/identity
            i, j = i + 1, j + 1
        elif lengths[i + 1][j] >= lengths[i][j + 1]:
            merged.append(old[i])
            i += 1
        else:
            merged.append(scanned[j])
            j += 1
    return merged + old[i:] + scanned[j:]


def merge_reviewed_transcript(reviewed: list, source: list, latest: list) -> list:
    """Reapply user corrections/deletions while incorporating new captured rows."""
    def rows(items):
        return [(r[0], r[1], r[2] if len(r) > 2 else None) for r in items]

    reviewed, source, latest = rows(reviewed), rows(source), rows(latest)
    merged = merge_transcript(source, latest, unmatched="newer")
    replacements, insertions = {}, {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, source, reviewed, autojunk=False).get_opcodes():
        if tag == "insert":
            insertions[i1] = reviewed[j1:j2]
        elif tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                replacements[i] = [reviewed[j]]
        else:
            for i in range(i1, i2):
                replacements[i] = reviewed[j1:j2] if i == i1 else []
    result, index = [], 0
    for row in merged:
        if index < len(source) and row == source[index]:
            result.extend(insertions.get(index, []))
            result.extend(replacements[index])
            index += 1
        else:
            result.append(row)
    result.extend(insertions.get(len(source), []))
    return result
