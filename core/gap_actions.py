"""
core.gap_actions
==================

Capability gaps (core/capability_gaps.py, build plan step 9) through the
action contract (core/actions.py): `gap.build` (the person says yes to a
new ability being built: a development task naming the gap, never their
words) and `gap.dismiss` (not wanted: never offered again).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _gap(context, params) -> dict:
    """The capability gap the params name, or ActionError."""
    from core import capability_gaps

    gap = capability_gaps.get(context, str(params.get("gap_id", "")))
    if gap is None:
        raise ActionError("There's no such request on my list.")
    return gap


def _describe_build(context, params) -> str:
    """The sentence the approval card shows for `gap.build` (Propose); raises ActionError when it can't be done. Only a gap that needs code, and isn't asked for yet."""
    gap = _gap(context, params)
    if gap["need"] != "code":
        raise ActionError(f"That one doesn't need building: {gap['what']}.")
    if gap.get("task"):
        raise ActionError(f"It's already asked for ({gap['task']}).")
    return "Ask for it to be built"


def _build(context, params) -> str:
    """Does `gap.build` once approved, and says what happened. It opens a development task for the gap; only on the PC with MIA's development."""
    from core import capability_gaps, loops

    if not loops._has_repo():
        raise ActionError("Only the PC with MIA's development can take this; ask from there.")
    task = capability_gaps.open_task(context, _gap(context, params)["id"])
    return f"Asked for. It's on the development list ({task}); I'll tell you when it's in."


def _describe_dismiss(context, params) -> str:
    """The sentence the approval card shows for `gap.dismiss` (Propose); raises ActionError when it can't be done."""
    _gap(context, params)
    return "Stop offering it"


def _dismiss(context, params) -> str:
    """Does `gap.dismiss` once approved, and says what happened. The gap is marked declined and never offered again."""
    from core import capability_gaps

    capability_gaps.mark(context, _gap(context, params)["id"], "declined")
    return "Okay, I won't bring that one up again."


GAP_ACTIONS = {a.kind: a for a in (
    ActionType("gap.build", "Ask for it", {"gap_id": "the gap"}, _describe_build, _build),
    ActionType("gap.dismiss", "Not needed", {"gap_id": "the gap"}, _describe_dismiss, _dismiss),
)}
ACTION_TYPES.update(GAP_ACTIONS)
