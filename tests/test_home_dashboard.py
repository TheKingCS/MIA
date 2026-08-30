"""
tests.test_home_dashboard
============================

Unit tests for gui.home_dashboard's pure formatting helpers. The
reactive widget/QTimer behavior itself is verified with a headless
offscreen-QPA smoke test (this project's convention for Qt widget
behavior), not pytest — see gui/character_panel.py's own test file for
the same split.
"""

from __future__ import annotations

from datetime import date, datetime

from core.activity_log_manager import ActivityLogEntry
from core.finance_manager import FinancialSnapshot
from core.homestead_manager import HomesteadSnapshot
from core.mission_manager import Mission, Objective
from core.power_manager import PowerStatus
from core.project_manager import Project
from core.volume_manager import VolumeStatus
from gui.home_dashboard import (
    format_active_mission_line,
    format_activity_log_line,
    format_clock_date,
    format_clock_time,
    format_current_project_line,
    format_homestead_line,
    format_kraken_line,
    format_net_worth_line,
    format_power_line,
    format_real_estate_line,
    format_volume_line,
)


def test_format_clock_time():
    assert format_clock_time(datetime(2026, 7, 14, 9, 5, 3)) == "09:05:03"


def test_format_clock_date_has_no_leading_zero_and_no_platform_specific_codes():
    assert format_clock_date(date(2026, 7, 4)) == "Saturday, July 4"


def test_format_power_line_no_battery():
    assert format_power_line(None) == "No battery or UPS detected on this system."


def test_format_power_line_plugged_in():
    status = PowerStatus(percent=87.4, plugged_in=True, seconds_left=None)
    assert format_power_line(status) == "87%  —  Plugged in"


def test_format_power_line_on_battery():
    status = PowerStatus(percent=42.0, plugged_in=False, seconds_left=600)
    assert format_power_line(status) == "42%  —  On battery"


def test_format_active_mission_line_none():
    assert format_active_mission_line(None, 0, 0) == "No active mission."


def test_format_active_mission_line_no_objectives():
    mission = Mission(mission_id="m1", name="Scout the ridge")
    assert format_active_mission_line(mission, 0, 0) == "Scout the ridge  (no objectives yet)"


def test_format_active_mission_line_with_progress():
    mission = Mission(
        mission_id="m1",
        name="Scout the ridge",
        objectives=[
            Objective(description="Reach the summit", metric_type="tally", target=1),
            Objective(description="Take a photo", metric_type="tally", target=1),
        ],
    )
    assert format_active_mission_line(mission, 1, 2) == "Scout the ridge  —  1 of 2 objectives complete"


def test_format_volume_line_unavailable():
    assert format_volume_line(None) == "Not available on this device."


def test_format_volume_line_normal():
    assert format_volume_line(VolumeStatus(percent=62, muted=False)) == "62%"


def test_format_volume_line_muted():
    assert format_volume_line(VolumeStatus(percent=62, muted=True)) == "62%  —  Muted"


def test_format_current_project_line_none():
    assert format_current_project_line(None, 0) == "No active projects."


def test_format_current_project_line_single_active():
    project = Project(project_id="p1", name="Garage Rewire", status="Active")
    assert format_current_project_line(project, 1) == "Garage Rewire  [Active]"


def test_format_current_project_line_multiple_active():
    project = Project(project_id="p1", name="Garage Rewire", status="Active")
    assert format_current_project_line(project, 3) == "Garage Rewire  [Active]  (+2 more active)"


def test_format_activity_log_line_empty():
    assert format_activity_log_line([]) == "No recent activity."


def test_format_activity_log_line_single_entry():
    entries = [ActivityLogEntry(entry_id="e1", event_type="module_opened", summary="Opened Notes", timestamp="2026-07-15T14:02:00")]
    assert format_activity_log_line(entries) == "14:02 Opened Notes"


def test_format_activity_log_line_multiple_entries_joined():
    entries = [
        ActivityLogEntry(entry_id="e1", event_type="waypoint_added", summary="Waypoint added", timestamp="2026-07-15T14:02:00"),
        ActivityLogEntry(entry_id="e2", event_type="battery_check", summary="Battery check ok", timestamp="2026-07-15T14:00:00"),
    ]
    assert format_activity_log_line(entries) == "14:02 Waypoint added  //  14:00 Battery check ok"


def _snapshot(source: str, summary: dict) -> FinancialSnapshot:
    return FinancialSnapshot(
        source=source, generated_at="2026-07-16T00:00:00.000Z", imported_at="2026-07-16T00:00:00.000Z",
        data={"source": source, "summary": summary},
    )


def test_format_real_estate_line_no_snapshot():
    assert format_real_estate_line(None) == "No snapshot imported yet."


def test_format_real_estate_line_missing_summary():
    snapshot = _snapshot("real_estate_portfolio", {})
    assert format_real_estate_line(snapshot) == "Snapshot imported, but no summary data found."


def test_format_real_estate_line_with_equity_only():
    snapshot = _snapshot("real_estate_portfolio", {"total_equity": 210000})
    assert format_real_estate_line(snapshot) == "$210,000 equity"


def test_format_real_estate_line_with_equity_and_cash_flow():
    snapshot = _snapshot("real_estate_portfolio", {"total_equity": 210000, "monthly_cash_flow": 875.50})
    assert format_real_estate_line(snapshot) == "$210,000 equity  —  $876/mo cash flow"


def test_format_kraken_line_no_snapshot():
    assert format_kraken_line(None) == "No snapshot imported yet."


def test_format_kraken_line_missing_summary():
    assert format_kraken_line(_snapshot("kraken_trading_agent", {})) == "Snapshot imported, but no summary data found."


def test_format_kraken_line_with_value_only():
    snapshot = _snapshot("kraken_trading_agent", {"total_value": 8500})
    assert format_kraken_line(snapshot) == "$8,500"


def test_format_kraken_line_with_positive_gain():
    snapshot = _snapshot("kraken_trading_agent", {"total_value": 8500, "gain_loss_pct": 12.5})
    assert format_kraken_line(snapshot) == "$8,500  (+12.5%)"


def test_format_kraken_line_with_negative_gain():
    snapshot = _snapshot("kraken_trading_agent", {"total_value": 8500, "gain_loss_pct": -4.2})
    assert format_kraken_line(snapshot) == "$8,500  (-4.2%)"


def test_format_net_worth_line_no_snapshots():
    assert format_net_worth_line([]) == "No financial snapshots imported yet."


def test_format_net_worth_line_excludes_snapshots_missing_total_value():
    snapshots = [_snapshot("real_estate_portfolio", {})]
    assert format_net_worth_line(snapshots) == "No financial snapshots imported yet."


def test_format_net_worth_line_single_source():
    snapshots = [_snapshot("real_estate_portfolio", {"total_value": 540000})]
    assert format_net_worth_line(snapshots) == "$540,000  —  from 1 source"


def test_format_net_worth_line_sums_multiple_sources():
    snapshots = [
        _snapshot("real_estate_portfolio", {"total_value": 540000}),
        _snapshot("kraken_trading_agent", {"total_value": 8500}),
    ]
    assert format_net_worth_line(snapshots) == "$548,500  —  from 2 sources"


def _homestead_snapshot(summary: dict, top_alert: dict | None = None) -> HomesteadSnapshot:
    return HomesteadSnapshot(
        source="mia_homestead", generated_at="2026-08-30T22:33:19Z", imported_at="2026-08-30T22:33:19Z",
        data={"source": "mia_homestead", "summary": summary, "top_alert": top_alert},
    )


def test_format_homestead_line_no_snapshot():
    assert format_homestead_line(None) == "No snapshot imported yet."


def test_format_homestead_line_missing_summary():
    snapshot = HomesteadSnapshot(
        source="mia_homestead", generated_at="x", imported_at="x", data={"source": "mia_homestead"}
    )
    assert format_homestead_line(snapshot) == "Snapshot imported, but no summary data found."


def test_format_homestead_line_all_clear_with_yield():
    snapshot = _homestead_snapshot({"critical_alert_count": 0, "warning_alert_count": 0, "yield_this_week_kg": 7.4})
    assert format_homestead_line(snapshot) == "All clear  —  7.4 kg harvested this week"


def test_format_homestead_line_all_clear_no_yield_data():
    snapshot = _homestead_snapshot({"critical_alert_count": 0, "warning_alert_count": 0})
    assert format_homestead_line(snapshot) == "All clear"


def test_format_homestead_line_warnings_only():
    snapshot = _homestead_snapshot({"critical_alert_count": 0, "warning_alert_count": 2})
    assert format_homestead_line(snapshot) == "2 warnings, no critical alerts"


def test_format_homestead_line_single_warning_uses_singular_noun():
    snapshot = _homestead_snapshot({"critical_alert_count": 0, "warning_alert_count": 1})
    assert format_homestead_line(snapshot) == "1 warning, no critical alerts"


def test_format_homestead_line_critical_leads_over_warning_and_yield():
    snapshot = _homestead_snapshot(
        {"critical_alert_count": 3, "warning_alert_count": 1, "yield_this_week_kg": 7.4},
        top_alert={"severity": "critical", "source": "greenhouse_power", "message": "power fault"},
    )
    assert format_homestead_line(snapshot) == "3 critical alerts  —  power fault"


def test_format_homestead_line_single_critical_uses_singular_noun():
    snapshot = _homestead_snapshot({"critical_alert_count": 1, "warning_alert_count": 0})
    assert format_homestead_line(snapshot) == "1 critical alert"


def test_format_homestead_line_truncates_long_alert_message():
    long_message = "x" * 80
    snapshot = _homestead_snapshot(
        {"critical_alert_count": 1, "warning_alert_count": 0},
        top_alert={"severity": "critical", "source": "greenhouse_power", "message": long_message},
    )
    line = format_homestead_line(snapshot)
    assert line == "1 critical alert  —  " + "x" * 57 + "..."
