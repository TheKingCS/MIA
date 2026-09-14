"""
tests.test_mission_patterns
==============================

Unit tests for core.mission_patterns — isolates _DATA_DIR for
mission/insight/profile files into a tmp_path scratch area, same
monkeypatch pattern as test_mission_insights.py's own isolated_paths.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

import core.config_manager as config_manager_module
import core.expedition_manager as expedition_manager_module
import core.insight_manager as insight_manager_module
import core.mission_manager as mission_manager_module
import core.profile_manager as profile_manager_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.insight_manager import InsightManager
from core.mission_manager import Mission, MissionManager
from core.mission_patterns import (
    build_abandonment_recommendation,
    format_abandonment_pattern_message,
    format_pattern_insights_message,
    most_common_abandon_reason,
    recent_abandoned_missions,
    scan_pattern_insights,
)
from core.profile_manager import ProfileManager
from core.trip_manager import TripManager
from core.waypoint_manager import WaypointManager

TODAY = date(2026, 9, 14)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
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
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    return data_dir


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.waypoints = WaypointManager(context)
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.missions = MissionManager(context)
    context.insights = InsightManager(context)
    context.profiles = ProfileManager(context)
    return context


def _mission(**overrides) -> Mission:
    defaults = dict(
        mission_id="m1", name="Master Angler", status="abandoned", profile_id="p1",
        created_at="2026-09-01T10:00:00", updated_at="2026-09-01T10:00:00", abandon_reason="too_hard",
    )
    defaults.update(overrides)
    return Mission(**defaults)


# ------------------------------------------------------------------
# recent_abandoned_missions (pure logic)
# ------------------------------------------------------------------

def test_recent_abandoned_missions_within_window():
    mission = _mission(updated_at=(TODAY - timedelta(days=10)).isoformat())
    assert recent_abandoned_missions([mission], "p1", TODAY) == [mission]


def test_recent_abandoned_missions_outside_window_excluded():
    mission = _mission(updated_at=(TODAY - timedelta(days=31)).isoformat())
    assert recent_abandoned_missions([mission], "p1", TODAY) == []


def test_recent_abandoned_missions_excludes_active_missions():
    mission = _mission(status="active", updated_at=TODAY.isoformat())
    assert recent_abandoned_missions([mission], "p1", TODAY) == []


def test_recent_abandoned_missions_excludes_other_profiles():
    mission = _mission(profile_id="p2", updated_at=TODAY.isoformat())
    assert recent_abandoned_missions([mission], "p1", TODAY) == []


def test_recent_abandoned_missions_excludes_unattributed():
    mission = _mission(profile_id=None, updated_at=TODAY.isoformat())
    assert recent_abandoned_missions([mission], "p1", TODAY) == []
    assert recent_abandoned_missions([mission], None, TODAY) == [mission]


# ------------------------------------------------------------------
# most_common_abandon_reason (pure logic)
# ------------------------------------------------------------------

def test_most_common_abandon_reason_clear_winner():
    missions = [_mission(abandon_reason="too_hard"), _mission(abandon_reason="too_hard"), _mission(abandon_reason="no_time")]
    assert most_common_abandon_reason(missions) == "too_hard"


def test_most_common_abandon_reason_no_reasons_recorded():
    missions = [_mission(abandon_reason=""), _mission(abandon_reason="")]
    assert most_common_abandon_reason(missions) == ""


def test_most_common_abandon_reason_tie_returns_empty():
    missions = [_mission(abandon_reason="too_hard"), _mission(abandon_reason="no_time")]
    assert most_common_abandon_reason(missions) == ""


# ------------------------------------------------------------------
# format_abandonment_pattern_message / build_abandonment_recommendation
# ------------------------------------------------------------------

def test_format_abandonment_pattern_message_with_reason():
    missions = [_mission(), _mission(), _mission()]
    assert format_abandonment_pattern_message(missions, "too_hard") == (
        "You've abandoned 3 Missions in the last 30 days, most often because they felt too hard."
    )


def test_format_abandonment_pattern_message_no_reason():
    missions = [_mission(), _mission(), _mission()]
    assert format_abandonment_pattern_message(missions, "") == "You've abandoned 3 Missions in the last 30 days."


def test_format_abandonment_pattern_message_singular():
    assert format_abandonment_pattern_message([_mission()], "") == "You've abandoned 1 Mission in the last 30 days."


def test_build_abandonment_recommendation_too_hard():
    assert "easier difficulty" in build_abandonment_recommendation("too_hard")


def test_build_abandonment_recommendation_unknown_reason_falls_back():
    assert build_abandonment_recommendation("") == "Consider what would make your next Mission easier to stick with."


# ------------------------------------------------------------------
# scan_pattern_insights
# ------------------------------------------------------------------

def test_scan_flags_a_profile_at_the_threshold(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    for _ in range(3):
        mission = context.missions.add_mission(name="Quest")
        context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason="too_hard")

    new_insights = scan_pattern_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "repeated_abandonment"
    assert new_insights[0].source_id == profile.profile_id
    assert "3 Missions" in new_insights[0].message
    assert len(context.insights.recommendations_for_insight(new_insights[0].insight_id)) == 1


def test_scan_does_not_flag_below_threshold(isolated_paths):
    context = _make_context()
    context.profiles.create_profile(name="Alex")
    for _ in range(2):
        mission = context.missions.add_mission(name="Quest")
        context.missions.update_mission(mission.mission_id, status="abandoned")

    assert scan_pattern_insights(context, TODAY) == []


def test_scan_does_not_duplicate_on_a_second_scan(isolated_paths):
    context = _make_context()
    context.profiles.create_profile(name="Alex")
    for _ in range(3):
        mission = context.missions.add_mission(name="Quest")
        context.missions.update_mission(mission.mission_id, status="abandoned")

    first_run = scan_pattern_insights(context, TODAY)
    second_run = scan_pattern_insights(context, TODAY)

    assert len(first_run) == 1
    assert second_run == []
    assert len(context.insights.all_insights()) == 1


def test_scan_resolves_insight_once_back_under_threshold(isolated_paths):
    """All 3 abandonments age out of the rolling window on a later
    scan — the insight resolves automatically, same "derive fresh each
    time" behavior as Maintenance/Missions-stale insights."""
    context = _make_context()
    context.profiles.create_profile(name="Alex")
    abandoned_date = (TODAY - timedelta(days=25)).isoformat()
    for _ in range(3):
        mission = context.missions.add_mission(name="Quest")
        context.missions.update_mission(mission.mission_id, status="abandoned")
        context.missions.get_mission(mission.mission_id).updated_at = abandoned_date
    context.missions._save()

    new_insights = scan_pattern_insights(context, TODAY)
    assert len(new_insights) == 1
    insight_id = new_insights[0].insight_id

    later = TODAY + timedelta(days=10)  # now 35 days since abandonment, outside the 30-day window
    scan_pattern_insights(context, later)

    assert context.insights.get_insight(insight_id).status == "resolved"


def test_scan_does_not_resolve_a_different_kind_of_insight_for_the_same_profile(isolated_paths):
    """Regression test: a real bug found while adding a second pattern
    kind (core/skill_patterns.py) — resolution here must be scoped to
    kind="repeated_abandonment" specifically, not every open insight
    under source_type="patterns" for this profile."""
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    unrelated_insight = context.insights.create_insight_if_new(
        source_type="patterns", source_id=profile.profile_id, kind="interest_gap",
        title="Unrelated", message="A different real pattern, nothing to do with abandonment.",
    )

    # Fewer than the abandonment threshold — scan should have nothing
    # of its own to resolve, and must leave the unrelated insight alone.
    mission = context.missions.add_mission(name="Quest")
    context.missions.update_mission(mission.mission_id, status="abandoned")

    scan_pattern_insights(context, TODAY)

    assert context.insights.get_insight(unrelated_insight.insight_id).status == "open"


def test_scan_with_separate_profiles_tracked_independently(isolated_paths):
    context = _make_context()
    zac = context.profiles.create_profile(name="Zac", make_active=True)
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    for _ in range(3):
        mission = context.missions.add_mission(name="Quest")
        context.missions.update_mission(mission.mission_id, status="abandoned")  # Zac active

    context.profiles.set_active_profile(faith.profile_id)
    mission = context.missions.add_mission(name="Quest")
    context.missions.update_mission(mission.mission_id, status="abandoned")  # only 1 for Faith

    new_insights = scan_pattern_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].source_id == zac.profile_id


def test_scan_with_no_missions_service_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.insights = InsightManager(context)
    context.profiles = ProfileManager(context)
    assert scan_pattern_insights(context, TODAY) == []


def test_scan_with_no_profiles_service_returns_empty(isolated_paths):
    context = _make_context()
    context.profiles = None
    assert scan_pattern_insights(context, TODAY) == []


# ------------------------------------------------------------------
# format_pattern_insights_message
# ------------------------------------------------------------------

def test_format_pattern_insights_message_none_when_empty():
    assert format_pattern_insights_message([]) is None
