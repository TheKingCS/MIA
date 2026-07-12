"""
modules.assistant.llm_worker
==============================

Runs a single `AppContext.llm.generate()` call off the GUI thread —
docs/ROADMAP.md milestone 5.2. A blocking HTTP call to Ollama
(core/llm_manager.py, milestone 5.1) on the GUI thread would freeze the
whole app for the duration of every reply. This is the first module to
need the scoped worker-thread pattern CLAUDE.md's "no async/threading
anywhere in core" note explicitly carves out an exception for — a
`QThread` local to modules/assistant, not a change to
core/event_bus.py or any other core service.

Chat is inherently one-reply-in-flight-at-a-time, so a fresh `LLMWorker`
per prompt (rather than a persistent worker + queue) is enough; the
module disables its input while a worker is running instead of
managing a queue.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.llm_manager import LLMManager


class LLMWorker(QThread):
    """Runs one `llm.generate(prompt)` call and emits the result (or None) when done."""

    result_ready = Signal(object)  # Optional[str]

    def __init__(self, llm: LLMManager, prompt: str) -> None:
        super().__init__()
        self._llm = llm
        self._prompt = prompt

    def run(self) -> None:
        reply: Optional[str] = self._llm.generate(self._prompt)
        self.result_ready.emit(reply)
