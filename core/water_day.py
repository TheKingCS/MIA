"""
core.water_day
================

A day without safe water (Jarvis brainstorm, round 10): the water's off, or there's a boil-water notice. What he has
and how to make water safe, from his own records and the CDC's guidance, offline.

**What he has** (`say`): his drinking water in the pantry as days for the people he plans for
(core/preparedness.water_days, a gallon a person a day), the tanks, barrels and cistern he logs
(core/water_budget.stored: for the animals, flushing and washing, never said as drinkable), and what his hens drink
(a pint a hen a day).

**Making water safe** (`SAFE`, the CDC's guidance for emergencies): a rolling boil for 1 minute (3 minutes above 6,500
feet), cooled before use; or, without a way to boil, unscented household bleach (6 or 8.25%): 8 drops a gallon (6 drops
of 8.25%), stirred, 30 minutes before drinking, doubled if the water is cloudy (after letting it settle and filtering
it through a clean cloth); it should smell faintly of chlorine. A boil-water notice adds: no ice, drinks or
toothbrushing from the tap.

Facts and figures are put together here; the model only phrases them. Read only.
"""

from __future__ import annotations

from typing import Optional

SAFE = ("To make water safe: a rolling boil for 1 minute (3 minutes above 6,500 feet), then let it cool. Without a way "
        "to boil: unscented household bleach, 8 drops a gallon (6 drops if it's 8.25%), stir and wait 30 minutes; "
        "double it if the water is cloudy, after letting it settle and straining it through a clean cloth. It should "
        "smell faintly of chlorine.")
NOTICE = "Under a boil-water notice: no ice, drinks, baby formula or toothbrushing from the tap until it's lifted."
HEN_GAL_A_DAY = 0.125


def _people(context) -> int:
    """The people he plans for (prepared.people, 1 unless he said)."""
    config = getattr(context, "config", None)
    try:
        return max(1, int(config.get("prepared.people", 1) if config is not None else 1))
    except (TypeError, ValueError):
        return 1


def say(context, boil: bool = False) -> str:
    """What he has and what to do (see the module's opening). `boil`: a boil-water notice rather than no water at
    all."""
    from core import preparedness, water_budget

    people = _people(context)
    kitchen = getattr(context, "kitchen", None)
    days, unread = preparedness.water_days(kitchen.all_pantry_items() if kitchen is not None else [], people)
    who = "you" if people == 1 else f"{people} people"
    lines = [NOTICE] if boil else []
    if days > 0:
        lines.append(f"You have about {days:g} days of drinking water for {who}, at a gallon a person a day.")
    else:
        lines.append(f"I don't see drinking water in the pantry: a gallon a person a day is {people} for {who}, "
                     "and fill what you can now if it's still running.")
    if unread:
        lines.append("Some water containers have no size I can read: " + ", ".join(unread[:3]) + ".")
    tanks = [t for t in water_budget.stored(context) if t.get("gallons")]
    if tanks:
        total = sum(t["gallons"] for t in tanks)
        lines.append(f"Your tanks hold about {total:g} gallons ({', '.join(t['tank'] for t in tanks[:4])}): for the "
                     "animals, flushing and washing; to drink it, treat it first.")
    flock = getattr(context, "flock", None)
    hens = sum(max(0, int(f.hens or 0)) for f in (getattr(flock, "flocks", None) or []))
    if hens:
        lines.append(f"Your {hens} hens drink about {hens * HEN_GAL_A_DAY:g} gallons a day.")
    lines.append(SAFE)
    return " ".join(lines)
