"""
core.system_map
=================

One map of everything that makes MIA (Zac, 2026-11-08: "everything she learns and does needs to be organized and
categorized and mapped into a distinguishable map of the total system architecture, capabilities, decisions, loops,
user preferences, etc… so MIA and everything that makes her is easy to understand").

The pieces already exist, but scattered — the code atlas, the decisions log, the loops catalogue, the dev-knowledge she
writes as she's built, her night-school learnings, the stores she keeps, the person's style preferences. This module
gathers them into one categorized picture (`assemble()`) and renders it to `docs/MIA_MAP.md` (`main()`), so there's a
single place that answers "what is MIA, and what is she made of?" — and it regenerates as she grows.

    python -m core.system_map            # rewrite docs/MIA_MAP.md
    python -m core.system_map --print    # print it instead

Every source is read defensively: one that can't be read becomes a noted gap, never a crash, so the map always renders.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "docs" / "MIA_MAP.md"


def _safe(fn, default):
    """Run a source reader; on any failure return `default` so the map always assembles."""
    try:
        return fn()
    except Exception:  # noqa: BLE001 - a broken source is a gap in the map, never a crash
        return default


def decisions() -> list[dict]:
    """Every decision (DEC-NNNN): id, title and status, from docs/DECISIONS.md."""
    text = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"^### (DEC-\d+): (.+?)$\n(?:- Status: (.+?)$)?", text, re.M):
        out.append({"id": m.group(1), "title": m.group(2).strip(),
                    "status": (m.group(3) or "").strip().split(" ")[0].rstrip(".,") or "—"})
    return out


def loops() -> dict:
    """How many improvement loops MIA runs, and how many processes are deliberately left without one."""
    import json

    from core import loops as loops_mod

    from collections import Counter

    decided = _safe(lambda: json.loads((ROOT / "work" / "loop_coverage.json").read_text("utf-8")), {})
    registry = getattr(loops_mod, "LOOPS", ())
    return {"active": len(registry),
            "by_area": dict(Counter(getattr(l, "area", "?") for l in registry)),
            "decided_without": len([k for k, v in decided.items() if isinstance(v, dict)])}


def knowledge() -> dict:
    """The dev-knowledge entries MIA has written about building herself, grouped by kind."""
    from collections import Counter

    from core import dev_knowledge

    items = dev_knowledge.entries()
    return {"total": len(items), "by_kind": dict(Counter(e.get("kind", "?") for e in items))}


def learnings() -> dict:
    """What night school has studied: how many nights, and the latest report card if any."""
    from core import night_school

    nights = night_school.nights()
    card = _safe(night_school.report_card, {})
    return {"nights": len(nights), "report": {k: card.get(k) for k in ("passed", "failed", "studied") if k in (card or {})}}


def stores() -> dict:
    """What MIA keeps: how many personal and household stores, and how many are sealed at rest."""
    from core import at_rest, personal_data

    return {"personal": len(getattr(personal_data, "PERSONAL_STORES", ())),
            "household": len(getattr(personal_data, "HOUSEHOLD_STORES", ())),
            "sealed": len(getattr(at_rest, "SEALED", ()))}


def capabilities() -> dict:
    """Roughly how many Assistant tools/capabilities, from docs/ASSISTANT_CAPABILITIES.md."""
    text = (ROOT / "docs" / "ASSISTANT_CAPABILITIES.md").read_text(encoding="utf-8")
    tokens = set(re.findall(r"`([a-z][a-z0-9_]+(?:\.[a-z0-9_]+)?)`", text))
    tools = {t for t in tokens if "_" in t or "." in t}  # tool ids look like get_calendar or maintenance.done
    return {"tools": len(tools)}


def architecture() -> dict:
    """The layered codebase: how many Python files in each layer."""
    def count(folder: str) -> int:
        here = ROOT / folder
        return sum(1 for p in here.rglob("*.py") if "__pycache__" not in p.parts) if here.is_dir() else 0

    return {layer: count(layer) for layer in ("core", "modules", "gui", "server", "tools")}


def preferences() -> dict:
    """How the person can shape MIA: the answer-style dimensions she learns (DEC-0138) and settings."""
    from core.response_style import DIMENSIONS

    return {"style_dimensions": {d: list(opts) for d, opts in DIMENSIONS.items()}}


def assemble() -> dict:
    """The whole categorized map of MIA."""
    return {
        "architecture": _safe(architecture, {}),
        "decisions": _safe(decisions, []),
        "capabilities": _safe(capabilities, {}),
        "loops": _safe(loops, {}),
        "knowledge": _safe(knowledge, {}),
        "learnings": _safe(learnings, {}),
        "stores": _safe(stores, {}),
        "preferences": _safe(preferences, {}),
    }


def render(data: Optional[dict] = None) -> str:
    """The map as Markdown — one navigable page, a section per category, newest decisions last."""
    data = data or assemble()
    arch = data["architecture"]
    decs = data["decisions"]
    lines = ["# MIA — the map of everything that makes her",
             "",
             "*Generated by `python -m core.system_map` from the code, the decisions, the loops, her knowledge and "
             "learnings, her stores and the person's preferences. One place to understand what MIA is.*",
             "",
             "## At a glance",
             "",
             f"- **Architecture** — {sum(arch.values())} Python files across "
             + ", ".join(f"{n} {layer}" for layer, n in arch.items() if n) + " (strict one-way layering; see docs/ARCHITECTURE.md).",
             f"- **Decisions** — {len(decs)} logged (docs/DECISIONS.md); the why behind every part.",
             f"- **Capabilities** — ~{data['capabilities'].get('tools', '?')} Assistant tools "
             "(docs/ASSISTANT_CAPABILITIES.md).",
             f"- **Improvement loops** — {data['loops'].get('active', '?')} active, "
             f"{data['loops'].get('decided_without', '?')} processes decided to need none (docs/LOOPS.md).",
             f"- **Knowledge she's written** — {data['knowledge'].get('total', '?')} dev entries (work/knowledge/).",
             f"- **Night-school learnings** — {data['learnings'].get('nights', '?')} nights studied.",
             f"- **What she keeps** — {data['stores'].get('personal', '?')} personal + "
             f"{data['stores'].get('household', '?')} household stores, {data['stores'].get('sealed', '?')} sealed at rest.",
             f"- **How you shape her** — {len(data['preferences'].get('style_dimensions', {}))} answer-style dimensions "
             "she learns from your picks (DEC-0138).",
             ""]

    lines += ["## Decisions — why MIA is built the way she is", ""]
    by_status: dict[str, list] = {}
    for d in decs:
        by_status.setdefault(d["status"], []).append(d)
    for status in sorted(by_status):
        lines.append(f"**{status}** ({len(by_status[status])}): "
                     + ", ".join(d["id"] for d in by_status[status]))
    lines += ["", "<details><summary>Every decision</summary>", ""]
    lines += [f"- **{d['id']}** [{d['status']}] — {d['title']}" for d in decs]
    lines += ["", "</details>", ""]

    lines += ["## How she improves", "",
              f"- **{data['loops'].get('active', '?')} improvement loops** watch her processes (docs/LOOPS.md, "
              "DEC-0094/0101) — Observe → Measure → Evaluate → Improve → Verify.",
              f"- **Night school** (DEC-0100) — {data['learnings'].get('nights', '?')} nights spent studying how to "
              "build herself; what went right and wrong is written back as knowledge.",
              f"- **Dev-knowledge** — {data['knowledge'].get('total', '?')} entries "
              + (", ".join(f"{n} {k}" for k, n in data['knowledge'].get('by_kind', {}).items()) or "") + ".",
              ""]

    lines += ["## What she keeps, and how it's protected", "",
              f"- {data['stores'].get('personal', '?')} personal stores (each person's own) and "
              f"{data['stores'].get('household', '?')} household stores.",
              f"- {data['stores'].get('sealed', '?')} of them are **sealed at rest** (DEC-0126) — encrypted on disk, "
              "the real/fictional boundary kept separate (DEC-0137).",
              ""]

    lines += ["## How you shape her", "",
              "MIA learns the way you like to be answered (DEC-0138), across:",
              ""]
    lines += [f"- **{dim}** — {' / '.join(opts)}" for dim, opts in data['preferences'].get('style_dimensions', {}).items()]
    lines += ["", "*The map of the map: this file is generated; the detail lives in docs/ATLAS.md (code), "
              "docs/DECISIONS.md (why), docs/LOOPS.md (improvement), work/knowledge/ (what she learned building).*", ""]
    return "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    """Rewrite docs/MIA_MAP.md (or --print it)."""
    args = argv if argv is not None else sys.argv[1:]
    text = render()
    if "--print" in args:
        print(text)
    else:
        MAP_FILE.write_text(text, encoding="utf-8")
        print(f"Wrote {MAP_FILE.relative_to(ROOT)} ({len(text.splitlines())} lines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
