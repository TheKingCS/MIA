"""
core.assistant_self_actions
=============================

MIA about herself (2026-10-21, the intelligence spec's first slice):
"What AI model are you using?" answered from the runtime
(core/model_registry.py), never from the model's guess about itself.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _action_get_model_info(context, arguments: dict) -> str:
    from core.model_registry import assistant_info, describe

    return describe(assistant_info(context))


def register_self_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="get_model_info", domain="system",
        description=("Which AI model MIA is answering with right now, asked of the runtime: its name, family, size, "
                     "quantization, context, where it runs (this phone, the home computer) and the fallback. Use it "
                     "for any question about MIA's own model or AI; never answer that from memory."),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_model_info,
        # About MIA herself only: "what model of mower do I have?" isn't this.
        trigger_phrases=("model are you", "model do you", "model you use", "model you're using", "your model",
                         "your ai", "what ai are you", "which ai are you", "ai model", "what llm", "which llm",
                         "are you running on", "what are you running", "what brain", "model is mia", "model does mia",
                         "mia's model", "model mia"),
        subjects=("model", "ai", "llm", "brain"),
    ))
