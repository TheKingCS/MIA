"""Cross-domain reasoning (build plan step 8): questions that span apps gather several plans onto one sheet;
"can I afford it and still hit my freedom date" is worked out by the freedom plan twice; every plan answer says
how sure it can be, from the sheet, and answers.calibration checks that "sure" is earned."""

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
