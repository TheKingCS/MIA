"""
core.generate_worker
=======================

Runs a single `AppContext.llm.generate()` call off the GUI thread —
same reasoning as `core/chat_worker.py`, a separate class only because
`generate()` and `chat_with_tools()` have different signatures/return
types (`Optional[str]` vs `Optional[ChatReply]`), not because the
threading concern itself differs.

2026-07-14 aesthetic pass part 5 (docs/ROADMAP.md): introduced for two
background, non-blocking, best-effort enhancements that must never hold
up the actual chat reply already shown to the user — memory extraction
(`core.assistant_chat.build_memory_extraction_prompt()`/
`parse_extracted_memories()`) and conversation auto-titling
(`build_title_generation_prompt()`/`clean_generated_title()`). Both
callers fire this *after* displaying the assistant's reply, not before,
and simply do nothing further if `result_ready` emits `None` (LLM
unavailable) — see those functions' own docstrings for why a failure
here is always non-fatal.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.llm_manager import LLMManager


class GenerateWorker(QThread):
    """Runs one `llm.generate(prompt)` call and emits the result (or None) when done."""

    result_ready = Signal(object)  # Optional[str]

    def __init__(self, llm: LLMManager, prompt: str) -> None:
        super().__init__()
        self._llm = llm
        self._prompt = prompt

    def run(self) -> None:
        reply: Optional[str] = self._llm.generate(self._prompt)
        self.result_ready.emit(reply)
