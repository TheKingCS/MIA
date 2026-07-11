"""
tests.test_secrets_manager
=============================

Unit tests for core.secrets_manager.encrypt_bytes / decrypt_bytes.
"""

from __future__ import annotations

import pytest

from core.secrets_manager import SecretsError, decrypt_bytes, encrypt_bytes


def test_roundtrip_returns_original_data():
    data = b"the quick brown fox jumps over the lazy dog"
    blob = encrypt_bytes(data, "correct horse battery staple")
    assert decrypt_bytes(blob, "correct horse battery staple") == data


def test_wrong_passphrase_raises_secrets_error():
    blob = encrypt_bytes(b"secret data", "right passphrase")
    with pytest.raises(SecretsError):
        decrypt_bytes(blob, "wrong passphrase")


def test_corrupted_blob_raises_secrets_error():
    blob = encrypt_bytes(b"secret data", "a passphrase")
    corrupted = blob[:-1] + bytes([blob[-1] ^ 0xFF])
    with pytest.raises(SecretsError):
        decrypt_bytes(corrupted, "a passphrase")


def test_too_short_blob_raises_secrets_error():
    with pytest.raises(SecretsError):
        decrypt_bytes(b"short", "any passphrase")


def test_same_data_encrypted_twice_produces_different_output():
    # A random salt per call means identical inputs must not produce
    # identical ciphertext — otherwise two backups would leak that
    # they contain the same data just by comparing bytes.
    blob1 = encrypt_bytes(b"same data", "same passphrase")
    blob2 = encrypt_bytes(b"same data", "same passphrase")
    assert blob1 != blob2
