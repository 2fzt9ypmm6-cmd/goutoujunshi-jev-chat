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
