"""
core.application
=================

MIAApplication: the orchestrator that boots the system.

This class is the one place that knows the *order* things happen in:
create Qt app -> show splash -> init core services -> discover modules
-> decide first-run vs normal boot -> show the right window. Keeping
this sequencing in one class (rather than spread across main.py) means
main.py can stay a two-line entry point forever, which matters because
main.py is the first file every new contributor reads.

main.py should never import PySide6 widgets directly or contain any
startup logic — it only constructs and runs MIAApplication.
"""

from __future__ import annotations

import sys
import tempfile
import urllib.error
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from core.activity_log_manager import ActivityLogManager
from core.alarm_manager import AlarmManager
from core.avatar_manager import AvatarManager
from core.budget_manager import (
    EXPENSE_CATEGORIES as BUDGET_EXPENSE_CATEGORIES,
    INCOME_CATEGORIES as BUDGET_INCOME_CATEGORIES,
    Bill,
    BudgetManager,
    IncomeSource,
    days_until_bill_due,
)
from core.finance_manager import FinanceManager
from core.homestead_manager import HomesteadManager
from core.workshop_machine import LaserEngraverMachine, WorkshopMachineRegistry
from core.app_context import AppContext
from core.assistant_actions import AssistantAction
from core.calendar_manager import RECURRENCE_TYPES as CALENDAR_RECURRENCE_TYPES, CalendarManager
from core.component_manager import ComponentManager
from core.boot_sound import write_boot_sound_wav
from core.boot_sound_worker import BootSoundWorker
from core.job_manager import JobManager
from core.material_manager import MaterialManager
from core.ledger_manager import LedgerManager
from core.product_manager import ProductManager
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.budget_nudges import build_nudge_message
from core.daily_occasions import calendar_events_today, is_birthday_today, should_run_once_daily, should_send_checkin
from core.smart_suggestions import build_smart_suggestions_message
from core.dashboard_widgets import DashboardWidgetRegistry, WidgetDescriptor
from core.data_logger_manager import DataLoggerManager
from core.device_framework import DeviceFramework
from core.device_help_manager import DeviceHelpManager
from core.device_profile import CORE, get_device_profile
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.hash_identifier import identify_hash
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.maintenance_manager import (
    ASSET_CATEGORIES as MAINTENANCE_ASSET_CATEGORIES,
    MaintenanceManager,
    MaintenanceTask,
    days_until_due as maintenance_days_until_due,
    is_sensor_task_due,
    meter_used_since_last,
)
from core.llm_manager import LLMManager
from core.logger import get_logger
from core.map_tile_cache import MapTileCache
from core.memory_manager import MemoryManager
from core.mission_manager import METRIC_TYPES as MISSION_METRIC_TYPES, MissionManager
from core.module_manager import ModuleManager
from core.notification_manager import NotificationManager
from core.password_strength import assess_password
from core.port_scanner import scan_ports
from core.energy_manager import EnergyManager
from core.power_manager import PowerManager
from core.profile_manager import ProfileManager
from core.project_manager import PROJECT_STATUSES, ProjectManager
from core.plaid_manager import PlaidManager
from core.real_estate_manager import Property, RealEstateManager, equity as property_equity
from core.reference_library_manager import ReferenceLibraryManager
from core.script_library_manager import ScriptLibraryManager
from core.subnet_calculator import calculate_subnet
from core.search_manager import SearchManager, SearchResult
from core.system_health import format_system_health, read_system_health
from core.task_manager import TaskManager
from core.trail_map_library import NotAPdfError, TrailMapLibrary
from core.music_manager import MusicManager
from core.kitchen_manager import KitchenManager
from core.workout_manager import WorkoutManager
from core.relationships_manager import RelationshipsManager
from core.trip_manager import ACTIVITY_TYPES, TripManager
from core.user_memory_manager import UserMemoryManager
from core.voice_manager import VoiceManager
from core.volume_manager import VolumeManager
from core.waypoint_manager import WAYPOINT_CATEGORIES, WaypointManager
from gui.lock_screen import LockScreen
from gui.main_window import MainWindow
from gui.profile_select import ProfileSelectScreen
from gui.setup_wizard import SetupWizard
from gui.splash_screen import SplashScreen
from gui.theme_manager import THEME_DISPLAY_NAMES, THEMES, get_theme_stylesheet

log = get_logger(__name__)

# Assistant tool calls run synchronously on the GUI thread (see
# modules/assistant/module.py's docstring) — unlike the Field Kit
# Security tab's port scanner, which offloads to a QThread
# (modules/field_kit/port_scan_worker.py) precisely because a full
# COMMON_PORTS sweep can take several seconds. _action_scan_ports below
# deliberately checks only these 3 fast, common ports with a short
# timeout to keep worst-case blocking time small (~0.9s) rather than
# freezing the UI for a full sweep; point the user at the Security tab
# for anything more thorough.
_ASSISTANT_SCAN_PORTS = (22, 80, 443)
_ASSISTANT_SCAN_TIMEOUT_SECONDS = 0.3


_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_BUNDLED_FONT_FILES = (
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    "Inter-ExtraBold.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "JetBrainsMono-Bold.ttf",
)


def _load_bundled_fonts() -> None:
    """Registers the "ForMIA" design handoff's Inter/JetBrains Mono font
    files (assets/fonts/, see assets/fonts/NOTICE.md for license/source)
    with Qt's font database, so gui/styles.py's DARK_FIELD_THEME QSS can
    reference them by name. Must run after QApplication exists (Qt
    requirement for QFontDatabase) but before any stylesheet/widget is
    applied/shown. Neither font is a default system font on a fresh
    Windows/Linux/Pi install — bundling avoids silently falling back to
    a generic system font and looking wrong without any visible error.
    A font file failing to load (missing/corrupt) is logged and skipped
    rather than crashing boot; Qt's own font-fallback chain (the QSS's
    own listed fallback fonts) still covers that case gracefully."""
    for filename in _BUNDLED_FONT_FILES:
        font_id = QFontDatabase.addApplicationFont(str(_FONTS_DIR / filename))
        if font_id == -1:
            log.warning("Could not load bundled font: %s", filename)


class MIAApplication:
    """Owns the Qt application object and the startup sequence."""

    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("MIA")
        _load_bundled_fonts()

        self.config = ConfigManager()
        self.events = EventBus()
        self.context = AppContext(config=self.config, events=self.events)

        # Applied once, at the QApplication level — Qt's stylesheet
        # cascade means every widget/dialog inherits this automatically,
        # which is why individual dialogs no longer call their own
        # setStyleSheet() (gui/theme_manager.py, docs/ROADMAP.md
        # milestone 13.2). "theme.changed" (published by
        # modules/settings/module.py's Theme dropdown) re-applies this
        # live, no restart required.
        self.qt_app.setStyleSheet(get_theme_stylesheet(self.config.get("gui.theme", "dark_field")))
        self.events.subscribe("theme.changed", self._on_theme_changed)
        # ProfileManager needs the context to already exist (it reads/
        # writes config through it), so it's attached right after
        # construction rather than passed into AppContext's constructor.
        # Its __init__ also runs the legacy-user migration — see
        # core/profile_manager.py.
        self.context.profiles = ProfileManager(self.context)
        self.context.notifications = NotificationManager(self.context)
        self.context.calendar = CalendarManager(self.context)
        self.context.alarms = AlarmManager(self.context)
        self.context.journal = JournalManager(self.context)
        self.context.inventory = InventoryManager(self.context)
        self.context.data_logger = DataLoggerManager(self.context)
        self.context.components = ComponentManager(self.context)
        self.context.materials = MaterialManager(self.context)
        self.context.products = ProductManager(self.context)
        # Jobs references both materials and products
        # (consume_material()/produce_product()/total_cost() reach into
        # self.context.materials/self.context.products), so it's
        # constructed after both already are — same ordering precedent
        # as Trips/Waypoints/Inventory in core/application.py.
        self.context.jobs = JobManager(self.context)
        # Ledger references products (record_sale() reaches into
        # self.context.products), so it's constructed after products
        # already is, same ordering precedent as above.
        self.context.ledger = LedgerManager(self.context)
        self.context.reference_library = ReferenceLibraryManager(self.context)
        self.context.llm = LLMManager(self.context)
        self.context.voice = VoiceManager(self.context)
        self.context.waypoints = WaypointManager(self.context)
        self.context.power = PowerManager(self.context)
        self.context.volume = VolumeManager(self.context)
        self.context.devices = DeviceFramework(self.context)
        self.context.scripts = ScriptLibraryManager(self.context)
        # Trips references waypoints/inventory/journal, so it's
        # constructed after all three are already on the context.
        self.context.expeditions = ExpeditionManager(self.context)
        self.context.trips = TripManager(self.context)
        self.context.projects = ProjectManager(self.context)
        self.context.tasks = TaskManager(self.context)
        # Memories is read-only aggregation over Expeditions/Trips/
        # Waypoints/Journal, so it's constructed after all four are
        # already on the context, same reasoning as Trips above.
        self.context.memories = MemoryManager(self.context)
        # Missions references trips (for the trip_duration_hours metric
        # type), so it's constructed after trips already is.
        self.context.missions = MissionManager(self.context)
        self.context.conversations = ConversationManager(self.context)
        self.context.user_memories = UserMemoryManager(self.context)
        self.context.dashboard_widgets = DashboardWidgetRegistry(self.context)
        self.context.avatar = AvatarManager(self.context)
        self.context.finance = FinanceManager(self.context)
        self.context.homestead = HomesteadManager(self.context)
        self.context.maintenance = MaintenanceManager(self.context)
        self.context.budget = BudgetManager(self.context)
        self.context.real_estate = RealEstateManager(self.context)
        self.context.energy = EnergyManager(self.context)
        self.context.plaid = PlaidManager(self.context)
        self.context.map_tiles = MapTileCache(self.context)
        self.context.trail_maps = TrailMapLibrary(self.context)
        self.context.music = MusicManager(self.context)
        self.context.kitchen = KitchenManager(self.context)
        self.context.workout = WorkoutManager(self.context)
        self.context.relationships = RelationshipsManager(self.context)
        self.context.workshop_machines = WorkshopMachineRegistry(self.context)
        # Registered by default so the registry has something real to
        # demonstrate end-to-end — it's a stub (no real driver), not a
        # working device, see core/workshop_machine.py's docstring.
        self.context.workshop_machines.register(LaserEngraverMachine())
        self.module_manager = ModuleManager(self.context)
        self.context.module_manager = self.module_manager
        self.context.search = SearchManager(self.context)
        self.context.device_help = DeviceHelpManager(self.context)
        self.context.activity_log = ActivityLogManager(self.context)
        # module_manager.all is stored as a callable, not called now — it's
        # still empty until self.module_manager.discover() runs later in
        # the boot sequence (run()'s boot_steps), and device_help/
        # activity_log only invoke it lazily on their own first use anyway.
        self.context.device_help.register_module_lister(self.module_manager.all)
        self.context.activity_log.register_module_lister(self.module_manager.all)
        self.context.device_help.register_reference_library(self.context.reference_library)
        self._register_search_providers()
        self._register_calculators()
        self._register_assistant_actions()
        self._register_dashboard_widgets()

        self.splash: SplashScreen | None = None
        self._boot_sound_worker: BootSoundWorker | None = None
        self.main_window: MainWindow | None = None
        self.setup_wizard: SetupWizard | None = None
        self.profile_select: ProfileSelectScreen | None = None
        self.lock_screen: LockScreen | None = None

        # Alarms need to fire regardless of which module is currently on
        # screen, so this timer lives here (the one place that's always
        # alive for the whole app session) rather than inside the Alarm
        # tool's widget, which only exists while that screen is open.
        # 20s is frequent enough that no HH:MM minute window is ever
        # skipped between polls.
        self._alarm_check_timer = QTimer()
        self._alarm_check_timer.timeout.connect(self._check_alarms)
        self._alarm_check_timer.start(20_000)

        # Same reasoning as the alarm timer above — a low-battery
        # warning must fire regardless of which module is on screen,
        # not just while the Power module happens to be open. 30s is
        # frequent enough for a warning to matter without polling
        # psutil needlessly often (battery percentage changes slowly).
        self._power_check_timer = QTimer()
        self._power_check_timer.timeout.connect(self._check_power)
        self._power_check_timer.start(30_000)

        # Same "always alive for the whole app session" reasoning as
        # the timers above — birthdays/calendar/check-in must fire
        # regardless of which screen is open. 5 minutes is plenty
        # responsive for "once a day" events (see
        # core/daily_occasions.py's own docstring for why each of the
        # three checks below has its own independent "already ran
        # today" gate rather than sharing one).
        self._daily_occasion_timer = QTimer()
        self._daily_occasion_timer.timeout.connect(self._check_daily_occasions)
        self._daily_occasion_timer.start(300_000)

        # Same "always alive for the whole app session" reasoning as
        # the timers above — MIA Home's watched-folder financial
        # snapshot ingestion (core/finance_manager.py) must pick up a
        # dropped export regardless of which screen is open, not just
        # while a future finance widget/module happens to be visible.
        # 60s is frequent enough that "I just dropped a file" gets
        # noticed promptly without polling the filesystem needlessly
        # often for what's normally a rare event.
        self._finance_snapshot_timer = QTimer()
        self._finance_snapshot_timer.timeout.connect(self._check_finance_snapshots)
        self._finance_snapshot_timer.start(60_000)

        # Same "always alive for the whole app session" reasoning as
        # the finance snapshot timer directly above — MIA Homestead's
        # watched-folder state snapshot ingestion (core/homestead_manager.py)
        # must pick up a dropped export regardless of which screen is
        # open. Same 60s cadence, same reasoning: prompt enough without
        # polling the filesystem needlessly often for what's normally a
        # rare (manual) event — see mia-homestead's own
        # docs/MIA_HOME_SYNC_PLAN.md for why delivery here isn't
        # automated yet.
        self._homestead_snapshot_timer = QTimer()
        self._homestead_snapshot_timer.timeout.connect(self._check_homestead_snapshots)
        self._homestead_snapshot_timer.start(60_000)

        # Same "always alive for the whole app session" reasoning as the
        # timers above — "MIA should assign me missions sometimes"
        # (docs/VISION.md's gamification goal) needs to fire regardless
        # of whether the Missions screen is even open. 5 minutes matches
        # _daily_occasion_timer's cadence: check_for_auto_assignment()'s
        # own rules are day-granularity (core/mission_manager.py), so
        # this is just frequent enough to notice a newly-idle/newly-stale
        # state promptly without polling meaningfully more than needed.
        self._mission_check_timer = QTimer()
        self._mission_check_timer.timeout.connect(self._check_mission_auto_assignment)
        self._mission_check_timer.start(300_000)
        # Also run once immediately at boot — QTimer.start() only
        # schedules the *next* firing, so without this a long-idle user
        # would wait a full 5 minutes after opening MIA before getting a
        # mission that was already overdue.
        self._check_mission_auto_assignment()

    def _check_alarms(self) -> None:
        self.context.alarms.check_due(datetime.now())

    def _check_power(self) -> None:
        self.context.power.check_low_battery()

    def _check_mission_auto_assignment(self) -> None:
        self.context.missions.check_for_auto_assignment()

    def _check_finance_snapshots(self) -> None:
        newly_imported = self.context.finance.scan_for_new_snapshots()
        for snapshot in newly_imported:
            self.context.notifications.notify(
                "New financial snapshot imported",
                f"Imported an updated snapshot from '{snapshot.source}'.",
            )

    def _check_homestead_snapshots(self) -> None:
        newly_imported = self.context.homestead.scan_for_new_snapshots()
        for snapshot in newly_imported:
            self.context.notifications.notify(
                "New homestead snapshot imported",
                f"Imported an updated snapshot from '{snapshot.source}'.",
            )

    def _check_daily_occasions(self) -> None:
        """See core/daily_occasions.py's docstring for the full reasoning behind each check."""
        now = datetime.now()
        today_iso = now.date().isoformat()
        config = self.context.config

        if should_run_once_daily(config.get("system.last_birthday_celebrated_date"), today_iso):
            active_profile = self.context.profiles.get_active_profile() if self.context.profiles else None
            if active_profile is not None and is_birthday_today(active_profile.birthday, now.date()):
                self.context.notifications.notify(
                    title="\U0001F389 Happy Birthday!",
                    message=f"Happy birthday, {active_profile.name}! Wishing you an amazing day.",
                    level="info",
                    source="system",
                )
                config.set("system.last_birthday_celebrated_date", today_iso)
                config.save()

        if should_run_once_daily(config.get("system.last_calendar_digest_date"), today_iso):
            events_today = (
                calendar_events_today(self.context.calendar.all_events(), today_iso)
                if self.context.calendar is not None
                else []
            )
            if events_today:
                titles = ", ".join(event.title for event in events_today)
                self.context.notifications.notify(
                    title="Today's calendar",
                    message=f"You have {len(events_today)} event(s) today: {titles}",
                    level="info",
                    source="system",
                )
            config.set("system.last_calendar_digest_date", today_iso)
            config.save()

        if should_run_once_daily(config.get("system.last_checkin_date"), today_iso):
            has_activity_today = self.context.conversations is not None and any(
                conversation.updated_at[:10] == today_iso
                for conversation in self.context.conversations.all_conversations()
            )
            if should_send_checkin(now, has_activity_today):
                self.context.notifications.notify(
                    title="Just checking in",
                    message="Haven't heard from you today — how's everything going?",
                    level="info",
                    source="system",
                )
                config.set("system.last_checkin_date", today_iso)
                config.save()

        if should_run_once_daily(config.get("system.last_budget_nudge_date"), today_iso) and self.context.budget is not None:
            bills = self.context.budget.all_bills()
            income_sources = self.context.budget.all_income_sources()
            targets = self.context.budget.all_budget_targets()
            month_start = now.date().replace(day=1).isoformat()
            actual_by_category = self.context.budget.total_expenses_by_category(month_start, None)
            message = build_nudge_message(bills, income_sources, targets, actual_by_category, now.date())
            if message:
                self.context.notifications.notify(
                    title="Budget check-in",
                    message=message,
                    level="info",
                    source="system",
                )
            config.set("system.last_budget_nudge_date", today_iso)
            config.save()

        if should_run_once_daily(config.get("system.last_smart_suggestion_date"), today_iso):
            last_session_date = self.context.workout.last_session_date() if self.context.workout is not None else None
            pantry_items = self.context.kitchen.all_pantry_items() if self.context.kitchen is not None else []
            people = self.context.relationships.all_people() if self.context.relationships is not None else []
            message = build_smart_suggestions_message(last_session_date, pantry_items, people, now.date())
            if message:
                self.context.notifications.notify(
                    title="Smart Suggestion",
                    message=message,
                    level="info",
                    source="system",
                )
            config.set("system.last_smart_suggestion_date", today_iso)
            config.save()

    def _display(self, widget) -> None:
        """
        Show a top-level screen, going fullscreen if kiosk_mode is on.

        This is the single place kiosk-mode display behavior lives.
        Previously, only MainWindow applied fullscreen (in its own
        showEvent), which meant kiosk mode silently dropped the moment
        you left MainWindow — the lock screen, profile selector, and
        setup wizard all just called plain .show(). Routing every
        screen transition through this one method is what makes
        fullscreen actually persist across the whole boot/switch flow,
        not just within MainWindow.

        **2026-07-17: resize to the screen's own geometry before
        requesting fullscreen.** Every top-level screen constructs
        itself at a small fixed windowed size first (e.g. MainWindow's
        own `resize(1100, 700)`, SplashScreen's `resize(720, 640)`) —
        harmless normally, but going straight from that small windowed
        size to `showFullScreen()` is exactly the transition that
        triggered a real crash: `xdg_surface buffer (1920 x 1205) is
        larger than the configured fullscreen state (1920 x 1200)` — a
        fatal Wayland protocol error that killed the whole Wayland
        connection, not just MIA Explicitly resizing to the actual
        screen size first means the widget is already at the correct
        geometry before the fullscreen request, removing the small-
        then-huge jump Qt's Wayland backend was mis-negotiating.
        **Unverified beyond this one incident** — this dev sandbox has
        no real Wayland display to reproduce/confirm the fix against
        (same "genuinely unverifiable here" situation as
        docs/KNOWN_ISSUES.md's other real-hardware-only entries);
        needs confirming on the machine that actually hit the crash.
        """
        if self.config.get("system.kiosk_mode", False):
            screen = widget.screen() or self.qt_app.primaryScreen()
            if screen is not None:
                widget.resize(screen.size())
            widget.showFullScreen()
        else:
            widget.show()

    def _on_theme_changed(self, theme_id: str, **_kwargs) -> None:
        """Live theme swap — published by modules/settings/module.py's Theme dropdown. No restart required."""
        self.qt_app.setStyleSheet(get_theme_stylesheet(theme_id))

    def _register_search_providers(self) -> None:
        """
        Register the two search providers available from day one:
        modules (so typing "map" finds and opens the Maps module) and
        profiles (so typing a name finds that profile to switch to).
        Both are registered here, in the orchestrator, rather than
        inside ModuleManager/ProfileManager themselves — those services
        shouldn't need to know search exists at all; this is the one
        place that wires independent core services together.
        """
        self.context.search.register_provider("modules", self._search_modules)
        self.context.search.register_provider("profiles", self._search_profiles)

    def _register_calculators(self) -> None:
        """
        Register the general-purpose calculators that ship with core
        (Unit Converter, Ohm's Law) — they have no single obvious
        module home, so they're registered here rather than inside a
        specific module's on_load(). A domain-specific module (e.g. a
        future Electronics module) can register its own calculators
        into the same self.context.calculators from its own on_load()
        without needing any change here.
        """
        from modules.toolbox.calculators.ohms_law import OhmsLawCalculator
        from modules.toolbox.calculators.unit_converter import UnitConverterCalculator

        self.context.calculators.register(UnitConverterCalculator())
        self.context.calculators.register(OhmsLawCalculator())

    def _register_dashboard_widgets(self) -> None:
        """
        Register the Home dashboard's built-in widgets — 2026-07-15,
        "framework first" per the widget/dashboard-customization
        conversation (docs/VISION.md). The actual QWidget construction
        for each of these lives in gui/home_dashboard.py; this registry
        only tracks identity/enabled-state/order, same core/gui split as
        ModuleManager (core, module_ids) vs. MainWindow (gui, the grid).
        """
        self.context.dashboard_widgets.register(WidgetDescriptor("power", "Power", "\U0001F50B"))
        self.context.dashboard_widgets.register(WidgetDescriptor("mission", "Mission", "\U0001F3C6"))
        # 2026-07-18: Volume moved out of the dashboard grid entirely,
        # into a compact control in the header's new profile menu (see
        # gui/main_window.py) — real user report traced the dashboard's
        # recurring "spacing/wording is off" complaint to this widget:
        # it's the only 3-element card (header + slider + body) among
        # otherwise-uniform 2-element cards, and it happened to land in
        # the very first grid row (registration order 3rd) right next to
        # Power/Mission, forcing that row taller than the others.
        self.context.dashboard_widgets.register(WidgetDescriptor("current_project", "Current Project", "\U0001F4CB"))
        # 2026-07-15 "ForMIA" design handoff, pass 2: the first two new
        # widgets from the mockup that need zero new data-gathering
        # infrastructure (both reuse fully-existing real services) —
        # CPU Load/Network are deliberately deferred to a later pass,
        # see docs/ROADMAP.md for why.
        self.context.dashboard_widgets.register(WidgetDescriptor("activity_log", "Activity Log", "\U0001F4DC"))
        self.context.dashboard_widgets.register(WidgetDescriptor("quick_bus", "Quick Bus", "\U0001F39B"))
        # 2026-07-16: the Companion Avatar widget (core/avatar_manager.py,
        # gui/widgets/avatar_camera_widget.py) is deliberately NOT
        # registered here for now — dropped at the user's explicit call
        # once a real architecture conflict surfaced: VMagicMirror is
        # Windows-only, but Project 2's Home Cloud machine
        # (docs/HARDWARE.md) is planned to run Ubuntu for ROCm support,
        # not Windows. The code is left in place, unregistered rather
        # than deleted, since it's real and reusable once either a
        # Linux-native avatar renderer or a network-streaming approach
        # is decided — see docs/ROADMAP.md's entry for the open options.
        # 2026-07-16: MIA Home's expanded scope (docs/VISION.md) —
        # real estate + Kraken agent widgets over
        # core/finance_manager.py's watched-folder snapshot ingestion,
        # plus a combined Net Worth rollup. Both degrade gracefully to
        # "No snapshot imported yet" until the user actually drops an
        # export file in.
        self.context.dashboard_widgets.register(WidgetDescriptor("real_estate", "Real Estate", "\U0001F3D8"))
        self.context.dashboard_widgets.register(WidgetDescriptor("kraken_agent", "Kraken Agent", "\U0001F4C8"))
        self.context.dashboard_widgets.register(WidgetDescriptor("net_worth", "Net Worth", "\U0001F4B0"))
        # 2026-08-30: MIA Homestead sync (see that repo's own
        # docs/MIA_HOME_SYNC_PLAN.md) — same watched-folder snapshot
        # pattern as the finance widgets above, over
        # core/homestead_manager.py instead. Degrades the same way to
        # "No snapshot imported yet" until a human drops an export in.
        self.context.dashboard_widgets.register(WidgetDescriptor("homestead", "Homestead", "\U0001F33F"))
        # 2026-09-07: Maintenance tracking (core/maintenance_manager.py)
        # for vehicles/power equipment/appliances/property/tools —
        # degrades to "All caught up" until a real asset/task is added.
        self.context.dashboard_widgets.register(WidgetDescriptor("maintenance", "Maintenance", "\U0001F527"))
        self.context.dashboard_widgets.register(WidgetDescriptor("budget", "Budget", "\U0001F4B0"))
        # "real_estate" is already taken by the pre-existing Kraken-style
        # external ingestion widget (core.finance_manager's snapshot
        # import) — "property_portfolio" is this session's NEW native
        # module (modules/real_estate/module.py), deliberately named/
        # labeled to avoid two same-named "Real Estate" cards confusing
        # which is which.
        self.context.dashboard_widgets.register(WidgetDescriptor("property_portfolio", "My Properties", "\U0001F3D8"))
        # 2026-09-09: Music (core/music_manager.py) — degrades to
        # "Nothing playing" until the user actually plays a track.
        self.context.dashboard_widgets.register(WidgetDescriptor("music", "Music", "\U0001F3B5"))
        self.context.dashboard_widgets.register(WidgetDescriptor("kitchen", "Kitchen", "\U0001F373"))
        self.context.dashboard_widgets.register(WidgetDescriptor("workout", "Workout", "\U0001F3CB"))
        self.context.dashboard_widgets.register(WidgetDescriptor("relationships", "People & Pets", "\U0001F465"))

    def _register_assistant_actions(self) -> None:
        """
        Register the built-in actions the Assistant can invoke via
        core/llm_manager.py's chat_with_tools() — docs/ROADMAP.md
        milestone 5.5. Registered here (not in modules/assistant/) for
        the same reason search providers and calculators are: this is
        the one place independent core services get wired together.
        Every handler below is a `@staticmethod` — a pure function of
        (context, arguments) — except that none of them actually need
        `self` at all; `context.module_manager` (set right above) is
        what `_action_open_module` reads to validate the target
        actually exists. That staticmethod-purity is what let
        `core/core_runtime.py`'s headless Core entry point curate its
        own smaller Assistant action set (see that module) without
        having to duplicate this class or its Qt/gui-heavy imports.
        """
        self.context.assistant_actions.register(AssistantAction(
            name="open_module",
            domain="system",
            description="Open/navigate to a MIA module by its module_id.",
            parameters={
                "type": "object",
                "properties": {
                    "module_id": {
                        "type": "string",
                        "description": "The module_id to open, e.g. 'notes', 'toolbox', 'settings'.",
                    },
                },
                "required": ["module_id"],
            },
            handler=self._action_open_module,
            trigger_phrases=("open ", "launch ", "go to ", "switch to ", "take me to "),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_alarm",
            domain="alarms",
            description=(
                "Create a new alarm in MIA for a specific clock time (e.g. wake up at 07:00). "
                "NOT for recurring vehicle/equipment upkeep on a day interval (e.g. 'change the oil "
                "every 6 months') — use add_maintenance_task for that instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "A short name for the alarm."},
                    "time": {"type": "string", "description": "Time in 24-hour HH:MM format, e.g. '07:00'."},
                },
                "required": ["label", "time"],
            },
            handler=self._action_add_alarm,
            trigger_phrases=("set an alarm", "set a timer", "add an alarm", "remind me", "wake me up"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_alarms",
            domain="alarms",
            description="List the user's current alarms in MIA",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_alarms,
            trigger_phrases=(
                "list my alarms", "list alarms", "what alarms", "show my alarms", "do i have any alarms",
                # 2026-07-18: real gap — "when is my next alarm" matched nothing at all.
                "next alarm", "when is my alarm",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_alarm",
            domain="alarms",
            destructive=True,
            description="Delete an existing alarm in MIA by its label.",
            parameters={
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "The label of the alarm to delete, e.g. 'Wake Up'."},
                },
                "required": ["label"],
            },
            handler=self._action_delete_alarm,
            # Bare "alarm " (trailing space, so it doesn't match inside
            # "alarming") is needed alongside the combo phrases because
            # a real label sits between the verb and the noun in
            # natural phrasing ("delete my Wake Up alarm") — no fixed
            # combo phrase can match an arbitrary inserted name.
            trigger_phrases=("delete an alarm", "delete alarm", "remove an alarm", "remove alarm", "cancel my alarm", "cancel the alarm", "alarm "),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_note",
            domain="notes",
            description="Add a new journal/note entry in MIA's Notes module.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The note's title."},
                    "body": {"type": "string", "description": "The note's body text."},
                },
                "required": ["title"],
            },
            handler=self._action_add_note,
            trigger_phrases=("add a note", "take a note", "make a note", "write down", "jot down"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_notes",
            domain="notes",
            description=(
                "List or search the user's journal/note entries in MIA's Notes module. "
                "Leave query empty to list everything, most recently updated first."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to search titles/bodies/tags for."},
                },
                "required": [],
            },
            handler=self._action_list_notes,
            trigger_phrases=(
                "show me my notes", "show my notes", "list my notes", "list notes",
                "search my notes", "search notes", "find a note", "read my notes", "what notes do i have",
                # 2026-07-18: real gap — "anything I wrote down" matched
                # nothing. Deliberately overlaps add_note's own "write
                # down" trigger (both domains attach together, same
                # already-proven "let the model disambiguate via tool
                # descriptions" pattern as other collision pairs in this
                # registry) rather than trying to avoid it.
                "anything i wrote down", "what did i write down",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_note",
            domain="notes",
            destructive=True,
            description="Delete an existing journal/note entry in MIA's Notes module by its title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the note to delete."},
                },
                "required": ["title"],
            },
            handler=self._action_delete_note,
            # No bare "note " trigger (unlike delete_alarm's bare
            # "alarm ") — "note" collides with extremely common
            # unrelated phrases ("please note that...", "of note"),
            # so only combo phrases are used here; this means a
            # "delete my [title] note" construction (name inserted
            # before the noun) won't gate open, a known, deliberate
            # trade-off, not an oversight.
            trigger_phrases=("delete a note", "delete the note", "delete note", "delete my note", "remove a note", "remove the note", "remove note"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_inventory_item",
            domain="inventory",
            description="Add a new item to MIA's general Inventory tool.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The item's name."},
                    "quantity": {"type": "integer", "description": "How many to add."},
                },
                "required": ["name"],
            },
            handler=self._action_add_inventory_item,
            trigger_phrases=("add to inventory", "add an inventory item", "inventory item"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_inventory",
            domain="inventory",
            description=(
                "List or search MIA's Inventory tool, including quantities. "
                "Use this to answer 'how many X do I have' questions about "
                "inventory items. Leave query empty to list everything."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to search item names/categories/notes for."},
                },
                "required": [],
            },
            handler=self._action_list_inventory,
            # "how many" alone was tried and rejected: verified against
            # the live model that it made "How many people live in
            # Ohio?" hallucinate a get_system_health call — the exact
            # failure mode this gating mechanism exists to prevent.
            # "do i have" (without "any") still catches "how many M3
            # bolts do I have?" without that false-positive.
            #
            # milestone 5.15 finding: once the registry crossed ~39
            # tools (adding the Security tab's 4 tools), "How many M3
            # bolts do I have?" started reproducibly (5/5 runs)
            # hallucinating a non-existent "get_inventory_quantity"
            # tool-call-shaped string as plain content instead of
            # calling this tool — not sampling noise (see
            # llm_manager.py's temperature=0 note), a real
            # tool-count/schema-interference regression isolated by
            # bisecting the attached tool set. Spelling out the "how
            # many X do I have" phrasing directly in this description
            # (rather than renaming/removing any tool) fixed it
            # reliably at the full 39-tool count — cheaper than
            # fighting the registry's all-or-nothing gating design.
            trigger_phrases=("inventory", "do i have"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_inventory_item",
            domain="inventory",
            destructive=True,
            description="Remove an item entirely from MIA's Inventory tool by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the item to remove."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_inventory_item,
            trigger_phrases=("delete from inventory", "delete an inventory item", "remove from inventory", "remove an inventory item"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="adjust_inventory_quantity",
            domain="inventory",
            destructive=True,
            description=(
                "Change the quantity of an existing inventory item by an amount (positive to add "
                "more, negative to use/remove some), e.g. 'I used 5 M3 bolts' -> delta -5. "
                "Quantity never goes below zero. Use add_inventory_item instead for a brand-new item."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the existing item."},
                    "delta": {"type": "integer", "description": "Amount to change the quantity by. Negative to subtract."},
                },
                "required": ["name", "delta"],
            },
            handler=self._action_adjust_inventory_quantity,
            trigger_phrases=("i used", "used up", "use up", "got more", "received more"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_waypoints",
            domain="waypoints",
            description="List or search the user's saved waypoints (named locations) in MIA's Navigation module.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to search waypoint names/notes for."},
                },
                "required": [],
            },
            handler=self._action_list_waypoints,
            trigger_phrases=(
                "waypoint", "waypoints", "list my waypoints", "list waypoints",
                # 2026-07-18: real gap — "what locations have I saved"
                # matched nothing (bare "waypoint(s)" wasn't said at all).
                "locations have i saved", "saved locations",
                # 2026-07-19: real gap found via tests/core_live_voice_check.py's
                # Piper-TTS-to-Vosk-STT tier — Vosk's small model
                # transcribes "waypoint(s)" as the two separate words
                # "way point(s)" 100% of the time in testing (6/6 across
                # several phrasings/positions), so the bare "waypoint"
                # trigger above never actually fires from real speech.
                "way point", "way points",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="waypoint_distance",
            domain="waypoints",
            description="Get the distance and compass bearing between two of the user's saved waypoints, by name.",
            parameters={
                "type": "object",
                "properties": {
                    "from_name": {"type": "string", "description": "Name of the starting waypoint."},
                    "to_name": {"type": "string", "description": "Name of the destination waypoint."},
                },
                "required": ["from_name", "to_name"],
            },
            handler=self._action_waypoint_distance,
            trigger_phrases=("distance to", "distance from", "how far is", "how far apart", "bearing to", "bearing from"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_waypoint",
            domain="waypoints",
            destructive=True,
            description="Delete an existing saved waypoint in MIA's Navigation module by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the waypoint to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_waypoint,
            trigger_phrases=("delete a waypoint", "delete waypoint", "remove a waypoint", "remove waypoint"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_system_health",
            domain="system",
            description="Get a live snapshot of this device's system health: CPU, memory, disk, temperature, and network usage.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_system_health,
            trigger_phrases=(
                "system health", "cpu usage", "cpu temperature", "memory usage",
                "disk usage", "diagnostics", "how's the system", "check diagnostics",
                # 2026-07-18: real gap — "is everything running okay"
                # matched nothing at all (no tool call, not even
                # recognized as an action request).
                "everything ok", "everything okay", "everything running",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="recall_recent_activity",
            domain="system",
            description=(
                "Look up what the user has recently done in MIA (modules opened, "
                "notifications, profile switches), optionally filtered by a keyword. "
                "Use this for questions like 'what have I been doing' or 'what did I do "
                "with notes recently'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Optional keyword to filter activity by (e.g. a module or project name). Leave empty for everything recent.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "How many recent entries to look at, default 20.",
                    },
                },
                "required": [],
            },
            handler=self._action_recall_recent_activity,
            trigger_phrases=("recent activity", "activity log", "what have i done", "what have i been doing", "what did i do"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_waypoint",
            domain="waypoints",
            description="Save a new named waypoint (location) in MIA's Navigation module.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name for the waypoint."},
                    "latitude": {"type": "number", "description": "Latitude in decimal degrees."},
                    "longitude": {"type": "number", "description": "Longitude in decimal degrees."},
                    "category": {
                        "type": "string",
                        "description": "Optional category: Campsite, Trailhead, Water Source, Viewpoint, or Other.",
                    },
                },
                "required": ["name", "latitude", "longitude"],
            },
            handler=self._action_add_waypoint,
            trigger_phrases=("add a waypoint", "save a waypoint", "new waypoint", "mark a waypoint"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_sun_moon_info",
            domain="waypoints",
            description=(
                "Get today's sunrise/sunset times and moon phase for a saved waypoint's "
                "location — real survival-relevant info (how much daylight is left, "
                "moon phase for night navigation)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "waypoint_name": {"type": "string", "description": "The name of the saved waypoint."},
                },
                "required": ["waypoint_name"],
            },
            handler=self._action_get_sun_moon_info,
            trigger_phrases=(
                "sunrise", "sunset", "moon phase", "when does the sun", "when will the sun",
                "what time does the sun", "how much daylight",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_expedition",
            domain="expeditions",
            description="Start a new Expedition (a dated outing that can hold multiple trips) in MIA's Expeditions module.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name for the expedition."},
                    "start_date": {"type": "string", "description": "Optional start date, YYYY-MM-DD."},
                    "location": {"type": "string", "description": "Optional region/area name."},
                },
                "required": ["name"],
            },
            handler=self._action_add_expedition,
            trigger_phrases=("start an expedition", "new expedition", "add an expedition", "create an expedition", "plan an expedition"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_expeditions",
            domain="expeditions",
            description="List the user's Expeditions in MIA",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_expeditions,
            trigger_phrases=(
                "list my expeditions", "list expeditions", "what expeditions", "show my expeditions",
                # 2026-07-18: real gap — "how many expeditions have I
                # been on" matched nothing at all.
                "how many expeditions", "expeditions have i",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="recall_expedition",
            domain="expeditions",
            description=(
                "Get a detailed recap of ONE Expedition in MIA's Memories: duration, "
                "distance/pace per activity type, waypoint categories visited, latest "
                "journal/conditions entry, and photo count. This is a single-Expedition "
                "summary, NOT a bare list — use list_expeditions instead for 'what "
                "expeditions do I have'-style questions. Leave name empty for the most "
                "recent Expedition."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Optional Expedition name. Leave empty for the most recent one.",
                    },
                },
                "required": [],
            },
            handler=self._action_recall_expedition,
            # "Tell me about my Field Season expedition" (name inserted
            # before the noun) doesn't match any of these — same
            # accepted trade-off as delete_project/delete_task/
            # mark_task_done (see tests/test_assistant_action_gating.py's
            # test_delete_project_phrasing_gates_open docstring). "the
            # expedition called X" phrasing (name after the noun) is
            # supported instead via the dedicated triggers below.
            trigger_phrases=(
                "tell me about my last expedition", "tell me about my expedition",
                "tell me about the expedition", "describe my expedition",
                "describe the expedition", "recap my expedition", "expedition recap",
                "what did i do on my expedition", "what have i done on my expedition",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_trip",
            domain="expeditions",
            description="Add a new Trip (one hike, paddle, ride, fishing trip, etc.) under an existing Expedition in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "expedition_name": {
                        "type": "string",
                        "description": "The name of the Expedition this trip belongs to (must already exist).",
                    },
                    "name": {"type": "string", "description": "A short name for the trip."},
                    "activity_type": {
                        "type": "string",
                        "description": "Optional activity type: Hiking, Camping, Fishing, Kayaking, Biking, or Other.",
                    },
                    "start_date": {"type": "string", "description": "Optional start date, YYYY-MM-DD."},
                },
                "required": ["expedition_name", "name"],
            },
            handler=self._action_add_trip,
            trigger_phrases=("add a trip", "new trip", "start a trip", "plan a trip", "create a trip"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_trips",
            domain="expeditions",
            description="List the user's Trips in MIA, optionally filtered to one Expedition by name.",
            parameters={
                "type": "object",
                "properties": {
                    "expedition_name": {
                        "type": "string",
                        "description": "Optional Expedition name to filter by. Leave empty for all trips.",
                    },
                },
                "required": [],
            },
            handler=self._action_list_trips,
            trigger_phrases=("list my trips", "list trips", "what trips", "show my trips"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_gear_item",
            domain="expeditions",
            description="Add an item to a Trip's gear checklist in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "trip_name": {
                        "type": "string",
                        "description": "The name of the trip to add gear to (must already exist).",
                    },
                    "label": {"type": "string", "description": "The gear item's name, e.g. 'Tent' or 'First aid kit'."},
                },
                "required": ["trip_name", "label"],
            },
            handler=self._action_add_gear_item,
            trigger_phrases=("add gear", "add to my gear", "gear list", "packing list"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_trip_log_entry",
            domain="expeditions",
            description=(
                "Add a dated journal/log entry to a specific Trip in MIA, optionally "
                "recording weather/conditions. Use this instead of add_note when the user "
                "is logging something about a specific trip/outing (arriving somewhere, "
                "conditions encountered, etc.), not a general-purpose note."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "trip_name": {
                        "type": "string",
                        "description": "The name of the trip this log entry belongs to (must already exist).",
                    },
                    "title": {"type": "string", "description": "A short title for the log entry."},
                    "body": {"type": "string", "description": "Optional body text describing what happened."},
                    "conditions": {
                        "type": "string",
                        "description": "Optional weather/conditions, e.g. 'Clear, ~15C, light wind'.",
                    },
                },
                "required": ["trip_name", "title"],
            },
            handler=self._action_add_trip_log_entry,
            trigger_phrases=("trip journal", "log entry for my trip", "log my arrival", "add to my trip log", "trip log"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_expedition",
            domain="expeditions",
            destructive=True,
            description="Delete an existing Expedition in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the expedition to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_expedition,
            # "Delete my Field Season expedition" (name inserted before
            # the noun) doesn't match any of these — same accepted
            # trade-off as delete_project/delete_task (see
            # tests/test_assistant_action_gating.py). "the expedition
            # called X"/"delete the expedition" (name after) is supported.
            trigger_phrases=("delete an expedition", "delete my expedition", "remove an expedition", "delete the expedition"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_trip",
            domain="expeditions",
            destructive=True,
            description="Delete an existing Trip in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the trip to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_trip,
            # Same accepted name-before-noun trade-off as delete_expedition
            # above — "delete the trip called X" gates open, "delete my
            # Day 1 trip" (name in the middle) doesn't.
            trigger_phrases=("delete a trip", "delete my trip", "remove a trip", "delete the trip"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="toggle_gear_packed",
            domain="expeditions",
            description="Mark a gear checklist item on a Trip as packed or not packed (toggles its current state).",
            parameters={
                "type": "object",
                "properties": {
                    "trip_name": {"type": "string", "description": "The name of the trip the gear item belongs to."},
                    "label": {"type": "string", "description": "The gear item's name, e.g. 'Tent' or 'First aid kit'."},
                },
                "required": ["trip_name", "label"],
            },
            handler=self._action_toggle_gear_packed,
            trigger_phrases=("mark packed", "mark as packed", "i packed", "packed my", "gear is packed", "mark unpacked", "not packed yet"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_trip_summary",
            domain="expeditions",
            description="Get a Trip's logged distance, average speed, and planned route distance in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the trip."},
                },
                "required": ["name"],
            },
            handler=self._action_get_trip_summary,
            trigger_phrases=("how far did i", "trip distance", "trip summary", "how fast was i", "average speed", "how long is my planned route", "planned route distance"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_device_profile",
            domain="system",
            description=(
                "Tell the user which MIA EDITION (hardware/software variant) this "
                "device is running: Core (Pi 5 + AI HAT+ 2 field edition) or Home "
                "(desktop workstation edition). This is about the device/installation "
                "itself, NOT about user accounts — use list_profiles for the people "
                "set up on this device."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_device_profile,
            trigger_phrases=("what device profile", "am i on core or home", "which edition", "device profile"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="set_theme",
            domain="system",
            description="Change MIA's visual theme.",
            parameters={
                "type": "object",
                "properties": {
                    "theme_id": {
                        "type": "string",
                        "description": "One of: dark_field, low_energy, colored, anime_monochrome.",
                    },
                },
                "required": ["theme_id"],
            },
            handler=self._action_set_theme,
            trigger_phrases=(
                "change the theme", "set the theme", "switch the theme", "use a different theme",
                "low energy theme", "anime theme", "colored theme", "dark field theme",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="set_birthday",
            domain="system",
            description=(
                "Remember the current user's own birthday, so MIA can recognize and celebrate it. "
                "Use this whenever the user tells you their birthday in conversation — do not ask for "
                "it unprompted."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "birthday": {
                        "type": "string",
                        "description": "The user's birthday as YYYY-MM-DD. Use a plausible recent year if only month/day were given.",
                    },
                },
                "required": ["birthday"],
            },
            handler=self._action_set_birthday,
            trigger_phrases=("my birthday is", "my birthday's", "remember my birthday"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_calendar_event",
            domain="calendar",
            description="Add a new event to MIA's Calendar, optionally repeating yearly/monthly/weekly.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "A short title for the event."},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                    "time": {"type": "string", "description": "Optional time in 24-hour HH:MM format. Leave empty for an all-day event."},
                    "notes": {"type": "string", "description": "Optional notes."},
                    "recurrence": {
                        "type": "string",
                        "description": (
                            "Optional: 'yearly', 'monthly', or 'weekly' for a repeating event (e.g. a "
                            "birthday or anniversary). Leave empty for a one-time event."
                        ),
                    },
                },
                "required": ["title", "date"],
            },
            handler=self._action_add_calendar_event,
            trigger_phrases=("add an event", "add a calendar event", "schedule an event", "new calendar event"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_calendar_events",
            domain="calendar",
            description=(
                "List the user's upcoming/scheduled Calendar events in MIA — what's coming up "
                "today, this week, or on any date. Not for past activity — see recall_recent_activity for that."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_calendar_events,
            trigger_phrases=(
                "list my events", "list my calendar", "what's on my calendar", "upcoming events", "show my calendar",
                # 2026-07-18: real gaps found live-probing beyond the
                # official golden set — "do i have anything today" was
                # ONLY catching inventory's broad "do i have" trigger,
                # never calendar's own domain at all; "going on this
                # week" matched nothing. Both now covered here.
                "anything on my calendar", "anything today", "going on this week", "going on today",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_calendar_event",
            domain="calendar",
            destructive=True,
            description="Delete an existing Calendar event in MIA by its title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the event to delete."},
                },
                "required": ["title"],
            },
            handler=self._action_delete_calendar_event,
            # Bare "event " (trailing space, avoids matching inside "eventful")
            # needed alongside the combo phrases for the same name-between-
            # verb-and-noun reason as "alarm "/"component " below.
            trigger_phrases=("delete an event", "delete the event", "remove an event", "cancel the event", "event "),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_power_status",
            domain="power",
            description="Get this device's current battery/power status.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_power_status,
            trigger_phrases=(
                "battery level", "battery status", "power status", "how much battery", "how's my battery",
                # 2026-07-18: real gap — "am I plugged in" matched nothing at all.
                "plugged in", "am i charging",
                # 2026-07-18: real gap — "What is my power percentage"
                # matched nothing at all (STT correctly transcribed it,
                # but no trigger phrase used the word "power" alone with
                # "percentage"/"level"), so it fell through to the
                # grounded info-question path instead of calling this
                # tool, and got a hedging "I don't know" reply that only
                # awkwardly related power to battery in prose.
                "power percentage", "power level", "percent power", "how much power",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_component",
            domain="components",
            description="Add a new electronic component to MIA's Workshop & Electronics component database.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The component's name, e.g. 'M3 bolts' or '10k resistor'."},
                    "category": {"type": "string", "description": "Optional category, e.g. 'Resistor', 'Capacitor', 'IC'."},
                    "value": {"type": "string", "description": "Optional value, e.g. '10k', '100nF'."},
                    "package": {"type": "string", "description": "Optional package, e.g. 'THT', '0805'."},
                    "quantity": {"type": "integer", "description": "Quantity on hand, default 0."},
                    "location": {"type": "string", "description": "Optional storage location."},
                },
                "required": ["name"],
            },
            handler=self._action_add_component,
            trigger_phrases=("add a component", "new component", "add a part", "add to my parts"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_components",
            domain="components",
            description="List or search the user's electronic components in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all components."},
                },
                "required": [],
            },
            handler=self._action_list_components,
            trigger_phrases=(
                "list my components", "list components", "what components", "show my components", "search components",
                # 2026-07-18: real gap — "what parts do I have" only
                # matched inventory's broad "do i have" trigger, never
                # reached the components domain at all.
                "what parts", "my parts",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_component",
            domain="components",
            destructive=True,
            description="Delete an existing electronic component in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the component to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_component,
            trigger_phrases=("delete a component", "remove a component", "component "),
        ))
        # 2026-07-18: Workshop's Materials/Jobs/Products/Ledger production
        # pipeline (built earlier this session) had zero Assistant
        # actions until now — a real gap found via a module-coverage
        # audit, not guessed. Four small domains (not one big "workshop"
        # domain) so a materials-only question doesn't also attach
        # ledger/job tools it doesn't need — same per-topic scoping this
        # registry already uses everywhere else.
        self.context.assistant_actions.register(AssistantAction(
            name="add_material",
            domain="materials",
            description="Add a raw Material to MIA's Workshop production pipeline (Materials tab).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The material's name, e.g. 'Plywood' or 'PLA Filament'."},
                    "unit": {"type": "string", "description": "Optional unit, e.g. 'sheet', 'kg', 'spool'."},
                    "quantity_on_hand": {"type": "number", "description": "Optional starting quantity on hand."},
                },
                "required": ["name"],
            },
            handler=self._action_add_material,
            trigger_phrases=("add a material", "new material", "add material"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_materials",
            domain="materials",
            description="List the user's raw Materials in MIA's Workshop production pipeline.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all materials."},
                },
                "required": [],
            },
            handler=self._action_list_materials,
            trigger_phrases=("list my materials", "list materials", "what materials", "show my materials"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_product",
            domain="products",
            description="Add a finished Product to MIA's Workshop production pipeline (Products tab).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The product's name."},
                    "quantity_in_stock": {"type": "number", "description": "Optional starting quantity in stock."},
                    "base_price": {"type": "number", "description": "Optional default selling price."},
                },
                "required": ["name"],
            },
            handler=self._action_add_product,
            trigger_phrases=("add a product", "new product", "add product"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_products",
            domain="products",
            description="List the user's finished Products in MIA's Workshop production pipeline.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all products."},
                },
                "required": [],
            },
            handler=self._action_list_products,
            trigger_phrases=("list my products", "list products", "what products", "show my products"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_job",
            domain="jobs",
            description="Start a new production Job in MIA's Workshop pipeline.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The job's name."},
                    "description": {"type": "string", "description": "Optional description of the job."},
                },
                "required": ["name"],
            },
            handler=self._action_add_job,
            # Deliberately no bare "new job" — found via live testing that
            # it falsely gates open on "I love my new job at the bakery"
            # and, worse, the model then hallucinated an unrelated
            # set_birthday call once the (wrongly) attached jobs-domain
            # tools were in front of it. "start a new job" (matching the
            # same "Start a new X called Y" phrasing add_mission/
            # add_project/add_expedition already use) is specific enough
            # to avoid that collision.
            trigger_phrases=("start a job", "start a new job", "add a job", "create a job"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_jobs",
            domain="jobs",
            description="List the user's production Jobs in MIA's Workshop pipeline.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_jobs,
            trigger_phrases=("list my jobs", "list jobs", "what jobs", "show my jobs"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="consume_material",
            domain="jobs",
            description=(
                "Record that an existing Job consumed some quantity of an existing Material — deducts "
                "that quantity from the Material's own stock automatically."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "The name of the existing Job."},
                    "material_name": {"type": "string", "description": "The name of the existing Material consumed."},
                    "quantity": {"type": "number", "description": "How much of the material was used."},
                },
                "required": ["job_name", "material_name", "quantity"],
            },
            handler=self._action_consume_material,
            # "job used" not "my job used" — real phrasing puts the job's
            # own name between "my" and "job used" ("My Birdhouse Batch
            # job used..."), which the stricter phrase missed entirely.
            trigger_phrases=("used material", "consumed material", "consume material", "job used"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="produce_product",
            domain="jobs",
            description=(
                "Record that an existing Job produced some quantity of an existing Product — credits "
                "that quantity onto the Product's own stock automatically."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "The name of the existing Job."},
                    "product_name": {"type": "string", "description": "The name of the existing Product produced."},
                    "quantity": {"type": "number", "description": "How much of the product was produced."},
                },
                "required": ["job_name", "product_name", "quantity"],
            },
            handler=self._action_produce_product,
            # "job produced" not "my job produced" — same reasoning as
            # consume_material's "job used" fix just above.
            trigger_phrases=("job produced", "job finished producing", "produced product", "produce product"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="record_sale",
            domain="ledger",
            description=(
                "Record a sale of an existing Product in MIA's Workshop Ledger — deducts the sold "
                "quantity from the Product's stock and logs the revenue."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "The name of the existing Product sold."},
                    "quantity": {"type": "number", "description": "How many units were sold."},
                    "amount": {"type": "number", "description": "The total sale amount in dollars."},
                },
                "required": ["product_name", "quantity", "amount"],
            },
            handler=self._action_record_sale,
            trigger_phrases=("record a sale", "log a sale", "sold a product", "i sold", "record sale"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_ledger_summary",
            domain="ledger",
            description="Get the user's total revenue, expenses, and net profit from MIA's Workshop Ledger.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_ledger_summary,
            trigger_phrases=("ledger summary", "how much profit", "my revenue", "my expenses", "net profit"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_connected_devices",
            domain="field_kit",
            description="List currently connected external USB storage and serial devices in MIA's Field Kit.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_connected_devices,
            trigger_phrases=("connected devices", "what devices are connected", "list devices", "usb devices", "list connected devices"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_scripts",
            domain="field_kit",
            description="List the user's saved scripts in MIA's Field Kit script library.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all scripts."},
                },
                "required": [],
            },
            handler=self._action_list_scripts,
            trigger_phrases=("list my scripts", "list scripts", "what scripts", "show my scripts"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_profiles",
            domain="system",
            description=(
                "List the user ACCOUNTS/PEOPLE set up on this MIA device (e.g. "
                "'Zac', 'Guest'). This is about user accounts, NOT the device's "
                "Core/Home edition setting — use get_device_profile for that."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_profiles,
            trigger_phrases=("list my profiles", "list profiles", "what profiles", "show my profiles", "who's set up"),
        ))
        # Deliberately NOT registering a "switch_profile" action:
        # gui/profile_select.py requires verify_password() to succeed
        # BEFORE set_active_profile() for any password-protected
        # profile — an Assistant action calling set_active_profile()
        # directly would bypass that check entirely (a real security
        # hole), and the alternative (accepting a password argument from
        # the LLM) would mean a spoken/typed password sits in plaintext
        # chat history, which is worse than a masked password field, not
        # just a different capability class. Same "exclude, don't
        # silently omit" treatment as run_script above.
        self.context.assistant_actions.register(AssistantAction(
            name="identify_hash",
            domain="security",
            description="Identify the likely algorithm(s) for a hash string (e.g. bcrypt, MD5, SHA-256) by its format.",
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": "The hash string to identify."},
                },
                "required": ["value"],
            },
            handler=self._action_identify_hash,
            trigger_phrases=("identify this hash", "what hash is this", "identify hash", "hash format", "what kind of hash"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="check_password_strength",
            domain="security",
            description=(
                "Estimate a password's strength (entropy-based rating and warnings). "
                "For a real account password, prefer MIA's Field Kit Security tab "
                "(a masked input field) over pasting it into chat — chat history isn't "
                "masked/hidden the way a password field is."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "password": {"type": "string", "description": "The password text to assess."},
                },
                "required": ["password"],
            },
            handler=self._action_check_password_strength,
            trigger_phrases=("check my password", "password strength", "how strong is this password", "rate this password", "check password strength"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="calculate_subnet",
            domain="security",
            description="Calculate subnet/CIDR details (network address, broadcast, netmask, usable host range) for an IPv4 or IPv6 CIDR.",
            parameters={
                "type": "object",
                "properties": {
                    "cidr": {"type": "string", "description": "CIDR notation, e.g. '192.168.1.0/24'."},
                },
                "required": ["cidr"],
            },
            handler=self._action_calculate_subnet,
            trigger_phrases=("calculate this subnet", "subnet calculator", "calculate subnet", "cidr calculator", "what's my subnet"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="scan_ports",
            domain="security",
            description=(
                "Quickly check whether 3 common ports (22 SSH, 80 HTTP, 443 HTTPS) are "
                "open on a host. This is a fast, limited check — for a fuller scan of "
                "more ports, use MIA's Field Kit Security tab instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Host or IP to scan, e.g. '192.168.1.1'."},
                },
                "required": ["host"],
            },
            handler=self._action_scan_ports,
            # "for open ports" added after domain-scoped attachment
            # (core/assistant_actions.py) surfaced a real, latent gap:
            # "Scan 192.168.1.1 for open ports"/"Scan 10.0.0.1 for open
            # ports" — this tool's OWN golden-set cases — never actually
            # matched any prior trigger phrase here. That only "worked"
            # before because every prompt gating open at all (here, via
            # open_module's bare "open " substring) attached the full
            # 47-tool registry, so the model could still see and pick
            # scan_ports despite its own trigger never firing. Scoped
            # attachment means a domain that never matches is never
            # offered, so this latent gap needed fixing, not masking.
            trigger_phrases=(
                "scan this host", "scan for open ports", "port scan",
                "what ports are open", "scan ports", "for open ports",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_project",
            domain="projects",
            description="Start a new Project (a container for tasks) in MIA's Project Manager tool.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name for the project."},
                    "status": {
                        "type": "string",
                        "description": "Optional status: Planning, Active, On Hold, or Complete. Defaults to Planning.",
                    },
                    "due_date": {"type": "string", "description": "Optional due date, YYYY-MM-DD."},
                },
                "required": ["name"],
            },
            handler=self._action_add_project,
            trigger_phrases=("add a project", "new project", "start a project", "create a project"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_projects",
            domain="projects",
            description="List the user's Projects in MIA's Project Manager tool.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_projects,
            trigger_phrases=(
                "list my projects", "list projects", "what projects", "show my projects",
                # 2026-07-18: real gap — "what am I currently working
                # on" matched nothing at all (no tool call).
                "what am i working on", "currently working on",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_task",
            domain="projects",
            description="Add a new Task under an existing Project in MIA's Project Manager tool.",
            parameters={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "The name of the Project this task belongs to (must already exist).",
                    },
                    "title": {"type": "string", "description": "A short title for the task."},
                    "due_date": {"type": "string", "description": "Optional due date, YYYY-MM-DD."},
                },
                "required": ["project_name", "title"],
            },
            handler=self._action_add_task,
            trigger_phrases=("add a task", "new task", "add to my tasks", "create a task"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_tasks",
            domain="projects",
            description="List the user's Tasks in MIA, optionally filtered to one Project by name.",
            parameters={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Optional Project name to filter by. Leave empty for all tasks.",
                    },
                },
                "required": [],
            },
            handler=self._action_list_tasks,
            trigger_phrases=(
                "list my tasks", "list tasks", "what tasks", "show my tasks",
                # 2026-07-18: real gap — "what do I need to do" matched
                # nothing at all (no tool call).
                "what do i need to do", "what do i have to do",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_project",
            domain="projects",
            destructive=True,
            description="Delete an existing Project (and unlink, but not delete, its Tasks) in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the project to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_project,
            trigger_phrases=("delete a project", "delete my project", "remove a project", "delete the project"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_task",
            domain="projects",
            destructive=True,
            description="Delete an existing Task in MIA by title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the task to delete."},
                },
                "required": ["title"],
            },
            handler=self._action_delete_task,
            trigger_phrases=("delete a task", "delete my task", "remove a task", "delete the task"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="mark_task_done",
            domain="projects",
            description="Mark an existing Task as done (complete) or not done in MIA by title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the task to update."},
                    "done": {
                        "type": "boolean",
                        "description": "True to mark it done/complete, false to mark it not done. Defaults to true.",
                    },
                },
                "required": ["title"],
            },
            handler=self._action_mark_task_done,
            trigger_phrases=("mark task", "mark my task", "mark the task", "complete my task", "finish my task", "task done", "task complete"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_mission",
            domain="missions",
            description=(
                "Start a new gamified Mission in MIA (e.g. a 'Master Angler' mission for a "
                "fishing trip). Optionally link it to an existing Trip by name."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short, fun name for the mission."},
                    "trip_name": {
                        "type": "string",
                        "description": "Optional name of an existing Trip to link this mission to (must already exist).",
                    },
                },
                "required": ["name"],
            },
            handler=self._action_add_mission,
            trigger_phrases=("start a mission", "new mission", "create a mission", "add a mission"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_missions",
            domain="missions",
            description="List the user's Missions in MIA, including each objective's progress.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_missions,
            trigger_phrases=(
                "list my missions", "list missions", "what missions", "show my missions",
                # 2026-07-18: real gap found live — "what is my current
                # mission" matched none of the phrases above, so the
                # missions domain never got attached and the model just
                # said "I don't know, check the Missions module." This
                # is the same list_missions handler (it already returns
                # every mission with its status, current ones included)
                # — the gap was purely in trigger-phrase coverage, not
                # the handler itself.
                "current mission", "my current mission", "my mission", "active mission", "what mission",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_objective",
            domain="missions",
            description=(
                "Add an Objective to an existing Mission in MIA — either a manually-tracked "
                "tally (e.g. 'catch 3 fish') or a target computed automatically from time spent "
                "on the mission's linked trip (e.g. 'spend 2 hours fishing')."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "mission_name": {"type": "string", "description": "The name of the mission (must already exist)."},
                    "description": {"type": "string", "description": "A short description of the objective, e.g. 'Catch 3 fish'."},
                    "metric_type": {
                        "type": "string",
                        "description": "One of 'tally' (manually counted) or 'trip_duration_hours' (auto-computed from the linked trip). Defaults to 'tally'.",
                    },
                    "target": {"type": "number", "description": "The target value to reach, e.g. 3 for '3 fish' or 2 for '2 hours'."},
                },
                "required": ["mission_name", "description", "target"],
            },
            handler=self._action_add_objective,
            trigger_phrases=("add an objective", "new objective", "add a goal", "create an objective"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="log_mission_progress",
            domain="missions",
            description=(
                "Log progress toward a tally-type Objective on a Mission in MIA — e.g. "
                "recording a catch, a species identified, or any other manually-counted goal. "
                "Only works for tally-type objectives; trip_duration_hours objectives track "
                "themselves automatically and never need this."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "mission_name": {"type": "string", "description": "The name of the mission (must already exist)."},
                    "objective_description": {
                        "type": "string",
                        "description": "Optional — which objective to log against, if the mission has more than one tally objective.",
                    },
                    "delta": {"type": "number", "description": "How much to add to the tally. Defaults to 1."},
                },
                "required": ["mission_name"],
            },
            handler=self._action_log_mission_progress,
            trigger_phrases=("log a catch", "log progress", "count that", "add to my tally", "update my mission progress", "mark progress on my mission"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_mission",
            domain="missions",
            destructive=True,
            description="Delete an existing Mission in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the mission to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_mission,
            trigger_phrases=("delete a mission", "delete my mission", "remove a mission", "delete the mission"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="complete_mission",
            domain="missions",
            description="Mark an existing Mission as completed in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the mission to mark complete."},
                },
                "required": ["name"],
            },
            handler=self._action_complete_mission,
            trigger_phrases=("complete my mission", "mark my mission complete", "finish my mission", "complete the mission", "mark the mission complete"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_trail_maps",
            domain="maps",
            description="List the trail map PDFs cataloged in MIA's Maps module, optionally filtered by park name or state.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to filter by park name or state."},
                },
                "required": [],
            },
            handler=self._action_list_trail_maps,
            trigger_phrases=(
                "trail map", "trail maps", "park map", "park maps", "list my trail maps",
                "what maps do i have", "maps do i have", "maps have i",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_trail_map_from_url",
            domain="maps",
            description=(
                "Download a trail map PDF from a direct URL and add it to MIA's trail map "
                "catalog. Not for offline tile/basemap downloads — those are only available "
                "from the Maps module's own UI, since they can take too long to run as part "
                "of a chat reply."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "park_name": {"type": "string", "description": "The name of the park."},
                    "state": {"type": "string", "description": "The U.S. state the park is in."},
                    "url": {"type": "string", "description": "Direct URL to the trail map PDF."},
                    "notes": {"type": "string", "description": "Optional notes about this trail map."},
                },
                "required": ["park_name", "state", "url"],
            },
            handler=self._action_add_trail_map_from_url,
            trigger_phrases=("add a trail map", "add trail map", "download a trail map", "download this trail map", "catalog this trail map"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_trail_map",
            domain="maps",
            destructive=True,
            description="Delete a cataloged trail map PDF from MIA's Maps module by park name.",
            parameters={
                "type": "object",
                "properties": {
                    "park_name": {"type": "string", "description": "The name of the park whose trail map should be deleted."},
                },
                "required": ["park_name"],
            },
            handler=self._action_delete_trail_map,
            trigger_phrases=("delete a trail map", "delete trail map", "remove a trail map", "remove trail map"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="convert_units",
            domain="toolbox",
            description=(
                "Convert a numeric value between two units of measurement using MIA's "
                "Unit Converter (length, area, volume, weight, temperature, speed, pressure, "
                "energy, power, time, data storage, angle, or fuel economy). Unit names can "
                "be everyday words (e.g. 'miles', 'celsius') — no need for exact formatting."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "The numeric value to convert."},
                    "from_unit": {"type": "string", "description": "The unit to convert from, e.g. 'miles'."},
                    "to_unit": {"type": "string", "description": "The unit to convert to, e.g. 'kilometers'."},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
            handler=self._action_convert_units,
            # 2026-07-18: a bare "convert" trigger gated the domain open
            # for "I'm trying to convert my garage into a workshop" and
            # the model then actually hallucinated a convert_units call
            # for it — same class of cross-domain confabulation as
            # add_job's old bare "new job" trigger. Replaced with
            # specific "to <unit>"/"how many <unit>" compounds, which
            # still cover real conversion phrasing without the bare-verb
            # false-positive risk.
            trigger_phrases=(
                "convert units", "unit conversion",
                "to miles", "to kilometers", "to feet", "to meters", "to yards", "to inches",
                "to pounds", "to kilograms", "to ounces", "to grams",
                "to celsius", "to fahrenheit", "to liters", "to gallons",
                "how many miles", "how many kilometers", "how many feet", "how many meters",
                "how many pounds", "how many kilograms",
                "in fahrenheit", "in celsius",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="calculate_ohms_law",
            domain="toolbox",
            description=(
                "Solve Ohm's Law (V = I x R) for voltage, current, or resistance, given the "
                "other two values, using MIA's Ohm's Law calculator."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "solve_for": {"type": "string", "description": "Which value to solve for: 'voltage', 'current', or 'resistance'."},
                    "voltage": {"type": "number", "description": "Voltage in volts, if known."},
                    "current": {"type": "number", "description": "Current in amps, if known."},
                    "resistance": {"type": "number", "description": "Resistance in ohms, if known."},
                },
                "required": ["solve_for"],
            },
            handler=self._action_calculate_ohms_law,
            # 2026-07-18: real gap — "I have 2 amps through a 10 ohm
            # resistor, what's the voltage?" (a natural way to actually
            # ask this) matched none of the original triggers, which all
            # assumed the user would say "Ohm's law" or "solve for X"
            # explicitly. Added specific electronics vocabulary instead
            # of a bare "current" (too ambiguous — collides with "current
            # events"/"current job") or bare "voltage"/"resistance".
            trigger_phrases=(
                "ohm's law", "ohms law", "solve for voltage", "solve for current", "solve for resistance",
                "amps through", "ohm resistor", "volts across",
                "how many volts", "how many ohms", "how many amps",
                "what's the voltage", "what is the voltage",
            ),
        ))
        # --- Maintenance (vehicles, power equipment, appliances,
        # property, tools) — 2026-09-07, closing the gap found in a
        # full-registry audit: 76 actions existed across 19 domains and
        # Maintenance (built the same session, a substantial new
        # feature — assets, 6 trigger types, documents, meter/sensor
        # logging) had zero. Real collision risk against two existing
        # domains, deliberately not avoided by picking evasive trigger
        # phrases but resolved the same way this registry always has —
        # distinct tool descriptions + live-model verification
        # (tests/live_model_check.py): "projects" already owns generic
        # "add/list/delete a task" phrasing (core.task_manager.Task,
        # under a Project) — a maintenance task is a DIFFERENT concept
        # (recurring upkeep tied to an asset), so both domains
        # legitimately attach together on ambiguous phrasing and the
        # model disambiguates via description, same pattern as the
        # existing add_note/add_trip_log_entry collision. "alarms"
        # already owns "remind me" — a real "remind me to change the
        # oil every 6 months" phrasing plausibly attaches both domains
        # too; verified live rather than assumed safe.
        #
        # add_maintenance_task is deliberately calendar-trigger-only —
        # asking the model to correctly extract a meter unit/interval/
        # threshold/direction from a sentence is a much riskier parse
        # than this registry's established 1-2-field extractions, and
        # every existing action here favors that same "one clean field
        # or two" shape (add_alarm: label+time; add_task: project+title).
        # Runtime/Mileage/Cycles/Condition/Sensor tasks still need the
        # Maintenance module's own dialog, where the interval/threshold/
        # direction fields are all visible together — stated plainly in
        # this tool's own description, not silently unsupported.
        self.context.assistant_actions.register(AssistantAction(
            name="add_maintenance_asset",
            domain="maintenance",
            description=(
                "Add a new vehicle, power equipment, appliance, property item, or tool to MIA's "
                "Maintenance tracker (not Inventory, and not Workshop's electronics parts)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. '2019 Ford F-150', 'Lawn Mower'."},
                    "category": {
                        "type": "string",
                        "description": f"One of: {', '.join(MAINTENANCE_ASSET_CATEGORIES)}. Defaults to 'Other' if unclear.",
                    },
                },
                "required": ["name"],
            },
            handler=self._action_add_maintenance_asset,
            trigger_phrases=(
                "track my", "start tracking", "add a vehicle", "add an asset to maintenance", "add to maintenance",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_maintenance_assets",
            domain="maintenance",
            description="List every vehicle, power equipment, appliance, property item, and tool tracked in MIA's Maintenance tracker.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_maintenance_assets,
            trigger_phrases=(
                "what vehicles", "list my vehicles", "list my equipment", "what am i tracking",
                "list maintenance assets", "show my assets", "what's in my garage",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_maintenance_asset",
            domain="maintenance",
            destructive=True,
            description="Delete a vehicle/equipment/appliance/property/tool from MIA's Maintenance tracker by name (also deletes its tasks).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The exact name of the asset to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_maintenance_asset,
            trigger_phrases=("delete a vehicle", "remove a vehicle", "delete an asset", "stop tracking", "remove from maintenance"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_maintenance_task",
            domain="maintenance",
            description=(
                "Add a recurring or one-time CALENDAR-based maintenance task tied to an existing vehicle/"
                "equipment/appliance/property/tool asset in MIA (e.g. 'change the truck's oil every 90 "
                "days', 'renew tags every year'). NOT a clock-time alarm — use this whenever the task "
                "repeats on a day interval for a specific owned asset, even if phrased as 'remind me to'. "
                "Only for day-interval recurrence — mileage/engine-hour/start-count/sensor-triggered tasks "
                "need the Maintenance module's own screen, not this tool. Only for SETTING UP a new task — "
                "if the user is reporting they already did something (past tense, e.g. 'I renewed the "
                "tags'), use complete_maintenance_task instead, not this."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "asset_name": {"type": "string", "description": "The exact name of the existing asset this task is for."},
                    "title": {"type": "string", "description": "A short task title, e.g. 'Oil change', 'Renew tags'."},
                    "interval_days": {
                        "type": "integer",
                        "description": "Repeat every N days. Omit for a one-time task.",
                    },
                },
                "required": ["asset_name", "title"],
            },
            handler=self._action_add_maintenance_task,
            trigger_phrases=(
                "add a maintenance task", "schedule maintenance", "set up maintenance",
                "add an oil change", "maintenance task", "service reminder", "remind me to service",
                # Broadened from the too-narrow "remind me to change the
                # oil" — real phrasing inserts the asset's own name/
                # possessive between verb and noun ("remind me to
                # change my Truck's oil"), same class of gap as
                # delete_alarm's name-before-noun fix. A strict superset
                # of alarms' own bare "remind me" trigger, so this adds
                # no new false-positive surface beyond what that
                # already accepts.
                "remind me to change", "every months",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_maintenance_tasks",
            domain="maintenance",
            description=(
                "List MIA's maintenance tasks and their real due/overdue status, optionally filtered by a "
                "keyword matching the task title or asset name. Leave query empty to list everything."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to filter by task title or asset name."},
                },
                "required": [],
            },
            handler=self._action_list_maintenance_tasks,
            trigger_phrases=(
                "what maintenance is due", "what's due for maintenance", "list maintenance tasks",
                "what maintenance do i have", "is anything overdue", "maintenance status", "what needs maintenance",
                "what maintenance is overdue",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="complete_maintenance_task",
            domain="maintenance",
            description=(
                "Mark an EXISTING maintenance task complete/done in MIA by title, because the user is "
                "reporting they already did it (past tense — 'I renewed the tags', 'I changed the oil'). "
                "Optionally name the asset to disambiguate. Do NOT use this to set up a new task — use "
                "add_maintenance_task for that instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The task's title, e.g. 'Oil change'."},
                    "asset_name": {"type": "string", "description": "Optional — the asset's name, needed only if more than one asset has a same-titled task."},
                    "meter_value": {
                        "type": "number",
                        "description": "For a mileage/runtime/cycles/condition task, the meter reading at completion. Omit to use the latest logged reading.",
                    },
                },
                "required": ["title"],
            },
            handler=self._action_complete_maintenance_task,
            # No fixed phrase list can enumerate every task-specific way
            # to say "I did the thing" ("I renewed the tags", "I rotated
            # the tires", "I inspected the brakes", ...) — same real
            # limitation this registry already accepts for "note "
            # (core/application.py's delete_note trigger comment).
            # Covers the common maintenance completion verbs found via
            # live-model testing rather than guessing further ones.
            trigger_phrases=(
                "i changed the oil", "i finished the maintenance", "mark maintenance done",
                "completed the maintenance", "did the oil change", "serviced my", "maintenance complete",
                "finished servicing", "i renewed", "i replaced", "i repaired", "i rotated", "i inspected",
                "i fixed my", "just did the",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="log_maintenance_reading",
            domain="maintenance",
            description=(
                "Log a meter/sensor reading (mileage, engine hours, start count, a sensor value like battery "
                "voltage) for an existing mileage/runtime/cycles/condition/sensor-triggered maintenance task."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The task's title, e.g. 'Oil change'."},
                    "asset_name": {"type": "string", "description": "Optional — the asset's name, needed only if more than one asset has a same-titled task."},
                    "value": {"type": "number", "description": "The current reading value, e.g. 46000 for miles."},
                    "unit": {"type": "string", "description": "Optional unit, e.g. 'miles', 'hours', 'V'."},
                },
                "required": ["title", "value"],
            },
            handler=self._action_log_maintenance_reading,
            # Tried a bare "log " (trailing space) here to catch "Log
            # 46000 miles" (a real number always sits between "log" and
            # the unit, so no fixed compound can match it) — live-model
            # testing found it made an UNRELATED "I need to log off for
            # the night" gate open and hallucinate set_birthday. Reverted:
            # same accepted trade-off this registry already made for
            # "note " (too common a word to gate safely) — "log <value>
            # <unit>" with no other maintenance-specific wording is a
            # known, real gap, not silently assumed fixed.
            trigger_phrases=(
                "log the mileage", "log miles", "log a reading", "log the odometer",
                "update the mileage", "log engine hours", "log the voltage",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_maintenance_task",
            domain="maintenance",
            destructive=True,
            description="Delete a maintenance task in MIA by title (optionally naming the asset to disambiguate).",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The task's title to delete."},
                    "asset_name": {"type": "string", "description": "Optional — the asset's name, needed only if more than one asset has a same-titled task."},
                },
                "required": ["title"],
            },
            handler=self._action_delete_maintenance_task,
            trigger_phrases=("delete a maintenance task", "remove a maintenance task", "delete the maintenance task"),
        ))
        # --- Lab (Data Logger) — 2026-09-08, same audit that found
        # Maintenance had zero Assistant actions also flagged Lab
        # (modules/lab/module.py, core/data_logger_manager.py): manual
        # sensor/experiment reading entry, zero actions. A series_id is
        # an arbitrary freeform string (no separate registry file — see
        # that manager's own docstring), so "log a reading" here means
        # something genuinely different from Maintenance's version
        # (a specific tracked task's meter, resolved by title/asset) —
        # both tools' descriptions say so explicitly, same
        # disambiguation approach as every other legitimate multi-domain
        # collision in this registry.
        self.context.assistant_actions.register(AssistantAction(
            name="log_lab_reading",
            domain="lab",
            description=(
                "Log a manual sensor/experiment/measurement reading in MIA's Lab (Data Logger) under a "
                "named series (e.g. 'soil moisture', 'multimeter voltage', 'greenhouse temp') — general "
                "experiment/sensor-testing data. NOT for a specific tracked Maintenance task's mileage/"
                "engine hours/sensor value — use log_maintenance_reading for that instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "series": {"type": "string", "description": "The series name, e.g. 'soil moisture'."},
                    "value": {"type": "number", "description": "The reading's numeric value."},
                    "unit": {"type": "string", "description": "Optional unit, e.g. '%', 'V', 'F'."},
                    "note": {"type": "string", "description": "Optional note about this reading."},
                },
                "required": ["series", "value"],
            },
            handler=self._action_log_lab_reading,
            trigger_phrases=(
                "log a reading", "log a measurement", "log a value", "record a reading", "add a reading",
                "log this reading",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_lab_series",
            domain="lab",
            description="List every Data Logger series name in MIA's Lab module that has at least one logged reading.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_lab_series,
            # "data series" often has words inserted before "am i
            # logging" ("What data series am I logging in the Lab?") —
            # same name/noun-insertion gap as several other bare
            # triggers in this registry. Added narrower but still
            # distinctive compounds rather than a fully generic bare
            # "series" (too easy to collide with an unrelated "TV
            # series"/"a series of events").
            trigger_phrases=(
                "what series do i have", "list my data series", "what am i logging", "list lab series",
                "show my series", "what series", "data series", "my series",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_lab_readings",
            domain="lab",
            description="List the logged readings for one Data Logger series in MIA's Lab module, oldest first.",
            parameters={
                "type": "object",
                "properties": {
                    "series": {"type": "string", "description": "The series name to list readings for."},
                },
                "required": ["series"],
            },
            handler=self._action_list_lab_readings,
            trigger_phrases=("show me the readings for", "what are my readings for", "readings for", "history for", "show my data for"),
        ))
        # --- Budget (household bills, income, expenses) — 2026-09-08,
        # the second item from the same planning session that added
        # Property. Real collision risk, deliberately not evaded:
        # add_bill vs. add_maintenance_task (both "recurring thing due
        # on a schedule") — resolved via distinct descriptions, same
        # pattern already proven for the alarm/maintenance-task
        # collision, verified live rather than assumed safe.
        self.context.assistant_actions.register(AssistantAction(
            name="add_bill",
            domain="budget",
            description=(
                "Add a recurring or one-time household BILL (e.g. electric, mortgage, insurance) to MIA's "
                "Budget tracker — a dollar amount due on a schedule. NOT a Maintenance task (an asset's "
                "physical upkeep) — use add_maintenance_task for that instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. 'Electric', 'Mortgage'."},
                    "amount": {"type": "number", "description": "The bill amount in dollars."},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format."},
                    "category": {
                        "type": "string",
                        "description": f"One of: {', '.join(BUDGET_EXPENSE_CATEGORIES)}. Defaults to 'Utilities'.",
                    },
                    "recurrence": {
                        "type": "string",
                        "description": "Optional: 'yearly', 'monthly', or 'weekly' for a repeating bill. Leave empty for a one-time bill.",
                    },
                },
                "required": ["name", "amount", "due_date"],
            },
            handler=self._action_add_bill,
            # A bill's own descriptor word ("monthly", "electric") sits
            # between "add a"/"a" and "bill" in real phrasing ("Add a
            # monthly electric bill for $120") — same name-before-noun
            # gap as delete_alarm's "alarm " fix. Covers common bill-
            # type nouns directly rather than a fully bare "bill "
            # (too collision-prone — "foot the bill", "dollar bill").
            trigger_phrases=(
                "add a bill", "new bill", "track a bill", "add a household bill",
                "add my electric bill", "add my mortgage", "electric bill", "gas bill",
                "water bill", "utility bill", "internet bill", "add a bill for",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_bills",
            domain="budget",
            description="List MIA's household bills and their real due/overdue status, most urgent first.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_bills,
            trigger_phrases=(
                "list my bills", "what bills do i have", "what's due", "is anything overdue",
                "what bills are due", "show my bills",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="mark_bill_paid",
            domain="budget",
            description="Mark a household bill paid in MIA by name — records a real expense and advances a recurring bill's next due date.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The bill's name, e.g. 'Electric'."},
                    "amount": {"type": "number", "description": "Optional — the actual amount paid, if different from the bill's usual amount."},
                },
                "required": ["name"],
            },
            handler=self._action_mark_bill_paid,
            trigger_phrases=("i paid my", "paid the bill", "mark my bill paid", "mark the bill paid", "i paid the"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_income",
            domain="budget",
            description=(
                "When the user states a specific new dollar amount of income received (e.g. 'I got paid $3000', "
                "'record $1500 of rental income') and no specific property/address is mentioned, record general "
                "household income in MIA — salary, investment income, or rental income. A Workshop business sale "
                "uses record_sale instead. When a tracked recurring income source (e.g. 'my paycheck') arrives "
                "WITHOUT the user restating a dollar amount, use mark_income_received instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The income amount in dollars."},
                    "category": {"type": "string", "description": "One of: Salary, Rental Income, Investment, Other. Defaults to 'Other'."},
                    "description": {"type": "string", "description": "Optional description."},
                    "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format. Defaults to today."},
                },
                "required": ["amount"],
            },
            handler=self._action_add_income,
            # A dollar amount sits between "record"/"of" and "income" in
            # real phrasing ("Record $1500 of rental income") — same
            # name-before-noun gap as add_bill's fix above.
            trigger_phrases=(
                "record income", "add income", "i got paid", "received rent", "got my paycheck",
                "log my paycheck", "record my rental income", "rental income", "of income", "income of",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_expense",
            domain="budget",
            description="Record a household expense entry in MIA (groceries, car repair, etc.) — NOT a bill (a recurring scheduled obligation, use add_bill) and NOT a Workshop job cost.",
            parameters={
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The expense amount in dollars."},
                    "category": {"type": "string", "description": "One of: Utilities, Mortgage/Rent, Insurance, Groceries, Maintenance, Transportation, Taxes, Other. Defaults to 'Other'."},
                    "description": {"type": "string", "description": "Optional description."},
                    "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format. Defaults to today."},
                },
                "required": ["amount"],
            },
            handler=self._action_add_expense,
            trigger_phrases=("record an expense", "add an expense", "log an expense", "i spent", "bought groceries"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_budget_summary",
            domain="budget",
            description=(
                "When the user wants specific TOTALS or NUMBERS — how much income, how much spent, net cash flow, "
                "or tax-relevant subtotals — for a date range (e.g. this month, this year, or all time), get that "
                "here. For a general status question like 'how are we doing' or 'are we on budget' rather than a "
                "request for specific totals, use get_financial_checkin instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Optional start date, YYYY-MM-DD. Leave empty for no lower bound."},
                    "end_date": {"type": "string", "description": "Optional end date, YYYY-MM-DD. Leave empty for no upper bound."},
                },
                "required": [],
            },
            handler=self._action_get_budget_summary,
            trigger_phrases=(
                "budget summary", "how much have i spent", "how much did i make", "net cash flow",
                "my cash flow", "how much income", "tax summary",
            ),
        ))
        # --- Proactive nudges follow-up (2026-09-08): expected/recurring
        # income (IncomeSource) is a distinct concept from a one-off
        # add_income entry, so it needs its own action rather than
        # overloading add_income. Real collision risk with both add_income
        # (both take "amount") and add_bill (both take "amount" + a
        # schedule) — resolved by leading each description with the
        # condition that picks it ("a RECURRING/EXPECTED source" vs. "a
        # one-off actual" vs. "an obligation you OWE"), same positive/
        # condition-first phrasing this session's lesson established
        # (a negated description caused a real regression on add_income
        # vs. record_sale earlier this session — never repeat that).
        # list_income_sources/set_budget_target deliberately stay GUI-only
        # this pass, same stated scope limit as Real Estate's first slice.
        self.context.assistant_actions.register(AssistantAction(
            name="add_income_source",
            domain="budget",
            description=(
                "Add a RECURRING or EXPECTED income source to MIA — a paycheck, rental income, or other income "
                "that arrives on a schedule (a future expectation, not money already received). For income "
                "already received right now, use add_income instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. 'Paycheck', 'Rental — 123 Main St'."},
                    "expected_amount": {"type": "number", "description": "The expected amount in dollars."},
                    "next_date": {"type": "string", "description": "The next expected date in YYYY-MM-DD format."},
                    "category": {
                        "type": "string",
                        "description": f"One of: {', '.join(BUDGET_INCOME_CATEGORIES)}. Defaults to 'Salary'.",
                    },
                    "recurrence": {
                        "type": "string",
                        "description": "Optional: 'yearly', 'monthly', 'biweekly', or 'weekly' for a repeating income source. Leave empty for a one-time expectation.",
                    },
                },
                "required": ["name", "expected_amount", "next_date"],
            },
            handler=self._action_add_income_source,
            trigger_phrases=(
                "add an income source", "new income source", "track my paycheck", "add my paycheck",
                "set up my paycheck", "expect income", "track expected income", "add a recurring income source",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="mark_income_received",
            domain="budget",
            description=(
                "When a tracked, recurring income source (a paycheck, rent, or similar already set up in MIA) has "
                "arrived and the user does NOT restate a new dollar amount (e.g. 'my paycheck came in', 'got my "
                "paycheck', 'received my rent'), mark it received here by name — records a real income entry using "
                "the source's known expected amount and advances its next expected date. If the user states a new "
                "specific dollar amount instead, use add_income."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The income source's name, e.g. 'Paycheck'."},
                    "amount": {"type": "number", "description": "Optional — the actual amount received, if different from the expected amount."},
                },
                "required": ["name"],
            },
            handler=self._action_mark_income_received,
            trigger_phrases=(
                "got paid", "my paycheck came in", "received my paycheck", "mark my paycheck received",
                "i got my paycheck", "received my income",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_financial_checkin",
            domain="budget",
            description=(
                "When the user asks a general STATUS question about their finances — 'how are we doing "
                "financially', 'are we on budget', 'are we ok with money' — rather than asking for specific "
                "totals, get MIA's proactive financial check-in here: overdue/upcoming bills, when the next "
                "paycheck is expected and for how much, and any budget categories running over plan this month. "
                "For a request for specific totals (income, expenses, net cash flow, tax subtotals), use "
                "get_budget_summary instead."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_financial_checkin,
            trigger_phrases=(
                "financial check-in", "how are we doing financially", "are we on budget", "financial checkin",
                "how's our budget", "money check-in", "how are we doing with money",
            ),
        ))
        # --- Real Estate (property portfolio) — 2026-09-08, same
        # planning session as Property/Budget. record_rental_income
        # deliberately shares "rental income" vocabulary with Budget's
        # own add_income (both legitimately attach; disambiguated by
        # description — a property-scoped entry vs. a plain household
        # one — same collision-resolution pattern proven all session).
        self.context.assistant_actions.register(AssistantAction(
            name="add_property",
            domain="real_estate",
            description="Add a new real estate property to MIA's portfolio (value, mortgage balance, purchase info).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. '123 Main St', 'Lake Cabin'."},
                    "property_type": {"type": "string", "description": "One of: Primary Residence, Rental, Investment, Land, Other. Defaults to 'Rental'."},
                    "current_value": {"type": "number", "description": "Optional current estimated value in dollars."},
                    "mortgage_balance": {"type": "number", "description": "Optional current mortgage balance in dollars."},
                },
                "required": ["name"],
            },
            handler=self._action_add_property,
            trigger_phrases=("add a property", "new property", "add a rental property", "track a property", "add my house"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_properties",
            domain="real_estate",
            description="List every property in MIA's real estate portfolio with its equity (value minus mortgage).",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_properties,
            trigger_phrases=("list my properties", "what properties do i have", "show my properties", "my property portfolio"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="record_rental_income",
            domain="real_estate",
            # Known, accepted live-model limitation (llama3.2): "Record
            # rental income of $1800 for 123 Main St" — a named property
            # right in the sentence — still sometimes resolves to
            # add_income instead of this one. Tried three description
            # phrasings (negation-based, positive-only, condition-first,
            # this one) — the negation attempt actively regressed to
            # zero tool calls on unrelated cases, so it was reverted;
            # none of the three fully fixed this specific direction.
            # Non-destructive, low-impact when it happens (the income is
            # still recorded, just as a plain Budget entry instead of
            # linked to the property via property_id) — accepted rather
            # than chased further, same trade-off class as this
            # registry's "log " reversion.
            description=(
                "When a specific property/address (e.g. '123 Main St') is mentioned, record rental income "
                "for it in MIA's real estate portfolio by that property's name."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "property_name": {"type": "string", "description": "The exact name of the existing property."},
                    "amount": {"type": "number", "description": "The rental income amount in dollars."},
                    "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format. Defaults to today."},
                },
                "required": ["property_name", "amount"],
            },
            handler=self._action_record_rental_income,
            trigger_phrases=("record rental income for", "got rent for", "received rent for", "rent payment for"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_property_summary",
            domain="real_estate",
            description="Get net operating income, cap rate, and equity for one property in MIA's real estate portfolio, by name.",
            parameters={
                "type": "object",
                "properties": {
                    "property_name": {"type": "string", "description": "The exact name of the existing property."},
                },
                "required": ["property_name"],
            },
            handler=self._action_get_property_summary,
            # The property's own name sits between "my" and "property"
            # in real phrasing ("How is my 123 Main St property
            # doing?") — same name-before-noun gap as every other
            # trigger-phrase fix this session. "property doing" alone
            # (not the fuller "how is my property doing") survives that
            # insertion without resorting to a riskier bare "how is my".
            trigger_phrases=(
                "property summary", "how is my property doing", "cap rate for", "how much equity",
                "property doing",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="play_track",
            domain="music",
            description="Play a specific song from MIA's local music library, by title or artist.",
            parameters={
                "type": "object",
                "properties": {
                    "track_name": {"type": "string", "description": "Title or artist to search for."},
                },
                "required": ["track_name"],
            },
            handler=self._action_play_track,
            trigger_phrases=("play ", "play the song", "queue up"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="play_playlist",
            domain="music",
            description="Play one of MIA's saved music playlists, by name.",
            parameters={
                "type": "object",
                "properties": {
                    "playlist_name": {"type": "string", "description": "The exact name of the existing playlist."},
                },
                "required": ["playlist_name"],
            },
            handler=self._action_play_playlist,
            trigger_phrases=("play my playlist", "play the playlist", "play my music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="pause_music",
            domain="music",
            description="Pause the currently playing music.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_pause_music,
            trigger_phrases=("pause the music", "pause music", "pause the song"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="resume_music",
            domain="music",
            description="Resume/unpause the currently paused music.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_resume_music,
            trigger_phrases=("resume the music", "unpause the music", "continue playing", "resume music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="stop_music",
            domain="music",
            # Deliberately never a bare "stop" — that already means
            # "stop tracking" under the maintenance domain.
            description="Stop music playback entirely (clears the play queue, unlike pause).",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_stop_music,
            trigger_phrases=("stop the music", "stop playing", "stop the song", "stop music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="next_track",
            domain="music",
            description="Skip to the next track in the current music queue.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_next_track,
            trigger_phrases=("next song", "next track", "skip this song", "skip track"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="previous_track",
            domain="music",
            description="Go back to the previous track in the current music queue.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_previous_track,
            trigger_phrases=("previous song", "previous track", "go back a song"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="set_music_volume",
            domain="music",
            description="Set the music player's own playback volume (separate from the device's system volume).",
            parameters={
                "type": "object",
                "properties": {
                    "percent": {"type": "integer", "description": "Volume percent, 0-100."},
                },
                "required": ["percent"],
            },
            handler=self._action_set_music_volume,
            trigger_phrases=("music volume", "turn up the music", "turn down the music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_now_playing",
            domain="music",
            description="Get the title/artist and playback position of whatever song is currently playing.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_now_playing,
            trigger_phrases=("what's playing", "now playing", "what song is this", "what song is playing"),
        ))

    @staticmethod
    def _action_open_module(context: AppContext, arguments: dict) -> str:
        requested = str(arguments.get("module_id", "")).strip()
        module = context.module_manager.resolve(requested) if context.module_manager is not None else None
        if module is None:
            return f"There's no module called '{requested}'."
        # Published rather than calling MainWindow directly — this
        # handler can be invoked from any thread the LLM's reply
        # arrives on (see modules/assistant/module.py's docstring), and
        # MainWindow (a Qt widget) must only ever be touched from the
        # GUI thread.
        context.events.publish("assistant.open_module_requested", module_id=module.module_id)
        return f"Opening {module.display_name}."

    @staticmethod
    def _action_add_alarm(context: AppContext, arguments: dict) -> str:
        label = str(arguments.get("label", "") or "Alarm").strip() or "Alarm"
        time_str = str(arguments.get("time", "")).strip()
        if not time_str:
            return "I need a time (HH:MM) to set an alarm."
        alarm = context.alarms.add_alarm(label=label, time=time_str)
        return f"Alarm '{alarm.label}' set for {alarm.time}."

    @staticmethod
    def _action_list_alarms(context: AppContext, arguments: dict) -> str:
        alarms = context.alarms.all_alarms()
        if not alarms:
            return "You have no alarms set."
        lines = [f"- '{a.label}' at {a.time}" + ("" if a.enabled else " (disabled)") for a in alarms]
        return "Your alarms:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_alarm(context: AppContext, arguments: dict) -> str:
        label = str(arguments.get("label", "")).strip().lower()
        match = next((a for a in context.alarms.all_alarms() if a.label.lower() == label), None)
        if match is None:
            return f"I don't have an alarm called '{arguments.get('label', '')}'."
        context.alarms.delete_alarm(match.alarm_id)
        return f"Deleted the alarm '{match.label}'."

    @staticmethod
    def _action_add_note(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a title to add a note."
        body = str(arguments.get("body", ""))
        entry = context.journal.add_entry(title=title, body=body)
        return f"Note '{entry.title}' added."

    @staticmethod
    def _action_list_notes(context: AppContext, arguments: dict) -> str:
        """Returns raw entries (title + body) as plain text — same
        retrieve-then-let-the-LLM-answer shape as
        _action_recall_recent_activity, so the model can quote/summarize
        rather than this handler guessing what's relevant."""
        query = str(arguments.get("query", "") or "").strip()
        entries = context.journal.search(query) if query else context.journal.all_entries()
        if not entries:
            return "No matching notes found." if query else "You have no notes yet."
        lines = [f"- '{e.title}': {e.body}" if e.body else f"- '{e.title}'" for e in entries]
        return "Your notes:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_note(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip().lower()
        match = next((e for e in context.journal.all_entries() if e.title.lower() == title), None)
        if match is None:
            return f"I don't have a note titled '{arguments.get('title', '')}'."
        context.journal.delete_entry(match.entry_id)
        return f"Deleted the note '{match.title}'."

    @staticmethod
    def _action_add_inventory_item(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need an item name to add to inventory."
        try:
            quantity = int(arguments.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            quantity = 0
        item = context.inventory.add_item(name=name, quantity=quantity)
        return f"Added {item.quantity}x '{item.name}' to inventory."

    @staticmethod
    def _action_list_inventory(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").strip()
        items = context.inventory.search(query) if query else context.inventory.all_items()
        if not items:
            return "No matching inventory items found." if query else "Your inventory is empty."
        lines = [f"- {i.quantity}x '{i.name}'" for i in items]
        return "Your inventory:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_inventory_item(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((i for i in context.inventory.all_items() if i.name.lower() == name), None)
        if match is None:
            return f"I don't have an inventory item called '{arguments.get('name', '')}'."
        context.inventory.delete_item(match.item_id)
        return f"Removed '{match.name}' from inventory."

    @staticmethod
    def _action_adjust_inventory_quantity(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        try:
            delta = int(arguments.get("delta", 0) or 0)
        except (TypeError, ValueError):
            return "I need a whole number to adjust the quantity by."
        match = next((i for i in context.inventory.all_items() if i.name.lower() == name), None)
        if match is None:
            return f"I don't have an inventory item called '{arguments.get('name', '')}'."
        updated = context.inventory.adjust_quantity(match.item_id, delta)
        return f"'{updated.name}' is now {updated.quantity}."

    @staticmethod
    def _action_list_waypoints(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").lower().strip()
        waypoints = context.waypoints.all_waypoints()
        if query:
            waypoints = [w for w in waypoints if query in f"{w.name} {w.notes}".lower()]
        if not waypoints:
            return "No matching waypoints found." if query else "You have no waypoints saved."
        lines = [f"- '{w.name}' ({w.latitude:.5f}, {w.longitude:.5f})" for w in waypoints]
        return "Your waypoints:\n" + "\n".join(lines)

    @staticmethod
    def _action_waypoint_distance(context: AppContext, arguments: dict) -> str:
        from_name = str(arguments.get("from_name", "")).strip().lower()
        to_name = str(arguments.get("to_name", "")).strip().lower()
        waypoints = {w.name.lower(): w for w in context.waypoints.all_waypoints()}
        from_wp = waypoints.get(from_name)
        to_wp = waypoints.get(to_name)
        if from_wp is None:
            return f"I don't have a waypoint called '{arguments.get('from_name', '')}'."
        if to_wp is None:
            return f"I don't have a waypoint called '{arguments.get('to_name', '')}'."
        result = context.waypoints.distance_and_bearing(from_wp.waypoint_id, to_wp.waypoint_id)
        if result is None:
            return f"Couldn't compute a distance between '{from_wp.name}' and '{to_wp.name}'."
        distance_km, bearing = result
        return f"'{from_wp.name}' to '{to_wp.name}': {distance_km:.1f} km, bearing {bearing:.0f}°."

    @staticmethod
    def _action_list_trail_maps(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").lower().strip()
        trail_maps = context.trail_maps.all_trail_maps()
        if query:
            trail_maps = [t for t in trail_maps if query in f"{t.park_name} {t.state}".lower()]
        if not trail_maps:
            return "No matching trail maps found." if query else "You have no trail maps cataloged."
        lines = [f"- '{t.park_name}' ({t.state})" for t in trail_maps]
        return "Your trail maps:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_trail_map_from_url(context: AppContext, arguments: dict) -> str:
        park_name = str(arguments.get("park_name", "")).strip()
        state = str(arguments.get("state", "")).strip()
        url = str(arguments.get("url", "")).strip()
        notes = str(arguments.get("notes", "") or "")
        if not park_name or not state or not url:
            return "I need a park name, state, and URL to add a trail map."
        try:
            trail_map = context.trail_maps.add_from_url(park_name, state, url, notes=notes)
        except NotAPdfError:
            return f"The file at '{url}' doesn't look like a real trail map PDF — nothing was added."
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return f"Couldn't download that trail map: {exc}"
        return f"Added '{trail_map.park_name}' ({trail_map.state}) to your trail map catalog."

    @staticmethod
    def _action_delete_trail_map(context: AppContext, arguments: dict) -> str:
        park_name = str(arguments.get("park_name", "")).strip().lower()
        match = next((t for t in context.trail_maps.all_trail_maps() if t.park_name.lower() == park_name), None)
        if match is None:
            return f"I don't have a trail map called '{arguments.get('park_name', '')}'."
        context.trail_maps.delete_trail_map(match.trail_map_id)
        return f"Deleted the trail map for '{match.park_name}'."

    @staticmethod
    def _action_convert_units(context: AppContext, arguments: dict) -> str:
        from modules.toolbox.calculators.unit_converter import UNIT_CATEGORIES, convert, resolve_unit_key

        from_text = str(arguments.get("from_unit", "")).strip()
        to_text = str(arguments.get("to_unit", "")).strip()
        if not from_text or not to_text:
            return "I need both a 'from' and 'to' unit to convert."
        try:
            value = float(arguments.get("value"))
        except (TypeError, ValueError):
            return "I need a numeric value to convert."

        for category, units in UNIT_CATEGORIES.items():
            from_key = resolve_unit_key(units, from_text)
            to_key = resolve_unit_key(units, to_text)
            if from_key is not None and to_key is not None:
                result = convert(category, from_key, to_key, value)
                return f"{value:g} {from_key} = {result:.4g} {to_key}"
        return f"I don't recognize '{from_text}' and/or '{to_text}' as units I can convert between."

    @staticmethod
    def _action_calculate_ohms_law(context: AppContext, arguments: dict) -> str:
        from modules.toolbox.calculators.ohms_law import solve

        solve_for = str(arguments.get("solve_for", "")).strip().lower()
        if solve_for not in ("voltage", "current", "resistance"):
            return "I need to know which value to solve for: voltage, current, or resistance."

        def _optional_float(key: str):
            raw = arguments.get(key)
            if raw is None or raw == "":
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        voltage = _optional_float("voltage")
        current = _optional_float("current")
        resistance = _optional_float("resistance")
        try:
            result = solve(solve_for, voltage, current, resistance)
        except (TypeError, ZeroDivisionError):
            return f"I need the other two values (not {solve_for}) to solve this."
        units = {"voltage": "V", "current": "A", "resistance": "Ω"}
        return f"{solve_for.capitalize()} = {result:.4g} {units[solve_for]}"

    @staticmethod
    def _action_delete_waypoint(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((w for w in context.waypoints.all_waypoints() if w.name.lower() == name), None)
        if match is None:
            return f"I don't have a waypoint called '{arguments.get('name', '')}'."
        context.waypoints.delete_waypoint(match.waypoint_id)
        return f"Deleted the waypoint '{match.name}'."

    @staticmethod
    def _action_get_sun_moon_info(context: AppContext, arguments: dict) -> str:
        from datetime import date as _date

        from modules.navigation.module import format_sun_moon_summary

        name = str(arguments.get("waypoint_name", "")).strip().lower()
        match = next((w for w in context.waypoints.all_waypoints() if w.name.lower() == name), None)
        if match is None:
            return f"I don't have a waypoint called '{arguments.get('waypoint_name', '')}'."
        summary = format_sun_moon_summary(match.latitude, match.longitude, _date.today())
        return f"For '{match.name}': {summary}"

    @staticmethod
    def _action_get_system_health(context: AppContext, arguments: dict) -> str:
        return format_system_health(read_system_health())

    @staticmethod
    def _action_recall_recent_activity(context: AppContext, arguments: dict) -> str:
        """
        Fetches raw recent activity log entries as plain text — no
        attempt at natural-language date parsing ("yesterday", "last
        week") here. Letting the LLM read the raw entries (each already
        timestamped) and phrase its own answer keeps this simple and
        testable, same reasoning as core/device_help_manager.py's
        retrieval-then-let-the-LLM-answer shape.
        """
        keyword = str(arguments.get("keyword", "") or "").strip()
        try:
            limit = int(arguments.get("limit", 20) or 20)
        except (TypeError, ValueError):
            limit = 20

        entries = context.activity_log.search(keyword, limit=limit) if keyword else context.activity_log.recent(limit)
        if not entries:
            return "No matching recent activity found." if keyword else "No recent activity recorded yet."

        lines = [f"{e.timestamp.replace('T', ' ')} — {e.summary}" for e in entries]
        return "\n".join(lines)

    @staticmethod
    def _action_add_waypoint(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to save a waypoint."
        try:
            latitude = float(arguments.get("latitude"))
            longitude = float(arguments.get("longitude"))
        except (TypeError, ValueError):
            return "I need a valid latitude and longitude to save a waypoint."
        category = str(arguments.get("category", "") or "").strip()
        if category not in WAYPOINT_CATEGORIES:
            category = ""  # unrecognized value -> uncategorized, same fail-safe as the UI's blank option
        waypoint = context.waypoints.add_waypoint(name=name, latitude=latitude, longitude=longitude, category=category)
        return f"Waypoint '{waypoint.name}' saved at ({waypoint.latitude:.5f}, {waypoint.longitude:.5f})."

    @staticmethod
    def _action_add_expedition(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start an expedition."
        start_date = str(arguments.get("start_date", "") or "").strip()
        location = str(arguments.get("location", "") or "").strip()
        expedition = context.expeditions.add_expedition(name=name, start_date=start_date, location=location)
        return f"Expedition '{expedition.name}' created."

    @staticmethod
    def _action_list_expeditions(context: AppContext, arguments: dict) -> str:
        expeditions = context.expeditions.all_expeditions()
        if not expeditions:
            return "You have no expeditions yet."
        lines = []
        for expedition in expeditions:
            date_part = f" ({expedition.start_date})" if expedition.start_date else ""
            location_part = f" — {expedition.location}" if expedition.location else ""
            lines.append(f"- '{expedition.name}'{date_part}{location_part}")
        return "Your expeditions:\n" + "\n".join(lines)

    @staticmethod
    def _action_recall_expedition(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "") or "").strip().lower()
        if name:
            expedition = next(
                (e for e in context.expeditions.all_expeditions() if e.name.lower() == name), None
            )
            if expedition is None:
                return f"I don't have an expedition called '{arguments.get('name', '')}'."
            recap = context.memories.recap_for_expedition(expedition.expedition_id)
        else:
            recaps = context.memories.all_recaps()
            if not recaps:
                return "You have no expeditions yet."
            recap = recaps[0]

        lines = [f"'{recap.expedition.name}'"]
        if recap.expedition.location:
            lines.append(f"Location: {recap.expedition.location}")
        if recap.duration_days:
            lines.append(f"Duration: {recap.duration_days} day{'s' if recap.duration_days != 1 else ''}")
        for stats in recap.activity_breakdown.values():
            parts = [f"{stats.trip_count} trip(s)"]
            if stats.distance_km:
                parts.append(f"{stats.distance_km:.1f} km")
            if stats.average_speed_kmh:
                parts.append(f"avg {stats.average_speed_kmh:.1f} km/h")
            lines.append(f"{stats.activity_type}: " + ", ".join(parts))
        if recap.waypoint_categories_visited:
            categories = ", ".join(
                f"{count} {category}" for category, count in sorted(recap.waypoint_categories_visited.items())
            )
            lines.append(f"Visited: {categories}")
        if recap.journal_highlights:
            latest = recap.journal_highlights[0]
            conditions = f" ({latest.conditions})" if latest.conditions else ""
            lines.append(f"Latest log: '{latest.title}'{conditions}")
        if recap.photo_count:
            lines.append(f"Photos: {recap.photo_count}")
        return "\n".join(lines)

    @staticmethod
    def _action_add_trip(context: AppContext, arguments: dict) -> str:
        expedition_name = str(arguments.get("expedition_name", "")).strip().lower()
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a trip."
        expedition = next(
            (e for e in context.expeditions.all_expeditions() if e.name.lower() == expedition_name), None
        )
        if expedition is None:
            return f"I don't have an expedition called '{arguments.get('expedition_name', '')}'."
        activity_type = str(arguments.get("activity_type", "") or "").strip()
        if activity_type not in ACTIVITY_TYPES:
            activity_type = ""
        start_date = str(arguments.get("start_date", "") or "").strip()
        trip = context.trips.add_trip(
            expedition_id=expedition.expedition_id, name=name, activity_type=activity_type, start_date=start_date,
        )
        return f"Trip '{trip.name}' added under expedition '{expedition.name}'."

    @staticmethod
    def _action_list_trips(context: AppContext, arguments: dict) -> str:
        expedition_name = str(arguments.get("expedition_name", "") or "").strip().lower()
        if expedition_name:
            expedition = next(
                (e for e in context.expeditions.all_expeditions() if e.name.lower() == expedition_name), None
            )
            if expedition is None:
                return f"I don't have an expedition called '{arguments.get('expedition_name', '')}'."
            trips = context.trips.trips_for_expedition(expedition.expedition_id)
        else:
            trips = context.trips.all_trips()

        if not trips:
            return "No matching trips found." if expedition_name else "You have no trips yet."
        lines = []
        for trip in trips:
            activity_part = f" [{trip.activity_type}]" if trip.activity_type else ""
            lines.append(f"-{activity_part} '{trip.name}' ({trip.status})")
        return "Your trips:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_gear_item(context: AppContext, arguments: dict) -> str:
        trip_name = str(arguments.get("trip_name", "")).strip().lower()
        label = str(arguments.get("label", "")).strip()
        if not label:
            return "I need a gear item name to add it to a trip's checklist."
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
        context.trips.add_gear_item(trip.trip_id, label=label)
        return f"Added '{label}' to the gear checklist for '{trip.name}'."

    @staticmethod
    def _action_add_trip_log_entry(context: AppContext, arguments: dict) -> str:
        trip_name = str(arguments.get("trip_name", "")).strip().lower()
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a title to add a trip log entry."
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
        body = str(arguments.get("body", "") or "")
        conditions = str(arguments.get("conditions", "") or "")
        context.journal.add_entry(title=title, body=body, trip_id=trip.trip_id, conditions=conditions)
        return f"Log entry '{title}' added to '{trip.name}'."

    @staticmethod
    def _action_delete_expedition(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((e for e in context.expeditions.all_expeditions() if e.name.lower() == name), None)
        if match is None:
            return f"I don't have an expedition called '{arguments.get('name', '')}'."
        context.expeditions.delete_expedition(match.expedition_id)
        return f"Deleted the expedition '{match.name}'."

    @staticmethod
    def _action_delete_trip(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((t for t in context.trips.all_trips() if t.name.lower() == name), None)
        if match is None:
            return f"I don't have a trip called '{arguments.get('name', '')}'."
        context.trips.delete_trip(match.trip_id)
        return f"Deleted the trip '{match.name}'."

    @staticmethod
    def _action_toggle_gear_packed(context: AppContext, arguments: dict) -> str:
        trip_name = str(arguments.get("trip_name", "")).strip().lower()
        label = str(arguments.get("label", "")).strip().lower()
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
        index = next((i for i, g in enumerate(trip.gear) if g.label.lower() == label), None)
        if index is None:
            return f"'{trip.name}' has no gear item called '{arguments.get('label', '')}'."
        updated = context.trips.toggle_gear_packed(trip.trip_id, index)
        item = updated.gear[index]
        state = "packed" if item.packed else "not packed"
        return f"'{item.label}' on '{trip.name}' is now marked {state}."

    @staticmethod
    def _action_get_trip_summary(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('name', '')}'."
        lines = [f"'{trip.name}':"]
        distance = context.trips.total_distance_km(trip.trip_id)
        if distance is not None:
            lines.append(f"- Logged distance: {distance:.1f} km")
        speed = context.trips.average_speed_kmh(trip.trip_id)
        if speed is not None:
            lines.append(f"- Average speed: {speed:.1f} km/h")
        planned = context.trips.planned_route_distance_km(trip.trip_id)
        if planned is not None:
            lines.append(f"- Planned route distance: {planned:.1f} km")
        if len(lines) == 1:
            lines.append("- No distance/speed data logged for this trip yet.")
        return "\n".join(lines)

    @staticmethod
    def _action_get_device_profile(context: AppContext, arguments: dict) -> str:
        profile = get_device_profile(context)
        label = "Core (Pi 5 + AI HAT+ 2 field edition)" if profile == CORE else "Home (desktop workstation edition)"
        return f"This device is running the {label}."

    @staticmethod
    def _action_set_birthday(context: AppContext, arguments: dict) -> str:
        birthday = str(arguments.get("birthday", "")).strip()
        try:
            datetime.fromisoformat(birthday)
        except ValueError:
            return "I need a birthday in YYYY-MM-DD format to remember it."
        active_profile = context.profiles.get_active_profile() if context.profiles is not None else None
        if active_profile is None:
            return "I don't have an active user profile to save that to."
        context.profiles.set_birthday(active_profile.profile_id, birthday)
        return f"Got it — I'll remember your birthday is {birthday}."

    @staticmethod
    def _action_set_theme(context: AppContext, arguments: dict) -> str:
        theme_id = str(arguments.get("theme_id", "")).strip().lower()
        if theme_id not in THEMES:
            valid = ", ".join(THEMES.keys())
            return f"'{arguments.get('theme_id', '')}' isn't a theme I know. Valid themes: {valid}."
        context.config.set("gui.theme", theme_id)
        context.config.save()
        context.events.publish("theme.changed", theme_id=theme_id)
        return f"Theme changed to {THEME_DISPLAY_NAMES[theme_id]}."

    @staticmethod
    def _action_add_calendar_event(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip()
        date_str = str(arguments.get("date", "") or "").strip()
        if not title:
            return "I need a title to add a calendar event."
        if not date_str:
            return "I need a date (YYYY-MM-DD) to add a calendar event."
        time_str = str(arguments.get("time", "") or "").strip() or None
        notes = str(arguments.get("notes", "") or "")
        recurrence = str(arguments.get("recurrence", "") or "").strip().lower() or None
        if recurrence not in (None, *CALENDAR_RECURRENCE_TYPES):
            recurrence = None
        event = context.calendar.add_event(title=title, date=date_str, time=time_str, notes=notes, recurrence=recurrence)
        time_part = f" at {event.time}" if event.time else ""
        recurrence_part = f", repeating {event.recurrence}" if event.recurrence else ""
        return f"Calendar event '{event.title}' added for {event.date}{time_part}{recurrence_part}."

    @staticmethod
    def _action_list_calendar_events(context: AppContext, arguments: dict) -> str:
        events = context.calendar.all_events()
        if not events:
            return "You have no calendar events."
        lines = [
            f"- '{e.title}' on {e.date}" + (f" at {e.time}" if e.time else "") + (f" (repeats {e.recurrence})" if e.recurrence else "")
            for e in events
        ]
        return "Your calendar events:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_calendar_event(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip().lower()
        match = next((e for e in context.calendar.all_events() if e.title.lower() == title), None)
        if match is None:
            return f"I don't have a calendar event called '{arguments.get('title', '')}'."
        context.calendar.delete_event(match.event_id)
        return f"Deleted the calendar event '{match.title}'."

    @staticmethod
    def _action_get_power_status(context: AppContext, arguments: dict) -> str:
        status = context.power.read()
        if status is None:
            return "No battery or power status is available on this device."
        plugged = "plugged in" if status.plugged_in else "on battery"
        time_part = ""
        if status.seconds_left is not None:
            time_part = f", about {status.seconds_left // 60} minutes remaining"
        return f"Battery: {status.percent:.0f}% ({plugged}{time_part})."

    @staticmethod
    def _action_add_component(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a component."
        category = str(arguments.get("category", "") or "").strip()
        value = str(arguments.get("value", "") or "").strip()
        package = str(arguments.get("package", "") or "").strip()
        try:
            quantity = int(arguments.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            quantity = 0
        location = str(arguments.get("location", "") or "").strip()
        component = context.components.add_component(
            name=name, category=category, value=value, package=package, quantity=quantity, location=location,
        )
        return f"Component '{component.name}' added (qty {component.quantity})."

    @staticmethod
    def _action_list_components(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").strip()
        components = context.components.search(query) if query else context.components.all_components()
        if not components:
            return "No matching components found." if query else "You have no components saved."
        lines = [f"- '{c.name}' qty {c.quantity}" + (f" ({c.category})" if c.category else "") for c in components]
        return "Your components:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_component(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((c for c in context.components.all_components() if c.name.lower() == name), None)
        if match is None:
            return f"I don't have a component called '{arguments.get('name', '')}'."
        context.components.delete_component(match.component_id)
        return f"Deleted the component '{match.name}'."

    @staticmethod
    def _action_add_material(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a material."
        unit = str(arguments.get("unit", "") or "").strip()
        try:
            quantity_on_hand = float(arguments.get("quantity_on_hand", 0) or 0)
        except (TypeError, ValueError):
            quantity_on_hand = 0.0
        material = context.materials.add_material(name=name, unit=unit, quantity_on_hand=quantity_on_hand)
        return f"Material '{material.name}' added (qty {material.quantity_on_hand:g}{' ' + unit if unit else ''})."

    @staticmethod
    def _action_list_materials(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").strip()
        materials = context.materials.search(query) if query else context.materials.all_materials()
        if not materials:
            return "No matching materials found." if query else "You have no materials saved."
        lines = [f"- '{m.name}': {m.quantity_on_hand:g}{' ' + m.unit if m.unit else ''} on hand" for m in materials]
        return "Your materials:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_product(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a product."
        try:
            quantity_in_stock = float(arguments.get("quantity_in_stock", 0) or 0)
        except (TypeError, ValueError):
            quantity_in_stock = 0.0
        try:
            base_price = float(arguments.get("base_price", 0) or 0)
        except (TypeError, ValueError):
            base_price = 0.0
        product = context.products.add_product(name=name, quantity_in_stock=quantity_in_stock, base_price=base_price)
        return f"Product '{product.name}' added (qty {product.quantity_in_stock:g})."

    @staticmethod
    def _action_list_products(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").strip()
        products = context.products.search(query) if query else context.products.all_products()
        if not products:
            return "No matching products found." if query else "You have no products saved."
        lines = [f"- '{p.name}': {p.quantity_in_stock:g} in stock" for p in products]
        return "Your products:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_job(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start a job."
        description = str(arguments.get("description", "") or "").strip()
        job = context.jobs.add_job(name=name, description=description)
        return f"Job '{job.name}' started (status {job.status})."

    @staticmethod
    def _action_list_jobs(context: AppContext, arguments: dict) -> str:
        jobs = context.jobs.all_jobs()
        if not jobs:
            return "You have no jobs yet."
        return "Your jobs:\n" + "\n".join(f"- '{j.name}' ({j.status})" for j in jobs)

    @staticmethod
    def _action_consume_material(context: AppContext, arguments: dict) -> str:
        job_name = str(arguments.get("job_name", "")).strip().lower()
        material_name = str(arguments.get("material_name", "")).strip().lower()
        job = next((j for j in context.jobs.all_jobs() if j.name.lower() == job_name), None)
        if job is None:
            return f"I don't have a job called '{arguments.get('job_name', '')}'."
        material = next((m for m in context.materials.all_materials() if m.name.lower() == material_name), None)
        if material is None:
            return f"I don't have a material called '{arguments.get('material_name', '')}'."
        try:
            quantity = float(arguments.get("quantity", 0))
        except (TypeError, ValueError):
            return "I need a numeric quantity to record material use."
        context.jobs.consume_material(job.job_id, material.material_id, quantity)
        return f"Recorded {quantity:g} of '{material.name}' used on job '{job.name}'."

    @staticmethod
    def _action_produce_product(context: AppContext, arguments: dict) -> str:
        job_name = str(arguments.get("job_name", "")).strip().lower()
        product_name = str(arguments.get("product_name", "")).strip().lower()
        job = next((j for j in context.jobs.all_jobs() if j.name.lower() == job_name), None)
        if job is None:
            return f"I don't have a job called '{arguments.get('job_name', '')}'."
        product = next((p for p in context.products.all_products() if p.name.lower() == product_name), None)
        if product is None:
            return f"I don't have a product called '{arguments.get('product_name', '')}'."
        try:
            quantity = float(arguments.get("quantity", 0))
        except (TypeError, ValueError):
            return "I need a numeric quantity to record production."
        context.jobs.produce_product(job.job_id, product.product_id, quantity)
        return f"Recorded {quantity:g} of '{product.name}' produced by job '{job.name}'."

    @staticmethod
    def _action_record_sale(context: AppContext, arguments: dict) -> str:
        product_name = str(arguments.get("product_name", "")).strip().lower()
        product = next((p for p in context.products.all_products() if p.name.lower() == product_name), None)
        if product is None:
            return f"I don't have a product called '{arguments.get('product_name', '')}'."
        try:
            quantity = float(arguments.get("quantity", 0))
            amount = float(arguments.get("amount", 0))
        except (TypeError, ValueError):
            return "I need a numeric quantity and sale amount to record a sale."
        context.ledger.record_sale(product.product_id, quantity, amount)
        return f"Recorded a sale of {quantity:g} '{product.name}' for ${amount:.2f}."

    @staticmethod
    def _action_get_ledger_summary(context: AppContext, arguments: dict) -> str:
        revenue = context.ledger.total_revenue()
        expenses = context.ledger.total_expenses()
        profit = context.ledger.net_profit()
        return f"Total revenue: ${revenue:.2f}. Total expenses: ${expenses:.2f}. Net profit: ${profit:.2f}."

    @staticmethod
    def _action_list_connected_devices(context: AppContext, arguments: dict) -> str:
        block_devices = context.devices.list_block_devices()
        serial_devices = context.devices.list_serial_devices()
        if not block_devices and not serial_devices:
            return "No external devices are currently connected."
        lines = [f"- {d.display_name} (storage)" for d in block_devices]
        lines += [f"- {d.display_name} (serial)" for d in serial_devices]
        return "Connected devices:\n" + "\n".join(lines)

    @staticmethod
    def _action_list_scripts(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").strip()
        scripts = context.scripts.search(query) if query else context.scripts.all_scripts()
        if not scripts:
            return "No matching scripts found." if query else "You have no saved scripts."
        lines = [f"- '{s.name}'" + (f" [{s.category}]" if s.category else "") + f" ({s.interpreter})" for s in scripts]
        return "Your scripts:\n" + "\n".join(lines)

    @staticmethod
    def _action_list_profiles(context: AppContext, arguments: dict) -> str:
        profiles = context.profiles.list_profiles()
        if not profiles:
            return "No profiles are set up on this device."
        active = context.profiles.get_active_profile()
        lines = []
        for profile in profiles:
            marker = " (active)" if active is not None and profile.profile_id == active.profile_id else ""
            lock = " \U0001F512" if profile.has_password else ""
            lines.append(f"- '{profile.name}'{marker}{lock}")
        return "Profiles on this device:\n" + "\n".join(lines)

    @staticmethod
    def _action_identify_hash(context: AppContext, arguments: dict) -> str:
        value = str(arguments.get("value", "")).strip()
        if not value:
            return "I need a hash value to identify."
        candidates = identify_hash(value)
        if not candidates:
            return "No known hash format matched."
        return "Possible format(s): " + ", ".join(candidates)

    @staticmethod
    def _action_check_password_strength(context: AppContext, arguments: dict) -> str:
        password = str(arguments.get("password", ""))
        if not password:
            return "I need a password to check."
        result = assess_password(password)
        lines = [f"Strength: {result.rating} ({result.entropy_bits:.1f} bits)"]
        lines.extend(result.warnings)
        return "\n".join(lines)

    @staticmethod
    def _action_calculate_subnet(context: AppContext, arguments: dict) -> str:
        cidr = str(arguments.get("cidr", "")).strip()
        if not cidr:
            return "I need a CIDR, e.g. '192.168.1.0/24', to calculate a subnet."
        try:
            info = calculate_subnet(cidr)
        except ValueError as exc:
            return f"Invalid CIDR: {exc}"
        lines = [
            f"Network: {info.network_address}/{info.prefix_length}",
            f"Broadcast: {info.broadcast_address}",
            f"Netmask: {info.netmask}",
            f"Total addresses: {info.total_addresses}",
            f"Usable hosts: {info.usable_host_count}",
        ]
        if info.first_usable:
            lines.append(f"Usable range: {info.first_usable} - {info.last_usable}")
        return "\n".join(lines)

    @staticmethod
    def _action_scan_ports(context: AppContext, arguments: dict) -> str:
        host = str(arguments.get("host", "")).strip()
        if not host:
            return "I need a host or IP to scan."
        result = scan_ports(host, ports=list(_ASSISTANT_SCAN_PORTS), timeout=_ASSISTANT_SCAN_TIMEOUT_SECONDS)
        if result.error:
            return result.error
        ports_checked = ", ".join(str(p) for p in _ASSISTANT_SCAN_PORTS)
        if not result.open_ports:
            return f"No open ports found among the common ports checked ({ports_checked})."
        ports_open = ", ".join(str(p) for p in result.open_ports)
        return f"Open ports on {host}: {ports_open} (checked {ports_checked})."

    @staticmethod
    def _action_add_project(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start a project."
        status = str(arguments.get("status", "") or "").strip()
        if status not in PROJECT_STATUSES:
            status = "Planning"
        due_date = str(arguments.get("due_date", "") or "").strip()
        project = context.projects.add_project(name=name, status=status, due_date=due_date)
        return f"Project '{project.name}' created."

    @staticmethod
    def _action_list_projects(context: AppContext, arguments: dict) -> str:
        projects = context.projects.all_projects()
        if not projects:
            return "You have no projects yet."
        lines = []
        for project in projects:
            due_part = f" (due {project.due_date})" if project.due_date else ""
            lines.append(f"- '{project.name}' [{project.status}]{due_part}")
        return "Your projects:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_task(context: AppContext, arguments: dict) -> str:
        project_name = str(arguments.get("project_name", "")).strip().lower()
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a title to add a task."
        project = next(
            (p for p in context.projects.all_projects() if p.name.lower() == project_name), None
        )
        if project is None:
            return f"I don't have a project called '{arguments.get('project_name', '')}'."
        due_date = str(arguments.get("due_date", "") or "").strip()
        task = context.tasks.add_task(project_id=project.project_id, title=title, due_date=due_date)
        return f"Task '{task.title}' added under project '{project.name}'."

    @staticmethod
    def _action_list_tasks(context: AppContext, arguments: dict) -> str:
        project_name = str(arguments.get("project_name", "") or "").strip().lower()
        if project_name:
            project = next(
                (p for p in context.projects.all_projects() if p.name.lower() == project_name), None
            )
            if project is None:
                return f"I don't have a project called '{arguments.get('project_name', '')}'."
            tasks = context.tasks.tasks_for_project(project.project_id)
        else:
            tasks = context.tasks.all_tasks()

        if not tasks:
            return "No matching tasks found." if project_name else "You have no tasks yet."
        lines = []
        for task in tasks:
            mark = "[x]" if task.done else "[ ]"
            due_part = f" (due {task.due_date})" if task.due_date else ""
            lines.append(f"- {mark} '{task.title}'{due_part}")
        return "Your tasks:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_project(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((p for p in context.projects.all_projects() if p.name.lower() == name), None)
        if match is None:
            return f"I don't have a project called '{arguments.get('name', '')}'."
        context.projects.delete_project(match.project_id)
        return f"Deleted the project '{match.name}'."

    @staticmethod
    def _action_delete_task(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip().lower()
        match = next((t for t in context.tasks.all_tasks() if t.title.lower() == title), None)
        if match is None:
            return f"I don't have a task called '{arguments.get('title', '')}'."
        context.tasks.delete_task(match.task_id)
        return f"Deleted the task '{match.title}'."

    @staticmethod
    def _action_mark_task_done(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip().lower()
        match = next((t for t in context.tasks.all_tasks() if t.title.lower() == title), None)
        if match is None:
            return f"I don't have a task called '{arguments.get('title', '')}'."
        done = bool(arguments.get("done", True))
        context.tasks.update_task(match.task_id, done=done)
        status = "done" if done else "not done"
        return f"Marked the task '{match.title}' as {status}."

    @staticmethod
    def _action_add_mission(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start a mission."
        trip_name = str(arguments.get("trip_name", "") or "").strip().lower()
        trip_id = None
        if trip_name:
            trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
            if trip is None:
                return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
            trip_id = trip.trip_id
        mission = context.missions.add_mission(name=name, trip_id=trip_id)
        linked_note = f" Linked to trip '{trip.name}'." if trip_id else ""
        return f"Mission '{mission.name}' created.{linked_note}"

    @staticmethod
    def _action_list_missions(context: AppContext, arguments: dict) -> str:
        missions = context.missions.all_missions()
        if not missions:
            return "You have no missions yet."
        lines = []
        for mission in missions:
            lines.append(f"- '{mission.name}' ({mission.status})")
            for index, objective in enumerate(mission.objectives):
                progress = context.missions.objective_progress(mission.mission_id, index) or 0.0
                mark = "x" if context.missions.is_objective_complete(mission.mission_id, index) else " "
                lines.append(f"    [{mark}] {objective.description}: {progress:g} of {objective.target:g}")
        return "Your missions:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_objective(context: AppContext, arguments: dict) -> str:
        mission_name = str(arguments.get("mission_name", "")).strip().lower()
        description = str(arguments.get("description", "")).strip()
        if not description:
            return "I need a description to add an objective."
        mission = next((m for m in context.missions.all_missions() if m.name.lower() == mission_name), None)
        if mission is None:
            return f"I don't have a mission called '{arguments.get('mission_name', '')}'."
        metric_type = str(arguments.get("metric_type", "") or "tally").strip()
        if metric_type not in MISSION_METRIC_TYPES:
            metric_type = "tally"
        try:
            target = float(arguments.get("target", 1))
        except (TypeError, ValueError):
            return "I need a numeric target for this objective."
        context.missions.add_objective(mission.mission_id, description, metric_type, target)
        return f"Objective '{description}' added to mission '{mission.name}'."

    @staticmethod
    def _action_log_mission_progress(context: AppContext, arguments: dict) -> str:
        mission_name = str(arguments.get("mission_name", "")).strip().lower()
        mission = next((m for m in context.missions.all_missions() if m.name.lower() == mission_name), None)
        if mission is None:
            return f"I don't have a mission called '{arguments.get('mission_name', '')}'."

        tally_objectives = [(i, o) for i, o in enumerate(mission.objectives) if o.metric_type == "tally"]
        objective_description = str(arguments.get("objective_description", "") or "").strip().lower()
        if objective_description:
            match_index = next((i for i, o in tally_objectives if o.description.lower() == objective_description), None)
            if match_index is None:
                return f"I don't have a tally objective called '{arguments.get('objective_description', '')}' on mission '{mission.name}'."
        elif len(tally_objectives) == 1:
            match_index = tally_objectives[0][0]
        else:
            return f"Mission '{mission.name}' has {len(tally_objectives)} tally objectives — tell me which one."

        delta = float(arguments.get("delta", 1) or 1)
        context.missions.increment_tally(mission.mission_id, match_index, delta=delta)
        new_progress = context.missions.objective_progress(mission.mission_id, match_index)
        objective = mission.objectives[match_index]
        done_note = " Objective complete!" if context.missions.is_objective_complete(mission.mission_id, match_index) else ""
        return f"Logged progress on '{objective.description}': {new_progress:g} of {objective.target:g}.{done_note}"

    @staticmethod
    def _action_delete_mission(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((m for m in context.missions.all_missions() if m.name.lower() == name), None)
        if match is None:
            return f"I don't have a mission called '{arguments.get('name', '')}'."
        context.missions.delete_mission(match.mission_id)
        return f"Deleted the mission '{match.name}'."

    @staticmethod
    def _action_complete_mission(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((m for m in context.missions.all_missions() if m.name.lower() == name), None)
        if match is None:
            return f"I don't have a mission called '{arguments.get('name', '')}'."
        context.missions.update_mission(match.mission_id, status="completed")
        return f"Marked the mission '{match.name}' as completed. Nice work!"

    # ------------------------------------------------------------------
    # Maintenance actions — see the registration block's comment above
    # for the collision-risk/scope-limitation reasoning.
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_maintenance_task(context: AppContext, title: str, asset_name: str) -> tuple[Optional[MaintenanceTask], Optional[str]]:
        """Exact case-insensitive title match, optionally narrowed by
        asset name — never fuzzy, same fail-closed name-resolution
        discipline as every other write/destructive action in this
        registry. Returns (task, None) on a unique match, or
        (None, error_message) otherwise — including "multiple assets
        share this task title," which asks the user to disambiguate
        rather than guessing which one they meant."""
        candidates = [t for t in context.maintenance.all_tasks() if t.title.lower() == title.lower()]
        if asset_name:
            asset = next((a for a in context.maintenance.all_assets() if a.name.lower() == asset_name.lower()), None)
            if asset is None:
                return None, f"I don't have a maintenance asset called '{asset_name}'."
            candidates = [t for t in candidates if t.asset_id == asset.asset_id]
        if not candidates:
            return None, f"I don't have a maintenance task called '{title}'" + (f" for {asset_name}." if asset_name else ".")
        if len(candidates) > 1:
            names = sorted({
                (context.maintenance.get_asset(t.asset_id).name if context.maintenance.get_asset(t.asset_id) else "Unknown asset")
                for t in candidates
            })
            return None, f"Multiple assets have a task called '{title}' ({', '.join(names)}) — tell me which one."
        return candidates[0], None

    @staticmethod
    def _action_add_maintenance_asset(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a maintenance asset."
        category = str(arguments.get("category", "") or "Other").strip()
        if category not in MAINTENANCE_ASSET_CATEGORIES:
            category = "Other"
        asset = context.maintenance.add_asset(name=name, category=category)
        return f"Added '{asset.name}' to Maintenance as a {asset.category}."

    @staticmethod
    def _action_list_maintenance_assets(context: AppContext, arguments: dict) -> str:
        assets = context.maintenance.all_assets()
        if not assets:
            return "You have no vehicles or equipment tracked in Maintenance yet."
        lines = [f"- {a.name} [{a.category}]" for a in assets]
        return "Tracked in Maintenance:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_maintenance_asset(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((a for a in context.maintenance.all_assets() if a.name.lower() == name), None)
        if match is None:
            return f"I don't have a maintenance asset called '{arguments.get('name', '')}'."
        context.maintenance.delete_asset(match.asset_id)
        return f"Deleted '{match.name}' from Maintenance."

    @staticmethod
    def _action_add_maintenance_task(context: AppContext, arguments: dict) -> str:
        asset_name = str(arguments.get("asset_name", "")).strip()
        asset = next((a for a in context.maintenance.all_assets() if a.name.lower() == asset_name.lower()), None)
        if asset is None:
            return f"I don't have a maintenance asset called '{asset_name}'."
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a task title."
        interval_days = arguments.get("interval_days")
        interval_days = int(interval_days) if interval_days not in (None, "") else None
        task = context.maintenance.add_task(asset_id=asset.asset_id, title=title, interval_days=interval_days)
        if interval_days:
            return f"Added '{task.title}' for {asset.name}, repeating every {interval_days} days."
        return f"Added '{task.title}' for {asset.name} (one-time)."

    @staticmethod
    def _action_list_maintenance_tasks(context: AppContext, arguments: dict) -> str:
        query = str(arguments.get("query", "") or "").strip().lower()
        today = date.today()
        lines = []
        for task in context.maintenance.all_tasks():
            asset = context.maintenance.get_asset(task.asset_id)
            asset_name = asset.name if asset is not None else "Unknown asset"
            if query and query not in task.title.lower() and query not in asset_name.lower():
                continue

            if task.trigger_type == "calendar":
                remaining = maintenance_days_until_due(task, today)
                if remaining is None:
                    status = "one-time" if task.interval_days is None else "never done"
                elif remaining < 0:
                    status = f"overdue by {-remaining} days"
                elif remaining == 0:
                    status = "due today"
                else:
                    status = f"due in {remaining} days"
            elif task.is_meter_task:
                unit = task.meter_unit or "units"
                readings = context.maintenance.readings_for_task(task.task_id)
                if task.last_completed_meter_value is None:
                    status = "never done"
                elif not readings:
                    status = "no readings logged"
                else:
                    used = meter_used_since_last(task, readings) or 0.0
                    interval = task.meter_interval or 0.0
                    remaining_units = interval - used
                    status = (
                        f"overdue by {-remaining_units:.0f} {unit}"
                        if remaining_units <= 0
                        else f"{used:.0f}/{interval:.0f} {unit} used"
                    )
            elif task.is_sensor_task:
                readings = context.maintenance.readings_for_task(task.task_id)
                if not readings:
                    status = "no readings logged"
                else:
                    latest = readings[-1].value
                    unit = task.meter_unit or ""
                    status = "due" if is_sensor_task_due(task, readings) else f"ok ({latest:g}{unit})"
            else:
                status = "unknown"

            lines.append(f"- {task.title} ({asset_name}): {status}")

        if not lines:
            return "No maintenance tasks match that." if query else "You have no maintenance tasks tracked yet."
        return "Maintenance tasks:\n" + "\n".join(lines)

    @staticmethod
    def _action_complete_maintenance_task(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a task title to mark complete."
        task, error = MIAApplication._resolve_maintenance_task(context, title, str(arguments.get("asset_name", "") or "").strip())
        if error:
            return error
        meter_value = arguments.get("meter_value")
        meter_value = float(meter_value) if meter_value not in (None, "") else None
        context.maintenance.mark_complete(task.task_id, meter_value=meter_value)
        return f"Marked '{task.title}' complete."

    @staticmethod
    def _action_log_maintenance_reading(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a task title to log a reading for."
        value = arguments.get("value")
        if value is None:
            return "I need a value to log."
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "That value doesn't look like a number."
        task, error = MIAApplication._resolve_maintenance_task(context, title, str(arguments.get("asset_name", "") or "").strip())
        if error:
            return error
        unit = str(arguments.get("unit", "") or "")
        reading = context.maintenance.log_reading(task.task_id, value, unit=unit)
        unit_part = f" {reading.unit}" if reading.unit else ""
        return f"Logged {reading.value:g}{unit_part} for '{task.title}'."

    @staticmethod
    def _action_delete_maintenance_task(context: AppContext, arguments: dict) -> str:
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a task title to delete."
        task, error = MIAApplication._resolve_maintenance_task(context, title, str(arguments.get("asset_name", "") or "").strip())
        if error:
            return error
        context.maintenance.delete_task(task.task_id)
        return f"Deleted the maintenance task '{task.title}'."

    # ------------------------------------------------------------------
    # Lab (Data Logger) actions
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_lab_series(context: AppContext, requested: str) -> str:
        """Case-insensitive match against existing series names, reusing
        the exact stored id if one matches — so 'Soil Moisture' and
        'soil moisture' don't silently fragment into two series. Falls
        back to the requested string verbatim when nothing matches yet
        (a brand-new series, created implicitly on first reading — same
        "no separate series-registry file" convention as
        core.data_logger_manager's own design)."""
        canonical = next((s for s in context.data_logger.list_series() if s.lower() == requested.lower()), None)
        return canonical or requested

    @staticmethod
    def _action_log_lab_reading(context: AppContext, arguments: dict) -> str:
        series = str(arguments.get("series", "")).strip()
        if not series:
            return "I need a series name to log a reading under."
        value = arguments.get("value")
        if value is None:
            return "I need a value to log."
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "That value doesn't look like a number."
        series = MIAApplication._resolve_lab_series(context, series)
        unit = str(arguments.get("unit", "") or "")
        note = str(arguments.get("note", "") or "")
        reading = context.data_logger.add_reading(series_id=series, value=value, unit=unit, note=note)
        unit_part = f" {reading.unit}" if reading.unit else ""
        return f"Logged {reading.value:g}{unit_part} to '{series}'."

    @staticmethod
    def _action_list_lab_series(context: AppContext, arguments: dict) -> str:
        series = context.data_logger.list_series()
        if not series:
            return "You have no Data Logger series yet."
        return "Data Logger series:\n" + "\n".join(f"- {s}" for s in series)

    @staticmethod
    def _action_list_lab_readings(context: AppContext, arguments: dict) -> str:
        series = str(arguments.get("series", "")).strip()
        if not series:
            return "I need a series name to list readings for."
        series = MIAApplication._resolve_lab_series(context, series)
        readings = context.data_logger.readings_for(series)
        if not readings:
            return f"No readings logged for '{series}' yet."
        lines = [
            f"- {r.timestamp}: {r.value:g}" + (f" {r.unit}" if r.unit else "") + (f" — {r.note}" if r.note else "")
            for r in readings
        ]
        return f"Readings for '{series}':\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # Budget actions
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_bill(context: AppContext, name: str) -> tuple[Optional[Bill], Optional[str]]:
        """Exact case-insensitive name match — never fuzzy, same
        fail-closed discipline as _resolve_maintenance_task above."""
        match = next((b for b in context.budget.all_bills() if b.name.lower() == name.lower()), None)
        if match is None:
            return None, f"I don't have a bill called '{name}'."
        return match, None

    @staticmethod
    def _action_add_bill(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a bill."
        amount = arguments.get("amount")
        if amount is None:
            return "I need an amount to add a bill."
        due_date = str(arguments.get("due_date", "") or "").strip()
        if not due_date:
            return "I need a due date (YYYY-MM-DD) to add a bill."
        category = str(arguments.get("category", "") or "Utilities").strip()
        recurrence = str(arguments.get("recurrence", "") or "").strip().lower() or None
        bill = context.budget.add_bill(
            name=name, amount=float(amount), due_date=due_date, category=category, recurrence=recurrence,
        )
        recurrence_part = f", repeating {bill.recurrence}" if bill.recurrence else ""
        return f"Bill '{bill.name}' added for ${bill.amount:.2f} due {bill.due_date}{recurrence_part}."

    @staticmethod
    def _action_list_bills(context: AppContext, arguments: dict) -> str:
        bills = context.budget.all_bills()
        if not bills:
            return "You have no bills tracked."
        today = date.today()
        lines = []
        for bill in bills:
            remaining = days_until_bill_due(bill, today)
            if remaining is None:
                status = "paid"
            elif remaining < 0:
                status = f"overdue by {-remaining} days"
            elif remaining == 0:
                status = "due today"
            else:
                status = f"due in {remaining} days"
            lines.append(f"- {bill.name} (${bill.amount:.2f}, {bill.category}): {status}")
        return "Your bills:\n" + "\n".join(lines)

    @staticmethod
    def _action_mark_bill_paid(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a bill name to mark paid."
        bill, error = MIAApplication._resolve_bill(context, name)
        if error:
            return error
        amount = arguments.get("amount")
        amount = float(amount) if amount not in (None, "") else None
        entry = context.budget.mark_bill_paid(bill.bill_id, amount=amount)
        return f"Marked '{bill.name}' paid — recorded ${entry.amount:.2f}."

    @staticmethod
    def _action_add_income(context: AppContext, arguments: dict) -> str:
        amount = arguments.get("amount")
        if amount is None:
            return "I need an amount to record income."
        category = str(arguments.get("category", "") or "Other").strip()
        description = str(arguments.get("description", "") or "")
        date_str = str(arguments.get("date", "") or "").strip() or None
        entry = context.budget.add_income(amount=float(amount), category=category, description=description, date=date_str)
        return f"Recorded ${entry.amount:.2f} of income ({entry.category})."

    @staticmethod
    def _action_add_expense(context: AppContext, arguments: dict) -> str:
        amount = arguments.get("amount")
        if amount is None:
            return "I need an amount to record an expense."
        category = str(arguments.get("category", "") or "Other").strip()
        description = str(arguments.get("description", "") or "")
        date_str = str(arguments.get("date", "") or "").strip() or None
        entry = context.budget.add_expense(amount=float(amount), category=category, description=description, date=date_str)
        return f"Recorded ${entry.amount:.2f} expense ({entry.category})."

    @staticmethod
    def _action_get_budget_summary(context: AppContext, arguments: dict) -> str:
        start_date = str(arguments.get("start_date", "") or "").strip() or None
        end_date = str(arguments.get("end_date", "") or "").strip() or None
        income = context.budget.total_income(start_date, end_date)
        expenses = context.budget.total_expenses(start_date, end_date)
        tax_income = context.budget.total_income(start_date, end_date, tax_relevant_only=True)
        tax_expenses = context.budget.total_expenses(start_date, end_date, tax_relevant_only=True)
        return (
            f"Income: ${income:,.2f}. Expenses: ${expenses:,.2f}. Net: ${income - expenses:,.2f}. "
            f"Tax-relevant income: ${tax_income:,.2f}. Tax-relevant (deductible) expenses: ${tax_expenses:,.2f}."
        )

    @staticmethod
    def _resolve_income_source(context: AppContext, name: str) -> tuple[Optional[IncomeSource], Optional[str]]:
        """Exact case-insensitive name match — never fuzzy, same
        fail-closed discipline as _resolve_bill above."""
        match = next((s for s in context.budget.all_income_sources() if s.name.lower() == name.lower()), None)
        if match is None:
            return None, f"I don't have an income source called '{name}'."
        return match, None

    @staticmethod
    def _action_add_income_source(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add an income source."
        expected_amount = arguments.get("expected_amount")
        if expected_amount is None:
            return "I need an expected amount to add an income source."
        next_date = str(arguments.get("next_date", "") or "").strip()
        if not next_date:
            return "I need a next expected date (YYYY-MM-DD) to add an income source."
        category = str(arguments.get("category", "") or "Salary").strip()
        recurrence = str(arguments.get("recurrence", "") or "").strip().lower() or None
        source = context.budget.add_income_source(
            name=name, expected_amount=float(expected_amount), next_date=next_date, category=category, recurrence=recurrence,
        )
        recurrence_part = f", repeating {source.recurrence}" if source.recurrence else ""
        return f"Income source '{source.name}' added — ${source.expected_amount:.2f} expected {source.next_date}{recurrence_part}."

    @staticmethod
    def _action_mark_income_received(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need an income source name to mark received."
        source, error = MIAApplication._resolve_income_source(context, name)
        if error:
            return error
        amount = arguments.get("amount")
        amount = float(amount) if amount not in (None, "") else None
        entry = context.budget.mark_income_received(source.source_id, amount=amount)
        return f"Marked '{source.name}' received — recorded ${entry.amount:.2f}."

    @staticmethod
    def _action_get_financial_checkin(context: AppContext, arguments: dict) -> str:
        today = date.today()
        bills = context.budget.all_bills()
        income_sources = context.budget.all_income_sources()
        targets = context.budget.all_budget_targets()
        month_start = today.replace(day=1).isoformat()
        actual_by_category = context.budget.total_expenses_by_category(month_start, None)
        message = build_nudge_message(bills, income_sources, targets, actual_by_category, today)
        return message or "Everything looks on track — no overdue bills, nothing due soon, and no categories over budget."

    # ------------------------------------------------------------------
    # Real Estate actions
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_property(context: AppContext, name: str) -> tuple[Optional[Property], Optional[str]]:
        """Exact case-insensitive name match — never fuzzy, same
        fail-closed discipline as every other name-resolution action
        this session."""
        match = next((p for p in context.real_estate.all_properties() if p.name.lower() == name.lower()), None)
        if match is None:
            return None, f"I don't have a property called '{name}'."
        return match, None

    @staticmethod
    def _action_add_property(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a property."
        property_type = str(arguments.get("property_type", "") or "Rental").strip()
        current_value = arguments.get("current_value")
        mortgage_balance = arguments.get("mortgage_balance")
        prop = context.real_estate.add_property(
            name=name,
            property_type=property_type,
            current_value=float(current_value) if current_value not in (None, "") else 0.0,
            mortgage_balance=float(mortgage_balance) if mortgage_balance not in (None, "") else 0.0,
        )
        return f"Property '{prop.name}' added ({prop.property_type})."

    @staticmethod
    def _action_list_properties(context: AppContext, arguments: dict) -> str:
        properties = context.real_estate.all_properties()
        if not properties:
            return "You have no properties tracked."
        lines = [f"- {p.name} ({p.property_type}): ${property_equity(p):,.2f} equity" for p in properties]
        return "Your properties:\n" + "\n".join(lines)

    @staticmethod
    def _action_record_rental_income(context: AppContext, arguments: dict) -> str:
        property_name = str(arguments.get("property_name", "")).strip()
        if not property_name:
            return "I need a property name to record rental income."
        amount = arguments.get("amount")
        if amount is None:
            return "I need an amount to record rental income."
        prop, error = MIAApplication._resolve_property(context, property_name)
        if error:
            return error
        date_str = str(arguments.get("date", "") or "").strip() or None
        entry = context.real_estate.record_rental_income(prop.property_id, amount=float(amount), date_str=date_str)
        return f"Recorded ${entry.amount:.2f} rental income for '{prop.name}'."

    @staticmethod
    def _action_get_property_summary(context: AppContext, arguments: dict) -> str:
        property_name = str(arguments.get("property_name", "")).strip()
        if not property_name:
            return "I need a property name."
        prop, error = MIAApplication._resolve_property(context, property_name)
        if error:
            return error
        noi = context.real_estate.net_operating_income(prop.property_id)
        cap_rate = context.real_estate.cap_rate(prop.property_id)
        cap_rate_text = f"{cap_rate * 100:.2f}%" if cap_rate is not None else "n/a (no current value set)"
        return (
            f"'{prop.name}': equity ${property_equity(prop):,.2f}, "
            f"net operating income ${noi:,.2f}, cap rate {cap_rate_text}."
        )

    @staticmethod
    def _action_play_track(context: AppContext, arguments: dict) -> str:
        track_name = str(arguments.get("track_name", "")).strip()
        if not track_name:
            return "I need a song or artist name to play."
        matches = context.music.search_tracks(track_name)
        if not matches:
            return f"I couldn't find a song matching '{track_name}'."
        track = matches[0]
        context.music.play_track(track.track_id)
        artist_part = f" by {track.artist}" if track.artist else ""
        return f"Playing '{track.title}'{artist_part}."

    @staticmethod
    def _action_play_playlist(context: AppContext, arguments: dict) -> str:
        playlist_name = str(arguments.get("playlist_name", "")).strip()
        if not playlist_name:
            return "I need a playlist name to play."
        playlist = next(
            (p for p in context.music.all_playlists() if p.name.lower() == playlist_name.lower()), None
        )
        if playlist is None:
            return f"I couldn't find a playlist called '{playlist_name}'."
        if not context.music.play_playlist(playlist.playlist_id):
            return f"'{playlist.name}' doesn't have any tracks yet."
        return f"Playing playlist '{playlist.name}'."

    @staticmethod
    def _action_pause_music(context: AppContext, arguments: dict) -> str:
        context.music.pause()
        return "Paused."

    @staticmethod
    def _action_resume_music(context: AppContext, arguments: dict) -> str:
        context.music.resume()
        return "Resumed."

    @staticmethod
    def _action_stop_music(context: AppContext, arguments: dict) -> str:
        context.music.stop()
        return "Stopped."

    @staticmethod
    def _action_next_track(context: AppContext, arguments: dict) -> str:
        if not context.music.next_track():
            return "There's no next track in the queue."
        now_playing = context.music.now_playing()
        return f"Now playing '{now_playing.title}'." if now_playing else "Skipped."

    @staticmethod
    def _action_previous_track(context: AppContext, arguments: dict) -> str:
        if not context.music.previous_track():
            return "There's no previous track in the queue."
        now_playing = context.music.now_playing()
        return f"Now playing '{now_playing.title}'." if now_playing else "Went back a track."

    @staticmethod
    def _action_set_music_volume(context: AppContext, arguments: dict) -> str:
        percent = arguments.get("percent")
        if percent is None:
            return "I need a volume percent."
        percent = max(0, min(100, int(percent)))
        context.music.set_volume(percent)
        return f"Music volume set to {percent}%."

    @staticmethod
    def _action_get_now_playing(context: AppContext, arguments: dict) -> str:
        now_playing = context.music.now_playing()
        if now_playing is None:
            return "Nothing is currently playing."
        artist_part = f" by {now_playing.artist}" if now_playing.artist else ""
        state = "Playing" if now_playing.is_playing else "Paused"
        return f"{state}: '{now_playing.title}'{artist_part}."

    def _search_modules(self, query: str) -> list[SearchResult]:
        query_lower = query.lower()
        results = []
        for module in self.module_manager.all():
            haystack = f"{module.display_name} {module.description} {module.module_id}".lower()
            if query_lower in haystack:
                results.append(SearchResult(
                    title=module.display_name,
                    description=module.description or "Open this module",
                    source="Modules",
                    action_type="open_module",
                    action_target=module.module_id,
                ))
        return results

    def _search_profiles(self, query: str) -> list[SearchResult]:
        query_lower = query.lower()
        results = []
        for profile in self.context.profiles.list_profiles():
            if query_lower in profile.name.lower():
                results.append(SearchResult(
                    title=profile.name,
                    description="Switch to this profile",
                    source="Profiles",
                    action_type="switch_profile",
                    action_target=profile.profile_id,
                ))
        return results

    def run(self) -> int:
        """Start the boot sequence and enter the Qt event loop."""
        log.info("MIA starting up (version %s)", self.config.get("system.version"))

        self.splash = SplashScreen()
        self._display(self.splash)
        self._play_boot_sound()

        # The splash screen steps through a sequence of boot checks
        # before handing off to the wizard or main window. Using a
        # QTimer chain (rather than time.sleep) keeps the GUI responsive
        # during startup instead of freezing.
        #
        # 2026-07-15: each step now reports something *real* (an actual
        # module count, an actual Assistant/voice/power availability
        # check) instead of cosmetic filler text — docs/VISION.md's
        # Home visual-identity section asked for boot to feel like
        # "the system initializes, modules come online, sensors
        # activate" specifically, not just decorative HUD dressing.
        boot_steps = [
            self._boot_step_core_systems,
            self._boot_step_module_array,
            self._boot_step_assistant_core,
            self._boot_step_voice_interface,
            self._boot_step_power_systems,
            self._boot_step_personality_matrix,
        ]
        self._run_boot_steps(boot_steps, index=0)

        return self.qt_app.exec()

    def _play_boot_sound(self) -> None:
        """Fire-and-forget, same pattern as gui/home_dashboard.py's
        _speak_briefing() — degrades silently (logged inside
        VoiceManager.play() itself) if Voice/PortAudio isn't available,
        never blocks or delays the boot sequence. The synthesized
        "growing pulsing energy" sound (core/boot_sound.py) is
        regenerated fresh each boot rather than cached — numpy
        synthesis of a few seconds of audio is cheap enough that
        caching would be premature."""
        if self.context.voice is None:
            return
        output_path = Path(tempfile.gettempdir()) / "mia_boot_sound.wav"
        write_boot_sound_wav(output_path)
        self._boot_sound_worker = BootSoundWorker(self.context.voice, output_path)
        self._boot_sound_worker.start()

    def _boot_step_core_systems(self) -> str:
        return "CORE SYSTEMS... ONLINE"

    def _boot_step_module_array(self) -> str:
        self.module_manager.discover()
        modules = self.module_manager.all()
        return f"MODULE ARRAY... {len(modules)} MODULES ONLINE"

    def _boot_step_assistant_core(self) -> str:
        available = self.context.llm.is_available() if self.context.llm is not None else False
        return "ASSISTANT CORE... ONLINE" if available else "ASSISTANT CORE... OFFLINE (OLLAMA NOT DETECTED)"

    def _boot_step_voice_interface(self) -> str:
        if self.context.voice is None:
            return "VOICE INTERFACE... UNAVAILABLE"
        tts_ok = self.context.voice.is_tts_available()
        stt_ok = self.context.voice.is_stt_available()
        if tts_ok and stt_ok:
            return "VOICE INTERFACE... ONLINE"
        if tts_ok or stt_ok:
            return "VOICE INTERFACE... PARTIAL (CHECK VOICE MODELS)"
        return "VOICE INTERFACE... UNAVAILABLE"

    def _boot_step_power_systems(self) -> str:
        status = self.context.power.read() if self.context.power is not None else None
        if status is None:
            return "POWER SYSTEMS... NO BATTERY DETECTED"
        return f"POWER SYSTEMS... NOMINAL ({status.percent:.0f}%)"

    def _boot_step_personality_matrix(self) -> str:
        return "PERSONALITY MATRIX... LOADED — ALL SYSTEMS NOMINAL"

    def _run_boot_steps(self, steps: list, index: int) -> None:
        if index >= len(steps):
            self._finish_boot()
            return

        step = steps[index]
        try:
            message = step()
        except Exception:
            log.exception("Error during boot step %d (%s)", index, getattr(step, "__name__", step))
            message = None
        if message:
            self.splash.set_status(message)

        # 1400ms/step — gives the splash's presence orb
        # (gui/presence_widget.py) a couple of full breathing cycles per
        # step; the original 350ms made the animation flash by too fast
        # to register.
        QTimer.singleShot(1400, lambda: self._run_boot_steps(steps, index + 1))

    def _finish_boot(self) -> None:
        if self.config.is_first_run:
            log.info("First run detected — launching setup wizard.")
            self.setup_wizard = SetupWizard(self.context)
            self.setup_wizard.finished.connect(self._on_setup_finished)
            self.splash.close()
            self._display(self.setup_wizard)
            return

        profiles = self.context.profiles
        if not profiles.has_any_profiles():
            # Edge case: setup was previously marked complete but no
            # profile exists (e.g. manual config editing). Fall back to
            # the wizard rather than booting into a nameless main window.
            log.warning("setup_complete is set but no profiles exist — re-running setup wizard.")
            self.setup_wizard = SetupWizard(self.context)
            self.setup_wizard.finished.connect(self._on_setup_finished)
            self.splash.close()
            self._display(self.setup_wizard)
            return

        if profiles.needs_profile_selection():
            log.info("Multiple profiles found — showing profile selector.")
            self.profile_select = ProfileSelectScreen(self.context)
            self.profile_select.profile_selected.connect(self._on_profile_selected)
            self.splash.close()
            self._display(self.profile_select)
            return

        # Exactly one profile — auto-activate it if it isn't already
        # (e.g. right after the legacy-user migration ran). This is the
        # common single-user case, and it should never be interrupted
        # by the profile *selector* screen. But if this one profile has
        # a password, we still need to gate entry — otherwise setting a
        # password on a single-profile device would do nothing at all,
        # since the selector (where passwords are normally checked)
        # would never appear.
        if profiles.get_active_profile() is None:
            only_profile = profiles.list_profiles()[0]
            profiles.set_active_profile(only_profile.profile_id)

        # 2026-07-18: real ask — a single, password-less profile should
        # skip straight to the main window (already true below), *and*
        # that should be an explicit, toggleable setting
        # (`profile.always_show_login_screen`, default False — matches
        # the behavior every existing single-profile-no-password user
        # already gets today, so this formalizes it rather than
        # changing it) rather than just an unconditional code path with
        # no way to opt back into a confirmation screen. Toggled from
        # the profile-avatar menu (gui/main_window.py).
        always_show_login = self.context.config.get("profile.always_show_login_screen", False)
        active_profile = profiles.get_active_profile()
        if active_profile is not None and (active_profile.has_password or always_show_login):
            log.info(
                "Showing the login screen (%s).",
                "password-protected" if active_profile.has_password else "always_show_login_screen is on",
            )
            self.lock_screen = LockScreen(self.context, active_profile)
            self.lock_screen.unlocked.connect(self._on_lock_screen_unlocked)
            self.splash.close()
            self._display(self.lock_screen)
            return

        self._show_main_window()

    def _on_setup_finished(self) -> None:
        self._show_main_window()

    def _on_profile_selected(self) -> None:
        if self.profile_select is not None:
            self.profile_select.close()
        self._show_main_window()

    def _on_lock_screen_unlocked(self) -> None:
        if self.lock_screen is not None:
            self.lock_screen.close()
        self._show_main_window()

    def _on_switch_profile_requested(self) -> None:
        """
        Triggered by the "Switch User" button in MainWindow's header.
        Unlike the boot-time flow, this always shows the profile
        selector regardless of how many profiles exist — it's also the
        entry point for adding a second profile to a previously
        single-profile device.
        """
        log.info("Switch User requested.")
        if self.main_window is not None:
            self.main_window.close()
            self.main_window.deleteLater()
            self.main_window = None

        self.profile_select = ProfileSelectScreen(self.context)
        self.profile_select.profile_selected.connect(self._on_profile_selected)
        self._display(self.profile_select)

    def _show_main_window(self) -> None:
        if self.splash is not None:
            self.splash.close()
        self.main_window = MainWindow(self.context, self.module_manager)
        self.main_window.switch_profile_requested.connect(self._on_switch_profile_requested)
        self._display(self.main_window)
