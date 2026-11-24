"""
core.achievement_cards
========================

The achievements log and the card that congratulates him (the game layer, Zac 2026-11-24: "keep an achievements log
and reward me with unlocking those, have cards that pop up congratulating me and showing me the achievement").

**One catalog** (`catalog`): every achievement MIA knows, from core/rewards_manager.py (each challenge chain's tiers,
the hidden achievements) and core/life_milestones.py (structures built), each as a card: its name, what it took, its
icon, its rarity (core/rarity.py) and its kind. A hidden achievement is in the catalog only for naming one already
unlocked; `page` never lists a locked one.

**The log** (`log`): what he has unlocked, newest first, dated from his history (core/progress_history.py records a
`reward_unlocked` life event as each one unlocks), and every reward a mission earned him beyond XP (a structure, a
song, a recipe...: core/mission_trophies.py's `trophy_earned` events). One unlocked before that history existed is
listed undated.

**The cards** (`unseen`, `mark_seen`): the ones he hasn't seen a card for, oldest first, three at most with how many
more, for the web frame to show as a card each (web/shell.js). Each is marked seen by its id as its card is closed
(POST /api/achievements/seen), kept in his own `achievements.seen` (core/person_settings.py): the ids seen, and
`since`, before which nothing is offered, so the first time only the last day's show, never his whole history.
Marking seen is bookkeeping, not a change of his: it's written outside undo (core/undo_log.outside_undo), so it never
stands in the way of undoing the harvest that earned the card. The log is read again only when a history file has
changed (`_cached`), since the frame asks on every live change.

**The page and the voice twin** (`page`, `say`; /api/achievements, the tool `my_achievements`): the log, the chains'
progress toward each next tier, and the structures built and still to build.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log_ = get_logger(__name__)

SEEN_KEY = "achievements.seen"
CARDS_AT_ONCE = 3
SEEN_KEPT = 400  # ids remembered as seen; past this the oldest go and `since` moves up to cover them
_cache: dict = {}  # person id -> (the history files' state, their log)


def _rarity(index: int) -> dict:
    """Pure logic. A rarity's index, name and colour token for a card."""
    from core.rarity import rarity_name_for_index

    return {"rarity": index, "rarity_name": rarity_name_for_index(index)}


def catalog() -> dict[str, dict]:
    """Pure logic. Every achievement by its reward id, as a card: {id, kind (tier, hidden or structure), headline,
    name, description, icon, rarity, rarity_name, chain (a tier's chain id, else "")}."""
    from core.life_milestones import STRUCTURES
    from core.rewards_manager import CHALLENGE_CHAINS, HIDDEN_ACHIEVEMENTS

    cards: dict[str, dict] = {}
    for chain in CHALLENGE_CHAINS:
        for tier in chain.tiers:
            cards[tier.reward_id] = {"id": tier.reward_id, "kind": "tier", "headline": "Achievement Unlocked",
                                     "name": tier.name, "description": tier.description, "icon": tier.icon,
                                     "chain": chain.chain_id, **_rarity(tier.rarity_index)}
    for hidden in HIDDEN_ACHIEVEMENTS:
        cards[hidden.achievement_id] = {"id": hidden.achievement_id, "kind": "hidden",
                                        "headline": "Hidden Achievement Found", "name": hidden.name,
                                        "description": hidden.description, "icon": hidden.icon, "chain": "",
                                        **_rarity(hidden.rarity_index)}
    for s in STRUCTURES:
        cards[s.reward_id] = {"id": s.reward_id, "kind": "structure", "headline": "Milestone Reached", "name": s.name,
                              "description": s.description, "icon": s.icon, "chain": "", **_rarity(s.rarity_index)}
    return cards


def _person(context) -> Optional[str]:
    """The signed-in person's id, or None."""
    from core.person_settings import person_id

    return person_id(context)


def _unlocked(context, pid: Optional[str]) -> list[str]:
    """The reward ids this person has unlocked (from their profile)."""
    rewards = getattr(context, "rewards", None)
    return rewards.unlocked_reward_ids(pid) if rewards is not None and pid else []


def _trophy_card(event) -> dict:
    """Pure logic. A mission's trophy_earned event as a card: its kind's headline, icon and rarity, the mission it came
    from."""
    from core.mission_trophies import KINDS

    kind = KINDS.get(str(event.payload.get("kind", "")))
    rarity = kind.rarity_index if kind is not None else 1
    return {"id": f"trophy:{event.event_id}", "kind": "trophy", "headline": kind.headline if kind else "Reward Earned",
            "name": str(event.payload.get("name", "")), "icon": kind.icon if kind else "🏆", "chain": "",
            "description": f"From the mission {event.payload.get('mission', '')}.".replace(" .", "."),
            "when": event.at, **_rarity(rarity)}


def _files(context, pid) -> tuple:
    """The state (path, size, modified) of the history files this person's log reads: the cache's key."""
    from core.life_events import FILE_NAME

    folders = [getattr(getattr(context, n, None), "data_dir", None) for n in ("life_events", "personal_life_events")]
    state = []
    for folder in folders:
        try:
            info = os.stat(os.path.join(str(folder), FILE_NAME)) if folder is not None else None
        except OSError:
            info = None
        state.append((str(folder), info.st_size if info else -1, info.st_mtime_ns if info else -1))
    return (pid, tuple(_unlocked(context, pid)), tuple(state))


def _cached(context, pid) -> list[dict]:
    """The log, read again only when a history file or the person's unlocks have changed."""
    key = _files(context, pid)
    held = _cache.get(pid)
    if held is not None and held[0] == key:
        return [dict(row) for row in held[1]]
    rows = _read_log(context, pid)
    _cache[pid] = (key, rows)
    return [dict(row) for row in rows]


def log(context) -> list[dict]:
    """What the signed-in person has unlocked and the trophies missions earned them, newest first: each card with
    `when` (its date-time from the history, or "" for an unlock from before that history was kept, listed last)."""
    pid = _person(context)
    return _cached(context, pid) if pid else []


def _read_log(context, pid) -> list[dict]:
    """The log, read from the history (see `log`)."""
    from core import life_events

    known, unlocked = catalog(), _unlocked(context, pid)
    try:
        events = life_events.events_for(context, types=("reward_unlocked", "trophy_earned"))
    except Exception:  # noqa: BLE001 - a history that can't be read leaves the log undated
        log_.exception("Couldn't read the unlock history")
        events = []
    rows, dated = [], set()
    for event in events:  # newest first
        if event.type == "trophy_earned":
            if event.profile_id in (None, pid):
                rows.append(_trophy_card(event))
            continue
        rid = str(event.payload.get("reward_id", ""))
        if rid in unlocked and rid in known and rid not in dated:
            dated.add(rid)
            rows.append({**known[rid], "when": event.at})
    rows += [{**known[rid], "when": ""} for rid in reversed(unlocked) if rid in known and rid not in dated]
    return rows


def _seen(context, now: datetime) -> dict:
    """The person's seen record: {since (nothing before it is offered; a day ago until first set), ids}."""
    from core import person_settings

    held = person_settings.get(context, SEEN_KEY)
    held = held if isinstance(held, dict) else {}
    since = str(held.get("since") or (now - timedelta(days=1)).isoformat(timespec="seconds"))
    return {"since": since, "ids": [str(i) for i in held.get("ids") or []]}


def unseen(context, now: Optional[datetime] = None) -> dict:
    """The ones he hasn't seen a card for, oldest first: {cards (three at most, each with its id), more (how many
    beyond those)}. Nothing from before `since` (the first time: the last day only)."""
    seen = _seen(context, now or datetime.now())
    ids = set(seen["ids"])
    fresh = [row for row in log(context) if row["when"] and row["when"] >= seen["since"] and row["id"] not in ids]
    fresh.reverse()  # oldest first: they're shown in the order they were earned
    return {"cards": fresh[:CARDS_AT_ONCE], "more": max(0, len(fresh) - CARDS_AT_ONCE)}


def mark_seen(context, ids, now: Optional[datetime] = None) -> str:
    """Marks these cards seen (by id), outside undo: bookkeeping, never a change "undo that" takes back. Past
    `SEEN_KEPT` ids, the oldest are let go and `since` moves up to the earliest card still remembered, so none of
    them is offered again. ValueError for no ids."""
    from core import person_settings, undo_log

    ids = [str(i).strip()[:60] for i in (ids if isinstance(ids, (list, tuple)) else [ids]) if str(i or "").strip()]
    if not ids:
        raise ValueError("Which cards?")
    now = now or datetime.now()
    seen = _seen(context, now)
    kept = seen["ids"] + [i for i in ids if i not in seen["ids"]]
    since = seen["since"]
    if len(kept) > SEEN_KEPT:
        dropped, kept = kept[:-SEEN_KEPT], kept[-SEEN_KEPT:]
        whens = {row["id"]: row["when"] for row in log(context)}
        latest = max((whens.get(i, "") for i in dropped), default="")
        if latest and latest >= since:
            since = (datetime.fromisoformat(latest) + timedelta(seconds=1)).isoformat(timespec="seconds")
    with undo_log.outside_undo():
        person_settings.put(context, SEEN_KEY, {"since": since, "ids": kept})
    return "Seen."


def page(context) -> dict:
    """The Achievements page: {available, earned (the log, trophies included), counts {earned (achievements),
    total (hidden ones only once found), trophies (rewards missions earned)},
    chains (core.web_progress.rewards_block's, with each next tier's progress), structures [{name, icon,
    description, earned, rarity...}]}."""
    from core.life_milestones import STRUCTURES
    from core.web_progress import rewards_block

    pid = _person(context)
    rewards = getattr(context, "rewards", None)
    if rewards is None or not pid:
        return {"available": False, "earned": [], "counts": {"earned": 0, "total": 0, "trophies": 0}, "chains": [],
                "structures": []}
    earned = log(context)
    trophies = sum(1 for row in earned if row["kind"] == "trophy")
    unlocked = set(_unlocked(context, pid))
    known = catalog()
    shown = [c for c in known.values() if c["kind"] != "hidden" or c["id"] in unlocked]
    block = rewards_block(context, pid)
    structures = [{"id": s.reward_id, "name": s.name, "icon": s.icon, "description": s.description,
                   "earned": s.reward_id in unlocked, **_rarity(s.rarity_index)} for s in STRUCTURES]
    return {"available": True, "earned": earned,
            "counts": {"earned": len(earned) - trophies, "total": len(shown), "trophies": trophies},
            "chains": block.get("chains", []), "structures": structures}


def _number(value: float) -> str:
    """Pure logic. 612.0 -> "612", 1234.5 -> "1,234.5"."""
    return f"{value:,.1f}".rstrip("0").rstrip(".")


def say(context) -> str:
    """The voice twin of the page: how many he's earned, the latest three with their dates, and the next tier he's
    closest to, with his number against it.
    Rewards that missions earned are counted beside the achievements."""
    found = page(context)
    if not found["available"]:
        return "Achievements need a signed-in profile."
    counts = found["counts"]
    parts = [f"You've unlocked {counts['earned']} of {counts['total']} achievements"
             + (f", and missions have earned you {counts['trophies']} rewards." if counts["trophies"] else ".")]
    latest = found["earned"][:3]
    if latest:
        parts.append("Latest: " + "; ".join(f"{c['name']} ({c['description'].rstrip('.')}"
                                             + (f", {c['when'][:10]})" if c["when"] else ")") for c in latest) + ".")
    close = [c for c in found["chains"] if c.get("next")]
    if close:
        best = max(close, key=lambda c: c["next"]["percent"])
        unit = f" {best['unit']}" if best.get("unit") else ""
        parts.append(f"Closest next: {best['next']['name']}, {_number(best['value'])}{unit} of "
                     f"{_number(best['next']['threshold'])}{unit} ({best['stat'].lower()}).")
    still = [s for s in found["structures"] if not s["earned"]]
    if still and len(still) < len(found["structures"]):
        parts.append(f"{len(still)} structure milestones still to build.")
    return " ".join(parts)
