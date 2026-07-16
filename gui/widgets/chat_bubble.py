"""
gui.widgets.chat_bubble
==========================

ChatBubble: one message in gui/character_panel.py's sidebar chat —
the ForMIA mockup's alternating-alignment bubble pattern (user
right-aligned, assistant left-aligned with a teal-accented border),
replacing the plain scrolling QPlainTextEdit the sidebar shipped with
since 2026-07-14. Flagged as a known gap in every ForMIA pass since
(see docs/ROADMAP.md) — this closes it.

Deliberately scoped to the sidebar only. modules/assistant/module.py's
full-screen chat keeps its existing QPlainTextEdit log — that's a
denser, more terminal-like view by design (voice transcripts, tool-call
confirmations), not the compact "companion chat" the mockup depicts.

A plain QFrame + word-wrapped QLabel, not a custom-painted widget —
unlike gui/presence_widget.py's orb, a rounded rectangle with a border
is exactly what QSS already does well, no reason to hand-roll paint
code for it.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

_MAX_BUBBLE_WIDTH = 190  # leaves room to visibly not touch the panel edge at ~220-300px sidebar widths
_BUBBLE_MARGINS = (12, 8, 12, 8)
_MAX_LABEL_WIDTH = _MAX_BUBBLE_WIDTH - _BUBBLE_MARGINS[0] - _BUBBLE_MARGINS[2]


class ChatBubble(QFrame):
    """`role` is "user" or "assistant" — selects both the QSS look
    (gui/styles.py's #ChatBubbleUser/#ChatBubbleAssistant) and which
    side of the panel the bubble aligns to (see how callers add this to
    a layout: alignment=Qt.AlignmentFlag.AlignRight for user,
    AlignLeft for assistant — this widget doesn't set its own alignment
    since that's a property of its position *within* the parent layout,
    not of the widget itself)."""

    def __init__(self, role: str, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ChatBubbleUser" if role == "user" else "ChatBubbleAssistant")
        self.setMaximumWidth(_MAX_BUBBLE_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*_BUBBLE_MARGINS)

        label = QLabel(text)
        label.setObjectName("ChatBubbleText")
        label.setWordWrap(True)
        # Qt's QVBoxLayout has a long-documented limitation: it doesn't
        # reliably negotiate heightForWidth() through nested layouts
        # (this frame's own QVBoxLayout, itself added to the chat log's
        # outer QVBoxLayout with an alignment flag, inside a QScrollArea).
        # Confirmed via direct measurement, not guessed: label.sizeHint()
        # correctly reported the full wrapped height (e.g. 75px for 5
        # lines), but the layout only ever actually allocated 60px (4
        # lines) regardless of adjustSize()/activate()/explicit show()
        # calls — every wrapped bubble rendered with its first and last
        # lines clipped/overlapping. Fixed by computing the exact needed
        # height ourselves via heightForWidth() and setting it as a
        # *fixed* size — this removes Qt's automatic negotiation from the
        # picture entirely rather than trying to coax it into working.
        label.setFixedWidth(_MAX_LABEL_WIDTH)
        label.setFixedHeight(label.heightForWidth(_MAX_LABEL_WIDTH))
        layout.addWidget(label)
