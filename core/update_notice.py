"""
core.update_notice
====================

An update waiting for his restart, said (Q-114, Zac 2026-11-23: "Never by itself": MIA OS never restarts the computer
by itself to finish an update, and MIA tells him when one is waiting).

On MIA OS an update is downloaded and staged at night (bootc); it goes in the next time he restarts or shuts down,
after a snapshot of his files. While one is staged, ostree keeps `/run/ostree/staged-deployment` (readable by
anyone, so no privilege is asked to look). `waiting()` says whether one is; `offer()` is the daily check's message
through the communication gate (paced like any other, never a nag): once for each staged update (its file's time is
the fingerprint), with how to do it now (Settings, or "restart to update": the action `system.apply_update`, his
password asked by the system's own dialog, core/system_helper.py). Off MIA OS there's nothing to say.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

STAGED = Path("/run/ostree/staged-deployment")


def waiting(path: Path = STAGED) -> Optional[str]:
    """Whether an update is staged for the next restart: a stamp for that update (when it was staged), or None."""
    if not sys.platform.startswith("linux") and path == STAGED:
        return None
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime).isoformat(timespec="minutes")
    except OSError:
        return None


def offer(context, now: datetime, path: Path = STAGED) -> list:
    """The daily check's message, once for each staged update: that it's ready and goes in at his next restart, that
    MIA never restarts by herself, and how to do it now. [] with none waiting."""
    from core.communication_gate import AMBIENT, Candidate

    stamp = waiting(path)
    if stamp is None:
        return []
    return [Candidate(
        topic="update_waiting", title="An update is ready",
        message=("An update for MIA OS is ready. It goes in the next time you restart or shut down, after a snapshot "
                 "of your files; I never restart the computer by myself. To do it now: Settings, then Restart To "
                 "Update, or say \"restart to update\"."),
        urgency=AMBIENT, source="system", fingerprint=f"update-staged-{stamp}")]
