"""
core.grant_actions
====================

Taking a grant back, on the action contract (DEC-0156; core/grants.py): proposed in plain words, approved by the
person, run, undoable.

- `grant.take_back`: ends something MIA may do on her own. A learned skill goes back to practising with the person;
  a published workflow is put away (kept, with its records). Named by `grant_id` (from the Apps page's list) or by
  `grant` in words (its name).

There is deliberately no action that gives a grant: one is earned (a skill run cleanly with the person watching) or
approved where it's made (publishing a workflow), so nothing MIA reads or says can grant her anything.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _grant(context, params):
    """The grant the params name (grant_id, or `grant` by its name); ActionError when none or several."""
    from core import grants

    found = grants.find(context, str(params.get("grant_id") or params.get("grant") or ""))
    if found is None:
        raise ActionError("Which one? Say its name as the Apps page lists it under what I may do on my own.")
    return found


def _describe(context, params) -> str:
    """The approval sentence for `grant.take_back`."""
    g = _grant(context, params)
    after = "it goes back to practising with you" if g.kind == "skill" else "it's put away and won't run"
    return f"Take back “{g.name}”: {after}"


def _execute(context, params) -> str:
    """Does `grant.take_back`."""
    from core import grants

    try:
        return grants.take_back(context, _grant(context, params).grant_id)
    except ValueError as problem:
        raise ActionError(str(problem)) from None


def _register() -> None:
    """Adds `grant.take_back` to ACTION_TYPES. Runs once, when this module is imported."""
    kind = ActionType("grant.take_back", "Take Back", {"grant_id": "the grant", "grant": "or its name"},
                      _describe, _execute)
    ACTION_TYPES[kind.kind] = kind


_register()
