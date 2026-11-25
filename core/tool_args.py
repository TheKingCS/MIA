"""
core.tool_args
================

A tool's arguments as he could have said them (the Fable audit, 2026-11-25: the local model fills a tool's details
with placeholders, and about 65 of the tools that write records saved them: a bill named "bill reminders" for $0.00
due "null", a debt's balance set to 0, an alarm at "25:99", a sale of -1 for -1.00). Every tool call goes through
`cleaned` before its handler (core/assistant_actions.AssistantActionRegistry.execute), so a handler sees a detail
he never gave as missing, and asks for it or leaves it, the way it already does for one the model left out.

**What goes** (`cleaned`): a placeholder string ("null", "unknown", "N/A", "untitled", ""), anywhere, list items
too; "none" only where it can't be a real value (a date, a time, an amount). For a tool that adds a record, a name
that is only the tool's own subject ("note" for add_note, "a task" for add_task). For a change: a time that isn't
one ("25:99"), a negative amount or count (never a reading or a temperature: -5 °F is real), and an update's zeros
when the model zero-filled two or more at once (one zero alone is real: "I paid it off", "I'm out of plywood").

**What's tidied:** a time said any common way ("0630", "5:30p", "6:30 in the morning", "7 o'clock") becomes HH:MM
on the 24-hour clock; a date in words ("December 15", "yesterday") becomes its YYYY-MM-DD by core/budget_manager.read_date,
and for what's due or coming (a bill, an event, a task) a month and day already past this year is next year's.
Nothing else is touched: a word the handler can't read is still the handler's to refuse.
(Its second Fable audit, 2026-11-25, found the first version blocking real zeros, temperatures and times.)
"""

from __future__ import annotations

import re
from datetime import date

PLACEHOLDERS = frozenset({"", "null", "nil", "unknown", "n/a", "n.a", "n.a.", "undefined", "not specified",
                          "unspecified", "not given", "not provided", "-", "--", "?", "none given", "no date",
                          "no time", "not applicable", "untitled", "unnamed", "<unknown>", "(none)", "(unknown)",
                          "not sure", "not mentioned", "nan", "unknown date", "unknown time", "<none>", "<null>"})
# "none", "tbd" and "na" can be real ("project: none" unlinks a mission; an allergy of None), so only where a value
# must be a date, a time or a number
_EMPTY_THERE = frozenset({"none", "tbd", "tba", "na", "n/a", "no"})
# a count or an amount, never below zero; a reading, a value, a level or a temperature can be
_POSITIVE = re.compile(r"^(?:amount|quantity|qty|count|hours|minutes|duration\w*|gallons|liters|pounds|lbs|weight|"
                       r"length|price|cost|unit_cost|servings|interval_days|days|miles|inches|eggs|jars|budget|limit|"
                       r"balance|minimum_payment|payment|quantity_on_hand|percent|monthly_amount|expected_amount|"
                       r"current_value|watts)$")
_NUMERIC = re.compile(r"^(?:amount|balance|interest_rate|apr|minimum_payment|quantity_on_hand|price|cost|unit_cost|"
                      r"hours|interval_days|budget|limit|target|monthly_amount|expected_amount|current_value|watts)$")
_DUE = re.compile(r"^(?:due|due_date|next_date|date|start|start_date|end|end_date|refill_on|when)$")
_AHEAD = re.compile(r"(?:bill|calendar|event|task|reminder|income_source|trip|expedition|project|appointment|alarm|"
                    r"medication)", re.I)
_NAME_KEYS = frozenset({"name", "title", "label", "item", "what"})
_GENERIC = frozenset({"item", "thing", "entry", "record", "new item", "new entry", "new record", "something"})


def is_placeholder(value, key: str = "") -> bool:
    """Pure logic. Whether a value is a placeholder, not something he said ("null", "N/A", "untitled", ""); "none"
    too where a date, a time or a number goes (`key`)."""
    if not isinstance(value, str):
        return False
    said = " ".join(value.lower().split()).strip(" .")
    if said in PLACEHOLDERS:
        return True
    k = str(key or "").lower()
    return said in _EMPTY_THERE and bool(_DUE.match(k) or k == "time" or k.endswith("_time") or _NUMERIC.match(k))


def a_time(value):
    """Pure logic. A time of day said any common way, as "HH:MM" on the 24-hour clock ("0630", "6.30", "06:30:00",
    "630am", "5:30p", "7 o'clock", "6:30 in the morning", "noon"); None when it isn't one ("25:99", a date)."""
    said = " ".join(str(value or "").lower().split())
    if said in ("noon", "midday"):
        return "12:00"
    if said == "midnight":
        return "00:00"
    part = re.search(r"\s*(?:in the (morning|afternoon|evening)|at night|tonight)$", said)
    if part:
        said = said[:part.start()]
    said = re.sub(r"\s*o'?clock$", "", said)
    found = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2})(?::\d{2})?)?\s*([ap])\.?(?:m\.?)?|(\d{1,2})[:.](\d{2})(?::\d{2})?|"
                         r"(\d{1,2})(\d{2})\s*([ap])\.?(?:m\.?)?|(\d{2})(\d{2})|(\d{1,2})", said)
    if not found:
        return None
    g = found.groups()
    if g[0] is not None:
        hour, minute, ap = int(g[0]), int(g[1] or 0), g[2]
    elif g[3] is not None:
        hour, minute, ap = int(g[3]), int(g[4]), None
    elif g[5] is not None:
        hour, minute, ap = int(g[5]), int(g[6]), g[7]
    elif g[8] is not None:
        hour, minute, ap = int(g[8]), int(g[9]), None
    else:
        hour, minute, ap = int(g[10]), 0, None
    if part and not ap:
        ap = "a" if part.group(1) == "morning" else "p"
    if minute > 59 or (ap and not 1 <= hour <= 12) or (not ap and hour > 23):
        return None
    if ap:  # on the 24-hour clock, the way every store keeps a time
        hour = (0 if hour == 12 else hour) + (12 if ap == "p" else 0)
    return f"{hour:02d}:{minute:02d}"


def _number(value):
    """A number from an int, a float or a numeric string; None otherwise."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None


def _subject(name: str) -> set:
    """Pure logic. What a tool adds, in the words a model would put as its name: add_note's "note",
    add_inventory_item's "inventory item" and "item"."""
    rest = re.sub(r"^(?:add|log|create|new|start|record|set)_", "", str(name or ""))
    words = rest.split("_")
    return {" ".join(words), words[-1], *(w for w in words if len(w) > 3)}


def _ahead(iso: str, said: str) -> str:
    """Pure logic but for today. What's due on a month and day already past this year (no year said) is next
    year's."""
    try:
        day = date.fromisoformat(iso)
    except ValueError:
        return iso
    if day < date.today() and not re.search(r"\b\d{4}\b|\b(?:yesterday|last|ago)\b", said, re.I):
        try:
            return day.replace(year=day.year + 1).isoformat()
        except ValueError:  # Feb 29
            return iso
    return iso


def cleaned(name: str, arguments: dict, changes: bool = True) -> dict:
    """Pure logic but for today's date. `arguments` without a placeholder (list items too), and, for a tool that
    changes his records (`changes`), without a name that's only its own subject, a time that isn't one, a negative
    amount or count, or an update's zeros filled in two or more at once; times and dates tidied (see the module's
    opening)."""
    if not isinstance(arguments, dict):
        return arguments
    out = {}
    updating = bool(re.match(r"(?:update|change|edit|set|mark|move)", str(name or "")))
    zeros = [k for k, v in arguments.items() if _NUMERIC.match(str(k).lower()) and _number(v) == 0]
    zero_filled = updating and len(zeros) >= 2  # "balance 0, interest_rate 0, minimum_payment 0": the model's
    for key, value in arguments.items():
        k = str(key).lower()
        if is_placeholder(value, k):
            continue
        if isinstance(value, list):
            value = [v for v in value if not is_placeholder(v)]
            if not value and arguments[key]:
                continue
        if changes:
            if k in _NAME_KEYS and isinstance(value, str) and str(name).startswith(("add_", "create_", "log_")):
                bare = re.sub(r"^(?:an?|the|new|my)\s+", "", " ".join(value.lower().split()))
                if bare in _subject(name) or bare in _GENERIC:
                    continue  # "note" for add_note: no name at all
            if (k == "time" or k.endswith("_time")) and isinstance(value, str):
                tidy = a_time(value)
                if tidy is None:
                    continue  # "25:99", or a date passed as the time: the handler asks for one
                value = tidy
            number = _number(value) if _POSITIVE.match(k) or _NUMERIC.match(k) else None
            if number is not None and number < 0 and _POSITIVE.match(k):
                continue
            if number == 0 and zero_filled and k in zeros:
                continue
            if _DUE.match(k) and isinstance(value, str):
                from core.budget_manager import read_date

                iso = read_date(value)
                if iso:
                    value = _ahead(iso, value) if _AHEAD.search(str(name)) else iso
        out[key] = value
    return out
