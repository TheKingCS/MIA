"""
core.restore_drill
====================

The monthly restore drill (WP-09, DEC-0259, REQ-SEC-037): proof that a backup really comes back. Once a month, from
AFTER_HOUR at night, the newest backup that can be opened without a passphrase (the nightly `mia_auto_` one, else the
newest plain zip) is restored into a scratch folder of its own, never over MIA's data, and every store in it is
opened: a `.json` file read whole, a `.jsonl` file line by line, each sealed one through its key (core/at_rest.py),
exactly as MIA reads them at start. The scratch folder is removed afterwards.

The result is kept in the config (`backup.drill`: when, which backup, how many files, how many opened, the first
names that didn't) and shown on Settings, Backups. A drill that fails is told at once (it's about not losing his
data: a direct notification, like an alarm); one that passes is just kept. A backup locked with a passphrase can't
be opened at night, so it's never the one drilled.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

AFTER_HOUR = 3  # after the nightly backup (core/auto_backup.AFTER_HOUR)
EVERY_DAYS = 28
SHOWN_FAILURES = 10


def due(config, now: Optional[datetime] = None) -> bool:
    """Whether this month's drill is still to run: from AFTER_HOUR, and EVERY_DAYS since the last one (or never); one
    that was skipped (no backup yet) is tried again the next night."""
    now = now or datetime.now()
    if now.hour < AFTER_HOUR:
        return False
    kept = (config.get("backup.drill", {}) or {}) if config is not None else {}
    if kept.get("skipped"):
        return str(kept.get("at", ""))[:10] != now.date().isoformat()  # no backup yet: looked for again each night
    last = kept.get("at", "")
    try:
        return (now.date() - date.fromisoformat(str(last)[:10])).days >= EVERY_DAYS
    except ValueError:
        return True


def newest_backup(folder: Path) -> Optional[Path]:
    """The backup to drill: the newest nightly one, else the newest plain zip (a passphrase-locked .miabackup can't be
    opened at night); None when there's none."""
    try:
        zips = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".zip"]
    except OSError:
        return None
    nightly = [p for p in zips if p.name.startswith("mia_auto_")]
    pool = nightly or zips
    return max(pool, key=lambda p: p.stat().st_mtime) if pool else None


def open_store(path: Path) -> Optional[str]:
    """Opens one restored store the way MIA does: None when it opens, else why not (sealed under a key not held, a
    damaged envelope, JSON that won't read). A .jsonl may be sealed line by line or whole; each line is read."""
    from core import at_rest

    try:
        text = path.read_text(encoding="utf-8")
        if at_rest.line_sealed(path):  # sealed a line at a time: each line opened (as open_text does)
            lines, failed = at_rest.open_lines(text)
            if failed:
                return f"{failed} line(s) wouldn't open"
            text = "\n".join(lines)
        elif at_rest.is_sealed(text):  # sealed whole, a .jsonl too (turn traces, the Fix-It Log)
            text = at_rest.unseal(text)
        if path.suffix.lower() == ".jsonl":
            for line in text.splitlines():
                if line.strip():
                    json.loads(line)
        else:
            json.loads(text)
        return None
    except (OSError, ValueError, UnicodeDecodeError) as problem:
        return str(problem)[:120] or type(problem).__name__


def drill(backup: Path) -> dict:
    """Restores one backup's stores (data/ .json and .jsonl, never photos or documents) into a scratch folder and opens
    every one: {at, backup, files, opened, failed: [{file, why}], passed}. Never raises; the scratch folder is
    always removed."""
    from core.backup_manager import safe_extract_zip

    at = datetime.now().isoformat(timespec="seconds")
    scratch = Path(tempfile.mkdtemp(prefix="mia_restore_drill_"))
    try:
        with zipfile.ZipFile(backup) as zf:
            # Only the stores, through the same safe extraction a restore uses: photos and media aren't read here.
            stores_only = zipfile.ZipFile(scratch / "stores.zip", "w")
            for member in zf.infolist():
                if member.filename.startswith("data/") and member.filename.lower().endswith((".json", ".jsonl")):
                    stores_only.writestr(member, zf.read(member))
            stores_only.close()
            with zipfile.ZipFile(scratch / "stores.zip") as only:
                safe_extract_zip(only, scratch)
            (scratch / "stores.zip").unlink()
        stores = sorted(p for p in (scratch / "data").rglob("*") if p.is_file() and p.suffix.lower() in (".json", ".jsonl"))
        failed = []
        for path in stores:
            why = open_store(path)
            if why:
                failed.append({"file": str(path.relative_to(scratch / "data")).replace("\\", "/"), "why": why})
        passed = bool(stores) and not failed
        return {"at": at, "backup": backup.name, "files": len(stores), "opened": len(stores) - len(failed),
                "failed": failed[:SHOWN_FAILURES], "passed": passed,
                **({} if stores else {"why": "the backup holds no stores"})}
    except Exception as problem:  # noqa: BLE001 - a BackupError, a bad zip, a full disk: the drill fails, said
        return {"at": at, "backup": backup.name, "files": 0, "opened": 0, "failed": [], "passed": False,
                "why": f"it couldn't be restored: {str(problem)[:160]}"}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def run(context, now: Optional[datetime] = None) -> dict:
    """This month's drill: the newest backup restored and every store opened, the result kept in `backup.drill` and a
    failure told to the PC's owner at once. Returns the result; {"skipped": why} when there's no backup to drill."""
    from core.web_backups import folder

    config = context.config
    backup = newest_backup(folder(context))
    if backup is None:
        result = {"at": (now or datetime.now()).isoformat(timespec="seconds"), "skipped": "no backup to drill yet"}
        config.set("backup.drill", result)
        config.save()
        return result
    result = drill(backup)
    config.set("backup.drill", result)
    config.save()
    if result["passed"]:
        log.info("Restore drill passed: %s, %d stores opened.", backup.name, result["opened"])
    else:
        log.warning("Restore drill failed: %s", result.get("why") or result["failed"])
        notes = getattr(context, "notifications", None)
        if notes is not None:
            said = result.get("why") or (f"{result['files'] - result['opened']} of {result['files']} stores in it "
                                         f"wouldn't open, the first {result['failed'][0]['file']}")
            notes.notify("This month's backup check failed", f"MIA restored {backup.name} into a scratch folder to "
                         f"check it, and {said}. Your data on this PC is untouched. Settings, Backups has more.",
                         level="warning", source="backup", always=True)
    return result


def words(result: Optional[dict]) -> str:
    """Pure logic. The last drill in a sentence, for the Backups section and the backup tool."""
    if not result:
        return "No restore check has run yet: the first runs on its own within a month."
    day = str(result.get("at", ""))[:10]
    if result.get("skipped"):
        return f"The restore check on {day} had no backup to check yet."
    if result.get("passed"):
        return f"Restore check {day}: {result.get('backup')} came back whole, all {result.get('files')} stores opened."
    return f"Restore check {day} FAILED on {result.get('backup')}: " + (
        result.get("why") or f"{result.get('files', 0) - result.get('opened', 0)} stores wouldn't open")
