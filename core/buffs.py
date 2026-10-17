"""
core.buffs
============

Buffs (DEC-0028, the game layer's fifth piece): good effects you've
earned by what you really did. **Never debuffs** (DEC-0014): nothing here
is ever taken away as a penalty; a buff simply runs out, and earning it
again brings it back.

Each buff says what earned it, how long it lasts, and the attribute it
lifts by +1 while it's active (core/character_stats.py adds it). Nothing
is stored: buffs are read fresh from the stores every time.

| Buff | Earned by | Lasts | Lifts |
|---|---|---|---|
| Well Fed | logging what you ate today | today | Vitality |
| Momentum | 3 workouts in 7 days | 7 days from the 3rd | Strength |
| On A Roll | 3 missions finished in 7 days | 7 days from the 3rd | Wisdom |
| Prepared | every tracked asset Good or better | while it holds | Craft |
| Good Company | catching up with someone | 7 days | Charisma |
| Clear Mind | a journal entry | 2 days | Wisdom |
| Trailblazer | finishing a trip or expedition | 14 days | Stamina |
| Maker's Pride | finishing a workshop job | 7 days | Craft |
| Debt Slayer | a payment on a debt (never for a child) | 7 days | Charisma |

Well Rested (sleep) waits for a watch (docs/GAME_LAYER.md, idea 12).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)


def _day(text) -> Optional[date]:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def nth_latest(days: list[Optional[date]], n: int, today: date, window: int) -> Optional[date]:
    """Pure logic. The n-th most recent of `days` inside the last `window`
    days (today included), or None when there aren't n of them: the day a
    "3 in 7 days" buff was earned, so it lasts `window` days from then."""
    recent = sorted((d for d in days if d is not None and today - timedelta(days=window - 1) <= d <= today),
                    reverse=True)
    return recent[n - 1] if len(recent) >= n else None


def latest(days: list[Optional[date]], today: date, window: int) -> Optional[date]:
    return nth_latest(days, 1, today, window)


def _buff(key, name, icon, stat, why, earned: Optional[date], days: Optional[int], today: date) -> Optional[dict]:
    """A buff earned on `earned` lasting `days` (None: while it holds)."""
    if earned is None:
        return None
    ends = earned + timedelta(days=days - 1) if days else None
    if ends is not None and ends < today:
        return None
    left = (ends - today).days if ends is not None else None
    return {"key": key, "name": name, "icon": icon, "stat": stat, "bonus": 1, "why": why,
            "earned": earned.isoformat(), "ends": ends.isoformat() if ends else "",
            "lasts": "while it holds" if ends is None else "ends today" if left == 0 else
            "ends tomorrow" if left == 1 else f"{left} more days"}


def _well_fed(context, today):
    fitness = getattr(context, "fitness", None)
    kitchen = getattr(context, "kitchen", None)
    ate = bool(fitness and fitness.food_on(today.isoformat())) or \
        bool(kitchen and any(e.date == today.isoformat() for e in kitchen.all_meal_log_entries()))
    return _buff("well_fed", "Well Fed", "🍲", "vitality", "You logged what you ate today.",
                 today if ate else None, 1, today)


def _momentum(context, today):
    workout = getattr(context, "workout", None)
    earned = nth_latest([_day(s.date) for s in workout.all_sessions()], 3, today, 7) if workout else None
    return _buff("momentum", "Momentum", "🔥", "strength", "Three workouts in a week.", earned, 7, today)


def _on_a_roll(context, today):
    missions = getattr(context, "missions", None)
    done = [_day(m.updated_at) for m in missions.all_missions() if m.status == "completed"] if missions else []
    return _buff("on_a_roll", "On A Roll", "⭐", "wisdom", "Three missions finished in a week.",
                 nth_latest(done, 3, today, 7), 7, today)


def _prepared(context, today):
    from core.web_equipment import _task_row, condition

    maintenance = getattr(context, "maintenance", None)
    if maintenance is None:
        return None
    bars = []
    for asset in maintenance.all_assets():
        bar = condition([_task_row(context, t, asset, today) for t in maintenance.tasks_for_asset(asset.asset_id)])
        if bar is not None:
            bars.append(bar["percent"])
    ready = bool(bars) and min(bars) >= 50
    return _buff("prepared", "Prepared", "🛡", "craft",
                 f"All {len(bars)} pieces of your gear are in good condition." if len(bars) > 1 else
                 "Your gear is in good condition.", today if ready else None, None, today)


def _good_company(context, today):
    people = getattr(context, "relationships", None)
    seen = [(_day(getattr(p, "last_contact", "")), p.name) for p in people.all_people()] if people else []
    earned = latest([d for d, _n in seen], today, 7)
    who = [n for d, n in seen if d == earned]
    return _buff("good_company", "Good Company", "🤝", "charisma",
                 f"You caught up with {who[0]}." if who else "", earned, 7, today)


def _clear_mind(context, today):
    journal = getattr(context, "journal", None)
    earned = latest([_day(e.created_at) for e in journal.all_entries()], today, 2) if journal else None
    return _buff("clear_mind", "Clear Mind", "📘", "wisdom", "You wrote in your journal.", earned, 2, today)


def _trailblazer(context, today):
    days = []
    trips = getattr(context, "trips", None)
    if trips is not None:
        days += [_day(t.end_date or t.start_date) for t in trips.all_trips() if t.status == "completed"]
    expeditions = getattr(context, "expeditions", None)
    if expeditions is not None:
        days += [_day(e.end_date) for e in expeditions.all_expeditions()]
    return _buff("trailblazer", "Trailblazer", "🧭", "stamina", "You finished a trip.", latest(days, today, 14), 14, today)


def _makers_pride(context, today):
    jobs = getattr(context, "jobs", None)
    done = [_day(j.updated_at) for j in jobs.all_jobs() if j.status == "Complete"] if jobs else []
    return _buff("makers_pride", "Maker's Pride", "🛠", "craft", "You finished a workshop job.",
                 latest(done, today, 7), 7, today)


def _debt_slayer(context, today):
    from core.child_accounts import is_child

    budget = getattr(context, "budget", None)
    if budget is None or is_child(context):
        return None
    paid = [(_day(d.last_payment_date), d.name) for d in budget.all_debts()]
    earned = latest([d for d, _n in paid], today, 7)
    name = next((n for d, n in paid if d == earned), "")
    return _buff("debt_slayer", "Debt Slayer", "⚔", "charisma", f"You landed a hit on {name}." if name else "",
                 earned, 7, today)


SOURCES: tuple[Callable, ...] = (_well_fed, _momentum, _on_a_roll, _prepared, _good_company, _clear_mind,
                                 _trailblazer, _makers_pride, _debt_slayer)


def buffs(context, today: Optional[date] = None) -> list[dict]:
    """Every buff the person has right now, newest first."""
    today = today or date.today()
    out = []
    for source in SOURCES:
        try:
            b = source(context, today)
        except Exception:
            log.debug("Buffs: %s failed", source.__name__, exc_info=True)
            continue
        if b is not None:
            out.append(b)
    return sorted(out, key=lambda b: b["earned"], reverse=True)


def bonuses(active: list[dict]) -> dict[str, list[dict]]:
    """Per attribute: the buffs lifting it."""
    out: dict[str, list[dict]] = {}
    for b in active:
        out.setdefault(b["stat"], []).append(b)
    return out
