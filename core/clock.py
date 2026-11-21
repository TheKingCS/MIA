"""
core.clock
============

One clock for MIA (LS-07, DEC-0284; `docs/mia_os/MIA_COGNITIVE_ARCHITECTURE.md` §6). Before it, 168 files in `core/`
each asked the machine for a naive local time. New code asks here instead:
- `now()`: the time in his zone, aware of it;
- `today()`: the day as he means it;
- `week_of(day)`: Monday to Sunday;
- `parse_day(text, today)`: the day a phrase means.

`parse_day` understands:
- "today", "tonight", "tomorrow" and the weekdays (as `core/life_notes.due_date` already does);
- "in 3 days", "in two weeks", "in a month";
- "March 5", "5 March", "2026-12-01";
- "the first Saturday of March".

Dates are always worked out here in code, never by a model (P3).

**His zone** is the setting `region.timezone` (an IANA name such as "America/Chicago") when it's set and known, else
the computer's own, asked of the system for each moment so a summer date gets summer time (`_Local`). **Tests
freeze it** (`frozen(moment)`), so a test can't fail because the suite crossed midnight
(the glasses test of 2026-11-18). Existing modules move here as they're next touched; nothing is changed underneath
them.
"""

from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta, tzinfo
from typing import Iterator, Optional

SETTING = "region.timezone"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "last": -1}
WORD_NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
_frozen = threading.local()


class _Local(tzinfo):
    """The computer's own zone, asked of the operating system for each moment, so a date in summer gets summer
    time even when it's winter now (a fixed offset taken today didn't)."""

    def _local(self, dt: datetime):
        """The operating system's local time for this wall-clock moment."""
        import time as _time

        stamp = _time.mktime((dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, 0, 0, -1))
        return _time.localtime(stamp)

    def utcoffset(self, dt):
        """The offset from UTC at that moment."""
        return timedelta(seconds=self._local(dt).tm_gmtoff) if dt is not None else None

    def dst(self, dt):
        """How much of the offset is summer time at that moment."""
        return timedelta(hours=1) if dt is not None and self._local(dt).tm_isdst > 0 else timedelta(0)

    def tzname(self, dt):
        """The zone's short name at that moment."""
        return self._local(dt).tm_zone if dt is not None else None


_LOCAL = _Local()


def zone(context=None) -> tzinfo:
    """His time zone: the `region.timezone` setting when it names a known zone, else the computer's own (`_LOCAL`,
    with each date's own offset)."""
    name = ""
    config = getattr(context, "config", None) if context is not None else None
    if config is not None:
        try:
            name = str(config.get(SETTING, "") or "")
        except Exception:  # noqa: BLE001 - a setting that can't be read is the computer's zone
            name = ""
    if name:
        try:
            from zoneinfo import ZoneInfo

            return ZoneInfo(name)
        except Exception:  # noqa: BLE001 - an unknown name is the computer's zone
            pass
    return _LOCAL


def now(context=None) -> datetime:
    """The time now in his zone, aware of it; the frozen moment while a test holds one."""
    held = getattr(_frozen, "moment", None)
    if held is not None:
        return held if held.tzinfo else held.replace(tzinfo=zone(context))
    return datetime.now(zone(context))


def today(context=None) -> date:
    """The day it is for him."""
    return now(context).date()


@contextmanager
def frozen(moment: datetime) -> Iterator[datetime]:
    """Holds `now()` at `moment` on this thread for the block (tests)."""
    previous = getattr(_frozen, "moment", None)
    _frozen.moment = moment
    try:
        yield moment
    finally:
        _frozen.moment = previous


def week_of(day: date) -> tuple[date, date]:
    """Pure logic. The Monday and Sunday of the week a day is in."""
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def nth_weekday(year: int, month: int, n: int, weekday: int) -> Optional[date]:
    """Pure logic. The `n`th given weekday of a month (1 the first, -1 the last); None when the month has no such day
    (a fifth Monday)."""
    if n == -1:
        last = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1))
        return last - timedelta(days=(last.weekday() - weekday) % 7)
    first = date(year, month, 1)
    found = first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    return found if found.month == month else None


def _add_months(day: date, months: int) -> date:
    """Pure logic. The same day `months` later, or the month's last day when it's shorter."""
    year, month = day.year + (day.month - 1 + months) // 12, (day.month - 1 + months) % 12 + 1
    for d in range(day.day, 27, -1) if day.day > 28 else (day.day,):
        try:
            return date(year, month, d)
        except ValueError:
            continue
    return date(year, month, 28)


def _number(word: str) -> Optional[int]:
    """Pure logic. A count in digits or words ("3", "two", "a"); None when it isn't one."""
    return int(word) if word.isdigit() else WORD_NUMBERS.get(word)


def _next_on_or_after(month: int, day: int, after: date) -> Optional[date]:
    """Pure logic. The next `month`/`day` on or after `after` (this year's, else next year's)."""
    for year in (after.year, after.year + 1):
        try:
            found = date(year, month, day)
        except ValueError:
            continue
        if found >= after:
            return found
    return None


def parse_day(text: str, said: date) -> Optional[date]:
    """Pure logic. The day a phrase means, from the day it was said; None when it isn't one this understands."""
    phrase = " ".join((text or "").lower().replace(",", " ").split())
    phrase = re.sub(r"^(on|by|until|till) ", "", phrase)
    from core.life_notes import due_date

    found = due_date(phrase, said)
    if found is not None:
        return found
    m = re.fullmatch(r"in (\w+) (day|days|week|weeks|month|months)", phrase)
    if m and _number(m.group(1)) is not None:
        n, unit = _number(m.group(1)), m.group(2)
        if unit.startswith("day"):
            return said + timedelta(days=n)
        if unit.startswith("week"):
            return said + timedelta(weeks=n)
        return _add_months(said, n)
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", phrase)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    months = "|".join(MONTHS)
    m = re.fullmatch(rf"({months}) (\d{{1,2}})(?:st|nd|rd|th)?", phrase) or \
        re.fullmatch(rf"(?:the )?(\d{{1,2}})(?:st|nd|rd|th)? (?:of )?({months})", phrase)
    if m:
        month_word, day_text = (m.group(1), m.group(2)) if m.group(1) in MONTHS else (m.group(2), m.group(1))
        return _next_on_or_after(MONTHS.index(month_word) + 1, int(day_text), said)
    m = re.fullmatch(rf"the ({'|'.join(ORDINALS)}) ({'|'.join(DAYS)}) (?:of|in) ({months})", phrase)
    if m:
        month = MONTHS.index(m.group(3)) + 1
        for year in (said.year, said.year + 1):
            found = nth_weekday(year, month, ORDINALS[m.group(1)], DAYS.index(m.group(2)))
            if found is not None and found >= said:
                return found
    return None
