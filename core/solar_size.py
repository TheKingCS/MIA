"""
core.solar_size
=================

"How many solar panels would I need?" (Jarvis brainstorm, round 12; his power, docs/future/SMART_AG_PLAN.md): the
array and battery worked out in code (core/eng_calcs.py `solar_array`), from his own use:

- **The whole house** (`house_kwh_day`): his kWh meter's months (core/utility_bills.kwh_used, the last three with
  readings), else the kWh a month he says ("we use 900 kWh a month"; a bare "900 kWh" is a month's at 100 or more,
  a day's under); a bill in dollars alone can't say kWh, so he's
  asked for the kWh on it.
- **The essentials** (`what` = essentials, core/power_picture.loads): the loads that must keep running, his own or
  the typical ones said as typical, sized off-grid with two days of battery.

"Do I have enough solar?" is about what he has, so it's answered by core/power_picture.say (`HAVE_ENOUGH`), even
when the model brings it here. Peak sun hours: the ones he gives, else 4, said as an assumption (much of the US gets about 4 to 5 a day over a year,
less in winter; NREL's PVWatts gives his own site's). Panels of 400 W unless he names a size. Read-only.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

ESSENTIAL_DAYS = 2  # an off-grid essentials system carries two sunless days
HAVE_ENOUGH = re.compile(r"\b(?:(?:do i have|have i got|is it) enough|is (?:my|the|our) (?:solar|battery)(?: \w+)? "
                         r"enough)\b|\benough solar\b|\bsolar (?:is |be )?enough\b", re.I)


def house_kwh_day(context, today: Optional[date] = None) -> Optional[tuple]:
    """(kWh a day, how many months) from his meter's last three months with readings, or None."""
    from core.utility_bills import _back, kwh_used

    today = today or date.today()
    month = today.strftime("%Y-%m")
    found = []
    for n in range(1, 13):
        used = kwh_used(context, _back(month, n))
        if used:
            found.append(used)
        if len(found) == 3:
            break
    if not found:
        return None
    return round(sum(found) / len(found) / 30.4, 1), len(found)


def _number(words, pattern: str) -> Optional[float]:
    """Pure logic. A number before a unit pattern in his words, or None."""
    got = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*" + pattern, str(words or ""), re.I)
    return float(got.group(1).replace(",", "")) if got else None


def say(context, what: str = "", words: str = "") -> str:
    """The answer (see the module's opening); a question about the solar he has goes to the power picture.
    A follow-up's own words decide its figures and whether it's the house or the essentials."""
    from core import eng_calcs, power_picture

    words = f"{what} {words}"
    if HAVE_ENOUGH.search(words):  # about the solar he has: the power picture's answer (live check 2026-11-24)
        return power_picture.say(context)
    own = words.split(" (after:")[0]  # a follow-up's own words decide; the question it follows fills the rest

    def figure(pattern):
        """A number from the follow-up's own words, else from the whole."""
        found = _number(own, pattern)
        return found if found is not None else _number(words, pattern)

    house = re.compile(r"whole house|the house|whole home", re.I)
    backup = re.compile(r"essential|backup|off.?grid|well pump|freezer|outage|the pumps", re.I)
    essentials = (bool(backup.search(own)) and not house.search(own)) if (house.search(own) or backup.search(own)) \
        else bool(backup.search(words))
    sun = figure(r"(?:peak\s*)?sun\s*hours?")
    panel = figure(r"(?:w|watt)s?\b(?:\s*(?:solar\s*)?panels?)")
    inputs = {"sun": f"{sun:g} h"} if sun else {}
    if panel:
        inputs["panel"] = f"{panel:g} W"
    if essentials:
        rows, mine = power_picture.loads(context)
        daily = sum(r["kwh_day"] for r in rows)
        inputs.update({"daily": f"{daily:g} kWh", "days": str(ESSENTIAL_DAYS)})
        source = (f"your essentials ({daily:.3g} kWh a day: " + ", ".join(r["name"] for r in rows) + ")" if mine else
                  f"typical homestead essentials ({daily:.3g} kWh a day: " + ", ".join(r["name"] for r in rows)
                  + "; tell me yours, like \"the well pump draws 1000 watts for an hour a day\")")
    else:
        month = _number(own, r"kwh\s*(?:a|per|each)?\s*month")
        day = _number(own, r"kwh\s*(?:a|per|each)\s*day")
        if month is None and day is None:  # none in the follow-up's own words: the question it follows
            month = _number(words, r"kwh\s*(?:a|per|each)?\s*month")
            day = _number(words, r"kwh\s*(?:a|per|each)\s*day")
        bare = figure(r"kwh\b")  # the model often passes only "900 kWh": a month's at 100 or more, else a day's
        metered = house_kwh_day(context)
        if not (day or month) and bare:
            month, day = (bare, None) if bare >= 100 else (None, bare)
        if day:
            daily, source = day, f"the {day:g} kWh a day you said"
        elif month:
            daily, source = round(month / 30.4, 1), f"the {month:g} kWh a month you said"
        elif metered:
            daily, source = metered[0], f"your meter's last {metered[1]} month{'s' if metered[1] != 1 else ''}"
        else:
            return ("How much power does the house use? The kWh on your electric bill (\"we use 900 kWh a month\") is "
                    "what I size from; or ask for the essentials only (well pump, freezer, the greenhouse pumps) "
                    "for a backup system.")
        inputs["daily"] = f"{daily:g} kWh"
    try:
        result = eng_calcs.calculate("solar_array", inputs)
    except eng_calcs.CalcError as problem:
        return str(problem)
    sun_said = (f"the {sun:g} peak sun hours you gave" if sun else
                "4 peak sun hours, an assumption: much of the US gets about 4 to 5 a day over a year, less in winter, "
                "and NREL's PVWatts gives your own site's")
    return (f"From {source}, at {sun_said}: {result['said']} " + result["caveat"])


def _tool(context, arguments: dict) -> str:
    """Tool size_solar: `say` with what he asked for and his words."""
    return say(context, str(arguments.get("what", "") or ""), str(arguments.get("question", "") or ""))


def register_solar_size_actions(registry) -> None:
    """Registers size_solar."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="size_solar", domain="power",
        description="Planning solar he doesn't have yet: how many panels to buy and how big a battery, for the whole "
                    "house from his kWh, or for the essentials (well pump, freezer, greenhouse pumps) off-grid, worked "
                    "out in code. \"Do I have enough solar?\" about what he has now is power_picture, not this.",
        parameters={"type": "object", "properties": {
            "what": {"type": "string", "description": "house or essentials"},
            "question": {"type": "string", "description": "his words, with any kWh, sun hours or panel size"}},
            "required": []},
        handler=_tool, trigger_phrases=("how many solar panels", "how many panels", "solar panels would",
                                        "size a solar", "solar array", "solar system for", "panels do i need",
                                        "panels would i need", "go solar", "going solar", "solar setup"),
    ))
