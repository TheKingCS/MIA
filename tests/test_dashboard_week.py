"""
tests.test_dashboard_week
===========================

The Dashboard's DEC-0153 cards (Zac, 2026-11-11): Your Week (core/today.week_days, each due thing on its day once,
by voice too), the weather (core/weather.py: the town found and kept as the person's own, the forecast read into
words, never online from a test), the mission in play with its next objective, and Agent Activity
(core/agent_activity.py: her own changes, held-back messages and the team only for the owner). Trade Master lives in
Home's Learning.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import weather
from core.actions import ACTION_TYPES, ActionError
from core.assistant_today_actions import describe_week
from core.today import week_days
from core.web_surfaces import active_mission, day_label
from tests.test_today import DAY, ctx, iso  # noqa: F401  (the fixture)

FORECAST = {"current": {"temperature_2m": 47.6, "weather_code": 2},
            "daily": {"time": ["d0", "d1"], "temperature_2m_max": [54.2, 50.8], "temperature_2m_min": [38.9, 36.1],
                      "weather_code": [3, 61]}}
TOWNS = {"results": [{"name": "Springfield", "admin1": "Missouri", "country": "United States", "latitude": 37.2,
                      "longitude": -93.3},
                     {"name": "Springfield", "admin1": "Illinois", "country": "United States", "latitude": 39.8,
                      "longitude": -89.6}]}


def test_your_week_puts_each_due_thing_on_its_day_once(ctx):
    ctx.calendar.add_event(title="Dentist", date=iso(1), time="09:30")
    ctx.calendar.add_event(title="Fair", date=iso(3))
    ctx.calendar.add_event(title="Too far", date=iso(9))
    ctx.budget.add_bill(name="Water", amount=40.0, due_date=iso(2))
    ctx.budget.add_bill(name="Electric", amount=120.0, due_date=iso(-2))
    ctx.alarms.add_alarm("Wake", "07:00") if hasattr(ctx.alarms, "add_alarm") else None
    days = week_days(ctx, DAY)
    assert days[0]["date"] == DAY.isoformat()
    on = {d["date"]: [i["title"] for i in d["items"]] for d in days}
    assert "Pay Electric" in on[DAY.isoformat()] and on[iso(1)] == ["Dentist"] and on[iso(3)] == ["Fair"]
    assert any("Water" in t for t in on[iso(2)])
    assert not any("Too far" in t for ts in on.values() for t in ts)
    assert not any("Wake" in t for d in days[1:] for t in [i["title"] for i in d["items"]])  # alarms stay on Today
    titles = [t for ts in on.values() for t in ts]
    assert len(titles) == len(set(titles))
    said = describe_week(days, DAY)
    assert "Tomorrow: Dentist." in said and describe_week([], DAY) == "Nothing is due this week."


def test_a_day_in_your_week_is_named_plainly():
    assert day_label(DAY, DAY) == "Today" and day_label(DAY + timedelta(days=1), DAY) == "Tomorrow"
    later = DAY + timedelta(days=3)
    assert day_label(later, DAY) == f"{later:%A}, {later:%b} {later.day}"


def test_the_forecast_is_read_into_words_and_rounded():
    got = weather.read(FORECAST, "fahrenheit")
    assert got == {"temp": 48, "words": "Partly cloudy", "high": 54, "low": 39,
                   "tomorrow": {"high": 51, "low": 36, "words": "Light rain"}, "unit": "°F"}
    assert weather.read({"nothing": 1}, "celsius") is None
    assert "temperature_unit=celsius" in weather.forecast_url(51.5, -0.12, "celsius")


def test_a_town_is_found_by_name_and_its_state(monkeypatch):
    asked = []

    def fetch(url):
        asked.append(url)
        return TOWNS

    assert weather.find_place("Springfield, Illinois", fetch) == {"name": "Springfield, Illinois", "lat": 39.8,
                                                                   "lon": -89.6}
    assert weather.find_place("Springfield", fetch)["name"] == "Springfield, Missouri"
    assert "name=Springfield&" in asked[0] and weather.find_place("", fetch) is None
    assert weather.find_place("Nowhere", lambda url: {}) is None


def test_the_weather_card_asks_for_a_town_then_shows_the_forecast(ctx, monkeypatch):
    weather._kept.clear()
    assert weather.card(ctx) == {"status": "PLANNED", "set": True, "text": None}
    assert "don't know your town" in weather.say(ctx)
    monkeypatch.setattr(weather, "_fetch_json", lambda url: TOWNS)
    action = ACTION_TYPES["weather.place"]
    assert action.describe(ctx, {"place": "Springfield, Illinois"}) == "Use Springfield, Illinois for the weather"
    assert action.execute(ctx, {"place": "Springfield, Illinois"}) == "The weather is for Springfield, Illinois now."
    with pytest.raises(ActionError, match="Which town"):
        action.describe(ctx, {"place": "  "})
    ctx.config.set("region.country", "US")
    assert weather.card(ctx)["loading"] is True  # a test run never goes online by itself
    shown = weather.card(ctx, fetch=lambda url: FORECAST)
    assert shown["text"] == "48°F, partly cloudy" and shown["place"] == "Springfield, Illinois"
    assert weather.card(ctx)["text"] == "48°F, partly cloudy"  # kept, not fetched again
    assert weather.say(ctx).startswith("In Springfield, Illinois it's 48°F, partly cloudy; today 54 and 39.")
    weather._kept.clear()


def test_the_mission_in_play_shows_its_next_objective():
    class Store:
        """Two active missions; the later-worked one is in play."""

        def all_missions(self):
            """The missions."""
            obj = lambda d: SimpleNamespace(description=d)  # noqa: E731
            return [SimpleNamespace(mission_id="a", name="Old", status="active", updated_at="2026-11-01", created_at="",
                                    icon="", objectives=[]),
                    SimpleNamespace(mission_id="b", name="Build the coop", status="active", updated_at="2026-11-10",
                                    created_at="", icon="", objectives=[obj("Buy lumber"), obj("Frame the walls")]),
                    SimpleNamespace(mission_id="c", name="Done", status="completed", updated_at="2026-11-11",
                                    created_at="", icon="", objectives=[])]

        def is_objective_complete(self, mission_id, index):
            """The first objective is done."""
            return index == 0

    got = active_mission(SimpleNamespace(missions=Store()))
    assert got["name"] == "Build the coop" and got["next"] == "Frame the walls" and (got["done"], got["total"]) == (1, 2)
    assert got["others"] == 1 and active_mission(SimpleNamespace()) is None


def test_agent_activity_shows_her_own_changes_and_the_team_only_to_the_owner(monkeypatch):
    import core.agent_activity as aa
    import core.web_changes as changes
    import core.work_dashboard as work

    now = datetime(2026, 11, 11, 15, 0)
    monkeypatch.setattr(changes, "changes_page", lambda context, now=None: {"undoable": [
        {"what": "Logged 6 eggs", "when": "2:05 PM", "by": "MIA"}, {"what": "Added a bill", "when": "1:00 PM", "by": "You"}]})
    monkeypatch.setattr(aa, "_held", lambda context: [])
    monkeypatch.setattr(work, "allowed", lambda context, pid: pid == "owner")
    import core.work_activity as wa

    monkeypatch.setattr(wa, "events", lambda: [{"at": "2026-11-11T13:00:00", "who": "Claude", "action": "build",
                                                 "task": "T-0057", "detail": "the eight"}])
    import core.council as council

    monkeypatch.setattr(council, "recent", lambda n: [])
    mine = aa.activity(SimpleNamespace(), "someone", now)
    assert [r["what"] for r in mine["mine"]] == ["Logged 6 eggs"] and mine["team"] == [] and mine["any"]
    owner = aa.activity(SimpleNamespace(), "owner", now)
    assert owner["team"][0]["who"] == "Claude" and owner["team"][0]["page"] == "dev.html"


def test_trade_master_is_in_homes_learning():
    from core.web_areas import areas_of

    assert areas_of("trades") == ["learning"]
