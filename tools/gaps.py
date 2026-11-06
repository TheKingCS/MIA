"""
tools.gaps
============

The PC owner's capability gaps (core/capability_gaps.py, build plan step 9):
what MIA was asked and couldn't do, grouped, with what each would take. The
requests are the person's own words, so they're read here, on this PC, and
never copied into the repo.

    python -m tools.gaps            every gap, most asked first
    python -m tools.gaps show G-0001
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    from core import capability_gaps
    from tools.intelligence_check import build_context

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    context = build_context()
    gaps = capability_gaps.refresh(context)
    if argv[:1] == ["show"] and len(argv) > 1:
        gap = capability_gaps.get(context, argv[1].upper())
        if gap is None:
            print(f"No gap {argv[1]}.")
            return 1
        print(f"{gap['id']} [{gap['status']}] asked {gap['count']} times ({gap['first'][:10]} to {gap.get('last', '')[:10]})")
        print(f"Needs: {gap['need']}: {gap['what']}" + (f" (task {gap['task']})" if gap.get("task") else ""))
        for example in gap["examples"]:
            print(f"  - {example}")
        return 0
    for gap in sorted(gaps, key=lambda g: -g["count"]):
        print(f"{gap['id']}  {gap['count']:3}x  {gap['need']:8} {gap['status']:9} {gap['examples'][-1][:70]}")
    if not gaps:
        print("No gaps: nothing asked that she couldn't match.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
