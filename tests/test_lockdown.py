"""Tests for the lockdown (WP-01, DEC-0254, core/lockdown.py): the phrase; what it ends, unlinks, locks and stops;
that "carry on" can't lift it and only his password can; and the button on the server."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from core import lockdown, stop


@pytest.fixture
def home(monkeypatch):
    """One person's MIA in memory: settings, a server with sessions, two vaults, a security log."""
    kept = {}
    monkeypatch.setattr("core.person_settings.get", lambda context, key, default=None: kept.get(key, default))
    monkeypatch.setattr("core.person_settings.put", lambda context, key, value: kept.__setitem__(key, value))
    monkeypatch.setattr("core.person_settings.person_id", lambda context: "p1")
    monkeypatch.setattr(stop, "_mark_on_disk", lambda value: None)
    unlinked = []
    monkeypatch.setattr("core.linked_devices.unlink_all", lambda config, pid: unlinked.append(pid) or 2)
    locked = []
    vault = lambda name: SimpleNamespace(lock=lambda: locked.append(name))  # noqa: E731
    logged = []
    state = SimpleNamespace(sessions={"a": "p1", "b": "p1", "c": "p2"}, last_seen={"a": 1}, session_started={"b": 1})
    context = SimpleNamespace(
        config=object(), phone_server=SimpleNamespace(_app=SimpleNamespace(state=state)),
        passwords=vault("passwords"), private_journal=vault("private_journal"), inbox_mail=None,
        security_log=SimpleNamespace(record=lambda *a: logged.append(a[0])),
        profiles=SimpleNamespace(verify_password=lambda pid, pw: pw == "right"))
    return SimpleNamespace(context=context, kept=kept, state=state, locked=locked, unlinked=unlinked, logged=logged)


def test_the_phrase_is_the_whole_message():
    """\"lockdown\" and its few ways of saying it; never a sentence that mentions it."""
    for said in ("lockdown", "Lock down!", "MIA, lock everything down", "lock it all down now", "lock everything"):
        assert lockdown.recognise(said), said
    for said in ("what is a lockdown", "lock the door", "lockdown the shed tomorrow", "lock everything in the shed"):
        assert not lockdown.recognise(said), said


def test_a_lockdown_ends_his_sessions_unlinks_his_phones_locks_the_vaults_and_stops_everything(home):
    """His two sessions end (another person's stays); phones unlinked; both vaults locked; a stop with no end; logged."""
    done = lockdown.engage(home.context, now=datetime(2026, 11, 20, 9, 0))
    assert done == {"sessions": 2, "phones": 2, "vaults": ["passwords", "private_journal"]}
    assert home.state.sessions == {"c": "p2"} and home.state.last_seen == {} and home.state.session_started == {}
    assert home.unlinked == ["p1"] and home.locked == ["passwords", "private_journal"]
    assert lockdown.active(home.context) == {"since": "2026-11-20T09:00:00"}
    assert stop.state(home.context, datetime(2026, 11, 21)) is not None  # held, no end
    assert home.logged == ["lockdown"]


def test_carry_on_doesnt_lift_it_and_only_his_password_does(home):
    """"Carry on" is refused; a wrong password lifts nothing; the right one lifts the lockdown and the stop."""
    lockdown.engage(home.context)
    assert "password" in stop.handle(home.context, "carry on") and not stop.carry_on(home.context)
    assert lockdown.active(home.context) is not None
    assert not lockdown.lift(home.context, "p1", "wrong") and lockdown.active(home.context) is not None
    assert lockdown.lift(home.context, "p1", "right")
    assert lockdown.active(home.context) is None and stop.state(home.context) is None
    assert home.logged[-1] == "lockdown_lifted"


def test_the_phrase_in_a_turn_locks_down_and_says_what_it_did(home):
    """Taken before the model: what she says names what ended and how to lift it."""
    said = lockdown.handle(home.context, "lockdown")
    assert said.startswith("Lockdown is on: 2 sign-ins ended, 2 phones unlinked, the vaults locked.")
    assert "Sign in with your password" in said and lockdown.handle(home.context, "hello") is None
