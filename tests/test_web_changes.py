"""
tests.test_web_changes
========================

Recent Changes (core/web_changes.py): the person's changes newest first in
words, who made them, Undo only on the newest, and undoing it puts the file
back the way it was, the same as "undo that".
"""

from datetime import datetime
from types import SimpleNamespace

from core import web_changes
from core.undo_log import Change, UndoLog

NOW = datetime(2026, 11, 7, 21, 0)


def _context(undo):
    """A context with this undo log and one signed-in person."""
    profile = SimpleNamespace(profile_id="p1")
    return SimpleNamespace(undo=undo, profiles=SimpleNamespace(get_active_profile=lambda: profile,
                                                               active_profile=profile))


def test_changes_are_listed_newest_first_in_words_with_undo_on_the_newest(monkeypatch):
    """What, when (a clock today, the date before), who, and only the newest undoable."""
    monkeypatch.setattr("core.person_settings.person_id", lambda context: "p1")
    log = UndoLog()
    log.add(Change("bill.pay", "p1", at="2026-11-06T18:40:00", files={"a": b"x"}))
    log.add(Change("inbox_auto_file", "p1", at="2026-11-07T08:12:00", files={"b": b"y"}, by="mia"))
    page = web_changes.changes_page(_context(log), NOW)
    assert page["changes"] == [
        {"what": "Inbox auto file", "when": "8:12 AM", "by": "MIA", "latest": True},
        {"what": "Bill pay", "when": "Nov 6, 6:40 PM", "by": "You", "latest": False}]


def test_undo_puts_the_newest_change_back(tmp_path, monkeypatch):
    """The file is restored and the change leaves the list."""
    monkeypatch.setattr("core.person_settings.person_id", lambda context: "p1")
    monkeypatch.setattr("core.undo_log.reload_stores", lambda context, paths: 0)
    monkeypatch.setattr("core.main_thread.publish", lambda *a, **k: None)
    path = tmp_path / "bills.json"
    path.write_text("after", encoding="utf-8")
    log = UndoLog()
    log.add(Change("bill.pay", "p1", files={path: b"before"}))
    context = _context(log)
    assert web_changes.undo_latest(context) == "Undone: bill pay."
    assert path.read_text(encoding="utf-8") == "before" and log.recent("p1") == []
    assert web_changes.undo_latest(context) == "There's nothing to undo."
