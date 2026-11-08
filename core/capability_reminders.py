"""
core.capability_reminders
===========================

Now and then, MIA reminds the person of what they're already capable of doing right now — "did you know you could go
do X?" (Zac, 2026-11-08). It isn't a new task and it isn't a value to live up to: it's a subtle redirect that meets
him where he is — the gentle reminder that the ability is already in his hands, which is often all it takes to get
moving.

Facts in code, the model only phrases — the same rule the rest of MIA follows. `on_hand(context)` gathers the
real abilities on his table (for the daily check in `core/application.py` and the My Directions screen): a learning path he's a step from advancing (`core/paths.py`), a project he
started and parked (`core/project_manager.py`), a plan whose materials are all on the shelf, a recipe he has
everything for, and the homestead's next doable step. This module wraps one in a warm, low-pressure frame. Empty in, empty
out — a reminder never fires without a true thing behind it — and the communication gate paces it, so it stays a
gentle redirect and never a push.
"""

from __future__ import annotations

from typing import Sequence, Tuple

from core.logger import get_logger

log = get_logger(__name__)

# Warm, low-pressure openings. {x} is a short verb phrase the caller has grounded in real state ("pick the guitar back
# up", "get back to your bookshelf project"); an optional reason follows as its own sentence. The tone is agency, not
# obligation — the point is to remind him the thing is already within reach, never to make him feel behind.
_FRAMES: Tuple[str, ...] = (
    "Did you know you could {x} right now?",
    "Quiet reminder — you've already got everything you need to {x}.",
    "No pressure, but right now you could {x}.",
    "Whenever you want an easy win today: you could {x}.",
    "You're more ready than it feels — you could {x} today.",
    "Something's within reach: you could {x}.",
)


def a_reminder(abilities: Sequence[Tuple[str, str]], roll: float) -> str:
    """Wrap one real, right-now ability in a warm, low-pressure frame — or "" when there's nothing concrete to point
    to.

    `abilities` are `(phrase, reason)` pairs the caller has already grounded in real state: `phrase` is a short verb
    phrase ("pick the guitar back up"), `reason` the honest why ("you're a clean run from the next stage") or "".
    `roll` (0–1) picks the ability and the frame deterministically, so the reminder is testable.
    """
    items = [(p.strip(), (r or "").strip()) for p, r in (abilities or []) if p and p.strip()]
    if not items:
        return ""
    phrase, reason = items[min(int(roll * len(items)), len(items) - 1)]
    frame = _FRAMES[min(int(((roll * 9) % 1.0) * len(_FRAMES)), len(_FRAMES) - 1)]
    line = frame.format(x=phrase)
    return f"{line} {reason}" if reason else line


def on_hand(context) -> list:
    """The real, right-now abilities a reminder can draw from: a started learning path with an open next step
    (core/paths.py), a project begun but not finished (core/project_manager.py), a built-in plan whose materials are
    all on the shelf (core/plan_library.py), a recipe with everything in the pantry (the kitchen), and the homestead's
    next doable step for someone already homesteading (core/development_engine.py). Each is a (verb phrase, honest
    reason) pair; every source is read defensively, so a missing one simply contributes nothing. Used by the daily
    check (core/application.py) and the My Directions screen (core/web_directions.py)."""
    out = []
    try:
        from core import paths

        book = paths.PathBook(context=context)
        for path_id in book.started():
            program = paths.program_of(context, path_id)
            if program is not None and paths.open_checks(book, program):
                stage = paths.stage_of(book, program)
                out.append((f"put some time into {program.name}",
                            f"You're on stage {stage.number}, {stage.name} — the next step is ready when you are."))
    except Exception:
        log.exception("Capability reminder: reading learning paths failed — skipped.")
    try:
        if getattr(context, "projects", None) is not None:
            done = {"done", "complete", "completed", "finished", "archived", "sold", "cancelled", "canceled"}
            for p in context.projects.all_projects():
                if (p.status or "").strip().lower() not in done:
                    out.append((f"get back to your {p.name} project", f"it's been sitting at “{p.status}.”"))
    except Exception:
        log.exception("Capability reminder: reading projects failed — skipped.")
    try:  # a built-in plan whose materials are all on the shelf (core/plan_library.py, DEC-0118)
        library = getattr(context, "plans", None)
        stock = getattr(context, "materials", None)
        if library is not None and stock is not None and stock.all_materials():
            from core.plan_library import shopping_list

            for plan in library.built_in():
                materials = plan.get("materials") or {}
                if materials.get("items") and not shopping_list(context, materials)["to_buy"]:
                    out.append((f"build the {plan['title'].lower()}", "Everything it needs is already on your shelf."))
    except Exception:
        log.exception("Capability reminder: reading the plans failed — skipped.")
    try:  # a recipe they have everything for (the kitchen's own match against the pantry)
        kitchen = getattr(context, "kitchen", None)
        if kitchen is not None:
            ready = [r for r, missing in kitchen.recipes_makeable_now() if not missing and not getattr(r, "locked", False)]
            if ready:
                out.append((f"make {ready[0].name}", "You've got everything for it in the pantry."))
    except Exception:
        log.exception("Capability reminder: reading the kitchen failed — skipped.")
    try:  # the homestead's next doable step (core/development_engine.py, DEC-0144), for someone already homesteading
        from core.development_engine import plan as homestead_plan

        p = homestead_plan(context)
        if p["have"] and p.get("next") and p["next"]["kind"] == "do":
            why = p["next"]["reason"].split(" — ", 1)[-1]
            out.append((f"start the {p['next']['name'].lower()}", f"It's the most useful next step on the homestead: {why}"))
    except Exception:
        log.exception("Capability reminder: reading the homestead plan failed — skipped.")
    return out
