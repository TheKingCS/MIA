"""
tools.night_school
====================

Night School from the command line (DEC-0100, core/night_school.py).

    python -m tools.night_school            the latest night, her report card and how her choosing is going
    python -m tools.night_school run        a night now (MIA's daily check starts one at 01:30 by itself)
    python -m tools.night_school plan       what she'd study tonight and why, without running anything
    python -m tools.night_school coverage   which processes have a loop, and which don't yet (DEC-0101)
    python -m tools.night_school curriculum where she stands in each area of computing (DEC-0107)
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    """Runs one command (the latest night by default)."""
    from core import loop_coverage, loops, night_school

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    command = argv[0] if argv else "report"
    if command == "run":
        print(night_school.describe(night_school.night()), flush=True)
        return 0
    if command == "plan":
        from core import dev_ledger

        cfg = night_school.settings()
        step = night_school.plan_step()
        print(f"Mode: {cfg['mode']}. Starts at {cfg['start']} for {cfg['hours']:g} hours.")
        print(f"The plan's next step: {step['number']}. {step['title']}" if step else "The plan has no step left.")
        areas = night_school.self_assessment(loops.summary(None, "device"),
                                             dev_ledger.ledger().get("ollama-coder", {}), night_school.report_card(),
                                             loop_coverage.report()["counts"].get("todo", 0))
        print("What she'd choose:")
        for a in areas[:8]:
            print(f"  {a['area']}: {a['why']}")
        return 0
    if command == "curriculum":
        from core import curriculum

        rows = curriculum.progress(l for n in night_school.nights() for l in n.get("lessons", []))
        for s in curriculum.standing(rows):
            print(f"{s['name']}: {s['mastered']} of {s['of']} mastered (level: {s['level']})")
        nxt = curriculum.next_objective(rows)
        print(f"Next: {nxt.id}, she can {nxt.can}." if nxt else "Every objective is mastered.")
        return 0
    if command == "coverage":
        r = loop_coverage.report()
        print(f"{r['total']} processes: " + ", ".join(f"{n} {s}" for s, n in sorted(r["counts"].items()))
              + f"; {r['share']:.0%} of those that need a loop have one.")
        for row in r["rows"]:
            if row["state"] in ("new", "proposed") or "-v" in argv:
                print(f"  [{row['state']}] {row['id']}: {row['what']}"
                      + (f" ({', '.join(row['loops'])})" if row["loops"] else "") + (f" {row['task']}" if row["task"] else ""))
        return 0
    if command == "report":
        last = night_school.nights()
        print(night_school.describe(last[-1]) if last else "No night of school yet.")
        card = night_school.report_card()
        if card:
            print("Report card: " + "; ".join(f"{s} {r['passed']}/{r['lessons']}" for s, r in card.items()))
        c = night_school.choosing()
        print(f"Her own picks matched her teacher's {c['agreed']} of {c['nights']} nights"
              + (" - the evidence supports letting her choose (set \"mode\": \"self\" in work/night_school.json)."
                 if c["ready"] else "."))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
