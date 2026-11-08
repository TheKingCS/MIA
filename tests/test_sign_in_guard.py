"""
tests.test_sign_in_guard
==========================

Sign-in protection (core/sign_in_guard.py, docs/SECURITY.md): the wait after
wrong passwords doubles and is capped, old failures are forgotten, a success
clears the account; sessions end when idle or old; and account passwords are
hashed at OWASP's count, older hashes upgraded on the next right password.
"""

from core import sign_in_guard as g


def test_the_wait_starts_after_the_free_tries_and_doubles_up_to_the_cap():
    """Nothing for five, then 30 s, 60 s, ... never more than 15 minutes."""
    assert [g.wait_for(n) for n in range(5)] == [0, 0, 0, 0, 0]
    assert g.wait_for(5) == 30 and g.wait_for(6) == 60 and g.wait_for(7) == 120
    assert g.wait_for(40) == g.MAX_WAIT


def test_a_guard_counts_by_account_and_device_and_forgets_old_failures():
    """Five failures then a wait; the device is held too; after the window it's free again; success clears it."""
    guard, keys = g.SignInGuard(), ["who:zac", "from:100.64.0.7"]
    for i in range(5):
        guard.failed(keys, now=1000 + i)
    assert guard.wait_left(keys, now=1004) == 30 and guard.wait_left(keys, now=1014) == 20
    assert guard.wait_left(["who:someone-else", "from:100.64.0.7"], now=1004) == 30  # the same device, another name
    assert guard.wait_left(keys, now=1004 + g.WINDOW_SECONDS + 1) == 0
    guard.succeeded(["who:zac"])
    assert guard.wait_left(["who:zac"], now=1006) == 0


def test_sessions_end_when_idle_or_old_and_the_desktop_s_never_do():
    """Idle past IDLE_SECONDS or older than MAX_AGE_SECONDS; no start time (the desktop's) never ends this way."""
    assert not g.session_expired(0, 100, 200)
    assert g.session_expired(0, 0, g.IDLE_SECONDS + 1)
    assert g.session_expired(0, g.MAX_AGE_SECONDS, g.MAX_AGE_SECONDS + 10)
    assert not g.session_expired(None, None, 10 ** 9)


def test_new_passwords_use_today_s_count_and_old_ones_are_upgraded_on_sign_in(tmp_path, monkeypatch):
    """A hash without a count was made at 200,000 rounds: it still works, and the right password re-hashes it."""
    import hashlib

    from core import profile_manager as pm
    from tests.engine_world import build_world

    w = build_world(tmp_path, monkeypatch)
    profile = w.profiles.create_profile("Robin", password="first-pass-1")
    raw = w.config.get(f"profiles.{profile.profile_id}")
    assert raw["password_iterations"] == pm._PBKDF2_ITERATIONS == 600_000
    salt = "00" * 16
    old = dict(raw, password_salt=salt,
               password_hash=hashlib.pbkdf2_hmac("sha256", b"old-pass-1", bytes.fromhex(salt), 200_000).hex())
    old.pop("password_iterations")
    w.config.set(f"profiles.{profile.profile_id}", old)
    assert not w.profiles.verify_password(profile.profile_id, "wrong")
    assert w.profiles.verify_password(profile.profile_id, "old-pass-1")
    upgraded = w.config.get(f"profiles.{profile.profile_id}")
    assert upgraded["password_iterations"] == 600_000 and upgraded["password_hash"] != old["password_hash"]
    assert w.profiles.verify_password(profile.profile_id, "old-pass-1")
