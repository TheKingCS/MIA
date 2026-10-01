"""
core.homestead_manager
=======================

Watched-folder ingestion for MIA Home's summarized-state snapshots from
sibling automation projects — the first (and so far only) source is
MIA Homestead's greenhouse/aquaponics system
(`~/Projects/mia-homestead`, a separate repo), which exports via its
own `viewer/export_home_snapshot.py`. See that repo's
`docs/MIA_HOME_SYNC_PLAN.md` for the full cross-project scoping this
implements one half of.

Deliberately a sibling of `core/finance_manager.py`, not a shared
abstraction over it — same reasoning `core/finance_manager.py`'s own
docstring gives for why finance isn't generalized into
`reference_library_manager.py`'s pattern either: this project's
convention is one manager per external-content domain
(`finance_manager.py`, `reference_library_manager.py`, this one), and
two instances of a shape isn't yet reason enough to extract a base
class nothing else needs. This manager has no idea what "homestead"
means beyond the generic shape (`source`/`generated_at`, everything
else opaque) — same "don't assume more of the schema than's confirmed"
stance, since a homestead export could gain fields over time without
this manager needing to change.

**Delivery here is deliberately NOT automated** (matches finance's own
two sources, both manual/user-downloaded per docs/VISION.md) — a human
still has to get the exported `home_snapshot.json` from the greenhouse
Pi onto this machine's watched folder. See
mia-homestead's `docs/MIA_HOME_SYNC_PLAN.md` for why that's left
undecided rather than guessed at here.

Folder lives as a sibling of `data/` at the repo root
(`homestead_snapshots/`, same precedent as `financial_snapshots/`),
configurable via `homestead.snapshot_import_folder`, same
resolve-with-default pattern as `core/finance_manager.py`'s
`import_folder_path`. Successfully-parsed files move to
`homestead_snapshots/imported/` (kept, not deleted); files that fail to
parse move to `homestead_snapshots/failed/` so a broken file doesn't
get retried and re-logged on every poll forever.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_IMPORT_DIR = _PROJECT_ROOT / "homestead_snapshots"
_IMPORTED_SUBDIR = "imported"
_FAILED_SUBDIR = "failed"

_DATA_DIR = _PROJECT_ROOT / "data"
_SNAPSHOTS_FILE = _DATA_DIR / "homestead_snapshots.json"


@dataclass
class HomesteadSnapshot:
    source: str
    generated_at: str
    imported_at: str
    # The full raw parsed JSON, deliberately opaque beyond source/
    # generated_at — same reasoning as FinancialSnapshot.data: widgets
    # read whatever fields they need directly (e.g.
    # data["summary"]["critical_alert_count"]) rather than this manager
    # modeling every field of a schema that can grow independently on
    # the exporting side.
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"source": self.source, "generated_at": self.generated_at, "imported_at": self.imported_at, "data": self.data}

    @classmethod
    def from_dict(cls, raw: dict) -> "HomesteadSnapshot":
        return cls(
            source=raw["source"],
            generated_at=raw["generated_at"],
            imported_at=raw["imported_at"],
            data=raw.get("data", {}),
        )


def parse_snapshot_content(content: str) -> Optional[HomesteadSnapshot]:
    """
    Pure parsing/validation logic — testable without any filesystem
    I/O. Only `source` (str) and `generated_at` (str) are required;
    everything else is accepted as-is into `.data` without further
    validation, same reasoning as `core/finance_manager.py`'s function
    of the same name — being strict about optional fields risks
    rejecting a real, valid export over a field this project guessed
    wrong. Returns None (never raises) for anything unparseable/
    malformed.
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
    return HomesteadSnapshot(
        source=source,
        generated_at=generated_at,
        imported_at=datetime.now(timezone.utc).isoformat(),
        data=raw,
    )


class HomesteadManager:
    """Core-level Homestead service (`AppContext.homestead`)."""

    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._snapshots_file = self.data_dir / "homestead_snapshots.json" if data_dir is not None else _SNAPSHOTS_FILE
        self.context = context
        self._snapshots: dict[str, HomesteadSnapshot] = {}
        self._load()

        try:
            self.import_folder_path.mkdir(parents=True, exist_ok=True)
            (self.import_folder_path / _IMPORTED_SUBDIR).mkdir(exist_ok=True)
            (self.import_folder_path / _FAILED_SUBDIR).mkdir(exist_ok=True)
        except OSError:
            # Same "don't crash over a missing/unmounted folder" stance
            # as FinanceManager — scan_for_new_snapshots() below already
            # no-ops gracefully if the folder isn't there.
            log.warning("Could not create/access homestead snapshot import folder: %s", self.import_folder_path)

    @property
    def import_folder_path(self) -> Path:
        configured = self.context.config.get("homestead.snapshot_import_folder", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_IMPORT_DIR

    def _load(self) -> None:
        if not self._snapshots_file.exists():
            return
        try:
            raw = json.loads(self._snapshots_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.warning("Could not read %s — starting with no stored snapshots.", self._snapshots_file)
            notify_data_corruption(self.context, self._snapshots_file.name)
            return
        for source, snapshot_raw in raw.items():
            try:
                self._snapshots[source] = HomesteadSnapshot.from_dict(snapshot_raw)
            except (KeyError, TypeError):
                continue

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._snapshots_file,
            json.dumps({source: snap.to_dict() for source, snap in self._snapshots.items()}, indent=2),
            encoding="utf-8",
        )

    def scan_for_new_snapshots(self) -> list[HomesteadSnapshot]:
        """
        Called by a periodic timer (core/application.py) — scans the
        watched folder's top level (not the imported/failed
        subfolders) for `*.json` files, parses each, and either stores
        it (moving the file into `imported/`) or discards it (moving
        into `failed/`, logged once). Returns the snapshots that were
        newly imported *this call*, so the caller can decide whether to
        fire a notification, without this manager needing to know
        anything about notifications itself. Same shape as
        FinanceManager.scan_for_new_snapshots() — see that method for
        the fuller reasoning, identical here.

        A snapshot only replaces an existing one for the same `source`
        if its `generated_at` is newer (plain string comparison — both
        rely on ISO 8601 timestamps, which sort correctly as strings) —
        a stale re-dropped file shouldn't regress already-imported
        newer data.
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
                log.warning("Could not parse homestead snapshot %s — moving to failed/.", file_path.name)
                self._move_file(file_path, _FAILED_SUBDIR)
                continue

            existing = self._snapshots.get(snapshot.source)
            if existing is None or snapshot.generated_at > existing.generated_at:
                self._snapshots[snapshot.source] = snapshot
                newly_imported.append(snapshot)
                log.info("Imported homestead snapshot from source '%s'.", snapshot.source)
            else:
                log.info(
                    "Homestead snapshot %s is not newer than the stored '%s' snapshot — discarding.",
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

    def latest_snapshot(self, source: str) -> Optional[HomesteadSnapshot]:
        return self._snapshots.get(source)

    def all_latest_snapshots(self) -> list[HomesteadSnapshot]:
        return list(self._snapshots.values())
