"""
tools.data_key
================

MIA's data key for sealed files (DEC-0126, core/at_rest.py), from the command line on the PC:

    python -m tools.data_key               # whether sealing works here, and which files are sealed
    python -m tools.data_key recovery      # the recovery key: keep it in a password manager, never in a file
    python -m tools.data_key restore       # take a recovery key back (a new Windows account, another PC, Linux);
                                           # it asks for the key without showing it (or: restore CODE)
    python -m tools.data_key protect       # Linux, once: make this machine's unlock secret (core/key_unlock.py),
                                           # which protects the data key the way the Windows sign-in does there
    python -m tools.data_key seal          # seal every plain sealed-kind file now, not at its next save
    python -m tools.data_key seal --history  # with MIA closed: seal the history's lines from before 2026-11-08

`restore` typed without the key keeps it out of the shell's history. `protect` is run by
`deploy/install_runtime.sh`; it never replaces a secret that's already there. `seal` walks data/ and every profile
and household folder under it. `--history` rewrites each history
(life_events.jsonl) once, every line kept: the only time it's rewritten, so it refuses while MIA is open.
"""

from __future__ import annotations

import getpass
import socket
import sys
from pathlib import Path
from typing import Optional

from core import at_rest
from core.data_root import DATA_DIR

DATA = DATA_DIR


def folders(data: Path = DATA) -> list[Path]:
    """data/ and each profile's and household's folder in it."""
    return at_rest.data_folders(data)


def protect() -> int:
    """`protect`: makes this machine's unlock secret on Linux (once), and says how the data key is protected."""
    from core import key_unlock

    if at_rest.dpapi_available():
        print("On Windows your sign-in protects the data key. There's nothing to set up.")
        return 0
    path = key_unlock.credential_file()
    if path.exists():
        secret, why = key_unlock.find_in_file()
        if secret is None:
            print(f"The unlock secret at {path} won't open: {why}.\nIt isn't replaced: the data key opens with it. "
                  f"If it's truly gone, move it away yourself, run this again, then: python -m tools.data_key restore")
            return 1
        print(f"This machine's unlock secret is already made ({path}).")
        return 0
    try:
        path = key_unlock.make()
    except key_unlock.UnlockError as problem:
        print(f"No unlock secret was made: {problem}")
        return 1
    print(f"Made this machine's unlock secret ({path}), kept encrypted by systemd for you on this machine, "
          + ("bound to its TPM chip." if key_unlock.has_tpm() else
             "with the machine's own key (it has no TPM chip: a drive read elsewhere isn't protected by this)."))
    print("Sealed files from another computer open once its recovery key is entered: python -m tools.data_key restore")
    return 0


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
              " this account on this computer opens them.")
        return 0
    if command == "restore":
        code = " ".join(args[1:]) or getpass.getpass("Recovery key (it won't show as you type or paste): ")
        try:
            print(f"Restored key {at_rest.restore(code)}.")
        except ValueError as problem:
            print(f"Not restored: {problem}")
            return 1
        stuck = at_rest.unopenable(folders())
        if stuck:
            print(f"{len(stuck)} sealed files still don't open with the keys held here (the first: {stuck[0]}). "
                  f"They were sealed with another key.")
            return 1
        return 0
    if command == "protect":
        return protect()
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
