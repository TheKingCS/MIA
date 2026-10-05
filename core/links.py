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
  intent SUPPORTS an intent (core/why_graph.py), a completed mission
  EVIDENCE_FOR each skill it trained. Status: DERIVED.

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
)}


def _records(context, kind: Kind) -> list:
    store = getattr(context, kind.store, None)
    lister: Optional[Callable] = getattr(store, kind.lister, None)
    if lister is None:
        return []
    try:
        return list(lister())
    except Exception:
        log.exception("Couldn't list %s for links.", kind.kind)
        return []


def ref_of(kind: str, record) -> str:
    return f"{kind}:{getattr(record, KINDS[kind].id_attr)}"


def name_of(context, ref: str) -> str:
    """The record's own name, or the ref itself if it's gone."""
    kind_name, _, record_id = ref.partition(":")
    kind = KINDS.get(kind_name)
    if kind is None:
        return ref
    for record in _records(context, kind):
        if str(getattr(record, kind.id_attr, "")) == record_id:
            return str(getattr(record, kind.name_attr, "") or ref)
    return ref


def exists(context, ref: str) -> bool:
    return name_of(context, ref) != ref


def find(context, text: str, kinds: Optional[Iterable[str]] = None) -> tuple[Optional[str], Optional[str]]:
    """A ref from what someone called it ("the land loan", "Rental A").
    Returns (ref, None), or (None, what to say back)."""
    from core.assistant_lookup import resolve_by_name

    candidates = []
    for kind in (KINDS[k] for k in (kinds or KINDS) if k in KINDS):
        candidates += [(kind.kind, r) for r in _records(context, kind)
                       if str(getattr(r, kind.name_attr, "") or "").strip()]
    cleaned = (text or "").strip()
    for article in ("the ", "my ", "our "):
        if cleaned.lower().startswith(article):
            cleaned = cleaned[len(article):]
    match, problem = resolve_by_name(candidates, cleaned, lambda c: str(getattr(c[1], KINDS[c[0]].name_attr)),
                                     "thing")
    if match is None:
        return None, problem
    return ref_of(match[0], match[1]), None


# ------------------------------------------------------------------ links


@dataclass
class Link:
    source: str  # kind:id
    relation: str
    target: str  # kind:id
    link_id: str = ""
    note: str = ""
    created_at: str = ""
    by: Optional[str] = None  # profile id
    derived: bool = False  # computed from the stores, not stated

    def as_dict(self) -> dict:
        return asdict(self)


class LinkStore:
    """A household's stated links (`links.json`)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self._links: list[Link] = []
        self._load()

    def _load(self) -> None:
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
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps([l.as_dict() for l in self._links], indent=2), encoding="utf-8")

    def all_links(self) -> list[Link]:
        return list(self._links)

    def add(self, source: str, relation: str, target: str, note: str = "", by: Optional[str] = None) -> Link:
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
    return found


def all_links(context) -> list[Link]:
    """Stated links plus derived ones."""
    store = getattr(context, "links", None)
    return (store.all_links() if store is not None else []) + derived_links(context)


def links_for(context, ref: str) -> list[Link]:
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
    return f"{name_of(context, link.source)} {RELATIONS.get(link.relation, link.relation)} {name_of(context, link.target)}"
