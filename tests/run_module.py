#!/usr/bin/env python3
"""
tests/run_module.py
=====================

Standalone test harness: boots just enough of MIA to display a
single module's widget, without the splash screen, setup wizard, or
main menu. This is the fast feedback loop for module development —
see docs/ADDING_MODULES.md.

Usage:
    python tests/run_module.py <module_id>
    python tests/run_module.py --list          (show all discovered module ids)

Example:
    python tests/run_module.py notes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this script directly (python tests/run_module.py) by
# ensuring the project root is on sys.path, since it's not a package
# entry point like main.py.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: E402

from core.alarm_manager import AlarmManager  # noqa: E402
from core.app_context import AppContext  # noqa: E402
from core.activity_log_manager import ActivityLogManager  # noqa: E402
from core.budget_manager import BudgetManager  # noqa: E402
from core.plaid_manager import PlaidManager  # noqa: E402
from core.real_estate_manager import RealEstateManager  # noqa: E402
from core.calendar_manager import CalendarManager  # noqa: E402
from core.component_manager import ComponentManager  # noqa: E402
from core.config_manager import ConfigManager  # noqa: E402
from core.conversation_manager import ConversationManager  # noqa: E402
from core.data_logger_manager import DataLoggerManager  # noqa: E402
from core.device_framework import DeviceFramework  # noqa: E402
from core.device_help_manager import DeviceHelpManager  # noqa: E402
from core.energy_manager import EnergyManager  # noqa: E402
from core.event_bus import EventBus  # noqa: E402
from core.expedition_manager import ExpeditionManager  # noqa: E402
from core.inventory_manager import InventoryManager  # noqa: E402
from core.journal_manager import JournalManager  # noqa: E402
from core.llm_manager import LLMManager  # noqa: E402
from core.maintenance_manager import MaintenanceManager  # noqa: E402
from core.map_tile_cache import MapTileCache  # noqa: E402
from core.mission_manager import MissionManager  # noqa: E402
from core.module_manager import ModuleManager  # noqa: E402
from core.music_manager import MusicManager  # noqa: E402
from core.power_manager import PowerManager  # noqa: E402
from core.profile_manager import ProfileManager  # noqa: E402
from core.reference_library_manager import ReferenceLibraryManager  # noqa: E402
from core.script_library_manager import ScriptLibraryManager  # noqa: E402
from core.search_manager import SearchManager  # noqa: E402
from core.trail_map_library import TrailMapLibrary  # noqa: E402
from core.trip_manager import TripManager  # noqa: E402
from core.user_memory_manager import UserMemoryManager  # noqa: E402
from core.voice_manager import VoiceManager  # noqa: E402
from core.waypoint_manager import WaypointManager  # noqa: E402
from gui.theme_manager import get_theme_stylesheet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single MIA module in isolation.")
    parser.add_argument("module_id", nargs="?", help="The module_id to load, e.g. 'notes'")
    parser.add_argument("--list", action="store_true", help="List all discovered module ids and exit.")
    args = parser.parse_args()

    # Wires the same data-manager services core/application.py constructs
    # at real boot (minus notifications, which no module reads from
    # get_widget()/on_load() today and which carries a real side effect —
    # NotificationManager's QTimer — this harness has no business
    # triggering). Add a manager here if a new module's
    # get_widget()/on_load() starts needing one and this script starts
    # crashing the same way it used to for Notes' context.search before
    # this fix. ProfileManager moved from "deliberately omitted" to wired
    # for real once modules/missions/module.py's 2026-07-18 redesign
    # started reading context.profiles for its Level/XP footer.
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.missions = MissionManager(context)
    context.calendar = CalendarManager(context)
    context.alarms = AlarmManager(context)
    context.journal = JournalManager(context)
    context.maintenance = MaintenanceManager(context)
    context.energy = EnergyManager(context)
    context.budget = BudgetManager(context)
    context.real_estate = RealEstateManager(context)
    context.plaid = PlaidManager(context)
    context.inventory = InventoryManager(context)
    context.data_logger = DataLoggerManager(context)
    context.components = ComponentManager(context)
    context.reference_library = ReferenceLibraryManager(context)
    context.llm = LLMManager(context)
    context.voice = VoiceManager(context)
    context.waypoints = WaypointManager(context)
    context.power = PowerManager(context)
    context.devices = DeviceFramework(context)
    context.scripts = ScriptLibraryManager(context)
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.search = SearchManager(context)
    context.device_help = DeviceHelpManager(context)
    context.activity_log = ActivityLogManager(context)
    context.conversations = ConversationManager(context)
    context.user_memories = UserMemoryManager(context)
    context.map_tiles = MapTileCache(context)
    context.trail_maps = TrailMapLibrary(context)
    context.music = MusicManager(context)
    manager = ModuleManager(context)
    manager.discover()
    context.device_help.register_module_lister(manager.all)
    context.activity_log.register_module_lister(manager.all)
    context.device_help.register_reference_library(context.reference_library)

    if args.list or not args.module_id:
        print("Discovered modules:")
        for module in manager.all():
            print(f"  {module.module_id:20s} {module.display_name}")
        if not args.module_id:
            return 0
        return 0

    module = manager.get(args.module_id)
    if module is None:
        print(f"No module with id '{args.module_id}' was discovered.")
        print("Run with --list to see available module ids.")
        return 1

    app = QApplication(sys.argv)
    app.setStyleSheet(get_theme_stylesheet(context.config.get("gui.theme", "dark_field")))
    module.on_load()

    window = QMainWindow()
    window.setWindowTitle(f"MIA Module Test — {module.display_name}")
    window.resize(700, 500)
    window.setCentralWidget(module.get_widget())
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
