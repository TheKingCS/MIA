"""
tests.test_change_history
===========================

The lasting history of MIA's changes (prompt 23's review, UI-3; core/change_history.py): every change is kept with
its files' bytes before (sealed, compressed, once per content), so it outlives a restart; "undo what you did this
afternoon" puts changes back newest first, each whole or not at all, and only where nothing changed the files since;
a change already put back by "undo that" is never put back twice; old changes are forgotten after 30 days; the tool
lists exactly what it would undo and waits for a yes; the Recent Changes page offers the same.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import change_history as ch
from core.atomic_write import atomic_write_text
from core.undo_log import UndoLog, recording, undo_last


@pytest.fixture
def home(tmp_path, monkeypatch):
    """MIA's data folder in a temp dir, a context with an undo log, and a store file holding "v0"."""
    monkeypatch.setattr(ch, "DATA_DIR", tmp_path)
    ch._pruned.clear()
    store = tmp_path / "greenhouse_log.json"
    store.write_text("v0", encoding="utf-8")
    return SimpleNamespace(dir=tmp_path, store=store, context=SimpleNamespace(undo=UndoLog()))


def change(home, label, text, path=None, summary=""):
    """One change by MIA: the store (or `path`) rewritten to `text` through atomic_write_text, kept as she keeps one."""
    with recording(label, None) as c:
        atomic_write_text(path or home.store, text)
    c.by, c.summary = "mia", summary
    home.context.undo.add(c)
    return c


def today():
    """Today's window."""
    return ch.window("today")


def test_a_change_is_kept_with_its_before_bytes_sealed_and_survives_a_restart(home):
    first = change(home, "log_reading", "v1", summary="log reading: greenhouse, 74")
    [entry] = ch.entries(None)
    assert entry.change_id == first.change_id and entry.what == "log reading: greenhouse, 74"
    assert entry.files[0]["path"] == "greenhouse_log.json" and entry.files[0]["before"] != entry.files[0]["after"]
    blob = next((home.dir / "history" / "blobs").glob("*.blob")).read_text(encoding="utf-8")
    assert "v0" not in blob and blob.startswith("MIA")  # sealed (the suite seals with its test key)
    home.context.undo = UndoLog()  # MIA restarted: "undo that" has nothing, the history still has it
    found = ch.find(None, *today(), "greenhouse")
    assert [e.change_id for e in found] == [first.change_id]
    done = ch.undo(home.context, None, found)
    assert len(done["undone"]) == 1 and home.store.read_text(encoding="utf-8") == "v0"
    assert ch.find(None, *today()) == []  # marked undone: not offered again


def test_changes_go_back_newest_first_and_each_whole_or_not_at_all(home):
    other = home.dir / "budget.json"
    other.write_text("b0", encoding="utf-8")
    change(home, "log_reading", "v1")
    with recording("move_money", None) as both:  # one action, two files
        atomic_write_text(home.store, "v2")
        atomic_write_text(other, "b1")
    home.context.undo.add(both)
    done = ch.undo(home.context, None, ch.find(None, *today()))
    assert len(done["undone"]) == 2 and home.store.read_text(encoding="utf-8") == "v0"
    assert other.read_text(encoding="utf-8") == "b0"


def test_a_change_whose_file_changed_again_since_is_left_and_said(home):
    other = home.dir / "budget.json"
    other.write_text("b0", encoding="utf-8")
    with recording("move_money", None) as both:
        atomic_write_text(home.store, "v1")
        atomic_write_text(other, "b1")
    home.context.undo.add(both)
    other.write_text("b2 typed by him", encoding="utf-8")  # changed again, not by this change
    done = ch.undo(home.context, None, ch.find(None, *today()))
    assert not done["undone"] and "changed again" in done["left"][0][1]
    assert home.store.read_text(encoding="utf-8") == "v1"  # whole or nothing: the other file wasn't touched either


def test_only_the_subject_named_is_undone_and_a_later_change_protects_the_file(home):
    notes = home.dir / "notes.json"
    notes.write_text("n0", encoding="utf-8")
    change(home, "add_note", "n1", path=notes, summary="add note: seed order")
    change(home, "log_reading", "v1", summary="log reading: greenhouse")
    picked = ch.find(None, *today(), "greenhouse")
    assert [e.label for e in picked] == ["log_reading"]
    ch.undo(home.context, None, picked)
    assert notes.read_text(encoding="utf-8") == "n1" and home.store.read_text(encoding="utf-8") == "v0"


def test_undo_that_and_the_history_never_put_the_same_change_back_twice(home):
    change(home, "log_reading", "v1")
    change(home, "log_reading", "v2")
    undo_last(home.context, None)  # "undo that": v2 goes back to v1
    assert home.store.read_text(encoding="utf-8") == "v1"
    [left] = ch.find(None, *today())
    ch.undo(home.context, None, [left])
    assert home.store.read_text(encoding="utf-8") == "v0" and undo_last(home.context, None) is None


def test_append_only_logs_are_never_kept_or_undone(home):
    log = home.dir / "life_events.jsonl"
    with recording("note", None) as c:
        atomic_write_text(log, "{}\n")
    home.context.undo.add(c)
    assert ch.entries(None) == []


def test_times_in_words():
    now = datetime(2026, 11, 16, 15, 30)
    assert ch.window("this afternoon", now) == (datetime(2026, 11, 16, 12), datetime(2026, 11, 16, 15, 30))
    assert ch.window("in the last two hours", now)[0] == datetime(2026, 11, 16, 13, 30)
    assert ch.window("the last 30 minutes", now)[0] == datetime(2026, 11, 16, 15, 0)
    assert ch.window("yesterday", now) == (datetime(2026, 11, 15), datetime(2026, 11, 16))
    assert ch.window("whenever", now)[0] == datetime(2026, 11, 16)


def test_changes_older_than_thirty_days_and_their_bytes_are_forgotten(home):
    change(home, "log_reading", "v1")
    later = datetime.now() + timedelta(days=ch.KEEP_DAYS + 1)
    assert ch.prune(home.dir / "history", now=later) == 1
    assert ch.entries(None) == [] and not list((home.dir / "history" / "blobs").glob("*.blob"))


def test_the_tool_lists_first_and_undoes_only_after_the_yes_and_the_page_offers_it(home, monkeypatch):
    from core.actions import ActionCenter
    from core.assistant_undo_actions import _action_undo_by_time
    from core.web_changes import changes_page

    home.context.actions = ActionCenter()
    change(home, "log_reading", "v1", summary="log reading: greenhouse, 74")
    said = _action_undo_by_time(home.context, {"when": "today", "what": "greenhouse"})
    assert "Undo 1 change from today" in said and "greenhouse, 74" in said and "Shall I?" in said
    assert home.store.read_text(encoding="utf-8") == "v1"  # nothing yet
    said = _action_undo_by_time(home.context, {"when": "today", "what": "greenhouse", "confirm": True})
    assert said.startswith("Put back 1") and home.store.read_text(encoding="utf-8") == "v0"
    assert "didn't change anything to greenhouse" in _action_undo_by_time(home.context, {"when": "today",
                                                                                          "what": "greenhouse"})
    page = changes_page(home.context)
    assert {c["id"] for c in page["when_choices"]} >= {"this afternoon", "today", "last hour"}
    js = (Path(__file__).resolve().parent.parent / "web" / "changes.js").read_text(encoding="utf-8")
    assert 'kind: "history.undo"' in js
