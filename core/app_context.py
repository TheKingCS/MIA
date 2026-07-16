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
from typing import TYPE_CHECKING, Optional

from core.assistant_actions import AssistantActionRegistry
from core.calculator_engine import CalculatorEngine
from core.config_manager import ConfigManager
from core.event_bus import EventBus

if TYPE_CHECKING:
    from core.activity_log_manager import ActivityLogManager
    from core.alarm_manager import AlarmManager
    from core.avatar_manager import AvatarManager
    from core.calendar_manager import CalendarManager
    from core.component_manager import ComponentManager
    from core.material_manager import MaterialManager
    from core.conversation_manager import ConversationManager
    from core.dashboard_widgets import DashboardWidgetRegistry
    from core.data_logger_manager import DataLoggerManager
    from core.device_framework import DeviceFramework
    from core.device_help_manager import DeviceHelpManager
    from core.expedition_manager import ExpeditionManager
    from core.finance_manager import FinanceManager
    from core.inventory_manager import InventoryManager
    from core.journal_manager import JournalManager
    from core.llm_manager import LLMManager
    from core.memory_manager import MemoryManager
    from core.mission_manager import MissionManager
    from core.notification_manager import NotificationManager
    from core.power_manager import PowerManager
    from core.profile_manager import ProfileManager
    from core.project_manager import ProjectManager
    from core.reference_library_manager import ReferenceLibraryManager
    from core.script_library_manager import ScriptLibraryManager
    from core.search_manager import SearchManager
    from core.task_manager import TaskManager
    from core.trip_manager import TripManager
    from core.user_memory_manager import UserMemoryManager
    from core.voice_manager import VoiceManager
    from core.volume_manager import VolumeManager
    from core.waypoint_manager import WaypointManager
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
    reference_library: Optional["ReferenceLibraryManager"] = field(default=None, repr=False)
    llm: Optional["LLMManager"] = field(default=None, repr=False)
    voice: Optional["VoiceManager"] = field(default=None, repr=False)
    device_help: Optional["DeviceHelpManager"] = field(default=None, repr=False)
    power: Optional["PowerManager"] = field(default=None, repr=False)
    data_logger: Optional["DataLoggerManager"] = field(default=None, repr=False)
    components: Optional["ComponentManager"] = field(default=None, repr=False)
    materials: Optional["MaterialManager"] = field(default=None, repr=False)
    activity_log: Optional["ActivityLogManager"] = field(default=None, repr=False)
    waypoints: Optional["WaypointManager"] = field(default=None, repr=False)
    devices: Optional["DeviceFramework"] = field(default=None, repr=False)
    scripts: Optional["ScriptLibraryManager"] = field(default=None, repr=False)
    expeditions: Optional["ExpeditionManager"] = field(default=None, repr=False)
    trips: Optional["TripManager"] = field(default=None, repr=False)
    projects: Optional["ProjectManager"] = field(default=None, repr=False)
    tasks: Optional["TaskManager"] = field(default=None, repr=False)
    memories: Optional["MemoryManager"] = field(default=None, repr=False)
    missions: Optional["MissionManager"] = field(default=None, repr=False)
    volume: Optional["VolumeManager"] = field(default=None, repr=False)
    conversations: Optional["ConversationManager"] = field(default=None, repr=False)
    # Named user_memories, not memories, to stay distinct from the
    # pre-existing `memories` field above (core/memory_manager.py's
    # Expedition recaps) — same word, unrelated concept.
    user_memories: Optional["UserMemoryManager"] = field(default=None, repr=False)
    dashboard_widgets: Optional["DashboardWidgetRegistry"] = field(default=None, repr=False)
    avatar: Optional["AvatarManager"] = field(default=None, repr=False)
    finance: Optional["FinanceManager"] = field(default=None, repr=False)
    workshop_machines: Optional["WorkshopMachineRegistry"] = field(default=None, repr=False)
    # CalculatorEngine/AssistantActionRegistry take no AppContext
    # dependency, so — unlike the services above — they can just be
    # constructed directly here.
    calculators: CalculatorEngine = field(default_factory=CalculatorEngine, repr=False)
    assistant_actions: AssistantActionRegistry = field(default_factory=AssistantActionRegistry, repr=False)
