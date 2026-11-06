"""
core.loop_catalog
===================

The loops as built (DEC-0094, DEC-0101): `docs/LOOPS.md` is the code's own
list of every loop in `core/loops.py`, by area, with what it watches, its
floor, what it does when it slips and the processes it covers. It's
generated, never edited by hand, and `tests/test_loop_catalog.py` fails
when it falls behind the code, so the list can't drift the way a
hand-kept table does (`docs/IMPROVEMENT_LOOPS.md` keeps the design and the
reasons; this keeps what's there).

    python -m core.loop_catalog        rewrite docs/LOOPS.md
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTS = {"task": "opens a task", "offer": "offers it to them", "watch": "shown, never acted on"}


def render(loops=None) -> str:
    if loops is None:
        from core.loops import LOOPS as loops
    by_area: dict[str, list] = {}
    for loop in loops:
        by_area.setdefault(loop.area, []).append(loop)
    lines = ["# MIA's loops, as built", "",
             "*Generated from `core/loops.py` by `python -m core.loop_catalog`; never edit by hand (a test keeps it "
             "current). The design and the reasons: `docs/IMPROVEMENT_LOOPS.md`; what each process is watched by: "
             "`python -m tools.night_school coverage`.*", "",
             f"{len(loops)} loops in {len(by_area)} areas.", ""]
    for area in sorted(by_area):
        lines += [f"## {area.capitalize()}", "", "| Loop | Watches | Scope | Floor | When it slips | Covers |",
                  "|---|---|---|---|---|---|"]
        for loop in sorted(by_area[area], key=lambda l: l.id):
            floor = "trend" if loop.floor is None else f"{'≥' if loop.better == 'higher' else '≤'} {loop.floor:g}"
            if loop.min_n > 1:
                floor += f" (from {loop.min_n})"
            covers = ", ".join(f"`{c}`" for c in loop.covers[:6]) + (f" and {len(loop.covers) - 6} more"
                                                                     if len(loop.covers) > 6 else "")
            when = ACTS.get(loop.acts, loop.acts) + (", weekly" if loop.every == 7 else "") + \
                (", heavy" if loop.heavy else "")
            lines.append(f"| `{loop.id}` | {loop.what} | {loop.scope} | {floor} | {when} | {covers} |")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    (ROOT / "docs" / "LOOPS.md").write_text(render(), encoding="utf-8")
    print("docs/LOOPS.md written")
