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
`reward_unlocked` life event as each one unlocks). One unlocked before that history existed is listed undated.

**The cards** (`unseen`, `mark_seen`): the unlocks since he last saw one, oldest first, three at most with how many
more, for the web frame to show as a card each (web/cards.js) and the action `achievement.seen` to mark them seen
(the person's own `achievements.seen_at`, core/person_settings.py). The first time, only the last day's are shown,
never his whole history at once.

**The page and the voice twin** (`page`, `say`; /api/achievements, the tool `my_achievements`): the log, the chains'
progress toward each next tier, and the structures built and still to build.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log_ = get_logger(__name__)

SEEN_KEY = "achievements.seen_at"
CARDS_AT_ONCE = 3


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


def log(context) -> list[dict]:
    """What the signed-in person has unlocked, newest first: each card with `when` (its date-time from the history,
    or "" for one unlocked before that history was kept, listed last)."""
    from core import life_events

    pid = _person(context)
    known, unlocked = catalog(), _unlocked(context, pid)
    try:
        events = life_events.events_for(context, types=("reward_unlocked",))
    except Exception:  # noqa: BLE001 - a history that can't be read leaves the log undated
        log_.exception("Couldn't read the unlock history")
        events = []
    rows, dated = [], set()
    for event in events:  # newest first
        rid = str(event.payload.get("reward_id", ""))
        if rid in unlocked and rid in known and rid not in dated:
            dated.add(rid)
            rows.append({**known[rid], "when": event.at})
    rows += [{**known[rid], "when": ""} for rid in reversed(unlocked) if rid in known and rid not in dated]
    return rows


def unseen(context, now: Optional[datetime] = None) -> dict:
    """The unlocks he hasn't seen a card for, oldest first: {cards (three at most), more (how many beyond those),
    upto (the newest one's time, for `mark_seen`)}. Before he has ever seen one, only the last day's count."""
    from core import person_settings

    now = now or datetime.now()
    seen = person_settings.get(context, SEEN_KEY) or (now - timedelta(days=1)).isoformat(timespec="seconds")
    fresh = [row for row in log(context) if row["when"] and row["when"] > str(seen)]
    fresh.reverse()  # oldest first: they're shown in the order they were earned
    return {"cards": fresh[:CARDS_AT_ONCE], "more": max(0, len(fresh) - CARDS_AT_ONCE),
            "upto": fresh[-1]["when"] if fresh else ""}


def mark_seen(context, upto: str = "") -> str:
    """Marks every unlock up to `upto` (a time from `unseen`, or now) as seen; returns what it did."""
    from core import person_settings

    when = str(upto or "").strip()[:19] or datetime.now().isoformat(timespec="seconds")
    try:
        datetime.fromisoformat(when)
    except ValueError:
        raise ValueError("That isn't a time.") from None
    current = person_settings.get(context, SEEN_KEY) or ""
    if when > current:
        person_settings.put(context, SEEN_KEY, when)
    return "Seen."


def page(context) -> dict:
    """The Achievements page: {available, earned (the log), counts {earned, total (hidden ones only once found)},
    chains (core.web_progress.rewards_block's, with each next tier's progress), structures [{name, icon,
    description, earned, rarity...}]}."""
    from core.life_milestones import STRUCTURES
    from core.web_progress import rewards_block

    pid = _person(context)
    rewards = getattr(context, "rewards", None)
    if rewards is None or not pid:
        return {"available": False, "earned": [], "counts": {"earned": 0, "total": 0}, "chains": [], "structures": []}
    earned = log(context)
    unlocked = set(_unlocked(context, pid))
    known = catalog()
    shown = [c for c in known.values() if c["kind"] != "hidden" or c["id"] in unlocked]
    block = rewards_block(context, pid)
    structures = [{"id": s.reward_id, "name": s.name, "icon": s.icon, "description": s.description,
                   "earned": s.reward_id in unlocked, **_rarity(s.rarity_index)} for s in STRUCTURES]
    return {"available": True, "earned": earned, "counts": {"earned": len(earned), "total": len(shown)},
            "chains": block.get("chains", []), "structures": structures}


def _number(value: float) -> str:
    """Pure logic. 612.0 -> "612", 1234.5 -> "1,234.5"."""
    return f"{value:,.1f}".rstrip("0").rstrip(".")


def say(context) -> str:
    """The voice twin of the page: how many he's earned, the latest three with their dates, and the next tier he's
    closest to, with his number against it."""
    found = page(context)
    if not found["available"]:
        return "Achievements need a signed-in profile."
    counts = found["counts"]
    parts = [f"You've unlocked {counts['earned']} of {counts['total']} achievements."]
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
    still = [s["name"] + " (" + s["description"].rstrip(".").lower() + ")" for s in found["structures"]
             if not s["earned"]]
    if still and len(still) < len(found["structures"]):
        parts.append(f"{len(still)} structure milestones still to build.")
    return " ".join(parts)
