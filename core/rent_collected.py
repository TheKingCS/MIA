"""
core.rent_collected
=====================

"How much rent did I collect this month?" (Jarvis brainstorm, round 12; his rentals): his rental income by property
from his records (core/real_estate_manager.py income_for_property), for this month, last month, this year or a month
he names (`span_of`, a follow-up's own words first), with the total, and the properties that paid in the months
before but have nothing logged yet in this one. Read-only; nothing guessed. Before, only recording rent had a tool,
and "how much rent did I collect?" went to the month's money plan, which said it didn't know (live check through the
whole turn, 2026-11-24).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")


def span_of(words: str, today: date) -> tuple:
    """Pure logic. (label, first day, last day) his words ask about: last month, this year, a month by name (the
    latest one not after today), else this month; only a follow-up's own words count (before its " (after: ...)")."""
    own = str(words or "").lower().split(" (after:")[0]
    first_of_month = today.replace(day=1)
    if "last month" in own:
        end = first_of_month - timedelta(days=1)
        return f"in {end:%B}", end.replace(day=1), end
    if "this year" in own or "so far this year" in own:
        return f"so far in {today.year}", date(today.year, 1, 1), today
    for n, name in enumerate(MONTHS, 1):
        if re.search(rf"\b{name}\b", own):
            year = today.year if n <= today.month else today.year - 1
            start = date(year, n, 1)
            end = (date(year + (n == 12), n % 12 + 1, 1) - timedelta(days=1))
            return f"in {start:%B %Y}", start, min(end, today)
    return "so far this month", first_of_month, today


def say(context, words: str = "", today: Optional[date] = None) -> str:
    """The answer (see the module's opening)."""
    from core.region import money

    today = today or date.today()
    estate = getattr(context, "real_estate", None)
    props = list(estate.all_properties()) if estate is not None else []
    if not props:
        return "No properties in MIA yet: add one in Real Estate and log its rent as it comes in."
    label, first, last = span_of(words, today)
    lines, total, quiet = [], 0.0, []
    for p in props:
        got = sum(float(e.amount or 0) for e in estate.income_for_property(p.property_id, first.isoformat(),
                                                                            last.isoformat()))
        if got:
            lines.append(f"{p.name} {money(got)}")
            total += got
        elif label == "so far this month":
            before = estate.income_for_property(p.property_id, (first - timedelta(days=92)).isoformat(),
                                                (first - timedelta(days=1)).isoformat())
            if before:
                quiet.append(p.name)
    if not lines:
        out = f"No rent logged {label}."
    else:
        out = f"Rent collected {label}: {money(total)}" + (f" ({'; '.join(lines)})" if len(lines) > 1 else
                                                         f", from {lines[0]}") + "."
    if quiet:
        out += f" Nothing logged yet this month from {', '.join(quiet)}, which paid in the months before."
    return out


def _tool(context, arguments: dict) -> str:
    """Tool rent_collected: `say` on his words."""
    return say(context, str(arguments.get("question", "") or ""))


def register_rent_collected_actions(registry) -> None:
    """Registers rent_collected (its words its prompt_arg, so it's answered in code)."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="rent_collected", domain="real_estate",
        description="How much rent he collected from his rentals this month, last month, this year or in a month he "
                    "names, by property, and which haven't paid yet this month. Logging rent is record_rental_income.",
        parameters={"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                    "required": []},
        handler=_tool, prompt_arg="question",
        trigger_phrases=("rent did i collect", "rent have i collected", "rent came in", "rent collected",
                         "rental income this", "rental income last", "how much rent", "who paid rent",
                         "paid their rent", "rent this month", "rent last month"),
        subjects=("rent", "rental"),
    ))
