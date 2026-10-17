# -*- coding: utf-8 -*-
"""Headless construction smoke test for the packaged Qt views."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import main as windows_main  # smoke-import the actual Windows capture/fill orchestration
from app.overlay import Overlay
from app.review import ReviewDialog
from app.trend_ui import TrendWindow


def main():
    overlay = Overlay(on_fill=lambda _text: None, result_of=lambda _title: None)
    overlay.open_settings()
    overlay._back_home()
    overlay.show({"candidates": ["好，周六见", "行，周六见"], "best_index": 0,
                  "scores": [.6, .4], "goutou": {"intent": "可能愿意继续聊",
                  "action": "先承接", "facts": ["对方说周六见"]}})
    overlay.set_chat("测试会话")
    overlay.log_message("her", "仅属于上一应用", chat="测试会话")
    overlay.reset_chat_state()
    assert not overlay.current_chat() and not overlay.feeds and not overlay.cands
    source = [("me", "在吗"), ("her", "在")]
    snapshot = {"rows": source, "revision": 1}
    review = ReviewDialog("测试会话", source, overlay.win,
                          history_of=lambda: snapshot["rows"],
                          revision_of=lambda: snapshot["revision"])
    assert review.editor.toPlainText().count("：") == 2
    review.editor.setPlainText("我：在吗\n对方：在的")
    snapshot.update(rows=source + [("her", "下午见")], revision=2)
    review._accumulate()
    assert review.reviewed_revision == 2
    assert review.editor.toPlainText() == "我：在吗\n对方：在的\n对方：下午见"
    review._confirm()
    assert review.messages == [("me", "在吗"), ("her", "在的"), ("her", "下午见")]
    trend = TrendWindow()
    assert trend.canvas.candles
    trend.close()
    review.close()
    overlay.win.close()
    print("windows ui ok")


if __name__ == "__main__":
    main()
