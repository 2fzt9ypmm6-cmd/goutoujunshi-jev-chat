# -*- coding: utf-8 -*-
"""消息区截图 → 谁说了什么。RapidOCR 吃 numpy，不落盘。"""
import difflib
import re
import time

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from app import profiles


_ENGINE = None


def _engine():
    """OCR 引擎全进程共用：一个实例 ~40MB，每个会话一个 Reader，不能各带一个。
    det_limit_type 默认 'min' 会把小图放大到短边 736，裁小反而更慢；必须 'max'。"""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RapidOCR(intra_op_num_threads=4, det_limit_type="max", det_limit_side_len=4000)
    return _ENGINE


def read_title(header):
    """面板头部那一条截图 → 会话名（numpy RGB）。取最靠上的一行，同一行里取最左的
    （右边是图标按钮，OCR 不出字；下面那行是公告）。群聊的成员数「(422)」去掉，只留名字当 key。
    认不出返回 ""。一次约 60ms，所以调用方只在头部像素变了时才问。"""
    res, _ = _engine()(header, use_cls=False)
    if not res:
        return ""
    first = min(res, key=lambda r: r[0][0][1])
    row = first[0][0][1] + (first[0][2][1] - first[0][0][1])  # 框底：顶在这之上的算同一行
    text = min((r for r in res if r[0][0][1] < row), key=lambda r: r[0][0][0])[1]
    return re.sub(r"\s*[（(]\d+[)）]\s*$", "", text.strip())


def title_crop(full, area, app=profiles.WECHAT):
    """给 read_title 的头部裁剪。微信 = 面板头部（现状）。QQ = Electron 自绘标题栏：
    名字后面紧跟灰色的「编辑个性签名/个性签名」，整条 OCR 会连成一串（实测），所以先按深色像素
    裁出名字段——名字是深色粗体，签名/天气是灰字；裁不出来就把整条交给 read_title 挑最上最左。"""
    x0, y0, x1, y1, _bg, y_pane = area
    if app != profiles.QQ:
        return full[y_pane:y0, x0:x1]
    titlebar = full[0:y_pane]
    scale = (y_pane / 40) if y_pane else 1.0
    luma = titlebar.astype(int) @ np.array([0.299, 0.587, 0.114])
    band = luma[max(4, int(8 * scale)): max(6, y_pane - int(2 * scale))]
    lo = int(55 * scale)
    hi = min(titlebar.shape[1], int(360 * scale))
    hits = np.where((band[:, lo:hi] < 90).any(0))[0] if hi > lo else []
    right = int(hits.max()) + lo + int(8 * scale) if len(hits) else titlebar.shape[1]
    return titlebar[:, lo:right]


def qq_pane_header(full, area):
    """QQ 聊天面板头部一条（标题栏下面、消息区上面）：群名常常只在这里出现（实测 Electron 标题栏
    在群聊下还挂着上一个会话名），单聊时这里是空的。"""
    x0, y_top, x1, y_in, _bg, y_pane = area
    return full[y_pane + 4: max(y_pane + 12, y_top - 6), x0 + 6: min(x1, x0 + 460)]


def read_chat_title(full, area, app=profiles.WECHAT):
    """会话名。微信 = 面板头部（现状）。QQ = 先读聊天面板头部（群里名字在这里），没字再回退
    标题栏（单聊名字只在标题栏）——只读标题栏会「切了会话不跟随」。"""
    if app != profiles.QQ:
        x0, y0, x1, y1, _bg, y_pane = area
        return read_title(full[y_pane:y0, x0:x1])
    name = read_title(qq_pane_header(full, area))
    if name:
        return name
    return read_title(title_crop(full, area, app))


def header_pixels(full, area, app=profiles.WECHAT):
    """「头部变了才重认标题」的像素比对区：微信 = 面板头部一段；QQ = 面板头部 + 标题栏两段
    （群里名字在面板头部、单聊名字在标题栏，两处都要盯，不然切到群聊时一处不动就漏了）。"""
    x0, y0, x1, y1, _bg, y_pane = area
    if app != profiles.QQ:
        return (full[y_pane:y0, x0:x1], np.empty(0, dtype=np.uint8))
    return (qq_pane_header(full, area), title_crop(full, area, app))


def who_said(chat, box, app=profiles.WECHAT):
    """按 OCR 框里的颜色分类，不看 x 坐标。返回 (谁, 底色, 墨高)：
    先看底色平不平：框里众数颜色占比 <45% 就是图片（头像/照片/表情包）里的字 → None 丢掉。
    me / her / gray 的判定按应用走 profiles.classify_bubble——微信绿底 = me（气泡正文对比度实测
    178~208，绿色 me 泡 142~150，灰字 ≤ 93）；QQ 高饱和度 = me（蓝泡、金黄主题泡都覆盖）。
    墨高 = 框里最长一段连续有字的行数（OCR 框对小字有固定 padding、还会蹭到上下行，不能拿框高比大小）。"""
    xs, ys = [p[0] for p in box], [p[1] for p in box]
    reg = chat[int(min(ys)):int(max(ys)), int(min(xs)):int(max(xs))].astype(int)
    if reg.size == 0:
        return None, None, 0
    vals, cnt = np.unique(reg.reshape(-1, 3), axis=0, return_counts=True)
    bg = vals[cnt.argmax()]
    if not profiles.looks_like_text_region(app, bg, float(cnt.max()) / reg.shape[0] / reg.shape[1]):
        # 文字必须落在平底色上：微信面板/气泡里众数颜色占 0.56~0.82，头像/照片/表情包里只有 0.1~0.3
        # （那是图片里的字，比如头像上的「借仲夏夜之梦」）；QQ 短句密排会把我方气泡压到 0.2 出头，
        # 高饱和底色另按 15% 放行——见 profiles.looks_like_text_region。
        # ponytail: 只对精确像素的帧成立；缩放/压缩过的截图（比如拿预览窗再截一次的图）底色会糊成几百种颜色，全会被当图片。
        return None, bg, 0
    diff = np.abs(reg @ [0.299, 0.587, 0.114] - bg @ [0.299, 0.587, 0.114])
    ink_h = best = 0
    for r in (diff > 60).any(axis=1):
        best = best + 1 if r else 0
        ink_h = max(ink_h, best)
    return profiles.classify_bubble(app, bg, float(diff.max())), bg, ink_h


def similar(a, b):
    """同一段像素挪个位置 OCR 会抖（「傻逼了」↔「傻逼」、「不好意思」↔「不好竟思」），按相似度判同一条。"""
    if a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75:
        return True
    return len(a) == len(b) >= 3 and sum(x != y for x, y in zip(a, b)) <= 1  # 短句错一个字


class Reader:
    """一个会话一个 Reader：lh/seen 各自算各自的，切走再切回来不会把旧消息当新的重报一遍。"""

    def __init__(self, app=profiles.WECHAT):
        self.ocr = _engine()
        self.app = app  # 说话人判定按应用走（微信绿主导 / QQ 高饱和度）
        self.lh = None  # 正常气泡字高，头一帧定
        self.seen = []  # [(who, name, text)]，累计，封顶 500
        self.last_boxes = []  # 调试视图用：[(x0,y0,x1,y1,kind,text)]，消息区裁剪坐标
        self.last_ms = 0  # 上一帧 OCR 耗时

    def read(self, chat, pane_bg):
        """→ [(who, name, text, y)]，同一气泡的多行已合并。who ∈ me/her；name 群聊里是发言人，单聊 None。
        顺带把每个框的分类记进 self.last_boxes（调试视图画框用，几十个 tuple，不开也不亏）。"""
        t0 = time.perf_counter()
        res, _ = self.ocr(chat, use_cls=False)
        self.last_ms = int((time.perf_counter() - t0) * 1000)
        self.last_boxes = []
        W = chat.shape[1]
        # 群聊：每条 her 气泡上方一行灰色发言人名（靠左、短、不带冒号、印在面板底色上），从上往下扫，名字带给后面的气泡。
        # 引用块/时间戳/公告带冒号，链接卡片灰字印在气泡底色上，都不会被当成名字。
        # ponytail: 名字行被 OCR 漏掉时会挂到上一个人头上。
        name, raw = None, []
        for box, text, _ in sorted(res or [], key=lambda r: r[0][0][1]):
            kind, bg, h = who_said(chat, box, self.app)
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            rect = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            if kind == "gray":
                on_pane = profiles.on_pane(self.app, bg, pane_bg)
                taken = bool(on_pane and box[0][0] < 0.25 * W and len(text) <= 16
                             and not re.search("[:：]", text))
                if taken:
                    name = text
                self.last_boxes.append(rect + ("name" if taken else "gray", text))
                continue
            if kind is None or (self.lh and h < 0.6 * self.lh):
                # 字比正常气泡小得多 = 图片消息（截图/表情包）里的字，不是气泡
                self.last_boxes.append(rect + ("image" if kind is None else "tiny", text))
                continue
            self.last_boxes.append(rect + (kind, text))
            raw.append((kind, name if kind == "her" else None, text, box[0][1], box[2][1], h))
        if not self.lh and len(raw) >= 3:
            self.lh = float(np.median([r[5] for r in raw]))
        # 同一气泡的多行合并：同人、上一行底到这一行顶的间距不到半个字高（不同气泡之间至少隔一个字高）
        lines = []
        for who, nm, text, top, bottom, h in raw:
            if lines and lines[-1][0] == who and lines[-1][1] == nm and top - lines[-1][4] < 0.6 * (self.lh or h):
                lines[-1][2] += text
                lines[-1][4] = bottom
            else:
                lines.append([who, nm, text, top, bottom])
        return [(w, n, t, y) for w, n, t, y, _ in lines]

    def new_lines(self, lines):
        """去重（滚动不重复）→ 这一帧里真正新出现的 [(who, name, text)]。
        本帧有已知行时只要已知行下方的：往上滚翻出来的旧消息在已知行上方，不算。
        本帧一行已知的都没有（大图把旧文字全顶出去了、切了聊天、滚远了）：全算，宁可多算不能漏。
        ponytail: 同一人连发两句一模一样的会吞一句——对触发分析无害。"""
        known_y = [y for w, n, t, y in lines if self._seen(w, n, t)]
        floor = max(known_y) if known_y else -1
        new = [(w, n, t) for w, n, t, y in lines if y > floor and not self._seen(w, n, t)]
        self.seen.extend((w, n, t) for w, n, t, _ in lines if not self._seen(w, n, t))
        del self.seen[:-500]
        return new

    def _seen(self, who, name, text):
        # 名字不参与判重：名字行滚出画面后同一条消息会从 her(LO) 变成 her，不能算新消息
        return any(w == who and similar(t, text) for w, _, t in self.seen)
