"""
tools.css_colours
===================

Hard-coded colours in MIA's style sheets (prompt 24 phase A2, DEC-0184; `docs/mia_os/MIA_OS_APPEARANCE_ENGINE.md` D):
every colour belongs in `web/tokens.css`, so a theme or colour scheme can change it and high contrast can override it.
The ones written straight into the other sheets (a `#hex`, `rgb(` or `rgba(` with numbers, `hsl(`) are counted here;
each sheet's count may only go down (`work/css_colour_baseline.json`), and a new sheet starts at none.

    python -m tools.css_colours            # each sheet's count against the baseline
    python -m tools.css_colours baseline   # write the current counts as the new baseline (after removing some)

`rgba(var(--rgb-…), a)` is a token and isn't counted; neither is `tokens.css`, where values live.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
BASELINE = ROOT / "work" / "css_colour_baseline.json"
EXEMPT = {"tokens.css"}  # where the values live
_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(\s*\d|\bhsla?\(\s*\d")


def count(text: str) -> int:
    """Pure logic. How many hard-coded colours a style sheet has, comments left out."""
    return len(_LITERAL.findall(re.sub(r"/\*.*?\*/", "", text, flags=re.S)))


def counts(folder: Path = WEB) -> dict:
    """Each style sheet's count ({name: n}), the token file left out."""
    return {p.name: count(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.css")) if p.name not in EXEMPT}


def problems(folder: Path = WEB, baseline: Path = BASELINE) -> list[str]:
    """The sheets with more hard-coded colours than their baseline (a sheet not in it has a baseline of none)."""
    allowed = json.loads(baseline.read_text(encoding="utf-8")) if baseline.exists() else {}
    return [f"web/{name}: {n} hard-coded colours, more than its {allowed.get(name, 0)}; use a token from web/tokens.css"
            for name, n in counts(folder).items() if n > allowed.get(name, 0)]


def main(argv: Optional[list] = None) -> int:
    """`baseline` writes the current counts; otherwise prints each sheet's count and any over its baseline."""
    args = argv if argv is not None else sys.argv[1:]
    now = counts()
    if args[:1] == ["baseline"]:
        BASELINE.write_text(json.dumps(now, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"{BASELINE.relative_to(ROOT)} written: {sum(now.values())} in {len(now)} sheets")
        return 0
    for name, n in now.items():
        print(f"{name}: {n}")
    found = problems()
    for p in found:
        print(p)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
