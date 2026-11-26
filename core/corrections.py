"""
core.corrections
==================

Corrections in every area (build plan step 4, DEC-0094;
`docs/IMPROVEMENT_LOOPS.md` section C): when the person undoes, edits or
deletes something MIA just did, that's a judgment of her work, and the same
code counts it in every area.

- **What MIA did** (`mia_changed()`): an action she proposed that the
  person approved (core/actions.py), or a change an Assistant tool made
  (core/assistant_actions.py). Kept by its kind (`bill.add`,
  `add_expense`) and the ids it named, never what was in it.
- **A correction** (`person_changed()`, `undone()`): within `WITHIN` (3
  days), the person undoes that change, or edits or deletes something of
  the same kind (the same record, when both sides name its id). Each of
  MIA's changes counts as corrected once.
- **Areas** (`area_of()`): money, kitchen, workouts, missions, calendar,
  maintenance, inbox, memories, creations, home... from the kind.
  `summary()` gives each area's changes and corrections for the
  `corrections.*` loops (core/loops.py).

Both go into `corrections.jsonl` in the person's own folder (DEC-0001),
beside their Fix-It Log. This file is on the lab's protected list: MIA
can't change what counts as her being corrected.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from core.at_rest import open_text, seal_line
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "corrections.jsonl"
WITHIN = timedelta(days=3)
CORRECTING = ("edit", "delete", "remove", "rename", "set", "adjust", "forget", "status", "document_remove")
_MAX_LINES = 4000
_lock = threading.Lock()

# area -> words its kinds start with or contain (an action's family before the dot, or a tool's name)
AREAS = {
    "money": ("bill", "income", "expense", "debt", "budget", "asset_value", "portfolio", "freedom", "insurance",
              "sale", "order", "quote", "customer", "shop_expense", "payment", "spend", "obligation", "market"),
    "kitchen": ("recipe", "pantry", "meal", "grocery", "cook", "food"),
    "workouts": ("workout", "exercise", "fitness", "training", "run", "lift"),
    "missions": ("mission", "quest", "objective", "pathway", "boss", "raid", "dungeon", "party", "reward", "shop",
                 "character"),
    "calendar": ("event", "calendar", "reminder", "alarm"),
    "maintenance": ("maintenance", "asset", "gear", "reading", "vehicle"),
    "inbox": ("inbox", "document", "scan"),
    "memories": ("memory", "remember", "forget", "journal", "life_note"),
    "creations": ("creation", "records", "workflow"),
    "home": ("grow", "flock", "pet", "property", "security", "place", "trip", "expedition", "map", "product",
             "material", "component", "craft", "goods", "job", "batch", "experiment", "inventory", "waypoint"),
    "tasks": ("task", "routine", "plan", "project", "loop"),
    "people": ("person", "relationship"),
    "music": ("playlist", "track", "music"),
    "files": ("myfile",),
}


def family_of(kind: str) -> str:
    """Pure logic. `bill.add` -> `bill`; a tool's name (`add_expense`) stays itself."""
    kind = str(kind or "")
    kind = kind[len("action_"):] if kind.startswith("action_") else kind
    return kind.split(".", 1)[0]


def verb_of(kind: str) -> str:
    """Pure logic. The verb in an action kind (bill.add gives add; an action_ prefix is ignored), or empty."""
    kind = str(kind or "")
    kind = kind[len("action_"):] if kind.startswith("action_") else kind
    return kind.split(".", 1)[1] if "." in kind else ""


def area_of(kind: str) -> str:
    """Pure logic. The area a kind of change belongs to ("other" when none fits)."""
    family = family_of(kind)
    for area, words in AREAS.items():
        if family in words:
            return area
    for area, words in AREAS.items():
        if any(w in family for w in words):
            return area
    return "other"


def ids_in(params: Optional[dict]) -> list[str]:
    """Pure logic. The record ids an action names (`id`, `bill_id`...), never anything else in it."""
    out = []
    for key, value in (params or {}).items():
        if (key == "id" or key.endswith("_id")) and isinstance(value, (str, int)) and str(value):
            out.append(str(value)[:60])
    return sorted(set(out))


def _folder(context) -> Optional[Path]:
    """The person's folder corrections are kept in (the failure log's, else the traces'), or None."""
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def _lines(folder: Path) -> list[dict]:
    """Every correction record (corrections.jsonl), one JSON line each; a bad line is skipped, a missing file gives
    none. Its sealed lines open through open_text (WP-04).
    """
    try:
        text = open_text(folder / FILE_NAME)  # sealed a line at a time (WP-04)
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _append(folder: Path, entry: dict) -> None:
    """Adds one record, under a lock; past 4,000 lines the oldest are dropped down to 2,400. A file that can't be
    written is logged, never raised. Each line is sealed as it's written (seal_line, WP-04). The kept lines are written back sealed, a line at a time (WP-04).
    """
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with _lock:
            path = folder / FILE_NAME
            with open(path, "a", encoding="utf-8") as out:
                out.write(seal_line(path, json.dumps(entry)) + "\n")
            lines = path.read_text(encoding="utf-8").splitlines()  # as stored: kept lines stay sealed
            if len(lines) > _MAX_LINES:
                atomic_write_text(path, "\n".join(lines[-(_MAX_LINES * 3 // 5):]) + "\n")  # each line sealed
    except OSError:
        log.exception("Couldn't keep a correction record.")


def _now() -> datetime:
    """The time now (its own function, so tests can set it)."""
    return datetime.now()


def mia_changed(context, kind: str, params: Optional[dict] = None, now: Optional[datetime] = None) -> None:
    """MIA changed something: kept by its kind and the ids it named."""
    folder = _folder(context)
    if folder is None:
        return
    when = (now or _now()).isoformat(timespec="seconds")
    _append(folder, {"at": when, "id": uuid.uuid4().hex[:10], "what": "mia", "kind": str(kind)[:80],
                     "family": family_of(kind),
                     "area": area_of(kind), "ids": ids_in(params)})


_VERBS = frozenset(("add", "log", "create", "record", "set", "update", "edit", "delete", "remove", "plan", "mark",
                    "adjust", "start", "schedule", "new", "make", "put", "rename", "item", "entry"))


def _nouns(family: str) -> set:
    """Pure logic. What a family is about: `add_calendar_event` -> {calendar, event}; `event` -> {event}."""
    return {w for w in str(family or "").split("_") if w and w not in _VERBS}


def _same_thing(hers: str, theirs: str) -> bool:
    """Pure logic. The same kind of record: the same family, or (a tool's name against an action's family) a noun
    in common within the same area."""
    if hers == theirs:
        return True
    return bool(_nouns(hers) & _nouns(theirs)) and area_of(hers) == area_of(theirs) != "other"


def _corrects(folder: Path, family: str, ids: list[str], now: datetime, label: str = "") -> Optional[dict]:
    """The latest of MIA's changes this one corrects: same family (or the same undo label), within WITHIN,
    the same record when both name ids, and not corrected already."""
    lines = _lines(folder)
    done = {l.get("corrects") for l in lines if l.get("what") == "corrected"}  # each of hers counts once
    since = (now - WITHIN).isoformat(timespec="seconds")
    for entry in reversed(lines):
        if entry.get("what") != "mia" or entry.get("at", "") < since or entry.get("id") in done:
            continue
        if label:
            if entry.get("kind") != label and f"action_{entry.get('kind')}" != label:
                continue
        elif not _same_thing(entry.get("family", ""), family):
            continue
        elif ids and entry.get("ids") and not set(ids) & set(entry["ids"]):
            continue
        return entry
    return None


DOUBT_COUNT = 2  # his corrections of one kind she does on her own, within DOUBT_DAYS, before she asks
DOUBT_DAYS = 7


def _doubt(context, folder: Path, kind: str, now: datetime) -> None:
    """After he corrects a kind of change she makes on her own (his standing yes, core/kind_grants.py) DOUBT_COUNT
    times within DOUBT_DAYS and since he gave it (brainstorm round 17: learned this week, then asked), by edit,
    delete or Undo: she offers, through the gate, to ask him first again, never taking his yes back herself, naming
    the one yes by family and verb ("grocery add"). Once a week per kind. Never raises."""
    try:
        from core import kind_grants

        kind = kind[len("action_"):] if kind.startswith("action_") else kind
        if not kind_grants.has(context, kind):
            return
        given = str(kind_grants.live(context).get(kind, {}).get("given", ""))
        since = max((now - timedelta(days=DOUBT_DAYS)).isoformat(timespec="seconds"), given)  # since his yes only
        times = sum(1 for e in _lines(folder) if e.get("what") == "corrected" and e.get("at", "") >= since
                    and (e.get("kind") == kind or e.get("kind") == f"action_{kind}"))
        gate = getattr(context, "communication", None)
        if times < DOUBT_COUNT or gate is None:
            return
        from core.communication_gate import TIMELY, Candidate

        family = family_of(kind).replace("_", " ")
        named = f"{family} {verb_of(kind).replace('_', ' ')}".strip()  # "grocery add": the one yes, never its family
        year, week, _ = now.isocalendar()
        gate.offer(Candidate(
            topic="grant_doubt", title=f"Should I ask first about {family}?",
            message=(f"You've corrected my {family} changes {times} times this week, and I make those on my own "
                     f"since you said yes from now on. Say \"ask me first for {named}\" and I'll check with you "
                     f"again before each one."),
            urgency=TIMELY, source="system", fingerprint=f"grant-doubt-{kind}-{year}-W{week:02d}"), now)
    except Exception:
        log.exception("Couldn't offer to ask first about %s.", kind)


def person_changed(context, kind: str, params: Optional[dict] = None, now: Optional[datetime] = None) -> Optional[dict]:
    """The person edited or deleted something: a correction when it's of a kind MIA just changed (and, at the second
    within a week of a kind she does on her own, her offer to ask him first again: `_doubt`)."""
    if verb_of(kind) not in CORRECTING:
        return None
    folder = _folder(context)
    if folder is None:
        return None
    now = now or _now()
    found = _corrects(folder, family_of(kind), ids_in(params), now)
    if found is None:
        return None
    entry = {"at": now.isoformat(timespec="seconds"), "what": "corrected", "how": verb_of(kind),
             "kind": found["kind"], "area": found["area"], "corrects": found.get("id")}
    _append(folder, entry)
    _doubt(context, folder, str(found["kind"]), now)
    return entry


def screen_edit(context, kind: str, record_id: str = "") -> Optional[dict]:
    """A record edited or deleted on one of the desktop's Qt screens, which change stores directly (the web's go
    through actions, counted there): a correction when it's of a kind MIA just changed. Inside an action or an
    Assistant tool (life_events.acting) it's counted there instead, so never twice. Never raises: the record never
    breaks the change."""
    from core import life_events

    if getattr(life_events._local, "source", None):
        return None
    try:
        return person_changed(context, kind, {"id": record_id} if record_id else None)
    except Exception:
        log.exception("Couldn't keep the correction record for %s.", kind)
        return None


def undone(context, label: str, now: Optional[datetime] = None) -> Optional[dict]:
    """The person undid one of MIA's changes (its undo label: `add_expense`, `action_bill.add`); at the second within
    a week of a kind she does on her own, her offer to ask first again (`_doubt`)."""
    folder = _folder(context)
    if folder is None:
        return None
    now = now or _now()
    found = _corrects(folder, family_of(label), [], now, label=label)
    if found is None:
        return None
    entry = {"at": now.isoformat(timespec="seconds"), "what": "corrected", "how": "undo", "kind": found["kind"],
             "area": found["area"], "corrects": found.get("id")}
    _append(folder, entry)
    _doubt(context, folder, str(found["kind"]), now)  # an Undo of something she did on her own counts too
    return entry


def summary(context, days: int = 30, now: Optional[datetime] = None) -> dict:
    """area -> {changes, corrected, kinds: {kind: corrected}} over the last `days`."""
    folder = _folder(context)
    if folder is None:
        return {}
    since = ((now or _now()) - timedelta(days=days)).isoformat(timespec="seconds")
    out: dict[str, dict] = {}
    for entry in _lines(folder):
        if entry.get("at", "") < since:
            continue
        row = out.setdefault(entry.get("area", "other"), {"changes": 0, "corrected": 0, "kinds": {}})
        if entry.get("what") == "mia":
            row["changes"] += 1
        elif entry.get("what") == "corrected":
            row["corrected"] += 1
            row["kinds"][entry.get("kind", "")] = row["kinds"].get(entry.get("kind", ""), 0) + 1
    return out


def areas() -> Iterable[str]:
    """Every area corrections are counted in."""
    return tuple(AREAS)
