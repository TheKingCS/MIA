"""
core.habit_offers
===================

Routines offered from his habits (DEC-0294; Zac, 2026-11-23: "Offer once, I decide"): when the same kind of thing
shows in his history on the same weekday three weeks running (workouts logged on Mondays, the budget checked on
Sundays), MIA offers one routine for it, a weekly reminder, once. His yes makes it, by his own words ("remind me every
Monday to ...", the reminder tool he already has); anything else, and it's never offered again. It only ever offers a
reminder: it never changes a record by itself.

`habits(events, today)` finds them (pure: his own history only, nothing MIA did herself); `offer(context, now)` is the
daily check's message, tried once a day, each habit counted as offered (`OFFERED_KEY`, never again) only once
the gate's log shows it reached him.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

WEEKS = 3
OFFERED_KEY = "habits.offered"  # "<type>@<weekday>" already offered: never again
TRIED_KEY = "habits.tried_on"  # the day an offer was last put to the gate: one try a day
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
# what MIA did on her own (a standing yes records "mia"), a machine did, or an email brought is no habit of his
_NOT_HIS = ("mia", "system", "workflow", "sync", "import", "email", "inbox", "browser")


def habits(events: list, today: date) -> list[tuple[str, int]]:
    """Pure logic. The (event type, weekday) pairs that happened on that weekday in each of the last WEEKS weeks
    (counting back from yesterday), from his own doing only, by weekday (Monday first), then kind."""
    start = today - timedelta(days=7 * WEEKS)
    seen: dict = {}
    for e in events:
        if str(getattr(e, "source", "") or "").split(":")[0].lower() in _NOT_HIS:
            continue
        try:
            day = date.fromisoformat(str(e.at)[:10])
        except ValueError:
            continue
        if start <= day < today:
            seen.setdefault((e.type, day.weekday()), set()).add((today - day).days // 7)
    return sorted((k for k, weeks in seen.items() if len(weeks) >= WEEKS), key=lambda k: (k[1], k[0]))


def _title(kind: str, weekday: int) -> str:
    """Pure logic. One habit's message title, which is also how its delivery is found in the gate's log."""
    from core.life_events import TYPES

    return f"Every {DAYS[weekday]}: {TYPES.get(kind, kind.replace('_', ' '))}"


def _told(context, today) -> set:
    """The titles of habit offers the gate let through in the last 60 days (its log), so one counts as offered only
    once he could actually see it."""
    gate = getattr(context, "communication", None)
    try:
        entries = gate.entries_since((today - timedelta(days=60)).isoformat()) if gate is not None else []
    except Exception:  # noqa: BLE001 - a log that can't be read only means it tries again tomorrow
        return set()
    return {e.get("title", "") for e in entries if e.get("topic") == "habit_offer" and e.get("action") == "act"}


def offer(context, now: datetime) -> list:
    """The daily check's message: the first habit not offered yet, through the gate (AMBIENT), tried once a day. A
    habit counts as offered (never again) only once the gate's log shows it went through, so one held back for
    spacing or a busy moment is tried again another day, never lost."""
    from core import life_events
    from core.communication_gate import AMBIENT, Candidate

    config = getattr(context, "config", None)
    if config is None:
        return []
    today = now.date()
    try:
        events = [e for e in life_events.events_for(context, since=(today - timedelta(days=7 * WEEKS)).isoformat())
                  if e.type in life_events.WINS]
    except Exception:  # noqa: BLE001 - the history that can't be read never breaks the check
        log.exception("Habit offers: the history couldn't be read")
        return []
    offered = list(config.get(OFFERED_KEY, []) or [])
    fresh = [(t, d) for t, d in habits(events, today) if f"{t}@{d}" not in offered]
    told = _told(context, today)
    reached = [(t, d) for t, d in fresh if _title(t, d) in told]
    if reached:  # the gate let it through: offered once, whatever he says, never again
        offered += [f"{t}@{d}" for t, d in reached]
        config.set(OFFERED_KEY, offered)
        fresh = [h for h in fresh if h not in reached]
    if not fresh or config.get(TRIED_KEY, "") == today.isoformat():
        return []  # one try a day: the gate may have held it back for now, never burning it
    config.set(TRIED_KEY, today.isoformat())
    kind, weekday = fresh[0]
    what = life_events.TYPES.get(kind, kind.replace("_", " "))
    day = DAYS[weekday]
    return [Candidate(topic="habit_offer", title=_title(kind, weekday), urgency=AMBIENT, source="system",
                      fingerprint=f"habit-{kind}-{weekday}",
                      message=(f"Three {day}s running there were {what}. Want a reminder every {day}? Say \"remind me "
                               f"every {day} to ...\" and I'll set it. If not, I won't bring this one up again."))]
