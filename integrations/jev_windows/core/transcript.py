"""聊天记录窗口合并：把「当前可见的一段」并进累计记录，平台无关、可离线测试。"""
from __future__ import annotations

import difflib


def similar(a: str, b: str) -> bool:
    """同一段像素挪个位置 OCR 会抖（「傻逼了」↔「傻逼」、「不好意思」↔「不好竟思」），按相似度判同一条。"""
    if a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75:
        return True
    return len(a) == len(b) >= 3 and sum(x != y for x, y in zip(a, b)) <= 1  # 短句错一个字


def merge_transcript(old: list, scan: list) -> list:
    """old = 已累计记录，scan = 刚扫到的当前窗口可见段（两者都是 (who, text, name) 行）。
    用文本重叠定位：scan 里比重叠点更早的（没见过的）插到 old 的重叠行前面，保持时间顺序；
    完全找不到重叠就把 scan 当作翻上来的更早内容整体放在最前；scan 尾部的未见行补到末尾。
    判重口径和 Reader 一样（同 who + similar 文本）。"""
    old = [tuple(row) for row in old]
    scan = [tuple(row) for row in scan]
    if not old or not scan:
        return scan or old

    def same(a, b):
        return a[0] == b[0] and similar(str(a[1]), str(b[1]))

    def in_old(row):
        return any(same(row, o) for o in old)

    join = None
    for i in range(len(scan)):  # 第一个重叠点：在它之前的扫描内容都比它更早，要插到 old 的对应行前面
        if in_old(scan[i]):
            join = i
            break
    if join is None:
        return scan + old
    j = next(k for k, o in enumerate(old) if same(scan[join], o))
    prefix = [row for row in scan[:join] if not in_old(row)]
    suffix = [row for row in scan[join + 1:] if not in_old(row)]
    return old[:j] + prefix + old[j:] + suffix
