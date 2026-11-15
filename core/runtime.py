"""
core.runtime
==============

The MIA Runtime (DEC-0155; step 4 of
`docs/mia_os/preliminary/MIA_OS_INITIAL_IMPLEMENTATION_PLAN.md`): the whole
MIA, running with no window.

What it is:
- `build_services(context)`: the one place every core service is put on
  the context, in dependency order. Until 2026-11-15 this was inside the Qt
  window's `MIAApplication.__init__`, so the full MIA only existed while
  the desktop window did. The desktop now calls this too.
- `Runtime`: a MIA with no window. It takes the one-MIA-per-data-folder
  lock, builds the services, registers the full Assistant tool registry
  (`core.assistant_tools.AssistantTools`), runs the background schedule
  (`core.background_jobs.BackgroundJobs` on `core.scheduler.Scheduler`) on
  a thread, and starts the phone server when it's switched on
  (`core.phone_server.PhoneServer`). `health()` says how it's doing.
- `python -m core.runtime` runs one until it's told to stop (Ctrl+C, or a
  service manager's stop): what a systemd user service on MIA OS or the Pi
  starts.

How it differs from `core/core_runtime.py`: that file builds a smaller,
hand-picked MIA (the phone app and a few tools still use it). This one is
the full MIA the desktop has, minus only what needs a window. The two will
be folded together once the phone runs this one.

What it doesn't do yet: no desktop window attaches to a running runtime
(step 5); nothing starts it automatically (step 6). The desktop app still
builds its own MIA in its own process, and the one-MIA lock keeps the two
from running on the same data folder at once.

Nothing here imports Qt, `gui/` or `modules/`.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional

from core.actions import ActionCenter
from core.activity_log_manager import ActivityLogManager
from core.alarm_manager import AlarmManager
from core.avatar_manager import AvatarManager
from core.browser import Browsers
from core.budget_manager import BudgetManager
from core.business_use import BusinessUseManager
from core.calendar_manager import CalendarManager
from core.classroom_manager import ClassroomManager
from core.communication_gate import CommunicationGate
from core.component_manager import ComponentManager
from core.connectivity import ConnectivityMonitor
from core.conversation_manager import ConversationManager
from core.dashboard_widgets import DashboardWidgetRegistry
from core.data_logger_manager import DataLoggerManager
from core.device_framework import DeviceFramework
from core.device_help_manager import DeviceHelpManager
from core.discovery_manager import DiscoveryManager
from core.energy_manager import EnergyManager
from core.expedition_manager import ExpeditionManager
from core.finance_manager import FinanceManager
from core.homestead_manager import HomesteadManager
from core.household_manager import HouseholdManager
from core.inbox_mail import MailChecker, MailSettings, MailVault
from core.inbox_manager import InboxManager
from core.insight_manager import InsightManager
from core.intent_manager import IntentManager
from core.inventory_manager import InventoryManager
from core.job_manager import JobManager
from core.journal_manager import JournalManager
from core.kitchen_manager import KitchenManager
from core.ledger_manager import LedgerManager
from core.life_events import LifeEventLog
from core.links import LinkStore
from core.lite_capture_manager import LiteCaptureManager
from core.llm_manager import LLMManager
from core.maintenance_manager import MaintenanceManager
from core.map_tile_cache import MapTileCache
from core.material_manager import MaterialManager
from core.memory_manager import MemoryManager
from core.mission_manager import MissionManager
from core.module_manager import ModuleManager
from core.music_manager import MusicManager
from core.net_worth_history import NetWorthHistory
from core.notification_manager import NotificationManager
from core.ocr import OcrQueue
from core.online_watch import OnlineReminders
from core.pathway_manager import PathwayManager
from core.personal_data import PersonalData
from core.plaid_manager import PlaidManager
from core.plan_library import PlanLibrary
from core.power_manager import PowerManager
from core.private_journal import PrivateJournalManager
from core.product_manager import ProductManager
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.push_subscription_manager import PushSubscriptionManager
from core.real_estate_manager import RealEstateManager
from core.recurring_mission_manager import RecurringMissionManager
from core.reference_library_manager import ReferenceLibraryManager
from core.relationships_manager import RelationshipsManager
from core.rewards_manager import RewardsManager
from core.script_library_manager import ScriptLibraryManager
from core.search_manager import SearchManager
from core.skill_manager import SkillManager
from core.task_manager import TaskManager
from core.textbook_manager import TextbookManager
from core.trail_map_library import TrailMapLibrary
from core.trip_manager import TripManager
from core.undo_log import UndoLog
from core.usage_tracker import UsageTracker
from core.user_memory_manager import UserMemoryManager
from core.voice_manager import VoiceManager
from core.volume_manager import VolumeManager
from core.waypoint_manager import WaypointManager
from core.workout_manager import WorkoutManager
from core.workshop_machine import LaserEngraverMachine, WorkshopMachineRegistry
from core.app_context import AppContext
from core import data_root
from core.assistant_tools import AssistantTools
from core.background_jobs import JOBS, BackgroundJobs
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.logger import get_logger
from core.scheduler import Scheduler

log = get_logger(__name__)


def build_services(context: AppContext) -> AppContext:
    """Puts every core service on the context, in dependency order (a store that reaches into another is built after
    it), ending with each person's own stores, the module manager (nothing discovered yet), search and the usage
    and help services. The same for the desktop and the headless runtime; returns the context."""
    # ProfileManager needs the context to already exist (it reads/
    # writes config through it), so it's attached right after
    # construction rather than passed into AppContext's constructor.
    # Its __init__ also runs the legacy-user migration — see
    # core/profile_manager.py.
    context.profiles = ProfileManager(context)
    context.households = HouseholdManager(context)
    context.undo = UndoLog()
    # Propose → Approve → Execute → Record → Undo (core/actions.py).
    context.actions = ActionCenter()
    # MIA's own browser (DEC-0117): nothing starts until she's asked to open a page.
    context.browsers = Browsers(context)
    context.notifications = NotificationManager(context)
    # Mobile access, Phase 1 (2026-09-12) — cheap to construct
    # unconditionally like every other manager here; only the
    # opt-in server thread itself (_start_mobile_server(), called
    # from run()) is gated behind server.enabled.
    context.push_subscriptions = PushSubscriptionManager(context)
    context.calendar = CalendarManager(context)
    context.alarms = AlarmManager(context)
    context.journal = JournalManager(context)
    context.inventory = InventoryManager(context)
    context.data_logger = DataLoggerManager(context)
    context.components = ComponentManager(context)
    context.materials = MaterialManager(context)
    context.products = ProductManager(context)
    # Jobs references both materials and products
    # (consume_material()/produce_product()/total_cost() reach into
    # context.materials/context.products), so it's
    # constructed after both already are — same ordering precedent
    # as Trips/Waypoints/Inventory in core/application.py.
    context.jobs = JobManager(context)
    # Ledger references products (record_sale() reaches into
    # context.products), so it's constructed after products
    # already is, same ordering precedent as above.
    context.ledger = LedgerManager(context)
    from core.craft_recipes import CraftRecipeBook

    context.craft_recipes = CraftRecipeBook(context)  # crafting recipes (DEC-0030)
    from core.business_book import BusinessBook

    context.business = BusinessBook(context)  # quotes, customers, orders (DEC-0030)
    from core.grow_lab import GrowLab

    context.grow_lab = GrowLab(context)  # the grow lab (DEC-0030)
    from core.security_cams import SecurityBook

    context.security = SecurityBook(context)  # cameras (DEC-0033)
    from core.security_log import SecurityLog

    context.security_log = SecurityLog()  # who signed in from where (docs/SECURITY.md step 3)
    from core.security_log import on_account_change

    # A password or email changed at the desktop is logged too (the web logs its own with the device).
    context.events.subscribe("profile.password_changed", on_account_change(context, "password_changed"))
    context.events.subscribe("profile.email_changed", on_account_change(context, "email_changed"))
    from core import progress_history

    progress_history.subscribe(context)  # a prestige or reward unlocked, kept in that person's history
    from core.insurance import InsuranceBook

    context.insurance = InsuranceBook(context)  # the insurance check-up (DEC-0034)
    from core.flock import FlockBook

    context.flock = FlockBook(context)  # chickens (DEC-0037)
    from core.record_sets import RecordSets

    context.record_sets = RecordSets(context)  # the household's record sets (DEC-0089)
    from core.obligations import ObligationBook

    context.obligations = ObligationBook(context)  # tax and compliance deadlines (DEC-0040)
    context.reference_library = ReferenceLibraryManager(context)
    # The Library's plans shelf: built-in plans, kept ones, and plan files (core/plan_library.py).
    context.plans = PlanLibrary(context)
    context.llm = LLMManager(context)
    # Online/offline awareness — first check starts now in the
    # background; see core/connectivity.py.
    context.connectivity = ConnectivityMonitor(context)
    context.connectivity.refresh_async()
    context.online_reminders = OnlineReminders(context)
    context.voice = VoiceManager(context)
    context.waypoints = WaypointManager(context)
    context.power = PowerManager(context)
    context.volume = VolumeManager(context)
    context.devices = DeviceFramework(context)
    context.scripts = ScriptLibraryManager(context)
    # Trips references waypoints/inventory/journal, so it's
    # constructed after all three are already on the context.
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.projects = ProjectManager(context)
    context.intents = IntentManager(context)
    context.tasks = TaskManager(context)
    # Memories is read-only aggregation over Expeditions/Trips/
    # Waypoints/Journal, so it's constructed after all four are
    # already on the context, same reasoning as Trips above.
    context.memories = MemoryManager(context)
    # "My Hero's Path" — constructed before Missions since
    # _credit_mission_rewards() now optionally credits skill XP
    # through it (Mission.skill_rewards).
    context.skills = SkillManager(context)
    # Missions references trips (for the trip_duration_hours metric
    # type) and skills (for skill_rewards crediting), so it's
    # constructed after both already are.
    context.missions = MissionManager(context)
    # Mission Pathways — subscribes to Missions' new
    # "mission.completed" event at construction, so it must be
    # constructed after context.missions already exists (the
    # subscription itself doesn't need Missions to exist yet, but
    # this ordering matches every other "reacts to X" manager's
    # own construction-order convention).
    context.pathways = PathwayManager(context)
    # Recurring Missions — same "subscribes to mission.completed at
    # construction" ordering rule as Pathways just above.
    context.recurring_missions = RecurringMissionManager(context)
    from core import upkeep_missions

    upkeep_missions.wire(context)  # DEC-0153: an upkeep mission done marks its upkeep done
    # Discovery references skills/projects/intents/missions (all
    # read-only, to build its generation prompt), so it's
    # constructed after all four already are — same reasoning as
    # Pathways above.
    context.discovery = DiscoveryManager(context)
    context.conversations = ConversationManager(context)
    context.user_memories = UserMemoryManager(context)
    context.private_journal = PrivateJournalManager(context)
    context.communication = CommunicationGate(context)
    context.business_use = BusinessUseManager(context)
    context.ocr = OcrQueue(context)
    context.textbooks = TextbookManager(context)
    context.inbox = InboxManager(context)
    context.inbox_mail = MailChecker(context.inbox, MailSettings(context), MailVault())
    context.dashboard_widgets = DashboardWidgetRegistry(context)
    context.avatar = AvatarManager(context)
    context.finance = FinanceManager(context)
    context.homestead = HomesteadManager(context)
    from core.greenhouse_link import GreenhouseLink

    context.greenhouse_link = GreenhouseLink(context)  # "take over the greenhouse" (DEC-0150)
    context.lite_captures = LiteCaptureManager(context)
    context.maintenance = MaintenanceManager(context)
    context.insights = InsightManager(context)
    context.budget = BudgetManager(context)
    context.net_worth = NetWorthHistory(context)
    context.real_estate = RealEstateManager(context)
    context.energy = EnergyManager(context)
    from core.sensors import SensorStore

    context.sensors = SensorStore(context)  # sensors that send their own readings (core/sensors.py)
    context.plaid = PlaidManager(context)
    context.map_tiles = MapTileCache(context)
    context.trail_maps = TrailMapLibrary(context)
    context.music = MusicManager(context)
    context.kitchen = KitchenManager(context)
    context.workout = WorkoutManager(context)
    # Rewards — reads real stat data from maintenance/missions/workout
    # and unlocks against context.profiles, so it's constructed last
    # among those four (see core/rewards_manager.py's own docstring).
    context.rewards = RewardsManager(context)
    context.relationships = RelationshipsManager(context)
    context.classroom = ClassroomManager(context)
    # What happened (core/life_events.py): the household's history.
    context.life_events = LifeEventLog(context)
    # How things relate (core/links.py): the household's stated links.
    context.links = LinkStore(context)
    # Each person's own things and their household's shared things
    # (core/personal_data.py): swapped in on every sign-in. After every
    # store above, so the device's first household keeps those.
    context.personal_data = PersonalData(context)
    context.personal_data.watch(context.events)
    context.personal_data.activate_current()
    context.workshop_machines = WorkshopMachineRegistry(context)
    # Registered by default so the registry has something real to
    # demonstrate end-to-end — it's a stub (no real driver), not a
    # working device, see core/workshop_machine.py's docstring.
    context.workshop_machines.register(LaserEngraverMachine())
    context.module_manager = ModuleManager(context)
    context.search = SearchManager(context)
    context.device_help = DeviceHelpManager(context)
    context.activity_log = ActivityLogManager(context)
    context.usage_tracker = UsageTracker(context)
    # module_manager.all is stored as a callable, not called now — it's
    # still empty until context.module_manager.discover() runs later in
    # the boot sequence (run()'s boot_steps), and device_help/
    # activity_log only invoke it lazily on their own first use anyway.
    context.device_help.register_module_lister(context.module_manager.all)
    context.activity_log.register_module_lister(context.module_manager.all)
    context.device_help.register_reference_library(context.reference_library)
    return context


class Runtime(BackgroundJobs, AssistantTools):
    """A whole MIA with no window: every service, the full tool registry, the background schedule and the phone
    server (see the module's opening)."""

    def __init__(self, config: Optional[ConfigManager] = None, events: Optional[EventBus] = None,
                 take_lock: bool = True) -> None:
        """Builds MIA without starting anything: the one-MIA lock for this data folder (RuntimeError when another MIA
        holds it), a restore chosen before the restart, the config, the event bus, the store lock, every service,
        the tools and the schedule. `take_lock=False` is for tests on a temporary folder."""
        from core import instance_lock
        from core.backup_manager import apply_pending_restore
        from core.store_lock import StoreLock

        if take_lock:
            if not instance_lock.acquire():
                raise RuntimeError("MIA is already running on this data folder.")
            apply_pending_restore()  # before anything has read its files
        context = AppContext(config=config or ConfigManager(), events=events or EventBus())
        context.store_lock = StoreLock()  # shared with the phone server (server/app.py)
        build_services(context)
        BackgroundJobs.__init__(self, context, context.module_manager)
        self._register_assistant_actions()
        self.scheduler = Scheduler(lock=context.store_lock)
        self.schedule(self.scheduler)
        context.scheduler = self.scheduler
        context.runtime = self
        self.started_at = ""
        self._started = 0.0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self, serve: bool = True) -> None:
        """Starts the schedule on its own thread and, with `serve`, the phone server when it's switched on
        (server.enabled). A phone server that can't start is logged and doesn't stop the rest."""
        if self._thread is not None:
            return
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self._started = time.monotonic()
        self._stop.clear()
        with self.context.store_lock:
            try:  # a mission already overdue is assigned now, not in five minutes (as the desktop does at boot)
                self._check_mission_auto_assignment()
            except Exception:  # noqa: BLE001 - never stops the start
                log.exception("The first mission check failed.")
        self._thread = threading.Thread(target=self.scheduler.run_forever, args=(self._stop,), name="mia-schedule",
                                        daemon=True)
        self._thread.start()
        if serve:
            try:
                from core.phone_server import PhoneServer

                self.context.phone_server = PhoneServer(self.context)
                if self.context.phone_server.enabled:
                    self.context.phone_server.start()
            except Exception:  # noqa: BLE001 - the schedule runs with or without the phone
                log.exception("The phone server couldn't start.")
        log.info("The MIA Runtime is up: %d services, %d tools, %d scheduled jobs.", len(self.services()),
                 len(self.context.assistant_actions._actions), len(JOBS))

    def stop(self) -> None:
        """Stops the schedule (waiting for a job in progress, up to 30 seconds) and the phone server."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=30)
            self._thread = None
        server = getattr(self.context, "phone_server", None)
        if server is not None:
            try:
                server.stop()
            except Exception:  # noqa: BLE001 - stopping is best effort
                log.exception("The phone server didn't stop cleanly.")

    def services(self) -> list[str]:
        """The names of the services on the context (the fields that hold one)."""
        from dataclasses import fields

        return sorted(f.name for f in fields(self.context) if getattr(self.context, f.name, None) is not None)

    def health(self) -> dict:
        """How this MIA is doing: whether the schedule is running, since when and for how long, each job's record
        (core.scheduler.Scheduler.status), how many jobs have failed or never run, whether the model answers, and
        whether the phone server is up, and where her files are (core/data_root.describe). For /api/runtime/health and
        Diagnostics."""
        jobs = self.scheduler.status()
        running = self._thread is not None and self._thread.is_alive()
        llm = getattr(self.context, "llm", None)
        try:
            model = bool(llm is not None and llm.is_available())
        except Exception:  # noqa: BLE001 - a model that can't be asked isn't available
            model = False
        server = getattr(self.context, "phone_server", None)
        return {
            "running": running, "started_at": self.started_at,
            "uptime_seconds": round(time.monotonic() - self._started) if running else 0,
            "jobs": jobs, "jobs_failing": [j["name"] for j in jobs if j["last_error"]],
            "services": len(self.services()), "tools": len(self.context.assistant_actions._actions),
            "model_available": model, "phone_server": bool(server is not None and getattr(server, "running", False)),
            "window": False, "home": data_root.describe(),
        }

    def run_until_stopped(self) -> None:
        """Starts, then waits for Ctrl+C or a stop signal (SIGTERM, what a service manager sends), and stops."""
        import signal

        def asked(*_args) -> None:
            """A stop was asked for."""
            self._stop.set()
        for name in ("SIGTERM", "SIGINT"):
            try:
                signal.signal(getattr(signal, name), asked)
            except (ValueError, OSError, AttributeError):  # not the main thread, or not on this system
                pass
        self.start()
        try:
            while not self._stop.wait(1.0):
                pass
        finally:
            self.stop()
            log.info("The MIA Runtime has stopped.")


def main() -> int:
    """`python -m core.runtime`: runs MIA with no window until told to stop. 1 when another MIA already holds this
    data folder."""
    try:
        runtime = Runtime()
    except RuntimeError as problem:
        print(problem)
        return 1
    runtime.run_until_stopped()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
