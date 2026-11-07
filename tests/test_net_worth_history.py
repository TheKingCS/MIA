"""Tests for core/net_worth_history.py: one net worth point a day, the change this month, and the Overview's line."""

from datetime import date

from core import net_worth_history as nwh
from core.net_worth_history import NetWorthHistory


def test_a_day_keeps_one_point_and_the_last_reading_wins():
    points = []
    assert nwh.add_point(points, date(2026, 11, 7), 1000)
    assert not nwh.add_point(points, date(2026, 11, 7), 1000)  # same total: nothing to write
    assert nwh.add_point(points, date(2026, 11, 7), 1250.555)
    assert points == [{"date": "2026-11-07", "total": 1250.56}]


def test_nothing_to_add_up_records_no_point():
    points = []
    assert not nwh.add_point(points, date(2026, 11, 7), None)
    assert points == []


def test_points_older_than_two_years_are_dropped():
    points = [{"date": "2024-01-01", "total": 5.0}]
    nwh.add_point(points, date(2026, 11, 7), 10)
    assert [p["date"] for p in points] == ["2026-11-07"]


def test_the_month_change_is_from_the_months_first_point():
    points = [{"date": "2026-10-20", "total": 900.0}, {"date": "2026-11-02", "total": 1000.0},
              {"date": "2026-11-07", "total": 1300.0}]
    assert nwh.month_change(points, date(2026, 11, 7)) == 300.0


def test_with_only_today_this_month_the_change_is_from_the_last_point_before_it():
    points = [{"date": "2026-10-20", "total": 900.0}, {"date": "2026-11-07", "total": 1300.0}]
    assert nwh.month_change(points, date(2026, 11, 7)) == 400.0


def test_with_one_point_there_is_no_change_to_show():
    assert nwh.month_change([{"date": "2026-11-07", "total": 1.0}], date(2026, 11, 7)) is None
    assert nwh.month_change([], date(2026, 11, 7)) is None


def test_the_line_is_the_last_six_months():
    points = [{"date": "2026-01-01", "total": 1.0}, {"date": "2026-10-01", "total": 2.0}]
    assert nwh.line(points, date(2026, 11, 7)) == [{"date": "2026-10-01", "total": 2.0}]


def test_the_store_writes_only_when_the_point_changes(tmp_path):
    store = NetWorthHistory(None, data_dir=tmp_path)
    store.note(500, date(2026, 11, 1))
    first = (tmp_path / "net_worth_history.json").stat().st_mtime_ns
    store.note(500, date(2026, 11, 1))
    assert (tmp_path / "net_worth_history.json").stat().st_mtime_ns == first
    store.note(800, date(2026, 11, 7))
    again = NetWorthHistory(None, data_dir=tmp_path)
    assert again.summary(date(2026, 11, 7)) == {
        "month_change": 300.0, "line": [{"date": "2026-11-01", "total": 500.0}, {"date": "2026-11-07", "total": 800.0}]}


def test_an_unreadable_history_file_starts_the_line_again(tmp_path):
    (tmp_path / "net_worth_history.json").write_text("{not json", encoding="utf-8")
    assert NetWorthHistory(None, data_dir=tmp_path).points == []
