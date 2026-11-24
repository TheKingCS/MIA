"""Cross-domain reasoning (build plan step 8): questions that span apps gather several plans onto one sheet;
"can I afford it and still hit my freedom date" is worked out by the freedom plan twice; every plan answer says
how sure it can be, from the sheet, and answers.calibration checks that "sure" is earned; a purchase asked against
the debts is worked out as the same money on the debt instead, never as that much more a month, told apart from
money put on a debt however it's said, and a lump that clears the first debt keeps its minimum rolling; "the card"
said plainly reaches the debts plan by its words, a birthday card never."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

import core.meaning as meaning
from core import calibration, freedom, loops
from core import question_plans as qp
from tests.test_crafting import shop  # noqa: F401  (the fixture)

TODAY = date(2026, 11, 6)
BY_ID = {l.id: l for l in loops.LOOPS}


@pytest.fixture
def life(shop, monkeypatch):  # noqa: F811
    """The test household with the desktop's tools, and the meaning search turned off."""
    from tests.assistant_registry import build_desktop_registry

    shop.assistant_actions = build_desktop_registry()
    monkeypatch.setattr(meaning, "nearest", lambda *a, **k: None)
    return shop


def test_the_cross_domain_questions_find_their_plans(life):
    assert qp.match(life, "Can I afford a $3,000 truck and still hit my freedom date?").name == "afford"
    assert qp.match(life, "What slipped this week and why?").name == "slipped"


def test_a_question_that_joins_domains_gathers_them_onto_one_sheet(life):
    life.budget.add_debt(name="Card", balance=3000, interest_rate=20, minimum_payment=90)
    asked = "When will the card be paid off and how much did I spend this month?"
    plan = qp.PLAN_BY_NAME["debts"]
    also = qp.composed_with(plan, asked)
    assert [p.name for p in also] == ["money month"]
    sheet = qp.gather(life, plan, asked, TODAY, tuple(also))
    assert sheet.composed == ["money month"] and sheet.title == "Debts and paying them off and Money this month"
    text = sheet.as_text()
    assert "At the minimums" in text and "This month so far" in text
    assert qp.composed_with(plan, "When will the card be paid off?") == []  # one domain: one plan
    assert len({f.text for f in sheet.facts}) == len(sheet.facts)  # a fact two plans found is said once


def test_affording_it_against_the_freedom_date(life, monkeypatch):
    inputs = freedom.Inputs(needs=3000, saved=5000, pace=1000, pace_source="the bank", cushion_months=6)
    monkeypatch.setattr(freedom, "gather", lambda context, today: (inputs, []))
    sheet = qp.gather(life, qp.PLAN_BY_NAME["afford"], "Can I afford a $3,000 truck and still hit my freedom date?", TODAY)
    text = sheet.as_text()
    now, later = freedom.plan(inputs, TODAY)["date"], freedom.plan(freedom.Inputs(
        needs=3000, saved=2000, pace=1000, cushion_months=6), TODAY)["date"]
    assert f"Freedom date as things stand: {now}" in text and f"With it: {later}" in text and "days later" in text
    monthly = qp.gather(life, qp.PLAN_BY_NAME["afford"], "Can I afford $1,000 a month for a truck payment?", TODAY)
    assert "the fund stops growing" in monthly.as_text()  # all of the saving pace: no date
    vague = qp.gather(life, qp.PLAN_BY_NAME["afford"], "Can I afford it?", TODAY)
    assert "doesn't say how much" in vague.as_text()


def test_how_sure_comes_from_the_sheet():
    sheet = qp.Sheet("x", "X")
    sheet.add(qp.FACT, "Rent is due on the 1st.")
    sheet.add(qp.CALCULATION, "Net this month: 400.")
    assert qp.sureness(sheet)[0] == qp.SURE
    sheet.add(qp.ESTIMATE, "If the pace holds.")
    assert qp.sureness(sheet) == (qp.LIKELY, "1 estimate")
    empty = qp.Sheet("y", "Y")
    empty.add(qp.MISSING, "No budget is set up.")
    assert qp.sureness(empty)[0] == qp.UNSURE


def test_the_model_is_told_how_sure_and_the_answer_is_noted(life, tmp_path):
    life.failures = SimpleNamespace(data_dir=tmp_path)
    built = qp.request(life, SimpleNamespace(messages=[], mode=None), "Can I afford a $3,000 truck?", TODAY)
    assert built is not None and "How sure you can be:" in built[0][0]["content"]
    said = qp.finish("You can, if the pace holds.", built[1], "Can I afford a $3,000 truck?", life)
    found = calibration.notes(life)
    assert found[-1]["plan"] == "afford" and found[-1]["key"] == calibration.key(said)
    assert "truck" not in (tmp_path / calibration.FILE_NAME).read_text(encoding="utf-8")


def test_calibration_sure_has_to_be_earned(tmp_path):
    person = SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path), ratings=SimpleNamespace(ratings=[]))
    for n in range(6):
        calibration.note(person, "debts", "sure", f"sure answer {n}")
        calibration.note(person, "afford", "likely", f"maybe answer {n}")
    person.ratings.ratings = [{"rating": "down" if n < 3 else "up", "answer": f"sure answer {n}"} for n in range(6)] + \
                             [{"rating": "up", "answer": f"maybe answer {n}"} for n in range(4)]
    assert calibration.rated(person) == {"sure": {"up": 3, "down": 3}, "likely": {"up": 4, "down": 0}}
    reading = BY_ID["answers.calibration"].measure(person)
    assert reading.value == -0.5 and loops.judge(BY_ID["answers.calibration"], reading, [])["state"] == "below"


def test_a_how_can_i_question_that_is_a_plans_own_example(life, monkeypatch):
    """G2 went to the help docs: "How can I...?" looked like a how-to. An exact example is the plan's."""
    monkeypatch.setattr(meaning, "nearest", lambda c, text, examples: ("freedom", 1.0))
    assert qp.match(life, "How can I get out of my current job faster?").name == "freedom"
    monkeypatch.setattr(meaning, "nearest", lambda c, text, examples: ("debts", 0.8))
    assert qp.match(life, "How do I add a bill?") is None  # still the help docs'


def test_the_new_cross_domain_plans_gather(life):
    for name in ("projects", "habits", "priorities", "resources"):
        sheet = qp.gather(life, qp.PLAN_BY_NAME[name], "", TODAY)
        assert sheet.facts, name
    resources = qp.gather(life, qp.PLAN_BY_NAME["resources"], "", TODAY)
    assert any("not market research" in f.text for f in resources.facts)


def test_projected_dates_are_checked_when_they_come(tmp_path):
    from datetime import datetime

    person = SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path), ratings=None)
    calibration.project(person, "debt_free", "2026-12")
    calibration.project(person, "debt_free", "2026-12")  # once per kind and date
    calibration.project(person, "freedom", "2027-03-01")
    assert len(calibration.projections(person)) == 2
    assert calibration.check_due(person, datetime(2027, 1, 10), judge=lambda kind: True) == 0  # a month's grace
    assert calibration.check_due(person, datetime(2027, 2, 1), judge=lambda kind: kind == "freedom") == 1
    [debt, freedom] = calibration.projections(person)
    assert debt["outcome"] == "wrong" and freedom["outcome"] is None
    calibration.check_due(person, datetime(2027, 5, 1), judge=lambda kind: True)
    reading = BY_ID["answers.projections"].measure(person)
    assert (reading.value, reading.n) == (0.5, 2)


def test_the_debt_plan_keeps_its_projection(life, tmp_path):
    life.failures = SimpleNamespace(data_dir=tmp_path)
    life.budget.add_debt(name="Card", balance=3000, interest_rate=20, minimum_payment=150)
    qp.gather(life, qp.PLAN_BY_NAME["debts"], "When will I be debt free?", TODAY)
    [kept] = calibration.projections(life)
    assert kept["kind"] == "debt_free" and kept["when"].startswith("20") and kept["outcome"] is None


def test_a_purchase_asked_against_the_debts_is_worked_out_as_a_purchase(life):
    """Brainstorm 1.4: "if I buy a $900 welder can I still pay off the loan?" gathers the afford facts too, and the
    $900 is never taken as $900 more a month to the debt: it's what the same money would do on the debt instead."""
    life.budget.add_debt(name="Truck loan", balance=6000, interest_rate=8, minimum_payment=250)
    asked = "If I buy a $900 welder can I still pay off the truck loan by summer?"
    plan = qp.match(life, asked)
    also = qp.composed_with(plan, asked)
    assert {plan.name, *(p.name for p in also)} >= {"afford", "debts"}
    sheet = qp.gather(life, qp.PLAN_BY_NAME["debts"], asked, TODAY)
    text = sheet.as_text()
    assert "900 more a month" not in text and "$900.00 once would make you debt-free" in text
    assert "payoff dates above hold either way" in text


def test_money_toward_a_debt_is_still_extra_a_month():
    assert not qp.buying("What if I put an extra $200 toward the card every month?")
    assert qp.buying("Can I afford a $400 chainsaw and still pay down the card?")
    assert qp.buying("Can I spend $150 a month on a gym and still pay off my debts?")


def test_a_purchase_or_a_payment_is_told_apart_however_its_said():
    for said in ("Can I get a $900 welder and still pay off the loan?",
                 "Should I get the $900 welder or pay down the card first?",
                 "If I buy a $1,200 trailer, will it take more months to pay off the loan?"):
        assert qp.buying(said), said
    for said in ("Can I afford to throw $1,000 at the card?", "Can I afford to pay $300 a month on my loans?",
                 "Should I spend my $3,000 tax refund paying down the loan?",
                 "I'm spending $400 a month on interest, when will I be debt free?",
                 "What if I put an extra $200 toward the card every month?"):
        assert not qp.buying(said), said


def test_a_lump_that_clears_the_first_debt_keeps_its_minimum_rolling():
    """More money never gives a later date: a cleared debt's minimum rolls on, and one that covers them all says so."""
    from core.debt_math import simulate

    day = date(2026, 11, 23)
    ranked = [SimpleNamespace(name="Card", balance=500, interest_rate=24, minimum_payment=50),
              SimpleNamespace(name="Loan", balance=10000, interest_rate=8, minimum_payment=200)]
    now = simulate(ranked, 0, day)
    money = lambda a: f"${a:,.2f}"  # noqa: E731
    small = qp.instead(ranked, 400, False, now, day, money)[1][1]
    big = qp.instead(ranked, 3000, False, now, day, money)[1][1]

    def months(line):
        return int(line.split(" months sooner")[0].rsplit(", ", 1)[-1])

    assert months(big) > months(small)
    assert "pay them all off now" in qp.instead(ranked, 20000, False, now, day, money)[1][1]

def test_the_card_said_plainly_reaches_the_debts_plan_but_a_birthday_card_doesnt():
    """Nor a card he pays with, a lost card's bank balance, a bill he paid on the card, or a card game."""
    import re

    debts = qp.PLAN_BY_NAME["debts"].words
    for said in ("what if i put an extra $200 toward the card?", "which card should i pay first?",
                 "when is my card paid off?"):
        assert re.search(debts, said), said
    for said in ("did i get a birthday card?", "what card should i use at the store?",
                 "which card should i pay with at the hardware store?", "i lost the card, what's my bank balance?",
                 "what's due this week, did i pay my card?", "which card game should i play?"):
        assert not re.search(debts, said), said
