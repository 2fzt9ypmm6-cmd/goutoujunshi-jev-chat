# -*- coding: utf-8 -*-
"""找目标聊天窗口（微信 / QQNT）+ Windows Graphics Capture 盯着它 + 从帧里定位消息区。帧全程内存，绝不落盘。"""
import ctypes
import ctypes.wintypes as wt
import os
import time

import numpy as np

from app import profiles

u32 = ctypes.windll.user32


def find_app_hwnd(app="wechat"):
    """枚举可见顶层窗口，交给 profiles.pick_window 按应用规则挑：
    微信 = Weixin.exe/WeChat.exe 里标题「微信」的（主窗口），没有就取第一个（同进程还有 'Weixin'（工具窗）、
    '图片和视频'（看图窗）等，面积可能更大，所以不能按面积挑）；
    QQ = qq.exe 的 Electron 窗口（Chrome_WidgetWin_1）里挑最大的——QQNT 是多进程，同进程还有一堆 0 尺寸
    和弹层窗口，全靠可见性 + 类名过滤。没有可用窗口时抛 RuntimeError。"""
    k32 = ctypes.windll.kernel32
    found = []

    def exe_of(pid):
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        buf, size = ctypes.create_unicode_buffer(1024), ctypes.c_uint(1024)
        ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        k32.CloseHandle(h)
        return os.path.basename(buf.value).lower() if ok else ""

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = exe_of(pid.value)
        if exe not in ("weixin.exe", "wechat.exe", "qq.exe"):
            return True
        title = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd, title, 256)
        cls = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cls, 256)
        rect = wt.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(rect))
        found.append({"hwnd": hwnd, "exe": exe, "cls": cls.value, "title": title.value,
                      "area": (rect.right - rect.left) * (rect.bottom - rect.top)})
        return True

    u32.EnumWindows(cb, 0)
    hwnd = profiles.pick_window(app, found)
    if hwnd is None:
        raise RuntimeError(profiles.window_error(app))
    return hwnd


def unminimize(hwnd):
    """Windows 不渲染最小化的窗口，什么截图法都拿不到画面。发现被最小化就无激活还原，再压到所有窗口最底下——
    看着跟收起来一样，但 DWM 继续画。不抢焦点、不动大小位置。返回是否动了手。"""
    if not u32.IsIconic(hwnd):
        return False
    u32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
    u32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 0x13)  # HWND_BOTTOM, SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE
    return True


def chat_area(full, app="wechat"):
    """按应用分派定位消息区；认不出返回 None。"""
    return chat_area_qq(full) if app == profiles.QQ else chat_area_wechat(full)


def chat_area_wechat(full, header_h=60):
    """消息列表区 (x0, y_top, x1, y_in, 面板底色, y_pane)，全靠像素锚点，不写死坐标，深浅主题通用：
    - 面板底色 = 右半边最常见的颜色（抽样算，全量 np.unique 在 2560 宽的图上要半秒）
    - 面板左/右边界 = 第一/最后一根「底色占比 > 30%」的列（联系人列表是另一种底色，占比 0）
    - y_pane = 面板第一行；会话名就印在 y_pane~y_top 这条头部里（公告条也在里面）
    - 横向分隔线 = 整行单色且非底色；输入框顶 y_in = 面板 45% 高度以下第一根；
      公告条下面那根（有的话）= 消息区顶 y_top，没有就用 header_h
    认不出（窗口太小 / 拖到一半布局没铺好）返回 None。
    ponytail: 输入框拉高超过面板一半会认错；header_h 按 100% DPI 给的，缩放了按比例调。"""
    H, W = full.shape[:2]
    right = full[::8, W // 2::8].reshape(-1, 3)
    vals, cnt = np.unique(right, axis=0, return_counts=True)
    bg = vals[cnt.argmax()]
    isbg = np.abs(full.astype(int) - bg).sum(-1) <= 6
    col = isbg[H // 4: H * 3 // 4].mean(0)
    x0 = int(np.argmax(col > 0.3))
    x1 = W - int(np.argmax(col[::-1] > 0.3))
    row = isbg[:, x0:x1].mean(1)
    y0 = int(np.argmax(row > 0.9))
    y1 = H - int(np.argmax(row[::-1] > 0.9))
    band = full[y0:y1, x0:x1].astype(int)
    seps = y0 + np.where((band.std(axis=(1, 2)) < 4) & (row[y0:y1] < 0.1))[0]
    seps = [int(s) for i, s in enumerate(seps) if i == 0 or s - seps[i - 1] > 3]
    below = [s for s in seps if s > y0 + 0.45 * (y1 - y0)]
    y_in = below[0] if below else y1
    above = [s for s in seps if y0 + header_h < s < y_in - 50]
    y_top = above[-1] if above else y0 + header_h
    if x1 - x0 < 100 or y_in - y_top < 40:
        return None
    return x0, y_top, x1, y_in, bg, y0


def chat_area_qq(full):
    """QQNT 主面板锚点 (x0, y_top, x1, y_in, 面板底色, y_pane)。QQ 皮肤是整窗渐变、列表和面板
    颜色几乎一样，没有可用的色块边界，全靠结构台阶（标定：浅色皮肤、100% DPI、默认列表宽度）：
    - y_pane = 标题栏下边线：>=50% 的列出现 +2 亮度台阶的第一行（Electron 自绘标题栏，下面才是内容）
    - y_top = y_pane + 50：消息区顶（头部只有右上角一排工具图标，整行跳过）
    - x0 = 会话列表搜索框右缘 + 16：跟着列表宽度走，拖过列表也不会把列表文字切进消息区；框认不出按 240px 兜底
    - y_in = 输入框上边线：从上往下 >=85% 的列同时 +2 台阶、下一行整行平整，取最后一个
      （图片/宽气泡的上缘也是台阶，取最后一个就能跳过它们）
    - 底色 = 右侧滚动条内侧的竖条带取中位数：渐变皮肤也不会被采样成渐变
    认不出（窗口太小 / 布局没铺好）返回 None。
    ponytail: 深色皮肤台阶可能反向，认不出就等下一帧；头部按 50px 算，缩放了按比例调。"""
    H, W = full.shape[:2]
    if H < 320 or W < 480:
        return None
    pixels = full.astype(int)
    luma = pixels @ np.array([0.299, 0.587, 0.114])
    xl, xr = W // 3, W - max(8, W // 40)
    dc = luma[1:, xl:xr] - luma[:-1, xl:xr]
    d, frac = dc.mean(1), (dc >= 2).mean(1)
    y_tb = next((i + 1 for i in range(5, min(150, H - 150)) if d[i] >= 1.5 and frac[i] >= 0.5), None)
    scale = (y_tb / 40) if y_tb else 1.0
    if y_tb is None:
        y_tb = int(40 * scale)
    y_top = y_tb + int(50 * scale)
    # 会话列表搜索框右缘 → 面板左边界（搜索框 + 右边的「+」按钮是一组，中间小缝合并；
    # 聊天面板顶部的「对方正在输入」之类窄元素离得远，不会被合进来）
    band = pixels[y_tb + int(15 * scale): y_tb + int(38 * scale), : W // 2]
    x0 = None
    if band.size:
        colc = np.median(band, axis=0)
        hit = np.abs(colc - colc[max(4, int(6 * scale))]).sum(1) >= 15
        run = best = 0
        edge = -1
        gap = 10 ** 9
        for x, v in enumerate(hit):
            if v:
                run = run + 1 if gap <= int(14 * scale) else 1
                gap = 0
                if run > best:
                    best, edge = run, x
            else:
                gap += 1
        if best >= int(40 * scale):  # 至少 40px 宽的命中段才算搜索框，窄元素（未读点等）不算
            x0 = int(edge + 10 * scale)
    if not x0 or x0 < 60:
        x0 = int(240 * scale)
    # 输入框上边线：从下往上找第一个“整行台阶 + 下方平整”，跳过图片/宽气泡的上缘
    y_in = None
    for i in range(H - 20, y_top + 40, -1):
        if frac[i] >= 0.85 and d[i] >= 1.5 and luma[i + 1, xl:xr].std() <= 8:
            y_in = i + 1
            break
    if y_in is None or y_in - y_top < 60 or W - 2 - x0 < 200:
        return None
    x1 = W - 2
    strip = full[y_top:y_in, max(x0 + 10, W - int(48 * scale)): W - int(4 * scale)]
    bg = np.median(strip.reshape(-1, 3), axis=0).astype(np.uint8)
    return x0, y_top, x1, y_in, bg, y_tb


class Capture:
    """WGC 盯窗口。采集线程只做「跟上一帧比」；settled() 在画面停稳后交出整帧，中间帧（滚动动画、
    新消息滑入的半截气泡）全跳过。动图表情永远停不稳，所以最多等 max_wait 秒照样交。"""

    def __init__(self, hwnd, app="wechat", settle=0.25, max_wait=1.0):
        from windows_capture import WindowsCapture

        self.settle, self.max_wait = settle, max_wait
        self.app = app
        self.shape = self.area = self.last = self.pending = None
        self.t = self.t0 = 0.0
        cap = WindowsCapture(window_hwnd=hwnd)  # cursor_capture/draw_border 留默认，老版 Win10 不支持切换会抛异常
        cap.event(self.on_frame_arrived)
        cap.event(self.on_closed)
        self.ctl = cap.start_free_threaded()

    def on_frame_arrived(self, frame, control):
        full = np.ascontiguousarray(frame.frame_buffer[:, :, :3][:, :, ::-1])  # BGRA → RGB；缓冲区回调后就没了，必须拷
        if full.max() == 0:
            return
        if self.area is None or full.shape != self.shape:
            self.shape, self.area = full.shape, chat_area(full, self.app)
        if self.area is None:
            return
        x0, y0, x1, y1 = self.area[:4]  # 拿上一次的消息区做 diff 就够了，光标闪烁在输入框里，不算变化
        # ponytail: diff 不含头部——公告条会滚动，带上它就永远停不稳。切会话时消息区必然也变，照样出帧。
        chat = full[y0:y1, x0:x1]
        if self.last is not None and np.array_equal(chat, self.last):
            return
        self.last = chat
        if self.pending is None:
            self.t0 = time.perf_counter()
        self.pending, self.t = full, time.perf_counter()

    def on_closed(self):
        pass

    def settled(self):
        """停稳了就返回整帧，否则 None。"""
        if self.pending is None:
            return None
        now = time.perf_counter()
        if now - self.t < self.settle and now - self.t0 < self.max_wait:
            return None
        full, self.pending = self.pending, None
        return full

    def alive(self):
        return not self.ctl.is_finished()

    def stop(self):
        self.ctl.stop()

    def wait(self):
        self.ctl.wait()  # 采集线程若是报错死的，这里把错误抛出来
