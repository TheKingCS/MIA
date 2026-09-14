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
from core.budget_manager import Bill
from core.real_estate_manager import Property
from core.finance_manager import FinancialSnapshot
from core.homestead_manager import HomesteadSnapshot
from core.data_logger_manager import Reading
from core.insight_manager import Insight
from core.maintenance_manager import MaintenanceTask
from core.mission_manager import Mission, Objective
from core.music_manager import NowPlaying
from core.power_manager import PowerStatus
from core.project_manager import Project
from gui.home_dashboard import (
    format_active_mission_line,
    format_activity_log_line,
    format_clock_date,
    format_clock_time,
    format_budget_line,
    format_dashboard_hero_tagline,
    format_property_portfolio_line,
    format_current_project_line,
    format_homestead_line,
    format_kraken_line,
    format_maintenance_line,
    format_music_line,
    format_net_worth_line,
    format_observations_line,
    format_party_activity_line,
    format_power_line,
    format_real_estate_line,
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


def test_format_dashboard_hero_tagline():
    assert format_dashboard_hero_tagline(14, 3, 2) == "Level 14 · 3 missions available · 2 active projects"


def test_format_dashboard_hero_tagline_zeros():
    assert format_dashboard_hero_tagline(1, 0, 0) == "Level 1 · 0 missions available · 0 active projects"


def test_format_party_activity_line():
    assert format_party_activity_line("Zac", "Mow the Homestead") == 'Zac completed "Mow the Homestead"'


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


def test_format_net_worth_line_includes_plaid_snapshot():
    """core.plaid_manager.sync() now writes summary.total_value on its
    balance snapshots (added 2026-09-09, see core/plaid_manager.py's
    compute_net_balance_total) — this generic formatter needed no code
    change to pick it up, since it already reads any source's
    summary.total_value the same way."""
    snapshots = [_snapshot("plaid_item-1", {"total_value": 12345.0})]
    assert format_net_worth_line(snapshots) == "$12,345  —  from 1 source"


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


def _task(interval_days=None, last_completed=None):
    return MaintenanceTask(
        task_id="t1", asset_id="a1", title="Oil change",
        interval_days=interval_days, last_completed=last_completed,
    )


def test_format_maintenance_line_no_tasks():
    assert format_maintenance_line([], date(2026, 9, 7)) == "No maintenance tasks tracked yet."


def test_format_maintenance_line_all_caught_up():
    # Recurring, completed today — not due for a long while.
    tasks = [_task(interval_days=90, last_completed="2026-09-07")]
    assert format_maintenance_line(tasks, date(2026, 9, 7)) == "All caught up"


def test_format_maintenance_line_due_soon():
    tasks = [_task(interval_days=30, last_completed="2026-08-10")]  # due 2026-09-09, 2 days out
    assert format_maintenance_line(tasks, date(2026, 9, 7)) == "1 task due within 7 days"


def test_format_maintenance_line_overdue():
    tasks = [_task(interval_days=30, last_completed="2026-07-01")]  # due 2026-07-31, well overdue
    assert format_maintenance_line(tasks, date(2026, 9, 7)) == "1 overdue task"


def test_format_maintenance_line_overdue_and_due_soon_combined():
    tasks = [
        _task(interval_days=30, last_completed="2026-07-01"),  # overdue
        _task(interval_days=30, last_completed="2026-08-10"),  # due soon
    ]
    assert format_maintenance_line(tasks, date(2026, 9, 7)) == "1 overdue task, 1 due soon"


def test_format_maintenance_line_one_time_and_never_completed_are_not_due():
    # Neither a one-time task nor a never-completed recurring task has
    # a computable next_due_date — neither should count as due/overdue.
    tasks = [_task(interval_days=None, last_completed=None), _task(interval_days=90, last_completed=None)]
    assert format_maintenance_line(tasks, date(2026, 9, 7)) == "All caught up"


def _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0):
    return MaintenanceTask(
        task_id="tm1", asset_id="a1", title="Oil change", trigger_type="mileage",
        meter_unit="miles", meter_interval=meter_interval,
        last_completed_meter_value=last_completed_meter_value, last_completed="2026-08-01",
    )


def _reading(value, task_id="tm1"):
    return Reading(reading_id="r", series_id=f"maintenance_{task_id}", value=value, unit="", note="", timestamp="2026-09-01T00:00:00")


def test_format_maintenance_line_meter_task_overdue_counts():
    tasks = [_meter_task()]
    readings = {"tm1": [_reading(46000)]}  # 6000 used, interval 5000 -> overdue
    assert format_maintenance_line(tasks, date(2026, 9, 7), readings) == "1 overdue task"


def test_format_maintenance_line_meter_task_not_due_is_all_caught_up():
    tasks = [_meter_task()]
    readings = {"tm1": [_reading(42000)]}  # 2000 used, interval 5000 -> not due
    assert format_maintenance_line(tasks, date(2026, 9, 7), readings) == "All caught up"


def test_format_maintenance_line_meter_task_with_no_readings_is_all_caught_up():
    # Honest — no logged reading means no evidence it's due, not a fabricated overdue count.
    tasks = [_meter_task()]
    assert format_maintenance_line(tasks, date(2026, 9, 7), {}) == "All caught up"


def test_format_observations_line_none_open():
    assert format_observations_line([]) == "All caught up"


def test_format_observations_line_singular():
    insight = Insight(insight_id="i1", source_type="maintenance", source_id="t1", kind="overdue", title="T", message="M")
    assert format_observations_line([insight]) == "1 thing noticed"


def test_format_observations_line_plural():
    insights = [
        Insight(insight_id="i1", source_type="maintenance", source_id="t1", kind="overdue", title="T", message="M"),
        Insight(insight_id="i2", source_type="missions", source_id="m1", kind="stale", title="T2", message="M2"),
    ]
    assert format_observations_line(insights) == "2 things noticed"


def _bill(due_date="2026-09-07", recurrence=None, last_paid_date=None):
    return Bill(bill_id="b1", name="Electric", amount=120.0, due_date=due_date, recurrence=recurrence, last_paid_date=last_paid_date)


def test_format_budget_line_no_bills():
    assert format_budget_line([], date(2026, 9, 7)) == "No bills tracked yet."


def test_format_budget_line_all_paid():
    bills = [_bill(due_date="2026-09-01", recurrence="monthly", last_paid_date="2026-09-01")]
    assert format_budget_line(bills, date(2026, 9, 7)) == "All bills paid"


def test_format_budget_line_overdue():
    bills = [_bill(due_date="2026-08-01")]
    assert format_budget_line(bills, date(2026, 9, 7)) == "1 overdue bill"


def test_format_budget_line_due_soon():
    bills = [_bill(due_date="2026-09-10")]
    assert format_budget_line(bills, date(2026, 9, 7)) == "1 bill due within 7 days"


def test_format_property_portfolio_line_no_properties():
    assert format_property_portfolio_line([]) == "No properties tracked yet."


def test_format_property_portfolio_line_sums_equity_across_properties():
    properties = [
        Property(property_id="p1", name="123 Main St", current_value=280000.0, mortgage_balance=150000.0),
        Property(property_id="p2", name="456 Oak Ave", current_value=200000.0, mortgage_balance=200000.0),
    ]
    assert format_property_portfolio_line(properties) == "2 properties  —  $130,000 total equity"


def test_format_net_worth_line_property_portfolio_equity_alone():
    assert format_net_worth_line([], property_portfolio_equity=130000.0) == "$130,000  —  from 1 source"


def test_format_net_worth_line_combines_snapshots_and_property_portfolio_equity():
    snapshots = [_snapshot("kraken_trading_agent", {"total_value": 8500})]
    result = format_net_worth_line(snapshots, property_portfolio_equity=130000.0)
    assert result == "$138,500  —  from 2 sources"


def test_format_net_worth_line_none_property_equity_behaves_as_before():
    snapshots = [_snapshot("real_estate_portfolio", {"total_value": 540000})]
    assert format_net_worth_line(snapshots, property_portfolio_equity=None) == "$540,000  —  from 1 source"


def test_format_net_worth_line_no_data_at_all_still_says_no_snapshots():
    assert format_net_worth_line([], property_portfolio_equity=None) == "No financial snapshots imported yet."


def test_format_music_line_nothing_playing():
    assert format_music_line(None) == "Nothing playing"


def test_format_music_line_playing_with_artist():
    now_playing = NowPlaying(
        track_id="t1", title="Blue Skies", artist="Sam", album="Weather",
        position_seconds=10, duration_seconds=200, is_playing=True, volume_percent=70,
    )
    assert format_music_line(now_playing) == "Playing: Blue Skies — Sam"


def test_format_music_line_paused():
    now_playing = NowPlaying(
        track_id="t1", title="Blue Skies", artist="Sam", album="Weather",
        position_seconds=10, duration_seconds=200, is_playing=False, volume_percent=70,
    )
    assert format_music_line(now_playing) == "Paused: Blue Skies — Sam"


def test_format_music_line_no_artist_omits_dash():
    now_playing = NowPlaying(
        track_id="t1", title="Untitled Track", artist="", album="",
        position_seconds=0, duration_seconds=200, is_playing=True, volume_percent=70,
    )
    assert format_music_line(now_playing) == "Playing: Untitled Track"
