"""Fable's review of Opus's work, 2026-11-20, batch A (authority and actions): the capability check sees how tools
really reach kinds; the lab's proof must be seen to pass; the read-back checks the record a line is about; a failed
change takes its history back; a stop isn't a taught task's failure; a held action is "refused"."""
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.dev_lab as lab
from core import capability_check as cc
from core import read_back
from core.undo_log import Change
from tests.test_dev_lab import git, repo, suite  # noqa: F401  (the fixture and the stand-in suite)


def test_the_capability_check_reads_run_and_run_as_tool_as_well_as_propose():
    """Most tools reach a kind through their module's `_run` or `run_as_tool`; the check sees those links."""
    def through_run(context, args):
        """Runs a kind through the module's helper."""
        return _run(context, "meal.plan", args)  # noqa: F821 - read as text, never called

    def through_tool(context, args):
        """Runs a kind as a tool."""
        return run_as_tool(context, "grant.take_back", args)  # noqa: F821

    assert cc.proposed_kinds(through_run) == ["meal.plan"] and cc.proposed_kinds(through_tool) == ["grant.take_back"]
    described = cc.describe(dict(__import__("core.parity", fromlist=["x"]).desktop_registry()._actions), {}, {}, set())
    assert sum(1 for d in described.values() if d["proposes"]) > 50  # it was 5 of 463 before


def test_a_test_that_only_errors_on_the_old_code_or_isnt_seen_to_pass_is_no_proof(repo):
    """An import error on the starting code names a file, not a test; and a named test must be PASSED in the lab."""
    p = lab.create("Fix", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 3\n"))
    errored = lab.check(p.proposal_id, suite=suite({"*": []}), proof=lambda cwd, files: {"failed": ["tests/test_new.py"]})
    assert errored.status == lab.NOT_READY and errored.tests["shown_by"] == []
    base_fails = suite({p.proposal_id: [], "*": ["tests/test_a.py::old"]})
    unseen = lab.check(p.proposal_id, suite=base_fails, passing=lambda cwd, tests: set())  # deleted, renamed or skipped
    assert unseen.status == lab.NOT_READY and "DEC-0224" in unseen.note
    seen = lab.check(p.proposal_id, suite=base_fails, passing=lambda cwd, tests: set(tests))
    assert seen.status == lab.READY and seen.tests["shown_by"] == ["tests/test_a.py::old"]


def test_passing_reads_pytests_own_passed_lines(tmp_path, monkeypatch):
    """The real check: a passing test is named, a failing or missing one isn't."""
    monkeypatch.setattr(lab, "_python", lambda: __import__("sys").executable)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n\ndef test_bad():\n    assert False\n")
    found = lab._passing(tmp_path, ["tests/test_x.py::test_ok", "tests/test_x.py::test_bad", "tests/test_x.py::test_gone"])
    assert found == {"tests/test_x.py::test_ok"}


def test_practice_is_graded_without_the_proof_a_merge_needs(repo):
    """Her coder's shadow attempts can't always add a test; the grade says whether one was there."""
    p = lab.create("Practice", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 8\n"))
    graded = lab.check(p.proposal_id, suite=suite({"*": []}), require_proof=False)
    assert graded.status == lab.READY and graded.tests["shown_by"] == []


def _projects(ids):
    """A view whose projects store holds these ids."""
    return SimpleNamespace(projects=SimpleNamespace(all_projects=lambda: [SimpleNamespace(project_id=i, name=i) for i in ids]))


def test_the_read_back_checks_the_record_a_line_is_about_and_knows_dropped():
    """A second ref may rightly dangle; a dropped record isn't expected back; the first ref still is."""
    related = Change("t", None, touched=[("project_updated", ["project:p1", "project:gone"])])
    assert read_back.check(_projects(["p1"]), related) == []
    dropped = Change("t", None, touched=[("project_dropped", ["project:p2"])])
    assert read_back.check(_projects([]), dropped) == []
    missing = Change("t", None, touched=[("project_added", ["project:p3"])])
    assert read_back.check(_projects([]), missing) == ["project:p3 doesn't read back"]


def test_a_failed_change_takes_its_history_lines_back(tmp_path, monkeypatch):
    """The events a failed change recorded are reversed by one "undone" line, so the history's sums don't count them."""
    from core import actions, life_events

    recorded = []
    monkeypatch.setattr(life_events, "record", lambda where, type, summary, refs=(), payload=None, **kw:
                        recorded.append((type, payload)))
    monkeypatch.setattr("core.live.bump", lambda: None)
    monkeypatch.setattr("core.main_thread.publish", lambda *a, **k: None)
    change = Change("action_bill.pay", "p1", events=["e1", "e2"])
    assert actions._put_back(SimpleNamespace(life_events=object()), change) is True
    assert recorded == [("undone", {"label": "action_bill.pay", "reverses": ["e1", "e2"], "failed": True})]


def test_a_stop_isnt_held_against_a_taught_task():
    """Stopped by him or by its time: the run isn't recorded as a failed one, and he isn't told to teach it again."""
    from core import browser_routines

    runs = []
    store = SimpleNamespace(record_run=lambda *a, **k: runs.append(k))
    routine = {"id": "r1", "steps": [{"kind": "open", "url": "https://example.com"}]}
    said = browser_routines._stopped(store, routine, 0, [], "everything is stopped", counts=False)
    assert runs == [] and "Show me again" not in said
    browser_routines._stopped(store, routine, 0, [], "the page changed")
    assert runs and runs[0]["clean"] is False


def test_what_the_grants_hold_back_is_refused():
    """A tier that needs his yes, or a kind that's never hers, is an ActionError of the kind `refused`."""
    from core import grants
    from core.actions import Refused, error_kind

    with pytest.raises(Refused) as held:
        grants.require("bill.pay", grants.MIA, granted=True)
    assert error_kind(held.value) == "refused"
