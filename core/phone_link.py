"""
core.phone_link
=================

When a linked phone last reached this PC (build plan step 3's `phone.link`;
the server kept it only in memory, so a restart forgot it). `seen()` is called
when a linked phone's device key signs a request in (server/app.py); it
writes at most once every `EVERY` per person, so a busy phone costs nothing.
Device-level, on the PC (`data/phone_link.json`): profile id -> the time.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text

FILE = Path(__file__).resolve().parent.parent / "data" / "phone_link.json"
EVERY = 300  # seconds between writes for one person
_written: dict[str, float] = {}


def seen(profile_id: str, path: Optional[Path] = None, now: Optional[float] = None) -> None:
    now = now if now is not None else time.time()
    if now - _written.get(profile_id, 0) < EVERY:
        return
    _written[profile_id] = now
    path = path or FILE
    found = last(path)
    found[profile_id] = datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(found, indent=1))
    except OSError:
        pass  # the record never breaks a request


def last(path: Optional[Path] = None) -> dict[str, str]:
    try:
        return json.loads((path or FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def hours_since(profile_id: str, path: Optional[Path] = None, now: Optional[datetime] = None) -> Optional[float]:
    when = last(path).get(profile_id)
    if not when:
        return None
    now = now or datetime.now(timezone.utc)
    return round((now - datetime.fromisoformat(when)).total_seconds() / 3600, 1)
