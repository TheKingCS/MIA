"""
core.app_intro
================

What MIA says when she introduces an app (slice 5 of
docs/GLASSES_FIRST_BOOT_PLAN.md), in two halves:

1. **What the app is**: written here. STATIC.
2. **What's already here for you**: put together in code from the
   person's own data, and only when the data exists. Nothing else is
   claimed: no line for a store that's empty.

`app_intro(context, module_id)` -> {"what": ..., "yours": [lines],
"status": "DERIVED"}. One builder per app, for the apps with a tour.
"""

from __future__ import annotations

from core.logger import get_logger

log = get_logger(__name__)

WHAT = {
    "missions": "Your goals, broken into steps, each worth XP.",
    "budget": "Spending, bills and savings goals.",
    "workout": "Your training plan, what's on today and how it's going.",
    "kitchen": "Your recipes, your pantry, and what's for dinner.",
}


def _count(n: int, one: str) -> str:
    """"1 mission", "3 missions": a count with its word, plural when it isn't one."""
    return f"{n} {one}{'' if n == 1 else 's'}"


def _active_missions(context) -> list:
    """The person's active missions (none without a missions store)."""
    missions = getattr(context, "missions", None)
    return [m for m in missions.all_missions() if m.status == "active"] if missions is not None else []


def _missions(context) -> list[str]:
    """What's already here for the Missions intro: how many missions are running and the first one's name; nothing when there's none."""
    active = _active_missions(context)
    return [f"{_count(len(active), 'mission')} running, starting with {active[0].name}."] if active else []


def _budget(context) -> list[str]:
    """What's already here for the Budget intro: how many bills there are, and a Save for... mission from earlier; nothing when there's none."""
    lines = []
    budget = getattr(context, "budget", None)
    bills = budget.all_bills() if budget is not None else []
    if bills:
        lines.append(f"{_count(len(bills), 'bill')} already here.")
    saving = [m.name for m in _active_missions(context) if m.name.startswith("Save for ")]
    if saving:
        lines.append(f"{saving[0]} is on your missions, from earlier.")
    return lines


def _workout(context) -> list[str]:
    """What's already here for the Workout intro: the training plan's days by name; nothing when there's none."""
    fitness = getattr(context, "fitness", None)
    days = (fitness.plan.get("training") or {}).get("rotation") or [] if fitness is not None else []
    return [f"Your plan is here: {', '.join(d['name'] for d in days)}."] if days else []


def _kitchen(context) -> list[str]:
    """What's already here for the Kitchen intro: how many recipes are in the book, naming one; nothing when there's none."""
    kitchen = getattr(context, "kitchen", None)
    recipes = kitchen.all_recipes() if kitchen is not None else []
    return [f"{_count(len(recipes), 'recipe')} in your book, like {recipes[0].name}."] if recipes else []


YOURS = {"missions": _missions, "budget": _budget, "workout": _workout, "kitchen": _kitchen}


def app_intro(context, module_id: str) -> dict:
    """An app's introduction: what it is (written here) and what's already here for this person (from their data);
    a builder that fails is logged and says nothing. Status DERIVED.
    """
    try:
        yours = YOURS[module_id](context) if module_id in YOURS else []
    except Exception:
        log.exception("The intro for %s couldn't read its data.", module_id)
        yours = []
    return {"what": WHAT.get(module_id, ""), "yours": yours, "status": "DERIVED"}
