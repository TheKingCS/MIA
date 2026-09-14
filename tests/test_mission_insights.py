"""
tests.test_mission_insights
==============================

Unit tests for core.mission_insights — isolates _DATA_DIR for
mission/insight files into a tmp_path scratch area, same monkeypatch
pattern as test_maintenance_insights.py's own isolated_paths.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

import core.expedition_manager as expedition_manager_module
import core.insight_manager as insight_manager_module
import core.mission_manager as mission_manager_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.insight_manager import InsightManager
from core.mission_insights import (
    days_since_last_touch,
    format_mission_insights_message,
    is_stale,
    scan_mission_insights,
)
from core.mission_manager import Mission, MissionManager
from core.trip_manager import TripManager
from core.waypoint_manager import WaypointManager

TODAY = date(2026, 9, 14)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", data_dir / "expeditions.json")
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", data_dir / "trips.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")
    monkeypatch.setattr(insight_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(insight_manager_module, "_INSIGHTS_FILE", data_dir / "insights.json")
    monkeypatch.setattr(insight_manager_module, "_RECOMMENDATIONS_FILE", data_dir / "recommendations.json")
    return data_dir


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.waypoints = WaypointManager(context)
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.missions = MissionManager(context)
    context.insights = InsightManager(context)
    return context


def _mission(**overrides) -> Mission:
    defaults = dict(
        mission_id="m1", name="Master Angler", status="active",
        created_at="2026-09-01T10:00:00", updated_at="2026-09-01T10:00:00",
    )
    defaults.update(overrides)
    return Mission(**defaults)


# ------------------------------------------------------------------
# days_since_last_touch / is_stale (pure logic)
# ------------------------------------------------------------------

def test_days_since_last_touch_uses_updated_at():
    mission = _mission(updated_at="2026-09-01T10:00:00")
    assert days_since_last_touch(mission, TODAY) == 13


def test_days_since_last_touch_falls_back_to_created_at_when_never_updated():
    mission = _mission(created_at="2026-09-01T10:00:00", updated_at="")
    assert days_since_last_touch(mission, TODAY) == 13


def test_days_since_last_touch_none_when_both_blank():
    mission = _mission(created_at="", updated_at="")
    assert days_since_last_touch(mission, TODAY) is None


def test_is_stale_true_at_exactly_fourteen_days():
    mission = _mission(updated_at=(TODAY - timedelta(days=14)).isoformat())
    assert is_stale(mission, TODAY) is True


def test_is_stale_false_just_under_fourteen_days():
    mission = _mission(updated_at=(TODAY - timedelta(days=13)).isoformat())
    assert is_stale(mission, TODAY) is False


def test_is_stale_false_for_a_completed_mission_regardless_of_age():
    mission = _mission(status="completed", updated_at=(TODAY - timedelta(days=100)).isoformat())
    assert is_stale(mission, TODAY) is False


def test_is_stale_false_for_an_abandoned_mission():
    mission = _mission(status="abandoned", updated_at=(TODAY - timedelta(days=100)).isoformat())
    assert is_stale(mission, TODAY) is False


# ------------------------------------------------------------------
# scan_mission_insights
# ------------------------------------------------------------------

def test_scan_flags_a_stale_active_mission(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    # Force it stale — add_mission() stamps "now", not a real 14-days-ago date.
    mission.updated_at = (TODAY - timedelta(days=20)).isoformat()
    context.missions._save()

    new_insights = scan_mission_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "stale"
    assert new_insights[0].source_id == mission.mission_id
    assert new_insights[0].message == "'Master Angler' hasn't been touched in 20 days."
    assert len(context.insights.recommendations_for_insight(new_insights[0].insight_id)) == 1


def test_scan_does_not_flag_a_recently_touched_mission(isolated_paths):
    context = _make_context()
    context.missions.add_mission(name="Master Angler")  # touched "now" by add_mission()

    assert scan_mission_insights(context, TODAY) == []


def test_scan_does_not_duplicate_on_a_second_scan(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    mission.updated_at = (TODAY - timedelta(days=20)).isoformat()
    context.missions._save()

    first_run = scan_mission_insights(context, TODAY)
    second_run = scan_mission_insights(context, TODAY)

    assert len(first_run) == 1
    assert second_run == []
    assert len(context.insights.all_insights()) == 1


def test_scan_resolves_insight_once_the_mission_is_touched_again(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    mission.updated_at = (TODAY - timedelta(days=20)).isoformat()
    context.missions._save()
    new_insights = scan_mission_insights(context, TODAY)
    insight_id = new_insights[0].insight_id

    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)  # bumps updated_at
    scan_mission_insights(context, TODAY)

    assert context.insights.get_insight(insight_id).status == "resolved"


def test_scan_resolves_insight_once_the_mission_is_completed(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    mission.updated_at = (TODAY - timedelta(days=20)).isoformat()
    context.missions._save()
    new_insights = scan_mission_insights(context, TODAY)
    insight_id = new_insights[0].insight_id

    context.missions.update_mission(mission.mission_id, status="completed")
    scan_mission_insights(context, TODAY)

    assert context.insights.get_insight(insight_id).status == "resolved"


def test_scan_with_no_missions_service_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.insights = InsightManager(context)
    assert scan_mission_insights(context, TODAY) == []


def test_scan_with_no_insights_service_returns_empty(isolated_paths):
    context = _make_context()
    context.insights = None
    mission = context.missions.add_mission(name="Master Angler")
    mission.updated_at = (TODAY - timedelta(days=20)).isoformat()
    context.missions._save()
    assert scan_mission_insights(context, TODAY) == []


# ------------------------------------------------------------------
# format_mission_insights_message
# ------------------------------------------------------------------

def test_format_mission_insights_message_none_when_empty():
    assert format_mission_insights_message([]) is None


def test_format_mission_insights_message_joins_multiple(isolated_paths):
    context = _make_context()
    m1 = context.missions.add_mission(name="Master Angler")
    m1.updated_at = (TODAY - timedelta(days=20)).isoformat()
    m2 = context.missions.add_mission(name="Lawn Ranger")
    m2.updated_at = (TODAY - timedelta(days=30)).isoformat()
    context.missions._save()

    new_insights = scan_mission_insights(context, TODAY)
    message = format_mission_insights_message(new_insights)

    assert message is not None
    assert "Master Angler" in message
    assert "Lawn Ranger" in message
