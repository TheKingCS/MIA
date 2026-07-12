"""
modules.assistant.module
=========================

Assistant Chat UI — docs/ROADMAP.md milestones 5.2 (text chat), 5.3
(voice), and 5.4 (device-help grounding). A chat screen (scrollback +
input box) wired to `AppContext.llm` (core/llm_manager.py), plus a
push-to-talk "Hold to Talk" button wired to `AppContext.voice`
(core/voice_manager.py) for speech in, speech out.

Every prompt is run through `AppContext.device_help.build_grounded_prompt()`
(core/device_help_manager.py) before it reaches the LLM — the actual text
sent to `LLMWorker` is the retrieval-grounded version (M.I.A.'s own docs +
module metadata as context), not the user's raw words, though the chat
log still displays what the user actually typed/said. This is
deliberate scope, not an accident: docs/HARDWARE.md's hardware note
says the realistic on-device model size (1-7B params) should be aimed
at "device help, structured Q&A" rather than open-ended conversation,
and grounding is milestone 5.4's explicit job.

Two blocking operations each get their own scoped `QThread` rather than
running on the GUI thread:
  - `context.llm.generate()` runs on `modules.assistant.llm_worker.LLMWorker`.
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
stuck disabled. `context.llm.generate()` / `context.voice.*` returning
`None`/`False` means the backend logged a warning and couldn't be
reached — surfaced here as a status line, never a crash.

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

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.push_to_talk_trigger import PushToTalkTrigger
from modules.assistant.llm_worker import LLMWorker
from modules.assistant.tts_worker import TTSWorker
from modules.module_base import ModuleBase

_LLM_UNAVAILABLE_STATUS = "Assistant unavailable — is Ollama running?"
_MIC_UNAVAILABLE_STATUS = "Microphone unavailable."
_STT_UNAVAILABLE_STATUS = "Speech-to-text unavailable."


def format_chat_line(speaker: str, text: str) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_assistant_module.py)."""
    return f"{speaker}: {text}"


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
        self._worker: Optional[LLMWorker] = None
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

        llm_prompt = prompt
        if self.context.device_help is not None:
            llm_prompt = self.context.device_help.build_grounded_prompt(prompt)

        self._worker = LLMWorker(self.context.llm, llm_prompt)
        self._worker.result_ready.connect(self._on_reply)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_reply(self, reply: Optional[str]) -> None:
        if reply is None:
            self._status_label.setText(_LLM_UNAVAILABLE_STATUS)
        else:
            self._log.appendPlainText(format_chat_line(self.display_name, reply))
            self._status_label.setText("")
            self._speak(reply)

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
