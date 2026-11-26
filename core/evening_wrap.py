"""
core.evening_wrap
===================

The evening wrap (DEC-0292; Zac, 2026-11-23: "Yes"): once an evening, two sentences: what got done today, then
tomorrow's first thing and tomorrow's weather. Everything from his records, worked out in code: today's wins from the
history (core/life_events.py), tomorrow's list (core/today.py, overdue and today first, timed ones in time order), the
forecast kept (core/weather.py, never fetched for this). Through the communication gate like any of her messages
(paced, and mutable from the message itself), from the hour he sets (`evening_wrap.hour`, 8 pm unless he sets another),
once a day.

`wrap(context, now)` is the words ("" when there's nothing at all to say); `offer(context, now)` the daily check's
message. A course practised today on a streak of three days or more is named after the day ("Guitar: 4 days in a
row.", `streaks`, brainstorm round 17). What she noticed today (`noticed_today`, brainstorm round 18): the first thing
off his usual (core/unusual) she told him today, named again in one line ("Something I flagged today: Feed, more
than usual."), from the gate's own log, so it's only ever what reached him today.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

HOUR_KEY = "evening_wrap.hour"
DEFAULT_HOUR = 20


def done_today(context, today: date) -> str:
    """Today's wins in a few words ("2 workouts, 1 bill paid": one of a thing said singular, `_count`), "" for
    none."""
    from core import life_events

    events = [e for e in life_events.events_for(context, since=today.isoformat(), until=today.isoformat())
              if e.type not in life_events.AUDIT_ONLY]
    taken_back = life_events.reversed_ids(events)
    wins = [e for e in events if e.type in life_events.WINS and e.event_id not in taken_back]
    totals = life_events.counts(wins)
    return ", ".join(_count(n, life_events.TYPES.get(t, t)) for t, n in sorted(totals.items(), key=lambda kv: -kv[1]))


def _count(n: int, label: str) -> str:
    """Pure logic. "1 bill paid", "2 bills paid": a label's first word made singular for one."""
    if n != 1:
        return f"{n} {label}"
    first, _, rest = label.partition(" ")
    one = first[:-3] + "y" if first.endswith("ies") else first[:-1] if first.endswith("s") else first
    return f"1 {one}" + (f" {rest}" if rest else "")


def first_tomorrow(context, tomorrow: date) -> str:
    """Tomorrow's first thing from its own list (a timed one with its time), else what's still open; never an alarm;
    "" for nothing.
    An alarm is told by `core/today.is_alarm`; a task can be the first thing."""
    from core.today import is_alarm, today_items

    items = [i for i in today_items(context, tomorrow) if i.when == "today" and not is_alarm(i)]
    if not items:  # nothing of tomorrow's own: what's still open (an alarm is never the day's first thing; a task is)
        items = [i for i in today_items(context, tomorrow) if i.when == "overdue" and not is_alarm(i)]
    if not items:
        return ""
    first = items[0]
    return first.title + (f" at {first.time}" if getattr(first, "time", "") else "")


def weather_tomorrow(context) -> str:
    """Tomorrow's forecast in a few words, from the forecast already kept; "" without one."""
    from core import weather

    card = weather.card(context)
    t = card.get("tomorrow") if card.get("text") else None
    if not t:
        return ""
    words = (t.get("words") or "").lower()
    return f"{words + ', ' if words else ''}{t['high']}{card.get('unit', '')} and {t['low']}"


STREAK_FROM = 3  # days in a row worth a word


def streaks(context, today: date) -> str:
    """His courses practised today on a streak of STREAK_FROM days or more (core/paths.stats), said in a few words
    ("Guitar: 4 days in a row."), or "" (brainstorm round 17: hobby streaks in the evening wrap)."""
    from core import paths

    book = getattr(context, "paths", None)
    if book is None:
        return ""
    said = []
    for path_id in book.started():
        program = paths.program_of(context, path_id)
        record = book.path(path_id) or {}
        if program is None or not any(s.get("date") == today.isoformat() for s in record.get("sessions", [])):
            continue
        streak = paths.stats(book, program, today)["streak"]
        if streak >= STREAK_FROM:
            said.append(f"{program.name}: {streak} days in a row")
    return ("; ".join(said) + ".") if said else ""


def noticed_today(context, today: date) -> str:
    """What she noticed today: the title of the first unusual finding (core/unusual's topic) the gate delivered to him
    today (a notification made) and he didn't dismiss, and how many more; "" when none (one held back or dropped is
    never said here: it may still come, or he heard it days ago). A finding first found in the same background run as
    the wrap isn't in the log yet, so it isn't named; it went out beside the wrap anyway (the Fable review,
    2026-11-26)."""
    from core.communication_gate import ACT

    gate = getattr(context, "communication", None)
    if gate is None:
        return ""
    sent = [e for e in gate.entries_for_day(today.isoformat())
            if e.get("topic") == "unusual" and e.get("action") == ACT and e.get("title")
            and e.get("notification_id") and not e.get("dismissed_at")]
    if not sent:
        return ""
    more = len(sent) - 1
    title = sent[0]["title"].replace(": ", ", ")
    others = f" (and {more} other thing{'s' if more > 1 else ''})" if more else ""
    return f"Something I flagged today: {title}{others}."


def wrap(context, now: datetime) -> str:
    """The two sentences, with any course on a streak practised today and what she noticed today (`noticed_today`)
    between them; "" when there's nothing done, nothing tomorrow, no weather, no streak and nothing noticed
    (a day of only practice says the streak, never "a quiet day")."""
    today = now.date()
    parts = []
    for read, name in ((lambda: done_today(context, today), "done"),
                       (lambda: first_tomorrow(context, today + timedelta(days=1)), "first"),
                       (lambda: weather_tomorrow(context), "weather")):
        try:
            parts.append(read())
        except Exception:  # noqa: BLE001 - one part that can't be read never stops the wrap
            log.exception("Evening wrap: %s couldn't be read", name)
            parts.append("")
    done, first, sky = parts
    try:
        streak = streaks(context, today)
    except Exception:  # noqa: BLE001 - the wrap goes without it
        log.exception("Evening wrap: the streaks couldn't be read")
        streak = ""
    try:
        noticed = noticed_today(context, today)
    except Exception:  # noqa: BLE001 - the wrap goes without it
        log.exception("Evening wrap: what she noticed couldn't be read")
        noticed = ""
    if not (done or first or sky or streak or noticed):
        return ""
    head = f"Today: {done}." if done else "" if streak else "A quiet day today."  # practice is a day's doing too
    if streak:
        head = f"{head} {streak}".strip()
    if noticed:
        head = f"{head} {noticed}".strip()
    tail = []
    if first:
        tail.append(f"first up, {first}")
    if sky:
        tail.append(f"the weather: {sky}")
    return head + (" Tomorrow, " + "; ".join(tail) + "." if tail else "")


def _hour(context) -> int:
    """The hour the wrap may come from: his setting from noon to 11 pm, else DEFAULT_HOUR."""
    try:
        from core import person_settings

        hour = int(person_settings.get(context, HOUR_KEY, DEFAULT_HOUR))
        return hour if 12 <= hour <= 23 else DEFAULT_HOUR  # an evening wrap: never about a day barely begun
    except (TypeError, ValueError, AttributeError):
        return DEFAULT_HOUR


def offer(context, now: datetime) -> list:
    """The daily check's message: from his hour on, once a day, TIMELY until the day ends."""
    from core.communication_gate import TIMELY, Candidate

    if now.hour < _hour(context):
        return []
    said = wrap(context, now)
    if not said:
        return []
    midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    return [Candidate(topic="evening_wrap", title="Your evening wrap", message=said, urgency=TIMELY, source="system",
                      fingerprint=f"evening-wrap-{now.date().isoformat()}", expires=midnight.isoformat())]
