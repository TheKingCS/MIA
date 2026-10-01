"""
core.account_data
===================

Your data is yours to take or remove (2026-10-01, accounts stage 5).

- **Export** (`export_account`): one .zip with your account details (no
  password or recovery hashes), every file in your own folder
  (conversations, memories, notes, reasons, workouts, classes, drafts,
  notifications; the private journal stays encrypted with your
  passphrase), and, if you ask, your household's shared files. The stored
  mail password for sending is never included.
- **Delete** (`delete_account`): your password confirms it; your folder
  is archived (`data/profiles/_deleted_<id>_<time>/`, as before) or, if
  you choose, erased for good. A household nobody belongs to any more is
  forgotten; one you share stays with the others.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

# Never exported: the encrypted mail password (core/mail_send.py).
_NEVER_EXPORT = {"mail_send.enc"}
_PRIVATE_FIELDS = {"password_hash", "password_salt", "recovery_hash", "recovery_salt"}

README = """This is your MIA data, exported {when}.

profile.json   your account: name, email, settings, interests
personal/      your own things (each .json file is readable text)
household/     your household's shared things, if you chose to include them

private_journal.json stays encrypted: only your journal passphrase opens it.
The password MIA uses to send your email is never exported.
"""


def _store_paths(store) -> list[Path]:
    """The files and folders a store keeps (its Path attributes)."""
    return [v for k, v in vars(store).items() if isinstance(v, Path) and k != "data_dir" and v.exists()]


def household_files(context, profile_id: str) -> dict[Path, str]:
    """The household's shared files: path -> name inside the export."""
    personal = getattr(context, "personal_data", None)
    households = getattr(context, "households", None)
    if personal is None:
        return {}
    hid = households.household_of(profile_id) if households is not None else None
    files: dict[Path, str] = {}
    for store in personal.household_stores(hid).values():
        root = Path(getattr(store, "data_dir", ""))
        for path in _store_paths(store):
            for found in ([path] if path.is_file() else path.rglob("*")):
                if found.is_file():
                    try:
                        files[found] = found.relative_to(root).as_posix()
                    except ValueError:
                        files[found] = found.name
    return files


def export_account(context, profile_id: str, destination: Path, include_household: bool = False) -> Path:
    """Write the .zip and return its path."""
    profiles = context.profiles
    profile = profiles.get_profile(profile_id)
    if profile is None:
        raise ValueError("No such account.")
    record = {k: v for k, v in (context.config.get(f"profiles.{profile_id}") or {}).items() if k not in _PRIVATE_FIELDS}
    record["profile_id"] = profile_id
    households = getattr(context, "households", None)
    if households is not None:
        hid = households.household_of(profile_id)
        record["household"] = {"id": hid, "name": households.name(hid),
                               "shared_with": [p.name for p in households.shares_with(profile_id)]}
    destination = Path(destination)
    if destination.is_dir():
        stamp = datetime.now().strftime("%Y-%m-%d")
        destination = destination / f"MIA export - {profile.name} - {stamp}.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    personal = getattr(context, "personal_data", None)
    folder = personal.folder(profile_id) if personal is not None else profile.data_dir
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", README.format(when=datetime.now().strftime("%Y-%m-%d %H:%M")))
        archive.writestr("profile.json", json.dumps(record, indent=2))
        if folder.exists():
            for path in sorted(folder.rglob("*")):
                if path.is_file() and path.name not in _NEVER_EXPORT:
                    archive.write(path, f"personal/{path.relative_to(folder).as_posix()}")
        if include_household:
            for path, name in household_files(context, profile_id).items():
                archive.write(path, f"household/{name}")
    log.info("Exported account %s to %s", profile_id, destination)
    return destination


def delete_account(context, profile_id: str, password: Optional[str], erase: bool = False) -> bool:
    """Delete the account (refused for the device's only account or a wrong
    password). `erase`: remove the archived folder too, for good."""
    profiles = context.profiles
    profile = profiles.get_profile(profile_id)
    if profile is None:
        return False
    households = getattr(context, "households", None)
    hid = households.household_of(profile_id) if households is not None else None
    archive_root = profile.data_dir.parent
    before = set(archive_root.glob(f"_deleted_{profile_id}_*")) if archive_root.exists() else set()
    if not profiles.delete_profile(profile_id, password=password):
        return False
    if erase:
        for archived in set(archive_root.glob(f"_deleted_{profile_id}_*")) - before:
            shutil.rmtree(archived, ignore_errors=True)
        log.info("Erased the data of deleted account %s.", profile_id)
    if households is not None and hid:
        households._drop_if_empty(hid)
    return True
