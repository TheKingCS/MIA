"""
core.record_sets
==================

A home for information MIA has no store for (DEC-0089; ACAF,
`docs/ACAF_REVIEW.md` section 3.4). Every other store is made for one
thing: bills, the flock, workouts. A *record set* is a typed list a person
or MIA defines: its fields (text, number, money, date, choice, yes/no) and
whose it is. "The seeds I save: variety, where from, when, how many,
germination" is one.

Like every store it lives where it belongs (DEC-0001): `record_sets` is the
household's (HOUSEHOLD_STORES), `my_record_sets` the person's own
(PERSONAL_STORES). Changes go through actions (`records.add`,
`records.remove`, core/creation_actions.py), so they're approved, recorded
in the history (core/life_events.py) and undoable; it writes through
`atomic_write_text`.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core import life_events
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "record_sets.json"
FIELD_TYPES = ("text", "number", "money", "date", "choice", "yesno")
MAX_FIELDS = 12
MAX_TEXT = 500
NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


class RecordError(ValueError):
    """A record set or a record that isn't right; the message says what."""


def check_fields(fields: list[dict]) -> list[str]:
    """Pure logic. What's wrong with a set's fields, if anything."""
    problems = []
    if not fields:
        problems.append("A record set needs at least one field.")
    if len(fields) > MAX_FIELDS:
        problems.append(f"At most {MAX_FIELDS} fields.")
    seen = set()
    for f in fields:
        name = str(f.get("name", ""))
        if not NAME.match(name):
            problems.append(f"Field name {name!r} must be lower-case letters, numbers and underscores.")
        if name in seen:
            problems.append(f"Field {name!r} is there twice.")
        seen.add(name)
        if f.get("type") not in FIELD_TYPES:
            problems.append(f"Field {name!r}: the type is one of {', '.join(FIELD_TYPES)}.")
        if f.get("type") == "choice" and not [c for c in f.get("choices") or [] if str(c).strip()]:
            problems.append(f"Field {name!r} is a choice with no choices.")
    return problems


def coerce(field: dict, value) -> object:
    """Pure logic. A value for a field, as its type keeps it; raises RecordError if it can't be."""
    kind, label = field["type"], field.get("label") or field["name"]
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if kind in ("number", "money"):
        try:
            return float(str(value).replace(",", "").lstrip("$"))
        except ValueError:
            raise RecordError(f"{label} should be a number.") from None
    if kind == "date":
        try:
            return date.fromisoformat(str(value)[:10]).isoformat()
        except ValueError:
            raise RecordError(f"{label} should be a date (YYYY-MM-DD).") from None
    if kind == "yesno":
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")
    if kind == "choice":
        choices = [str(c) for c in field.get("choices") or []]
        match = next((c for c in choices if c.lower() == str(value).strip().lower()), None)
        if match is None:
            raise RecordError(f"{label} is one of: {', '.join(choices)}.")
        return match
    return str(value).strip()[:MAX_TEXT]


class RecordSets:
    """Record sets (DEC-0089): lists a person makes for themselves, each with its own fields (record_sets.json, in
    their own folder or the household's, written through atomic_write_text). Adding and removing a record is a life
    event.
    """
    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the record sets from a folder (data/ by default)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads the sets; a missing file gives none, and a damaged one is logged and starts empty."""
        try:
            self.sets: list[dict] = json.loads(self._file.read_text(encoding="utf-8")).get("sets", [])
        except FileNotFoundError:
            self.sets = []
        except (OSError, ValueError):
            log.exception("Couldn't read the record sets; starting empty")
            self.sets = []

    def _save(self) -> None:
        """Writes the sets atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"sets": self.sets}, indent=2, ensure_ascii=False) + "\n")

    def get(self, set_id: str) -> dict:
        """The set with this id, or RecordError."""
        found = next((s for s in self.sets if s["id"] == set_id), None)
        if found is None:
            raise RecordError(f"No record set {set_id}.")
        return found

    def create(self, name: str, fields: list[dict], about: str = "", set_id: str = "") -> dict:
        """A new set with checked fields (a label made from the name when none is given, choices kept for a choice
        field), the next free R-number id unless one is given; RecordError for bad fields or a taken id.
        """
        problems = check_fields(fields)
        if problems:
            raise RecordError(" ".join(problems))
        taken = {s["id"] for s in self.sets}
        if set_id and set_id in taken:
            raise RecordError(f"{set_id} already exists.")
        new_id = set_id or next(f"R-{n:04d}" for n in range(1, 10_000) if f"R-{n:04d}" not in taken)
        made = {"id": new_id, "name": " ".join(name.split())[:60] or "Records", "about": about[:300],
                "fields": [{"name": f["name"], "label": f.get("label") or f["name"].replace("_", " ").capitalize(),
                            "type": f["type"], **({"choices": [str(c) for c in f["choices"]]} if f["type"] == "choice" else {})}
                           for f in fields],
                "records": [], "created": datetime.now().isoformat(timespec="seconds")}
        self.sets.append(made)
        self._save()
        return made

    def add(self, set_id: str, values: dict) -> dict:
        """Adds a record, each field's value coerced to its type; at least one must be filled in (RecordError). Recorded
        as a life event naming its first value.
        """
        found = self.get(set_id)
        kept = {}
        for field in found["fields"]:
            kept[field["name"]] = coerce(field, (values or {}).get(field["name"]))
        if all(v is None for v in kept.values()):
            raise RecordError("Fill in at least one field.")
        taken = {r["id"] for r in found["records"]}
        record = {"id": next(f"r{n}" for n in range(1, 10**6) if f"r{n}" not in taken),
                  "at": datetime.now().isoformat(timespec="seconds"), "values": kept}
        found["records"].append(record)
        self._save()
        first = next((str(v) for v in kept.values() if v not in (None, "")), "")
        life_events.record(self, "record_added", f"Added to {found['name']}: {first[:60]}",
                           refs=[f"record_set:{set_id}"], payload={"record": record["id"]})
        return record

    def remove(self, set_id: str, record_id: str) -> dict:
        """Removes a record (RecordError when it isn't there), recorded as a life event."""
        found = self.get(set_id)
        record = next((r for r in found["records"] if r["id"] == record_id), None)
        if record is None:
            raise RecordError("That record isn't there.")
        found["records"].remove(record)
        self._save()
        life_events.record(self, "record_removed", f"Removed from {found['name']}", refs=[f"record_set:{set_id}"])
        return record
