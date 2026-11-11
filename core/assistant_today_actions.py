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


def register_today_actions(registry: AssistantActionRegistry) -> None:
    """Registers get_today, get_week, get_weather and set_weather_place (domain today: the Dashboard's)."""
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
        name="set_weather_place", domain="today",
        description="Set which town the weather is for, by name (with the state or country if there are several).",
        parameters={"type": "object", "properties": {
            "place": {"type": "string", "description": "the town, e.g. 'Springfield, Illinois'."}}, "required": ["place"]},
        handler=_action_set_weather_place,
        trigger_phrases=("my town is", "set my town", "change my town", "weather town"),
    ))
