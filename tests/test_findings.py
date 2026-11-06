"""Findings (DEC-0052 step 3, core/findings.py): what MIA notices by
putting apps together, with the records it came from, why it matters, a
next step, and only Zac's chosen kinds unprompted."""

from datetime import date, timedelta

import pytest

from core import findings as F
from tests.test_crafting import shop  # noqa: F401  (the fixture)

TODAY = date(2026, 10, 30)  # a Friday


@pytest.fixture
def life(shop):  # noqa: F811
    return shop


def test_a_bill_before_payday(life, monkeypatch):
    life.budget.add_income_source(name="Paycheck", expected_amount=1200, next_date="2026-11-06")
    life.budget.add_bill(name="Electric", amount=140, due_date="2026-11-03")
    life.budget.add_bill(name="Water", amount=40, due_date="2026-11-20")  # after payday: not this finding
    monkeypatch.setattr("core.freedom.bank_cash", lambda context, only=None: 100.0)
    (f,) = F.bill_before_pay(life, TODAY)
    assert "Electric ($140.00, Tuesday, November 3)" in f.claim and "Water" not in f.claim
    assert "less than they add up to" in f.claim and f.unprompted  # money short: allowed unprompted
    monkeypatch.setattr("core.freedom.bank_cash", lambda context, only=None: None)
    (f,) = F.bill_before_pay(life, TODAY)
    assert not f.unprompted  # no bank: Home only, never a guess that money is short


def test_a_mission_that_hasnt_moved(life):
    m = life.missions.add_mission(name="Oil Change")
    life.missions.add_objective(m.mission_id, "Schedule appointment", "tally", 1)
    m.updated_at = (TODAY - timedelta(days=20)).isoformat() + "T09:00:00"
    (f,) = [x for x in F.goal_not_moving(life, TODAY) if "Oil Change" in x.claim]
    assert f.claim == "Oil Change hasn't moved since October 10; next is Schedule appointment."
    assert not f.unprompted and f.refs == [f"mission:{m.mission_id}"]


def test_a_build_past_its_budget(life):
    p = life.projects.add_project("Chicken coop")
    life.projects.update_project(p.project_id, budget=500)
    life.budget.add_expense(amount=620, category="Materials", description="Lumber", date="2026-10-20",
                            project_id=p.project_id)
    (f,) = F.build_over_budget(life, TODAY)
    assert "$620.00 of its $500.00 budget" in f.claim and not f.unprompted


def test_the_noticed_plan_says_them(life):
    from core import question_plans as qp

    m = life.missions.add_mission(name="Oil Change")
    m.updated_at = "2026-10-01T09:00:00"
    sheet = qp.gather(life, qp.PLAN_BY_NAME["noticed"], "What have you noticed about me lately?", TODAY)
    assert any("Oil Change hasn't moved" in f.text for f in sheet.facts)


def test_every_rule_runs_on_an_empty_life(life):
    for rule in F.RULES:
        assert isinstance(rule(life, TODAY), list), rule.__name__
    assert isinstance(F.findings(life, TODAY), list)


def test_only_the_chosen_kinds_go_out_unprompted():
    unprompted = {"bill_before_pay", "upkeep_before_trip", "deadline_in_packed_week", "cheaper_quote",
                  "goods_before_market"}  # DEC-0052: goods passing their best-by before market day
    import inspect

    for rule in F.RULES:
        allows = "unprompted=True" in inspect.getsource(rule) or "unprompted=short" in inspect.getsource(rule)
        assert allows == (rule.__name__ in unprompted), rule.__name__


def test_goods_that_wont_make_market_day(monkeypatch):
    from datetime import date
    from types import SimpleNamespace

    import core.calendar_view as cv
    import core.goods as goods
    from core.findings import goods_before_market
    from core.goods import Lot

    today = date(2026, 11, 6)
    monkeypatch.setattr(cv, "calendar_items", lambda context, start, end, today=None: [
        {"date": "2026-11-08", "title": "Dentist", "time": "", "kind": "event"},
        {"date": "2026-11-14", "title": "Farmers market", "time": "", "kind": "event"}])
    made = [Lot("j1", "r1", "jam", "2026-10-20", "2026-11-10", 12, 4, 0, 2.0),  # 8 left, gone by the 10th
            Lot("j2", "r1", "jam", "2026-11-01", "2026-11-30", 12, 0, 0, 2.0),  # keeps till after
            Lot("j3", "r2", "soap", "2026-09-01", "", 10, 2, 0, 1.0),  # keeps
            Lot("j4", "r3", "bread", "2026-11-04", "2026-11-07", 6, 6, 0, 1.0)]  # all sold
    monkeypatch.setattr(goods, "lots", lambda jobs, recipes, sales, include_empty=False: made)
    context = SimpleNamespace(craft_recipes=SimpleNamespace(all_recipes=lambda: []),
                              jobs=SimpleNamespace(all_jobs=lambda: []), ledger=None)
    [found] = goods_before_market(context, today)
    assert found.refs == ["job:j1"] and found.unprompted and found.key == "goods_before_market:j1:2026-11-14"
    assert found.claim.startswith("8 jam made 2026-10-20 pass their sell-by") and "before Farmers market" in found.claim
    monkeypatch.setattr(cv, "calendar_items", lambda context, start, end, today=None: [])
    assert goods_before_market(context, today) == []  # no market day ahead: nothing to say


def test_why_a_finding_was_said():
    from core.message_reasons import explain, name_of

    assert name_of("finding_goods_before_market") == "things I noticed across your apps"
    assert "two of your apps together" in explain({"topic": "finding_bill_before_pay", "title": "A bill before payday"})
