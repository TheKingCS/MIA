"""
tests.test_smart_suggestions
===============================

Unit tests for core.smart_suggestions — no Qt, no manager instances,
same shape as tests/test_budget_nudges.py.
"""

from __future__ import annotations

from datetime import date

from core.kitchen_manager import PantryItem
from core.smart_suggestions import (
    build_pantry_suggestion,
    build_recovery_suggestion,
    build_smart_suggestions_message,
)


def _pantry_item(name="Milk", expiration_date="") -> PantryItem:
    return PantryItem(item_id="p1", name=name, expiration_date=expiration_date)


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
    assert build_smart_suggestions_message(None, [], date(2026, 9, 10)) is None


def test_build_smart_suggestions_message_joins_both_real_findings():
    items = [_pantry_item(name="Milk", expiration_date="2026-09-12")]
    message = build_smart_suggestions_message("2026-09-09", items, date(2026, 9, 10))
    assert message is not None
    assert "yesterday" in message.lower()
    assert "Milk" in message


def test_build_smart_suggestions_message_only_recovery():
    message = build_smart_suggestions_message("2026-09-09", [], date(2026, 9, 10))
    assert message is not None
    assert "yesterday" in message.lower()


def test_build_smart_suggestions_message_only_pantry():
    items = [_pantry_item(name="Milk", expiration_date="2026-09-12")]
    message = build_smart_suggestions_message(None, items, date(2026, 9, 10))
    assert message is not None
    assert "Milk" in message
