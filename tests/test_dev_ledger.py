"""The independence ledger (DEC-0075, core/dev_ledger.py): computed from the
history, scored by a lower confidence bound, stages proposed by the evidence
and confirmed by Zac, never above what the evidence supports now."""

import pytest

from core import dev_ledger as dl
from core import work_activity as activity
from core import work_tasks as tasks_mod


@pytest.fixture
def place(tmp_path):
    """Two tasks (one in review, one done) in a temporary folder, and an activity log beside them."""
    folder, log = tmp_path / "tasks", tmp_path / "activity.jsonl"
    tasks_mod.save(tasks_mod.Task(id="T-0019", title="OCR tests", files=["tests/test_ocr.py"], status="review"), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0020", title="Inspection", files=["core/inspection.py"], status="done"), folder)
    return folder, log


def test_a_few_tries_mean_little_many_mean_more():
    assert dl.wilson(3, 3) < 0.6 < dl.wilson(30, 30)
    assert dl.wilson(0, 0) == 0.0 and dl.wilson(9, 10) > dl.wilson(5, 10)
    assert dl.stage_for(3, 1.0, True) == 1 and dl.stage_for(5, 0.1, True) == 2
    assert dl.stage_for(12, 0.65, True) == 3 and dl.stage_for(31, 0.92, True) == 5


def test_skills_follow_what_a_task_touched():
    T = tasks_mod.Task
    assert dl.skill_of(T(id="a", title="", files=["tests/test_x.py"])) == "fix failing tests"
    assert dl.skill_of(T(id="a", title="", files=["docs/x.md"])) == "documentation"
    assert dl.skill_of(T(id="a", title="", files=["web/x.js", "core/y.py"])) == "engine changes"


def test_outcomes_from_the_real_shape_of_a_task(place):
    folder, log = place
    rec = lambda who, action, task, detail: activity.record(who, action, task, detail, log)  # noqa: E731
    rec("Debugging Engineer (claude-code)", "loop", "T-0019", "write: fixed both causes")
    rec("QA Engineer (ollama-coder)", "review", "T-0019", "changes: _WINDOWS_DEFAULT unused")
    rec("zac", "resolve", "T-0019", "the fix is right")
    rec("zac", "approve", "T-0019", "merged abc1234567")
    rec("MIA (ollama-coder)", "shadow", "T-0019", "fail: changed nothing")
    rec("Software Engineer (claude-code)", "loop", "T-0020", "write: done")
    rec("Security Auditor (codex)", "review", "T-0020", "approve: fine")
    rec("zac", "approve", "T-0020", "reverted: It broke here")
    found = dl.outcomes(activity.events(log), tasks_mod.load(folder))
    got = {(o["provider"], o["task"], o["why"]): o["passed"] for o in found}
    assert got[("claude-code", "T-0019", "merged")] is True
    assert got[("ollama-coder", "T-0019", "objection overturned")] is False  # the wrong objection counts against it
    assert got[("ollama-coder", "T-0019", "shadow attempt")] is False
    assert got[("claude-code", "T-0020", "reverted")] is False
    assert got[("codex", "T-0020", "approved a change that broke")] is False


def test_stages_need_zacs_confirmation_and_never_outrun_the_evidence(place):
    folder, log = place
    for n in range(12):  # twelve shadow passes on test fixes
        activity.record("MIA (ollama-coder)", "shadow", "T-0019", "pass: fixed 1", log)
    row = dl.ledger(log, folder)["ollama-coder"]["fix failing tests"]
    assert row["attempts"] == 12 and row["stage"] == 3 and row["proposed"] and row["shown"] == 2  # waits for Zac
    with pytest.raises(ValueError, match="supports Contributor at most"):
        dl.confirm("ollama-coder", "fix failing tests", 4, log)
    dl.confirm("ollama-coder", "fix failing tests", 3, log)
    assert dl.ledger(log, folder)["ollama-coder"]["fix failing tests"]["shown"] == 3
    for n in range(20):  # then she gets worse: the evidence drops, and so does what's shown
        activity.record("MIA (ollama-coder)", "shadow", "T-0019", "fail: new failures", log)
    row = dl.ledger(log, folder)["ollama-coder"]["fix failing tests"]
    assert row["stage"] == 2 and row["shown"] == 2


def test_a_revert_then_a_reopen_is_pending_not_a_failure(place):
    folder, log = place
    activity.record("Debugging Engineer (claude-code)", "loop", "T-0019", "write: fixed", log)
    activity.record("zac", "approve", "T-0019", "reverted: the baseline", log)
    activity.record("claude", "move", "T-0019", "review: rebuilt on the running copy", log)
    assert [o for o in dl.outcomes(activity.events(log), tasks_mod.load(folder)) if o["why"] in ("merged", "reverted")] == []
    activity.record("zac", "approve", "T-0019", "merged abc", log)
    assert [o["passed"] for o in dl.outcomes(activity.events(log), tasks_mod.load(folder)) if o["why"] == "merged"] == [True]
