"""
tests.test_disagreements
==========================

Disagreements over a decision or a design (core/disagreements.py, T-0022,
DEC-0071 point 3): an objection names a real decision or doc, is answered,
goes to Zac when raised again after an answer, closes only when Zac
settles it at the keyboard, and shows in the dashboard's list with the
tasks whose review is still argued over.
"""

import pytest

from core import disagreements as dis
from core import work_activity as activity
from core import work_tasks as tasks_mod


@pytest.fixture
def repo(tmp_path):
    """A repository with one decision and one design doc, and an empty activity log."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "DECISIONS.md").write_text("### DEC-0071: Three things\n- Status: APPROVED\n",
                                                    encoding="utf-8")
    (tmp_path / "docs" / "X_PROPOSAL.md").write_text("# X\n", encoding="utf-8")
    return tmp_path, tmp_path / "activity.jsonl"


def test_an_objection_must_name_a_real_decision_or_design(repo):
    """A decision on record or a doc in docs/ that exists; anything else is refused, as is an empty why."""
    root, _ = repo
    assert dis.subject_of("dec-0071", root) == "DEC-0071" and dis.subject_of("docs/X_PROPOSAL.md", root)
    for bad in ("DEC-0999", "docs/MISSING.md", "core/x.py", "docs/../CLAUDE.md"):
        with pytest.raises(dis.DisagreementError):
            dis.subject_of(bad, root)
    with pytest.raises(dis.DisagreementError):
        dis.object_to("DEC-0071", "codex", " ", repo[1], root)


def test_a_disagreement_is_answered_then_goes_to_zac_when_it_stands(repo):
    """Objected: the author's move. Answered: the objector's. Raised again: Zac's, and only he closes it."""
    root, log = repo
    assert dis.object_to("docs/X_PROPOSAL.md", "codex", "It skips the undo.", log, root)["status"] == dis.OPEN
    with pytest.raises(dis.DisagreementError):
        dis.answer("DEC-0071", "claude", "nothing to answer", log, root)
    assert dis.answer("docs/X_PROPOSAL.md", "claude", "It has one: section 4.", log, root)["status"] == dis.ANSWERED
    assert dis.object_to("docs/X_PROPOSAL.md", "codex", "Section 4 isn't exact.", log, root)["status"] == dis.ZACS
    with pytest.raises(dis.DisagreementError):  # no person at the keyboard typing it back
        dis.settle("docs/X_PROPOSAL.md", "Exact undo first.", confirm=lambda q: "", log=log, root=root)
    done = dis.settle("docs/X_PROPOSAL.md", "Exact undo first.", confirm=lambda q: "docs/x_proposal.md", log=log,
                      root=root)
    assert done["status"] == "settled" and dis.open_disagreements(log, root / "tasks") == []
    assert [e["action"] for e in activity.events(log)] == ["object", "answer", "object", "settle"]  # all kept


def test_the_open_list_puts_zacs_first_and_includes_argued_reviews(repo):
    """The dashboard's list: a standing disagreement before an open one; a task whose review asked for changes is
    there with its reviewer, and one answered but still refused is Zac's."""
    root, log = repo
    folder = root / "tasks"
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="A change", status="review"), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0002", title="Another", status="review"), folder)
    activity.record("QA Engineer (codex)", "review", "T-0001", "changes: the test doesn't test it", log)
    activity.record("QA Engineer (codex)", "review", "T-0002", "changes: no", log)
    activity.record("claude", "resolve", "T-0002", "1 from codex: it does", log)
    activity.record("QA Engineer (codex)", "review", "T-0002", "changes: still no", log)
    activity.record("QA Engineer (codex)", "resolve", "T-0002", "x", log)  # an agent's resolve doesn't settle it
    activity.record("QA Engineer (codex)", "review", "T-0002", "changes: still no", log)
    activity.record("claude", "resolve", "T-0002", "1 from codex: it does", log)
    dis.object_to("DEC-0071", "codex", "Point 2 is too broad.", log, root)
    rows = dis.open_disagreements(log, folder)
    by = {r["subject"]: r for r in rows}
    assert by["DEC-0071"]["status"] == dis.OPEN and by["DEC-0071"]["kind"] == "decision"
    assert by["T-0001"]["status"] == dis.OPEN and by["T-0001"]["raised_by"] == ["QA Engineer (codex)"]
    assert by["T-0002"]["status"] == dis.ZACS and "--by zac" in by["T-0002"]["command"]
    assert rows[0]["subject"] == "T-0002"
