"""
core.week_ahead
=================

The weekly look-ahead (brainstorm round 16, 2026-11-25): "what does my week look like?" answered with more than
what's due. After the week's bills, upkeep, events, tasks and birthdays (core/today.week_days, said by the tool
get_week), it joins what the rest of MIA already knows about the coming seven days: a holiday in it
(core/holidays), what the next day or two's forecast means for his plans (core/weather_watch reads tonight and
tomorrow: the garden, the flock, builds; never the long pipes note, which is said when he asks), a flock's feed
running out in it from a bag bought in the last HISTORY_WINDOW days (core/feed_runway; an old record isn't said
every time), the garden's steps due (core/garden_week) and water, food or fuel down to a week or under
(core/homestead_health). Each part comes from its own module in code; only the joining is new. The weekend plan
(core/question_plans) asks get_week without it (`look_ahead` false), since it looks the garden up itself and an
empty week there reads as missing (the Fable review, 2026-11-25).

How: `extras(context, today)` gives the lines (each part that can't be read is left out); get_week
(core/assistant_today_actions) ends with them after "Looking ahead:". Read only; the weather is the forecast
core/weather keeps (never fetched during a test run).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DAYS = 7


def _holidays(context, today: date) -> list:
    """A holiday in the coming week, in its own words."""
    from core.holidays import coming_line

    said = coming_line(context, today, DAYS - 1)  # inclusive: today and the six days after
    return [said] if said else []


def _weather(context, today: date) -> list:
    """What tonight's and tomorrow's forecast means for his plans (core/weather_watch.watch), each concern's words;
    never an ASKED_ONLY one (the pipes)."""
    from core import weather_watch

    return [c["text"] for c in weather_watch.watch(context, today) if c.get("kind") not in weather_watch.ASKED_ONLY]


def _feed(context, today: date) -> list:
    """Each flock whose feed runs out within the week (core/feed_runway), from a bag bought in the last
    HISTORY_WINDOW days (a bag logged months ago isn't said as run out every week)."""
    from core import feed_runway

    book = getattr(context, "flock", None)
    out = []
    for flock in getattr(book, "flocks", []) or []:
        found = feed_runway.runway(book.entries, flock, today)
        if not found or found.get("unknown") or found["days_left"] is None or found["days_left"] > DAYS:
            continue
        try:
            bought = date.fromisoformat(str(found.get("bought_on") or "")[:10])
        except ValueError:
            continue
        if (today - bought).days <= feed_runway.HISTORY_WINDOW:
            out.append(feed_runway.words(flock.name, found))
    return out


def _garden(context, today: date) -> list:
    """The garden's steps in the week (core/garden_week)."""
    from core import garden_week

    items = garden_week.this_week(context, today)
    return [f"In the garden: {garden_week.words(items, today)}."] if items else []


def _supplies(context, today: date) -> list:
    """Water, food or generator fuel lasting a week or under (core/homestead_health.days; the feed is `_feed`'s)."""
    from core import homestead_health

    found, _missing = homestead_health.days(context, today)
    low = sorted(((n, v) for n, v in found.items() if not n.startswith("Feed") and v <= DAYS), key=lambda kv: kv[1])
    if not low:
        return []
    return ["Running low on " + ", ".join(f"{n.lower()} ({v:g} day{'' if v == 1 else 's'} left)" for n, v in low)
            + "."]


def extras(context, today: Optional[date] = None) -> list[str]:
    """The look-ahead's lines for the coming week, in order: holidays, the weather against his plans, feed, the
    garden, supplies; a part that can't be read is left out, never the rest."""
    today = today or date.today()
    out = []
    for part, name in ((_holidays, "holidays"), (_weather, "weather"), (_feed, "feed"), (_garden, "garden"),
                       (_supplies, "supplies")):
        try:
            out.extend(part(context, today))
        except Exception:  # noqa: BLE001 - one part that can't be read never stops the rest
            log.exception("Week ahead: the %s couldn't be read", name)
    return out
