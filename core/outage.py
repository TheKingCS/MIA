"""
core.outage
=============

The power's out (Jarvis brainstorm, round 10): a clock from when it went out, and what that means for him right now,
worked out in code from the hours gone and his own records. Survival at home, offline: it needs nothing but this PC
on a battery, or the phone.

**The clock** (`start`, `end`, `since`): "the power went out" (or "...at 6 am") starts it, kept as a device setting
(`outage.since`); "the power's back" ends it and says how long it was and what that means for the food.

**What it means now** (`status`), each line only when it applies:
- *The fridge and the freezer* (FoodSafety.gov's guidance): a closed fridge keeps food safe about 4 hours; a full
  freezer about 48 hours, a half-full one about 24, kept shut. Said as time left, or past it.
- *The generator*: how long his fuel lasts (core/power_ready.say), from his inventory and his settings.
- *The fish*: with the greenhouse taken over (core/greenhouse_link.py), its tank's air pump is the first thing to
  power: fish can suffocate within hours without aeration.
- *The hens*: with a flock, fresh water, which a heated waterer won't keep from freezing now.
- *Water*: with a well pump among his assets, it needs power: fill jugs and the tub while the pressure lasts.
- *Afterwards* (`end`): food from the fridge (meat, poultry, seafood, milk, eggs, leftovers) that sat above 40 F for
  over 2 hours goes; freezer food that still has ice crystals or is 40 F or colder can be refrozen.

Facts and times are put together here; the model only phrases them, and never guesses a time he didn't say.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

KEY = "outage.since"
FRIDGE_HOURS = 4
FREEZER_FULL_HOURS = 48
FREEZER_HALF_HOURS = 24
AFTER = ("When it's back: fridge food (meat, poultry, seafood, milk, eggs, leftovers) that sat above 40 F for more than "
         "2 hours goes, and don't taste to check. Freezer food that still has ice crystals or is 40 F or colder can be "
         "refrozen.")
_AT = re.compile(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", re.I)
_AGO = re.compile(r"\b(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?)\s+ago\b", re.I)


def when_said(text: str, now: datetime) -> Optional[datetime]:
    """Pure logic. When he said it went out: "at 6 am", "at 18:30", "2 hours ago"; None when he didn't say (then it's
    now). A time later than now is taken as yesterday's."""
    text = text or ""
    ago = _AGO.search(text)
    if ago:
        n = float(ago.group(1))
        return now - (timedelta(hours=n) if ago.group(2).lower().startswith("h") else timedelta(minutes=n))
    at = _AT.search(text)
    if not at:
        return None
    hour, minute, half = int(at.group(1)), int(at.group(2) or 0), (at.group(3) or "").lower().replace(".", "")
    if half == "pm" and hour < 12:
        hour += 12
    if half == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    then = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return then - timedelta(days=1) if then > now else then


def since(context) -> Optional[datetime]:
    """When the power went out, or None when it isn't out."""
    config = getattr(context, "config", None)
    raw = config.get(KEY) if config is not None else None
    try:
        return datetime.fromisoformat(str(raw)) if raw else None
    except ValueError:
        return None


def _span(hours: float) -> str:
    """Pure logic. 3.17 -> "3 h 10 min"; under an hour in minutes."""
    minutes = max(0, int(round(hours * 60)))
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60} h" + (f" {minutes % 60} min" if minutes % 60 else "")


def food_lines(hours: float) -> list[str]:
    """Pure logic. The fridge and freezer after `hours` without power, kept closed."""
    fridge = (f"The fridge keeps food safe about {_span(FRIDGE_HOURS - hours)} more if you keep it closed."
              if hours < FRIDGE_HOURS else
              "The fridge is past its 4 safe hours: its perishables (meat, milk, eggs, leftovers) are no longer safe.")
    if hours < FREEZER_HALF_HOURS:
        freezer = (f"The freezer, kept shut, has about {_span(FREEZER_FULL_HOURS - hours)} if it's full, "
                   f"{_span(FREEZER_HALF_HOURS - hours)} if it's half full.")
    elif hours < FREEZER_FULL_HOURS:
        freezer = (f"A half-full freezer is past its 24 hours; a full one has about {_span(FREEZER_FULL_HOURS - hours)} "
                   "more, kept shut. Check for ice crystals.")
    else:
        freezer = "The freezer is past 48 hours: check each item for ice crystals or 40 F and colder before refreezing."
    return [fridge, freezer]


def _has_well_pump(context) -> bool:
    """Whether a well pump is among his maintenance assets."""
    maintenance = getattr(context, "maintenance", None)
    try:
        return any(re.search(r"\bwell\b", a.name or "", re.I) for a in (maintenance.all_assets() if maintenance else []))
    except Exception:  # noqa: BLE001 - a store that can't be read leaves the line out
        return False


def status(context, now: Optional[datetime] = None) -> str:
    """What the outage means now (see the module's opening), or that the power isn't out."""
    from core import power_ready

    now = now or datetime.now()
    start = since(context)
    if start is None:
        return "As far as I know the power's on. If it goes out, tell me \"the power went out\" and I'll keep the clock."
    hours = max(0.0, (now - start).total_seconds() / 3600)
    lines = [f"The power's been out {_span(hours)} (since {start:%H:%M}{'' if start.date() == now.date() else f' on {start:%b} {start.day}'})."]
    lines += food_lines(hours)
    lines.append(power_ready.say(context))
    link = getattr(context, "greenhouse_link", None)
    if link is not None and getattr(link, "taken_over", False):
        lines.append("Power the fish tank's air pump first: fish can suffocate within hours without aeration.")
    flock = getattr(context, "flock", None)
    if flock is not None and getattr(flock, "flocks", None):
        lines.append("The hens need fresh water; a heated waterer won't keep it from freezing now.")
    if _has_well_pump(context):
        lines.append("The well pump needs power: fill jugs and the tub while the pressure lasts.")
    return " ".join(lines)


def start(context, text: str = "", now: Optional[datetime] = None) -> str:
    """Starts the clock (from when he said, else now) and says what it means; "" never: always a sentence."""
    now = now or datetime.now()
    at = when_said(text, now) or now
    context.config.set(KEY, at.isoformat(timespec="minutes"))
    context.config.save()
    return status(context, now)


def end(context, now: Optional[datetime] = None) -> str:
    """Stops the clock and says how long it was and what that means for the food."""
    now = now or datetime.now()
    start_at = since(context)
    if start_at is None:
        return "I didn't have the power as out. Good that it's on."
    hours = max(0.0, (now - start_at).total_seconds() / 3600)
    context.config.set(KEY, "")
    context.config.save()
    fridge = ("The fridge stayed inside its 4 safe hours if it was kept closed." if hours < FRIDGE_HOURS else
              "The fridge went past its 4 safe hours.")
    return f"The power was out {_span(hours)}. {fridge} {AFTER}"
