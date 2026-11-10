"""
tests.test_health
===================

Health (DEC-0129: core/health_manager.py, core/health_actions.py, core/assistant_health_actions.py): nights of sleep,
visits, medications with their reminders, and records, each change an action; what comes due shows on Today; the file
is sealed at rest; nothing about a medication's name reaches a shared alarm; and each change reaches the
person's history without its name or details.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.alarm_manager import AlarmManager
from core.assistant_health_actions import _log_sleep, _stop, _summary, _took
from core.at_rest import SEALED
from core.event_bus import EventBus
from core.health_actions import health_page
from core.health_manager import DOSE_LABEL, HealthStore, clean_times

TODAY = date.today()


@pytest.fixture
def context(tmp_path):
    """A person's health store and the device's alarms, in a temporary folder."""
    ctx = SimpleNamespace(events=EventBus(), config=None)
    ctx.alarms = AlarmManager(ctx, data_dir=tmp_path)
    ctx.health = HealthStore(ctx, data_dir=tmp_path)
    return ctx


def run(ctx, action, **params):
    """Runs one action."""
    return ACTION_TYPES[action].execute(ctx, params)


def test_times_are_read_the_ways_people_write_them():
    assert clean_times("8:00, 8 pm; 12am") == ["00:00", "08:00", "20:00"]
    with pytest.raises(ValueError):
        clean_times("25:00")


def test_a_night_logged_twice_is_replaced_and_the_week_averages_what_was_logged(context):
    night = (TODAY - timedelta(days=1)).isoformat()
    run(context, "sleep.log", hours="6", rested="3")
    run(context, "sleep.log", hours="7.5", rested="4", night=night)
    week = context.health.sleep_week(TODAY)
    assert week["nights"][-1] == {"night": night, "hours": 7.5, "rested": 4} and week["average"] == 7.5
    with pytest.raises(ActionError):
        run(context, "sleep.log", hours="30")


def test_a_medication_gets_daily_alarms_that_never_say_its_name(context):
    said = run(context, "med.add", name="Vitamin D3", dose="2000 IU", times="8:00, 20:00", kind="Supplement")
    assert "Reminders at 08:00, 20:00" in said
    alarms = context.alarms.all_alarms()
    assert {a.time for a in alarms} == {"08:00", "20:00"} and {a.label for a in alarms} == {DOSE_LABEL}
    med = context.health.meds[0]
    assert _took(context, {"name": "vitamin d"}) == "Logged Vitamin D3: 1 today."
    assert "reminders are off" in _stop(context, {"name": "vitamin d3"})
    assert context.alarms.all_alarms() == []
    run(context, "med.edit", med_id=med["id"], active="yes")
    assert len(context.alarms.all_alarms()) == 2
    run(context, "med.delete", med_id=med["id"])
    assert context.alarms.all_alarms() == [] and context.health.meds == []


def test_visits_and_refills_coming_due_show_on_today(context):
    from core.today import today_items

    run(context, "visit.add", kind="Dentist", when="2026-05-12", next_due=(TODAY + timedelta(days=2)).isoformat())
    run(context, "med.add", name="Allergy tablet", refill_on=(TODAY - timedelta(days=1)).isoformat())
    run(context, "visit.add", kind="Doctor", when="2026-09-03", next_due=(TODAY + timedelta(days=200)).isoformat())
    titles = {(i.title, i.when) for i in today_items(context, TODAY) if i.module_id == "health"}
    assert titles == {("Dentist visit due", "soon"), ("Refill Allergy tablet", "overdue")}


def test_records_and_the_page(context):
    run(context, "record.add", kind="Allergy", name="Penicillin", notes="Hives")
    page = health_page(context, TODAY)
    assert page["records"][0]["name"] == "Penicillin" and "alarm_ids" not in str(page["meds"])
    assert "1 health record kept" in _summary(context, {"what": "all"})
    assert health_page(SimpleNamespace()) == {"available": False}


def test_health_is_sealed_at_rest_and_saved(context, tmp_path):
    assert "health.json" in SEALED
    _log_sleep(context, {"hours": 8})
    assert HealthStore(context, data_dir=tmp_path).sleep[0]["hours"] == 8


def test_health_changes_reach_the_history_without_their_names(context, tmp_path):
    """A night, a visit, a medication and a record each note a life event in the person's own folder; none says
    the medication's name, the dose or the visit's reason."""
    from core.life_events import LifeEventLog

    store = context.health
    store.log_sleep(7.5, rested=4)
    store.add_visit("Dentist", "2026-11-01", who="Dr. Example", what_for="cleaning")
    store.add_med("Exampleprofen", dose="200 mg")
    store.add_record("Allergy", "Penicillin")
    events = [e for e in LifeEventLog(None, store.data_dir).all_events()]
    assert [e.type for e in events] == ["sleep_logged", "visit_added", "medication_added", "health_record_added"]
    said = " ".join(e.summary for e in events)
    for secret in ("Exampleprofen", "200 mg", "cleaning", "Dr. Example", "Penicillin"):
        assert secret not in said, secret
