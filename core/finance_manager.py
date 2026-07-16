"""
core.finance_manager
=======================

Watched-folder ingestion for MIA Home's external financial snapshot
exports — the Kraken trading agent and the real estate portfolio
dashboard (both built as separate projects, per `docs/VISION.md`'s
"MIA Home's expanded scope" section), each producing the same shared
JSON export shape documented there. This manager has no idea Kraken or
real estate exist as concepts — it only knows how to read that generic
shape (`source`/`generated_at`, everything else opaque) and doesn't
assume every field the one worked example in `VISION.md` happens to
show is actually present, since the real Kraken export's exact schema
isn't confirmed yet. Widgets that want specific fields read
`FinancialSnapshot.data` themselves.

**Why a watched folder, not a manual-only upload button** (the
decision this replaces an open question in `docs/ROADMAP.md`): both
source tools already require a manual export/download step on the
user's part (neither is a live device connection like Core docking to
Home) — reusing v0.19's Home Dock auto-import polling *pattern*
(`core/device_framework.py`'s periodic scan) here too means the only
manual step left is dropping the exported file into one folder, not
re-clicking an import button every time. Same "ambient, not
re-prompted" companion-philosophy preference this project has applied
elsewhere (Smart Suggestions, the startup briefing).

Folder lives as a sibling of `data/` at the repo root
(`financial_snapshots/`, same precedent as `reference_library/` and
`trip_photos/` — user-provided external content, not app-owned
`data/*.json` state), configurable via `finance.snapshot_import_folder`
same resolve-with-default pattern as
`core/reference_library_manager.py`'s `root_path`. Successfully-parsed
files move to `financial_snapshots/imported/` (kept, not deleted, in
case the raw export is ever needed again); files that fail to parse
move to `financial_snapshots/failed/` so a broken file doesn't get
retried and re-logged on every single poll forever.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_IMPORT_DIR = _PROJECT_ROOT / "financial_snapshots"
_IMPORTED_SUBDIR = "imported"
_FAILED_SUBDIR = "failed"

_DATA_DIR = _PROJECT_ROOT / "data"
_SNAPSHOTS_FILE = _DATA_DIR / "financial_snapshots.json"


@dataclass
class FinancialSnapshot:
    source: str
    generated_at: str
    imported_at: str
    # The full raw parsed JSON, deliberately opaque beyond source/
    # generated_at — widgets read whatever fields they need directly
    # (e.g. data["summary"]["monthly_cash_flow"]) rather than this
    # manager trying to model every field of a schema that isn't fully
    # confirmed yet (see module docstring).
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"source": self.source, "generated_at": self.generated_at, "imported_at": self.imported_at, "data": self.data}

    @classmethod
    def from_dict(cls, raw: dict) -> "FinancialSnapshot":
        return cls(
            source=raw["source"],
            generated_at=raw["generated_at"],
            imported_at=raw["imported_at"],
            data=raw.get("data", {}),
        )


def parse_snapshot_content(content: str) -> Optional[FinancialSnapshot]:
    """
    Pure parsing/validation logic — testable without any filesystem
    I/O. Only `source` (str) and `generated_at` (str) are required;
    everything else is accepted as-is into `.data` without further
    validation, since the real Kraken export's exact shape isn't
    confirmed — being strict about optional fields here would risk
    rejecting a real, valid export over a field this project guessed
    wrong. Returns None (never raises) for anything unparseable/
    malformed, same "degrade gracefully, don't crash the app over bad
    external input" stance as every other manager here.
    """
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    source = raw.get("source")
    generated_at = raw.get("generated_at")
    if not isinstance(source, str) or not source:
        return None
    if not isinstance(generated_at, str) or not generated_at:
        return None
    return FinancialSnapshot(
        source=source,
        generated_at=generated_at,
        imported_at=datetime.now(timezone.utc).isoformat(),
        data=raw,
    )


class FinanceManager:
    """Core-level Finance service (`AppContext.finance`)."""

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._snapshots: dict[str, FinancialSnapshot] = {}
        self._load()

        try:
            self.import_folder_path.mkdir(parents=True, exist_ok=True)
            (self.import_folder_path / _IMPORTED_SUBDIR).mkdir(exist_ok=True)
            (self.import_folder_path / _FAILED_SUBDIR).mkdir(exist_ok=True)
        except OSError:
            # Same "don't crash over a missing/unmounted folder" stance
            # as ReferenceLibraryManager — scan_for_new_snapshots()
            # below already no-ops gracefully if the folder isn't there.
            log.warning("Could not create/access financial snapshot import folder: %s", self.import_folder_path)

    @property
    def import_folder_path(self) -> Path:
        configured = self.context.config.get("finance.snapshot_import_folder", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_IMPORT_DIR

    def _load(self) -> None:
        if not _SNAPSHOTS_FILE.exists():
            return
        try:
            raw = json.loads(_SNAPSHOTS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.warning("Could not read %s — starting with no stored snapshots.", _SNAPSHOTS_FILE)
            return
        for source, snapshot_raw in raw.items():
            try:
                self._snapshots[source] = FinancialSnapshot.from_dict(snapshot_raw)
            except (KeyError, TypeError):
                continue

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _SNAPSHOTS_FILE.write_text(
            json.dumps({source: snap.to_dict() for source, snap in self._snapshots.items()}, indent=2),
            encoding="utf-8",
        )

    def scan_for_new_snapshots(self) -> list[FinancialSnapshot]:
        """
        Called by a periodic timer (core/application.py) — scans the
        watched folder's top level (not the imported/failed
        subfolders) for `*.json` files, parses each, and either stores
        it (moving the file into `imported/`) or discards it (moving
        into `failed/`, logged once). Returns the snapshots that were
        newly imported *this call*, so the caller can decide whether to
        fire a notification, without this manager needing to know
        anything about notifications itself.

        A snapshot only replaces an existing one for the same `source`
        if its `generated_at` is newer (plain string comparison — both
        source tools produce ISO 8601 timestamps, which sort correctly
        as strings) — a stale re-dropped file shouldn't regress
        already-imported newer data.
        """
        if not self.import_folder_path.is_dir():
            return []

        newly_imported = []
        for file_path in sorted(self.import_folder_path.glob("*.json")):
            try:
                content = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                log.warning("Could not read %s: %s", file_path, exc)
                continue

            snapshot = parse_snapshot_content(content)
            if snapshot is None:
                log.warning("Could not parse financial snapshot %s — moving to failed/.", file_path.name)
                self._move_file(file_path, _FAILED_SUBDIR)
                continue

            existing = self._snapshots.get(snapshot.source)
            if existing is None or snapshot.generated_at > existing.generated_at:
                self._snapshots[snapshot.source] = snapshot
                newly_imported.append(snapshot)
                log.info("Imported financial snapshot from source '%s'.", snapshot.source)
            else:
                log.info(
                    "Financial snapshot %s is not newer than the stored '%s' snapshot — discarding.",
                    file_path.name,
                    snapshot.source,
                )
            self._move_file(file_path, _IMPORTED_SUBDIR)

        if newly_imported:
            self._save()
        return newly_imported

    def _move_file(self, file_path: Path, subdir: str) -> None:
        destination = self.import_folder_path / subdir / file_path.name
        try:
            if destination.exists():
                # Avoid clobbering an earlier file of the same name —
                # timestamp-suffix it rather than overwrite or raise.
                stamp = datetime.now().strftime("%Y%m%d%H%M%S")
                destination = destination.with_stem(f"{destination.stem}_{stamp}")
            shutil.move(str(file_path), str(destination))
        except OSError as exc:
            log.warning("Could not move %s into %s/: %s", file_path, subdir, exc)

    def latest_snapshot(self, source: str) -> Optional[FinancialSnapshot]:
        return self._snapshots.get(source)

    def all_latest_snapshots(self) -> list[FinancialSnapshot]:
        return list(self._snapshots.values())
