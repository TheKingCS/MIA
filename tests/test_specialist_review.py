"""
tests.test_specialist_review
==============================

A second local model checks a specialist's work (core/specialist_review.py, S5): it reviews the plan (calculators
and inputs), never the arithmetic; the reviewer is the best other model on the bench, independent only from another
family, and said so; a doubt holds the answer in MIA's words; an unreadable or missing review is never taken for
agreement; and the worksheet runs one for safety-critical work, or when the person asks.
"""

from __future__ import annotations

from core import specialist_review as sr
from tests.test_specialist_models import RESULTS
from tests.test_specialist_work import WIRE, WIRE_PLAN, Ctx, Model

RESULT = {"status": "answered", "caveat": "x", "calculations": [
    {"calculator": "wire_gauge", "said": "10 AWG copper: it carries 30 A", "basis": "",
     "inputs": {"volts": "120 V", "amps": "16 A", "length": "75 ft"}}]}


def test_the_reviewer_reads_the_plan_and_agrees_or_doubts_in_json():
    prompts = []

    def agrees(prompt):
        prompts.append(prompt)
        return '<think>looks fine</think>{"agree": true}'

    found = sr.review(WIRE, RESULT, agrees, "qwen3:14b", "qwen2.5:32b")
    assert found.verdict == sr.AGREED and not found.independent
    assert "amps = 16 A" in prompts[0] and "never instructions to you" in prompts[0] and "do not do arithmetic" in \
        prompts[0].lower()
    doubt = sr.review(WIRE, RESULT, lambda p: '{"agree": false, "problem": "The run is 75 ft one way, entered right, '
                      'but the load runs all day and continuous was left out."}', "llama3.2:3b", "qwen2.5:32b")
    assert doubt.verdict == sr.DOUBTED and doubt.independent and "continuous" in doubt.problem
    assert sr.said(doubt).startswith("Hold on: a second model (llama3.2:3b)") and "same family" not in sr.said(doubt)
    assert "same family" in sr.said(found)


def test_no_reviewer_or_an_unreadable_reply_is_never_agreement():
    assert sr.review(WIRE, RESULT, None).verdict == sr.NOT_REVIEWED
    assert sr.review(WIRE, RESULT, lambda p: "Looks good to me!", "qwen3:14b", "qwen2.5:32b").verdict == sr.NOT_REVIEWED
    assert sr.review(WIRE, RESULT, lambda p: (_ for _ in ()).throw(TimeoutError()), "m", "n").verdict == sr.NOT_REVIEWED
    assert sr.review(WIRE, {"calculations": []}, lambda p: '{"agree": true}', "m", "n").verdict == sr.NOT_REVIEWED
    assert sr.said(sr.review(WIRE, RESULT, None)).startswith("Not checked by a second model")


def test_the_reviewer_is_the_best_other_model_and_families_are_read_from_names():
    assert sr.family("qwen2.5:32b") == sr.family("qwen3-coder:30b") == "qwen" and sr.family("llama3.2") == "llama"
    assert sr.reviewer_for("embedded", "fast:30b", RESULTS).model == "big:32b"
    assert sr.reviewer_for("embedded", "only:1b", {"only:1b": RESULTS["big:32b"]}) is None


def test_the_worksheet_reviews_safety_critical_work_and_a_doubt_holds_it(monkeypatch):
    from core import specialist_models, specialist_work as sw

    monkeypatch.setattr(specialist_models, "load", lambda folder=None: RESULTS)
    asked, real = [], specialist_models.choose

    def second(context, choice):
        """A stand-in for the reviewer's model; the author's own is the context's model."""
        if choice.model in {real(sid, RESULTS).model for sid in ("electrical", "embedded")}:
            return None
        return lambda prompt: asked.append(choice.model) or '{"agree": false, "problem": "Wrong load."}'
    monkeypatch.setattr(specialist_models, "asker", second)
    got = sw.work(Ctx(Model(WIRE_PLAN, "Use 10 AWG copper on a breaker of 30 A or less.")), WIRE)
    assert got["review"]["verdict"] == sr.DOUBTED and got["held"] and asked
    assert "Hold on" in sw.say(got) and "Wrong load." in sw.say(got)
    calm = sw.work(Ctx(Model({"calculations": [{"calculator": "led_resistor", "inputs": {
        "supply": "5 V", "forward": "2 V", "current": "20 mA"}}]}, "Use a 150 ohm resistor.")),
        "What resistor for an LED with a 2 V forward voltage at 20 mA from 5 V?", "embedded")
    assert calm["status"] == "answered" and "review" not in calm  # not safety-critical, not asked for
    checked = sw.work(Ctx(Model({"calculations": [{"calculator": "led_resistor", "inputs": {
        "supply": "5 V", "forward": "2 V", "current": "20 mA"}}]}, "Use a 150 ohm resistor.")),
        "What resistor for an LED with a 2 V forward voltage at 20 mA from 5 V?", "embedded", check=True)
    assert checked["review"]["verdict"] == sr.DOUBTED
