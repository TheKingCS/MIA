"""
tests.test_missions_module
=============================

Unit tests for modules.missions.module's pure functions, same style as
tests/test_expeditions_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.mission_manager import Mission, Objective
from modules.missions.module import format_mission_row, format_objective_row


def test_format_mission_row_with_trip():
    mission = Mission(mission_id="m1", name="Master Angler", status="active")
    assert format_mission_row(mission, trip_name="Day 1") == "Master Angler  [Day 1]  (active)"


def test_format_mission_row_no_trip():
    mission = Mission(mission_id="m1", name="General Goal", status="completed")
    assert format_mission_row(mission) == "General Goal  (completed)"


def test_format_objective_row_incomplete_tally():
    objective = Objective(description="Catch 3 fish", metric_type="tally", target=3.0, progress=1.0)
    assert format_objective_row(objective, progress=1.0, is_complete=False) == "[ ] Catch 3 fish: 1 of 3"


def test_format_objective_row_complete():
    objective = Objective(description="Catch 3 fish", metric_type="tally", target=3.0, progress=3.0)
    assert format_objective_row(objective, progress=3.0, is_complete=True) == "[x] Catch 3 fish: 3 of 3"


def test_format_objective_row_fractional_hours():
    objective = Objective(description="Spend 2 hours fishing", metric_type="trip_duration_hours", target=2.0)
    assert format_objective_row(objective, progress=1.5, is_complete=False) == "[ ] Spend 2 hours fishing: 1.5 of 2"
