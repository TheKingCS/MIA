"""
tests.test_module_manager
===========================

Unit tests for core.module_manager.ModuleManager.

Rather than mocking the filesystem, these tests run discovery against
the real modules/ package, since the v0.1 stub modules are stable and
lightweight. This also acts as a regression test: if someone adds a
module with a mistake (e.g. two ModuleBase subclasses in one file, or
a duplicate module_id), these tests will catch it.

The enable/disable/rescan tests below use the same isolated-config
pattern as test_config_manager.py (monkeypatching ConfigManager's file
paths into tmp_path) so they never write to a developer's real
config/config.json.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import core.config_manager as config_manager_module
import modules
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.module_manager import ModuleManager
from modules.module_base import ModuleBase

EXPECTED_MODULE_IDS = {
    "assistant",
    "files",
    "knowledge",
    "maps",
    "music",
    "notes",
    "diagnostics",
    "settings",
    "module_browser",
}


def _build_manager() -> ModuleManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = ModuleManager(context)
    manager.discover()
    return manager


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point ConfigManager's paths at a scratch directory for this test."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    default_file = config_dir / "default_config.json"
    default_file.write_text(json.dumps({
        "system": {"setup_complete": True, "version": "0.1.0"},
        "modules": {"disabled": []},
    }))

    config_file = config_dir / "config.json"

    monkeypatch.setattr(config_manager_module, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(config_manager_module, "_DEFAULT_CONFIG_FILE", default_file)
    return config_dir, config_file, default_file


def test_discovers_all_expected_stub_modules():
    manager = _build_manager()
    discovered_ids = {m.module_id for m in manager.all()}
    assert EXPECTED_MODULE_IDS.issubset(discovered_ids)


def test_every_discovered_module_is_a_module_base_instance():
    manager = _build_manager()
    for module in manager.all():
        assert isinstance(module, ModuleBase)


def test_get_returns_none_for_unknown_id():
    manager = _build_manager()
    assert manager.get("does_not_exist") is None


def test_all_returns_modules_sorted_by_display_name():
    manager = _build_manager()
    names = [m.display_name for m in manager.all()]
    assert names == sorted(names)


def test_module_base_itself_is_not_discovered():
    manager = _build_manager()
    assert "base" not in {m.module_id for m in manager.all()}


# ----------------------------------------------------------------------
# Enable / disable
# ----------------------------------------------------------------------

def test_all_modules_enabled_by_default(isolated_config):
    manager = _build_manager()
    assert manager.is_enabled("notes") is True
    assert {m.module_id for m in manager.enabled_modules()} == {m.module_id for m in manager.all()}


def test_set_enabled_false_disables_and_persists(isolated_config):
    _, config_file, _ = isolated_config
    manager = _build_manager()

    assert manager.set_enabled("music", False) is True
    assert manager.is_enabled("music") is False

    saved = json.loads(config_file.read_text())
    assert saved["modules"]["disabled"] == ["music"]


def test_set_enabled_true_reenables(isolated_config):
    manager = _build_manager()
    manager.set_enabled("music", False)
    manager.set_enabled("music", True)
    assert manager.is_enabled("music") is True


def test_module_browser_cannot_be_disabled(isolated_config):
    manager = _build_manager()
    assert manager.set_enabled("module_browser", False) is False
    assert manager.is_enabled("module_browser") is True


def test_set_enabled_publishes_event(isolated_config):
    manager = _build_manager()
    received = []
    manager.context.events.subscribe(
        "modules.enabled_changed", lambda **kwargs: received.append(kwargs)
    )
    manager.set_enabled("music", False)
    assert received == [{"module_id": "music", "enabled": False}]


def test_enabled_modules_excludes_disabled(isolated_config):
    manager = _build_manager()
    manager.set_enabled("music", False)

    enabled_ids = {m.module_id for m in manager.enabled_modules()}
    all_ids = {m.module_id for m in manager.all()}
    assert "music" not in enabled_ids
    assert "music" in all_ids


# ----------------------------------------------------------------------
# Rescan
# ----------------------------------------------------------------------

def test_rescan_detects_newly_added_module_folder(isolated_config):
    manager = _build_manager()
    assert "tmp_rescan_module" not in {m.module_id for m in manager.all()}

    modules_dir = Path(modules.__file__).parent
    new_module_dir = modules_dir / "_test_rescan_tmp_module"
    new_module_dir.mkdir()
    try:
        (new_module_dir / "__init__.py").write_text("")
        (new_module_dir / "module.py").write_text(
            "from modules.module_base import ModuleBase\n"
            "class TmpRescanModule(ModuleBase):\n"
            "    module_id = 'tmp_rescan_module'\n"
            "    display_name = 'Tmp Rescan'\n"
            "    def get_widget(self):\n"
            "        return None\n"
        )

        found = manager.rescan()

        assert found == 1
        assert "tmp_rescan_module" in {m.module_id for m in manager.all()}
    finally:
        shutil.rmtree(new_module_dir)


def test_rescan_finds_nothing_when_no_new_folders(isolated_config):
    manager = _build_manager()
    assert manager.rescan() == 0


def test_rescan_does_not_flag_already_known_modules_as_duplicates(isolated_config, caplog):
    """
    Regression test: discover() used to be re-run wholesale on every
    rescan(), which re-imported every already-known module and logged a
    false "Duplicate module_id" warning for each one — every single
    time a user clicked "Rescan Modules", even when nothing had
    changed. See core/module_manager.py's discover() docstring.
    """
    manager = _build_manager()
    known_count = len(manager.all())

    with caplog.at_level("WARNING"):
        manager.rescan()

    assert len(manager.all()) == known_count
    assert "Duplicate module_id" not in caplog.text
