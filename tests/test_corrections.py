"""Corrections in every area (build plan step 4, core/corrections.py): MIA's changes are watched for three
days; the person undoing one, or editing or deleting something of the same kind (the same record when both
name it), corrects her, once; the corrections.* loops count them by area. Kinds and ids only, never words."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import actions, corrections, loops
from core.actions import ActionCenter, ActionType

NOW = datetime(2026, 11, 6, 12, 0)
BY_ID = {l.id: l for l in loops.LOOPS}


def person(tmp_path):
    return SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path), traces=None)


def test_areas_and_ids():
    assert corrections.area_of("bill.add") == "money" and corrections.area_of("action_recipe.edit") == "kitchen"
    assert corrections.area_of("add_expense") == "money" and corrections.area_of("log_workout") == "workouts"
    assert corrections.area_of("zzz.add") == "other"
    assert corrections.ids_in({"bill_id": "b1", "id": 7, "name": "Rent", "amount": 1200}) == ["7", "b1"]


def test_an_edit_of_the_same_record_soon_after_corrects_her_once(tmp_path):
    who = person(tmp_path)
    corrections.mia_changed(who, "bill.add", {"title": "Rent"}, now=NOW)
    corrections.mia_changed(who, "bill.edit", {"bill_id": "b1", "amount": 1200}, now=NOW)
    assert corrections.person_changed(who, "bill.pay", {"bill_id": "b1"}, now=NOW) is None  # paying isn't correcting
    other = person(tmp_path / "other")
    corrections.mia_changed(other, "bill.edit", {"bill_id": "b1"}, now=NOW)
    assert corrections.person_changed(other, "bill.edit", {"bill_id": "b2"}, now=NOW) is None  # another bill
    first = corrections.person_changed(who, "bill.edit", {"bill_id": "b1", "amount": 1250}, now=NOW + timedelta(hours=2))
    assert first["kind"] == "bill.edit" and first["area"] == "money"
    again = corrections.person_changed(who, "bill.delete", {"bill_id": "b9"}, now=NOW + timedelta(hours=3))
    assert again["kind"] == "bill.add"  # an add can't know the new record's id: the same kind, soon after, counts
    assert corrections.person_changed(who, "bill.edit", {"bill_id": "b1"}, now=NOW + timedelta(hours=4)) is None
    late = person(tmp_path / "late")
    corrections.mia_changed(late, "recipe.add", {}, now=NOW)
    assert corrections.person_changed(late, "recipe.edit", {"recipe_id": "r1"}, now=NOW + timedelta(days=4)) is None
    text = (tmp_path / corrections.FILE_NAME).read_text(encoding="utf-8")
    assert "Rent" not in text and "1250" not in text  # what was in it never leaves the change


def test_the_loops_count_by_area(tmp_path):
    who = person(tmp_path)
    for n in range(6):
        corrections.mia_changed(who, "recipe.add", {}, now=datetime.now())
    corrections.mia_changed(who, "bill.add", {}, now=datetime.now())
    corrections.person_changed(who, "recipe.edit", {"recipe_id": "r1"})
    corrections.person_changed(who, "recipe.delete", {"recipe_id": "r2"})
    kitchen = BY_ID["corrections.kitchen"].measure(who)
    assert (kitchen.value, kitchen.n) == (0.33, 6) and "recipe.add 2" in kitchen.detail
    assert loops.judge(BY_ID["corrections.kitchen"], kitchen, [])["state"] == "below"
    assert BY_ID["corrections.money"].measure(who).value == 0.0
    assert BY_ID["corrections.all"].measure(who).n == 7
    assert BY_ID["corrections.workouts"].measure(who) is None


@pytest.fixture
def center(tmp_path, monkeypatch):
    made = []
    for kind, verb in (("recipe.add", "add"), ("recipe.edit", "edit")):
        monkeypatch.setitem(actions.ACTION_TYPES, kind, ActionType(
            kind, verb, {}, lambda c, p: "Do it", lambda c, p, k=kind: made.append(k) or "done"))
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    monkeypatch.setattr(actions, "_moment", lambda context, proposal: {})
    import core.profile_manager as pm
    from contextlib import nullcontext

    monkeypatch.setattr(pm, "crediting", lambda context, profile_id: nullcontext())
    return SimpleNamespace(c=ActionCenter(), context=SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path),
                                                                    config=None, undo=None), made=made)


def test_approved_actions_feed_it(center):
    hers = center.c.propose(center.context, "recipe.add", {"title": "Soup"}, proposed_by="mia")
    center.c.approve(center.context, hers.proposal_id)
    mine = center.c.propose(center.context, "recipe.edit", {"recipe_id": "r9", "title": "Better soup"})
    center.c.approve(center.context, mine.proposal_id)
    found = corrections.summary(center.context)
    assert center.made == ["recipe.add", "recipe.edit"]
    assert found["kitchen"] == {"changes": 1, "corrected": 1, "kinds": {"recipe.add": 1}}


def test_undoing_her_change_corrects_her(tmp_path):
    who = person(tmp_path)
    corrections.mia_changed(who, "add_expense", {"amount": 12}, now=datetime.now())
    assert corrections.undone(who, "add_expense")["how"] == "undo"
    assert corrections.undone(who, "add_expense") is None  # once
    corrections.mia_changed(who, "bill.add", {}, now=datetime.now())
    assert corrections.undone(who, "action_bill.add")["kind"] == "bill.add"


def test_undo_that_through_the_undo_log(tmp_path):
    from core.undo_log import Change, UndoLog, undo_last

    who = SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path), undo=UndoLog(), life_events=None)
    corrections.mia_changed(who, "add_expense", {}, now=datetime.now())
    kept = tmp_path / "budget.json"
    kept.write_text("new", encoding="utf-8")
    who.undo.add(Change("add_expense", "p1", files={kept: b"old"}, by="mia"))
    who.undo.add(Change("action_task.done", "p1", files={kept: b"older"}))  # the person's own: corrects no one
    undo_last(who, "p1")
    assert corrections.summary(who) == {"money": {"changes": 1, "corrected": 0, "kinds": {}}}
    undo_last(who, "p1")
    assert corrections.summary(who)["money"]["corrected"] == 1


def test_her_tools_are_matched_by_what_they_change():
    """A tool's name against an action's family: the same kind of record in the same area."""
    assert corrections._same_thing("add_calendar_event", "event") and corrections._same_thing("log_meal", "meal")
    assert corrections._same_thing("add_maintenance_task", "maintenance_task")
    assert not corrections._same_thing("add_task", "maintenance_task")  # a project task isn't an upkeep task
    assert not corrections._same_thing("add_recipe", "event")


def test_an_edit_on_a_desktop_screen_corrects_her_tool(tmp_path):
    from core import life_events

    who = person(tmp_path)
    corrections.mia_changed(who, "add_recipe", {"name": "Chili"})
    found = corrections.screen_edit(who, "recipe.edit", "r1")
    assert found["kind"] == "add_recipe" and found["area"] == "kitchen"
    corrections.mia_changed(who, "add_person", {"name": "Sam"})
    with life_events.acting("assistant"):  # inside an action or a tool: counted there, never twice
        assert corrections.screen_edit(who, "person.edit", "p1") is None
    assert corrections.screen_edit(who, "person.delete", "p1")["area"] == "people"
    assert corrections.screen_edit(None, "recipe.edit", "r1") is None  # no person: nothing kept, nothing raised
