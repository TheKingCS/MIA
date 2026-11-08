"""
tests.test_dev_history
========================

The shared development history (core/dev_history.py, T-0021, DEC-0071
point 2): decisions, commits, failures and experiments read from their
records, each kept once (again on a change of status), git asked only for
what's new, nothing the person said carried in, and an agent's briefing
read from the kept record.
"""

from types import SimpleNamespace

from core import dev_history as dh
from core.dev_store import DevStore

SEP, END = dh._SEP, dh._END


def _root(tmp_path, status="PROPOSED"):
    """A repository with two decisions, the second in the given status."""
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "DECISIONS.md").write_text(
        "# Decisions\n\n### DEC-0001: One history\n- Status: APPROVED\n- Approved by: Zac, 2026-11-03\n\n"
        f"### DEC-0002: Something later\n- Status: {status}\n", encoding="utf-8")
    return tmp_path


def _log(*commits):
    """git log output in commits()'s format, newest first: (sha, subject, body, files)."""
    return "".join(f"{END}{sha}{SEP}2026-11-08T10:00:00-06:00{SEP}Claude{SEP}{subject}{SEP}{body}{SEP}\n\n"
                   + "\n".join(files) + "\n" for sha, subject, body, files in commits)


def test_a_commit_log_becomes_records_with_their_task_and_files_oldest_first():
    """A multi-line body doesn't break the split; the task is found in the subject or the body; added files are
    told from changed ones, and a rename counts as its new name."""
    text = _log(("bbbbbbbbbb", "Second", "Line one\nT-0021: line two", ["M\tcore/b.py", "R090\tcore/o.py\tcore/n.py"]),
                ("aaaaaaaaaa", "T-0020: first", "", ["A\tcore/a.py", "M\ttests/test_a.py"]))
    found = dh.parse_log(text)
    assert [c["ref"] for c in found] == ["aaaaaaaa", "bbbbbbbb"]
    assert found[0]["task"] == "T-0020" and found[0]["files"] == ["core/a.py", "tests/test_a.py"]
    assert found[0]["added"] == ["core/a.py"] and found[1]["files"] == ["core/b.py", "core/n.py"]
    assert found[1]["task"] == "T-0021" and found[1]["who"] == "Claude"


def test_sync_keeps_each_record_once_and_asks_git_only_for_whats_new(tmp_path):
    """Decisions and commits are added once; a decision's new status is added again; the second sync asks git for the
    commits after the last one kept; a record keeps when it happened as `on`."""
    root, store = _root(tmp_path), DevStore(tmp_path / "history")
    asked = []

    def git(_root, *args):
        """A stand-in git: knows two commits, then a third."""
        asked.append(args)
        if args[0] == "rev-parse":
            return "bbbbbbbb\n"
        if args[-1] == "bbbbbbbb..HEAD":
            return _log(("cccccccccc", "Third", "", ["core/c.py"]))
        return _log(("bbbbbbbbbb", "Second", "", ["core/b.py"]), ("aaaaaaaaaa", "First", "", ["core/a.py"]))

    assert dh.sync(root, store, git=git, lab=False) == 4
    assert dh.sync(root, store, git=git, lab=False) == 1  # only the third commit
    assert asked[-1][-1] == "bbbbbbbb..HEAD"
    _root(tmp_path, status="APPROVED")
    assert dh.sync(root, store, git=lambda *a: "", lab=False) == 1  # DEC-0002 approved is history too
    kinds = [(r["kind"], r["ref"], r.get("status", "")) for r in store.records()]
    assert ("decision", "DEC-0002", "APPROVED") in kinds and ("commit", "cccccccc", "") in kinds
    kept = next(r for r in store.records() if r["ref"] == "DEC-0001")
    assert kept["on"] == "2026-11-03" and dh.when(kept) == "2026-11-03" and kept["at"] > "2026-11-03"


def test_failures_carry_the_codes_words_never_what_the_person_said():
    """A Fix-It issue is kept by its key, its code-made title and its count; its examples stay in the person's log."""
    book = SimpleNamespace(issues=lambda days: [
        {"key": "tool:log_shift", "title": "The log shift tool broke", "count": 3, "status": "open",
         "last": "2026-11-07T09:00:00", "examples": [{"prompt": "something private"}]}])
    found = dh.failures(SimpleNamespace(failures=book))
    assert found == [{"kind": "failure", "ref": "tool:log_shift", "title": "The log shift tool broke", "status": "open",
                      "who": "MIA", "task": "", "detail": "3 times, last 2026-11-07", "at": "2026-11-07T09:00:00"}]
    assert "private" not in str(found) and dh.failures(SimpleNamespace()) == [] and dh.failures(None) == []


def test_a_briefing_names_the_cited_decisions_and_recent_work_on_the_tasks_files(tmp_path):
    """The decisions a task cites, and commits or experiments on its files or naming it; nothing for an unrelated
    task."""
    store = DevStore(tmp_path / "history")
    for r in ({"kind": "decision", "ref": "DEC-0071", "title": "Independent inspection", "status": "APPROVED"},
              {"kind": "commit", "ref": "aaaaaaaa", "title": "Touch a", "files": ["core/a.py"], "task": "",
               "at": "2026-11-07T10:00:00", "who": "Claude"},
              {"kind": "commit", "ref": "bbbbbbbb", "title": "Name it", "files": [], "task": "T-0021",
               "at": "2026-11-08T10:00:00", "who": "Claude"},
              {"kind": "experiment", "ref": "P-1", "title": "Try a", "status": "merged", "files": ["core/a.py"]},
              {"kind": "commit", "ref": "cccccccc", "title": "Elsewhere", "files": ["core/z.py"], "task": ""}):
        store.append(r)
    task = SimpleNamespace(id="T-0021", files=["core/a.py"], decisions=["DEC-0071"])
    text = dh.briefing(task, store)
    assert "DEC-0071 (APPROVED): Independent inspection" in text and "commit aaaaaaaa" in text
    assert "commit bbbbbbbb" in text and "lab P-1 (merged): Try a" in text and "Elsewhere" not in text
    assert dh.briefing(SimpleNamespace(id="T-9999", files=["core/q.py"], decisions=[]), store) == ""


def test_the_one_search_finds_a_decision_beside_the_chat(tmp_path, monkeypatch):
    """council.index() searches the history store too, so a kept decision is found by its words."""
    from core import council, work_activity

    monkeypatch.setattr(work_activity, "ACTIVITY", tmp_path / "activity.jsonl")
    monkeypatch.setattr(council, "_store", lambda: DevStore(tmp_path / "council"))
    monkeypatch.setattr(council, "sync", lambda repo, store: None)
    DevStore(tmp_path / "history").append({"kind": "decision", "ref": "DEC-0071", "title": "Independent inspection"})
    hits = dh.search("independent inspection", kinds=dh.KINDS)
    assert [h["ref"] for h in hits] == ["DEC-0071"] and hits[0]["source"] == "history"
