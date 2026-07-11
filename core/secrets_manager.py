"""
core.secrets_manager
======================

Passphrase-based symmetric encryption for anything M.I.A. needs to keep
confidential at rest — introduced for encrypted Backup/Restore
(core/backup_manager.py), but deliberately generic rather than
backup-specific, so a future module with a real secret to protect
(wifi credentials, radio configs, an API key) has a ready-made,
already-proven place to call rather than inventing its own scheme.

Deliberately NOT built out further than this right now — no key
storage, no per-profile keys, no "encrypt this config value"
convenience wrapper — because those all depend on a concrete future
need (which value, tied to which profile, unlocked how) we don't have
yet. See docs/ARCHITECTURE.md's module layering rationale for why this
project pays structural cost early only for shapes that are already
known, not speculatively.

Uses Fernet (AES-128-CBC + HMAC-SHA256, authenticated encryption) with
a key derived from the caller-supplied passphrase via PBKDF2-HMAC-SHA256
— the same KDF core.profile_manager already uses for password hashing,
just applied here to derive an encryption key instead of a comparison
hash. A random salt is generated per encryption and packed into the
output, so the same passphrase never produces the same key twice.

Wrong passphrase / corrupted data raises SecretsError with a clear
message rather than leaking a raw cryptography exception.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.logger import get_logger

log = get_logger(__name__)

_PBKDF2_ITERATIONS = 200_000
_SALT_LENGTH = 16


class SecretsError(Exception):
    """Raised when encryption/decryption fails — wrong passphrase or corrupted data."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def encrypt_bytes(data: bytes, passphrase: str) -> bytes:
    """
    Encrypt `data` with `passphrase`. The returned blob is
    self-contained (salt + ciphertext) — decrypt_bytes needs nothing
    else besides the same passphrase.
    """
    salt = os.urandom(_SALT_LENGTH)
    key = _derive_key(passphrase, salt)
    ciphertext = Fernet(key).encrypt(data)
    return salt + ciphertext


def decrypt_bytes(blob: bytes, passphrase: str) -> bytes:
    """
    Decrypt a blob produced by encrypt_bytes. Raises SecretsError if
    the passphrase is wrong or the blob is corrupted/truncated —
    Fernet's HMAC check makes tampering detectable rather than
    silently returning garbage.
    """
    if len(blob) < _SALT_LENGTH:
        raise SecretsError("Not a valid encrypted blob (too short).")

    salt, ciphertext = blob[:_SALT_LENGTH], blob[_SALT_LENGTH:]
    key = _derive_key(passphrase, salt)
    try:
        return Fernet(key).decrypt(ciphertext)
    except InvalidToken as exc:
        raise SecretsError("Incorrect passphrase or corrupted data.") from exc
