"""
tests.test_specialist_review_fixes
====================================

The defects Fable's review of 2026-11-18 found in the specialists and their calculators, each kept fixed by a test
here: a second model's doubt in any wording holds the answer and leads it; a wrong small figure doesn't pass the
answer's number check; fabric counts pieces across the washed width; the joist table sits below the code's shortest
species; and impossible inputs are refused in words instead of crashing or giving a confident number.
"""

from __future__ import annotations

import pytest

from core import eng_calcs
from core import specialist_review as sr
from core import specialist_work as sw
from core.eng_calcs import CalcError, calculate


@pytest.mark.parametrize("reply", [
    '{"agree": false, "problem": "12 V was read as 120 V"}',
    '{"agree": "false", "problem": "12 V was read as 120 V"}',
    '{"agree": "no", "problem": "wrong voltage"}',
    '{"agree": 0}',
    '{"agree": true, "problem": "the length was one way, not out and back"}',
    'I disagree: 12 V was read as 120 V.',
    '{"agree": true} but actually {"agree": false, "problem": "the gauge is wrong"}',
    'The voltage is wrong here. }',
])
def test_a_reviewers_doubt_in_any_wording_is_a_doubt(reply):
    assert sr.read_reply(reply)[0] == sr.DOUBTED


def test_only_one_clean_agreement_agrees_and_silence_is_not_a_review():
    assert sr.read_reply('{"agree": true}') == (sr.AGREED, "")
    assert sr.read_reply('Sure. {"agree": true, "problem": ""}')[0] == sr.AGREED
    assert sr.read_reply("")[0] == sr.NOT_REVIEWED and sr.read_reply("I looked at it.")[0] == sr.NOT_REVIEWED


def test_a_held_answer_leads_with_the_doubt_and_marks_the_figures_unconfirmed():
    result = {"status": "answered", "answer": "Use 10 AWG copper.", "caveat": "This is a draft calculation.",
              "specialist_name": "Electrical", "checked": "Every number checked.", "held": True,
              "review": {"said": "Hold on: a second model doubted this: 12 V was read as 120 V."}}
    said = sw.say(result)
    assert said.startswith("Hold on:") and "unconfirmed" in said
    assert said.index("unconfirmed") < said.index("Use 10 AWG") and "Every number checked" not in said


def _wire_result():
    """The wire calculator's real result for a 16 A continuous load at 120 V over 75 ft."""
    return calculate("wire_gauge", {"amps": "16 A", "volts": "120 V", "length": "75 ft", "continuous": 1})


def test_a_wrong_small_figure_no_longer_passes_the_answers_number_check():
    result = _wire_result()
    question = "What wire for 16 A at 120 V over 75 ft?"
    allowed = sw.allowed_numbers(question, [result], [])
    chosen = sw.chosen_figures([result])
    assert 10 in chosen  # the gauge the calculator worked out
    assert sw.untraced("Use 8 AWG copper.", allowed, chosen) == [8]  # 8 used to be a "free" small number
    assert sw.untraced("Use 10 AWG copper.", allowed, chosen) == []
    assert sw.untraced("Take 2 wires.", allowed, []) == []  # with no small figure worked out, small counts stay free
    joist = {"choice": "2x10", "values": {}}
    assert sw.unsaid_choices("Use 2x12 joists.", [joist]) == ["2x10"]
    assert sw.unsaid_choices("Use 2x10 joists.", [joist]) == []


def test_fabric_counts_pieces_across_the_washed_width_and_exact_fits_fit():
    two = calculate("fabric_yardage", {"count": 2, "length": "20 in", "width": "11 in", "fabric": "24 in",
                                       "seam": "0.5 in", "shrink": "0%"})
    assert two["values"]["across"].value == 2  # 12 in cut pieces on 24 in fabric: two, not one
    shrunk = calculate("fabric_yardage", {"count": 6, "length": "20 in", "width": "19 in", "fabric": "60 in",
                                          "seam": "0.5 in", "shrink": "5%"})
    assert shrunk["values"]["across"].value == 2 and shrunk["values"]["rows"].value == 3  # 57 in washed: two fit


def test_the_joist_table_refuses_a_span_that_is_no_span():
    with pytest.raises(CalcError, match="too short"):
        calculate("joist_size", {"span": "12 in"}) if "joist_size" in eng_calcs.BY_ID else eng_calcs._joist(
            eng_calcs.q(1, "ft"))


def test_sixty_two_inches_of_rise_is_eight_risers_in_any_unit():
    assert eng_calcs._stair_risers(eng_calcs.q(62, "in"))["values"]["risers"].value == 8
    assert eng_calcs._stair_risers(eng_calcs.q(62 / 12, "ft"))["values"]["risers"].value == 8


@pytest.mark.parametrize("calc,inputs", [
    ("voltage_drop", {"volts": "0 V", "amps": "5 A", "length": "10 ft", "gauge": "14"}),
    ("battery_pack", {"cell_volts": "3.7 V", "cell_capacity": "2500 mAh", "series": "2.5", "parallel": "1"}),
    ("adc_step", {"vref": "3.3 V", "bits": "12.6"}),
    ("voltage_drop", {"volts": "12 V", "amps": "30 A", "length": "100 ft", "gauge": "14"}),
])
def test_values_that_cant_work_are_refused_in_words(calc, inputs):
    with pytest.raises(CalcError):
        calculate(calc, inputs)


def test_a_share_over_a_hundred_percent_or_a_bare_fraction_is_refused():
    calc = next(c for c in eng_calcs.CALCULATORS if any(u == "%" for u, _w, _d in c.inputs.values()))
    name = next(n for n, (u, _w, _d) in calc.inputs.items() if u == "%")
    with pytest.raises(CalcError, match="over 100%"):
        eng_calcs._read(calc, name, "150%")
    with pytest.raises(CalcError, match="% sign"):
        eng_calcs._read(calc, name, "0.8")
    assert eng_calcs._read(calc, name, "80%").value == 80 and eng_calcs._read(calc, name, 80).value == 80
    assert eng_calcs._read(calc, name, "0.5%").value == 0.5  # said with its sign, a small percentage is fine


def test_a_regulator_may_sit_below_freezing_and_listening_time_carries_the_safety_caveat():
    assert "ambient" in eng_calcs.BY_ID["regulator_heat"].signed
    assert eng_calcs.BY_ID["noise_exposure"].safety is True


def test_a_model_claude_hasnt_passed_is_said_and_gets_a_second_models_check(monkeypatch):
    from tests.test_specialist_work import WIRE, WIRE_PLAN, Ctx, Model

    monkeypatch.setattr(sw, "_inspected", lambda specialist_id: False)
    got = sw.work(Ctx(Model(WIRE_PLAN, "Use 10 AWG copper on a breaker of 30 A or less; the drop is 2.0%.")), WIRE)
    assert got["status"] == "answered" and got["inspected"] is False and "review" in got
    assert "hasn't inspected and passed" in sw.say(got)


def test_starting_a_team_by_voice_only_puts_a_card_to_him():
    from core.assistant_teamwork_actions import ASKS_HIM

    assert {"team.start", "teamwork.confirm"} <= ASKS_HIM
