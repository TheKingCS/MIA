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
"""

from __future__ import annotations

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)


def notify_data_corruption(context: AppContext, filename: str) -> None:
    """Best-effort, never raises — called from inside an already-
    handled exception block (the caller already logged the real
    failure via log.exception()), so this must never itself become a
    new crash. Graceful no-op with no notifications service, same
    stance as every other optional-service check in this codebase."""
    if context.notifications is None:
        return
    try:
        context.notifications.notify(
            title="⚠️ Data file recovered",
            message=f"'{filename}' couldn't be read and has been reset to empty. See logs/mia.log for detail.",
            level="warning",
            source="system",
        )
    except Exception:
        log.exception("Failed to raise the data-corruption notification itself for '%s'", filename)
