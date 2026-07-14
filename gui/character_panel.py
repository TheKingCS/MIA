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

**2026-07-14 aesthetic pass part 4** (docs/ROADMAP.md): at the user's
request ("the section on the right of the screen with the robot icon
would be a perfect spot for the Assistant Conversations"), this panel
now also holds a compact, always-available chat — text-only (no mic/
TTS; the full modules/assistant/module.py screen in Apps still has
voice for a larger, focused session). Reuses
`core.assistant_chat.build_chat_request()`/`split_safe_tool_calls()`/
`format_chat_line()` and `core.chat_worker.ChatWorker` — the exact same
request-building and tool-execution-safety logic the full Assistant
module uses, not a reimplementation, so the two surfaces can never
silently drift apart in behavior. `gui/` may import `core/` directly
but must never import `modules/` (CLAUDE.md's one-directional
layering), which is why that shared logic lives in `core/` now instead
of `modules/assistant/module.py` — see core/assistant_chat.py's
docstring for the full reasoning.

Also shows a handful of clickable suggested-prompt buttons above the
input box, refreshed every time the reaction changes (a new module
opens, or Home/Apps is shown) via
`core.assistant_chat.suggested_prompts_for_module()` — contextual to
whatever screen is currently active, at the user's explicit request
("the assistant should recommend questions that it has a good ability
to help with"). Clicking one sends it exactly like typing it and
pressing Send.
"""

from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.assistant_chat import build_chat_request, format_chat_line, split_safe_tool_calls, suggested_prompts_for_module
from core.chat_worker import ChatWorker
from core.llm_manager import ChatReply

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

        self._worker: Optional[ChatWorker] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

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

        layout.addWidget(self._build_chat_section(), stretch=1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        self._refresh_suggestions(module_id=None)  # Home is the initial screen

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
        self._refresh_suggestions(module_id=module_id)

    def _on_menu_shown(self, **kwargs) -> None:
        self._apply_reaction(_MENU_ICON, _MENU_LINE)
        self._refresh_suggestions(module_id=None)

    def _on_home_shown(self, **kwargs) -> None:
        self._apply_reaction(_HOME_ICON, _HOME_LINE)
        self._refresh_suggestions(module_id=None)

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

    # ------------------------------------------------------------------
    # Sidebar chat — see this module's docstring for why the shared
    # logic lives in core/assistant_chat.py + core/chat_worker.py rather
    # than being reimplemented here.
    # ------------------------------------------------------------------

    def _build_chat_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._chat_log = QPlainTextEdit()
        self._chat_log.setObjectName("ChatLog")
        self._chat_log.setReadOnly(True)
        layout.addWidget(self._chat_log, stretch=1)

        self._suggestions_layout = QVBoxLayout()
        self._suggestions_layout.setSpacing(4)
        layout.addLayout(self._suggestions_layout)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SubtitleLabel")
        layout.addWidget(self._status_label)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask me anything…")
        self._input.returnPressed.connect(self._on_send)
        input_row.addWidget(self._input, stretch=1)

        self._send_button = QPushButton("Send")
        self._send_button.setObjectName("HeaderButton")
        self._send_button.clicked.connect(self._on_send)
        input_row.addWidget(self._send_button)

        layout.addLayout(input_row)
        return section

    def _refresh_suggestions(self, module_id: Optional[str]) -> None:
        # `takeAt()` only detaches a widget from the *layout* — the
        # widget itself stays a visible child of this panel, at its old
        # position, until Qt actually processes the deferred delete.
        # Since the new (often shorter) suggestion list is added in the
        # same call, that left stale buttons visibly overlapping the
        # new ones until some later, unpredictable event-loop tick —
        # found by rendering a real module switch, not visible from a
        # quick glance at the widget tree. `hide()` + `setParent(None)`
        # removes it from the screen immediately; `deleteLater()` still
        # handles the actual C++ object cleanup.
        while self._suggestions_layout.count():
            item = self._suggestions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        for prompt in suggested_prompts_for_module(module_id):
            button = QPushButton(prompt)
            button.setObjectName("SuggestionButton")
            button.setToolTip(prompt)
            # `clicked` passes a `checked` bool for a checkable button —
            # this one isn't, but the signal still forwards a positional
            # arg; wrap in a lambda so _on_suggestion_clicked only ever
            # sees the prompt text, not that bool.
            button.clicked.connect(lambda _checked=False, p=prompt: self._on_suggestion_clicked(p))
            self._suggestions_layout.addWidget(button)

    def _on_suggestion_clicked(self, prompt: str) -> None:
        self._input.setText(prompt)
        self._on_send()

    def _on_send(self) -> None:
        prompt = self._input.text().strip()
        if not prompt or self._worker is not None or self.context.llm is None:
            return

        self._chat_log.appendPlainText(format_chat_line("You", prompt))
        self._input.clear()
        self._set_busy(True)

        messages, tools = build_chat_request(self.context, prompt)

        self._worker = ChatWorker(self.context.llm, messages, tools)
        self._worker.result_ready.connect(self._on_reply)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_reply(self, reply: Optional[ChatReply]) -> None:
        if reply is None:
            self._status_label.setText("Assistant unavailable — is Ollama running?")
            return

        if reply.tool_calls:
            # Executed here, not inside ChatWorker — see
            # core/chat_worker.py's docstring for why tool execution
            # needs the GUI thread.
            calls_to_execute, skipped_calls = split_safe_tool_calls(reply.tool_calls, self.context.assistant_actions)
            if skipped_calls:
                skipped_names = ", ".join(tc.name for tc in skipped_calls)
                self._chat_log.appendPlainText(format_chat_line(
                    "M.I.A.",
                    f"(Skipped a possibly unintended action for safety: {skipped_names}. Ask for that on its own if you really want it.)",
                ))
            for tool_call in calls_to_execute:
                confirmation = self.context.assistant_actions.execute(
                    self.context, tool_call.name, tool_call.arguments
                )
                self._chat_log.appendPlainText(format_chat_line("M.I.A.", confirmation))
            self._status_label.setText("")
            return

        self._chat_log.appendPlainText(format_chat_line("M.I.A.", reply.content))
        self._status_label.setText("")

    def _on_worker_finished(self) -> None:
        self._set_busy(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        if busy:
            self._status_label.setText("Thinking…")
