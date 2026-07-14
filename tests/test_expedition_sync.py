"""
tests.test_expedition_sync
=============================

Unit tests for core.expedition_sync. Isolates _DATA_DIR/_TRIP_PHOTOS_DIR
into a tmp_path scratch area (same monkeypatch pattern as
test_backup_manager.py's isolated_paths) so these tests never touch the
real data/ or trip_photos/ directories.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

import core.expedition_sync as expedition_sync_module
from core.expedition_sync import export_expedition_data, find_export_bundles, import_expedition_data


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    trip_photos_dir = tmp_path / "trip_photos"

    monkeypatch.setattr(expedition_sync_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_sync_module, "_TRIP_PHOTOS_DIR", trip_photos_dir)
    return data_dir, trip_photos_dir


def _write_json(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")


def test_export_bundles_expedition_files_and_photos(isolated_paths, tmp_path):
    data_dir, trip_photos_dir = isolated_paths
    _write_json(data_dir / "expeditions.json", [{"expedition_id": "exp1", "name": "Weekend"}])
    _write_json(data_dir / "trips.json", [{"trip_id": "t1", "expedition_id": "exp1", "name": "Hike"}])
    (trip_photos_dir / "t1").mkdir(parents=True)
    (trip_photos_dir / "t1" / "camp.jpg").write_bytes(b"fake photo bytes")

    destination = tmp_path / "export.zip"
    result = export_expedition_data(destination)

    assert result.passed is True
    assert destination.exists()
    with zipfile.ZipFile(destination) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "data/expeditions.json" in names
        assert "data/trips.json" in names
        assert "trip_photos/t1/camp.jpg" in names
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["bundle"] == "expedition_data"


def test_export_omits_missing_files_without_error(isolated_paths, tmp_path):
    # No data/trip_photos exist at all yet — a fresh install with no Expeditions.
    destination = tmp_path / "export.zip"
    result = export_expedition_data(destination)
    assert result.passed is True
    with zipfile.ZipFile(destination) as zf:
        assert zf.namelist() == ["manifest.json"]


def test_import_adds_new_records_and_merges_with_existing(isolated_paths, tmp_path):
    data_dir, trip_photos_dir = isolated_paths
    # "Home" already has one expedition of its own.
    _write_json(data_dir / "expeditions.json", [{"expedition_id": "home-exp", "name": "Already Here"}])

    # Build a bundle (from a separate "Pi" data dir) with a different expedition.
    pi_data_dir = tmp_path / "pi_data"
    _write_json(pi_data_dir / "expeditions.json", [{"expedition_id": "pi-exp", "name": "Field Trip"}])
    import core.expedition_sync as sync_module
    original_data_dir = sync_module._DATA_DIR
    sync_module._DATA_DIR = pi_data_dir
    try:
        bundle_path = tmp_path / "export.zip"
        export_expedition_data(bundle_path)
    finally:
        sync_module._DATA_DIR = original_data_dir

    result = import_expedition_data(bundle_path)
    assert result.passed is True
    assert result.counts["expeditions.json"] == 1

    merged = json.loads((data_dir / "expeditions.json").read_text(encoding="utf-8"))
    ids = {record["expedition_id"] for record in merged}
    assert ids == {"home-exp", "pi-exp"}


def test_import_skips_records_with_ids_already_present(isolated_paths, tmp_path):
    data_dir, _ = isolated_paths
    _write_json(data_dir / "trips.json", [{"trip_id": "t1", "expedition_id": "exp1", "name": "Hike"}])

    bundle_path = tmp_path / "export.zip"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"app": "M.I.A.", "bundle": "expedition_data", "manifest_version": 1}))
        zf.writestr("data/trips.json", json.dumps([{"trip_id": "t1", "expedition_id": "exp1", "name": "Hike (duplicate)"}]))

    result = import_expedition_data(bundle_path)
    assert result.passed is True
    assert result.counts["trips.json"] == 0

    trips = json.loads((data_dir / "trips.json").read_text(encoding="utf-8"))
    assert len(trips) == 1
    assert trips[0]["name"] == "Hike"  # untouched, not overwritten by the duplicate


def test_import_copies_new_photos_and_skips_existing(isolated_paths, tmp_path):
    data_dir, trip_photos_dir = isolated_paths
    (trip_photos_dir / "t1").mkdir(parents=True)
    (trip_photos_dir / "t1" / "existing.jpg").write_bytes(b"original bytes")

    bundle_path = tmp_path / "export.zip"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"app": "M.I.A.", "bundle": "expedition_data", "manifest_version": 1}))
        zf.writestr("trip_photos/t1/existing.jpg", "should not overwrite")
        zf.writestr("trip_photos/t1/new_photo.jpg", "new photo bytes")

    result = import_expedition_data(bundle_path)
    assert result.passed is True
    assert result.counts["trip_photos"] == 1  # only new_photo.jpg counted

    assert (trip_photos_dir / "t1" / "existing.jpg").read_bytes() == b"original bytes"  # untouched
    assert (trip_photos_dir / "t1" / "new_photo.jpg").read_bytes() == b"new photo bytes"


def test_reimporting_the_same_bundle_does_not_duplicate(isolated_paths, tmp_path):
    data_dir, trip_photos_dir = isolated_paths
    bundle_path = tmp_path / "export.zip"
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"app": "M.I.A.", "bundle": "expedition_data", "manifest_version": 1}))
        zf.writestr("data/expeditions.json", json.dumps([{"expedition_id": "exp1", "name": "Weekend"}]))
        zf.writestr("trip_photos/t1/camp.jpg", "photo bytes")

    first = import_expedition_data(bundle_path)
    second = import_expedition_data(bundle_path)

    assert first.counts["expeditions.json"] == 1
    assert second.counts["expeditions.json"] == 0
    assert first.counts["trip_photos"] == 1
    assert second.counts["trip_photos"] == 0

    expeditions = json.loads((data_dir / "expeditions.json").read_text(encoding="utf-8"))
    assert len(expeditions) == 1


def test_import_rejects_non_zip_file(isolated_paths, tmp_path):
    bad_path = tmp_path / "not_a_zip.zip"
    bad_path.write_text("this is not a zip file")

    result = import_expedition_data(bad_path)
    assert result.passed is False
    assert "not a valid archive" in result.errors[0].lower()


def test_import_rejects_zip_missing_manifest(isolated_paths, tmp_path):
    bad_path = tmp_path / "no_manifest.zip"
    with zipfile.ZipFile(bad_path, "w") as zf:
        zf.writestr("data/expeditions.json", "[]")

    result = import_expedition_data(bad_path)
    assert result.passed is False
    assert "missing manifest" in result.errors[0].lower()


def test_import_rejects_path_traversal(isolated_paths, tmp_path):
    malicious_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(malicious_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"app": "M.I.A.", "bundle": "expedition_data", "manifest_version": 1}))
        zf.writestr("../../evil.txt", "gotcha")

    result = import_expedition_data(malicious_path)
    assert result.passed is False
    assert "unsafe path" in result.errors[0].lower()


# ----------------------------------------------------------------------
# find_export_bundles — docs/ROADMAP.md milestone v0.19, Home Dock
# auto-launch Dashboard's Core-detection mechanism
# ----------------------------------------------------------------------

def test_find_export_bundles_empty_when_none_present(tmp_path):
    assert find_export_bundles(tmp_path) == []


def test_find_export_bundles_finds_matching_files(tmp_path):
    (tmp_path / "mia_expedition_export_20260814_120000.zip").write_bytes(b"fake")
    (tmp_path / "not_a_bundle.zip").write_bytes(b"fake")
    (tmp_path / "random.txt").write_text("hello")

    found = find_export_bundles(tmp_path)
    assert [p.name for p in found] == ["mia_expedition_export_20260814_120000.zip"]


def test_find_export_bundles_sorted_newest_first(tmp_path):
    (tmp_path / "mia_expedition_export_20260101_000000.zip").write_bytes(b"fake")
    (tmp_path / "mia_expedition_export_20260901_000000.zip").write_bytes(b"fake")

    found = find_export_bundles(tmp_path)
    assert [p.name for p in found] == [
        "mia_expedition_export_20260901_000000.zip",
        "mia_expedition_export_20260101_000000.zip",
    ]


def test_find_export_bundles_nonexistent_mountpoint_returns_empty(tmp_path):
    assert find_export_bundles(tmp_path / "does-not-exist") == []
