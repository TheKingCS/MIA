"""
gui.orb_presence
==================

MIA on the desktop as just herself: her presence orb and rings floating in the
middle of the screen, with no window, title bar or border around them (Zac,
2026-11-08: "boot up with just the icon appearing in the middle of the screen
in an animation state. No window or borders, just the orb and the rings
floating on the screen").

A frameless, transparent, always-on-top window (`Qt.Tool`, so it keeps no
taskbar button) that hosts the existing `gui.presence_widget.PresenceWidget` —
MIA's real orb, reused rather than reinvented, so she looks the same here as on
the splash and in the character panel. The window gently bobs so the orb reads
as floating, and it carries no opaque background, so only the orb and its rings
are ever drawn. Drag it anywhere; a plain click (not a drag) emits `activated`,
which `core.application.MIAApplication` connects to opening her main window.

Deliberately 2D/QPainter via PresenceWidget, same reasoning as the splash: a
breathing, ringed orb reads as "alive" without a 3D engine, and stays cheap.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

from gui.presence_widget import PresenceWidget

_FLOAT_INTERVAL_MS = 33  # ~30 fps for the bob
_FLOAT_AMPLITUDE_PX = 9  # how far she drifts up and down
_FLOAT_PERIOD_S = 4.2  # one full up-and-down cycle
_DRAG_SLOP_PX = 4  # movement under this on a press still counts as a click


class OrbPresence(QWidget):
    """MIA's orb floating borderless on the desktop; drag to move, click to open her."""

    activated = Signal()

    def __init__(self, diameter: int = 300, state: str = "idle") -> None:
        """A frameless, transparent, always-on-top orb window of the given size, bobbing where it stands."""
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool  # no taskbar button — she's a presence, not an app window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self._orb = PresenceWidget(self, diameter=diameter)
        self._orb.set_state(state)
        self._orb.set_glyph("")  # just the orb and the rings — no label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._orb, alignment=Qt.AlignmentFlag.AlignCenter)
        self.resize(diameter, diameter)

        # Floating bob — the window drifts a few pixels up and down so the orb reads as suspended, on top of the
        # PresenceWidget's own breathing. Anchored to a base y set the first time the window is placed.
        self._base_y: int | None = None
        self._phase = 0.0
        self._float_timer = QTimer(self)
        self._float_timer.timeout.connect(self._float_tick)

        # Drag-to-move state; a press that barely moves is treated as a click (activate), not a drag.
        self._press_global: QPoint | None = None
        self._press_window: QPoint | None = None
        self._dragged = False

    # ------------------------------------------------------------------ placement

    def show_centered(self) -> None:
        """Place her in the middle of the primary screen and start floating."""
        screen = self.screen() or (self.window().screen() if self.window() else None)
        geometry = screen.availableGeometry() if screen else None
        if geometry is not None:
            x = geometry.x() + (geometry.width() - self.width()) // 2
            y = geometry.y() + (geometry.height() - self.height()) // 2
            self.move(x, y)
            self._base_y = y
        self.show()
        self.raise_()
        self._float_timer.start(_FLOAT_INTERVAL_MS)

    def _float_tick(self) -> None:
        """Nudge the window along a slow sine so the orb bobs; anchored to its current base y."""
        if self._base_y is None:
            self._base_y = self.y()
        self._phase = (self._phase + _FLOAT_INTERVAL_MS / 1000.0 / _FLOAT_PERIOD_S) % 1.0
        offset = round(_FLOAT_AMPLITUDE_PX * math.sin(self._phase * 2 * math.pi))
        self.move(self.x(), self._base_y + offset)

    # ------------------------------------------------------------------ drag / click

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt override)
        """Start a possible drag; remember where, so a near-still release counts as a click instead."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_window = self.frameGeometry().topLeft()
            self._dragged = False
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt override)
        """Move the window with the cursor once the press has travelled past the click slop."""
        if self._press_global is None:
            return
        delta = event.globalPosition().toPoint() - self._press_global
        if not self._dragged and delta.manhattanLength() <= _DRAG_SLOP_PX:
            return
        self._dragged = True
        self.move(self._press_window + delta)
        self._base_y = self.y()  # re-anchor the bob to wherever she's dragged

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt override)
        """A press that didn't become a drag is a click: wake her (open the main window)."""
        if event.button() == Qt.MouseButton.LeftButton and self._press_global is not None:
            if not self._dragged:
                self.activated.emit()
            self._press_global = None
            event.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Enter/Space wakes her; Escape hides the orb."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def set_state(self, state: str) -> None:
        """Change the orb's state (idle/listening/thinking/speaking...), e.g. while she's working."""
        self._orb.set_state(state)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Stop both timers before she's torn down, so nothing ticks on a dead widget."""
        self._float_timer.stop()
        self._orb.stop()
        super().closeEvent(event)
