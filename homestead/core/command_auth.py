"""
The signature on MIA's directions to this node (DEC-0185; docs/MIA_COMMAND_INTERFACE.md, step 2 of 4).

A pure utility (no hardware, nothing to describe): viewer/serve_exports.py calls `verify()` before a direction
reaches core/mia_commands.py, and MIA's PC calls `sign()` with the same key.

**The key** (`load_key`): 32 random bytes, hex, in `config/mia_command_key` on this node (git-ignored, and never
part of a push), made on MIA's PC for this node alone when it's provisioned and sent here over SSH on standard input,
readable by its owner only (MIA's core/greenhouse_provision.py). A key per node, so a direction signed for one node
never works on another. No key file: every direction is refused, never accepted unsigned.

**A signed request** carries three headers: `X-MIA-Timestamp` (UTC seconds), `X-MIA-Nonce` (one-time, 16-64 safe
characters) and `X-MIA-Signature` (HMAC-SHA256, hex, over "timestamp\\nnonce\\nbody"). `verify()` refuses one
missing any of them, one whose time is more than `WINDOW` seconds from the node's, a nonce already seen (nonces are
kept in `mia_command_nonces` for twice the window), a signature that doesn't match (compared in constant time), and
one more than `WINDOW` older than the newest request ever accepted (`mia_command_state`'s high-water mark): so a
captured request can't be replayed later even if the node's clock is moved back and its nonce has been let go.
The reason is for the node's own log only; the caller is only ever told "refused".
"""

from __future__ import annotations

import hashlib
import hmac
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

KEY_PATH = Path(__file__).resolve().parent.parent / "config" / "mia_command_key"
WINDOW = 300  # seconds either side of the node's clock
MAX_BODY = 4096  # bytes: one direction is a few hundred
_NONCE = re.compile(r"[A-Za-z0-9_-]{16,64}")
_STAMP = re.compile(r"[0-9]{1,12}")
NONCE_SQL = "CREATE TABLE IF NOT EXISTS mia_command_nonces (nonce TEXT PRIMARY KEY, seen_at TEXT NOT NULL)"
STATE_SQL = "CREATE TABLE IF NOT EXISTS mia_command_state (name TEXT PRIMARY KEY, value INTEGER NOT NULL)"


def load_key(path: Path = KEY_PATH) -> bytes | None:
    """The shared key, or None (no file, or not at least 32 bytes of hex)."""
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
        key = bytes.fromhex(text)
    except (OSError, ValueError):
        return None
    return key if len(key) >= 32 else None


def sign(key: bytes, timestamp: str, nonce: str, body: bytes) -> str:
    """The signature for a request: HMAC-SHA256 (hex) over timestamp, nonce and body, newline-separated."""
    return hmac.new(key, f"{timestamp}\n{nonce}\n".encode() + body, hashlib.sha256).hexdigest()


def verify(db: sqlite3.Connection, key: bytes | None, headers, body: bytes,
           now: datetime | None = None) -> tuple[bool, str]:
    """Whether a request is signed with the key, fresh, newer than the high-water mark allows and not a replay:
    (True, "") or (False, why: for the node's log, never for the caller). A request that passes is recorded (its
    nonce, and the high-water mark moved up), so the same request is refused the second time."""
    if key is None:
        return False, "this node has no key for MIA's directions yet"
    stamp, nonce, signature = (str(headers.get(h) or "") for h in ("X-MIA-Timestamp", "X-MIA-Nonce",
                                                                    "X-MIA-Signature"))
    if not stamp or not nonce or not signature:
        return False, "unsigned"
    if not _NONCE.fullmatch(nonce) or not _STAMP.fullmatch(stamp):
        return False, "bad nonce or timestamp"
    now = now or datetime.utcnow()
    sent = datetime(1970, 1, 1) + timedelta(seconds=int(stamp))
    if abs((now - sent).total_seconds()) > WINDOW:
        return False, "too old or too far ahead"
    if not hmac.compare_digest(sign(key, stamp, nonce, body), signature.lower()):
        return False, "bad signature"
    db.execute(NONCE_SQL)
    db.execute(STATE_SQL)
    high = db.execute("SELECT value FROM mia_command_state WHERE name = 'high_water'").fetchone()
    if high is not None and int(stamp) < high[0] - WINDOW:
        db.commit()
        return False, "older than a request already accepted"
    db.execute("DELETE FROM mia_command_nonces WHERE seen_at < ?",
               ((now - timedelta(seconds=2 * WINDOW)).isoformat(timespec="seconds"),))
    try:
        db.execute("INSERT INTO mia_command_nonces (nonce, seen_at) VALUES (?, ?)",
                   (nonce, now.isoformat(timespec="seconds")))
    except sqlite3.IntegrityError:
        db.commit()
        return False, "replayed"
    db.execute("INSERT INTO mia_command_state (name, value) VALUES ('high_water', ?) ON CONFLICT(name) DO UPDATE "
               "SET value = MAX(value, excluded.value)", (int(stamp),))
    db.commit()
    return True, ""
