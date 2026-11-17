"""
tests.test_specialist_models
==============================

Which local model does each specialist's thinking (core/specialist_models.py, DEC-0197): chosen from this PC's
bench results in the worksheet's own mode, over the disciplines that specialist uses; a model that guesses a
missing input doesn't pass however many it gets right; the best that didn't pass is still used and said on the
answer; no results means MIA's everyday model, said; and only this machine's own Ollama gets a second model.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from core import specialist_models as sm


def _cell(tasks, right, asked=0, guessed=0, seconds=1.0):
    """One discipline's counts, as core/eng_bench.summary writes them."""
    return {"tasks": tasks, "right": right, "asked": asked, "wrong": tasks - right - asked - guessed,
            "guessed": guessed, "unreadable": 0, "seconds": seconds}


RESULTS = {
    "small:14b": {"tools": {"electrical": _cell(7, 6), "embedded": _cell(8, 4, guessed=2), "greenhouse": _cell(5, 3)},
                  "alone": {"electrical": _cell(7, 7)}},
    "big:32b": {"tools": {"electrical": _cell(7, 6, 1, seconds=3.0), "embedded": _cell(8, 7, 1, seconds=3.0),
                          "greenhouse": _cell(5, 4, 1, seconds=3.0)}},
    "fast:30b": {"tools": {"electrical": _cell(7, 6, 1, seconds=0.5), "embedded": _cell(8, 7, 1, seconds=0.5)}},
}


def test_a_specialist_gets_the_best_model_on_its_own_disciplines_in_the_worksheets_mode():
    pick = sm.choose("embedded", RESULTS)  # embedded + electrical
    assert pick.model == "fast:30b" and pick.passed and pick.tasks == 15  # ties on share go to the faster
    assert sm.choose("greenhouse", RESULTS).model == "big:32b"  # fast:30b wasn't benched on greenhouse work
    partial = sm.choose("greenhouse", {"fast:30b": RESULTS["fast:30b"]})
    assert partial.model == "fast:30b" and not partial.passed and "benched on all" in partial.why
    alone_only = {"cheat:7b": {"alone": {"electrical": _cell(7, 7)}}}
    assert sm.choose("electrical", alone_only).model is None  # only the tools mode counts


def test_guessing_a_missing_input_fails_a_model_and_the_answer_says_so():
    only_small = {"small:14b": RESULTS["small:14b"]}
    pick = sm.choose("embedded", only_small)
    assert pick.model == "small:14b" and not pick.passed and pick.guessed == 2
    assert "guessed 2 times" in pick.why and "best on this PC" in pick.why
    from core.specialist_work import say

    said = say({"status": "answered", "answer": "Use a 150 ohm resistor.", "caveat": "", "specialist_name": "Embedded",
                "checked": "Every number comes from a calculator.", "model_note": pick.why})
    assert "small:14b" in said and "check that it picked the right ones" in said


def test_without_results_the_everyday_model_answers_and_it_says_so(tmp_path):
    assert sm.choose("embedded", {}).model is None and "no bench results" in sm.choose("embedded", {}).why
    assert "benched on this work" in sm.choose("crafts", RESULTS).why
    (tmp_path / "a.json").write_text(json.dumps({"model": "big:32b", "summary": RESULTS["big:32b"]}), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    assert set(sm.load(tmp_path)) == {"big:32b"} and sm.load(tmp_path / "none") == {}
    rows = {r["specialist"]: r for r in sm.table(RESULTS)}
    assert rows["greenhouse"]["model"] == "big:32b" and rows["crafts"]["model"] is None


def test_only_this_machines_own_ollama_gets_the_specialists_model():
    from core.llm_manager import OllamaBackend

    pick = sm.choose("embedded", RESULTS)
    local = SimpleNamespace(llm=SimpleNamespace(_backend=OllamaBackend("http://localhost:11434", "llama3.2", "5m"),
                                                home=None))
    assert sm.asker(local, pick) is not None
    phone = SimpleNamespace(llm=SimpleNamespace(_backend=object(), home=None))
    linked = SimpleNamespace(llm=SimpleNamespace(_backend=local.llm._backend, home=object()))
    assert sm.asker(phone, pick) is None and sm.asker(linked, pick) is None
    assert sm.asker(local, sm.Choice(None, False)) is None
    capped = OllamaBackend("http://localhost:11434", "m", "5m", 0.0, think=False, num_predict=sm.MAX_TOKENS)
    assert capped._options()["num_predict"] == sm.MAX_TOKENS and "num_predict" not in local.llm._backend._options()
