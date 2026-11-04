"""
core.creation_sources
=======================

What MIA's screens may show besides their own record sets (ACAF step 2,
DEC-0088; `docs/ACAF_REVIEW.md` section 3.3). A catalogue, not free queries:
each source is a kind of history MIA already keeps (core/life_events.py),
read through `events_for()`, so it follows the same rules every screen does:
the person's own history and their household's, never anyone else's, and
money never to a child (MONEY_TYPES).

A source gives records the way a record set does (`id`, `at`, `values`), with
fixed fields, so the same blocks and the same checker work on both. It's
read-only: new eggs are still collected in Chickens, new expenses in Money.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    about: str
    types: tuple[str, ...]
    fields: tuple[dict, ...]
    picks: dict = field(default_factory=dict)  # field name -> payload key
    money: bool = False
    app: str = ""  # where its records are added


def _f(name: str, label: str, kind: str) -> dict:
    return {"name": name, "label": label, "type": kind}


DATE, WHAT = _f("date", "Date", "date"), _f("what", "What", "text")
SOURCES: dict[str, Source] = {s.id: s for s in (
    Source("eggs", "Eggs collected", "every egg collection logged in Chickens", ("eggs_collected",),
           (DATE, _f("eggs", "Eggs", "number"), WHAT), {"eggs": "eggs"}, app="Chickens"),
    Source("workouts", "Workouts", "every workout logged", ("workout_logged",),
           (DATE, _f("minutes", "Minutes", "number"), _f("sets", "Sets", "number"), WHAT),
           {"minutes": "minutes", "sets": "sets"}, app="Workout"),
    Source("meals", "Meals cooked", "every meal logged in Kitchen", ("meal_logged",), (DATE, WHAT), app="Kitchen"),
    Source("maintenance", "Upkeep done", "every maintenance task done", ("maintenance_done",), (DATE, WHAT),
           app="Maintenance"),
    Source("missions", "Missions completed", "every mission finished", ("mission_completed",),
           (DATE, _f("xp", "XP", "number"), WHAT), {"xp": "xp"}, app="Missions"),
    Source("spending", "Spending", "every expense in Money", ("expense_added",),
           (DATE, _f("amount", "Amount", "money"), _f("category", "Category", "text"), WHAT),
           {"amount": "amount", "category": "category"}, money=True, app="Money"),
    Source("bills_paid", "Bills paid", "every bill marked paid", ("bill_paid",),
           (DATE, _f("amount", "Amount", "money"), WHAT), {"amount": "amount"}, money=True, app="Money"),
)}


# Words that mean a need is about one of these: code points the model at it (a 14b model, asked to
# track eggs, would happily start a new egg log beside the one Chickens keeps).
WORDS = {"eggs": ("egg", "eggs", "laying", "lay"), "workouts": ("workout", "workouts", "exercise", "training", "gym"),
         "meals": ("meal", "meals", "cooked", "cooking", "dinners"), "maintenance": ("maintenance", "upkeep"),
         "missions": ("mission", "missions"), "spending": ("spend", "spending", "spent", "expenses", "expense"),
         "bills_paid": ("bill", "bills")}


def matching(need: str, child: bool = False) -> list[str]:
    """Pure logic. The sources a need is about, by its words."""
    import re

    words = set(re.findall(r"[a-z]+", (need or "").lower()))
    return [s.id for s in listing(child) if words & set(WORDS.get(s.id, ()))]


def listing(child: bool = False) -> list[Source]:
    return [s for s in SOURCES.values() if not (child and s.money)]


def fields_of(source_id: str) -> list[dict]:
    return [dict(f) for f in SOURCES[source_id].fields]


def records(context, source_id: str, limit: int = 2000) -> list[dict]:
    """The source's records, oldest first (as a record set keeps them)."""
    from core.child_accounts import is_child
    from core.life_events import events_for

    source = SOURCES[source_id]
    if source.money and getattr(context, "config", None) is not None and is_child(context):
        return []
    out = []
    for e in events_for(context, types=source.types)[:limit]:
        values = {"date": str(e.payload.get("date") or e.at)[:10], "what": e.summary}
        for name, key in source.picks.items():
            value = e.payload.get(key)
            values[name] = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else value
        out.append({"id": e.event_id, "at": e.at, "values": values})
    return list(reversed(out))


def describe(child: bool = False) -> str:
    """For MIA's prompt: what she can show without a record set of its own."""
    return "\n".join(f"  - {s.id}: {s.title} ({s.about}); fields: " + ", ".join(
        f"{f['name']} ({f['type']})" for f in s.fields) for s in listing(child))


def source_of(spec: dict) -> Optional[Source]:
    return SOURCES.get(str(spec.get("source") or "").removeprefix("history:")) if spec.get("source") else None
