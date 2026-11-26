"""
core.holidays
===============

When a holiday falls (the live sweep, 2026-11-25: "What day is Thanksgiving this year?" got "I don't have that
information"), worked out in code: the ones on a fixed date (Christmas, the Fourth of July, Halloween...), the ones on
a weekday of a month (Thanksgiving, the fourth Thursday of November in the US and the second Monday of October in
Canada; Memorial Day; Mother's Day...), and Easter by the Gregorian computus (Meeus/Jones/Butcher). A holiday kept
only in some countries is said only for those (the person's country, core/region.py); one this module doesn't know
is the model's.

How: `day_of(name, year, country)` (pure) gives the date or None; `reply(context, words)` reads "when is
Thanksgiving?", "what day is Easter next year?", "what date is Memorial Day in 2027?" and says the date, the weekday
and how far off it is; `coming_line` says the ones in his coming week (the morning briefing names them). Read-only.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Pure logic. The nth (1 to 5) weekday (Monday 0) of a month, or the last one for n = -1."""
    if n == -1:
        last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1))
        return last - timedelta(days=(last.weekday() - weekday) % 7)
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def easter(year: int) -> date:
    """Pure logic. Western Easter Sunday (the anonymous Gregorian algorithm, Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    return date(year, month, (h + l - 7 * m + 114) % 31 + 1)


# name: (the words that name it, the countries that keep it (None for everywhere it's known), how it falls)
HOLIDAYS = {
    "New Year's Day": (r"new year'?s(?: day)?", None, lambda y: date(y, 1, 1)),
    "Valentine's Day": (r"valentine'?s(?: day)?", None, lambda y: date(y, 2, 14)),
    "St. Patrick's Day": (r"st\.? patrick'?s(?: day)?|saint patrick'?s(?: day)?", None, lambda y: date(y, 3, 17)),
    "Easter": (r"easter(?: sunday)?", None, easter),
    "Good Friday": (r"good friday", None, lambda y: easter(y) - timedelta(days=2)),
    "Mother's Day": (r"mother'?s day", ("US", "CA"), lambda y: nth_weekday(y, 5, 6, 2)),
    "Memorial Day": (r"memorial day", ("US",), lambda y: nth_weekday(y, 5, 0, -1)),
    "Father's Day": (r"father'?s day", ("US", "CA", "GB"), lambda y: nth_weekday(y, 6, 6, 3)),
    "Independence Day": (r"(?:the )?fourth of july|independence day|july 4(?:th)?", ("US",), lambda y: date(y, 7, 4)),
    "Labor Day": (r"labou?r day", ("US", "CA"), lambda y: nth_weekday(y, 9, 0, 1)),
    "Halloween": (r"halloween", None, lambda y: date(y, 10, 31)),
    "Veterans Day": (r"veterans'? day", ("US",), lambda y: date(y, 11, 11)),
    "Thanksgiving (US)": (r"thanksgiving", ("US",), lambda y: nth_weekday(y, 11, 3, 4)),
    "Thanksgiving (Canada)": (r"thanksgiving", ("CA",), lambda y: nth_weekday(y, 10, 0, 2)),
    "Christmas Eve": (r"christmas eve", None, lambda y: date(y, 12, 24)),
    "Christmas": (r"christmas(?: day)?(?! eve)", None, lambda y: date(y, 12, 25)),
    "New Year's Eve": (r"new year'?s eve", None, lambda y: date(y, 12, 31)),
    "Martin Luther King Jr. Day": (r"(?:martin luther king|mlk)(?: jr\.?)?(?: day)?", ("US",),
                                   lambda y: nth_weekday(y, 1, 0, 3)),
    "Presidents' Day": (r"presidents'? day", ("US",), lambda y: nth_weekday(y, 2, 0, 3)),
    "Columbus Day": (r"columbus day|indigenous peoples'? day", ("US",), lambda y: nth_weekday(y, 10, 0, 2)),
}


def named(words: str, country: str = "US") -> Optional[str]:
    """Pure logic. The holiday his words name, kept in his country, or None: the one whose words cover the most of
    what he said ("new year's eve" is never New Year's Day: the Fable review), and never Easter Monday or Orthodox
    Easter as Easter Sunday."""
    said = " ".join(str(words or "").lower().replace("\u2019", "'").split())
    if re.search(r"\b(?:easter monday|orthodox easter|greek easter)\b", said):
        return None
    best, length = None, 0
    for name, (pattern, where, _fall) in HOLIDAYS.items():
        found = re.search(rf"\b(?:{pattern})\b", said)
        if found and (where is None or country in where) and len(found.group()) > length:
            best, length = name, len(found.group())
    return best


def day_of(name: str, year: int) -> date:
    """Pure logic. The date a holiday falls in a year."""
    return HOLIDAYS[name][2](year)


def coming(country: str, today: date, days: int = 7) -> list:
    """Pure logic. The holidays his country keeps in the next `days` days, today included: [(name, date)], soonest
    first (one name per day: Christmas, never Christmas and Christmas Eve on one date)."""
    found = {}
    for name, (_pattern, where, _fall) in HOLIDAYS.items():
        if where is not None and country not in where:
            continue
        for year in (today.year, today.year + 1):
            on = day_of(name, year)
            if 0 <= (on - today).days <= days and on not in found:
                found[on] = name.split(" (")[0]
    return sorted(((n, d) for d, n in found.items()), key=lambda nd: nd[1])


def coming_line(context, today: Optional[date] = None, days: int = 7) -> str:
    """The holidays in his coming week in words ("Thanksgiving is Thursday."), or "" when there are none."""
    from core.region import country_of

    today = today or date.today()
    try:
        country = country_of(context) if context is not None else "US"
    except Exception:  # noqa: BLE001 - no settings: the default
        country = "US"
    said = []
    for name, on in coming(country, today, days):
        when = "today" if on == today else "tomorrow" if (on - today).days == 1 else f"{on:%A}"
        said.append(f"{name} is {when}")
    return ("; ".join(said) + ".") if said else ""


_ASKED = re.compile(r"^\s*(?:when(?:'s|s)?(?: exactly)?(?: is| does| was)|what (?:day|date)(?: is| does| was)?|"
                    r"what day of the week is|which day is)\b"
                    r"(?P<rest>.+?)\s*\??\s*$", re.I)


def reply(context, words: str, today: Optional[date] = None) -> Optional[str]:
    """"When is Thanksgiving?", "What day is Easter next year?", "What date is Memorial Day in 2027?": the date, its
    weekday and how far off; None for anything else, or a holiday his country doesn't keep.
    Only the holiday itself, with a year or a country ("in Canada") at most; a past one is "was".
    "Thanksgiving day", "when exactly", "of the week" and "weekend" still name it; "when was" is the last one."""
    found = _ASKED.match(str(words or ""))
    if not found:
        return None
    from core.region import country_of

    try:
        country = country_of(context) if context is not None else "US"
    except Exception:  # noqa: BLE001 - no settings: the default
        country = "US"
    rest = found.group("rest")
    if re.search(r"\bin canada\b", rest, re.I):
        country = "CA"
    elif re.search(r"\bin the (?:us|usa|states|united states)\b", rest, re.I):
        country = "US"
    # only the holiday itself, with a year or a country at most: "when is the christmas concert?", "when is my labor
    # day party?" and "when should I start the easter ham?" are his own things (the Fable review)
    bare = re.sub(r"\b(?:this|next|last) year\b|\bin \d{4}\b|\b\d{4}\b|\bin (?:canada|the (?:us|usa|states|united "
                  r"states))\b|\bof the week\b|\b(?:is|this|on|fall|falls|land|lands|come|comes|be|the|exactly|again|"
                  r"weekend|was)\b|[?.,!]", " ", rest, flags=re.I)  # never "year": it's in "new year's"
    name = named(bare, country)
    if name is None:
        return None
    pattern = HOLIDAYS[name][0]
    left = re.sub(rf"\b(?:{pattern})\b", " ", " ".join(bare.lower().replace("\u2019", "'").split()))
    if re.sub(r"\bday\b", " ", left).strip():  # "thanksgiving day" is Thanksgiving
        return None
    today = today or date.today()
    year_said = re.search(r"\b(20\d\d)\b", found.group("rest"))
    if year_said:
        year = int(year_said.group(1))
    elif re.search(r"\bnext year\b", found.group("rest"), re.I):
        year = today.year + 1
    elif re.search(r"\blast year\b", found.group("rest"), re.I):
        year = today.year - 1
    elif re.match(r"\s*(?:when was|what (?:day|date) was)\b", str(words or ""), re.I):
        year = today.year if day_of(name, today.year) <= today else today.year - 1  # "when was labor day?"
    else:
        year = today.year if day_of(name, today.year) >= today or re.search(r"\bthis year\b", found.group("rest"),
                                                                          re.I) else today.year + 1
    when = day_of(name, year)
    days = (when - today).days
    away = ("today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days" if days > 0
            else f"{-days} days ago")
    label = name.split(" (")[0]
    verb = "was" if days < 0 else "is"
    return f"{label} {verb} {when:%A}, {when:%B} {when.day}, {when.year} ({away})."
