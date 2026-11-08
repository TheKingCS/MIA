"""
tools.fix_report
==================

The Fix-It Log's daily report (core/failure_log.py, DEC-0049), for Claude on
the PC: each person's open issues, worst first, with examples and the test to
write first. The report is sealed on disk like the log it comes from
(DEC-0126), so it's read through this, never opened as a file:

    .venv\\Scripts\\python -m tools.fix_report             (every person's)
    .venv\\Scripts\\python -m tools.fix_report <profile>   (one person's folder name)

It only reads. Personal: never paste it into the repo; turn each issue into a
test, not a copy of its words.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def reports(profile: str = "", root: Path = ROOT) -> list[tuple[str, str]]:
    """Each person's fix report as (their folder's name, its text), opened whatever way it's kept; a report that
    won't open says so instead."""
    from core.at_rest import open_text

    out = []
    for path in sorted((root / "data" / "profiles").glob("*/fix_report.md")):
        if profile and path.parent.name != profile:
            continue
        try:
            out.append((path.parent.name, open_text(path)))
        except (OSError, ValueError) as problem:
            out.append((path.parent.name, f"(the report won't open here: {problem})"))
    return out


def main(argv=None) -> int:
    """Prints the reports (one person's when a folder name is given). Returns the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    found = reports(args[0] if args else "")
    if not found:
        print("No fix report yet: MIA writes one a day when the Fix-It Log has open issues.")
        return 0
    for name, text in found:
        print(f"===== {name} =====\n{text.strip()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
