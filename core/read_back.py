"""
core.read_back
==============

Done means read back (DEC-0218, LS-05): after a change runs, code reads its effect back instead of trusting the report
that it worked. One generic check for every change (docs/mia_os/MIA_UNIVERSAL_RUNTIME_CONTRACTS.md section 2):

- each file it wrote still holds the bytes it left there (core/undo_log.py keeps their hash as it writes);
- each record its history names (a `kind:id` ref on its life events) still resolves through the record-type registry
  (core/record_types.py), unless the change removed it.

A kind that can't be read by id yet (`record_types.HISTORY_ONLY`), or whose store isn't on this view, is skipped, so
the read-back never claims more than it can see. A capability-specific check (a device's state, a page committed)
belongs to that capability.

Pure reads: nothing here writes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REMOVING = ("_removed", "_deleted", "_cancelled", "_archived", "_merged", "_discarded", "_undone")


def _removes(event_type: str) -> bool:
    """Whether a life event's type says a record went away (its ref isn't expected to resolve)."""
    return str(event_type or "").endswith(REMOVING)


def check(context, change) -> list[str]:
    """What didn't read back after a change, in plain words; [] when everything it says it did is there."""
    from core import record_types

    problems = []
    for path, digest in (getattr(change, "wrote", None) or {}).items():
        path = Path(path)
        try:
            now = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            problems.append(f"{path.name} isn't there")
            continue
        if digest and now != digest:
            problems.append(f"{path.name} doesn't hold what was written")
    touched = list(getattr(change, "touched", None) or [])
    gone = {ref for kind, refs in touched if _removes(kind) for ref in refs}
    for _type, refs in touched:
        for ref in refs:
            kind = str(ref).partition(":")[0]
            if ref in gone or not record_types.readable(context, kind):
                continue
            if record_types.read(context, ref) is None:
                problems.append(f"{ref} doesn't read back")
    return sorted(set(problems))
