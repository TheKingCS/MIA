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
import core.calendar_manager as calendar_manager_module
import core.component_manager as component_manager_module
import core.config_manager as config_manager_module
import core.conversation_manager as conversation_manager_module
import core.expedition_manager as expedition_manager_module
import core.inventory_manager as inventory_manager_module
import core.data_logger_manager as data_logger_manager_module
import core.job_manager as job_manager_module
import core.journal_manager as journal_manager_module
import core.ledger_manager as ledger_manager_module
import core.maintenance_manager as maintenance_manager_module
import core.material_manager as material_manager_module
import core.mission_manager as mission_manager_module
import core.product_manager as product_manager_module
import core.project_manager as project_manager_module
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
trail_map_library_module._TRAIL_MAPS_FILE = _TEMP_DATA_DIR / "trail_maps.json"

from core.activity_log_manager import ActivityLogManager
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.application import MIAApplication
from core.assistant_actions import AssistantActionRegistry
from core.assistant_chat import build_chat_request
from core.calendar_manager import CalendarManager
from core.component_manager import ComponentManager
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.device_help_manager import DeviceHelpManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.inventory_manager import InventoryManager
from core.data_logger_manager import DataLoggerManager
from core.job_manager import JobManager
from core.journal_manager import JournalManager
from core.ledger_manager import LedgerManager
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
        "known accepted gap: bare 'Log <value> <unit>' with no other maintenance wording doesn't gate open "
        "(same trade-off this registry already accepts for 'note ' — too common a word to match safely)",
        "Log 46000 miles for the Oil Change on my Truck",
        None,
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
    context.config.set("trips.photo_root_path", str(_TEMP_DATA_DIR / "trip_photos"))
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.calendar = CalendarManager(context)
    context.maintenance = MaintenanceManager(context)
    context.data_logger = DataLoggerManager(context)
    context.components = ComponentManager(context)
    context.scripts = ScriptLibraryManager(context)
    context.profiles = ProfileManager(context)
    context.projects = ProjectManager(context)
    context.tasks = TaskManager(context)
    # Read-only aggregation, no persisted file of its own — see
    # core/memory_manager.py's docstring — so no _DATA_DIR isolation
    # is needed the way every other manager above requires.
    context.memories = MemoryManager(context)
    context.missions = MissionManager(context)
    context.materials = MaterialManager(context)
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


def main() -> int:
    context = _build_context()
    _seed_fixtures(context)

    if not context.llm.is_available():
        print("Ollama is not reachable — start it (systemctl --user status ollama) and try again.")
        return 1

    failures = []
    for description, prompt, expected in GOLDEN_CASES:
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

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {description}: {prompt!r} — {detail}")
        if not ok:
            failures.append(description)

    print()
    print(f"{len(GOLDEN_CASES) - len(failures)}/{len(GOLDEN_CASES)} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
