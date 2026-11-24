"""
core.project_ripple
=====================

What a project touches (Zac, 2026-11-24: "You tell MIA you're planning to build a greenhouse. MIA understands that
this involves your available budget, your existing building materials, your garden and growing plans, your water and
electrical systems, your available time, your long-term agricultural research goals. It doesn't just answer
individual questions. It understands how the project affects the rest of your life."). The first piece of the
unified layer (docs/future/UNIFIED_INTELLIGENCE.md).

**What it does.** "I'm planning to build a greenhouse" reaches the question plan "project picture"
(core/question_plans.py; its own words are a build verb before one of `PROJECT_WORDS`, and a question about the
build's materials, cuts or price is its tools', never the plan's), whose gatherer is `gather`: it works out which of
his areas the project touches (`kind_of`, from the project's own words first:
a greenhouse touches money, materials, growing, water, power, time, goals and research; a shed money, materials,
time and goals) and puts each one's facts on one sheet, from the records and calculators MIA already has:

- **the build**: the Library plan for it (`SHELF`, core/plan_library.py) at its own size, or at the size of a draft
  he already has, with what's still to buy against the workshop's stock and its known cost;
- **already started**: a project or a Planner draft by that name, and a project's budget against what's spent on it
  (core/homestead_costs.py);
- **money**: this month in and out, and the freedom date, with the known cost when there is one
  (`question_plans.freedom_with`, filing nothing: a picture is only read);
- **materials**: what's on hand for it already;
- **growing, water, power, animals, time, goals, research**: his garden plans and what's due to plant, the rain he's
  logged and watering, the power system, the flock, his open projects and this week's calendar, his reasons, his grow
  lab's series and learning paths, each through the tool that already answers it.

Each area also carries a line of general guidance (`NEEDS`: "a greenhouse needs water at it"), marked as such, so the
model connects them without inventing his facts. What isn't recorded is said as missing. Nothing is planned, bought
or changed: the sheet ends by offering to draft the plan, which waits for his Confirm.

**In money answers** (`add_still_to_buy`, step 2 of the plan): what his confirmed builds still need from the store,
on the afford, priorities and projects sheets, so "can I afford it?" knows the greenhouse's lumber is still to come.

**When it changes** (`gone_short`, step 3): a material a confirmed build had fully on hand that isn't any more is
offered through the daily check of what's unusual (core/unusual.py), the gate saying each shortage once; stock is
counted once across the builds (`_allotted`), so two builds never both count the same boards.

**On his own page** lines are said to him (`to_you`), not about him.

**On the Planner page** (`for_plan`, /api/planner/touches): each plan's "What It Touches" is the same picture, at the
plan's own size (a garden plan's beds and crops in place of a build), opened when he asks for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

MONEY, MATERIALS, GROWING, WATER, POWER, ANIMALS, TIME, GOALS, RESEARCH = (
    "money", "materials", "growing", "water", "power", "animals", "time", "goals", "research")
BASIC = (MONEY, MATERIALS, TIME, GOALS)


@dataclass(frozen=True)
class Kind:
    """One kind of project: its name, the words that name it, the Library plan that builds it (or ""), and the areas
    of his life it touches, in the order they're said."""
    name: str
    words: str
    shelf: str
    touches: tuple


KINDS: tuple[Kind, ...] = (
    Kind("greenhouse", r"greenhouses?|hoop ?houses?|high tunnels?|poly ?tunnels?|grow tunnels?", "hoop-house",
         (MONEY, MATERIALS, GROWING, WATER, POWER, TIME, GOALS, RESEARCH)),
    Kind("cold room", r"cold rooms?|root cellars?|walk-in cooler", "cold-room", (MONEY, MATERIALS, POWER, GROWING, TIME,
                                                                               GOALS)),
    Kind("chicken coop", r"coops?|chicken house|hen house|chickens|hens|meat birds|broilers|a flock", "chicken-coop",
         (MONEY, MATERIALS, ANIMALS, WATER, TIME, GOALS)),
    Kind("garden", r"gardens?|raised beds?|garden beds?|cold frames?", "raised-bed",
         (MONEY, MATERIALS, GROWING, WATER, TIME, GOALS, RESEARCH)),
    Kind("power", r"solar|panels|generator|battery bank|batteries|inverter|wind turbine", "",
         (MONEY, POWER, MATERIALS, TIME, GOALS)),
    Kind("water", r"rain ?barrels?|rain catchment|rainwater|cisterns?|a well|irrigation|drip lines?|a pond", "",
         (MONEY, WATER, GROWING, MATERIALS, TIME, GOALS)),
    Kind("shed", r"sheds?", "gable-shed", BASIC),
    Kind("deck", r"decks?", "deck-frame", BASIC),
    Kind("fence", r"fences?|fencing", "privacy-fence", (MONEY, MATERIALS, ANIMALS, TIME, GOALS)),
    Kind("lean-to", r"lean-?tos?", "lean-to", BASIC),
    Kind("slab", r"slabs?|concrete pad", "shed-slab", BASIC),
)

# Every kind's words, for the plan's own words (core/question_plans.py: a build verb, then one of these)
PROJECT_WORDS = "|".join(k.words for k in KINDS)

# General guidance for an area, by kind: what such a project asks of it (said as guidance, never as his facts).
NEEDS = {
    ("greenhouse", WATER): "A greenhouse needs water at it every day in summer: a hose run, a line, or rain caught off "
                           "its own roof into barrels.",
    ("greenhouse", POWER): "Power is optional: a passive one with roll-up sides needs none; fans, a heater, grow "
                           "lights or sensors need a circuit, a panel and battery, or an extension run.",
    ("greenhouse", GROWING): "It stretches the growing year: seeds start earlier and crops keep later than the frost "
                             "dates allow outside, so the garden plans and seed list change with it.",
    ("greenhouse", RESEARCH): "A greenhouse is a controlled space: the place to run trials and log readings "
                              "(temperature, humidity, yields) against the outside beds.",
    ("cold room", POWER): "A cold room needs steady power for its cooler, around the clock.",
    ("chicken coop", WATER): "Hens need fresh water every day, and it freezes in winter: a heated waterer needs power.",
    ("chicken coop", ANIMALS): "A coop is sized by the birds: about 4 square feet a hen inside and 10 in the run.",
    ("garden", WATER): "A garden needs about an inch of water a week, from rain or from him.",
    ("power", POWER): "New power is sized from what it has to run: the loads, their hours, and the days of storage.",
    ("water", WATER): "Catchment is sized from the roof: about 0.6 gallons per square foot per inch of rain.",
}

# A request to plan something: the words after it are the project ("build a greenhouse next spring").
_PLANNING = re.compile(
    r"\b(?:build(?:ing)?|put(?:ting)? up|set(?:ting)? up|start(?:ing)?|add(?:ing)?|install(?:ing)?|get(?:ting)?|"
    r"make|making|plan(?:ning)?(?: for)?)\s+(?:a |an |the |some |my |our |new |big |small |another )*"
    r"(?P<what>[a-z][a-z' -]{1,40}?)(?=$|[,.?!]| for | this | next | in | on | by | so | and | to | before | after | "
    r"with | out back| behind)", re.I)


def _kind_in(text: str) -> Optional[Kind]:
    """Pure logic. The first of `KINDS` whose words appear in `text`, whole, or None."""
    lowered = (text or "").lower()
    return next((k for k in KINDS if re.search(rf"(?<![a-z])(?:{k.words})(?![a-z])", lowered)), None)


def kind_of(prompt: str) -> Optional[Kind]:
    """Pure logic. The kind of project the words plan: from the project itself (`planned`: "a shed next to the
    chicken coop" is a shed), else from anywhere in the words, or None."""
    return _kind_in(planned(prompt)) or _kind_in(prompt)


def planned(prompt: str) -> str:
    """Pure logic. The project the words plan ("greenhouse" from "I'm planning to build a greenhouse next spring",
    "fort" from "build the kids a fort": the thing after the last article; up to the first project word when there
    is one, so "a greenhouse or a cold room" is the greenhouse), or "" when no planning words are there."""
    found = ""
    for match in _PLANNING.finditer(prompt or ""):
        what = _LEAD.sub("", match.group("what").strip(" -'")).strip(" -'")
        named = re.search(rf"(?<![a-z])(?:{PROJECT_WORDS})(?:\s+(?:{PROJECT_WORDS}))*(?![a-z])", what)  # "solar panels"
        what = what[:named.end()] if named else what  # "a greenhouse or a cold room": the greenhouse
        what = re.split(r"\s(?:a|an|the)\s", f" {what} ")[-1].strip()  # "the kids a fort": the fort
        if what and what not in ("to", "on", "it", "that", "this", "something", "build", "put", "set"):
            return what
    return found


# "to build a", left at the front when the planning word was "planning" ("planning to build a greenhouse")
_LEAD = re.compile(r"^(?:(?:to|on)\s+)?(?:(?:build|put up|set up|start|add|install|get|make|put in|building|putting up|"
                   r"starting|adding)\s+)?(?:(?:a|an|the|some|my|our|new|big|small|another)\s+)*", re.I)


def _fact(sheet, kind: str, text: str, source: str) -> None:
    """Adds one line to the sheet (question_plans' kinds)."""
    sheet.add(kind, text, source)


def _same_words(name: str, project: str) -> bool:
    """Pure logic. Whether a record's name holds every word of the project ("Hoop-house greenhouse" holds "hoop
    house"; "Chicken feed" doesn't hold "chicken coop"), plurals and hyphens aside."""
    words = lambda s: {w.rstrip("s") for w in re.findall(r"[a-z]+", s.lower().replace("-", " "))}  # noqa: E731
    want = words(project) - {"a", "an", "the", "my", "new"}
    return bool(want) and want <= words(name)


def _started(context, sheet, kind: Kind, what: str):
    """What's already started for it: a project by its name (its budget against what's spent) and a Planner plan.
    Returns the Planner plan, when there is one, so the build is worked out at its size."""
    from core.question_plans import CALCULATION, FACT

    names = (what, kind.name)
    projects = getattr(context, "projects", None)
    for project in (projects.all_projects() if projects is not None else []):
        if project.status != "Complete" and any(_same_words(project.name, n) for n in names):
            line = f"There's already a project \"{project.name}\" ({project.status})."
            if getattr(project, "budget", None):
                try:
                    from core.homestead_costs import build_cost, describe_build

                    line += " " + describe_build(build_cost(context, project))
                except Exception:  # noqa: BLE001 - the budget line is extra
                    log.exception("Couldn't read %s's budget", project.name)
            _fact(sheet, CALCULATION if getattr(project, "budget", None) else FACT, line, "Projects")
            break
    book = getattr(context, "project_plans", None)
    for plan in (book.listed() if book is not None else []):
        if plan.status != "dropped" and (plan.shelf_plan.endswith(kind.shelf) and kind.shelf
                                         or any(_same_words(plan.title, n) for n in names)):
            _fact(sheet, FACT, f"There's a {plan.status} plan in the Planner: \"{plan.title}\".", "the Planner")
            return plan
    return None


def _build(context, sheet, kind: Kind, draft) -> float:
    """The build: the Library plan at its size, what's still to buy against the workshop's stock, what's on hand,
    and its known cost, returned (0 when nothing's priced or there's no plan)."""
    from core import question_plans as qp
    from core.plan_library import detail
    from core.region import money

    shelf = (draft.shelf_plan if draft is not None and draft.shelf_plan else
             (f"builtin:{kind.shelf}" if kind.shelf else ""))
    page = detail(context, shelf, (draft.sizes or None) if draft is not None else None) if shelf else None
    if page is None and shelf and not shelf.startswith("builtin:"):
        page = detail(context, f"builtin:{shelf}")
    if page is None:
        _fact(sheet, qp.MISSING, f"No plan on the Library's shelf builds a {kind.name}, so its materials and cost "
                                 "aren't worked out.", "the Library")
        return 0.0
    sizes = ", ".join(f"{s['label'].lower()} {s['value']:g}{(' ' + s['unit']) if s['unit'] else ''}"
                      for s in page.get("sizes", []) if isinstance(s.get("value"), (int, float)))
    _fact(sheet, qp.CALCULATION, f"The Library's \"{page['title']}\" plan" + (f" at {sizes}" if sizes else "")
          + f": {len(page.get('items', []))} materials" + ("" if draft is not None and draft.sizes else
                                                           ", at its own size until he says his") + ".", "the Library")
    shopping = page.get("shopping") or {}
    have = [r for r in shopping.get("rows", []) if r.get("have")]
    if MATERIALS in kind.touches:
        if have:
            _fact(sheet, qp.FACT, "Already on hand for it: " + "; ".join(
                f"{r['item']} ({r['have']:g} of {r['need']:g})" for r in have[:6]) + ".", "the Workshop's materials")
        else:
            _fact(sheet, qp.MISSING, "None of its materials are in the workshop's stock.", "the Workshop's materials")
    to_buy = shopping.get("to_buy", [])
    cost = float(shopping.get("known_cost") or 0)
    unpriced = len(to_buy) - int(shopping.get("priced") or 0)
    if to_buy:
        line = f"Still to buy: {len(to_buy)} of its {len(shopping.get('rows', []))} materials"
        line += f", {money(cost)} for the {shopping.get('priced', 0)} with a price" if cost else ""
        line += f"; {unpriced} have no price in the workshop yet, so the cost is a floor." if unpriced else "."
        _fact(sheet, qp.CALCULATION, line, "the Workshop's materials")
    return cost


# The part of MIA each looked-up tool reads, so a missing one is said, not a failure
_SERVICE = {"get_power_status": "power", "list_lab_series": "data_logger", "get_learning_progress": "classroom",
            "get_eggs": "flock", "list_projects": "projects", "show_my_why": "intents"}


def _area(context, sheet, kind: Kind, area: str, today: date) -> None:
    """One area of his life the project touches, through what already answers for it (water: only the rain he's
    logged and whether to water, nothing claimed about a system that wasn't checked), and its guidance line."""
    from core import question_plans as qp

    def look(context, sheet, tool: str, source: str) -> None:
        """Runs the tool when the part of MIA it reads is there (`_SERVICE`), else says it isn't set up."""
        service = _SERVICE.get(tool)
        if service and getattr(context, service, None) is None:
            _fact(sheet, qp.MISSING, f"{source[:1].upper()}{source[1:]} isn't set up here.", source)
            return
        qp._look(context, sheet, tool, source)

    if area == GROWING:
        look(context, sheet, "homestead_year", "the garden plans")
        look(context, sheet, "what_to_plant", "the garden")
    elif area == WATER:
        from core.weather_watch import rain_this_week

        rain = rain_this_week(context, today)
        if rain is None:
            _fact(sheet, qp.MISSING, "No rain logged this week.", "the rain gauge")
        else:
            _fact(sheet, qp.FACT, f"His gauge logged {rain:g} inches of rain over the last seven days.",
                  "the rain gauge")
        look(context, sheet, "should_i_water", "the garden")
    elif area == POWER:
        look(context, sheet, "get_power_status", "Power")
    elif area == ANIMALS:
        look(context, sheet, "get_eggs", "the flock")
    elif area == TIME:
        look(context, sheet, "list_projects", "Projects")
        try:
            from core.calendar_view import calendar_items

            monday = today - timedelta(days=today.weekday())
            items = calendar_items(context, monday, monday + timedelta(days=6), today)
        except Exception:  # noqa: BLE001 - the week is extra
            items = []
        if items:
            _fact(sheet, qp.CALCULATION, f"This week's calendar has {len(items)} things on it.", "Calendar")
        _fact(sheet, qp.MISSING, "How many hours the build takes him isn't recorded: when he says, it can be weighed "
                                 "against his week.", "your question")
    elif area == GOALS:
        look(context, sheet, "show_my_why", "your goals")
    elif area == RESEARCH:
        look(context, sheet, "list_lab_series", "the grow lab")
        look(context, sheet, "get_learning_progress", "learning paths")
    guidance = NEEDS.get((kind.name, area))
    if guidance:
        _fact(sheet, qp.ESTIMATE, guidance, "general guidance")


def gather(context, sheet, prompt: str, today: Optional[date] = None) -> None:
    """The project picture's gatherer: the project and what it touches (`kind_of`), each area's facts on the sheet
    (`_picture`, shared with the Planner page's `for_plan`),
    with the month's money and the freedom date gathered here for every kind that touches money (a project with no
    Library plan too), then the offer to draft the plan. A project of no known kind gets money, materials, time and
    goals."""
    from core import question_plans as qp

    today = today or date.today()
    kind = kind_of(prompt) or Kind(planned(prompt) or "project", "", "", BASIC)
    what = planned(prompt) or kind.name
    _fact(sheet, qp.FACT, f"The project he's planning: {what} (a {kind.name}). It touches: {', '.join(kind.touches)}.",
          "your words")
    draft = _started(context, sheet, kind, what)
    _picture(context, sheet, kind, draft, today)
    if draft is None and kind.shelf:
        _fact(sheet, qp.ESTIMATE, f"Nothing is planned or bought from this. He can say \"let's plan the {kind.name}\" "
                                  "and MIA drafts it at his size: the materials against what's on hand, then the "
                                  "build's steps; nothing is made until he confirms.", "how MIA works")


def _picture(context, sheet, kind: Kind, draft, today: date) -> None:
    """Every area `kind` touches onto the sheet: the build (at `draft`'s size when there is one; a garden plan's beds
    and crops instead), the month's money and the freedom date, then each other area."""
    from core import question_plans as qp

    cost = 0.0
    try:
        if draft is not None and draft.kind == "garden":
            _fact(sheet, qp.FACT, f"The garden plan: {len(draft.beds)} bed{'s' if len(draft.beds) != 1 else ''}, "
                                  f"{len(draft.crops)} crop{'s' if len(draft.crops) != 1 else ''}.", "the Planner")
        else:
            cost = _build(context, sheet, kind, draft)
    except Exception:  # noqa: BLE001 - one area failing leaves the rest
        log.exception("The project picture couldn't work out the build")
    if MONEY in kind.touches:  # the month, and the freedom date (with the known cost, when there is one)
        try:
            if qp.money_now(context, sheet, today):
                qp.freedom_with(context, sheet, cost or None, False, today, check=False)
        except Exception:  # noqa: BLE001
            log.exception("The project picture couldn't gather the money")
    for area in kind.touches:
        if area in (MONEY, MATERIALS):
            continue  # with the build
        try:
            _area(context, sheet, kind, area, today)
        except Exception:  # noqa: BLE001
            log.exception("The project picture couldn't gather %s", area)


def _allotted(context) -> list[tuple]:
    """Each confirmed build still under way (not a draft, not one whose project is Complete) with its materials laid
    against the workshop's stock in turn, oldest plan first, so stock one build counts on isn't counted again for
    the next: [(plan, rows)], each row {item, need, have, buy, cost (None without a price)}. A plan that can't be
    read is logged and left out."""
    from core.plan_library import _match, detail

    book = getattr(context, "project_plans", None)
    projects = getattr(context, "projects", None)
    stock = list(getattr(getattr(context, "materials", None), "all_materials", lambda: [])())
    left = {id(m): float(m.quantity_on_hand or 0) for m in stock}
    out = []
    plans = sorted((book.listed() if book is not None else []), key=lambda p: p.created_at or "")
    for plan in plans:
        if plan.status != "confirmed" or plan.kind != "build" or not plan.shelf_plan:
            continue
        project = projects.get_project(plan.project_id) if projects is not None and plan.project_id else None
        if project is not None and project.status == "Complete":
            continue
        try:
            items = (detail(context, plan.shelf_plan, plan.sizes or None) or {}).get("items", [])
        except Exception:  # noqa: BLE001 - one plan that can't be read leaves the rest
            log.exception("Couldn't read %s's materials", plan.title)
            continue
        rows = []
        for item in items:
            need = float(item.get("qty") or 0)
            match = _match(item["name"], stock)
            have = min(need, left[id(match)]) if match is not None else 0.0
            if match is not None:
                left[id(match)] -= have
            buy = max(0.0, need - have)
            cost = round(buy * float(match.unit_cost), 2) if match is not None and match.unit_cost and buy else None
            rows.append({"item": item["name"], "need": need, "have": have, "buy": buy, "cost": cost})
        out.append((plan, rows))
    return out


def still_to_buy(context) -> list[dict]:
    """What his confirmed builds still need from the store, each {title, cost, unpriced, items}: each build's Library
    plan at its size against the workshop's stock now, stock counted once across them (`_allotted`), so what he's
    bought and put in stock drops off. Drafts aren't counted (nothing's decided); a finished build isn't either."""
    out = []
    for plan, rows in _allotted(context):
        to_buy = [r for r in rows if r["buy"] > 0]
        if to_buy:
            out.append({"title": plan.title, "cost": round(sum(r["cost"] or 0 for r in to_buy), 2),
                        "unpriced": sum(1 for r in to_buy if r["cost"] is None), "items": len(to_buy)})
    return out


COVERED_KEY = "planner.covered"  # {plan_id: [materials it has had fully on hand]}


def gone_short(context, today: date) -> list[dict]:
    """Step 3 of the plan (a change ripples): each confirmed build with a material it once had fully on hand that it
    doesn't now (used on something else, gone into the build, or the count corrected), {kind, title, text, key} for
    core/unusual.py. Said for as long as it's short ("anything unusual?" always says what's short now); the gate
    says each once, its key naming the plan, the material and how many are on hand. What's been covered only grows
    (`COVERED_KEY`, merged plan by plan, never a plan dropped), so reading it never uses a notice up; the first check
    for a plan only remembers."""
    config = getattr(context, "config", None)
    if config is None:
        return []
    before = dict(config.get(COVERED_KEY, {}) or {})
    after, out = dict(before), []
    for plan, rows in _allotted(context):
        covered = {r["item"] for r in rows if r["need"] and r["buy"] <= 0}
        seen = set(before.get(plan.plan_id, covered))
        after[plan.plan_id] = sorted(seen | covered)
        lost = [r for r in rows if r["item"] in seen - covered]
        if lost:
            said = "; ".join(f"{r['item']} ({r['have']:g} on hand for it, it needs {r['need']:g})" for r in lost)
            out.append({"kind": "build", "title": f"{plan.title}: materials short again",
                        "text": f"What you had on hand for {plan.title} isn't all there any more: {said}. If it went "
                                "into this build, there's nothing to do; if it went to something else, it's back on "
                                "that build's list to buy.",
                        "key": f"build-{plan.plan_id}-" + "-".join(f"{r['item']}:{r['have']:g}" for r in lost)})
    if after != before:
        config.set(COVERED_KEY, after)
        config.save()
    return out


def add_still_to_buy(context, sheet) -> None:
    """The line money answers carry for his confirmed builds (`still_to_buy`), one calculation for them all, said as
    not counted in the freedom date beside it; nothing when none has anything left to buy."""
    from core.question_plans import CALCULATION
    from core.region import money

    rows = still_to_buy(context)
    if not rows:
        return
    parts = [f"{r['title']}: {r['items']} material{'s' if r['items'] != 1 else ''}"
             + (f", {money(r['cost'])} for those with a price" if r["cost"] else "")
             + (f" ({r['unpriced']} with no price yet)" if r["unpriced"] else "") for r in rows]
    total = sum(r["cost"] for r in rows)
    floor = any(r["unpriced"] for r in rows)
    sheet.add(CALCULATION, "Confirmed builds still to buy: " + "; ".join(parts) + "."
              + (f" That's {'at least ' if floor else ''}{money(total)} already spoken for (not counted in the "
                 "freedom date)." if total else ""),
              "the Planner, against the workshop's stock")


def _kind_of_plan(plan) -> Kind:
    """Pure logic. The kind a Planner plan is: a garden plan's garden; a build's by its Library plan, else by its
    title, else a project of its own name touching money, materials, time and goals."""
    if plan.kind == "garden":
        return next(k for k in KINDS if k.name == "garden")
    bare = str(plan.shelf_plan or "").split(":", 1)[-1]
    return (next((k for k in KINDS if k.shelf and k.shelf == bare), None) or _kind_in(plan.title)
            or Kind(plan.title or "project", "", "", BASIC))


def for_plan(context, plan_id: str, today: Optional[date] = None) -> list[dict]:
    """The Planner page's "What It Touches" for one plan: the same picture as asking about it (`_picture`, at the
    plan's own size), each line {kind, text, source}, said to him (`to_you`); [] for a plan that isn't there. Plans
    nothing."""
    from core.question_plans import Sheet

    book = getattr(context, "project_plans", None)
    plan = book.get(plan_id) if book is not None else None
    if plan is None:
        return []
    sheet = Sheet("project picture", "What it touches")
    _picture(context, sheet, _kind_of_plan(plan), plan, today or date.today())
    return [{"kind": f.kind, "text": to_you(f.text), "source": f.source} for f in sheet.facts]


# The sheet speaks of him to the model; his own page speaks to him
_YOU = ((r"\bHis gauge\b", "Your gauge"), (r"\buntil he says his\b", "until you say yours"),
        (r"\bwhen he says\b", "when you say"), (r"\bHe can say\b", "You can say"),
        (r"\bthe build takes him\b", "the build takes you"), (r"\bfrom rain or from him\b", "from rain or from you"),
        (r"\bhis week\b", "your week"), (r"\bhe's planning\b", "you're planning"),
        (r"\bhe confirms\b", "you confirm"), (r"\bat his size\b", "at your size"))


def to_you(text: str) -> str:
    """Pure logic. A sheet line as said to him on his own page: "His gauge logged" is "Your gauge logged"."""
    for pattern, said in _YOU:
        text = re.sub(pattern, said, text)
    return text
