"""
core.specialist_roster
========================

The specialists' roster and the "counts as added" bar, in code (the Specialist Forge, F1; DEC-0199;
`docs/mia_os/MIA_OS_LOCAL_SPECIALISTS_PLAN.md` section 7: "a name with a paragraph is not a specialist").

**The bar** (`check`), for every specialist in `core/specialists.py`:
- a charter, limits, the words that route questions to it, and at least two starter questions for Night School;
- an agent role (department, task types, tools: DEC-0198), and the caveat wherever its department is one whose work
  can hurt someone (`SAFETY_DEPARTMENTS`);
- for one whose answers rest on figures (a worksheet, `core/specialist_work.DISCIPLINES`): for each of its
  disciplines, calculators (`core/eng_calcs.py`) and at least `MIN_TASKS` bench tasks (`core/eng_bench.py`), one of
  them leaving an input out (the right answer is a question, never a guess);
- and, for those, a local model that passed its bench (`core/specialist_models.py`).

A specialist that works from notes rather than figures (strategy, research, music...) needs only the first two.

**Its standing** (`roster`): *added* (everything above), *built, not passing* (everything but a model that passes),
*in progress* (what's missing, each in words), or *planned* (`PLANNED`: the specialists the teams handoff names that
don't exist yet, in the order Zac's projects need them, so the list can't quietly stall).

Everything is read from the code and the bench's results; nothing here is a model's opinion.
"""

from __future__ import annotations

from typing import Optional

MIN_TASKS = 3
MIN_STARTERS = 2
ADDED, NOT_PASSING, IN_PROGRESS, PLANNED_STATUS = "added", "built, not passing", "in progress", "planned"

# The specialists the teams handoff names (docs/mia_os/prompts/25_SPECIALIZED_AGENT_TEAMS.md) that MIA doesn't have
# yet, as (id, name, department), roughly in the order his projects call for them (DEC-0198). The Forge takes them
# from the top; one that's built moves from here into core/specialists.py.
PLANNED: tuple[tuple[str, str, str], ...] = (
    ("iot", "IoT and sensors", "engineering"),
    ("water_systems", "Water systems and irrigation", "homestead"),
    ("aquaponics", "Aquaponics", "homestead"),
    ("energy", "Energy systems (solar and storage)", "engineering"),
    ("mechanical", "Mechanical engineering", "engineering"),
    ("materials", "Materials", "engineering"),
    ("pcb", "PCB design", "engineering"),
    ("industrial_design", "Industrial design", "design"),
    ("printing_3d", "3D printing", "fabrication"),
    ("cnc_laser", "CNC and laser fabrication", "fabrication"),
    ("quality", "Quality control", "fabrication"),
    ("sourcing", "Sourcing and supply", "business"),
    ("finance", "Financial analysis", "business"),
    ("product", "Product management", "business"),
    ("marketing", "Marketing", "business"),
    ("legal_research", "Legal and compliance research", "business"),
    ("smart_home", "Smart home", "engineering"),
    ("agriculture", "Agriculture and crops", "homestead"),
    ("property", "Property research", "business"),
    ("robotics", "Robotics", "engineering"),
    ("systems", "Systems engineering", "engineering"),
    ("security", "Cybersecurity", "software"),
    ("ui_ux", "UI and UX design", "design"),
    ("graphics", "Graphic design", "design"),
    ("fashion", "Fashion and garments", "design"),
    ("patents", "Patents and prior art", "research"),
    ("market", "Market intelligence", "research"),
    ("verification", "Fact verification", "research"),
)


def check(spec, role: Optional[dict] = None, disciplines: tuple = (), calculators=None, tasks=None,
          model=None) -> list[str]:
    """Pure logic. What one specialist lacks against the bar, each in words ([] when it meets it). `disciplines` are
    its worksheet's (empty: it works from notes); `calculators` and `tasks` the whole sets; `model` its chosen model
    (core/specialist_models.Choice), only asked about when everything else is there."""
    from core.specialists import SAFETY_DEPARTMENTS

    missing = []
    if not (spec.charter or "").strip():
        missing.append("a charter")
    if not (spec.limits or "").strip():
        missing.append("its limits")
    if not spec.words:
        missing.append("the words that route questions to it")
    if len(spec.starts_from) < MIN_STARTERS:
        missing.append(f"at least {MIN_STARTERS} starter questions")
    if not role:
        missing.append("an agent role (department, task types, tools)")
    elif getattr(spec, "department", role.get("department")) in SAFETY_DEPARTMENTS and not getattr(spec, "caveat", ""):
        missing.append("the caveat its kind of work needs")
    for d in disciplines:
        mine = [c for c in (calculators or ()) if c.discipline == d]
        if not mine:
            missing.append(f"calculators for {d.replace('_', ' ')}")
            continue
        ids = {c.id for c in mine}
        bench = [t for t in (tasks or ()) if t.calculator in ids]
        if len(bench) < MIN_TASKS:
            missing.append(f"at least {MIN_TASKS} bench tasks for {d.replace('_', ' ')} (has {len(bench)})")
        elif not any(t.missing for t in bench):
            missing.append(f"a bench task for {d.replace('_', ' ')} that leaves an input out")
    return missing


def standing(missing: list[str], disciplines: tuple, model) -> str:
    """Pure logic. Where a specialist stands: added, built not passing, or in progress."""
    if missing:
        return IN_PROGRESS
    if disciplines and not (model is not None and model.passed):
        return NOT_PASSING
    return ADDED


def _inspection(specialist: str, results: dict) -> str:
    """Claude's verdict on the specialist's chosen model on these results: "pass", "hold", or "" (not yet)."""
    from core import model_inspection

    _c, _d, print_ = model_inspection._choice(specialist, results)
    found = model_inspection.latest(specialist, print_) if print_ else None
    return found["verdict"] if found else ""


def roster(results: Optional[dict] = None) -> dict:
    """Every specialist with its standing and what it lacks, and the planned ones: {"specialists": [{id, name,
    department, status, missing, model, passed, inspected, why, calculators, tasks}], "planned": [...], "counts":
    {...}}. `inspected` is Claude's verdict on its model (DEC-0200): "pass", "hold" or "" (not yet)."""
    from core import eng_bench, eng_calcs, specialist_models
    from core.specialist_work import DISCIPLINES
    from core.specialists import ROLES, SPECIALISTS

    results = specialist_models.load() if results is None else results
    rows = []
    for spec in SPECIALISTS:
        disciplines = DISCIPLINES.get(spec.id, ())
        model = specialist_models.choose(spec.id, results) if disciplines else None
        missing = check(spec, ROLES.get(spec.id), disciplines, eng_calcs.CALCULATORS, eng_bench.TASKS, model)
        ids = {c.id for c in eng_calcs.CALCULATORS if c.discipline in disciplines}
        rows.append({"id": spec.id, "name": spec.name, "department": getattr(spec, "department", ""),
                     "status": standing(missing, disciplines, model), "missing": missing,
                     "disciplines": [d.replace("_", " ") for d in disciplines],
                     "calculators": len(ids), "tasks": sum(1 for t in eng_bench.TASKS if t.calculator in ids),
                     "model": model.model if model else "", "passed": bool(model and model.passed),
                     "inspected": _inspection(spec.id, results) if model and model.model else "",
                     "why": model.why if model else "works from its notes; no figures to bench"})
    have = {s.id for s in SPECIALISTS}
    planned = [{"id": i, "name": n, "department": d, "status": PLANNED_STATUS} for i, n, d in PLANNED if i not in have]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in (ADDED, NOT_PASSING, IN_PROGRESS)}
    counts[PLANNED_STATUS] = len(planned)
    return {"specialists": rows, "planned": planned, "counts": counts}


def said(results: Optional[dict] = None) -> str:
    """The roster in words, for voice: how many are added, which aren't passing or are in progress and why, and
    what's next on the planned list."""
    r = roster(results)
    c = r["counts"]
    lines = [f"{c[ADDED]} specialists are added, {c[NOT_PASSING]} built but not passing their bench, "
             f"{c[IN_PROGRESS]} in progress, and {c[PLANNED_STATUS]} planned."]
    for row in r["specialists"]:
        if row["status"] == NOT_PASSING:
            lines.append(f"{row['name']}: built, but no model on this computer passes its bench yet ({row['why']}).")
        elif row["status"] == IN_PROGRESS:
            lines.append(f"{row['name']} still needs " + ", ".join(row["missing"][:3]) + ".")
    if r["planned"]:
        lines.append("Next planned: " + ", ".join(p["name"] for p in r["planned"][:3]) + ".")
    return " ".join(lines)
