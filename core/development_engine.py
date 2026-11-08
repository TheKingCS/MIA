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
3. `next_step(profile, catalog, done)` — it looks ahead (Zac, 2026-11-08: "deep and smart about what to suggest").
   Every goal gets its whole path (`path_to`: what it needs, recursively, made or upcycled before bought), each path
   is weighed as a whole, value against the money *and* hours it takes (`_worth`), and the first step of the best one
   is the recommendation, said as "step 1 of 6 on the way to …" with the checks behind it (`readiness`: in place, in
   season, the rest lined up, the budget, made first, selling only after proof and a place to sell, a professional's
   look). So selling starts is reached through toilet-roll cups, a shelf, a first batch and a stand, never jumped to;
   and an $800 build waits while cheap foundations remain. When no path can start now: a seasonal wait, a savings
   target, or the prerequisite to clear first. What's already on hand is never recommended again (`met`: a project
   whose every provided tag is had counts as done, so compost going means no compost bin), and a stand for selling
   food waits for the state's cottage-food rules (`needs`), one for seedlings doesn't.

The homestead catalog here (`homestead_catalog`) is the first proving domain; the same engine takes any domain's
candidate list (workshop, business…), which is the cross-domain reuse DEC-0137 approved. Everything is pure and
deterministic, so the Zero-to-Something benchmark (`tests/test_development_engine.py`) can hold it to honest planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from core.environment import SIMULATED
from core.region import money

# A safety-critical candidate carries this: MIA guides, it never certifies. Structural, electrical, legal and
# financial decisions get a "qualified professional should verify" marker, surfaced in the reasoning.
PROFESSIONAL = "A qualified professional should verify this before you build or commit."

# Selling waits for proof it can be made well and a place to sell it (Zac, 2026-11-08: no selling plant starts before
# the shelf, the cups and a first batch). These tags say which is which; a test holds every revenue candidate to them.
OUTLET_TAGS = frozenset({"sales_outlet"})
PROOF_TAGS = frozenset({"grown_seedlings", "eggs", "preserves", "something_to_sell"})  # made well, before anyone pays
# Selling food made at home needs the state's cottage-food rules checked first (what may be sold, labels, permits):
# every food sale requires this tag, and a test holds it.
FOOD_SALE_TAG = "food_sale_ok"
# And a place to sell waits for that check when everything there is to sell is food: a stand built for jars or eggs the
# state won't allow is money spent for nothing, while seedlings (not food) need no such check (`needs`).
FOOD_GOODS = frozenset({"eggs", "preserves"})
OTHER_GOODS = frozenset({"grown_seedlings"})
STEP_PENALTY = 2.0  # each extra step on a path is a little less certain
# Needs that mean one particular thing, so a finished step that needed one says it exists: a laying flock means a coop
# and a feed bin. "Water" isn't one: a greenhouse watered by a hose doesn't mean a rain barrel.
IMPLIED_TAGS = frozenset({"coop", "feed_storage", "greenhouse_site", "canning"})
HOUR_VALUE = 15.0  # a rough worth of an hour, so work counts against a project the way money does (soft, not a wage)


def _worth(value: float, cost: float, labour: float) -> float:
    """Pure logic. Value judged against everything it takes: monthly value (with what it unlocks) over the money and
    the hours it costs. A free afternoon that opens doors beats an $800 build until the foundations are in; an unknown
    budget never makes a big step look cheap."""
    return value * 10 / (1 + (cost + labour * HOUR_VALUE) / 100)


@dataclass
class DevelopmentProfile:
    """The starting position a plan is built from — assembled from real state, never re-entered. A planning artifact,
    so it is `simulated`: it informs recommendations but is never a real-authority record."""

    budget: Optional[float] = None  # None: not known yet, so costs are said plainly, never judged against $0
    hours_per_week: float = 0.0
    skills: frozenset = frozenset()
    have: frozenset = frozenset()  # capability tags on hand: tools, materials, assets, finished prerequisites
    month: int = 1  # 1–12, for seasonal timing
    objectives: tuple = ()  # the person's stated whys/intents, in their words
    environment: str = SIMULATED


@dataclass
class Candidate:
    """One project MIA could recommend. `requires`/`provides` are capability tags that form the dependency graph;
    `unlocks` names the candidates this one makes possible or much better (its compounding value); `made` marks one
    made by hand or upcycled, chosen over a bought one that provides the same; `slow` one that takes months to be
    ready, chosen on a path only when nothing quicker would do."""

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
    made: bool = False  # made by hand or upcycled rather than bought: preferred when both would do (DEC-0141)
    slow: bool = False  # takes months to be ready (finished compost): on a path, only when nothing quicker meets the need
    note: str = ""
    evidence: tuple = ()  # words that mark it already done in the person's records ("greenhouse", "coop")

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


def needs(candidate: Candidate, have) -> frozenset:
    """Pure logic. What a candidate needs first, given what's on hand: its own requirements, and for a place to sell
    (OUTLET_TAGS) when everything there is to sell is food, the cottage-food rules checked (FOOD_SALE_TAG) before it's
    built."""
    have = set(have)
    food_only = bool(have & FOOD_GOODS) and not have & OTHER_GOODS
    extra = {FOOD_SALE_TAG} if candidate.provides & OUTLET_TAGS and food_only else set()
    return frozenset(candidate.requires) | extra


def met(profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> frozenset:
    """Pure logic. What's done, plus every project whose whole purpose is already on hand: each tag it provides is had
    (a compost pile going means no compost bin to build; seed cups on hand mean neither the toilet-roll cups nor the
    bought trays). A project that only earns (sales) provides nothing, so it's never met this way."""
    done = frozenset(done)
    have = _have_after(profile, catalog, done)
    return done | {c.id for c in catalog if c.provides and set(c.provides) <= have}


def available(candidate: Candidate, profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> tuple:
    """Whether a candidate's prerequisites are met (`needs`: its own, and the food rules before a stand for food), and
    which tags are missing if not (its dependency gate)."""
    have = _have_after(profile, catalog, frozenset(done))
    missing = set(needs(candidate, have)) - have
    return (not missing), sorted(missing)


def compounding_value(candidate: Candidate, catalog: Sequence[Candidate], discount: float = 0.5, depth: int = 2,
                      done=frozenset()) -> float:
    """The discounted monthly benefit of everything this candidate unlocks, out to `depth` hops — why a foundational
    project (compost, water) outscores a leaf project of the same cost. Something already `done` unlocks nothing new,
    so it adds nothing. And a step earns only its share of what it unlocks: its part of all the work still needed to
    get that thing (its own money and hours, against the cheapest way to meet each other need, plus the thing's own
    cost). A $25 feed bin is a sliver of the way to a flock that also needs a $300 coop, so it isn't credited with the
    flock (2026-11-08: crediting the whole had outranked selling starts that were ready)."""
    by_id = {c.id: c for c in catalog}
    have = set(candidate.provides)
    for cid in done:
        if cid in by_id:
            have |= set(by_id[cid].provides)
    total = 0.0
    seen = set()
    frontier = [(uid, 1, 1.0) for uid in candidate.unlocks]
    while frontier:
        uid, hop, carried = frontier.pop()
        if uid in seen or hop > depth or uid in done:
            continue
        seen.add(uid)
        nxt = by_id.get(uid)
        if nxt is None:
            continue
        share = carried * _share_of_work(candidate, nxt, have, catalog, done)
        total += nxt.benefit * share * (discount ** (hop - 1))
        frontier.extend((u, hop + 1, share) for u in nxt.unlocks)
    return round(total, 2)


def _effort(c: Candidate) -> float:
    """Pure logic. Everything a candidate takes, in one soft unit: its money (six months of running costs) and its
    hours at HOUR_VALUE."""
    return c.entry_cost + c.recurring_cost * 6 + c.labour_hours * HOUR_VALUE


def _share_of_work(step: Candidate, target: Candidate, have: set, catalog: Sequence[Candidate], done) -> float:
    """Pure logic. How much of the work of reaching `target` `step` is: its effort against its own plus the cheapest
    provider of each need still unmet, plus the target's own. 0 when a need has no way to be met."""
    extra = 0.0
    for tag in target.requires - have:
        options = [_effort(c) for c in catalog if tag in c.provides and c.id not in done and c is not step]
        if not options:
            return 0.0
        extra += min(options)
    mine = max(_effort(step), 1.0)
    return mine / (mine + extra + _effort(target))


def score(candidate: Candidate, profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> dict:
    """A transparent score for ranking, plus the honest facts behind it. The gates (affordable, unblocked, in season)
    dominate, so an out-of-reach project always sinks below a doable one; among doable ones, monthly benefit and
    compounding value are weighed against the money and hours it takes (`_worth`), less its risk. The number is an
    ordering aid on a soft scale,
    never a dollar prediction. An unknown budget (None) isn't a gate: the cost is said, not judged against $0."""
    ok, missing = available(candidate, profile, catalog, done)
    affordable = profile.budget is None or candidate.entry_cost <= profile.budget
    in_season = (not candidate.season) or (profile.month in candidate.season)
    cv = compounding_value(candidate, catalog, done=frozenset(done))
    value = candidate.benefit + cv
    cost = candidate.entry_cost + candidate.recurring_cost * 6  # a 6-month running horizon
    raw = _worth(value, cost, candidate.labour_hours) - candidate.risk * 20
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
    """Every candidate not yet done or already met (`met`), scored, best first."""
    done = met(profile, catalog, done)
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
        bits.append(f"about {money(s['entry_cost'], ',.0f')} to start")
    why = "; ".join(bits) or "it's the most useful thing within reach right now"
    pro = f" {PROFESSIONAL}" if s["needs_professional"] else ""
    return f"{s['name']} — {why}.{pro}"


def path_to(goal: Candidate, profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> Optional[list]:
    """The ordered steps that make `goal` doable from here, ending with the goal itself (Zac, 2026-11-08: "going
    straight to selling plant starts without any kind of building the infrastructure to manage that wouldn't be a good
    idea"). For each thing it still needs, the candidate that provides it: made or upcycled first (his producer
    direction, DEC-0141), then cheapest, then least work, and never a slow one (months to be ready) when something
    quicker meets the need, with that candidate's own needs (`needs`, so the food rules before a food stand) before
    it. None when
    something on the way has no way to get it. Pure logic."""
    done = frozenset(done)
    have = _have_after(profile, catalog, done)
    steps: list = []

    def provide(tag: str, seen: frozenset) -> bool:
        """Whether `tag` is on hand, or some candidate (and its own needs) can be added to the path to provide it."""
        if tag in have:
            return True
        options = sorted((c for c in catalog if tag in c.provides and c.id not in done and c.id not in seen),
                         key=lambda c: (c.slow, not c.made, c.entry_cost, c.labour_hours))
        return any(visit(c, seen | {c.id}) for c in options)

    def visit(c: Candidate, seen: frozenset) -> bool:
        """Adds `c` after everything it needs; on a dead end, puts the path back as it was."""
        kept_steps, kept_have = list(steps), set(have)
        for tag in sorted(needs(c, have)):  # what's on hand so far decides (the food rules before a food stand)
            if not provide(tag, seen):
                steps[:] = kept_steps
                have.clear()
                have.update(kept_have)
                return False
        if c not in steps:
            steps.append(c)
            have.update(c.provides)
        return True

    return steps if visit(goal, frozenset({goal.id})) else None


def _months_until(season: tuple, month: int) -> int:
    """Pure logic. Months from `month` until a step's season opens (0 in season, or with no season)."""
    if not season or month in season:
        return 0
    return min((m - month) % 12 for m in season)


def _path_score(goal: Candidate, steps: list, catalog: Sequence[Candidate], done, month: int = 0) -> float:
    """Pure logic. How worthwhile a whole path is, on the same soft scale as `score`: the goal's monthly value and what
    it unlocks, plus what each step produces on the way, against the path's cost, work and the goal's risk, and a
    little less for every extra step (a far goal is less certain). And a payoff that can't come for months is worth
    less than one now: the value is discounted by the longest wait for a step's season on the path (in September,
    preserves already put up beat seedling starts that can't sell until spring). A one-step path in season scores as
    its candidate does."""
    value = goal.benefit + compounding_value(goal, catalog, done=frozenset(done)) + sum(
        s.benefit for s in steps if s is not goal)
    cost = sum(s.entry_cost + s.recurring_cost * 6 for s in steps)
    labour = sum(s.labour_hours for s in steps)
    wait = max((_months_until(s.season, month) for s in steps), default=0) if month else 0
    return _worth(value, cost, labour) / (1 + wait / 6) - goal.risk * 20 - STEP_PENALTY * (len(steps) - 1)


def _months(season: tuple) -> str:
    """Pure logic. "March to May" for a season's months."""
    return f"{_MONTHS[season[0] - 1]} to {_MONTHS[season[-1] - 1]}" if season else ""


def readiness(first: Candidate, goal: Candidate, steps: list, profile: DevelopmentProfile,
              catalog: Sequence[Candidate], done=frozenset()) -> list:
    """The checks behind a recommendation, shown with it so the reasoning is open: everything it needs is in place,
    it's the right season (and when the rest of the path's steps come due), the cost against the budget, made before
    bought, selling only after proof and a place to sell, and a professional's look for anything structural. Each is
    {"check", "ok", "line"}; ok is None when it's only information. Pure logic."""
    done = frozenset(done)
    out = [{"check": "ready", "ok": True, "line": "Everything it needs is already in place."}]
    in_season = (not first.season) or profile.month in first.season
    out.append({"check": "season", "ok": in_season,
                "line": "A good time to do it." if in_season else f"Best begun {_months(first.season)}."})
    later = [s for s in steps[1:] if s.season and profile.month not in s.season]
    if later:
        out.append({"check": "timing", "ok": None, "line": "Line up the rest: " + "; ".join(
            f"{s.name.lower()} is best begun {_months(s.season)}" for s in later) + "."})
    total = sum(s.entry_cost for s in steps)
    if profile.budget is None:
        out.append({"check": "budget", "ok": None,
                    "line": f"About {money(first.entry_cost, ',.0f')} for this step, about {money(total, ',.0f')} "
                            "for the whole path; tell me your budget and I'll weigh it."})
    else:
        out.append({"check": "budget", "ok": total <= profile.budget,
                    "line": f"About {money(total, ',.0f')} for the whole path, "
                            + ("within" if total <= profile.budget else "more than")
                            + f" the {money(profile.budget, ',.0f')} you have; this step is "
                              f"{money(first.entry_cost, ',.0f')}."})
    for step in steps:
        rivals = [c for c in catalog if c is not step and c.id not in done and c.provides & step.provides]
        bought = [c for c in rivals if not c.made]
        if step.made and bought:
            out.append({"check": "made_first", "ok": True,
                        "line": f"Made, not bought: {step.name.lower()} rather than {bought[0].name.lower()} "
                                f"({money(bought[0].entry_cost, ',.0f')})."})
        elif not step.made and any(c.made for c in rivals):
            maker = next(c for c in rivals if c.made)
            out.append({"check": "made_first", "ok": False,
                        "line": f"{maker.name} could be made instead of buying {step.name.lower()}."})
    if goal.sector == "business":
        proof, outlet = goal.requires & PROOF_TAGS, goal.requires & OUTLET_TAGS
        out.append({"check": "start_small", "ok": bool(proof and outlet),
                    "line": "Selling waits for proof you can make it well (a first batch) and a place to sell it, "
                            "then starts small."})
    if any(s.needs_professional for s in steps):
        out.append({"check": "professional", "ok": None, "line": PROFESSIONAL})
    return out


def next_step(profile: DevelopmentProfile, catalog: Sequence[Candidate], done=frozenset()) -> Optional[dict]:
    """The single logical next move, with its reasoning, or None when the catalog is empty. It looks ahead: every goal
    gets its whole path (`path_to`), each path is weighed as a whole (`_path_score`), and the first step of the best
    one whose first step can be done now is the recommendation, with the path and the checks behind it
    (`readiness`), said as the start of the most productive goal that step begins. So a goal that needs
    infrastructure first (selling starts needs cups, a shelf, a first batch and a stand) is reached through that
    infrastructure, never jumped to. When no path can start now, it names a seasonal
    wait, a savings target, or the prerequisite to clear first. A project already met by what's on hand (`met`)
    counts as done."""
    done = met(profile, catalog, done)  # what's on hand already counts as done: it's never recommended again
    rows = ranked(profile, catalog, done)
    if not rows:
        return None
    best = None
    leads: dict = {}  # first step's id -> the best longer path it starts, to say what a step leads toward
    for goal in catalog:
        if goal.id in done:
            continue
        steps = path_to(goal, profile, catalog, done)
        if not steps:
            continue
        first = score(steps[0], profile, catalog, done)
        if not (first["available"] and first["affordable"] and first["in_season"]):
            continue
        weight = _path_score(goal, steps, catalog, done, profile.month)
        if best is None or weight > best[0]:
            best = (weight, goal, steps, first)
        # What a step leads toward: the goal it starts the path to that itself produces the most,
        # the longer path on a tie, so a free first step is said as the start of selling starts, not just the batch.
        aim = (goal.benefit, len(steps))  # what the goal itself produces, not what it unlocks (that counts its steps)
        if len(steps) > 1 and (steps[0].id not in leads or aim > leads[steps[0].id][0]):
            leads[steps[0].id] = (aim, goal, steps)
    if best is not None:
        _, goal, steps, first = best
        if first["id"] in leads:  # the same first step, said as the start of the most productive goal it begins
            _, goal, steps = leads[first["id"]]
        reason = _reason(first)
        if len(steps) > 1:
            reason += (f" It's step 1 of {len(steps)} on the way to \u201c{goal.name}\u201d: "
                       + " \u2192 ".join(s.name.lower() for s in steps) + ".")
        return {"kind": "do", "recommend": first, "reason": reason, "goal": {"id": goal.id, "name": goal.name},
                "path": [{"id": s.id, "name": s.name, "cost": money(s.entry_cost, ",.0f"), "made": s.made}
                         for s in steps],
                "checks": readiness(next(c for c in catalog if c.id == first["id"]), goal, steps, profile, catalog,
                                    done)}
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
                "reason": f"The highest-value move you're set up for is {best['name']}, about "
                          f"{money(best['entry_cost'], ',.0f')} to start — a bit beyond today's budget. Worth saving "
                          f"toward."}
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
    """(Long on purpose, the weekly audit asks: it is the catalog's data, one Candidate per project in chain order, so
    a chain reads in one place; the tests hold its rules.) The first proving domain (Zac, 2026-11-08): realistic, low-to-higher-cost homestead projects whose dependencies
    and unlocks exercise compounding value — compost and water are cheap and foundational (they unlock the beds and
    the greenhouse); the greenhouse is dear but scalable. Selling seedling starts sits at the end of a real chain:
    seed cups (toilet-paper rolls, made, before bought trays), a seed-starting shelf (scrap, before a bought one), seed
    mix, a first batch as proof, then a stand, so the plan reaches it through the infrastructure it needs. The flock
    the same way: a coop and a feed bin, hens in spring, eggs before selling eggs; a compost bin's first finished
    compost becomes made seed mix months later; preserving needs a harvest, the gear and a first batch; any food sold
    (eggs, preserves) waits for the state's cottage-food rules to be checked; and a greenhouse waits for a level,
    drained site. Grounded in plans MIA already knows
    (`core/plan_library.py`), each with the words that mark it already done in the person's records (`_EVIDENCE`,
    read by `done_from_records`). Costs are rough starting figures, not quotes."""
    catalog = [
        Candidate("rain_barrel", "Rain-barrel water collection", entry_cost=40, benefit=8, labour_hours=4,
                  provides=frozenset({"water"}), unlocks=("drip_irrigation", "greenhouse"), risk=0.1,
                  note="A barrel, a diverter and a screen — the cheapest thing that unlocks the most."),
        Candidate("compost_bin", "Three-bay compost bin", entry_cost=30, benefit=12, labour_hours=6, made=True,
                  provides=frozenset({"compost", "soil"}), unlocks=("raised_bed", "greenhouse", "finished_compost"),
                  risk=0.1,
                  note="Pallets are often free; turns scraps into the soil everything else needs."),
        Candidate("raised_bed", "Raised garden bed", entry_cost=60, benefit=25, labour_hours=8, made=True,
                  provides=frozenset({"beds"}), unlocks=("cold_frame",), season=(3, 4, 5), risk=0.15,
                  note="Better with compost under it; the first real food."),
        Candidate("drip_irrigation", "Drip irrigation", entry_cost=80, benefit=10, labour_hours=5,
                  requires=frozenset({"water"}), provides=frozenset({"irrigation"}), risk=0.15,
                  note="Needs a water source first; saves labour and water across every bed."),
        Candidate("cold_frame", "Cold frame", entry_cost=50, benefit=15, labour_hours=6, made=True,
                  requires=frozenset({"beds"}), provides=frozenset({"season_extension"}), season=(9, 10, 11), risk=0.15,
                  note="Extends the growing season at both ends."),
        Candidate("chickens", "Chicken coop and run", entry_cost=300, benefit=0, labour_hours=20, made=True,
                  provides=frozenset({"coop"}), unlocks=("flock",), risk=0.3,
                  note="Built before any bird comes home: roosts, nest boxes, vents and a predator-proof run."),
        # The flock: a coop and somewhere to keep feed first, hens in spring, eggs before selling eggs (2026-11-08).
        Candidate("feed_bin", "A rodent-proof feed bin", entry_cost=25, benefit=1, labour_hours=0.2,
                  provides=frozenset({"feed_storage"}), unlocks=("flock",), risk=0.05,
                  note="A metal can with a tight lid keeps feed dry and the mice out."),
        Candidate("flock", "Start a small laying flock", entry_cost=60, recurring_cost=20, benefit=40, labour_hours=4,
                  requires=frozenset({"coop", "feed_storage"}), provides=frozenset({"eggs", "manure", "something_to_sell"}),
                  unlocks=("compost_bin", "egg_sales"), season=(3, 4, 5, 6), risk=0.3,
                  note="Four to six pullets in spring; daily care, feed and water every day."),
        Candidate("egg_sales", "Sell extra eggs", entry_cost=15, benefit=30, labour_hours=2,
                  requires=frozenset({"eggs", "sales_outlet", "food_sale_ok"}), scalable=True, risk=0.2,
                  sector="business",
                  note="Once the flock lays more than you eat: cartons, a fair price, the same stand."),
        # Preserving: something to put up, the gear, a first batch, and the rules checked before any jar is sold.
        Candidate("canning_setup", "A water-bath canning setup", entry_cost=40, benefit=5, labour_hours=1,
                  requires=frozenset({"beds"}), provides=frozenset({"canning"}), unlocks=("pantry_stock",),
                  season=(6, 7, 8, 9), risk=0.1,
                  note="A deep pot with a rack, jars, a jar lifter: for high-acid food (jams, pickles, tomatoes with acid)."),
        Candidate("pantry_stock", "Put up a first batch of preserves", entry_cost=15, benefit=15, labour_hours=4,
                  requires=frozenset({"canning"}), provides=frozenset({"preserves", "something_to_sell"}),
                  unlocks=("preserve_sales",), season=(7, 8, 9, 10), risk=0.15,
                  note="Follow a tested recipe (the USDA's or Ball's) exactly; low-acid food needs a pressure canner."),
        Candidate("cottage_food_check", "Check your state's cottage-food rules", entry_cost=0, benefit=0, labour_hours=1,
                  requires=frozenset({"something_to_sell"}), provides=frozenset({"food_sale_ok"}),
                  unlocks=("preserve_sales", "egg_sales"), risk=0.0,
                  note="What may be sold from a home kitchen, how it's labelled, where, and whether a permit or a "
                       "food-handler card is needed. Rules differ by state."),
        Candidate("preserve_sales", "Sell jams and pickles", entry_cost=20, benefit=15, labour_hours=3,
                  requires=frozenset({"preserves", "sales_outlet", "food_sale_ok"}), scalable=True, risk=0.25,
                  sector="business", note="Labels as the rules ask; start with what sold best at the table."),
        # Compost matures: months after the bin, its sieved compost is seed mix you made.
        Candidate("finished_compost", "Turn and sieve the first finished compost", entry_cost=0, benefit=6,
                  labour_hours=4, made=True, slow=True, requires=frozenset({"compost"}),
                  provides=frozenset({"seed_mix", "rich_soil"}),
                  unlocks=("first_seedlings",), risk=0.1,
                  note="A few months after the bin starts: turned, cured and sieved, it's the seed mix and the beds' food."),
        Candidate("greenhouse_site", "Level and drain the greenhouse site", entry_cost=30, benefit=0, labour_hours=8,
                  made=True, provides=frozenset({"greenhouse_site"}), unlocks=("greenhouse",), risk=0.1,
                  note="A level, drained pad facing south, gravel under it: the frame waits for the ground."),
        Candidate("greenhouse", "Greenhouse", entry_cost=800, recurring_cost=10, benefit=90, labour_hours=40, made=True,
                  requires=frozenset({"water", "greenhouse_site"}), provides=frozenset({"year_round"}),
                  unlocks=("plant_sales",),
                  scalable=True, risk=0.35, needs_professional=True,
                  note="Year-round growing and a path to selling plants; the big step, so it waits."),
        # Seed starting: the infrastructure selling starts needs before anyone pays for one (Zac, 2026-11-08).
        Candidate("seed_cups", "Toilet-paper-roll seed cups", entry_cost=0, benefit=2, labour_hours=1, made=True,
                  provides=frozenset({"seed_cups"}), unlocks=("first_seedlings",), risk=0.05,
                  note="Save the rolls, cut and fold the bottoms; they go into the ground with the plant."),
        Candidate("cell_trays", "Plastic seed-cell trays", entry_cost=15, benefit=2, labour_hours=0.2,
                  provides=frozenset({"seed_cups"}), unlocks=("first_seedlings",), risk=0.05,
                  note="Reusable for years, but bought."),
        Candidate("seedling_shelf", "Seed-starting shelf", entry_cost=25, benefit=3, labour_hours=4, made=True,
                  provides=frozenset({"seedling_space"}), unlocks=("first_seedlings", "grow_light"), risk=0.1,
                  note="A simple rack from scrap lumber by your sunniest window; the shelving plan sizes it."),
        Candidate("wire_shelf", "A bought wire shelf for seedlings", entry_cost=40, benefit=3, labour_hours=0.5,
                  provides=frozenset({"seedling_space"}), unlocks=("first_seedlings", "grow_light"), risk=0.1,
                  note="Quick, but bought."),
        Candidate("seed_mix", "Seed-starting mix", entry_cost=10, benefit=1, labour_hours=0.2,
                  provides=frozenset({"seed_mix"}), unlocks=("first_seedlings",), risk=0.05,
                  note="Fine and clean; your own sieved compost can stand in once the bin has matured, months from now."),
        Candidate("grow_light", "Shop-light grow lights", entry_cost=40, benefit=6, labour_hours=1,
                  requires=frozenset({"seedling_space"}), provides=frozenset({"seedling_light"}), risk=0.1,
                  note="Stockier starts than a window alone; hang it a few inches over the tops."),
        Candidate("first_seedlings", "Start a first batch of seedlings", entry_cost=5, benefit=8, labour_hours=3,
                  requires=frozenset({"seed_cups", "seedling_space", "seed_mix"}),
                  provides=frozenset({"grown_seedlings", "something_to_sell"}),
                  unlocks=("raised_bed", "sales_stand", "plant_sales"),
                  season=(2, 3, 4), risk=0.2,
                  note="A dozen or two of something easy (tomatoes, peppers, herbs): proof you grow them well first."),
        Candidate("sales_stand", "A roadside stand or market table", entry_cost=20, benefit=0, labour_hours=4,
                  made=True, requires=frozenset({"something_to_sell"}), provides=frozenset({"sales_outlet"}),
                  unlocks=("plant_sales", "egg_sales"), risk=0.1,
                  note="Pallets and a sign, or a table at the local market, built once there's something to sell."),
        Candidate("plant_sales", "Sell seedling starts", entry_cost=10, benefit=20, labour_hours=3,
                  requires=frozenset({"grown_seedlings", "sales_outlet"}), season=(3, 4, 5), scalable=True, risk=0.4,
                  sector="business",
                  note="Start small: a few flats of what grew best, priced by the pot. Spring sales, so its value is "
                       "spread over the year."),
    ]
    for c in catalog:
        c.evidence = _EVIDENCE.get(c.id, ())
    return catalog


# The budget categories a homestead build's money goes to (core/homestead_costs.py, Finance #2).
BUILD_CATEGORIES = ("Building Materials", "Tools & Equipment")


def homestead_budget(context, today=None) -> Optional[float]:
    """What's left this month of the person's own monthly targets for homestead builds (BUILD_CATEGORIES, the personal
    ones, not a business's): the targets less this month's spending in them, never below zero. None when they've set
    no such target, so a budget is never invented. Reads the budget store only."""
    import datetime

    store = getattr(context, "budget", None)
    if store is None:
        return None
    targets = [t for t in store.all_budget_targets() if t.category in BUILD_CATEGORIES and not getattr(t, "entity_id", "")]
    if not targets:
        return None
    today = today or datetime.date.today()
    spent = store.total_expenses_by_category(today.replace(day=1).isoformat(), today.isoformat(), entity_id="")
    return round(max(0.0, sum(t.monthly_amount for t in targets) - sum(spent.get(c, 0.0) for c in BUILD_CATEGORIES)), 2)


def development_profile(context, budget: Optional[float] = None) -> DevelopmentProfile:
    """Assemble the starting position from state MIA already holds — budget, time, skills, what's on the shelf, the
    season, the person's stated objectives, and a budget: the one they give, else what's left this month of their
    homestead build targets (`homestead_budget`), else None (unknown, not $0) —
    reading every source defensively so a missing store just leaves a gap
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
    if getattr(context, "materials", None) is not None:
        have |= {m.name.lower() for m in _safe(lambda: context.materials.all_materials(), [])}
    if getattr(context, "skills", None) is not None:
        skills |= {s.name.lower() for s in _safe(lambda: context.skills.all_skills(), [])}
    if getattr(context, "intents", None) is not None:
        objectives = [i.name for i in _safe(lambda: context.intents.all_intents(), [])]
    if budget is None:
        budget = _safe(lambda: homestead_budget(context), None)
    return DevelopmentProfile(budget=budget, have=frozenset(have), skills=frozenset(skills),
                              month=datetime.date.today().month, objectives=tuple(objectives))


# What marks each homestead project as already done in the person's records (an asset's name, a finished project, a
# tank or bed in the grow lab, a flock): matched as words, so "Walipini greenhouse" counts as a greenhouse.
_EVIDENCE = {
    "rain_barrel": ("rain barrel", "rain catchment", "ibc tote", "water tank", "cistern"),
    "compost_bin": ("compost",),
    "raised_bed": ("raised bed", "garden bed", "grow bed"),
    "drip_irrigation": ("drip",),
    "cold_frame": ("cold frame",),
    "chickens": ("coop",),
    "flock": ("flock", "hens", "laying"),
    "feed_bin": ("feed bin",),
    "canning_setup": ("canner", "canning pot", "canning"),
    "greenhouse": ("greenhouse", "walipini", "hoop house", "polytunnel"),
    "seed_cups": ("seed cup",),
    "cell_trays": ("seed tray", "cell tray", "seedling tray", "plug tray"),
    "seedling_shelf": ("seed shelf", "seedling shelf", "seed-starting shelf", "seed starting shelf", "grow rack",
                       "grow shelf"),
    "seed_mix": ("seed starting mix", "seed-starting mix", "potting mix"),
    "grow_light": ("grow light", "shop light"),
    "first_seedlings": ("grown batch",),  # any batch in the grow lab: proof they grow things
    "sales_stand": ("farm stand", "roadside stand", "market table", "market booth", "produce stand"),
}
_FINISHED = frozenset({"done", "complete", "completed", "finished"})
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")


def done_from_records(context, catalog: Sequence[Candidate]) -> dict:
    """Which candidates the person already has, read from their own records: an asset (the Garage or Greenhouse), a
    finished project, a tank or bed in the grow lab (and any batch grown there, the proof selling waits for), a flock,
    a material on the workshop shelf, each matched by the candidate's `evidence` words; and what a done one needed
    when the need means one particular thing (IMPLIED_TAGS: a flock means a coop and a feed bin).
    {candidate id: where it was found}. A source that won't read just contributes nothing."""
    from core import links

    def _safe(fn) -> list:
        """A store's list, or [] when it can't be read."""
        try:
            return list(fn())
        except Exception:  # noqa: BLE001 - a missing store is a quiet gap
            return []

    names = []  # (lowercased name, where it was found)
    maintenance = getattr(context, "maintenance", None)
    if maintenance is not None:
        names += [(str(a.name).lower(), "your assets") for a in _safe(maintenance.all_assets)]
    projects = getattr(context, "projects", None)
    if projects is not None:
        names += [(str(x.name).lower(), "your finished projects") for x in _safe(projects.all_projects)
                  if str(getattr(x, "status", "")).strip().lower() in _FINISHED]
    lab = getattr(context, "grow_lab", None)
    if lab is not None:
        names += [(str(n).lower(), "your grow lab") for n in getattr(lab, "systems", [])]
        if getattr(lab, "batches", None):
            names.append(("grown batch", "your grow lab"))  # they've grown a batch: the proof selling waits for
    stock = getattr(context, "materials", None)
    if stock is not None:
        names += [(str(m.name).lower(), "your workshop shelf") for m in _safe(stock.all_materials)]
    names += [(f"{getattr(f, 'name', '')} flock".lower(), "your flock") for f in _safe(lambda: links.records(context, "flock"))]
    done = {}
    for c in catalog:
        where = next((w for name, w in names for word in c.evidence if word in name), None)
        if where:
            done[c.id] = where
    # What a finished step needed is done too, for the needs that mean one particular thing (IMPLIED_TAGS): a laying
    # flock means there's a coop and a feed bin. A general need (water) or alternatives (cups or trays) assume nothing.
    by_id = {c.id: c for c in catalog}
    changed = True
    while changed:
        changed = False
        for cid in list(done):
            for tag in by_id[cid].requires & IMPLIED_TAGS:
                providers = [c for c in catalog if tag in c.provides]
                if len(providers) == 1 and providers[0].id not in done:
                    done[providers[0].id] = f"needed for {by_id[cid].name.lower()}"
                    changed = True
    return done


def _why_not(row: dict, profile: DevelopmentProfile, by_id: dict) -> str:
    """Pure logic. Why an option isn't ready yet, in plain words ("" when it is)."""
    if not row["available"]:
        return "needs " + " and ".join(m.replace("_", " ") for m in row["missing"]) + " first"
    if not row["affordable"]:
        return (f"about {money(row['entry_cost'], ',.0f')}, more than the {money(profile.budget, ',.0f')} you said you "
                "have")
    if not row["in_season"]:
        months = by_id[row["id"]].season
        return f"best begun {_MONTHS[months[0] - 1]} to {_MONTHS[months[-1] - 1]}"
    return ""


def plan(context, budget: Optional[float] = None, catalog: Optional[Sequence[Candidate]] = None,
         month: Optional[int] = None) -> dict:
    """The homestead plan as a screen and a tool both show it (DEC-0125): what the person already has (from their
    records), the logical next step with its reasoning, the goal it leads toward, the whole path and the checks behind
    it (`next.goal`, `next.path`, `next.checks`), the best few options with why each isn't ready yet, and the budget it
    weighed (`budget`, and `budget_from`: "you", "your build budget", or None when unknown).
    Advisory and `simulated`: nothing here changes anything."""
    catalog = list(catalog) if catalog is not None else homestead_catalog()
    profile = development_profile(context, budget)
    if month is not None:
        profile.month = month
    have = done_from_records(context, catalog)
    by_id = {c.id: c for c in catalog}
    step = next_step(profile, catalog, frozenset(have))
    options = [{"id": r["id"], "name": r["name"], "entry_cost": r["entry_cost"],
                "cost": money(r["entry_cost"], ",.0f"), "payoff_months": r["payoff_months"],
                "unlocks": [by_id[u].name for u in r["unlocks"] if u in by_id and u not in have],
                "ready": r["available"] and r["affordable"] and r["in_season"],
                "why_not": _why_not(r, profile, by_id), "needs_professional": r["needs_professional"],
                "note": by_id[r["id"]].note}
               for r in ranked(profile, catalog, frozenset(have))[:6]]
    source = "you" if budget is not None else "your build budget" if profile.budget is not None else None
    return {"environment": SIMULATED, "budget": profile.budget, "budget_from": source, "month": profile.month,
            "have": [{"name": by_id[i].name, "found_in": where} for i, where in have.items()],
            "next": ({"kind": step["kind"], "id": step["recommend"]["id"], "name": step["recommend"]["name"],
                      "reason": step["reason"], "goal": step.get("goal"), "path": step.get("path", []),
                      "checks": step.get("checks", [])} if step else None),
            "options": options,
            "note": "Costs are rough starting figures, not quotes. Tell me your budget and I'll weigh it in."}


def describe(p: dict) -> str:
    """Plain words for the tool: the next step and why (with its path, when it's the start of one), what's already
    done, what comes after when there's no path, the checks that aren't met yet or need lining up, and a budget ask
    (or which budget it weighed, when it read it from their build targets)."""
    if not p.get("next"):
        return "I don't have homestead projects to weigh yet."
    lines = [f"Next on the homestead: {p['next']['reason']}"]
    if p["have"]:
        lines.append("Already yours, from your records: " + ", ".join(f"{h['name'].lower()} ({h['found_in']})" for h in p["have"]) + ".")
    path = p["next"].get("path") or []
    if len(path) <= 1:  # the path already says what follows; otherwise the best other options
        after = [o["name"].lower() for o in p["options"] if o["id"] != p["next"]["id"]][:3]
        if after:
            lines.append("After that: " + ", ".join(after) + ".")
    unmet = [c["line"] for c in p["next"].get("checks", []) if c["ok"] is False or c["check"] == "timing"]
    if unmet:
        lines.append(" ".join(unmet))
    if p["budget"] is None:
        lines.append("Tell me your budget and I'll weigh it in.")
    elif p.get("budget_from") == "your build budget":
        lines.append(f"Weighed against the {money(p['budget'], ',.0f')} left in your build budget this month.")
    return " ".join(lines)
