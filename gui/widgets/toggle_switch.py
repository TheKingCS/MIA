"""
gui.widgets.toggle_switch
============================

ToggleSwitch: a small pill-shaped on/off switch — the "Quick Bus"
widget's toggle rows in the 2026-07-15 "ForMIA" design handoff's
`WIDGET_STENCIL.md` ("28×15px teal pill with a 11×11 dark knob offset
2px from the active edge").

Custom-painted (`QAbstractButton` + `paintEvent`) rather than a styled
`QCheckBox` — Qt's `QCheckBox::indicator` QSS can fake a pill *shape*,
but not a knob that visibly slides between two positions depending on
state; that needs either a two-state image asset (this project avoids
bundling image assets for UI chrome, see `gui/theme_manager.py`'s
"bubble outline" icon language, all drawn/QSS, no PNGs) or real paint
code. Same shape as `gui/presence_widget.py`'s custom QPainter approach
— cheap, no new dependency, full control over the exact pixel spec.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

_WIDTH = 28
_HEIGHT = 15
_KNOB_DIAMETER = 11
_KNOB_MARGIN = 2
_TRACK_COLOR_ON = QColor("#38d9c9")
_TRACK_COLOR_OFF = QColor("#1b222e")
_KNOB_COLOR = QColor("#06131a")


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(_WIDTH, _HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        track_color = _TRACK_COLOR_ON if self.isChecked() else _TRACK_COLOR_OFF
        painter.setBrush(track_color)
        painter.drawRoundedRect(self.rect(), _HEIGHT / 2, _HEIGHT / 2)

        knob_x = _WIDTH - _KNOB_DIAMETER - _KNOB_MARGIN if self.isChecked() else _KNOB_MARGIN
        painter.setBrush(_KNOB_COLOR)
        painter.drawEllipse(QRectF(knob_x, _KNOB_MARGIN, _KNOB_DIAMETER, _KNOB_DIAMETER))

        painter.end()
