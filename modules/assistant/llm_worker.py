"""
modules.assistant.llm_worker
==============================

Runs a single `AppContext.llm.chat_with_tools()` call off the GUI
thread — docs/ROADMAP.md milestones 5.2/5.5. A blocking HTTP call to
Ollama (core/llm_manager.py) on the GUI thread would freeze the whole
app for the duration of every reply. This is the first module to need
the scoped worker-thread pattern CLAUDE.md's "no async/threading
anywhere in core" note explicitly carves out an exception for — a
`QThread` local to modules/assistant, not a change to
core/event_bus.py or any other core service.

`ChatWorker` only ever runs the network round-trip — it never executes
a tool call itself. Tool calls (`core/assistant_actions.py`) can touch
Qt (the `open_module` action) or other app state, so they're executed
back on the GUI thread by modules/assistant/module.py's `_on_reply()`
slot, which Qt's queued-connection signal delivery already guarantees
runs on the thread that owns this worker (the GUI thread) — same
reasoning as core/push_to_talk_trigger.py's docstring on why
cross-thread Qt work needs a signal, not a direct call.

Chat is inherently one-reply-in-flight-at-a-time, so a fresh
`ChatWorker` per prompt (rather than a persistent worker + queue) is
enough; the module disables its input while a worker is running
instead of managing a queue.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.llm_manager import ChatReply, LLMManager


class ChatWorker(QThread):
    """Runs one `llm.chat_with_tools(messages, tools)` call and emits the result (or None) when done."""

    result_ready = Signal(object)  # Optional[ChatReply]

    def __init__(self, llm: LLMManager, messages: list[dict], tools: list[dict]) -> None:
        super().__init__()
        self._llm = llm
        self._messages = messages
        self._tools = tools

    def run(self) -> None:
        reply: Optional[ChatReply] = self._llm.chat_with_tools(self._messages, self._tools)
        self.result_ready.emit(reply)
