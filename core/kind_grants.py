"""
core.kind_grants
==================

"Approve From Now On" (DEC-0215, amended by Zac 2026-11-17: "MIA should offer an approve for now or Approve going
forward option"). On a card for a change MIA may make within a grant, the person can approve this once, or approve it
from now on: then each time MIA herself proposes that kind of change again, it's done at once, with an Undo, instead
of waiting on a card.

**Which kinds can have it** (`grantable`): only one whose tier is `act_within_grant` (core/grants.py) and whose effect
stays in his own records and can be undone exactly (core/action_effects.py). A kind that pays, buys, sends, publishes,
deletes outside undo or changes the system is `act_with_approval` or `never` and never qualifies, and nor do the
grant and plan kinds themselves (`grant.*`, `steps.*`), so a standing yes can't grant another or run a plan.

**Where it's kept:** the person's own setting `grants.kinds` (`core/person_settings.py`): for each kind, when he gave
it and when it was last used. It lapses after `LAPSE_DAYS` unused (REQ-AUT-009). It appears in his list of grants
(`core.grants.standing`, "kind:<kind>") and is taken back there like any other.

**What it changes:** `ActionCenter.propose` with `proposed_by="mia"` for a granted kind executes at once and says so;
the person's own presses are unchanged. It never covers anything a page, an email or a model asked for: it only
applies to a proposal MIA's own code made, through the same checks as any approval.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

KEY = "grants.kinds"
LAPSE_DAYS = 90
_NEVER_PREFIXES = ("grant.", "steps.", "history.", "undo.")


def grantable(kind: str) -> bool:
    """Pure logic over the manifests and the effects table. Whether a card for this kind may offer Approve From Now On."""
    from core import grants
    from core.action_effects import effect_of

    if not kind or kind.startswith(_NEVER_PREFIXES):
        return False
    return grants.tier_of(kind) == grants.WITHIN_GRANT and effect_of(kind) == ("records", "undoable")


def _all(context) -> dict:
    """The person's standing yeses, {kind: {given, last_used}}; an unreadable setting is none."""
    from core import person_settings

    try:
        found = person_settings.get(context, KEY, {}) or {}
        return {k: dict(v) for k, v in found.items() if isinstance(v, dict)} if isinstance(found, dict) else {}
    except Exception:  # noqa: BLE001 - no setting reads as no grants, never as one
        log.exception("Couldn't read the standing yeses")
        return {}


def _save(context, kinds: dict) -> None:
    """Writes them back, outside "undo that" (taking one back is its own action)."""
    from core import person_settings
    from core.undo_log import outside_undo

    with outside_undo():
        person_settings.put(context, KEY, kinds)


def live(context, now: Optional[datetime] = None) -> dict:
    """The standing yeses still in force: given, still grantable (a kind's tier may have changed), and used or given
    within LAPSE_DAYS."""
    now = now or datetime.now()
    cutoff = (now - timedelta(days=LAPSE_DAYS)).isoformat(timespec="seconds")
    return {k: v for k, v in _all(context).items()
            if grantable(k) and max(v.get("last_used", ""), v.get("given", "")) >= cutoff}


def has(context, kind: str, now: Optional[datetime] = None) -> bool:
    """Whether MIA may make this kind of change at once when she proposes it."""
    return kind in live(context, now)


def give(context, kind: str, now: Optional[datetime] = None) -> None:
    """Keeps his standing yes for a kind (Approve From Now On). ValueError for a kind that can't have one."""
    if not grantable(kind):
        raise ValueError("That kind of change always asks first.")
    stamp = (now or datetime.now()).isoformat(timespec="seconds")
    kinds = _all(context)
    kinds[kind] = {"given": kinds.get(kind, {}).get("given", stamp), "last_used": stamp}
    _save(context, kinds)


def used(context, kind: str, now: Optional[datetime] = None) -> None:
    """Notes that a standing yes was used, which keeps it from lapsing."""
    kinds = _all(context)
    if kind in kinds:
        kinds[kind]["last_used"] = (now or datetime.now()).isoformat(timespec="seconds")
        _save(context, kinds)


def take_back(context, kind: str) -> bool:
    """Ends a standing yes; whether there was one."""
    kinds = _all(context)
    if kinds.pop(kind, None) is None:
        return False
    _save(context, kinds)
    return True
