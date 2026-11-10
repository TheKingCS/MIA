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

It is also where MIA's most private files are sealed (DEC-0126,
core/at_rest.py): `seal_text` encrypts a file whose name is in
at_rest.SEALED and leaves every other file's text as it is. Such a
file is read back with `at_rest.open_text`.

Two guards for the one failure an atomic write can't stop (2026-11-10):
a store that couldn't read its file starts empty, and its next save
would write that near-empty state over everything that was there.
(a) A write that would shrink a file of some size to under half keeps
the old file beside it as `.<name>.prev` (hidden, so sync skips it; one
per file, replaced by the next such write, and removed after
PREV_KEEP_DAYS so a deliberate clear-out doesn't linger). (b) On
Windows the replace fails with PermissionError while another reader
holds the file open, so it is retried a few times before giving up.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

# A file this size or larger that a write would shrink to under half keeps its old contents (guard a).
PREV_MIN_BYTES = 512
# How long a kept `.prev` copy stays before the next write of that file removes it.
PREV_KEEP_DAYS = 3
# Attempts at the replace while another reader holds the file (guard b), with a growing pause between.
REPLACE_ATTEMPTS = 5


def prev_path(path: Path) -> Path:
    """Where the writer keeps a file's old contents before a large shrink: `.<name>.prev` beside it."""
    path = Path(path)
    return path.with_name(f".{path.name}.prev")


def _keep_previous(path: Path, new_size: int) -> None:
    """Guard (a): copies `path` to its `.prev` when the new contents are under half its size, and drops a `.prev`
    older than PREV_KEEP_DAYS. Never raises: a failed copy is logged and the write goes on."""
    prev = prev_path(path)
    try:
        old_size = path.stat().st_size
    except OSError:
        return
    try:
        if old_size >= PREV_MIN_BYTES and new_size * 2 < old_size:
            shutil.copy2(path, prev)
        elif prev.exists() and time.time() - prev.stat().st_mtime > PREV_KEEP_DAYS * 86400:
            prev.unlink()
    except OSError:
        from core.logger import get_logger

        get_logger(__name__).exception("Couldn't keep the old contents of %s", path.name)


def _replace(tmp_path: Path, path: Path) -> None:
    """Guard (b): os.replace, retried on PermissionError (a reader holding the file on Windows)."""
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """
    Write `text` to `path` crash-safely — same call shape as
    `Path.write_text()` (just with `path` as an explicit first
    argument instead of the receiver), so it's a drop-in replacement
    at every call site. A file named in core.at_rest.SEALED is written
    sealed (DEC-0126). A large shrink keeps the old file as its `.prev`,
    and the replace is retried while a reader holds the file (see the
    module's docstring). `path`'s parent directory must already exist
    (same requirement every existing call site already satisfies via
    its own `_DATA_DIR.mkdir(parents=True, exist_ok=True)` before
    calling this).
    """
    path = Path(path)
    from core.at_rest import seal_text

    text = seal_text(path, text)
    # "Undo that" (core/undo_log.py): keep the old contents while an
    # Assistant change is being recorded.
    from core.undo_log import before_write

    before_write(path)
    _keep_previous(path, len(text.encode(encoding)))
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        _replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    # Live updates (core/live.py): open screens re-read the state.
    from core import live

    live.bump()
