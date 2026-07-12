"""
gui.character_panel
====================

M.I.A.'s reactive companion panel — docs/ROADMAP.md milestone 6.2.
Subscribes to the module-activity events milestone 6.1 added
("module.opened"/"menu.shown" from gui/main_window.py's navigation
methods) plus the existing "notification.created" event, and updates
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

Idle ambient behavior (rotating through lines when nothing's happened
in a while) is milestone 6.3, not built here.

Cleanup: unsubscribe() must be called before this widget is destroyed
(gui/main_window.py's closeEvent() does this) — otherwise EventBus
would keep calling into a deleted Qt widget on the next publish(),
same reasoning as MainWindow's own event unsubscription in closeEvent.

Likely future implementation notes (not built yet, intentionally):
    - Probably a QLabel with an animated QMovie, or a small QOpenGLWidget
      / QML view if the character needs more complex animation.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from core.app_context import AppContext

_DEFAULT_ICON = "\U0001F916"  # robot
_MENU_ICON = "\U0001F3E0"  # house
_NOTIFICATION_ICON = "\U0001F514"  # bell

_MENU_LINE = "What should we work on?"

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

        self._icon_label = QLabel(_DEFAULT_ICON)
        self._icon_label.setStyleSheet("font-size: 48px;")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._text_label = QLabel(_MENU_LINE)
        self._text_label.setObjectName("CharacterPlaceholderText")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setWordWrap(True)

        layout.addWidget(self._icon_label)
        layout.addWidget(self._text_label)

        self.context.events.subscribe("module.opened", self._on_module_opened)
        self.context.events.subscribe("menu.shown", self._on_menu_shown)
        self.context.events.subscribe("notification.created", self._on_notification_created)

    def unsubscribe(self) -> None:
        """Must be called before this widget is destroyed — see module docstring."""
        self.context.events.unsubscribe("module.opened", self._on_module_opened)
        self.context.events.unsubscribe("menu.shown", self._on_menu_shown)
        self.context.events.unsubscribe("notification.created", self._on_notification_created)

    def _on_module_opened(self, module_id: str) -> None:
        display_name = self._display_name_for(module_id)
        icon, line = reaction_for_module(module_id, display_name)
        self._set_reaction(icon, line)

    def _on_menu_shown(self, **kwargs) -> None:
        self._set_reaction(_MENU_ICON, _MENU_LINE)

    def _on_notification_created(self, notification) -> None:
        self._set_reaction(_NOTIFICATION_ICON, f'"{notification.title}"')

    def _display_name_for(self, module_id: str) -> str:
        """Best-effort human-readable fallback name if the module_id itself has to stand in for it."""
        return module_id.replace("_", " ").title()

    def _set_reaction(self, icon: str, line: str) -> None:
        self._icon_label.setText(icon)
        self._text_label.setText(line)
