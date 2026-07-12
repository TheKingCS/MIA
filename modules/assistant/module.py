"""
modules.assistant.module
=========================

Assistant Chat UI — docs/ROADMAP.md milestone 5.2. Upgrades the v0.1
placeholder to a real chat screen (scrollback + input box) wired to
`AppContext.llm` (core/llm_manager.py, milestone 5.1).

A blocking call to `context.llm.generate()` runs on a scoped
`modules.assistant.llm_worker.LLMWorker` (a `QThread`) rather than the
GUI thread — see that module's docstring for why. Only one reply can
be in flight at a time; the input/send button are disabled for the
duration and re-enabled in `_on_worker_finished`, which always runs
(success or "unavailable"), so the UI can never get stuck disabled.

`context.llm.generate()` returning `None` means the backend logged a
warning and couldn't be reached (see core/llm_manager.py) — surfaced
here as a status line, never a crash or a stuck "Thinking…" state.
"""

from __future__ import annotations

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

from modules.assistant.llm_worker import LLMWorker
from modules.module_base import ModuleBase

_UNAVAILABLE_STATUS = "Assistant unavailable — is Ollama running?"


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
        self._status_label: Optional[QLabel] = None
        self._worker: Optional[LLMWorker] = None

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

        layout.addLayout(input_row)

        self._refresh_availability()
        return widget

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def _refresh_availability(self) -> None:
        if self.context.llm is not None and self.context.llm.is_available():
            self._status_label.setText("")
        else:
            self._status_label.setText(_UNAVAILABLE_STATUS)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _on_send(self) -> None:
        prompt = self._input.text().strip()
        if not prompt or self._worker is not None or self.context.llm is None:
            return

        self._log.appendPlainText(format_chat_line("You", prompt))
        self._input.clear()
        self._set_busy(True)

        self._worker = LLMWorker(self.context.llm, prompt)
        self._worker.result_ready.connect(self._on_reply)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_reply(self, reply: Optional[str]) -> None:
        if reply is None:
            self._status_label.setText(_UNAVAILABLE_STATUS)
        else:
            self._log.appendPlainText(format_chat_line(self.display_name, reply))
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
