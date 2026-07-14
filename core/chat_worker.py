"""
core.chat_worker
===================

Runs a single `AppContext.llm.chat_with_tools()` call off the GUI
thread — docs/ROADMAP.md milestones 5.2/5.5. A blocking HTTP call to
Ollama (core/llm_manager.py) on the GUI thread would freeze the whole
app for the duration of every reply. This is the first module to need
the scoped worker-thread pattern CLAUDE.md's "no async/threading
anywhere in core" note explicitly carves out an exception for — same
precedent as `core/push_to_talk_trigger.py`'s `QObject`-based signal
delivery already living in core/ despite the general rule, since this
class only runs a blocking call and signals the result back, with no
actual widget/rendering code of its own.

Moved here from `modules/assistant/module.py` (2026-07-14 aesthetic
pass part 4, docs/ROADMAP.md) once the Assistant's chat needed to be
usable from `gui/character_panel.py`'s sidebar as well as the full
`modules/assistant/module.py` screen — `gui/` may import `core/`
directly but must never import `modules/` (CLAUDE.md's one-directional
layering), so anything both need had to live in core/, not modules/.

`ChatWorker` only ever runs the network round-trip — it never executes
a tool call itself. Tool calls (`core/assistant_actions.py`) can touch
Qt (the `open_module` action) or other app state, so they're executed
back on the GUI thread by the caller's own reply-handling slot, which
Qt's queued-connection signal delivery already guarantees runs on the
thread that owns this worker (the GUI thread) — same reasoning as
core/push_to_talk_trigger.py's docstring on why cross-thread Qt work
needs a signal, not a direct call.

Chat is inherently one-reply-in-flight-at-a-time, so a fresh
`ChatWorker` per prompt (rather than a persistent worker + queue) is
enough; each caller disables its own input while a worker is running
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
