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
}


def _action_set_preparedness(context, arguments: dict) -> str:
    """Sets what "how prepared am I?" counts with: how many people, the target days, and his generator's burn rate,
    hours a day and fuel (core/preparedness.py, core/power_ready.py). A propane rate in pounds an hour
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


def register_today_actions(registry: AssistantActionRegistry) -> None:
    """Registers get_today, get_week, get_weather, weather_for_my_plans (the forecast against his garden and flock,
    core/weather_watch.py), anything_unusual (core/unusual.py), where_were_we (core/left_off.py), how_prepared (core/preparedness.py), emergency_kit (core/ready_kit.py), set_preparedness (what those count with: people, days, the generator's rate in gallons or a propane
    rate in pounds an hour), evening_wrap (core/evening_wrap.py) and set_weather_place (domain today: the
    Dashboard's). Their trigger phrases cover the everyday ways he'd ask ("plan for 3 people", "how many days could my
    generator run?": tests/test_everyday_phrasing_routing.py)."""
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
        description="The weather in the user's town: now, today's high and low, and tomorrow.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_weather,
        trigger_phrases=("weather", "how hot", "how cold", "is it going to rain", "will it rain", "temperature outside",
                         "forecast"),
    ))
    registry.register(AssistantAction(
        name="weather_for_my_plans", domain="today",
        description="What the forecast means for what the user has going: frost tonight against the crops his "
                    "confirmed garden plans have in the ground, a cold night for seedlings hardening off, heat or "
                    "freezing water for his flock; or that nothing in it threatens them.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_weather_for_my_plans,
        trigger_phrases=("frost tonight", "will it frost", "going to frost", "freeze tonight", "will it freeze",
                         "cover the garden", "cover my plants", "weather for my garden", "weather mean for",
                         "too hot for the chickens", "too cold for the chickens", "hens' water"),
    ))
    registry.register(AssistantAction(
        name="anything_unusual", domain="today",
        description="Whether anything in the user's own records is far off its usual (first: the hens laying much "
                    "less than their normal), with what to check; or that nothing looks off.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_anything_unusual,
        trigger_phrases=("anything unusual", "anything off", "anything weird", "anything out of the ordinary",
                         "notice anything", "anything wrong"),
    ))
    registry.register(AssistantAction(
        name="where_were_we", domain="today",
        description="Where the user left off, from the records: missions worked on lately with their next step, "
                    "Planner drafts not yet confirmed, open promises and recent decisions.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_where_were_we,
        trigger_phrases=("where were we", "where did we leave off", "where did i leave off", "what was i working on",
                         "pick up where", "what was i doing", "remind me where i was"),
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
            "generator_fuel": {"type": "string", "description": "gasoline, diesel, kerosene or propane."}},
            "required": []},
        handler=_action_set_preparedness,
        trigger_phrases=("plan for people", "people to plan for", "plan for 2", "plan for 3", "plan for 4",
                         "plan for 5", "plan for 6", "plan for two", "plan for three", "plan for four",
                         "generator burns", "generator uses", "gallons an hour", "burn rate", "pounds an hour",
                         "plan for days", "prepare for days"),
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
        trigger_phrases=("wrap up my day", "evening wrap", "how did today go", "what's tomorrow", "end of day"),
    ))
    registry.register(AssistantAction(
        name="set_weather_place", domain="today",
        description="Set which town the weather is for, by name (with the state or country if there are several).",
        parameters={"type": "object", "properties": {
            "place": {"type": "string", "description": "the town, e.g. 'Springfield, Illinois'."}}, "required": ["place"]},
        handler=_action_set_weather_place,
        trigger_phrases=("my town is", "set my town", "change my town", "weather town"),
    ))
