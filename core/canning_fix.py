"""
core.canning_fix
==================

Fixing a batch of jars that was put up with the wrong count (the achievements review, 2026-11-24): "I put up 7
jars of tomatoes, not 70". The jars he has ever canned are counted from `canned` life events
(core/canning_shelf.py, core/life_milestones.jars_canned), because an eaten jar leaves the pantry; so a correction
is one more `canned` event carrying the difference (negative when it was fewer), never a rewrite of the history, and
the batch's pantry quantity moves by the same difference (never below 0). An achievement already unlocked stays
unlocked (unlocks are for good); the count from here on is right.

`recorded` and `correct` do the work; the action `jars.correct` (Kitchen's pantry, Fix Jar Count on a home-canned
batch) and the tool `fix_jar_count` (by the food's name, the newest batch of it) are how he asks.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction


def _batch(context, item_id: str):
    """The home-canned pantry batch with this id, or ActionError."""
    from core.canning_shelf import MARK

    kitchen = getattr(context, "kitchen", None)
    item = kitchen.get_pantry_item(str(item_id or "")) if kitchen is not None else None
    if item is None or MARK.lower() not in str(item.notes or "").lower():
        raise ActionError("That isn't a batch from the canning shelf.")
    return item


def recorded(context, item_id: str) -> float:
    """How many jars the history says this batch was put up with (its canned events, corrections included, an undone
    one left out)."""
    from core import life_events

    events = life_events.events_for(context, types=("canned", "undone"), ref=None)
    undone = life_events.reversed_ids(events)
    return sum(float(e.payload.get("jars") or 0) for e in events
               if e.type == "canned" and e.event_id not in undone and f"pantry:{item_id}" in e.refs)


def _jars(params) -> float:
    """The right count from the params (a number or a spoken one), or ActionError."""
    from core.canning_shelf import count_of

    jars = count_of(params.get("jars"))
    if not jars or jars < 0:
        raise ActionError("How many jars was it really?")
    return float(jars)


def _describe(context, params) -> str:
    """What jars.correct says: the batch, what was recorded and what it becomes."""
    item, jars = _batch(context, params.get("item_id")), _jars(params)
    was = recorded(context, item.item_id)
    if jars == was:
        raise ActionError(f"{item.name} is already {jars:g} jars.")
    return f"Make {item.name} {jars:g} jars put up (it was recorded as {was:g})"


def correct(context, params) -> str:
    """Does jars.correct: a canned event with the difference, the pantry quantity moved by it."""
    from core import life_events

    item, jars = _batch(context, params.get("item_id")), _jars(params)
    difference = jars - recorded(context, item.item_id)
    if difference == 0:
        return f"{item.name} is already {jars:g} jars."
    context.kitchen.update_pantry_item(item.item_id, quantity=max(0.0, float(item.quantity or 0) + difference))
    life_events.record(context.kitchen, "canned", f"Corrected {item.name} to {jars:g} jars put up",
                       refs=[f"pantry:{item.item_id}"], payload={"jars": difference, "correction": True,
                                                              "food": item.name})
    return f"{item.name} is now {jars:g} jars put up."


FIX_ACTIONS = {k.kind: k for k in (
    ActionType("jars.correct", "Fix Jar Count", {"item_id": "the batch", "jars": "how many jars it really was"},
               _describe, correct),
)}
ACTION_TYPES.update(FIX_ACTIONS)


def _fix(context, arguments: dict) -> str:
    """Tool fix_jar_count: the newest home-canned batch of the food he names, set to the right count."""
    from core.canning_shelf import MARK, food_of

    food = food_of(str(arguments.get("food", "") or "")).lower()
    kitchen = getattr(context, "kitchen", None)
    batches = [p for p in (kitchen.all_pantry_items() if kitchen is not None else [])
               if MARK.lower() in str(p.notes or "").lower() and food and food in p.name.lower()]
    if not batches:
        return f"There's no batch of {food or 'that'} on the canning shelf."
    newest = max(batches, key=lambda p: str(p.notes or ""))  # "put up YYYY-MM-DD" in the notes sorts by day
    params = {"item_id": newest.item_id, "jars": arguments.get("jars")}
    try:
        ACTION_TYPES["jars.correct"].describe(context, params)
        return ACTION_TYPES["jars.correct"].execute(context, params)
    except ActionError as problem:
        return str(problem)


def register_canning_fix_actions(registry) -> None:
    """Registers fix_jar_count.
    Reached by a correction's words (", not", "I meant"), so "7 jars of tomatoes, not 70" offers it beside
    put_up_jars (the live check, 2026-11-24)."""
    registry.register(AssistantAction(
        name="fix_jar_count", domain="kitchen",
        description="Fix how many jars a batch on the canning shelf was put up with, when it was said wrong ('I put "
                    "up 7 jars of tomatoes, not 70'); his canning count follows. A new batch is put_up_jars'.",
        parameters={"type": "object", "properties": {
            "food": {"type": "string", "description": "the food, e.g. 'tomatoes'"},
            "jars": {"type": "number", "description": "how many jars it really was"}},
            "required": ["food", "jars"]},
        handler=_fix, trigger_phrases=("jars not", "wrong number of jars", "fix the jar count", "fix my jar count",
                                       "jars, not", "not 70", ", not ", "i meant"),
    ))
