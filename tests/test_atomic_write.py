"""
tests.test_atomic_write
===========================

Unit tests for core.atomic_write.atomic_write_text — the crash-safety
guarantee is the whole point of this module, so these tests exercise
the failure path directly (a real exception mid-write), not just the
happy path.

Also the two guards added 2026-11-10: a large shrink keeps the old file
as its `.prev`, and the replace is retried while a reader holds the file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.atomic_write import atomic_write_text


def test_atomic_write_creates_a_new_file_with_the_given_content(tmp_path):
    target = tmp_path / "data.json"
    atomic_write_text(target, '{"a": 1}')
    assert target.read_text(encoding="utf-8") == '{"a": 1}'


def test_atomic_write_overwrites_an_existing_file(tmp_path):
    target = tmp_path / "data.json"
    target.write_text('{"old": true}', encoding="utf-8")
    atomic_write_text(target, '{"new": true}')
    assert target.read_text(encoding="utf-8") == '{"new": true}'


def test_atomic_write_leaves_no_temp_file_behind_on_success(tmp_path):
    atomic_write_text(tmp_path / "data.json", "content")
    remaining = list(tmp_path.iterdir())
    assert remaining == [tmp_path / "data.json"]


def test_atomic_write_respects_a_non_default_encoding(tmp_path):
    target = tmp_path / "data.json"
    atomic_write_text(target, "café", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "café"


def test_atomic_write_leaves_the_original_file_untouched_if_the_write_fails(tmp_path, monkeypatch):
    """The core guarantee: a real exception during the write must
    never corrupt or truncate the file that was already there."""
    target = tmp_path / "data.json"
    target.write_text('{"safe": true}', encoding="utf-8")

    def _boom(*args, **kwargs):
        raise OSError("simulated disk-full mid-write")

    monkeypatch.setattr("os.fsync", _boom)

    with pytest.raises(OSError):
        atomic_write_text(target, '{"never": "written"}')

    assert target.read_text(encoding="utf-8") == '{"safe": true}'


def test_atomic_write_cleans_up_its_temp_file_if_the_write_fails(tmp_path, monkeypatch):
    def _boom(*args, **kwargs):
        raise OSError("simulated disk-full mid-write")

    monkeypatch.setattr("os.fsync", _boom)

    with pytest.raises(OSError):
        atomic_write_text(tmp_path / "data.json", "content")

    assert list(tmp_path.iterdir()) == []


def test_atomic_write_creates_no_file_at_all_if_the_write_fails_and_none_existed_before(tmp_path, monkeypatch):
    target = tmp_path / "data.json"

    def _boom(*args, **kwargs):
        raise OSError("simulated failure")

    monkeypatch.setattr("os.fsync", _boom)

    with pytest.raises(OSError):
        atomic_write_text(target, "content")

    assert not target.exists()


def test_atomic_write_accepts_a_string_path_not_just_a_path_object(tmp_path):
    target = str(tmp_path / "data.json")
    atomic_write_text(target, "content")
    assert Path(target).read_text(encoding="utf-8") == "content"


def test_a_write_that_shrinks_a_large_file_keeps_the_old_contents_as_prev(tmp_path):
    """Guard (a): a store that started empty after a failed read can't silently wipe its file."""
    from core.atomic_write import prev_path

    target = tmp_path / "missions.json"
    original = "[" + ",".join('{"id": %d}' % i for i in range(100)) + "]"
    target.write_text(original, encoding="utf-8")
    atomic_write_text(target, '[{"id": 1}]')
    assert target.read_text(encoding="utf-8") == '[{"id": 1}]'
    assert prev_path(target).read_text(encoding="utf-8") == original


def test_a_small_change_or_a_small_file_keeps_no_prev_copy(tmp_path):
    from core.atomic_write import prev_path

    small = tmp_path / "small.json"
    small.write_text('{"a": 1}', encoding="utf-8")
    atomic_write_text(small, "{}")
    big = tmp_path / "big.json"
    big.write_text("x" * 2000, encoding="utf-8")
    atomic_write_text(big, "y" * 1500)
    assert not prev_path(small).exists() and not prev_path(big).exists()


def test_an_old_prev_copy_is_removed_by_the_next_write(tmp_path):
    import os
    import time

    from core.atomic_write import PREV_KEEP_DAYS, prev_path

    target = tmp_path / "notes.json"
    target.write_text("{}", encoding="utf-8")
    prev = prev_path(target)
    prev.write_text("old", encoding="utf-8")
    stale = time.time() - (PREV_KEEP_DAYS + 1) * 86400
    os.utime(prev, (stale, stale))
    atomic_write_text(target, '{"a": 1}')
    assert not prev.exists()


def test_the_replace_is_retried_while_another_reader_holds_the_file(tmp_path, monkeypatch):
    """Guard (b): Windows refuses the replace while the file is open elsewhere; a later attempt succeeds."""
    import os

    import core.atomic_write as aw

    monkeypatch.setattr(aw.time, "sleep", lambda s: None)
    real_replace = os.replace
    calls = []

    def _busy_twice(src, dst):
        calls.append(dst)
        if len(calls) < 3:
            raise PermissionError("in use")
        real_replace(src, dst)

    monkeypatch.setattr(aw.os, "replace", _busy_twice)
    target = tmp_path / "data.json"
    atomic_write_text(target, '{"saved": true}')
    assert target.read_text(encoding="utf-8") == '{"saved": true}' and len(calls) == 3
    assert list(tmp_path.iterdir()) == [target]


def test_a_replace_that_stays_refused_raises_and_leaves_no_temp_file(tmp_path, monkeypatch):
    import core.atomic_write as aw

    monkeypatch.setattr(aw.time, "sleep", lambda s: None)

    def _always_busy(src, dst):
        raise PermissionError("in use")

    monkeypatch.setattr(aw.os, "replace", _always_busy)
    target = tmp_path / "data.json"
    target.write_text('{"safe": true}', encoding="utf-8")
    with pytest.raises(PermissionError):
        atomic_write_text(target, '{"never": true}')
    assert target.read_text(encoding="utf-8") == '{"safe": true}'
    assert list(tmp_path.iterdir()) == [target]
