"""
DEC-0017 (2026-10-06): Money on the web does everything the PC app's
Budget screen does. The page's data (core/web_money.py) and every change
as an action kind (core/money_actions.py): add, edit, delete bills,
income sources, income, expenses and debts; pay a debt; set budgets.
Each one proposed, approved, recorded and undoable; none for a child.
"""

from datetime import date, timedelta

import pytest

from core.actions import ACTION_TYPES, ActionCenter, ActionError
from core.child_accounts import make_child
from core.money_actions import RECORDS, form_spec
from core.web_money import due_words, money_page, month_starts
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.bill = context.budget.add_bill("Electric", 120.0, (TODAY - timedelta(days=2)).isoformat(),
                                           recurrence="monthly")
    return context


def run(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    return proposal, world.actions.approve(world, proposal.proposal_id)


def test_pure_bits():
    assert [due_words(d) for d in (None, 0, 1, 3, -1, -5)] == [
        "nothing more due", "today", "tomorrow", "in 3 days", "1 day late", "5 days late"]
    starts = month_starts(date(2026, 3, 15), 6)
    assert starts[0] == date(2025, 10, 1) and starts[-1] == date(2026, 3, 1) and len(starts) == 6


def test_every_kind_is_registered_and_has_a_form():
    for key in RECORDS:
        assert {f"{key}.add", f"{key}.edit", f"{key}.delete"} <= set(ACTION_TYPES)
        assert [f["name"] for f in form_spec()[key]["fields"]] == [f.name for f in RECORDS[key].fields]
    assert {"debt.pay", "budget_target.set", "budget_target.delete"} <= set(ACTION_TYPES)
    assert not any(ACTION_TYPES[k].child_ok for k in ACTION_TYPES if k.split(".")[0] in RECORDS)


def test_the_page(world):
    world.budget.add_income_source("Pay", 1500.0, TODAY.isoformat(), recurrence="biweekly")
    world.budget.add_expense(35.5, "Groceries", "Food", TODAY.isoformat())
    world.budget.add_debt("Card", 2000.0, 24.99, 50.0)
    world.budget.add_debt("Loan", 500.0, 5.0, 25.0, debt_type="Personal Loan")
    world.budget.set_budget_target("Groceries", 400.0)
    page = money_page(world, TODAY)
    [bill] = page["bills"]
    assert (bill["name"], bill["when"], bill["action"]["kind"]) == ("Electric", "2 days late", "bill.pay")
    assert bill["values"]["amount"] == 120.0 and bill["values"]["recurrence"] == "monthly"
    assert page["income_sources"][0]["when"] == "today"
    assert page["expenses"][0]["description"] == "Food"
    assert [d["name"] for d in page["debts"]["ranked"]] == ["Card", "Loan"]
    assert page["debts"]["ranked"][0]["reason"].startswith("Highest current APR")
    snowball = money_page(world, TODAY, strategy="snowball")
    assert snowball["debts"]["strategy"] == "snowball" and snowball["debts"]["ranked"][0]["name"] == "Loan"
    assert page["budget_targets"] == [{"category": "Groceries", "budget": 400.0, "spent": 35.5, "left": 364.5}]
    assert len(page["trends"]) == 6 and page["trends"][-1]["expenses"] == 35.5
    assert page["spending_by_category"][0] == {"category": "Groceries", "amount": 35.5}
    assert page["bank"]["status"] == "PLANNED"  # no bank connection on this MIA
    assert page["summary"]["monthly_plan"]["bills"] == 120.0


def test_add_edit_delete_a_bill_with_undo(world):
    proposal, done = run(world, "bill.add", name="Water", amount="45", due_date=(TODAY + timedelta(days=10)).isoformat(),
                         recurrence="monthly", category="Utilities")
    assert proposal.summary.startswith("Add the bill Water: amount $45.00, due ")
    water = next(b for b in world.budget.all_bills() if b.name == "Water")

    proposal, _ = run(world, "bill.edit", bill_id=water.bill_id, name="Water", amount="50", category="Utilities")
    assert proposal.summary == "Change Water: amount $45.00 → $50.00"
    assert world.budget.get_bill(water.bill_id).amount == 50.0
    with pytest.raises(ActionError, match="Nothing to change"):
        world.actions.propose(world, "bill.edit", {"bill_id": water.bill_id, "amount": "50"})

    proposal, deleted = run(world, "bill.delete", bill_id=water.bill_id)
    assert proposal.summary == "Delete the bill Water ($50.00). Its past payments stay in Expenses."
    assert world.budget.get_bill(water.bill_id) is None
    world.actions.undo(world, deleted.proposal_id)
    assert world.budget.get_bill(water.bill_id).amount == 50.0


def test_the_engine_keeps_the_rules(world):
    for params, problem in (({"amount": "-5", "date": TODAY.isoformat()}, "can't be negative"),
                            ({"amount": "abc", "date": TODAY.isoformat()}, "has to be a number"),
                            ({"amount": "5", "date": "tomorrow"}, "has to be a date"),
                            ({"amount": "5", "date": TODAY.isoformat(), "category": "Yachts"}, "one of the list"),
                            ({"date": TODAY.isoformat()}, "Amount is needed")):
        with pytest.raises(ActionError, match=problem):
            world.actions.propose(world, "expense.add", params)
    with pytest.raises(ActionError, match="isn't there anymore"):
        world.actions.propose(world, "bill.delete", {"bill_id": "nope"})


def test_income_expenses_debts_and_budgets(world):
    proposal, done = run(world, "expense.add", amount="12.5", date=TODAY.isoformat(), category="Groceries",
                         description="Milk", payee="Corner store")
    assert proposal.summary.endswith("category Groceries, paid to Corner store")
    assert proposal.summary.startswith("Add the expense Milk: amount $12.50, date ")
    [expense] = [e for e in world.budget.all_expenses() if e.description == "Milk"]
    assert expense.payee == "Corner store"
    run(world, "expense.edit", entry_id=expense.entry_id, amount="13")
    assert world.budget.get_expense(expense.entry_id).amount == 13.0
    run(world, "income.add", amount="200", date=TODAY.isoformat(), description="Side job")
    assert [i.description for i in world.budget.all_income()] == ["Side job"]

    run(world, "debt.add", name="Card", balance="1000", interest_rate="20", minimum_payment="40")
    card = world.budget.all_debts()[0]
    proposal, _ = run(world, "debt.pay", debt_id=card.debt_id, amount="100")
    assert proposal.summary == "Record a $100.00 payment on Card ($900.00 left)"
    assert world.budget.get_debt(card.debt_id).balance == 900.0
    proposal, _ = run(world, "debt.pay", debt_id=card.debt_id)  # the minimum by default
    assert world.budget.get_debt(card.debt_id).balance == 860.0
    proposal, _ = run(world, "debt.edit", debt_id=card.debt_id, promo_apr="0",
                      promo_expires_date=(TODAY + timedelta(days=20)).isoformat())
    assert "promo APR none → 0%" in proposal.summary
    assert money_page(world, TODAY)["debts"]["ranked"][0]["promo"]["days_left"] == 20

    proposal, _ = run(world, "budget_target.set", category="Groceries", monthly_amount="300")
    assert proposal.summary == "Set a monthly Groceries budget of $300.00"
    run(world, "budget_target.delete", category="Groceries")
    assert world.budget.all_budget_targets() == []


def test_not_for_a_child(world):
    make_child(world, world.me.profile_id, [world.other.profile_id])
    with pytest.raises(ActionError, match="grown-ups"):
        world.actions.propose(world, "expense.add", {"amount": "5", "date": TODAY.isoformat()})


def test_the_endpoint(world):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    page = client.get("/api/money?strategy=avalanche").json()
    assert page["bills"][0]["name"] == "Electric" and page["debts"]["strategy"] == "avalanche"
    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert client.get("/api/money").status_code == 403


def test_either_module_can_be_imported_first():
    """2026-10-06: importing core.money_actions before core.actions failed."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for first in ("core.money_actions", "core.actions"):
        code = f"import {first}; from core.actions import ACTION_TYPES; assert 'bill.add' in ACTION_TYPES"
        assert subprocess.run([sys.executable, "-c", code], cwd=root).returncode == 0, first
