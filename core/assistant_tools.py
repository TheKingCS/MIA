"""
core.assistant_tools
======================

The desktop's own Assistant tools, without the window (the MIA Runtime,
DEC-0155, step 4).

What it is: `_register_assistant_actions` and the 111 tool handlers it
registers inline (`_action_*`, with the `_resolve_*` helpers they share),
plus the 62 tool families it registers from their own modules
(`core/assistant_*_actions.py`). Together they are MIA's full tool
registry. Until 2026-11-15 they were methods of the Qt window's
`MIAApplication`, so a MIA without a window (the phone, a service) only had
the smaller hand-picked list in `core/core_runtime.py`. They were moved
here unchanged; this file imports nothing from Qt, `gui/` or `modules/`.

How it's used: `AssistantTools` is a mixin. `MIAApplication` inherits it
(the tests that call `MIAApplication._action_...` still do), and the
headless runtime (`core/runtime.py`) inherits it too, so both register the
very same tools. Every handler is a static function of `(context,
arguments)`; only `_register_assistant_actions` uses `self.context`.

A handler that opens a desktop screen (`open_module`, `set_theme`) says so
plainly where there's no window.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
import urllib.error

from core.app_context import AppContext
from core.assistant_accessibility_actions import register_accessibility_actions
from core.assistant_actions import AssistantAction
from core.assistant_answer_style_actions import register_answer_style_actions
from core.assistant_asset_part_actions import register_asset_part_actions
from core.assistant_backup_actions import register_backup_actions
from core.assistant_desktop_actions import register_desktop_actions
from core.assistant_library_actions import register_library_actions
from core.assistant_project_plan_actions import register_project_plan_actions
from core.assistant_browser_actions import register_browser_actions
from core.assistant_business_view_actions import register_business_view_actions
from core.assistant_camera_actions import register_camera_actions
from core.assistant_closet_actions import register_closet_actions
from core.assistant_world_intel_actions import register_world_intel_actions
from core.assistant_requirement_actions import register_requirement_actions
from core.assistant_price_actions import register_price_actions
from core.assistant_app_registry_actions import register_app_registry_actions
from core.assistant_comm_actions import register_communication_actions
from core.assistant_connection_actions import register_connection_actions
from core.assistant_cooking_actions import register_cooking_actions
from core.assistant_correction_actions import register_correction_actions
from core.assistant_creation_actions import register_creation_actions
from core.assistant_direction_actions import register_direction_actions
from core.assistant_domain_actions import register_domain_actions
from core.assistant_dungeon_actions import (
    register_checkin_actions,
    register_dungeon_actions,
    register_loop_actions,
)
from core.assistant_email_actions import register_email_actions
from core.assistant_energy_actions import register_energy_actions
from core.assistant_focus_actions import register_focus_actions
from core.assistant_game_actions import register_game_actions
from core.assistant_goods_actions import register_goods_actions
from core.assistant_health_actions import register_health_actions
from core.assistant_homestead_actions import register_homestead_actions
from core.assistant_household_actions import register_household_actions
from core.assistant_humor_actions import register_humor_actions
from core.assistant_inbox_actions import register_inbox_actions
from core.assistant_lab_actions import register_lab_actions
from core.assistant_life_actions import register_life_actions
from core.assistant_life_event_actions import register_life_event_actions
from core.assistant_link_actions import register_link_actions
from core.assistant_lookup import resolve_by_name
from core.assistant_more_twins_actions import register_more_twins_actions
from core.assistant_notification_actions import register_notification_actions
from core.assistant_achievement_actions import register_achievement_actions
from core.mission_trophy_actions import register_mission_trophy_actions
from core.youtube_actions import register_youtube_actions
from core.repertoire_actions import register_repertoire_actions
from core.canning_fix import register_canning_fix_actions
from core.greenhouse_adjust import register_greenhouse_adjust_actions
from core.outage_actions import register_outage_actions
from core.utility_bills import register_utility_bill_actions
from core.spending_pace import register_spending_pace_actions
from core.catch_actions import register_catch_actions
from core.make_next import register_make_next_actions
from core.project_time import register_project_time_actions
from core.outdoor_work import register_outdoor_work_actions
from core.tax_setaside import register_tax_setaside_actions
from core.fishing_times import register_fishing_times_actions
from core.hen_laying import register_hen_laying_actions
from core.homestead_sums import register_homestead_sum_actions
from core.meat_cure import register_meat_cure_actions
from core.solar_size import register_solar_size_actions
from core.canning_times import register_canning_time_actions
from core.rent_collected import register_rent_collected_actions
from core.calendar_move import register_calendar_move_actions
from core.drills import register_drill_tools
from core.part_specs import register_part_spec_tools
from core.esp32_lab import register_esp32_lab_actions
from core.assistant_ownership_actions import register_ownership_actions
from core.assistant_path_actions import register_path_actions
from core.assistant_plan_actions import register_plan_actions
from core.assistant_playlist_actions import register_playlist_actions
from core.assistant_progress_actions import register_progress_actions
from core.assistant_proposal_actions import register_proposal_actions
from core.assistant_records_actions import register_records_actions
from core.assistant_screen_tools import register_screen_tools
from core.assistant_self_actions import register_capability_actions, register_self_actions, register_self_care_actions
from core.assistant_starter_actions import register_starter_actions
from core.assistant_subscription_actions import register_subscription_actions
from core.assistant_tagging_actions import register_tagging_actions
from core.assistant_taught_skill_actions import register_taught_skill_actions
from core.assistant_textbook_actions import register_textbook_actions
from core.assistant_today_actions import register_today_actions
from core.assistant_toolbox_actions import register_toolbox_actions
from core.assistant_trip_route_actions import register_trip_route_actions
from core.assistant_ual_actions import register_ual_actions
from core.assistant_undo_actions import register_undo_actions
from core.assistant_voice_choice_actions import register_voice_choice_actions
from core.assistant_waypoint_actions import register_waypoint_actions
from core.assistant_why_actions import register_why_actions
from core.assistant_world_actions import register_world_actions
from core.budget_manager import (
    Bill,
    EXPENSE_CATEGORIES as BUDGET_EXPENSE_CATEGORIES,
    INCOME_CATEGORIES as BUDGET_INCOME_CATEGORIES,
    IncomeSource,
    days_until_bill_due,
)
from core.budget_nudges import build_nudge_message
from core.calendar_manager import CALENDAR_RECURRENCE_TYPES
from core.connectivity import connectivity_action
from core.context_assembler import (
    assemble_life_state,
    assemble_life_state_v2,
    describe_life_state_v2,
    format_life_state_summary,
)
from core.device_profile import CORE, get_device_profile
from core.failure_actions import register_failure_actions
from core.hash_identifier import identify_hash
from core.journal_reflection import journal_reflection_action
from core.maintenance_manager import (
    ASSET_CATEGORIES as MAINTENANCE_ASSET_CATEGORIES,
    MaintenanceTask,
    days_until_due as maintenance_days_until_due,
    is_sensor_task_due,
    meter_used_since_last,
)
from core.online_watch import remind_when_online_action
from core.password_strength import assess_password
from core.port_scanner import scan_ports
from core.project_manager import PROJECT_STATUSES
from core.real_estate_manager import Property, equity as property_equity
from core.region import money
from core.specialists import register_specialist_actions
from core.assistant_teamwork_actions import register_teamwork_actions
from core.subnet_calculator import calculate_subnet
from core.system_health import format_system_health, read_system_health
from core.talk_it_out import register_journal_actions
from core.trail_map_library import NotAPdfError
from core.trip_manager import ACTIVITY_TYPES
from core.waypoint_manager import WAYPOINT_CATEGORIES

# Assistant tool calls run synchronously on the GUI thread (see
# modules/assistant/module.py's docstring) — unlike the Field Kit
# Security tab's port scanner, which offloads to a QThread
# (modules/field_kit/port_scan_worker.py) precisely because a full
# COMMON_PORTS sweep can take several seconds. _action_scan_ports below
# deliberately checks only these 3 fast, common ports with a short
# timeout to keep worst-case blocking time small (~0.9s) rather than
# freezing the UI for a full sweep; point the user at the Security tab
# for anything more thorough.
_ASSISTANT_SCAN_PORTS = (22, 80, 443)
_ASSISTANT_SCAN_TIMEOUT_SECONDS = 0.3

# A word for a kind of thing -> its maintenance category (list_maintenance_tasks' query).
MAINTENANCE_QUERY_CATEGORIES = {
    "vehicle": "Vehicle", "car": "Vehicle", "truck": "Vehicle", "auto": "Vehicle", "motorcycle": "Vehicle",
    "power equipment": "Power Equipment", "equipment": "Power Equipment", "mower": "Power Equipment",
    "appliance": "Appliance", "property": "Property", "house": "Property", "home": "Property",
    "garden": "Garden/Plant", "greenhouse": "Garden/Plant", "plant": "Garden/Plant", "garden/plant": "Garden/Plant",
    "tool": "Tool",
}


class AssistantTools:
    """MIA's full Assistant tool registry as a mixin: `_register_assistant_actions()` and every handler (see the
    module's opening). The class that inherits it has `self.context`."""

    # The desktop window's themes, id -> name, for `set_theme`. core never imports gui, so the desktop app fills
    # this in when it loads (core/application.py); a MIA with no window leaves it empty.
    DESKTOP_THEMES: dict = {}

    def _register_assistant_actions(self) -> None:
        """
        Register the built-in actions the Assistant can invoke via
        core/llm_manager.py's chat_with_tools() — docs/ROADMAP.md
        milestone 5.5 (MIA OS's settings pages and Linux apps among them, FW-11; her offline library's look-ups and fetches, core/assistant_library_actions.py; plans made together, core/assistant_project_plan_actions.py; their trigger phrases cover everyday ways of
        asking, "spent $120 at the feed store", "I bought 3 bags of chicken feed", "how's my budget looking", "where did I
        put the post hole digger", "what did I miss?", "we bought the house" as a property: never "where is my wife?" or
        "what's new in the news": tests/test_everyday_phrasing_routing.py; "what phase is the moon tonight?" and "when's
        the next full moon?" reach get_sun_moon_info, never "howl at the full moon").
        Registered here (not in modules/assistant/) for
        the same reason search providers and calculators are: this is
        the one place independent core services get wired together
        (tools in their own files register here too, such as
        core/assistant_screen_tools.py: look it up online, what isn't
        working, past conversations; core/assistant_self_actions.py: her
        model, and her care of herself, DEC-0222/0225; core/activity_watch.py:
        what he's working on, DEC-0197; core/recall_index.py: recall by
        meaning, DEC-0210).
        Every handler below is a `@staticmethod` — a pure function of
        (context, arguments) — except that none of them actually need
        `self` at all; `context.module_manager` (set right above) is
        what `_action_open_module` reads to validate the target
        actually exists. That staticmethod-purity is what let
        `core/core_runtime.py`'s headless Core entry point curate its
        own smaller Assistant action set (see that module) without
        having to duplicate this class or its Qt/gui-heavy imports.
        Every app's voice tools are registered here (DEC-0125:
        core/parity.py measures what this registers), including the
        photo search the headless Core had alone until 2026-11-07, and
        the Toolbox's board feet, concrete and alarm switch, the Lab's
        delete a reading, the Household's pause or resume a routine and
        Navigation's change a waypoint and notifications read out and marked
        read (2026-11-07).
        Taught skills' tools (DEC-0123) are registered here too.
        Where the live model picked a neighbouring tool (2026-11-24), a description names the one to use instead
        (list_inventory and list_materials, list_trips and get_trip_route...).
        my_achievements, the achievements log by voice, comes from core/assistant_achievement_actions.py.
        add_mission_reward and count_toward_mission (a mission's rewards beyond XP, objectives counted from records)
        come from core/mission_trophy_actions.py.
        find_on_youtube, save_from_youtube and play_on_youtube come from core/youtube_actions.py.
        learned_a_song and songs_i_can_play (his songbook) come from core/repertoire_actions.py.
        fix_jar_count (a batch put up with the wrong count) comes from core/canning_fix.py.
        adjust_greenhouse (the greenhouse node's targets, DEC-0185) comes from core/greenhouse_adjust.py.
        power_outage (the power outage clock) comes from core/outage_actions.py.
        why_bill_high (why an energy bill was high) comes from core/utility_bills.py; spending_vs_usual from core/spending_pace.py; log_catch and whats_biting from core/catch_actions.py; what_to_make_next from core/make_next.py; work_outside_wind_chill_heat_index from core/outdoor_work.py; tax_set_aside from core/tax_setaside.py; best_time_to_fish from core/fishing_times.py; why_hens_not_laying from core/hen_laying.py; meat_cure from core/meat_cure.py; size_solar from core/solar_size.py; canning_time from core/canning_times.py; rent_collected from core/rent_collected.py; move_calendar_event from core/calendar_move.py; flash_lab, check_lab and lab_board from core/esp32_lab.py; build_along and simulate_lab from core/esp32_sim.py; start_drill from core/drills.py; import_part_spec and part_specs from core/part_specs.py.
        The homestead sums too (water to store, generator hours, hens for eggs).
        list_calendar_events takes his words (`prompt_arg`).
        add_expense offers the Animals & Feed category.
        add_calendar_event offers a daily repeat.
        The hours he puts into his projects too (core/project_time.py).
        """
        self.context.assistant_actions.register(connectivity_action())
        self.context.assistant_actions.register(remind_when_online_action())
        register_domain_actions(self.context.assistant_actions)
        register_life_actions(self.context.assistant_actions)
        register_journal_actions(self.context.assistant_actions)
        self.context.assistant_actions.register(journal_reflection_action())
        register_why_actions(self.context.assistant_actions)
        register_communication_actions(self.context.assistant_actions)
        register_focus_actions(self.context.assistant_actions)
        register_email_actions(self.context.assistant_actions)
        register_undo_actions(self.context.assistant_actions)
        register_today_actions(self.context.assistant_actions)
        register_self_actions(self.context.assistant_actions)  # "what model are you?" from the runtime
        register_self_care_actions(self.context.assistant_actions)  # her own changes, repairs, protected list
        from core.activity_watch import register_activity_actions

        register_activity_actions(self.context.assistant_actions)  # what he's working on (DEC-0197)
        from core.recall_index import register_recall_actions

        register_recall_actions(self.context.assistant_actions)  # "what do I have about...?" by meaning (DEC-0210)
        register_capability_actions(self.context.assistant_actions)  # what MIA can do, how she's built (DEC-0041)
        register_specialist_actions(self.context.assistant_actions)  # her specialists' workbooks (DEC-0109)
        register_teamwork_actions(self.context.assistant_actions)  # a project's workspace and team (T2)
        register_energy_actions(self.context.assistant_actions)  # solar, generator, propane by voice (T-0053)
        register_path_actions(self.context.assistant_actions)  # learning paths: guitar and more (DEC-0111, DEC-0112)
        register_browser_actions(self.context.assistant_actions)  # MIA's own browser, taught by showing (DEC-0117)
        register_goods_actions(self.context.assistant_actions)  # eggs, goods, freedom, deadlines by voice
        register_cooking_actions(self.context.assistant_actions)  # cook mode by voice (DEC-0113, DEC-0125)
        register_toolbox_actions(self.context.assistant_actions)  # board feet, concrete, alarms on/off (DEC-0125)
        register_lab_actions(self.context.assistant_actions)  # the Lab: delete a reading by voice (DEC-0125)
        register_household_actions(self.context.assistant_actions)  # pause or resume a routine by voice (DEC-0125)
        register_waypoint_actions(self.context.assistant_actions)  # rename a waypoint, its kind and notes (DEC-0125)
        register_trip_route_actions(self.context.assistant_actions)  # a trip's route and checkpoints by voice (DEC-0125)
        register_backup_actions(self.context.assistant_actions)  # when MIA was last backed up (DEC-0125)
        register_desktop_actions(self.context.assistant_actions)  # MIA OS's settings pages and Linux apps (FW-11)
        register_library_actions(self.context.assistant_actions)  # her offline library: look up, fetch packs
        register_project_plan_actions(self.context.assistant_actions)  # plans made together, then missions
        register_voice_choice_actions(self.context.assistant_actions)  # MIA's own voice, effect and volume (DEC-0125)
        register_subscription_actions(self.context.assistant_actions)  # "still using it?" on subscriptions (DEC-0054)
        register_proposal_actions(self.context.assistant_actions)  # mission ideas and field recordings (DEC-0125)
        register_asset_part_actions(self.context.assistant_actions)  # the parts an asset uses
        register_health_actions(self.context.assistant_actions)  # sleep, visits, medications, records (DEC-0129)
        register_notification_actions(self.context.assistant_actions)  # read out and mark notifications read (DEC-0125)
        register_achievement_actions(self.context.assistant_actions)  # the achievements log by voice (2026-11-24)
        register_mission_trophy_actions(self.context.assistant_actions)  # mission rewards beyond XP, counted objectives
        register_youtube_actions(self.context.assistant_actions)  # YouTube in Music: find, save, play
        register_repertoire_actions(self.context.assistant_actions)  # his songbook: songs he can play
        register_canning_fix_actions(self.context.assistant_actions)  # a batch of jars put up with the wrong count
        register_greenhouse_adjust_actions(self.context.assistant_actions)  # the greenhouse node's targets (DEC-0185)
        register_outage_actions(self.context.assistant_actions)  # the power outage clock
        register_utility_bill_actions(self.context.assistant_actions)  # why an energy bill was high
        register_spending_pace_actions(self.context.assistant_actions)  # spending against his usual month
        register_catch_actions(self.context.assistant_actions)  # his catch log
        register_make_next_actions(self.context.assistant_actions)  # what to make next to sell
        register_project_time_actions(self.context.assistant_actions)  # the hours he puts into his projects
        register_outdoor_work_actions(self.context.assistant_actions)  # heat index and wind chill for work
        register_tax_setaside_actions(self.context.assistant_actions)  # taxes to set aside on the workshop
        register_fishing_times_actions(self.context.assistant_actions)  # when to go fishing
        register_hen_laying_actions(self.context.assistant_actions)  # why the hens stopped laying
        register_homestead_sum_actions(self.context.assistant_actions)  # water to store, generator hours, hens for eggs
        register_meat_cure_actions(self.context.assistant_actions)  # curing salt for meat
        register_solar_size_actions(self.context.assistant_actions)  # sizing solar from his use
        register_canning_time_actions(self.context.assistant_actions)  # canning times for his altitude
        register_rent_collected_actions(self.context.assistant_actions)  # rent collected by property
        register_calendar_move_actions(self.context.assistant_actions)  # moving a calendar event
        register_esp32_lab_actions(self.context.assistant_actions)  # the ESP32 lab bench
        register_drill_tools(self.context.assistant_actions)  # scenario drills
        register_part_spec_tools(self.context.assistant_actions)  # part specs for the free build
        register_screen_tools(self.context.assistant_actions)  # look it up online, what isn't working, past conversations
        register_dungeon_actions(self.context.assistant_actions)  # the Dungeon: shifts, loot, quests (DEC-0046)
        register_closet_actions(self.context.assistant_actions)  # Smart Closet: what to wear, outfits, ratings (DEC-0162)
        register_world_intel_actions(self.context.assistant_actions)  # World Intelligence: watches and finds (DEC-0170)
        register_requirement_actions(self.context.assistant_actions)  # what each project needs (DEC-0172)
        register_price_actions(self.context.assistant_actions)  # prices seen, comparisons, trip cost (DEC-0172)
        register_app_registry_actions(self.context.assistant_actions)  # her own apps, from their manifests (DEC-0178)
        register_taught_skill_actions(self.context.assistant_actions)  # taught skills: watch me, run, answer (DEC-0123)
        register_ual_actions(self.context.assistant_actions)  # the Universal Action Layer: actions on what is given (DEC-0165)
        register_creation_actions(self.context.assistant_actions)  # screens MIA made for you, by voice (DEC-0091)
        register_game_actions(self.context.assistant_actions)  # boss battles and questlines by voice (DEC-0028)
        register_loop_actions(self.context.assistant_actions)  # the loop: when things happen (DEC-0047)
        register_checkin_actions(self.context.assistant_actions)  # the Sunday check-in (DEC-0047)
        register_failure_actions(self.context.assistant_actions)  # the Fix-It Log (DEC-0049)
        register_ownership_actions(self.context.assistant_actions)
        register_humor_actions(self.context.assistant_actions)  # how funny she is, asked for in chat
        register_progress_actions(self.context.assistant_actions)  # Character, Skills, Reward Shop (DEC-0125)
        register_camera_actions(self.context.assistant_actions)  # the Security cameras by voice (DEC-0125)
        register_correction_actions(self.context.assistant_actions)  # fixing groceries, recipes, bills by voice (DEC-0125)
        register_playlist_actions(self.context.assistant_actions)  # making and changing playlists by voice (DEC-0125)
        register_more_twins_actions(self.context.assistant_actions)  # remember, orders paid, weigh-ins, missions (DEC-0125)
        register_records_actions(self.context.assistant_actions)  # Insurance, Kept, Operating, Play, Files (DEC-0125)
        from core.vault_captions import register_vault_caption_actions

        register_vault_caption_actions(self.context.assistant_actions)  # "find my photos of the creek", on the PC too
        register_plan_actions(self.context.assistant_actions)  # plans, blueprints and material lists
        register_accessibility_actions(self.context.assistant_actions)
        register_direction_actions(self.context.assistant_actions)  # My Directions by voice (DEC-0141)
        register_answer_style_actions(self.context.assistant_actions)  # how MIA answers, by voice (DEC-0138)
        register_world_actions(self.context.assistant_actions)  # Living Worlds by voice (DEC-0134)
        register_business_view_actions(self.context.assistant_actions)  # the Businesses by voice (DEC-0153)
        register_connection_actions(self.context.assistant_actions)  # "don't bring that up" (DEC-0146)
        register_starter_actions(self.context.assistant_actions)
        register_life_event_actions(self.context.assistant_actions)
        register_link_actions(self.context.assistant_actions)
        register_homestead_actions(self.context.assistant_actions)
        register_textbook_actions(self.context.assistant_actions)
        register_inbox_actions(self.context.assistant_actions)
        register_tagging_actions(self.context.assistant_actions)
        self.context.assistant_actions.register(AssistantAction(
            name="open_module",
            domain="system",
            description="Open/navigate to a MIA module by its module_id.",
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
            domain="alarms",
            description=(
                "Create a new alarm in MIA for a specific clock time (e.g. wake up at 07:00). "
                "NOT for recurring vehicle/equipment upkeep on a day interval (e.g. 'change the oil "
                "every 6 months') — use add_maintenance_task for that instead."
            ),
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
            domain="alarms",
            description="List the user's current alarms in MIA",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_alarms,
            trigger_phrases=(
                "list my alarms", "list alarms", "what alarms", "show my alarms", "do i have any alarms",
                # 2026-07-18: real gap — "when is my next alarm" matched nothing at all.
                "next alarm", "when is my alarm",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_alarm",
            domain="alarms",
            destructive=True,
            description="Delete an existing alarm in MIA by its label.",
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
            handler=self._action_add_note,
            trigger_phrases=("add a note", "take a note", "make a note", "write down", "jot down"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_notes",
            domain="notes",
            description=(
                "List or search the user's journal/note entries in MIA's Notes module. "
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
                # 2026-07-18: real gap — "anything I wrote down" matched
                # nothing. Deliberately overlaps add_note's own "write
                # down" trigger (both domains attach together, same
                # already-proven "let the model disambiguate via tool
                # descriptions" pattern as other collision pairs in this
                # registry) rather than trying to avoid it.
                "anything i wrote down", "what did i write down",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_note",
            domain="notes",
            destructive=True,
            description="Delete an existing journal/note entry in MIA's Notes module by its title.",
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
            handler=self._action_add_inventory_item,
            trigger_phrases=("add to inventory", "add an inventory item", "inventory item"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_inventory",
            domain="inventory",
            description=("List or search MIA's household Inventory (tools, parts, gear and supplies around the home), "
                         "including quantities: 'how many X do I have'. Not the Workshop's materials or products "
                         "(list_materials, list_products). Leave query empty to list everything."),
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
            #
            # milestone 5.15 finding: once the registry crossed ~39
            # tools (adding the Security tab's 4 tools), "How many M3
            # bolts do I have?" started reproducibly (5/5 runs)
            # hallucinating a non-existent "get_inventory_quantity"
            # tool-call-shaped string as plain content instead of
            # calling this tool — not sampling noise (see
            # llm_manager.py's temperature=0 note), a real
            # tool-count/schema-interference regression isolated by
            # bisecting the attached tool set. Spelling out the "how
            # many X do I have" phrasing directly in this description
            # (rather than renaming/removing any tool) fixed it
            # reliably at the full 39-tool count — cheaper than
            # fighting the registry's all-or-nothing gating design.
            trigger_phrases=("inventory", "do i have", "where did i put", "where did i leave the", "where did i leave my"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_inventory_item",
            domain="inventory",
            destructive=True,
            description="Remove an item entirely from MIA's Inventory tool by name.",
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
            handler=self._action_adjust_inventory_quantity,
            trigger_phrases=("i used", "used up", "use up", "got more", "received more"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_waypoints",
            domain="waypoints",
            description="List or search the user's saved waypoints (named locations) in MIA's Navigation module.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to search waypoint names/notes for."},
                },
                "required": [],
            },
            handler=self._action_list_waypoints,
            trigger_phrases=(
                "waypoint", "waypoints", "list my waypoints", "list waypoints",
                # 2026-07-18: real gap — "what locations have I saved"
                # matched nothing (bare "waypoint(s)" wasn't said at all).
                "locations have i saved", "saved locations",
                # 2026-07-19: real gap found via tests/core_live_voice_check.py's
                # Piper-TTS-to-Vosk-STT tier — Vosk's small model
                # transcribes "waypoint(s)" as the two separate words
                # "way point(s)" 100% of the time in testing (6/6 across
                # several phrasings/positions), so the bare "waypoint"
                # trigger above never actually fires from real speech.
                "way point", "way points",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
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
            handler=self._action_waypoint_distance,
            trigger_phrases=("distance to", "distance from", "how far is", "how far apart", "bearing to", "bearing from"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_waypoint",
            domain="waypoints",
            destructive=True,
            description="Delete an existing saved waypoint in MIA's Navigation module by name.",
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
            domain="system",
            description="Get a live snapshot of this device's system health: CPU, memory, disk, temperature, and network usage.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_system_health,
            trigger_phrases=(
                "system health", "cpu usage", "cpu temperature", "memory usage",
                "disk usage", "diagnostics", "how's the system", "check diagnostics",
                # 2026-07-18: real gap — "is everything running okay"
                # matched nothing at all (no tool call, not even
                # recognized as an action request).
                "everything ok", "everything okay", "everything running",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
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
        self.context.assistant_actions.register(AssistantAction(
            name="list_observations",
            domain="system",
            description=(
                "List everything MIA has currently noticed and hasn't resolved yet — overdue/due-soon "
                "Maintenance tasks and Missions that have gone stale. Use this for questions like 'what "
                "have you noticed' or 'anything I should know about' or 'any observations'."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_observations,
            trigger_phrases=(
                "what have you noticed", "any observations", "anything i should know",
                "what's open", "what needs attention", "system observations",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_field_captures",
            domain="system",
            description=(
                "List pending field captures — voice notes recorded on a MIA Lite field device, waiting "
                "for review before they become real Journal entries. Use this for questions like 'do I "
                "have any field captures' or 'what did I record in the field' or 'any voice notes waiting'."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_field_captures,
            trigger_phrases=(
                "field captures", "voice notes waiting", "what did i record",
                "captures to review", "field notes waiting",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_life_state",
            domain="system",
            description=(
                "Give a synthesized status report of what's currently going on in the active profile's "
                "life — active missions, live streaks, skill trends (growing/declining/dormant), open "
                "system observations, overdue maintenance, and active projects, all in one answer. Use "
                "this for broad questions like 'what's going on with me', 'how am I doing', 'give me a "
                "status report', or 'what's my life state' — not for a single-domain question that "
                "another action already answers more precisely."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_life_state,
            trigger_phrases=(
                "what's going on with me", "how am i doing", "status report",
                "my life state", "give me an overview", "catch me up",
                # "catch me up" said the other ways: what needs him, what she's holding, what she did on her own
                "what did i miss", "while i was out", "while i was gone", "any messages for me",
                "messages for me", "did you do on your own", "you do on your own", "bring me up to speed",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_waypoint",
            domain="waypoints",
            description="Save a new named waypoint (location) in MIA's Navigation module.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name for the waypoint."},
                    "latitude": {"type": "number", "description": "Latitude in decimal degrees."},
                    "longitude": {"type": "number", "description": "Longitude in decimal degrees."},
                    "grid": {"type": "string",
                             "description": "Or an MGRS grid reference instead of latitude and longitude, "
                                            "like 18S UJ 23478 06483."},
                    "category": {
                        "type": "string",
                        "description": "Optional category: Campsite, Trailhead, Water Source, Viewpoint, or Other.",
                    },
                },
                "required": ["name"],
            },
            handler=self._action_add_waypoint,
            trigger_phrases=("add a waypoint", "save a waypoint", "new waypoint", "mark a waypoint"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_sun_moon_info",
            domain="waypoints",
            description=(
                "Today's sunrise and sunset, and the moon tonight: its phase (days to the full or new moon), "
                "moonrise and moonset, for his town or a saved waypoint he names — how much daylight is left, "
                "the moon for night navigation. When to fish by the moon is best_time_to_fish."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "waypoint_name": {"type": "string",
                                      "description": "A saved waypoint, only if he named one; else his town."},
                },
                "required": [],
            },
            handler=self._action_get_sun_moon_info,
            trigger_phrases=(
                "sunrise", "sunset", "moon phase", "when does the sun", "when will the sun",
                "what time does the sun", "how much daylight", "phase of the moon", "phase is the moon",
                "moonrise", "moonset", "moon rise", "moon come up", "next full moon", "next new moon",
                "full moon tonight", "is the full moon", "the full moon be", "is the new moon",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_expedition",
            domain="expeditions",
            description="Start a new Expedition (a dated outing that can hold multiple trips) in MIA's Expeditions module.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name for the expedition."},
                    "start_date": {"type": "string", "description": "Optional start date, YYYY-MM-DD."},
                    "location": {"type": "string", "description": "Optional region/area name."},
                },
                "required": ["name"],
            },
            handler=self._action_add_expedition,
            trigger_phrases=("start an expedition", "new expedition", "add an expedition", "create an expedition", "plan an expedition"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_expeditions",
            domain="expeditions",
            description=("List the user's Expeditions in MIA by name only. To describe or recap one expedition, use "
                         "recall_expedition."),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_expeditions,
            trigger_phrases=(
                "list my expeditions", "list expeditions", "what expeditions", "show my expeditions",
                # 2026-07-18: real gap — "how many expeditions have I
                # been on" matched nothing at all.
                "how many expeditions", "expeditions have i",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="recall_expedition",
            domain="expeditions",
            description=(
                "Get a detailed recap of ONE Expedition in MIA's Memories: duration, "
                "distance/pace per activity type, waypoint categories visited, latest "
                "journal/conditions entry, and photo count. This is a single-Expedition "
                "summary, NOT a bare list — use list_expeditions instead for 'what "
                "expeditions do I have'-style questions. Leave name empty for the most "
                "recent Expedition."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Optional Expedition name. Leave empty for the most recent one.",
                    },
                },
                "required": [],
            },
            handler=self._action_recall_expedition,
            # "Tell me about my Field Season expedition" (name inserted
            # before the noun) doesn't match any of these — same
            # accepted trade-off as delete_project/delete_task/
            # mark_task_done (see tests/test_assistant_action_gating.py's
            # test_delete_project_phrasing_gates_open docstring). "the
            # expedition called X" phrasing (name after the noun) is
            # supported instead via the dedicated triggers below.
            trigger_phrases=(
                "tell me about my last expedition", "tell me about my expedition",
                "tell me about the expedition", "describe my expedition",
                "describe the expedition", "recap my expedition", "expedition recap",
                "what did i do on my expedition", "what have i done on my expedition",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_trip",
            domain="expeditions",
            description="Add a new Trip (one hike, paddle, ride, fishing trip, etc.) under an existing Expedition in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "expedition_name": {
                        "type": "string",
                        "description": "The name of the Expedition this trip belongs to (must already exist).",
                    },
                    "name": {"type": "string", "description": "A short name for the trip."},
                    "activity_type": {
                        "type": "string",
                        "description": "Optional activity type: Hiking, Camping, Fishing, Kayaking, Biking, or Other.",
                    },
                    "start_date": {"type": "string", "description": "Optional start date, YYYY-MM-DD."},
                },
                "required": ["expedition_name", "name"],
            },
            handler=self._action_add_trip,
            trigger_phrases=("add a trip", "new trip", "start a trip", "plan a trip", "create a trip"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_trips",
            domain="expeditions",
            description=("List the user's Trips in MIA, soonest first ('what's my next trip?'), optionally filtered "
                         "to one Expedition by name."),
            parameters={
                "type": "object",
                "properties": {
                    "expedition_name": {
                        "type": "string",
                        "description": "Optional Expedition name to filter by. Leave empty for all trips.",
                    },
                },
                "required": [],
            },
            handler=self._action_list_trips,
            trigger_phrases=("list my trips", "list trips", "what trips", "show my trips"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_gear_item",
            domain="expeditions",
            description="Add an item to a Trip's gear checklist in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "trip_name": {
                        "type": "string",
                        "description": "The name of the trip to add gear to (must already exist).",
                    },
                    "label": {"type": "string", "description": "The gear item's name, e.g. 'Tent' or 'First aid kit'."},
                },
                "required": ["trip_name", "label"],
            },
            handler=self._action_add_gear_item,
            trigger_phrases=("add gear", "add to my gear", "gear list", "packing list"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_trip_log_entry",
            domain="expeditions",
            description=(
                "Add a dated journal/log entry to a specific Trip in MIA, optionally "
                "recording weather/conditions. Use this instead of add_note when the user "
                "is logging something about a specific trip/outing (arriving somewhere, "
                "conditions encountered, etc.), not a general-purpose note."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "trip_name": {
                        "type": "string",
                        "description": "The name of the trip this log entry belongs to (must already exist).",
                    },
                    "title": {"type": "string", "description": "A short title for the log entry."},
                    "body": {"type": "string", "description": "Optional body text describing what happened."},
                    "conditions": {
                        "type": "string",
                        "description": "Optional weather/conditions, e.g. 'Clear, ~15C, light wind'.",
                    },
                },
                "required": ["trip_name", "title"],
            },
            handler=self._action_add_trip_log_entry,
            trigger_phrases=("trip journal", "log entry for my trip", "log my arrival", "add to my trip log", "trip log"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_expedition",
            domain="expeditions",
            destructive=True,
            description="Delete an existing Expedition in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the expedition to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_expedition,
            # "Delete my Field Season expedition" (name inserted before
            # the noun) doesn't match any of these — same accepted
            # trade-off as delete_project/delete_task (see
            # tests/test_assistant_action_gating.py). "the expedition
            # called X"/"delete the expedition" (name after) is supported.
            trigger_phrases=("delete an expedition", "delete my expedition", "remove an expedition", "delete the expedition"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_trip",
            domain="expeditions",
            destructive=True,
            description="Delete an existing Trip in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the trip to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_trip,
            # Same accepted name-before-noun trade-off as delete_expedition
            # above — "delete the trip called X" gates open, "delete my
            # Day 1 trip" (name in the middle) doesn't.
            trigger_phrases=("delete a trip", "delete my trip", "remove a trip", "delete the trip"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="toggle_gear_packed",
            domain="expeditions",
            description="Mark a gear checklist item on a Trip as packed or not packed (toggles its current state).",
            parameters={
                "type": "object",
                "properties": {
                    "trip_name": {"type": "string", "description": "The name of the trip the gear item belongs to."},
                    "label": {"type": "string", "description": "The gear item's name, e.g. 'Tent' or 'First aid kit'."},
                },
                "required": ["trip_name", "label"],
            },
            handler=self._action_toggle_gear_packed,
            trigger_phrases=("mark packed", "mark as packed", "i packed", "packed my", "gear is packed", "mark unpacked", "not packed yet"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_trip_summary",
            domain="expeditions",
            description="Get a Trip's logged distance, average speed, and planned route distance in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the trip."},
                },
                "required": ["name"],
            },
            handler=self._action_get_trip_summary,
            trigger_phrases=("how far did i", "trip distance", "trip summary", "how fast was i", "average speed", "how long is my planned route", "planned route distance"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_device_profile",
            domain="system",
            description=(
                "Tell the user which MIA EDITION (hardware/software variant) this "
                "device is running: Core (Pi 5 + AI HAT+ 2 field edition) or Home "
                "(desktop workstation edition). This is about the device/installation "
                "itself, NOT about user accounts — use list_profiles for the people "
                "set up on this device."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_device_profile,
            trigger_phrases=("what device profile", "am i on core or home", "which edition", "device profile"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="set_theme",
            domain="system",
            description="Change MIA's visual theme.",
            parameters={
                "type": "object",
                "properties": {
                    "theme_id": {
                        "type": "string",
                        "description": "One of: dark_field, low_energy, colored, anime_monochrome.",
                    },
                },
                "required": ["theme_id"],
            },
            handler=self._action_set_theme,
            trigger_phrases=(
                "change the theme", "set the theme", "switch the theme", "use a different theme",
                "low energy theme", "anime theme", "colored theme", "dark field theme",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="set_birthday",
            domain="system",
            description=(
                "Remember the current user's own birthday, so MIA can recognize and celebrate it. "
                "Use this whenever the user tells you their birthday in conversation — do not ask for "
                "it unprompted."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "birthday": {
                        "type": "string",
                        "description": "The user's birthday as YYYY-MM-DD. Use a plausible recent year if only month/day were given.",
                    },
                },
                "required": ["birthday"],
            },
            handler=self._action_set_birthday,
            trigger_phrases=("my birthday is", "my birthday's", "remember my birthday"),
        ))
        self.context.assistant_actions.register_domain_keywords(
            "calendar", ("next monday", "next tuesday", "next wednesday", "next thursday", "next friday",
                         "next saturday", "next sunday", "next week", "on monday", "on tuesday", "on wednesday",
                         "on thursday", "on friday", "on saturday", "on sunday"))
        self.context.assistant_actions.register(AssistantAction(
            name="add_calendar_event",
            domain="calendar",
            description="Add a new event to MIA's Calendar, optionally repeating yearly/monthly/weekly.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "A short title for the event."},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                    "time": {"type": "string", "description": "Optional time in 24-hour HH:MM format. Leave empty for an all-day event."},
                    "notes": {"type": "string", "description": "Optional notes."},
                    "recurrence": {
                        "type": "string",
                        "description": (
                            "Optional: 'yearly', 'monthly', 'weekly' or 'daily' for a repeating event (e.g. a "
                            "birthday or anniversary, a reminder every morning). Leave empty for a one-time event."
                        ),
                    },
                },
                "required": ["title", "date"],
            },
            handler=self._action_add_calendar_event,
            trigger_phrases=("add an event", "add a calendar event", "schedule an event", "new calendar event"),
            # a day named brings the calendar too, so "remind me to ... next Saturday" can go on it (live check
            # through the whole turn, 2026-11-24: it became a task repeating every 7 days)
            subjects=("calendar", "event"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_calendar_events",
            domain="calendar",
            description=(
                "List the user's upcoming/scheduled Calendar events in MIA — what's coming up "
                "today, this week, or on any date. Not for past activity — see recall_recent_activity for that."
            ),
            parameters={"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                        "required": []},
            handler=self._action_list_calendar_events, prompt_arg="question",
            trigger_phrases=(
                "list my events", "list my calendar", "what's on my calendar", "upcoming events", "show my calendar",
                # 2026-07-18: real gaps found live-probing beyond the
                # official golden set — "do i have anything today" was
                # ONLY catching inventory's broad "do i have" trigger,
                # never calendar's own domain at all; "going on this
                # week" matched nothing. Both now covered here.
                "anything on my calendar", "anything today", "going on this week", "going on today",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_calendar_event",
            domain="calendar",
            destructive=True,
            description="Delete an existing Calendar event in MIA by its title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the event to delete."},
                },
                "required": ["title"],
            },
            handler=self._action_delete_calendar_event,
            # Bare "event " (trailing space, avoids matching inside "eventful")
            # needed alongside the combo phrases for the same name-between-
            # verb-and-noun reason as "alarm "/"component " below.
            trigger_phrases=("delete an event", "delete the event", "remove an event", "cancel the event", "event "),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_power_status",
            domain="power",
            description="Get this device's current battery/power status.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_power_status,
            trigger_phrases=(
                "battery level", "battery status", "power status", "how much battery", "how's my battery",
                # 2026-07-18: real gap — "am I plugged in" matched nothing at all.
                "plugged in", "am i charging",
                # 2026-07-18: real gap — "What is my power percentage"
                # matched nothing at all (STT correctly transcribed it,
                # but no trigger phrase used the word "power" alone with
                # "percentage"/"level"), so it fell through to the
                # grounded info-question path instead of calling this
                # tool, and got a hedging "I don't know" reply that only
                # awkwardly related power to battery in prose.
                "power percentage", "power level", "percent power", "how much power",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_component",
            domain="components",
            description="Add a new electronic component to MIA's Workshop & Electronics component database.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The component's name, e.g. 'M3 bolts' or '10k resistor'."},
                    "category": {"type": "string", "description": "Optional category, e.g. 'Resistor', 'Capacitor', 'IC'."},
                    "value": {"type": "string", "description": "Optional value, e.g. '10k', '100nF'."},
                    "package": {"type": "string", "description": "Optional package, e.g. 'THT', '0805'."},
                    "quantity": {"type": "integer", "description": "Quantity on hand, default 0."},
                    "location": {"type": "string", "description": "Optional storage location."},
                },
                "required": ["name"],
            },
            handler=self._action_add_component,
            trigger_phrases=("add a component", "new component", "add a part", "add to my parts"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_components",
            domain="components",
            description="List or search the user's electronic components in MIA",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all components."},
                },
                "required": [],
            },
            handler=self._action_list_components,
            trigger_phrases=(
                "list my components", "list components", "what components", "show my components", "search components",
                # 2026-07-18: real gap — "what parts do I have" only
                # matched inventory's broad "do i have" trigger, never
                # reached the components domain at all.
                "what parts", "my parts",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_component",
            domain="components",
            destructive=True,
            description="Delete an existing electronic component in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the component to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_component,
            trigger_phrases=("delete a component", "remove a component", "component "),
        ))
        # 2026-07-18: Workshop's Materials/Jobs/Products/Ledger production
        # pipeline (built earlier this session) had zero Assistant
        # actions until now — a real gap found via a module-coverage
        # audit, not guessed. Four small domains (not one big "workshop"
        # domain) so a materials-only question doesn't also attach
        # ledger/job tools it doesn't need — same per-topic scoping this
        # registry already uses everywhere else.
        self.context.assistant_actions.register(AssistantAction(
            name="add_material",
            domain="materials",
            description="Add a raw Material to MIA's Workshop production pipeline (Materials tab).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The material's name, e.g. 'Plywood' or 'PLA Filament'."},
                    "unit": {"type": "string", "description": "Optional unit, e.g. 'sheet', 'kg', 'spool'."},
                    "quantity_on_hand": {"type": "number", "description": "Optional starting quantity on hand."},
                },
                "required": ["name"],
            },
            handler=self._action_add_material,
            trigger_phrases=("add a material", "new material", "add material"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_materials",
            domain="materials",
            description=("List the user's raw Materials in MIA's Workshop (lumber, hardware, supplies for builds), "
                         "with how many are on hand. Use this for 'what materials do I have'."),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all materials."},
                },
                "required": [],
            },
            handler=self._action_list_materials,
            trigger_phrases=("list my materials", "list materials", "what materials", "show my materials"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_product",
            domain="products",
            description="Add a finished Product to MIA's Workshop production pipeline (Products tab).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The product's name."},
                    "quantity_in_stock": {"type": "number", "description": "Optional starting quantity in stock."},
                    "base_price": {"type": "number", "description": "Optional default selling price."},
                },
                "required": ["name"],
            },
            handler=self._action_add_product,
            trigger_phrases=("add a product", "new product", "add product"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_products",
            domain="products",
            description=("List the user's finished Products in MIA's Workshop (things they make and sell), with "
                         "stock. Use this for 'what products do I have'."),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all products."},
                },
                "required": [],
            },
            handler=self._action_list_products,
            trigger_phrases=("list my products", "list products", "what products", "show my products"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_job",
            domain="jobs",
            description="Start a new production Job in MIA's Workshop pipeline.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The job's name."},
                    "description": {"type": "string", "description": "Optional description of the job."},
                },
                "required": ["name"],
            },
            handler=self._action_add_job,
            # Deliberately no bare "new job" — found via live testing that
            # it falsely gates open on "I love my new job at the bakery"
            # and, worse, the model then hallucinated an unrelated
            # set_birthday call once the (wrongly) attached jobs-domain
            # tools were in front of it. "start a new job" (matching the
            # same "Start a new X called Y" phrasing add_mission/
            # add_project/add_expedition already use) is specific enough
            # to avoid that collision.
            trigger_phrases=("start a job", "start a new job", "add a job", "create a job"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_jobs",
            domain="jobs",
            description="List the user's production Jobs in MIA's Workshop pipeline.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_jobs,
            trigger_phrases=("list my jobs", "list jobs", "what jobs", "show my jobs"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="consume_material",
            domain="jobs",
            description=(
                "Record that an existing Job consumed some quantity of an existing Material — deducts "
                "that quantity from the Material's own stock automatically."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "The name of the existing Job."},
                    "material_name": {"type": "string", "description": "The name of the existing Material consumed."},
                    "quantity": {"type": "number", "description": "How much of the material was used."},
                },
                "required": ["job_name", "material_name", "quantity"],
            },
            handler=self._action_consume_material,
            # "job used" not "my job used" — real phrasing puts the job's
            # own name between "my" and "job used" ("My Birdhouse Batch
            # job used..."), which the stricter phrase missed entirely.
            trigger_phrases=("used material", "consumed material", "consume material", "job used"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="produce_product",
            domain="jobs",
            description=(
                "Record that an existing Job produced some quantity of an existing Product — credits "
                "that quantity onto the Product's own stock automatically."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "The name of the existing Job."},
                    "product_name": {"type": "string", "description": "The name of the existing Product produced."},
                    "quantity": {"type": "number", "description": "How much of the product was produced."},
                },
                "required": ["job_name", "product_name", "quantity"],
            },
            handler=self._action_produce_product,
            # "job produced" not "my job produced" — same reasoning as
            # consume_material's "job used" fix just above.
            trigger_phrases=("job produced", "job finished producing", "produced product", "produce product"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="record_sale",
            domain="ledger",
            description=(
                "Record a sale of an existing Product in MIA's Workshop Ledger — deducts the sold "
                "quantity from the Product's stock and logs the revenue."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "The name of the existing Product sold."},
                    "quantity": {"type": "number", "description": "How many units were sold."},
                    "amount": {"type": "number", "description": "The total sale amount in dollars."},
                },
                "required": ["product_name", "quantity", "amount"],
            },
            handler=self._action_record_sale,
            trigger_phrases=("record a sale", "log a sale", "sold a product", "i sold", "record sale"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_ledger_summary",
            domain="ledger",
            description="Get the user's total revenue, expenses, and net profit from MIA's Workshop Ledger.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_ledger_summary,
            trigger_phrases=("ledger summary", "how much profit", "my revenue", "my expenses", "net profit"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_connected_devices",
            domain="field_kit",
            description="List currently connected external USB storage and serial devices in MIA's Field Kit.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_connected_devices,
            trigger_phrases=("connected devices", "what devices are connected", "list devices", "usb devices", "list connected devices"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_scripts",
            domain="field_kit",
            description="List the user's saved scripts in MIA's Field Kit script library.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search text. Leave empty for all scripts."},
                },
                "required": [],
            },
            handler=self._action_list_scripts,
            trigger_phrases=("list my scripts", "list scripts", "what scripts", "show my scripts"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_profiles",
            domain="system",
            description=(
                "List the user ACCOUNTS/PEOPLE set up on this MIA device (e.g. "
                "'Zac', 'Guest'). This is about user accounts, NOT the device's "
                "Core/Home edition setting — use get_device_profile for that."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_profiles,
            trigger_phrases=("list my profiles", "list profiles", "what profiles", "show my profiles", "who's set up"),
        ))
        # Deliberately NOT registering a "switch_profile" action:
        # gui/profile_select.py requires verify_password() to succeed
        # BEFORE set_active_profile() for any password-protected
        # profile — an Assistant action calling set_active_profile()
        # directly would bypass that check entirely (a real security
        # hole), and the alternative (accepting a password argument from
        # the LLM) would mean a spoken/typed password sits in plaintext
        # chat history, which is worse than a masked password field, not
        # just a different capability class. Same "exclude, don't
        # silently omit" treatment as run_script above.
        self.context.assistant_actions.register(AssistantAction(
            name="identify_hash",
            domain="security",
            description="Identify the likely algorithm(s) for a hash string (e.g. bcrypt, MD5, SHA-256) by its format.",
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": "The hash string to identify."},
                },
                "required": ["value"],
            },
            handler=self._action_identify_hash,
            trigger_phrases=("identify this hash", "what hash is this", "identify hash", "hash format", "what kind of hash"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="check_password_strength",
            domain="security",
            description=(
                "Estimate a password's strength (entropy-based rating and warnings). "
                "For a real account password, prefer MIA's Field Kit Security tab "
                "(a masked input field) over pasting it into chat — chat history isn't "
                "masked/hidden the way a password field is."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "password": {"type": "string", "description": "The password text to assess."},
                },
                "required": ["password"],
            },
            handler=self._action_check_password_strength,
            trigger_phrases=("check my password", "password strength", "how strong is this password", "rate this password", "check password strength"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="calculate_subnet",
            domain="security",
            description="Calculate subnet/CIDR details (network address, broadcast, netmask, usable host range) for an IPv4 or IPv6 CIDR.",
            parameters={
                "type": "object",
                "properties": {
                    "cidr": {"type": "string", "description": "CIDR notation, e.g. '192.168.1.0/24'."},
                },
                "required": ["cidr"],
            },
            handler=self._action_calculate_subnet,
            trigger_phrases=("calculate this subnet", "subnet calculator", "calculate subnet", "cidr calculator", "what's my subnet"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="scan_ports",
            domain="security",
            description=(
                "Quickly check whether 3 common ports (22 SSH, 80 HTTP, 443 HTTPS) are "
                "open on a host. This is a fast, limited check — for a fuller scan of "
                "more ports, use MIA's Field Kit Security tab instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Host or IP to scan, e.g. '192.168.1.1'."},
                },
                "required": ["host"],
            },
            handler=self._action_scan_ports,
            # "for open ports" added after domain-scoped attachment
            # (core/assistant_actions.py) surfaced a real, latent gap:
            # "Scan 192.168.1.1 for open ports"/"Scan 10.0.0.1 for open
            # ports" — this tool's OWN golden-set cases — never actually
            # matched any prior trigger phrase here. That only "worked"
            # before because every prompt gating open at all (here, via
            # open_module's bare "open " substring) attached the full
            # 47-tool registry, so the model could still see and pick
            # scan_ports despite its own trigger never firing. Scoped
            # attachment means a domain that never matches is never
            # offered, so this latent gap needed fixing, not masking.
            trigger_phrases=(
                "scan this host", "scan for open ports", "port scan",
                "what ports are open", "scan ports", "for open ports",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_project",
            domain="projects",
            description="Start a new Project (a container for tasks) in MIA's Project Manager tool.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name for the project."},
                    "status": {
                        "type": "string",
                        "description": "Optional status: Planning, Active, On Hold, or Complete. Defaults to Planning.",
                    },
                    "due_date": {"type": "string", "description": "Optional due date, YYYY-MM-DD."},
                },
                "required": ["name"],
            },
            handler=self._action_add_project,
            trigger_phrases=("add a project", "new project", "start a project", "create a project"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_projects",
            domain="projects",
            description="List the user's Projects in MIA's Project Manager tool.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_projects,
            trigger_phrases=(
                "list my projects", "list projects", "what projects", "show my projects",
                # 2026-07-18: real gap — "what am I currently working
                # on" matched nothing at all (no tool call).
                "what am i working on", "currently working on",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_task",
            domain="projects",
            description="Add a new Task under an existing Project in MIA's Project Manager tool.",
            parameters={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "The name of the Project this task belongs to (must already exist).",
                    },
                    "title": {"type": "string", "description": "A short title for the task."},
                    "due_date": {"type": "string", "description": "Optional due date, YYYY-MM-DD."},
                },
                "required": ["project_name", "title"],
            },
            handler=self._action_add_task,
            trigger_phrases=("add a task", "new task", "add to my tasks", "create a task"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_tasks",
            domain="projects",
            description=("List the user's Tasks in MIA (what they have to do, what they're working on), optionally "
                         "filtered to one Project by name."),
            parameters={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Optional Project name to filter by. Leave empty for all tasks.",
                    },
                },
                "required": [],
            },
            handler=self._action_list_tasks,
            trigger_phrases=(
                "list my tasks", "list tasks", "what tasks", "show my tasks",
                # 2026-07-18: real gap — "what do I need to do" matched
                # nothing at all (no tool call).
                "what do i need to do", "what do i have to do",
            ),
            subjects=("need to do", "have to do", "to-do", "todo"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_project",
            domain="projects",
            destructive=True,
            description="Delete an existing Project (and unlink, but not delete, its Tasks) in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the project to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_project,
            trigger_phrases=("delete a project", "delete my project", "remove a project", "delete the project"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_task",
            domain="projects",
            destructive=True,
            description="Delete an existing Task in MIA by title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the task to delete."},
                },
                "required": ["title"],
            },
            handler=self._action_delete_task,
            trigger_phrases=("delete a task", "delete my task", "remove a task", "delete the task"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="mark_task_done",
            domain="projects",
            description="Mark an existing Task as done (complete) or not done in MIA by title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the task to update."},
                    "done": {
                        "type": "boolean",
                        "description": "True to mark it done/complete, false to mark it not done. Defaults to true.",
                    },
                },
                "required": ["title"],
            },
            handler=self._action_mark_task_done,
            trigger_phrases=("mark task", "mark my task", "mark the task", "complete my task", "finish my task", "task done", "task complete"),
        ))
        self.context.assistant_actions.register(AssistantAction(
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
                    "trip_name": {
                        "type": "string",
                        "description": "Optional name of an existing Trip to link this mission to (must already exist).",
                    },
                },
                "required": ["name"],
            },
            handler=self._action_add_mission,
            trigger_phrases=("start a mission", "new mission", "create a mission", "add a mission"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_missions",
            domain="missions",
            description="List the user's Missions in MIA, including each objective's progress.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_missions,
            trigger_phrases=(
                "list my missions", "list missions", "what missions", "show my missions",
                # 2026-07-18: real gap found live — "what is my current
                # mission" matched none of the phrases above, so the
                # missions domain never got attached and the model just
                # said "I don't know, check the Missions module." This
                # is the same list_missions handler (it already returns
                # every mission with its status, current ones included)
                # — the gap was purely in trigger-phrase coverage, not
                # the handler itself.
                "current mission", "my current mission", "my mission", "active mission", "what mission",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
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
            handler=self._action_add_objective,
            trigger_phrases=("add an objective", "new objective", "add a goal", "create an objective"),
        ))
        self.context.assistant_actions.register(AssistantAction(
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
            handler=self._action_log_mission_progress,
            trigger_phrases=("log a catch", "log progress", "count that", "add to my tally", "update my mission progress", "mark progress on my mission"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_mission",
            domain="missions",
            destructive=True,
            description="Delete an existing Mission in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the mission to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_mission,
            trigger_phrases=("delete a mission", "delete my mission", "remove a mission", "delete the mission"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="complete_mission",
            domain="missions",
            description="Mark an existing Mission as completed in MIA by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the mission to mark complete."},
                },
                "required": ["name"],
            },
            handler=self._action_complete_mission,
            trigger_phrases=("complete my mission", "mark my mission complete", "finish my mission", "complete the mission", "mark the mission complete"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_trail_maps",
            domain="maps",
            description="List the trail map PDFs cataloged in MIA's Maps module, optionally filtered by park name or state.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to filter by park name or state."},
                },
                "required": [],
            },
            handler=self._action_list_trail_maps,
            trigger_phrases=(
                "trail map", "trail maps", "park map", "park maps", "list my trail maps",
                "what maps do i have", "maps do i have", "maps have i",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_trail_map_from_url",
            domain="maps",
            description=(
                "Download a trail map PDF from a direct URL and add it to MIA's trail map "
                "catalog. Not for offline tile/basemap downloads — those are only available "
                "from the Maps module's own UI, since they can take too long to run as part "
                "of a chat reply."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "park_name": {"type": "string", "description": "The name of the park."},
                    "state": {"type": "string", "description": "The U.S. state the park is in."},
                    "url": {"type": "string", "description": "Direct URL to the trail map PDF."},
                    "notes": {"type": "string", "description": "Optional notes about this trail map."},
                },
                "required": ["park_name", "state", "url"],
            },
            handler=self._action_add_trail_map_from_url,
            trigger_phrases=("add a trail map", "add trail map", "download a trail map", "download this trail map", "catalog this trail map"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_trail_map",
            domain="maps",
            destructive=True,
            description="Delete a cataloged trail map PDF from MIA's Maps module by park name.",
            parameters={
                "type": "object",
                "properties": {
                    "park_name": {"type": "string", "description": "The name of the park whose trail map should be deleted."},
                },
                "required": ["park_name"],
            },
            handler=self._action_delete_trail_map,
            trigger_phrases=("delete a trail map", "delete trail map", "remove a trail map", "remove trail map"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="convert_units",
            domain="toolbox",
            description=(
                "Convert a numeric value between two units of measurement using MIA's "
                "Unit Converter (length, area, volume, weight, temperature, speed, pressure, "
                "energy, power, time, data storage, angle, or fuel economy). Unit names can "
                "be everyday words (e.g. 'miles', 'celsius') — no need for exact formatting."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "The numeric value to convert."},
                    "from_unit": {"type": "string", "description": "The unit to convert from, e.g. 'miles'."},
                    "to_unit": {"type": "string", "description": "The unit to convert to, e.g. 'kilometers'."},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
            handler=self._action_convert_units,
            # 2026-07-18: a bare "convert" trigger gated the domain open
            # for "I'm trying to convert my garage into a workshop" and
            # the model then actually hallucinated a convert_units call
            # for it — same class of cross-domain confabulation as
            # add_job's old bare "new job" trigger. Replaced with
            # specific "to <unit>"/"how many <unit>" compounds, which
            # still cover real conversion phrasing without the bare-verb
            # false-positive risk.
            trigger_phrases=(
                "convert units", "unit conversion",
                "to miles", "to kilometers", "to feet", "to meters", "to yards", "to inches",
                "to pounds", "to kilograms", "to ounces", "to grams",
                "to celsius", "to fahrenheit", "to liters", "to gallons",
                "how many miles", "how many kilometers", "how many feet", "how many meters",
                "how many pounds", "how many kilograms",
                "in fahrenheit", "in celsius",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="calculate_ohms_law",
            domain="toolbox",
            description=(
                "Solve Ohm's Law (V = I x R) for voltage, current, or resistance, given the "
                "other two values, using MIA's Ohm's Law calculator."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "solve_for": {"type": "string", "description": "Which value to solve for: 'voltage', 'current', or 'resistance'."},
                    "voltage": {"type": "number", "description": "Voltage in volts, if known."},
                    "current": {"type": "number", "description": "Current in amps, if known."},
                    "resistance": {"type": "number", "description": "Resistance in ohms, if known."},
                },
                "required": ["solve_for"],
            },
            handler=self._action_calculate_ohms_law,
            # 2026-07-18: real gap — "I have 2 amps through a 10 ohm
            # resistor, what's the voltage?" (a natural way to actually
            # ask this) matched none of the original triggers, which all
            # assumed the user would say "Ohm's law" or "solve for X"
            # explicitly. Added specific electronics vocabulary instead
            # of a bare "current" (too ambiguous — collides with "current
            # events"/"current job") or bare "voltage"/"resistance".
            trigger_phrases=(
                "ohm's law", "ohms law", "solve for voltage", "solve for current", "solve for resistance",
                "amps through", "ohm resistor", "volts across",
                "how many volts", "how many ohms", "how many amps",
                "what's the voltage", "what is the voltage",
            ),
        ))
        # --- Maintenance (vehicles, power equipment, appliances,
        # property, tools) — 2026-09-07, closing the gap found in a
        # full-registry audit: 76 actions existed across 19 domains and
        # Maintenance (built the same session, a substantial new
        # feature — assets, 6 trigger types, documents, meter/sensor
        # logging) had zero. Real collision risk against two existing
        # domains, deliberately not avoided by picking evasive trigger
        # phrases but resolved the same way this registry always has —
        # distinct tool descriptions + live-model verification
        # (tests/live_model_check.py): "projects" already owns generic
        # "add/list/delete a task" phrasing (core.task_manager.Task,
        # under a Project) — a maintenance task is a DIFFERENT concept
        # (recurring upkeep tied to an asset), so both domains
        # legitimately attach together on ambiguous phrasing and the
        # model disambiguates via description, same pattern as the
        # existing add_note/add_trip_log_entry collision. "alarms"
        # already owns "remind me" — a real "remind me to change the
        # oil every 6 months" phrasing plausibly attaches both domains
        # too; verified live rather than assumed safe.
        #
        # add_maintenance_task is deliberately calendar-trigger-only —
        # asking the model to correctly extract a meter unit/interval/
        # threshold/direction from a sentence is a much riskier parse
        # than this registry's established 1-2-field extractions, and
        # every existing action here favors that same "one clean field
        # or two" shape (add_alarm: label+time; add_task: project+title).
        # Runtime/Mileage/Cycles/Condition/Sensor tasks still need the
        # Maintenance module's own dialog, where the interval/threshold/
        # direction fields are all visible together — stated plainly in
        # this tool's own description, not silently unsupported.
        self.context.assistant_actions.register(AssistantAction(
            name="add_maintenance_asset",
            domain="maintenance",
            description=(
                "Add a new vehicle, power equipment, appliance, property item, tool, or garden/greenhouse "
                "plant or bed (category Garden/Plant) to MIA's Maintenance tracker (not Inventory, and not "
                "Workshop's electronics parts)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. '2019 Ford F-150', 'Lawn Mower'."},
                    "category": {
                        "type": "string",
                        "description": f"One of: {', '.join(MAINTENANCE_ASSET_CATEGORIES)}. Defaults to 'Other' if unclear.",
                    },
                },
                "required": ["name"],
            },
            handler=self._action_add_maintenance_asset,
            trigger_phrases=(
                "track my", "start tracking", "add a vehicle", "add an asset to maintenance", "add to maintenance",
                "to the greenhouse", "to the garden",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_maintenance_assets",
            domain="maintenance",
            description="List every vehicle, power equipment, appliance, property item, tool and garden/greenhouse plant tracked in MIA's Maintenance tracker.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_maintenance_assets,
            trigger_phrases=(
                "what vehicles", "list my vehicles", "list my equipment", "what am i tracking",
                "list maintenance assets", "show my assets", "what's in my garage",
                "what plants", "list my plants", "my plants",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_maintenance_asset",
            domain="maintenance",
            destructive=True,
            description="Delete a vehicle/equipment/appliance/property/tool from MIA's Maintenance tracker by name (also deletes its tasks).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The exact name of the asset to delete."},
                },
                "required": ["name"],
            },
            handler=self._action_delete_maintenance_asset,
            trigger_phrases=("delete a vehicle", "remove a vehicle", "delete an asset", "stop tracking", "remove from maintenance"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_maintenance_task",
            domain="maintenance",
            description=(
                "Add a recurring or one-time CALENDAR-based maintenance task tied to an existing vehicle/"
                "equipment/appliance/property/tool asset in MIA (e.g. 'change the truck's oil every 90 "
                "days', 'renew tags every year', 'water the tomatoes every 2 days'). NOT a clock-time alarm — use this whenever the task "
                "repeats on a day interval for a specific owned asset, even if phrased as 'remind me to'. "
                "Only for day-interval recurrence — mileage/engine-hour/start-count/sensor-triggered tasks "
                "need the Maintenance module's own screen, not this tool. A one-time thing on a date "
                "('remind me to change the oil next Saturday') is add_calendar_event, never a task repeating every "
                "7 days. Only for SETTING UP a new task — "
                "if the user is reporting they already did something (past tense, e.g. 'I renewed the "
                "tags'), use complete_maintenance_task instead, not this."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "asset_name": {"type": "string", "description": "The existing asset this task is for, as the user referred to it (e.g. 'truck', 'tomatoes')."},
                    "title": {"type": "string", "description": "A short task title, e.g. 'Oil change', 'Renew tags', 'Water'."},
                    "interval_days": {
                        "type": "integer",
                        "description": "Repeat every N days. Omit for a one-time task.",
                    },
                    "date": {"type": "string",
                             "description": "The day, for a one-time thing he said a day for ('next Saturday')"},
                },
                "required": ["asset_name", "title"],
            },
            handler=self._action_add_maintenance_task,
            trigger_phrases=(
                "add a maintenance task", "schedule maintenance", "set up maintenance",
                "add an oil change", "maintenance task", "service reminder", "remind me to service",
                # Broadened from the too-narrow "remind me to change the
                # oil" — real phrasing inserts the asset's own name/
                # possessive between verb and noun ("remind me to
                # change my Truck's oil"), same class of gap as
                # delete_alarm's name-before-noun fix. A strict superset
                # of alarms' own bare "remind me" trigger, so this adds
                # no new false-positive surface beyond what that
                # already accepts.
                "remind me to change", "every months",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_maintenance_tasks",
            domain="maintenance",
            description=(
                "List MIA's maintenance tasks and their real due/overdue status, optionally filtered by a "
                "keyword matching the task title or asset name ('greenhouse' or 'garden' lists plant care). "
                "Leave query empty to list everything."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword to filter by task title or asset name."},
                },
                "required": [],
            },
            handler=self._action_list_maintenance_tasks,
            trigger_phrases=(
                "what maintenance is due", "what's due for maintenance", "list maintenance tasks",
                "what maintenance do i have", "is anything overdue", "maintenance status", "what needs maintenance",
                "what maintenance is overdue", "what's due on", "needs doing on", "service is due",
                "due for service", "due for an oil change",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="complete_maintenance_task",
            domain="maintenance",
            description=(
                "Mark an EXISTING maintenance task complete/done because the user is reporting they already "
                "did it (past tense — 'I changed the oil in the truck', 'sharpened the mower blades', 'I "
                "watered the tomatoes'). Use the user's own words for title and asset; MIA matches them to "
                "the real task. Do NOT use this to set up a new task — use add_maintenance_task instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "What was done, in the user's words, e.g. 'oil change', 'blades', 'water'."},
                    "asset_name": {"type": "string", "description": "The vehicle/tool/plant, in the user's words, e.g. 'truck', 'mower', 'tomatoes'."},
                    "meter_value": {
                        "type": "number",
                        "description": "For a mileage/runtime/cycles/condition task, the meter reading at completion. Omit to use the latest logged reading.",
                    },
                    "cost": {
                        "type": "number",
                        "description": "What it cost, if the user said (e.g. '$35 for the oil change'). Recorded as a maintenance expense for that item.",
                    },
                },
                "required": [],
            },
            handler=self._action_complete_maintenance_task,
            # No fixed phrase list can enumerate every task-specific way
            # to say "I did the thing" ("I renewed the tags", "I rotated
            # the tires", "I inspected the brakes", ...) — same real
            # limitation this registry already accepts for "note "
            # (core/application.py's delete_note trigger comment).
            # Covers the common maintenance completion verbs found via
            # live-model testing rather than guessing further ones.
            trigger_phrases=(
                "i changed the oil", "i finished the maintenance", "mark maintenance done",
                "completed the maintenance", "did the oil change", "serviced my", "maintenance complete",
                "finished servicing", "i renewed", "i replaced", "i repaired", "i rotated", "i inspected",
                "i fixed my", "just did the",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="log_maintenance_reading",
            domain="maintenance",
            description=(
                "Log a meter/sensor reading (mileage, engine hours, start count, a sensor value like battery "
                "voltage) for a tracked vehicle or tool, e.g. '120 hours on the mower', '46,000 miles on the "
                "truck'. Naming just the asset is enough; add a task title only if the user named one."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Optional task title, if the user named one."},
                    "asset_name": {"type": "string", "description": "The vehicle/tool, in the user's words, e.g. 'mower'."},
                    "value": {"type": "number", "description": "The current reading value, e.g. 46000 for miles."},
                    "unit": {"type": "string", "description": "Optional unit, e.g. 'miles', 'hours', 'V'."},
                },
                "required": ["value"],
            },
            handler=self._action_log_maintenance_reading,
            # Tried a bare "log " (trailing space) here to catch "Log
            # 46000 miles" (a real number always sits between "log" and
            # the unit, so no fixed compound can match it) — live-model
            # testing found it made an UNRELATED "I need to log off for
            # the night" gate open and hallucinate set_birthday. Reverted:
            # same accepted trade-off this registry already made for
            # "note " (too common a word to gate safely) — "log <value>
            # <unit>" with no other maintenance-specific wording is a
            # known, real gap, not silently assumed fixed.
            trigger_phrases=(
                "log the mileage", "log miles", "log a reading", "log the odometer",
                "update the mileage", "log engine hours", "log the voltage",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="delete_maintenance_task",
            domain="maintenance",
            destructive=True,
            description="Delete a maintenance task in MIA by title (optionally naming the asset to disambiguate).",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The task's title to delete."},
                    "asset_name": {"type": "string", "description": "Optional — the asset's name, needed only if more than one asset has a same-titled task."},
                },
                "required": ["title"],
            },
            handler=self._action_delete_maintenance_task,
            trigger_phrases=("delete a maintenance task", "remove a maintenance task", "delete the maintenance task"),
        ))
        # --- Lab (Data Logger) — 2026-09-08, same audit that found
        # Maintenance had zero Assistant actions also flagged Lab
        # (modules/lab/module.py, core/data_logger_manager.py): manual
        # sensor/experiment reading entry, zero actions. A series_id is
        # an arbitrary freeform string (no separate registry file — see
        # that manager's own docstring), so "log a reading" here means
        # something genuinely different from Maintenance's version
        # (a specific tracked task's meter, resolved by title/asset) —
        # both tools' descriptions say so explicitly, same
        # disambiguation approach as every other legitimate multi-domain
        # collision in this registry.
        self.context.assistant_actions.register(AssistantAction(
            name="log_lab_reading",
            domain="lab",
            description=(
                "Log a manual sensor/experiment/measurement reading in MIA's Lab (Data Logger) under a "
                "named series (e.g. 'soil moisture', 'multimeter voltage', 'greenhouse temp') — general "
                "experiment/sensor-testing data. NOT for a specific tracked Maintenance task's mileage/"
                "engine hours/sensor value — use log_maintenance_reading for that instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "series": {"type": "string", "description": "The series name, e.g. 'soil moisture'."},
                    "value": {"type": "number", "description": "The reading's numeric value."},
                    "unit": {"type": "string", "description": "Optional unit, e.g. '%', 'V', 'F'."},
                    "note": {"type": "string", "description": "Optional note about this reading."},
                },
                "required": ["series", "value"],
            },
            handler=self._action_log_lab_reading,
            trigger_phrases=(
                "log a reading", "log a measurement", "log a value", "record a reading", "add a reading",
                "log this reading",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_lab_series",
            domain="lab",
            description="List every Data Logger series name in MIA's Lab module that has at least one logged reading.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_lab_series,
            # "data series" often has words inserted before "am i
            # logging" ("What data series am I logging in the Lab?") —
            # same name/noun-insertion gap as several other bare
            # triggers in this registry. Added narrower but still
            # distinctive compounds rather than a fully generic bare
            # "series" (too easy to collide with an unrelated "TV
            # series"/"a series of events").
            trigger_phrases=(
                "what series do i have", "list my data series", "what am i logging", "list lab series",
                "show my series", "what series", "data series", "my series",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_lab_readings",
            domain="lab",
            description=("Show the readings already logged for one Data Logger series in MIA's Lab ('show me the "
                         "readings for soil moisture'), oldest first. To add a new reading, use log_lab_reading."),
            parameters={
                "type": "object",
                "properties": {
                    "series": {"type": "string", "description": "The series name to list readings for."},
                },
                "required": ["series"],
            },
            handler=self._action_list_lab_readings,
            trigger_phrases=("show me the readings for", "what are my readings for", "readings for", "history for", "show my data for"),
        ))
        # --- Budget (household bills, income, expenses) — 2026-09-08,
        # the second item from the same planning session that added
        # Property. Real collision risk, deliberately not evaded:
        # add_bill vs. add_maintenance_task (both "recurring thing due
        # on a schedule") — resolved via distinct descriptions, same
        # pattern already proven for the alarm/maintenance-task
        # collision, verified live rather than assumed safe.
        self.context.assistant_actions.register(AssistantAction(
            name="add_bill",
            domain="budget",
            description=(
                "Add a recurring or one-time household BILL (e.g. electric, mortgage, insurance) to MIA's "
                "Budget tracker — a dollar amount due on a schedule. NOT a Maintenance task (an asset's "
                "physical upkeep) — use add_maintenance_task for that instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. 'Electric', 'Mortgage'."},
                    "amount": {"type": "number", "description": "The bill amount in dollars."},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format."},
                    "category": {
                        "type": "string",
                        "description": f"One of: {', '.join(BUDGET_EXPENSE_CATEGORIES)}. Defaults to 'Utilities'.",
                    },
                    "recurrence": {
                        "type": "string",
                        "description": "Optional: 'yearly', 'monthly', or 'weekly' for a repeating bill. Leave empty for a one-time bill.",
                    },
                },
                "required": ["name", "amount", "due_date"],
            },
            handler=self._action_add_bill,
            # A bill's own descriptor word ("monthly", "electric") sits
            # between "add a"/"a" and "bill" in real phrasing ("Add a
            # monthly electric bill for $120") — same name-before-noun
            # gap as delete_alarm's "alarm " fix. Covers common bill-
            # type nouns directly rather than a fully bare "bill "
            # (too collision-prone — "foot the bill", "dollar bill").
            trigger_phrases=(
                "add a bill", "new bill", "track a bill", "add a household bill",
                "add my electric bill", "add my mortgage", "electric bill", "gas bill",
                "water bill", "utility bill", "internet bill", "add a bill for",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_bills",
            domain="budget",
            description="List MIA's household bills and their real due/overdue status, most urgent first.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_bills,
            trigger_phrases=(
                "list my bills", "what bills do i have", "what's due", "is anything overdue",
                "what bills are due", "show my bills",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="mark_bill_paid",
            domain="budget",
            description="Mark a household bill paid in MIA by name — records a real expense and advances a recurring bill's next due date.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The bill's name, e.g. 'Electric'."},
                    "amount": {"type": "number", "description": "Optional — the actual amount paid, if different from the bill's usual amount."},
                },
                "required": ["name"],
            },
            handler=self._action_mark_bill_paid,
            trigger_phrases=("i paid my", "paid the bill", "mark my bill paid", "mark the bill paid", "i paid the"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_income",
            domain="budget",
            description=(
                "When the user states a specific new dollar amount of income received (e.g. 'I got paid $3000', "
                "'record $1500 of rental income') and no specific property/address is mentioned, record general "
                "household income in MIA — salary, investment income, or rental income. A Workshop business sale "
                "uses record_sale instead. When a tracked recurring income source (e.g. 'my paycheck') arrives "
                "WITHOUT the user restating a dollar amount, use mark_income_received instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The income amount in dollars."},
                    "category": {"type": "string", "description": "One of: Salary, Rental Income, Investment, Other. Defaults to 'Other'."},
                    "description": {"type": "string", "description": "Optional description."},
                    "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format. Defaults to today."},
                },
                "required": ["amount"],
            },
            handler=self._action_add_income,
            # A dollar amount sits between "record"/"of" and "income" in
            # real phrasing ("Record $1500 of rental income") — same
            # name-before-noun gap as add_bill's fix above.
            trigger_phrases=(
                "record income", "add income", "i got paid", "received rent", "got my paycheck",
                "log my paycheck", "record my rental income", "rental income", "of income", "income of",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="add_expense",
            domain="budget",
            description="Record a household expense entry in MIA (groceries, car repair, etc.) — NOT a bill (a recurring scheduled obligation, use add_bill) and NOT a Workshop job cost.",
            parameters={
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The expense amount in dollars."},
                    "category": {"type": "string", "description": "One of: Utilities, Mortgage/Rent, Insurance, Groceries, Animals & Feed, Maintenance, Transportation, Taxes, Other. Defaults to 'Other'."},
                    "description": {"type": "string", "description": "Optional description."},
                    "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format. Defaults to today."},
                },
                "required": ["amount"],
            },
            handler=self._action_add_expense,
            trigger_phrases=("record an expense", "add an expense", "log an expense", "i spent", "bought groceries",
                             "spent $", "i bought"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_budget_summary",
            domain="budget",
            description=(
                "When the user wants specific TOTALS or NUMBERS — how much income, how much spent, net cash flow, "
                "or tax-relevant subtotals — for a date range (e.g. this month, this year, or all time), get that "
                "here. For a general status question like 'how are we doing' or 'are we on budget' rather than a "
                "request for specific totals, use get_financial_checkin instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Optional start date, YYYY-MM-DD. Leave empty for no lower bound."},
                    "end_date": {"type": "string", "description": "Optional end date, YYYY-MM-DD. Leave empty for no upper bound."},
                },
                "required": [],
            },
            handler=self._action_get_budget_summary,
            trigger_phrases=(
                "budget summary", "how much have i spent", "how much did i make", "net cash flow",
                "my cash flow", "how much income", "tax summary", "how's my budget", "how is my budget",
                "budget looking", "my budget look",
            ),
        ))
        # --- Proactive nudges follow-up (2026-09-08): expected/recurring
        # income (IncomeSource) is a distinct concept from a one-off
        # add_income entry, so it needs its own action rather than
        # overloading add_income. Real collision risk with both add_income
        # (both take "amount") and add_bill (both take "amount" + a
        # schedule) — resolved by leading each description with the
        # condition that picks it ("a RECURRING/EXPECTED source" vs. "a
        # one-off actual" vs. "an obligation you OWE"), same positive/
        # condition-first phrasing this session's lesson established
        # (a negated description caused a real regression on add_income
        # vs. record_sale earlier this session — never repeat that).
        # list_income_sources/set_budget_target deliberately stay GUI-only
        # this pass, same stated scope limit as Real Estate's first slice.
        self.context.assistant_actions.register(AssistantAction(
            name="add_income_source",
            domain="budget",
            description=(
                "Add a RECURRING or EXPECTED income source to MIA — a paycheck, rental income, or other income "
                "that arrives on a schedule (a future expectation, not money already received). For income "
                "already received right now, use add_income instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. 'Paycheck', 'Rental — 123 Main St'."},
                    "expected_amount": {"type": "number", "description": "The expected amount in dollars."},
                    "next_date": {"type": "string", "description": "The next expected date in YYYY-MM-DD format."},
                    "category": {
                        "type": "string",
                        "description": f"One of: {', '.join(BUDGET_INCOME_CATEGORIES)}. Defaults to 'Salary'.",
                    },
                    "recurrence": {
                        "type": "string",
                        "description": "Optional: 'yearly', 'monthly', 'biweekly', or 'weekly' for a repeating income source. Leave empty for a one-time expectation.",
                    },
                },
                "required": ["name", "expected_amount", "next_date"],
            },
            handler=self._action_add_income_source,
            trigger_phrases=(
                "add an income source", "new income source", "track my paycheck", "add my paycheck",
                "set up my paycheck", "expect income", "track expected income", "add a recurring income source",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="mark_income_received",
            domain="budget",
            description=(
                "When a tracked, recurring income source (a paycheck, rent, or similar already set up in MIA) has "
                "arrived and the user does NOT restate a new dollar amount (e.g. 'my paycheck came in', 'got my "
                "paycheck', 'received my rent'), mark it received here by name — records a real income entry using "
                "the source's known expected amount and advances its next expected date. If the user states a new "
                "specific dollar amount instead, use add_income."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The income source's name, e.g. 'Paycheck'."},
                    "amount": {"type": "number", "description": "Optional — the actual amount received, if different from the expected amount."},
                },
                "required": ["name"],
            },
            handler=self._action_mark_income_received,
            trigger_phrases=(
                "got paid", "my paycheck came in", "received my paycheck", "mark my paycheck received",
                "i got my paycheck", "received my income",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_financial_checkin",
            domain="budget",
            description=(
                "When the user asks a general STATUS question about their finances — 'how are we doing "
                "financially', 'are we on budget', 'are we ok with money' — rather than asking for specific "
                "totals, get MIA's proactive financial check-in here: overdue/upcoming bills, when the next "
                "paycheck is expected and for how much, and any budget categories running over plan this month. "
                "For a request for specific totals (income, expenses, net cash flow, tax subtotals), use "
                "get_budget_summary instead."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_financial_checkin,
            trigger_phrases=(
                "financial check-in", "how are we doing financially", "are we on budget", "financial checkin",
                "how's our budget", "money check-in", "how are we doing with money",
            ),
        ))
        # --- Real Estate (property portfolio) — 2026-09-08, same
        # planning session as Property/Budget. record_rental_income
        # deliberately shares "rental income" vocabulary with Budget's
        # own add_income (both legitimately attach; disambiguated by
        # description — a property-scoped entry vs. a plain household
        # one — same collision-resolution pattern proven all session).
        self.context.assistant_actions.register(AssistantAction(
            name="add_property",
            domain="real_estate",
            description="Add a new real estate property to MIA's portfolio (value, mortgage balance, purchase info).",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "A short name, e.g. '123 Main St', 'Lake Cabin'."},
                    "property_type": {"type": "string", "description": "One of: Primary Residence, Rental, Investment, Land, Other. Defaults to 'Rental'."},
                    "current_value": {"type": "number", "description": "Optional current estimated value in dollars."},
                    "mortgage_balance": {"type": "number", "description": "Optional current mortgage balance in dollars."},
                },
                "required": ["name"],
            },
            handler=self._action_add_property,
            trigger_phrases=("add a property", "new property", "add a rental property", "track a property", "add my house", "bought a house", "bought the house",
                             "bought land", "bought a property", "bought the property"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="list_properties",
            domain="real_estate",
            description="List every property in MIA's real estate portfolio with its equity (value minus mortgage).",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_list_properties,
            trigger_phrases=("list my properties", "what properties do i have", "show my properties", "my property portfolio"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="record_rental_income",
            domain="real_estate",
            # Known, accepted live-model limitation (llama3.2): "Record
            # rental income of $1800 for 123 Main St" — a named property
            # right in the sentence — still sometimes resolves to
            # add_income instead of this one. Tried three description
            # phrasings (negation-based, positive-only, condition-first,
            # this one) — the negation attempt actively regressed to
            # zero tool calls on unrelated cases, so it was reverted;
            # none of the three fully fixed this specific direction.
            # Non-destructive, low-impact when it happens (the income is
            # still recorded, just as a plain Budget entry instead of
            # linked to the property via property_id) — accepted rather
            # than chased further, same trade-off class as this
            # registry's "log " reversion.
            description=(
                "When a specific property/address (e.g. '123 Main St') is mentioned, record rental income "
                "for it in MIA's real estate portfolio by that property's name."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "property_name": {"type": "string", "description": "The exact name of the existing property."},
                    "amount": {"type": "number", "description": "The rental income amount in dollars."},
                    "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format. Defaults to today."},
                },
                "required": ["property_name", "amount"],
            },
            handler=self._action_record_rental_income,
            trigger_phrases=("record rental income for", "got rent for", "received rent for", "rent payment for"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_property_summary",
            domain="real_estate",
            description="Get net operating income, cap rate, and equity for one property in MIA's real estate portfolio, by name.",
            parameters={
                "type": "object",
                "properties": {
                    "property_name": {"type": "string", "description": "The exact name of the existing property."},
                },
                "required": ["property_name"],
            },
            handler=self._action_get_property_summary,
            # The property's own name sits between "my" and "property"
            # in real phrasing ("How is my 123 Main St property
            # doing?") — same name-before-noun gap as every other
            # trigger-phrase fix this session. "property doing" alone
            # (not the fuller "how is my property doing") survives that
            # insertion without resorting to a riskier bare "how is my".
            trigger_phrases=(
                "property summary", "how is my property doing", "cap rate for", "how much equity",
                "property doing",
            ),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="record_property_sale",
            domain="real_estate",
            description=("Record that a property in MIA's real estate portfolio was sold: its name, the sale price, and "
                         "optionally the selling costs and the date."),
            parameters={
                "type": "object",
                "properties": {
                    "property_name": {"type": "string", "description": "The exact name of the existing property."},
                    "sale_price": {"type": "number", "description": "What it sold for."},
                    "selling_costs": {"type": "number", "description": "Optional commissions and closing costs."},
                    "date": {"type": "string", "description": "Optional sale date, YYYY-MM-DD. Defaults to today."},
                },
                "required": ["property_name", "sale_price"],
            },
            handler=self._action_record_property_sale,
            trigger_phrases=("sold the property", "sold my rental", "we sold", "record the sale of", "property sold",
                             "i sold the house"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="play_track",
            domain="music",
            description="Play a specific song from MIA's local music library, by title or artist.",
            parameters={
                "type": "object",
                "properties": {
                    "track_name": {"type": "string", "description": "Title or artist to search for."},
                },
                "required": ["track_name"],
            },
            handler=self._action_play_track,
            trigger_phrases=("play ", "play the song", "queue up"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="play_playlist",
            domain="music",
            description="Play one of MIA's saved music playlists, by name.",
            parameters={
                "type": "object",
                "properties": {
                    "playlist_name": {"type": "string", "description": "The exact name of the existing playlist."},
                },
                "required": ["playlist_name"],
            },
            handler=self._action_play_playlist,
            trigger_phrases=("play my playlist", "play the playlist", "play my music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="pause_music",
            domain="music",
            description="Pause the currently playing music.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_pause_music,
            trigger_phrases=("pause the music", "pause music", "pause the song"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="resume_music",
            domain="music",
            description="Resume/unpause the currently paused music.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_resume_music,
            trigger_phrases=("resume the music", "unpause the music", "continue playing", "resume music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="stop_music",
            domain="music",
            # Deliberately never a bare "stop" — that already means
            # "stop tracking" under the maintenance domain.
            description="Stop music playback entirely (clears the play queue, unlike pause).",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_stop_music,
            trigger_phrases=("stop the music", "stop playing", "stop the song", "stop music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="next_track",
            domain="music",
            description="Skip to the next track in the current music queue.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_next_track,
            trigger_phrases=("next song", "next track", "skip this song", "skip track"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="previous_track",
            domain="music",
            description="Go back to the previous track in the current music queue.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_previous_track,
            trigger_phrases=("previous song", "previous track", "go back a song"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="set_music_volume",
            domain="music",
            description="Set the music player's own playback volume (separate from the device's system volume).",
            parameters={
                "type": "object",
                "properties": {
                    "percent": {"type": "integer", "description": "Volume percent, 0-100."},
                },
                "required": ["percent"],
            },
            handler=self._action_set_music_volume,
            trigger_phrases=("music volume", "turn up the music", "turn down the music"),
        ))
        self.context.assistant_actions.register(AssistantAction(
            name="get_now_playing",
            domain="music",
            description="Get the title/artist and playback position of whatever song is currently playing.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._action_get_now_playing,
            trigger_phrases=("what's playing", "now playing", "what song is this", "what song is playing"),
        ))

    @staticmethod
    def _action_open_module(context: AppContext, arguments: dict) -> str:
        """Assistant tool `open_module`: opens a module by id or name. It publishes assistant.open_module_requested instead of touching MainWindow, because the reply can arrive on any thread and Qt widgets belong to the GUI thread. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        requested = str(arguments.get("module_id", "")).strip()
        module = context.module_manager.resolve(requested) if context.module_manager is not None else None
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
        """Assistant tool `add_alarm`: sets an alarm at HH:MM with a label ("Alarm" when none). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_add_alarm(context, arguments)

    @staticmethod
    def _action_list_alarms(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_alarms`: every alarm with its time, marking disabled ones. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        alarms = context.alarms.all_alarms()
        if not alarms:
            return "You have no alarms set."
        lines = [f"- '{a.label}' at {a.time}" + ("" if a.enabled else " (disabled)") for a in alarms]
        return "Your alarms:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_alarm(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_alarm`: deletes the alarm whose label matches (case-insensitive). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_delete_alarm(context, arguments)

    @staticmethod
    def _action_add_note(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_note`: adds a journal note with a title and body. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_add_note(context, arguments)

    @staticmethod
    def _action_list_notes(context: AppContext, arguments: dict) -> str:
        """Returns raw entries (title + body) as plain text — same
        retrieve-then-let-the-LLM-answer shape as
        _action_recall_recent_activity, so the model can quote/summarize
        rather than this handler guessing what's relevant."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_list_notes(context, arguments)

    @staticmethod
    def _action_delete_note(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_note`: deletes the journal note whose title matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_delete_note(context, arguments)

    @staticmethod
    def _action_add_inventory_item(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_inventory_item`: adds an item with a quantity (0 when the number can't be read). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_add_inventory_item(context, arguments)

    @staticmethod
    def _action_list_inventory(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_inventory`: the inventory, or the items matching a query. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_list_inventory(context, arguments)

    @staticmethod
    def _action_delete_inventory_item(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_inventory_item`: removes the inventory item whose name matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_delete_inventory_item(context, arguments)

    @staticmethod
    def _action_adjust_inventory_quantity(context: AppContext, arguments: dict) -> str:
        """Assistant tool `adjust_inventory_quantity`: changes an item's quantity by a whole-number delta (negative to use some). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_adjust_inventory_quantity(context, arguments)

    @staticmethod
    def _action_list_waypoints(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_waypoints`: the saved waypoints (filtered by a query over name and notes), each with its coordinates and MGRS grid (none at the poles). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        query = str(arguments.get("query", "") or "").lower().strip()
        waypoints = context.waypoints.all_waypoints()
        if query:
            waypoints = [w for w in waypoints if query in f"{w.name} {w.notes}".lower()]
        if not waypoints:
            return "No matching waypoints found." if query else "You have no waypoints saved."
        from core.geo_grid import GridError, to_mgrs

        def grid(w) -> str:
            try:
                return f", grid {to_mgrs(w.latitude, w.longitude)}"
            except GridError:  # the poles: no MGRS there
                return ""
        lines = [f"- '{w.name}' ({w.latitude:.5f}, {w.longitude:.5f}{grid(w)})" for w in waypoints]
        return "Your waypoints:\n" + "\n".join(lines)

    @staticmethod
    def _action_waypoint_distance(context: AppContext, arguments: dict) -> str:
        """Assistant tool `waypoint_distance`: the distance in km and bearing between two named waypoints. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_waypoint_distance(context, arguments)

    @staticmethod
    def _action_list_trail_maps(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_trail_maps`: the cataloged trail-map PDFs, filtered by park or state. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        query = str(arguments.get("query", "") or "").lower().strip()
        trail_maps = context.trail_maps.all_trail_maps()
        if query:
            trail_maps = [t for t in trail_maps if query in f"{t.park_name} {t.state}".lower()]
        if not trail_maps:
            return "No matching trail maps found." if query else "You have no trail maps cataloged."
        lines = [f"- '{t.park_name}' ({t.state})" for t in trail_maps]
        return "Your trail maps:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_trail_map_from_url(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_trail_map_from_url`: downloads a trail-map PDF into the catalog; a file that isn't really a PDF is refused, a failed download is explained. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        park_name = str(arguments.get("park_name", "")).strip()
        state = str(arguments.get("state", "")).strip()
        url = str(arguments.get("url", "")).strip()
        notes = str(arguments.get("notes", "") or "")
        if not park_name or not state or not url:
            return "I need a park name, state, and URL to add a trail map."
        try:
            trail_map = context.trail_maps.add_from_url(park_name, state, url, notes=notes)
        except NotAPdfError:
            return f"The file at '{url}' doesn't look like a real trail map PDF — nothing was added."
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return f"Couldn't download that trail map: {exc}"
        return f"Added '{trail_map.park_name}' ({trail_map.state}) to your trail map catalog."

    @staticmethod
    def _action_delete_trail_map(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_trail_map`: deletes the trail map for the named park. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        park_name = str(arguments.get("park_name", "")).strip().lower()
        match = next((t for t in context.trail_maps.all_trail_maps() if t.park_name.lower() == park_name), None)
        if match is None:
            return f"I don't have a trail map called '{arguments.get('park_name', '')}'."
        context.trail_maps.delete_trail_map(match.trail_map_id)
        return f"Deleted the trail map for '{match.park_name}'."

    @staticmethod
    def _action_convert_units(context: AppContext, arguments: dict) -> str:
        """Assistant tool `convert_units`: converts a value between units, trying each category of the unit converter (core/unit_conversion.py, shared with the web Toolbox) until both units are recognized in the same one. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core.unit_conversion import UNIT_CATEGORIES, convert, resolve_unit_key

        from_text = str(arguments.get("from_unit", "")).strip()
        to_text = str(arguments.get("to_unit", "")).strip()
        if not from_text or not to_text:
            return "I need both a 'from' and 'to' unit to convert."
        try:
            value = float(arguments.get("value"))
        except (TypeError, ValueError):
            return "I need a numeric value to convert."

        for category, units in UNIT_CATEGORIES.items():
            from_key = resolve_unit_key(units, from_text)
            to_key = resolve_unit_key(units, to_text)
            if from_key is not None and to_key is not None:
                result = convert(category, from_key, to_key, value)
                return f"{value:g} {from_key} = {result:.4g} {to_key}"
        return f"I don't recognize '{from_text}' and/or '{to_text}' as units I can convert between."

    @staticmethod
    def _action_calculate_ohms_law(context: AppContext, arguments: dict) -> str:
        """Assistant tool `calculate_ohms_law`: solves voltage, current or resistance from the other two with Ohm's law (core/toolbox_calcs.solve, shared with the web Toolbox). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core.toolbox_calcs import solve

        solve_for = str(arguments.get("solve_for", "")).strip().lower()
        if solve_for not in ("voltage", "current", "resistance"):
            return "I need to know which value to solve for: voltage, current, or resistance."

        def _optional_float(key: str):
            raw = arguments.get(key)
            if raw is None or raw == "":
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        voltage = _optional_float("voltage")
        current = _optional_float("current")
        resistance = _optional_float("resistance")
        try:
            result = solve(solve_for, voltage, current, resistance)
        except (TypeError, ZeroDivisionError):
            return f"I need the other two values (not {solve_for}) to solve this."
        units = {"voltage": "V", "current": "A", "resistance": "Ω"}
        return f"{solve_for.capitalize()} = {result:.4g} {units[solve_for]}"

    @staticmethod
    def _action_delete_waypoint(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_waypoint`: deletes the waypoint whose name matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip().lower()
        match = next((w for w in context.waypoints.all_waypoints() if w.name.lower() == name), None)
        if match is None:
            return f"I don't have a waypoint called '{arguments.get('name', '')}'."
        context.waypoints.delete_waypoint(match.waypoint_id)
        return f"Deleted the waypoint '{match.name}'."

    @staticmethod
    def _action_get_sun_moon_info(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_sun_moon_info`: today's sunrise, sunset and moon phase (the Navigation module's
        summary) with the moon tonight (core/sun_moon.moon_tonight: days to the full or new moon, moonrise and
        moonset), at a named waypoint, else his town (core/weather.place). Returns the reply in words (an unknown
        waypoint, or no town yet, says so; nothing changes).
        One reading of the moon: the summary's four-bucket phase line is left out, so the reply never says Full Moon
        beside 6 days past it."""
        from datetime import date as _date

        from core import weather
        from core.sun_moon import format_sun_moon_summary, moon_tonight

        name = str(arguments.get("waypoint_name", "") or "").strip().lower()
        if name and name not in ("my town", "home", "here", "town", "null", "none", "unknown", "n/a"):
            match = next((w for w in context.waypoints.all_waypoints() if w.name.lower() == name), None)
            if match is None:
                return f"I don't have a waypoint called '{arguments.get('waypoint_name', '')}'."
            lat, lon, label = match.latitude, match.longitude, f"'{match.name}'"
        else:
            town = weather.place(context)
            if town is None:
                return ("I don't know your town yet. Tell me which one, like \"my town is Springfield, Illinois\", "
                        "or name a saved waypoint.")
            lat, lon, label = town["lat"], town["lon"], town["name"] or "your town"
        today = _date.today()
        sun_lines = [line for line in format_sun_moon_summary(lat, lon, today).splitlines()
                     if not line.startswith("Moon phase:")]  # one reading of the moon: moon_tonight's (review 2026-11-24)
        return f"For {label}: " + "\n".join(sun_lines + [moon_tonight(lat, lon, today)])

    @staticmethod
    def _action_get_system_health(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_system_health`: the PC's CPU, memory, disk and temperature, read and put in words. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
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
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_recall_recent_activity(context, arguments)

    @staticmethod
    def _action_list_observations(context: AppContext, arguments: dict) -> str:
        """
        Fetches every currently open Insight as plain text — same
        "let the LLM phrase its own answer from raw records" shape as
        _action_recall_recent_activity above. Distinct from that
        action: this is MIA's own durable observations (Maintenance/
        Missions scans, modules/observations/module.py), not a log of
        what the USER did.
        """
        if context.insights is None:
            return "Observations aren't available."
        open_insights = context.insights.open_insights()
        if not open_insights:
            return "Nothing open right now — no observations need attention."

        lines = []
        for insight in open_insights:
            pending = next(
                (r for r in context.insights.recommendations_for_insight(insight.insight_id) if r.status == "pending"),
                None,
            )
            line = f"[{insight.source_type}] {insight.message}"
            if pending:
                line += f" Recommendation: {pending.message}"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _action_list_field_captures(context: AppContext, arguments: dict) -> str:
        """
        Fetches every pending field-capture transcript as plain text —
        same "let the LLM phrase its own answer from raw records" shape
        as _action_list_observations above. GUI-only, same reason as
        that action: headless Core never constructs
        context.lite_captures either.
        """
        if context.lite_captures is None:
            return "Field Captures aren't available."
        pending = context.lite_captures.pending_proposals()
        if not pending:
            return "Nothing waiting for review."

        lines = [f"{proposal.journal_title}: {proposal.transcript}" for proposal in pending]
        return "\n".join(lines)

    @staticmethod
    def _action_get_life_state(context: AppContext, arguments: dict) -> str:
        """
        The first real consumer of core.context_assembler (2026-09-14) —
        a synthesized "what's going on with me" answer, led by what needs
        him now, what she's holding and what she did on her own
        (core/needs_now.py, 2026-11-23), then where he left off
        (core/left_off.py), built live from
        Missions/Skills/Insights/Maintenance/Projects rather than the
        LLM having to stitch together several separate action calls
        itself. GUI-only, same reason list_observations/
        list_field_captures are: context.insights/maintenance/projects/
        recurring_missions are only ever constructed in
        core/application.py, not the headless boot path.
        """
        if context.profiles is None:
            return "Life state isn't available without an active profile."
        from core.person_settings import person_id

        # The person this turn is for (the phone user on their own view).
        profile_id = person_id(context)
        if profile_id is None:
            return "No active profile — nothing to report."
        # First what needs him now, what she's holding and what she did on her own (core/needs_now.py, brainstorm
        # 2.1); then Life State v2 (wins, friction, waiting chains, the monthly plan), then v1's missions-and-skills
        # line.
        from core import left_off, needs_now

        first = needs_now.describe(needs_now.gather(context))
        picked_up = left_off.describe(left_off.gather(context))  # where he left off (brainstorm 1.2)
        wider = describe_life_state_v2(assemble_life_state_v2(context, date.today()))
        snapshot = assemble_life_state(context, profile_id, date.today())
        return " ".join(part for part in (first, picked_up, wider, format_life_state_summary(snapshot)) if part)

    @staticmethod
    def _action_add_waypoint(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_waypoint`: saves a waypoint from latitude/longitude or an MGRS grid reference (parsed in code, DEC-0099); an unknown category becomes uncategorized, like the UI's blank option. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to save a waypoint."
        from core.geo_grid import GridError, from_mgrs

        try:
            if str(arguments.get("grid") or "").strip():  # an MGRS grid reference, read in code (DEC-0099)
                latitude, longitude = from_mgrs(str(arguments["grid"]))
            else:
                latitude = float(arguments.get("latitude"))
                longitude = float(arguments.get("longitude"))
        except GridError as problem:
            return str(problem)
        except (TypeError, ValueError):
            return "I need a valid latitude and longitude, or a grid reference, to save a waypoint."
        category = str(arguments.get("category", "") or "").strip()
        if category not in WAYPOINT_CATEGORIES:
            category = ""  # unrecognized value -> uncategorized, same fail-safe as the UI's blank option
        waypoint = context.waypoints.add_waypoint(name=name, latitude=latitude, longitude=longitude, category=category)
        return f"Waypoint '{waypoint.name}' saved at ({waypoint.latitude:.5f}, {waypoint.longitude:.5f})."

    @staticmethod
    def _action_add_expedition(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_expedition`: starts an expedition with a start date and location. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start an expedition."
        start_date = str(arguments.get("start_date", "") or "").strip()
        location = str(arguments.get("location", "") or "").strip()
        expedition = context.expeditions.add_expedition(name=name, start_date=start_date, location=location)
        return f"Expedition '{expedition.name}' created."

    @staticmethod
    def _action_list_expeditions(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_expeditions`: every expedition with its date and location. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        expeditions = context.expeditions.all_expeditions()
        if not expeditions:
            return "You have no expeditions yet."
        lines = []
        for expedition in expeditions:
            date_part = f" ({expedition.start_date})" if expedition.start_date else ""
            location_part = f" — {expedition.location}" if expedition.location else ""
            lines.append(f"- '{expedition.name}'{date_part}{location_part}")
        return "Your expeditions:\n" + "\n".join(lines)

    @staticmethod
    def _action_recall_expedition(context: AppContext, arguments: dict) -> str:
        """Assistant tool `recall_expedition`: the memory recap of a named expedition (or the latest): duration, trips per activity with distance and speed, waypoint kinds visited, the latest log and photo count. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "") or "").strip().lower()
        if name:
            expedition = next(
                (e for e in context.expeditions.all_expeditions() if e.name.lower() == name), None
            )
            if expedition is None:
                return f"I don't have an expedition called '{arguments.get('name', '')}'."
            recap = context.memories.recap_for_expedition(expedition.expedition_id)
        else:
            recaps = context.memories.all_recaps()
            if not recaps:
                return "You have no expeditions yet."
            recap = recaps[0]

        lines = [f"'{recap.expedition.name}'"]
        if recap.expedition.location:
            lines.append(f"Location: {recap.expedition.location}")
        if recap.duration_days:
            lines.append(f"Duration: {recap.duration_days} day{'s' if recap.duration_days != 1 else ''}")
        for stats in recap.activity_breakdown.values():
            parts = [f"{stats.trip_count} trip(s)"]
            if stats.distance_km:
                parts.append(f"{stats.distance_km:.1f} km")
            if stats.average_speed_kmh:
                parts.append(f"avg {stats.average_speed_kmh:.1f} km/h")
            lines.append(f"{stats.activity_type}: " + ", ".join(parts))
        if recap.waypoint_categories_visited:
            categories = ", ".join(
                f"{count} {category}" for category, count in sorted(recap.waypoint_categories_visited.items())
            )
            lines.append(f"Visited: {categories}")
        if recap.journal_highlights:
            latest = recap.journal_highlights[0]
            conditions = f" ({latest.conditions})" if latest.conditions else ""
            lines.append(f"Latest log: '{latest.title}'{conditions}")
        if recap.photo_count:
            lines.append(f"Photos: {recap.photo_count}")
        return "\n".join(lines)

    @staticmethod
    def _action_add_trip(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_trip`: adds a trip under a named expedition (an unknown activity type is dropped). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        expedition_name = str(arguments.get("expedition_name", "")).strip().lower()
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a trip."
        expedition = next(
            (e for e in context.expeditions.all_expeditions() if e.name.lower() == expedition_name), None
        )
        if expedition is None:
            return f"I don't have an expedition called '{arguments.get('expedition_name', '')}'."
        activity_type = str(arguments.get("activity_type", "") or "").strip()
        if activity_type not in ACTIVITY_TYPES:
            activity_type = ""
        start_date = str(arguments.get("start_date", "") or "").strip()
        trip = context.trips.add_trip(
            expedition_id=expedition.expedition_id, name=name, activity_type=activity_type, start_date=start_date,
        )
        return f"Trip '{trip.name}' added under expedition '{expedition.name}'."

    @staticmethod
    def _action_list_trips(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_trips`: the trips, all or one expedition's, with activity and status. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        expedition_name = str(arguments.get("expedition_name", "") or "").strip().lower()
        if expedition_name:
            expedition = next(
                (e for e in context.expeditions.all_expeditions() if e.name.lower() == expedition_name), None
            )
            if expedition is None:
                return f"I don't have an expedition called '{arguments.get('expedition_name', '')}'."
            trips = context.trips.trips_for_expedition(expedition.expedition_id)
        else:
            trips = context.trips.all_trips()

        if not trips:
            return "No matching trips found." if expedition_name else "You have no trips yet."
        lines = []
        for trip in trips:
            activity_part = f" [{trip.activity_type}]" if trip.activity_type else ""
            lines.append(f"-{activity_part} '{trip.name}' ({trip.status})")
        return "Your trips:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_gear_item(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_gear_item`: adds an item to a trip's gear checklist. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        trip_name = str(arguments.get("trip_name", "")).strip().lower()
        label = str(arguments.get("label", "")).strip()
        if not label:
            return "I need a gear item name to add it to a trip's checklist."
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
        context.trips.add_gear_item(trip.trip_id, label=label)
        return f"Added '{label}' to the gear checklist for '{trip.name}'."

    @staticmethod
    def _action_add_trip_log_entry(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_trip_log_entry`: adds a journal entry tied to a trip, with conditions. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        trip_name = str(arguments.get("trip_name", "")).strip().lower()
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a title to add a trip log entry."
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
        body = str(arguments.get("body", "") or "")
        conditions = str(arguments.get("conditions", "") or "")
        context.journal.add_entry(title=title, body=body, trip_id=trip.trip_id, conditions=conditions)
        return f"Log entry '{title}' added to '{trip.name}'."

    @staticmethod
    def _action_delete_expedition(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_expedition`: deletes the expedition whose name matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip().lower()
        match = next((e for e in context.expeditions.all_expeditions() if e.name.lower() == name), None)
        if match is None:
            return f"I don't have an expedition called '{arguments.get('name', '')}'."
        context.expeditions.delete_expedition(match.expedition_id)
        return f"Deleted the expedition '{match.name}'."

    @staticmethod
    def _action_delete_trip(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_trip`: deletes the trip whose name matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip().lower()
        match = next((t for t in context.trips.all_trips() if t.name.lower() == name), None)
        if match is None:
            return f"I don't have a trip called '{arguments.get('name', '')}'."
        context.trips.delete_trip(match.trip_id)
        return f"Deleted the trip '{match.name}'."

    @staticmethod
    def _action_toggle_gear_packed(context: AppContext, arguments: dict) -> str:
        """Assistant tool `toggle_gear_packed`: flips a trip's gear item between packed and not packed. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        trip_name = str(arguments.get("trip_name", "")).strip().lower()
        label = str(arguments.get("label", "")).strip().lower()
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
        index = next((i for i, g in enumerate(trip.gear) if g.label.lower() == label), None)
        if index is None:
            return f"'{trip.name}' has no gear item called '{arguments.get('label', '')}'."
        updated = context.trips.toggle_gear_packed(trip.trip_id, index)
        item = updated.gear[index]
        state = "packed" if item.packed else "not packed"
        return f"'{item.label}' on '{trip.name}' is now marked {state}."

    @staticmethod
    def _action_get_trip_summary(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_trip_summary`: a trip's logged distance, average speed and planned route distance, whichever exist. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip().lower()
        trip = next((t for t in context.trips.all_trips() if t.name.lower() == name), None)
        if trip is None:
            return f"I don't have a trip called '{arguments.get('name', '')}'."
        lines = [f"'{trip.name}':"]
        distance = context.trips.total_distance_km(trip.trip_id)
        if distance is not None:
            lines.append(f"- Logged distance: {distance:.1f} km")
        speed = context.trips.average_speed_kmh(trip.trip_id)
        if speed is not None:
            lines.append(f"- Average speed: {speed:.1f} km/h")
        planned = context.trips.planned_route_distance_km(trip.trip_id)
        if planned is not None:
            lines.append(f"- Planned route distance: {planned:.1f} km")
        if len(lines) == 1:
            lines.append("- No distance/speed data logged for this trip yet.")
        return "\n".join(lines)

    @staticmethod
    def _action_get_device_profile(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_device_profile`: which edition this device runs (Core field edition or Home desktop). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        profile = get_device_profile(context)
        label = "Core (Pi 5 + AI HAT+ 2 field edition)" if profile == CORE else "Home (desktop workstation edition)"
        return f"This device is running the {label}."

    @staticmethod
    def _action_set_birthday(context: AppContext, arguments: dict) -> str:
        """Assistant tool `set_birthday`: saves the signed-in person's birthday (YYYY-MM-DD). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        birthday = str(arguments.get("birthday", "")).strip()
        try:
            datetime.fromisoformat(birthday)
        except ValueError:
            return "I need a birthday in YYYY-MM-DD format to remember it."
        active_profile = context.profiles.get_active_profile() if context.profiles is not None else None
        if active_profile is None:
            return "I don't have an active user profile to save that to."
        context.profiles.set_birthday(active_profile.profile_id, birthday)
        return f"Got it — I'll remember your birthday is {birthday}."

    @staticmethod
    def _action_set_theme(context: AppContext, arguments: dict) -> str:
        """Assistant tool `set_theme`: switches the theme and publishes theme.changed so it applies live. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        themes = AssistantTools.DESKTOP_THEMES  # filled by the desktop app; empty where there's no window
        if not themes:
            return "There's no desktop window here to change the theme of."
        theme_id = str(arguments.get("theme_id", "")).strip().lower()
        if theme_id not in themes:
            valid = ", ".join(themes.keys())
            return f"'{arguments.get('theme_id', '')}' isn't a theme I know. Valid themes: {valid}."
        context.config.set("gui.theme", theme_id)
        context.config.save()
        context.events.publish("theme.changed", theme_id=theme_id)
        return f"Theme changed to {themes[theme_id]}."

    @staticmethod
    def _action_add_calendar_event(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_calendar_event`: adds a calendar event with a date, optional time, notes and recurrence (an unknown recurrence is dropped); a date passed as words ("Friday at 2pm") is read as its day (core/calendar_move.day_of), never kept as words. Returns the reply in words (a missing or unknown name says so, nothing changes).
        A title that's only "reminder" or "event" asks what it's for."""
        title = str(arguments.get("title", "")).strip()
        date_str = str(arguments.get("date", "") or "").strip()
        if not title:
            return "I need a title to add a calendar event."
        import re

        if re.fullmatch(r"(?:an?\s+|the\s+|my\s+)?(?:calendar\s+)?(?:event|reminder|appointment|thing|item|task)s?",
                        title, re.I):
            return "What's it for? Say what the event is, like \"the dentist\"."  # never one called "Reminder"
        if not date_str:
            return "I need a date (YYYY-MM-DD) to add a calendar event."
        from core.calendar_move import event_day

        date_str = event_day(date_str) or ""  # "Friday at 2pm" passed as the date: its day, never the words
        if not date_str:
            return "Which day? Say a day like \"Friday\" or a date, and I'll put it on the calendar."
        time_str = str(arguments.get("time", "") or "").strip() or None
        notes = str(arguments.get("notes", "") or "")
        recurrence = str(arguments.get("recurrence", "") or "").strip().lower() or None
        if recurrence not in (None, *CALENDAR_RECURRENCE_TYPES):
            recurrence = None
        event = context.calendar.add_event(title=title, date=date_str, time=time_str, notes=notes, recurrence=recurrence)
        time_part = f" at {event.time}" if event.time else ""
        recurrence_part = f", repeating {event.recurrence}" if event.recurrence else ""
        return f"Calendar event '{event.title}' added for {event.date}{time_part}{recurrence_part}."

    @staticmethod
    def _action_list_calendar_events(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_calendar_events`: the events on the days his words name, else what's coming up (core/calendar_move.listing), with dates, times and repeats. Returns the reply in words; nothing changes."""
        from core.calendar_move import listing

        return listing(context.calendar.all_events(), str(arguments.get("question") or ""))

    @staticmethod
    def _action_delete_calendar_event(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_calendar_event`: deletes the calendar event whose title matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_delete_calendar_event(context, arguments)

    @staticmethod
    def _action_get_power_status(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_power_status`: battery percent, plugged in or not, and minutes left when known. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_get_power_status(context, arguments)

    @staticmethod
    def _action_add_component(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_component`: adds an electronics component (category, value, package, quantity, location). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a component."
        category = str(arguments.get("category", "") or "").strip()
        value = str(arguments.get("value", "") or "").strip()
        package = str(arguments.get("package", "") or "").strip()
        try:
            quantity = int(arguments.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            quantity = 0
        location = str(arguments.get("location", "") or "").strip()
        component = context.components.add_component(
            name=name, category=category, value=value, package=package, quantity=quantity, location=location,
        )
        return f"Component '{component.name}' added (qty {component.quantity})."

    @staticmethod
    def _action_list_components(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_components`: the components, or those matching a query. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        query = str(arguments.get("query", "") or "").strip()
        components = context.components.search(query) if query else context.components.all_components()
        if not components:
            return "No matching components found." if query else "You have no components saved."
        lines = [f"- '{c.name}' qty {c.quantity}" + (f" ({c.category})" if c.category else "") for c in components]
        return "Your components:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_component(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_component`: deletes the component whose name matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip().lower()
        match = next((c for c in context.components.all_components() if c.name.lower() == name), None)
        if match is None:
            return f"I don't have a component called '{arguments.get('name', '')}'."
        context.components.delete_component(match.component_id)
        return f"Deleted the component '{match.name}'."

    @staticmethod
    def _action_add_material(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_material`: adds a workshop material with its unit and quantity on hand. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a material."
        unit = str(arguments.get("unit", "") or "").strip()
        try:
            quantity_on_hand = float(arguments.get("quantity_on_hand", 0) or 0)
        except (TypeError, ValueError):
            quantity_on_hand = 0.0
        material = context.materials.add_material(name=name, unit=unit, quantity_on_hand=quantity_on_hand)
        return f"Material '{material.name}' added (qty {material.quantity_on_hand:g}{' ' + unit if unit else ''})."

    @staticmethod
    def _action_list_materials(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_materials`: the materials and how much of each is on hand. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        query = str(arguments.get("query", "") or "").strip()
        materials = context.materials.search(query) if query else context.materials.all_materials()
        if not materials:
            return "No matching materials found." if query else "You have no materials saved."
        lines = [f"- '{m.name}': {m.quantity_on_hand:g}{' ' + m.unit if m.unit else ''} on hand" for m in materials]
        return "Your materials:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_product(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_product`: adds a product with stock and base price. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a product."
        try:
            quantity_in_stock = float(arguments.get("quantity_in_stock", 0) or 0)
        except (TypeError, ValueError):
            quantity_in_stock = 0.0
        try:
            base_price = float(arguments.get("base_price", 0) or 0)
        except (TypeError, ValueError):
            base_price = 0.0
        product = context.products.add_product(name=name, quantity_in_stock=quantity_in_stock, base_price=base_price)
        return f"Product '{product.name}' added (qty {product.quantity_in_stock:g})."

    @staticmethod
    def _action_list_products(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_products`: the products and their stock. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        query = str(arguments.get("query", "") or "").strip()
        products = context.products.search(query) if query else context.products.all_products()
        if not products:
            return "No matching products found." if query else "You have no products saved."
        lines = [f"- '{p.name}': {p.quantity_in_stock:g} in stock" for p in products]
        return "Your products:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_job(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_job`: starts a production job. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start a job."
        description = str(arguments.get("description", "") or "").strip()
        job = context.jobs.add_job(name=name, description=description)
        return f"Job '{job.name}' started (status {job.status})."

    @staticmethod
    def _action_list_jobs(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_jobs`: every job with its status. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        jobs = context.jobs.all_jobs()
        if not jobs:
            return "You have no jobs yet."
        return "Your jobs:\n" + "\n".join(f"- '{j.name}' ({j.status})" for j in jobs)

    @staticmethod
    def _action_consume_material(context: AppContext, arguments: dict) -> str:
        """Assistant tool `consume_material`: records a quantity of a material used on a job (stock goes down). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        job_name = str(arguments.get("job_name", "")).strip().lower()
        material_name = str(arguments.get("material_name", "")).strip().lower()
        job = next((j for j in context.jobs.all_jobs() if j.name.lower() == job_name), None)
        if job is None:
            return f"I don't have a job called '{arguments.get('job_name', '')}'."
        material = next((m for m in context.materials.all_materials() if m.name.lower() == material_name), None)
        if material is None:
            return f"I don't have a material called '{arguments.get('material_name', '')}'."
        try:
            quantity = float(arguments.get("quantity", 0))
        except (TypeError, ValueError):
            return "I need a numeric quantity to record material use."
        context.jobs.consume_material(job.job_id, material.material_id, quantity)
        return f"Recorded {quantity:g} of '{material.name}' used on job '{job.name}'."

    @staticmethod
    def _action_produce_product(context: AppContext, arguments: dict) -> str:
        """Assistant tool `produce_product`: records a quantity of a product a job made (stock goes up). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        job_name = str(arguments.get("job_name", "")).strip().lower()
        product_name = str(arguments.get("product_name", "")).strip().lower()
        job = next((j for j in context.jobs.all_jobs() if j.name.lower() == job_name), None)
        if job is None:
            return f"I don't have a job called '{arguments.get('job_name', '')}'."
        product = next((p for p in context.products.all_products() if p.name.lower() == product_name), None)
        if product is None:
            return f"I don't have a product called '{arguments.get('product_name', '')}'."
        try:
            quantity = float(arguments.get("quantity", 0))
        except (TypeError, ValueError):
            return "I need a numeric quantity to record production."
        context.jobs.produce_product(job.job_id, product.product_id, quantity)
        return f"Recorded {quantity:g} of '{product.name}' produced by job '{job.name}'."

    @staticmethod
    def _action_record_sale(context: AppContext, arguments: dict) -> str:
        """Assistant tool `record_sale`: records a product sale in the ledger (quantity and amount). Returns the reply in words (a missing or unknown name says so, nothing changes).
        A sale needs a quantity and an amount above zero, or it asks."""
        product_name = str(arguments.get("product_name", "")).strip().lower()
        product = next((p for p in context.products.all_products() if p.name.lower() == product_name), None)
        if product is None:
            return f"I don't have a product called '{arguments.get('product_name', '')}'."
        try:
            quantity = float(arguments.get("quantity", 1) or 1)
            amount = float(arguments["amount"])
        except (TypeError, ValueError):
            return "I need a numeric quantity and sale amount to record a sale."
        if quantity <= 0 or amount <= 0:
            return "How many, and for how much? A sale needs both, like \"sold 2 birdhouses for $60\"."  # the Fable audit
        context.ledger.record_sale(product.product_id, quantity, amount)
        return f"Recorded a sale of {quantity:g} '{product.name}' for {money(amount, '.2f')}."

    @staticmethod
    def _action_get_ledger_summary(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_ledger_summary`: the ledger's total revenue, expenses and net profit, in the person's currency. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        revenue = context.ledger.total_revenue()
        expenses = context.ledger.total_expenses()
        profit = context.ledger.net_profit()
        return f"Total revenue: {money(revenue, '.2f')}. Total expenses: {money(expenses, '.2f')}. Net profit: {money(profit, '.2f')}."

    @staticmethod
    def _action_list_connected_devices(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_connected_devices`: the drives and serial devices plugged in now. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        block_devices = context.devices.list_block_devices()
        serial_devices = context.devices.list_serial_devices()
        if not block_devices and not serial_devices:
            return "No external devices are currently connected."
        lines = [f"- {d.display_name} (storage)" for d in block_devices]
        lines += [f"- {d.display_name} (serial)" for d in serial_devices]
        return "Connected devices:\n" + "\n".join(lines)

    @staticmethod
    def _action_list_scripts(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_scripts`: the saved scripts, or those matching a query. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        query = str(arguments.get("query", "") or "").strip()
        scripts = context.scripts.search(query) if query else context.scripts.all_scripts()
        if not scripts:
            return "No matching scripts found." if query else "You have no saved scripts."
        lines = [f"- '{s.name}'" + (f" [{s.category}]" if s.category else "") + f" ({s.interpreter})" for s in scripts]
        return "Your scripts:\n" + "\n".join(lines)

    @staticmethod
    def _action_list_profiles(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_profiles`: the profiles on this device, marking the active one. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        profiles = context.profiles.list_profiles()
        if not profiles:
            return "No profiles are set up on this device."
        active = context.profiles.get_active_profile()
        lines = []
        for profile in profiles:
            marker = " (active)" if active is not None and profile.profile_id == active.profile_id else ""
            lock = " \U0001F512" if profile.has_password else ""
            lines.append(f"- '{profile.name}'{marker}{lock}")
        return "Profiles on this device:\n" + "\n".join(lines)

    @staticmethod
    def _action_identify_hash(context: AppContext, arguments: dict) -> str:
        """Assistant tool `identify_hash`: the hash formats a value could be (identify_hash's candidates). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        value = str(arguments.get("value", "")).strip()
        if not value:
            return "I need a hash value to identify."
        candidates = identify_hash(value)
        if not candidates:
            return "No known hash format matched."
        return "Possible format(s): " + ", ".join(candidates)

    @staticmethod
    def _action_check_password_strength(context: AppContext, arguments: dict) -> str:
        """Assistant tool `check_password_strength`: a password's rating and entropy in bits, with its warnings (assessed locally). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        password = str(arguments.get("password", ""))
        if not password:
            return "I need a password to check."
        result = assess_password(password)
        lines = [f"Strength: {result.rating} ({result.entropy_bits:.1f} bits)"]
        lines.extend(result.warnings)
        return "\n".join(lines)

    @staticmethod
    def _action_calculate_subnet(context: AppContext, arguments: dict) -> str:
        """Assistant tool `calculate_subnet`: network, broadcast, netmask, address and usable-host counts and the usable range for a CIDR. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        cidr = str(arguments.get("cidr", "")).strip()
        if not cidr:
            return "I need a CIDR, e.g. '192.168.1.0/24', to calculate a subnet."
        try:
            info = calculate_subnet(cidr)
        except ValueError as exc:
            return f"Invalid CIDR: {exc}"
        lines = [
            f"Network: {info.network_address}/{info.prefix_length}",
            f"Broadcast: {info.broadcast_address}",
            f"Netmask: {info.netmask}",
            f"Total addresses: {info.total_addresses}",
            f"Usable hosts: {info.usable_host_count}",
        ]
        if info.first_usable:
            lines.append(f"Usable range: {info.first_usable} - {info.last_usable}")
        return "\n".join(lines)

    @staticmethod
    def _action_scan_ports(context: AppContext, arguments: dict) -> str:
        """Assistant tool `scan_ports`: scans common ports on a host, but only one on the person's own network (DEC-0056). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        host = str(arguments.get("host", "")).strip()
        if not host:
            return "I need a host or IP to scan."
        import socket

        from core.port_scanner import own_network

        try:
            socket.gethostbyname(host)
        except (OSError, UnicodeError):
            return f"Could not resolve '{host}'."
        if not own_network(host):  # DEC-0056: active scans only on your own network
            return (f"{host} isn't on your own network, so I won't scan it from a request. Scanning someone else's "
                    "machine needs their permission; the Field Kit's scanner is there if you're authorized.")
        result = scan_ports(host, ports=list(_ASSISTANT_SCAN_PORTS), timeout=_ASSISTANT_SCAN_TIMEOUT_SECONDS)
        if result.error:
            return result.error
        ports_checked = ", ".join(str(p) for p in _ASSISTANT_SCAN_PORTS)
        if not result.open_ports:
            return f"No open ports found among the common ports checked ({ports_checked})."
        ports_open = ", ".join(str(p) for p in result.open_ports)
        return f"Open ports on {host}: {ports_open} (checked {ports_checked})."

    @staticmethod
    def _action_add_project(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_project`: starts a project with a status and due date. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start a project."
        status = str(arguments.get("status", "") or "").strip()
        if status not in PROJECT_STATUSES:
            status = "Planning"
        due_date = str(arguments.get("due_date", "") or "").strip()
        project = context.projects.add_project(name=name, status=status, due_date=due_date)
        return f"Project '{project.name}' created."

    @staticmethod
    def _action_list_projects(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_projects`: every project with its status and due date. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        projects = context.projects.all_projects()
        if not projects:
            return "You have no projects yet."
        lines = []
        for project in projects:
            due_part = f" (due {project.due_date})" if project.due_date else ""
            lines.append(f"- '{project.name}' [{project.status}]{due_part}")
        return "Your projects:\n" + "\n".join(lines)

    @staticmethod
    def _action_add_task(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_task`: adds a task under a named project. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        project_name = str(arguments.get("project_name", "")).strip().lower()
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a title to add a task."
        project = next(
            (p for p in context.projects.all_projects() if p.name.lower() == project_name), None
        )
        if project is None:
            return f"I don't have a project called '{arguments.get('project_name', '')}'."
        due_date = str(arguments.get("due_date", "") or "").strip()
        task = context.tasks.add_task(project_id=project.project_id, title=title, due_date=due_date)
        return f"Task '{task.title}' added under project '{project.name}'."

    @staticmethod
    def _action_list_tasks(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_tasks`: the tasks, all or one project's, with done marks. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        project_name = str(arguments.get("project_name", "") or "").strip().lower()
        if project_name:
            project = next(
                (p for p in context.projects.all_projects() if p.name.lower() == project_name), None
            )
            if project is None:
                return f"I don't have a project called '{arguments.get('project_name', '')}'."
            tasks = context.tasks.tasks_for_project(project.project_id)
        else:
            tasks = context.tasks.all_tasks()

        if not tasks:
            return "No matching tasks found." if project_name else "You have no tasks yet."
        lines = []
        for task in tasks:
            mark = "[x]" if task.done else "[ ]"
            due_part = f" (due {task.due_date})" if task.due_date else ""
            lines.append(f"- {mark} '{task.title}'{due_part}")
        return "Your tasks:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_project(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_project`: deletes the project whose name matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip().lower()
        match = next((p for p in context.projects.all_projects() if p.name.lower() == name), None)
        if match is None:
            return f"I don't have a project called '{arguments.get('name', '')}'."
        context.projects.delete_project(match.project_id)
        return f"Deleted the project '{match.name}'."

    @staticmethod
    def _action_delete_task(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_task`: deletes the task whose title matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        title = str(arguments.get("title", "")).strip().lower()
        match = next((t for t in context.tasks.all_tasks() if t.title.lower() == title), None)
        if match is None:
            return f"I don't have a task called '{arguments.get('title', '')}'."
        context.tasks.delete_task(match.task_id)
        return f"Deleted the task '{match.title}'."

    @staticmethod
    def _action_mark_task_done(context: AppContext, arguments: dict) -> str:
        """Assistant tool `mark_task_done`: marks a task done (or not done). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        title = str(arguments.get("title", "")).strip().lower()
        match = next((t for t in context.tasks.all_tasks() if t.title.lower() == title), None)
        if match is None:
            return f"I don't have a task called '{arguments.get('title', '')}'."
        done = bool(arguments.get("done", True))
        context.tasks.update_task(match.task_id, done=done)
        status = "done" if done else "not done"
        return f"Marked the task '{match.title}' as {status}."

    @staticmethod
    def _action_add_mission(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_mission`: starts a mission, optionally linked to a trip. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to start a mission."
        trip_name = str(arguments.get("trip_name", "") or "").strip().lower()
        trip_id = None
        if trip_name:
            trip = next((t for t in context.trips.all_trips() if t.name.lower() == trip_name), None)
            if trip is None:
                return f"I don't have a trip called '{arguments.get('trip_name', '')}'."
            trip_id = trip.trip_id
        mission = context.missions.add_mission(name=name, trip_id=trip_id)
        linked_note = f" Linked to trip '{trip.name}'." if trip_id else ""
        return f"Mission '{mission.name}' created.{linked_note}"

    @staticmethod
    def _action_list_missions(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_missions`: every mission with each objective's progress and check mark. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_list_missions(context, arguments)

    @staticmethod
    def _action_add_objective(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_objective`: adds an objective to a mission (metric type, numeric target). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_add_objective(context, arguments)

    @staticmethod
    def _action_log_mission_progress(context: AppContext, arguments: dict) -> str:
        """Assistant tool `log_mission_progress`: adds to a mission's tally objective (the only one, or the one named) and says how close it is. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_log_mission_progress(context, arguments)

    @staticmethod
    def _action_delete_mission(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_mission`: deletes the mission whose name matches. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_delete_mission(context, arguments)

    @staticmethod
    def _action_complete_mission(context: AppContext, arguments: dict) -> str:
        """Assistant tool `complete_mission`: marks a mission completed. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        from core import core_runtime  # one body, shared with headless Core (no Qt there)

        return core_runtime._action_complete_mission(context, arguments)

    # ------------------------------------------------------------------
    # Maintenance actions — see the registration block's comment above
    # for the collision-risk/scope-limitation reasoning.
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_maintenance_task_tolerant(context: AppContext, title: str, asset_name: str) -> tuple[Optional[MaintenanceTask], Optional[str]]:
        """2026-09-27 conversational audit: people say "I changed the oil
        in the truck", not "Oil change" / "Pickup Truck". Non-destructive
        actions (complete, log a reading) resolve both names tolerantly
        via core.assistant_lookup, acting only on one unambiguous match
        and otherwise asking. Destructive ones keep the exact-match
        resolver below."""
        tasks = context.maintenance.all_tasks()
        if asset_name:
            asset, error = resolve_by_name(context.maintenance.all_assets(), asset_name, lambda a: a.name, "tracked item")
            if error:
                return None, error
            tasks = [t for t in tasks if t.asset_id == asset.asset_id]
            if not tasks:
                return None, f"{asset.name} doesn't have any maintenance tasks yet."
            if not title and len(tasks) == 1:
                return tasks[0], None
        return resolve_by_name(tasks, title, lambda t: t.title, "maintenance task")

    @staticmethod
    def _resolve_maintenance_task(context: AppContext, title: str, asset_name: str) -> tuple[Optional[MaintenanceTask], Optional[str]]:
        """Exact case-insensitive title match, optionally narrowed by
        asset name — never fuzzy, same fail-closed name-resolution
        discipline as every other write/destructive action in this
        registry. Returns (task, None) on a unique match, or
        (None, error_message) otherwise — including "multiple assets
        share this task title," which asks the user to disambiguate
        rather than guessing which one they meant."""
        candidates = [t for t in context.maintenance.all_tasks() if t.title.lower() == title.lower()]
        if asset_name:
            asset = next((a for a in context.maintenance.all_assets() if a.name.lower() == asset_name.lower()), None)
            if asset is None:
                return None, f"I don't have a maintenance asset called '{asset_name}'."
            candidates = [t for t in candidates if t.asset_id == asset.asset_id]
        if not candidates:
            return None, f"I don't have a maintenance task called '{title}'" + (f" for {asset_name}." if asset_name else ".")
        if len(candidates) > 1:
            names = sorted({
                (context.maintenance.get_asset(t.asset_id).name if context.maintenance.get_asset(t.asset_id) else "Unknown asset")
                for t in candidates
            })
            return None, f"Multiple assets have a task called '{title}' ({', '.join(names)}) — tell me which one."
        return candidates[0], None

    @staticmethod
    def _action_add_maintenance_asset(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_maintenance_asset`: adds a vehicle or piece of equipment to Maintenance. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a maintenance asset."
        category = str(arguments.get("category", "") or "Other").strip()
        category = next((c for c in MAINTENANCE_ASSET_CATEGORIES if c.lower() == category.lower()), category)
        if category.lower() in ("garden", "greenhouse", "plant", "plants"):
            category = "Garden/Plant"
        if category not in MAINTENANCE_ASSET_CATEGORIES:
            category = "Other"
        asset = context.maintenance.add_asset(name=name, category=category)
        return f"Added '{asset.name}' to Maintenance as a {asset.category}."

    @staticmethod
    def _action_list_maintenance_assets(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_maintenance_assets`: everything tracked in Maintenance. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        assets = context.maintenance.all_assets()
        if not assets:
            return "You have no vehicles or equipment tracked in Maintenance yet."
        lines = [f"- {a.name} [{a.category}]" for a in assets]
        return "Tracked in Maintenance:\n" + "\n".join(lines)

    @staticmethod
    def _action_delete_maintenance_asset(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_maintenance_asset`: deletes a tracked item from Maintenance. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip().lower()
        match = next((a for a in context.maintenance.all_assets() if a.name.lower() == name), None)
        if match is None:
            return f"I don't have a maintenance asset called '{arguments.get('name', '')}'."
        context.maintenance.delete_asset(match.asset_id)
        return f"Deleted '{match.name}' from Maintenance."

    @staticmethod
    def _action_add_maintenance_task(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_maintenance_task`: adds a task for a tracked item, repeating every N days or one-time; a one-time thing with a day ("next Saturday") goes on the calendar instead (live check, 2026-11-24). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        asset_name = str(arguments.get("asset_name", "")).strip()
        asset, error = resolve_by_name(context.maintenance.all_assets(), asset_name, lambda a: a.name, "tracked item")
        if error:
            return error
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a task title."
        interval_days = arguments.get("interval_days")
        interval_days = int(interval_days) if interval_days not in (None, "") else None
        when = str(arguments.get("date", "") or "").strip()
        if when and not interval_days and getattr(context, "calendar", None) is not None:
            # a one-time thing on a day ("next Saturday") goes on the calendar, never a task repeating every 7 days
            from datetime import date as _date

            from core.calendar_move import day_of

            day = day_of(when)
            if day:
                context.calendar.add_event(title=f"{title} ({asset.name})", date=day)
                on = _date.fromisoformat(day)
                return f"On your calendar for {on:%A, %B} {on.day}: {title} ({asset.name})."
        task = context.maintenance.add_task(asset_id=asset.asset_id, title=title, interval_days=interval_days)
        if interval_days:
            return f"Added '{task.title}' for {asset.name}, repeating every {interval_days} days."
        return f"Added '{task.title}' for {asset.name} (one-time)."

    @staticmethod
    def _action_list_maintenance_tasks(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_maintenance_tasks`: maintenance tasks with when they're due and the latest reading; a query naming a kind of thing ("vehicle") matches everything of that kind, not only names. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        query = str(arguments.get("query", "") or "").strip().lower()
        # A query that names a kind of thing matches everything of that kind (2026-10-30, live: "vehicle"
        # found nothing because the truck has its own name, and MIA said nothing was overdue).
        category = MAINTENANCE_QUERY_CATEGORIES.get(query.rstrip("s") if query.endswith("s") else query) \
            or MAINTENANCE_QUERY_CATEGORIES.get(query)
        today = date.today()
        lines = []
        for task in context.maintenance.all_tasks():
            asset = context.maintenance.get_asset(task.asset_id)
            asset_name = asset.name if asset is not None else "Unknown asset"
            if category:
                if asset is None or asset.category != category:
                    continue
            elif query and query not in task.title.lower() and query not in asset_name.lower():
                continue

            if task.trigger_type == "calendar":
                remaining = maintenance_days_until_due(task, today)
                if remaining is None:
                    status = "one-time" if task.interval_days is None else "never done"
                elif remaining < 0:
                    status = f"overdue by {-remaining} days"
                elif remaining == 0:
                    status = "due today"
                else:
                    status = f"due in {remaining} days"
            elif task.is_meter_task:
                unit = task.meter_unit or "units"
                readings = context.maintenance.readings_for_task(task.task_id)
                if task.last_completed_meter_value is None:
                    status = "never done"
                elif not readings:
                    status = "no readings logged"
                else:
                    used = meter_used_since_last(task, readings) or 0.0
                    interval = task.meter_interval or 0.0
                    remaining_units = interval - used
                    status = (
                        f"overdue by {-remaining_units:.0f} {unit}"
                        if remaining_units <= 0
                        else f"{used:.0f}/{interval:.0f} {unit} used"
                    )
            elif task.is_sensor_task:
                readings = context.maintenance.readings_for_task(task.task_id)
                if not readings:
                    status = "no readings logged"
                else:
                    latest = readings[-1].value
                    unit = task.meter_unit or ""
                    status = "due" if is_sensor_task_due(task, readings) else f"ok ({latest:g}{unit})"
            else:
                status = "unknown"

            lines.append(f"- {task.title} ({asset_name}): {status}")

        if not lines:
            return "No maintenance tasks match that." if query else "You have no maintenance tasks tracked yet."
        return "Maintenance tasks:\n" + "\n".join(lines)

    @staticmethod
    def _action_complete_maintenance_task(context: AppContext, arguments: dict) -> str:
        """Assistant tool `complete_maintenance_task`: marks a task done (with a meter reading), and a stated cost becomes an expense tagged to the item so it counts in its cost of ownership. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        title = str(arguments.get("title", "") or "").strip()
        asset_name = str(arguments.get("asset_name", "") or "").strip()
        if not title and not asset_name:
            return "Which maintenance task did you finish?"
        task, error = AssistantTools._resolve_maintenance_task_tolerant(context, title, asset_name)
        if error:
            return error
        meter_value = arguments.get("meter_value")
        meter_value = float(meter_value) if meter_value not in (None, "") else None
        context.maintenance.mark_complete(task.task_id, meter_value=meter_value)
        asset = context.maintenance.get_asset(task.asset_id)
        reply = f"Marked '{task.title}' complete" + (f" for {asset.name}." if asset is not None else ".")
        # Finance #2: a stated cost becomes an expense tagged to the item,
        # so it counts toward its cost of ownership (core/homestead_costs.py).
        try:
            cost = float(str(arguments.get("cost") or 0).replace("$", "").replace(",", ""))
        except ValueError:
            cost = 0.0
        if cost > 0 and context.budget is not None:
            context.budget.add_expense(
                amount=cost, category="Maintenance", description=task.title + (f" ({asset.name})" if asset else ""),
                asset_id=task.asset_id,
            )
            reply += f" Logged {money(cost, ',.2f')} toward it."
        return reply

    @staticmethod
    def _action_log_maintenance_reading(context: AppContext, arguments: dict) -> str:
        """Assistant tool `log_maintenance_reading`: logs a reading against a task, or against an item's meter ("120 hours on the mower": its one meter task in that unit, else its own meter). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        title = str(arguments.get("title", "") or "").strip()
        asset_name = str(arguments.get("asset_name", "") or "").strip()
        value = arguments.get("value")
        if value is None:
            return "I need a value to log."
        try:
            value = float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return "That value doesn't look like a number."
        unit = str(arguments.get("unit", "") or "").strip()
        if not title and not asset_name:
            return "Which vehicle or item is that reading for?"

        if not title:
            # "120 hours on the mower": the asset's one meter task in that
            # unit, else the asset's own meter (e.g. "Engine Hours").
            asset, error = resolve_by_name(context.maintenance.all_assets(), asset_name, lambda a: a.name, "tracked item")
            if error:
                return error
            meter_tasks = [
                t for t in context.maintenance.tasks_for_asset(asset.asset_id)
                if t.is_meter_task and (not unit or not t.meter_unit or t.meter_unit.lower().rstrip("s") == unit.lower().rstrip("s"))
            ]
            if len(meter_tasks) == 1:
                task = meter_tasks[0]
            else:
                meter_name = {"hour": "Engine Hours", "mile": "Odometer", "km": "Odometer"}.get(unit.lower().rstrip("s"), unit.title() or "Reading")
                context.maintenance.log_asset_reading(asset.asset_id, meter_name, value, unit=unit)
                return f"Logged {value:g}{(' ' + unit) if unit else ''} on {asset.name}'s {meter_name.lower()}."
        else:
            task, error = AssistantTools._resolve_maintenance_task_tolerant(context, title, asset_name)
            if error:
                return error
        reading = context.maintenance.log_reading(task.task_id, value, unit=unit)
        unit_part = f" {reading.unit}" if reading.unit else ""
        return f"Logged {reading.value:g}{unit_part} for '{task.title}'."

    @staticmethod
    def _action_delete_maintenance_task(context: AppContext, arguments: dict) -> str:
        """Assistant tool `delete_maintenance_task`: deletes a maintenance task, found by title and item. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        title = str(arguments.get("title", "")).strip()
        if not title:
            return "I need a task title to delete."
        task, error = AssistantTools._resolve_maintenance_task(context, title, str(arguments.get("asset_name", "") or "").strip())
        if error:
            return error
        context.maintenance.delete_task(task.task_id)
        return f"Deleted the maintenance task '{task.title}'."

    # ------------------------------------------------------------------
    # Lab (Data Logger) actions
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_lab_series(context: AppContext, requested: str) -> str:
        """Case-insensitive match against existing series names, reusing
        the exact stored id if one matches — so 'Soil Moisture' and
        'soil moisture' don't silently fragment into two series. Falls
        back to the requested string verbatim when nothing matches yet
        (a brand-new series, created implicitly on first reading — same
        "no separate series-registry file" convention as
        core.data_logger_manager's own design)."""
        canonical = next((s for s in context.data_logger.list_series() if s.lower() == requested.lower()), None)
        return canonical or requested

    @staticmethod
    def _action_log_lab_reading(context: AppContext, arguments: dict) -> str:
        """Assistant tool `log_lab_reading`: logs a numeric reading to a Data Logger series. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        series = str(arguments.get("series", "")).strip()
        if not series:
            return "I need a series name to log a reading under."
        value = arguments.get("value")
        if value is None:
            return "I need a value to log."
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "That value doesn't look like a number."
        series = AssistantTools._resolve_lab_series(context, series)
        unit = str(arguments.get("unit", "") or "")
        note = str(arguments.get("note", "") or "")
        reading = context.data_logger.add_reading(series_id=series, value=value, unit=unit, note=note)
        unit_part = f" {reading.unit}" if reading.unit else ""
        return f"Logged {reading.value:g}{unit_part} to '{series}'."

    @staticmethod
    def _action_list_lab_series(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_lab_series`: the Data Logger's series. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        series = context.data_logger.list_series()
        if not series:
            return "You have no Data Logger series yet."
        return "Data Logger series:\n" + "\n".join(f"- {s}" for s in series)

    @staticmethod
    def _action_list_lab_readings(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_lab_readings`: the readings in a Data Logger series. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        series = str(arguments.get("series", "")).strip()
        if not series:
            return "I need a series name to list readings for."
        series = AssistantTools._resolve_lab_series(context, series)
        readings = context.data_logger.readings_for(series)
        if not readings:
            return f"No readings logged for '{series}' yet."
        lines = [
            f"- {r.timestamp}: {r.value:g}" + (f" {r.unit}" if r.unit else "") + (f" — {r.note}" if r.note else "")
            for r in readings
        ]
        return f"Readings for '{series}':\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # Budget actions
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_bill(context: AppContext, name: str) -> tuple[Optional[Bill], Optional[str]]:
        """Exact case-insensitive name match — never fuzzy, same
        fail-closed discipline as _resolve_maintenance_task above."""
        match = next((b for b in context.budget.all_bills() if b.name.lower() == name.lower()), None)
        if match is None:
            return None, f"I don't have a bill called '{name}'."
        return match, None

    @staticmethod
    def _action_add_bill(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_bill`: adds a bill with an amount, due date, category and recurrence. Returns the reply in words (a missing or unknown name says so, nothing changes).
        Never added with no amount, a generic name ("bill reminders") or a day that doesn't read."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a bill."
        amount = arguments.get("amount")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0:  # the live sweep, 2026-11-25: "Can you automate my bill reminders?" had added a $0.00 bill
            return "I need the bill's amount to add it."
        import re

        if re.fullmatch(r"(?:the\s+|my\s+)?(?:bills?|bill reminders?|reminders?|payments?)", name, re.I):
            return "Which bill? Say its name, amount and due day, like \"add my electric bill, $120, due the 15th\"."
        due_date = str(arguments.get("due_date", "") or "").strip()
        from core.budget_manager import read_date

        due_date = read_date(due_date) or ""
        if not due_date:
            return "When is it due? Say a date, like 2026-12-15 or \"December 15\"."
        category = str(arguments.get("category", "") or "Utilities").strip()
        recurrence = str(arguments.get("recurrence", "") or "").strip().lower() or None
        bill = context.budget.add_bill(
            name=name, amount=float(amount), due_date=due_date, category=category, recurrence=recurrence,
        )
        recurrence_part = f", repeating {bill.recurrence}" if bill.recurrence else ""
        return f"Bill '{bill.name}' added for {money(bill.amount, '.2f')} due {bill.due_date}{recurrence_part}."

    @staticmethod
    def _action_list_bills(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_bills`: every bill with amount, category and whether it's paid, overdue, due today or due in N days. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        bills = context.budget.all_bills()
        if not bills:
            return "You have no bills tracked."
        today = date.today()
        lines = []
        for bill in bills:
            remaining = days_until_bill_due(bill, today)
            if remaining is None:
                status = "paid"
            elif remaining < 0:
                status = f"overdue by {-remaining} days"
            elif remaining == 0:
                status = "due today"
            else:
                status = f"due in {remaining} days"
            lines.append(f"- {bill.name} ({money(bill.amount, '.2f')}, {bill.category}): {status}")
        return "Your bills:\n" + "\n".join(lines)

    @staticmethod
    def _action_mark_bill_paid(context: AppContext, arguments: dict) -> str:
        """Assistant tool `mark_bill_paid`: marks a bill paid, recording the payment (the amount given, or the bill's). Returns the reply in words (a missing or unknown name says so, nothing changes).
        A zero amount is the bill's own, never a $0.00 payment."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a bill name to mark paid."
        bill, error = AssistantTools._resolve_bill(context, name)
        if error:
            return error
        amount = arguments.get("amount")
        try:
            amount = float(amount) if amount not in (None, "") else None
        except (TypeError, ValueError):
            amount = None
        if amount is not None and amount <= 0:
            amount = None  # a zero paid is the bill's own amount, never a $0.00 payment (the Fable audit)
        entry = context.budget.mark_bill_paid(bill.bill_id, amount=amount)
        return f"Marked '{bill.name}' paid — recorded {money(entry.amount, '.2f')}."

    @staticmethod
    def _action_add_income(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_income`: records income with a category and date. Returns the reply in words (a missing or unknown name says so, nothing changes).
        A day other than today is said in the reply.
        A day said that doesn't read is asked, never today in its place.
        A zero or missing amount asks, never $0.00 saved."""
        amount = arguments.get("amount")
        try:
            amount = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amount = None
        if not amount or amount <= 0:  # never $0.00 (the Fable audit)
            return "I need an amount to record income."
        category = str(arguments.get("category", "") or "Other").strip()
        description = str(arguments.get("description", "") or "")
        date_str = str(arguments.get("date", "") or "").strip() or None
        from core.budget_manager import read_date

        if date_str and date_str.lower() not in ("null", "none", "today", "now") and not read_date(date_str):
            return ("Which day was that? Say a date like 2026-11-20, \"yesterday\" or \"last Friday\", and I'll "
                    "record it.")  # never today in its place, unsaid (the Fable review, 2026-11-25)
        entry = context.budget.add_income(amount=float(amount), category=category, description=description, date=date_str)
        from core.budget_manager import _today_iso

        on = "" if entry.date == _today_iso() else f" on {entry.date}"
        return f"Recorded {money(entry.amount, '.2f')} of income ({entry.category}){on}."

    @staticmethod
    def _action_add_expense(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_expense`: records an expense with a category and date. Returns the reply in words (a missing or unknown name says so, nothing changes).
        A day other than today is said in the reply.
        A day said that doesn't read is asked, never today in its place.
        A zero or missing amount asks, never $0.00 saved."""
        amount = arguments.get("amount")
        try:
            amount = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amount = None
        if not amount or amount <= 0:  # never $0.00 (the Fable audit)
            return "I need an amount to record an expense."
        category = str(arguments.get("category", "") or "Other").strip()
        description = str(arguments.get("description", "") or "")
        date_str = str(arguments.get("date", "") or "").strip() or None
        from core.budget_manager import read_date

        if date_str and date_str.lower() not in ("null", "none", "today", "now") and not read_date(date_str):
            return ("Which day was that? Say a date like 2026-11-20, \"yesterday\" or \"last Friday\", and I'll "
                    "record it.")  # never today in its place, unsaid (the Fable review, 2026-11-25)
        entry = context.budget.add_expense(amount=float(amount), category=category, description=description, date=date_str)
        from core.budget_manager import _today_iso

        on = "" if entry.date == _today_iso() else f" on {entry.date}"  # a day other than today, said
        return f"Recorded {money(entry.amount, '.2f')} expense ({entry.category}){on}."

    @staticmethod
    def _action_get_budget_summary(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_budget_summary`: income, expenses and net for a date range, plus the tax-relevant totals. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        start_date = str(arguments.get("start_date", "") or "").strip() or None
        end_date = str(arguments.get("end_date", "") or "").strip() or None
        income = context.budget.total_income(start_date, end_date)
        expenses = context.budget.total_expenses(start_date, end_date)
        tax_income = context.budget.total_income(start_date, end_date, tax_relevant_only=True)
        tax_expenses = context.budget.total_expenses(start_date, end_date, tax_relevant_only=True)
        return (
            f"Income: {money(income, ',.2f')}. Expenses: {money(expenses, ',.2f')}. Net: {money(income - expenses, ',.2f')}. "
            f"Tax-relevant income: {money(tax_income, ',.2f')}. Tax-relevant (deductible) expenses: {money(tax_expenses, ',.2f')}."
        )

    @staticmethod
    def _resolve_income_source(context: AppContext, name: str) -> tuple[Optional[IncomeSource], Optional[str]]:
        """Exact case-insensitive name match — never fuzzy, same
        fail-closed discipline as _resolve_bill above."""
        match = next((s for s in context.budget.all_income_sources() if s.name.lower() == name.lower()), None)
        if match is None:
            return None, f"I don't have an income source called '{name}'."
        return match, None

    @staticmethod
    def _action_add_income_source(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_income_source`: adds an expected income source (amount, next date, recurrence). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add an income source."
        expected_amount = arguments.get("expected_amount")
        if expected_amount is None:
            return "I need an expected amount to add an income source."
        next_date = str(arguments.get("next_date", "") or "").strip()
        if not next_date:
            return "I need a next expected date (YYYY-MM-DD) to add an income source."
        category = str(arguments.get("category", "") or "Salary").strip()
        recurrence = str(arguments.get("recurrence", "") or "").strip().lower() or None
        source = context.budget.add_income_source(
            name=name, expected_amount=float(expected_amount), next_date=next_date, category=category, recurrence=recurrence,
        )
        recurrence_part = f", repeating {source.recurrence}" if source.recurrence else ""
        return f"Income source '{source.name}' added — {money(source.expected_amount, '.2f')} expected {source.next_date}{recurrence_part}."

    @staticmethod
    def _action_mark_income_received(context: AppContext, arguments: dict) -> str:
        """Assistant tool `mark_income_received`: marks an income source received, recording it. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need an income source name to mark received."
        source, error = AssistantTools._resolve_income_source(context, name)
        if error:
            return error
        amount = arguments.get("amount")
        amount = float(amount) if amount not in (None, "") else None
        entry = context.budget.mark_income_received(source.source_id, amount=amount)
        return f"Marked '{source.name}' received — recorded {money(entry.amount, '.2f')}."

    @staticmethod
    def _action_get_financial_checkin(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_financial_checkin`: this month's budget check-in: overdue and due-soon bills, expected income, categories over budget. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        today = date.today()
        bills = context.budget.all_bills()
        income_sources = context.budget.all_income_sources()
        targets = context.budget.all_budget_targets()
        month_start = today.replace(day=1).isoformat()
        actual_by_category = context.budget.total_expenses_by_category(month_start, None)
        message = build_nudge_message(bills, income_sources, targets, actual_by_category, today)
        return message or "Everything looks on track — no overdue bills, nothing due soon, and no categories over budget."

    # ------------------------------------------------------------------
    # Real Estate actions
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_property(context: AppContext, name: str) -> tuple[Optional[Property], Optional[str]]:
        """Exact case-insensitive name match — never fuzzy, same
        fail-closed discipline as every other name-resolution action
        this session."""
        match = next((p for p in context.real_estate.all_properties() if p.name.lower() == name.lower()), None)
        if match is None:
            return None, f"I don't have a property called '{name}'."
        return match, None

    @staticmethod
    def _action_add_property(context: AppContext, arguments: dict) -> str:
        """Assistant tool `add_property`: adds a property with type, value and mortgage balance. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        name = str(arguments.get("name", "")).strip()
        if not name:
            return "I need a name to add a property."
        property_type = str(arguments.get("property_type", "") or "Rental").strip()
        current_value = arguments.get("current_value")
        mortgage_balance = arguments.get("mortgage_balance")
        prop = context.real_estate.add_property(
            name=name,
            property_type=property_type,
            current_value=float(current_value) if current_value not in (None, "") else 0.0,
            mortgage_balance=float(mortgage_balance) if mortgage_balance not in (None, "") else 0.0,
        )
        return f"Property '{prop.name}' added ({prop.property_type})."

    @staticmethod
    def _action_list_properties(context: AppContext, arguments: dict) -> str:
        """Assistant tool `list_properties`: the properties tracked. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        properties = context.real_estate.all_properties()
        if not properties:
            return "You have no properties tracked."
        lines = [f"- {p.name} ({p.property_type}): {money(property_equity(p), ',.2f')} equity" for p in properties]
        return "Your properties:\n" + "\n".join(lines)

    @staticmethod
    def _action_record_rental_income(context: AppContext, arguments: dict) -> str:
        """Assistant tool `record_rental_income`: records rent received for a property. Returns the reply in words (a missing or unknown name says so, nothing changes).
        A zero or missing amount asks, never $0.00 saved."""
        property_name = str(arguments.get("property_name", "")).strip()
        if not property_name:
            return "I need a property name to record rental income."
        amount = arguments.get("amount")
        try:
            amount = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amount = None
        if not amount or amount <= 0:  # never $0.00 (the Fable audit)
            return "I need an amount to record rental income."
        prop, error = AssistantTools._resolve_property(context, property_name)
        if error:
            return error
        date_str = str(arguments.get("date", "") or "").strip() or None
        entry = context.real_estate.record_rental_income(prop.property_id, amount=float(amount), date_str=date_str)
        return f"Recorded {money(entry.amount, '.2f')} rental income for '{prop.name}'."

    @staticmethod
    def _action_record_property_sale(context: AppContext, arguments: dict) -> str:
        """Assistant tool `record_property_sale`: records a property as sold (price, costs, date) through the Real
        Estate page's own `property.sell`, and says it's recorded and what it comes to (the cash after the mortgage
        and the gain: estimates, never tax figures). Returns the reply in words (a missing or unknown name, a price
        that isn't a number, or a property already sold says so, nothing changes)."""
        from core.actions import ACTION_TYPES

        property_name = str(arguments.get("property_name", "")).strip()
        if not property_name:
            return "I need the property's name to record its sale."
        try:
            price = float(arguments.get("sale_price") or 0)
            costs = float(arguments.get("selling_costs") or 0)
        except (TypeError, ValueError):
            return "I need the sale price as a number."
        prop, error = AssistantTools._resolve_property(context, property_name)
        if error:
            return error
        kind = ACTION_TYPES["property.sell"]
        params = {"property_id": prop.property_id, "price": price, "selling_costs": costs,
                  "date": str(arguments.get("date") or "").strip()}
        try:
            figures = kind.describe(context, params).split(": ", 1)[-1]
            return f"{kind.execute(context, params)} {figures}"
        except ValueError as problem:  # ActionError is one
            return str(problem)

    @staticmethod
    def _action_get_property_summary(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_property_summary`: a property's net operating income and cap rate. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        property_name = str(arguments.get("property_name", "")).strip()
        if not property_name:
            return "I need a property name."
        prop, error = AssistantTools._resolve_property(context, property_name)
        if error:
            return error
        noi = context.real_estate.net_operating_income(prop.property_id)
        cap_rate = context.real_estate.cap_rate(prop.property_id)
        cap_rate_text = f"{cap_rate * 100:.2f}%" if cap_rate is not None else "n/a (no current value set)"
        return (
            f"'{prop.name}': equity {money(property_equity(prop), ',.2f')}, "
            f"net operating income {money(noi, ',.2f')}, cap rate {cap_rate_text}."
        )

    @staticmethod
    def _action_play_track(context: AppContext, arguments: dict) -> str:
        """Assistant tool `play_track`: plays the first song matching a title or artist. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        track_name = str(arguments.get("track_name", "")).strip()
        if not track_name:
            return "I need a song or artist name to play."
        matches = context.music.search_tracks(track_name)
        if not matches:
            return f"I couldn't find a song matching '{track_name}'."
        track = matches[0]
        context.music.play_track(track.track_id)
        artist_part = f" by {track.artist}" if track.artist else ""
        return f"Playing '{track.title}'{artist_part}."

    @staticmethod
    def _action_play_playlist(context: AppContext, arguments: dict) -> str:
        """Assistant tool `play_playlist`: plays a playlist by name (an empty one says so). Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        playlist_name = str(arguments.get("playlist_name", "")).strip()
        if not playlist_name:
            return "I need a playlist name to play."
        playlist = next(
            (p for p in context.music.all_playlists() if p.name.lower() == playlist_name.lower()), None
        )
        if playlist is None:
            return f"I couldn't find a playlist called '{playlist_name}'."
        if not context.music.play_playlist(playlist.playlist_id):
            return f"'{playlist.name}' doesn't have any tracks yet."
        return f"Playing playlist '{playlist.name}'."

    @staticmethod
    def _action_pause_music(context: AppContext, arguments: dict) -> str:
        """Assistant tool `pause_music`: pauses the music. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        context.music.pause()
        return "Paused."

    @staticmethod
    def _action_resume_music(context: AppContext, arguments: dict) -> str:
        """Assistant tool `resume_music`: resumes the music. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        context.music.resume()
        return "Resumed."

    @staticmethod
    def _action_stop_music(context: AppContext, arguments: dict) -> str:
        """Assistant tool `stop_music`: stops the music. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        context.music.stop()
        return "Stopped."

    @staticmethod
    def _action_next_track(context: AppContext, arguments: dict) -> str:
        """Assistant tool `next_track`: skips to the next track in the queue. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        if not context.music.next_track():
            return "There's no next track in the queue."
        now_playing = context.music.now_playing()
        return f"Now playing '{now_playing.title}'." if now_playing else "Skipped."

    @staticmethod
    def _action_previous_track(context: AppContext, arguments: dict) -> str:
        """Assistant tool `previous_track`: goes back a track. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        if not context.music.previous_track():
            return "There's no previous track in the queue."
        now_playing = context.music.now_playing()
        return f"Now playing '{now_playing.title}'." if now_playing else "Went back a track."

    @staticmethod
    def _action_set_music_volume(context: AppContext, arguments: dict) -> str:
        """Assistant tool `set_music_volume`: sets the music volume percent. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        percent = arguments.get("percent")
        if percent is None:
            return "I need a volume percent."
        percent = max(0, min(100, int(percent)))
        context.music.set_volume(percent)
        return f"Music volume set to {percent}%."

    @staticmethod
    def _action_get_now_playing(context: AppContext, arguments: dict) -> str:
        """Assistant tool `get_now_playing`: what's playing (or paused): title and artist. Returns the reply in words (a missing or unknown name says so, nothing changes)."""
        now_playing = context.music.now_playing()
        if now_playing is None:
            return "Nothing is currently playing."
        artist_part = f" by {now_playing.artist}" if now_playing.artist else ""
        state = "Playing" if now_playing.is_playing else "Paused"
        return f"{state}: '{now_playing.title}'{artist_part}."
