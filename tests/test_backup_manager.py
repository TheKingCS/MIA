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
            backup_manager_module.safe_extract_zip(zf, target_dir)


# ------------------------------------------------------------------
# External content directories (2026-09-14) — trip photos, trail
# maps, and lite captures all live outside data/, so they need their
# own explicit coverage, opt-in via the `config` parameter.
# ------------------------------------------------------------------

class _FakeConfig:
    """Fakes just what backup_manager.py actually uses — ConfigManager.get()."""

    def __init__(self, values: dict) -> None:
        self._values = values

    def get(self, key: str, default=None):
        return self._values.get(key, default)


@pytest.fixture
def external_content_paths(tmp_path, monkeypatch):
    dirs = {
        "trip_photos": tmp_path / "trip_photos",
        "trail_maps": tmp_path / "trail_maps",
        "lite_captures": tmp_path / "lite_captures",
        "homestead_snapshots": tmp_path / "homestead_snapshots",
        "financial_snapshots": tmp_path / "financial_snapshots",
        "maintenance_documents": tmp_path / "maintenance_documents",
    }
    for d in dirs.values():
        d.mkdir()
    monkeypatch.setattr(backup_manager_module, "_DEFAULT_TRIP_PHOTOS_DIR", dirs["trip_photos"])
    monkeypatch.setattr(backup_manager_module, "_DEFAULT_TRAIL_MAPS_DIR", dirs["trail_maps"])
    monkeypatch.setattr(backup_manager_module, "_DEFAULT_LITE_CAPTURES_DIR", dirs["lite_captures"])
    monkeypatch.setattr(backup_manager_module, "_DEFAULT_HOMESTEAD_SNAPSHOTS_DIR", dirs["homestead_snapshots"])
    monkeypatch.setattr(backup_manager_module, "_DEFAULT_FINANCIAL_SNAPSHOTS_DIR", dirs["financial_snapshots"])
    monkeypatch.setattr(backup_manager_module, "_DEFAULT_MAINTENANCE_DOCUMENTS_DIR", dirs["maintenance_documents"])
    monkeypatch.setattr(
        backup_manager_module,
        "_EXTERNAL_CONTENT_DIRS",
        (
            ("trips.photo_root_path", dirs["trip_photos"], "trip_photos"),
            ("maps.trail_map_root_path", dirs["trail_maps"], "trail_maps"),
            ("lite_capture.import_folder", dirs["lite_captures"], "lite_captures"),
            ("homestead.snapshot_import_folder", dirs["homestead_snapshots"], "homestead_snapshots"),
            ("finance.snapshot_import_folder", dirs["financial_snapshots"], "financial_snapshots"),
            (None, dirs["maintenance_documents"], "maintenance_documents"),
        ),
    )
    return dirs["trip_photos"], dirs["trail_maps"], dirs["lite_captures"]


@pytest.fixture
def all_external_content_dirs(external_content_paths, tmp_path):
    """Same isolated setup as external_content_paths, but returns every
    directory (including the three added in the second stabilization
    pass) rather than just the original three."""
    return {
        "trip_photos": tmp_path / "trip_photos",
        "trail_maps": tmp_path / "trail_maps",
        "lite_captures": tmp_path / "lite_captures",
        "homestead_snapshots": tmp_path / "homestead_snapshots",
        "financial_snapshots": tmp_path / "financial_snapshots",
        "maintenance_documents": tmp_path / "maintenance_documents",
    }


def test_create_backup_without_config_excludes_external_content(isolated_paths, external_content_paths, tmp_path):
    trip_photos, _, _ = external_content_paths
    (trip_photos / "hike.jpg").write_bytes(b"fake photo bytes")
    backup_path = tmp_path / "backup.zip"

    create_backup(backup_path)  # no config passed

    with zipfile.ZipFile(backup_path) as zf:
        assert not any(name.startswith("content/") for name in zf.namelist())


def test_create_backup_with_config_includes_external_content(isolated_paths, external_content_paths, tmp_path):
    trip_photos, trail_maps, lite_captures = external_content_paths
    (trip_photos / "hike.jpg").write_bytes(b"fake photo bytes")
    (lite_captures / "note.txt").write_text("a pending voice note transcript")
    backup_path = tmp_path / "backup.zip"
    config = _FakeConfig({})  # empty -> every key falls back to its default dir

    create_backup(backup_path, config=config)

    with zipfile.ZipFile(backup_path) as zf:
        names = zf.namelist()
        assert "content/trip_photos/hike.jpg" in names
        assert "content/lite_captures/note.txt" in names
        assert not any(name.startswith("content/trail_maps/") for name in names)  # trail_maps was empty


def test_create_backup_uses_configured_path_over_default(isolated_paths, external_content_paths, tmp_path):
    custom_photos_dir = tmp_path / "custom_photos"
    custom_photos_dir.mkdir()
    (custom_photos_dir / "sunset.jpg").write_bytes(b"fake photo bytes")
    backup_path = tmp_path / "backup.zip"
    config = _FakeConfig({"trips.photo_root_path": str(custom_photos_dir)})

    create_backup(backup_path, config=config)

    with zipfile.ZipFile(backup_path) as zf:
        assert "content/trip_photos/sunset.jpg" in zf.namelist()


def test_restore_with_config_restores_external_content(isolated_paths, external_content_paths, tmp_path):
    trip_photos, _, lite_captures = external_content_paths
    (trip_photos / "hike.jpg").write_bytes(b"original photo")
    (lite_captures / "old_note.txt").write_text("present at backup time")
    backup_path = tmp_path / "backup.zip"
    config = _FakeConfig({})

    create_backup(backup_path, config=config)

    # Simulate real changes after the backup: photo replaced, the old
    # note deleted, and a new pending capture arrives that was never
    # backed up.
    (trip_photos / "hike.jpg").write_bytes(b"OVERWRITTEN")
    (lite_captures / "old_note.txt").unlink()
    (lite_captures / "new_note.txt").write_text("arrived after the backup")

    result = restore_backup(backup_path, config=config)

    assert result.passed is True
    assert (trip_photos / "hike.jpg").read_bytes() == b"original photo"
    assert (lite_captures / "old_note.txt").read_text() == "present at backup time"
    assert not (lite_captures / "new_note.txt").exists()  # real destructive replace, not a merge


def test_restore_without_config_leaves_external_content_untouched(isolated_paths, external_content_paths, tmp_path):
    trip_photos, _, _ = external_content_paths
    (trip_photos / "hike.jpg").write_bytes(b"original photo")
    backup_path = tmp_path / "backup.zip"

    create_backup(backup_path, config=_FakeConfig({}))
    (trip_photos / "hike.jpg").write_bytes(b"changed after backup")

    result = restore_backup(backup_path)  # no config -> external content opted out

    assert result.passed is True
    assert (trip_photos / "hike.jpg").read_bytes() == b"changed after backup"  # untouched by this restore


def test_restore_backup_predating_external_content_leaves_dirs_untouched(isolated_paths, external_content_paths, tmp_path):
    """A backup made before this feature existed has no "content/"
    members at all — restoring it with a real config must not error
    and must not wipe whatever's currently in those directories."""
    trip_photos, _, _ = external_content_paths
    backup_path = tmp_path / "backup.zip"
    create_backup(backup_path)  # old-style backup, no config -> no content/ members

    (trip_photos / "still_here.jpg").write_bytes(b"never touched")

    result = restore_backup(backup_path, config=_FakeConfig({}))

    assert result.passed is True
    assert (trip_photos / "still_here.jpg").read_bytes() == b"never touched"


# ------------------------------------------------------------------
# The three external content directories added in the second
# stabilization pass (2026-09-14) — homestead/financial snapshot
# imports and maintenance asset documents. Same coverage shape as the
# original three above; maintenance_documents is the one entry with no
# configurable override (config key is None), so it gets its own
# explicit test for that branch.
# ------------------------------------------------------------------

def test_create_backup_includes_homestead_and_financial_snapshots(
    isolated_paths, all_external_content_dirs, tmp_path
):
    dirs = all_external_content_dirs
    (dirs["homestead_snapshots"] / "reading.json").write_text("{}")
    (dirs["financial_snapshots"] / "statement.json").write_text("{}")
    backup_path = tmp_path / "backup.zip"

    create_backup(backup_path, config=_FakeConfig({}))

    with zipfile.ZipFile(backup_path) as zf:
        names = zf.namelist()
        assert "content/homestead_snapshots/reading.json" in names
        assert "content/financial_snapshots/statement.json" in names


def test_create_backup_includes_maintenance_documents_with_no_config_override(
    isolated_paths, all_external_content_dirs, tmp_path
):
    """maintenance_documents has no configurable path at all (config
    key is None in _EXTERNAL_CONTENT_DIRS) — must still resolve to its
    default and be included, not silently skipped."""
    dirs = all_external_content_dirs
    (dirs["maintenance_documents"] / "receipt.pdf").write_bytes(b"fake pdf bytes")
    backup_path = tmp_path / "backup.zip"

    # An empty config with no relevant keys at all — proves the None
    # key branch doesn't depend on config.get() being called for it.
    create_backup(backup_path, config=_FakeConfig({}))

    with zipfile.ZipFile(backup_path) as zf:
        assert "content/maintenance_documents/receipt.pdf" in zf.namelist()


def test_restore_restores_all_six_external_content_directories(
    isolated_paths, all_external_content_dirs, tmp_path
):
    dirs = all_external_content_dirs
    for name, directory in dirs.items():
        (directory / "original.txt").write_text(f"original {name}")
    backup_path = tmp_path / "backup.zip"
    config = _FakeConfig({})

    create_backup(backup_path, config=config)

    for directory in dirs.values():
        (directory / "original.txt").write_text("OVERWRITTEN")

    result = restore_backup(backup_path, config=config)

    assert result.passed is True
    for name, directory in dirs.items():
        assert (directory / "original.txt").read_text() == f"original {name}"
