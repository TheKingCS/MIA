"""Independent review and Zac's approval (DEC-0069, core/work_review.py):
never reviewed by its author, approved only by a person at the keyboard,
and only after a review that approves it."""

import pytest

from core import work_agents as agents
from core import work_loop as loop
from core import work_review as rv
from core import work_tasks as tasks_mod
from tests.test_work_loop import REGISTRY, FakeLab


@pytest.fixture
def waiting(tmp_path):
    """T-0001, written by the Software Engineer on Claude Code, waiting for review."""
    folder, log = tmp_path / "tasks", tmp_path / "activity.jsonl"
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="A fix", files=["core/x.py"], body="Make x right."), folder)
    lab = FakeLab()
    lab.MERGED = "merged"

    def merge(pid, suite=None):
        p = lab.proposals[pid]
        p.status, p.merged_as, p.note = "merged", "abc1234567", "In."
        return p

    lab.approve = merge
    registry = agents.parse(REGISTRY)
    loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log)
    return folder, log, registry, lab


def _review(waiting, role, said):
    folder, log, registry, _ = waiting
    return rv.review("T-0001", role, registry, ask=lambda provider, prompt: said, diff=lambda pid: "+ fixed x",
                     folder=folder, log=log)


def test_a_reviewer_reads_the_change_and_gives_a_verdict(waiting):
    seen = {}
    folder, log, registry, _ = waiting
    found = rv.review("T-0001", "QA Engineer", registry, folder=folder, log=log, diff=lambda pid: "+ fixed x",
                      ask=lambda provider, prompt: seen.update(provider=provider, prompt=prompt) or "Looks right.\nVERDICT: approve")
    assert found == "approve" and seen["provider"] == "ollama" and "+ fixed x" in seen["prompt"]
    assert "Review: approve" in tasks_mod.load(folder)["T-0001"].body


def test_the_author_cant_review_its_own_change(waiting):
    folder, log, _, _ = waiting
    with pytest.raises(agents.AgentError, match="can't review"):  # its tier can't review anything
        _review(waiting, "Software Engineer", "VERDICT: approve")
    # A reviewer on the provider that wrote it, while another provider could review: refused.
    data = {**REGISTRY, "roles": REGISTRY["roles"] + [{"role": "Security Auditor", "provider": "claude-code", "tier": "review"}]}
    with pytest.raises(rv.ReviewError, match="wrote it"):
        rv.review("T-0001", "Security Auditor", agents.parse(data), ask=lambda pr, pm: "VERDICT: approve",
                  diff=lambda pid: "+ x", folder=folder, log=log)


def test_a_review_with_no_clear_verdict_counts_as_changes():
    assert rv.verdict("Seems fine to me.") == "changes"
    assert rv.verdict("VERDICT: changes ... no, VERDICT: approve") == "approve"


def test_approval_needs_an_approving_review_first(waiting):
    folder, log, _, lab = waiting
    with pytest.raises(rv.ReviewError, match="independent review"):
        rv.approve("T-0001", confirm=lambda q: "T-0001", lab=lab, folder=folder, log=log)
    _review(waiting, "QA Engineer", "A real bug in x.\nVERDICT: changes")
    with pytest.raises(rv.ReviewError, match="objection from QA Engineer"):
        rv.approve("T-0001", confirm=lambda q: "T-0001", lab=lab, folder=folder, log=log)


def test_only_a_person_typing_the_id_approves(waiting):
    folder, log, _, lab = waiting
    _review(waiting, "QA Engineer", "VERDICT: approve")

    def headless(question):
        raise EOFError

    for confirm in (headless, lambda q: "", lambda q: "yes"):
        with pytest.raises(rv.ReviewError, match="only Zac"):
            rv.approve("T-0001", confirm=confirm, lab=lab, folder=folder, log=log)
    assert rv.approve("T-0001", confirm=lambda q: "t-0001", lab=lab, folder=folder, log=log) == "abc1234567"
    task = tasks_mod.load(folder)["T-0001"]
    assert task.status == "done" and "merged as abc1234567" in task.body


def test_an_objection_cant_be_outvoted_only_answered(waiting):
    """Zac: a disagreement is recorded and resolved, not silently discarded."""
    folder, log, _, lab = waiting
    _review(waiting, "QA Engineer", "The retry hides a real error.\nVERDICT: changes")
    _review(waiting, "QA Engineer", "Looks fine.\nVERDICT: approve")  # a later yes doesn't erase the no
    with pytest.raises(rv.ReviewError, match="objection from QA Engineer"):
        rv.approve("T-0001", confirm=lambda q: "T-0001", lab=lab, folder=folder, log=log)
    with pytest.raises(rv.ReviewError, match="Say how"):
        rv.resolve("T-0001", "claude", "  ", folder=folder, log=log)
    assert rv.resolve("T-0001", "claude", "the retry now logs the error first", folder=folder, log=log) == 1
    assert rv.open_objections("T-0001", log) == []
    assert "Resolved the objection from QA Engineer (ollama): the retry now logs" in tasks_mod.load(folder)["T-0001"].body
    assert rv.approve("T-0001", confirm=lambda q: "T-0001", lab=lab, folder=folder, log=log)


def test_a_disagreement_that_outlasts_its_answer_is_zacs_to_settle(waiting):
    folder, log, _, lab = waiting
    _review(waiting, "QA Engineer", "A problem.\nVERDICT: changes")
    rv.resolve("T-0001", "claude", "checked: it doesn't hold", folder=folder, log=log)
    _review(waiting, "QA Engineer", "VERDICT: changes")  # still no, with nothing to answer
    rv.resolve("T-0001", "claude", "nothing new raised", folder=folder, log=log)
    with pytest.raises(rv.ReviewError, match="review that approves"):  # an agent can't settle it
        rv.approve("T-0001", confirm=lambda q: "T-0001", lab=lab, folder=folder, log=log)
    rv.resolve("T-0001", "zac", "read both; the change is right", folder=folder, log=log)
    assert rv.approve("T-0001", confirm=lambda q: "T-0001", lab=lab, folder=folder, log=log)

