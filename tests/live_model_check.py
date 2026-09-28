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

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TEMP_DATA_DIR = Path(tempfile.mkdtemp(prefix="mia_live_model_check_"))

import core.alarm_manager as alarm_manager_module
import core.calendar_manager as calendar_manager_module
import core.component_manager as component_manager_module
import core.config_manager as config_manager_module
import core.conversation_manager as conversation_manager_module
import core.expedition_manager as expedition_manager_module
import core.inventory_manager as inventory_manager_module
import core.kitchen_manager as kitchen_manager_module
import core.classroom_manager as classroom_manager_module
import core.recurring_mission_manager as recurring_mission_manager_module
import core.relationships_manager as relationships_manager_module
import core.workout_manager as workout_manager_module
import core.data_logger_manager as data_logger_manager_module
import core.job_manager as job_manager_module
import core.journal_manager as journal_manager_module
import core.ledger_manager as ledger_manager_module
import core.budget_manager as budget_manager_module
import core.real_estate_manager as real_estate_manager_module
import core.maintenance_manager as maintenance_manager_module
import core.material_manager as material_manager_module
import core.mission_manager as mission_manager_module
import core.product_manager as product_manager_module
import core.project_manager as project_manager_module
import core.intent_manager as intent_manager_module
import core.why_graph as why_graph_module
import core.script_library_manager as script_library_manager_module
import core.task_manager as task_manager_module
import core.trail_map_library as trail_map_library_module
import core.trip_manager as trip_manager_module
import core.user_memory_manager as user_memory_manager_module
import core.waypoint_manager as waypoint_manager_module

# ProfileManager.create_profile()/set_active_profile() persist via
# context.config.save() (not their own data file) — without this, that
# write would land in the real config/config.json, not a throwaway
# file. Found the hard way once already in this project (see
# docs/ROADMAP.md milestone 5.14); isolated here before ANY ConfigManager
# is ever constructed, same as every manager's own _DATA_DIR below.
config_manager_module._CONFIG_FILE = _TEMP_DATA_DIR / "config.json"
# 2026-09-27: creating the seed profile made a real data/profiles/<id>/
# folder on every run; keep it in the temp dir with everything else.
import core.profile_manager as profile_manager_module  # noqa: E402
profile_manager_module._DATA_PROFILES_DIR = _TEMP_DATA_DIR / "profiles"

alarm_manager_module._DATA_DIR = _TEMP_DATA_DIR
alarm_manager_module._ALARMS_FILE = _TEMP_DATA_DIR / "alarms.json"
journal_manager_module._DATA_DIR = _TEMP_DATA_DIR
journal_manager_module._ENTRIES_FILE = _TEMP_DATA_DIR / "journal_entries.json"
inventory_manager_module._DATA_DIR = _TEMP_DATA_DIR
inventory_manager_module._ITEMS_FILE = _TEMP_DATA_DIR / "inventory_items.json"
waypoint_manager_module._DATA_DIR = _TEMP_DATA_DIR
waypoint_manager_module._WAYPOINTS_FILE = _TEMP_DATA_DIR / "waypoints.json"
expedition_manager_module._DATA_DIR = _TEMP_DATA_DIR
expedition_manager_module._EXPEDITIONS_FILE = _TEMP_DATA_DIR / "expeditions.json"
trip_manager_module._DATA_DIR = _TEMP_DATA_DIR
trip_manager_module._TRIPS_FILE = _TEMP_DATA_DIR / "trips.json"
calendar_manager_module._DATA_DIR = _TEMP_DATA_DIR
calendar_manager_module._EVENTS_FILE = _TEMP_DATA_DIR / "calendar_events.json"
maintenance_manager_module._DATA_DIR = _TEMP_DATA_DIR
maintenance_manager_module._MAINTENANCE_FILE = _TEMP_DATA_DIR / "maintenance.json"
maintenance_manager_module._DOCUMENT_ROOT = _TEMP_DATA_DIR / "maintenance_documents"
budget_manager_module._DATA_DIR = _TEMP_DATA_DIR
budget_manager_module._BILLS_FILE = _TEMP_DATA_DIR / "bills.json"
budget_manager_module._INCOME_FILE = _TEMP_DATA_DIR / "income.json"
budget_manager_module._EXPENSES_FILE = _TEMP_DATA_DIR / "budget_expenses.json"
budget_manager_module._INCOME_SOURCES_FILE = _TEMP_DATA_DIR / "income_sources.json"
budget_manager_module._BUDGET_TARGETS_FILE = _TEMP_DATA_DIR / "budget_targets.json"
budget_manager_module._BUSINESS_ENTITIES_FILE = _TEMP_DATA_DIR / "business_entities.json"
budget_manager_module._DEBTS_FILE = _TEMP_DATA_DIR / "debts.json"
# 2026-09-27 conversational audit: Kitchen + the parts/materials/products
# usage logs, so seeding and any future executed call stay in the temp dir.
kitchen_manager_module._DATA_DIR = _TEMP_DATA_DIR
for _attr in ("_RECIPES_FILE", "_PANTRY_FILE", "_GROCERY_LIST_FILE", "_MEAL_LOG_FILE", "_RECIPE_USER_STATS_FILE"):
    setattr(kitchen_manager_module, _attr, _TEMP_DATA_DIR / getattr(kitchen_manager_module, _attr).name)
component_manager_module._USAGE_LOG_FILE = _TEMP_DATA_DIR / "component_usage_log.json"
material_manager_module._USAGE_LOG_FILE = _TEMP_DATA_DIR / "material_usage_log.json"
product_manager_module._USAGE_LOG_FILE = _TEMP_DATA_DIR / "product_usage_log.json"
for _module in (classroom_manager_module, recurring_mission_manager_module, relationships_manager_module, workout_manager_module):
    for _attr, _value in list(vars(_module).items()):
        if isinstance(_value, Path) and _value.parent == _module._DATA_DIR:
            setattr(_module, _attr, _TEMP_DATA_DIR / _value.name)
    _module._DATA_DIR = _TEMP_DATA_DIR
real_estate_manager_module._DATA_DIR = _TEMP_DATA_DIR
real_estate_manager_module._PROPERTIES_FILE = _TEMP_DATA_DIR / "properties.json"
data_logger_manager_module._DATA_DIR = _TEMP_DATA_DIR
data_logger_manager_module._READINGS_FILE = _TEMP_DATA_DIR / "data_logger_readings.json"
component_manager_module._DATA_DIR = _TEMP_DATA_DIR
component_manager_module._COMPONENTS_FILE = _TEMP_DATA_DIR / "components.json"
script_library_manager_module._DATA_DIR = _TEMP_DATA_DIR
script_library_manager_module._SCRIPTS_FILE = _TEMP_DATA_DIR / "scripts.json"
project_manager_module._DATA_DIR = _TEMP_DATA_DIR
project_manager_module._PROJECTS_FILE = _TEMP_DATA_DIR / "projects.json"
task_manager_module._DATA_DIR = _TEMP_DATA_DIR
task_manager_module._TASKS_FILE = _TEMP_DATA_DIR / "tasks.json"
mission_manager_module._DATA_DIR = _TEMP_DATA_DIR
mission_manager_module._MISSIONS_FILE = _TEMP_DATA_DIR / "missions.json"
material_manager_module._DATA_DIR = _TEMP_DATA_DIR
material_manager_module._MATERIALS_FILE = _TEMP_DATA_DIR / "materials.json"
job_manager_module._DATA_DIR = _TEMP_DATA_DIR
job_manager_module._JOBS_FILE = _TEMP_DATA_DIR / "jobs.json"
product_manager_module._DATA_DIR = _TEMP_DATA_DIR
product_manager_module._PRODUCTS_FILE = _TEMP_DATA_DIR / "products.json"
ledger_manager_module._DATA_DIR = _TEMP_DATA_DIR
ledger_manager_module._REVENUE_FILE = _TEMP_DATA_DIR / "revenue.json"
ledger_manager_module._EXPENSES_FILE = _TEMP_DATA_DIR / "expenses.json"
conversation_manager_module._DATA_DIR = _TEMP_DATA_DIR
conversation_manager_module._CONVERSATIONS_FILE = _TEMP_DATA_DIR / "conversations.json"
user_memory_manager_module._DATA_DIR = _TEMP_DATA_DIR
user_memory_manager_module._USER_MEMORIES_FILE = _TEMP_DATA_DIR / "user_memories.json"
trail_map_library_module._DATA_DIR = _TEMP_DATA_DIR
# Slice B: goals and the monthly why checkpoints.
intent_manager_module._DATA_DIR = _TEMP_DATA_DIR
intent_manager_module._INTENTS_FILE = _TEMP_DATA_DIR / "intents.json"
why_graph_module._DATA_DIR = _TEMP_DATA_DIR
why_graph_module._CHECKPOINTS_FILE = _TEMP_DATA_DIR / "why_checkpoints.json"
trail_map_library_module._TRAIL_MAPS_FILE = _TEMP_DATA_DIR / "trail_maps.json"

from core.activity_log_manager import ActivityLogManager
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.application import MIAApplication
from core.assistant_actions import AssistantActionRegistry
from core.assistant_chat import build_chat_request
from core.talk_it_out import pre_turn
from core.conversation_modes import PERSPECTIVE
from core.why_graph import build_why_sheet
from core.calendar_manager import CalendarManager
from core.component_manager import ComponentManager
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.device_help_manager import DeviceHelpManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.inventory_manager import InventoryManager
from core.kitchen_manager import KitchenManager
from core.classroom_manager import ClassroomManager
from core.recurring_mission_manager import RecurringMissionManager
from core.relationships_manager import RelationshipsManager
from core.workout_manager import WorkoutManager
from core.data_logger_manager import DataLoggerManager
from core.job_manager import JobManager
from core.journal_manager import JournalManager
from core.ledger_manager import LedgerManager
from core.budget_manager import BudgetManager
from core.real_estate_manager import RealEstateManager
from core.maintenance_manager import MaintenanceManager
from core.llm_manager import LLMManager
from core.material_manager import MaterialManager
from core.memory_manager import MemoryManager
from core.mission_manager import MissionManager
from core.module_manager import ModuleManager
from core.product_manager import ProductManager
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.reference_library_manager import ReferenceLibraryManager
from core.script_library_manager import ScriptLibraryManager
from core.task_manager import TaskManager
from core.trail_map_library import TrailMapLibrary
from core.trip_manager import TripManager
from core.user_memory_manager import UserMemoryManager
from core.waypoint_manager import WaypointManager

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
    # --- Assistant action-registry expansion: Expedition Mode + Device Profile/Theme ---
    ("add waypoint", "Save a waypoint here called Ridge Camp at latitude 44.0 longitude -110.1", "add_waypoint"),
    ("add expedition", "Start a new expedition called Field Season", "add_expedition"),
    ("list expeditions", "List my expeditions", "list_expeditions"),
    ("add trip", "Add a trip called Day 1 to my Field Season expedition", "add_trip"),
    ("list trips", "What trips do I have?", "list_trips"),
    ("add gear item", "Add a tent to the gear list for my Day 1 trip", "add_gear_item"),
    (
        "add trip log entry, not a generic note",
        "Log to my trip journal that I reached camp, conditions were clear and 15 degrees",
        "add_trip_log_entry",
    ),
    ("generic note still resolves to add_note, not trip log", "Add a note that says buy milk", "add_note"),
    ("delete an expedition", "Delete the expedition called Field Season", "delete_expedition"),
    ("delete a trip", "Delete the trip called Day 1", "delete_trip"),
    ("mark gear packed", "I packed my First aid kit for my Day 1 trip", "toggle_gear_packed"),
    ("get trip summary", "How far did I go on my Day 1 trip?", "get_trip_summary"),
    ("sunrise/sunset for a waypoint", "What time does the sun set at my Cabin waypoint?", "get_sun_moon_info"),
    ("moon phase for a waypoint", "What's the moon phase at Cabin tonight?", "get_sun_moon_info"),
    ("convert units", "Convert 5 miles to kilometers", "convert_units"),
    ("convert units, temperature", "What is 100 fahrenheit in celsius?", "convert_units"),
    ("ohms law", "I have 2 amps through a 10 ohm resistor, what's the voltage?", "calculate_ohms_law"),
    ("false-positive sanity: 'packed' unrelated to gear", "The stadium was packed for the game", None),
    ("false-positive sanity: 'convert' unrelated to units", "I'm trying to convert my garage into a workshop", None),
    ("get device profile", "What device profile is this running?", "get_device_profile"),
    ("set theme", "Change the theme to low energy", "set_theme"),
    (
        "collision risk: theme change phrased with 'switch to' must not hallucinate open_module",
        "Switch to the Anime Monochrome theme",
        "set_theme",
    ),
    ("set birthday", "My birthday is March 3rd, 1990", "set_birthday"),
    ("false-positive sanity: ordinary use of the word 'trip'", "That trip to the store took forever", None),
    (
        "false-positive sanity: ordinary use of the word 'log' unrelated to a trip",
        "I need to log off for the night",
        None,
    ),
    # --- Assistant action-registry expansion: Calendar, Power, Components, Field Kit ---
    ("add calendar event", "Add an event called Dentist on 2026-09-01 at 14:00", "add_calendar_event"),
    ("list calendar events", "What's on my calendar?", "list_calendar_events"),
    ("delete calendar event", "Delete my Doctor Appointment event", "delete_calendar_event"),
    ("get power status", "What's my battery level?", "get_power_status"),
    ("add component", "Add a component called 10k resistor", "add_component"),
    ("list components", "What components do I have?", "list_components"),
    ("delete component", "Delete the M3 bolts component", "delete_component"),
    ("list connected devices", "What devices are connected right now?", "list_connected_devices"),
    ("list scripts", "List my scripts", "list_scripts"),
    ("false-positive sanity: 'eventful' is not 'event '", "This was an eventful week at work", None),
    # --- milestone 5.14: Profiles (list only, no switch_profile) ---
    ("list profiles", "What user profiles do I have set up?", "list_profiles"),
    (
        "collision risk: 'profile' is overloaded (user profiles vs. device_profile edition)",
        "Show my profiles on this MIA device",
        "list_profiles",
    ),
    # --- milestone 5.15: Security tab tools (hash identifier, password
    # strength, subnet calculator, port scanner) ---
    ("identify hash", "What hash format is this: $2b$12$abcdefghijklmnopqrstuv", "identify_hash"),
    ("check password strength", "How strong is this password: hunter2", "check_password_strength"),
    ("calculate subnet", "Calculate this subnet: 192.168.1.0/24", "calculate_subnet"),
    ("scan ports", "Scan 192.168.1.1 for open ports", "scan_ports"),
    (
        "collision risk: scan_ports vs. list_connected_devices (both device/network-ish)",
        "Scan 10.0.0.1 for open ports",
        "scan_ports",
    ),
    # --- milestone: Project Manager (Projects, Tasks) ---
    ("add project", "Start a new project called Kitchen Remodel", "add_project"),
    ("list projects", "What projects do I have?", "list_projects"),
    (
        "add task, not a generic note",
        "Add a task called Buy fuse box to my Garage Rewire project",
        "add_task",
    ),
    ("list tasks", "What tasks do I have?", "list_tasks"),
    ("false-positive sanity: ordinary use of the word 'project'", "This project is taking forever", None),
    # --- Project Manager CRUD follow-up: delete_project, delete_task, mark_task_done ---
    ("delete project", "Delete the project called Garage Rewire", "delete_project"),
    ("delete task", "Delete the task called Buy fuse box", "delete_task"),
    ("mark task done", "Mark the task called Buy fuse box as done", "mark_task_done"),
    # --- milestone v0.17: Memories (recall_expedition) ---
    ("recall expedition by name", "Tell me about the expedition called Field Season", "recall_expedition"),
    ("recall most recent expedition", "Tell me about my last expedition", "recall_expedition"),
    (
        "collision risk: recall_expedition (one, detailed) vs. list_expeditions (bare list)",
        "Can you describe my expedition to me",
        "recall_expedition",
    ),
    # --- milestone v0.18: Missions/Gamification ---
    ("add mission", "Start a new mission called Kayak Explorer", "add_mission"),
    ("list missions", "What missions do I have?", "list_missions"),
    (
        "current mission phrasing — 2026-07-18 real gap, trigger phrases didn't cover this",
        "What is my current mission?",
        "list_missions",
    ),
    ("add objective", "Add an objective to my Master Angler mission: catch 5 fish, target 5", "add_objective"),
    ("log mission progress", "Log a catch for my Master Angler mission", "log_mission_progress"),
    ("delete mission", "Delete the mission called Master Angler", "delete_mission"),
    ("complete mission", "Complete the mission called Master Angler", "complete_mission"),
    ("false-positive sanity: ordinary use of the word 'mission'", "Our company's mission is customer satisfaction", None),
    # --- 2026-07-18: systematic trigger-phrase gap audit, prompted by the
    # "current mission" bug above — probed many natural alternate phrasings
    # across every existing domain (not just missions) and found 11 more
    # real gaps of the same shape (a plausible real phrasing simply
    # missing from trigger_phrases, not covered by the golden set above).
    # All fixed with new trigger phrases; kept here so future registry
    # growth can't silently reintroduce them. ---
    ("calendar: 'anything on my calendar today'", "Do I have anything on my calendar today?", "list_calendar_events"),
    ("calendar: 'what's going on this week'", "What do I have going on this week?", "list_calendar_events"),
    ("components: 'what parts do I have'", "What parts do I have in my workshop?", "list_components"),
    ("tasks: 'what am I working on'", "What am I currently working on?", "list_tasks"),
    ("tasks: 'what do I need to do'", "What do I need to do?", "list_tasks"),
    ("alarms: 'when is my next alarm'", "When is my next alarm?", "list_alarms"),
    ("power: 'am I plugged in'", "Am I plugged in right now?", "get_power_status"),
    (
        "power: 'power percentage' real gap — user report, no trigger phrase matched at all",
        "What is my power percentage?",
        "get_power_status",
    ),
    ("false-positive sanity: 'power' unrelated to battery", "This new drill has a lot more power than my old one", None),
    ("expeditions: 'how many expeditions have I done'", "How many expeditions have I been on?", "list_expeditions"),
    ("waypoints: 'what locations have I saved'", "What locations have I saved?", "list_waypoints"),
    ("notes: 'anything I wrote down'", "Is there anything I wrote down recently?", "list_notes"),
    ("system health: 'is everything ok'", "Is everything running okay on this device?", "get_system_health"),
    (
        "false-positive: 'everything ok' as small talk, not a system check",
        "Hey, is everything ok with you today?",
        "safe",
    ),
    ("false-positive: 'plugged in' unrelated to power", "I just plugged in my new keyboard.", "safe"),
    ("false-positive: 'working on' unrelated to tasks/projects", "I've been working on my patience lately.", "safe"),
    (
        "collision check: notes list vs add, both share 'wrote/write down' phrasing",
        "What did I write down about the trip?",
        "list_notes",
    ),
    # --- 2026-07-18: Workshop production pipeline (Materials/Jobs/Products/
    # Ledger) had zero Assistant actions until now — real gap found via a
    # module-coverage audit. ---
    ("add material", "Add a material called Aluminum Rod", "add_material"),
    ("list materials", "What materials do I have?", "list_materials"),
    ("add product", "Add a product called Bookshelf", "add_product"),
    ("list products", "What products do I have?", "list_products"),
    ("add job", "Start a new job called Bookshelf Batch", "add_job"),
    ("list jobs", "What jobs do I have?", "list_jobs"),
    (
        "consume material on a job",
        "My Birdhouse Batch job used 4 sheets of Plywood",
        "consume_material",
    ),
    (
        "produce product on a job",
        "My Birdhouse Batch job produced 3 Birdhouses",
        "produce_product",
    ),
    ("record a sale", "I sold 2 Birdhouses for $50", "record_sale"),
    ("ledger summary", "What's my net profit so far?", "get_ledger_summary"),
    ("false-positive sanity: ordinary use of the word 'job'", "I love my new job at the bakery", None),
    ("false-positive sanity: ordinary use of the word 'material'", "This shirt is made of a soft material", None),
    # --- 2026-07-18: Maps module (trail map catalog) had zero Assistant
    # actions until now — real gap found via a module-coverage audit. ---
    ("list trail maps", "What trail maps do I have?", "list_trail_maps"),
    (
        "add trail map from url",
        "Add a trail map for Red River Gorge in Kentucky from https://example.com/rrg.pdf",
        "add_trail_map_from_url",
    ),
    ("delete a trail map", "Delete my trail map for Mammoth Cave", "delete_trail_map"),
    ("false-positive sanity: ordinary use of the word 'map'", "I can't map out my whole week right now", None),
    # --- 2026-09-07: Maintenance module had zero Assistant actions
    # until now — real gap found via a full-registry coverage audit
    # (76 actions across 19 domains, Maintenance had none despite being
    # a substantial feature: assets, 6 trigger types, documents,
    # meter/sensor readings). Two real collision risks tested below
    # rather than assumed safe: "projects" already owns generic
    # "add/list a task" phrasing, and "alarms" already owns bare
    # "remind me" — a maintenance task is a legitimately different
    # concept from either, so both domains attaching together and the
    # model disambiguating via tool description is expected, same
    # pattern as the existing add_note/add_trip_log_entry collision.
    ("add maintenance asset", "Track my Truck as a vehicle in Maintenance", "add_maintenance_asset"),
    ("list maintenance assets", "What vehicles and equipment am I tracking in Maintenance?", "list_maintenance_assets"),
    ("delete maintenance asset", "Stop tracking my Truck in Maintenance", "delete_maintenance_asset"),
    (
        "add maintenance task, collision risk vs. add_alarm's bare 'remind me'",
        "Remind me to change my Truck's oil every 180 days",
        "add_maintenance_task",
    ),
    ("list maintenance tasks, due question", "What maintenance is due on my Truck?", "list_maintenance_tasks"),
    ("list maintenance tasks, overdue question", "Is anything overdue for maintenance?", "list_maintenance_tasks"),
    ("complete maintenance task", "I renewed the tags on my Truck", "complete_maintenance_task"),
    ("log a meter reading", "Log a reading of 46000 miles for the Oil Change on my Truck", "log_maintenance_reading"),
    (
        "formerly a known gap (bare 'Log <value> <unit>' never gated open); closed 2026-09-27 by matching "
        "the user's own record names ('Truck') and maintenance vocabulary",
        "Log 46000 miles for the Oil Change on my Truck",
        "log_maintenance_reading",
    ),
    ("delete maintenance task", "Delete the Renew Tags maintenance task", "delete_maintenance_task"),
    (
        "false-positive sanity: ordinary use of the word 'service' unrelated to maintenance",
        "I volunteered to do community service this weekend",
        None,
    ),
    (
        "collision risk: 'what tasks' must still resolve to Project Manager's list_tasks, not maintenance",
        "What tasks do I have?",
        "list_tasks",
    ),
    # --- 2026-09-08: Lab (Data Logger) — same audit as Maintenance,
    # found zero Assistant actions for manual sensor/experiment
    # readings. Real collision risk: "log a reading" is deliberately
    # shared vocabulary with log_maintenance_reading (both legitimately
    # attach; the model disambiguates via series vs. task/asset in each
    # tool's own description, same pattern as every other real
    # multi-domain collision in this registry) — tested explicitly below
    # rather than assumed safe.
    ("log a lab reading", "Log a reading of 65 for soil moisture", "log_lab_reading"),
    (
        "collision risk: 'log a reading' shared with log_maintenance_reading — must pick the Lab one for a series, not a task",
        "Log a reading of 12.4 volts for my multimeter test",
        "log_lab_reading",
    ),
    (
        "collision risk: same shared phrasing, but for a real tracked Maintenance task — must pick log_maintenance_reading",
        "Log a reading of 47000 miles for the Oil Change on my Truck",
        "log_maintenance_reading",
    ),
    ("list lab series", "What data series am I logging in the Lab?", "list_lab_series"),
    ("list lab readings for one series", "Show me the readings for Soil Moisture", "list_lab_readings"),
    (
        "false-positive sanity: ordinary use of 'reading' unrelated to Data Logger",
        "I'm reading a really good book right now",
        None,
    ),
    (
        "false-positive sanity: 'series' unrelated to Data Logger (TV series)",
        "I just finished watching a great TV series",
        None,
    ),
    # --- 2026-09-08: Budget (household bills, income, expenses) — same
    # planning session that added Property. Real collision risk tested
    # explicitly: add_bill vs. add_maintenance_task both cover "a
    # recurring thing due on a schedule" and legitimately both attach
    # on ambiguous phrasing — disambiguated by description, same
    # pattern already proven for the alarm/maintenance-task collision.
    ("add a bill", "Add a monthly electric bill for $120, due 2026-09-01", "add_bill"),
    (
        "collision risk: recurring bill vs. recurring maintenance task — must pick add_bill for a dollar amount",
        "Add a bill called Internet for $80 due on the 1st of every month",
        "add_bill",
    ),
    (
        "collision risk: same shared 'recurring thing due' shape, but for real asset upkeep — must pick add_maintenance_task",
        "Remind me to change my Truck's oil every 180 days",
        "add_maintenance_task",
    ),
    ("list bills", "What bills do I have?", "list_bills"),
    ("bill overdue question", "Is anything overdue?", "list_bills"),
    ("mark a bill paid", "I paid my Electric bill", "mark_bill_paid"),
    ("record income", "I got paid $3000 for my paycheck", "add_income"),
    ("record rental income", "Record $1500 of rental income", "add_income"),
    ("record an expense", "I spent $85 on groceries", "add_expense"),
    ("budget summary", "What's my net cash flow this month?", "get_budget_summary"),
    (
        "false-positive sanity: ordinary use of 'bill' unrelated to Budget",
        "Can you bill me for that later, just kidding",
        "safe",
    ),
    # --- 2026-09-08: Proactive nudges follow-up — expected/recurring
    # income (IncomeSource) vs. a one-off add_income entry vs. a
    # recurring-obligation add_bill. All three share "recurring thing
    # with an amount and a schedule" surface phrasing, so this is a
    # real three-way collision risk tested explicitly, same discipline
    # as the add_bill/add_maintenance_task collision above.
    (
        "collision risk: recurring EXPECTED income vs. add_bill (an obligation) — must pick add_income_source",
        "Add my paycheck as an income source — $2400 every two weeks starting 2026-09-08",
        "add_income_source",
    ),
    (
        "collision risk: recurring expected income vs. a one-off add_income — must pick add_income_source",
        "Track my rental income of $1500 a month starting 2026-09-01",
        "add_income_source",
    ),
    (
        "collision risk: income ALREADY received right now vs. add_income_source — must pick add_income",
        "I got paid $3000 today",
        "add_income",
    ),
    ("mark income source received", "My paycheck came in", "mark_income_received"),
    ("financial check-in", "How are we doing financially?", "get_financial_checkin"),
    ("financial check-in phrasing 2", "Are we on budget this month?", "get_financial_checkin"),
    (
        "false-positive sanity: 'paycheck' mentioned without any add/track/received intent",
        "What's a good way to budget my paycheck?",
        None,
    ),
    # --- 2026-09-08: Real Estate (property portfolio) — same planning
    # session as Property/Budget. Real collision risk tested explicitly:
    # record_rental_income shares "rental income" vocabulary with
    # Budget's own add_income; both legitimately attach on ambiguous
    # phrasing, disambiguated by description (a specific tracked
    # property vs. plain household income) — same pattern proven for
    # every other real collision this session.
    ("add a property", "Add a rental property called 123 Main St", "add_property"),
    ("list properties", "What properties do I have?", "list_properties"),
    (
        "known accepted trade-off: 'rental income' + a named property still sometimes resolves to plain "
        "add_income instead of record_rental_income (see that action's own registration comment — three "
        "description phrasings tried, none fully fixed this direction, non-destructive either way)",
        "Record rental income of $1800 for 123 Main St",
        "safe",
    ),
    (
        "collision risk: same shared 'rental income' phrasing, but no specific property named — must pick plain add_income",
        "Record $1500 of rental income",
        "add_income",
    ),
    ("property summary", "How is my 123 Main St property doing?", "get_property_summary"),
    (
        "false-positive sanity: ordinary use of 'property' unrelated to Real Estate",
        "That's a really useful property of this material",
        None,
    ),
    # --- 2026-09-10: teaching-mode conversation path (docs/VISION.md's
    # "Interactive onboarding + modular tutorial system") ---
    ("teaching request must not call a tool", "Teach me how missions work", None),
    (
        "collision risk: an explicit 'teach me how to X' must not execute X, "
        "even though its own trigger keyword ('add a mission') is present",
        "Teach me how to add a mission",
        None,
    ),
    # --- 2026-09-27 conversational audit (docs/ASSISTANT_AUDIT.md) ---
    # Assets and plants in the user's own words.
    ("reading on an asset by nickname", "I just put 120 hours on the mower", "log_maintenance_reading", {"asset_name": "mower", "value": 120}),
    ("completion in casual words", "Sharpened the mower blades this morning", "complete_maintenance_task", {"asset_name": "mower"}),
    ("completion for a plant", "I watered the tomatoes", "complete_maintenance_task", {"asset_name": "tomato"}),
    ("asset details", "My mower is a John Deere Z315E", "update_maintenance_asset", {"asset_name": "mower", "manufacturer": "John Deere"}),
    ("what MIA knows about an asset", "Tell me about my mower", "get_maintenance_asset", {"asset_name": "mower"}),
    ("observation note on a plant", "Note that the peppers are starting to flower", "add_asset_note", {"asset_name": "pepper"}),
    ("new greenhouse plant", "Add the lettuce bed to the greenhouse", "add_maintenance_asset", {"name": "lettuce"}),
    ("plant care schedule", "Remind me to water the pepper plants every 3 days", "add_maintenance_task", {"interval_days": 3}),
    ("greenhouse status", "What's due in the greenhouse?", "list_maintenance_tasks"),
    # Money.
    ("new debt with rate", "I owe $5,100 on my Capital One card at 27.49 percent", "add_debt", {"balance": 5100, "interest_rate": 27.49}),
    ("debt payment", "I paid $200 toward my Chase card", "record_debt_payment", {"debt_name": "chase", "amount": 200}),
    ("payoff advice", "Which debt should I pay off first?", "get_debt_payoff_plan"),
    ("total debt", "How much do I owe in total?", "list_debts"),
    ("budget target", "Set my grocery budget to $600 a month", "set_budget_target", {"monthly_amount": 600}),
    # Kitchen.
    ("new recipe", "Add a recipe for garden salsa", "add_recipe", {"name": "salsa"}),
    ("what to cook", "What can I make with what I have?", "suggest_recipes"),
    ("meal log by nickname", "I made the venison chili tonight", "log_meal", {"recipe_name": "chili"}),
    ("grocery add, multiple items", "Add milk and coffee to the grocery list", "add_grocery_item", {"items": "coffee"}),
    ("grocery check-off", "I bought the eggs", "check_off_grocery_item", {"items": "eggs"}),
    ("pantry out of", "We're out of flour", "update_pantry_item", {"name": "flour", "quantity": 0}),
    ("recipe shopping", "Add what I need for the venison chili to the grocery list", "add_recipe_ingredients_to_grocery_list"),
    # Workshop.
    ("parts used", "I used two 10k resistors", "adjust_component_quantity", {"delta": -2}),
    ("materials bought", "I bought 4 more sheets of plywood", "adjust_material_quantity", {"name": "plywood", "delta": 4}),
    ("material price", "Plywood costs $42 a sheet now", "update_material", {"unit_cost": 42}),
    ("products made", "I made 5 more cutting boards", "adjust_product_stock", {"delta": 5}),
    # How-to questions are answered, never executed.
    ("how-to must not execute", "How do I add a bill?", None),
    ("how-to must not execute (record name present)", "How do I track my mower?", None),
    # Passing mentions of the user's things now offer tools (documented
    # trade-off); the model must still not write anything.
    ("passing mention of an asset: no write", "I was driving the truck home and it felt great", "safe"),
    ("passing mention of an asset: no write", "Tell me a story about a mower", "safe"),
    # Workout, people & pets, household, classroom.
    ("log a workout", "Log my workout: 3x10 squats at 185", "log_workout", {"exercises": "squat"}),
    ("personal record", "What's my personal record on the squat?", "get_personal_record", {"exercise": "squat"}),
    ("remember a gift idea", "Sarah would love a new cast iron skillet", "update_person", {"name": "sarah", "gift_idea": "skillet"}),
    ("someone's birthday", "My friend Jake's birthday is May 9", "safe"),
    ("upcoming birthdays", "Any birthdays coming up?", "list_upcoming_birthdays"),
    ("pet vet visit", "Biscuit went to the vet for his rabies shot today", "update_pet", {"name": "biscuit", "medical_note": "rabies"}),
    ("household routine", "I did a load of laundry", "log_household_routine", {"routine": "laundry"}),
    ("chores status", "What chores are left today?", "list_household_routines"),
    ("finish a lesson", "I finished the lesson on circuit breakers", "complete_lesson", {"lesson": "circuit breaker"}),
    ("learning progress", "What am I learning right now?", "get_learning_progress"),
    ("small talk: 'of course'", "Of course, that makes sense", None),
    # Finance #2: homestead builds and tools.
    ("build cost: lumber", "I spent $240 on lumber for the greenhouse", "log_build_expense", {"amount": 240, "build": "greenhouse"}),
    ("tool purchase", "I just bought a chainsaw for $329", "record_tool_purchase", {"tool": "chainsaw", "price": 329}),
    ("tool cost question", "What has the chainsaw cost me so far?", "get_tool_costs"),
    # Slice C: when MIA speaks up.
    ("speaking up: what was held back", "What didn't you tell me today?", "get_held_back_messages"),
    ("speaking up: set the limit", "Only message me 3 times a day", "set_message_limit", {"count": 3}),
    ("small talk: a dog", "What's a good name for a dog?", None),
]


# Cognitive Extension slice A: personal modes. Each case switches the
# mode with a first message (applied by core.talk_it_out.pre_turn(), no
# model call), then checks PROPERTIES of the reply to the second, never
# its wording (docs/COGNITIVE_EXTENSION_PROPOSAL.md, question 12):
# (description, mode-switch message, prompt, expected tool or None, max words, lists allowed)
PERSONAL_CASES = [
    ("listen: plain vent", "MIA, just listen", "Work dragged so bad today. Same thing every single day.", None, 80, False),
    ("listen: vent naming a record", "I need to vent", "The truck broke down again and I'm so done with it.", None, 80, False),
    ("listen: command still works", "Just listen for a bit", "Add milk to the grocery list", "add_grocery_item", None, True),
    ("direct: short and plain", "MIA, no bullshit", "Am I wasting my life at this factory job?", None, 90, True),
    ("momentum: brief", "Hype me up", "I've got four hours left on this shift.", None, 70, True),
    ("plan: one next step", "Help me figure out what to do", "I have the greenhouse, the truck, and bills all at once.", None, 150, True),
    ("journal: listening", "I want to journal", "Today I realized I'm proud of how far I've come with the land.", None, 80, False),
    # Slice B: every number in the reply must come from the fact sheet (checked in main()).
    ("perspective: remind me why", "Hey MIA", "I'm dragged down at work. Remind me why I'm doing all this.", None, 120, True),
    ("perspective: no bullshit", "Hey MIA", "No bullshit, what's the point of all this?", None, 120, True),
]

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _invented_numbers(reply_text: str, sheet_text: str) -> list[str]:
    """Numbers (2+ digits) in the reply that aren't anywhere in the fact sheet."""
    known = {n.replace(",", "") for n in _NUMBER.findall(sheet_text)}
    said = [n for n in _NUMBER.findall(reply_text) if len(n.replace(",", "")) >= 2]
    return [n for n in said if n.replace(",", "") not in known]

_LIST_LINE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s", re.MULTILINE)


def _check_personal_reply(reply, expected, max_words, lists_ok) -> tuple[bool, str]:
    called = [tc.name for tc in reply.tool_calls] if reply and reply.tool_calls else []
    if expected is not None:
        return called == [expected], f"expected [{expected}], got {called}"
    if called:
        return False, f"expected no tool call, got {called}"
    text = (reply.content or "") if reply else ""
    words = len(text.split())
    if max_words is not None and words > max_words:
        return False, f"{words} words, over the {max_words}-word limit: {text[:120]!r}"
    if not lists_ok and _LIST_LINE.search(text):
        return False, f"listed/advised instead of listening: {text[:120]!r}"
    return True, f"{words} words"


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
    context.config.set("trips.photo_root_path", str(_TEMP_DATA_DIR / "trip_photos"))
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.calendar = CalendarManager(context)
    context.maintenance = MaintenanceManager(context)
    context.budget = BudgetManager(context)
    context.real_estate = RealEstateManager(context)
    context.data_logger = DataLoggerManager(context)
    context.components = ComponentManager(context)
    context.scripts = ScriptLibraryManager(context)
    context.profiles = ProfileManager(context)
    context.projects = ProjectManager(context)
    context.intents = intent_manager_module.IntentManager(context)
    context.tasks = TaskManager(context)
    # Read-only aggregation, no persisted file of its own — see
    # core/memory_manager.py's docstring — so no _DATA_DIR isolation
    # is needed the way every other manager above requires.
    context.memories = MemoryManager(context)
    context.missions = MissionManager(context)
    context.materials = MaterialManager(context)
    context.kitchen = KitchenManager(context)
    context.recurring_missions = RecurringMissionManager(context)
    context.workout = WorkoutManager(context)
    context.relationships = RelationshipsManager(context)
    context.classroom = ClassroomManager(context)
    context.jobs = JobManager(context)
    context.products = ProductManager(context)
    context.ledger = LedgerManager(context)
    context.conversations = ConversationManager(context)
    context.user_memories = UserMemoryManager(context)
    context.config.set("maps.trail_map_root_path", str(_TEMP_DATA_DIR / "trail_maps"))
    context.trail_maps = TrailMapLibrary(context)
    # Real DeviceFramework/PowerManager — both are read-only wrappers
    # over lsblk/psutil with no JSON file of their own, so no isolation
    # is needed the way every other manager above requires.
    from core.device_framework import DeviceFramework
    from core.power_manager import PowerManager
    context.devices = DeviceFramework(context)
    context.power = PowerManager(context)
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
    expedition = context.expeditions.add_expedition(name="Field Season", start_date="2026-08-14")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="Hiking")
    context.trips.add_gear_item(trip.trip_id, label="First aid kit")
    context.calendar.add_event(title="Doctor Appointment", date="2026-08-14", time="09:00")
    truck = context.maintenance.add_asset(name="Truck", category="Vehicle")
    context.maintenance.add_task(truck.asset_id, "Renew Tags", interval_days=365, last_completed="2026-01-01")
    mileage_task = context.maintenance.add_task(
        truck.asset_id, "Oil Change", trigger_type="mileage", meter_unit="miles", meter_interval=5000
    )
    context.maintenance.mark_complete(mileage_task.task_id, meter_value=40000)
    context.data_logger.add_reading(series_id="Soil Moisture", value=42.0, unit="%", note="raised bed 1")
    context.budget.add_bill(name="Electric", amount=120.0, due_date="2026-08-01", category="Utilities", recurrence="monthly")
    context.budget.add_income(amount=3000.0, category="Salary", date="2026-08-01")
    context.budget.add_income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-08-15", category="Salary", recurrence="biweekly")
    rental_property = context.real_estate.add_property(name="123 Main St", property_type="Rental", current_value=280000.0, mortgage_balance=150000.0)
    context.real_estate.record_rental_income(rental_property.property_id, amount=1800.0, date_str="2026-08-01")
    context.components.add_component(name="M3 bolts", quantity=25, category="Fastener")
    context.scripts.add_script(name="Backup", interpreter="shell", category="Maintenance")
    context.profiles.create_profile(name="Zac", make_active=True)
    project = context.projects.add_project(name="Garage Rewire", status="Active", due_date="2026-08-14")
    context.tasks.add_task(project_id=project.project_id, title="Buy fuse box")
    mission = context.missions.add_mission(name="Master Angler", trip_id=trip.trip_id)
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)
    context.materials.add_material(name="Plywood", unit="sheet", quantity_on_hand=10)
    context.jobs.add_job(name="Birdhouse Batch")
    context.products.add_product(name="Birdhouse", quantity_in_stock=2, base_price=25.0)
    fake_pdf_path = _TEMP_DATA_DIR / "seed_trail_map.pdf"
    fake_pdf_path.write_bytes(b"%PDF-1.4 fake trail map contents")
    context.trail_maps.add_from_local_file("Mammoth Cave", "Kentucky", fake_pdf_path)

    # 2026-09-27 conversational audit fixtures.
    mower = context.maintenance.add_asset(name="Riding Mower", category="Power Equipment")
    context.maintenance.add_task(mower.asset_id, "Sharpen blades", interval_days=30)
    bed = context.maintenance.add_asset(name="Tomato Bed", category="Garden/Plant")
    context.maintenance.add_task(bed.asset_id, "Water", interval_days=2)
    context.maintenance.add_asset(name="Pepper Plants", category="Garden/Plant")
    context.budget.add_debt(name="Chase Freedom", balance=4200.0, interest_rate=24.99, minimum_payment=90.0)
    # Slice B: the owner's chain of reasons, for the Perspective cases.
    factory = context.intents.add_intent("Factory work")
    debt_goal = context.intents.add_intent("Pay off debt")
    time_goal = context.intents.add_intent("Control over my time")
    context.intents.set_serves(factory.intent_id, debt_goal.intent_id, "the factory pays the bills")
    context.intents.set_serves(debt_goal.intent_id, time_goal.intent_id)
    context.budget.add_debt(name="Truck Loan", balance=18250.0, interest_rate=6.9, minimum_payment=455.0, debt_type="Auto Loan")
    chili = context.kitchen.add_recipe(name="Venison Chili", category="Dinner")
    context.kitchen.add_ingredient(chili.recipe_id, "ground venison", quantity=2, unit="lb")
    context.kitchen.add_recipe(name="Garden Omelette", category="Breakfast")
    context.kitchen.add_pantry_item("Flour", quantity=10, unit="lb")
    context.kitchen.add_grocery_item("Eggs")
    context.components.add_component(name="Resistor", value="10k", quantity=30, category="Resistor")
    context.products.add_product(name="Cutting Board", quantity_in_stock=3, base_price=40.0)
    context.workout.add_exercise("Back Squat", category="Legs")
    context.relationships.add_person("Sarah", relationship="Sister", birthday="2000-03-03")
    context.relationships.add_pet("Biscuit", species="Dog")
    context.recurring_missions.add_template(
        name="Laundry", objective_description_template="Laundry ({target:g}x)", base_target=2,
        target_increment_per_week=0, daily_reward_xp=10, weekly_bonus_reward_xp=25,
        start_date="2026-09-01", recurrence="weekly", category="Household",
    )
    electrical = context.classroom.add_subject("Electrical")
    wiring = context.classroom.add_course(electrical.subject_id, "Residential Wiring")
    context.classroom.add_lesson(wiring.course_id, "Circuit Breakers")


def _arguments_match(arguments: dict, expected: dict) -> tuple[bool, str]:
    """2026-09-27: did the model pass the user's actual words/numbers?
    Strings match case-insensitively as substrings either way ("mower" vs
    "Riding Mower"); numbers must be equal. Only listed keys are checked."""
    for key, want in expected.items():
        got = arguments.get(key)
        if isinstance(want, (int, float)):
            try:
                if abs(float(str(got).replace(",", "").replace("$", "")) - float(want)) > 1e-6:
                    return False, f"argument {key}={got!r}, expected {want!r}"
            except (TypeError, ValueError):
                return False, f"argument {key}={got!r}, expected {want!r}"
        else:
            got_text = " ".join(got) if isinstance(got, list) else str(got or "")
            if want.lower() not in got_text.lower() and got_text.lower() not in want.lower():
                return False, f"argument {key}={got!r}, expected something like {want!r}"
            if not got_text:
                return False, f"argument {key} missing"
    return True, f"called with {arguments}"


def main() -> int:
    context = _build_context()
    _seed_fixtures(context)

    if not context.llm.is_available():
        print("Ollama is not reachable — start it (systemctl --user status ollama) and try again.")
        return 1

    failures = []
    for description, prompt, expected, *expected_args in GOLDEN_CASES:
        # A fresh, empty conversation per case — this golden set verifies
        # tool-gating/grounding decisions in isolation, one case at a
        # time, not multi-turn history behavior (see
        # tests/test_assistant_chat.py's history-specific tests for
        # that instead).
        conversation = context.conversations.start_new_active_conversation()
        messages, tools = build_chat_request(context, conversation, prompt)
        reply = context.llm.chat_with_tools(messages, tools=tools)
        called = [tc.name for tc in reply.tool_calls] if reply and reply.tool_calls else []

        if expected is None:
            ok = called == []
            detail = f"expected no tool call, got {called}"
        elif expected == "safe":
            # Derived from the real registry's own destructive flag
            # (core/assistant_actions.py), not a hand-maintained set —
            # same "one source of truth" reasoning as trigger_phrases/
            # gating_keywords in milestone 5.9, applied here after the
            # 2026-07-14 qwen2.5:7b model-comparison finding formalized
            # this flag.
            destructive_names = context.assistant_actions.destructive_action_names()
            ok = not any(name in destructive_names for name in called)
            detail = f"expected no destructive tool call, got {called}"
        else:
            ok = called == [expected]
            detail = f"expected [{expected}], got {called}"
            if ok and expected_args:
                arguments = reply.tool_calls[0].arguments
                ok, detail = _arguments_match(arguments, expected_args[0])

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {description}: {prompt!r} — {detail}")
        if not ok:
            failures.append(description)

    for description, switch, prompt, expected, max_words, lists_ok in PERSONAL_CASES:
        conversation = context.conversations.start_new_active_conversation()
        pre_turn(context, conversation, switch)
        pre_turn(context, conversation, prompt)
        messages, tools = build_chat_request(context, conversation, prompt)
        reply = context.llm.chat_with_tools(messages, tools=tools)
        ok, detail = _check_personal_reply(reply, expected, max_words, lists_ok)
        if ok and conversation.mode == PERSPECTIVE:
            invented = _invented_numbers(reply.content or "", build_why_sheet(context).to_text())
            if invented:
                ok, detail = False, f"numbers not in the fact sheet: {invented}: {(reply.content or '')[:120]!r}"
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {description}: {prompt!r} — {detail}")
        if not ok:
            failures.append(description)

    total = len(GOLDEN_CASES) + len(PERSONAL_CASES)
    print()
    print(f"{total - len(failures)}/{total} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
