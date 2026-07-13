"""
core.hash_identifier
=======================

Identifies the plausible algorithm(s) for a hash string, by prefix
(for self-describing formats like bcrypt/crypt) or length+charset (for
bare hex digests) — docs/ROADMAP.md milestone 11.5, Field Kit's
Security/Network Toolkit. This is pattern-matching, not verification:
there is no way to truly determine a hash's algorithm from the digest
alone, and several algorithms share a digest length (MD5 and NTLM are
both 32 hex characters, for example) — hence a *list* of candidates,
not a single answer. Good-enough identification, not an exhaustive
hash-format database, same "don't over-engineer" reasoning as
core/device_framework.py's VID:PID board-identification table.
"""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")

# Self-describing prefixed formats, checked before the bare-hex table
# below — order matters, since e.g. "$2a$"/"$2b$"/"$2y$" are all bcrypt
# version markers.
_PREFIX_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("$2a$", "bcrypt"),
    ("$2b$", "bcrypt"),
    ("$2y$", "bcrypt"),
    ("$1$", "MD5 crypt"),
    ("$5$", "SHA-256 crypt"),
    ("$6$", "SHA-512 crypt"),
)

# Bare-hex digest length (characters, not bytes) -> plausible algorithms.
_HEX_LENGTH_CANDIDATES: dict[int, list[str]] = {
    32: ["MD5", "NTLM"],
    40: ["SHA-1"],
    56: ["SHA-224"],
    64: ["SHA-256"],
    96: ["SHA-384"],
    128: ["SHA-512"],
}


def identify_hash(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []

    for prefix, name in _PREFIX_CANDIDATES:
        if value.startswith(prefix):
            return [name]

    if _HEX_RE.match(value):
        return _HEX_LENGTH_CANDIDATES.get(len(value), [])

    return []
