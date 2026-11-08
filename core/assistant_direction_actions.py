"""
core.assistant_direction_actions
==================================

My Directions by voice (DEC-0141/0143, DEC-0125's both-ways rule; the screen is web/directions.html): "what are my
directions?", "add a direction: grow my own food, cook from scratch", "pause the whimsy direction", "bring it back",
"let go of that direction", and "give me something to make today" (today's seed, core/whimsy.py, from the person's
own directions and what's on the workshop shelf). Each change runs the same action as the screen
(core/web_directions.py), so it's undoable the same way. MIA only stores what the person said; she never invents a
direction for them.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry

_S = {"type": "string"}


def _run(context, kind: str, params: dict) -> str:
    """Runs a direction action as the screen would (its describe checks, then its execute); the problem as a line."""
    from core.actions import ACTION_TYPES, ActionError

    action = ACTION_TYPES[kind]
    try:
        action.describe(context, params)
        return action.execute(context, params)
    except ActionError as problem:
        return str(problem)


def _which(context, arguments: dict):
    """(direction, None) for the one named, or (None, a question)."""
    from core.web_directions import find

    found = find(context, str(arguments.get("direction") or ""))
    if found is None:
        return None, "Which direction? Say its name (\"what are my directions?\" lists them)."
    return found, None


def _action_list(context, arguments: dict) -> str:
    """Tool list_directions: the person's directions in their own words, paused ones said as paused."""
    book = getattr(context, "direction", None)
    if book is None or not book.directions:
        return "You haven't set any directions yet. Say \"add a direction\" and tell me the value in your own words."
    lines = [f"{d.title}{'' if d.active else ' (paused)'}: {d.statement}" for d in book.directions]
    return "Your directions: " + " ".join(lines)


def _action_add(context, arguments: dict) -> str:
    """Tool add_direction: a new standing direction from the person's own words."""
    statement = str(arguments.get("statement") or "").strip()
    title = str(arguments.get("title") or "").strip() or " ".join(statement.split()[:4]).rstrip(".,").title()
    return _run(context, "direction.add", {"title": title, "statement": statement,
                                           "encourage": str(arguments.get("encourage") or ""),
                                           "nudges": arguments.get("nudges") or []})


def _action_pause(context, arguments: dict) -> str:
    """Tool pause_direction: hold a direction out of MIA's view for a while."""
    found, question = _which(context, arguments)
    return question or _run(context, "direction.pause", {"direction_id": found.direction_id})


def _action_resume(context, arguments: dict) -> str:
    """Tool resume_direction: a paused direction back in force."""
    found, question = _which(context, arguments)
    return question or _run(context, "direction.resume", {"direction_id": found.direction_id})


def _action_remove(context, arguments: dict) -> str:
    """Tool remove_direction: let a direction go (undo brings it back)."""
    found, question = _which(context, arguments)
    return question or _run(context, "direction.remove", {"direction_id": found.direction_id})


def _action_seed(context, arguments: dict) -> str:
    """Tool todays_seed: today's little thing to make or do toward the person's directions, and one thing already
    within reach; honest when there's nothing to go on."""
    from core.web_directions import right_now, todays_seed

    seed, now = todays_seed(context), right_now(context)
    if not seed and not now:
        return ("I don't have anything grounded to suggest yet. Set a direction (\"add a direction\") and I'll find "
                "little things toward it.")
    return " ".join(x for x in (seed, now) if x)


def register_direction_actions(registry: AssistantActionRegistry) -> None:
    """Registers My Directions' tools: list, add, pause, resume, remove, and today's seed."""
    registry.register(AssistantAction(
        name="list_directions", domain="directions",
        description="List the user's standing directions (the values they asked MIA to hold and encourage).",
        parameters={"type": "object", "properties": {}}, handler=_action_list,
        trigger_phrases=("my directions", "what are my directions", "what values", "what am i steering"),
    ))
    registry.register(AssistantAction(
        name="add_direction", domain="directions",
        description="Set a new standing direction from the user's own words: a value they're steering their life by "
                    "that MIA should hold in mind and gently encourage. Only what they said; never invent one.",
        parameters={"type": "object", "properties": {
            "statement": {"type": "string", "description": "the value in the user's own words."},
            "title": {"type": "string", "description": "optional: a short name for it."},
            "encourage": {"type": "string", "description": "optional: how MIA should encourage it."},
            "nudges": {"type": "array", "items": _S, "description": "optional: little nudges MIA may raise."},
        }, "required": ["statement"]},
        handler=_action_add,
        trigger_phrases=("add a direction", "new direction", "set a direction", "i want to steer", "hold me to"),
    ))
    for name, handler, what, phrases in (
            ("pause_direction", _action_pause, "Pause one of the user's directions (MIA stops leaning that way).",
             ("pause the direction", "pause my direction", "stop encouraging")),
            ("resume_direction", _action_resume, "Resume a paused direction.",
             ("resume the direction", "resume my direction", "start encouraging")),
            ("remove_direction", _action_remove, "Let go of one of the user's directions for good (undo brings it back).",
             ("let go of the direction", "remove the direction", "delete the direction", "drop the direction"))):
        registry.register(AssistantAction(
            name=name, domain="directions", description=what,
            parameters={"type": "object", "properties": {"direction": {"type": "string",
                                                                       "description": "its name or words from it."}},
                        "required": ["direction"]},
            handler=handler, trigger_phrases=phrases))
    registry.register(AssistantAction(
        name="todays_seed", domain="directions",
        description="Today's little thing to make or do toward the user's directions (grounded in the season and what's "
                    "on their workshop shelf), and one thing they could already go and do right now.",
        parameters={"type": "object", "properties": {}}, handler=_action_seed,
        trigger_phrases=("something to make today", "what should i make", "inspire me", "today's seed",
                         "what could i do right now", "give me something to do"),
    ))
