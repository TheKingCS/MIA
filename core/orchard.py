"""
core.orchard
==============

The orchard (Zac, 2026-11-24: "will manage my orchard"; docs/future/SMART_AG_PLAN.md phase A1). Before this MIA had
nothing for fruit trees.

**His trees** are Maintenance assets (one owner for every physical thing he looks after, DEC-0153), in the
"Garden/Plant" category or any other, named as he'd say them: "Honeycrisp apple tree", "2 Elberta peaches by the
barn". `trees` finds them by the fruit kind in their name (`KINDS`: apple, pear, peach, nectarine, plum, sweet and
sour cherry, apricot, fig, persimmon, pawpaw, mulberry), with how many and the variety where the name gives them.

**What each kind needs** (`KINDS`): chill hours, years to first fruit, whether it needs a second variety to pollinate,
spacing, when it's pruned, and roughly how many days from bloom to ripe. These are the usual extension-service
figures, said as general guidance, never as his trees' facts; his own variety's tag or nursery comes first.

**The orchard's year** (`calendar`): each job dated from his last spring frost (`garden.last_frost`, the same date
the garden uses): dormant pruning (late winter; peaches and other stone fruit later, near bloom), dormant oil
before bud break, bloom and the frost watch, thinning a few weeks after bloom, summer pruning of water sprouts,
harvest by each kind's days from bloom, and fall cleanup and trunk guards before his first frost. Without a frost
date it says so and asks, never assumes one.

**What it says** (`say_month`, the tool `orchard_this_month`): the orchard's jobs in the next 30 days for the kinds
he has, with their dates and which trees, and a kind that needs a pollination partner he doesn't have (one variety
alone). `say_kind` (the tool `fruit_tree_facts`): one kind's needs. Read-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass(frozen=True)
class Kind:
    """One fruit: its name, the words that name it, chill hours (low, high), years to first fruit (dwarf, standard),
    whether one variety alone sets fruit, spacing in feet (dwarf, standard), whether it's stone fruit (pruned near
    bloom, not in deep winter), and days from bloom to ripe (early, late)."""
    name: str
    words: str
    chill: tuple
    bearing: tuple
    self_fruitful: bool
    spacing: tuple
    stone: bool
    ripe_days: tuple


KINDS: tuple[Kind, ...] = (
    Kind("apple", r"apples?|crab ?apples?", (500, 1000), (2, 7), False, (8, 25), False, (100, 180)),
    Kind("pear", r"pears?", (600, 1000), (3, 7), False, (10, 25), False, (100, 150)),
    Kind("peach", r"peach(?:es)?", (400, 1000), (2, 4), True, (12, 20), True, (90, 130)),
    Kind("nectarine", r"nectarines?", (400, 1000), (2, 4), True, (12, 20), True, (90, 130)),
    Kind("plum", r"plums?|prunes?", (500, 1000), (3, 6), False, (10, 20), True, (90, 120)),
    Kind("sweet cherry", r"sweet cherr(?:y|ies)|bing cherr(?:y|ies)|cherr(?:y|ies)", (700, 1100), (4, 7), False,
         (12, 30), True, (60, 75)),
    Kind("sour cherry", r"sour cherr(?:y|ies)|tart cherr(?:y|ies)|pie cherr(?:y|ies)|montmorency", (700, 1100),
         (3, 5), True, (10, 20), True, (55, 70)),
    Kind("apricot", r"apricots?", (300, 900), (3, 5), True, (12, 20), True, (90, 120)),
    Kind("fig", r"figs?", (100, 300), (1, 3), True, (10, 20), False, (60, 90)),
    Kind("persimmon", r"persimmons?", (100, 400), (3, 6), True, (15, 25), False, (150, 180)),
    Kind("pawpaw", r"paw ?paws?", (400, 900), (4, 7), False, (8, 15), False, (130, 160)),
    Kind("mulberry", r"mulberr(?:y|ies)", (400, 800), (2, 4), True, (15, 30), False, (45, 60)),
)
_TREE_WORDS = re.compile(r"\b(trees?|orchard|dwarf|semi-dwarf|standard)\b", re.I)


# The fruit's own noun, so a variety named in the fruit's words ("Bing cherry") stays the variety
_FRUIT_NOUN = re.compile(r"(?<![a-z])(?:crab ?apples?|apples?|pears?|peach(?:es)?|nectarines?|plums?|prunes?|"
                         r"cherr(?:y|ies)|apricots?|figs?|persimmons?|paw ?paws?|mulberr(?:y|ies))(?![a-z])", re.I)


def kind_in(name: str) -> Optional[Kind]:
    """Pure logic. The fruit a name holds ("Honeycrisp apple tree" is an apple; sour cherry before sweet), or None."""
    lowered = (name or "").lower()
    found = [k for k in KINDS if re.search(rf"(?<![a-z])(?:{k.words})(?![a-z])", lowered)]
    if not found:
        return None
    return next((k for k in found if k.name == "sour cherry"), found[0])


def _count(name: str) -> int:
    """Pure logic. How many trees a name says ("2 Elberta peaches", "three plums"); 1 when it doesn't."""
    m = re.match(r"\s*(\d+|two|three|four|five|six)\b", (name or "").lower())
    if not m:
        return 1
    return {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}.get(m.group(1)) or int(m.group(1))


def _variety(name: str, kind: Kind) -> str:
    """Pure logic. The variety a name gives before its fruit ("Honeycrisp" in "Honeycrisp apple tree"), or ""."""
    before = _FRUIT_NOUN.split(name, maxsplit=1)[0]  # the fruit's own noun: "Bing" stays the variety of a cherry
    before = re.sub(r"^\s*(\d+|two|three|four|five|six)\b", "", before, flags=re.I)
    before = re.sub(r"\b(sweet|sour|tart|pie)\b", "", before, flags=re.I)
    before = _TREE_WORDS.sub("", before).strip(" ,-")
    return before


def trees(context) -> list[dict]:
    """His fruit trees from Maintenance: [{name, kind, variety, count, asset_id}], by the fruit in each asset's name;
    [] without Maintenance or trees."""
    maintenance = getattr(context, "maintenance", None)
    out = []
    for asset in (maintenance.all_assets() if maintenance is not None else []):
        kind = kind_in(asset.name)
        if kind is None:
            continue
        out.append({"name": asset.name, "kind": kind, "variety": _variety(asset.name, kind),
                    "count": _count(asset.name), "asset_id": asset.asset_id})
    return out


def _last_frost(context, today: date) -> Optional[date]:
    """His last spring frost for the season ahead (core/planting_now._frost: the same date the garden uses)."""
    from core.planting_now import _frost

    return _frost(context, today)


def calendar(kinds: list[Kind], last_frost: date, first_frost: Optional[date] = None) -> list[tuple]:
    """Pure logic. The orchard's year for these kinds: [(day, job, kinds)] in date order, from the last spring frost
    (bloom is taken as two weeks before it, the frost watch the weeks around it) and, for the fall jobs, the first."""
    if not kinds:
        return []
    bloom = last_frost - timedelta(days=14)
    pome = [k.name for k in kinds if not k.stone]
    stone = [k.name for k in kinds if k.stone]
    jobs = []
    if pome:
        jobs.append((last_frost - timedelta(days=70), "Dormant pruning, on a dry day above freezing", pome))
    if stone:
        jobs.append((bloom - timedelta(days=10), "Prune stone fruit near bloom (less disease than in deep winter)",
                     stone))
    every = [k.name for k in kinds]
    jobs.append((last_frost - timedelta(days=42), "Dormant oil spray before bud break, above 40°F with no rain due",
                 every))
    jobs.append((bloom, "Bloom: watch the frost forecast; cover small trees on a frosty night", every))
    jobs.append((bloom + timedelta(days=35), "Thin fruit to one every 6 to 8 inches once it has set", [
        k.name for k in kinds if k.name in ("apple", "pear", "peach", "nectarine", "plum", "apricot")] or every))
    jobs.append((date(last_frost.year, 7, 15), "Summer pruning: cut water sprouts and suckers", every))
    for k in kinds:
        jobs.append((bloom + timedelta(days=k.ripe_days[0]), f"{k.name.capitalize()} harvest can begin (to about "
                     f"{(bloom + timedelta(days=k.ripe_days[1])):%B %d})", [k.name]))
    fall = (first_frost - timedelta(days=14)) if first_frost else date(last_frost.year, 10, 15)
    jobs.append((fall, "Fall cleanup: rake dropped fruit and leaves, trunk guards against mice and rabbits", every))
    return sorted(jobs, key=lambda j: j[0])


def pollination_gaps(found: list[dict]) -> list[str]:
    """Pure logic. The kinds he has only one variety of that need a second to set fruit."""
    gaps = []
    for kind in {t["kind"] for t in found if not t["kind"].self_fruitful}:
        varieties = {t["variety"].lower() for t in found if t["kind"] == kind}
        if len(varieties) < 2:
            gaps.append(kind.name)
    return sorted(gaps)


def say_month(context, today: Optional[date] = None) -> str:
    """The orchard's jobs in the next 30 days for the kinds he has, each with its day and his trees, and a kind
    missing its pollination partner; or what's needed first (trees, his frost date)."""
    from core.planting_now import _first_frost

    today = today or date.today()
    found = trees(context)
    if not found:
        return ("No fruit trees in your records yet. Add each one in Maintenance with its fruit in the name, like "
                "\"Honeycrisp apple tree\" or \"2 Elberta peaches\", and I'll keep the orchard's year.")
    frost = _last_frost(context, today)
    if frost is None:
        return ("I need your last spring frost to date the orchard's work: tell me (\"my last frost is April 20\"). "
                f"You have {len(found)} fruit tree entries.")
    kinds = sorted({t["kind"] for t in found}, key=lambda k: k.name)
    jobs = []
    for year_frost in (frost - timedelta(days=365), frost):  # the season now ending and the one ahead
        first = _first_frost(context, year_frost)
        jobs += [j for j in calendar(kinds, year_frost, first) if today <= j[0] <= today + timedelta(days=30)]
    parts = []
    for day, job, names in sorted(jobs, key=lambda j: j[0]):
        which = ", ".join(t["name"] for t in found if t["kind"].name in names)
        parts.append(f"{day:%B} {day.day}: {job} ({which})")
    out = ("The orchard in the next 30 days: " + "; ".join(parts) + "."
           if parts else "Nothing in the orchard's calendar falls in the next 30 days.")
    gaps = pollination_gaps(found)
    if gaps:
        out += (" " + ", ".join(gaps).capitalize() + (" needs" if len(gaps) == 1 else " need") + " a second variety "
                "nearby to set fruit, and your records show only one.")
    return out + " Dates are general guidance from your frost date: the buds on your own trees come first."


def say_kind(name: str) -> str:
    """One fruit's needs, as general guidance."""
    kind = kind_in(name)
    if kind is None:
        return "Which fruit? I know " + ", ".join(k.name for k in KINDS) + "."
    return (f"{kind.name.capitalize()} trees need about {kind.chill[0]} to {kind.chill[1]} chill hours (below 45°F "
            f"over winter); they bear in {kind.bearing[0]} to {kind.bearing[1]} years (dwarf sooner); "
            + ("one variety alone sets fruit" if kind.self_fruitful else "they need a second variety nearby to "
               "pollinate") + f"; space them {kind.spacing[0]} to {kind.spacing[1]} feet apart (dwarf to standard); "
            + ("prune near bloom, as stone fruit" if kind.stone else "prune while dormant in late winter")
            + f"; fruit ripens about {kind.ripe_days[0]} to {kind.ripe_days[1]} days after bloom. These are usual "
            "figures; your variety's tag or nursery comes first.")
