"""
core.development_engine
=========================

The strategic layer (DEC-0144, proposed, from ChatGPT's Development Intelligence + Convergence handoffs; proving
domain: homestead, Zac 2026-11-08). Over the systems MIA already has — projects, intents, missions, plans, skills,
materials — it does the one thing they don't: decide *what's worth doing*, in *what order*, from the resources
actually on hand.

Three parts, all **advisory** and tagged `simulated` (DEC-0137): nothing here commits a real change. It scores and
recommends; any real action still goes through `core/actions.py` with the person's approval and an exact Undo. The
same rule the rest of MIA runs on holds — facts are assembled in code, the model only phrases them, so a plan is never
the model improvising dollars.

1. `development_profile(context)` — the resources and gaps, read defensively from state MIA already holds (budget,
   time, skills, what's on the shelf, the season, the person's stated objectives).
2. `score(candidate, profile, catalog, done)` — a transparent score over entry cost, monthly benefit, labour, risk
   and season, and — the point of the whole thing — **compounding value**: what a project *unlocks*. Compost isn't
   worth building for compost; it's worth building because it unlocks soil, the raised bed's yield and the
   greenhouse. Estimates stay honestly estimates, never fake-precise predictions.
3. `next_step(profile, catalog, done)` — the single highest-value *available* move (affordable, unblocked, in
   season), with its reasoning; or, when nothing is doable yet, the cheapest prerequisite or the gap to close.

The homestead catalog here (`homestead_catalog`) is the first proving domain; the same engine takes any domain's
candidate list (workshop, business…), which is the cross-domain reuse DEC-0137 approved. Everything is pure and
deterministic, so the Zero-to-Something benchmark (`tests/test_development_engine.py`) can hold it to honest planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from core.environment import SIMULATED

# A safety-critical candidate carries this: MIA guides, it never certifies. Structural, electrical, legal and
# financial decisions get a "qualified professional should verify" marker, surfaced in the reasoning.
PROFESSIONAL = "A qualified professional should verify this before you build or commit."


@dataclass
class DevelopmentProfile:
    """The starting position a plan is built from — assembled from real state, never re-entered. A planning artifact,
    so it is `simulated`: it informs recommendations but is never a real-authority record."""

    budget: float = 0.0
    hours_per_week: float = 0.0
    skills: frozenset = frozenset()
    have: frozenset = frozenset()  # capability tags on hand: tools, materials, assets, finished prerequisites
    month: int = 1  # 1–12, for seasonal timing
    objectives: tuple = ()  # the person's stated whys/intents, in their words
    environment: str = SIMULATED


@dataclass
class Candidate:
    """One project MIA could recommend. `requires`/`provides` are capability tags that form the dependency graph;
    `unlocks` names the candidates this one makes possible or much better (its compounding value)."""

    id: str
    name: str
    sector: str = "homestead"  # which development area it belongs to (not a tool domain): homestead, business...
    entry_cost: float = 0.0  # dollars to start
    recurring_cost: float = 0.0  # dollars per month to run
    labour_hours: float = 0.0  # rough hours to complete
    benefit: float = 0.0  # estimated monthly value produced or saved (soft)
    risk: float = 0.2  # 0–1
    requires: frozenset = frozenset()  # tags that must be satisfied (profile.have, or a finished candidate's provides)
    provides: frozenset = frozenset()  # tags this grants when done
    unlocks: tuple = ()  # candidate ids this makes possible / much better
    season: tuple = ()  # months it's best begun; () means any time
    scalable: bool = False
    needs_professional: bool = False  # safety-critical: structural, electrical, legal, financial
    note: str = ""

    def payoff_months(self) -> Optional[float]:
        """Rough months for the monthly benefit to repay the entry cost, or None when there's no benefit to repay."""
        return round(self.entry_cost / self.benefit, 1) if self.benefit > 0 else None


def _have_after(profile: DevelopmentProfile, catalog: Sequence[Candidate], done: frozenset) -> set:
    """The capability tags on hand once the finished candidates' `provides` are added to the profile's own."""
    have = set(profile.have)
    by_id = {c.id: c for c in catalog}
    for cid in done:
        c = by_id.get(cid)
        if c is not None:
            have |= set(c.provides)
    return have


def available(candidate: Candidate, profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> tuple:
    """Whether a candidate's prerequisites are met, and which tags are missing if not (its dependency gate)."""
    missing = set(candidate.requires) - _have_after(profile, catalog, frozenset(done))
    return (not missing), sorted(missing)


def compounding_value(candidate: Candidate, catalog: Sequence[Candidate], discount: float = 0.5, depth: int = 2) -> float:
    """The discounted monthly benefit of everything this candidate unlocks, out to `depth` hops — why a foundational
    project (compost, water) outscores a leaf project of the same cost."""
    by_id = {c.id: c for c in catalog}
    total = 0.0
    seen = set()
    frontier = [(uid, 1) for uid in candidate.unlocks]
    while frontier:
        uid, hop = frontier.pop()
        if uid in seen or hop > depth:
            continue
        seen.add(uid)
        nxt = by_id.get(uid)
        if nxt is None:
            continue
        total += nxt.benefit * (discount ** (hop - 1))
        frontier.extend((u, hop + 1) for u in nxt.unlocks)
    return round(total, 2)


def score(candidate: Candidate, profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> dict:
    """A transparent score for ranking, plus the honest facts behind it. The gates (affordable, unblocked, in season)
    dominate, so an out-of-reach project always sinks below a doable one; among doable ones, monthly benefit and
    compounding value win and cost, labour and risk weigh against. The number is an ordering aid on a soft scale,
    never a dollar prediction."""
    ok, missing = available(candidate, profile, catalog, done)
    affordable = candidate.entry_cost <= profile.budget
    in_season = (not candidate.season) or (profile.month in candidate.season)
    cv = compounding_value(candidate, catalog)
    value = candidate.benefit + cv
    cost = candidate.entry_cost + candidate.recurring_cost * 6  # a 6-month running horizon
    raw = value * 10 - cost * 0.05 - candidate.labour_hours * 0.5 - candidate.risk * 20
    if not affordable:
        raw -= 1000
    if not ok:
        raw -= 1000
    if not in_season:
        raw -= 15
    return {
        "id": candidate.id,
        "name": candidate.name,
        "score": round(raw, 1),
        "available": ok,
        "missing": missing,
        "affordable": affordable,
        "in_season": in_season,
        "entry_cost": candidate.entry_cost,
        "benefit": candidate.benefit,
        "payoff_months": candidate.payoff_months(),
        "compounding_value": cv,
        "unlocks": list(candidate.unlocks),
        "needs_professional": candidate.needs_professional,
    }


def ranked(profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> list:
    """Every not-yet-done candidate, scored, best first."""
    done = frozenset(done)
    return sorted((score(c, profile, catalog, done) for c in catalog if c.id not in done),
                  key=lambda s: s["score"], reverse=True)


def _reason(s: dict) -> str:
    """A plain, honest sentence for why a recommendation is the move — its benefit, what it unlocks, its cost."""
    bits = []
    if s["compounding_value"] > 0 and s["unlocks"]:
        bits.append(f"it opens the door to {len(s['unlocks'])} more project{'s' if len(s['unlocks']) != 1 else ''}")
    if s["benefit"] > 0:
        pay = f", paying for itself in about {s['payoff_months']} months" if s["payoff_months"] else ""
        bits.append(f"it starts producing value{pay}")
    if s["entry_cost"] > 0:
        bits.append(f"about ${s['entry_cost']:.0f} to start")
    why = "; ".join(bits) or "it's the most useful thing within reach right now"
    pro = f" {PROFESSIONAL}" if s["needs_professional"] else ""
    return f"{s['name']} — {why}.{pro}"


def next_step(profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> Optional[dict]:
    """The single logical next move, with its reasoning — or None when the catalog is empty. Prefers a doable project
    (affordable, unblocked, in season); failing that, names a seasonal wait, a savings target, or the prerequisite to
    clear first, so the answer is always grounded in the real starting position."""
    rows = ranked(profile, catalog, done)
    if not rows:
        return None
    doable = [s for s in rows if s["available"] and s["affordable"] and s["in_season"]]
    if doable:
        best = doable[0]
        return {"kind": "do", "recommend": best, "reason": _reason(best)}
    # Nothing is doable right now — explain the nearest path to a doable one.
    off_season = [s for s in rows if s["available"] and s["affordable"] and not s["in_season"]]
    if off_season:
        best = off_season[0]
        return {"kind": "wait_season",
                "recommend": best,
                "reason": f"{_reason(best)} It's best begun in its season — line it up and start then."}
    unaffordable = [s for s in rows if s["available"] and not s["affordable"]]
    if unaffordable:
        best = unaffordable[0]
        return {"kind": "save",
                "recommend": best,
                "reason": f"The highest-value move you're set up for is {best['name']}, about ${best['entry_cost']:.0f}"
                          f" to start — a bit beyond today's budget. Worth saving toward."}
    # Everything worthwhile is blocked by a missing prerequisite: recommend clearing one.
    blocked = [s for s in rows if not s["available"] and s["missing"]]
    if blocked:
        want = blocked[0]
        need = want["missing"][0]
        provider = next((score(c, profile, catalog, done) for c in catalog
                         if need in c.provides and c.id not in frozenset(done)), None)
        if provider is not None:
            return {"kind": "prerequisite",
                    "recommend": provider,
                    "reason": f"To get to {want['name']} you'll first need {need.replace('_', ' ')} — "
                              f"{_reason(provider)}"}
    return {"kind": "none", "recommend": rows[0],
            "reason": "Nothing quite fits the resources on hand yet — let's close a gap first (budget, tools or a "
                      "prerequisite) and the options open up."}


def homestead_catalog() -> list:
    """The first proving domain (Zac, 2026-11-08): realistic, low-to-higher-cost homestead projects whose dependencies
    and unlocks exercise compounding value — compost and water are cheap and foundational (they unlock the beds and
    the greenhouse); the greenhouse is dear but scalable and opens plant sales. Grounded in plans MIA already knows
    (`core/plan_library.py`). Costs are rough starting figures, not quotes."""
    return [
        Candidate("rain_barrel", "Rain-barrel water collection", entry_cost=40, benefit=8, labour_hours=4,
                  provides=frozenset({"water"}), unlocks=("drip_irrigation", "greenhouse"), risk=0.1,
                  note="A barrel, a diverter and a screen — the cheapest thing that unlocks the most."),
        Candidate("compost_bin", "Three-bay compost bin", entry_cost=30, benefit=12, labour_hours=6,
                  provides=frozenset({"compost", "soil"}), unlocks=("raised_bed", "greenhouse"), risk=0.1,
                  note="Pallets are often free; turns scraps into the soil everything else needs."),
        Candidate("raised_bed", "Raised garden bed", entry_cost=60, benefit=25, labour_hours=8,
                  provides=frozenset({"beds"}), unlocks=("cold_frame", "plant_sales"), season=(3, 4, 5), risk=0.15,
                  note="Better with compost under it; the first real food."),
        Candidate("drip_irrigation", "Drip irrigation", entry_cost=80, benefit=10, labour_hours=5,
                  requires=frozenset({"water"}), provides=frozenset({"irrigation"}), risk=0.15,
                  note="Needs a water source first; saves labour and water across every bed."),
        Candidate("cold_frame", "Cold frame", entry_cost=50, benefit=15, labour_hours=6,
                  requires=frozenset({"beds"}), provides=frozenset({"season_extension"}), season=(9, 10, 11), risk=0.15,
                  note="Extends the growing season at both ends."),
        Candidate("chickens", "Chicken coop and run", entry_cost=300, recurring_cost=25, benefit=40, labour_hours=20,
                  provides=frozenset({"manure", "eggs"}), unlocks=("compost_bin",), risk=0.3, needs_professional=False,
                  note="Eggs and manure for the compost; ongoing feed cost and daily chores."),
        Candidate("greenhouse", "Greenhouse", entry_cost=800, recurring_cost=10, benefit=90, labour_hours=40,
                  requires=frozenset({"water"}), provides=frozenset({"year_round"}), unlocks=("plant_sales",),
                  scalable=True, risk=0.35, needs_professional=True,
                  note="Year-round growing and a path to selling plants; the big step, so it waits."),
        Candidate("plant_sales", "Sell seedlings and produce", entry_cost=40, benefit=60, labour_hours=6,
                  requires=frozenset({"beds"}), scalable=True, risk=0.4, sector="business",
                  note="Where the homestead starts paying back — the bridge to a small business."),
    ]


def development_profile(context) -> DevelopmentProfile:
    """Assemble the starting position from state MIA already holds — budget, time, skills, what's on the shelf, the
    season, the person's stated objectives — reading every source defensively so a missing store just leaves a gap
    rather than crashing the plan. Everything stays `simulated`; this never writes."""
    import datetime

    def _safe(fn, default):
        try:
            return fn()
        except Exception:  # noqa: BLE001 - a missing source is a quiet gap in the plan, not an error
            return default

    have = set()
    skills = set()
    objectives = []
    budget = 0.0
    if getattr(context, "materials", None) is not None:
        have |= {m.name.lower() for m in _safe(lambda: context.materials.all_materials(), [])}
    if getattr(context, "skills", None) is not None:
        skills |= {s.name.lower() for s in _safe(lambda: context.skills.all_skills(), [])}
    if getattr(context, "intents", None) is not None:
        objectives = [i.name for i in _safe(lambda: context.intents.all_intents(), [])]
    return DevelopmentProfile(budget=budget, have=frozenset(have), skills=frozenset(skills),
                              month=datetime.date.today().month, objectives=tuple(objectives))
