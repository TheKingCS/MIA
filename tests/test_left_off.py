"""
tests.test_left_off
=====================

Where he left off (core/left_off.py, brainstorm 1.2): missions changed lately with their next step, Planner drafts not
yet confirmed, open promises and recent decisions, from the records only.
"""

from datetime import datetime
from types import SimpleNamespace

from core import left_off

NOW = datetime(2026, 11, 23, 9, 0)


def _mission(name, at, done, status="active"):
    objs = [SimpleNamespace(description=d) for d, _ok in done]
    return SimpleNamespace(mission_id=name, name=name, status=status, updated_at=at, created_at=at, objectives=objs,
                           _done=[ok for _d, ok in done])


def _manager(missions):
    by = {m.mission_id: m for m in missions}
    return SimpleNamespace(all_missions=lambda: missions,
                           is_objective_complete=lambda mid, i: by[mid]._done[i])


def test_missions_changed_lately_come_with_their_next_step_newest_first():
    ctx = SimpleNamespace(missions=_manager([
        _mission("Build the coop", "2026-11-22T18:00:00", [("Frame the floor", True), ("Put up the walls", False)]),
        _mission("Fence the garden", "2026-11-20T10:00:00", [("Set the posts", True)]),
        _mission("Old one", "2026-09-01T10:00:00", [("Something", False)]),
        _mission("Done one", "2026-11-22T10:00:00", [("x", False)], status="completed")]))
    found = left_off.missions_in_motion(ctx, datetime(2026, 11, 9))
    assert [(m["name"], m["next"]) for m in found] == [("Build the coop", "Put up the walls"), ("Fence the garden", "")]


def test_only_recent_unconfirmed_drafts_are_named():
    plans = [SimpleNamespace(title="Coop floor", status="draft", updated_at="2026-11-21T10:00:00"),
             SimpleNamespace(title="Shed", status="confirmed", updated_at="2026-11-21T10:00:00"),
             SimpleNamespace(title="Old garden", status="draft", updated_at="2026-08-01T10:00:00")]
    ctx = SimpleNamespace(project_plans=SimpleNamespace(listed=lambda: plans))
    assert left_off.drafts(ctx, datetime(2026, 11, 9)) == ["Coop floor"]


def test_it_is_said_in_order_and_says_nothing_on_a_clean_slate():
    said = left_off.describe({"missions": [{"name": "Build the coop", "next": "Put up the walls", "at": ""}],
                              "drafts": ["Coop floor"], "promises": ["a promise to Sam: fix his gate"],
                              "decisions": ["a decision: 2x8 joists"]})
    assert said.index("Build the coop (next: Put up the walls)") < said.index("Coop floor") < said.index("Sam") \
        < said.index("2x8")
    assert left_off.describe({"missions": [], "drafts": [], "promises": [], "decisions": []}) == ""
    assert "Nothing's mid-way" in left_off.say(SimpleNamespace(missions=None, project_plans=None, life_notes=None))


def test_a_source_that_fails_never_stops_the_rest():
    broken = SimpleNamespace(all_missions=lambda: 1 / 0)
    ctx = SimpleNamespace(missions=broken, project_plans=SimpleNamespace(listed=lambda: [
        SimpleNamespace(title="Coop floor", status="draft", updated_at="2026-11-21T10:00:00")]), life_notes=None)
    assert left_off.gather(ctx, NOW)["drafts"] == ["Coop floor"]
