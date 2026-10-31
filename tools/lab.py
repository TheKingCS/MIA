"""
tools.lab
===========

MIA's development lab from the command line (DEC-0058, core/dev_lab.py).

    python -m tools.lab list
    python -m tools.lab propose "Title" "The problem" ["evidence"] ["plan"]   (lab, write, check)
    python -m tools.lab check <id>
    python -m tools.lab approve <id>      (Zac: merge into the running copy, suite, revert on a new failure)
    python -m tools.lab reject <id> ["why"]
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    from core import dev_lab

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not argv or argv[0] == "list":
        for p in dev_lab.all_proposals():
            print(f"{p.proposal_id}  {dev_lab.describe(p)}")
        return 0
    command, rest = argv[0], argv[1:]
    try:
        if command == "propose":
            p = dev_lab.create(*rest[:4])
            print(f"Lab {p.proposal_id} at {dev_lab.folder(p)}; Claude Code is writing it...", flush=True)
            p = dev_lab.write(p.proposal_id)
            print(p.coder_said or "(no summary)", flush=True)
            if p.status == dev_lab.WRITTEN:
                print("Checking: the rules, then the suite in the lab and at the start...", flush=True)
                p = dev_lab.check(p.proposal_id)
        elif command == "check":
            p = dev_lab.check(rest[0])
        elif command == "approve":
            p = dev_lab.approve(rest[0])
        elif command == "reject":
            p = dev_lab.reject(rest[0], rest[1] if len(rest) > 1 else "")
        else:
            print(__doc__)
            return 2
    except (ValueError, RuntimeError, IndexError) as exc:
        print(f"Couldn't: {exc}")
        return 1
    print(dev_lab.describe(p))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
