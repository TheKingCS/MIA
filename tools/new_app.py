"""
tools.new_app
===============

MIA Forge's scaffold from the command line (core/app_scaffold.py, phase M7): a new app as a registered, empty screen.

    python -m tools.new_app seed_bank "Seed Bank" home --tagline "Every seed you've saved." --ask "What seeds do I have?"
    python -m tools.new_app seed_bank "Seed Bank" home --dry-run     # show what would be written, write nothing
    python -m tools.new_app seed_bank "Seed Bank" home --root ../MIA-lab/L-0042   # in a lab worktree

It prints each file it creates or changes and what's left to do. It gives the app no capabilities: those are added to
its manifest by whoever builds it, each with a tier. Run it in a lab worktree when MIA or another model is building
the app; it reaches the running MIA only by the lab's merge.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core import app_scaffold
from core.data_root import CODE_ROOT


def main(argv=None) -> int:
    """Parses the command line, scaffolds (or only plans, with --dry-run), and prints what happened; 1 on a refusal."""
    parser = argparse.ArgumentParser(prog="python -m tools.new_app", description="Scaffold a new MIA app.")
    parser.add_argument("id", help="snake_case id, e.g. seed_bank")
    parser.add_argument("name", help="the name people see")
    parser.add_argument("area", help="the web area it lives in (core/web_areas.py)")
    parser.add_argument("--tagline", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--ask", default="", help="an example of what to say to it")
    parser.add_argument("--icon", default="▫")
    parser.add_argument("--group", default=app_scaffold.GROUPS[-1], help="its group on the Apps page")
    parser.add_argument("--root", default=str(CODE_ROOT), help="the checkout to write into (a lab worktree)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    spec = app_scaffold.AppSpec(args.id, args.name, args.area, args.tagline, args.description, args.ask, args.icon,
                                args.group)
    try:
        made = (app_scaffold.plan if args.dry_run else app_scaffold.write)(spec, Path(args.root))
    except app_scaffold.ScaffoldError as problem:
        print(str(problem), file=sys.stderr)
        return 1
    verb = "Would" if args.dry_run else "Did"
    for path in made["create"]:
        print(f"{verb} create {path}")
    for path in made["change"]:
        print(f"{verb} change {path}")
    print("\nNext:")
    for step in made["next"]:
        print(f"- {step}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
