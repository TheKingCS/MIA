"""
core.expedition_sync
=======================

Export/import Expedition Mode data as a single bundle file — docs/
ROADMAP.md milestone 15, built for the "Pi 5 docked to a Home desktop"
workflow: `docs/HARDWARE.md`'s storage-split section already anticipated
this exact need ("the same drive can be pulled and mounted on a desktop
directly"). Reuses `core/backup_manager.py`'s proven zip-bundle pattern
(manifest.json + payload files, `zipfile`, staged-extraction safety via
`safe_extract_zip()`) but differs from it in two ways:

1. **Scoped to Expedition-relevant data only**, not a full app backup —
   `expeditions.json`/`trips.json`/`waypoints.json`/`journal_entries.json`/
   `inventory_items.json` (everything a Trip detail view references)
   plus the `trip_photos/` tree.
2. **Import merges by record id rather than overwriting.** Unlike
   `restore_backup()`'s destructive full-replace (appropriate for
   restoring your own single machine to a prior state), a Home desktop
   likely already has its own expeditions/trips/waypoints/journal
   entries from other sources — merging is the only sane semantic here.
   A record whose id already exists at the destination is skipped (ids
   are independently-generated UUIDs, so a real match means "already
   imported before," not a coincidence); new ones are appended. Photos:
   any `trip_photos/<trip_id>/<filename>` not already present is copied
   in.

Like `core/backup_manager.py`, this module only touches files on disk —
it has no `AppContext`/manager coupling, so an already-running
`TripManager`/`ExpeditionManager`/etc. won't see newly-imported records
until the app restarts (same "restart to see the change" UX already
used for `restore_backup()`, not a new pattern to learn).
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.backup_manager import BackupError, safe_extract_zip
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_TRIP_PHOTOS_DIR = _PROJECT_ROOT / "trip_photos"

_MANIFEST_VERSION = 1
_BUNDLE_KIND = "expedition_data"

#: (filename in data/, the record dataclass's id field) — every file an
#: Expedition/Trip's detail view can reference. Order doesn't matter for
#: correctness (each file merges independently), listed in the order a
#: Trip detail view surfaces them (route -> gear/inventory -> journal).
_DATA_FILES: tuple[tuple[str, str], ...] = (
    ("expeditions.json", "expedition_id"),
    ("trips.json", "trip_id"),
    ("waypoints.json", "waypoint_id"),
    ("inventory_items.json", "item_id"),
    ("journal_entries.json", "entry_id"),
)


@dataclass
class ExportResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    destination: Optional[Path] = None


@dataclass
class ImportResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    # filename (e.g. "trips.json") -> number of new records merged in;
    # "trip_photos" -> number of new photo files copied in.
    counts: dict[str, int] = field(default_factory=dict)


_EXPORT_FILENAME_GLOB = "mia_expedition_export_*.zip"


def find_export_bundles(mountpoint: Path) -> list[Path]:
    """
    docs/ROADMAP.md milestone v0.19 (Home Dock auto-launch Dashboard) —
    the detection mechanism for "is this docked device a Core with data
    to bring in," used by modules/field_kit/module.py's auto-import.
    Deliberately does NOT try to read a marker file describing the
    docked device's own config (e.g. its `system.device_profile`) —
    the real Pi 5 USB gadget-mode mount layout (docs/HARDWARE.md) is
    still unverified against real hardware, so any assumption about
    where such a file would even live on the exposed volume would be a
    guess. Instead this looks for the exact filenames
    `_on_export_expedition_data_clicked()` already writes at a device's
    mount root — files this app itself created, so detection works
    regardless of how gadget-mode ends up exposing storage. Sorted
    newest-first by filename (the export timestamp is baked into the
    name); import_expedition_data()'s merge-by-id is already idempotent,
    so re-processing an already-imported bundle on a later dock is safe
    and cheap rather than something that needs its own "already seen"
    tracking.
    """
    mountpoint = Path(mountpoint)
    if not mountpoint.is_dir():
        return []
    return sorted(mountpoint.glob(_EXPORT_FILENAME_GLOB), reverse=True)


def export_expedition_data(destination_path: Path) -> ExportResult:
    """Build an Expedition-data bundle at destination_path (e.g. a docked drive's mount path)."""
    destination_path = Path(destination_path)

    try:
        zip_bytes = _build_zip_bytes()
    except OSError as exc:
        return ExportResult(passed=False, errors=[f"Could not read expedition data to export: {exc}"])

    try:
        destination_path.write_bytes(zip_bytes)
    except OSError as exc:
        return ExportResult(passed=False, errors=[f"Could not write export file: {exc}"])

    log.info("Exported expedition data to %s", destination_path)
    return ExportResult(passed=True, destination=destination_path)


def _build_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "app": "M.I.A.",
            "bundle": _BUNDLE_KIND,
            "manifest_version": _MANIFEST_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        for filename, _id_field in _DATA_FILES:
            file_path = _DATA_DIR / filename
            if file_path.exists():
                zf.write(file_path, arcname=f"data/{filename}")

        if _TRIP_PHOTOS_DIR.exists():
            for file_path in _TRIP_PHOTOS_DIR.rglob("*"):
                if file_path.is_file():
                    arcname = "trip_photos/" + str(file_path.relative_to(_TRIP_PHOTOS_DIR))
                    zf.write(file_path, arcname=arcname)

    return buffer.getvalue()


def import_expedition_data(source_path: Path) -> ImportResult:
    """
    Merge an Expedition-data bundle (created by export_expedition_data())
    into this machine's data/trip_photos — never overwrites an existing
    record/photo, only adds new ones. Restart MIA to see imported
    data if the app is currently running (same as restore_backup()).
    """
    source_path = Path(source_path)

    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        return ImportResult(passed=False, errors=[f"Could not read '{source_path}': {exc}"])

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return ImportResult(passed=False, errors=["File is not a valid archive (corrupted?)."])

    if "manifest.json" not in zf.namelist():
        return ImportResult(passed=False, errors=["Not a MIA expedition data export (missing manifest)."])

    staging_dir = Path(tempfile.mkdtemp(prefix="mia_expedition_import_staging_"))
    counts: dict[str, int] = {}
    try:
        try:
            safe_extract_zip(zf, staging_dir)
        except BackupError as exc:
            return ImportResult(passed=False, errors=[str(exc)])

        for filename, id_field in _DATA_FILES:
            staged_file = staging_dir / "data" / filename
            live_file = _DATA_DIR / filename
            counts[filename] = _merge_json_records(staged_file, live_file, id_field)

        staged_photos = staging_dir / "trip_photos"
        counts["trip_photos"] = _merge_photo_files(staged_photos, _TRIP_PHOTOS_DIR)
    except OSError as exc:
        return ImportResult(passed=False, errors=[f"Import failed while writing to disk: {exc}"])
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    log.info("Imported expedition data from '%s': %s", source_path, counts)
    return ImportResult(passed=True, counts=counts)


def _merge_json_records(staged_file: Path, live_file: Path, id_field: str) -> int:
    """Appends records from staged_file whose id_field isn't already present in live_file. Returns count added."""
    if not staged_file.exists():
        return 0

    staged_records = json.loads(staged_file.read_text(encoding="utf-8"))

    if live_file.exists():
        try:
            live_records = json.loads(live_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            live_records = []
    else:
        live_records = []

    live_ids = {record.get(id_field) for record in live_records}
    added = 0
    for record in staged_records:
        if record.get(id_field) in live_ids:
            continue
        live_records.append(record)
        live_ids.add(record.get(id_field))
        added += 1

    if added:
        live_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(live_file, json.dumps(live_records, indent=2), encoding="utf-8")
    return added


def _merge_photo_files(staged_dir: Path, live_dir: Path) -> int:
    """Copies any staged photo file not already present at the same relative path under live_dir."""
    if not staged_dir.exists():
        return 0

    added = 0
    for file_path in staged_dir.rglob("*"):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(staged_dir)
        destination = live_dir / relative
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, destination)
        added += 1
    return added
