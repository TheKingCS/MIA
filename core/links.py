"""
core.links
============

How things relate (2026-10-05, Engine Phase 1 step 2,
docs/ENGINE_PHASE1_PLAN.md): typed links between the records MIA
already keeps, like "this loan FUNDS that property", "the walipini
DEPENDS_ON selling the lot", "this mission is EVIDENCE_FOR that skill".
(Named `links` because `relationships_manager` is People & Pets.)

**An index, not a copy.** The records stay in their own stores; a link
only names them by reference, `kind:id` (`property:ab12`, `debt:9f3c`,
the same refs core/life_events.py uses). Two sources:

- **Stated links** (`links.json`, one per household, a household store):
  what a person told MIA, in Settings or by saying it ("the land loan
  funds the rental"). Written through `atomic_write_text`, so "undo
  that" takes one back. Status: REAL.
- **Derived links**: computed live from fields the stores already have,
  never stored, so they can't drift: who OWNS an asset
  (core/ownership.py), a task or maintenance task PART_OF its project or
  asset, a property, bill or debt PART_OF a business, a project or an
  intent SUPPORTS an intent (core/why_graph.py), a property's upkeep
  record RELATED_TO the property, a completed mission
  EVIDENCE_FOR each skill it trained; and (2026-11-08, the ties
  core/connections.py's `connections.unlinked` loop looks for) a
  mission PART_OF its project or trip, a skill BUILDS_ON its
  prerequisites, a trip PART_OF its expedition, a production job
  USES its workshop recipe, a product RELATED_TO the job that made
  it, a workshop recipe RELATED_TO its product and USES each
  workshop material its lines name (matched as core/craft_recipes.py
  matches them), an insurance policy RELATED_TO the asset it covers, a
  project RELATED_TO each skill it trains. None of these use the
  waiting words (REQUIRES, DEPENDS_ON, BLOCKED_BY): those are the
  person's own "what waits on what" in the Life State. Status: DERIVED.

What a link can point at is KINDS: each kind's store, the list or
method that holds its records, and their id and name fields. A store
may keep objects or dicts (a plan, a creation, a note, a GPS track:
2026-11-09); `field_of` reads either.

Pure logic where possible; the stores are only read.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILE_NAME = "links.json"

# The relation names (the kickoff spec's list), with how each one reads.
RELATIONS = {
    "OWNS": "owns",
    "LOCATED_AT": "is at",
    "PART_OF": "is part of",
    "DEPENDS_ON": "depends on",
    "COSTS": "is a cost of",
    "FUNDS": "funds",
    "GENERATES_INCOME": "brings in income for",
    "REQUIRES": "requires",
    "BLOCKED_BY": "is blocked by",
    "EVIDENCE_FOR": "is evidence for",
    "SUPPORTS": "supports",
    "RELATED_TO": "is related to",
    "USES": "uses",  # a workshop recipe and its materials, a job and its recipe: needs, not waits
    "BUILDS_ON": "builds on",  # a skill and the skills it starts from
}

# What people say -> the relation.
_RELATION_WORDS = (
    ("blocked by", "BLOCKED_BY"), ("depends on", "DEPENDS_ON"), ("waits on", "DEPENDS_ON"),
    ("needs", "REQUIRES"), ("requires", "REQUIRES"), ("pays for", "FUNDS"), ("funds", "FUNDS"),
    ("finances", "FUNDS"), ("brings in", "GENERATES_INCOME"), ("earns", "GENERATES_INCOME"),
    ("income", "GENERATES_INCOME"), ("costs", "COSTS"), ("cost of", "COSTS"), ("part of", "PART_OF"),
    ("belongs to", "PART_OF"), ("located", "LOCATED_AT"), ("is at", "LOCATED_AT"), ("kept at", "LOCATED_AT"),
    ("owns", "OWNS"), ("supports", "SUPPORTS"), ("serves", "SUPPORTS"), ("helps", "SUPPORTS"),
    ("toward", "SUPPORTS"), ("evidence", "EVIDENCE_FOR"), ("related", "RELATED_TO"), ("goes with", "RELATED_TO"),
)


def relation_from(text: str) -> Optional[str]:
    """Pure logic. "depends on" -> DEPENDS_ON; a relation name works too."""
    text = (text or "").strip()
    if text.upper().replace(" ", "_") in RELATIONS:
        return text.upper().replace(" ", "_")
    lowered = text.lower()
    for words, relation in _RELATION_WORDS:
        if words in lowered:
            return relation
    return None


# ------------------------------------------------------------------ what can be linked


@dataclass(frozen=True)
class Kind:
    """One kind of thing a link can point at (an asset, a mission, a person...): its name and label, the store and method
    that list them, and which attributes are its id and its name.
    """
    kind: str
    label: str
    store: str  # AppContext attribute
    lister: str  # method returning the records
    id_attr: str
    name_attr: str = "name"


KINDS: dict[str, Kind] = {k.kind: k for k in (
    Kind("property", "property", "real_estate", "all_properties", "property_id"),
    Kind("asset", "vehicle, tool or appliance", "maintenance", "all_assets", "asset_id"),
    Kind("maintenance_task", "maintenance task", "maintenance", "all_tasks", "task_id", "title"),
    Kind("bill", "bill", "budget", "all_bills", "bill_id"),
    Kind("debt", "debt", "budget", "all_debts", "debt_id"),
    Kind("income_source", "income source", "budget", "all_income_sources", "source_id"),
    Kind("business", "business", "budget", "all_business_entities", "entity_id"),
    Kind("project", "project", "projects", "all_projects", "project_id"),
    Kind("task", "task", "tasks", "all_tasks", "task_id", "title"),
    Kind("intent", "goal", "intents", "all_intents", "intent_id"),
    Kind("mission", "mission", "missions", "all_missions", "mission_id"),
    Kind("skill", "skill", "skills", "all_skills", "skill_id"),
    Kind("person", "person", "relationships", "all_people", "person_id"),
    Kind("pet", "pet", "relationships", "all_pets", "pet_id"),
    Kind("recipe", "recipe", "kitchen", "all_recipes", "recipe_id"),
    Kind("profile", "account", "profiles", "list_profiles", "profile_id"),
    # 2026-11-07 (DEC-0108's interconnection audit): the rest of the records a life is made of, so they can depend
    # on, serve, block or belong to each other. The kind names match the refs their stores' life events carry.
    Kind("calendar_event", "event", "calendar", "all_events", "event_id", "title"),
    Kind("inventory_item", "item", "inventory", "all_items", "item_id"),
    Kind("component", "part", "components", "all_components", "component_id"),
    Kind("material", "material", "materials", "all_materials", "material_id"),
    Kind("product", "product", "products", "all_products", "product_id"),
    Kind("job", "job", "jobs", "all_jobs", "job_id"),
    Kind("craft_recipe", "workshop recipe", "craft_recipes", "all_recipes", "recipe_id"),
    Kind("waypoint", "waypoint", "waypoints", "all_waypoints", "waypoint_id"),
    Kind("trip", "trip", "trips", "all_trips", "trip_id"),
    Kind("expedition", "expedition", "expeditions", "all_expeditions", "expedition_id"),
    Kind("textbook", "book", "textbooks", "all_books", "book_id", "title"),
    Kind("energy_source", "energy source", "energy", "all_energy_sources", "source_id"),
    Kind("journal_entry", "journal entry", "journal", "all_entries", "entry_id", "title"),
    Kind("reward", "reward", "reward_shop", "all_rewards", "reward_id"),
    Kind("script", "script", "scripts", "all_scripts", "script_id"),
    Kind("place", "place", "places", "places", "place_id"),
    Kind("obligation", "obligation", "obligations", "obligations", "obligation_id", "title"),
    Kind("policy", "insurance policy", "insurance", "policies", "policy_id", "insurer"),
    Kind("customer", "customer", "business", "customers", "customer_id"),
    Kind("flock", "flock", "flock", "flocks", "flock_id"),
    # 2026-11-09, the self-audit's links column: what a person may want to tie to a goal, project or debt.
    Kind("subject", "class subject", "classroom", "all_subjects", "subject_id"),
    Kind("workout_template", "workout", "workout", "all_templates", "template_id"),
    Kind("grow_batch", "grow-lab batch", "grow_lab", "batches", "batch_id", "crop"),
    Kind("questline", "questline", "quest_book", "quests", "quest_id"),
    Kind("workplace", "workplace", "dungeon", "dungeons", "dungeon_id"),
    Kind("direction", "direction", "direction", "directions", "direction_id", "title"),
    Kind("campaign", "campaign", "living_worlds", "campaigns", "campaign_id"),
    Kind("inbox_item", "letter or document", "inbox", "all_items", "item_id", "subject"),
    Kind("plan", "build plan", "plans", "plans", "id", "title"),  # these four keep dicts
    Kind("creation", "creation", "creations", "items", "id", "title"),
    Kind("note", "note", "life_notes", "notes", "id", "what"),  # the refs their history already uses
    Kind("track", "GPS track", "gps_tracks", "tracks", "id"),
    Kind("shop_expense", "shop expense", "ledger", "all_expenses", "entry_id", "description"),  # history's refs
    Kind("shop_revenue", "shop sale or income", "ledger", "all_revenue", "entry_id", "description"),
    Kind("rhythm", "rhythm of the week", "loop", "rhythms", "rhythm_id"),
    Kind("record_set", "household record set", "record_sets", "sets", "id"),
    Kind("my_record_set", "record set", "my_record_sets", "sets", "id"),
    Kind("play", "game or sport played", "recreation", "entries", "id", "what"),
    Kind("picture", "picture MIA painted", "art", "items", "id", "description"),
)}


def field_of(record, attr: str, default=""):
    """One field of a record, whether the store keeps objects or dicts (a plan, a creation, a note: 2026-11-09)."""
    return record.get(attr, default) if isinstance(record, dict) else getattr(record, attr, default)


def _records(context, kind: Kind) -> list:
    """Every record of a kind, from its store (a method that lists them, or a list or dict the store keeps: a dict
    gives its values); [] (logged) when the store is missing or fails."""
    store = getattr(context, kind.store, None)
    lister: Optional[Callable] = getattr(store, kind.lister, None)
    if lister is None:
        return []
    try:
        found = lister() if callable(lister) else lister
        return list(found.values() if isinstance(found, dict) else found)
    except Exception:
        log.exception("Couldn't list %s for links.", kind.kind)
        return []


def records(context, kind: str) -> list:
    """Every record of a kind by its name ("project", "material"...): [] for an unknown kind or a missing store. The
    public way for another module (core/connections.py) to walk the things links can point at."""
    return _records(context, KINDS[kind]) if kind in KINDS else []


def ref_of(kind: str, record) -> str:
    """A record's reference, "kind:id" (how links point at things, never by copying them)."""
    return f"{kind}:{field_of(record, KINDS[kind].id_attr)}"


def name_of(context, ref: str) -> str:
    """The record's own name, or the ref itself if it's gone."""
    kind_name, _, record_id = ref.partition(":")
    kind = KINDS.get(kind_name)
    if kind is None:
        return ref
    for record in _records(context, kind):
        if str(field_of(record, kind.id_attr)) == record_id:
            return str(field_of(record, kind.name_attr) or ref)
    return ref


def exists(context, ref: str) -> bool:
    """Whether a reference points at a record that's still there."""
    return name_of(context, ref) != ref


def find(context, text: str, kinds: Optional[Iterable[str]] = None) -> tuple[Optional[str], Optional[str]]:
    """A ref from what someone called it ("the land loan", "Rental A").
    Returns (ref, None), or (None, what to say back)."""
    from core.assistant_lookup import resolve_by_name

    candidates = []
    for kind in (KINDS[k] for k in (kinds or KINDS) if k in KINDS):
        candidates += [(kind.kind, r) for r in _records(context, kind)
                       if str(field_of(r, kind.name_attr) or "").strip()]
    cleaned = (text or "").strip()
    for article in ("the ", "my ", "our "):
        if cleaned.lower().startswith(article):
            cleaned = cleaned[len(article):]
    match, problem = resolve_by_name(candidates, cleaned, lambda c: str(field_of(c[1], KINDS[c[0]].name_attr)),
                                     "thing")
    if match is None:
        return None, problem
    return ref_of(match[0], match[1]), None


# ------------------------------------------------------------------ links


@dataclass
class Link:
    """One relation between two things, by reference: source, relation (RELATIONS), target, a note, when, who stated
    it, and whether it was derived from the stores rather than stated.
    """
    source: str  # kind:id
    relation: str
    target: str  # kind:id
    link_id: str = ""
    note: str = ""
    created_at: str = ""
    by: Optional[str] = None  # profile id
    derived: bool = False  # computed from the stores, not stated

    def as_dict(self) -> dict:
        """The link as a plain dict."""
        return asdict(self)


class LinkStore:
    """A household's stated links (`links.json`)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """The stated links (links.json in the household's folder, data/ by default); derived ones are worked out when asked."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self._links: list[Link] = []
        self._load()

    def _load(self) -> None:
        """Reads the stated links; an unreadable file is logged, reported and starts with none."""
        self._links = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            self._links = [Link(**{k: v for k, v in d.items() if k in Link.__dataclass_fields__}) for d in raw]
        except (json.JSONDecodeError, OSError, TypeError):
            log.exception("Couldn't read %s; starting with no stated links.", self._file)
            from core.data_recovery import notify_data_corruption

            notify_data_corruption(self.context, FILE_NAME)

    def _save(self) -> None:
        """Writes the stated links atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps([l.as_dict() for l in self._links], indent=2), encoding="utf-8")

    def all_links(self) -> list[Link]:
        """Every stated link."""
        return list(self._links)

    def add(self, source: str, relation: str, target: str, note: str = "", by: Optional[str] = None) -> Link:
        """States a link (a known relation, between two different things); the same link twice is kept once."""
        if relation not in RELATIONS:
            raise ValueError(f"Unknown relation '{relation}'.")
        if source == target:
            raise ValueError("A thing can't be linked to itself.")
        for link in self._links:
            if (link.source, link.relation, link.target) == (source, relation, target):
                return link  # already there
        link = Link(source, relation, target, uuid.uuid4().hex[:10], note.strip(),
                    datetime.now().isoformat(timespec="seconds"), by)
        self._links.append(link)
        self._save()
        return link

    def remove(self, source: str, target: str, relation: Optional[str] = None) -> int:
        """Removes the links between two things (either way round), or only those of one relation; returns how many."""
        before = len(self._links)
        self._links = [l for l in self._links
                       if not ({l.source, l.target} == {source, target} and (relation is None or l.relation == relation))]
        if len(self._links) != before:
            self._save()
        return before - len(self._links)


def derived_links(context) -> list[Link]:
    """Links the stores already imply. Computed fresh; never stored."""
    found: list[Link] = []

    def add(source: str, relation: str, target: str) -> None:
        found.append(Link(source, relation, target, derived=True))

    for asset in _records(context, KINDS["asset"]):
        if getattr(asset, "owner_profile_id", None):
            add(f"profile:{asset.owner_profile_id}", "OWNS", ref_of("asset", asset))
    for task in _records(context, KINDS["maintenance_task"]):
        add(ref_of("maintenance_task", task), "PART_OF", f"asset:{task.asset_id}")
    for task in _records(context, KINDS["task"]):
        if getattr(task, "project_id", None):
            add(ref_of("task", task), "PART_OF", f"project:{task.project_id}")
    for kind in ("property", "bill", "debt", "income_source"):
        for record in _records(context, KINDS[kind]):
            if getattr(record, "entity_id", ""):
                add(ref_of(kind, record), "PART_OF", f"business:{record.entity_id}")
    for prop in _records(context, KINDS["property"]):
        if getattr(prop, "maintenance_asset_id", ""):
            add(f"asset:{prop.maintenance_asset_id}", "RELATED_TO", ref_of("property", prop))
    for project in _records(context, KINDS["project"]):
        if getattr(project, "intent_id", None):
            add(ref_of("project", project), "SUPPORTS", f"intent:{project.intent_id}")
    for intent in _records(context, KINDS["intent"]):
        if getattr(intent, "serves_intent_id", None):
            add(ref_of("intent", intent), "SUPPORTS", f"intent:{intent.serves_intent_id}")
    for mission in _records(context, KINDS["mission"]):
        if getattr(mission, "status", "") == "completed":
            for weight in getattr(mission, "skill_rewards", None) or []:
                add(ref_of("mission", mission), "EVIDENCE_FOR", f"skill:{weight.skill_id}")
    # 2026-11-08: ties the stores' own fields already say, which the graph didn't make (core/connections.py's
    # connections.unlinked loop counts the ones still missing). A mission's task_id is left out: it doesn't say which
    # kind of task it means. Never the waiting words: those are the person's stated dependencies (the Life State's
    # "what waits on what"), and a skill tree or a recipe's materials would bury them.
    for mission in _records(context, KINDS["mission"]):
        for attr, kind in (("project_id", "project"), ("trip_id", "trip")):
            if getattr(mission, attr, None):
                add(ref_of("mission", mission), "PART_OF", f"{kind}:{getattr(mission, attr)}")
    for skill in _records(context, KINDS["skill"]):
        for needed in getattr(skill, "prerequisite_skill_ids", None) or []:
            add(ref_of("skill", skill), "BUILDS_ON", f"skill:{needed}")
    for trip in _records(context, KINDS["trip"]):
        if getattr(trip, "expedition_id", None):
            add(ref_of("trip", trip), "PART_OF", f"expedition:{trip.expedition_id}")
    for job in _records(context, KINDS["job"]):
        if getattr(job, "recipe_id", None):
            add(ref_of("job", job), "USES", f"craft_recipe:{job.recipe_id}")
    for product in _records(context, KINDS["product"]):
        if getattr(product, "job_id", None):
            add(ref_of("product", product), "RELATED_TO", f"job:{product.job_id}")
    for policy in _records(context, KINDS["policy"]):
        if getattr(policy, "asset_id", None):
            add(ref_of("policy", policy), "RELATED_TO", f"asset:{policy.asset_id}")
    for project in _records(context, KINDS["project"]):
        for weight in getattr(project, "skill_weights", None) or []:
            add(ref_of("project", project), "RELATED_TO", f"skill:{weight.skill_id}")
    recipes = _records(context, KINDS["craft_recipe"])
    if recipes:
        from core.craft_recipes import key

        stock = {key(m.name): m for m in _records(context, KINDS["material"])}
        for recipe in recipes:
            if getattr(recipe, "product_id", None):
                add(ref_of("craft_recipe", recipe), "RELATED_TO", f"product:{recipe.product_id}")
            for line in getattr(recipe, "lines", None) or []:
                material = stock.get(key(line.name))
                if material is not None:
                    add(ref_of("craft_recipe", recipe), "USES", ref_of("material", material))
    return found


def all_links(context) -> list[Link]:
    """Stated links plus derived ones."""
    store = getattr(context, "links", None)
    return (store.all_links() if store is not None else []) + derived_links(context)


def links_for(context, ref: str) -> list[Link]:
    """Every link, stated or derived, that touches one thing."""
    return [l for l in all_links(context) if ref in (l.source, l.target)]


def downstream(context, ref: str, relations: Iterable[str] = ("DEPENDS_ON", "BLOCKED_BY", "REQUIRES")) -> list[str]:
    """Everything that waits on `ref`, directly or through a chain
    ("what depends on selling the lot?"). Pure walk, cycle-safe."""
    wanted = set(relations)
    waiting_on: dict[str, list[str]] = {}
    for link in all_links(context):
        if link.relation in wanted:
            waiting_on.setdefault(link.target, []).append(link.source)
    found: list[str] = []
    queue = list(waiting_on.get(ref, []))
    while queue:
        current = queue.pop(0)
        if current in found or current == ref:
            continue
        found.append(current)
        queue += waiting_on.get(current, [])
    return found


def describe_link(context, link: Link) -> str:
    """A link in words: "<source> <relation> <target>" with their names."""
    return f"{name_of(context, link.source)} {RELATIONS.get(link.relation, link.relation)} {name_of(context, link.target)}"
