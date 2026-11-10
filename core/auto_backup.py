"""
core.auto_backup
==================

A backup every night without anyone pressing a button (2026-11-10). Until
now `core/backup_manager.create_backup` ran only from the two Backup
buttons, so a person who never pressed one had none.

- `due(config, today)`: whether tonight's backup is still to make: on, not
  made yet today, and after AFTER_HOUR (night, when MIA is least in use).
- `run(context, today)`: one backup into the same folder as the buttons'
  (`core/web_backups.folder`, outside `data/`), named `mia_auto_<date>.zip`,
  then the rotation. The day is stamped in `backup.auto_last` either way, so
  a failing backup is tried once a night, not every five minutes; a problem
  is kept in `backup.auto_problem` for the Backups screen and the log.
- `keep(names, today)`: pure logic. Which automatic backups stay: the newest
  DAILY days, and the newest one of each week in the WEEKLY weeks before.
  Only `mia_auto_` files are ever removed; a backup made by hand never is.

Not encrypted: a passphrase can't be typed at night. MIA's most private
files are sealed on disk already (DEC-0126), and go into the zip sealed.
Run from the desktop's daily checks (`core/application.py`).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

PREFIX = "mia_auto_"
DAILY = 7
WEEKLY = 4
AFTER_HOUR = 2
_NAME = re.compile(r"^mia_auto_(\d{4}-\d{2}-\d{2})\.zip$")


def due(config, now: Optional[datetime] = None) -> bool:
    """Whether tonight's backup is still to make: `backup.auto_enabled` (on unless turned off), not yet today, and
    from AFTER_HOUR on."""
    now = now or datetime.now()
    if not config.get("backup.auto_enabled", True):
        return False
    return now.hour >= AFTER_HOUR and config.get("backup.auto_last", "") != now.date().isoformat()


def keep(names: list[str], today: date) -> set[str]:
    """Pure logic. The automatic backups to keep: those from the last DAILY days, and the newest of each week (Monday
    to Sunday) in the WEEKLY weeks before that, at most WEEKLY. Names that aren't automatic backups are never in
    question."""
    dated = sorted(((date.fromisoformat(m.group(1)), n) for n in names if (m := _NAME.match(n))), reverse=True)
    kept = {n for d, n in dated if (today - d).days < DAILY}
    weeks = []
    for d, n in dated:
        if (today - d).days < DAILY:
            continue
        if (today - d).days >= DAILY + 7 * WEEKLY:
            break  # older than the weekly window: removed
        week = d - timedelta(days=d.weekday())
        if week not in weeks:
            if len(weeks) == WEEKLY:
                break
            weeks.append(week)
            kept.add(n)
    return kept


def run(context, now: Optional[datetime] = None) -> dict:
    """Tonight's backup and the rotation: {"made": name, "removed": n} or {"error": why}. Never raises."""
    from core.backup_manager import create_backup
    from core.web_backups import folder

    now = now or datetime.now()
    config = context.config
    config.set("backup.auto_last", now.date().isoformat())
    where = folder(context)
    name = f"{PREFIX}{now.date().isoformat()}.zip"
    try:
        where.mkdir(parents=True, exist_ok=True)
        result = create_backup(where / name, config=config)
    except Exception as problem:  # a full disk, a missing drive: logged and said, never a crash at night
        log.exception("Tonight's automatic backup failed")
        result = None
        errors = [str(problem)]
    else:
        errors = list(result.errors)
    if result is None or not result.passed:
        config.set("backup.auto_problem", f"{now:%Y-%m-%d}: " + "; ".join(errors)[:300])
        config.save()
        return {"error": "; ".join(errors)}
    config.set("backup.auto_problem", "")
    config.save()
    removed = 0
    try:
        names = [p.name for p in where.iterdir() if p.is_file() and p.name.startswith(PREFIX)]
        for old in set(names) - keep(names, now.date()):
            (where / old).unlink()
            removed += 1
    except OSError:
        log.exception("Couldn't remove old automatic backups")
    log.info("Automatic backup %s made; %d old one(s) removed.", name, removed)
    return {"made": name, "removed": removed}
