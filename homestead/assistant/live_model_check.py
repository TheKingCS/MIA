"""
MIA Homestead — Live Local-Model Golden Set
v0.1

Step 5 of docs/OFFLINE_ASSISTANT_PLAN.md: nothing proves the assistant's
tool-calling accuracy against a real (local) model the way
scenarios/scenarios.py proves the control loop's safety behavior. This is
that harness — same spirit as the sibling M.I.A. project's
tests/live_model_check.py, adapted to this system's own tools and domains.

Every case runs against a FRESH, isolated temp-file SQLite DB (never the
real mia_homestead.db) — same isolation discipline this project's own
history says matters: a scratch verification script that touches real
data has caused real pollution before, elsewhere in this project's sibling
codebase. Several of the cases are direct regressions for real bugs found
while building the local-model backend (2026-08-26, see
docs/OFFLINE_ASSISTANT_PLAN.md steps 4-5): the "attach everything on
ambiguous input" fallback that broke llama3.2:3b's tool-calling entirely,
and a fabrication bug where the model invented numbers lifted verbatim
from PERSONALITY.md's own example text instead of reporting that no data
existed — fixed centrally via GreenhouseAssistant._annotate_if_empty()
rather than per-tool, since the same pattern reproduced on more than one
tool.

Grading is deliberately modest for a first pass, matching this project's
own established lesson that live-model behavior needs iterative tuning,
not one perfect pass: did AT LEAST ONE of the expected tools get called
(proves grounding actually happened, not a skipped-tool invented answer),
and — where specified — do none of a case's forbidden substrings appear
in the final answer (the direct fabrication regression check).

Usage:
    python assistant/live_model_check.py                    # all cases
    python assistant/live_model_check.py --only status_empty
    python assistant/live_model_check.py --model qwen2.5:7b  # re-run the
                                                               # bake-off
"""

import argparse
import json
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.species_registry import SpeciesRegistry  # noqa: E402
from core.backup_manager import BackupManager  # noqa: E402
from drivers.simulator import Simulator, setup_demo_cell  # noqa: E402
from assistant.greenhouse_assistant import OLLAMA_MODEL, GreenhouseAssistant  # noqa: E402

SCHEMA_PATH = ROOT / "schema" / "mia_homestead_schema.sql"


@dataclass
class GoldenCase:
    name: str
    question: str
    expected_tools: set[str]
    forbidden_substrings: list[str] = field(default_factory=list)
    extra_setup: "callable" = None  # optional: fn(conn, cell_id) -> None, run after base seeding
    base_ticks: int = 3  # simulator ticks before this case runs; 0 = genuinely empty sensor_readings


def _base_seed(conn: sqlite3.Connection, ticks: int = 3) -> int:
    """Schema + demo cell + a few simulator ticks (real sensor_readings)
    + baseline species — the shared starting state every case builds on.
    Everything else (inventory, maintenance, experiments, devices,
    backups, help_requests, revenue, dosing, yield/planting) is
    deliberately left empty — that's this project's actual current real
    state, not a contrived test fixture, and exercises the "no data yet"
    grounding path the step-4 bug was found in."""
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    sim = Simulator(conn)
    for _ in range(ticks):
        sim.tick()
    SpeciesRegistry(conn)  # seeds lettuce/basil/tilapia baseline profiles
    return cell_id


def _seed_one_planting(conn: sqlite3.Connection, cell_id: int) -> None:
    row = conn.execute("SELECT id FROM species_profiles WHERE common_name = 'Lettuce'").fetchone()
    conn.execute(
        "INSERT INTO bed_plantings (grow_bed_name, cell_id, species_id) VALUES (?, ?, ?)",
        ("Bed A1", cell_id, row[0]),
    )
    conn.commit()


def _seed_one_snapshot(conn: sqlite3.Connection, cell_id: int) -> None:
    BackupManager(conn).create_snapshot("golden_set_test_snapshot", reason="live_model_check.py seed")


GOLDEN_CASES: list[GoldenCase] = [
    # --- status: the exact step-4 regression, empty data must not fabricate ---
    GoldenCase(
        name="status_empty_no_fabrication",
        question="How is everything looking?",
        expected_tools={"get_current_status", "get_open_alerts", "get_greenhouse_report"},
        # The exact numbers llama3.2:3b fabricated from PERSONALITY.md's
        # own example text before the _system_prompt() fix — this is a
        # direct regression test for that specific bug, not a generic check.
        # base_ticks=0 is load-bearing here: this case must see genuinely
        # empty sensor_readings, or it's silently testing the wrong thing
        # (real-data reporting, not fabrication avoidance) — caught this
        # exact mistake in the first draft, see plan doc step 5 notes.
        forbidden_substrings=["6.9", "740", "68%"],
        base_ticks=0,
    ),
    GoldenCase(
        name="status_current_reading",
        question="What's the current pH reading?",
        expected_tools={"get_current_status"},
    ),
    # --- dosing: empty by default in the base seed ---
    GoldenCase(
        name="dosing_history_empty",
        question="Has it been dosing much lately?",
        expected_tools={"get_dosing_history", "get_dosing_rationale"},
    ),
    # --- yield_planting: one empty case, one seeded-positive case ---
    GoldenCase(
        name="yield_empty",
        question="What's my yield looking like?",
        expected_tools={"get_yield_summary"},
    ),
    GoldenCase(
        name="bed_plantings_seeded",
        question="What's planted in Cell A?",
        expected_tools={"get_bed_plantings"},
        extra_setup=_seed_one_planting,
    ),
    # --- species: always has real baseline data from _base_seed ---
    GoldenCase(
        name="species_lettuce_ph",
        question="What pH does lettuce want?",
        expected_tools={"get_species_profile", "list_species"},
    ),
    # --- experiments: empty ---
    GoldenCase(
        name="experiments_empty",
        question="Any experiments running right now?",
        expected_tools={"get_active_experiments"},
    ),
    # --- inventory: empty ---
    GoldenCase(
        name="inventory_low_stock_empty",
        question="What's low on stock?",
        expected_tools={"get_low_stock_items", "get_inventory_status"},
    ),
    # --- maintenance: empty ---
    GoldenCase(
        name="maintenance_open_tasks_empty",
        question="Any open repair tasks?",
        expected_tools={"get_open_maintenance_tasks"},
    ),
    # --- infrastructure: always real, comes from config YAML not the DB ---
    GoldenCase(
        name="infrastructure_wiring",
        question="How is the pH-up pump wired?",
        expected_tools={"get_wiring_info"},
    ),
    # --- multi-domain: dosing + infrastructure, the pump example from PERSONALITY.md ---
    GoldenCase(
        name="dosing_infrastructure_multi_domain",
        question="Why does that pump run so much?",
        # diagnose_alert added 2026-08-31: this case's real purpose (see
        # its own name) is proving BOTH the dosing and infrastructure
        # domains gated in and got used — not pinning one specific tool.
        # diagnose_alert is a legitimate infrastructure-domain tool a
        # model can reasonably reach for on an ambiguous "why is this
        # happening" question; a real live-model run picked it with no
        # real alert_id, got back an honest {"error": "no alert null"},
        # and (once _annotate_if_empty() was fixed the same day to also
        # cover error results, not just empty lists) correctly answered
        # "I'm not sure" instead of fabricating wiring facts from
        # PERSONALITY.md's example text. That's the case this test
        # actually needs to catch — a defensible tool choice was never
        # the bug.
        expected_tools={
            "get_dosing_history", "get_dosing_rationale",
            "get_wiring_info", "get_plumbing_info", "diagnose_alert",
        },
        # Real regression guard, not a hypothetical one — this exact
        # question, against this exact fresh/empty fixture, reproduced
        # the PERSONALITY.md-verbatim fabrication bug 2026-08-31 (see
        # _annotate_if_empty()'s own docstring). "relay channel" and
        # "dosing mcu" are specific enough that a real, tool-grounded
        # wiring answer would only ever use them after an actual
        # get_wiring_info() call returned them — this case's fixture
        # never calls that tool, so their presence at all means fabrication.
        forbidden_substrings=["relay channel", "dosing mcu", "ph-up/ph-down bottles"],
    ),
    # --- devices: empty ---
    GoldenCase(
        name="devices_unpaired_empty",
        question="Is there a device waiting to be paired?",
        expected_tools={"get_unpaired_devices"},
    ),
    # --- backups: one seeded-positive case ---
    GoldenCase(
        name="backups_snapshots_seeded",
        question="What snapshots exist?",
        expected_tools={"list_config_snapshots"},
        extra_setup=_seed_one_snapshot,
    ),
    # --- help_requests: empty ---
    GoldenCase(
        name="help_requests_empty",
        question="Is the greenhouse asking for help right now?",
        expected_tools={"get_active_help_requests"},
    ),
    # --- revenue: empty ---
    GoldenCase(
        name="revenue_empty",
        question="What's my revenue looking like this month?",
        expected_tools={"get_revenue_summary"},
    ),
    # --- self_knowledge: always-on, tests basic self-description grounding ---
    GoldenCase(
        name="self_knowledge_capabilities",
        question="What can you do?",
        expected_tools={"get_system_capabilities"},
    ),
]


def _called_tool_names(history: list[dict]) -> set[str]:
    names = set()
    for msg in history:
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            if fn.get("name"):
                names.add(fn["name"])
    return names


def run_case(case: GoldenCase, model: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "golden_set_test.db")
        conn = sqlite3.connect(db_path)
        cell_id = _base_seed(conn, ticks=case.base_ticks)
        if case.extra_setup:
            case.extra_setup(conn, cell_id)
        conn.close()

        assistant = GreenhouseAssistant(db_path=db_path, model=model)
        try:
            answer = assistant.ask(case.question)
        except Exception as e:
            return False, f"ERROR during ask(): {e}"

        called = _called_tool_names(assistant.history)
        tool_ok = bool(called & case.expected_tools)
        if not tool_ok:
            return False, f"expected one of {case.expected_tools}, model called {called or 'nothing'}"

        answer_lower = answer.lower()
        for forbidden in case.forbidden_substrings:
            if forbidden.lower() in answer_lower:
                return False, f"answer contains forbidden fabricated substring '{forbidden}': {answer!r}"

        if not answer.strip():
            return False, "final answer was empty"

        return True, answer[:120]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Run a single case by name")
    parser.add_argument("--model", default=OLLAMA_MODEL, help="Ollama model tag to test against")
    args = parser.parse_args()

    cases = [c for c in GOLDEN_CASES if c.name == args.only] if args.only else GOLDEN_CASES
    if args.only and not cases:
        print(f"No case named '{args.only}'. Available: {[c.name for c in GOLDEN_CASES]}")
        sys.exit(1)

    print(f"Running {len(cases)} case(s) against model: {args.model}\n")
    passed, failed = 0, 0
    for case in cases:
        ok, detail = run_case(case, args.model)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case.name}: {detail}")
        passed += ok
        failed += not ok

    print(f"\n{passed} passed, {failed} failed (model: {args.model})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
