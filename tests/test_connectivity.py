"""
tests.test_connectivity
=========================

core.connectivity: the online/offline monitor (with an injected fake
connect function and clock, so no real network and no real waiting),
the system-prompt text, and the get_connectivity_status action.
"""

from __future__ import annotations

import threading

import pytest

from core.app_context import AppContext
from core.assistant_chat import build_system_message
from core.connectivity import (
    CHECK_INTERVAL_SECONDS,
    OFFLINE,
    ONLINE,
    ONLINE_ONLY_CAPABILITIES,
    STALE_AFTER_SECONDS,
    UNKNOWN,
    ConnectivityMonitor,
    connectivity_action,
    connectivity_prompt_block,
    describe_capabilities,
    parse_probe_host,
)
from core.event_bus import EventBus


class _Config:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _context(values=None) -> AppContext:
    return AppContext(config=_Config(values), events=EventBus())


def _connect_ok(address, timeout):
    return None


def _connect_fail(address, timeout):
    raise OSError("unreachable")


def _monitor(connect, values=None, clock=None):
    ctx = _context(values)
    monitor = ConnectivityMonitor(ctx, connect=connect, clock=clock or _Clock())
    ctx.connectivity = monitor
    return monitor


# ------------------------------------------------------------------ pure


def test_parse_probe_host():
    assert parse_probe_host("1.1.1.1:443") == ("1.1.1.1", 443)
    assert parse_probe_host("example.com:80") == ("example.com", 80)
    assert parse_probe_host("nope") is None
    assert parse_probe_host("host:notaport") is None
    assert parse_probe_host(":443") is None


def test_prompt_block_offline_lists_every_online_only_feature_and_what_to_do():
    block = connectivity_prompt_block(OFFLINE)
    assert "OFFLINE" in block
    for capability in ONLINE_ONLY_CAPABILITIES:
        assert capability.name in block
    assert "offer" in block and "remind" in block


def test_prompt_block_online_is_one_short_line():
    block = connectivity_prompt_block(ONLINE)
    assert block.startswith("Internet: connected")
    assert "\n" not in block


def test_prompt_block_unknown_says_nothing():
    assert connectivity_prompt_block(UNKNOWN) == ""


@pytest.mark.parametrize("status, opening", [
    (ONLINE, "I'm online"), (OFFLINE, "I'm offline"), (UNKNOWN, "I can't tell"),
])
def test_describe_capabilities_opening_and_lists(status, opening):
    text = describe_capabilities(status)
    assert text.startswith(opening)
    assert "Only these need the internet" in text
    for capability in ONLINE_ONLY_CAPABILITIES:
        assert capability.what in text


# ------------------------------------------------------------------ monitor


def test_check_now_online_when_any_probe_connects():
    attempts = []

    def connect(address, timeout):
        attempts.append(address)
        if address[0] == "1.1.1.1":
            raise OSError("blocked")

    monitor = _monitor(connect)
    assert monitor.check_now() == ONLINE
    assert attempts == [("1.1.1.1", 443), ("8.8.8.8", 53)]


def test_check_now_offline_when_every_probe_fails():
    assert _monitor(_connect_fail).check_now() == OFFLINE


def test_check_now_closes_the_probe_connection():
    closed = []

    class Conn:
        def close(self):
            closed.append(True)

    _monitor(lambda address, timeout: Conn()).check_now()
    assert closed == [True]


def test_custom_probe_hosts_from_config():
    attempts = []
    monitor = _monitor(lambda a, timeout: attempts.append(a), {"network.probe_hosts": ["10.0.0.1:80"]})
    monitor.check_now()
    assert attempts == [("10.0.0.1", 80)]


def test_disabled_monitor_never_probes_and_reports_unknown():
    def must_not_connect(address, timeout):
        raise AssertionError("probed while disabled")

    monitor = _monitor(must_not_connect, {"network.connectivity_check": False})
    assert monitor.check_now() == UNKNOWN
    assert monitor.status == UNKNOWN
    monitor.refresh_async()


def test_status_is_unknown_before_first_check_and_starts_one(monkeypatch):
    monitor = _monitor(_connect_ok)
    started = []
    monkeypatch.setattr(monitor, "refresh_async", lambda: started.append(True))
    assert monitor.status == UNKNOWN
    assert started == [True]


def test_status_returns_cached_result_without_rechecking_until_due(monkeypatch):
    clock = _Clock()
    monitor = _monitor(_connect_fail, clock=clock)
    monitor.check_now()
    started = []
    monkeypatch.setattr(monitor, "refresh_async", lambda: started.append(True))

    clock.now += CHECK_INTERVAL_SECONDS - 1
    assert monitor.status == OFFLINE
    assert started == []

    clock.now += 1
    assert monitor.status == OFFLINE  # still the last result while a re-check runs
    assert started == [True]


def test_status_goes_unknown_when_result_is_stale(monkeypatch):
    clock = _Clock()
    monitor = _monitor(_connect_ok, clock=clock)
    monitor.check_now()
    monkeypatch.setattr(monitor, "refresh_async", lambda: None)
    clock.now += STALE_AFTER_SECONDS
    assert monitor.status == UNKNOWN


def test_refresh_async_runs_one_check_at_a_time():
    release = threading.Event()
    calls = []

    def slow_connect(address, timeout):
        calls.append(address)
        release.wait(5)

    monitor = _monitor(slow_connect, {"network.probe_hosts": ["h:1"]})
    monitor.refresh_async()
    monitor.refresh_async()  # ignored: a check is already in flight
    release.set()
    for _ in range(100):
        if not monitor._check_in_flight:
            break
        threading.Event().wait(0.01)
    assert calls == [("h", 1)]
    assert monitor.status == ONLINE


# ------------------------------------------------------------------ prompt + action


def _message(status):
    ctx = _context()
    ctx.connectivity = type("Fixed", (), {"status": status})()
    return build_system_message(ctx, is_action_request=False)


def test_system_message_includes_offline_block():
    assert "Internet: OFFLINE" in _message(OFFLINE)


def test_system_message_includes_online_line():
    assert "Internet: connected" in _message(ONLINE)


def test_system_message_omits_block_when_unknown_or_no_monitor():
    assert "Internet:" not in _message(UNKNOWN)
    assert "Internet:" not in build_system_message(_context(), is_action_request=False)


def test_action_path_stays_lean():
    ctx = _context()
    ctx.connectivity = type("Fixed", (), {"status": OFFLINE})()
    assert "Internet" not in build_system_message(ctx, is_action_request=True)


def test_action_reports_cached_status():
    monitor = _monitor(_connect_fail)
    monitor.check_now()
    text = connectivity_action().handler(monitor.context, {})
    assert text.startswith("I'm offline")


def test_action_checks_right_away_when_status_unknown(monkeypatch):
    monitor = _monitor(_connect_ok)
    monkeypatch.setattr(monitor, "refresh_async", lambda: None)
    assert connectivity_action().handler(monitor.context, {}).startswith("I'm online")


def test_action_without_monitor_still_answers():
    assert connectivity_action().handler(_context(), {}).startswith("I can't tell")


@pytest.mark.parametrize("prompt", ["are you online right now", "what can you do without internet", "is my internet connection up"])
def test_action_triggers_on_connectivity_questions(prompt):
    triggers = connectivity_action().trigger_phrases
    assert any(t in prompt for t in triggers)


@pytest.mark.parametrize("prompt", ["how do offline maps work", "open the online store"])
def test_action_does_not_trigger_on_unrelated_offline_words(prompt):
    triggers = connectivity_action().trigger_phrases
    assert not any(t in prompt for t in triggers)
