"""
core.web_backups
==================

Backups from the web's Settings (DEC-0125: Backup & Restore was on the
desktop's Settings only). For the PC's owner (the first account) only, since a
backup holds everyone's data on this MIA.

- `status(context, now)`: where backups go, the newest ones (name, size,
  when, whether it needs a passphrase), how long since the last one, and
  the nightly automatic backup (core/auto_backup.py): on or off, and its
  last problem if it had one.
- `make(context, passphrase, now)`: one backup into the backups folder
  (core/backup_manager.create_backup: config, data and the outside content
  folders), encrypted when a passphrase is given; named by the date and time.

Making one is not an action: a passphrase must never sit in a proposal, the
history or the undo log (the same rule as a password, server/app.py). It changes
nothing in MIA, so there's nothing to undo. Restoring stays on the PC: it
replaces everything and needs a person at the computer to confirm it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

KEEP_SHOWN = 5
SUFFIXES = (".zip", ".miabackup")


def folder(context) -> Path:
    """Where web backups are written: the `backup.folder` setting, else "MIA Backups" in the home folder."""
    config = getattr(context, "config", None)
    configured = config.get("backup.folder", "") if config is not None else ""
    return Path(configured) if configured else Path.home() / "MIA Backups"


def age_words(days: Optional[int]) -> str:
    """Pure logic. How long since the last backup: "today", "yesterday", "12 days ago", "never"."""
    if days is None:
        return "never"
    return "today" if days <= 0 else "yesterday" if days == 1 else f"{days} days ago"


def size_words(size: int) -> str:
    """Pure logic. A file's size: "820 KB", "14.2 MB"."""
    return f"{size / 1_048_576:.1f} MB" if size >= 1_048_576 else f"{max(1, round(size / 1024))} KB"


def status(context, now: Optional[datetime] = None) -> dict:
    """The backups section: the folder, the newest backups (newest first), how long since the last one, and the
    nightly backup's state (auto: {"on", "problem"})."""
    from core.backup_manager import is_backup_encrypted

    now = now or datetime.now()
    where = folder(context)
    try:
        files = [p for p in where.iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES] if where.is_dir() else []
    except OSError:
        files = []
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    rows = []
    for p in files[:KEEP_SHOWN]:
        made = datetime.fromtimestamp(p.stat().st_mtime)
        rows.append({"name": p.name, "size": size_words(p.stat().st_size), "when": made.strftime("%b %d, %Y %H:%M"),
                     "locked": is_backup_encrypted(p)})
    last = (now.date() - datetime.fromtimestamp(files[0].stat().st_mtime).date()).days if files else None
    config = getattr(context, "config", None)
    auto = {"on": bool(config.get("backup.auto_enabled", True)) if config is not None else False,
            "problem": str(config.get("backup.auto_problem", "") or "") if config is not None else ""}
    return {"folder": str(where), "backups": rows, "count": len(files), "last": age_words(last), "days": last,
            "auto": auto}


def make(context, passphrase: str = "", now: Optional[datetime] = None) -> dict:
    """Writes one backup into the folder (encrypted when there's a passphrase); {"made": name} or {"error": why}."""
    from core.backup_manager import create_backup

    now = now or datetime.now()
    where = folder(context)
    try:
        where.mkdir(parents=True, exist_ok=True)
    except OSError as problem:
        return {"error": f"Couldn't make the backups folder: {problem}"}
    name = f"mia_backup_{now:%Y-%m-%d_%H%M}" + (".miabackup" if passphrase else ".zip")
    result = create_backup(where / name, passphrase=passphrase or None, config=getattr(context, "config", None))
    if not result.passed:
        return {"error": "; ".join(result.errors) or "The backup didn't work."}
    return {"made": name, "locked": bool(passphrase)}
