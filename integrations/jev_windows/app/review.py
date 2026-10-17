# -*- coding: utf-8 -*-
"""核对本轮对话：和主界面同一套外观（暖白底、白卡片、深绿字、无边框圆角），
底部可以「累计聊天记录」——把采集到的最新记录并进列表（不覆盖你改过的行），累计之后再分析。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (FluentIcon as FIF, PlainTextEdit, PrimaryPushButton,
                            PushButton, setCustomStyleSheet)

from app.overlay import _MUTED, _Surface, _TitleBar, _label, _tool
from core.transcript import (format_review_rows, merge_reviewed_transcript,
                             merge_transcript, parse_review_rows)


class ReviewDialog(QDialog):
    def __init__(self, title: str, messages: list, parent=None, history_of=None, revision_of=None):
        super().__init__(parent)
        self._history_of = history_of  # 取该会话最新累计记录的可调用对象 → [(who, text, name)]
        self._revision_of = revision_of
        self.reviewed_revision = revision_of() if revision_of else None
        self._source_rows = list(messages)
        self.setWindowTitle(f"核对本轮对话 · {title}")  # 无障碍/任务栏标题保留
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(
            "QDialog { background: #f5f7f6; border: 1px solid #dce3de; border-radius: 14px; }"
        )
        width = parent.width() if parent is not None else 440  # 宽度跟主页面一致
        self.resize(max(360, width), 600)
        if parent is not None:
            geo = parent.geometry()
            self.move(geo.x() + max(0, (geo.width() - self.width()) // 2), geo.y() + 40)

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
            "每行以「我：」「对方：」或「对方（名字）：」开头；OCR 可能认错字、错分边或漏行，改好再分析。\n"
            "群聊里对方的消息会带发言人名字（可以改），分析时一并带给模型；单聊不带名字。\n"
            "上滑翻看旧消息后，点「累计聊天记录」将新采集内容并入本页，再核对并确认。", 12, _MUTED))

        editor_card = _Surface()
        card_box = QVBoxLayout(editor_card)
        card_box.setContentsMargins(14, 12, 14, 12)
        self.editor = PlainTextEdit()
        self.editor.setPlainText("\n".join(format_review_rows(messages)))
        self.editor.setStyleSheet("PlainTextEdit { background: transparent; border: none; }")
        card_box.addWidget(self.editor)
        body.addWidget(editor_card, 1)

        self.feedback = _label("", 12, _MUTED)
        body.addWidget(self.feedback)

        actions = QVBoxLayout()
        actions.setSpacing(8)
        self.accumulateButton = PushButton("累计聊天记录")
        self.accumulateButton.setToolTip("按对话顺序合并最新采集记录，保留已核对的文字；合并后请再次核对")
        self.accumulateButton.clicked.connect(self._accumulate)
        confirm = PrimaryPushButton("确认并分析")
        confirm.clicked.connect(self._confirm)
        cancel = PushButton("取消")
        cancel.clicked.connect(self.reject)
        for button in (self.accumulateButton, confirm, cancel):  # 全部按钮按主页面宽度整行铺满
            button.setMinimumWidth(0)
            actions.addWidget(button)
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
        current = parse_review_rows(self.editor.toPlainText().splitlines())
        merged = merge_reviewed_transcript(current, self._source_rows, latest)
        self._source_rows = merge_transcript(self._source_rows, latest, unmatched="newer")
        added = len(merged) - len(current)
        self.editor.setPlainText("\n".join(format_review_rows(merged)))
        if self._revision_of:
            self.reviewed_revision = self._revision_of()
        if added > 0:
            self._feedback(f"已累计：新增 {added} 条，共 {len(merged)} 条。")
        else:
            self._feedback("没有新的记录（列表已是最新）。")

    def _confirm(self):
        rows = parse_review_rows(self.editor.toPlainText().splitlines())
        parsed = []
        for who, content, name in rows:
            if who not in ("me", "her"):
                self._feedback("每行须以「我：」「对方：」或「对方（名字）：」开头（不需要的行直接删掉）。", error=True)
                return
            if not content:
                self._feedback("请删除空消息，或补上正文。", error=True)
                return
            parsed.append((who, content, name) if name else (who, content))
        if not parsed or len(parsed) > 60:
            self._feedback("请保留 1 到 60 条相关消息。", error=True)
            return
        self.messages = parsed
        self.accept()
