"""
gui.character_panel
====================

MIA's reactive companion panel — docs/ROADMAP.md milestone 6.2.
Subscribes to the module-activity events milestone 6.1 added
("module.opened"/"menu.shown" from gui/main_window.py's navigation
methods, plus "home.shown" added in the 2026-07-14 aesthetic pass part 3
once Home became its own landing screen separate from the Apps grid)
plus the existing "notification.created" event, and updates
its displayed icon/line to react to whatever's happening — the "reacts
to whatever module is active" behavior the v0.6 phase-plan entry calls
for.

`MODULE_REACTIONS` is a static per-module_id flavor-line mapping kept
in this one file (not spread across every module's own code) so adding
a new module never requires touching this file; an unlisted module
just gets a generic fallback line built from its display_name.

**2026-07-15: the static emoji icon is now `gui/presence_widget.py`'s
`PresenceWidget`** — a living orb (extends `gui/boot_core_widget.py`'s
breathing-glow technique) that renders each module's icon centered in
it, same as before, but now also communicates *state* (idle/thinking/
loading/notification) through color, pulse speed, and a rotating
highlight ring for "actively working" states — see
`docs/VISION.md`'s Home visual-identity section for the design brief
this answers. `_apply_reaction()`/`_set_display()` below take an
explicit `state` now, not just an icon+line; `_start_transient_state()`
handles states that should auto-revert to idle after a short delay
(module-open "loading," a notification) rather than sticking
permanently the way the icon swap used to.

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
now also holds a compact, always-available chat. **2026-07-18: gained
full voice parity with the full-screen Assistant module** — push-to-
talk (on-screen click only, see _build_chat_section()'s docstring for
why it doesn't share a PushToTalkTrigger with the full module) and a
Stop button to interrupt mid-sentence — at the user's request, since
this panel is now meant to replace keeping the full Assistant screen
open all the time, not just supplement it. Reuses
`core.assistant_chat.build_chat_request()`/`split_safe_tool_calls()`
and `core.chat_worker.ChatWorker` — the exact same request-building and
tool-execution-safety logic the full Assistant module uses, not a
reimplementation, so the two surfaces can never silently drift apart in
behavior. `gui/` may import `core/` directly but must never import
`modules/` (CLAUDE.md's one-directional layering), which is why that
shared logic lives in `core/` now instead of
`modules/assistant/module.py` — see core/assistant_chat.py's docstring
for the full reasoning.

**2026-07-16: real message bubbles** (`gui/widgets/chat_bubble.py`'s
`ChatBubble`, alternating right/left alignment per the ForMIA mockup)
replace the plain scrolling `QPlainTextEdit` log this panel shipped
with — `format_chat_line()`'s "Speaker: text" plain-string formatting
is no longer used here (each `ConversationMessage`'s `.role`/`.content`
goes straight into a bubble instead); the full Assistant module screen
keeps using it unchanged for its own denser, more terminal-like log.

Also shows a handful of clickable suggested-prompt buttons above the
input box, refreshed every time the reaction changes (a new module
opens, or Home/Apps is shown) via
`core.assistant_chat.suggested_prompts_for_module()` — contextual to
whatever screen is currently active, at the user's explicit request
("the assistant should recommend questions that it has a good ability
to help with"). Clicking one sends it exactly like typing it and
pressing Send.

**2026-07-14 aesthetic pass part 5**: this panel no longer owns its own
chat transcript — like `modules/assistant/module.py`'s full screen, it's
a live *view* over `AppContext.conversations`
(`core/conversation_manager.py`)'s active conversation, re-rendering
whenever `"conversation.updated"`/`"conversation.active_changed"`
publish (subscribed here alongside the existing nav events), which is
what keeps this compact chat and the full-screen one always showing the
same conversation without a direct reference to each other. Also fires
the same background auto-titling/memory-extraction
(`core.generate_worker.GenerateWorker`) the full screen does after a
plain-text reply — whichever surface the user is actually typing into
does the extracting; the other just reflects the result via the event.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.assistant_chat import (
    build_chat_request,
    build_memory_extraction_prompt,
    build_title_generation_prompt,
    clean_generated_title,
    parse_extracted_memories,
    split_safe_tool_calls,
    suggested_prompts_for_module,
)
from core.chat_worker import ChatWorker
from core.conversation_manager import DEFAULT_TITLE
from core.generate_worker import GenerateWorker
from core.llm_manager import ChatReply
from core.tts_worker import TTSWorker
from gui.conversation_history_dialog import ConversationHistoryDialog
from gui.presence_widget import PresenceWidget
from gui.widgets.chat_bubble import ChatBubble

_LOADING_STATE_MS = 700
_NOTIFICATION_STATE_MS = 3000

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

# Same wording as modules/assistant/module.py's own copies of these —
# can't import them directly (gui/ may import core/ but never modules/,
# CLAUDE.md's one-directional layering).
_MIC_UNAVAILABLE_STATUS = "Microphone unavailable."
_STT_UNAVAILABLE_STATUS = "Speech-to-text unavailable."
_VOICE_INPUT_DISABLED_STATUS = "Voice input is turned off (Quick Bus, Home dashboard)."

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
        self._title_worker: Optional[GenerateWorker] = None
        self._memory_worker: Optional[GenerateWorker] = None
        self._tts_worker: Optional[TTSWorker] = None
        self._recording = False
        self._conversation = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # PresenceWidget self-paints its own glow/motion (same technique
        # as gui/boot_core_widget.py's PulsingCoreWidget) rather than
        # pulling a look from the theme QSS cascade the way every other
        # widget in this app does — that's deliberate here, the whole
        # point is state-driven color/animation a static stylesheet rule
        # can't express. See gui/presence_widget.py's docstring.
        self._presence = PresenceWidget(diameter=96)
        self._presence.set_glyph(_HOME_ICON)

        self._text_label = QLabel(_HOME_LINE)
        self._text_label.setObjectName("CharacterPlaceholderText")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setWordWrap(True)
        self._text_label.setFixedWidth(180)

        layout.addWidget(self._presence, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._text_label)

        self._transient_state_timer = QTimer(self)
        self._transient_state_timer.setSingleShot(True)
        self._transient_state_timer.timeout.connect(lambda: self._presence.set_state("idle"))

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
        self.context.events.subscribe("conversation.updated", self._on_conversation_updated)
        self.context.events.subscribe("conversation.active_changed", self._on_conversation_active_changed)

        self._last_event_at = time.monotonic()
        self._idle_index = 0
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._on_idle_tick)
        self._idle_timer.start(_IDLE_TICK_MS)

        # 2026-07-18: real user ask — the sidebar used to load and
        # render whatever conversation was last active, meaning a long-
        # running chat history greeted the user again on every single
        # app launch. Starts a brand new conversation on construction
        # instead (this is also what the full Assistant module's "+ New
        # Conversation" button does) — start_new_active_conversation()
        # publishes "conversation.active_changed" synchronously, which
        # _on_conversation_active_changed() (subscribed above) already
        # reloads/renders from, so no separate render call is needed
        # here. The new "History" button is the way back to an older one.
        self.context.conversations.start_new_active_conversation()

    def unsubscribe(self) -> None:
        """Must be called before this widget is destroyed — see module docstring."""
        self._idle_timer.stop()
        self._transient_state_timer.stop()
        self._presence.stop()
        self.context.events.unsubscribe("module.opened", self._on_module_opened)
        self.context.events.unsubscribe("menu.shown", self._on_menu_shown)
        self.context.events.unsubscribe("home.shown", self._on_home_shown)
        self.context.events.unsubscribe("notification.created", self._on_notification_created)
        self.context.events.unsubscribe("conversation.updated", self._on_conversation_updated)
        self.context.events.unsubscribe("conversation.active_changed", self._on_conversation_active_changed)

    def _load_active_conversation(self) -> None:
        self._conversation = self.context.conversations.get_or_create_active_conversation()
        self._render_conversation_log()

    def _render_conversation_log(self) -> None:
        """Full rebuild on every call (a new/switched/updated
        conversation), same "clear and refill" shape as
        gui/home_dashboard.py's widget grid — explicit hide() +
        setParent(None) before deleteLater() since this app has hit
        real ghosted-widget bugs from skipping that step (see
        gui/home_dashboard.py's _build_widgets_grid() docstring). The
        trailing stretch is removed and re-added each time so bubbles
        always stack above it, not after it."""
        while self._chat_log_layout.count():
            item = self._chat_log_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        for message in self._conversation.messages:
            bubble = ChatBubble(message.role, message.content)
            alignment = Qt.AlignmentFlag.AlignRight if message.role == "user" else Qt.AlignmentFlag.AlignLeft
            self._chat_log_layout.addWidget(bubble, alignment=alignment)
            # A widget added to a layout isn't always auto-shown by Qt
            # on every platform — same real gap gui/home_dashboard.py's
            # widget grid hit (see its _build_widgets_grid() docstring).
            bubble.show()

        self._chat_log_layout.addStretch()
        self._chat_log_layout.activate()

        # Scroll to the latest message — QScrollArea has no QPlainTextEdit-
        # style auto-scroll-on-append, so this has to be explicit. Queued
        # via QTimer.singleShot(0, ...) because the scrollbar's maximum
        # isn't updated to reflect the new content until after this
        # method returns and Qt processes the pending layout.
        QTimer.singleShot(0, self._scroll_chat_log_to_bottom)

    def _scroll_chat_log_to_bottom(self) -> None:
        scrollbar = self._chat_log_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_conversation_updated(self, conversation_id: str) -> None:
        """A write from either this panel or the full Assistant module — reflect it if it's ours."""
        if self._conversation is not None and conversation_id == self._conversation.conversation_id:
            self._conversation = self.context.conversations.get_conversation(conversation_id) or self._conversation
            self._render_conversation_log()

    def _on_conversation_active_changed(self, conversation_id: Optional[str]) -> None:
        """The active conversation itself changed (new/switched/deleted from the full module) — always reload."""
        self._load_active_conversation()

    def _on_module_opened(self, module_id: str) -> None:
        display_name = self._display_name_for(module_id)
        icon, line = reaction_for_module(module_id, display_name)
        self._apply_reaction(icon, line)
        self._start_transient_state("loading", _LOADING_STATE_MS)
        self._refresh_suggestions(module_id=module_id)

    def _on_menu_shown(self, **kwargs) -> None:
        self._apply_reaction(_MENU_ICON, _MENU_LINE)
        self._refresh_suggestions(module_id=None)

    def _on_home_shown(self, **kwargs) -> None:
        self._apply_reaction(_HOME_ICON, _HOME_LINE)
        self._refresh_suggestions(module_id=None)

    def _on_notification_created(self, notification) -> None:
        self._apply_reaction(_NOTIFICATION_ICON, f'"{notification.title}"')
        self._start_transient_state("notification", _NOTIFICATION_STATE_MS)

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

    def _start_transient_state(self, state: str, duration_ms: int) -> None:
        """A presence state that should auto-revert to idle after a
        short delay rather than sticking permanently — module-open
        "loading" and a notification's brief pulse, per
        docs/VISION.md's "communicate her state through motion,
        lighting, and animation" ask. Restarting the timer on every
        call means a second transient event (e.g. two notifications
        close together) simply extends the current one rather than
        fighting it."""
        self._presence.set_state(state)
        self._transient_state_timer.start(duration_ms)

    def _set_display(self, icon: str, line: str) -> None:
        self._presence.set_glyph(icon)
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

        # 2026-07-18: real user ask — a way to reach older conversations
        # now that this panel starts fresh every launch instead of
        # showing whatever was last active (see __init__'s comment).
        history_row = QHBoxLayout()
        history_row.addStretch()
        self._history_button = QPushButton("\U0001F553 History")
        self._history_button.setObjectName("HeaderButton")
        self._history_button.clicked.connect(self._on_open_history)
        history_row.addWidget(self._history_button)
        layout.addLayout(history_row)

        self._chat_log_scroll = QScrollArea()
        self._chat_log_scroll.setObjectName("ChatLog")
        self._chat_log_scroll.setWidgetResizable(True)
        self._chat_log_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._chat_log_container = QWidget()
        self._chat_log_layout = QVBoxLayout(self._chat_log_container)
        self._chat_log_layout.setContentsMargins(4, 4, 4, 4)
        self._chat_log_layout.setSpacing(8)
        self._chat_log_layout.addStretch()
        self._chat_log_scroll.setWidget(self._chat_log_container)
        layout.addWidget(self._chat_log_scroll, stretch=1)

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

        # 2026-07-18: real user ask — push-to-talk and a stop button,
        # matching modules/assistant/module.py's full-screen voice
        # controls. On their own row since this panel can be as narrow
        # as 220px (setMinimumWidth above) — input+Send+Talk+Stop all in
        # one row would crowd badly at that width. Deliberately does NOT
        # construct its own core.push_to_talk_trigger.PushToTalkTrigger —
        # that would bind a second gpiozero.Button to the same physical
        # GPIO pin the full Assistant module's own trigger already binds
        # to, which fails on real hardware. The physical PTT button (if
        # ever wired) drives the full module only, for now; this panel's
        # mic is on-screen-click only, same as this method's Send button.
        voice_row = QHBoxLayout()
        self._talk_button = QPushButton("\U0001F3A4  Hold to Talk")
        self._talk_button.setObjectName("TalkButton")
        self._talk_button.pressed.connect(self._on_talk_pressed)
        self._talk_button.released.connect(self._on_talk_released)
        voice_row.addWidget(self._talk_button, stretch=1)

        self._stop_speaking_button = QPushButton("⏹  Stop")
        self._stop_speaking_button.setObjectName("StopSpeakingButton")
        self._stop_speaking_button.setEnabled(False)
        self._stop_speaking_button.clicked.connect(self._on_stop_speaking)
        voice_row.addWidget(self._stop_speaking_button)

        layout.addLayout(voice_row)
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
            # AlignLeft so the pill-shaped chip sizes to its own text
            # (the ForMIA mockup's compact "chip" look) instead of
            # QVBoxLayout's default of stretching the button to the
            # panel's full width.
            self._suggestions_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)

    def _on_suggestion_clicked(self, prompt: str) -> None:
        self._input.setText(prompt)
        self._on_send()

    def _on_send(self) -> None:
        prompt = self._input.text().strip()
        if not prompt or self._worker is not None or self.context.llm is None:
            return

        self._input.clear()
        self._set_busy(True)
        self.context.conversations.add_message(self._conversation.conversation_id, "user", prompt)

        messages, tools = build_chat_request(self.context, self._conversation, prompt)

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
                self.context.conversations.add_message(
                    self._conversation.conversation_id,
                    "assistant",
                    f"(Skipped a possibly unintended action for safety: {skipped_names}. Ask for that on its own if you really want it.)",
                )
            for tool_call in calls_to_execute:
                confirmation = self.context.assistant_actions.execute(
                    self.context, tool_call.name, tool_call.arguments
                )
                self.context.conversations.add_message(self._conversation.conversation_id, "assistant", confirmation)
                self._speak(confirmation)
            self._status_label.setText("")
            return

        user_message = self._conversation.messages[-1].content if self._conversation.messages else ""
        self.context.conversations.add_message(self._conversation.conversation_id, "assistant", reply.content)
        self._status_label.setText("")
        self._speak(reply.content)
        self._maybe_generate_title(user_message, reply.content)
        self._extract_memories(user_message)

    def _on_worker_finished(self) -> None:
        self._set_busy(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    # ------------------------------------------------------------------
    # Auto-titling + memory extraction — same shape as
    # modules/assistant/module.py's, both best-effort and non-blocking.
    # ------------------------------------------------------------------

    def _maybe_generate_title(self, user_message: str, assistant_message: str) -> None:
        if self._conversation.title != DEFAULT_TITLE or self._title_worker is not None:
            return
        prompt = build_title_generation_prompt(user_message, assistant_message)
        self._title_worker = GenerateWorker(self.context.llm, prompt)
        conversation_id = self._conversation.conversation_id
        self._title_worker.result_ready.connect(lambda raw: self._on_title_generated(conversation_id, raw))
        self._title_worker.finished.connect(self._on_title_worker_finished)
        self._title_worker.start()

    def _on_title_generated(self, conversation_id: str, raw_title: Optional[str]) -> None:
        title = clean_generated_title(raw_title)
        if title is not None:
            self.context.conversations.set_title(conversation_id, title)

    def _on_title_worker_finished(self) -> None:
        if self._title_worker is not None:
            self._title_worker.deleteLater()
            self._title_worker = None

    def _extract_memories(self, user_message: str) -> None:
        if self._memory_worker is not None or self.context.user_memories is None:
            return
        prompt = build_memory_extraction_prompt(user_message)
        self._memory_worker = GenerateWorker(self.context.llm, prompt)
        conversation_id = self._conversation.conversation_id
        self._memory_worker.result_ready.connect(lambda raw: self._on_memories_extracted(conversation_id, raw))
        self._memory_worker.finished.connect(self._on_memory_worker_finished)
        self._memory_worker.start()

    def _on_memories_extracted(self, conversation_id: str, raw_text: Optional[str]) -> None:
        for fact in parse_extracted_memories(raw_text):
            self.context.user_memories.add_memory(fact, source_conversation_id=conversation_id)

    def _on_memory_worker_finished(self) -> None:
        if self._memory_worker is not None:
            self._memory_worker.deleteLater()
            self._memory_worker = None

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        self._talk_button.setEnabled(not busy)
        self._presence.set_state("thinking" if busy else "idle")
        if busy:
            self._status_label.setText("Thinking…")

    # ------------------------------------------------------------------
    # Conversation history popup
    # ------------------------------------------------------------------

    def _on_open_history(self) -> None:
        current_id = self._conversation.conversation_id if self._conversation else None
        dialog = ConversationHistoryDialog(self.context, current_id, parent=self)
        if dialog.exec() and dialog.selected_conversation_id is not None:
            if dialog.selected_conversation_id != current_id:
                self.context.conversations.set_active_conversation_id(dialog.selected_conversation_id)

    # ------------------------------------------------------------------
    # Push-to-talk (speech in) — same behavior as
    # modules/assistant/module.py's, see _build_chat_section()'s
    # docstring for why this panel doesn't share a PushToTalkTrigger
    # with it.
    # ------------------------------------------------------------------

    def _on_talk_pressed(self) -> None:
        if self.context.voice is None or self._worker is not None or self._recording:
            return
        if not self.context.config.get("voice.push_to_talk_enabled", True):
            self._status_label.setText(_VOICE_INPUT_DISABLED_STATUS)
            return
        if not self.context.voice.start_recording():
            self._status_label.setText(_MIC_UNAVAILABLE_STATUS)
            return
        self._recording = True
        self._set_talk_button_recording(True)
        self._status_label.setText("Listening…")

    def _on_talk_released(self) -> None:
        if self.context.voice is None or not self._recording:
            return
        self._recording = False
        self._set_talk_button_recording(False)

        wav_path = self.context.voice.stop_recording()
        if wav_path is None:
            self._status_label.setText(_MIC_UNAVAILABLE_STATUS)
            return

        self._status_label.setText("Transcribing…")
        transcript = self.context.voice.transcribe(wav_path)
        if not transcript:
            self._status_label.setText(_STT_UNAVAILABLE_STATUS)
            return

        self._input.setText(transcript)
        self._on_send()

    def _set_talk_button_recording(self, recording: bool) -> None:
        """Same dynamic-property technique as modules/assistant/module.py's Talk button."""
        self._talk_button.setProperty("recording", recording)
        self._talk_button.style().unpolish(self._talk_button)
        self._talk_button.style().polish(self._talk_button)

    # ------------------------------------------------------------------
    # Speech out
    # ------------------------------------------------------------------

    def _speak(self, text: str) -> None:
        if self.context.voice is None or self._tts_worker is not None:
            return
        output_path = Path(tempfile.gettempdir()) / "mia_character_panel_reply.wav"
        self._tts_worker = TTSWorker(self.context.voice, text, output_path)
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.start()
        self._stop_speaking_button.setEnabled(True)

    def _on_tts_finished(self) -> None:
        if self._tts_worker is not None:
            self._tts_worker.deleteLater()
            self._tts_worker = None
        self._stop_speaking_button.setEnabled(False)

    def _on_stop_speaking(self) -> None:
        if self.context.voice is not None:
            self.context.voice.stop_playback()
