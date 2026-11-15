"""
tests.test_living_system
==========================

The Living System doctrine's invariants that had no test yet (DEC-0173, `docs/mia_os/MIA_OS_LIVING_SYSTEM.md`
section 8):
- **Identity:** MIA's identity is written in one place (core/personality.py). The files that already frame a task
  prompt as "You are MIA" in their own words are listed here and may only shrink; a new one fails.
- **Continuity across models:** what MIA knows and assembles for a turn lives outside any model: switching the model
  backend changes neither the stores nor the assembled life state.
- **Knowledge:** every store created from now on declares the epistemic contract (`EPISTEMIC`: its record, where each
  record came from, when, how it's known: said, observed, inferred or computed, and when last checked). The stores
  that existed before the doctrine are listed and may only shrink, as each is brought under it.
"""

import dataclasses
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# The files that already say "You are MIA" in their own words (2026-11-15). Each is a task framing consistent with
# core/personality.IDENTITY; bringing one under personality.py takes it off this list. Never add to it.
OWN_WORDS_BASELINE = frozenset({
    "core/assistant_chat.py", "core/conversation_export.py", "core/council_floor.py", "core/discovery_manager.py",
    "core/response_composer.py", "core/ual.py",
})
_IDENTITY_LINE = re.compile(r"You(?: are|'re) MIA\b(?!'s)")

# The stores that existed before the epistemic contract (2026-11-15). Bring one under it (an EPISTEMIC declaration)
# and take it off; never add to it.
EPISTEMIC_BASELINE = frozenset({
    "alarms", "art", "boss_book", "browser_routines", "budget", "business", "business_use", "calendar", "classroom",
    "closet", "communication", "components", "connections", "conversations", "cooking", "craft_recipes", "creations",
    "data_logger", "direction", "dungeon", "email_drafts", "energy", "expeditions", "failures", "finance", "fitness",
    "flock", "freedom_log", "gps_tracks", "grow_lab", "health", "homestead", "id_wallet", "inbox", "insights",
    "insurance", "intents", "inventory", "jobs", "journal", "kitchen", "ledger", "life_events", "life_notes", "links",
    "lite_captures", "living_worlds", "loop", "maintenance", "materials", "memory_vault", "my_record_sets",
    "net_worth", "notifications", "obligations", "online_reminders", "operating_journal", "passwords", "paths",
    "personal_life_events", "places", "plaid", "plans", "private_journal", "products", "projects", "quest_book",
    "ratings", "real_estate", "record_sets", "recreation", "relationships", "response_style", "reward_shop",
    "saga_moments", "scripts", "security", "tasks", "taught_skills", "textbooks", "traces", "trade_session",
    "training", "trips", "user_memories", "waypoints", "workout", "world_map",
})
HOW = ("said", "observed", "inferred", "computed")


def test_no_new_file_gives_mia_an_identity_of_her_own_beyond_personality():
    found = set()
    for folder in ("core", "server", "modules", "gui", "tools"):
        for path in (ROOT / folder).rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if rel != "core/personality.py" and _IDENTITY_LINE.search(path.read_text(encoding="utf-8")):
                found.add(rel)
    new = found - OWN_WORDS_BASELINE
    assert not new, f"Take MIA's identity from core/personality.py (IDENTITY), not your own words: {sorted(new)}"
    gone = OWN_WORDS_BASELINE - found
    assert not gone, f"These no longer state an identity of their own: take them off OWN_WORDS_BASELINE: {sorted(gone)}"


def test_every_store_created_since_the_doctrine_declares_where_its_facts_come_from():
    import core.actions  # noqa: F401  (the action contract first, as MIA loads it)
    from core.personal_data import HOUSEHOLD_STORES, PERSONAL_STORES

    stores = dict(PERSONAL_STORES + HOUSEHOLD_STORES)
    missing, wrong = [], []
    for name, cls in stores.items():
        contract = getattr(cls, "EPISTEMIC", None)
        if contract is None:
            if name not in EPISTEMIC_BASELINE:
                missing.append(name)
            continue
        record = contract.get("record")
        fields = {f.name for f in dataclasses.fields(record)} if dataclasses.is_dataclass(record) else set()
        for key in ("source", "at"):
            if contract.get(key) not in fields:
                wrong.append(f"{name}: {key}")
        how = contract.get("how")
        if how not in HOW and how not in fields:
            wrong.append(f"{name}: how")
        if contract.get("checked") and contract["checked"] not in fields:
            wrong.append(f"{name}: checked")
    assert not missing, f"New stores declare EPISTEMIC (DEC-0173, G3): {missing}"
    assert not wrong, f"EPISTEMIC names fields its record doesn't have: {wrong}"
    under = {n for n, c in stores.items() if getattr(c, "EPISTEMIC", None) is not None}
    assert not (under & EPISTEMIC_BASELINE), f"Now under the contract: take off EPISTEMIC_BASELINE: {under & EPISTEMIC_BASELINE}"


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The test household, with a goal, a project and a workout, for the life state."""
    from tests.engine_world import build_world

    context = build_world(tmp_path, monkeypatch)
    goal = context.intents.add_intent("Grow our own food", primary=True)
    context.projects.add_project("Greenhouse", intent_id=goal.intent_id)
    context.workout.add_session(duration_minutes=30)
    return context


def _snapshot(folder: Path) -> dict:
    """Every file under a folder with its bytes."""
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def test_switching_the_model_changes_neither_what_mia_knows_nor_what_she_assembles(world, tmp_path):
    from datetime import date

    from core.context_assembler import assemble_life_state_v2

    day = date(2026, 11, 15)
    world.config.set("llm.backend", "ollama")
    before, files = assemble_life_state_v2(world, day), _snapshot(tmp_path / "household")
    world.config.set("llm.backend", "openai")  # llama.cpp's server, as on the phone
    after = assemble_life_state_v2(world, day)
    assert before == after
    assert _snapshot(tmp_path / "household") == files
    source = (ROOT / "core" / "context_assembler.py").read_text(encoding="utf-8")
    assert "llm_manager" not in source and "context.llm" not in source  # assembled by code, not by a model
