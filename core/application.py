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
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.activity_log_manager import ActivityLogManager
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.assistant_actions import AssistantAction
from core.calendar_manager import CalendarManager
from core.component_manager import ComponentManager
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.device_framework import DeviceFramework
from core.device_help_manager import DeviceHelpManager
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.llm_manager import LLMManager
from core.logger import get_logger
from core.module_manager import ModuleManager
from core.notification_manager import NotificationManager
from core.power_manager import PowerManager
from core.profile_manager import ProfileManager
from core.reference_library_manager import ReferenceLibraryManager
from core.search_manager import SearchManager, SearchResult
from core.system_health import format_system_health, read_system_health
from core.voice_manager import VoiceManager
from core.waypoint_manager import WaypointManager
from gui.lock_screen import LockScreen
from gui.main_window import MainWindow
from gui.profile_select import ProfileSelectScreen
from gui.setup_wizard import SetupWizard
from gui.splash_screen import SplashScreen

log = get_logger(__name__)


class MIAApplication:
    """Owns the Qt application object and the startup sequence."""

    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("M.I.A.")

        self.config = ConfigManager()
        self.events = EventBus()
        self.context = AppContext(config=self.config, events=self.events)
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
        self.context.reference_library = ReferenceLibraryManager(self.context)
        self.context.llm = LLMManager(self.context)
        self.context.voice = VoiceManager(self.context)
        self.context.waypoints = WaypointManager(self.context)
        self.context.power = PowerManager(self.context)
        self.context.devices = DeviceFramework(self.context)
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

        self.splash: SplashScreen | None = None
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

    def _check_alarms(self) -> None:
        self.context.alarms.check_due(datetime.now())

    def _check_power(self) -> None:
        self.context.power.check_low_battery()

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
            description="List the user's current alarms in M.I.A.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_alarms,
            trigger_phrases=("list my alarms", "list alarms", "what alarms", "show my alarms", "do i have any alarms"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_alarm",
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
            description=(
                "List or search M.I.A.'s Inventory tool, including quantities. "
                "Leave query empty to list everything."
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
            trigger_phrases=("inventory", "do i have"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_inventory_item",
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

        # The splash screen steps through a short sequence of boot
        # messages before handing off to the wizard or main window. Using
        # a QTimer chain (rather than time.sleep) keeps the GUI responsive
        # during startup instead of freezing.
        boot_steps = [
            ("INITIALIZING CORE SYSTEMS...", self._noop),
            ("SYNCING CONFIGURATION MATRIX...", self._noop),
            ("SCANNING MODULE ARRAY...", self.module_manager.discover),
            ("ENGAGING INTERFACE...", self._noop),
        ]
        self._run_boot_steps(boot_steps, index=0)

        return self.qt_app.exec()

    def _run_boot_steps(self, steps: list[tuple[str, callable]], index: int) -> None:
        if index >= len(steps):
            self._finish_boot()
            return

        message, action = steps[index]
        self.splash.set_status(message)
        try:
            action()
        except Exception:
            log.exception("Error during boot step: %s", message)

        # 1400ms/step (5.6s total for the 4 steps below) — gives the
        # splash's pulsing core (gui/boot_core_widget.py) a couple of
        # full breathing cycles per step; the original 350ms made the
        # animation flash by too fast to register.
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

    @staticmethod
    def _noop() -> None:
        pass
