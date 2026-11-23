"""
tests.test_homestead_year
===========================

The homestead's year (core/homestead_year.py, brainstorm 4.4): his confirmed garden plans' crop dates and his
recurring upkeep, month by month over the next twelve, from his own records.
"""

from datetime import date
from types import SimpleNamespace

from core import homestead_year as hy

TODAY = date(2026, 11, 23)
END = date(2027, 11, 30)


def _garden(crops, status="confirmed"):
    return SimpleNamespace(kind="garden", status=status, last_frost="April 20", first_frost="October 15",
                           crops=[{"crop": c} for c in crops])


def test_crop_dates_come_from_his_frost_dates_and_only_confirmed_plans():
    items = hy.garden_items([_garden(["tomato"]), _garden(["corn"], status="draft")], TODAY, END)
    whats = [w for _d, w in items]
    assert "Start tomatoes indoors" in whats and "Transplant tomatoes" in whats
    assert any(w.startswith("Tomatoes ready to harvest") for w in whats)
    assert not any("corn" in w.lower() for w in whats)
    assert all(TODAY <= d <= END for d, _w in items)


def test_recurring_upkeep_falls_in_each_month_it_comes():
    task = SimpleNamespace(trigger_type="calendar", interval_days=90, last_completed="2026-10-01", title="Clean the coop")
    once = SimpleNamespace(trigger_type="calendar", interval_days=None, last_completed=None, title="Fix the gate")
    days = [d for d, _t in hy.upkeep_items([task, once], TODAY, END)]
    assert days[0] == date(2026, 12, 30) and len(days) == 4


def test_the_year_is_months_in_order_and_said_a_few_at_a_time():
    ctx = SimpleNamespace(project_plans=SimpleNamespace(listed=lambda: [_garden(["tomato", "lettuce"])]),
                          maintenance=SimpleNamespace(all_tasks=lambda: [SimpleNamespace(
                              trigger_type="calendar", interval_days=30, last_completed="2026-11-10",
                              title="Check the fence")]))
    months = hy.year(ctx, TODAY)
    assert [m["month"] for m in months] == sorted(m["month"] for m in months) and months[0]["month"] == "2026-12"
    said = hy.say(ctx, TODAY)
    assert said.startswith("December 2026: Check the fence") and "more month" in said


def test_with_nothing_planned_she_says_how_to_fill_it():
    assert "confirm a garden plan" in hy.say(SimpleNamespace(project_plans=None, maintenance=None), TODAY)
