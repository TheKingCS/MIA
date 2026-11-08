"""
core.starter_actions
======================

Starter sets on the web's Settings (DEC-0125: offered on the desktop's setup
and Settings, and by voice, but not on the web). `starters(context)` lists
each set with its parts for the page; `starter.add` adds a set, or just the
parts ticked, as one action whose Undo takes it all back
(core/starter_templates.apply with the action's own undo step). By voice:
list_starter_sets and add_starter_set.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def starters(context) -> list[dict]:
    """Every starter set for the Settings page: id, name, description, and its parts (id and label)."""
    from core.starter_templates import STARTERS

    return [{"id": s.starter_id, "name": s.name, "description": s.description,
             "parts": [{"id": p.part_id, "label": p.label} for p in s.parts]} for s in STARTERS.values()]


def _chosen(params) -> tuple:
    """(the starter set, the part ids asked for: all when none are named); ActionError for a set or part that isn't
    one."""
    from core.starter_templates import STARTERS

    starter = STARTERS.get(str(params.get("starter_id") or ""))
    if starter is None:
        raise ActionError("Pick a starter set from the list.")
    raw = params.get("parts")
    wanted = [p.strip() for p in (raw if isinstance(raw, list) else str(raw or "").split(",")) if str(p).strip()]
    known = {p.part_id for p in starter.parts}
    if any(p not in known for p in wanted):
        raise ActionError("That part isn't in this set.")
    return starter, wanted or sorted(known)


def _describe(context, params) -> str:
    """The approval sentence: the set, and the parts when only some are added."""
    starter, wanted = _chosen(params)
    labels = [p.label for p in starter.parts if p.part_id in wanted]
    every = len(labels) == len(starter.parts)
    return f"Add the {starter.name} starter set" + ("" if every else ": " + ", ".join(labels))


def _add(context, params) -> str:
    """Does starter.add (nothing already there by name is added twice) and says what happened."""
    from core.starter_templates import apply

    starter, wanted = _chosen(params)
    return f"{starter.name}: " + apply(context, starter.starter_id, wanted, own_undo=False).describe()


STARTER_ACTIONS = {"starter.add": ActionType("starter.add", "Add", {"starter_id": "the set",
                                                                    "parts": "which parts (comma separated; all if none)"},
                                             _describe, _add, child_ok=True)}
ACTION_TYPES.update(STARTER_ACTIONS)
