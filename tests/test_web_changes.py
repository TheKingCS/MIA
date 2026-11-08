"""Recent Changes on the web (core/web_changes.py, DEC-0125): what MIA can put back, newest first, in the history's
own words; the fortnight's history by day with undone ones marked; and Undo as the action undo.last, which never
leaves a change of its own behind."""

from __future__ import annotations

from datetime import datetime

from core.actions import ActionCenter, ActionError
from core.web_changes import changes_page, label_words, when_words
from tests.engine_world import build_world


def test_labels_and_times_read_as_words():
    assert label_words("action_routine.add") == "Add Routine" and label_words("add_expense") == "add expense"
    now = datetime(2026, 11, 7, 18, 0)
    assert when_words("2026-11-07T14:05:00", now) == "2:05 PM"
    assert when_words("2026-11-06T09:10:00", now) == "yesterday 9:10 AM"
    assert when_words("2026-11-03T09:10:00", now) == "Nov 3" and when_words("soon", now) == ""


def test_a_change_is_listed_undone_from_the_page_and_the_undo_leaves_nothing_behind(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    center = ActionCenter()
    for t in world.recurring_missions.all_templates():
        world.recurring_missions.set_active(t.template_id, False)
    added = center.propose(world, "routine.add", {"name": "Trash to the road", "every": "week"})
    center.approve(world, added.proposal_id)
    page = changes_page(world)
    assert page["undoable"][0]["newest"] and page["undoable"][0]["by"] == "You"
    assert "Trash to the road" in page["undoable"][0]["what"] or page["undoable"][0]["what"] == "Add Routine"
    undo = center.propose(world, "undo.last", {})
    assert undo.summary.startswith("Undo: ")
    done = center.approve(world, undo.proposal_id)
    assert done.status == "executed", done.result
    assert not any(t.name == "Trash to the road" for t in world.recurring_missions.all_templates())
    assert changes_page(world)["undoable"] == []  # the undo itself is not a change to undo
    try:
        center.propose(world, "undo.last", {})
        raise AssertionError("nothing to undo should be refused")
    except ActionError as problem:
        assert str(problem) == "There's nothing of mine to undo right now."
