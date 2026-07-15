"""
modules.assistant.module
=========================

Assistant Chat UI — docs/ROADMAP.md milestones 5.2 (text chat), 5.3
(voice), 5.4 (device-help grounding), and 5.5 (tool use / action
execution). A chat screen (scrollback + input box) wired to
`AppContext.llm` (core/llm_manager.py), plus a push-to-talk "Hold to
Talk" button wired to `AppContext.voice` (core/voice_manager.py) for
speech in, speech out.

**2026-07-14 aesthetic pass part 4** (docs/ROADMAP.md): the pure
request-building logic this module used to own directly
(`format_chat_line`/`split_safe_tool_calls`/`looks_like_action_request`/
`build_chat_request`) moved to `core/assistant_chat.py`, and the two
`QThread` workers below moved to `core/chat_worker.py`/`core/tts_worker.py`
— once `gui/character_panel.py`'s sidebar chat needed the exact same
logic, it had to live in `core/` rather than here, since `gui/` may
import `core/` directly but must never import `modules/`
(CLAUDE.md's one-directional layering). This module still owns the
full-screen widget/voice/GPIO wiring; only the non-Qt pieces moved.

**2026-07-14 aesthetic pass part 5**: ChatGPT-style redesign, at the
user's explicit request — a left-hand conversation history (auto-titled,
reviewable, deletable, click-to-continue) alongside the chat itself, and
a "🧠 Memories" button opening `gui/user_memory_dialog.py`. The screen no
longer owns its own single chat transcript — it's a live *view* over
`AppContext.conversations` (`core/conversation_manager.py`), the same
active conversation `gui/character_panel.py`'s sidebar chat reads and
appends to. Neither widget renders from its own local message list;
both re-render from `ConversationManager` whenever it publishes
`"conversation.updated"` (subscribed once in `get_widget()`), which is
what keeps the two surfaces showing the same conversation without a
direct reference to each other — same event-bus-mediated-reactivity
pattern this codebase already uses for module-navigation events.

`_on_send()` first classifies the prompt with `looks_like_action_request()`
against `AppContext.assistant_actions.gating_keywords()` — the live union
of every registered action's own `trigger_phrases`
(core/assistant_actions.py), not a hand-maintained list in this file — and
branches on the result, because grounding and tool-calling actively
interfere with each other:

- **Information questions** (the common case) are run through
  `AppContext.device_help.build_grounded_prompt()`
  (core/device_help_manager.py) before reaching the LLM — the actual text
  sent as the chat message is the retrieval-grounded version (M.I.A.'s own
  docs + module metadata + Reference Library as context), not the user's
  raw words, though the chat log still displays what the user actually
  typed/said. No tools are attached. This is deliberate scope, not an
  accident: docs/HARDWARE.md's hardware note says the realistic on-device
  model size (1-7B params) should be aimed at "device help, structured
  Q&A" rather than open-ended conversation.
- **Action requests** skip grounding entirely and send the user's raw
  prompt with `AppContext.assistant_actions` (core/assistant_actions.py)'s
  registered tools attached, so the model can perform an action (open a
  module, add an alarm/note/inventory item).

Two real-usage bugs drove this split, both found only against the live
model, not mocks:
1. Attaching tools to *every* message made the model hallucinate a
   nonexistent module_id and call `open_module` for a plain information
   question ("What can you tell me about Honda Civics?") that had no
   grounded match, instead of just saying "I don't know" — fixed by only
   attaching tools when the prompt looks action-oriented.
2. Grounding *every* message (including action requests) then broke the
   opposite case: "Set an alarm called Wake Up for 07:00" pulled in
   irrelevant doc chunks (e.g. `docs/ADDING_MODULES.md`, matched on the
   word "add") that convinced the model the conversation was about
   M.I.A.'s own developer docs, so it answered in prose instead of
   calling `add_alarm` — fixed by skipping grounding for action requests
   and sending the raw prompt instead.

Tool calls are executed here, in `_on_reply()` — which Qt's
queued-connection signal delivery guarantees runs on the GUI thread (see
`ChatWorker`'s docstring) — not inside the worker thread, since an action
like `open_module` needs to touch the GUI. This is **not** the
Self-Modification / Dev Mode staged plan in docs/ROADMAP.md (that's
specifically about the assistant editing M.I.A.'s own source code);
these are just ordinary app actions a user could already do by hand.

Two blocking operations each get their own scoped `QThread` rather than
running on the GUI thread:
  - `context.llm.chat_with_tools()` runs on `core.chat_worker.ChatWorker`.
  - `context.voice.synthesize()` + `.play()` run on
    `core.tts_worker.TTSWorker` (playback duration scales
    with reply length).
Speech-to-text (`context.voice.transcribe()`) runs synchronously on the
GUI thread — Vosk's small model transcribes a short push-to-talk clip
in well under a second in practice, so this hasn't needed the same
worker-thread treatment; revisit if a future larger STT model changes
that.

Only one LLM reply can be in flight at a time; input/send/mic are
disabled for that duration and re-enabled in `_on_worker_finished`,
which always runs (success or "unavailable"), so the UI can never get
stuck disabled. `context.llm.chat_with_tools()` / `context.voice.*`
returning `None`/`False` means the backend logged a warning and
couldn't be reached — surfaced here as a status line, never a crash.

Two more background `core.generate_worker.GenerateWorker` calls fire
*after* a plain-text reply is shown (never before/blocking it): title
generation (only once, the first time a conversation has a real
exchange and its title is still the default) and memory extraction
(every exchange) — both best-effort, both silently do nothing further
if the LLM is unreachable or returns nothing usable. Not fired for
tool-call replies — "add a waypoint" doesn't need a title or memory
extraction pass of its own.

Push-to-talk itself can be triggered two ways, unified by
`core.push_to_talk_trigger.PushToTalkTrigger`: the on-screen "Hold to
Talk" button (dev, and always available as a fallback) or a real GPIO
button on the Pi (`voice.push_to_talk_gpio_pin` in config) — see that
module's docstring for why a `QObject`+signals is needed here rather
than a plain callback.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.assistant_chat import (
    build_chat_request,
    build_memory_extraction_prompt,
    build_title_generation_prompt,
    clean_generated_title,
    format_chat_line,
    parse_extracted_memories,
    split_safe_tool_calls,
)
from core.chat_worker import ChatWorker
from core.conversation_manager import DEFAULT_TITLE, Conversation
from core.generate_worker import GenerateWorker
from core.llm_manager import ChatReply
from core.logger import get_logger
from core.push_to_talk_trigger import PushToTalkTrigger
from core.tts_worker import TTSWorker
from gui.delete_confirm_dialog import DeleteConfirmDialog
from gui.user_memory_dialog import UserMemoryDialog
from gui.widgets.conversation_card import ConversationCard
from modules.module_base import ModuleBase

log = get_logger(__name__)

_LLM_UNAVAILABLE_STATUS = "Assistant unavailable — is Ollama running?"
_MIC_UNAVAILABLE_STATUS = "Microphone unavailable."
_STT_UNAVAILABLE_STATUS = "Speech-to-text unavailable."


class AssistantModule(ModuleBase):
    module_id = "assistant"
    display_name = "Assistant"
    description = "Conversational assistant and local AI."
    icon = "\U0001F5E8"  # speech balloon

    def __init__(self, context) -> None:
        super().__init__(context)
        self._log: Optional[QPlainTextEdit] = None
        self._input: Optional[QLineEdit] = None
        self._send_button: Optional[QPushButton] = None
        self._talk_button: Optional[QPushButton] = None
        self._status_label: Optional[QLabel] = None
        self._conversation_list_layout: Optional[QVBoxLayout] = None
        self._worker: Optional[ChatWorker] = None
        self._tts_worker: Optional[TTSWorker] = None
        self._title_worker: Optional[GenerateWorker] = None
        self._memory_worker: Optional[GenerateWorker] = None
        self._ptt_trigger: Optional[PushToTalkTrigger] = None
        self._recording = False
        self._conversation: Optional[Conversation] = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QHBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(20)

        outer.addWidget(self._build_conversation_sidebar())
        outer.addWidget(self._build_chat_pane(), stretch=1)

        # GPIO path is a no-op unless voice.push_to_talk_gpio_pin is
        # configured and gpiozero + real hardware are present — see
        # core/push_to_talk_trigger.py. Both paths call the exact same
        # handlers as the on-screen button.
        self._ptt_trigger = PushToTalkTrigger(self.context, parent=widget)
        self._ptt_trigger.pressed.connect(self._on_talk_pressed)
        self._ptt_trigger.released.connect(self._on_talk_released)

        self.context.events.subscribe("conversation.updated", self._on_conversation_updated)
        self.context.events.subscribe("conversation.active_changed", self._on_conversation_active_changed)

        self._load_active_conversation()
        self._refresh_conversation_list()
        self._refresh_availability()
        return widget

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_conversation_sidebar(self) -> QWidget:
        container = QFrame()
        container.setFixedWidth(220)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        new_button = QPushButton("+ New Conversation")
        new_button.setObjectName("AppsLaunchButton")
        new_button.clicked.connect(self._on_new_conversation)
        layout.addWidget(new_button)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        list_container = QWidget()
        self._conversation_list_layout = QVBoxLayout(list_container)
        self._conversation_list_layout.setSpacing(8)
        self._conversation_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(list_container)
        layout.addWidget(scroll, stretch=1)

        memories_button = QPushButton("\U0001F9E0 Memories")
        memories_button.setObjectName("HeaderButton")
        memories_button.clicked.connect(self._on_open_memories)
        layout.addWidget(memories_button)

        return container

    def _build_chat_pane(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        self._log = QPlainTextEdit()
        self._log.setObjectName("ChatLog")
        self._log.setReadOnly(True)
        layout.addWidget(self._log, stretch=1)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SubtitleLabel")
        layout.addWidget(self._status_label)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask the assistant…")
        self._input.returnPressed.connect(self._on_send)
        input_row.addWidget(self._input, stretch=1)

        self._send_button = QPushButton("Send")
        self._send_button.clicked.connect(self._on_send)
        input_row.addWidget(self._send_button)

        self._talk_button = QPushButton("\U0001F3A4  Hold to Talk")
        self._talk_button.pressed.connect(self._on_talk_pressed)
        self._talk_button.released.connect(self._on_talk_released)
        input_row.addWidget(self._talk_button)

        layout.addLayout(input_row)
        return container

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def _refresh_availability(self) -> None:
        if self.context.llm is not None and self.context.llm.is_available():
            self._status_label.setText("")
        else:
            self._status_label.setText(_LLM_UNAVAILABLE_STATUS)

    # ------------------------------------------------------------------
    # Conversation history (left pane)
    # ------------------------------------------------------------------

    def _load_active_conversation(self) -> None:
        self._conversation = self.context.conversations.get_or_create_active_conversation()
        self._render_conversation_log()

    def _render_conversation_log(self) -> None:
        self._log.clear()
        for message in self._conversation.messages:
            speaker = "You" if message.role == "user" else self.display_name
            self._log.appendPlainText(format_chat_line(speaker, message.content))

    def _refresh_conversation_list(self) -> None:
        while self._conversation_list_layout.count():
            item = self._conversation_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # See gui/character_panel.py's _refresh_suggestions() for
                # why hide()+setParent(None) is needed before
                # deleteLater() — a real ghosting bug found there
                # otherwise.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        active_id = self._conversation.conversation_id if self._conversation else None
        for conversation in self.context.conversations.all_conversations():
            card = ConversationCard(conversation)
            card.set_selected(conversation.conversation_id == active_id)
            card.activated.connect(self._on_select_conversation)
            card.delete_requested.connect(self._on_delete_conversation)
            self._conversation_list_layout.addWidget(card)

    def _on_select_conversation(self, conversation_id: str) -> None:
        # Just changes the pointer — _on_conversation_active_changed()
        # (subscribed in get_widget()) does the actual reload, since
        # set_active_conversation_id() publishes that event synchronously
        # on the same call stack. No-op if already the active one, same
        # as before, to avoid an unnecessary republish.
        if self._conversation is not None and conversation_id == self._conversation.conversation_id:
            return
        self.context.conversations.set_active_conversation_id(conversation_id)

    def _on_new_conversation(self) -> None:
        self.context.conversations.start_new_active_conversation()

    def _on_delete_conversation(self, conversation_id: str) -> None:
        conversation = self.context.conversations.get_conversation(conversation_id)
        if conversation is None:
            return
        dialog = DeleteConfirmDialog(conversation.title, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        # delete_conversation() itself publishes "conversation.updated"
        # (refreshes the list either way) and, if this was the active
        # conversation, also "conversation.active_changed" (reloads a
        # fresh one) — both subscribed in get_widget(), nothing further
        # needed here.
        self.context.conversations.delete_conversation(conversation_id)

    def _on_open_memories(self) -> None:
        dialog = UserMemoryDialog(self.context, parent=self._log.window())
        dialog.exec()

    def _on_conversation_updated(self, conversation_id: str) -> None:
        """
        Fires for a write from *either* chat surface (this module or
        gui/character_panel.py's sidebar) — reload from
        ConversationManager rather than assuming this widget's own
        in-memory `self._conversation` is still current, since the
        write that triggered this may have come from the sidebar.
        """
        if self._conversation is not None and conversation_id == self._conversation.conversation_id:
            self._conversation = self.context.conversations.get_conversation(conversation_id) or self._conversation
            self._render_conversation_log()
        self._refresh_conversation_list()

    def _on_conversation_active_changed(self, conversation_id: Optional[str]) -> None:
        """
        The *active conversation itself* changed — from either surface
        (this module's own New/switch/delete actions, or the sidebar
        starting fresh) — always reload, regardless of what this widget
        was previously displaying. See core/conversation_manager.py's
        set_active_conversation_id() docstring for why this is a
        separate event from "conversation.updated".
        """
        self._load_active_conversation()
        self._refresh_conversation_list()

    # ------------------------------------------------------------------
    # Text sending
    # ------------------------------------------------------------------

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
            self._status_label.setText(_LLM_UNAVAILABLE_STATUS)
            return

        if reply.tool_calls:
            # Executed here, not inside ChatWorker — see this module's
            # docstring and ChatWorker's for why tool execution needs
            # the GUI thread.
            calls_to_execute, skipped_calls = split_safe_tool_calls(reply.tool_calls, self.context.assistant_actions)
            if skipped_calls:
                skipped_names = ", ".join(tc.name for tc in skipped_calls)
                log.warning(
                    "Skipped destructive tool call(s) bundled with other calls in one reply: %s", skipped_names
                )
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

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        self._talk_button.setEnabled(not busy)
        if busy:
            self._status_label.setText("Thinking…")

    # ------------------------------------------------------------------
    # Auto-titling + memory extraction — both best-effort, both fired
    # only after a plain-text reply is already shown (never blocking).
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

    # ------------------------------------------------------------------
    # Push-to-talk (speech in)
    # ------------------------------------------------------------------

    def _on_talk_pressed(self) -> None:
        if self.context.voice is None or self._worker is not None or self._recording:
            return
        if not self.context.voice.start_recording():
            self._status_label.setText(_MIC_UNAVAILABLE_STATUS)
            return
        self._recording = True
        self._status_label.setText("Listening…")

    def _on_talk_released(self) -> None:
        if self.context.voice is None or not self._recording:
            return
        self._recording = False

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

    # ------------------------------------------------------------------
    # Speech out
    # ------------------------------------------------------------------

    def _speak(self, text: str) -> None:
        if self.context.voice is None or self._tts_worker is not None:
            return
        output_path = Path(tempfile.gettempdir()) / "mia_assistant_reply.wav"
        self._tts_worker = TTSWorker(self.context.voice, text, output_path)
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.start()

    def _on_tts_finished(self) -> None:
        if self._tts_worker is not None:
            self._tts_worker.deleteLater()
            self._tts_worker = None
