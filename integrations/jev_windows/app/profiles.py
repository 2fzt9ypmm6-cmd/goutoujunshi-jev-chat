# -*- coding: utf-8 -*-
"""目标聊天应用档案：窗口筛选、说话人气泡判定、填入锚点的纯逻辑。不碰 win32，CI 可离线测试。
颜色阈值按真实客户端标定（微信 4.0 / QQNT 9.x，100% DPI）；调参先改这里的数字。"""
from __future__ import annotations

WECHAT, QQ = "wechat", "qq"
TARGET_APPS = (WECHAT, QQ)

APP_NAMES = {WECHAT: "微信", QQ: "QQ"}

# 我方气泡的饱和度下限：QQ 默认蓝泡 ~237、金黄主题 ~150、深色主题品牌色也过；对方浅灰白泡 <25。
# 微信仍用绿色主导规则，不共用这个阈值。
_QQ_ME_CHROMA = 60

# 消息区下缘（y1）往下多少像素是输入框文字区，填草稿点这里。
# QQ 实测：输入区上边线（含边界线）下面 17~40px 是表情/截图/文件那一排图标，78 落在图标下方的大块打字区
FILL_DROP = {WECHAT: 40, QQ: 78}
FILL_SIDE = 60  # 输入框文字区从消息区左缘往里多少像素（两边都靠左，避开表情/工具按钮）


def app_name(app: str) -> str:
    return APP_NAMES.get(app, APP_NAMES[WECHAT])


def window_error(app: str) -> str:
    if app == QQ:
        return "没找到 QQ 的可见窗口，把 QQ 主面板打开再试"
    return "没找到 Weixin.exe / WeChat.exe 的可见窗口，微信开着吗？"


def pick_window(app: str, candidates: list[dict]):
    """按应用规则挑窗口，没有返回 None。candidates 只收可见顶层窗口，键：hwnd/exe/cls/title/area。
    QQ：可见的 qq.exe Chrome_WidgetWin_1（Electron）里挑最大；微信：标题「微信」优先，否则第一个。"""
    if app == QQ:
        windows = [c for c in candidates if c["exe"] == "qq.exe" and c["cls"] == "Chrome_WidgetWin_1"]
        return max(windows, key=lambda c: c["area"])["hwnd"] if windows else None
    windows = [c for c in candidates if c["exe"] in ("weixin.exe", "wechat.exe")]
    if not windows:
        return None
    return next((c["hwnd"] for c in windows if c["title"] == "微信"), windows[0]["hwnd"])


def _chroma(bg) -> int:
    r, g, b = int(bg[0]), int(bg[1]), int(bg[2])
    return max(r, g, b) - min(r, g, b)


def classify_bubble(app: str, bg, diff_max: float) -> str:
    """气泡底色 + 文字对底色的最大对比度 → me / her / gray。
    微信：绿色主导 = me（现状规则，不动）；QQ：高饱和度 = me（主题无关）。
    非 me 里摘要算 her，灰字/时间戳（对比度低）算 gray。"""
    r, g, b = int(bg[0]), int(bg[1]), int(bg[2])
    if app == QQ:
        me = _chroma(bg) >= _QQ_ME_CHROMA
    else:
        me = g > r + 40 and g > b + 40
    if me:
        return "me"
    return "her" if diff_max >= 150 else "gray"


def looks_like_text_region(app: str, bg, mode_frac: float) -> bool:
    """OCR 框里的字是不是落在「平底色」上（否则是头像/照片/表情包里的字，要丢掉）。
    微信：众数颜色占比 >= 45%（现状）。QQ：短句密排把金黄气泡的占比压到 0.2 出头，光看占比会误杀，
    所以高饱和底色（chroma 达标）放宽到 >= 15%；中性底色（照片里的浅色区域）仍按 45% 卡。"""
    if mode_frac >= 0.45:
        return True
    return app == QQ and mode_frac >= 0.15 and _chroma(bg) >= _QQ_ME_CHROMA


def fill_point(area, app: str) -> tuple[int, int]:
    """消息区 (x0, y0, x1, y1) → 输入框文字区点击坐标（窗口坐标系内）。"""
    x0, _, _, y1 = area[:4]
    return x0 + FILL_SIDE, y1 + FILL_DROP.get(app, FILL_DROP[WECHAT])
