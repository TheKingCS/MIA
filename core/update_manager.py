"""
core.update_manager
======================

Apply an offline update package (a zip of new/changed project files)
onto the running M.I.A. installation, per docs/ROADMAP.md milestone
2.8. "No internet required" — the package is just a local file (from
a USB drive, or anywhere else); this module never makes a network call.

Update package format — see docs/UPDATE_PACKAGE_SPEC.md for the full
reference. Briefly: a zip with `update_manifest.json` at its root
    {"app": "M.I.A.", "manifest_version": 1, "description": "...", "target_version": "..."}
plus the actual files to apply, at the same relative paths they'd have
in the project (e.g. "core/module_manager.py", "gui/new_widget.py").
Applying copies every non-manifest file in the package into the
project root at its matching path, overwriting whatever's there and
creating new files/directories as needed.

Security note: this can overwrite ANY file in the project, including
core/ and deploy/ (boot infrastructure) — there is no sandboxing and
no code review performed. Only apply update packages you built
yourself or reviewed and trust, exactly the same judgment
docs/MODULE_SPEC.md already asks for when installing a new module.

Safety net: if the project directory is a git working tree and `git`
is on PATH, a successful update stages and commits *only the files the
update itself touched* (not a blanket `git add -A`, which could sweep
in unrelated uncommitted work already sitting in the tree) — so a bad
update is a one-command `git revert` away, per the "every change
should go through git" principle in docs/ROADMAP.md's Self-Modification
section. If git isn't available, the update still applies; the result
just notes that no commit was made.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MANIFEST_NAME = "update_manifest.json"


class UpdateError(Exception):
    """Raised internally for failures surfaced back to callers as a result object."""


@dataclass
class UpdateManifest:
    description: str
    target_version: str


@dataclass
class UpdateResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    applied_files: list[str] = field(default_factory=list)
    committed: bool = False


def peek_update_manifest(source_path: Path) -> Optional[UpdateManifest]:
    """
    Read just the manifest from an update package without applying it —
    used by the GUI to show "what is this update?" before confirming.
    Returns None if the file isn't a readable, recognizable update
    package; callers should still let apply_update_package() do the
    real validation rather than treating a None here as fatal.
    """
    try:
        with zipfile.ZipFile(source_path) as zf:
            if _MANIFEST_NAME not in zf.namelist():
                return None
            raw = zf.read(_MANIFEST_NAME)
    except (OSError, zipfile.BadZipFile):
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if data.get("app") != "M.I.A.":
        return None

    return UpdateManifest(
        description=data.get("description", ""),
        target_version=data.get("target_version", "unknown"),
    )


def apply_update_package(source_path: Path) -> UpdateResult:
    """
    Validate and apply an update package. Extracts into a staging temp
    directory first and validates it before touching any live project
    file, so a corrupt/malicious package can't leave a half-applied
    mess (same pattern as core/backup_manager.py's restore_backup()).
    """
    source_path = Path(source_path)

    try:
        zf = zipfile.ZipFile(source_path)
    except (OSError, zipfile.BadZipFile) as exc:
        return UpdateResult(passed=False, errors=[f"Not a valid update package: {exc}"])

    if _MANIFEST_NAME not in zf.namelist():
        return UpdateResult(passed=False, errors=["Not a M.I.A. update package (missing manifest)."])

    try:
        manifest_data = json.loads(zf.read(_MANIFEST_NAME))
    except json.JSONDecodeError as exc:
        return UpdateResult(passed=False, errors=[f"Update manifest is not valid JSON: {exc}"])

    if manifest_data.get("app") != "M.I.A.":
        return UpdateResult(passed=False, errors=["Not a M.I.A. update package (manifest app mismatch)."])

    staging_dir = Path(tempfile.mkdtemp(prefix="mia_update_staging_"))
    try:
        try:
            _safe_extract_all(zf, staging_dir)
        except UpdateError as exc:
            return UpdateResult(passed=False, errors=[str(exc)])

        applied_files: list[str] = []
        for staged_path in sorted(staging_dir.rglob("*")):
            if not staged_path.is_file():
                continue
            relative_path = staged_path.relative_to(staging_dir)
            if str(relative_path) == _MANIFEST_NAME:
                continue

            destination = _PROJECT_ROOT / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_path, destination)
            applied_files.append(str(relative_path))

    except OSError as exc:
        return UpdateResult(passed=False, errors=[f"Update failed while writing to disk: {exc}"])
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    if not applied_files:
        return UpdateResult(passed=False, errors=["Update package contained no files besides the manifest."])

    result = UpdateResult(passed=True, applied_files=applied_files)
    committed, commit_warning = _commit_update(applied_files, manifest_data.get("description", ""), source_path)
    result.committed = committed
    if commit_warning:
        result.warnings.append(commit_warning)

    log.info(
        "Applied update package '%s': %d file(s), git commit=%s",
        source_path, len(applied_files), committed,
    )
    return result


def _safe_extract_all(zf: zipfile.ZipFile, target_dir: Path) -> None:
    """
    Extract every member of `zf` into `target_dir`, refusing to write
    outside it. Same defense-in-depth zip-slip guard as
    core/backup_manager.py's _safe_extract_all — see that module's
    comment for why this is checked explicitly rather than trusting
    zipfile's own (already decent, but not this codebase's only line
    of defense) path sanitization.
    """
    target_dir = target_dir.resolve()
    for member in zf.namelist():
        member_path = (target_dir / member).resolve()
        if member_path != target_dir and target_dir not in member_path.parents:
            raise UpdateError(f"Refusing to extract unsafe path in update package: {member}")
    zf.extractall(target_dir)


def _commit_update(
    applied_files: list[str], description: str, source_path: Path
) -> tuple[bool, Optional[str]]:
    """
    Best-effort: stage and commit exactly the files the update applied,
    if the project is a git working tree and git is on PATH. Never
    raises — a failure here doesn't undo the (already-successful) file
    update, it just means no automatic rollback point was created.

    Deliberately `git add <specific files>`, not `git add -A` — a
    developer could have unrelated uncommitted work already sitting in
    the tree, and that shouldn't get swept into this commit.
    """
    if shutil.which("git") is None:
        return False, "git is not available — no automatic rollback commit was created."

    if not (_PROJECT_ROOT / ".git").exists():
        return False, "This is not a git working tree — no automatic rollback commit was created."

    message = f"Apply update package: {source_path.name}"
    if description:
        message += f"\n\n{description}"

    try:
        subprocess.run(
            ["git", "add", "--"] + applied_files,
            cwd=_PROJECT_ROOT, check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=_PROJECT_ROOT, check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        return False, f"Update applied, but the automatic git commit failed: {detail}"

    return True, None
