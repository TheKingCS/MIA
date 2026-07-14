"""
modules.assistant.module
=========================

Assistant Chat UI — docs/ROADMAP.md milestones 5.2 (text chat), 5.3
(voice), 5.4 (device-help grounding), and 5.5 (tool use / action
execution). A chat screen (scrollback + input box) wired to
`AppContext.llm` (core/llm_manager.py), plus a push-to-talk "Hold to
Talk" button wired to `AppContext.voice` (core/voice_manager.py) for
speech in, speech out.

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
  - `context.llm.chat_with_tools()` runs on
    `modules.assistant.llm_worker.ChatWorker`.
  - `context.voice.synthesize()` + `.play()` run on
    `modules.assistant.tts_worker.TTSWorker` (playback duration scales
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
from typing import Iterable, Optional

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.llm_manager import ChatReply
from core.push_to_talk_trigger import PushToTalkTrigger
from modules.assistant.llm_worker import ChatWorker
from modules.assistant.tts_worker import TTSWorker
from modules.module_base import ModuleBase

_LLM_UNAVAILABLE_STATUS = "Assistant unavailable — is Ollama running?"
_MIC_UNAVAILABLE_STATUS = "Microphone unavailable."
_STT_UNAVAILABLE_STATUS = "Speech-to-text unavailable."

# Fallback keyword phrases, used only when looks_like_action_request()
# is called without an explicit `keywords` argument (e.g. exercising
# the pure classifier directly in tests/test_assistant_module.py).
# Production code (_on_send() below) instead passes
# `AppContext.assistant_actions.gating_keywords()` — the live union of
# every registered action's own `trigger_phrases`
# (core/assistant_actions.py), not this static list. Milestone 5.9
# moved gating phrases onto each action's own registration for exactly
# this reason: a hand-maintained central tuple like this one silently
# drifts out of sync once the registry grows past a handful of
# actions — this fallback exists purely so the classifier stays
# testable in isolation, not as the real source of truth.
_ACTION_REQUEST_KEYWORDS = (
    "open ", "launch ", "go to ", "switch to ", "take me to ",
    "set an alarm", "set a timer", "add an alarm", "remind me", "wake me up",
    "add a note", "take a note", "make a note", "write down", "jot down",
    "add to inventory", "add an inventory item", "inventory item",
    "recent activity", "activity log", "what have i done", "what have i been doing", "what did i do",
)


def format_chat_line(speaker: str, text: str) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_assistant_module.py)."""
    return f"{speaker}: {text}"


def looks_like_action_request(text: str, keywords: Iterable[str] = _ACTION_REQUEST_KEYWORDS) -> bool:
    """
    Drives both halves of the grounding/tool-calling split in
    `_on_send()` — see this module's docstring for the two real-usage
    regressions (hallucinated `open_module` call on an info question;
    grounding noise blocking a real `add_alarm` call) this classifier
    fixes. Pure keyword matching, same simplicity level as
    core/device_help_manager.py's retrieval scoring. `keywords` defaults
    to this module's own fallback list only for standalone testing —
    see `_ACTION_REQUEST_KEYWORDS`'s docstring for why production code
    always passes the registry's live keyword set instead.
    """
    lowered = f" {text.lower().strip()} "
    return any(keyword in lowered for keyword in keywords)


def build_chat_request(context, prompt: str) -> tuple[list[dict], list[dict]]:
    """
    Decides whether `prompt` looks like an action request and builds
    the (messages, tools) pair `_on_send()` hands to `ChatWorker` —
    pulled out as its own function (touches only `context`, no Qt) so
    `tests/live_model_check.py` (the golden-set live-model regression
    script, milestone 5.11) exercises this exact decision logic
    against the real Ollama server, not a hand-copied reimplementation
    that could quietly drift from what production actually does.
    """
    matched_actions = (
        context.assistant_actions.matching_actions(prompt)
        if context.assistant_actions is not None
        else []
    )
    is_action_request = bool(matched_actions)

    llm_prompt = prompt
    if not is_action_request and context.device_help is not None:
        llm_prompt = context.device_help.build_grounded_prompt(prompt)

    messages = [{"role": "user", "content": llm_prompt}]
    tools = []
    if is_action_request and context.assistant_actions is not None:
        # Domain-scoped, not the full registry — see
        # core/assistant_actions.py's docstring on why (tool-count
        # scaling has caused real live-model-only interference bugs;
        # matching_actions() attaches only the small always-on set plus
        # whichever domain(s) this prompt's own triggers matched).
        tools = context.assistant_actions.to_ollama_tools(matched_actions)

    return messages, tools


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
        self._worker: Optional[ChatWorker] = None
        self._tts_worker: Optional[TTSWorker] = None
        self._ptt_trigger: Optional[PushToTalkTrigger] = None
        self._recording = False

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
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

        # GPIO path is a no-op unless voice.push_to_talk_gpio_pin is
        # configured and gpiozero + real hardware are present — see
        # core/push_to_talk_trigger.py. Both paths call the exact same
        # handlers as the on-screen button.
        self._ptt_trigger = PushToTalkTrigger(self.context, parent=widget)
        self._ptt_trigger.pressed.connect(self._on_talk_pressed)
        self._ptt_trigger.released.connect(self._on_talk_released)

        self._refresh_availability()
        return widget

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def _refresh_availability(self) -> None:
        if self.context.llm is not None and self.context.llm.is_available():
            self._status_label.setText("")
        else:
            self._status_label.setText(_LLM_UNAVAILABLE_STATUS)

    # ------------------------------------------------------------------
    # Text sending
    # ------------------------------------------------------------------

    def _on_send(self) -> None:
        prompt = self._input.text().strip()
        if not prompt or self._worker is not None or self.context.llm is None:
            return

        self._log.appendPlainText(format_chat_line("You", prompt))
        self._input.clear()
        self._set_busy(True)

        messages, tools = build_chat_request(self.context, prompt)

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
            for tool_call in reply.tool_calls:
                confirmation = self.context.assistant_actions.execute(
                    self.context, tool_call.name, tool_call.arguments
                )
                self._log.appendPlainText(format_chat_line(self.display_name, confirmation))
                self._speak(confirmation)
            self._status_label.setText("")
            return

        self._log.appendPlainText(format_chat_line(self.display_name, reply.content))
        self._status_label.setText("")
        self._speak(reply.content)

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
