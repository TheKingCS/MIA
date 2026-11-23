"""
core.data_recovery
======================

One shared helper for the visible half of data-corruption recovery.
Every core/*_manager.py's own `_load()` already falls back to an empty
state on a malformed JSON file (correct — the app must never fail to
boot or fail to open a screen over one bad file) and logs the failure.
But a log line nobody's watching on a kiosk device leaves the user
silently confused about why their data just reset, with no idea
anything went wrong at all.

Distinct from core.config_manager's own `_quarantine_corrupted_file()`
(2026-09-14, same stabilization pass) rather than sharing it: config.json
loads before `context.notifications` exists at all (ConfigManager is
the very first core service constructed), so quarantining the file
aside was the only real recovery trail available there. Every other
manager here DOES have notifications access by the time it loads, so
the more valuable fix is a real, visible notification — the user finds
out immediately, rather than only if they ever thought to go looking
for a stray `.corrupted-<timestamp>` file.

Each file that couldn't be read is also kept for the run (`unreadable`), so her answers name the
records they couldn't read rather than treating them as empty (REQ-FUN-221), until a restore brings
them back (`recovered`).
"""

from __future__ import annotations

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)


_unreadable: dict[str, float] = {}  # this run's stores that couldn't be read, by file name (REQ-FUN-221)


def recovered() -> None:
    """A restore brought the records back (core/backup_manager.restore_backup): nothing is unreadable any more, so
    her answers stop naming files as missing."""
    _unreadable.clear()


def unreadable() -> list[str]:
    """The stores that couldn't be read since MIA started (each reset to empty, its file set aside), by file name, in
    the order they were met: what an answer built from her records must name rather than leave out silently
    (REQ-FUN-221, core/assistant_chat.build_user_context_block)."""
    return list(_unreadable)


def notify_data_corruption(context: AppContext, filename: str) -> None:
    """Best-effort, never raises — called from inside an already-
    handled exception block (the caller already logged the real
    failure via log.exception()), so this must never itself become a
    new crash. Graceful no-op with no notifications service, same
    stance as every other optional-service check in this codebase. The file's name is also kept for this run
    (`unreadable`), so her answers say which of his records they couldn't read; the note says the way back (last
    night's backup), never a log file."""
    import time

    _unreadable.setdefault(str(filename), time.time())
    try:  # the data.recovered loop (core/loops.py): the file's name only, on this device
        from core.dev_store import DEV_DATA, DevStore

        DevStore(DEV_DATA / "recovered").append({"file": str(filename)[:120]})
    except Exception:
        log.exception("Couldn't keep the recovery of '%s' for the loops", filename)
    if context.notifications is None:
        return
    try:
        context.notifications.notify(
            title="⚠️ Data file recovered",
            message=(f"'{filename}' couldn't be read, so MIA started it empty; the unreadable copy was kept aside. "
                     "Restoring last night's backup (Settings, Backups) brings its records back."),
            level="warning",
            source="system",
        )
    except Exception:
        log.exception("Failed to raise the data-corruption notification itself for '%s'", filename)
