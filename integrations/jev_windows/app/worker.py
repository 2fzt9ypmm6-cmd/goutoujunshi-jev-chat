# -*- coding: utf-8 -*-
"""子进程：截图 → 定位消息区 → OCR 头部会话名和消息 → 按会话去重，全在这边跑。
一次 OCR 250~800ms，放父进程的 Qt 主线程界面就僵了。
只往队列里丢纯 tuple/str（底色 bg 是 numpy，留在这边不过队列）。帧全程内存，绝不落盘。"""
import ctypes
import time
import traceback

import numpy as np

from app import profiles, settings
from app.capture import Capture, chat_area, unminimize
from app.ocr import Reader, read_chat_title, header_pixels, strip_member_count
from core.transcript import is_scrollback, looks_like_group_title, similar


def _err(q):
    """异常压成一行发给父进程，子进程的 stderr 一般没人看得见。"""
    q.put(("status", " ".join(traceback.format_exc().split())[-200:]))


def _packet(full, area, title, reader, lines):
    """调试视图的一帧：整帧缩到长边 ≤1100 再走队列（原帧 2560 宽裸传要 20MB），只在内存里传，不落盘。
    整数步长切片够用，不引新依赖；框和坐标照发原始值，画的那边按 scale 折算。"""
    k = max(1, -(-max(full.shape[:2]) // 1100))
    small = np.ascontiguousarray(full[::k, ::k])
    return {"w": small.shape[1], "h": small.shape[0], "rgb": small.tobytes(), "scale": k,
            "area": tuple(int(v) for v in area[:4]) if area else None,
            "pane_top": int(area[5]) if area else 0, "title": title,
            "boxes": reader.last_boxes if reader else [],
            "lines": [(w, n, t) for w, n, t, _ in lines],
            "ocr_ms": reader.last_ms if reader else 0, "ts": time.time()}


def run(q, hwnd, enabled, debug_on, stop=None, app=profiles.WECHAT):
    """enabled 置位=采集，清掉=暂停。暂停时停掉 WGC 会话（Windows 那圈黄色采集边框也跟着没了），
    恢复时重开一个；readers 一直留着，去重状态不丢，恢复后不会把屏幕上的旧消息再报一遍。
    debug_on 置位才往队列里送整帧（一帧 2~3MB），关着一点额外活都不干。
    app 决定窗口读取规则（微信绿泡 / QQ 饱和度）和锚点算法，切应用由父进程重启子进程。
    stop 置位=父进程请它退出：在循环里自己收摊、把队列喂完再走，不等着被 terminate 打死在半路
    （打死的后果见 main.stop_worker 的注释——共享信号量会被打坏，父进程下一次 Event 操作直接卡死）。"""
    ctypes.windll.user32.SetProcessDPIAware()
    cap = None
    readers = {}  # {会话名: Reader}，一个会话一套去重状态
    title, head = "", None  # 当前会话名 / 上一帧的头部像素
    last_area = None  # 上次发给父进程的 4 元组，变了才再发一次
    warned = False  # 消息区识别失败是否已经报过，拖窗口时别每帧刷一条
    rescan = True  # 开采集/恢复采集后，把当前窗口可见的记录全量上报一次（翻旧消息后重开采集就靠它）
    group_mode, group_warned = False, False  # QQ 只保留单聊：群聊整帧跳过（切回好友自动恢复）
    while True:
        if stop is not None and stop.is_set():
            break
        if not enabled.is_set():
            if cap is not None:
                cap.stop()
                cap = None
                q.put(("paused",))
            # 带超时地等：stop 来了也能及时走，不用被强杀
            while not (stop is not None and stop.is_set()) and not enabled.wait(0.5):
                pass
            rescan = True  # 恢复采集：重新看一眼当前窗口
            continue
        if cap is None:
            try:
                cap = Capture(hwnd, app)
            except Exception as e:
                q.put(("dead", "无法开始采集：" + (" ".join(str(e).split())[:120] or type(e).__name__)))
                enabled.clear()  # 自己清掉，下一圈就去等着，别一秒重试几十次
                continue
            q.put(("resumed",))
        if not cap.alive():
            break
        try:
            unminimize(hwnd)
            full = cap.settled()
            if full is not None:
                reader, lines = None, []  # 调试视图要用，消息区没认出来时就是空的
                area = chat_area(full, app)  # 每次停稳都重算：拖完窗口布局会晚一拍才铺好，只按尺寸变化算一次会锁死
                if area is None:
                    if not warned:
                        q.put(("status", "消息区认不出来（窗口太小？）"))
                        warned = True
                else:
                    warned = False
                    cap.area = area  # 采集线程拿它做 diff
                    x0, y0, x1, y1, bg, y_pane = area
                    rect = (x0, y0, x1, y1)
                    if rect != last_area:
                        q.put(("area", rect))
                        last_area = rect
                    crop = header_pixels(full, area, app)  # 头部：会话名在这里（QQ 是面板头部+标题栏两处）
                    if head is None or not (np.array_equal(crop[0], head[0]) and np.array_equal(crop[1], head[1])):  # 名字没动就别白跑一次 OCR
                        head = crop
                        if app == profiles.QQ:
                            raw = read_chat_title(full, area, app, keep_count=True)
                            group_mode = looks_like_group_title(raw)
                            if group_mode:
                                # 只保留单聊（用户要求）：群聊整帧跳过，不报会话、不进记录、不累计
                                title = ""
                                if not group_warned:
                                    q.put(("status", "当前是群聊，仅保留单聊；切到好友会话再试"))
                                    group_warned = True
                            else:
                                group_warned = False  # 回到单聊，下次再进群再提示一次
                                name = strip_member_count(raw)
                        else:
                            name = read_chat_title(full, area, app)
                        if not group_mode:
                            # OCR 抖一下（「小分队」↔「小分认」）不能分裂出一个新会话
                            name = next((k for k in readers if similar(k, name)), name) if name else ""
                            # ponytail: 认不出就沿用上次；开头就认不出给个占位名，总比把消息全丢了强
                            name = name or title or "当前会话"
                            if name != title:
                                title = name
                                q.put(("chat", title))
                    if group_mode:
                        continue  # 群聊帧：头部照算（才能发现切走），消息/累计/上报全跳过
                    ocr_provider = settings.ocr_provider()
                    if ocr_provider == "local":
                        if title not in readers or not isinstance(readers[title], Reader):
                            readers[title] = Reader(app)
                    else:
                        from app.cloud_ocr import CloudReader
                        model, key = settings.ocr_model(), settings.ocr_key()
                        old = readers.get(title)
                        if (not isinstance(old, CloudReader) or old.provider != ocr_provider or
                                old.model != model or old.key != key):
                            readers[title] = CloudReader(ocr_provider, model, key)
                    reader = readers[title]
                    lines = reader.read(full[y0:y1, x0:x1], bg)
                    # 滑动回看检测：采集中直接上滑翻旧消息，停稳后自动把新露出来、没见过的记录并进累计
                    known_ys, unknown = [], []
                    for w, n, t, y in lines:
                        if reader._seen(w, n, t):
                            known_ys.append(y)
                        else:
                            unknown.append((w, n, t, y))
                    scrolled = is_scrollback(known_ys, unknown)
                    new = reader.new_lines(lines)
                    if rescan or scrolled:
                        rescan = False
                        # 全量重扫已含本轮所有可见行，这一帧不要再发增量，不然父进程会记两遍
                        q.put(("rescan", title, [(w, t, n) for w, n, t, _ in lines], rect))
                    elif new:
                        q.put(("lines", title, new, rect))
                if debug_on.is_set():
                    q.put(("debug", _packet(full, area, title, reader, lines)))
        except Exception:
            _err(q)  # 一帧出错不退出
        time.sleep(0.05)
    if stop is not None and stop.is_set():
        # 干净的主动退出（父进程在编排重启/关闭）：收掉 WGC，不报 dead，别让父进程清状态
        if cap is not None:
            try:
                cap.stop()
                cap.wait()
            except Exception:
                pass
    else:
        q.put(("dead", f"采集停了（{profiles.app_name(app)}关了？）"))
        try:
            cap.wait()  # 采集线程若是报错死的，这里把错抛出来
        except Exception:
            _err(q)
    try:  # 队列的 feeder 还在后台线程里，先冲干净再退，父进程能收到最后一条
        q.close()
        q.join_thread()
    except Exception:
        pass
