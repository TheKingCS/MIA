"""
tests.core_live_voice_check
==============================

Golden-set regression check for **headless MIA Core**'s curated
Assistant action registry (`core/core_runtime.py`) — the sibling of
`tests/live_model_check.py`, which covers Home's much larger registry.
Not a pytest test (no `test_` prefix), same reason as that script: this
needs a REAL running Ollama server, and destructive tool calls are
inspected/executed against isolated fixture data, never the developer's
real `data/*.json`.

Run with: `python tests/core_live_voice_check.py` (needs `ollama serve`
running locally). Two tiers:

1. **GOLDEN_CASES** — clean-text prompts against every action in Core's
   curated registry, same shape as `live_model_check.py`'s golden set,
   scoped down to the ~20 actions `core/core_runtime.py` actually
   registers. Also asserts a few actions Core deliberately does NOT
   register (`open_module`, `set_theme`, `get_sun_moon_info`) never
   fire even when a prompt could plausibly trigger them on Home.

2. **VOICE_CASES** — the part `live_model_check.py` never covers: real
   speech noise. Each prompt is synthesized to a real `.wav` via Piper,
   then transcribed back via real Vosk (not typed text) before being
   run through the exact same `build_chat_request()` ->
   `chat_with_tools()` pipeline `core/voice_loop.py` uses. Vosk's small
   model is known-imperfect (see docs/ROADMAP.md's STT round-trip
   notes) — this tier's job is finding out whether that imperfection
   actually breaks tool-calling for realistic wearable voice commands,
   not assuming a clean-text pass implies a spoken pass would too.

Uses `core/core_runtime.py::build_core_context()` directly (not a
hand-duplicated context builder like `live_model_check.py`'s own
`_build_context()`) — this script IS the fresh-eyes reuse check for
that function, and any future drift in Core's registry surfaces here
automatically instead of needing to be kept in sync by hand.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TEMP_DATA_DIR = Path(tempfile.mkdtemp(prefix="mia_core_voice_check_"))

import core.alarm_manager as alarm_manager_module
import core.calendar_manager as calendar_manager_module
import core.config_manager as config_manager_module
import core.expedition_manager as expedition_manager_module
import core.inventory_manager as inventory_manager_module
import core.journal_manager as journal_manager_module
import core.mission_manager as mission_manager_module
import core.notification_manager as notification_manager_module
import core.trip_manager as trip_manager_module
import core.user_memory_manager as user_memory_manager_module
import core.waypoint_manager as waypoint_manager_module

# Same isolation rule as tests/live_model_check.py, applied before ANY
# manager is constructed: never let a scratch/verification run touch
# the developer's real data/*.json or config/config.json.
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
mission_manager_module._DATA_DIR = _TEMP_DATA_DIR
mission_manager_module._MISSIONS_FILE = _TEMP_DATA_DIR / "missions.json"
user_memory_manager_module._DATA_DIR = _TEMP_DATA_DIR
user_memory_manager_module._USER_MEMORIES_FILE = _TEMP_DATA_DIR / "user_memories.json"
notification_manager_module._DATA_DIR = _TEMP_DATA_DIR
notification_manager_module._NOTIFICATIONS_FILE = _TEMP_DATA_DIR / "notifications.json"

from core.app_context import AppContext
from core.assistant_chat import build_chat_request
from core.config_manager import ConfigManager
from core.conversation_manager import Conversation
from core.core_runtime import build_core_context
from core.event_bus import EventBus

# (description, prompt, expected)
#   expected == None       -> must NOT call any tool
#   expected == "safe"      -> may gate open, but must NOT call a destructive tool
#   expected == <tool name> -> must call exactly that tool
GOLDEN_CASES = [
    ("add alarm", "Set an alarm called Wake Up for 07:00", "add_alarm"),
    ("list alarms", "List my alarms", "list_alarms"),
    ("delete alarm, name-before-noun phrasing", "Delete my Wake Up alarm", "delete_alarm"),
    ("add note", "Add a note that says buy milk", "add_note"),
    ("list notes", "List my notes", "list_notes"),
    ("delete note", "Delete the note called Groceries", "delete_note"),
    ("inventory quantity question", "How many M3 bolts do I have?", "list_inventory"),
    ("add inventory item", "Add 10 carabiners to my inventory", "add_inventory_item"),
    ("delete inventory item", "Remove M3 bolts from inventory", "delete_inventory_item"),
    ("adjust inventory quantity down", "I used 5 M3 bolts", "adjust_inventory_quantity"),
    ("add calendar event", "Add an event called Dentist on 2026-09-01 at 14:00", "add_calendar_event"),
    ("list calendar events", "What's on my calendar?", "list_calendar_events"),
    ("delete calendar event", "Delete my Doctor Appointment event", "delete_calendar_event"),
    ("add waypoint", "Save a waypoint here called Ridge Camp at latitude 44.0 longitude -110.1", "add_waypoint"),
    ("list waypoints", "List my waypoints", "list_waypoints"),
    ("waypoint distance, 'from' phrasing", "What's the distance from Home to Cabin?", "waypoint_distance"),
    ("add mission", "Start a new mission called Kayak Explorer", "add_mission"),
    ("list missions", "What missions do I have?", "list_missions"),
    ("current mission phrasing", "What is my current mission?", "list_missions"),
    ("add objective", "Add an objective to my Master Angler mission: catch 5 fish, target 5", "add_objective"),
    ("log mission progress", "Log a catch for my Master Angler mission", "log_mission_progress"),
    ("delete mission", "Delete the mission called Master Angler", "delete_mission"),
    ("complete mission", "Complete the mission called Master Angler", "complete_mission"),
    ("get power status", "What's my battery level?", "get_power_status"),
    ("system health", "What's my system health?", "get_system_health"),
    ("recall recent activity", "What have I been doing recently?", "recall_recent_activity"),
    ("false-positive sanity: 'alarming' is not 'alarm '", "This is alarming news about the economy", None),
    ("false-positive sanity: ordinary use of the word 'mission'", "Our company's mission is customer satisfaction", None),
    ("false-positive sanity: 'power' unrelated to battery", "This new drill has a lot more power than my old one", None),
    ("out-of-scope info question", "What can you tell me about Honda Civics?", None),
    # --- Core deliberately excludes these — see core/core_runtime.py's docstring ---
    ("excluded from Core: open_module never fires", "Open the notes module for me", "safe"),
    ("excluded from Core: set_theme never fires", "Change the theme to low energy", "safe"),
    ("excluded from Core: get_sun_moon_info never fires", "What time does the sun set at my Cabin waypoint?", "safe"),
]

# A representative prompt per domain, run through REAL Piper TTS -> REAL
# Vosk STT before being sent to the LLM — see this module's docstring.
# Picked for phrasing that's natural to actually say out loud (not just
# type), since that's the whole point of this tier.
VOICE_CASES = [
    ("alarms", "Set an alarm called Wake Up for seven AM", "add_alarm"),
    ("notes", "Add a note that says buy more rope", "add_note"),
    ("inventory", "How many carabiners do I have", "list_inventory"),
    ("calendar", "What's on my calendar", "list_calendar_events"),
    ("waypoints", "List my waypoints", "list_waypoints"),
    ("missions", "What is my current mission", "list_missions"),
    ("power", "What's my battery level", "get_power_status"),
    ("system", "What's my system health", "get_system_health"),
]


def _build_context() -> AppContext:
    config = ConfigManager()
    events = EventBus()
    return build_core_context(config, events)


def _seed_fixtures(context: AppContext) -> None:
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    context.journal.add_entry(title="Groceries", body="buy milk and eggs")
    context.inventory.add_item(name="M3 bolts", quantity=25)
    context.inventory.add_item(name="carabiners", quantity=6)
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    context.waypoints.add_waypoint(name="Cabin", latitude=41.5, longitude=-84.5)
    context.calendar.add_event(title="Doctor Appointment", date="2026-08-14", time="09:00")
    expedition = context.expeditions.add_expedition(name="Field Season", start_date="2026-08-14")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="Hiking")
    mission = context.missions.add_mission(name="Master Angler", trip_id=trip.trip_id)
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)


def _run_case(context: AppContext, prompt: str, expected) -> tuple[bool, str, list[str]]:
    conversation = Conversation(conversation_id="check")
    messages, tools = build_chat_request(context, conversation, prompt)
    reply = context.llm.chat_with_tools(messages, tools=tools)
    called = [tc.name for tc in reply.tool_calls] if reply and reply.tool_calls else []

    if expected is None:
        return called == [], f"expected no tool call, got {called}", called
    if expected == "safe":
        destructive_names = context.assistant_actions.destructive_action_names()
        ok = not any(name in destructive_names for name in called)
        return ok, f"expected no destructive/excluded tool call, got {called}", called
    return called == [expected], f"expected [{expected}], got {called}", called


def _run_golden_cases(context: AppContext) -> int:
    print("=== Tier 1: clean-text golden set (Core's curated registry) ===")
    failures = []
    for description, prompt, expected in GOLDEN_CASES:
        ok, detail, _ = _run_case(context, prompt, expected)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {description}: {prompt!r} — {detail}")
        if not ok:
            failures.append(description)
    print(f"\n{len(GOLDEN_CASES) - len(failures)}/{len(GOLDEN_CASES)} passed.\n")
    return len(failures)


def _run_voice_cases(context: AppContext) -> int:
    print("=== Tier 2: real Piper TTS -> real Vosk STT -> tool-calling ===")
    if not (context.voice.is_tts_available() and context.voice.is_stt_available()):
        print("Voice models unavailable — skipping tier 2 (see deploy/download_voice_models.sh).")
        return 0

    wav_path = Path(tempfile.gettempdir()) / "core_voice_check_case.wav"
    failures = []
    for domain, prompt, expected in VOICE_CASES:
        synthesized = context.voice.synthesize(prompt, wav_path)
        transcript = context.voice.transcribe(synthesized) if synthesized else None
        if not transcript:
            print(f"[FAIL] {domain}: STT produced nothing for {prompt!r}")
            failures.append(domain)
            continue

        ok, detail, called = _run_case(context, transcript, expected)
        status = "PASS" if ok else "FAIL"
        noisy = " (noisy)" if transcript.lower() != prompt.lower() else ""
        print(f"[{status}] {domain}: said {prompt!r} -> heard {transcript!r}{noisy} — {detail}")
        if not ok:
            failures.append(domain)
    print(f"\n{len(VOICE_CASES) - len(failures)}/{len(VOICE_CASES)} passed.\n")
    return len(failures)


def main() -> int:
    context = _build_context()
    _seed_fixtures(context)

    if not context.llm.is_available():
        print("Ollama is not reachable — start it (systemctl --user status ollama) and try again.")
        return 1

    golden_failures = _run_golden_cases(context)
    voice_failures = _run_voice_cases(context)

    return 1 if (golden_failures or voice_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
