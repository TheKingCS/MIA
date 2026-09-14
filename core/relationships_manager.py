"""
core.relationships_manager
=============================

Relationship Profiles and Pet Profiles — docs/VISION.md's own
"structured extensions of the same idea" as Memory Palace
(core/user_memory_manager.py). One manager, two related dataclasses,
same shape as core/kitchen_manager.py.

"Favorite things"/"gift ideas" (Person) and "medical history" (Pet)
are single freeform text fields the user edits as a running note, not
structured sub-lists — same "don't force premature structure" call
made throughout this session (core.kitchen_manager.Recipe.instructions,
core.workout_manager.WorkoutTemplate's own notes field).

Deliberately no photo support yet, despite VISION naming it for Pet
Profiles — real file-import handling (a configurable photo root, an
import dialog, orphaned-file cleanup on delete — the exact
core.trip_manager.TripManager.add_photo() precedent) is real added
scope on top of an already-large pass; medical_notes covers the real
"have this on hand" need in text form today. Visual recognition is
explicitly framed as hardware-optional/future in VISION itself.

Person.birthday feeds core/smart_suggestions.py's own gift-reminder
check — the real payoff for deferring that example when Smart
Suggestions first shipped this session.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PEOPLE_FILE = _DATA_DIR / "relationships_people.json"
_PETS_FILE = _DATA_DIR / "relationships_pets.json"


@dataclass
class Person:
    person_id: str
    name: str
    relationship: str = ""  # freeform: "Sister", "Best friend", "Coworker", ...
    birthday: str = ""      # ISO "YYYY-MM-DD", "" = not set
    favorite_things: str = ""
    gift_ideas: str = ""
    notes: str = ""          # "shared memories" — freeform
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "person_id": self.person_id, "name": self.name, "relationship": self.relationship,
            "birthday": self.birthday, "favorite_things": self.favorite_things,
            "gift_ideas": self.gift_ideas, "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Person":
        return Person(
            person_id=data.get("person_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            relationship=data.get("relationship", ""),
            birthday=data.get("birthday", ""),
            favorite_things=data.get("favorite_things", ""),
            gift_ideas=data.get("gift_ideas", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class Pet:
    pet_id: str
    name: str
    species: str = ""        # freeform: "Dog", "Cat", "Bird", ...
    birthday: str = ""       # ISO date (birthday or adoption date), "" = not set
    medical_notes: str = ""  # medical history + vet visits — freeform
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "pet_id": self.pet_id, "name": self.name, "species": self.species,
            "birthday": self.birthday, "medical_notes": self.medical_notes,
            "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Pet":
        return Pet(
            pet_id=data.get("pet_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            species=data.get("species", ""),
            birthday=data.get("birthday", ""),
            medical_notes=data.get("medical_notes", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


def days_until_birthday(birthday_iso: str, today: date) -> Optional[int]:
    """Pure logic — testable without Qt. Days until the NEXT occurrence
    of this month/day (year is irrelevant — same "compare month/day
    only" convention core.daily_occasions.is_birthday_today() already
    uses), wrapping to next year once this year's date has passed.
    0 means today. None when birthday_iso is unset/unparseable."""
    if not birthday_iso:
        return None
    try:
        parsed = date.fromisoformat(birthday_iso)
    except ValueError:
        return None
    try:
        next_occurrence = date(today.year, parsed.month, parsed.day)
    except ValueError:
        return None  # real Feb 29 birthday in a non-leap today.year — no fabricated "closest" date
    if next_occurrence < today:
        try:
            next_occurrence = date(today.year + 1, parsed.month, parsed.day)
        except ValueError:
            return None
    return (next_occurrence - today).days


class RelationshipsManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._people: list[Person] = []
        self._pets: list[Pet] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._people = self._load_file(_PEOPLE_FILE, Person)
        self._pets = self._load_file(_PETS_FILE, Pet)

    @staticmethod
    def _load_file(path: Path, cls) -> list:
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [cls.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            return []

    @staticmethod
    def _save_file(path: Path, records: list) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps([r.to_dict() for r in records], indent=2), encoding="utf-8")

    def _save_people(self) -> None:
        self._save_file(_PEOPLE_FILE, self._people)

    def _save_pets(self) -> None:
        self._save_file(_PETS_FILE, self._pets)

    # ------------------------------------------------------------------
    # Person CRUD
    # ------------------------------------------------------------------

    def add_person(
        self, name: str, relationship: str = "", birthday: str = "",
        favorite_things: str = "", gift_ideas: str = "", notes: str = "",
    ) -> Person:
        person = Person(
            person_id=uuid.uuid4().hex[:10],
            name=name,
            relationship=relationship,
            birthday=birthday,
            favorite_things=favorite_things,
            gift_ideas=gift_ideas,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._people.append(person)
        self._save_people()
        log.info("Person added: '%s'", person.name)
        return person

    def update_person(self, person_id: str, **fields) -> Person:
        person = self.get_person(person_id)
        if person is None:
            raise ValueError(f"No person with id '{person_id}'.")
        for key, value in fields.items():
            if not hasattr(person, key):
                raise ValueError(f"Person has no field '{key}'.")
            setattr(person, key, value)
        self._save_people()
        return person

    def delete_person(self, person_id: str) -> None:
        self._people = [p for p in self._people if p.person_id != person_id]
        self._save_people()

    def get_person(self, person_id: str) -> Optional[Person]:
        for person in self._people:
            if person.person_id == person_id:
                return person
        return None

    def all_people(self) -> list[Person]:
        return sorted(self._people, key=lambda p: p.name.lower())

    # ------------------------------------------------------------------
    # Pet CRUD
    # ------------------------------------------------------------------

    def add_pet(
        self, name: str, species: str = "", birthday: str = "", medical_notes: str = "", notes: str = "",
    ) -> Pet:
        pet = Pet(
            pet_id=uuid.uuid4().hex[:10],
            name=name,
            species=species,
            birthday=birthday,
            medical_notes=medical_notes,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._pets.append(pet)
        self._save_pets()
        log.info("Pet added: '%s'", pet.name)
        return pet

    def update_pet(self, pet_id: str, **fields) -> Pet:
        pet = self.get_pet(pet_id)
        if pet is None:
            raise ValueError(f"No pet with id '{pet_id}'.")
        for key, value in fields.items():
            if not hasattr(pet, key):
                raise ValueError(f"Pet has no field '{key}'.")
            setattr(pet, key, value)
        self._save_pets()
        return pet

    def delete_pet(self, pet_id: str) -> None:
        self._pets = [p for p in self._pets if p.pet_id != pet_id]
        self._save_pets()

    def get_pet(self, pet_id: str) -> Optional[Pet]:
        for pet in self._pets:
            if pet.pet_id == pet_id:
                return pet
        return None

    def all_pets(self) -> list[Pet]:
        return sorted(self._pets, key=lambda p: p.name.lower())

    # ------------------------------------------------------------------
    # Birthdays
    # ------------------------------------------------------------------

    def nearest_upcoming_birthday(self, today: date) -> Optional[tuple[Person, int]]:
        """(person, days_until) for whichever tracked Person has the
        soonest upcoming birthday, or None if no Person has one set —
        the real fact the dashboard widget leads with."""
        candidates = []
        for person in self._people:
            days = days_until_birthday(person.birthday, today)
            if days is not None:
                candidates.append((person, days))
        if not candidates:
            return None
        return min(candidates, key=lambda pair: pair[1])
