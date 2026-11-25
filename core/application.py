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
import threading
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from core.activity_log_manager import ActivityLogManager
from core.actions import ActionCenter
from core.life_events import LifeEventLog
from core.links import LinkStore
from core.usage_tracker import UsageTracker
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
from core.lite_capture_manager import LiteCaptureManager
from core.workshop_machine import LaserEngraverMachine, WorkshopMachineRegistry
from core.app_context import AppContext
from core.assistant_tools import AssistantTools
from core.background_jobs import BackgroundJobs
from core.assistant_actions import AssistantAction
from core.calendar_manager import CALENDAR_RECURRENCE_TYPES, CalendarManager
from core.component_manager import ComponentManager
from core.boot_sound import write_boot_sound_wav  # noqa: F401  (kept: the original sound, also a choice)
from core.boot_sound_worker import BootSoundWorker
from core.job_manager import JobManager
from core.material_manager import MaterialManager
from core.ledger_manager import LedgerManager
from core.product_manager import ProductManager
from core.config_manager import ConfigManager
from core.connectivity import ConnectivityMonitor, connectivity_action
from core.online_watch import CAME_BACK, WENT_OFFLINE, OnlineReminders, OnlineWatch, remind_when_online_action, transition_message
from core.assistant_domain_actions import register_domain_actions
from core.assistant_life_actions import register_life_actions
from core.talk_it_out import register_journal_actions
from core.journal_reflection import journal_reflection_action, reflection_due, reflection_notice
from core.warranty_watch import due_notices, warranty_message
from core.assistant_why_actions import register_why_actions
from core.assistant_direction_actions import register_direction_actions
from core.assistant_answer_style_actions import register_answer_style_actions
from core.assistant_world_actions import register_world_actions
from core.assistant_business_view_actions import register_business_view_actions
from core.assistant_connection_actions import register_connection_actions
from core.assistant_comm_actions import register_communication_actions
from core.assistant_email_actions import register_email_actions
from core.assistant_focus_actions import register_focus_actions
from core.assistant_accessibility_actions import register_accessibility_actions
from core.assistant_humor_actions import register_humor_actions
from core.assistant_progress_actions import register_progress_actions
from core.assistant_camera_actions import register_camera_actions
from core.assistant_correction_actions import register_correction_actions
from core.assistant_playlist_actions import register_playlist_actions
from core.assistant_more_twins_actions import register_more_twins_actions
from core.assistant_records_actions import register_records_actions
from core.assistant_plan_actions import register_plan_actions
from core.plan_library import PlanLibrary
from core.assistant_starter_actions import register_starter_actions
from core.assistant_life_event_actions import register_life_event_actions
from core.assistant_link_actions import register_link_actions
from core.assistant_ownership_actions import register_ownership_actions
from core.assistant_today_actions import register_today_actions
from core.assistant_self_actions import register_capability_actions, register_self_actions
from core.specialists import register_specialist_actions
from core.assistant_energy_actions import register_energy_actions
from core.assistant_path_actions import register_path_actions
from core.assistant_browser_actions import register_browser_actions
from core.browser import Browsers
from core.assistant_cooking_actions import register_cooking_actions
from core.assistant_household_actions import register_household_actions
from core.assistant_lab_actions import register_lab_actions
from core.assistant_notification_actions import register_notification_actions
from core.assistant_screen_tools import register_screen_tools
from core.assistant_toolbox_actions import register_toolbox_actions
from core.assistant_waypoint_actions import register_waypoint_actions
from core.assistant_trip_route_actions import register_trip_route_actions
from core.assistant_backup_actions import register_backup_actions
from core.assistant_voice_choice_actions import register_voice_choice_actions
from core.assistant_subscription_actions import register_subscription_actions
from core.assistant_proposal_actions import register_proposal_actions
from core.assistant_asset_part_actions import register_asset_part_actions
from core.assistant_health_actions import register_health_actions
from core.assistant_goods_actions import register_goods_actions
from core.assistant_dungeon_actions import register_checkin_actions, register_dungeon_actions, register_loop_actions
from core.assistant_closet_actions import register_closet_actions
from core.assistant_taught_skill_actions import register_taught_skill_actions
from core.assistant_ual_actions import register_ual_actions
from core.assistant_creation_actions import register_creation_actions
from core.assistant_game_actions import register_game_actions
from core.failure_actions import register_failure_actions
from core.assistant_undo_actions import register_undo_actions
from core.assistant_homestead_actions import register_homestead_actions
from core.assistant_textbook_actions import register_textbook_actions
from core.assistant_inbox_actions import register_inbox_actions
from core.assistant_tagging_actions import register_tagging_actions
from core.assistant_lookup import resolve_by_name
from core.conversation_manager import ConversationManager
from core.budget_nudges import build_nudge_message
from core.context_assembler import (assemble_life_state, assemble_life_state_v2, describe_life_state_v2,
                                     format_life_state_summary)
from core.daily_occasions import calendar_events_today, is_birthday_today, should_run_once_daily, should_send_checkin
from core.maintenance_insights import format_maintenance_insights_message, scan_maintenance_insights
from core.mission_insights import format_mission_insights_message, scan_mission_insights
from core.mission_patterns import format_pattern_insights_message, scan_pattern_insights
from core.skill_patterns import (
    format_skill_decline_insights_message,
    format_skill_momentum_insights_message,
    format_skill_pattern_insights_message,
    scan_skill_decline_insights,
    scan_skill_momentum_insights,
    scan_skill_pattern_insights,
)
from core.smart_suggestions import build_smart_suggestions_message, build_walkthrough_suggestion
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
from core.pathway_manager import PathwayManager
from core.recurring_mission_manager import RecurringMissionManager
from core.discovery_manager import DiscoveryManager
from core.skill_manager import SkillManager
from core.module_manager import ModuleManager
from core.notification_manager import NotificationManager
from core.password_strength import assess_password
from core.port_scanner import scan_ports
from core.energy_manager import EnergyManager
from core.power_manager import PowerManager
from core.household_manager import HouseholdManager
from core.undo_log import UndoLog
from core.profile_manager import ProfileManager
from core.push_subscription_manager import PushSubscriptionManager
from core.insight_manager import InsightManager
from core.intent_manager import IntentManager
from core.project_manager import PROJECT_STATUSES, ProjectManager
from core.plaid_manager import PlaidManager
from core.net_worth_history import NetWorthHistory
from core.real_estate_manager import Property, RealEstateManager, equity as property_equity
from core.reference_library_manager import ReferenceLibraryManager
from core.rewards_manager import RewardsManager
from core.script_library_manager import ScriptLibraryManager
from core.subnet_calculator import calculate_subnet
from core.search_manager import SearchManager, SearchResult
from core.system_health import format_system_health, read_system_health
from core.task_manager import TaskManager
from core.trail_map_library import NotAPdfError, TrailMapLibrary
from core.music_manager import MusicManager
from core.kitchen_manager import KitchenManager
from core.classroom_manager import ClassroomManager
from core.workout_manager import WorkoutManager
from core.relationships_manager import RelationshipsManager
from core.trip_manager import ACTIVITY_TYPES, TripManager
from core.user_memory_manager import UserMemoryManager
from core.private_journal import PrivateJournalManager
from core.communication_gate import AMBIENT, TIMELY, Candidate, CommunicationGate
from core.business_use import BusinessUseManager
from core.textbook_manager import TextbookManager
from core.inbox_manager import InboxManager, describe_new_items
from core.inbox_mail import MailChecker, MailSettings, MailVault
from core.ocr import OcrQueue
from core.personal_data import PersonalData
from core.voice_manager import VoiceManager
from core.volume_manager import VolumeManager
from core.waypoint_manager import WAYPOINT_CATEGORIES, WaypointManager
from gui.lock_screen import LockScreen
from gui.main_window import MainWindow
from gui.profile_select import ProfileSelectScreen
from gui.setup_wizard import SetupWizard
from gui.splash_screen import SplashScreen
from gui.theme_manager import THEME_DISPLAY_NAMES, THEMES, build_stylesheet, get_theme_stylesheet
from core.region import money

log = get_logger(__name__)



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



class MainThreadInvoker(QObject):
    """Runs functions on the GUI thread: call() may be used from any
    thread; the queued signal delivers to the thread this object lives
    in (the GUI thread, where MIAApplication creates it)."""

    _run = Signal(object)

    def __init__(self) -> None:
        """Connects the signal with a queued connection, so whatever is emitted runs later on this object's thread."""
        super().__init__()
        self._run.connect(self._execute, Qt.ConnectionType.QueuedConnection)

    def call(self, fn) -> None:
        """Hands fn to the GUI thread; safe from any thread."""
        self._run.emit(fn)

    @staticmethod
    def _execute(fn) -> None:
        """Runs a handed-over function on the GUI thread, logging (never raising) its failure."""
        try:
            fn()
        except Exception:
            log.exception("A function handed to the GUI thread failed.")

def _console_or_nothing() -> None:
    """Started from the desktop shortcut (pythonw.exe on Windows) there's no
    console, so sys.stdout and sys.stderr are None and any library writing
    to them crashes MIA. Give them somewhere harmless to go; what matters
    is in logs/mia.log anyway."""
    import os

    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))

AssistantTools.DESKTOP_THEMES = {theme_id: THEME_DISPLAY_NAMES[theme_id] for theme_id in THEMES}  # for set_theme


class MIAApplication(BackgroundJobs, AssistantTools):
    """Owns the Qt application object and the startup sequence. Its periodic jobs and daily checks are
    core.background_jobs.BackgroundJobs', and its Assistant tools core.assistant_tools.AssistantTools', both inherited
    so they are the same with or without this window (DEC-0155)."""

    def __init__(self) -> None:
        """Builds the whole app before anything is shown: the Qt application and fonts, the one-MIA-per-data-folder
        check (core/instance_lock.py: a second copy says so and quits), a restore chosen before the restart
        (core/backup_manager.apply_pending_restore, before anything reads its files), config, the event bus, the store
        lock shared with the phone server (each scheduled job runs under it or waits) and AppContext, the
        theme, then every core service onto the context through core/runtime.build_services (the same function the
        headless runtime uses: profiles and households, each store, the model, voice, the communication gate, the
        module manager and search), each person's look, the registries (search providers,
        calculators, the Assistant's tools, dashboard widgets) and the schedule of periodic jobs
        (core/background_jobs.py on core/scheduler.py, asked what's due by one QTimer). Only
        construction happens here; run() shows the splash and boots.
        """
        _console_or_nothing()
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("MIA")
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "mia_icon.png"
        if icon_path.exists():
            from PySide6.QtGui import QIcon

            self.qt_app.setWindowIcon(QIcon(str(icon_path)))
        _load_bundled_fonts()

        from core import instance_lock

        if not instance_lock.acquire():  # one MIA per data folder: a second copy would save over the first's changes
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(None, "MIA is already running",
                                    "MIA is already open on this computer. Use the window that's open (it may be "
                                    "minimised or in the tray).")
            sys.exit(0)
        from core.backup_manager import apply_pending_restore

        apply_pending_restore()  # a restore chosen before the restart, before anything has read its files
        self.config = ConfigManager()
        self.events = EventBus()
        self.context = AppContext(config=self.config, events=self.events)
        from core.store_lock import StoreLock

        self.context.store_lock = StoreLock()  # shared with the phone server (server/app.py)
        # Lets background threads (the phone server) hand work to the GUI
        # thread safely (core/main_thread.py).
        self._main_thread_invoker = MainThreadInvoker()
        self.context.main_thread_call = self._main_thread_invoker.call

        # Applied once, at the QApplication level — Qt's stylesheet
        # cascade means every widget/dialog inherits this automatically,
        # which is why individual dialogs no longer call their own
        # setStyleSheet() (gui/theme_manager.py, docs/ROADMAP.md
        # milestone 13.2). "theme.changed" (published by
        # modules/settings/module.py's Theme dropdown) re-applies this
        # live, no restart required.
        self.qt_app.setStyleSheet(get_theme_stylesheet(self.config.get("gui.theme", "dark_field")))
        self.events.subscribe("theme.changed", self._on_theme_changed)
        # Every core service onto the context, in dependency order: built by core/runtime.build_services(), the one
        # place the whole MIA is put together, shared with the headless runtime (DEC-0155).
        from core.runtime import build_services

        build_services(self.context)
        self.module_manager = self.context.module_manager
        self._online_watch = OnlineWatch()
        # Each person's text size and contrast (core/accessibility.py),
        # applied now and whenever someone signs in or changes them.
        self._base_font = self.qt_app.font()
        self._apply_look()
        for event in ("profile.switched", "profile.created", "display.changed"):
            self.events.subscribe(event, self._apply_look)
        self._register_search_providers()
        self._register_calculators()
        self._register_assistant_actions()
        self._register_dashboard_widgets()

        self.splash: SplashScreen | None = None
        self._boot_sound_worker: BootSoundWorker | None = None
        self.main_window: MainWindow | None = None
        # MIA's floating desktop orb (gui/orb_presence.py, Zac 2026-11-08), when gui.boot_orb is on: boot opens on
        # just her orb, and clicking it wakes the main window. _orb_dismissed stays True for the rest of the session
        # once woken, so a later Switch User doesn't drop back to the orb.
        self._orb = None
        self._orb_dismissed = False
        self.setup_wizard: SetupWizard | None = None
        self.profile_select: ProfileSelectScreen | None = None
        self.lock_screen: LockScreen | None = None

        # MIA's background schedule (core/background_jobs.py on core/scheduler.py, DEC-0155): alarms, the battery,
        # the daily checks, the watched folders, the inbox, the connection and missions she assigns. They were ten
        # QTimers here until 2026-11-15; now one QTimer asks the scheduler what's due, on this thread as before, and
        # each job runs under the store lock or waits for the next tick. A headless runtime runs the same schedule
        # without this window.
        from core.scheduler import Scheduler

        self.scheduler = Scheduler(lock=self.context.store_lock)
        self.context.scheduler = self.scheduler  # /api/runtime/health reads its jobs
        self.schedule(self.scheduler)
        self._schedule_timer = QTimer()
        self._schedule_timer.timeout.connect(self.scheduler.run_due)
        self._schedule_timer.start(5_000)
        # Also run once immediately at boot: a job's first run is one
        # interval in, so without this a long-idle user would wait a full
        # 5 minutes after opening MIA before getting a mission that was
        # already overdue.
        self._check_mission_auto_assignment()

    def _display(self, widget) -> None:
        """
        Show a top-level screen, going fullscreen if kiosk_mode is on; the main window opens maximized unless
        `gui.start_maximized` is off (a screen class says it wants that with START_MAXIMIZED).

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
        elif getattr(widget, "START_MAXIMIZED", False) and self.config.get("gui.start_maximized", True):
            widget.showMaximized()  # Zac, 2026-11-17: the fixed 1100 x 700 window left the page too long to see
        else:
            widget.show()

    def _on_theme_changed(self, theme_id: str, **_kwargs) -> None:
        """Live theme swap — published by modules/settings/module.py's Theme dropdown. No restart required."""
        self._apply_look(theme_id=theme_id)

    def _apply_look(self, theme_id: Optional[str] = None, **_kwargs) -> None:
        """The theme plus the signed-in person's text size and contrast
        (core/accessibility.py, gui/theme_manager.py's build_stylesheet())."""
        from PySide6.QtGui import QFont

        from core.accessibility import look_for, text_scale

        size, high_contrast = look_for(self.context)
        theme = theme_id or self.config.get("gui.theme", "dark_field")
        self.qt_app.setStyleSheet(build_stylesheet(theme, size, high_contrast))
        base = getattr(self, "_base_font", None)
        if base is not None:
            font = QFont(base)
            if base.pointSizeF() > 0:
                font.setPointSizeF(base.pointSizeF() * text_scale(size))
            self.qt_app.setFont(font)

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
        self.context.dashboard_widgets.register(WidgetDescriptor("observations", "Observations", "\U0001F50D"))
        self.context.dashboard_widgets.register(WidgetDescriptor("lite_captures", "Field Captures", "\U0001F399"))
        self.context.dashboard_widgets.register(WidgetDescriptor("life_state", "Life State", "\U0001F9ED"))

    def _search_modules(self, query: str) -> list[SearchResult]:
        """The Ctrl+K search provider for modules: every module whose name, description or id contains the query, each
        opening it (action_type open_module).
        """
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
        """The Ctrl+K search provider for profiles: every profile whose name contains the query, each switching to it."""
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
        """Start the boot sequence and enter the Qt event loop (her browser windows close when it ends)."""
        log.info("MIA starting up (version %s)", self.config.get("system.version"))

        self.splash = SplashScreen()
        self._display(self.splash)
        self._play_boot_sound()
        self._start_mobile_server()

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
        # Her browser windows close with her (DEC-0117).
        self.qt_app.aboutToQuit.connect(self.context.browsers.close_all)

        return self.qt_app.exec()

    def _play_boot_sound(self) -> None:
        """Fire-and-forget, same pattern as gui/home_dashboard.py's
        _speak_briefing() — degrades silently (logged inside
        VoiceManager.play() itself) if Voice/PortAudio isn't available,
        never blocks or delays the boot sequence. The synthesized
        "growing pulsing energy" sound (core/boot_sound.py) is
        regenerated fresh each boot rather than cached — numpy
        synthesis of a few seconds of audio is cheap enough that
        caching would be premature. Which sound (or none) is the device's
        `sound.startup`, chosen in Settings (core/startup_sounds.py)."""
        from core.boot_sound import write_startup_wav
        from core.startup_sounds import OFF, startup_choice

        chosen = startup_choice(self.config)  # Settings' "Startup sound" (2026-11-07), or off
        if self.context.voice is None or chosen == OFF:
            return
        output_path = Path(tempfile.gettempdir()) / "mia_boot_sound.wav"
        write_startup_wav(chosen, output_path)
        self._boot_sound_worker = BootSoundWorker(self.context.voice, output_path)
        self._boot_sound_worker.start()

    def _start_mobile_server(self) -> None:
        """The phone API server (core/phone_server.py): created always so
        Settings can switch it on later; started now only when enabled
        (server.enabled). Never blocks or fails boot."""
        from core.phone_server import PhoneServer

        self.context.phone_server = PhoneServer(self.context)
        if self.context.phone_server.enabled:
            self.context.phone_server.start()

    def _boot_step_core_systems(self) -> str:
        """Splash step: the core services were built in __init__, so this only reports them online."""
        return "CORE SYSTEMS... ONLINE"

    def _boot_step_module_array(self) -> str:
        """Splash step: discovers the modules and reports how many are online."""
        self.module_manager.discover()
        modules = self.module_manager.all()
        return f"MODULE ARRAY... {len(modules)} MODULES ONLINE"

    def _boot_step_assistant_core(self) -> str:
        """Splash step: checks whether the local model (Ollama) answers and reports online or offline."""
        available = self.context.llm.is_available() if self.context.llm is not None else False
        return "ASSISTANT CORE... ONLINE" if available else "ASSISTANT CORE... OFFLINE (OLLAMA NOT DETECTED)"

    def _boot_step_voice_interface(self) -> str:
        """Splash step: reports voice as online (speech out and in both work), partial, or unavailable."""
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
        """Splash step: reads the battery and reports its percent, or that there's no battery."""
        status = self.context.power.read() if self.context.power is not None else None
        if status is None:
            return "POWER SYSTEMS... NO BATTERY DETECTED"
        return f"POWER SYSTEMS... NOMINAL ({status.percent:.0f}%)"

    def _boot_step_personality_matrix(self) -> str:
        """Splash step: the last line, all systems nominal."""
        return "PERSONALITY MATRIX... LOADED — ALL SYSTEMS NOMINAL"

    def _run_boot_steps(self, steps: list, index: int) -> None:
        """Runs the splash's boot steps one at a time, 1.4 s apart (time for the presence orb to breathe), showing each
        step's line; a step that fails is logged and skipped. After the last it calls _finish_boot().
        """
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
        """Decides the first screen after the splash: the setup wizard on a first run (or when setup was marked done but no
        profile exists), the lock screen when the one profile has a password, the main window when there's one profile,
        and the profile selector when there are several. Every screen goes through _display() (kiosk fullscreen).
        """
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
        """The wizard finished: show the main window."""
        self._show_main_window()

    def _on_profile_selected(self) -> None:
        """Someone was chosen on the profile selector: close it and show the main window."""
        if self.profile_select is not None:
            self.profile_select.close()
        self._show_main_window()

    def _on_lock_screen_unlocked(self) -> None:
        """The lock screen was unlocked: close it and show the main window."""
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
        """Closes the splash and shows the main window (through _display(), so kiosk fullscreen holds), wiring its Switch
        User button. When gui.boot_orb is on, opens on MIA's floating orb first and waits for a click.
        """
        if self._should_show_orb():
            self._show_orb()
            return
        if self.splash is not None:
            self.splash.close()
        self.main_window = MainWindow(self.context, self.module_manager)
        self.main_window.switch_profile_requested.connect(self._on_switch_profile_requested)
        self._display(self.main_window)

    def _should_show_orb(self) -> bool:
        """Whether to open on MIA's floating orb first (Zac, 2026-11-08): opt-in via gui.boot_orb, never in kiosk mode
        (the Pi wants a full screen, not a desktop presence), and only until she's been woken this session."""
        return (bool(self.config.get("gui.boot_orb", False))
                and not self.config.get("system.kiosk_mode", False)
                and not self._orb_dismissed)

    def _show_orb(self) -> None:
        """Show just her orb and rings floating in the middle of the screen; a click wakes her into the main window."""
        from gui.orb_presence import OrbPresence

        if self.splash is not None:
            self.splash.close()
        self._orb = OrbPresence()
        self._orb.activated.connect(self._wake_from_orb)
        self._orb.show_centered()
        log.info("Opened on MIA's floating orb (gui.boot_orb); waiting for a click to wake the main window.")

    def _wake_from_orb(self) -> None:
        """The orb was clicked (or Enter/Space): close it and open her main window for the rest of the session."""
        self._orb_dismissed = True
        if self._orb is not None:
            self._orb.close()
            self._orb = None
        self._show_main_window()
