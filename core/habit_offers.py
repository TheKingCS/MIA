"""
core.habit_offers
===================

Routines offered from his habits (DEC-0294; Zac, 2026-11-23: "Offer once, I decide"): when the same kind of thing
shows in his history on the same weekday three weeks running (workouts logged on Mondays, the budget checked on
Sundays), MIA offers one routine for it, a weekly reminder, once. His yes makes it, by his own words ("remind me every
Monday to ...", the reminder tool he already has); anything else, and it's never offered again. It only ever offers a
reminder: it never changes a record by itself.

`habits(events, today)` finds them (pure: his own history only, nothing MIA did herself); `offer(context, now)` is the
daily check's message, each habit offered once ever (`OFFERED_KEY` keeps which).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

WEEKS = 3
OFFERED_KEY = "habits.offered"  # "<type>@<weekday>" already offered: never again
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_NOT_HIS = ("mia", "system", "workflow", "sync", "import")  # what MIA or a machine did is no habit of his


def habits(events: list, today: date) -> list[tuple[str, int]]:
    """Pure logic. The (event type, weekday) pairs that happened on that weekday in each of the last WEEKS weeks
    (counting back from yesterday), from his own doing only, the oldest habit first."""
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


def offer(context, now: datetime) -> list:
    """The daily check's message: the first habit not offered yet, once ever, through the gate (AMBIENT)."""
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
    if not fresh:
        return []
    kind, weekday = fresh[0]
    offered.append(f"{kind}@{weekday}")
    config.set(OFFERED_KEY, offered)  # offered once: whatever he says, never again
    what = life_events.TYPES.get(kind, kind.replace("_", " "))
    day = DAYS[weekday]
    return [Candidate(topic="habit_offer", title=f"Every {day}: {what}", urgency=AMBIENT, source="system",
                      fingerprint=f"habit-{kind}-{weekday}",
                      message=(f"Three {day}s running there were {what}. Want a reminder every {day}? Say \"remind me "
                               f"every {day} to ...\" and I'll set it. If not, I won't bring this one up again."))]
