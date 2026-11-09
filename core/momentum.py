"""
core.momentum
===============

Natural Momentum (DEC-0148; Zac, 2026-11-08: a morning where waking naturally and a cup of coffee led to the dishes,
laundry, the kitchen, the development list and getting ready for work, quickly and without forcing it). MIA learns
the conditions of those runs and helps them happen again, and stays out of the way while they do. Never a schedule,
never a checklist, never a score: every finding is a count ("6 of your 9 quickest runs began with ..."), said only
once it has happened a few times.

Read from what's already kept (no new tracking): the history's done things (`DONE_TYPES`: what they said they did,
core/did_it.py, routines and maintenance, meals, workouts, play, practice, finished tasks, projects and missions),
the work dungeon's shifts (core/work_dungeon.py), the nights of sleep (core/health_manager.py).

- `windows()`: runs of things done, each within RUN_GAP of the last, MIN_RUN or more.
- `findings()`: what the runs have in common: what started them, the time of day, a work day or a day off, a full
  night's sleep before.
- `chains()` / `next_in_chain()`: what tends to follow what ("after starting the laundry you often pick up the
  kitchen"), said once, never while they're in flow.
- `in_flow()`: FLOW_COUNT things done in the last FLOW_MINUTES: the communication gate holds her non-urgent messages
  then (core/communication_gate.py).
- `easy_start()`: in their usual hour for a run, with nothing done yet today, the smallest thing that usually starts
  one, offered through the gate.
- `tomorrow_prep()`: in the evening before a work day, the prep they've done themselves on such evenings before.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DONE_TYPES = frozenset({"did", "maintenance_done", "meal_logged", "mission_completed", "path_practice",
                        "path_stage_done", "played", "project_completed", "task_done", "workout_logged"})
RUN_GAP = timedelta(minutes=45)  # each thing in a run within this of the last
MIN_RUN = 3
MIN_RUNS = 3  # runs seen before anything is said about them
CHAIN_GAP = timedelta(minutes=45)
CHAIN_MIN = 3  # times B followed A
CHAIN_SHARE = 0.5  # of the times A was done
FLOW_COUNT = 2
FLOW_MINUTES = 30
LOOKBACK_DAYS = 90
FULL_NIGHT = 7.0  # hours
_PREP = re.compile(r"\b(?:tomorrow|tonight|for work|lunch|coffee|set out|lay out|laid out|pack|packed|charge|"
                   r"charged|prep|prepped|prepared|ready)\b")
_PARTS = (("morning", 5, 12), ("afternoon", 12, 17), ("evening", 17, 22))


def _when(e) -> Optional[datetime]:
    """An event's time as a datetime (None when it can't be read)."""
    try:
        return datetime.fromisoformat(str(e.at)[:19])
    except ValueError:
        return None


def _what(e) -> str:
    """Pure logic. What a done thing was, in words: what they said ("Did: put away the dishes" -> "put away the
    dishes"), else the event's summary."""
    summary = str(e.summary or "")
    return summary[5:] if summary.startswith("Did: ") else summary


def _key(e) -> str:
    """Pure logic. What a done thing is, for counting: its said key, else its type and summary."""
    return str((e.payload or {}).get("key") or f"{e.type}:{(e.summary or '').lower()}")


def done_events(context, now: Optional[datetime] = None) -> list:
    """The real done things in the person's history in the last LOOKBACK_DAYS, oldest first."""
    from core.life_events import events_for

    now = now or datetime.now()
    try:
        found = events_for(context, since=(now.date() - timedelta(days=LOOKBACK_DAYS)).isoformat(), types=DONE_TYPES)
    except Exception:
        log.exception("Couldn't read the history for momentum")
        return []
    timed = [(w, e) for e in found for w in [_when(e)] if w is not None and w <= now]
    return [e for _w, e in sorted(timed, key=lambda p: p[0])]


def windows(events: list) -> list:
    """Pure logic. Runs of things done: each within RUN_GAP of the one before, MIN_RUN or more, oldest first."""
    runs, current, last = [], [], None
    for e in events:
        at = _when(e)
        if at is None:
            continue
        if last is not None and at - last > RUN_GAP:
            if len(current) >= MIN_RUN:
                runs.append(current)
            current = []
        current.append(e)
        last = at
    if len(current) >= MIN_RUN:
        runs.append(current)
    return runs


def _part(hour: int) -> str:
    """Pure logic. The part of the day an hour is in."""
    return next((name for name, start, end in _PARTS if start <= hour < end), "night")


def _work_days(context) -> set:
    """The days with a shift (worked or planned) in the work dungeon."""
    book = getattr(context, "dungeon", None)
    return {r.date for r in getattr(book, "runs", [])} if book is not None else set()


def _full_nights(context) -> tuple[set, set]:
    """(nights logged with a full night's sleep, every night logged), by the evening's date."""
    store = getattr(context, "health", None)
    nights = getattr(store, "sleep", []) if store is not None else []
    full = {n["night"] for n in nights if (n.get("hours") or 0) >= FULL_NIGHT}
    return full, {n["night"] for n in nights}


def findings(context, now: Optional[datetime] = None) -> list[str]:
    """What the person's runs have in common, each as a count in plain words; none until MIN_RUNS runs."""
    runs = windows(done_events(context, now))
    if len(runs) < MIN_RUNS:
        return []
    n = len(runs)
    out = []
    starters = Counter(_key(r[0]) for r in runs)
    top, count = starters.most_common(1)[0]
    if count >= 2:
        first = next(_what(r[0]) for r in runs if _key(r[0]) == top)
        out.append(f"{count} of your {n} runs of getting things done began with {first}.")
    parts = Counter(_part(_when(r[0]).hour) for r in runs)
    part, count = parts.most_common(1)[0]
    if count >= 2:
        out.append(f"{count} of {n} began in the {part}.")
    work = _work_days(context)
    if work:
        off = sum(1 for r in runs if _when(r[0]).date().isoformat() not in work)
        out.append(f"{off} of {n} were on a day off." if off * 2 >= n else f"{n - off} of {n} were on a work day.")
    full, logged = _full_nights(context)
    nights = [(_when(r[0]).date() - timedelta(days=1)).isoformat() for r in runs]
    seen = [x for x in nights if x in logged]
    if len(seen) >= 2:
        rested = sum(1 for x in seen if x in full)
        out.append(f"{rested} of the {len(seen)} with sleep logged came after a full night.")
    return out


def chains(events: list) -> dict:
    """Pure logic. key A -> (key B, what B was) when B followed A within CHAIN_GAP at least CHAIN_MIN times and in at
    least CHAIN_SHARE of A's times."""
    times_a, pairs, said = Counter(), Counter(), {}
    for a, b in zip(events, events[1:]):
        ta, tb = _when(a), _when(b)
        if ta is None or tb is None:
            continue
        times_a[_key(a)] += 1
        if tb - ta <= CHAIN_GAP and _key(a) != _key(b):
            pairs[(_key(a), _key(b))] += 1
            said[_key(b)] = _what(b)
    if events:
        times_a[_key(events[-1])] += 1
    best: dict = {}
    for (a, b), count in pairs.most_common():
        if a not in best and count >= CHAIN_MIN and count >= CHAIN_SHARE * times_a[a]:
            best[a] = (b, said[b])
    return best


def next_in_chain(context, done_key: str, now: Optional[datetime] = None) -> Optional[str]:
    """What usually follows something just done (by its key), in their words, or None."""
    found = chains(done_events(context, now)).get(done_key)
    return found[1] if found else None


def in_flow(context, now: Optional[datetime] = None) -> bool:
    """Whether the person is in the middle of getting things done: FLOW_COUNT or more in the last FLOW_MINUTES."""
    now = now or datetime.now()
    since = now - timedelta(minutes=FLOW_MINUTES)
    recent = [e for e in done_events(context, now)[-10:] if (_when(e) or since) > since]
    return len(recent) >= FLOW_COUNT


def easy_start(context, now: Optional[datetime] = None) -> Optional[str]:
    """In their usual hour for a run, with nothing done yet today: the thing that most often starts one, as a gentle
    line; None otherwise (too few runs, another hour, already moving)."""
    now = now or datetime.now()
    events = done_events(context, now)
    runs = windows(events)
    if len(runs) < MIN_RUNS or any(_when(e).date() == now.date() for e in events):
        return None
    hours = Counter(_when(r[0]).hour for r in runs)
    if hours.get(now.hour, 0) + hours.get((now.hour + 1) % 24, 0) < 2:
        return None
    starters = Counter(_key(r[0]) for r in runs)
    top, count = starters.most_common(1)[0]
    if count < 2:
        return None
    first = next(_what(r[0]) for r in runs if _key(r[0]) == top)
    return f"Your best runs usually start small, like {first}. If you're up for it, that's an easy first one."


def tomorrow_prep(context, now: Optional[datetime] = None) -> Optional[str]:
    """In the evening before a work day: the prep they've done themselves on such evenings before (said at least
    twice), if it isn't done yet tonight; None otherwise."""
    now = now or datetime.now()
    if not 17 <= now.hour < 23:
        return None
    work = _work_days(context)
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    if tomorrow not in work:
        return None
    events = done_events(context, now)
    preps = Counter()
    said = {}
    for e in events:
        at = _when(e)
        if e.type == "did" and at.hour >= 17 and _PREP.search(_what(e).lower()) and at.date() != now.date():
            preps[_key(e)] += 1
            said[_key(e)] = _what(e)
    tonight = {_key(e) for e in events if _when(e).date() == now.date()}
    for k, count in preps.most_common():
        if count >= 2 and k not in tonight:
            return f"You work tomorrow. Last times you {said[k]} the night before. Want to do that tonight?"
    return None
