"""
core.retention
==============

The retention registry (DEC-0286, LS-03): one table of every data file MIA keeps, with its class, how long it's
kept, what happens at its end, and whether sync carries it. Sync reads it (`core/sync.syncable`), and
`tests/test_retention.py` fails on a `.json` or `.jsonl` file named in core/ or modules/ that isn't here.

**Classes.**
- `record`: his or his household's own records, kept until he removes them;
- `log`: an account of what happened, appended, kept or trimmed as its store says;
- `derived`: worked out from his records and rebuilt when they change;
- `device`: belongs to the device it's on (a pairing, a camera, this machine's usage), never synced;
- `mia`: MIA's own working records (her lab, her reviews, her lessons), kept beside her code;
- `config`: settings.

`syncs` says whether sync carries the file when it sits in a person's or household's folder; files kept anywhere
else never reach sync. A device's own files and anything derived from records on one device never sync
(REQ-DST-011). Pure data: nothing here reads or writes a file.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Retention:
    """One data file's place: its class, how long it's kept, what happens at the end, whether sync carries it."""
    cls: str
    keep: str
    end: str
    syncs: bool


CLASSES = ("record", "log", "derived", "device", "mia", "config")

_RECORD = ("until he removes it", "deleted when he removes it or erases his account")
_LOG = ("for as long as the account", "erased with the account")
_DERIVED = ("rebuilt from his records", "rebuilt or dropped; nothing is lost")
_DEVICE = ("on this device", "removed with this device's data")
_MIA = ("beside her code", "kept in her history")


def _many(names: str, cls: str, keep_end: tuple, syncs: bool) -> dict:
    """Pure logic. One class's files, from a space-separated list of names."""
    return {name: Retention(cls, keep_end[0], keep_end[1], syncs) for name in names.split()}


REGISTRY: dict[str, Retention] = {
    **_many("""alarms.json art.json bills.json boss_battles.json boss_book.json browser_routines.json
        budget_expenses.json budget_targets.json business.json business_entities.json business_use.json
        calendar_events.json classroom_courses.json classroom_lessons.json classroom_subjects.json components.json
        connections.json conversations.json cooking_session.json craft_recipes.json creations.json debts.json
        directions.json email_drafts.json energy_sources.json expeditions.json expenses.json fitness.json flock.json
        gps_tracks.json grow_lab.json health.json id_wallet.json inbox.json income.json income_sources.json
        insurance.json intents.json inventory_items.json jobs.json journal_entries.json kitchen.json
        kitchen_grocery_list.json kitchen_meal_log.json kitchen_pantry.json kitchen_recipe_user_stats.json
        kitchen_recipes.json life_notes.json links.json living_worlds.json loop.json maintenance.json materials.json
        mission_pathways.json missions.json music_playlists.json music_tracks.json obligations.json
        online_reminders.json operating_journal.json password_vault.json paths.json pathway_progress.json places.json
        plans.json private_journal.json private_journal_keys.json products.json profile.json projects.json
        properties.json questlines.json record_sets.json recreation.json recurring_mission_templates.json
        relationships_people.json relationships_pets.json response_styles.json revenue.json reward_shop.json
        saga_moments.json scripts.json seasons.json sensors.json shelf.json skill_definitions.json
        skill_progress.json smart_closet.json step_plans.json project_plans.json tasks.json taught_skills.json teamwork.json
        textbooks.json trade_session.json trail_maps.json training_session.json trips.json user_memories.json
        vocab.json waypoints.json why_checkpoints.json work_dungeon.json workout_exercises.json
        workout_sessions.json workout_templates.json world_map.json game.json good_news_following.json
        data_logger_readings.json mission_proposals.json capture_proposals.json decided.json
        requirements.json homestead_snapshots.json part_specs.json bench_builds.json condition_watches.json""",
            "record", _RECORD, True),
    **_many("""life_events.jsonl inbox_reading.jsonl corrections.jsonl memory_corrections.jsonl sureness.jsonl
        skill_xp_log.json component_usage_log.json inventory_usage_log.json material_usage_log.json
        product_usage_log.json freedom_log.json maker_log.jsonl failures.jsonl sight_log.jsonl answer_ratings.json
        notifications.json insights.json recommendations.json good_news_heard.json net_worth_history.json
        financial_snapshots.json projections.jsonl inbox_mail_state.json failure_log.json failure_state.json
        security_log.jsonl capability_gaps.json""",
            "log", _LOG, True),
    **_many("""meaning.json world_intel.json price_observations.json""", "derived", _DERIVED, True),
    **_many("""security_cameras.json security_logins.json activity_log.json communication_log.json
        model_bench_cases.json push_subscriptions.json memory_vault.json activity.json recall_index.json runs.json
        turn_traces.jsonl phone_link.json module_usage.json page_usage.json vapid_keys.json update_manifest.json
        auth.json data_key.json greenhouse_link.json dashboard_state.json status.json youtube_key.json
        files.json manifest.json index.json card.json conversation_cases.json engineering_bench.json
        user_sync_cases.json changes.jsonl capability_states.json queue.json""",
            "device", _DEVICE, False),
    **_many("""activity.jsonl agents.json council.jsonl doc_baseline.json inspections.json known_failures.json
        loop_coverage.json night_school.json parity.json review_lessons.json
        dependency_audit.json own_proposals.json self_merges.json self_repairs.json proposals.json""",
            "mia", _MIA, False),
    **_many("config.json default_config.json", "config", ("until changed", "reset to the defaults"), False),
}

# What the stores themselves trim, said as it is in their code.
_TRIMMED = {
    "changes.jsonl": ("30 days (core/change_history.KEEP_DAYS)", "pruned, with the bytes it kept"),
    "activity.json": ("7 days (core/activity_watch.KEEP_DAYS)", "pruned; erased at once on his say"),
    "price_observations.json": ("730 days (core/price_book.KEEP_DAYS)", "pruned"),
    "world_intel.json": ("90 days unless saved (core/world_intel.KEEP_DAYS)", "let go"),
    "runs.json": ("the newest 200 finished runs (core/runs.KEEP_DONE)", "trimmed"),
    "security_log.jsonl": ("the newest 5000 events (core/security_log.KEEP)", "trimmed"),
    "turn_traces.jsonl": ("the newest 2000 turns (core/turn_trace.MAX_KEPT)", "trimmed"),
    "failure_log.json": ("about the newest 5000 lines (core/failure_log)", "trimmed"),
    "communication_log.json": ("30 days (core/communication_gate)", "trimmed"),
    "recall_index.json": ("rebuilt from his records on this device", "rebuilt; dropped refs leave at once"),
}
for _name, (_keep, _end) in _TRIMMED.items():
    _old = REGISTRY[_name]
    REGISTRY[_name] = Retention(_old.cls, _keep, _end, _old.syncs)

_warned: set = set()


def syncs(name: str) -> bool:
    """Whether sync carries a data file of this name. One the registry doesn't know syncs as before (a file from an
    older MIA), said once in the log; the test keeps every file MIA names in the registry."""
    found = REGISTRY.get(name)
    if found is not None:
        return found.syncs
    if name not in _warned:
        _warned.add(name)
        log.info("%s isn't in the retention registry; it syncs as before.", name)
    return True


def of(name: str) -> Retention | None:
    """A data file's place in the registry, or None when it isn't listed."""
    return REGISTRY.get(name)
