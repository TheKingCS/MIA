"""
core.power_picture
====================

The whole property's power (Zac, 2026-11-24: "will manage ... my power systems"; docs/future/SMART_AG_PLAN.md phase
A3): what has to keep running, how long the battery carries it, what the solar has been making, and the generator's
days on the fuel in his records.

**The essentials** (`loads`): the loads that must not stop, each with its watts and hours a day. His own, set by
voice ("the well pump draws 1000 watts for an hour a day": `set_power_load`, kept as `power.loads`), else the usual
figures for a homestead's (`TYPICAL`: a well pump, the aquaponics air and water pumps, a fridge, a freezer, some
lights), said as typical, never as his.

**The battery** (`power.battery_kwh`, the usable kilowatt-hours, set by voice): how many hours it carries the
essentials with no sun.

**The solar** (core/energy_manager.py): the kilowatt-hours a day his solar sources' readings show over the last 30
days, against what the essentials take. Without readings in kWh it says so.

**The generator** (core/power_ready.py): its days on the fuel in his records, as "how prepared am I?" says it.

Read-only but for the settings he says. Sensor feeds (an inverter, a charge controller) come later (the plan's
phase D); until then the readings are his.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

# The usual essentials on a homestead with an aquaponics greenhouse: (name, watts, hours a day)
TYPICAL = (("well pump", 1000, 1.0), ("aquaponics air pump", 60, 24.0), ("aquaponics water pump", 100, 24.0),
           ("refrigerator", 150, 24.0), ("chest freezer", 80, 24.0), ("lights", 60, 5.0))
LOADS_KEY = "power.loads"  # {name: {"watts", "hours"}}


def loads(context) -> tuple[list[dict], bool]:
    """The essentials: ([{name, watts, hours, kwh_day}], his own?) from `power.loads`, else `TYPICAL`."""
    from core import person_settings

    mine = person_settings.get(context, LOADS_KEY, {}) if getattr(context, "config", None) is not None else {}
    rows = [(n, float(v.get("watts") or 0), float(v.get("hours") or 0)) for n, v in (mine or {}).items()] \
        if isinstance(mine, dict) and mine else list(TYPICAL)
    return ([{"name": n, "watts": w, "hours": h, "kwh_day": round(w * h / 1000, 2)} for n, w, h in rows],
            bool(isinstance(mine, dict) and mine))


def set_load(context, name: str, watts, hours) -> str:
    """Keeps one of his essential loads (watts, hours a day); 0 watts takes it off. Says it back."""
    from core import person_settings

    name = " ".join(str(name or "").lower().split())
    if not name:
        return "Which load: the well pump, the freezer...?"
    try:
        watts = float(watts)
        hours = float(hours) if hours not in (None, "") else 24.0
    except (TypeError, ValueError):
        return f"How many watts does the {name} draw, and how many hours a day does it run?"
    if not 0 <= watts <= 20000 or not 0 < hours <= 24:
        return "Watts should be 0 to 20,000 and hours 1 to 24 a day."
    mine = dict(person_settings.get(context, LOADS_KEY, {}) or {})
    if watts == 0:
        mine.pop(name, None)
        person_settings.put(context, LOADS_KEY, mine)
        return f"Took the {name} off your essentials."
    mine[name] = {"watts": watts, "hours": hours}
    person_settings.put(context, LOADS_KEY, mine)
    return f"Kept: the {name} draws {watts:g} watts for {hours:g} hours a day ({watts * hours / 1000:g} kWh)."


def solar_kwh_day(context, today: date) -> Optional[float]:
    """His solar's kilowatt-hours a day over the last 30 days: one meter a source (never a running or lifetime
    total), each reading by its own unit first (Wh is a thousandth of a kWh), the 30 days' sum over 30; None
    without any."""
    energy = getattr(context, "energy", None)
    if energy is None:
        return None
    since = (today - timedelta(days=29)).isoformat()
    total, found = 0.0, False
    for source in energy.all_energy_sources():
        if source.source_type != "Solar":
            continue
        meters = [m for m in energy.energy_source_meter_names(source.source_id)
                  if not re.search(r"\b(total|lifetime|cumulative)\b", m, re.I)]  # a running total isn't a day's
        for meter in meters[:1]:  # one meter a source: two kWh meters on one array aren't added together
            for r in energy.energy_source_readings(source.source_id, meter):
                if str(r.timestamp)[:10] < since:
                    continue
                unit = (r.unit or meter).lower()  # the reading's own unit first, then the meter's name
                if "kwh" in unit:
                    total += float(r.value)
                elif "wh" in unit:
                    total += float(r.value) / 1000
                else:
                    continue
                found = True
    return round(total / 30, 1) if found else None  # the 30 days' production, a day


def say(context, today: Optional[date] = None) -> str:
    """The power picture in words: the essentials a day, the battery's hours on them, the solar against them, and
    the generator's days on his fuel."""
    from core import person_settings

    today = today or date.today()
    rows, mine = loads(context)
    need = sum(r["kwh_day"] for r in rows)
    parts = [("Your essentials" if mine else "Typical essentials (tell me yours, like \"the well pump draws 1000 watts "
              "for an hour a day\")") + ": " + "; ".join(f"{r['name']} {r['watts']:g} W for {r['hours']:g} h"
                                                     for r in rows)
             + f", about {need:g} kWh a day."]
    battery = person_settings.get(context, "power.battery_kwh", 0) if getattr(context, "config", None) else 0
    if battery:
        parts.append(f"Your {float(battery):g} kWh battery carries them about {float(battery) / need * 24:.0f} hours "
                     "with no sun." if need else "")
    else:
        parts.append("No battery size set: tell me its usable kilowatt-hours, like \"my battery is 10 kWh\".")
    solar = solar_kwh_day(context, today)
    if solar is None:
        parts.append("No solar readings in kWh in the last 30 days, so I can't set the panels against them.")
    else:
        word = "more than" if solar >= need else "less than"
        parts.append(f"Your solar averaged {solar:g} kWh a day over the last 30 days: {word} the essentials take.")
    try:
        from core.power_ready import say as generator

        parts.append(generator(context))
    except Exception:  # noqa: BLE001 - the generator line is one part
        log.exception("The power picture couldn't read the generator")
    parts.append("The greenhouse's own battery and load-shedding are the greenhouse node's; this is the house side.")
    return " ".join(p for p in parts if p)
