"""
tests.test_hash_identifier
============================

Unit tests for core.hash_identifier — pure pattern-matching logic, no
external dependency, real hashes used as test fixtures (not mocks).
"""

from __future__ import annotations

import hashlib

from core.hash_identifier import identify_hash


def test_identifies_real_md5_digest():
    digest = hashlib.md5(b"hello").hexdigest()
    assert "MD5" in identify_hash(digest)


def test_identifies_real_sha1_digest():
    digest = hashlib.sha1(b"hello").hexdigest()
    assert identify_hash(digest) == ["SHA-1"]


def test_identifies_real_sha256_digest():
    digest = hashlib.sha256(b"hello").hexdigest()
    assert identify_hash(digest) == ["SHA-256"]


def test_identifies_real_sha512_digest():
    digest = hashlib.sha512(b"hello").hexdigest()
    assert identify_hash(digest) == ["SHA-512"]


def test_md5_length_also_suggests_ntlm():
    digest = hashlib.md5(b"hello").hexdigest()
    assert identify_hash(digest) == ["MD5", "NTLM"]


def test_identifies_bcrypt_by_prefix():
    assert identify_hash("$2b$12$KIXQ4Z5z5z5z5z5z5z5z5uZ5z5z5z5z5z5z5z5z5z5z5z5z5z5z5") == ["bcrypt"]


def test_identifies_sha512_crypt_by_prefix():
    assert identify_hash("$6$somesalt$abcdefghijklmnopqrstuvwxyz") == ["SHA-512 crypt"]


def test_unrecognized_length_returns_empty_list():
    assert identify_hash("abc123") == []


def test_non_hex_value_returns_empty_list():
    assert identify_hash("not-a-hash-at-all!!") == []


def test_empty_string_returns_empty_list():
    assert identify_hash("") == []


def test_whitespace_only_returns_empty_list():
    assert identify_hash("   ") == []


def test_strips_surrounding_whitespace():
    digest = hashlib.sha256(b"hello").hexdigest()
    assert identify_hash(f"  {digest}  ") == ["SHA-256"]


def test_uppercase_hex_is_identified():
    digest = hashlib.sha256(b"hello").hexdigest().upper()
    assert identify_hash(digest) == ["SHA-256"]
