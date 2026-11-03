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
    return f"{n} {one}{'' if n == 1 else 's'}"


def _active_missions(context) -> list:
    missions = getattr(context, "missions", None)
    return [m for m in missions.all_missions() if m.status == "active"] if missions is not None else []


def _missions(context) -> list[str]:
    active = _active_missions(context)
    return [f"{_count(len(active), 'mission')} running, starting with {active[0].name}."] if active else []


def _budget(context) -> list[str]:
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
    fitness = getattr(context, "fitness", None)
    days = (fitness.plan.get("training") or {}).get("rotation") or [] if fitness is not None else []
    return [f"Your plan is here: {', '.join(d['name'] for d in days)}."] if days else []


def _kitchen(context) -> list[str]:
    kitchen = getattr(context, "kitchen", None)
    recipes = kitchen.all_recipes() if kitchen is not None else []
    return [f"{_count(len(recipes), 'recipe')} in your book, like {recipes[0].name}."] if recipes else []


YOURS = {"missions": _missions, "budget": _budget, "workout": _workout, "kitchen": _kitchen}


def app_intro(context, module_id: str) -> dict:
    try:
        yours = YOURS[module_id](context) if module_id in YOURS else []
    except Exception:
        log.exception("The intro for %s couldn't read its data.", module_id)
        yours = []
    return {"what": WHAT.get(module_id, ""), "yours": yours, "status": "DERIVED"}
