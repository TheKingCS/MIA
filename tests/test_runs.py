"""
tests.test_runs
=================

The run record (prompt 23's review, UI-1, DEC-0188; core/runs.py): one record for anything MIA runs in steps. A run
moves through running, waiting and an end, keeping each step with what she said; a restart never leaves a cut-off
run looking alive or calls it done (shown with a real process killed mid-step); a browser routine waiting for his OK
says where it is, ends "stopped" when MIA restarts, carries on after he approves, and ends at once when he says no
or nobody approves in time; "what's running?" answers from it; a run book rebuilt in the same process leaves live
runs alone (`restarted` clears the once-per-process mark to stand in for a new process).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core import browser as browser_module
from core.runs import KEEP_DONE, RunBook, describe, summary
from tests.test_browser import DONE, SHOP, edge, tool, world  # noqa: F401  (the browser test world)


def restarted(data_dir, context=None):
    """The run book as a new MIA process would load it (the once-per-process recovery mark cleared)."""
    from core import runs

    runs._RECOVERED.clear()
    return RunBook(context, data_dir=data_dir)


def test_a_run_moves_through_its_steps_to_an_end_and_says_where_it_is(tmp_path):
    book = RunBook(data_dir=tmp_path)
    run = book.start("browser_routines", "browser_routine:ab", "Order widgets")
    assert run.status == "running" and run.at == "1" and book.open_runs() == [run]
    book.step(run.run_id, "1", "Opened the shop.", actions=["p1"], next_at="2")
    book.wait(run.run_id, "2", "commit", "Press Place order on shop.example")
    assert run.status == "waiting" and run.waiting["kind"] == "commit" and "waiting for you at step 2" in describe(run)
    book.finish(run.run_id, "done")
    assert run.status == "done" and run.waiting is None and not book.open_runs()
    book.step(run.run_id, "3", "too late")  # a finished run is left alone
    assert len(run.steps) == 1 and run.steps[0]["actions"] == ["p1"]
    with pytest.raises(ValueError):
        book.start("shell", "x", "y")
    again = RunBook(data_dir=tmp_path)
    assert again.get(run.run_id).status == "done" and again.get(run.run_id).steps[0]["said"] == "Opened the shop."


def test_a_restart_never_leaves_a_cut_off_run_looking_alive(tmp_path):
    book = RunBook(data_dir=tmp_path)
    mid = book.start("workflows", "creation:C-1", "Weekly totals")
    routine = book.start("browser_routines", "browser_routine:ab", "Order widgets")
    book.wait(routine.run_id, "4", "commit", "Press Place order")
    skill = book.start("taught_skills", "skill:s1", "Friday reset")
    book.wait(skill.run_id, "2", "ask", "Which room first?")
    later = restarted(tmp_path)  # MIA started again
    assert later.get(mid.run_id).status == "stopped" and "in progress" in later.get(mid.run_id).why
    assert later.get(routine.run_id).status == "stopped" and "run it again from step 4" in later.get(routine.run_id).why
    assert later.get(skill.run_id).status == "waiting"  # a skill keeps its own wait across a restart


def test_a_process_killed_mid_step_comes_back_stopped_never_done(tmp_path):
    child = (
        "import os, sys\n"
        "from core.runs import RunBook\n"
        f"book = RunBook(data_dir=r'{tmp_path}')\n"
        "run = book.start('workflows', 'creation:C-9', 'Nightly')\n"
        "book.step(run.run_id, '1', 'read 3 records', next_at='2')\n"
        "print(run.run_id, flush=True)\n"
        "os._exit(9)  # killed mid-step 2: no clean-up of any kind\n"
    )
    out = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True,
                         cwd=Path(__file__).resolve().parent.parent, timeout=60)
    run_id = out.stdout.strip().splitlines()[-1]
    run = restarted(tmp_path).get(run_id)
    assert run.status == "stopped" and run.at == "2" and len(run.steps) == 1


def test_only_the_last_finished_runs_are_kept_and_open_ones_always(tmp_path):
    book = RunBook(data_dir=tmp_path)
    keep = book.start("taught_skills", "skill:s", "Still going")
    book.wait(keep.run_id, "1", "you", "Your turn")
    for n in range(KEEP_DONE + 5):
        book.finish(book.start("workflows", f"creation:{n}", f"W{n}").run_id)
    stored = json.loads((tmp_path / "runs.json").read_text(encoding="utf-8"))["runs"]
    assert len(stored) == KEEP_DONE + 1 and any(r["run_id"] == keep.run_id for r in stored)
    (tmp_path / "runs.json").write_text("not json", encoding="utf-8")
    assert RunBook(data_dir=tmp_path).open_runs() == []  # an unreadable file is no runs, never a crash


def _waiting_routine(context):
    """A routine that opens the shop and presses Place order, run until it waits for the person."""
    context.runs = RunBook(context, data_dir=Path(context.browser_routines.data_dir))
    context.browser_routines.add("Order widgets", SHOP, [{"kind": "open", "url": SHOP},
                                                        {"kind": "click", "role": "button", "name": "Place order"}])
    said = tool(context, "do_browser_task", name="Order widgets")
    [run] = context.runs.open_runs()
    return said, run


def test_a_routine_waiting_on_a_commit_says_where_it_is_and_finishes_after_the_yes(world):  # noqa: F811
    said, run = _waiting_routine(world)
    assert "Place order" in said and run.status == "waiting" and run.at == "2" and run.waiting["kind"] == "commit"
    assert "waiting for you at step 2" in summary(world)
    [proposal] = world.actions.pending(world.me.profile_id)
    world.actions.approve(world, proposal.proposal_id)
    assert run.status == "done" and [s["at"] for s in run.steps] == ["1", "2"]


def test_a_routine_ends_at_once_when_the_person_says_no(world):  # noqa: F811
    _said, run = _waiting_routine(world)
    [proposal] = world.actions.pending(world.me.profile_id)
    world.actions.reject(world, proposal.proposal_id)
    assert run.status == "stopped" and "you said no" in run.why and not world.browsers.for_person(world).pending
    assert ("click", 5) not in edge(world).did


def test_a_routine_ends_when_nobody_approves_in_time(world, monkeypatch):  # noqa: F811
    _said, run = _waiting_routine(world)
    browser = world.browsers.for_person(world)
    later = time.time() + 10 ** 6  # well past the half hour a held step waits
    monkeypatch.setattr(browser_module.time, "time", lambda: later)
    browser._expire()
    assert run.status == "stopped" and "within 30 minutes" in run.why


def test_a_routine_waiting_when_mia_restarts_says_to_run_it_again_from_that_step(world):  # noqa: F811
    _said, run = _waiting_routine(world)
    later = restarted(Path(world.browser_routines.data_dir), world)
    again = later.get(run.run_id)
    assert again.status == "stopped" and "run it again from step 2" in again.why


def test_whats_running_answers_from_the_record(tmp_path):
    from types import SimpleNamespace

    context = SimpleNamespace(runs=RunBook(data_dir=tmp_path))
    assert "Nothing's running" in summary(context)
    context.runs.start("workflows", "creation:C-2", "Tidy receipts")
    assert summary(context).startswith("Running now: Tidy receipts: at step 1.")
    assert "can't see" in summary(SimpleNamespace())


def test_the_dashboard_shows_whats_running_and_what_stopped_and_the_tool_says_it(tmp_path):
    """Agent Activity's Running column (core/agent_activity.py) lists open runs and ones that stopped in the last day,
    each linking to its own page; the whats_running tool answers from the same record; the demo data has the column."""
    from datetime import datetime
    from types import SimpleNamespace

    from core.agent_activity import _running, activity
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_taught_skill_actions import register_taught_skill_actions

    context = SimpleNamespace(runs=RunBook(data_dir=tmp_path))
    waiting = context.runs.start("browser_routines", "browser_routine:ab", "Order widgets")
    context.runs.wait(waiting.run_id, "2", "commit", "Press Place order")
    broke = context.runs.start("workflows", "creation:C-0003", "Seed check")
    context.runs.finish(broke.run_id, "failed", "a store couldn't be read")
    rows = _running(context, datetime.now())
    assert rows[0]["page"] == "browser.html" and "waiting for you at step 2" in rows[0]["what"]
    assert rows[1]["page"] == "made.html?id=C-0003" and rows[1]["status"] == "failed"
    assert activity(context, None)["any"] is True
    registry = AssistantActionRegistry()
    register_taught_skill_actions(registry)
    said = registry._actions["whats_running"].handler(context, {})
    assert said.startswith("Running now: Order widgets: waiting for you at step 2")
    root = Path(__file__).resolve().parent.parent
    demo = json.loads((root / "docs" / "schema" / "dashboard.example.json").read_text(encoding="utf-8"))
    assert demo["activity"]["running"][0]["page"] == "browser.html"
    assert 'col("Running", a.running' in (root / "web" / "welcome.js").read_text(encoding="utf-8")


def test_every_run_matches_its_published_schema(tmp_path):
    """docs/schema/run.schema.json is the one contract every engine's runs are checked against (Opus's review)."""
    from dataclasses import asdict

    from core import schema_check

    schema = schema_check.load("run.schema.json")
    book = RunBook(data_dir=tmp_path)
    run = book.start("taught_skills", "skill:s1", "Friday reset")
    book.step(run.run_id, "1", "Friday reset.", next_at="2")
    book.wait(run.run_id, "2", "ask", "Which room?")
    assert schema_check.errors(asdict(run), schema) == []
    book.finish(run.run_id, "stopped", "stopped by you")
    assert schema_check.errors(asdict(run), schema) == []
    assert schema_check.errors({**asdict(run), "status": "paused"}, schema)  # not a status


def test_a_run_book_rebuilt_in_the_same_process_leaves_live_runs_alone(tmp_path):
    """Fable's review: a store reload (after an undo or a sync) builds a new RunBook; runs really going must not be
    marked as cut off. Only the first load in a process recovers."""
    from core import runs

    runs._RECOVERED.clear()
    book = RunBook(data_dir=tmp_path)
    run = book.start("workflows", "creation:C-1", "Weekly totals")
    reloaded = RunBook(data_dir=tmp_path)  # the same process, the store built again
    assert reloaded.get(run.run_id).status == "running"
    assert restarted(tmp_path).get(run.run_id).status == "stopped"
