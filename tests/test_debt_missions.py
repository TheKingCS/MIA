"""
tests.test_debt_missions
==========================

His debt payoff plan as a mission (core/debt_missions.py, brainstorm 6.2): the order and months worked out in code,
one mission with an objective for each debt on his press, each ticked when that debt (by its id) reaches zero,
the mission completed when all are, one running at a time.
"""

from datetime import date
from types import SimpleNamespace

from core import debt_missions as dm
from core.budget_manager import Debt

TODAY = date(2026, 11, 23)


def _debts():
    return [Debt(debt_id="c", name="Card", balance=1200, interest_rate=24.0, minimum_payment=60),
            Debt(debt_id="l", name="Truck loan", balance=3000, interest_rate=6.0, minimum_payment=150),
            Debt(debt_id="z", name="Paid", balance=0, interest_rate=5.0, minimum_payment=20)]


def _ctx(debts=None, missions=None):
    """A context with the budget's debts, the missions and a small settings store (the steps' debt ids)."""
    store = {}
    config = SimpleNamespace(get=lambda key, default=None: store.get(key, default),
                             set=lambda key, value: store.__setitem__(key, value))
    return SimpleNamespace(budget=SimpleNamespace(all_debts=lambda: debts if debts is not None else _debts()),
                           missions=missions, config=config)


def test_the_plan_orders_debts_and_dates_each_payoff():
    found = dm.plan(_ctx(), "avalanche", 100, TODAY)
    assert [s["name"] for s in found["steps"]] == ["Card", "Truck loan"]  # the paid one is left out
    assert all(s["by"] for s in found["steps"]) and found["debt_free"] == max(s["by"] for s in found["steps"])
    said = dm.say(found)
    assert said.startswith("In order (avalanche, with $100.00 extra a month): Card") and "Debt-free by" in said


def test_no_open_debts_says_so_and_the_card_refuses():
    assert dm.plan(_ctx([]), today=TODAY) == {}
    assert "No open debts" in dm.say({})
    try:
        dm._describe(_ctx([]), {})
        raise AssertionError("expected ActionError")
    except dm.ActionError:
        pass


class _Missions:
    """A small stand-in for core/mission_manager.MissionManager."""
    def __init__(self):
        self.missions = []

    def add_mission(self, name, **kw):
        m = SimpleNamespace(mission_id=f"m{len(self.missions)}", name=name, status="active", objectives=[], **kw)
        self.missions.append(m)
        return m

    def add_objective(self, mission_id, description, metric_type, target):
        m = next(x for x in self.missions if x.mission_id == mission_id)
        m.objectives.append(SimpleNamespace(description=description, metric_type=metric_type, target=target,
                                            progress=0.0))

    def all_missions(self):
        return self.missions

    def set_objective_progress(self, mission_id, progress):
        m = next(x for x in self.missions if x.mission_id == mission_id)
        for o, v in zip(m.objectives, progress):
            if v is not None:
                o.progress = v


def test_the_mission_has_a_step_a_debt_and_each_ticks_when_paid(monkeypatch):
    monkeypatch.setattr("core.person_settings.person_id", lambda context: "p1")
    missions = _Missions()
    debts = _debts()
    ctx = _ctx(debts, missions)
    said = dm._make(ctx, {"strategy": "avalanche"})
    [m] = missions.missions
    assert m.name.startswith("Debt-free by") and "2 steps" in said
    assert [o.description.split(" (by")[0] for o in m.objectives] == ["Pay off Card", "Pay off Truck loan"]
    assert dm.tick(ctx) == 0
    debts[0].balance = 0
    assert dm.tick(ctx) == 1 and [o.progress for o in m.objectives] == [1.0, 0.0]
    assert dm.tick(ctx) == 0  # already ticked


def test_the_card_kind_is_registered_for_his_press():
    from core.actions import ACTION_TYPES

    assert "debts.missions" in ACTION_TYPES and ACTION_TYPES["debts.missions"].label == "Make It A Mission"


def test_a_renamed_or_twin_named_debt_ticks_only_its_own_step_and_the_mission_completes(monkeypatch):
    monkeypatch.setattr("core.person_settings.person_id", lambda context: "p1")
    missions = _Missions()
    completed = []
    missions.update_mission = lambda mid, **kw: completed.append((mid, kw))
    debts = [Debt(debt_id="v1", name="Visa", balance=300, interest_rate=20.0, minimum_payment=30),
             Debt(debt_id="v2", name="Visa", balance=2000, interest_rate=20.0, minimum_payment=60)]
    store = {}
    config = SimpleNamespace(get=lambda key, default=None: store.get(key, default),
                             set=lambda key, value: store.__setitem__(key, value))
    ctx = SimpleNamespace(budget=SimpleNamespace(all_debts=lambda: debts), missions=missions, config=config)
    dm._make(ctx, {"strategy": "snowball"})
    [m] = missions.missions
    debts[1].name = "Visa (old card)"  # renamed: still owed, never ticked
    debts[0].balance = 0
    assert dm.tick(ctx) == 1 and [o.progress for o in m.objectives] == [1.0, 0.0] and not completed
    debts[1].balance = 0
    assert dm.tick(ctx) == 1 and completed == [(m.mission_id, {"status": "completed"})]


def test_a_second_payoff_mission_is_refused_while_one_runs():
    running = SimpleNamespace(all_missions=lambda: [SimpleNamespace(status="active", name="Debt-free by May 2028")])
    try:
        dm._describe(_ctx(missions=running), {})
        raise AssertionError("expected ActionError")
    except dm.ActionError as problem:
        assert "already a payoff mission" in str(problem)
