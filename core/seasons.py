"""
core.seasons
==============

Seasons of memory (build plan step 10, DEC-0094; the gap: "long-term memory is
lists, not understanding"). What changed this month and this year, worked out
in code from the person's history (core/life_events.py) and their memories
(core/user_memory_manager.py), against the period before:

- what grew or shrank (each kind of thing done, and its numbers: minutes
  trained, eggs collected, XP earned, hours on builds);
- what's new this time and what stopped;
- money in and out, from the history's own amounts;
- what she came to know about them (memories kept, by kind);
- the biggest moments (the wins' own one-line summaries).

**This month** is the 1st to today, against the same days of last month;
**this year** is January 1 to today against the same span last year; **last
month / last year** are the whole closed period against the one before. The
question plan `seasons` (core/question_plans.py) puts these lines on a fact
sheet and the model only phrases them. Each closed month and year is kept
(`close_past()`, the daily check) in the person's own folder
(`seasons.json`, sealed on disk: DEC-0126), which the Chronicle's yearly edition grows from.

A child account never sees the money lines (core/child_accounts.py).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from core.at_rest import open_text, seal
from core.atomic_write import atomic_write_text

FILE_NAME = "seasons.json"
MONEY_IN = ("income_added", "income_received", "rent_received")
MONEY_OUT = ("expense_added", "property_expense", "bill_paid", "debt_payment")
NUMBERS = {"workout_logged": ("minutes", "minutes trained"), "eggs_collected": ("eggs", "eggs"),
           "mission_completed": ("xp", "XP from missions"), "skill_evidence": ("xp", "skill XP"),
           "build_finished": ("hours", "hours on builds"), "dungeon_cleared": ("hours", "hours at work")}
CHANGE = 0.2  # a count this much higher or lower is "more" or "fewer"; less is "about the same"


# ------------------------------------------------------------------ periods (pure)

def _month_start(day: date) -> date:
    """Pure logic. The first day of a day's month."""
    return day.replace(day=1)


def _prev_month_start(day: date) -> date:
    """Pure logic. The first day of the month before."""
    return (_month_start(day) - timedelta(days=1)).replace(day=1)


def periods(kind: str, today: date) -> tuple[tuple[date, date], tuple[date, date], str]:
    """Pure logic. (this period, the one compared with, its label). `kind`: month, year, last month, last year."""
    if kind == "month":
        start = _month_start(today)
        before = _prev_month_start(today)
        last_day = (start - timedelta(days=1)).day
        return (start, today), (before, before.replace(day=min(today.day, last_day))), f"{today:%B} so far"
    if kind == "last month":
        start = _prev_month_start(today)
        end = _month_start(today) - timedelta(days=1)
        before = _prev_month_start(start)
        return (start, end), (before, start - timedelta(days=1)), f"{start:%B}"
    if kind == "year":
        start = date(today.year, 1, 1)
        try:
            same = today.replace(year=today.year - 1)
        except ValueError:  # February 29th
            same = today.replace(year=today.year - 1, day=28)
        return (start, today), (date(today.year - 1, 1, 1), same), f"{today.year} so far"
    if kind == "last year":
        y = today.year - 1
        return (date(y, 1, 1), date(y, 12, 31)), (date(y - 1, 1, 1), date(y - 1, 12, 31)), str(y)
    raise ValueError(f"No period {kind!r}.")


def kind_in(prompt: str, today: Optional[date] = None) -> str:
    """Pure logic. The period a question means ("how did October go?" in November is last month)."""
    text = (prompt or "").lower()
    today = today or date.today()
    if "last year" in text or str(today.year - 1) in text:
        return "last year"
    if "last month" in text or f"{_prev_month_start(today):%B}".lower() in text:
        return "last month"
    if "year" in text:
        return "year"
    return "month"


# ------------------------------------------------------------------ the comparison

def _in(events: list, span: tuple[date, date]) -> list:
    """Pure logic. The life events whose day falls in a span (both ends included)."""
    a, b = span[0].isoformat(), span[1].isoformat()
    return [e for e in events if a <= e.day <= b]


def _total(events: list, types: tuple, key: str = "amount") -> float:
    """Pure logic. The sum of one payload field (the amount by default) over the events of the given types; a value
    that isn't a number is skipped.
    """
    total = 0.0
    for e in events:
        if e.type in types:
            try:
                total += float((e.payload or {}).get(key) or 0)
            except (TypeError, ValueError):
                continue
    return total


def compare(now_events: list, before_events: list, label: str, money: bool = True, memories_now: Optional[dict] = None,
            money_word=None) -> list[str]:
    """Pure logic. The lines of a season: what changed between two lists of life events."""
    from core.life_events import AUDIT_ONLY, TYPES, WINS, counts, reversed_ids

    gone = reversed_ids(now_events) | reversed_ids(before_events)
    now = [e for e in now_events if e.type not in AUDIT_ONLY and e.event_id not in gone and e.type != "undone"]
    before = [e for e in before_events if e.type not in AUDIT_ONLY and e.event_id not in gone and e.type != "undone"]
    from core.life_events import MONEY_TYPES

    if not money:
        now = [e for e in now if e.type not in MONEY_TYPES]
        before = [e for e in before if e.type not in MONEY_TYPES]
    if not now and not before:
        return [f"Nothing recorded for {label} or the period before it."]
    a, b = counts(now), counts(before)
    lines, more, fewer, same, new, stopped = [], [], [], [], [], []
    for t in sorted(set(a) | set(b), key=lambda t: -(a.get(t, 0) + b.get(t, 0))):
        if t in MONEY_TYPES:
            continue
        x, y = a.get(t, 0), b.get(t, 0)
        word = TYPES.get(t, t.replace("_", " "))
        if y == 0 and x:
            new.append(f"{word} ({x})")
        elif x == 0 and y:
            stopped.append(f"{word} (none, after {y} the period before)")
        elif x >= y * (1 + CHANGE):
            more.append(f"{word} {x}, up from {y}")
        elif x <= y * (1 - CHANGE):
            fewer.append(f"{word} {x}, down from {y}")
        else:
            same.append(f"{word} {x}")
    if new:
        lines.append(f"New in {label}: " + "; ".join(new) + ".")
    if stopped:
        lines.append(f"Stopped in {label}: " + "; ".join(stopped) + ".")
    if more:
        lines.append(f"More in {label}: " + "; ".join(more) + ".")
    if fewer:
        lines.append(f"Fewer in {label}: " + "; ".join(fewer) + ".")
    if same:
        lines.append(f"About the same: " + "; ".join(same) + ".")
    for t, (key, word) in NUMBERS.items():
        x, y = _total(now, (t,), key), _total(before, (t,), key)
        if x or y:
            lines.append(f"{word[0].upper() + word[1:]}: {x:g} in {label}, {y:g} the period before.")
    if money:
        fmt = money_word or (lambda v: f"{v:,.2f}")
        i, o = _total(now, MONEY_IN), _total(now, MONEY_OUT)
        pi, po = _total(before, MONEY_IN), _total(before, MONEY_OUT)
        if i or o or pi or po:
            lines.append(f"Money recorded in {label}: {fmt(i)} in and {fmt(o)} out (the period before: {fmt(pi)} in, "
                         f"{fmt(po)} out).")
    if memories_now:
        lines.append(f"What I came to know about you in {label}: " + ", ".join(
            f"{n} about {k.lower()}" for k, n in sorted(memories_now.items(), key=lambda kv: -kv[1])) + ".")
    wins, kinds = [], set()
    for e in (e for e in now if e.type in WINS):  # the latest of each kind first: variety, not five workouts
        if e.type not in kinds:
            wins.append(e)
            kinds.add(e.type)
    wins = wins[:5]
    if wins:
        lines.append("Some of what you did: " + "; ".join(e.summary for e in wins) + ".")
    return lines


def season(context, kind: str = "month", today: Optional[date] = None) -> tuple[str, list[str]]:
    """(the label, the lines) for a period of this person's life."""
    from core.child_accounts import is_child
    from core.life_events import events_for

    today = today or date.today()
    (a, b), (c, d), label = periods(kind, today)
    events = events_for(context, since=c.isoformat(), until=b.isoformat())
    child = getattr(context, "config", None) is not None and is_child(context)
    memories: dict[str, int] = {}
    store = getattr(context, "user_memories", None)
    if store is not None:
        for m in store.all_memories():
            if a.isoformat() <= (m.created_at or "")[:10] <= b.isoformat():
                memories[m.category] = memories.get(m.category, 0) + 1
    try:
        from core.region import money

        word = lambda v: money(v)  # noqa: E731
    except Exception:
        word = None
    return label, compare(_in(events, (a, b)), _in(events, (c, d)), label, money=not child, memories_now=memories,
                          money_word=word)


# ------------------------------------------------------------------ kept seasons

def _folder(context) -> Optional[Path]:
    """The person's folder seasons are kept in (the failure log's, else the traces'), or None."""
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def kept(context) -> dict:
    """Every season kept so far (seasons.json, sealed: DEC-0126), by its key; none when it's missing or unreadable
    (a sealed one that won't open is copied aside first, so a later save can't lose it)."""
    folder = _folder(context)
    if folder is None:
        return {}
    try:
        return json.loads(open_text(folder / FILE_NAME))
    except (OSError, ValueError):
        return {}


def close_past(context, today: Optional[date] = None) -> list[str]:
    """Keep last month (and, in January, last year) once each, sealed. Returns the keys kept now."""
    folder = _folder(context)
    if folder is None:
        return []
    today = today or date.today()
    found = kept(context)
    added = []
    for kind, key in (("last month", f"{_prev_month_start(today):%Y-%m}"), ("last year", str(today.year - 1))):
        if key in found:
            continue
        label, lines = season(context, kind, today)
        found[key] = {"label": label, "lines": lines, "kept": today.isoformat()}
        added.append(key)
    if added:
        folder.mkdir(parents=True, exist_ok=True)
        # sealed here (DEC-0126): its lines are worked out from the sealed memories and history; not a SEALED name,
        # since no store loads it
        atomic_write_text(folder / FILE_NAME, seal(json.dumps(found, indent=1, ensure_ascii=False)))
    return added
