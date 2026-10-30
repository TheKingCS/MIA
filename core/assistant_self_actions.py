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


# ---------------------------------------------------------------- DEC-0041: what MIA can do, and how she's built


def _action_what_can_you_do(context, arguments: dict) -> str:
    from core.capabilities import overview

    return overview(context)


def _action_about_yourself(context, arguments: dict) -> str:
    from core.capabilities import introduction

    return introduction(context)


def _action_can_you(context, arguments: dict) -> str:
    from core.capabilities import can_i

    return can_i(context, str(arguments.get("thing") or ""))


def _action_about_mia(context, arguments: dict) -> str:
    from core.self_docs import answer

    return answer(str(arguments.get("question") or ""))


def register_capability_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="what_can_you_do", domain="system",
        description="Everything MIA can do, app by app, from her own app list (never from memory).",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_what_can_you_do,
        trigger_phrases=("what can you do", "what are you able to do", "what features do you", "what can mia do",
                         "what apps do you have", "what all can you", "what do you do", "you capable of",
                         "mia capable of", "your capabilities", "mia's capabilities", "what are your features",
                         "what are you good at", "what all do you"),
        subjects=("you", "mia"),
    ))
    registry.register(AssistantAction(
        name="get_introduction", domain="system",
        description="Who MIA is, in her own words: where she runs, what she keeps track of, how she works.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_about_yourself,
        trigger_phrases=("about yourself", "who are you", "introduce yourself", "describe yourself", "who is mia",
                         "what is mia", "what are you exactly", "what exactly are you"),
        subjects=("you", "mia"),
    ))
    registry.register(AssistantAction(
        name="get_capability", domain="system",
        description=("Whether MIA can do something, and where: only when the user asks WHETHER MIA can (\"can you "
                     "track my chickens?\"), never when they ask MIA to do it. Answers from MIA's own app and tool "
                     "list, with what's missing."),
        parameters={"type": "object", "properties": {
            "thing": {"type": "string", "description": "What the user wants to know if MIA can do, in their words."}},
            "required": ["thing"]},
        handler=_action_can_you, prompt_arg="thing",
        # Not "can you do": that's inside "what can you do" (what_can_you_do's own).
        trigger_phrases=("are you able to", "is it possible to", "do you support", "does mia support", "can mia",
                         "do you have a feature", "is there a feature", "could you ever", "can you handle",
                         "can you track", "can you keep track", "can you manage", "can you help me with",
                         "can you help with", "do you track", "do you keep track"),
        subjects=("you", "mia", "feature"),
    ))
    registry.register(AssistantAction(
        name="get_mia_docs", domain="system",
        description=("How MIA herself is designed and why: her decisions, specs and docs, with the file each "
                     "answer comes from. For questions about MIA's own design, limits or decisions, not the user's "
                     "records."),
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "The user's question about MIA, in their words."}},
            "required": ["question"]},
        handler=_action_about_mia, prompt_arg="question",
        trigger_phrases=("what did we decide", "did we decide", "decision about", "decision on", "why can't you",
                         "why cant you", "why can't mia", "why doesn't mia", "why don't you", "how is mia built",
                         "how are you built", "how were you built", "mia's design", "your design", "how does mia",
                         "which decision"),
        subjects=("decide", "decision", "design", "mia", "you"),
    ))
