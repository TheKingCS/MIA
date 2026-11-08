"""MIA's improvement loops (DEC-0094, core/loops.py): measured in code, judged
against a floor and their own trend, a task opened once while a loop is
below, offers for the person through the gate, never a change by itself."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from core import loops
from core import work_tasks as tasks_mod
from core.dev_store import DevStore


def loop(**kw):
    """A loop with a reading of 3 of 10, with any field overridden."""
    base = dict(id="t.loop", area="test", what="things that went wrong", scope="device",
                measure=lambda c: loops.Reading(3, 10, "3 of 10"), floor=1, files=("core/x.py",))
    return loops.Loop(**{**base, **kw})


def test_judging_a_reading():
    """A reading is judged below its floor, ok, thin, or slid against its usual."""
    low = loop(floor=1)
    assert loops.judge(low, loops.Reading(3, 10), [])["state"] == "below"
    assert loops.judge(low, loops.Reading(0, 10), [])["state"] == "ok"
    assert loops.judge(low, None, [])["state"] == "none"
    assert loops.judge(loop(min_n=20), loops.Reading(3, 10), [])["state"] == "thin"  # three of ten means little
    trend = loop(floor=None)
    assert loops.judge(trend, loops.Reading(9, 10), [4, 5, 4, 5, 4])["state"] == "slid"  # worse than its usual
    assert loops.judge(trend, loops.Reading(5, 10), [4, 5, 4, 5, 4])["state"] == "ok"
    high = loop(better="higher", floor=0.7)
    assert loops.judge(high, loops.Reading(0.6, 10), [])["state"] == "below"


@pytest.fixture
def place(tmp_path, monkeypatch):
    """Points the loops' development data at a temporary folder; where tasks and the activity log go."""
    monkeypatch.setattr(loops, "DEV_DATA", tmp_path / "dev")
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    return tmp_path / "tasks", tmp_path / "activity.jsonl"


def test_a_loop_below_its_floor_opens_one_task_with_numbers_only(place):
    folder, log = place
    now = datetime(2026, 11, 6, 9, tzinfo=timezone.utc)
    one = loop()
    loops.run(None, "device", now=now, loops=(one,), tasks_dir=folder, log=log)
    tasks = tasks_mod.load(folder)
    assert len(tasks) == 1
    task = next(iter(tasks.values()))
    assert task.source == "loop:t.loop" and task.files == ["core/x.py"] and "3 of 10" in task.body
    loops.run(None, "device", now=now + timedelta(days=1), loops=(one,), tasks_dir=folder, log=log)
    assert len(tasks_mod.load(folder)) == 1  # still below: the same task, not another
    task.status = "done"
    tasks_mod.save(task, folder)
    loops.run(None, "device", now=now + timedelta(days=2), loops=(one,), tasks_dir=folder, log=log)
    assert len(tasks_mod.load(folder)) == 2  # done but still below: reopened as new work


def test_once_a_day_and_a_broken_measure_never_stops_the_rest(place):
    folder, log = place
    now = datetime(2026, 11, 6, 9, tzinfo=timezone.utc)
    calls = []
    counted = loop(id="a", measure=lambda c: calls.append(1) or loops.Reading(0, 1))
    broken = loop(id="b", measure=lambda c: 1 / 0)
    loops.run(None, "device", now=now, loops=(broken, counted), tasks_dir=folder, log=log)
    loops.run(None, "device", now=now + timedelta(hours=3), loops=(broken, counted), tasks_dir=folder, log=log)
    assert len(calls) == 1  # once a day
    kept = loops.history(None, "device")
    assert kept["b"][-1]["state"] == "error" and kept["a"][-1]["state"] == "ok"


def test_a_persons_loops_keep_their_history_in_their_folder_and_offer_through_the_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    person = SimpleNamespace(traces=SimpleNamespace(data_dir=tmp_path / "profiles" / "zac"))
    tidy = loop(id="p.tidy", scope="person", acts="offer", floor=0, what="screens nobody opens",
                measure=lambda c: loops.Reading(2, 3, "2 of 3 not opened in 30 days"))
    offers = loops.run(person, "person", loops=(tidy,))
    assert offers[0].message == "Screens nobody opens: 2 of 3 not opened in 30 days." and offers[0].topic == "loop:p.tidy"
    assert (tmp_path / "profiles" / "zac" / "loops").exists()


def test_the_real_registry_measures_without_breaking():
    ids = [l.id for l in loops.LOOPS]
    assert len(ids) == len(set(ids)) and all(l.scope in ("device", "person") for l in loops.LOOPS)
    person = SimpleNamespace(traces=None, failures=None, ratings=None, creations=None)
    for l in loops.LOOPS:
        if l.scope == "person":
            assert l.measure(person) is None  # nothing to measure yet is "none", not a crash


def test_the_answer_loops_read_traces_and_the_fix_it_log():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    turns = [{"at": now, "seconds": 3}] * 30 + [{"at": now, "seconds": 40}] * 10
    fails = [{"kind": "rephrased"}] * 4 + [{"kind": "talked_instead"}] * 2
    person = SimpleNamespace(traces=SimpleNamespace(recent=lambda n: turns),
                             failures=SimpleNamespace(events=lambda days=None: fails),
                             ratings=SimpleNamespace(counts=lambda: {"up": 6, "down": 4}))
    by_id = {l.id: l for l in loops.LOOPS}
    assert by_id["answers.failures"].measure(person).value == 15.0  # 6 in 40 turns
    assert by_id["answers.rephrased"].measure(person).value == 10.0
    assert by_id["answers.slow"].measure(person).value == 0.25
    thumbs = by_id["answers.thumbs"].measure(person)
    assert thumbs.value == 0.6 and loops.judge(by_id["answers.thumbs"], thumbs, [])["state"] == "below"
