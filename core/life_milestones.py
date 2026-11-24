"""
core.life_milestones
======================

What his homestead life has added up to, read from the records, for the achievements (the game layer, Zac
2026-11-24: "grow 1000 pounds of produce, built the greenhouse, built the chicken coop, harvested 100 dozen eggs").
Nothing here is kept twice: each number is worked out now from the store that already holds it, the same "derive it"
rule core/rewards_manager.py follows, and an undone record stops counting.

**Lifetime counts** (`produce_pounds`, `eggs_collected`, `jars_canned`): every harvest weighed in pounds, ounces or
kilograms in the grow lab (core/grow_lab.py; a harvest counted in heads or bunches has no weight and isn't guessed
at), every egg logged in the flock book (core/flock.py), and every jar put up on the canning shelf
(core/canning_shelf.py records a `canned` life event with its jar count, because a jar eaten leaves the pantry; an
undone one is dropped by `life_events.reversed_ids`).

**Structures built** (`STRUCTURES`, `built`): one-time milestones, each earned when a project whose name says that
structure ("Greenhouse", "Build the chicken coop") is marked Complete in the Workshop (core/project_manager.py).
Read by core/rewards_manager.py, which unlocks and celebrates them like every other reward.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.logger import get_logger

log = get_logger(__name__)

POUNDS = {"lb": 1.0, "oz": 1 / 16, "kg": 2.20462}  # a harvest's unit (core.harvest_log.unit_of) to pounds


def produce_pounds(context) -> float:
    """Every harvest in the grow lab that was weighed, in pounds (lb, oz and kg converted; heads, bunches and counts
    have no weight and are left out, never guessed). 0 without a grow lab."""
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
              r"greenhouse|hoop ?house|high tunnel|poly ?tunnel|grow tunnel"),
    Structure("built_aquaponics", "Fish and Greens", "Built the aquaponics system.", "🐟", 4, r"aquaponics?"),
    Structure("built_chicken_coop", "Rule the Roost", "Built the chicken coop.", "🐔", 3,
              r"chicken coop|coop|hen ?house|chicken house"),
    Structure("built_barn", "Raised the Barn", "Built the barn.", "🏚️", 4, r"barn|pole barn"),
    Structure("built_shed", "Shed Raiser", "Built a shed.", "🛖", 2, r"shed"),
    Structure("built_garage", "Bay Builder", "Built the garage.", "🚘", 3, r"garage|carport"),
    Structure("built_workshop", "The Workshop", "Built the workshop.", "🛠️", 3, r"workshop|shop building"),
    Structure("built_cold_room", "Cold Keeper", "Built the cold room or root cellar.", "🧊", 3,
              r"cold room|root cellar|walk-?in cooler"),
    Structure("built_power_station", "Off the Grid", "Built the solar or power station.", "☀️", 4,
              r"solar (?:array|panels?|system|power)|power station|battery bank|power system"),
    Structure("built_water_system", "Water Keeper", "Built the rain catchment or water system.", "💧", 3,
              r"rain ?catchment|cistern|rain ?barrels?|water system|irrigation"),
    Structure("built_well_pump", "Wellspring", "Put in the well pump.", "🚰", 3, r"well pump|water well|(?:drill|dig)(?:ing)? (?:a |the )?well"),
    Structure("built_raised_beds", "Bed Maker", "Built the raised beds.", "🪴", 1, r"raised beds?|garden beds?"),
    Structure("built_orchard", "Orchardist", "Planted the orchard.", "🍎", 3, r"orchard"),
    Structure("built_fence", "Good Fences", "Built the fence.", "🚧", 1, r"fence|fencing"),
)

# Words that mean the project is about the structure, not building it ("Repair the shed roof" built no shed).
_NOT_A_BUILD = re.compile(r"\b(?:repair|fix|paint|clean|re-?roof|insulate|organi[sz]e|tear down|demolish|move|sell)\b",
                          re.I)


def _names(structure: Structure, name: str) -> bool:
    """Pure logic. Whether a project's name says this structure (whole words) and isn't about mending or moving one."""
    return bool(re.search(rf"\b(?:{structure.words})\b", name or "", re.I)) and not _NOT_A_BUILD.search(name or "")


def built(context, reward_id: str) -> bool:
    """Whether a project naming this structure is marked Complete (the household's Workshop projects). False for a
    reward id that isn't a structure, or without projects."""
    structure = next((s for s in STRUCTURES if s.reward_id == reward_id), None)
    projects = getattr(context, "projects", None)
    if structure is None or projects is None:
        return False
    return any(p.status == "Complete" and _names(structure, p.name) for p in projects.all_projects())
