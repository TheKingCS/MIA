"""
tests.test_relationships_module
==================================

Unit tests for modules.relationships.module's pure row formatters — no
Qt widget construction, same shape as tests/test_kitchen_module.py's own
formatter tests.
"""

from __future__ import annotations

from datetime import date

from core.relationships_manager import Person, Pet
from modules.relationships.module import (
    _birthday_tag,
    format_person_row,
    format_pet_row,
)


def _person(name="Jamie", relationship="", birthday="") -> Person:
    return Person(person_id="p1", name=name, relationship=relationship, birthday=birthday)


def _pet(name="Rex", species="", birthday="") -> Pet:
    return Pet(pet_id="x1", name=name, species=species, birthday=birthday)


# ------------------------------------------------------------------
# _birthday_tag
# ------------------------------------------------------------------

def test_birthday_tag_empty_when_unset():
    assert _birthday_tag("", date(2026, 9, 10)) == ""


def test_birthday_tag_today():
    assert _birthday_tag("1990-09-10", date(2026, 9, 10)) == "[BIRTHDAY TODAY]  "


def test_birthday_tag_upcoming():
    assert _birthday_tag("1990-09-17", date(2026, 9, 10)) == "[BIRTHDAY IN 7d]  "


# ------------------------------------------------------------------
# format_person_row
# ------------------------------------------------------------------

def test_format_person_row_name_only():
    row = format_person_row(_person(name="Jamie"), date(2026, 9, 10))
    assert row == "Jamie"


def test_format_person_row_includes_relationship():
    row = format_person_row(_person(name="Jamie", relationship="Sister"), date(2026, 9, 10))
    assert "Jamie" in row
    assert "[Sister]" in row


def test_format_person_row_includes_birthday_tag():
    row = format_person_row(_person(name="Jamie", birthday="1990-09-17"), date(2026, 9, 10))
    assert row.startswith("[BIRTHDAY IN 7d]")
    assert "Jamie" in row


# ------------------------------------------------------------------
# format_pet_row
# ------------------------------------------------------------------

def test_format_pet_row_name_only():
    row = format_pet_row(_pet(name="Rex"), date(2026, 9, 10))
    assert row == "Rex"


def test_format_pet_row_includes_species():
    row = format_pet_row(_pet(name="Rex", species="Dog"), date(2026, 9, 10))
    assert "Rex" in row
    assert "[Dog]" in row


def test_format_pet_row_includes_birthday_tag():
    row = format_pet_row(_pet(name="Rex", birthday="1990-09-10"), date(2026, 9, 10))
    assert row.startswith("[BIRTHDAY TODAY]")
    assert "Rex" in row
