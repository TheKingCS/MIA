"""
core.atomic_write
====================

One shared helper for crash-safe file writes. Every core/*_manager.py
persists its state as JSON via a direct `path.write_text(...)` call —
which is NOT atomic: a crash, power loss, or disk-full condition mid-
write can leave that file truncated or corrupted, permanently losing
everything in it. A real risk for this project's actual deployment
target (a kiosk device that can lose power ungracefully in the field),
found by auditing every manager's own `_save()` method (2026-09-14) —
not a single one used a safer write, across ~45 files.

The fix: write the new content to a temporary file in the SAME
directory as the real target (same filesystem — required for
os.replace() to be atomic across platforms), flush + fsync it to disk,
then os.replace() it onto the real path. os.replace() is atomic on
both POSIX and Windows — the live file is always either the complete
old content or the complete new content, never a partial write, no
matter when a crash happens. If anything goes wrong before the
replace, the temp file is cleaned up and the original file is left
completely untouched.

Deliberately a single small function, not a class or a context
manager — every call site here is "serialize the whole state, write
the whole file," never a streaming/partial write, so there's nothing
more to abstract.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """
    Write `text` to `path` crash-safely — same call shape as
    `Path.write_text()` (just with `path` as an explicit first
    argument instead of the receiver), so it's a drop-in replacement
    at every call site. `path`'s parent directory must already exist
    (same requirement every existing call site already satisfies via
    its own `_DATA_DIR.mkdir(parents=True, exist_ok=True)` before
    calling this).
    """
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
