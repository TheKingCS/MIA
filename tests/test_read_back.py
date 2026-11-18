"""Tests for the generic read-back after a change (DEC-0218, LS-05, core/read_back.py): the files a change wrote
still hold what it left, and the records its history names still resolve, unless it removed them."""
from types import SimpleNamespace

from core import read_back
from core.atomic_write import atomic_write_text
from core.undo_log import Change, note_event, recording


def _context(projects):
    """A view with one projects store holding the given ids."""
    return SimpleNamespace(projects=SimpleNamespace(
        all_projects=lambda: [SimpleNamespace(project_id=p, name=p) for p in projects]))


def test_a_change_whose_files_and_records_are_there_reads_back(tmp_path):
    """What it wrote is still there and the project it named resolves: nothing to say."""
    with recording("t", None) as change:
        atomic_write_text(tmp_path / "a.json", "{}", live=False)
        note_event("e1", ["project:p1"], "project_added")
    assert read_back.check(_context(["p1"]), change) == []


def test_a_file_changed_or_gone_after_the_write_doesnt_read_back(tmp_path):
    """Another writer replaced it, or it vanished: both said plainly."""
    with recording("t", None) as change:
        atomic_write_text(tmp_path / "a.json", "{}", live=False)
        atomic_write_text(tmp_path / "b.json", "{}", live=False)
    (tmp_path / "a.json").write_text("[1]")
    (tmp_path / "b.json").unlink()
    assert read_back.check(_context([]), change) == ["a.json doesn't hold what was written", "b.json isn't there"]


def test_a_named_record_that_isnt_there_doesnt_read_back():
    """The history says it added project p2, but the store has no p2."""
    change = Change("t", None, touched=[("project_added", ["project:p2"])])
    assert read_back.check(_context(["p1"]), change) == ["project:p2 doesn't read back"]


def test_a_removed_record_and_kinds_it_cant_read_are_skipped():
    """A removal's ref isn't expected to resolve; a kind with no store here, or one not readable by id, is skipped."""
    change = Change("t", None, touched=[("project_added", ["project:p3"]), ("project_removed", ["project:p3"]),
                                        ("alarm_set", ["alarm:a1"]), ("asset_added", ["asset:x"])])
    assert read_back.check(_context([]), change) == []


def test_an_approved_action_says_whether_it_read_back(tmp_path, monkeypatch):
    """approve() keeps "ok", or what didn't read back in its result line; it stays done."""
    from core import actions

    calls = []

    def fake(context, change):
        """The read-back's verdict for this test."""
        calls.append(change)
        return ["project:p9 doesn't read back"] if len(calls) > 1 else []

    monkeypatch.setattr(read_back, "check", fake)
    fine = actions.Proposal("a", "x", {}, "x", None, result="Done.")
    actions._read_back(None, fine, Change("t", None))
    assert fine.read_back == "ok" and fine.result == "Done."
    off = actions.Proposal("b", "x", {}, "x", None, result="Done.")
    actions._read_back(None, off, Change("t", None))
    assert off.read_back == "project:p9 doesn't read back"
    assert off.result == "Done. But reading it back: project:p9 doesn't read back."
