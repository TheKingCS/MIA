"""
core.life_milestones
======================

What his homestead life has added up to, read from the records, for the achievements (the game layer, Zac
2026-11-24: "grow 1000 pounds of produce, built the greenhouse, built the chicken coop, harvested 100 dozen eggs").
Nothing here is kept twice: each number is worked out now from the store that already holds it, the same "derive it"
rule core/rewards_manager.py follows, and an undone record stops counting.

**Lifetime counts** (`produce_pounds`, `eggs_collected`, `jars_canned`): every harvest weighed in pounds, ounces,
kilograms or grams in the grow lab, and the greenhouse node's produce harvests MIA keeps (core/grow_lab.py,
core/greenhouse_link.keep_harvests; a harvest counted in heads or bunches has no weight and isn't guessed
at), every egg logged in the flock book (core/flock.py), and every jar put up on the canning shelf
(core/canning_shelf.py records a `canned` life event with its jar count, because a jar eaten leaves the pantry; an
undone one is dropped by `life_events.reversed_ids`).

**The business and the money** (`sales_made`, `debts_paid_off`, 2026-11-24, brainstorm round 9): each sale in the
workshop's ledger, and each debt paid down to nothing (a debt_payment event that left 0, one per debt).

**Structures built** (`STRUCTURES`, `built`, `structure_of`): one-time milestones, each earned when a project that
built it is marked Complete in the Workshop (core/project_manager.py): its name is just the structure ("Greenhouse")
or says it was built ("Build the chicken coop", "Install solar"), never one about mending, moving or a part of one
("Painting the shed", "Greenhouse automation"), and one project builds one structure. An unlock is for good, so a
name that doesn't say it plainly earns nothing.
Read by core/rewards_manager.py, which unlocks and celebrates them like every other reward.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.logger import get_logger

log = get_logger(__name__)

POUNDS = {"lb": 1.0, "oz": 1 / 16, "kg": 2.20462, "g": 0.00220462}  # a harvest's unit (core.harvest_log.unit_of) to pounds


def produce_pounds(context) -> float:
    """Every harvest in the grow lab that was weighed, in pounds (lb, oz, kg and g converted; heads, bunches and counts
    have no weight and are left out, never guessed), and the greenhouse node's produce harvests MIA kept
    (core/greenhouse_link.keep_harvests; a fish harvest isn't produce). 0 without either."""
    from core import life_events
    from core.harvest_log import unit_of

    lab = getattr(context, "grow_lab", None)
    total = 0.0
    for batch in (lab.batches if lab is not None else []):
        for harvest in batch.harvests or []:
            factor = POUNDS.get(unit_of(str(harvest.get("unit", ""))))
            try:
                total += float(harvest.get("amount") or 0) * factor if factor else 0.0
            except (TypeError, ValueError):
                continue
    try:
        node = life_events.events_for(context, types=("greenhouse_harvest",))
    except Exception:  # noqa: BLE001 - a history that can't be read leaves the node's part out
        node = []
    for e in node:
        factor = POUNDS.get(unit_of(str(e.payload.get("unit", ""))))
        if factor and e.payload.get("kind") != "harvest_fish":
            try:
                total += float(e.payload.get("quantity") or 0) * factor
            except (TypeError, ValueError):
                continue
    return round(total, 2)


def eggs_collected(context) -> float:
    """Every egg logged as collected in the flock book, all flocks together. 0 without one."""
    flock = getattr(context, "flock", None)
    return float(sum(e.count or 0 for e in (flock.entries if flock is not None else []) if e.kind == "eggs"))


def jars_canned(context) -> float:
    """Every jar put up on the canning shelf, from its `canned` life events (an undone batch is dropped)."""
    from core import life_events

    try:
        events = life_events.events_for(context, types=("canned", "undone"))
    except Exception:  # noqa: BLE001 - a history that can't be read counts nothing
        log.exception("Couldn't read the canning history")
        return 0.0
    undone = life_events.reversed_ids(events)
    total = 0.0
    for event in events:
        if event.type == "canned" and event.event_id not in undone:
            try:
                total += float(event.payload.get("jars") or 0)
            except (TypeError, ValueError):
                continue
    return total


def sales_made(context) -> float:
    """Every sale in the workshop's ledger (core/ledger_manager.py): each revenue entry of more than nothing."""
    ledger = getattr(context, "ledger", None)
    return float(sum(1 for r in (ledger.all_revenue() if ledger is not None else []) if (r.amount or 0) > 0))


def debts_paid_off(context) -> float:
    """Each debt paid down to nothing, from his history: a debt_payment event that left a balance of 0 (core/
    budget_manager.py records it), one per debt, an undone payment dropped."""
    from core import life_events

    try:
        events = life_events.events_for(context, types=("debt_payment", "undone"))
    except Exception:  # noqa: BLE001 - a history that can't be read counts nothing
        log.exception("Couldn't read the debt payments")
        return 0.0
    undone = life_events.reversed_ids(events)
    cleared = set()
    for e in events:
        if e.type != "debt_payment" or e.event_id in undone:
            continue
        try:
            balance = float(e.payload.get("balance"))
        except (TypeError, ValueError):
            continue
        debt = next((r for r in e.refs if r.startswith("debt:")), "")
        if balance <= 0.005 and debt:
            cleared.add(debt)
    return float(len(cleared))


@dataclass(frozen=True)
class Structure:
    """A structure whose building is a milestone: its stable reward id (kept on the profile once unlocked, so it never
    changes), its name, what it says, its icon, its rarity (0 Common to 4 Legendary, core/rarity.py), and the words a
    project's name uses for it."""
    reward_id: str
    name: str
    description: str
    icon: str
    rarity_index: int
    words: str


STRUCTURES: tuple[Structure, ...] = (
    Structure("built_greenhouse", "Glass and Green", "Built the greenhouse.", "🌿", 4,
              r"greenhouses?|glasshouses?|hoop ?houses?|high tunnels?|poly ?tunnels?|grow tunnels?"),
    Structure("built_aquaponics", "Fish and Greens", "Built the aquaponics system.", "🐟", 4,
              r"aquaponics?(?: system| setup)?"),
    Structure("built_chicken_coop", "Rule the Roost", "Built the chicken coop.", "🐔", 3,
              r"(?:chicken )?coops?|hen ?houses?|chicken houses?|chicken tractors?"),
    Structure("built_barn", "Raised the Barn", "Built the barn.", "🏚️", 4, r"(?:pole )?barns?"),
    Structure("built_shed", "Shed Raiser", "Built a shed.", "🛖", 2, r"(?:storage |garden |tool )?sheds?"),
    Structure("built_garage", "Bay Builder", "Built the garage.", "🚘", 3, r"garages?|carports?"),
    Structure("built_workshop", "The Workshop", "Built the workshop.", "🛠️", 3, r"workshops?|shop buildings?"),
    Structure("built_cold_room", "Cold Keeper", "Built the cold room or root cellar.", "🧊", 3,
              r"cold rooms?|root cellars?|walk-?in coolers?"),
    Structure("built_power_station", "Off the Grid", "Built the solar or power station.", "☀️", 4,
              r"solar(?: arrays?| panels?| systems?| power)?|power stations?|battery banks?|power systems?"),
    Structure("built_water_system", "Water Keeper", "Built the rain catchment or water system.", "💧", 3,
              r"rain ?catchment|cisterns?|rain ?barrels?|water systems?|irrigation(?: systems?)?"),
    Structure("built_well_pump", "Wellspring", "Put in the well pump.", "🚰", 3, r"well pumps?|water wells?|wells?"),
    Structure("built_raised_beds", "Bed Maker", "Built the raised beds.", "🪴", 1, r"raised beds?|garden beds?"),
    Structure("built_orchard", "Orchardist", "Planted the orchard.", "🍎", 3, r"orchards?"),
    Structure("built_fence", "Good Fences", "Built the fence.", "🚧", 1, r"fences?|fencing"),
)

# A project that builds one says so: a build verb ("Build the chicken coop", "Install solar"), or its name is just
# the structure ("Greenhouse", "The new barn").
_BUILD = re.compile(r"\b(?:build|built|building|raise|raising|construct\w*|erect\w*|install\w*|put (?:in|up)|"
                    r"set(?:ting)? up|plant\w*|dig\w*|drill\w*|frame|framing|pour\w*)\b", re.I)
_JUST = r"^\s*(?:(?:the|a|an|my|our|new|first|second|big|small)\s+)*(?:{words})\s*$"
# Words that make it about mending, moving or a part of one, never building it: "Painting the shed", "Greenhouse
# automation", "Barn door hardware". Stem-aware, so "repairing" and "winterize" are caught.
_NOT_A_BUILD = re.compile(r"\b(?:repair|fix|paint|clean|re-?roof|insulat|organi[sz]|tear\w* down|demolish|mov|sell|"
                          r"sold|winteriz|replac|prun|weed|harvest|automat|sensor|controller|door|opener|hardware|"
                          r"bench|roof|light|wiring|wire|shelv|shelf|join|upgrad|maintain|maintenance|inspect|"
                          r"stain|seal|patch|empty|restock)\w*", re.I)


def structure_of(name: str):
    """Pure logic. The one structure a project's name says it builds, or None: its name is only the structure, or a
    build verb is followed by one (the first named after the verb: "Install solar panels for the shed" built the
    power, not the shed), and nothing in it says mending, moving or a part (`_NOT_A_BUILD`)."""
    name = " ".join(str(name or "").split())
    if not name or _NOT_A_BUILD.search(name):
        return None
    for s in STRUCTURES:
        if re.match(_JUST.format(words=s.words), name, re.I):
            return s
    verb = _BUILD.search(name)
    if verb is None:
        return None
    after = name[verb.end():]
    found = [(m.start(), s) for s in STRUCTURES for m in [re.search(rf"\b(?:{s.words})\b", after, re.I)] if m]
    return min(found, key=lambda f: f[0])[1] if found else None


def _names(structure: Structure, name: str) -> bool:
    """Pure logic. Whether a project's name says it built this structure (`structure_of`)."""
    return structure_of(name) is structure


def built(context, reward_id: str) -> bool:
    """Whether a project that built this structure is marked Complete (the household's Workshop projects). False for
    a reward id that isn't a structure, or without projects."""
    structure = next((s for s in STRUCTURES if s.reward_id == reward_id), None)
    projects = getattr(context, "projects", None)
    if structure is None or projects is None:
        return False
    return any(p.status == "Complete" and _names(structure, p.name) for p in projects.all_projects())
