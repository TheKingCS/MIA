"""
gui.widgets.circular_gauge

A circular progress ring with a centered value/label — the "telemetry
gauge" look from the 2026-07-18 design handoff (CCH.zip's Dashboard
console, Processing Load + CPU/NET/SYS gauges). The design itself
draws these as inline SVG (`<circle>` + `stroke-dasharray`); this is
the same visual result via plain `QPainter` (this app's established
technique for anything circular/animated — see gui/presence_widget.py
and gui/widgets/toggle_switch.py — no SVG dependency needed).

Static (no animation/timer of its own) — `set_value()` just triggers a
repaint. The caller (gui/home_dashboard.py's periodic refresh) owns
when the underlying reading changes; this widget only knows how to
draw whatever value it's currently told.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

_TRACK_COLOR = QColor("#182130")
_PROGRESS_COLOR = QColor("#38d9c9")
_VALUE_COLOR = QColor("#e7ecf3")
_UNIT_COLOR = QColor("#5b6a80")


class CircularGauge(QWidget):
    def __init__(self, diameter: int = 150, stroke_width: int = 8, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self._stroke_width = stroke_width
        self._value = 0.0
        self._max_value = 100.0
        self._value_text = "0"
        self._unit_text = ""

    def set_value(self, value: float, max_value: float = 100.0, value_text: str = "", unit_text: str = "") -> None:
        """`value_text`/`unit_text` are shown as-is (e.g. "38" + "%",
        or "124.6" + "mbps") — kept separate from `value`/`max_value`
        (which only drive the ring's fill fraction) so a gauge can show
        a unit the fill fraction itself doesn't share, e.g. a NET gauge
        capped visually at some assumed ceiling but labeled with the
        real uncapped Mbps reading."""
        self._value = value
        self._max_value = max(max_value, 0.001)
        self._value_text = value_text if value_text else f"{value:.0f}"
        self._unit_text = unit_text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        half_stroke = self._stroke_width / 2
        rect = QRectF(half_stroke, half_stroke, self.width() - self._stroke_width, self.height() - self._stroke_width)

        track_pen = QPen(_TRACK_COLOR, self._stroke_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        fraction = max(0.0, min(1.0, self._value / self._max_value))
        if fraction > 0:
            progress_pen = QPen(_PROGRESS_COLOR, self._stroke_width)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)
            # Start at 12 o'clock (90°), sweep clockwise — Qt angles are
            # in 1/16ths of a degree, counter-clockwise-positive, so a
            # clockwise sweep from 12 o'clock needs a negative span.
            painter.drawArc(rect, 90 * 16, int(-fraction * 360 * 16))

        painter.setPen(_VALUE_COLOR)
        value_font = QFont()
        value_font.setBold(True)
        value_font.setPointSizeF(max(1.0, self.width() * 0.16))
        painter.setFont(value_font)
        text_rect = self.rect().adjusted(0, 0, 0, -int(self.height() * 0.12) if self._unit_text else 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._value_text)

        if self._unit_text:
            painter.setPen(_UNIT_COLOR)
            unit_font = QFont()
            unit_font.setPointSizeF(max(1.0, self.width() * 0.06))
            painter.setFont(unit_font)
            unit_rect = self.rect().adjusted(0, int(self.height() * 0.58), 0, 0)
            painter.drawText(unit_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._unit_text)

        painter.end()
