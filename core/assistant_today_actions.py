"""
core.assistant_today_actions
===============================

"What's on today?" (core/today.py, 2026-10-01): everything that needs
the person today, across every app, in one answer. And the rest of the
Dashboard by voice (DEC-0153, 2026-11-11): "what's this week?" (Your
Week, core/today.week_days), "what's the weather?" and "my town is
Springfield, Illinois" (core/weather.py; setting the town goes through the
action `weather.place`, so it's undoable).
"""

from __future__ import annotations

from datetime import date

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.today import describe, today_items


def _action_get_today(context, arguments: dict) -> str:
    """Tool get_today: everything that needs the person today, across every app (core.today)."""
    return describe(today_items(context))


def describe_week(days: list[dict], today: date) -> str:
    """Pure logic. Your Week in a few sentences: each day with something due, and what."""
    from core.web_surfaces import day_label

    parts = []
    for d in days:
        items = d["items"]
        if not items:
            continue
        names = "; ".join(i["title"] for i in items[:6]) + (f"; and {len(items) - 6} more" if len(items) > 6 else "")
        parts.append(f"{day_label(date.fromisoformat(d['date']), today)}: {names}.")
    return " ".join(parts) if parts else "Nothing is due this week."


def _action_get_week(context, arguments: dict) -> str:
    """Tool get_week: what's due each day this week (core.today.week_days), Your Week on the Dashboard."""
    from core.today import week_days

    today = date.today()
    return describe_week(week_days(context, today), today)


def _action_get_weather(context, arguments: dict) -> str:
    """Tool get_weather: the weather in the person's town (core.weather)."""
    from core.weather import say

    return say(context)


def _action_set_weather_place(context, arguments: dict) -> str:
    """Tool set_weather_place: which town the weather is for (the action weather.place, undoable)."""
    from core.actions import ActionError
    from core.weather import _do

    try:
        return _do(context, {"place": str(arguments.get("place") or "")})
    except ActionError as problem:
        return str(problem)


def _action_log_rain(context, arguments: dict) -> str:
    """Rainfall off his gauge, kept in the data logger in inches (core/weather_watch.RAIN_SERIES), dated the day it fell
    when he says ("Saturday"); the same amount again within a day is said, not added twice; a trace isn't counted.
    Said back with the week's total."""
    from core import weather_watch as ww

    from datetime import datetime, timedelta

    from core import hatch_tracker

    inches = ww.rain_inches(str(arguments.get("amount") or ""))
    if inches is None or not 0 <= inches < 30:
        return "How much rain did the gauge show? Say it in inches or millimeters, like \"half an inch\"."
    if inches == 0:
        return "A trace: nothing to count for the garden."
    logger = getattr(context, "data_logger", None)
    if logger is None:
        return "There's no data logger here to keep it in."
    day = hatch_tracker.set_day(str(arguments.get("when") or "today"))
    if day is None:
        return "Which day did it rain?"
    stamp = f"{day}T07:00:00" if day != datetime.now().date().isoformat() else None
    cutoff = (datetime.now() - timedelta(hours=18)).isoformat(timespec="seconds")
    if any(abs(r.value - inches) < 0.005 and str(r.timestamp) >= cutoff for r in logger.readings_for(ww.RAIN_SERIES)):
        return f"I already have {inches:g} inches from the last day; I haven't added it again. Empty the gauge after you read it."
    from core.person_settings import person_id

    logger.add_reading(ww.RAIN_SERIES, inches, unit="in", note="rain gauge", timestamp=stamp,
                       profile_id=person_id(context))
    week = ww.rain_this_week(context)
    return f"Logged {inches:g} inches of rain. That's {week:g} this week." if week else f"Logged {inches:g} inches."


def _action_should_i_water(context, arguments: dict) -> str:
    """Whether to water the garden today, from the forecast and what's in the ground (core/weather_watch.say_watering)."""
    from core import weather_watch

    return weather_watch.say_watering(context)


def _action_weather_for_my_plans(context, arguments: dict) -> str:
    """What the weather means for his garden and flock (core/weather_watch.say)."""
    from core import weather_watch

    return weather_watch.say(context)


def _action_evening_wrap(context, arguments: dict) -> str:
    """The evening wrap, now, on his own clock (core/evening_wrap.wrap, core/clock.now)."""
    from core import clock, evening_wrap

    return evening_wrap.wrap(context, clock.now(context).replace(tzinfo=None)) or \
        "A quiet day, and nothing on tomorrow's list yet."


def _action_how_prepared(context, arguments: dict) -> str:
    """How ready he is: water, what to rotate, what isn't counted (core/preparedness.say)."""
    from core import preparedness

    return preparedness.say(context)


_PREPARED = {  # argument: (setting, lowest, highest, whole number, how it's said)
    "people": ("prepared.people", 1, 20, True, "people"),
    "target_days": ("prepared.target_days", 1, 365, True, "days to plan for"),
    "generator_gph": ("prepared.generator_gph", 0.05, 5.0, False, "generator gallons an hour"),
    "generator_hours": ("prepared.generator_hours", 1, 24, False, "generator hours a day"),
    "firewood_cords": ("prepared.firewood_cords", 0.25, 30, False, "cords of firewood a winter"),
    "roof_sqft": ("water.roof_sqft", 10, 50000, False, "catchment roof square feet"),
    "battery_kwh": ("power.battery_kwh", 0.1, 500, False, "battery kWh"),
}


def _action_set_preparedness(context, arguments: dict) -> str:
    """Sets what "how prepared am I?" counts with: how many people, the target days, and his generator's burn rate,
    hours a day and fuel (core/preparedness.py, core/power_ready.py), and the cords of firewood a winter takes him
    (core/firewood.py), and the roof he catches rain from (core/water_budget.py). A propane rate in pounds an hour
    (`generator_lb_per_hour`, as manuals give it) is turned to gallons; "gas" or "petrol" is gasoline, "LP" propane.
    Each is checked against a sensible range; one out of range is said and not kept. Returns what was set."""
    from core import person_settings
    from core.power_ready import PROPANE_LB_A_GALLON, SAID_AS

    arguments = dict(arguments or {})
    said, problems = [], []
    if arguments.get("generator_lb_per_hour") not in (None, ""):
        try:
            arguments["generator_gph"] = round(float(arguments["generator_lb_per_hour"]) / PROPANE_LB_A_GALLON, 3)
            arguments.setdefault("generator_fuel", "propane")
        except (TypeError, ValueError):
            problems.append("generator pounds an hour isn't a number")
    for name, (key, low, high, whole, words) in _PREPARED.items():
        if arguments.get(name) in (None, ""):
            continue
        try:
            value = float(arguments[name])
        except (TypeError, ValueError):
            problems.append(f"{words} isn't a number")
            continue
        if not low <= value <= high:
            problems.append(f"{words} should be {low:g} to {high:g}")
            continue
        value = int(round(value)) if whole else value
        person_settings.put(context, key, value)
        said.append(f"{words} {value:g}")
    fuel = str(arguments.get("generator_fuel", "") or "").strip().lower()
    if fuel:
        if fuel in SAID_AS:
            person_settings.put(context, "prepared.generator_fuel", SAID_AS[fuel])
            said.append(f"generator fuel {SAID_AS[fuel]}")
        else:
            problems.append("the generator's fuel is gasoline, diesel, kerosene or propane")
    if not said and not problems:
        return "What should I set: how many people, the days to plan for, or your generator's burn rate?"
    return ("Set: " + ", ".join(said) + "." if said else "") + \
        ((" " if said else "") + "Not set: " + "; ".join(problems) + "." if problems else "")


_WATER = r"(\d+(?:\.\d+)?)\s*-?\s*(gallons?|gal|liters?|litres?|l|quarts?|qt)\b"
_STRENGTH = r"(\d+(?:\.\d+)?)\s*%"
COMMON_STRENGTHS = ("6 %", "8.25 %")  # most US household bleach is one of these


def _action_bleach_for_water(context, arguments: dict) -> str:
    """How much household bleach makes water safe to drink, worked out in code by the EPA's method
    (core/eng_calcs.py water_bleach), never from the model's memory. The amount of water and the bleach's strength
    are read from what he said; with no strength, both common strengths are said, to check against the label."""
    import re

    from core import eng_calcs

    said = " ".join(str(arguments.get(k) or "") for k in ("question", "water", "strength"))
    water = re.search(_WATER, said, re.I)
    if not water:
        return "How much water: how many gallons or liters?"
    amount = f"{water.group(1)} {'gal' if water.group(2).lower().startswith(('g', 'q')) else 'L'}"
    if water.group(2).lower().startswith("q"):
        amount = f"{float(water.group(1)) / 4:g} gal"
    strength = re.search(_STRENGTH, said)
    try:
        if strength:
            result = eng_calcs.calculate("water_bleach", {"water": amount, "strength": f"{strength.group(1)} %"})
            return f"{result['said']} (Basis: {result['basis']}.)"
        lines = [eng_calcs.calculate("water_bleach", {"water": amount, "strength": s}) for s in COMMON_STRENGTHS]
    except eng_calcs.CalcError as problem:
        return str(problem)
    first = lines[0]
    drops = [int(r["values"]["drops"].si) for r in lines]
    return (f"Check the label for the bleach's strength: for 6% it's {drops[0]} drops, for 8.25% it's {drops[1]}. "
            f"{first['said']} (Basis: {first['basis']}.)")


def _action_firewood(context, arguments: dict) -> str:
    """Cords of firewood on hand against what a winter takes him (core/firewood.say)."""
    from core import firewood

    return firewood.say(context)


def _action_emergency_kit(context, arguments: dict) -> str:
    """Ready.gov's basic emergency kit against his inventory and pantry (core/ready_kit.say)."""
    from core import ready_kit

    return ready_kit.say(context)


def _action_where_were_we(context, arguments: dict) -> str:
    """Where he left off (core/left_off.say)."""
    from core import left_off

    return left_off.say(context)


def _action_anything_unusual(context, arguments: dict) -> str:
    """What in his records is far off its own normal (core/unusual.say)."""
    from core import unusual

    return unusual.say(context)


# Garden crops by name, for "should I water the tomatoes?" (each a stem, so "tomato" covers "tomatoes" and "tomato
# plants"); never a houseplant or an animal, and only asked ("should I", "do I"), never "remind me to water the
# tomatoes every 2 days" (a maintenance task).
GARDEN_CROPS = ("tomato", "pepper", "bean", "squash", "cucumber", "corn", "lettuce", "potato", "carrot", "onion",
                "garlic", "melon", "pumpkin", "pea", "kale", "cabbage", "broccoli", "strawberr", "zucchini", "okra",
                "spinach", "beet", "radish", "seedlings", "transplants")
_WATER_A_CROP = tuple(f"{verb} {crop}" for crop in GARDEN_CROPS
                      for verb in ("should i water the", "should i water my", "do i water the", "do i water my",
                                   "need to water the", "need to water my"))


def register_today_actions(registry: AssistantActionRegistry) -> None:
    """Registers get_today, get_week, get_weather (never the wind chill or heat index: those go to
    work_outside_wind_chill_heat_index, core/outdoor_work.py), should_i_water (core/weather_watch.say_watering, heard only of the
    garden or a garden crop by name, GARDEN_CROPS: "should I water the tomatoes?", never houseplants or the hens), log_rain (his rain gauge, which that answer counts; heard only when he reads it, never "is an inch of rain enough?"), weather_for_my_plans (the forecast against his garden, flock and pipes,
    core/weather_watch.py), anything_unusual (core/unusual.py), where_were_we (core/left_off.py), how_prepared (core/preparedness.py), emergency_kit (core/ready_kit.py), firewood_check (core/firewood.py), bleach_for_water (the EPA's dose, core/eng_calcs.py), set_preparedness (what those count with: people, days, the generator's rate in gallons or a propane
    rate in pounds an hour, the catchment roof the water budget counts, and the battery the power picture counts), evening_wrap (core/evening_wrap.py) and set_weather_place (domain today: the
    Dashboard's). Their trigger phrases cover the everyday ways he'd ask ("plan for 3 people", "how many days could my
    generator run?", "do I need to cover the tomatoes", "what was I in the middle of",
    "have I been spending more than normal?", "what's first tomorrow":
    tests/test_everyday_phrasing_routing.py).
    The battery size is reached by "battery bank is" or "kWh battery", never "my battery is" ("my battery is at 20
    percent")."""
    registry.register(AssistantAction(
        name="get_today", domain="today",
        description=("Everything that needs the user today across all apps: overdue things, today's events, bills, "
                     "maintenance, tasks, birthdays, things waiting (inbox, drafts), and what's coming in 3 days."),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_today,
        trigger_phrases=("what's on today", "whats on today", "what's on for today", "what do i have today",
                         "what's my day", "whats my day", "my day look like", "plan for today", "what's today",
                         "anything due today", "what needs me today", "what do i need to do today"),
    ))
    registry.register(AssistantAction(
        name="get_week", domain="today",
        description="What's due each day this week across all apps (bills, upkeep, events, tasks, birthdays): the "
                    "Dashboard's Your Week.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_week,
        trigger_phrases=("what's this week", "whats this week", "this week look", "due this week", "my week", "week ahead",
                         "rest of the week"),
    ))
    registry.register(AssistantAction(
        name="get_weather", domain="today",
        description="The weather in the user's town: now, today's high and low, and tomorrow. Not for the wind chill "
                    "or heat index, or whether it's safe to work outside: those are work_outside_wind_chill_heat_index.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_weather,
        trigger_phrases=("weather", "how hot", "how cold", "is it going to rain", "will it rain", "temperature outside",
                         "forecast"),
    ))
    registry.register(AssistantAction(
        name="log_rain", domain="today",
        description="Log the rainfall he read off his rain gauge (inches or millimeters), for the week's watering.",
        parameters={"type": "object", "properties": {
            "amount": {"type": "string", "description": "how much, as he said it: '0.6 inches', 'half an inch'"},
            "when": {"type": "string", "description": "the day it fell, if not today: 'yesterday', 'Saturday'"}},
            "required": ["amount"]},
        handler=_action_log_rain,
        trigger_phrases=("rain gauge says", "gauge says", "gauge read", "got an inch of rain", "inches of rain",
                         "mm of rain", "rained an inch", "rained half an inch", "in the rain gauge"),
    ))
    registry.register(AssistantAction(
        name="should_i_water", domain="today",
        description="Whether to water the garden today: rain now or likely tomorrow, a hot dry day, and the soil check.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_should_i_water,
        # garden words and garden crops by name (GARDEN_CROPS) only: never "should I water the houseplants?" or "do
        # I need to water the chickens?"
        trigger_phrases=("water the garden", "water the beds", "water the vegetables", "garden need water",
                         "garden need watering", "need watering", "need to be watered", "watering the garden",
                         *_WATER_A_CROP),
    ))
    registry.register(AssistantAction(
        name="weather_for_my_plans", domain="today",
        description="What the forecast means for what the user has going: frost tonight against the crops his "
                    "confirmed garden plans have in the ground, a cold night for seedlings hardening off, heat or "
                    "freezing water for his flock, a night cold enough to freeze the pipes or the well; or that "
                    "nothing in it threatens them.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_weather_for_my_plans,
        trigger_phrases=("frost tonight", "will it frost", "going to frost", "freeze tonight", "will it freeze",
                         "cover the garden", "cover my plants", "weather for my garden", "weather mean for",
                         "too hot for the chickens", "too cold for the chickens", "hens' water", "need to cover",
                         "rain tomorrow", "rain mess", "rain on the", "rain for the build", "pipes freeze",
                         "pipes to freeze", "frozen pipes", "pipes from freezing", "pipes going to freeze"),
    ))
    registry.register(AssistantAction(
        name="anything_unusual", domain="today",
        description="Whether anything in the user's own records is far off its usual (first: the hens laying much "
                    "less than their normal), with what to check; or that nothing looks off.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_anything_unusual,
        trigger_phrases=("anything unusual", "anything off", "anything weird", "anything out of the ordinary",
                         "notice anything", "anything wrong", "more than normal", "more than usual", "than usual",
                         "than normal"),
    ))
    registry.register(AssistantAction(
        name="where_were_we", domain="today",
        description="Where the user left off, from the records: missions worked on lately with their next step, "
                    "Planner drafts not yet confirmed, open promises and recent decisions.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_where_were_we,
        trigger_phrases=("where were we", "where did we leave off", "where did i leave off", "what was i working on",
                         "pick up where", "what was i doing", "remind me where i was", "in the middle of"),
    ))
    registry.register(AssistantAction(
        name="how_prepared", domain="today",
        description="How ready the user is if things go wrong: days of drinking water in the pantry at a gallon a "
                    "person a day against his target, what to use before it expires, and what isn't counted yet.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_how_prepared,
        trigger_phrases=("how prepared", "days of water", "how much water do i have", "emergency supplies",
                         "generator run", "generator last", "fuel last", "fuel for the generator",
                         "if the power goes out", "grid down", "prepared for an emergency", "what should i rotate"),
    ))
    registry.register(AssistantAction(
        name="set_preparedness", domain="today",
        description="Set what preparedness counts with: how many people to plan for, the days to plan for, and the "
                    "generator's burn rate (gallons an hour), hours a day and fuel.",
        parameters={"type": "object", "properties": {
            "people": {"type": "number", "description": "How many people to plan for."},
            "target_days": {"type": "number", "description": "Days of water and food to aim for."},
            "generator_gph": {"type": "number", "description": "The generator's gallons an hour at its usual load."},
            "generator_lb_per_hour": {"type": "number", "description": "A propane generator's pounds an hour."},
            "generator_hours": {"type": "number", "description": "Hours a day he'd run it."},
            "generator_fuel": {"type": "string", "description": "gasoline, diesel, kerosene or propane."},
            "firewood_cords": {"type": "number", "description": "Cords of firewood a winter takes him."},
            "roof_sqft": {"type": "number", "description": "The roof he catches rain from, in square feet."},
            "battery_kwh": {"type": "number", "description": "His battery bank's usable kilowatt-hours."}},
            "required": []},
        handler=_action_set_preparedness,
        trigger_phrases=("cords a winter", "cords of wood a winter", "plan for people", "people to plan for", "plan for 2", "plan for 3", "plan for 4",
                         "plan for 5", "plan for 6", "plan for two", "plan for three", "plan for four",
                         "generator burns", "generator uses", "gallons an hour", "burn rate", "pounds an hour",
                         "plan for days", "prepare for days", "catchment roof is", "catch rain off",
                         "battery bank is", "kwh battery", "battery holds"),
    ))
    registry.register(AssistantAction(
        name="bleach_for_water", domain="today",
        description="How much unscented household bleach makes water safe to drink (the EPA's method, worked out in "
                    "code): the amount of water, and the bleach's strength if they said it.",
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "Their words, with the amount of water and any strength."}},
            "required": ["question"]},
        handler=_action_bleach_for_water,
        trigger_phrases=("bleach to purify", "how much bleach", "bleach in water", "bleach per gallon",
                         "drops of bleach", "purify water with bleach", "bleach to make water safe",
                         "disinfect water", "bleach for drinking water"),
    ))
    registry.register(AssistantAction(
        name="firewood_check", domain="today",
        description="Cords of firewood in his inventory against what a winter takes him (his own figure).",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_firewood,
        trigger_phrases=("enough firewood", "enough wood for the winter", "how much firewood", "firewood do i have",
                         "cords of wood", "cords of firewood", "wood for winter"),
    ))
    registry.register(AssistantAction(
        name="emergency_kit", domain="today",
        description="Check the user's 72-hour emergency kit: Ready.gov's basic kit against his inventory and pantry, "
                    "water and food against three days, and what isn't in his records.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_emergency_kit,
        trigger_phrases=("emergency kit", "72 hour kit", "72-hour kit", "go bag", "bug out bag", "bug-out bag",
                         "disaster kit", "survival kit", "what am i missing for an emergency"),
    ))
    registry.register(AssistantAction(
        name="evening_wrap", domain="today",
        description="The evening wrap now: what got done today, then tomorrow's first thing and tomorrow's weather.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_evening_wrap,
        trigger_phrases=("wrap up my day", "evening wrap", "how did today go", "what's tomorrow", "end of day",
                         "first tomorrow", "first thing tomorrow", "tomorrow first"),
    ))
    registry.register(AssistantAction(
        name="set_weather_place", domain="today",
        description="Set which town the weather is for, by name (with the state or country if there are several).",
        parameters={"type": "object", "properties": {
            "place": {"type": "string", "description": "the town, e.g. 'Springfield, Illinois'."}}, "required": ["place"]},
        handler=_action_set_weather_place,
        trigger_phrases=("my town is", "set my town", "change my town", "weather town"),
    ))
