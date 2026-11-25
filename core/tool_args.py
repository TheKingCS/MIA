"""
core.tool_args
================

A tool's arguments as he could have said them (the Fable audit, 2026-11-25: the local model fills a tool's details
with placeholders, and about 65 of the tools that write records saved them: a bill named "bill reminders" for $0.00
due "null", a debt's balance set to 0, an alarm at "25:99", a sale of -1 for -1.00). Every tool call goes through
`cleaned` before its handler (core/assistant_actions.AssistantActionRegistry.execute), so a handler sees a detail
he never gave as missing, and asks for it or leaves it, the way it already does for one the model left out.

**What goes** (`cleaned`): a placeholder string ("null", "unknown", "N/A", "TBD", "none", ""), anywhere; and, for a
tool that changes his records, a time that isn't one ("25:99", "null"), and a negative amount, quantity or count. An
update's or a payment's zero ("balance 0", "amount 0") goes too: "change it to nothing" is never how the model says
he paid something off, and a zero there had overwritten real numbers. **What's tidied:** a date said in words
("December 15", "yesterday") becomes its YYYY-MM-DD, by core/budget_manager.read_date. Nothing else is touched:
a word the handler can't read is still the handler's to refuse.
"""

from __future__ import annotations

import re

PLACEHOLDERS = frozenset({"", "null", "none", "nil", "unknown", "n/a", "na", "tbd", "tba", "undefined",
                          "not specified", "unspecified", "not given", "not provided", "-", "--", "?", "none given",
                          "no date", "no time", "not applicable"})
# a count or an amount, never below zero: "-1 gallons", "a sale of -1"
_POSITIVE = re.compile(r"^(?:amount|quantity|qty|count|hours|minutes|duration\w*|gallons|liters|pounds|lbs|weight|"
                       r"length|price|cost|servings|interval_days|days|miles|inches|eggs|jars|target|budget|limit|"
                       r"balance|minimum_payment|payment|value|quantity_on_hand|reading|level|percent)$")
# what an update or a payment never sets to zero on the model's say-so
_NO_ZERO = re.compile(r"^(?:amount|balance|interest_rate|apr|minimum_payment|quantity_on_hand|price|cost|hours|"
                      r"interval_days|budget|limit|target)$")
_TIME = re.compile(r"^(?:noon|midnight|(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap]\.?m\.?)?)$", re.I)


def is_placeholder(value) -> bool:
    """Pure logic. Whether a value is a placeholder, not something he said ("null", "N/A", "unknown", "")."""
    return isinstance(value, str) and " ".join(value.lower().split()).strip(" .") in PLACEHOLDERS


def a_time(value) -> bool:
    """Pure logic. Whether a value reads as a time of day ("6:30", "7pm", "noon", "18:00"); never "25:99"."""
    found = _TIME.match(" ".join(str(value or "").split()))
    if not found:
        return False
    if found.group("h") is None:
        return True
    hour, minute = int(found.group("h")), int(found.group("m") or 0)
    return minute < 60 and (hour < 24 if not found.group("ap") else 1 <= hour <= 12)


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


def cleaned(name: str, arguments: dict, changes: bool = True) -> dict:
    """Pure logic but for today's date. `arguments` without a placeholder, and, for a tool that changes his records
    (`changes`), without a time that isn't one, a negative amount or count, or an update's or payment's zero; a date
    in words as YYYY-MM-DD (see the module's opening)."""
    if not isinstance(arguments, dict):
        return arguments
    out = {}
    updating = bool(re.match(r"(?:update|change|edit|set|mark|record_debt_payment|move)", str(name or "")))
    for key, value in arguments.items():
        if is_placeholder(value):
            continue
        k = str(key).lower()
        if changes:
            if (k == "time" or k.endswith("_time")) and isinstance(value, str) and not a_time(value):
                continue  # "25:99" or a date passed as the time: the handler asks for one
            number = _number(value) if _POSITIVE.match(k) or _NO_ZERO.match(k) else None
            if number is not None and number < 0:
                continue
            if number == 0 and updating and _NO_ZERO.match(k):
                continue
            if (k == "date" or k.endswith("_date") or k in ("due", "start", "end")) and isinstance(value, str):
                from core.budget_manager import read_date

                value = read_date(value) or value  # a word the handler can't read stays its to refuse
        out[key] = value
    return out
