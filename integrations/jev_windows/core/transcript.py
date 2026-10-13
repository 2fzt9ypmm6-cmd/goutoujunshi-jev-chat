"""聊天记录窗口合并：把「当前可见的一段」并进累计记录，平台无关、可离线测试。"""
from __future__ import annotations

import difflib


def similar(a: str, b: str) -> bool:
    """同一段像素挪个位置 OCR 会抖（「傻逼了」↔「傻逼」、「不好意思」↔「不好竟思」），按相似度判同一条。"""
    if a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75:
        return True
    return len(a) == len(b) >= 3 and sum(x != y for x, y in zip(a, b)) <= 1  # 短句错一个字


def same_row(a, b) -> bool:
    """两条记录算不算同一条：同 who + 文本相似（OCR 会抖）。"""
    return a[0] == b[0] and similar(str(a[1]), str(b[1]))


def speaker_label(who, name) -> str:
    """给模型看的说话人标签：群里的对方带发言人名字（方便模型分辨谁说了什么），其余保持 her/me。"""
    return str(name) if who == "her" and name else who


def format_review_rows(rows: list) -> list[str]:
    """核对弹窗的文本行：我：… / 对方：… / 对方（发言人）：…（群聊里对方的消息带上发言人）。"""
    out = []
    for row in rows:
        who, text = row[0], row[1]
        name = row[2] if len(row) > 2 else None
        prefix = ("我：" if who == "me" else
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


def merge_transcript(old: list, scan: list) -> list:
    """累计合并：old = 已累计记录，scan = 刚扫到的当前窗口可见段（都是 (who, text, name) 行）。
    本次扫到、old 里没有的记录**放在最前面**（后采集的在前），相同的记录只保留一份——
    扫描内部先自去重，再整体对 old 判重。判重口径和 Reader 一致（同 who + similar 文本）。"""
    old = [tuple(row) for row in old]
    fresh, seen = [], []
    for row in scan:
        row = tuple(row)
        if any(same_row(row, o) for o in old) or any(same_row(row, s) for s in seen):
            continue
        seen.append(row)
        fresh.append(row)
    return fresh + old
