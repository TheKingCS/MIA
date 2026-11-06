"""The weekly benchmarks (build plan step 5, core/benchmarks.py): graded by code against the run before,
kept as grades only (never an answer), read by the answers.* loops."""

from datetime import datetime, timedelta, timezone

from core import benchmarks, loops
from core.dev_store import DevStore

BY_ID = {l.id: l for l in loops.LOOPS}


def row(qid, route="plan: money_left", warnings=(), note="", seconds=3.0, **kw):
    return {"id": qid, "route": route, "warnings": list(warnings), "note": note, "seconds": seconds,
            "answer": "You have 412 left this month.", **kw}


def test_a_grade_keeps_no_words_of_the_answer():
    g = benchmarks.grade(row("B1", warnings=["Question plan money_left: the answer had numbers not on the sheet"]))
    assert g["rank"] == 0 and g["flags"] and "answer" not in g and "412" not in str(g)
    assert benchmarks.rank("model, 12 tools") == 1 and benchmarks.rank("model, 3 tools", "the model didn't answer") == 2
    assert benchmarks.rank("error") == 3


def test_what_falls_since_the_run_before():
    before = [benchmarks.grade(r) for r in (row("A1"), row("A2"), row("A3", seconds=10), row("A4", route="model, 9 tools"))]
    now = [benchmarks.grade(r) for r in (row("A1", route="model, 9 tools"), row("A2", note="wanted to add_expense"),
                                         row("A3", seconds=40), row("A4", route="plan: priorities"), row("A5"))]
    fell = {f["id"]: f["why"] for f in benchmarks.falls(before, now)}
    assert set(fell) == {"A1", "A2", "A3"}  # A4 got better; A5 is new
    assert "route plan: money_left -> model, 9 tools" in fell["A1"] and "10s -> 40s" in fell["A3"]


def test_the_loops_read_the_latest_two_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmarks, "DEV_DATA", tmp_path)
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    benchmarks.keep("intelligence", [benchmarks.grade(row("A1")), benchmarks.grade(row("A2"))])
    benchmarks.keep("intelligence", [benchmarks.grade(row("A1", route="error")), benchmarks.grade(row("A2"))])
    fell = BY_ID["answers.benchmark"].measure(None)
    assert fell.value == 1 and "A1" in fell.detail
    assert loops.judge(BY_ID["answers.benchmark"], fell, [])["state"] == "below"
    assert BY_ID["answers.benchmark_clean"].measure(None).value == 0.5
    benchmarks.keep("routing", [benchmarks.grade_route({"id": "A1", "route": "model only"}),
                                benchmarks.grade_route({"id": "A2", "route": "plan"})])
    assert BY_ID["answers.routing"].measure(None).value == 1
    benchmarks.keep("corpus", [benchmarks.grade({"id": "c1", "surface": "glasses", "route": "model, 0 tools",
                                                 "flags": ["closing_offer"]}),
                               benchmarks.grade({"id": "c1", "surface": "phone", "route": "model, 0 tools"})])
    assert BY_ID["answers.corpus"].measure(None).value == 0.5


def test_weekly(tmp_path):
    store = DevStore(tmp_path)
    assert benchmarks.due(store=store)
    benchmarks.keep("intelligence", [], store=store)
    now = datetime.now(timezone.utc)
    assert not benchmarks.due(now + timedelta(days=6), store=store)
    assert benchmarks.due(now + timedelta(days=7, minutes=1), store=store)


def test_a_test_run_never_asks_the_real_model():
    assert "not from a test run" in benchmarks.run_now()
