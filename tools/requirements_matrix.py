"""
tools.requirements_matrix
===========================

Writes MIA OS's requirements traceability matrix (Prompt 04, deliverable 11;
`docs/mia_os/MIA_OS_SYSTEM_REQUIREMENTS.md` §1) from the requirement tables themselves, so it can't drift from them:

    python -m tools.requirements_matrix          # writes docs/mia_os/MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md
    python -m tools.requirements_matrix check    # problems only, nothing written

**What it reads.** Every table row in `SPEC_DOCS` that starts `| REQ-`, in the specification's eight columns (ID,
requirement, priority, tier, devices, status, verify, trace), and the "Exercises:" lines of the user scenarios.

**What it checks** (`problems`): each ID well formed and defined once; eight cells; a known priority, tier and status
(the status's first word); a trace with an arrow to at least one owner prompt; a scenario naming only IDs that exist.

**What it writes.** Counts by status, tier and owner; every requirement with its sources, owners, the scenarios that
exercise it, the other requirements it names, and how it's verified; the Must requirements still New or Planned for the
MVP (the work list); and the requirements with no owner yet.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
OS_DOCS = ROOT / "docs" / "mia_os"
SPEC_DOCS = ("MIA_OS_SYSTEM_REQUIREMENTS.md", "MIA_OS_FUNCTIONAL_REQUIREMENTS.md", "MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md",
             "MIA_OS_USER_EXPERIENCE_REQUIREMENTS.md", "MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md",
             "MIA_OS_DEVICE_AND_HARDWARE_REQUIREMENTS.md", "MIA_OS_RELIABILITY_AND_DEGRADATION_REQUIREMENTS.md",
             # Prompt 06's hardware requirements (REQ-HW-007 to 031), in the documents that justify them
             "MIA_OS_DESKTOP_HARDWARE_REQUIREMENTS.md",
             "MIA_OS_CPU_AND_ARCHITECTURE_EVALUATION.md",
             "MIA_OS_GPU_AND_AI_ACCELERATION_STRATEGY.md",
             "MIA_OS_MEMORY_AND_STORAGE_REQUIREMENTS.md",
             "MIA_OS_ANDROID_HARDWARE_INTEGRATION.md",
             "MIA_OS_WEARABLE_AND_SPATIAL_HARDWARE.md",
             "MIA_OS_EMBEDDED_AND_HOMESTEAD_HARDWARE.md",
             "MIA_OS_PERIPHERAL_COMPATIBILITY.md",
             "MIA_OS_NETWORK_AND_DISTRIBUTED_HARDWARE.md",
             "MIA_OS_VIRTUALIZATION_AND_ISOLATION.md",
             "MIA_OS_POWER_THERMAL_AND_HARDWARE_HEALTH.md",
             "MIA_OS_HARDWARE_DISCOVERY_AND_CAPABILITY_REGISTRY.md",
             "MIA_OS_HARDWARE_RESOURCE_COORDINATION.md",
             "MIA_OS_HARDWARE_FAILURE_AND_DEGRADED_OPERATION.md")
SCENARIOS = "MIA_OS_USER_SCENARIOS.md"
MATRIX = OS_DOCS / "MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md"
PRIORITIES = ("Must", "Should", "Could", "Won't")
TIERS = ("MVP", "R1", "Mature", "Later")
STATUSES = ("Exists", "Partial", "Planned", "New")
_ID = re.compile(r"REQ-[A-Z]{2,3}-\d{3}")


def _cells(line: str) -> list[str]:
    """A markdown table row's cells, trimmed (a pipe inside backticks is not expected in these tables)."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read(folder: Path = OS_DOCS) -> tuple[list[dict], dict, list[str]]:
    """Every requirement row ({id, doc, text, pri, tier, dev, status, verify, sources, owners}), the scenarios that
    exercise each ID ({id: [S-nn]}), and what couldn't be read."""
    rows, problems = [], []
    for name in SPEC_DOCS:
        path = folder / name
        if not path.exists():
            problems.append(f"{name} is missing")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| REQ-"):
                continue
            cells = _cells(line)
            if len(cells) != 8:
                problems.append(f"{cells[0]}: {len(cells)} cells, not 8")
                continue
            rid, text, pri, tier, dev, status, verify, trace = cells
            sources, _, owners = trace.partition("→")
            rows.append({"id": rid, "doc": name, "text": text, "pri": pri, "tier": tier, "dev": dev,
                         "status": status, "verify": verify, "sources": sources.strip(), "owners": owners.strip(),
                         "arrow": "→" in trace})
    exercised: dict = defaultdict(list)
    path = folder / SCENARIOS
    scenario = ""
    for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
        m = re.match(r"### (S-\d+)", line)
        if m:
            scenario = m.group(1)
        if "Exercises:" in line and scenario:
            for rid in _ID.findall(line):
                exercised[rid].append(scenario)
    return rows, dict(exercised), problems


def problems(folder: Path = OS_DOCS) -> list[str]:
    """What's wrong with the requirement tables (see the module's opening); [] when they're sound."""
    rows, exercised, out = read(folder)
    seen = Counter(r["id"] for r in rows)
    out += [f"{rid} is defined {n} times" for rid, n in sorted(seen.items()) if n > 1]
    for r in rows:
        if not _ID.fullmatch(r["id"]):
            out.append(f"{r['id']}: not an ID like REQ-ABC-001")
        if r["pri"] not in PRIORITIES:
            out.append(f"{r['id']}: priority {r['pri']!r}")
        if r["tier"] not in TIERS:
            out.append(f"{r['id']}: tier {r['tier']!r}")
        if r["status"].split(" ")[0].rstrip(":(") not in STATUSES:
            out.append(f"{r['id']}: status {r['status']!r}")
        if not r["arrow"] or not re.search(r"\d\d|all", r["owners"]):
            out.append(f"{r['id']}: its trace names no owner prompt after →")
    known = set(seen)
    for rid, scenarios in sorted(exercised.items()):
        if rid not in known:
            out.append(f"{', '.join(scenarios)} exercise {rid}, which isn't defined")
    return out


def render(folder: Path = OS_DOCS) -> str:
    """The matrix document (see the module's opening)."""
    rows, exercised, _ = read(folder)
    ids = {r["id"] for r in rows}
    status = Counter(r["status"].split(" ")[0].rstrip(":(") for r in rows)
    tier = Counter(r["tier"] for r in rows)
    owner = Counter(o for r in rows for o in re.findall(r"\b\d\d\b|\ball\b", r["owners"]))
    out = ["# MIA OS: requirements traceability matrix (Prompt 04, deliverable 11)", "",
           "*Generated by `python -m tools.requirements_matrix` from the requirement tables; don't edit by hand. "
           "`tests/test_requirements_spec.py` fails when it's out of date or a row is malformed. Fields are explained in "
           "[MIA_OS_SYSTEM_REQUIREMENTS.md](MIA_OS_SYSTEM_REQUIREMENTS.md) §1.*", "",
           f"**{len(rows)} requirements.** "
           + "; ".join(f"{k}: {status[k]}" for k in STATUSES) + ". "
           + "; ".join(f"{k}: {tier[k]}" for k in TIERS) + ".", "",
           "**By owner prompt:** " + ", ".join(f"{o} ({n})" for o, n in sorted(owner.items())) + ".", "",
           "## The MVP's remaining work (Must · MVP, not yet built)", "",
           "| ID | Requirement | Status | Owner |", "|---|---|---|---|"]
    for r in rows:
        if r["pri"] == "Must" and r["tier"] == "MVP" and r["status"].split(" ")[0].rstrip(":(") in ("New", "Planned", "Partial"):
            out.append(f"| {r['id']} | {r['text']} | {r['status']} | {r['owners']} |")
    out += ["", "## Every requirement", "",
            "| ID | Pri | Tier | Status | Sources | Owner | Scenarios | Names | Verify | Defined in |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["id"]):
        names = sorted((set(_ID.findall(r["text"] + " " + r["sources"])) & ids) - {r["id"]})
        out.append(f"| {r['id']} | {r['pri']} | {r['tier']} | {r['status'].split(' ')[0].rstrip(':(')} | {r['sources']} "
                   f"| {r['owners']} | {', '.join(exercised.get(r['id'], [])) or '—'} | {', '.join(names) or '—'} "
                   f"| {r['verify']} | {r['doc'].removeprefix('MIA_OS_').removesuffix('.md')} |")
    unowned = [r["id"] for r in rows if not re.search(r"\d\d|all", r["owners"])]
    out += ["", "## Not yet assignable", "",
            ("Every requirement names an owner prompt. Those whose evaluation waits on an unresolved question are in "
             "[MIA_OS_REQUIREMENTS_OPEN_QUESTIONS.md](MIA_OS_REQUIREMENTS_OPEN_QUESTIONS.md) §4.") if not unowned
            else "No owner yet: " + ", ".join(unowned), ""]
    return "\n".join(out)


def main(argv: Optional[list] = None) -> int:
    """`check` prints the problems; otherwise writes the matrix. 1 when there are problems."""
    args = argv if argv is not None else sys.argv[1:]
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # a Windows console can't print every character in a requirement
    found = problems()
    for p in found:
        print(p)
    if args[:1] == ["check"]:
        return 1 if found else 0
    MATRIX.write_text(render(), encoding="utf-8", newline="\n")
    print(f"{MATRIX.relative_to(ROOT)} written")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
