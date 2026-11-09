"""
core.trades
=============

Trade Master (DEC-0149; Zac, 2026-11-08: "walk me through step by step of any home construction, repair, or
diagnosis jobs with industry standard professional steps so nothing is missed ... She should become a Trade master
and be able to teach an entry level Apprentice"). The jobs and diagnoses MIA walks someone through, as data written
once, sourced and reviewed, never made up by a model while someone is holding a saw.

- **A job** (`Job`): its trade, scope, the stop rules that apply, the permit and inspection note, hazards and PPE,
  tools, materials (with quantities from a plan's calculator in core/build_calcs.py when it has one), and phases of
  steps. Each step says what to do, why, what to watch for, and may be a **hold point**: something verified before
  going on (power proven dead, a layout checked square). Each job carries its sources and a status: DRAFTED until a
  person confirms it.
- **A diagnosis** (`Diagnosis`): a symptom's checks in order, safest and cheapest first, each yes or no leading to the
  next check, a cause with its fix job, or a professional and what to tell them.
- **Stop rules** (`STOP_RULES`): in code, never the model's call. A job that hits one stops, says why and what to do
  instead (a gas smell, a circuit that can't be proven dead, a doubt about structure, old materials untested for
  asbestos or lead, height without fall protection, digging without a utility locate, work the law there needs a
  licence for, someone hurt, weather). Licensed work is walked through only where a homeowner may legally do it under
  a permit (Zac's answer 3).
- **The standard** (`problems()`, Zac's answer 4: "MIA needs to be held to a high standard to be able to provide
  thorough and complete instructions"): what a job or diagnosis must have before it's offered at all. A test holds
  every one to it, and the `trades.depth` loop (core/loops.py) counts how much of `WANTED` meets it.
- **What's wanted next** (`WANTED`): Zac's order (the greenhouse, the coop, the workshop, cold storage, then all of
  home building), each id written or still to write; the loop opens a task for the next one.

The content lives in core/trade_jobs.py; the step-by-step session in core/trade_session.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

DRAFTED, CONFIRMED = "drafted", "confirmed"
TRADES = {"carpentry": "Carpentry and framing", "plumbing": "Plumbing", "electrical": "Electrical", "hvac": "HVAC",
          "appliances": "Appliances", "exterior": "Roofing, siding and windows", "concrete": "Concrete and masonry",
          "site": "Site work", "finishing": "Drywall, paint and finishing",
          "aquaponics": "Aquaponics systems (DEC-0150)"}
KINDS = ("build", "install", "repair")


@dataclass(frozen=True)
class StopRule:
    """A reason to stop a job: when it applies, what to do instead, and the words that mean it's happening."""
    id: str
    when: str
    instead: str
    words: tuple[str, ...] = ()


STOP_RULES: dict[str, StopRule] = {r.id: r for r in (
    StopRule("gas", "you smell gas, or the work touches a gas line",
             "Stop. Don't switch anything on or off or make a spark. Leave, and call the gas utility's emergency line "
             "from outside. Gas piping is a licensed trade's work in most places.",
             ("smell gas", "gas smell", "rotten egg", "hissing")),
    StopRule("live_power", "a circuit can't be proven dead, or the work is in the panel or the service",
             "Stop. Don't touch it. Prove it dead with a tester you've just checked on a live circuit, or call a "
             "licensed electrician. Panel and service work only where your permit lets a homeowner do it.",
             ("still live", "tester beeps", "tester lit", "got shocked", "sparked", "buzzing")),
    StopRule("structural", "the work changes or doubts how the load reaches the ground",
             "Stop. Shore it if anything is already carrying load, and get an engineer (or the manufacturer's "
             "stamped sizing) before going on.",
             ("sagging", "cracked beam", "wall is moving", "bowing", "load bearing")),
    StopRule("hazmat", "old materials (a house built before 1980) would be cut, sanded or torn out untested",
             "Stop. Have them tested for asbestos and lead first; if they're positive, an abatement professional "
             "handles them.", ("asbestos", "lead paint", "old insulation", "vermiculite")),
    StopRule("fall", "work at height without fall protection, or alone on a roof",
             "Stop. Get a harness and anchor (or scaffold with rails), and never work up high alone.",
             ("no harness", "by myself on the roof", "slipped")),
    StopRule("utilities", "digging before the utility lines are located",
             "Stop. Call 811 (in the US) and wait for the marks before you dig.", ("hit a line", "hit a pipe",
                                                                                   "found a cable")),
    StopRule("licensed", "work the law where you live reserves for a licensed trade, with no homeowner permit",
             "Stop. Check with your building department; if a homeowner can't pull the permit, hire the licensed "
             "trade for that part.", ()),
    StopRule("injury", "someone is hurt", "Stop everything. First aid, and call 911 for anything serious.",
             ("i'm hurt", "i cut myself", "bleeding", "someone's hurt", "broke my")),
    StopRule("weather", "lightning, high wind, or ice while working outside or up high",
             "Stop and come down. Pick it back up when the weather clears.", ("lightning", "high wind", "icy")),
)}


@dataclass(frozen=True)
class Step:
    """One step: what to do, why, what to watch for (common mistakes too), and a hold point: what's verified before
    going on ("" for none)."""
    do: str
    why: str
    watch: tuple[str, ...] = ()
    hold: str = ""


@dataclass(frozen=True)
class Phase:
    """One phase of a job: its name and steps."""
    name: str
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class Job:
    """A job MIA walks someone through (see the module docstring for each part)."""
    id: str
    trade: str
    kind: str
    name: str
    scope: str
    words: tuple[str, ...]
    stop_if: tuple[str, ...]
    permit: str
    hazards: tuple[str, ...]
    ppe: tuple[str, ...]
    tools: tuple[str, ...]
    materials: tuple[str, ...]
    phases: tuple[Phase, ...]
    sources: tuple[str, ...]
    plan: str = ""  # a plans-shelf id (core/plan_library.py) whose calculator gives the quantities
    status: str = DRAFTED
    skill: str = "Construction"

    def steps(self) -> list[tuple[int, int, Step]]:
        """Every step in order, with its phase's index and its own."""
        return [(p, i, s) for p, phase in enumerate(self.phases) for i, s in enumerate(phase.steps)]


@dataclass(frozen=True)
class DiagCheck:
    """One check in a diagnosis: what to look at or do (a question with how), why it comes now, and where a yes and
    a no lead: another check's id, "cause:<what it is>|<job id or ''>", or "pro:<who, and what to tell them>"."""
    id: str
    ask: str
    why: str
    yes: str
    no: str


@dataclass(frozen=True)
class Diagnosis:
    """A symptom worked through checks, safest and cheapest first (see the module docstring)."""
    id: str
    trade: str
    name: str
    words: tuple[str, ...]
    stop_if: tuple[str, ...]
    safety: str
    start: str
    checks: tuple[DiagCheck, ...]
    sources: tuple[str, ...]
    status: str = DRAFTED

    def check(self, check_id: str) -> Optional[DiagCheck]:
        """A check by id, or None."""
        return next((c for c in self.checks if c.id == check_id), None)


JOBS: dict[str, Job] = {}
DIAGNOSES: dict[str, Diagnosis] = {}

# Zac's order (2026-11-08): the four builds first, then all of home building. Each is written (in JOBS or DIAGNOSES)
# or still to write; the trades.depth loop opens a task for the next one not written to the standard.
WANTED: tuple[str, ...] = (
    "hoop_house", "chicken_coop", "workshop", "cold_room",
    "aquaponics_system", "aquaponics_controls", "aquaponics_commission",  # DEC-0150: the pilot, built then handed over
    "toilet_running", "workshop_circuit", "root_cellar", "greenhouse_calc", "cold_room_calc",
    "site_layout", "footings", "slab_on_grade", "foundation_wall", "floor_framing", "wall_framing", "roof_framing",
    "roof_sheathing_underlayment", "asphalt_shingles", "metal_roof", "windows_doors", "house_wrap_flashing",
    "siding_lap", "insulation", "air_sealing", "drywall_hang_finish", "interior_trim", "paint_interior",
    "flooring_lvp", "tile_floor", "rough_plumbing_dwv", "rough_plumbing_supply", "water_heater", "fixtures_set",
    "rough_electrical", "electrical_finish", "hvac_ductwork", "minisplit", "deck", "stairs", "gutters",
    "breaker_tripping", "no_hot_water", "ac_not_cooling", "dryer_no_heat", "roof_leak", "furnace_no_heat",
)


def register(item):
    """Adds a job or a diagnosis (core/trade_jobs.py registers its content on import); returns it."""
    (DIAGNOSES if isinstance(item, Diagnosis) else JOBS)[item.id] = item
    return item


def _loaded() -> None:
    """Imports the content (once)."""
    import core.trade_jobs  # noqa: F401


# ------------------------------------------------------------------ the standard

MIN_STEPS, MIN_PHASES, MIN_SOURCES = 12, 3, 2
_TRIGGERS = (  # words in a job's steps that mean a stop rule must be on it
    ("utilities", r"\b(?:dig|digging|dug|post ?holes?|trench|footing|excavat)"),
    ("live_power", r"\b(?:circuits?|breakers?|outlets?|receptacles?|wiring|electrical panel|breaker panel|"
                   r"service panel|live wire|hot wire)\b"),
    ("gas", r"\bgas (?:line|pipe|piping|valve)\b"),
    ("fall", r"\b(?:ladder|roof|rafters?|scaffold|ridge)\b"),
    ("structural", r"\b(?:bearing wall|beam|header|footing|foundation)\b"),
)
_PREP = re.compile(r"\b(?:plan|prepare|prep|permit|before)\b", re.I)
_FINAL = re.compile(r"\b(?:inspect|inspection|check|finish|final|close)\b", re.I)


def _text(job: Job) -> str:
    """Pure logic. Every word of a job's steps, lowercase."""
    return " ".join(f"{s.do} {s.why} {s.hold} {' '.join(s.watch)}" for _p, _i, s in job.steps()).lower()


def problems(item) -> list[str]:
    """Pure logic. What a job or diagnosis lacks against the standard (empty when it meets it)."""
    return _diagnosis_problems(item) if isinstance(item, Diagnosis) else _job_problems(item)


def _job_problems(job: Job) -> list[str]:
    """Pure logic. A job's gaps against the standard: complete parts, enough phases and steps, a reason for every
    step, hold points through the job, the stop rules its own words call for, a permit note pointing to the local
    office, and sources."""
    out = []
    if job.trade not in TRADES or job.kind not in KINDS:
        out.append("an unknown trade or kind")
    if len(job.scope) < 60:
        out.append("a scope that says what's in and out")
    if not job.words:
        out.append("the words that name it")
    if "local" not in job.permit.lower():
        out.append("a permit note that points to the local building department")
    for part, least in (("hazards", 2), ("ppe", 1), ("tools", 4), ("materials", 3)):
        if len(getattr(job, part)) < least:
            out.append(f"at least {least} {part}")
    if len(job.phases) < MIN_PHASES:
        out.append(f"at least {MIN_PHASES} phases")
    elif not _PREP.search(job.phases[0].name) or not _FINAL.search(job.phases[-1].name):
        out.append("a planning phase first and an inspection phase last")
    steps = job.steps()
    if len(steps) < MIN_STEPS:
        out.append(f"at least {MIN_STEPS} steps")
    if any(len(s.why) < 20 for _p, _i, s in steps):
        out.append("a reason (why) for every step")
    if sum(1 for _p, _i, s in steps if s.watch) * 2 < len(steps):
        out.append("what to watch for on at least half the steps")
    holds = {p for p, _i, s in steps if s.hold}
    if len(holds) < len(job.phases) - 1 or (len(job.phases) - 1) not in holds:
        out.append("a hold point in every phase but the first, and one in the last")
    unknown = [r for r in job.stop_if if r not in STOP_RULES]
    if unknown or not job.stop_if or "injury" not in job.stop_if:
        out.append("known stop rules, injury among them")
    text = _text(job)
    for rule, pattern in _TRIGGERS:
        if re.search(pattern, text) and rule not in job.stop_if:
            out.append(f"the {rule} stop rule (its steps call for it)")
    if len(job.sources) < MIN_SOURCES or any(len(s) < 15 for s in job.sources):
        out.append(f"at least {MIN_SOURCES} sources, each named in full")
    if job.status not in (DRAFTED, CONFIRMED):
        out.append("a status")
    if job.plan:
        from core.plan_library import BUILT_IN

        if not any(p["id"] == job.plan for p in BUILT_IN):
            out.append("a plan that's on the plans shelf")
    return out


def _diagnosis_problems(d: Diagnosis) -> list[str]:
    """Pure logic. A diagnosis's gaps: a start that exists, every branch ending somewhere real (a check, a cause, a
    professional), every check reachable and explained, safety first, stop rules, and sources."""
    out = []
    ids = {c.id for c in d.checks}
    if d.trade not in TRADES or not d.words or d.start not in ids:
        out.append("a trade, words and a start that exists")
    if len(d.safety) < 30:
        out.append("safety said first")
    if not d.stop_if or any(r not in STOP_RULES for r in d.stop_if):
        out.append("known stop rules")
    reached, todo = set(), [d.start]
    while todo:
        cid = todo.pop()
        if cid in reached or cid not in ids:
            continue
        reached.add(cid)
        c = d.check(cid)
        for target in (c.yes, c.no):
            if target in ids:
                todo.append(target)
            elif target.startswith("cause:"):
                what, _, job = target[6:].partition("|")
                if len(what) < 10 or (job and job not in JOBS):
                    out.append(f"a cause that's named, with a written job if any ({cid})")
            elif not (target.startswith("pro:") and len(target) > 14):
                out.append(f"a branch that ends somewhere ({cid})")
    if reached != ids:
        out.append("every check reachable")
    if len(d.checks) < 4 or any(len(c.why) < 20 for c in d.checks):
        out.append("at least 4 checks, each with why")
    if len(d.sources) < 1 or any(len(s) < 15 for s in d.sources):
        out.append("sources, named in full")
    return out


# ------------------------------------------------------------------ finding one, and how much is written

def find(words: str):
    """The job or diagnosis the words name (most of its own words, then its id), or None."""
    _loaded()
    said = (words or "").lower()
    best, score = None, 0
    for item in list(JOBS.values()) + list(DIAGNOSES.values()):
        hits = max((len(w) for w in item.words if w in said), default=0)
        if hits > score:
            best, score = item, hits
    return best


def depth() -> dict:
    """How much of WANTED is written to the standard: {wanted, written, next (the first not yet written), failing
    (written but short of the standard)}."""
    _loaded()
    written = [w for w in WANTED if (w in JOBS or w in DIAGNOSES) and not problems(JOBS.get(w) or DIAGNOSES[w])]
    failing = [w for w in WANTED if (w in JOBS or w in DIAGNOSES) and w not in written]
    nxt = next((w for w in WANTED if w not in written), "")
    return {"wanted": len(WANTED), "written": len(written), "next": nxt, "failing": failing}


def outline(item) -> str:
    """Pure logic. A job or diagnosis said in a few lines: what it is, the stop rules, the permit note, what it takes
    and its phases (a job), or where it starts (a diagnosis), and whether a person has confirmed it."""
    status = "" if item.status == CONFIRMED else " (drafted from its sources, not yet confirmed by a person)"
    if isinstance(item, Diagnosis):
        return f"{item.name}{status}. Safety first: {item.safety} First check: {item.check(item.start).ask}"
    phases = "; ".join(f"{i + 1}. {p.name}" for i, p in enumerate(item.phases))
    return (f"{item.name}{status}: {item.scope} Permit: {item.permit} Hazards: {', '.join(item.hazards)}. "
            f"Wear: {', '.join(item.ppe)}. Tools: {', '.join(item.tools)}. Phases: {phases}.")
