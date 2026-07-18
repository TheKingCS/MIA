"""
tests.test_device_profile
============================

Unit tests for core.device_profile. Isolates ConfigManager's
_CONFIG_FILE (same pattern as test_assistant_action_handlers.py's own
fixture) — without this, `ConfigManager()` here loads the real
config/config.json, and `test_defaults_to_core_when_unset` silently
starts asserting against whatever this dev machine's actual
system.device_profile happens to be set to, rather than a genuinely
unset value. Found exactly this way: the real config.json had
"device_profile": "home" set (this project's own MIA Home work),
which made the "defaults to core" test fail — not a real regression,
a pre-existing isolation gap this just happened to newly expose.
"""

from __future__ import annotations

import pytest

import core.config_manager as config_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.device_profile import CORE, HOME, get_device_profile, is_core_profile, is_home_profile
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


def test_defaults_to_core_when_unset(isolated_paths):
    context = _make_context()
    assert get_device_profile(context) == CORE
    assert is_core_profile(context) is True
    assert is_home_profile(context) is False


def test_reads_home_when_configured(isolated_paths):
    context = _make_context()
    context.config.set("system.device_profile", HOME)
    assert get_device_profile(context) == HOME
    assert is_home_profile(context) is True
    assert is_core_profile(context) is False


def test_unrecognized_value_is_not_core_or_home(isolated_paths):
    context = _make_context()
    context.config.set("system.device_profile", "bogus")
    assert is_core_profile(context) is False
    assert is_home_profile(context) is False
