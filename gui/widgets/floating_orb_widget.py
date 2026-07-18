"""
gui.widgets.floating_orb_widget

A small blue glowing orb that appears and "reaches" toward the mouse
when the cursor nears the bottom-right corner of the window — real
user ask (2026-07-18): "when the mouse goes to the bottom right of the
screen a small blue glowing orb moves towards the mouse and when
clicked on it pulls out the sidebar for the assistant so we don't have
to have a 24/7 open assistant screen." `gui/main_window.py` owns a
QTimer polling `QCursor.pos()` (simpler and more robust than an event
filter fighting mouse-move propagation across this app's deep widget
tree — a scroll area, a stacked widget, and whatever module is
currently open) and calls `update_position()` on every tick; this class
only knows how to compute/apply its own position and paint itself, not
how the polling works.

Deliberately no QPropertyAnimation easing on top of the timer-driven
movement — keeping the first pass simple until the "feel" of a plain
polled follow can actually be judged live (screenshot-only review can't
judge motion feel, so don't stack more animation ideas into an
unverified first version).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QWidget

_DIAMETER = 56
_MARGIN = 24  # distance from the window's bottom-right corner to the orb's home position
_TRIGGER_ZONE = 180  # square region near the corner that reveals the orb
_MAX_TRAVEL = 48  # how far the orb can shift from home toward the mouse, at most


class FloatingOrbWidget(QPushButton):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("FloatingOrb")
        self.setFixedSize(_DIAMETER, _DIAMETER)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Open the Assistant")

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(36)
        glow.setXOffset(0)
        glow.setYOffset(0)
        glow.setColor(QColor(59, 130, 246, 200))  # blue glow, matches the orb's own gradient
        self.setGraphicsEffect(glow)

        self.hide()

    def home_center(self) -> QPoint:
        parent = self.parentWidget()
        size = parent.size() if parent is not None else self.size()
        return QPoint(size.width() - _MARGIN - _DIAMETER // 2, size.height() - _MARGIN - _DIAMETER // 2)

    def update_position(self) -> None:
        """Called on every tick of gui/main_window.py's mouse-tracking
        QTimer. Shows/hides and repositions itself based on the global
        cursor position relative to this widget's parent."""
        parent = self.parentWidget()
        if parent is None:
            return

        local_pos = parent.mapFromGlobal(QCursor.pos())
        size = parent.size()
        trigger_rect = QRect(
            size.width() - _TRIGGER_ZONE, size.height() - _TRIGGER_ZONE, _TRIGGER_ZONE, _TRIGGER_ZONE
        )

        # The `isVisible()` guard matters: before this widget has ever
        # been shown, Qt leaves it at its default (0, 0) geometry — a
        # bare `self.geometry().contains(local_pos)` check would then
        # false-positive for any mouse position near the window's
        # top-left corner, nowhere near the actual bottom-right trigger
        # zone (found via a real headless test, not assumed).
        in_zone = trigger_rect.contains(local_pos) or (self.isVisible() and self.geometry().contains(local_pos))
        if not in_zone:
            self.hide()
            return

        home = self.home_center()
        dx = local_pos.x() - home.x()
        dy = local_pos.y() - home.y()
        distance = math.hypot(dx, dy)

        if distance > 0:
            travel = min(distance * 0.5, _MAX_TRAVEL)
            unit_x, unit_y = dx / distance, dy / distance
        else:
            travel = 0.0
            unit_x, unit_y = 0.0, 0.0

        new_center_x = home.x() + unit_x * travel
        new_center_y = home.y() + unit_y * travel
        self.move(int(new_center_x - _DIAMETER / 2), int(new_center_y - _DIAMETER / 2))
        self.show()
        self.raise_()
