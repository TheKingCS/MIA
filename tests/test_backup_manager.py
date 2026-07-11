"""
tests.test_backup_manager
============================

Unit tests for core.backup_manager. Isolates _CONFIG_FILE/_DATA_DIR
into a tmp_path scratch area (same monkeypatch pattern as
test_config_manager.py) so these tests never touch the real
config/config.json or data/ directory.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

import core.backup_manager as backup_manager_module
from core.backup_manager import create_backup, is_backup_encrypted, restore_backup


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    config_file = tmp_path / "config" / "config.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(json.dumps({"user": {"name": "Alex"}}))

    data_dir = tmp_path / "data"
    (data_dir / "profiles" / "abc123").mkdir(parents=True)
    (data_dir / "notifications.json").write_text("[]")
    (data_dir / "profiles" / "abc123" / "note.txt").write_text("hello from a profile")

    monkeypatch.setattr(backup_manager_module, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(backup_manager_module, "_DATA_DIR", data_dir)
    return config_file, data_dir


def test_create_plain_backup_then_restore_roundtrip(isolated_paths, tmp_path):
    config_file, data_dir = isolated_paths
    backup_path = tmp_path / "backup.zip"

    result = create_backup(backup_path)
    assert result.passed is True
    assert backup_path.exists()

    # Simulate the live state changing after the backup was taken.
    config_file.write_text(json.dumps({"user": {"name": "Someone Else"}}))
    (data_dir / "notifications.json").write_text('["changed"]')

    restore_result = restore_backup(backup_path)
    assert restore_result.passed is True
    assert json.loads(config_file.read_text()) == {"user": {"name": "Alex"}}
    assert (data_dir / "profiles" / "abc123" / "note.txt").read_text() == "hello from a profile"
    assert (data_dir / "notifications.json").read_text() == "[]"


def test_encrypted_backup_requires_correct_passphrase(isolated_paths, tmp_path):
    backup_path = tmp_path / "backup.miabackup"

    result = create_backup(backup_path, passphrase="hunter2")
    assert result.passed is True

    no_passphrase = restore_backup(backup_path)
    assert no_passphrase.passed is False
    assert "passphrase is required" in no_passphrase.errors[0]

    wrong_passphrase = restore_backup(backup_path, passphrase="wrong")
    assert wrong_passphrase.passed is False

    correct = restore_backup(backup_path, passphrase="hunter2")
    assert correct.passed is True


def test_is_backup_encrypted_detects_correctly(isolated_paths, tmp_path):
    plain_path = tmp_path / "plain.zip"
    encrypted_path = tmp_path / "encrypted.miabackup"

    create_backup(plain_path)
    create_backup(encrypted_path, passphrase="secret")

    assert is_backup_encrypted(plain_path) is False
    assert is_backup_encrypted(encrypted_path) is True


def test_is_backup_encrypted_false_for_unrelated_file(tmp_path):
    junk = tmp_path / "not_a_backup.txt"
    junk.write_text("hello")
    assert is_backup_encrypted(junk) is False


def test_restore_rejects_unrelated_file_without_touching_live_state(isolated_paths, tmp_path):
    config_file, data_dir = isolated_paths
    original_config = config_file.read_text()

    junk = tmp_path / "not_a_backup.txt"
    junk.write_text("just some random file, not a backup")

    result = restore_backup(junk)

    assert result.passed is False
    assert "not a valid archive" in result.errors[0]
    assert config_file.read_text() == original_config


def test_restore_rejects_corrupted_plain_payload_without_touching_live_state(isolated_paths, tmp_path):
    config_file, data_dir = isolated_paths
    original_config = config_file.read_text()

    fake_backup = tmp_path / "corrupt.zip"
    fake_backup.write_bytes(b"not a real zip at all")

    result = restore_backup(fake_backup)

    assert result.passed is False
    assert config_file.read_text() == original_config


def test_restore_rejects_corrupted_encrypted_payload_without_touching_live_state(isolated_paths, tmp_path):
    config_file, data_dir = isolated_paths
    original_config = config_file.read_text()

    fake_backup = tmp_path / "corrupt.miabackup"
    fake_backup.write_bytes(backup_manager_module._MAGIC + b"not a real encrypted blob")

    result = restore_backup(fake_backup, passphrase="whatever")

    assert result.passed is False
    assert config_file.read_text() == original_config


def test_plain_backup_is_a_standard_zip_with_no_prefix(isolated_paths, tmp_path):
    """
    Regression test: an earlier version prepended the same magic
    header to plain backups too, which broke standard zip tools
    (`unzip` reports "extra bytes at beginning" and exits non-zero).
    Plain backups must open as a zip with zero bytes of preamble.
    """
    backup_path = tmp_path / "plain.zip"
    create_backup(backup_path)

    raw = backup_path.read_bytes()
    assert raw.startswith(b"PK")  # the actual zip local-file-header signature, at byte 0


def test_safe_extract_rejects_path_traversal(tmp_path):
    malicious_zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(malicious_zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"app": "M.I.A.", "manifest_version": 1}))
        zf.writestr("../../evil.txt", "gotcha")

    target_dir = tmp_path / "staging"
    target_dir.mkdir()

    with zipfile.ZipFile(malicious_zip_path) as zf:
        with pytest.raises(backup_manager_module.BackupError):
            backup_manager_module._safe_extract_all(zf, target_dir)
