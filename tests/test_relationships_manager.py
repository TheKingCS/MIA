"""
tests.test_relationships_manager
===================================

Unit tests for core.relationships_manager. Isolates _DATA_DIR/the two
per-record-type file constants into a tmp_path scratch area, same
monkeypatch pattern as test_workout_manager.py's isolated_paths.
"""

from __future__ import annotations

from datetime import date

import pytest

import core.relationships_manager as relationships_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.relationships_manager import (
    Person,
    Pet,
    RelationshipsManager,
    days_until_birthday,
)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(relationships_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(relationships_manager_module, "_PEOPLE_FILE", data_dir / "relationships_people.json")
    monkeypatch.setattr(relationships_manager_module, "_PETS_FILE", data_dir / "relationships_pets.json")
    return data_dir


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


def _make_manager(context: AppContext) -> RelationshipsManager:
    manager = RelationshipsManager(context)
    context.relationships = manager
    return manager


# ------------------------------------------------------------------
# days_until_birthday
# ------------------------------------------------------------------

def test_days_until_birthday_none_when_unset():
    assert days_until_birthday("", date(2026, 9, 10)) is None


def test_days_until_birthday_none_for_unparseable():
    assert days_until_birthday("not-a-date", date(2026, 9, 10)) is None


def test_days_until_birthday_zero_when_today():
    assert days_until_birthday("1990-09-10", date(2026, 9, 10)) == 0


def test_days_until_birthday_counts_forward_within_this_year():
    assert days_until_birthday("1990-09-17", date(2026, 9, 10)) == 7


def test_days_until_birthday_wraps_to_next_year_once_passed():
    # Jan 1 birthday, checked from Dec 30 — wraps forward, not negative.
    days = days_until_birthday("1990-01-01", date(2026, 12, 30))
    assert days == 2


def test_days_until_birthday_none_for_feb_29_in_a_non_leap_year():
    # 2026 is not a leap year — no fabricated "closest" date.
    assert days_until_birthday("1990-02-29", date(2026, 2, 20)) is None


# ------------------------------------------------------------------
# Person CRUD
# ------------------------------------------------------------------

def test_add_person_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_person(name="Jamie", relationship="Sister", birthday="1990-09-17")

    reloaded = RelationshipsManager(context)
    people = reloaded.all_people()
    assert len(people) == 1
    assert people[0].name == "Jamie"
    assert people[0].relationship == "Sister"
    assert people[0].birthday == "1990-09-17"


def test_update_person_changes_fields(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    person = manager.add_person(name="Jamie")
    manager.update_person(person.person_id, name="Jamie Lee", gift_ideas="Headphones")
    updated = manager.get_person(person.person_id)
    assert updated.name == "Jamie Lee"
    assert updated.gift_ideas == "Headphones"


def test_update_person_unknown_field_raises(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    person = manager.add_person(name="Jamie")
    with pytest.raises(ValueError):
        manager.update_person(person.person_id, nonsense_field="x")


def test_update_person_unknown_id_raises(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.update_person("nonexistent", name="X")


def test_delete_person_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    person = manager.add_person(name="Jamie")
    manager.delete_person(person.person_id)
    assert manager.get_person(person.person_id) is None
    assert manager.all_people() == []


def test_get_person_returns_none_when_missing(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.get_person("nonexistent") is None


def test_all_people_sorted_by_name(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_person(name="Zoe")
    manager.add_person(name="alex")
    manager.add_person(name="Mia")
    names = [p.name for p in manager.all_people()]
    assert names == ["alex", "Mia", "Zoe"]


# ------------------------------------------------------------------
# Pet CRUD
# ------------------------------------------------------------------

def test_add_pet_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_pet(name="Rex", species="Dog", medical_notes="Allergic to chicken")

    reloaded = RelationshipsManager(context)
    pets = reloaded.all_pets()
    assert len(pets) == 1
    assert pets[0].name == "Rex"
    assert pets[0].species == "Dog"
    assert pets[0].medical_notes == "Allergic to chicken"


def test_update_pet_changes_fields(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    pet = manager.add_pet(name="Rex")
    manager.update_pet(pet.pet_id, species="Dog", notes="Loves the park")
    updated = manager.get_pet(pet.pet_id)
    assert updated.species == "Dog"
    assert updated.notes == "Loves the park"


def test_update_pet_unknown_id_raises(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.update_pet("nonexistent", name="X")


def test_delete_pet_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    pet = manager.add_pet(name="Rex")
    manager.delete_pet(pet.pet_id)
    assert manager.get_pet(pet.pet_id) is None
    assert manager.all_pets() == []


def test_all_pets_sorted_by_name(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_pet(name="Zeus")
    manager.add_pet(name="apollo")
    names = [p.name for p in manager.all_pets()]
    assert names == ["apollo", "Zeus"]


# ------------------------------------------------------------------
# to_dict / from_dict round-trip
# ------------------------------------------------------------------

def test_person_from_dict_backward_compatible_with_missing_fields():
    person = Person.from_dict({"person_id": "p1", "name": "Jamie"})
    assert person.relationship == ""
    assert person.birthday == ""
    assert person.gift_ideas == ""


def test_pet_from_dict_backward_compatible_with_missing_fields():
    pet = Pet.from_dict({"pet_id": "x1", "name": "Rex"})
    assert pet.species == ""
    assert pet.medical_notes == ""


# ------------------------------------------------------------------
# nearest_upcoming_birthday
# ------------------------------------------------------------------

def test_nearest_upcoming_birthday_none_when_no_people(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.nearest_upcoming_birthday(date(2026, 9, 10)) is None


def test_nearest_upcoming_birthday_none_when_no_birthdays_set(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_person(name="Jamie")
    assert manager.nearest_upcoming_birthday(date(2026, 9, 10)) is None


def test_nearest_upcoming_birthday_picks_the_soonest(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_person(name="Jamie", birthday="1990-12-25")
    manager.add_person(name="Alex", birthday="1990-09-17")
    result = manager.nearest_upcoming_birthday(date(2026, 9, 10))
    assert result is not None
    person, days = result
    assert person.name == "Alex"
    assert days == 7
