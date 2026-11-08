"""
core.assistant_answer_style_actions
=====================================

How MIA answers, by voice (DEC-0138, DEC-0125's both-ways rule; the screen is web/answers.html): "keep your answers
short", "use bullet points", "be more direct", "lead with the answer", "how do I like answers?", "forget how I like
answers", "stop asking which I prefer". The person's words are mapped to a style in code (`wanted`), never guessed by
the model, and each change runs the same style.* action as the screen (core/answer_compare.py), so it's undoable.
"""

from __future__ import annotations

from typing import Optional

from core.assistant_actions import AssistantAction, AssistantActionRegistry

# Words people use -> (dimension, value). Longest phrases are checked first, so "more detail" beats "more".
WORDS = (
    ("context first", ("lead", "context_first")), ("background first", ("lead", "context_first")),
    ("answer first", ("lead", "answer_first")), ("lead with the answer", ("lead", "answer_first")),
    ("get to the point", ("lead", "answer_first")), ("bottom line first", ("lead", "answer_first")),
    ("bullet", ("format", "bulleted")), ("list", ("format", "bulleted")),
    ("prose", ("format", "prose")), ("paragraph", ("format", "prose")), ("no bullets", ("format", "prose")),
    ("mixed", ("format", "mixed")),
    ("more detail", ("length", "detailed")), ("detailed", ("length", "detailed")), ("longer", ("length", "detailed")),
    ("thorough", ("length", "detailed")), ("shorter", ("length", "brief")), ("short", ("length", "brief")),
    ("brief", ("length", "brief")), ("concise", ("length", "brief")), ("normal length", ("length", "standard")),
    ("standard", ("length", "standard")),
    ("warmer", ("tone", "warm")), ("warm", ("tone", "warm")), ("friendly", ("tone", "warm")),
    ("direct", ("tone", "direct")), ("blunt", ("tone", "direct")), ("no fluff", ("tone", "direct")),
    ("neutral", ("tone", "neutral")), ("plain", ("tone", "neutral")),
)


def wanted(words: str) -> Optional[tuple]:
    """Pure logic. The (dimension, value) the person's words ask for, or None when nothing matches. "no bullets" is
    prose, not bulleted."""
    said = " ".join(str(words or "").lower().split())
    if "no bullet" in said or "without bullet" in said:
        return ("format", "prose")
    for phrase, choice in sorted(WORDS, key=lambda w: -len(w[0])):
        if phrase in said:
            return choice
    return None


def _run(context, kind: str, params: dict) -> str:
    """Runs a style action as the screen would (describe's checks, then execute); the problem as a line."""
    from core.actions import ACTION_TYPES, ActionError

    try:
        ACTION_TYPES[kind].describe(context, params)
        return ACTION_TYPES[kind].execute(context, params)
    except ActionError as problem:
        return str(problem)


def _action_set(context, arguments: dict) -> str:
    """Tool set_answer_style: one part of how MIA answers, from the person's words."""
    choice = wanted(arguments.get("how"))
    if choice is None:
        return ("I can change how long my answers are, bullets or prose, the tone, or whether the answer comes first. "
                "Which would you like?")
    return _run(context, "style.set", {"dimension": choice[0], "value": choice[1]})


def _action_get(context, arguments: dict) -> str:
    """Tool get_answer_style: what MIA has learned about how the person likes answers."""
    from core.answer_compare import LABELS, screen

    page = screen(context)
    if not page.get("available"):
        return "I haven't got anywhere to keep how you like answers on this MIA."
    learned = [f"{d['name'].lower()}: {LABELS[d['preferred']].lower()}" for d in page["dimensions"] if d["picks"]]
    two = " I offer an answer two ways now and then." if page["compare"] else " I've stopped offering two ways."
    if not learned:
        return "I haven't learned how you like answers yet. Tell me (\"keep it short\"), or pick when I offer two ways." + two
    return "So far: " + "; ".join(learned) + "." + two


def _action_reset(context, arguments: dict) -> str:
    """Tool reset_answer_style: forget every pick."""
    return _run(context, "style.reset", {})


def _action_two_ways(context, arguments: dict) -> str:
    """Tool answer_two_ways: offers of an answer two ways on or off."""
    on = str(arguments.get("on", "true")).lower() not in ("false", "no", "0", "off", "stop")
    return _run(context, "style.compare", {"on": on})


def register_answer_style_actions(registry: AssistantActionRegistry) -> None:
    """Registers how-MIA-answers tools: set, get, reset, and two ways on or off."""
    registry.register(AssistantAction(
        name="set_answer_style", domain="answer_style",
        description="Change how MIA answers from now on, in the user's words: shorter or more detailed, bullet points "
                    "or prose, warmer or more direct or neutral, the answer first or the context first.",
        parameters={"type": "object", "properties": {"how": {"type": "string", "description": "the user's words."}},
                    "required": ["how"]},
        handler=_action_set,
        trigger_phrases=("answers short", "answers shorter", "keep it short", "be more direct", "use bullet", "bullet points",
                         "more detail in your answers", "answer first", "lead with the answer", "less wordy",
                         "talk to me more", "answer in prose", "be warmer"),
    ))
    registry.register(AssistantAction(
        name="get_answer_style", domain="answer_style",
        description="Say what MIA has learned about how the user likes to be answered.",
        parameters={"type": "object", "properties": {}}, handler=_action_get,
        trigger_phrases=("how do i like answers", "how do i like my answers", "what have you learned about how i",
                         "my answer style"),
    ))
    registry.register(AssistantAction(
        name="reset_answer_style", domain="answer_style",
        description="Forget what MIA learned about how the user likes answers (undo brings it back).",
        parameters={"type": "object", "properties": {}}, handler=_action_reset,
        trigger_phrases=("forget how i like answers", "reset my answer style", "reset how you answer"),
    ))
    registry.register(AssistantAction(
        name="answer_two_ways", domain="answer_style",
        description="Turn on or off MIA now and then offering an answer two ways and asking which the user prefers.",
        parameters={"type": "object", "properties": {"on": {"type": "boolean", "description": "true to offer, false to stop."}},
                    "required": ["on"]},
        handler=_action_two_ways,
        trigger_phrases=("stop asking which i prefer", "which one i prefer", "ask me which i prefer", "two ways"),
    ))
