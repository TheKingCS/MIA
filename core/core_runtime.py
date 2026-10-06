"""
core.core_runtime
===================

Builds the `AppContext` and curated Assistant action registry for
**headless MIA Core** — docs/VISION.md's 2026-07-15 "Core drops its GUI
entirely" split. Core is a voice-first, screen-free runtime (the Pi 5 +
AI HAT+2 Receiver hardware, docs/HARDWARE.md): push-to-talk button in,
speech out, no `gui/`/`modules/` construction at all. Home
(`core/application.py`'s `MIAApplication`) is the only place the full
PySide6 desktop shell — and its much larger Assistant action registry —
lives.

**Deliberately gui-free**: nothing in this file imports `PySide6` or
`gui.*`, directly or transitively, so a Core deployment never needs
Qt/PySide6 installed at all (a real footprint concern on the Pi 5's
constrained storage/RAM, not just architectural tidiness — see the
memory of the 2026-07-17/18 Pi5 bring-up session's "the pi5 doesn't
need everything that MIA Home needs" correction). `core/module_manager.py`
is still constructed below (cheap — it doesn't import anything from
`modules/` until `.discover()` runs, and this file never calls that),
so `context.module_manager`-dependent handlers (just `open_module`,
which Core's own registry below doesn't even register) degrade
gracefully instead of crashing, same as every other "hardware/feature
not present here" case in this codebase.

**Curated, not full parity, Assistant action registry.** Every handler
in `core/application.py`'s `_register_assistant_actions()` is a
`@staticmethod` — a pure function of `(context, arguments)` with zero
dependency on `MIAApplication` itself (confirmed while scoping this
file) — which is what makes it safe to reuse a subset of that same
logic here without importing `core.application` (and its gui.* imports)
at all. Rather than transcribing all ~65 actions, this file registers
the smaller slice that actually makes sense for a screen-free personal
voice companion: alarms, notes, inventory, calendar, waypoints,
missions, recent activity/system health/power status. Left out
deliberately, not by oversight:
- `open_module`/`set_theme`/anything GUI-navigation-only — there's no
  screen to navigate.
- Workshop/Field Kit/Maps/Project Manager/Expedition-trip-detail
  actions — genuinely Home-desktop-scoped surfaces (production
  pipelines, device flashing, cartography, kanban boards); nothing
  about the hardware forces this, it's a real product-scope call that
  can be revisited once this first slice is validated against actual
  use on the Pi.
- `get_sun_moon_info` — its handler imports `modules.navigation.module`
  for `format_sun_moon_summary()`, which would drag a `modules/`/PySide6
  import into a supposedly gui-free process; worth moving that helper
  into `core/` before adding it here, not silently skipping forever.
Handler bodies below are intentionally short, independent copies of
their `core/application.py` counterparts (same pattern as
`tests/run_module.py` already being its own independent AppContext
wiring point) — see that file if these two ever need to be reconciled.
"""

from __future__ import annotations

from core.activity_log_manager import ActivityLogManager
from core.usage_tracker import UsageTracker
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.assistant_actions import AssistantAction
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.connectivity import ConnectivityMonitor, connectivity_action
from core.device_help_manager import DeviceHelpManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.llm_manager import LLMManager
from core.logger import get_logger
from core.memory_manager import MemoryManager
from core.mission_manager import METRIC_TYPES as MISSION_METRIC_TYPES, MissionManager
from core.pathway_manager import PathwayManager
from core.discovery_manager import DiscoveryManager
from core.skill_manager import SkillManager
from core.module_manager import ModuleManager
from core.notification_manager import NotificationManager
from core.power_manager import PowerManager
from core.household_manager import HouseholdManager
from core.undo_log import UndoLog
from core.profile_manager import ProfileManager
from core.reference_library_manager import ReferenceLibraryManager
from core.system_health import format_system_health, read_system_health
from core.trip_manager import TripManager
from core.user_memory_manager import UserMemoryManager
from core.private_journal import PrivateJournalManager
from core.talk_it_out import register_journal_actions
from core.voice_manager import VoiceManager
from core.waypoint_manager import WAYPOINT_CATEGORIES, WaypointManager
from core.assistant_why_actions import register_why_actions
from core.budget_manager import BudgetManager
from core.intent_manager import IntentManager
from core.personal_data import PersonalData
from core.project_manager import ProjectManager
from core.real_estate_manager import RealEstateManager

log = get_logger(__name__)


def build_core_context(config: ConfigManager, events: EventBus) -> AppContext:
    """
    Constructs the manager subset a headless Core voice loop needs.
    Mirrors `MIAApplication.__init__`'s construction order/dependency
    rules (waypoints/inventory/journal before expeditions/trips before
    memories/missions) but only for the managers this scope actually
    uses — see this module's docstring for what's deliberately excluded.
    """
    context = AppContext(config=config, events=events)

    context.profiles = ProfileManager(context)
    context.households = HouseholdManager(context)
    context.undo = UndoLog()
    from core.actions import ActionCenter

    context.actions = ActionCenter()
    context.notifications = NotificationManager(context)
    context.calendar = CalendarManager(context)
    context.alarms = AlarmManager(context)
    context.journal = JournalManager(context)
    context.inventory = InventoryManager(context)
    context.reference_library = ReferenceLibraryManager(context)
    context.llm = LLMManager(context)
    context.connectivity = ConnectivityMonitor(context)
    context.connectivity.refresh_async()
    context.voice = VoiceManager(context)
    context.waypoints = WaypointManager(context)
    context.power = PowerManager(context)
    # Expeditions/Trips referenced by Missions (trip_duration_hours
    # metric type) and by add_mission's optional trip_name link below,
    # so constructed before Memories/Missions, same ordering rule as
    # core/application.py.
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.memories = MemoryManager(context)
    # "My Hero's Path" — constructed before Missions since
    # _credit_mission_rewards() now optionally credits skill XP
    # through it (Mission.skill_rewards), same ordering rule as
    # core/application.py.
    context.skills = SkillManager(context)
    context.missions = MissionManager(context)
    # Mission Pathways — subscribes to Missions' "mission.completed"
    # event at construction, same ordering rule as core/application.py.
    context.pathways = PathwayManager(context)
    # Discovery — references skills/missions (projects/intents aren't
    # wired in this headless scope; it degrades gracefully without
    # them, same as every other optional-service check here), same
    # ordering rule as core/application.py.
    context.discovery = DiscoveryManager(context)
    context.user_memories = UserMemoryManager(context)
    context.private_journal = PrivateJournalManager(context)
    # 2026-09-28: what "remind me why" (Perspective, core/why_graph.py)
    # reads: the owner's reasons and the evidence for them (debts paid
    # down, builds, rentals). All gui-free, cheap JSON loads.
    context.intents = IntentManager(context)
    context.budget = BudgetManager(context)
    context.projects = ProjectManager(context)
    context.real_estate = RealEstateManager(context)
    # 2026-10-05 (Engine Phase 1): the rest of what Life State v2 reads
    # (core/context_assembler.py), so a headless MIA (the state export,
    # a server without the desktop) sees the same picture. Cheap JSON loads.
    from core.data_logger_manager import DataLoggerManager
    from core.kitchen_manager import KitchenManager
    from core.maintenance_manager import MaintenanceManager
    from core.recurring_mission_manager import RecurringMissionManager
    from core.relationships_manager import RelationshipsManager
    from core.task_manager import TaskManager

    context.data_logger = DataLoggerManager(context)
    context.maintenance = MaintenanceManager(context)
    context.tasks = TaskManager(context)
    context.kitchen = KitchenManager(context)
    context.relationships = RelationshipsManager(context)
    context.recurring_missions = RecurringMissionManager(context)
    from core.life_events import LifeEventLog

    context.life_events = LifeEventLog(context)
    from core.links import LinkStore

    context.links = LinkStore(context)
    # Each person's own stores (core/personal_data.py), as on the desktop.
    context.personal_data = PersonalData(context)
    context.personal_data.watch(events)
    context.personal_data.activate_current()
    # Challenge chains, hidden achievements and prestige emblems (the web's
    # Skills and Character screens, 2026-10-06), as on the desktop.
    from core.rewards_manager import RewardsManager

    context.rewards = RewardsManager(context)

    # Constructed but never `.discover()`-ed — stays empty for the life
    # of a headless Core process, so `open_module` (not registered
    # below anyway) and anything else touching it degrades gracefully
    # rather than crashing. See this module's docstring.
    context.module_manager = ModuleManager(context)
    context.device_help = DeviceHelpManager(context)
    context.activity_log = ActivityLogManager(context)
    context.usage_tracker = UsageTracker(context)
    context.device_help.register_module_lister(context.module_manager.all)
    context.activity_log.register_module_lister(context.module_manager.all)
    context.device_help.register_reference_library(context.reference_library)

    _register_core_assistant_actions(context)
    return context


def _register_core_assistant_actions(context: AppContext) -> None:
    """Registers Core's curated Assistant action subset — see this module's docstring."""
    registry = context.assistant_actions
    registry.register(connectivity_action())
    register_journal_actions(registry)
    register_why_actions(registry)

    registry.register(AssistantAction(
        name="add_alarm",
        domain="alarms",
        description="Create a new alarm in MIA",
        parameters={
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "A short name for the alarm."},
                "time": {"type": "string", "description": "Time in 24-hour HH:MM format, e.g. '07:00'."},
            },
            "required": ["label", "time"],
        },
        handler=_action_add_alarm,
        trigger_phrases=("set an alarm", "set a timer", "add an alarm", "remind me", "wake me up"),
    ))
    registry.register(AssistantAction(
        name="list_alarms",
        domain="alarms",
        description="List the user's current alarms in MIA",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_list_alarms,
        trigger_phrases=(
            "list my alarms", "list alarms", "what alarms", "show my alarms", "do i have any alarms",
            "next alarm", "when is my alarm",
        ),
    ))
    registry.register(AssistantAction(
        name="delete_alarm",
        domain="alarms",
        destructive=True,
        description="Delete an existing alarm in MIA by its label.",
        parameters={
            "type": "object",
            "properties": {"label": {"type": "string", "description": "The label of the alarm to delete, e.g. 'Wake Up'."}},
            "required": ["label"],
        },
        handler=_action_delete_alarm,
        trigger_phrases=("delete an alarm", "delete alarm", "remove an alarm", "remove alarm", "cancel my alarm", "cancel the alarm", "alarm "),
    ))

    registry.register(AssistantAction(
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
        handler=_action_add_note,
        trigger_phrases=("add a note", "take a note", "make a note", "write down", "jot down"),
    ))
    registry.register(AssistantAction(
        name="list_notes",
        domain="notes",
        description=(
            "List or search the user's journal/note entries in MIA's Notes module. "
            "Leave query empty to list everything, most recently updated first."
        ),
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Optional keyword to search titles/bodies/tags for."}},
            "required": [],
        },
        handler=_action_list_notes,
        trigger_phrases=(
            "show me my notes", "show my notes", "list my notes", "list notes",
            "search my notes", "search notes", "find a note", "read my notes", "what notes do i have",
            "anything i wrote down", "what did i write down",
        ),
    ))
    registry.register(AssistantAction(
        name="delete_note",
        domain="notes",
        destructive=True,
        description="Delete an existing journal/note entry in MIA's Notes module by its title.",
        parameters={
            "type": "object",
            "properties": {"title": {"type": "string", "description": "The title of the note to delete."}},
            "required": ["title"],
        },
        handler=_action_delete_note,
        trigger_phrases=("delete a note", "delete the note", "delete note", "delete my note", "remove a note", "remove the note", "remove note"),
    ))

    registry.register(AssistantAction(
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
        handler=_action_add_inventory_item,
        trigger_phrases=("add to inventory", "add an inventory item", "inventory item"),
    ))
    registry.register(AssistantAction(
        name="list_inventory",
        domain="inventory",
        description=(
            "List or search MIA's Inventory tool, including quantities. "
            "Use this to answer 'how many X do I have' questions about "
            "inventory items. Leave query empty to list everything."
        ),
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Optional keyword to search item names/categories/notes for."}},
            "required": [],
        },
        handler=_action_list_inventory,
        trigger_phrases=("inventory", "do i have"),
    ))
    registry.register(AssistantAction(
        name="delete_inventory_item",
        domain="inventory",
        destructive=True,
        description="Remove an item entirely from MIA's Inventory tool by name.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The name of the item to remove."}},
            "required": ["name"],
        },
        handler=_action_delete_inventory_item,
        trigger_phrases=("delete from inventory", "delete an inventory item", "remove from inventory", "remove an inventory item"),
    ))
    registry.register(AssistantAction(
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
        handler=_action_adjust_inventory_quantity,
        trigger_phrases=("i used", "used up", "use up", "got more", "received more"),
    ))

    registry.register(AssistantAction(
        name="add_calendar_event",
        domain="calendar",
        description="Add a new event to MIA's Calendar.",
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
        handler=_action_add_calendar_event,
        trigger_phrases=("add an event", "add a calendar event", "schedule an event", "new calendar event"),
    ))
    registry.register(AssistantAction(
        name="list_calendar_events",
        domain="calendar",
        description=(
            "List the user's upcoming/scheduled Calendar events in MIA — what's coming up "
            "today, this week, or on any date. Not for past activity — see recall_recent_activity for that."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_list_calendar_events,
        trigger_phrases=(
            "list my events", "list my calendar", "what's on my calendar", "upcoming events", "show my calendar",
            "anything on my calendar", "anything today", "going on this week", "going on today",
        ),
    ))
    registry.register(AssistantAction(
        name="delete_calendar_event",
        domain="calendar",
        destructive=True,
        description="Delete an existing Calendar event in MIA by its title.",
        parameters={
            "type": "object",
            "properties": {"title": {"type": "string", "description": "The title of the event to delete."}},
            "required": ["title"],
        },
        handler=_action_delete_calendar_event,
        trigger_phrases=("delete an event", "delete the event", "remove an event", "cancel the event", "event "),
    ))

    registry.register(AssistantAction(
        name="add_waypoint",
        domain="waypoints",
        description="Save a new named waypoint (location) in MIA's Navigation module.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "A short name for the waypoint."},
                "latitude": {"type": "number", "description": "Latitude in decimal degrees."},
                "longitude": {"type": "number", "description": "Longitude in decimal degrees."},
                "category": {"type": "string", "description": "Optional category: Campsite, Trailhead, Water Source, Viewpoint, or Other."},
            },
            "required": ["name", "latitude", "longitude"],
        },
        handler=_action_add_waypoint,
        trigger_phrases=("add a waypoint", "save a waypoint", "new waypoint", "mark a waypoint"),
    ))
    registry.register(AssistantAction(
        name="list_waypoints",
        domain="waypoints",
        description="List or search the user's saved waypoints (named locations) in MIA's Navigation module.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Optional keyword to search waypoint names/notes for."}},
            "required": [],
        },
        handler=_action_list_waypoints,
        # "way point"/"way points" added 2026-07-19 — see
        # core/application.py's twin registration for why: Vosk's small
        # STT model transcribes "waypoint(s)" as two separate words
        # every time in testing, so the bare "waypoint" trigger alone
        # never fires from real speech.
        trigger_phrases=(
            "waypoint", "waypoints", "list my waypoints", "list waypoints",
            "locations have i saved", "saved locations", "way point", "way points",
        ),
    ))
    registry.register(AssistantAction(
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
        handler=_action_waypoint_distance,
        trigger_phrases=("distance to", "distance from", "how far is", "how far apart", "bearing to", "bearing from"),
    ))

    registry.register(AssistantAction(
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
                "trip_name": {"type": "string", "description": "Optional name of an existing Trip to link this mission to (must already exist)."},
            },
            "required": ["name"],
        },
        handler=_action_add_mission,
        trigger_phrases=("start a mission", "new mission", "create a mission", "add a mission"),
    ))
    registry.register(AssistantAction(
        name="list_missions",
        domain="missions",
        description="List the user's Missions in MIA, including each objective's progress.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_list_missions,
        trigger_phrases=(
            "list my missions", "list missions", "what missions", "show my missions",
            "current mission", "my current mission", "my mission", "active mission", "what mission",
        ),
    ))
    registry.register(AssistantAction(
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
        handler=_action_add_objective,
        trigger_phrases=("add an objective", "new objective", "add a goal", "create an objective"),
    ))
    registry.register(AssistantAction(
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
        handler=_action_log_mission_progress,
        trigger_phrases=("log a catch", "log progress", "count that", "add to my tally", "update my mission progress", "mark progress on my mission"),
    ))
    registry.register(AssistantAction(
        name="delete_mission",
        domain="missions",
        destructive=True,
        description="Delete an existing Mission in MIA by name.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The name of the mission to delete."}},
            "required": ["name"],
        },
        handler=_action_delete_mission,
        trigger_phrases=("delete a mission", "delete my mission", "remove a mission", "delete the mission"),
    ))
    registry.register(AssistantAction(
        name="complete_mission",
        domain="missions",
        description="Mark an existing Mission as completed in MIA by name.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The name of the mission to mark complete."}},
            "required": ["name"],
        },
        handler=_action_complete_mission,
        trigger_phrases=("complete my mission", "mark my mission complete", "finish my mission", "complete the mission", "mark the mission complete"),
    ))

    registry.register(AssistantAction(
        name="get_power_status",
        domain="power",
        description="Get this device's current battery/power status.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_power_status,
        trigger_phrases=(
            "battery level", "battery status", "power status", "how much battery", "how's my battery",
            "plugged in", "am i charging", "power percentage", "power level", "percent power", "how much power",
        ),
    ))
    registry.register(AssistantAction(
        name="get_system_health",
        domain="system",
        description="Get a live snapshot of this device's system health: CPU, memory, disk, temperature, and network usage.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_system_health,
        trigger_phrases=(
            "system health", "cpu usage", "cpu temperature", "memory usage",
            "disk usage", "diagnostics", "how's the system", "check diagnostics",
            "everything ok", "everything okay", "everything running",
        ),
    ))
    registry.register(AssistantAction(
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
                "keyword": {"type": "string", "description": "Optional keyword to filter activity by (e.g. a module or project name). Leave empty for everything recent."},
                "limit": {"type": "integer", "description": "How many recent entries to look at, default 20."},
            },
            "required": [],
        },
        handler=_action_recall_recent_activity,
        trigger_phrases=("recent activity", "activity log", "what have i done", "what have i been doing", "what did i do"),
    ))


# ----------------------------------------------------------------------
# Action handlers — independent copies of core/application.py's
# staticmethods (see this module's docstring for why). Each is a pure
# function of (context, arguments) -> str, exactly like its twin there.
# ----------------------------------------------------------------------

def _action_add_alarm(context: AppContext, arguments: dict) -> str:
    label = str(arguments.get("label", "") or "Alarm").strip() or "Alarm"
    time_str = str(arguments.get("time", "")).strip()
    if not time_str:
        return "I need a time (HH:MM) to set an alarm."
    alarm = context.alarms.add_alarm(label=label, time=time_str)
    return f"Alarm '{alarm.label}' set for {alarm.time}."


def _action_list_alarms(context: AppContext, arguments: dict) -> str:
    alarms = context.alarms.all_alarms()
    if not alarms:
        return "You have no alarms set."
    lines = [f"- '{a.label}' at {a.time}" + ("" if a.enabled else " (disabled)") for a in alarms]
    return "Your alarms:\n" + "\n".join(lines)


def _action_delete_alarm(context: AppContext, arguments: dict) -> str:
    label = str(arguments.get("label", "")).strip().lower()
    match = next((a for a in context.alarms.all_alarms() if a.label.lower() == label), None)
    if match is None:
        return f"I don't have an alarm called '{arguments.get('label', '')}'."
    context.alarms.delete_alarm(match.alarm_id)
    return f"Deleted the alarm '{match.label}'."


def _action_add_note(context: AppContext, arguments: dict) -> str:
    title = str(arguments.get("title", "")).strip()
    if not title:
        return "I need a title to add a note."
    body = str(arguments.get("body", ""))
    entry = context.journal.add_entry(title=title, body=body)
    return f"Note '{entry.title}' added."


def _action_list_notes(context: AppContext, arguments: dict) -> str:
    query = str(arguments.get("query", "") or "").strip()
    entries = context.journal.search(query) if query else context.journal.all_entries()
    if not entries:
        return "No matching notes found." if query else "You have no notes yet."
    lines = [f"- '{e.title}': {e.body}" if e.body else f"- '{e.title}'" for e in entries]
    return "Your notes:\n" + "\n".join(lines)


def _action_delete_note(context: AppContext, arguments: dict) -> str:
    title = str(arguments.get("title", "")).strip().lower()
    match = next((e for e in context.journal.all_entries() if e.title.lower() == title), None)
    if match is None:
        return f"I don't have a note titled '{arguments.get('title', '')}'."
    context.journal.delete_entry(match.entry_id)
    return f"Deleted the note '{match.title}'."


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


def _action_list_inventory(context: AppContext, arguments: dict) -> str:
    query = str(arguments.get("query", "") or "").strip()
    items = context.inventory.search(query) if query else context.inventory.all_items()
    if not items:
        return "No matching inventory items found." if query else "Your inventory is empty."
    lines = [f"- {i.quantity}x '{i.name}'" for i in items]
    return "Your inventory:\n" + "\n".join(lines)


def _action_delete_inventory_item(context: AppContext, arguments: dict) -> str:
    name = str(arguments.get("name", "")).strip().lower()
    match = next((i for i in context.inventory.all_items() if i.name.lower() == name), None)
    if match is None:
        return f"I don't have an inventory item called '{arguments.get('name', '')}'."
    context.inventory.delete_item(match.item_id)
    return f"Removed '{match.name}' from inventory."


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


def _action_list_calendar_events(context: AppContext, arguments: dict) -> str:
    events = context.calendar.all_events()
    if not events:
        return "You have no calendar events."
    lines = [f"- '{e.title}' on {e.date}" + (f" at {e.time}" if e.time else "") for e in events]
    return "Your calendar events:\n" + "\n".join(lines)


def _action_delete_calendar_event(context: AppContext, arguments: dict) -> str:
    title = str(arguments.get("title", "")).strip().lower()
    match = next((e for e in context.calendar.all_events() if e.title.lower() == title), None)
    if match is None:
        return f"I don't have a calendar event called '{arguments.get('title', '')}'."
    context.calendar.delete_event(match.event_id)
    return f"Deleted the calendar event '{match.title}'."


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
        category = ""
    waypoint = context.waypoints.add_waypoint(name=name, latitude=latitude, longitude=longitude, category=category)
    return f"Waypoint '{waypoint.name}' saved at ({waypoint.latitude:.5f}, {waypoint.longitude:.5f})."


def _action_list_waypoints(context: AppContext, arguments: dict) -> str:
    query = str(arguments.get("query", "") or "").lower().strip()
    waypoints = context.waypoints.all_waypoints()
    if query:
        waypoints = [w for w in waypoints if query in f"{w.name} {w.notes}".lower()]
    if not waypoints:
        return "No matching waypoints found." if query else "You have no waypoints saved."
    lines = [f"- '{w.name}' ({w.latitude:.5f}, {w.longitude:.5f})" for w in waypoints]
    return "Your waypoints:\n" + "\n".join(lines)


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


def _action_add_mission(context: AppContext, arguments: dict) -> str:
    name = str(arguments.get("name", "")).strip()
    if not name:
        return "I need a name to start a mission."
    trip_name = str(arguments.get("trip_name", "") or "").strip().lower()
    trip_id = None
    trip = None
    if trip_name:
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
        trip_id = trip.trip_id
    mission = context.missions.add_mission(name=name, trip_id=trip_id)
    linked_note = f" Linked to trip '{trip.name}'." if trip_id else ""
    return f"Mission '{mission.name}' created.{linked_note}"


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


def _action_delete_mission(context: AppContext, arguments: dict) -> str:
    name = str(arguments.get("name", "")).strip().lower()
    match = next((m for m in context.missions.all_missions() if m.name.lower() == name), None)
    if match is None:
        return f"I don't have a mission called '{arguments.get('name', '')}'."
    context.missions.delete_mission(match.mission_id)
    return f"Deleted the mission '{match.name}'."


def _action_complete_mission(context: AppContext, arguments: dict) -> str:
    name = str(arguments.get("name", "")).strip().lower()
    match = next((m for m in context.missions.all_missions() if m.name.lower() == name), None)
    if match is None:
        return f"I don't have a mission called '{arguments.get('name', '')}'."
    context.missions.update_mission(match.mission_id, status="completed")
    return f"Marked the mission '{match.name}' as completed. Nice work!"


def _action_get_power_status(context: AppContext, arguments: dict) -> str:
    status = context.power.read()
    if status is None:
        return "No battery or power status is available on this device."
    plugged = "plugged in" if status.plugged_in else "on battery"
    time_part = ""
    if status.seconds_left is not None:
        time_part = f", about {status.seconds_left // 60} minutes remaining"
    return f"Battery: {status.percent:.0f}% ({plugged}{time_part})."


def _action_get_system_health(context: AppContext, arguments: dict) -> str:
    return format_system_health(read_system_health())


def _action_recall_recent_activity(context: AppContext, arguments: dict) -> str:
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
