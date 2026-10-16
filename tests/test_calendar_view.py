"""
The Calendar (Zac, 2026-10-16: "I want the Calendar to be filled and I
want to be able to access it both in the app and on the glasses"):
core/calendar_view.py fills it from everything with a date, sorted Past
Due / Due Today / Due Soon; your own events are actions.
"""

from datetime import date, timedelta

import pytest

from core.actions import ActionCenter, ActionError
from core.calendar_view import calendar_items, calendar_page, day_label
from core.child_accounts import make_child
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.budget.add_bill("Electric", 120.0, (TODAY - timedelta(days=2)).isoformat(), recurrence="monthly")
    mower = context.maintenance.add_asset("Mower", category="Power Equipment")
    context.maintenance.add_task(mower.asset_id, "Check oil", interval_days=30,
                                 last_completed=(TODAY - timedelta(days=40)).isoformat())
    return context


def test_day_labels():
    assert day_label(TODAY, TODAY) == "Today" and day_label(TODAY + timedelta(days=1), TODAY) == "Tomorrow"
    assert day_label(date(2026, 10, 18), date(2026, 10, 16)) == "Sun, Oct 18"


def test_the_calendar_is_filled_from_everything_with_a_date(world):
    world.calendar.add_event("Trash day", TODAY.isoformat(), recurrence="weekly")
    world.calendar.add_event("Dentist", (TODAY + timedelta(days=3)).isoformat(), "09:30")
    page = calendar_page(world, TODAY)

    late = {i["title"] for i in page["past_due"]}
    assert any(t.startswith("Electric") for t in late) and "Check oil: Mower" in late
    assert all(i["due"] for i in page["past_due"])
    assert "Trash day" in {i["title"] for i in page["today"]}
    soon = {i["title"]: g["label"] for g in page["soon"] for i in g["items"]}
    assert soon.get("Dentist") == day_label(TODAY + timedelta(days=3), TODAY)
    # a weekly event repeats a week later
    assert any(i["title"] == "Trash day" for g in page["soon"] for i in g["items"]
               if g["date"] == (TODAY + timedelta(days=7)).isoformat())
    # the month grid marks today and has whole weeks
    days = page["month"]["days"]
    assert len(days) % 7 == 0 and sum(d["today"] for d in days) == (1 if TODAY.month == date.fromisoformat(
        page["month"]["key"] + "-01").month else 0)
    oil = next(i for i in page["past_due"] if i["title"] == "Check oil: Mower")
    assert oil["action"]["kind"] == "maintenance.done" and oil["kind_label"] == "Upkeep"


def test_adding_and_removing_your_own_events(world):
    p = world.actions.propose(world, "event.add", {"title": "Vet", "date": TODAY.isoformat(), "time": "2:30 pm"})
    assert p.summary.startswith('Add "Vet" to the calendar') and "14:30" in p.summary
    world.actions.approve(world, p.proposal_id)
    vet = next(i for i in calendar_items(world, TODAY, TODAY, TODAY) if i["title"] == "Vet")
    assert vet["time"] == "14:30" and vet["event_id"]
    with pytest.raises(ActionError):
        world.actions.propose(world, "event.add", {"title": "", "date": TODAY.isoformat()})
    with pytest.raises(ActionError):
        world.actions.propose(world, "event.add", {"title": "X", "date": "someday"})
    world.actions.approve(world, world.actions.propose(world, "event.delete", {"event_id": vet["event_id"]}).proposal_id)
    assert not any(i["title"] == "Vet" for i in calendar_items(world, TODAY, TODAY, TODAY))


def test_a_child_calendar_has_no_money(world):
    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert not any(i["kind"] in ("bill", "income") for i in calendar_items(world, TODAY, TODAY + timedelta(days=30), TODAY))


def test_the_glasses_calendar(world):
    from core.glasses import glasses_apps, glasses_panel

    card = next(a for a in glasses_apps(world, TODAY)["apps"] if a["id"] == "calendar")
    assert [m["label"] for m in card["menu"] if m["type"] == "panel"] == ["Past Due", "Due Today", "Due Soon"]
    assert "past due" in card["status"]
    late = glasses_panel(world, "calendar", "past_due", TODAY)
    oil = next(line for line in late["lines"] if line["text"] == "Check oil: Mower")
    assert oil["action"]["kind"] == "maintenance.done"
    electric = next(line for line in late["lines"] if line["text"].startswith("Electric"))
    assert "action" not in electric  # money stays readouts on the glasses
