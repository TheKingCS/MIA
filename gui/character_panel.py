"""
gui.character_panel
====================

M.I.A.'s reactive companion panel — docs/ROADMAP.md milestone 6.2.
Subscribes to the module-activity events milestone 6.1 added
("module.opened"/"menu.shown" from gui/main_window.py's navigation
methods, plus "home.shown" added in the 2026-07-14 aesthetic pass part 3
once Home became its own landing screen separate from the Apps grid)
plus the existing "notification.created" event, and updates
its displayed icon/line to react to whatever's happening — the "reacts
to whatever module is active" behavior the v0.6 phase-plan entry calls
for.

Deliberately text + emoji only, no animation/sprite assets or rendering
engine — that upgrade is real future work (see the bottom of this
docstring) but a separate, later decision, not part of this phase.
`MODULE_REACTIONS` is a static per-module_id flavor-line mapping kept
in this one file (not spread across every module's own code) so adding
a new module never requires touching this file; an unlisted module
just gets a generic fallback line built from its display_name.

Idle ambient behavior — milestone 6.3: a `QTimer` (same
timer-owned-by-the-widget pattern as core/application.py's alarm-check
timer) ticks every `_IDLE_TICK_MS`; if `_IDLE_THRESHOLD_SECONDS` has
passed since the last real event (module switch / menu / notification),
it rotates through `_IDLE_LINES` so the panel doesn't look frozen
during a long stretch on one screen. A real event always resets the
idle clock and rotation index, so idle lines never fight with an
actual reaction.

Cleanup: unsubscribe() must be called before this widget is destroyed
(gui/main_window.py's closeEvent() does this) — otherwise EventBus
would keep calling into a deleted Qt widget on the next publish(), and
the idle timer would keep firing into a deleted widget too; same
reasoning as MainWindow's own event unsubscription in closeEvent.

Likely future implementation notes (not built yet, intentionally):
    - Probably a QLabel with an animated QMovie, or a small QOpenGLWidget
      / QML view if the character needs more complex animation.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout

from core.app_context import AppContext

_DEFAULT_ICON = "\U0001F916"  # robot
_MENU_ICON = "\U0001F3E0"  # house
_HOME_ICON = "\U0001F3E1"  # house with garden — distinct from the Apps grid's plain house above
_NOTIFICATION_ICON = "\U0001F514"  # bell

_MENU_LINE = "What should we work on?"
_HOME_LINE = "Welcome home."

_IDLE_LINES = [
    "Just keeping watch.",
    "All systems nominal.",
    "Let me know if you need anything.",
    "Standing by.",
]
_IDLE_THRESHOLD_SECONDS = 30.0
_IDLE_TICK_MS = 20_000  # matches core/application.py's alarm-check timer cadence

# module_id -> (icon, line). Any module not listed here falls back to
# (_DEFAULT_ICON, "Watching over <display_name>.") in _reaction_for_module.
MODULE_REACTIONS: dict[str, tuple[str, str]] = {
    "assistant": ("\U0001F5E8", "Ready to help — ask me anything."),
    "diagnostics": ("\U0001F4CA", "Keeping an eye on the vitals."),
    "files": ("\U0001F4C1", "Let's find what you're looking for."),
    "knowledge": ("\U0001F4DA", "So much to read, so little time."),
    "maps": ("\U0001F5FA", "Charting the way forward."),
    "module_browser": ("\U0001F9E9", "New tools, new possibilities."),
    "music": ("\U0001F3B5", "Let's set the mood."),
    "notes": ("\U0001F4DD", "Jot it down before you forget."),
    "settings": ("\U00002699", "Tuning things just right."),
    "toolbox": ("\U0001F527", "Let's get building."),
}


def reaction_for_module(module_id: str, display_name: str) -> tuple[str, str]:
    """Pure lookup logic — testable without Qt (see tests/test_character_panel.py)."""
    if module_id in MODULE_REACTIONS:
        return MODULE_REACTIONS[module_id]
    return (_DEFAULT_ICON, f"Watching over {display_name}.")


def idle_line(index: int) -> str:
    """Pure lookup logic, wrapping around _IDLE_LINES — testable without Qt."""
    return _IDLE_LINES[index % len(_IDLE_LINES)]


class CharacterPanel(QFrame):
    """Reactive companion panel — see module docstring."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setObjectName("CharacterPanel")
        self.setMinimumWidth(220)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(18)

        # A fixed-size circular badge (same "icon in a colored disc"
        # treatment gui/widgets/module_button.py's redesign introduced
        # for #ModuleButtonIcon) instead of a bare, inline-styled emoji
        # floating in empty space — found via rendering the old version
        # that a huge emoji directly on the panel's own background read
        # as placeholder art rather than an intentional character slot.
        # Object name + theme QSS, not setStyleSheet() — every other
        # widget in this app pulls its look from the QApplication-level
        # cascade (see gui/styles.py's module docstring); a widget-level
        # setStyleSheet() call breaks that cascade for itself and its
        # children.
        self._icon_label = QLabel(_HOME_ICON)
        self._icon_label.setObjectName("CharacterIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(96, 96)

        self._text_label = QLabel(_HOME_LINE)
        self._text_label.setObjectName("CharacterPlaceholderText")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setWordWrap(True)
        self._text_label.setFixedWidth(180)

        layout.addWidget(self._icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._text_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        self.context.events.subscribe("module.opened", self._on_module_opened)
        self.context.events.subscribe("menu.shown", self._on_menu_shown)
        self.context.events.subscribe("home.shown", self._on_home_shown)
        self.context.events.subscribe("notification.created", self._on_notification_created)

        self._last_event_at = time.monotonic()
        self._idle_index = 0
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._on_idle_tick)
        self._idle_timer.start(_IDLE_TICK_MS)

    def unsubscribe(self) -> None:
        """Must be called before this widget is destroyed — see module docstring."""
        self._idle_timer.stop()
        self.context.events.unsubscribe("module.opened", self._on_module_opened)
        self.context.events.unsubscribe("menu.shown", self._on_menu_shown)
        self.context.events.unsubscribe("home.shown", self._on_home_shown)
        self.context.events.unsubscribe("notification.created", self._on_notification_created)

    def _on_module_opened(self, module_id: str) -> None:
        display_name = self._display_name_for(module_id)
        icon, line = reaction_for_module(module_id, display_name)
        self._apply_reaction(icon, line)

    def _on_menu_shown(self, **kwargs) -> None:
        self._apply_reaction(_MENU_ICON, _MENU_LINE)

    def _on_home_shown(self, **kwargs) -> None:
        self._apply_reaction(_HOME_ICON, _HOME_LINE)

    def _on_notification_created(self, notification) -> None:
        self._apply_reaction(_NOTIFICATION_ICON, f'"{notification.title}"')

    def _on_idle_tick(self) -> None:
        if time.monotonic() - self._last_event_at < _IDLE_THRESHOLD_SECONDS:
            return
        self._set_display(_DEFAULT_ICON, idle_line(self._idle_index))
        self._idle_index += 1

    def _display_name_for(self, module_id: str) -> str:
        """Best-effort human-readable fallback name if the module_id itself has to stand in for it."""
        return module_id.replace("_", " ").title()

    def _apply_reaction(self, icon: str, line: str) -> None:
        """A real event (module/menu/notification) — updates the display and resets the idle clock."""
        self._set_display(icon, line)
        self._last_event_at = time.monotonic()
        self._idle_index = 0

    def _set_display(self, icon: str, line: str) -> None:
        self._icon_label.setText(icon)
        self._text_label.setText(line)
