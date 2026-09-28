"""
core.app_context
=================

Defines AppContext: a small bundle of shared services (config, logger
factory, event bus) that gets handed to every module and every GUI
component.

Why this exists: modules and GUI screens need access to core services,
but we don't want them reaching for globals (e.g. `import core.state as
state; state.config`) because that makes testing hard and hides
dependencies. Instead, everything that needs core services receives one
`AppContext` object at construction time. This is a lightweight form of
dependency injection — enough structure to keep things testable, without
pulling in a DI framework this project doesn't need yet.

Any new core-level service (e.g. a future "hardware" service for
robotics, or a "local_ai" service) should be added as an attribute here
and constructed in core/application.py, not scattered as ad-hoc imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from core.assistant_actions import AssistantActionRegistry
from core.calculator_engine import CalculatorEngine
from core.config_manager import ConfigManager
from core.event_bus import EventBus

if TYPE_CHECKING:
    from core.activity_log_manager import ActivityLogManager
    from core.alarm_manager import AlarmManager
    from core.avatar_manager import AvatarManager
    from core.budget_manager import BudgetManager
    from core.plaid_manager import PlaidManager
    from core.real_estate_manager import RealEstateManager
    from core.calendar_manager import CalendarManager
    from core.classroom_manager import ClassroomManager
    from core.component_manager import ComponentManager
    from core.maintenance_manager import MaintenanceManager
    from core.material_manager import MaterialManager
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
    from core.lite_capture_manager import LiteCaptureManager
    from core.intent_manager import IntentManager
    from core.insight_manager import InsightManager
    from core.inventory_manager import InventoryManager
    from core.job_manager import JobManager
    from core.journal_manager import JournalManager
    from core.kitchen_manager import KitchenManager
    from core.ledger_manager import LedgerManager
    from core.llm_manager import LLMManager
    from core.map_tile_cache import MapTileCache
    from core.memory_manager import MemoryManager
    from core.mission_manager import MissionManager
    from core.module_manager import ModuleManager
    from core.music_manager import MusicManager
    from core.notification_manager import NotificationManager
    from core.pathway_manager import PathwayManager
    from core.power_manager import PowerManager
    from core.profile_manager import ProfileManager
    from core.product_manager import ProductManager
    from core.push_subscription_manager import PushSubscriptionManager
    from core.connectivity import ConnectivityMonitor
    from core.recurring_mission_manager import RecurringMissionManager
    from core.project_manager import ProjectManager
    from core.reference_library_manager import ReferenceLibraryManager
    from core.rewards_manager import RewardsManager
    from core.relationships_manager import RelationshipsManager
    from core.script_library_manager import ScriptLibraryManager
    from core.search_manager import SearchManager
    from core.skill_manager import SkillManager
    from core.task_manager import TaskManager
    from core.trail_map_library import TrailMapLibrary
    from core.trip_manager import TripManager
    from core.usage_tracker import UsageTracker
    from core.user_memory_manager import UserMemoryManager
    from core.private_journal import PrivateJournalManager
    from core.communication_gate import CommunicationGate
    from core.business_use import BusinessUseManager
    from core.textbook_manager import TextbookManager
    from core.inbox_manager import InboxManager
    from core.inbox_mail import MailChecker
    from core.ocr import OcrQueue
    from core.online_watch import OnlineReminders
    from core.phone_server import PhoneServer
    from core.voice_manager import VoiceManager
    from core.volume_manager import VolumeManager
    from core.waypoint_manager import WaypointManager
    from core.workout_manager import WorkoutManager
    from core.workshop_machine import WorkshopMachineRegistry


@dataclass
class AppContext:
    """Shared services passed to modules and GUI components."""

    config: ConfigManager
    events: EventBus
    # Assigned by MIAApplication right after construction (each of
    # these takes an AppContext, so none can be created in the same
    # dataclass __init__ call — see core/application.py). Optional here
    # so AppContext remains constructible on its own for tests.
    profiles: Optional["ProfileManager"] = field(default=None, repr=False)
    notifications: Optional["NotificationManager"] = field(default=None, repr=False)
    search: Optional["SearchManager"] = field(default=None, repr=False)
    calendar: Optional["CalendarManager"] = field(default=None, repr=False)
    alarms: Optional["AlarmManager"] = field(default=None, repr=False)
    journal: Optional["JournalManager"] = field(default=None, repr=False)
    inventory: Optional["InventoryManager"] = field(default=None, repr=False)
    # Connective-infrastructure pass, phase 3 (2026-09-11) — the
    # observe->insight->recommend layer, piloted in Maintenance
    # (core/maintenance_insights.py). See core/insight_manager.py's own
    # docstring for why Insight/Recommendation are real new entities
    # rather than derived like everything else in that pass.
    insights: Optional["InsightManager"] = field(default=None, repr=False)
    reference_library: Optional["ReferenceLibraryManager"] = field(default=None, repr=False)
    llm: Optional["LLMManager"] = field(default=None, repr=False)
    voice: Optional["VoiceManager"] = field(default=None, repr=False)
    device_help: Optional["DeviceHelpManager"] = field(default=None, repr=False)
    power: Optional["PowerManager"] = field(default=None, repr=False)
    data_logger: Optional["DataLoggerManager"] = field(default=None, repr=False)
    energy: Optional["EnergyManager"] = field(default=None, repr=False)
    components: Optional["ComponentManager"] = field(default=None, repr=False)
    materials: Optional["MaterialManager"] = field(default=None, repr=False)
    jobs: Optional["JobManager"] = field(default=None, repr=False)
    products: Optional["ProductManager"] = field(default=None, repr=False)
    ledger: Optional["LedgerManager"] = field(default=None, repr=False)
    activity_log: Optional["ActivityLogManager"] = field(default=None, repr=False)
    waypoints: Optional["WaypointManager"] = field(default=None, repr=False)
    devices: Optional["DeviceFramework"] = field(default=None, repr=False)
    scripts: Optional["ScriptLibraryManager"] = field(default=None, repr=False)
    expeditions: Optional["ExpeditionManager"] = field(default=None, repr=False)
    trips: Optional["TripManager"] = field(default=None, repr=False)
    projects: Optional["ProjectManager"] = field(default=None, repr=False)
    # Connective-infrastructure pass (2026-09-11, post Hero's Path
    # architecture review) — the "why" layer a Project can optionally
    # link to via Project.intent_id. See core/intent_manager.py's own
    # docstring for why this is a separate small manager rather than a
    # flag on Project.
    intents: Optional["IntentManager"] = field(default=None, repr=False)
    tasks: Optional["TaskManager"] = field(default=None, repr=False)
    memories: Optional["MemoryManager"] = field(default=None, repr=False)
    missions: Optional["MissionManager"] = field(default=None, repr=False)
    # "My Hero's Path" (2026-09-11) — the skill-tree layer underneath
    # Missions/the profile-wide Level above. See core/skill_manager.py's
    # own docstring for why definitions/progress are deliberately split
    # into two files instead of living on this one service alone.
    skills: Optional["SkillManager"] = field(default=None, repr=False)
    # Mission Pathways (2026-09-11) — user picks a skill, MIA hands
    # them a pre-authored sequence of real Missions that build it. See
    # core/pathway_manager.py's own docstring.
    pathways: Optional["PathwayManager"] = field(default=None, repr=False)
    # Discovery (2026-09-11) — the AI-generated counterpart to
    # Pathways: MIA proposes one Mission at a time from real Skill/
    # Project/Intent state, validated deterministically, accepted or
    # rejected by the user. See core/discovery_manager.py's own
    # docstring for the full design and what's deliberately deferred.
    discovery: Optional["DiscoveryManager"] = field(default=None, repr=False)
    volume: Optional["VolumeManager"] = field(default=None, repr=False)
    conversations: Optional["ConversationManager"] = field(default=None, repr=False)
    # Named user_memories, not memories, to stay distinct from the
    # pre-existing `memories` field above (core/memory_manager.py's
    # Expedition recaps) — same word, unrelated concept.
    user_memories: Optional["UserMemoryManager"] = field(default=None, repr=False)
    # The encrypted private journal (core/private_journal.py, Cognitive
    # Extension slice A). Writable while locked, readable only unlocked.
    private_journal: Optional["PrivateJournalManager"] = field(default=None, repr=False)
    # "Know when to speak" (core/communication_gate.py, Cognitive
    # Extension slice C): every unprompted message goes through here.
    communication: Optional["CommunicationGate"] = field(default=None, repr=False)
    # Finance #3 (core/business_use.py): business-use log for personal
    # equipment (the mower's lawn-care jobs) and the write-off worksheet.
    business_use: Optional["BusinessUseManager"] = field(default=None, repr=False)
    # Textbook tutor (core/textbook_manager.py): the owner's books, indexed
    # by page and chapter, for study and quiz conversations.
    textbooks: Optional["TextbookManager"] = field(default=None, repr=False)
    # Document inbox (core/inbox_manager.py): receipts, manuals and other
    # documents dropped, uploaded from the phone or emailed in, proposed
    # for filing; inbox_mail checks the optional mailbox (core/inbox_mail.py).
    inbox: Optional["InboxManager"] = field(default=None, repr=False)
    inbox_mail: Optional["MailChecker"] = field(default=None, repr=False)
    # Reading photos and scanned pages (core/ocr.py, Tesseract), in the
    # background; used by the inbox and the textbook tutor.
    ocr: Optional["OcrQueue"] = field(default=None, repr=False)
    # The phone API server (server/app.py), switched on/off from Settings
    # (core/phone_server.py).
    phone_server: Optional["PhoneServer"] = field(default=None, repr=False)
    # Runs a function on the main (GUI) thread; set by core/application.py.
    # Used by core/main_thread.publish() so events raised on the phone
    # server's thread reach screens safely.
    main_thread_call: Optional[Callable[[Callable[[], None]], None]] = field(default=None, repr=False)
    # "Remind me when I'm back online" (core/online_watch.py).
    online_reminders: Optional["OnlineReminders"] = field(default=None, repr=False)
    dashboard_widgets: Optional["DashboardWidgetRegistry"] = field(default=None, repr=False)
    avatar: Optional["AvatarManager"] = field(default=None, repr=False)
    finance: Optional["FinanceManager"] = field(default=None, repr=False)
    homestead: Optional["HomesteadManager"] = field(default=None, repr=False)
    # MIA Lite (2026-09-14) — the receiving/processing side of the
    # field-capture tier docs/VISION.md's Core/Home split section
    # names. See core/lite_capture_manager.py's own docstring for what
    # this is (and deliberately isn't yet — no device-side capture or
    # wireless sync exists).
    lite_captures: Optional["LiteCaptureManager"] = field(default=None, repr=False)
    maintenance: Optional["MaintenanceManager"] = field(default=None, repr=False)
    budget: Optional["BudgetManager"] = field(default=None, repr=False)
    real_estate: Optional["RealEstateManager"] = field(default=None, repr=False)
    plaid: Optional["PlaidManager"] = field(default=None, repr=False)
    workshop_machines: Optional["WorkshopMachineRegistry"] = field(default=None, repr=False)
    map_tiles: Optional["MapTileCache"] = field(default=None, repr=False)
    trail_maps: Optional["TrailMapLibrary"] = field(default=None, repr=False)
    music: Optional["MusicManager"] = field(default=None, repr=False)
    kitchen: Optional["KitchenManager"] = field(default=None, repr=False)
    workout: Optional["WorkoutManager"] = field(default=None, repr=False)
    relationships: Optional["RelationshipsManager"] = field(default=None, repr=False)
    # Classroom (2026-09-11) — the user's own self-education content
    # model (Subjects -> Courses -> Lessons). v1 is deliberately just
    # the content structure; see core/classroom_manager.py's own
    # docstring for what's not built yet.
    classroom: Optional["ClassroomManager"] = field(default=None, repr=False)
    # Mobile access, Phase 1 (2026-09-12) — Web Push subscription
    # storage for the opt-in local API server (server/app.py). See
    # core/push_subscription_manager.py's own docstring; only
    # constructed when server.enabled is true (core/application.py),
    # so stays None everywhere else, same "optional service, degrades
    # gracefully" pattern as e.g. context.energy.
    push_subscriptions: Optional["PushSubscriptionManager"] = field(default=None, repr=False)
    # Online/offline awareness (2026-09-27) — whether the internet is
    # reachable, and which features need it. See core/connectivity.py.
    connectivity: Optional["ConnectivityMonitor"] = field(default=None, repr=False)
    # Recurring Missions (2026-09-13) — subscribes to Missions' own
    # "mission.completed" event at construction (same ordering rule as
    # Pathways above — must be constructed after context.missions
    # already exists).
    recurring_missions: Optional["RecurringMissionManager"] = field(default=None, repr=False)
    # Rewards (2026-09-14) — real lifetime stats (mower hours, workout
    # hours, missions completed, ...) unlocking real cosmetic/emblem
    # rewards at thresholds, CoD-style. See core/rewards_manager.py.
    rewards: Optional["RewardsManager"] = field(default=None, repr=False)
    # Set by MIAApplication (Home) or core/core_runtime.py (headless
    # Core) right after construction, same "assigned after the fact"
    # reason as profiles/etc. above. _action_open_module is the only
    # assistant action handler that needs it; every other handler is a
    # pure function of (context, arguments). Headless Core never calls
    # .discover() on it, so .all() stays empty and open_module degrades
    # to "there's no module called X" rather than crashing — there's no
    # screen to open one on anyway.
    module_manager: Optional["ModuleManager"] = field(default=None, repr=False)
    # Modular tutorial system, "never-used feature" walkthrough
    # suggestions (2026-09-14) — see core/usage_tracker.py's own
    # docstring for why this is a separate, never-pruned record from
    # context.activity_log's capped narrative log.
    usage_tracker: Optional["UsageTracker"] = field(default=None, repr=False)
    # CalculatorEngine/AssistantActionRegistry take no AppContext
    # dependency, so — unlike the services above — they can just be
    # constructed directly here.
    calculators: CalculatorEngine = field(default_factory=CalculatorEngine, repr=False)
    assistant_actions: AssistantActionRegistry = field(default_factory=AssistantActionRegistry, repr=False)
