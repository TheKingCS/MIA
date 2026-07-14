"""
tests.test_field_kit_module
==============================

Unit test for modules.field_kit.module.format_script_row — pure
formatting logic, no Qt event loop needed. Same shape as
tests/test_notes_module.py's format_entry_row test: the widget-building
(QTabWidget, device list, script list) and worker-thread wiring in
FieldKitModule needs a real Qt event loop to exercise meaningfully, so
that was verified with a manual headless smoke test instead (offscreen
QPA platform) rather than unit-tested here.

`_check_for_docked_core()` (docs/ROADMAP.md milestone v0.19) is the one
exception — it's plain business logic against `self.context` with no
Qt widget involved (FieldKitModule.__init__ never builds one), so it's
tested directly here rather than only via manual smoke test.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

import core.expedition_manager as expedition_manager_module
import core.expedition_sync as expedition_sync_module
import core.inventory_manager as inventory_manager_module
import core.journal_manager as journal_manager_module
import core.notification_manager as notification_manager_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.device_framework import BlockDevice
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.expedition_sync import export_expedition_data
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.notification_manager import NotificationManager
from core.script_library_manager import Script
from core.trip_manager import TripManager
from core.waypoint_manager import WaypointManager
from modules.field_kit.module import FieldKitModule, format_script_row


def test_formats_script_with_category():
    script = Script(script_id="1", name="Ping Sweep", interpreter="shell", category="Network")
    assert format_script_row(script) == "[Network]  Ping Sweep  (shell)"


def test_formats_script_without_category():
    script = Script(script_id="1", name="Ping Sweep", interpreter="python", category="")
    assert format_script_row(script) == "Ping Sweep  (python)"


# ----------------------------------------------------------------------
# _check_for_docked_core — docs/ROADMAP.md milestone v0.19, Home Dock
# auto-launch Dashboard
# ----------------------------------------------------------------------

@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", data_dir / "expeditions.json")
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", data_dir / "trips.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", data_dir / "journal_entries.json")
    monkeypatch.setattr(inventory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(inventory_manager_module, "_ITEMS_FILE", data_dir / "inventory_items.json")
    monkeypatch.setattr(notification_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(notification_manager_module, "_NOTIFICATIONS_FILE", data_dir / "notifications.json")
    monkeypatch.setattr(expedition_sync_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_sync_module, "_TRIP_PHOTOS_DIR", tmp_path / "trip_photos")


def _make_context(tmp_path, device_profile: str = "home") -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.config.set("system.device_profile", device_profile)
    context.config.set("trips.photo_root_path", str(tmp_path / "trip_photos"))
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.waypoints = WaypointManager(context)
    context.journal = JournalManager(context)
    context.inventory = InventoryManager(context)
    context.notifications = NotificationManager(context)
    return context


def _make_bundle(tmp_path) -> Path:
    """A real export bundle from a separate, isolated 'Pi' data dir."""
    pi_data_dir = tmp_path / "pi_data"
    original_data_dir = expedition_sync_module._DATA_DIR
    expedition_sync_module._DATA_DIR = pi_data_dir
    try:
        pi_context = AppContext(config=ConfigManager(), events=EventBus())
        pi_context.config.set("trips.photo_root_path", str(tmp_path / "pi_trip_photos"))
        pi_expeditions = ExpeditionManager.__new__(ExpeditionManager)
        pi_expeditions.context = pi_context
        pi_expeditions._expeditions = []
        import core.expedition_manager as em
        original_exp_dir, original_exp_file = em._DATA_DIR, em._EXPEDITIONS_FILE
        em._DATA_DIR = pi_data_dir
        em._EXPEDITIONS_FILE = pi_data_dir / "expeditions.json"
        try:
            pi_expeditions._load()
            pi_expeditions.add_expedition(name="Field Season", start_date="2026-08-14")
        finally:
            em._DATA_DIR, em._EXPEDITIONS_FILE = original_exp_dir, original_exp_file

        mount_dir = tmp_path / "docked_mount"
        mount_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = mount_dir / f"mia_expedition_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        export_expedition_data(bundle_path)
        return bundle_path
    finally:
        expedition_sync_module._DATA_DIR = original_data_dir


def _make_device(mountpoint: Path, name: str = "sdb") -> BlockDevice:
    return BlockDevice(name=name, size="32G", mountpoint=str(mountpoint), fstype="ext4", model="Test Drive", tran="usb", removable=True)


def test_check_for_docked_core_imports_and_reloads_on_home_profile(isolated_paths, tmp_path):
    context = _make_context(tmp_path, device_profile="home")
    bundle_path = _make_bundle(tmp_path)
    device = _make_device(bundle_path.parent)

    navigated_to = []
    context.events.subscribe("assistant.open_module_requested", lambda module_id: navigated_to.append(module_id))

    field_kit = FieldKitModule(context)
    field_kit._check_for_docked_core(device)

    assert len(context.expeditions.all_expeditions()) == 1
    assert context.expeditions.all_expeditions()[0].name == "Field Season"
    assert navigated_to == ["dashboard"]
    assert len(context.notifications.list_all()) == 1


def test_check_for_docked_core_ignores_on_core_profile(isolated_paths, tmp_path):
    context = _make_context(tmp_path, device_profile="core")
    bundle_path = _make_bundle(tmp_path)
    device = _make_device(bundle_path.parent)

    field_kit = FieldKitModule(context)
    field_kit._check_for_docked_core(device)

    assert context.expeditions.all_expeditions() == []


def test_check_for_docked_core_no_bundles_does_nothing(isolated_paths, tmp_path):
    context = _make_context(tmp_path, device_profile="home")
    empty_mount = tmp_path / "empty_mount"
    empty_mount.mkdir()
    device = _make_device(empty_mount)

    field_kit = FieldKitModule(context)
    field_kit._check_for_docked_core(device)

    assert context.expeditions.all_expeditions() == []
    assert context.notifications.list_all() == []


def test_check_for_docked_core_does_not_retrigger_for_the_same_device(isolated_paths, tmp_path):
    context = _make_context(tmp_path, device_profile="home")
    bundle_path = _make_bundle(tmp_path)
    device = _make_device(bundle_path.parent)

    navigated_to = []
    context.events.subscribe("assistant.open_module_requested", lambda module_id: navigated_to.append(module_id))

    field_kit = FieldKitModule(context)
    field_kit._check_for_docked_core(device)
    field_kit._check_for_docked_core(device)  # same still-docked device, second poll tick

    assert navigated_to == ["dashboard"]  # only once
    assert len(context.notifications.list_all()) == 1


def test_check_for_docked_core_no_mountpoint_does_nothing(isolated_paths, tmp_path):
    context = _make_context(tmp_path, device_profile="home")
    device = BlockDevice(name="sdb", size="32G", mountpoint=None, fstype=None, model="Test Drive", tran="usb", removable=True)

    field_kit = FieldKitModule(context)
    field_kit._check_for_docked_core(device)  # must not raise

    assert context.expeditions.all_expeditions() == []
