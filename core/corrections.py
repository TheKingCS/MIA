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
              "sale", "order", "quote", "customer", "shop_expense", "payment", "spend"),
    "kitchen": ("recipe", "pantry", "meal", "grocery", "cook", "food"),
    "workouts": ("workout", "exercise", "fitness", "training", "run", "lift"),
    "missions": ("mission", "quest", "objective", "pathway", "boss", "raid", "dungeon", "party", "reward"),
    "calendar": ("event", "calendar", "reminder", "alarm"),
    "maintenance": ("maintenance", "asset", "gear", "reading", "vehicle"),
    "inbox": ("inbox", "document", "scan"),
    "memories": ("memory", "remember", "forget"),
    "creations": ("creation", "records", "workflow"),
    "home": ("grow", "flock", "pet", "property", "security", "place", "trip", "expedition", "map", "product",
             "material", "component", "craft", "goods", "job", "batch", "experiment"),
    "tasks": ("task", "routine", "plan", "project"),
}


def family_of(kind: str) -> str:
    """Pure logic. `bill.add` -> `bill`; a tool's name (`add_expense`) stays itself."""
    kind = str(kind or "")
    kind = kind[len("action_"):] if kind.startswith("action_") else kind
    return kind.split(".", 1)[0]


def verb_of(kind: str) -> str:
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
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def _lines(folder: Path) -> list[dict]:
    try:
        text = (folder / FILE_NAME).read_text(encoding="utf-8")
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
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with _lock:
            path = folder / FILE_NAME
            with open(path, "a", encoding="utf-8") as out:
                out.write(json.dumps(entry) + "\n")
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > _MAX_LINES:
                path.write_text("\n".join(lines[-(_MAX_LINES * 3 // 5):]) + "\n", encoding="utf-8")
    except OSError:
        log.exception("Couldn't keep a correction record.")


def _now() -> datetime:
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
        elif entry.get("family") != family:
            continue
        elif ids and entry.get("ids") and not set(ids) & set(entry["ids"]):
            continue
        return entry
    return None


def person_changed(context, kind: str, params: Optional[dict] = None, now: Optional[datetime] = None) -> Optional[dict]:
    """The person edited or deleted something: a correction when it's of a kind MIA just changed."""
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
    return entry


def undone(context, label: str, now: Optional[datetime] = None) -> Optional[dict]:
    """The person undid one of MIA's changes (its undo label: `add_expense`, `action_bill.add`)."""
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
    return tuple(AREAS)
