"""
core.password_strength
=========================

Password strength estimation — docs/ROADMAP.md milestone 11.5, Field
Kit's Security/Network Toolkit. A simple Shannon-entropy-over-character-
pool-size estimate plus a handful of pattern warnings, not a full
zxcvbn-style dictionary/pattern-cracking-time model — "don't
over-engineer" for a field tool's quick strength check, same
reasoning as this project's other identification/estimation tables
(hash identification, board identification).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

_COMMON_PASSWORDS = {
    "password", "123456", "12345678", "123456789", "qwerty", "letmein",
    "admin", "welcome", "111111", "abc123", "iloveyou", "monkey", "dragon",
}

_MIN_RECOMMENDED_LENGTH = 8


@dataclass
class PasswordStrength:
    entropy_bits: float
    rating: str  # "Very Weak" | "Weak" | "Moderate" | "Strong" | "Very Strong"
    warnings: list[str] = field(default_factory=list)


def assess_password(password: str) -> PasswordStrength:
    if not password:
        return PasswordStrength(entropy_bits=0.0, rating="Very Weak", warnings=["Password is empty."])

    warnings = []
    if password.lower() in _COMMON_PASSWORDS:
        warnings.append("This is one of the most commonly used passwords in the world.")
    if len(password) < _MIN_RECOMMENDED_LENGTH:
        warnings.append(f"Shorter than {_MIN_RECOMMENDED_LENGTH} characters.")

    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    if sum([has_lower, has_upper, has_digit, has_symbol]) <= 1:
        warnings.append("Uses only one character type (e.g. all lowercase letters).")

    pool_size = 26 * has_lower + 26 * has_upper + 10 * has_digit + 32 * has_symbol
    entropy_bits = round(len(password) * math.log2(pool_size), 1) if pool_size else 0.0

    if password.lower() in _COMMON_PASSWORDS:
        # A common password is weak regardless of what its raw entropy
        # math says — an attacker checks the common-password list
        # before brute-forcing the full character space.
        rating = "Very Weak"
    elif entropy_bits < 28:
        rating = "Very Weak"
    elif entropy_bits < 36:
        rating = "Weak"
    elif entropy_bits < 60:
        rating = "Moderate"
    elif entropy_bits < 80:
        rating = "Strong"
    else:
        rating = "Very Strong"

    return PasswordStrength(entropy_bits=entropy_bits, rating=rating, warnings=warnings)
