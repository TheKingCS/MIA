"""
tests.test_smart_suggestions
===============================

Unit tests for core.smart_suggestions — no Qt, no manager instances,
same shape as tests/test_budget_nudges.py.
"""

from __future__ import annotations

from datetime import date

from core.kitchen_manager import PantryItem
from core.relationships_manager import Person
from core.smart_suggestions import (
    build_gift_reminder_suggestion,
    build_pantry_suggestion,
    build_recovery_suggestion,
    build_smart_suggestions_message,
    build_walkthrough_suggestion,
)


def _pantry_item(name="Milk", expiration_date="") -> PantryItem:
    return PantryItem(item_id="p1", name=name, expiration_date=expiration_date)


def _person(name="Jamie", birthday="", gift_ideas="") -> Person:
    return Person(person_id="p1", name=name, birthday=birthday, gift_ideas=gift_ideas)


# ------------------------------------------------------------------
# build_recovery_suggestion
# ------------------------------------------------------------------

def test_build_recovery_suggestion_none_when_never_logged():
    assert build_recovery_suggestion(None, date(2026, 9, 10)) is None


def test_build_recovery_suggestion_fires_when_session_was_yesterday():
    message = build_recovery_suggestion("2026-09-09", date(2026, 9, 10))
    assert message is not None
    assert "yesterday" in message.lower()


def test_build_recovery_suggestion_none_when_session_was_today():
    assert build_recovery_suggestion("2026-09-10", date(2026, 9, 10)) is None


def test_build_recovery_suggestion_none_when_session_was_two_days_ago():
    assert build_recovery_suggestion("2026-09-08", date(2026, 9, 10)) is None


def test_build_recovery_suggestion_none_for_unparseable_date():
    assert build_recovery_suggestion("not-a-date", date(2026, 9, 10)) is None


# ------------------------------------------------------------------
# build_pantry_suggestion
# ------------------------------------------------------------------

def test_build_pantry_suggestion_none_when_pantry_empty():
    assert build_pantry_suggestion([], date(2026, 9, 10)) is None


def test_build_pantry_suggestion_none_when_nothing_expiring():
    items = [_pantry_item(name="Flour", expiration_date="")]
    assert build_pantry_suggestion(items, date(2026, 9, 10)) is None


def test_build_pantry_suggestion_none_when_expiration_is_far_off():
    items = [_pantry_item(name="Flour", expiration_date="2026-12-01")]
    assert build_pantry_suggestion(items, date(2026, 9, 10)) is None


def test_build_pantry_suggestion_names_expiring_item():
    items = [_pantry_item(name="Milk", expiration_date="2026-09-12")]
    message = build_pantry_suggestion(items, date(2026, 9, 10))
    assert message is not None
    assert "Milk" in message


def test_build_pantry_suggestion_names_already_expired_item():
    items = [_pantry_item(name="Yogurt", expiration_date="2026-09-01")]
    message = build_pantry_suggestion(items, date(2026, 9, 10))
    assert message is not None
    assert "Yogurt" in message


def test_build_pantry_suggestion_names_multiple_items():
    items = [
        _pantry_item(name="Milk", expiration_date="2026-09-12"),
        _pantry_item(name="Eggs", expiration_date="2026-09-11"),
        _pantry_item(name="Flour", expiration_date="2026-12-01"),  # not expiring, excluded
    ]
    message = build_pantry_suggestion(items, date(2026, 9, 10))
    assert "Milk" in message
    assert "Eggs" in message
    assert "Flour" not in message


# ------------------------------------------------------------------
# build_smart_suggestions_message
# ------------------------------------------------------------------

def test_build_smart_suggestions_message_none_when_everything_is_quiet():
    assert build_smart_suggestions_message(None, [], [], date(2026, 9, 10)) is None


def test_build_smart_suggestions_message_joins_both_real_findings():
    items = [_pantry_item(name="Milk", expiration_date="2026-09-12")]
    message = build_smart_suggestions_message("2026-09-09", items, [], date(2026, 9, 10))
    assert message is not None
    assert "yesterday" in message.lower()
    assert "Milk" in message


def test_build_smart_suggestions_message_only_recovery():
    message = build_smart_suggestions_message("2026-09-09", [], [], date(2026, 9, 10))
    assert message is not None
    assert "yesterday" in message.lower()


def test_build_smart_suggestions_message_only_pantry():
    items = [_pantry_item(name="Milk", expiration_date="2026-09-12")]
    message = build_smart_suggestions_message(None, items, [], date(2026, 9, 10))
    assert message is not None
    assert "Milk" in message


def test_build_smart_suggestions_message_only_gift_reminder():
    people = [_person(name="Jamie", birthday="2026-09-17")]
    message = build_smart_suggestions_message(None, [], people, date(2026, 9, 10))
    assert message is not None
    assert "Jamie" in message


def test_build_smart_suggestions_message_joins_all_three():
    items = [_pantry_item(name="Milk", expiration_date="2026-09-12")]
    people = [_person(name="Jamie", birthday="2026-09-17")]
    message = build_smart_suggestions_message("2026-09-09", items, people, date(2026, 9, 10))
    assert message is not None
    assert "yesterday" in message.lower()
    assert "Milk" in message
    assert "Jamie" in message


# ------------------------------------------------------------------
# build_gift_reminder_suggestion
# ------------------------------------------------------------------

def test_build_gift_reminder_suggestion_none_when_no_people():
    assert build_gift_reminder_suggestion([], date(2026, 9, 10)) is None


def test_build_gift_reminder_suggestion_none_when_birthday_unset():
    people = [_person(name="Jamie", birthday="")]
    assert build_gift_reminder_suggestion(people, date(2026, 9, 10)) is None


def test_build_gift_reminder_suggestion_none_when_not_exactly_seven_days_out():
    people = [_person(name="Jamie", birthday="2026-09-16")]  # 6 days out
    assert build_gift_reminder_suggestion(people, date(2026, 9, 10)) is None


def test_build_gift_reminder_suggestion_fires_at_exactly_seven_days_out():
    people = [_person(name="Jamie", birthday="2026-09-17")]  # exactly 7 days out
    message = build_gift_reminder_suggestion(people, date(2026, 9, 10))
    assert message is not None
    assert "Jamie" in message
    assert "7 days" in message


def test_build_gift_reminder_suggestion_includes_gift_ideas_when_present():
    people = [_person(name="Jamie", birthday="2026-09-17", gift_ideas="Headphones")]
    message = build_gift_reminder_suggestion(people, date(2026, 9, 10))
    assert message is not None
    assert "Headphones" in message


def test_build_gift_reminder_suggestion_omits_gift_ideas_when_absent():
    people = [_person(name="Jamie", birthday="2026-09-17", gift_ideas="")]
    message = build_gift_reminder_suggestion(people, date(2026, 9, 10))
    assert message is not None
    assert "Gift ideas" not in message


def test_build_gift_reminder_suggestion_names_multiple_people():
    people = [
        _person(name="Jamie", birthday="2026-09-17"),
        _person(name="Alex", birthday="2026-09-17"),
        _person(name="Sam", birthday="2026-12-25"),  # not 7 days out, excluded
    ]
    message = build_gift_reminder_suggestion(people, date(2026, 9, 10))
    assert message is not None
    assert "Jamie" in message
    assert "Alex" in message
    assert "Sam" not in message


# ------------------------------------------------------------------
# build_walkthrough_suggestion
# ------------------------------------------------------------------

def test_build_walkthrough_suggestion_none_when_nothing_chosen():
    assert build_walkthrough_suggestion(None) is None


def test_build_walkthrough_suggestion_names_the_module_and_the_teach_me_phrase():
    message = build_walkthrough_suggestion("Kitchen")
    assert message is not None
    assert "Kitchen" in message
    assert 'teach me how kitchen works' in message
