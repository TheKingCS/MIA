"""
tests.test_model_inspection
=============================

Claude inspects MIA's models (DEC-0200, core/model_inspection.py): every specialist's chosen model is pending until a
verdict on its current bench results; a re-run of the bench makes it pending again; the inspector is shown the
bench counts and the problems it got wrong, never asked to change anything; a pass can't stand against a failing
bench and an unreadable reply is a hold; every verdict is kept; a pass clears the model; voice and the roster say so;
and Night School inspects one a night with her teacher.
"""

from __future__ import annotations

import json
from datetime import datetime

from core import model_inspection as mi
from core.specialist_models import MODE
from core.specialist_work import DISCIPLINES

GOOD = {"tasks": 5, "right": 5, "asked": 0, "wrong": 0, "guessed": 0, "unreadable": 0, "seconds": 3.0}
POOR = {"tasks": 5, "right": 2, "asked": 0, "wrong": 2, "guessed": 1, "unreadable": 0, "seconds": 3.0}
ALL = sorted({d for ds in DISCIPLINES.values() for d in ds})
NOW = datetime(2026, 11, 17, 2, 0)


def _results(cell=GOOD, model="m:32b"):
    """Bench results in specialist_models.load()'s shape: one model, every discipline."""
    return {model: {MODE: {d: dict(cell) for d in ALL}}}


def _rows(folder, model="m:32b"):
    """A results file with one wrong electrical problem, as tools.eng_bench writes it."""
    from core.eng_bench import TASKS

    task = next(t for t in TASKS if t.discipline == "electrical")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (model.replace(":", "_") + ".json")).write_text(json.dumps({"model": model, "rows": [
        {"task": task.id, "discipline": "electrical", "mode": "tools", "verdict": "wrong", "got": "12 A",
         "detail": "picked the wrong calculator", "expected": "1,500 W", "seconds": 4.0},
        {"task": task.id, "discipline": "electrical", "mode": "alone", "verdict": "wrong", "got": "9", "detail": "",
         "expected": "1,500 W", "seconds": 4.0}]}), encoding="utf-8")
    return task


def test_every_chosen_model_is_pending_until_inspected_and_again_after_a_new_bench(tmp_path):
    record = tmp_path / "inspections.json"
    results = _results()
    waiting = mi.pending(results, mi.load(record))
    assert waiting == list(DISCIPLINES) and not mi.cleared("electrical", results, mi.load(record))
    mi.inspect("electrical", lambda p: '{"verdict": "pass", "findings": []}', "claude-code", results, NOW, record)
    assert "electrical" not in mi.pending(results, mi.load(record)) and mi.cleared("electrical", results, mi.load(record))
    rerun = _results({**GOOD, "seconds": 2.5})  # the same model, a new run
    assert "electrical" in mi.pending(rerun, mi.load(record)) and not mi.cleared("electrical", rerun, mi.load(record))


def test_the_inspector_sees_the_bench_and_what_went_wrong_and_is_told_to_change_nothing(tmp_path):
    task = _rows(tmp_path / "bench")
    asked = []
    mi.inspect("electrical", lambda p: asked.append(p) or '{"verdict": "hold", "findings": ["picks the wrong one"]}',
               "claude-code", _results(), NOW, tmp_path / "i.json", rows_folder=tmp_path / "bench")
    [prompt] = asked
    assert "Electrical" in prompt and "m:32b" in prompt and "you change nothing" in prompt
    assert task.ask in prompt and "Expected: 1,500 W" in prompt and "picked the wrong calculator" in prompt
    assert prompt.count(task.ask) == 1  # the alone-mode row isn't shown


def test_a_pass_cant_stand_against_a_failing_bench_and_an_unreadable_reply_is_a_hold(tmp_path):
    record = tmp_path / "i.json"
    held = mi.inspect("electrical", lambda p: '{"verdict": "pass"}', "codex", _results(POOR), NOW, record)
    assert held["verdict"] == mi.HOLD and held["findings"][0] == "the bench didn't pass, so it can't be passed"
    assert mi.verdict_from("I think it's fine!", True) == (mi.HOLD, ["the inspector's reply couldn't be read as a verdict"])
    assert mi.verdict_from('{"verdict": "maybe"}', True)[0] == mi.HOLD
    assert mi.verdict_from('{"verdict": "PASS", "findings": ["ok"]}', True) == (mi.PASS, ["ok"])


def test_every_verdict_is_kept_with_who_when_and_what_it_was_about(tmp_path):
    record = tmp_path / "i.json"
    mi.inspect("electrical", lambda p: '{"verdict": "hold", "findings": ["guesses"]}', "codex", _results(), NOW, record)
    mi.inspect("electrical", lambda p: '{"verdict": "pass", "findings": []}', "claude-code", _results(), NOW, record)
    kept = mi.load(record)
    assert [v["verdict"] for v in kept] == ["hold", "pass"] and kept[0]["inspector"] == "codex"
    assert kept[1]["at"] == "2026-11-17T02:00:00" and kept[1]["model"] == "m:32b" and kept[1]["fingerprint"]
    assert mi.latest("electrical", kept[1]["fingerprint"], kept)["verdict"] == "pass"


def test_voice_and_the_roster_say_what_claude_passed_held_or_has_not_looked_at(tmp_path, monkeypatch):
    from core import specialist_models, specialist_roster

    record = tmp_path / "i.json"
    monkeypatch.setattr(mi, "RECORD", record)
    monkeypatch.setattr(specialist_models, "load", lambda folder=None: _results())
    mi.inspect("electrical", lambda p: '{"verdict": "pass"}', "claude-code", None, NOW, record)
    mi.inspect("greenhouse", lambda p: '{"verdict": "hold", "findings": ["guesses the night low"]}', "claude-code",
               None, NOW, record)
    said = mi.said()
    assert "Claude passed the models for Electrical" in said and "Held: Greenhouse systems (guesses the night low)" in said
    assert "Not inspected yet:" in said and "Night School inspects one a night" in said
    rows = {r["id"]: r for r in specialist_roster.roster()["specialists"]}
    assert rows["electrical"]["inspected"] == "pass" and rows["greenhouse"]["inspected"] == "hold"
    assert rows["embedded"]["inspected"] == "" and rows["strategy"]["inspected"] == ""


def test_night_school_inspects_one_a_night_with_her_teacher():
    import inspect as source

    from core import night_school

    code = source.getsource(night_school.night)
    assert code.index("model_inspection.inspect(") < code.index("specialists.study(")
    assert night_school.DEFAULTS["inspections"] is True and "waiting[0]" in code
