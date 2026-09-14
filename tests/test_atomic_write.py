"""
tests.test_atomic_write
===========================

Unit tests for core.atomic_write.atomic_write_text — the crash-safety
guarantee is the whole point of this module, so these tests exercise
the failure path directly (a real exception mid-write), not just the
happy path.
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
