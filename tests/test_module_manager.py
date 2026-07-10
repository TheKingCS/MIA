"""
tests.test_module_manager
===========================

Unit tests for core.module_manager.ModuleManager.

Rather than mocking the filesystem, these tests run discovery against
the real modules/ package, since the v0.1 stub modules are stable and
lightweight. This also acts as a regression test: if someone adds a
module with a mistake (e.g. two ModuleBase subclasses in one file, or
a duplicate module_id), these tests will catch it.
"""

from __future__ import annotations

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
