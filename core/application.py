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
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from core.activity_log_manager import ActivityLogManager
from core.alarm_manager import AlarmManager
from core.avatar_manager import AvatarManager
from core.finance_manager import FinanceManager
from core.workshop_machine import LaserEngraverMachine, WorkshopMachineRegistry
from core.app_context import AppContext
from core.assistant_actions import AssistantAction
from core.calendar_manager import CalendarManager
from core.component_manager import ComponentManager
from core.boot_sound import write_boot_sound_wav
from core.boot_sound_worker import BootSoundWorker
from core.job_manager import JobManager
from core.material_manager import MaterialManager
from core.ledger_manager import LedgerManager
from core.product_manager import ProductManager
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.daily_occasions import calendar_events_today, is_birthday_today, should_run_once_daily, should_send_checkin
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
from core.llm_manager import LLMManager
from core.logger import get_logger
from core.map_tile_cache import MapTileCache
from core.memory_manager import MemoryManager
from core.mission_manager import METRIC_TYPES as MISSION_METRIC_TYPES, MissionManager
from core.module_manager import ModuleManager
from core.notification_manager import NotificationManager
from core.password_strength import assess_password
from core.port_scanner import scan_ports
from core.power_manager import PowerManager
from core.profile_manager import ProfileManager
from core.project_manager import PROJECT_STATUSES, ProjectManager
from core.reference_library_manager import ReferenceLibraryManager
from core.script_library_manager import ScriptLibraryManager
from core.subnet_calculator import calculate_subnet
from core.search_manager import SearchManager, SearchResult
from core.system_health import format_system_health, read_system_health
from core.task_manager import TaskManager
from core.trail_map_library import TrailMapLibrary
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
        self.qt_app.setApplicationName("M.I.A.")
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
        self.context.map_tiles = MapTileCache(self.context)
        self.context.trail_maps = TrailMapLibrary(self.context)
        self.context.workshop_machines = WorkshopMachineRegistry(self.context)
        # Registered by default so the registry has something real to
        # demonstrate end-to-end — it's a stub (no real driver), not a
        # working device, see core/workshop_machine.py's docstring.
        self.context.workshop_machines.register(LaserEngraverMachine())
        self.module_manager = ModuleManager(self.context)
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
        """
        if self.config.get("system.kiosk_mode", False):
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
        self.context.dashboard_widgets.register(WidgetDescriptor("volume", "Volume", "\U0001F50A"))
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

    def _register_assistant_actions(self) -> None:
        """
        Register the built-in actions the Assistant can invoke via
        core/llm_manager.py's chat_with_tools() — docs/ROADMAP.md
        milestone 5.5. Registered here (not in modules/assistant/) for
        the same reason search providers and calculators are: this is
        the one place independent core services get wired together,
        and open_module's handler needs self.module_manager to
        validate the target actually exists.
        """
        self.context.assistant_actions.register(AssistantAction(
            name="open_module",
            domain="system",
            description="Open/navigate to a M.I.A. module by its module_id.",
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
            description="Create a new alarm in M.I.A.",
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
            description="List the user's current alarms in M.I.A.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_alarms,
            trigger_phrases=("list my alarms", "list alarms", "what alarms", "show my alarms", "do i have any alarms"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_alarm",
            domain="alarms",
            destructive=True,
            description="Delete an existing alarm in M.I.A. by its label.",
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
            description="Add a new journal/note entry in M.I.A.'s Notes module.",
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
                "List or search the user's journal/note entries in M.I.A.'s Notes module. "
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
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_note",
            domain="notes",
            destructive=True,
            description="Delete an existing journal/note entry in M.I.A.'s Notes module by its title.",
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
            description="Add a new item to M.I.A.'s general Inventory tool.",
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
                "List or search M.I.A.'s Inventory tool, including quantities. "
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
            description="Remove an item entirely from M.I.A.'s Inventory tool by name.",
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
            description="List or search the user's saved waypoints (named locations) in M.I.A.'s Navigation module.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to search waypoint names/notes for."},
                },
                "required": [],
            },
            handler=self._action_list_waypoints,
            trigger_phrases=("waypoint", "waypoints", "list my waypoints", "list waypoints"),
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
            description="Delete an existing saved waypoint in M.I.A.'s Navigation module by name.",
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
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="recall_recent_activity",
            domain="system",
            description=(
                "Look up what the user has recently done in M.I.A. (modules opened, "
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
            description="Save a new named waypoint (location) in M.I.A.'s Navigation module.",
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
            name="add_expedition",
            domain="expeditions",
            description="Start a new Expedition (a dated outing that can hold multiple trips) in M.I.A.'s Expeditions module.",
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
            description="List the user's Expeditions in M.I.A.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_expeditions,
            trigger_phrases=("list my expeditions", "list expeditions", "what expeditions", "show my expeditions"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="recall_expedition",
            domain="expeditions",
            description=(
                "Get a detailed recap of ONE Expedition in M.I.A.'s Memories: duration, "
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
            description="Add a new Trip (one hike, paddle, ride, fishing trip, etc.) under an existing Expedition in M.I.A.",
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
            description="List the user's Trips in M.I.A., optionally filtered to one Expedition by name.",
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
            description="Add an item to a Trip's gear checklist in M.I.A.",
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
                "Add a dated journal/log entry to a specific Trip in M.I.A., optionally "
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
            name="get_device_profile",
            domain="system",
            description=(
                "Tell the user which M.I.A. EDITION (hardware/software variant) this "
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
            description="Change M.I.A.'s visual theme.",
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
                "Remember the current user's own birthday, so M.I.A. can recognize and celebrate it. "
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
            description="Add a new event to M.I.A.'s Calendar.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "A short title for the event."},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                    "time": {"type": "string", "description": "Optional time in 24-hour HH:MM format. Leave empty for an all-day event."},
                    "notes": {"type": "string", "description": "Optional notes."},
                },
                "required": ["title", "date"],
            },
            handler=self._action_add_calendar_event,
            trigger_phrases=("add an event", "add a calendar event", "schedule an event", "new calendar event"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_calendar_events",
            domain="calendar",
            description="List the user's Calendar events in M.I.A.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_calendar_events,
            trigger_phrases=("list my events", "list my calendar", "what's on my calendar", "upcoming events", "show my calendar"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_calendar_event",
            domain="calendar",
            destructive=True,
            description="Delete an existing Calendar event in M.I.A. by its title.",
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
            trigger_phrases=("battery level", "battery status", "power status", "how much battery", "how's my battery"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_component",
            domain="components",
            description="Add a new electronic component to M.I.A.'s Workshop & Electronics component database.",
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
            description="List or search the user's electronic components in M.I.A.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all components."},
                },
                "required": [],
            },
            handler=self._action_list_components,
            trigger_phrases=("list my components", "list components", "what components", "show my components", "search components"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_component",
            domain="components",
            destructive=True,
            description="Delete an existing electronic component in M.I.A. by name.",
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
        self.context.assistant_actions.register(AssistantAction(
            name="list_connected_devices",
            domain="field_kit",
            description="List currently connected external USB storage and serial devices in M.I.A.'s Field Kit.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_connected_devices,
            trigger_phrases=("connected devices", "what devices are connected", "list devices", "usb devices", "list connected devices"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_scripts",
            domain="field_kit",
            description="List the user's saved scripts in M.I.A.'s Field Kit script library.",
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
                "List the user ACCOUNTS/PEOPLE set up on this M.I.A. device (e.g. "
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
                "For a real account password, prefer M.I.A.'s Field Kit Security tab "
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
                "more ports, use M.I.A.'s Field Kit Security tab instead."
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
            description="Start a new Project (a container for tasks) in M.I.A.'s Project Manager tool.",
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
            description="List the user's Projects in M.I.A.'s Project Manager tool.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_projects,
            trigger_phrases=("list my projects", "list projects", "what projects", "show my projects"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_task",
            domain="projects",
            description="Add a new Task under an existing Project in M.I.A.'s Project Manager tool.",
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
            description="List the user's Tasks in M.I.A., optionally filtered to one Project by name.",
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
            trigger_phrases=("list my tasks", "list tasks", "what tasks", "show my tasks"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_project",
            domain="projects",
            destructive=True,
            description="Delete an existing Project (and unlink, but not delete, its Tasks) in M.I.A. by name.",
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
            description="Delete an existing Task in M.I.A. by title.",
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
            description="Mark an existing Task as done (complete) or not done in M.I.A. by title.",
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
                "Start a new gamified Mission in M.I.A. (e.g. a 'Master Angler' mission for a "
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
            description="List the user's Missions in M.I.A., including each objective's progress.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_missions,
            trigger_phrases=("list my missions", "list missions", "what missions", "show my missions"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_objective",
            domain="missions",
            description=(
                "Add an Objective to an existing Mission in M.I.A. — either a manually-tracked "
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
                "Log progress toward a tally-type Objective on a Mission in M.I.A. — e.g. "
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
            description="Delete an existing Mission in M.I.A. by name.",
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
            description="Mark an existing Mission as completed in M.I.A. by name.",
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

    def _action_open_module(self, context: AppContext, arguments: dict) -> str:
        requested = str(arguments.get("module_id", "")).strip()
        module = self.module_manager.resolve(requested)
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
    def _action_delete_waypoint(context: AppContext, arguments: dict) -> str:
        name = str(arguments.get("name", "")).strip().lower()
        match = next((w for w in context.waypoints.all_waypoints() if w.name.lower() == name), None)
        if match is None:
            return f"I don't have a waypoint called '{arguments.get('name', '')}'."
        context.waypoints.delete_waypoint(match.waypoint_id)
        return f"Deleted the waypoint '{match.name}'."

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
        event = context.calendar.add_event(title=title, date=date_str, time=time_str, notes=notes)
        time_part = f" at {event.time}" if event.time else ""
        return f"Calendar event '{event.title}' added for {event.date}{time_part}."

    @staticmethod
    def _action_list_calendar_events(context: AppContext, arguments: dict) -> str:
        events = context.calendar.all_events()
        if not events:
            return "You have no calendar events."
        lines = [f"- '{e.title}' on {e.date}" + (f" at {e.time}" if e.time else "") for e in events]
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
                lines.append(f"    [{mark}] {objective.description}: {progress:g}/{objective.target:g}")
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
        return f"Logged progress on '{objective.description}': {new_progress:g}/{objective.target:g}.{done_note}"

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
        log.info("M.I.A. starting up (version %s)", self.config.get("system.version"))

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

        active_profile = profiles.get_active_profile()
        if active_profile is not None and active_profile.has_password:
            log.info("Single profile is password-protected — showing lock screen.")
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
