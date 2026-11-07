"""
core.cooking_actions
======================

Cook mode's changes (core/cooking_session.py, DEC-0113) as action kinds on
the contract in core/actions.py, so the Kitchen screen, the tablet on the
counter and, later, voice and the glasses all move the one session the same
way: start cooking a recipe, next step, back, go to a step, start or stop a
named timer, "I made this" (which is the existing `meal.cook`: the meal is
logged and the pantry used up, then the session closes), and stop without
logging. Each person's own session. Not offered to child accounts (DEC-0119: MIA is
for Zac alone; nothing new is built for children).
"""

from __future__ import annotations

from datetime import datetime

from core import cooking_session as cs
from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _store(context):
    """The person's cook-mode store, or ActionError when it isn't here."""
    return _need(context, "cooking")


def _live(context):
    """The recipe being cooked, or ActionError saying how to start."""
    s = _store(context).live()
    if s is None:
        raise ActionError("Nothing's cooking. Open a recipe and press Start Cooking.")
    return s


def _ingredients(context, recipe_id: str) -> list:
    """The recipe's ingredients, for what each step uses ([] when the recipe is gone)."""
    kitchen = getattr(context, "kitchen", None)
    recipe = kitchen.get_recipe(recipe_id) if kitchen is not None else None
    return list(recipe.ingredients) if recipe is not None else []


def _run(context, change) -> str:
    """Apply one move to the session, save, and say where they are."""
    store, now = _store(context), datetime.now()
    s = _live(context)
    try:
        change(s, now)
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    store.save()
    return cs.say(s, now)


def _recipe(context, params):
    """The recipe named by recipe_id, not locked, or ActionError."""
    kitchen = _need(context, "kitchen")
    recipe = kitchen.get_recipe(str(params.get("recipe_id") or ""))
    if recipe is None:
        raise ActionError("That recipe isn't in the book.")
    if recipe.locked:
        raise ActionError(f"{recipe.name} is still locked.")
    return recipe


def _describe_start(context, params) -> str:
    """The sentence the approval card shows for `cooking.start` (Propose); raises ActionError when it can't be done:
    something else is cooking, or the recipe has no steps."""
    from core.web_screens import recipe_steps

    recipe = _recipe(context, params)
    if _store(context).live() is not None:
        raise ActionError(f"{_store(context).live().title} is already cooking.")
    steps = recipe_steps(recipe.instructions)
    if not steps:
        raise ActionError(f"{recipe.name} has no steps written down yet. Add them to the recipe first.")
    return f"Start cooking {recipe.name}: {len(steps)} step{'s' if len(steps) != 1 else ''}"


def _start(context, params) -> str:
    """Does `cooking.start` once approved: the recipe's steps become the session, and it says the first step."""
    from core.web_screens import recipe_steps

    recipe = _recipe(context, params)
    try:
        s = _store(context).begin(recipe.recipe_id, recipe.name, recipe_steps(recipe.instructions))
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    return cs.say(s, datetime.now())


def _number(params) -> int:
    """The step number from the params, or ActionError."""
    try:
        return int(str(params.get("step") or "").strip())
    except ValueError:
        raise ActionError("Which step? Give its number.") from None


def _minutes(params) -> int:
    """A timer's length in seconds from `minutes` (decimals allowed), or ActionError."""
    try:
        minutes = float(str(params.get("minutes") or "").strip())
    except ValueError:
        raise ActionError("How many minutes?") from None
    return int(round(minutes * 60))


def _describe_timer(context, params) -> str:
    """The sentence for `cooking.timer`: its name and length."""
    _live(context)
    seconds = _minutes(params)
    name = str(params.get("name") or "Timer").strip() or "Timer"
    return f"Start a {name.lower()} timer for {seconds // 60} min" + (f" {seconds % 60} s" if seconds % 60 else "")


def _timer(context, params) -> str:
    """Does `cooking.timer`: starts (or restarts) the named timer, which keeps running across steps."""
    seconds = _minutes(params)
    name = str(params.get("name") or "Timer")
    _run(context, lambda s, now: cs.add_timer(s, name, seconds, now))
    return f"{name.strip() or 'Timer'} timer: {seconds // 60} minutes."


def _timer_cancel(context, params) -> str:
    """Does `cooking.timer_cancel`: stops the named timer."""
    name = str(params.get("name") or "")
    _run(context, lambda s, now: cs.cancel_timer(s, name))
    return f"Stopped the {name.lower()} timer."


def _describe_made(context, params) -> str:
    """The sentence for `cooking.made`: the same as "I made this" for the recipe being cooked."""
    from core.kitchen_actions import KITCHEN_ACTIONS

    s = _live(context)
    return KITCHEN_ACTIONS["meal.cook"].describe(context, {**params, "recipe_id": s.recipe_id})


def _made(context, params) -> str:
    """Does `cooking.made`: runs "I made this" (`meal.cook`: the meal logged, the pantry used up unless told not to),
    then closes the session."""
    from core.kitchen_actions import KITCHEN_ACTIONS

    s = _live(context)
    said = KITCHEN_ACTIONS["meal.cook"].execute(context, {**params, "recipe_id": s.recipe_id})
    _store(context).close()
    return said


def _stop(context, params) -> str:
    """Does `cooking.stop`: closes the session without logging a meal."""
    s = _live(context)
    _store(context).close()
    return f"Stopped cooking {s.title}. Nothing was logged."


_KINDS = [
    ActionType("cooking.start", "Start Cooking", {"recipe_id": "the recipe"}, _describe_start, _start, False),
    ActionType("cooking.next", "Next Step", {}, lambda c, p: "Next step", lambda c, p: _run(c, lambda s, now: cs.next_step(s)), False),
    ActionType("cooking.back", "Back", {}, lambda c, p: "Back a step", lambda c, p: _run(c, lambda s, now: cs.back(s)), False),
    ActionType("cooking.go_to", "Go To Step", {"step": "its number"}, lambda c, p: f"Go to step {_number(p)}",
               lambda c, p: _run(c, lambda s, now: cs.go_to(s, _number(p))), False),
    ActionType("cooking.timer", "Start Timer", {"name": "what it's for", "minutes": "how long"}, _describe_timer, _timer, False),
    ActionType("cooking.timer_cancel", "Stop Timer", {"name": "the timer"}, lambda c, p: f"Stop the {p.get('name', '')} timer",
               _timer_cancel, False),
    ActionType("cooking.made", "I Made This", {"pantry": "Yes or No: take it out of the pantry", "batches": "optional",
                                               "notes": "optional"}, _describe_made, _made, False),
    ActionType("cooking.stop", "Stop Cooking", {}, lambda c, p: "Stop cooking without logging it", _stop, False),
]
COOKING_ACTIONS = {k.kind: k for k in _KINDS}
ACTION_TYPES.update(COOKING_ACTIONS)


def screen(context, now=None) -> dict | None:
    """The session for the Kitchen screen and cook mode (core.web_screens.kitchen_page): the view with what each step
    uses, or None when nothing's cooking."""
    store = getattr(context, "cooking", None)
    s = store.live() if store is not None else None
    if s is None:
        return None
    return cs.view(s, now or datetime.now(), _ingredients(context, s.recipe_id))
