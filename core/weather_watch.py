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
- **The house's pipes** (always: everyone has some): a low of 20°F (-7°C) or under, when pipes in unheated spots
  can freeze: let a faucet on an outside wall drip, open the cabinets under the sinks, unhook the hoses, keep the heat
  at 55°F (13°C) or above; and with a well pump among his assets (core/outage._has_well_pump), keep its pump house or
  pressure tank from freezing. Said when he asks only: the daily message leaves it out (`ASKED_ONLY`), since a new
  kind of unprompted message is his to decide.
- **A build in progress** (a confirmed Planner build with a mission still active): rain RAIN_LIKELY% likely or more
  tomorrow (or, where the forecast gives no chance, its words say rain, showers, drizzle or thunder), plan the outside
  steps around it and cover what's out.

The night that matters is tonight: the forecast's low for tomorrow (its coldest hour is early tomorrow morning). The
heat is today's high and tomorrow's.

**Where it shows:** `watch(context)` for the tool `weather_for_my_plans` ("will it frost tonight?") and the Home
weather card's lines (core/web_surfaces.py); `offer(context, now)` is the daily check's message through the
communication gate, TIMELY (it's useful within hours), once per concern per day. Without a town, a forecast or
anything planted or kept, there's nothing to say.

"Should I water the garden today?" (`watering`, `say_watering`) is read from the same forecast: rain now or likely
tomorrow says hold off, a hot dry day says water deeply in the morning, and every answer ends with the soil check.
His rain gauge's readings ("I got half an inch of rain", `log_rain`) are kept in the data logger (`RAIN_SERIES`, in
inches), so the watering answer counts the week's real rain, not only the forecast.
"""

from __future__ import annotations

import re
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
RAIN_LIKELY = 60  # percent chance of rain tomorrow worth a word to a build in progress
PIPES_FREEZE = 20  # pipes in unheated spots can freeze at about this low
ASKED_ONLY = ("pipes",)  # concerns said when he asks, never as the daily message (his say)


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


def concerns(forecast: dict, growing: dict, birds: int, builds: tuple = (), well: bool = False) -> list[dict]:
    """Pure logic. What tonight's and the next days' weather means for what he's growing, keeping and building, and
    for the house's pipes: each {kind, text}, the most pressing first. `forecast` is core/weather.card's (high, low,
    unit, tomorrow); `builds` the titles of builds in progress (rain from tomorrow's chance, or its words when no
    chance is given); `well` whether he has a well pump; [] without a forecast."""
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
    if cold <= PIPES_FREEZE:
        metric = "C" in unit
        out.append({"kind": "pipes", "text": (
            f"Cold enough tonight to freeze pipes (a low of {said_low}; pipes in unheated spots can freeze at about "
            f"{'-7°C' if metric else '20°F'}): let a faucet on an outside wall drip, open the cabinet doors under the "
            f"sinks, unhook the garden hoses, and keep the heat at {'13°C' if metric else '55°F'} or above."
            + (" Keep the well's pump house or pressure tank from freezing too: a heat lamp or heat tape made for it."
               if well else ""))})
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
    rain = tomorrow.get("rain")
    words = str(tomorrow.get("words") or "").lower()
    wet = rain >= RAIN_LIKELY if rain is not None else any(w in words for w in ("rain", "shower", "thunder", "drizzle"))
    if builds and wet:
        chance = f"Rain is {rain}% likely tomorrow" if rain is not None else f"Tomorrow's forecast says {words}"
        out.append({"kind": "rain_build", "text": (
            f"{chance}: for {', '.join(builds)}, "
            "keep the outside steps (concrete, roofing, paint, framing) for a dry day and cover lumber and tools left "
            "out.")})
    return out


def _builds(context) -> tuple:
    """The titles of confirmed Planner builds with a mission still active."""
    book, missions = getattr(context, "project_plans", None), getattr(context, "missions", None)
    if book is None or missions is None:
        return ()
    active = {m.mission_id for m in missions.all_missions() if m.status == "active"}
    return tuple(p.title for p in book.listed()
                 if p.kind == "build" and p.status == "confirmed" and active.intersection(p.mission_ids))


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
    """What the weather means for his plans right now (`concerns`: the garden, the flock, builds in progress, the
    pipes and his well, `_well`), from the forecast core/weather.py keeps (or the one given); [] when there's no
    forecast yet or nothing it touches."""
    from core import weather

    today = today or date.today()
    if forecast is None:
        forecast = weather.card(context, fetch)
    if not forecast or not forecast.get("text"):
        return []
    try:
        builds = _builds(context)
    except Exception:  # noqa: BLE001 - a plan or mission that can't be read never stops the rest
        log.exception("Weather watch: the builds couldn't be read")
        builds = ()
    return concerns(forecast, _growing(context, today), _birds(context), builds, _well(context))


def _well(context) -> bool:
    """Whether he has a well pump (core/outage._has_well_pump); False when that can't be read."""
    from core.outage import _has_well_pump

    try:
        return _has_well_pump(context)
    except Exception:  # noqa: BLE001 - assets that can't be read leave the well line out
        return False


def say(context) -> str:
    """For "will it frost tonight?", "will the pipes freeze?" and "what does the weather mean for my garden?": each
    concern, or what she checked and found fine."""
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
    """The daily check's messages: one per concern per day (frost, a hard freeze, seedlings, the hens, rain on a
    build; never an `ASKED_ONLY` one, the pipes), TIMELY (it matters within hours), through the gate."""
    from core.communication_gate import TIMELY, Candidate

    day = now.date()
    found = watch(context, day, fetch)
    titles = {"frost": "Frost tonight", "hard_freeze": "A hard freeze tonight", "hardening": "Bring the seedlings in",
              "flock_heat": "Hot for the hens", "flock_water": "The hens' water may freeze",
              "rain_build": "Rain tomorrow"}
    return [Candidate(topic="weather_watch", title=titles.get(c["kind"], "The weather and your plans"),
                      message=c["text"], urgency=TIMELY, source="system",
                      fingerprint=f"weather-{c['kind']}-{day.isoformat()}",
                      expires=(datetime.combine(day, datetime.min.time()) + timedelta(days=1, hours=9)).isoformat())
            for c in found if c["kind"] not in ASKED_ONLY]


HOT_F, HOT_C = 85, 29  # a high this warm dries beds out fast
_WET_WORDS = ("rain", "shower", "drizzle", "thunder")


def watering(forecast: dict, in_ground: list) -> str:
    """Pure logic. Whether to water the garden today, from the forecast core/weather.py keeps (today's words, the
    day's and the current, and high; tomorrow's chance of rain, or its words when no chance is given) and what's in
    the ground (`crops_now`): freezing or snow says no watering; rain now or likely tomorrow says hold off; a hot day
    says water deeply in the morning; rain is never said as "none" when it isn't known; nothing planted out is said
    first. Ends with the soil check, the one sure test."""
    soil = "Push a finger in 1 to 2 inches: water if it's dry there, and aim for about an inch a week, rain included."
    growing = f" for the {_names([n for n, _f in in_ground])}" if in_ground else ""
    if not forecast or forecast.get("high") is None or not forecast.get("unit"):
        return f"I don't have today's forecast. {soil}"
    unit = forecast["unit"]
    words = f"{forecast.get('words') or ''} {forecast.get('today_words') or ''} {forecast.get('text') or ''}".lower()
    tomorrow = forecast.get("tomorrow")
    rain = (tomorrow or {}).get("rain")
    later = str((tomorrow or {}).get("words") or "").lower()
    if _f(forecast["high"], unit) <= 32 or any(w in words for w in ("snow", "sleet", "freezing")):
        return "No watering today: it's freezing or snowing, and frozen ground can't take it in."
    if not in_ground:
        lead = "Nothing's planted out that I know of. "
    else:
        lead = ""
    if any(w in words for w in _WET_WORDS):
        return f"{lead}It's wet today, so you can likely skip watering{growing}. {soil}"
    wet_tomorrow = rain >= RAIN_LIKELY if rain is not None else any(w in later for w in _WET_WORDS)
    if wet_tomorrow:
        chance = f"Rain is {rain}% likely tomorrow" if rain is not None else f"Tomorrow's forecast says {later}"
        return f"{lead}{chance}, so hold off{growing} unless the soil's dry or the plants are wilting. {soil}"
    hot = forecast["high"] >= (HOT_F if unit == "°F" else HOT_C)
    chance = f"only a {rain}% chance of rain tomorrow" if rain is not None else ""
    if hot:
        return (f"{lead}It's hot today ({forecast['high']}{unit}){', ' + chance if chance else ''}, so water"
                f"{growing} deeply, early in the morning, at the base of the plants. {soil}")
    return f"{lead}{(chance[0].upper() + chance[1:] + '. ') if chance else ''}{soil}"


def say_watering(context, today: Optional[date] = None) -> str:
    """For "should I water the garden today?": `watering`, from the kept forecast and what his confirmed garden plans
    have in the ground, led by the inches his rain gauge logged this week (`rain_this_week`) against the inch a week
    the garden wants (after "nothing's planted out"; with enough rain on a hot day, only the soil decides, never "skip
    it" then "water deeply"); while the forecast is still coming, says so and to ask again."""
    from core import weather

    today = today or date.today()
    got = weather.card(context)
    if got.get("set"):
        return ("I don't know your town for the forecast yet. Push a finger in 1 to 2 inches: water if it's dry there, "
                "about an inch a week, rain included.")
    if got.get("loading"):
        return f"I'm getting the weather for {got.get('place') or 'your town'}; ask me again in a moment."
    try:
        in_ground = _growing(context, today).get("in_ground", [])
    except Exception:  # noqa: BLE001 - plans that can't be read never stop the answer
        log.exception("Watering: the garden plans couldn't be read")
        in_ground = []
    said = watering(got if got.get("text") else {}, in_ground)
    gauge = rain_this_week(context, today)
    if gauge is None or said.startswith("No watering today"):
        return said
    lead = "Nothing's planted out that I know of. "
    rest = said[len(lead):] if said.startswith(lead) else said
    first = lead if said.startswith(lead) else ""
    if gauge >= INCH_A_WEEK:
        if "It's hot today" in rest:  # enough rain, but a hot day dries beds: only the soil decides
            line = f"Your gauge has {gauge:g} inches this week, enough for the week, so water only if the soil's dry. "
            return first + line + rest[rest.index("Push a finger"):]
        line = f"Your gauge has {gauge:g} inches this week, the inch a week the garden wants, so you can likely skip it. "
    else:
        short = round(INCH_A_WEEK - gauge, 2)
        line = f"Your gauge has {gauge:g} inches this week, about {short:g} inch short of the garden's inch. "
    return first + line + rest


RAIN_SERIES = "weather:rain_gauge"  # his rain gauge, in inches (the data logger's series)
INCH_A_WEEK = 1.0  # the garden's usual need, rain included
_UNIT = r"(?:\"|in\b|inch(?:es)?|mm|millimet(?:er|re)s?|cm|centimet(?:er|re)s?)"
_MIXED = re.compile(r"(\d+)\s+(\d+)/(\d+)\s*(?:of an?\s+)?" + _UNIT, re.I)  # "1 1/2 inches"
_FRACTION = re.compile(r"(?<![\d/])(\d+)/(\d+)\s*(?:of an?\s+)?" + _UNIT, re.I)  # "1/2 inch", "6/10 of an inch"
_DECIMAL = re.compile(r"(\d+(?:\.\d+)?|\.\d+)\s*" + _UNIT, re.I)
_BARE = re.compile(r"(?<![\d/])(\d*\.\d+|\d+)(?![\d/])")
# Words, the longest first so "a quarter of an inch" is never "an inch"
_RAIN_WORDS = tuple(sorted((
    ("an inch and a half", 1.5), ("inch and a half", 1.5), ("an inch and a quarter", 1.25),
    ("three quarters of an inch", 0.75), ("three quarters inch", 0.75), ("half an inch", 0.5), ("half inch", 0.5),
    ("a quarter of an inch", 0.25), ("quarter of an inch", 0.25), ("a quarter inch", 0.25), ("quarter inch", 0.25),
    ("a tenth of an inch", 0.1), ("tenth of an inch", 0.1), ("two inches", 2.0), ("an inch", 1.0), ("a trace", 0.0),
), key=lambda w: -len(w[0])))


def _unit_factor(text: str) -> float:
    """Pure logic. Inches per one of the unit at the end of `text`."""
    unit = text.lower()
    if re.search(r"mm|millimet", unit):
        return 1 / 25.4
    if re.search(r"cm|centimet", unit):
        return 1 / 2.54
    return 1.0


def rain_inches(said: str) -> Optional[float]:
    """Pure logic. Rainfall he read off the gauge, in inches: "0.6 in", "1 1/2 inches", "6/10 of an inch", "half an
    inch", "a quarter of an inch", "15 mm", or a bare number when it's the only one ("gauge says .3"); None when it
    says no amount."""
    text = " ".join(str(said or "").lower().split())
    for pattern in (_MIXED, _FRACTION):  # written fractions first: "6/10 of an inch" is never "an inch"
        m = pattern.search(text)
        if m:
            nums = [float(g) for g in m.groups()]
            value = nums[0] + nums[1] / nums[2] if len(nums) == 3 else nums[0] / nums[1]
            return round(value * _unit_factor(m.group(0)), 2)
    for words, value in _RAIN_WORDS:
        if words in text:
            return value
    m = _DECIMAL.search(text)
    if m:
        return round(float(m.group(1)) * _unit_factor(m.group(0)), 2)
    bare = _BARE.findall(text)
    return float(bare[0]) if len(bare) == 1 else None


def rain_this_week(context, today: Optional[date] = None) -> Optional[float]:
    """The inches his gauge logged over the last seven days (today counting), or None when nothing's logged then."""
    today = today or date.today()
    logger = getattr(context, "data_logger", None)
    if logger is None:
        return None
    since = (today - timedelta(days=6)).isoformat()
    found = [r.value for r in logger.readings_for(RAIN_SERIES) if str(r.timestamp)[:10] >= since]
    return round(sum(found), 2) if found else None
