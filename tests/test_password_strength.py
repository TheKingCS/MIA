"""
tests.test_password_strength
===============================

Unit tests for core.password_strength — pure computation, no
dependency, no mocks needed.
"""

from __future__ import annotations

from core.password_strength import assess_password


def test_empty_password_is_very_weak():
    result = assess_password("")
    assert result.rating == "Very Weak"
    assert result.entropy_bits == 0.0
    assert "empty" in result.warnings[0].lower()


def test_common_password_is_very_weak_regardless_of_length():
    result = assess_password("password")
    assert result.rating == "Very Weak"
    assert any("commonly used" in w for w in result.warnings)


def test_short_all_lowercase_password_is_weak():
    result = assess_password("abcdef")
    assert result.rating in ("Very Weak", "Weak")
    assert any("8 characters" in w for w in result.warnings)
    assert any("one character type" in w for w in result.warnings)


def test_long_mixed_password_is_strong():
    result = assess_password("Tr0ub4dor&3xtraLong!")
    assert result.rating in ("Strong", "Very Strong")
    assert result.warnings == []


def test_longer_password_has_higher_entropy_than_shorter_with_same_pool():
    short_result = assess_password("abcABC1!")
    long_result = assess_password("abcABC1!abcABC1!")
    assert long_result.entropy_bits > short_result.entropy_bits


def test_more_character_types_increases_entropy_at_same_length():
    lowercase_only = assess_password("abcdefgh")
    mixed_types = assess_password("aB3!efgh")
    assert mixed_types.entropy_bits > lowercase_only.entropy_bits


def test_single_character_type_warning_present_for_all_digits():
    result = assess_password("12345678901234")
    assert any("one character type" in w for w in result.warnings)


def test_case_insensitive_common_password_match():
    result = assess_password("PaSsWoRd")
    assert result.rating == "Very Weak"
    assert any("commonly used" in w for w in result.warnings)
