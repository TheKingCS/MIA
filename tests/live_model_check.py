"""
tests.live_model_check
=========================

Golden-set regression check for the Assistant's tool-gating/grounding
decision (`modules.assistant.module.build_chat_request()`) against a
REAL running Ollama server — milestone 5.11. Not a pytest test (no
`test_` prefix, so pytest never collects it): every prior round of this
kind of verification (5.6's follow-up fix, 5.7-5.9, 5.10) was a
throwaway scratch script written fresh each time, re-deriving the same
setup and re-discovering some of the same categories of gaps. This
script is the same idea, kept around and extended instead of thrown
away, so growing the action registry further doesn't mean starting
from zero each time — this project's established rule ("re-verify
against the live model at each future batch of new actions, don't
assume scaling stays safe by design") now has a place to actually live.

Run with: `python tests/live_model_check.py` (needs `ollama serve`
running locally — see `systemctl --user status ollama`). Exits 0 if
every case passes, 1 otherwise, so it can be used as a manual gate
before committing new assistant actions.

Every manager's data file is redirected into a throwaway temp
directory before any manager is constructed — this script seeds real
alarms/notes/inventory/waypoints to test against, and must never write
into the developer's actual `data/*.json`. Tool CALLS ARE NEVER
EXECUTED here (only `reply.tool_calls` is inspected) — same convention
as every scratch script this session used — so even a wrongly-called
destructive action can't do anything, on top of the isolated data.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TEMP_DATA_DIR = Path(tempfile.mkdtemp(prefix="mia_live_model_check_"))

import core.alarm_manager as alarm_manager_module
import core.inventory_manager as inventory_manager_module
import core.journal_manager as journal_manager_module
import core.waypoint_manager as waypoint_manager_module

alarm_manager_module._DATA_DIR = _TEMP_DATA_DIR
alarm_manager_module._ALARMS_FILE = _TEMP_DATA_DIR / "alarms.json"
journal_manager_module._DATA_DIR = _TEMP_DATA_DIR
journal_manager_module._ENTRIES_FILE = _TEMP_DATA_DIR / "journal_entries.json"
inventory_manager_module._DATA_DIR = _TEMP_DATA_DIR
inventory_manager_module._ITEMS_FILE = _TEMP_DATA_DIR / "inventory_items.json"
waypoint_manager_module._DATA_DIR = _TEMP_DATA_DIR
waypoint_manager_module._WAYPOINTS_FILE = _TEMP_DATA_DIR / "waypoints.json"

from core.activity_log_manager import ActivityLogManager
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.application import MIAApplication
from core.assistant_actions import AssistantActionRegistry
from core.config_manager import ConfigManager
from core.device_help_manager import DeviceHelpManager
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.llm_manager import LLMManager
from core.module_manager import ModuleManager
from core.reference_library_manager import ReferenceLibraryManager
from core.waypoint_manager import WaypointManager
from modules.assistant.module import build_chat_request

# Tool names whose handlers mutate or delete real data — see this
# module's docstring on the "safe" expectation below.
_DESTRUCTIVE_TOOLS = {
    "delete_alarm", "delete_note", "delete_inventory_item",
    "adjust_inventory_quantity", "delete_waypoint",
}

# (description, prompt, expected)
#   expected == None      -> must NOT call any tool
#   expected == "safe"     -> may gate open, but must NOT call a destructive tool
#   expected == <tool name> -> must call exactly that tool
GOLDEN_CASES = [
    ("out-of-scope info question", "What can you tell me about Honda Civics?", None),
    ("module description question", "What does the Notes module do?", None),
    ("open module", "Open the notes module for me", "open_module"),
    ("add alarm", "Set an alarm called Wake Up for 07:00", "add_alarm"),
    ("list alarms", "List my alarms", "list_alarms"),
    ("delete alarm, name-before-noun phrasing", "Delete my Wake Up alarm", "delete_alarm"),
    ("add note", "Add a note that says buy milk", "add_note"),
    ("list notes", "List my notes", "list_notes"),
    ("delete note", "Delete the note called Groceries", "delete_note"),
    ("inventory quantity question", "How many M3 bolts do I have?", "list_inventory"),
    ("delete inventory item", "Remove M3 bolts from inventory", "delete_inventory_item"),
    ("adjust inventory quantity down", "I used 5 M3 bolts", "adjust_inventory_quantity"),
    ("list waypoints", "List my waypoints", "list_waypoints"),
    ("waypoint distance, 'from' phrasing", "What's the distance from Home to Cabin?", "waypoint_distance"),
    ("delete waypoint", "Delete the Cabin waypoint", "delete_waypoint"),
    ("system health", "What's my system health?", "get_system_health"),
    ("recall recent activity", "What have I been doing recently?", "recall_recent_activity"),
    ("false-positive sanity: 'alarming' is not 'alarm '", "This is alarming news about the economy", None),
    (
        "known accepted trade-off: 'used to' collides with 'i used'",
        "I used to live in Ohio",
        "safe",
    ),
]


def _build_context() -> AppContext:
    config = ConfigManager()
    events = EventBus()
    context = AppContext(config=config, events=events)
    context.llm = LLMManager(context)

    module_manager = ModuleManager(context)
    module_manager.discover()
    context.module_manager = module_manager

    context.device_help = DeviceHelpManager(context)
    context.device_help.register_module_lister(module_manager.all)
    ref_lib = ReferenceLibraryManager(context)
    context.reference_library = ref_lib
    context.device_help.register_reference_library(ref_lib)

    context.assistant_actions = AssistantActionRegistry()
    context.alarms = AlarmManager(context)
    context.journal = JournalManager(context)
    context.inventory = InventoryManager(context)
    context.waypoints = WaypointManager(context)
    context.activity_log = ActivityLogManager(context)
    context.activity_log.register_module_lister(module_manager.all)

    app_stub = object.__new__(MIAApplication)
    app_stub.context = context
    app_stub.module_manager = module_manager
    MIAApplication._register_assistant_actions(app_stub)

    return context


def _seed_fixtures(context: AppContext) -> None:
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    context.journal.add_entry(title="Groceries", body="buy milk and eggs")
    context.inventory.add_item(name="M3 bolts", quantity=25)
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    context.waypoints.add_waypoint(name="Cabin", latitude=41.5, longitude=-84.5)


def main() -> int:
    context = _build_context()
    _seed_fixtures(context)

    if not context.llm.is_available():
        print("Ollama is not reachable — start it (systemctl --user status ollama) and try again.")
        return 1

    failures = []
    for description, prompt, expected in GOLDEN_CASES:
        messages, tools = build_chat_request(context, prompt)
        reply = context.llm.chat_with_tools(messages, tools=tools)
        called = [tc.name for tc in reply.tool_calls] if reply and reply.tool_calls else []

        if expected is None:
            ok = called == []
            detail = f"expected no tool call, got {called}"
        elif expected == "safe":
            ok = not any(name in _DESTRUCTIVE_TOOLS for name in called)
            detail = f"expected no destructive tool call, got {called}"
        else:
            ok = called == [expected]
            detail = f"expected [{expected}], got {called}"

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {description}: {prompt!r} — {detail}")
        if not ok:
            failures.append(description)

    print()
    print(f"{len(GOLDEN_CASES) - len(failures)}/{len(GOLDEN_CASES)} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
