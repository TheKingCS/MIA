"""
core.record_types
=================

The record-type registry (LS-05, docs/mia_os/MIA_UNIVERSAL_RUNTIME_CONTRACTS.md section 3): one table of every kind
of record MIA keeps that a `kind:id` reference can name, with its store, how to list it, and its id and name fields.
Links (core/links.py) point at these, the history's refs name them, and the read-back after a change
(core/read_back.py) uses them to see that what a change says it touched is still there.

`HISTORY_ONLY` lists the kinds the history names that can't be read by id yet, each with why, so the read-back skips
them; `tests/test_record_types.py` fails on a kind the history names that is in neither list. Moving one from
`HISTORY_ONLY` into `TYPES` is how a kind becomes readable.

Pure lookups: nothing here writes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class RecordType:
    """One kind of record MIA keeps (an asset, a mission, a person...): its name (the `kind` in a `kind:id` ref)
    and label, the store (an AppContext attribute) and the method or attribute that lists them, and which
    attributes are its id and its name, and any other store a ref of that kind may be in.
    """
    kind: str
    label: str
    store: str  # AppContext attribute
    lister: str  # method returning the records
    id_attr: str
    name_attr: str = "name"
    read_also: tuple = ()  # more stores read() looks in for the same ref kind (a person's own record sets)


TYPES: dict[str, RecordType] = {k.kind: k for k in (
    RecordType("property", "property", "real_estate", "all_properties", "property_id"),
    RecordType("asset", "vehicle, tool or appliance", "maintenance", "all_assets", "asset_id"),
    RecordType("maintenance_task", "maintenance task", "maintenance", "all_tasks", "task_id", "title"),
    RecordType("bill", "bill", "budget", "all_bills", "bill_id"),
    RecordType("debt", "debt", "budget", "all_debts", "debt_id"),
    RecordType("income_source", "income source", "budget", "all_income_sources", "source_id"),
    RecordType("business", "business", "budget", "all_business_entities", "entity_id"),
    RecordType("project", "project", "projects", "all_projects", "project_id"),
    RecordType("task", "task", "tasks", "all_tasks", "task_id", "title"),
    RecordType("intent", "goal", "intents", "all_intents", "intent_id"),
    RecordType("mission", "mission", "missions", "all_missions", "mission_id"),
    RecordType("skill", "skill", "skills", "all_skills", "skill_id"),
    RecordType("person", "person", "relationships", "all_people", "person_id"),
    RecordType("pet", "pet", "relationships", "all_pets", "pet_id"),
    RecordType("recipe", "recipe", "kitchen", "all_recipes", "recipe_id"),
    RecordType("profile", "account", "profiles", "list_profiles", "profile_id"),
    # 2026-11-07 (DEC-0108's interconnection audit): the rest of the records a life is made of, so they can depend
    # on, serve, block or belong to each other. The kind names match the refs their stores' life events carry.
    RecordType("calendar_event", "event", "calendar", "all_events", "event_id", "title"),
    RecordType("inventory_item", "item", "inventory", "all_items", "item_id"),
    RecordType("component", "part", "components", "all_components", "component_id"),
    RecordType("material", "material", "materials", "all_materials", "material_id"),
    RecordType("product", "product", "products", "all_products", "product_id"),
    RecordType("job", "job", "jobs", "all_jobs", "job_id"),
    RecordType("craft_recipe", "workshop recipe", "craft_recipes", "all_recipes", "recipe_id"),
    RecordType("waypoint", "waypoint", "waypoints", "all_waypoints", "waypoint_id"),
    RecordType("trip", "trip", "trips", "all_trips", "trip_id"),
    RecordType("expedition", "expedition", "expeditions", "all_expeditions", "expedition_id"),
    RecordType("textbook", "book", "textbooks", "all_books", "book_id", "title"),
    RecordType("energy_source", "energy source", "energy", "all_energy_sources", "source_id"),
    RecordType("journal_entry", "journal entry", "journal", "all_entries", "entry_id", "title"),
    RecordType("reward", "reward", "reward_shop", "all_rewards", "reward_id"),
    RecordType("script", "script", "scripts", "all_scripts", "script_id"),
    RecordType("place", "place", "places", "places", "place_id"),
    RecordType("obligation", "obligation", "obligations", "obligations", "obligation_id", "title"),
    RecordType("policy", "insurance policy", "insurance", "policies", "policy_id", "insurer"),
    RecordType("customer", "customer", "business", "customers", "customer_id"),
    RecordType("flock", "flock", "flock", "flocks", "flock_id"),
    # 2026-11-09, the self-audit's links column: what a person may want to tie to a goal, project or debt.
    RecordType("subject", "class subject", "classroom", "all_subjects", "subject_id"),
    RecordType("workout_template", "workout", "workout", "all_templates", "template_id"),
    RecordType("grow_batch", "grow-lab batch", "grow_lab", "batches", "batch_id", "crop"),
    RecordType("questline", "questline", "quest_book", "quests", "quest_id"),
    RecordType("workplace", "workplace", "dungeon", "dungeons", "dungeon_id"),
    RecordType("direction", "direction", "direction", "directions", "direction_id", "title"),
    RecordType("campaign", "campaign", "living_worlds", "campaigns", "campaign_id"),
    RecordType("inbox_item", "letter or document", "inbox", "all_items", "item_id", "subject"),
    RecordType("plan", "build plan", "plans", "plans", "id", "title"),  # these four keep dicts
    RecordType("creation", "creation", "creations", "items", "id", "title"),
    RecordType("note", "note", "life_notes", "notes", "id", "what"),  # the refs their history already uses
    RecordType("track", "GPS track", "gps_tracks", "tracks", "id"),
    RecordType("shop_expense", "shop expense", "ledger", "all_expenses", "entry_id", "description"),  # history's refs
    RecordType("shop_revenue", "shop sale or income", "ledger", "all_revenue", "entry_id", "description"),
    RecordType("rhythm", "rhythm of the week", "loop", "rhythms", "rhythm_id"),
    RecordType("record_set", "household record set", "record_sets", "sets", "id",
               read_also=("my_record_sets",)),  # the person's own sets record record_set: refs too
    RecordType("my_record_set", "record set", "my_record_sets", "sets", "id"),
    RecordType("play", "game or sport played", "recreation", "entries", "id", "what"),
    RecordType("picture", "picture MIA painted", "art", "items", "id", "description"),
)}


# The kinds the history's refs use that can't be read back by id yet: why each, so the read-back skips it.
HISTORY_ONLY: dict[str, str] = {
    "alarm": "alarms live in the alarm manager's own list; no lister by id yet",
    "browser_routine": "a routine's file is per person and read through the browser's own store",
    "business_use": "a business-use split is a field on another record, not a record of its own",
    "camera": "cameras are device settings, not a household store",
    "character": "Living Worlds characters live inside a campaign",
    "course": "Classroom courses live inside the person's Classroom store, by subject",
    "dungeon": "the work dungeon's floors are inside the dungeon store; links call it workplace",
    "email_draft": "drafts are per person and leave when sent or discarded",
    "expense": "a budget or rental expense is an entry inside its own ledger, no lister by id yet",
    "income": "an income entry is inside its ledger, no lister by id yet",
    "insurance_quote": "quotes live inside a policy's comparison",
    "lesson": "Classroom lessons live inside a course",
    "market": "a market day is inside the business book",
    "meal": "a meal plan entry is inside the kitchen's week",
    "memory": "his memories are personal and read through their own store, never listed for links",
    "operating_line": "a line of the operating journal is an append-only entry",
    "order": "an order is inside the business book",
    "path": "learning paths are read through core/paths.py by id, not a store on the context",
    "played": "the history says played:, links call the same record play:",
    "quest": "Living Worlds quests and questline steps are inside their campaign or questline",
    "quote": "a business quote is inside the business book",
    "style": "a response style is a setting, not a record",
    "universe": "a Living Worlds universe is inside the campaign store",
    "version": "a version of a world or dungeon is a snapshot inside its record",
    "workout": "a logged workout is an entry in the person's workout log; links point at the template",
}


def field_of(record, attr: str, default=""):
    """One field of a record, whether the store keeps objects or dicts (a plan, a creation, a note)."""
    return record.get(attr, default) if isinstance(record, dict) else getattr(record, attr, default)


def records_of(context, kind: RecordType) -> list:
    """Every record of a kind, from its store (a method that lists them, or a list or dict the store keeps: a dict
    gives its values); [] (logged) when the store is missing or fails."""
    store = getattr(context, kind.store, None)
    lister: Optional[Callable] = getattr(store, kind.lister, None)
    if lister is None:
        return []
    try:
        found = lister() if callable(lister) else lister
        return list(found.values() if isinstance(found, dict) else found)
    except Exception:  # noqa: BLE001 - one store failing never breaks a lookup
        log.exception("Couldn't list %s.", kind.kind)
        return []


def known(kind: str) -> bool:
    """Whether the registry knows a kind: readable (`TYPES`) or named with why it isn't yet (`HISTORY_ONLY`)."""
    return kind in TYPES or kind in HISTORY_ONLY


def read(context, ref: str):
    """The record a `kind:id` ref names (from its store, then any `read_also` store), or None when it's gone, its
    store is missing, or the kind can't be read."""
    kind_name, _, record_id = str(ref).partition(":")
    kind = TYPES.get(kind_name)
    if kind is None or not record_id:
        return None
    for store in (kind.store, *kind.read_also):
        for record in records_of(context, replace(kind, store=store)):
            if str(field_of(record, kind.id_attr)) == record_id:
                return record
    return None


def readable(context, kind_name: str) -> bool:
    """Whether a kind can be read back here: in `TYPES`, with its store on this context."""
    kind = TYPES.get(kind_name)
    return kind is not None and getattr(context, kind.store, None) is not None
