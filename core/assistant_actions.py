"""
core.assistant_actions
=========================

The Assistant's tool-use/action-execution registry — docs/ROADMAP.md
milestone 5.5. Lets the LLM actually DO things in M.I.A. (open a
module, add an alarm, a note, an inventory item), not just answer
questions, via Ollama's structured tool-calling API
(core/llm_manager.py's `chat_with_tools()`).

This is a **different** capability from the Self-Modification / Dev
Mode staged plan in docs/ROADMAP.md, which is specifically about the
assistant editing M.I.A.'s own source code and is gated behind a
cautious multi-stage rollout (read & explain -> propose-not-apply ->
sandboxed testing -> scoped autonomy). Actions registered here are
just normal, everyday app operations any user could already do by
hand through the UI — there is no file-write/code-execution capability
anywhere in this module.

Same pluggable-registry shape as core/calculator_engine.py: register()
here, core/application.py wires the built-in actions in
(`_register_assistant_actions()`, mirroring `_register_calculators()`),
so this file doesn't need to know about ModuleManager or any specific
manager directly.

A handler receives the AppContext and the LLM's parsed arguments dict,
and returns a short human-readable confirmation string. There is
deliberately no second LLM round-trip to phrase that confirmation —
keeps this fast, fully deterministic, and unit-testable without a real
model. A handler that needs to touch the GUI (e.g. `open_module`) must
publish an event rather than reach into Qt directly, since handlers
can be invoked from contexts where that matters — see
modules/assistant/module.py's docstring for the threading reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from core.logger import get_logger

if TYPE_CHECKING:
    from core.app_context import AppContext

log = get_logger(__name__)


@dataclass
class AssistantAction:
    name: str
    description: str
    parameters: dict  # JSON schema "parameters" object (Ollama/OpenAI tool-call format)
    handler: Callable[[AppContext, dict], str]

    def to_ollama_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class AssistantActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, AssistantAction] = {}

    def register(self, action: AssistantAction) -> None:
        self._actions[action.name] = action
        log.info("Registered assistant action: %s", action.name)

    def to_ollama_tools(self) -> list[dict]:
        return [action.to_ollama_tool() for action in self._actions.values()]

    def execute(self, context: AppContext, name: str, arguments: dict) -> str:
        """
        Run the named action's handler, or a clear message if the name
        is unknown or the handler raises — a malformed/hallucinated
        tool call from the LLM must never crash the app.
        """
        action = self._actions.get(name)
        if action is None:
            log.warning("Assistant tried to call unknown action '%s'", name)
            return f"(I tried to do something I don't know how to do: '{name}'.)"
        try:
            return action.handler(context, arguments)
        except Exception:
            log.exception("Assistant action '%s' failed", name)
            return f"(Sorry, '{name}' didn't work.)"
