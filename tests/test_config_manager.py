"""
tests.test_config_manager
===========================

Unit tests for core.config_manager.ConfigManager.

These tests redirect ConfigManager's file paths into a pytest tmp_path
directory (via monkeypatch) rather than touching the real config/
folder, so running the test suite never risks clobbering a developer's
actual configuration.
"""

from __future__ import annotations

import json

import pytest

import core.config_manager as config_manager_module
from core.config_manager import ConfigManager


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point ConfigManager's paths at a scratch directory for this test."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    default_file = config_dir / "default_config.json"
    default_file.write_text(json.dumps({
        "system": {"setup_complete": False, "version": "0.1.0"},
        "user": {"name": ""},
    }))

    config_file = config_dir / "config.json"

    monkeypatch.setattr(config_manager_module, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(config_manager_module, "_DEFAULT_CONFIG_FILE", default_file)
    return config_dir, config_file, default_file


def test_loads_defaults_when_no_user_config_exists(isolated_config):
    manager = ConfigManager()
    assert manager.get("system.version") == "0.1.0"
    assert manager.is_first_run is True


def test_set_and_save_persists_to_disk(isolated_config):
    _, config_file, _ = isolated_config
    manager = ConfigManager()
    manager.set("user.name", "Alex")
    manager.save()

    assert config_file.exists()
    saved = json.loads(config_file.read_text())
    assert saved["user"]["name"] == "Alex"


def test_mark_setup_complete(isolated_config):
    manager = ConfigManager()
    assert manager.is_first_run is True
    manager.mark_setup_complete()
    assert manager.is_first_run is False


def test_reload_merges_new_default_keys_without_losing_user_values(isolated_config):
    _, config_file, default_file = isolated_config

    manager = ConfigManager()
    manager.set("user.name", "Alex")
    manager.save()

    # Simulate an upgrade that adds a brand-new default key.
    defaults = json.loads(default_file.read_text())
    defaults["gui"] = {"theme": "dark_field"}
    default_file.write_text(json.dumps(defaults))

    reloaded = ConfigManager()
    assert reloaded.get("user.name") == "Alex"  # preserved
    assert reloaded.get("gui.theme") == "dark_field"  # new default merged in


def test_get_with_missing_path_returns_default(isolated_config):
    manager = ConfigManager()
    assert manager.get("nonexistent.path", "fallback") == "fallback"
