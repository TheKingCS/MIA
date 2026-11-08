"""
core.two_step
===============

Two-step sign-in (docs/SECURITY.md step 4; Zac, 2026-11-08: "fortify our security measures to industry standards and
beyond"): signing in from another device asks, after the password, for the 6-digit code an authenticator app shows
(Google Authenticator, Microsoft Authenticator, Authy, a password manager). The codes are TOTP (RFC 6238): HMAC-SHA1
of the 30-second step since 1970 with the account's secret, 6 digits, the step before and after accepted for a clock
a little off; a code that's been used is never accepted again (`StepMemory`).

Turning it on (`/api/account/two-step/*`): MIA makes a secret and shows it as a key to type in (and an otpauth link a
phone opens straight in its app); it's on only once a code from the app is entered, so a mistyped key can't lock
anyone out. Off needs the password and a current code. The secret is kept in the account's record; the recovery code
still gets a person back in when the phone with the app is lost (it sets a new password and turns this off).

The PC's own window never asks: it's signed in by the person already at the computer.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import threading
import time
from typing import Optional
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1  # steps either side accepted


def new_secret() -> str:
    """A new random secret: 160 bits, base32 without padding (what authenticator apps expect)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _key(secret: str) -> bytes:
    """Pure logic. The secret's bytes from its base32 (spaces and case ignored, padding restored)."""
    clean = "".join(secret.split()).upper()
    return base64.b32decode(clean + "=" * (-len(clean) % 8))


def code_at(secret: str, step: int) -> str:
    """Pure logic. The 6-digit code for one 30-second step (RFC 6238 / RFC 4226)."""
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10 ** DIGITS).zfill(DIGITS)


def step_of(now: Optional[float] = None) -> int:
    """Pure logic. The 30-second step a moment falls in."""
    return int((time.time() if now is None else now) // STEP_SECONDS)


def matching_step(secret: str, code: str, now: Optional[float] = None) -> Optional[int]:
    """Pure logic. The step a code belongs to (this one or one either side), compared in constant time; None when it's
    wrong or not 6 digits."""
    code = "".join(str(code or "").split())
    if len(code) != DIGITS or not code.isdigit() or not secret:
        return None
    here = step_of(now)
    found = None
    for step in range(here - WINDOW, here + WINDOW + 1):
        if hmac.compare_digest(code_at(secret, step), code):
            found = step
    return found


def otpauth_uri(secret: str, account: str, issuer: str = "MIA") -> str:
    """Pure logic. The link an authenticator app reads (a phone opens it in the app)."""
    label = quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"


def grouped(secret: str) -> str:
    """Pure logic. The key in groups of four, easier to type into an app by hand."""
    return " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))


class StepMemory:
    """The last step each account's code was used at, so a code is never accepted twice (a code someone saw over a
    shoulder or in a log is already spent); thread-safe, in memory."""

    def __init__(self) -> None:
        """Nothing used yet."""
        self._last: dict[str, int] = {}
        self._lock = threading.Lock()

    def accept(self, account: str, secret: str, code: str, now: Optional[float] = None) -> bool:
        """Whether a code is right and not used before for this account; a right one is spent."""
        step = matching_step(secret, code, now)
        if step is None:
            return False
        with self._lock:
            if step <= self._last.get(account, -1):
                return False
            self._last[account] = step
            return True
