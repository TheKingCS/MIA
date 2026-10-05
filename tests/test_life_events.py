"""
Life events (core/life_events.py), Engine Phase 1 step 1, 2026-10-05:
the append-only history beside the stores. What happened, who did it
and how, in the folder the data lives in.
"""

import json
from datetime import date

import pytest

from core import life_events
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_life_event_actions import _action_get_life_events
from core.child_accounts import make_child
from core.gamification import SkillWeight
from core.life_events import LifeEventLog, acting, events_for, quiet
from core.undo_log import undo_last
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    return build_world(tmp_path, monkeypatch)


def _types(context, **kwargs):
    return [e.type for e in events_for(context, **kwargs)]


def test_record_and_read_back(world):
    log = world.life_events
    event = log.record("task_done", "Done: sweep", ["task:t1"], {"n": 1})
    [back] = log.all_events()
    assert (back.type, back.summary, back.refs, back.payload) == ("task_done", "Done: sweep", ["task:t1"], {"n": 1})
    assert back.source == "manual" and back.profile_id == world.me.profile_id and back.event_id == event.event_id
    assert life_events.record(None, "task_done", "nowhere") is None


def test_quiet_and_acting(world):
    with quiet():
        world.life_events.record("task_done", "hidden")
    with acting("import", world.other.profile_id):
        world.life_events.record("imported", "x")
    [event] = world.life_events.all_events()
    assert (event.source, event.profile_id) == ("import", world.other.profile_id)


def test_a_damaged_line_is_skipped_not_fatal(world):
    world.life_events.record("task_done", "one")
    with open(world.life_events.path, "a", encoding="utf-8") as handle:
        handle.write("{not json\n\n")
    world.life_events.record("task_done", "two")
    assert [e.summary for e in world.life_events.all_events()] == ["one", "two"]


def test_paying_a_bill_is_one_event_and_leaves_the_due_list(world):
    from core.today import today_items

    bill = world.budget.add_bill("Electric", 120.0, date.today().isoformat())
    assert any(i.title == "Pay Electric" for i in today_items(world))
    world.budget.mark_bill_paid(bill.bill_id)
    assert _types(world) == ["bill_paid"]  # not also an "expense_added"
    [event] = events_for(world)
    assert f"bill:{bill.bill_id}" in event.refs and event.payload["amount"] == 120.0
    assert not any(i.title == "Pay Electric" for i in today_items(world))  # the store's state moved on


def test_money_events(world):
    world.budget.add_expense(40.0, "Groceries", "Market")
    world.budget.add_expense(9.0, "Entertainment", "Stream", plaid_transaction_id="tx1")
    source = world.budget.add_income_source("Pay", 1000.0, date.today().isoformat())
    world.budget.mark_income_received(source.source_id)
    debt = world.budget.add_debt("Card", 500.0, 20.0)
    world.budget.record_debt_payment(debt.debt_id, 100.0)
    events = list(reversed(events_for(world)))
    assert [e.type for e in events] == ["expense_added", "expense_added", "income_received", "debt_payment"]
    assert events[1].source == "import" and events[3].payload["balance"] == 400.0


def test_rent_goes_to_the_budget_folder_as_one_event(world):
    prop = world.real_estate.add_property("Rental A")
    world.real_estate.record_rental_income(prop.property_id, 600.0)
    assert _types(world) == ["rent_received"]
    assert f"property:{prop.property_id}" in events_for(world)[0].refs


def test_a_completed_mission_logs_skill_evidence(world):
    mission = world.missions.add_mission("Clean the shed", reward_xp=10,
                                         skill_rewards=[SkillWeight("organization", 15), SkillWeight("repair", 5)])
    world.missions.update_mission(mission.mission_id, status="completed")
    log = LifeEventLog(world, world.device_dir)  # Missions are device-level: data/
    types = sorted(e.type for e in log.all_events())
    assert types == ["mission_completed", "skill_evidence", "skill_evidence"]
    evidence = [e for e in log.all_events() if e.type == "skill_evidence"]
    assert {e.refs[0] for e in evidence} == {"skill:organization", "skill:repair"}
    assert all(f"mission:{mission.mission_id}" in e.refs for e in evidence)


def test_workouts_are_personal_maintenance_and_tasks_are_household(world):
    world.workout.add_session(duration_minutes=30)
    asset = world.maintenance.add_asset("Mower", "Power Equipment")
    task = world.maintenance.add_task(asset.asset_id, "Sharpen blades", interval_days=90)
    world.maintenance.mark_complete(task.task_id)
    project = world.projects.add_project("Shed")
    todo = world.tasks.add_task(project.project_id, "Buy screws")
    world.tasks.update_task(todo.task_id, notes="the long ones")  # not done: nothing
    world.tasks.toggle_done(todo.task_id)
    world.tasks.toggle_done(todo.task_id)  # undone again
    world.tasks.toggle_done(todo.task_id)  # done again: a second real completion
    assert [e.type for e in world.personal_life_events.all_events()] == ["workout_logged"]
    assert [e.type for e in world.life_events.all_events()] == ["maintenance_done", "task_done", "task_done"]
    assert sorted(_types(world)) == ["maintenance_done", "task_done", "task_done", "workout_logged"]


def test_the_assistant_s_changes_are_marked_as_hers(world):
    registry = AssistantActionRegistry()
    registry.register(AssistantAction("pay", "Pay.", {"type": "object", "properties": {}},
                                      lambda ctx, args: ctx.budget.add_expense(5.0, "Other", "Tip") and "ok",
                                      (), "budget"))
    registry.execute(world, "pay", {})
    [event] = events_for(world)
    assert (event.source, event.profile_id) == ("assistant", world.me.profile_id)


def test_undo_adds_to_history_instead_of_erasing_it(world):
    registry = AssistantActionRegistry()
    registry.register(AssistantAction("add_expense", "Add.", {"type": "object", "properties": {}},
                                      lambda ctx, args: ctx.budget.add_expense(5.0, "Other", "Oops") and "ok",
                                      (), "budget"))
    registry.execute(world, "add_expense", {})
    assert world.budget.all_expenses()
    undo_last(world, world.me.profile_id)
    assert world.budget.all_expenses() == []
    assert _types(world) == ["undone", "expense_added"]


def test_an_import_is_one_event(world, tmp_path):
    from core import imports

    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n10/01/2026,SHOP,-5.00\n10/02/2026,CAFE,-3.00\n")
    imports.run(world, tmp_path / "bank.csv")
    [event] = events_for(world)
    assert (event.type, event.source, event.payload["added"]) == ("imported", "import", 2)


def test_filters_and_a_child_never_sees_money(world):
    world.budget.add_expense(5.0, "Other", "Snack")
    world.workout.add_session(duration_minutes=10)
    assert _types(world, types=["workout_logged"]) == ["workout_logged"]
    assert _types(world, since="2999-01-01") == []
    kid = world.profiles.create_profile("Ari", make_active=False)
    make_child(world, kid.profile_id, [world.me.profile_id])
    world.profiles.set_active_profile(kid.profile_id)
    assert "expense_added" not in _types(world)


def test_what_did_i_get_done(world):
    world.workout.add_session(duration_minutes=20)
    world.workout.add_session(duration_minutes=25)
    bill = world.budget.add_bill("Water", 30.0, date.today().isoformat())
    world.budget.mark_bill_paid(bill.bill_id)
    reply = _action_get_life_events(world, {"period": "this week"})
    assert reply.startswith("Done in the last 7 days: 2 workouts, 1 bills paid.")
    assert "Paid Water" in _action_get_life_events(world, {"kind": "bills"})
    assert life_events.describe([], "month") == "Nothing recorded in the last 30 days yet."


def test_the_file_is_plain_json_lines(world):
    world.life_events.record("task_done", "Done: x", ["task:1"])
    line = world.life_events.path.read_text(encoding="utf-8").strip()
    assert json.loads(line)["type"] == "task_done"


def test_personal_data_gives_each_household_and_person_their_own_log(tmp_path, monkeypatch):
    from core.personal_data import HOUSEHOLD_ATTRIBUTES, PERSONAL_ATTRIBUTES

    assert "life_events" in HOUSEHOLD_ATTRIBUTES and "personal_life_events" in PERSONAL_ATTRIBUTES
