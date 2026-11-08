"""
tests.test_two_step
=====================

Two-step sign-in (core/two_step.py, docs/SECURITY.md step 4): the codes are
RFC 6238's, a clock a step off still works, a used code never works twice, and
the authenticator link carries the secret and MIA's name.
"""

import base64

from core import two_step as ts

RFC_SECRET = base64.b32encode(b"12345678901234567890").decode().rstrip("=")


def test_the_codes_match_rfc_6238_s_published_values():
    """The RFC's SHA-1 vectors, last six digits."""
    assert ts.code_at(RFC_SECRET, 59 // 30) == "287082"
    assert ts.code_at(RFC_SECRET, 1111111109 // 30) == "081804"
    assert ts.code_at(RFC_SECRET, 1234567890 // 30) == "005924"


def test_a_code_from_the_step_before_or_after_still_works_but_not_further():
    """A clock off by one step is forgiven; two steps isn't; a non-number never matches."""
    now = 1_800_000_000
    assert ts.matching_step(RFC_SECRET, ts.code_at(RFC_SECRET, ts.step_of(now) - 1), now) == ts.step_of(now) - 1
    assert ts.matching_step(RFC_SECRET, ts.code_at(RFC_SECRET, ts.step_of(now) + 2), now) is None
    assert ts.matching_step(RFC_SECRET, "12ab56", now) is None and ts.matching_step(RFC_SECRET, "", now) is None


def test_a_code_is_spent_once_used():
    """The same code, or an older one, is refused after a newer one was accepted."""
    memory, now = ts.StepMemory(), 1_800_000_000
    code = ts.code_at(RFC_SECRET, ts.step_of(now))
    assert memory.accept("p1", RFC_SECRET, code, now)
    assert not memory.accept("p1", RFC_SECRET, code, now)
    assert not memory.accept("p1", RFC_SECRET, ts.code_at(RFC_SECRET, ts.step_of(now) - 1), now)


def test_new_secrets_are_random_160_bit_base32_and_the_link_names_mia():
    """Two secrets differ; each decodes to 20 bytes; the link is an otpauth TOTP link for MIA."""
    a, b = ts.new_secret(), ts.new_secret()
    assert a != b and len(base64.b32decode(a + "=" * (-len(a) % 8))) == 20
    link = ts.otpauth_uri(a, "zac@example.com")
    assert link.startswith("otpauth://totp/MIA%3Azac%40example.com?secret=" + a) and "issuer=MIA" in link
    assert ts.grouped("ABCDEFGHIJ") == "ABCD EFGH IJ"


def test_the_recovery_code_turns_two_step_off_so_a_lost_phone_never_locks_anyone_out(tmp_path, monkeypatch):
    """Forgot the password and lost the phone with the app: the recovery code sets a new password and two-step goes off."""
    from tests.engine_world import build_world

    w = build_world(tmp_path, monkeypatch)
    profile = w.profiles.create_profile("Robin", password="first-pass-1")
    code = w.profiles.issue_recovery_code(profile.profile_id)
    w.profiles.set_two_step(profile.profile_id, ts.new_secret())
    assert w.profiles.two_step_secret(profile.profile_id)
    assert w.profiles.reset_password_with_code(profile.profile_id, code, "second-pass-2")
    assert w.profiles.two_step_secret(profile.profile_id) == ""
