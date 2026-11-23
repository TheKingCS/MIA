"""
core.weather_watch
====================

The forecast read against what he's actually got going (brainstorm 2.2, `docs/future/JARVIS_BRAINSTORM.md`; Zac,
2026-11-23: "aware"): a frost tonight against the crops his confirmed garden plans have in the ground, seedlings out
hardening off on a cold night, heat and a freezing waterer against his flock. Worked out in code from his records and
the forecast (core/weather.py); the model only says it.

**What counts** (`concerns`), each with what to do:

- **Crops in the ground** (`crops_now`): a confirmed garden plan's crops between their day out (transplant or sow,
  core/garden_plans.schedule from his frost dates) and three weeks past first harvest. Tender ones at a low of
  34°F (1°C) or under (the National Weather Service's frost advisory starts at 36°F, and frost forms on plants before
  the air reaches freezing); half-hardy ones at 28°F (-2°C) or under (a hard freeze). Hardy crops take it.
- **Seedlings hardening off** (between their harden-off day and their day out): a low of 45°F (7°C) or under, bring
  them in for the night.
- **The flock** (any flock with birds): a high of 90°F (32°C) or over, shade, cool water and air; a low of 32°F
  (0°C) or under, the waterer may freeze by morning.

The night that matters is tonight: the forecast's low for tomorrow (its coldest hour is early tomorrow morning). The
heat is today's high and tomorrow's.

**Where it shows:** `watch(context)` for the tool `weather_for_my_plans` ("will it frost tonight?") and the Home
weather card's lines (core/web_surfaces.py); `offer(context, now)` is the daily check's message through the
communication gate, TIMELY (it's useful within hours), once per concern per day. Without a town, a forecast or
anything planted or kept, there's nothing to say.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

# In °F; converted for a Celsius forecast (`_f`).
FROST_TENDER = 34
FREEZE_HALF_HARDY = 28
HARDENING_COLD = 45
FLOCK_HEAT = 90
WATER_FREEZE = 32
HARVEST_WEEKS = 3  # a crop is still in the ground this long past its first harvest


def _f(value: float, unit: str) -> float:
    """Pure logic. A forecast temperature in °F (it is one already, or it's °C)."""
    return float(value) if unit == "°F" else float(value) * 9 / 5 + 32


def crops_now(plans: list, today: date) -> dict:
    """Pure logic. From confirmed garden plans: {"in_ground": [(name, frost)], "hardening": [name]} on this day, each
    name once (several plans may hold the same crop)."""
    from core.garden_plans import CROPS, parse_day, schedule

    ground: dict = {}
    hardening: list = []
    for plan in plans:
        if getattr(plan, "kind", "") != "garden" or getattr(plan, "status", "") != "confirmed":
            continue
        last = parse_day(plan.last_frost, today.year)
        if last is None:
            continue
        if (last - today).days > 300:  # "April 20" read for this year, but this garden's spring was last year's
            last = last.replace(year=last.year - 1) if not (last.month == 2 and last.day == 29) else last
        for item in plan.crops:
            crop = CROPS.get(str(item.get("crop") if isinstance(item, dict) else item))
            if crop is None:
                continue
            when = schedule(crop, last)
            if when["out"] <= today <= when["harvest"] + timedelta(weeks=HARVEST_WEEKS):
                ground.setdefault(crop.name, crop.frost)
            elif when["harden_off"] is not None and when["harden_off"] <= today < when["out"]:
                if crop.name not in hardening:
                    hardening.append(crop.name)
    return {"in_ground": sorted(ground.items()), "hardening": hardening}


def _names(names: list) -> str:
    """Pure logic. "tomatoes, peppers and basil"."""
    names = [n.lower() for n in names]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def concerns(forecast: dict, growing: dict, birds: int) -> list[dict]:
    """Pure logic. What tonight's and the next days' weather means for what he's growing and keeping: each
    {kind, text}, the most pressing first. `forecast` is core/weather.card's (high, low, unit, tomorrow); [] without
    one."""
    if not forecast or forecast.get("high") is None or not forecast.get("unit"):
        return []
    unit = forecast["unit"]
    tomorrow = forecast.get("tomorrow") or {}
    night = tomorrow.get("low", forecast.get("low"))  # tonight's coldest is early tomorrow morning
    if night is None:
        return []
    cold = _f(night, unit)
    said_low = f"{round(night)}{unit}"
    out = []
    tender = [n for n, frost in growing.get("in_ground", []) if frost == "tender"]
    half = [n for n, frost in growing.get("in_ground", []) if frost == "half-hardy"]
    if tender and cold <= FROST_TENDER:
        out.append({"kind": "frost", "text": (
            f"Frost is possible tonight (a low of {said_low}): cover the {_names(tender)}, or water the soil in the "
            "afternoon so it holds its warmth; take the covers off in the morning.")})
    if half and cold <= FREEZE_HALF_HARDY:
        out.append({"kind": "hard_freeze", "text": (
            f"A hard freeze tonight (a low of {said_low}) can hurt even the {_names(half)}: cover them too.")})
    if growing.get("hardening") and cold <= HARDENING_COLD:
        out.append({"kind": "hardening", "text": (
            f"Too cold tonight for seedlings hardening off (a low of {said_low}): bring the "
            f"{_names(growing['hardening'])} in for the night.")})
    if birds:
        highs = [h for h in (forecast.get("high"), tomorrow.get("high")) if h is not None]
        hottest = max(highs) if highs else None
        if hottest is not None and _f(hottest, unit) >= FLOCK_HEAT:
            out.append({"kind": "flock_heat", "text": (
                f"Hot for the hens ({round(hottest)}{unit}): shade, cool fresh water in more than one place, and air "
                "through the coop; panting with wings held out means they're too hot.")})
        if cold <= WATER_FREEZE:
            out.append({"kind": "flock_water", "text": (
                f"The hens' water may freeze by morning (a low of {said_low}): a heated base, or fresh water first "
                "thing.")})
    return out


def _growing(context, today: date) -> dict:
    """What his confirmed garden plans have in the ground or hardening off today."""
    book = getattr(context, "project_plans", None)
    if book is None:
        return {"in_ground": [], "hardening": []}
    try:
        return crops_now(book.listed(), today)
    except Exception:  # noqa: BLE001 - a plan that can't be read never stops the rest
        log.exception("Weather watch: the garden plans couldn't be read")
        return {"in_ground": [], "hardening": []}


def _birds(context) -> int:
    """How many birds his flocks have (0 without a flock book)."""
    book = getattr(context, "flock", None)
    return sum(max(0, f.hens) + max(0, f.roosters) for f in getattr(book, "flocks", []) or [])


def watch(context, today: Optional[date] = None, fetch: Optional[Callable[[str], dict]] = None,
          forecast: Optional[dict] = None) -> list[dict]:
    """What the weather means for his plans right now (`concerns`), from the forecast core/weather.py keeps (or the
    one given); [] when there's no forecast yet or nothing it touches."""
    from core import weather

    today = today or date.today()
    if forecast is None:
        forecast = weather.card(context, fetch)
    if not forecast or not forecast.get("text"):
        return []
    return concerns(forecast, _growing(context, today), _birds(context))


def say(context) -> str:
    """For "will it frost tonight?" and "what does the weather mean for my garden?": each concern, or what she
    checked and found fine."""
    from core import weather

    got = weather.card(context)
    if got.get("set"):
        return "I don't know your town yet. Tell me which one, like \"my town is Springfield, Illinois\"."
    if got.get("loading") or not got.get("text"):
        return f"I'm getting the weather for {got.get('place') or 'your town'}; ask me again in a moment."
    found = watch(context, forecast=got)
    if found:
        return " ".join(c["text"] for c in found)
    growing, birds = _growing(context, date.today()), _birds(context)
    if not growing["in_ground"] and not growing["hardening"] and not birds:
        return (weather.say(context) + " Nothing of yours is planted out or kept outside that I know of: a garden "
                "plan confirmed in the Planner, or a flock, and I'll watch the weather for them.")
    return weather.say(context) + " Nothing in it threatens your garden or the flock."


def offer(context, now: datetime, fetch: Optional[Callable[[str], dict]] = None) -> list:
    """The daily check's messages: one per concern per day, TIMELY (it matters within hours), through the gate."""
    from core.communication_gate import TIMELY, Candidate

    day = now.date()
    found = watch(context, day, fetch)
    titles = {"frost": "Frost tonight", "hard_freeze": "A hard freeze tonight", "hardening": "Bring the seedlings in",
              "flock_heat": "Hot for the hens", "flock_water": "The hens' water may freeze"}
    return [Candidate(topic="weather_watch", title=titles.get(c["kind"], "The weather and your plans"),
                      message=c["text"], urgency=TIMELY, source="system",
                      fingerprint=f"weather-{c['kind']}-{day.isoformat()}",
                      expires=(datetime.combine(day, datetime.min.time()) + timedelta(days=1, hours=9)).isoformat())
            for c in found]
