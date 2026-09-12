"""
gui.widgets.blueprint_frame
==============================

BlueprintFrame — a QFrame that paints four small "+" registration
marks, one per corner, the "MIA Smart User OS Design" handoff's
blueprint-frame convention (that bundle's README.md, "Blueprint
registration marks" section): applied to major panels so they read as
a designed instrument, not a plain card. Same "small QPainter-based
visual atom, reused across screens" shape as
gui/widgets/circular_gauge.py.

Renders the marks just inside its own border (Qt clips anything a
paintEvent draws outside a widget's own rect) rather than literally
outside the frame the way the design spec's own coordinates describe
— visually equivalent at this scale, avoids fighting Qt's clipping.
A widget wrapped in `BlueprintFrame` needs real padding around its
own content (16px+, matching the handoff's own card-padding spec) so
the marks don't overlap anything real — that's the caller's own inner
layout margin, not something this class sets itself, since it has no
opinion on what's inside it.

**2026-09-12 design restyle, phase 1**: introduced alongside
`gui/widgets/glow.py`; applied this pass only to
`gui/home_dashboard.py`'s Clock and Mission widget cards. Every other
call site the full design calls for (active-quest card, sensor-task
card, achievements panel, ...) is real, deferred follow-up scope, not
built yet.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFrame, QWidget

_MARK = "+"
_MARK_INSET = 8  # distance from each edge to where a mark is centered
_MARK_FONT_SIZE = 11

_INK_COLOR = QColor("#22424a")
_ACCENT_INK_COLOR = QColor("#2b5459")


class BlueprintFrame(QFrame):
    """Wrap content in this instead of a plain QFrame to get the four
    corner marks. `accent=True` uses the brighter ink color, for a
    panel already sitting on an accent-tinted (#0f1a1c/#1f3538)
    background — see the design handoff's own color table."""

    def __init__(self, parent: Optional[QWidget] = None, accent: bool = False) -> None:
        super().__init__(parent)
        self._ink = _ACCENT_INK_COLOR if accent else _INK_COLOR

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self._ink)
        font = QFont("JetBrains Mono")
        font.setPointSize(_MARK_FONT_SIZE)
        painter.setFont(font)

        rect = self.rect()
        corners = [
            (rect.left() + _MARK_INSET, rect.top() + _MARK_INSET),
            (rect.right() - _MARK_INSET, rect.top() + _MARK_INSET),
            (rect.left() + _MARK_INSET, rect.bottom() - _MARK_INSET),
            (rect.right() - _MARK_INSET, rect.bottom() - _MARK_INSET),
        ]
        for x, y in corners:
            painter.drawText(x - 5, y - 7, 10, 14, Qt.AlignmentFlag.AlignCenter, _MARK)
        painter.end()
