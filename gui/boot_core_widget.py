"""
gui.boot_core_widget
=======================

PulsingCoreWidget: the animated "core" graphic on the boot splash
screen (gui/splash_screen.py) — a soft glowing orb that breathes
(brightens/dims continuously) with "M.I.A." rendered directly in its
center, the first piece of the "Jarvis-style" boot animation captured
in docs/ROADMAP.md milestone 2.9.

Driven by a plain QTimer ticking a phase value through math.sin,
rather than QPropertyAnimation — for a single looping sine wave, a
custom Qt property plus animation object is more ceremony than the
effect needs. Runs only while the splash screen is visible (a couple
of seconds at boot), so repainting at ~30fps for that long is not a
meaningful cost even on Pi 5 hardware. stop() is called from
SplashScreen.closeEvent() so the timer doesn't outlive the widget.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

_CORE_COLOR = QColor("#4fd1c5")
_LABEL_COLOR = QColor("#0d1116")  # dark, reads as a "cutout" against the bright core
_FRAME_INTERVAL_MS = 33  # ~30fps
_PHASE_STEP = 0.08


class PulsingCoreWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(440, 440)
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(_FRAME_INTERVAL_MS)

    def _tick(self) -> None:
        self._phase += _PHASE_STEP
        self.update()

    def stop(self) -> None:
        """Stop the animation timer — call before the widget is discarded."""
        self._timer.stop()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # Breathing intensity oscillates between 0.8 and 1.0 (not 0-1)
        # so the core never fades out completely.
        intensity = 0.8 + 0.2 * math.sin(self._phase)

        center = self.rect().center()
        max_radius = min(self.width(), self.height()) / 2 - 4

        # Soft outer glow: a few translucent rings, largest and
        # faintest outward — a cheap bloom effect with no blur pass.
        for radius_frac, alpha_frac in ((1.0, 0.10), (0.75, 0.20), (0.55, 0.35)):
            color = QColor(_CORE_COLOR)
            color.setAlphaF(alpha_frac * intensity)
            painter.setBrush(color)
            radius = max_radius * radius_frac
            painter.drawEllipse(center, radius, radius)

        # Solid core — radius breathes slightly alongside brightness.
        core_color = QColor(_CORE_COLOR)
        core_color.setAlphaF(0.75 + 0.25 * intensity)
        painter.setBrush(core_color)
        core_radius = max_radius * (0.32 + 0.03 * intensity)
        painter.drawEllipse(center, core_radius, core_radius)

        # "M.I.A." rendered directly in the core rather than as a
        # separate label — reads as a HUD emblem, and scales naturally
        # with the widget instead of needing separate layout.
        font = QFont()
        font.setBold(True)
        font.setPointSizeF(max(1.0, max_radius * 0.32))
        painter.setFont(font)
        text_color = QColor(_LABEL_COLOR)
        text_color.setAlphaF(0.85 + 0.15 * intensity)
        painter.setPen(text_color)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "M.I.A.")

        painter.end()
