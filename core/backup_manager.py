"""
core.backup_manager
=====================

Export/import M.I.A.'s config + data directory as a single backup
file, per docs/ROADMAP.md milestone 2.7. Optionally passphrase-encrypted
via core/secrets_manager.py.

File format:
    - Unencrypted: the raw zip bytes, completely unmodified — a plain
      backup is a genuinely standard zip file, openable with any zip
      tool (unzip, Windows Explorer, etc.), not just this codebase.
    - Encrypted: b"MIAB1" + secrets_manager.encrypt_bytes(zip_bytes, passphrase).
      An encrypted blob isn't a valid zip on its own regardless, so
      prepending a marker there costs nothing — and it's what lets
      restore (and the GUI, via is_backup_encrypted()) tell a
      passphrase is needed without depending on the file's extension,
      which a user could rename.
    (An earlier version prepended the same marker to plain backups
    too, for a uniform format — but that broke `unzip` and other
    standard tools, which choke on leading bytes before the zip
    signature. Not worth it for files meant to be tool-compatible.)

The zip itself contains:
    - manifest.json    — {"app": "M.I.A.", "manifest_version": 1, "created_at": ...}
    - config.json      — a copy of config/config.json
    - data/...          — a full copy of the data/ directory tree

Restoring is a destructive operation — it overwrites the live
config/config.json and replaces the entire data/ directory with the
backup's contents. This module performs that unconditionally when
asked; confirming with the user is the GUI layer's job (see
modules/settings/module.py), the same division of responsibility as
core/module_manager.py's install vs. the Modules screen's confirmation
dialogs.
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

from core.logger import get_logger
from core.secrets_manager import SecretsError, decrypt_bytes, encrypt_bytes

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _PROJECT_ROOT / "config" / "config.json"
_DATA_DIR = _PROJECT_ROOT / "data"

_MAGIC = b"MIAB1"
_MANIFEST_VERSION = 1


class BackupError(Exception):
    """Raised internally for failures surfaced back to callers as a result object."""


@dataclass
class BackupResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    destination: Optional[Path] = None


@dataclass
class RestoreResult:
    passed: bool
    errors: list[str] = field(default_factory=list)


def is_backup_encrypted(path: Path) -> bool:
    """
    Peek at a backup file's header to tell whether it needs a
    passphrase, without reading/decrypting the whole file. Returns
    False for anything that isn't a recognized M.I.A. backup at all —
    callers should rely on restore_backup()'s own validation for that;
    this is only for deciding whether to show a passphrase prompt.
    """
    try:
        with path.open("rb") as f:
            header = f.read(len(_MAGIC))
    except OSError:
        return False
    return header == _MAGIC


def create_backup(destination_path: Path, passphrase: Optional[str] = None) -> BackupResult:
    """Build a backup archive at destination_path, encrypted if `passphrase` is given."""
    destination_path = Path(destination_path)

    try:
        zip_bytes = _build_zip_bytes()
    except OSError as exc:
        return BackupResult(passed=False, errors=[f"Could not read config/data to back up: {exc}"])

    try:
        with destination_path.open("wb") as f:
            if passphrase:
                f.write(_MAGIC)
                f.write(encrypt_bytes(zip_bytes, passphrase))
            else:
                f.write(zip_bytes)
    except OSError as exc:
        return BackupResult(passed=False, errors=[f"Could not write backup file: {exc}"])

    log.info("Created backup at %s%s", destination_path, " (encrypted)" if passphrase else "")
    return BackupResult(passed=True, destination=destination_path)


def _build_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "app": "M.I.A.",
            "manifest_version": _MANIFEST_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        if _CONFIG_FILE.exists():
            zf.write(_CONFIG_FILE, arcname="config.json")

        if _DATA_DIR.exists():
            for file_path in _DATA_DIR.rglob("*"):
                if file_path.is_file():
                    arcname = "data/" + str(file_path.relative_to(_DATA_DIR))
                    zf.write(file_path, arcname=arcname)

    return buffer.getvalue()


def restore_backup(source_path: Path, passphrase: Optional[str] = None) -> RestoreResult:
    """
    Restore config/config.json and the data/ directory from a backup
    file created by create_backup(). Destructive: replaces the live
    config file and the entire data/ directory. Extracts into a staging
    temp directory first and validates it before touching anything
    live, so a bad/corrupt/wrong-passphrase backup can't leave a
    half-restored mess.
    """
    source_path = Path(source_path)

    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        return RestoreResult(passed=False, errors=[f"Could not read '{source_path}': {exc}"])

    if raw.startswith(_MAGIC):
        if not passphrase:
            return RestoreResult(passed=False, errors=["This backup is encrypted — a passphrase is required."])
        try:
            zip_bytes = decrypt_bytes(raw[len(_MAGIC):], passphrase)
        except SecretsError as exc:
            return RestoreResult(passed=False, errors=[str(exc)])
    else:
        # No magic prefix means "not encrypted" — a plain backup is
        # just a raw zip, so there's nothing to strip. Whether it's
        # actually a M.I.A. backup (vs. an unrelated file) is checked
        # below via the zip-open + manifest.json checks.
        zip_bytes = raw

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        return RestoreResult(passed=False, errors=["Backup contents are not a valid archive (corrupted?)."])

    if "manifest.json" not in zf.namelist():
        return RestoreResult(passed=False, errors=["Not a M.I.A. backup file (missing manifest)."])

    staging_dir = Path(tempfile.mkdtemp(prefix="mia_restore_staging_"))
    try:
        try:
            _safe_extract_all(zf, staging_dir)
        except BackupError as exc:
            return RestoreResult(passed=False, errors=[str(exc)])

        staged_config = staging_dir / "config.json"
        if not staged_config.exists():
            return RestoreResult(passed=False, errors=["Backup is missing config.json."])

        try:
            json.loads(staged_config.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return RestoreResult(passed=False, errors=[f"Backup's config.json is not valid JSON: {exc}"])

        # Everything validated — now touch the live filesystem.
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_config, _CONFIG_FILE)

        staged_data = staging_dir / "data"
        if _DATA_DIR.exists():
            shutil.rmtree(_DATA_DIR)
        if staged_data.exists():
            shutil.copytree(staged_data, _DATA_DIR)
        else:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)

    except OSError as exc:
        return RestoreResult(passed=False, errors=[f"Restore failed while writing to disk: {exc}"])
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    log.info("Restored config and data from backup '%s'.", source_path)
    return RestoreResult(passed=True)


def _safe_extract_all(zf: zipfile.ZipFile, target_dir: Path) -> None:
    """
    Extract every member of `zf` into `target_dir`, refusing to write
    outside it. zipfile has sanitized path traversal since Python 3.6,
    but this is cheap, explicit, and matches the same defense-in-depth
    core/module_validator.py already applies to untrusted archives.
    """
    target_dir = target_dir.resolve()
    for member in zf.namelist():
        member_path = (target_dir / member).resolve()
        if member_path != target_dir and target_dir not in member_path.parents:
            raise BackupError(f"Refusing to extract unsafe path in backup: {member}")
    zf.extractall(target_dir)
