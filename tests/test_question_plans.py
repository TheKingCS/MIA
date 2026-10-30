"""Question plans (DEC-0052 step 2a, core/question_plans.py): the right
plan for a question, lookups gathered by code onto a marked sheet, and an
answer that never states a number MIA didn't look up."""

from datetime import date
from types import SimpleNamespace

import pytest

import core.meaning as meaning
from core import question_plans as qp
from core.llm_manager import ChatReply
from tests.test_crafting import shop  # noqa: F401  (the fixture)

TODAY = date(2026, 10, 30)


@pytest.fixture
def life(shop, monkeypatch):  # noqa: F811
    from tests.assistant_registry import build_desktop_registry

    shop.assistant_actions = build_desktop_registry()
    monkeypatch.setattr(meaning, "nearest", lambda *a, **k: None)  # no embedding model: the plans' own words
    return shop


class _Model:
    def __init__(self, said):
        self.said, self.asked = said, []

    def chat_with_tools(self, messages, tools):
        self.asked.append(messages)
        return ChatReply(content=self.said, tool_calls=[])


def test_only_questions_reach_a_plan(life):
    assert qp.match(life, "Which debt should I prioritize?").name == "debts"
    assert qp.match(life, "How much money came in and went out this month?").name == "money month"
    assert qp.match(life, "Add a debt called Truck Loan") is None  # a change, not a question
    assert qp.match(life, "How do I add a bill?") is None  # how-to: the help docs
    assert qp.match(life, "Thanks!") is None


def test_by_meaning_when_the_model_is_there(life, monkeypatch):
    monkeypatch.setattr(meaning, "nearest", lambda c, text, examples: ("debts", 0.79))
    assert qp.match(life, "when will I be out from under all this?").name == "debts"
    monkeypatch.setattr(meaning, "nearest", lambda c, text, examples: ("today", 0.60))  # too far: not a plan
    assert qp.match(life, "How are you?") is None


def test_debts_sheet_has_the_payoff_math(life):
    life.budget.add_debt(name="Card", balance=3000, interest_rate=20, minimum_payment=90)
    life.budget.add_debt(name="Truck", balance=8000, interest_rate=6, minimum_payment=250)
    sheet = qp.gather(life, qp.PLAN_BY_NAME["debts"], "What if I put an extra $300 toward my debts?", TODAY)
    kinds = [f.kind for f in sheet.facts]
    assert "list_debts" in sheet.looked_up and qp.CALCULATION in kinds
    text = sheet.as_text()
    assert "At the minimums" in text and "$300.00 more a month to Card first" in text


def test_money_month_counts_in_code(life):
    life.budget.add_income(amount=2000, category="Salary", description="Pay", date="2026-10-15")
    life.budget.add_expense(amount=150, category="Groceries", description="Food", date="2026-10-20")
    sheet = qp.gather(life, qp.PLAN_BY_NAME["money month"], "Where is my money going?", TODAY)
    text = sheet.as_text()
    assert "$2,000.00 came in, $150.00 went out, net $1,850.00" in text and "Groceries $150.00" in text
    assert "entered by hand" in text


def test_an_invented_number_falls_back_to_the_sheet(life):
    life.budget.add_debt(name="Card", balance=3000, interest_rate=20, minimum_payment=90)
    life.llm = _Model("Pay off Card first; it'll take 41 months and $1,234.56 of interest.")
    conversation = SimpleNamespace(messages=[], mode=None)
    said, sheet = qp.answer(life, conversation, "Which debt should I prioritize?", TODAY)
    assert said == sheet.plain() and "1234.56" not in said  # the model's made-up number never reaches the person
    system = life.llm.asked[0][0]["content"]
    assert "Fact sheet" in system and "[calculation" in system


def test_numbers_and_the_sheet_in_plain_words():
    assert qp.numbers_in("$1,200.00 and 3.50") == {"1200", "3.5"}
    assert qp.invented_numbers("You have 3 bills: $45.10.", "- [fact] Electric $45.10", "") == set()
    assert qp.invented_numbers("About $99 left.", "- [fact] Electric $45.10", "") == {"99"}
    assert qp._amount_in("my next $1,000") == 1000 and qp._amount_in("an extra 200 dollars") == 200
    sheet = qp.Sheet("x", "X")
    sheet.add(qp.FACT, "Electric is due Friday.")
    sheet.add(qp.MISSING, "No pay rate in the Dungeon.")
    assert sheet.plain() == "Electric is due Friday. Not recorded yet: No pay rate in the Dungeon."


def test_every_plan_gathers_without_failing(life):
    for plan in qp.PLANS:
        sheet = qp.gather(life, plan, plan.examples[0], TODAY)
        assert sheet.facts, plan.name  # something, even if it's "missing"


def test_personal_modes_stay_a_conversation(life):
    talk = SimpleNamespace(messages=[], mode="listen")
    assert qp.request(life, talk, "Which debt should I prioritize?") is None
