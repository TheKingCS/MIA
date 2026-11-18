"""
tests.test_observation_review
===============================

The defects Fable's review of 2026-11-18 found in what MIA notes and recalls, each kept fixed by a test here: private
windows that used to be noted, a browser's titles kept only on his say-so, an erase that leaves no copy, the seven
days holding while noting is off, and a recall index that keeps nothing of a removed record and never embeds under its
lock.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import activity_watch as aw
from core import recall_index as ri
from core import undo_log
from core.atomic_write import prev_path
from tests.test_recall_index import _context

T0 = datetime(2026, 11, 18, 9, 0, 0)


@pytest.mark.parametrize("app,title", [
    ("Proton Pass", "Vaults"), ("NordPass", "Home"), ("Enpass", "All Items"), ("RoboForm", "Logins"),
    ("chrome", "Bitwarden Web Vault - Google Chrome"), ("chrome", "Login - MyBank"), ("msedge", "Signin"),
    ("firefox", "Accounts - First National Bank"), ("chrome", "PayPal: Summary"), ("msedge", "MyChart - Test Results"),
    ("Code", "tax return 2025.xlsx"), ("consent", "User Account Control"),
])
def test_password_managers_sign_ins_money_and_health_windows_are_never_noted(app, title):
    assert not aw.keep_this(app, title)


def test_his_own_words_to_skip_are_honoured():
    assert aw.keep_this("Code", "surprise party plan.md")
    assert not aw.keep_this("Code", "surprise party plan.md", own_words=("Surprise Party",))


def test_a_browsers_page_title_is_kept_only_when_he_turned_that_on(tmp_path):
    log = aw.ActivityLog(None, tmp_path)
    log.note("chrome", "lumber prices - Google Search", T0)
    log.note("Code", "coop.py", T0 + timedelta(minutes=5))
    log.note("chrome", "lumber prices - Google Search", T0 + timedelta(minutes=10), browser_titles=True)
    assert [s["title"] for s in log.spans()] == [aw.A_WEB_PAGE, "coop.py", "lumber prices - Google Search"]
    assert aw.is_browser("msedge") and not aw.is_browser("SearchHost") and not aw.is_browser("ArcGIS")


def test_erase_leaves_no_copy_behind_and_nothing_for_an_undo_to_bring_back(tmp_path):
    log = aw.ActivityLog(None, tmp_path)
    for i in range(40):  # enough that the writer would keep a safety copy of a file shrinking this much
        log.note("Code", f"secret project file number {i}.py", T0 + timedelta(minutes=10 * i))
    with undo_log.recording("action_activity.erase", "p1") as change:
        assert log.erase() == 40
    assert change.files == {}  # nothing of it entered the undo history
    assert not prev_path(tmp_path / "activity.json").exists()
    assert aw.ActivityLog(None, tmp_path).spans() == []
    left = b"".join(p.read_bytes() for p in tmp_path.iterdir() if p.is_file())
    assert b"secret project" not in left


def test_an_erase_says_it_cant_be_undone():
    from core.action_effects import effect_of

    assert effect_of("activity.erase") == ("records", "irreversible")


def test_what_was_noted_ages_out_even_while_noting_is_off(tmp_path, monkeypatch):
    log = aw.ActivityLog(None, tmp_path)
    log.note("Code", "old work", T0 - timedelta(days=8))
    log._spans.append({"app": "Code", "title": "kept", "start": T0.isoformat(), "end": T0.isoformat()})
    monkeypatch.setattr(aw, "noting", lambda context: False)
    assert aw.sample(SimpleNamespace(activity=log), now=T0) is False
    assert [s["title"] for s in log.spans()] == ["kept"]


# ------------------------------------------------------------------ the recall index


def test_the_embedding_never_runs_under_the_indexs_lock(tmp_path):
    ctx = _context(tmp_path, {"m1": "the chicken coop needs a roof"})
    seen = []

    def embed(texts, kind):
        """Records whether the lock was held while embedding."""
        seen.append(ctx.recall._lock.locked())
        return [[1.0, 0.0] for _ in texts]

    embed.model = "test-embed"
    assert ctx.recall.refresh(ctx, embed=embed)["added"] == 1 and seen == [False]


def test_a_record_removed_while_it_was_being_embedded_is_not_kept(tmp_path):
    ctx = _context(tmp_path, {"m1": "keep me", "m2": "delete me"})

    def embed(texts, kind):
        """Deletes a memory in the middle, as he might."""
        ctx.user_memories.items.pop("m2", None)
        return [[1.0, 0.0] for _ in texts]

    embed.model = "test-embed"
    ctx.recall.refresh(ctx, embed=embed)
    assert list(ctx.recall.items) == ["memory:m1"]


def test_something_removed_leaves_the_index_at_once_without_a_model(tmp_path):
    ctx = _context(tmp_path, {"m1": "one", "m2": "two"})
    ctx.recall.items = {"memory:m1": {"h": "x", "v": [1.0]}, "memory:m2": {"h": "y", "v": [1.0]}}
    del ctx.user_memories.items["m2"]
    assert ctx.recall.drop_gone(ctx) == 1 and list(ctx.recall.items) == ["memory:m1"]
    assert list(ri.RecallIndex(ctx, tmp_path).items) == ["memory:m1"]


def test_reloading_after_an_undo_keeps_the_same_lock(tmp_path):
    ctx = _context(tmp_path, {})
    lock = ctx.recall._lock
    ctx.recall._load()
    assert ctx.recall._lock is lock and isinstance(lock, type(threading.Lock()))
