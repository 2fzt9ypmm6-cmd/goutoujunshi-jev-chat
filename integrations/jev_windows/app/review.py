# -*- coding: utf-8 -*-
"""核对本轮对话：和主界面同一套外观（暖白底、白卡片、深绿字、无边框圆角），
底部可以「累计聊天记录」——把采集到的最新记录并进列表（不覆盖你改过的行），累计之后再分析。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (FluentIcon as FIF, PlainTextEdit, PrimaryPushButton,
                            PushButton, setCustomStyleSheet)

from app.overlay import _MUTED, _Surface, _TitleBar, _label, _tool
from core.transcript import merge_transcript


def _row_text(who, text):
    return ("我：" if who == "me" else "对方：" if who == "her" else "") + str(text)


def parse_rows(lines):
    """编辑器各行 → [(who, text)]；不以「我：/对方：」开头的行原样保留（who 留空，不参与判重）。"""
    parsed = []
    for row in lines:
        row = row.strip()
        if not row:
            continue
        if row.startswith("我："):
            parsed.append(("me", row[2:].strip()))
        elif row.startswith("对方："):
            parsed.append(("her", row[3:].strip()))
        else:
            parsed.append(("", row))
    return parsed


class ReviewDialog(QDialog):
    def __init__(self, title: str, messages: list, parent=None, history_of=None):
        super().__init__(parent)
        self._history_of = history_of  # 取该会话最新累计记录的可调用对象 → [(who, text, name)]
        self.setWindowTitle(f"核对本轮对话 · {title}")  # 无障碍/任务栏标题保留
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(
            "QDialog { background: #f5f7f6; border: 1px solid #dce3de; border-radius: 14px; }"
        )
        self.resize(640, 560)
        if parent is not None:
            geo = parent.geometry()
            self.move(geo.x() + max(0, (geo.width() - self.width()) // 2), geo.y() + 60)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)
        header = _TitleBar(self)
        head = QHBoxLayout(header)
        head.setContentsMargins(18, 12, 10, 8)
        head.addWidget(_label("核对本轮对话", 18, "#24382d", True), 1)
        head.addWidget(_tool(FIF.CLOSE, "关闭", self.reject, header))
        outer.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(20, 4, 20, 16)
        body.setSpacing(10)
        body.addWidget(_label(f"会话：{title}", 13, "#304c3c", True))
        body.addWidget(_label(
            "每行以「我：」或「对方：」开头；OCR 可能认错字、错分边或漏行，改好再分析。\n"
            "在聊天窗口上滑翻出更早的消息后，回主界面点一次「采集」开关，再点「累计聊天记录」就能并入。", 12, _MUTED))

        editor_card = _Surface()
        card_box = QVBoxLayout(editor_card)
        card_box.setContentsMargins(14, 12, 14, 12)
        self.editor = PlainTextEdit()
        self.editor.setPlainText("\n".join(_row_text(row[0], row[1]) for row in messages))
        self.editor.setStyleSheet("PlainTextEdit { background: transparent; border: none; }")
        card_box.addWidget(self.editor)
        body.addWidget(editor_card, 1)

        self.feedback = _label("", 12, _MUTED)
        body.addWidget(self.feedback)

        actions = QHBoxLayout()
        cancel = PushButton("取消")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        actions.addStretch(1)
        self.accumulateButton = PushButton("累计聊天记录")
        self.accumulateButton.setToolTip("把采集到的最新记录并入下方列表；新读到的排最前，相同内容只保留一份，你改过的行不动")
        self.accumulateButton.clicked.connect(self._accumulate)
        actions.addWidget(self.accumulateButton)
        confirm = PrimaryPushButton("确认并分析")
        confirm.clicked.connect(self._confirm)
        actions.addWidget(confirm)
        body.addLayout(actions)
        outer.addLayout(body, 1)

        self.messages = []

    def _feedback(self, text, error=False):
        color = "#b44832" if error else "#18794e"
        qss = f"BodyLabel {{ color: {color}; background: transparent; }}"
        setCustomStyleSheet(self.feedback, qss, qss)
        self.feedback.setText(text)

    def _accumulate(self):
        if not self._history_of:
            return
        latest = self._history_of()
        if not latest:
            self._feedback("还没有可累计的记录：先回主界面，在聊天窗口开着时点一次「采集」开关。", error=True)
            return
        current = parse_rows(self.editor.toPlainText().splitlines())
        merged = merge_transcript([(who, text, None) for who, text in current],
                                  [tuple(row) for row in latest])
        added = len(merged) - len(current)
        self.editor.setPlainText("\n".join(_row_text(row[0], row[1]) for row in merged))
        if added > 0:
            self._feedback(f"已累计：新增 {added} 条，共 {len(merged)} 条。")
        else:
            self._feedback("没有新的记录（列表已是最新）。")

    def _confirm(self):
        rows = parse_rows(self.editor.toPlainText().splitlines())
        parsed = []
        for who, content in rows:
            if who not in ("me", "her"):
                self._feedback("每行须以「我：」或「对方：」开头（不需要的行直接删掉）。", error=True)
                return
            if not content:
                self._feedback("请删除空消息，或补上正文。", error=True)
                return
            parsed.append((who, content))
        if not parsed or len(parsed) > 60:
            self._feedback("请保留 1 到 60 条相关消息。", error=True)
            return
        self.messages = parsed
        self.accept()
