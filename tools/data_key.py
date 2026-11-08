"""
tools.data_key
================

MIA's data key for sealed files (DEC-0126, core/at_rest.py), from the command line on the PC:

    python -m tools.data_key               # whether sealing works here, and which files are sealed
    python -m tools.data_key recovery      # the recovery key: keep it in a password manager, never in a file
    python -m tools.data_key restore CODE  # take a recovery key back (a new Windows account, another PC)
    python -m tools.data_key seal          # seal every plain sealed-kind file now, not at its next save
    python -m tools.data_key seal --history  # with MIA closed: seal the history's lines from before 2026-11-08

`seal` walks data/ and every profile and household folder under it. `--history` rewrites each history
(life_events.jsonl) once, every line kept: the only time it's rewritten, so it refuses while MIA is open.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import Optional

from core import at_rest

DATA = at_rest.ROOT / "data"


def folders(data: Path = DATA) -> list[Path]:
    """data/ and each profile's and household's folder in it."""
    out = [data]
    for parent in (data / "profiles", data / "households"):
        if parent.is_dir():
            out += sorted(p for p in parent.iterdir() if p.is_dir() and not p.name.startswith("_deleted_"))
    return out


def mia_open(port: int = 8765) -> bool:
    """Whether MIA looks open on this PC: her server answering on its port (core/phone_server.py's default)."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def main(argv: Optional[list] = None) -> int:
    """Runs one command; 1 when it couldn't be done."""
    args = argv if argv is not None else sys.argv[1:]
    command = args[0] if args else "status"
    if command == "status":
        s = at_rest.status()
        print(("Sealing is on" if s["sealing"] else f"Sealing is off: {s['why_not']}") +
              (f" (key {s['key_id']}, protected by {s['protection']})" if s["sealing"] else ""))
        print("Sealed files: " + ", ".join(s["files"]))
        print("Sealed a line at a time: " + ", ".join(s.get("lines", [])))
        return 0 if s["sealing"] else 1
    if command == "recovery":
        try:
            print(at_rest.recovery_key())
        except ValueError as problem:
            print(f"No recovery key: {problem}")
            return 1
        print("Keep this in your password manager. With it your sealed files open on any computer; without it, only"
              " this Windows account opens them.")
        return 0
    if command == "restore" and len(args) > 1:
        try:
            print(f"Restored key {at_rest.restore(' '.join(args[1:]))}.")
        except ValueError as problem:
            print(f"Not restored: {problem}")
            return 1
        return 0
    if command == "seal" and "--history" in args[1:]:
        if mia_open():
            print("MIA looks open. Close her first: the history is never rewritten while she can add to it.")
            return 1
        print(f"Sealed the earlier lines of {at_rest.seal_history(folders())} histories.")
        return 0
    if command == "seal":
        print(f"Sealed {at_rest.seal_now(folders())} files.")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
