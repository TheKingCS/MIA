"""
tests.test_step_plans
=======================

Plans across apps (UI-7, core/step_plans.py; REQ-FUN-220): a plan shows every step with its app, tier, reach and
whether it can be undone; nothing runs when a plan is made; the person does, changes or drops steps one at a time;
a kind that reaches outside, can't be undone or is tiered never is listed as "can't" and is never run from a plan;
a step is checked again when it's done; undoing a step puts back its change and the step waits again; a plan is a
run that waits on the person; the week's plan comes from today's list in code; and voice does what the screen does.
Opus's review (2026-11-17): nothing that pays, buys, sends, publishes, deletes or touches a grant is a step (marking a
bill paid is bookkeeping); the card pins the step it showed; a finished plan takes no more changes; a failed step can
be tried again; and doing a step by voice never rides along with other calls.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from core import step_plans
from core.actions import ACTION_TYPES, ActionError, ActionType
from core.runs import RunBook
from core.shelf import Shelf
from core.step_plans import CANT, DONE, DROPPED, FAILED, WAITING, PlanError, StepPlanBook
from tests.test_crafting import shop  # noqa: F401  (the fixture)

ITEMS = [{"kind": "mission.add", "params": {"name": "Stake the tomatoes"}, "source": "Storm on Friday"},
         {"kind": "shelf.keep", "params": {"text": "Drip line on a timer"}, "source": "Something to read"},
         {"kind": "mission.add", "params": {"name": "Order seed"}, "source": "Spring is coming"}]


@pytest.fixture
def world(shop, tmp_path):  # noqa: F811
    """The crafting test world with the person's plans, shelf and run book on their own folders."""
    shop.step_plans = StepPlanBook(shop, data_dir=tmp_path / "plans")
    shop.shelf = Shelf(shop, data_dir=tmp_path / "shelf")
    shop.runs = RunBook(shop, data_dir=tmp_path / "runs")
    return shop


def test_making_a_plan_changes_nothing_and_shows_every_step_with_its_app_tier_and_reach(world):
    missions = len(world.missions.all_missions())
    plan = world.step_plans.make(world, "Get ready", ITEMS)
    assert len(world.missions.all_missions()) == missions and world.shelf.entries() == []
    assert [s.status for s in plan.steps] == [WAITING] * 3
    first = step_plans.step_dict(plan, plan.steps[0])
    assert first["number"] == 1 and "Stake the tomatoes" in first["summary"] and first["source"] == "Storm on Friday"
    assert first["tier"] and first["reach"] == "records" and first["reversibility"] == "undoable" and first["app"]
    assert plan.steps[1].app != plan.steps[0].app  # two apps in one plan
    page = step_plans.page(world)
    assert page["open"][0]["waiting"] == 3 and len(page["open"][0]["steps"]) == 3


def test_steps_are_done_changed_and_dropped_one_at_a_time(world):
    plan = world.step_plans.make(world, "Get ready", ITEMS)
    missions = len(world.missions.all_missions())
    done = world.step_plans.do(world, plan.plan_id, "1")
    assert done.status == DONE and len(world.missions.all_missions()) == missions + 1
    assert world.shelf.entries() == [] and [s.status for s in plan.steps] == [DONE, WAITING, WAITING]
    changed = world.step_plans.change(world, plan.plan_id, 3, {"name": "Order tomato seed", "not_a_field": "x"})
    assert "Order tomato seed" in changed.summary and "not_a_field" not in changed.params
    with pytest.raises(PlanError):
        world.step_plans.change(world, plan.plan_id, 3, {"name": ""})
    assert plan.steps[2].params["name"] == "Order tomato seed"  # a refused change leaves the step as it was
    world.step_plans.drop(world, plan.plan_id, 2)
    assert plan.steps[1].status == DROPPED and world.shelf.entries() == [] and plan.status == "open"
    with pytest.raises(PlanError, match="already done"):
        world.step_plans.do(world, plan.plan_id, 1)
    world.step_plans.do(world, plan.plan_id, 3)
    assert plan.status == "done" and world.step_plans.open_plans() == []
    assert any(m.name == "Order tomato seed" for m in world.missions.all_missions())


def test_a_kind_that_reaches_outside_cant_be_undone_or_is_unknown_is_never_a_step(world, monkeypatch):
    from core import action_effects, grants

    ran = []
    for kind in ("test.outward", "test.forever", "test.never"):
        monkeypatch.setitem(ACTION_TYPES, kind, ActionType(kind, "Go", {}, lambda c, p: "It goes",
                                                           lambda c, p, k=kind: ran.append(k) or "Went"))
    monkeypatch.setitem(action_effects.EFFECTS, "test.outward", ("outside", "undoable", "a test"))
    monkeypatch.setitem(action_effects.EFFECTS, "test.forever", ("records", "irreversible", "a test"))
    real = grants.tier_of
    monkeypatch.setattr(grants, "tier_of", lambda c: grants.NEVER if c == "test.never" else real(c))
    plan = world.step_plans.make(world, "Mixed", [{"kind": k, "params": {}} for k in
                                                  ("test.outward", "test.forever", "test.never", "no.such.kind",
                                                   "steps.do")] + ITEMS[:1])
    assert [s.status for s in plan.steps] == [CANT] * 5 + [WAITING]
    assert plan.steps[0].why == step_plans.ELSEWHERE and "no such action" in plan.steps[3].why
    for n in range(1, 6):
        with pytest.raises(PlanError):
            world.step_plans.do(world, plan.plan_id, n)
        with pytest.raises(PlanError):
            world.step_plans.change(world, plan.plan_id, n, {"x": 1})
    plan.steps[0].status = WAITING  # even a step forced to waiting is refused when it's done
    with pytest.raises(PlanError, match="can't be done here"):
        world.step_plans.do(world, plan.plan_id, 1)
    assert ran == []
    with pytest.raises(PlanError, match="Nothing in that"):
        world.step_plans.make(world, "Nothing", [{"kind": "test.outward", "params": {}}])


def test_a_step_is_checked_again_when_it_is_done_and_a_broken_one_fails_without_taking_the_plan(world, monkeypatch):
    """(The stand-in is "test.mark": a kind ending in .pay always asks, so it can't be a step.)"""
    state = {"ok": True}

    def describe(context, params):
        if not state["ok"]:
            raise ActionError("That bill is already paid.")
        return "Mark the bill paid"

    def execute(context, params):
        raise RuntimeError("disk on fire")

    monkeypatch.setitem(ACTION_TYPES, "test.mark", ActionType("test.mark", "Mark Paid", {}, describe, lambda c, p: "Paid"))
    monkeypatch.setitem(ACTION_TYPES, "test.break", ActionType("test.break", "Break", {}, lambda c, p: "Break it",
                                                               execute))
    plan = world.step_plans.make(world, "Bills", [{"kind": "test.mark", "params": {}},
                                                  {"kind": "test.break", "params": {}}] + ITEMS[:1])
    state["ok"] = False
    with pytest.raises(PlanError, match="already paid"):
        world.step_plans.do(world, plan.plan_id, 1)
    assert plan.steps[0].status == WAITING  # still his to change or drop
    broke = world.step_plans.do(world, plan.plan_id, 2)
    assert broke.status == FAILED and "RuntimeError" in broke.why and plan.status == "open"
    assert world.step_plans.do(world, plan.plan_id, 3).status == DONE


def test_doing_a_step_is_an_action_he_approves_and_undo_puts_back_the_change_and_the_step(world):
    plan = world.step_plans.make(world, "Get ready", ITEMS)
    proposal = world.actions.propose(world, "steps.do", {"plan_id": plan.plan_id, "step_id": "2"})
    assert "Drip line on a timer" in proposal.summary and "step 2 of 3" in proposal.summary
    assert world.shelf.entries() == [] and plan.steps[1].status == WAITING  # proposing ran nothing
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed" and [e.text for e in world.shelf.entries()] == ["Drip line on a timer"]
    assert "Next: step 1" in done.result
    world.actions.undo(world, done.proposal_id)
    world.shelf._load()
    world.step_plans._load()
    assert world.shelf.entries() == []
    assert world.step_plans.get(plan.plan_id).steps[1].status == WAITING
    with pytest.raises(ActionError, match="no step 9"):
        world.actions.propose(world, "steps.do", {"plan_id": plan.plan_id, "step_id": "9"})


def test_a_plan_is_a_run_that_waits_on_him_and_ends_when_the_plan_does(world):
    plan = world.step_plans.make(world, "Get ready", ITEMS)
    [run] = world.runs.open_runs()
    assert run.source == "plans" and run.ref == f"step_plan:{plan.plan_id}" and run.status == "waiting"
    assert "Stake the tomatoes" in run.waiting["text"]
    world.step_plans.do(world, plan.plan_id, 1)
    assert run.status == "waiting" and run.at == "2" and len(run.steps) == 1 and run.steps[0]["actions"] == ["mission.add"]
    world.step_plans.drop_plan(world, plan.plan_id)
    assert run.status == "stopped" and "dropped" in run.why and world.runs.open_runs() == []
    assert [s.status for s in plan.steps] == [DONE, DROPPED, DROPPED] and plan.status == "dropped"
    other = world.step_plans.make(world, "Short", ITEMS[:1])
    world.step_plans.do(world, other.plan_id, 1)
    assert world.runs.open_runs() == [] and other.status == "done"


def test_the_weeks_plan_comes_from_todays_list_in_code_and_is_made_once(world, monkeypatch):
    import core.today as today

    items = [SimpleNamespace(title="Stake the tomatoes", detail="overdue 2 days",
                             action={"kind": "mission.add", "label": "Add", "params": {"name": "Stake the tomatoes"}}),
             SimpleNamespace(title="Dentist at 3", detail="", action=None),
             SimpleNamespace(title="Read later", detail="", action={"kind": "shelf.keep", "params": {"text": "An article"}})]
    monkeypatch.setattr(today, "today_items", lambda context, day=None: items)
    plan = step_plans.plan_week(world, date(2026, 11, 16))
    assert plan.title == "Your week, from Monday 16 November" and plan.made_by == "mia"
    assert [s.source for s in plan.steps] == ["Stake the tomatoes (overdue 2 days)", "Read later"]
    with pytest.raises(PlanError, match="already open"):
        step_plans.plan_week(world, date(2026, 11, 16))
    monkeypatch.setattr(today, "today_items", lambda context, day=None: items[1:2])
    with pytest.raises(PlanError, match="Nothing due"):
        step_plans.plan_week(world, date(2026, 11, 17))


def test_plans_survive_a_restart_and_old_finished_ones_are_let_go(world, tmp_path, monkeypatch):
    plan = world.step_plans.make(world, "Get ready", ITEMS)
    world.step_plans.do(world, plan.plan_id, 1)
    again = StepPlanBook(world, data_dir=tmp_path / "plans")
    back = again.get(plan.plan_id)
    assert [s.status for s in back.steps] == [DONE, WAITING, WAITING] and back.steps[0].result
    monkeypatch.setattr(step_plans, "KEEP_FINISHED", 2)
    for n in range(4):
        p = again.make(world, f"Plan {n}", ITEMS[1:2])
        again.drop_plan(world, p.plan_id)
    assert sum(1 for p in again.plans.values() if p.status != "open") == 2 and plan.plan_id in again.plans


def test_voice_reads_the_plan_and_does_and_drops_steps_by_number(world):
    from core.assistant_taught_skill_actions import _plan_step, _the_plan

    assert "no plan open" in _the_plan(world, {})
    plan = world.step_plans.make(world, "Get ready", ITEMS)
    said = _the_plan(world, {})
    assert said.startswith("Get ready: 3 steps waiting for you.") and "1. " in said and "Nothing runs until you say" in said
    assert "Next: step 2" in _plan_step("steps.do")(world, {"step": "1"})
    assert "Left out" in _plan_step("steps.drop")(world, {"step": "2"})
    assert "no step 7" in _plan_step("steps.do")(world, {"step": "7"})
    assert [s.status for s in plan.steps] == [DONE, DROPPED, WAITING]


def test_no_kind_that_pays_buys_sends_publishes_deletes_or_touches_a_grant_is_ever_a_step():
    from core.taught_skills import always_asks

    let_through = [kind for kind in ACTION_TYPES
                   if not step_plans._allowed(kind) and (always_asks(kind) or kind.startswith("grant."))]
    assert sorted(let_through) == sorted(step_plans.BOOKKEEPING)  # marking a bill or debt paid moves no money
    for kind in ("shop.buy", "order.pay", "quote.send", "quote.email", "creation.publish", "mission.delete",
                 "grant.take_back", "taught_skill.keep", "profile.edit", "freedom.fund_account"):
        assert step_plans._allowed(kind) == step_plans.ELSEWHERE, kind


def test_the_approval_card_pins_the_step_so_a_change_before_the_press_is_refused(world):
    plan = world.step_plans.make(world, "Get ready", ITEMS)
    proposal = world.actions.propose(world, "steps.do", {"plan_id": plan.plan_id, "step_id": "1"})
    assert proposal.params["seen"] == step_plans.fingerprint(plan.steps[0])
    world.step_plans.change(world, plan.plan_id, 1, {"name": "Something else entirely"})
    missions = len(world.missions.all_missions())
    refused = world.actions.approve(world, proposal.proposal_id)
    assert refused.status == "failed" and "changed since you saw it" in refused.result
    assert len(world.missions.all_missions()) == missions and plan.steps[0].status == WAITING


def test_a_finished_or_dropped_plan_cant_be_changed_or_done_again(world, monkeypatch):
    monkeypatch.setitem(ACTION_TYPES, "test.no", ActionType("test.no", "No", {"x": "x"},
                                                            lambda c, p: (_ for _ in ()).throw(ActionError("not now")),
                                                            lambda c, p: "ran"))
    plan = world.step_plans.make(world, "Short", ITEMS[:1] + [{"kind": "test.no", "params": {"x": "1"}}])
    assert plan.steps[1].status == CANT
    world.step_plans.drop_plan(world, plan.plan_id)
    for call in (lambda: world.step_plans.change(world, plan.plan_id, 2, {"x": "2"}),
                 lambda: world.step_plans.do(world, plan.plan_id, 1),
                 lambda: world.step_plans.drop(world, plan.plan_id, 1)):
        with pytest.raises(PlanError):
            call()
    assert plan.status == "dropped" and [s.status for s in plan.steps] == [DROPPED, CANT]


def test_a_failed_step_can_be_tried_again_and_its_failure_is_said_not_raised(world, monkeypatch):
    tries = []

    def execute(context, params):
        tries.append(1)
        if len(tries) == 1:
            raise ActionError("the disk was busy")
        return "Done at last"

    monkeypatch.setitem(ACTION_TYPES, "test.flaky", ActionType("test.flaky", "Go", {}, lambda c, p: "Try it", execute))
    plan = world.step_plans.make(world, "Flaky", [{"kind": "test.flaky", "params": {}}])
    proposal = world.actions.propose(world, "steps.do", {"plan_id": plan.plan_id, "step_id": "1"})
    first = world.actions.approve(world, proposal.proposal_id)
    assert first.status == "executed" and "didn't work" in first.result and "the disk was busy" in first.result
    assert plan.steps[0].status == FAILED and plan.status == "open"
    assert world.step_plans.do(world, plan.plan_id, 1).status == DONE and plan.status == "done"


def test_doing_a_step_by_voice_is_never_run_when_bundled_with_other_calls():
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_taught_skill_actions import register_taught_skill_actions

    registry = AssistantActionRegistry()
    register_taught_skill_actions(registry)
    assert registry.is_destructive("do_plan_step") and not registry.is_destructive("whats_the_plan")
