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
A standing yes is for a routine entry in his records, so these always ask as well (`always_asks`; Fable's review,
2026-11-18): a kind that covers many different things (`setting.set` is every setting); one that changes what MIA
herself may reach, watch, learn or say (her browser, connections, what she notes, her skills, her messages, the lab,
teams); and one that removes or forgets something.

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
# Always ask (see the module's opening). By the part before the dot, or the whole name for a tool's own kind.
_ASKS_AREAS = frozenset({
    "setting", "style", "lab", "connect", "connection", "activity", "comms", "communication", "browser", "browse",
    "firstboot", "world_intel", "world_watch", "world_source", "news", "teamwork", "team", "failures", "loop", "online",
    "capture", "creation", "gap", "insurance", "market", "listing", "trade", "portfolio", "path", "pathway", "plan",
})
_ASKS_NAMES = frozenset({
    "browser_back", "browser_click", "browser_close", "browser_type", "do_browser_task", "learn_browser_task",
    "take_over_tab", "use_everyday_browser", "private_sites", "set_activity_noting", "set_message_limit",
    "world_intelligence_switch", "watch_for", "watch_me_teach", "teach_skill_in_steps", "keep_taught_skill",
    "change_taught_skill", "run_taught_skill", "answer_taught_skill", "stop_taught_skill", "confirm_workspace_entry",
    "withdraw_workspace_entry", "scan_ports", "save_camera_picture", "selections_search_web", "ask_specialist",
    "add_trail_map_from_url", "make_textbook_course", "set_receipt_autofile", "set_schedule", "start_plan_project",
    "keep_plan", "do_with_this", "actions_for_this", "stop_medication", "record_property_sale", "record_sale",
})
_ASKS_WORDS = ("forget", "remove", "delete", "clear", "discard", "withdraw", "retire", "abandon", "rollback", "drop",
               "toss", "lost", "unlist", "dismiss", "reject", "decline", "sell", "switched")


def always_asks(kind: str) -> bool:
    """Pure logic. Whether this kind is one a standing yes never covers, whatever its tier (see the opening)."""
    area, _dot, rest = kind.partition(".")
    if kind.startswith(_NEVER_PREFIXES) or area in _ASKS_AREAS or kind in _ASKS_NAMES:
        return True
    words = (rest or kind).split("_")
    return any(word in _ASKS_WORDS for word in words)


def grantable(kind: str) -> bool:
    """Pure logic over the manifests and the effects table. Whether a card for this kind may offer Approve From Now On:
    its tier is within-grant, it only changes his records undoably, and it isn't one that always asks."""
    from core import grants
    from core.action_effects import effect_of

    if not kind or always_asks(kind):
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
    """Notes that a standing yes was used, which keeps it from lapsing. One no longer in force (taken back, lapsed,
    or for a kind that now always asks) is left alone, so a late note can't bring it back."""
    kinds = _all(context)
    if kind in kinds and kind in live(context, now):
        kinds[kind]["last_used"] = (now or datetime.now()).isoformat(timespec="seconds")
        _save(context, kinds)


def take_back(context, kind: str) -> bool:
    """Ends a standing yes; whether there was one."""
    kinds = _all(context)
    if kinds.pop(kind, None) is None:
        return False
    _save(context, kinds)
    return True
