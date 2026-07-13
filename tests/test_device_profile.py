"""
tests.test_device_profile
============================

Unit tests for core.device_profile. No isolated data dir needed — this
reads config only, no persisted-JSON manager involved.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.device_profile import CORE, HOME, get_device_profile, is_core_profile, is_home_profile
from core.event_bus import EventBus


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


def test_defaults_to_core_when_unset():
    context = _make_context()
    assert get_device_profile(context) == CORE
    assert is_core_profile(context) is True
    assert is_home_profile(context) is False


def test_reads_home_when_configured():
    context = _make_context()
    context.config.set("system.device_profile", HOME)
    assert get_device_profile(context) == HOME
    assert is_home_profile(context) is True
    assert is_core_profile(context) is False


def test_unrecognized_value_is_not_core_or_home():
    context = _make_context()
    context.config.set("system.device_profile", "bogus")
    assert is_core_profile(context) is False
    assert is_home_profile(context) is False
