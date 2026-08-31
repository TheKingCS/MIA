"""
MIA Homestead — Digital Biofilter / Nitrogen-Cycle Model
v0.1

Tracks the classic aquaponics nitrogen cycle (ammonia -> nitrite ->
nitrate) from real, periodically logged water test results, and warns
if livestock is present (or about to be) on a cell that isn't confirmed
cycled yet.

Deliberately NOT built on continuous sensor data — sensors.type has no
ammonia/nitrite/nitrate entry anywhere in this codebase, and real
aquaponics ammonia/nitrite/nitrate testing is a periodic liquid/strip
test-kit reading (see describe_hardware_requirements() below), not
something a cheap continuous probe exists for the way pH/EC do.
Pretending otherwise would mean fabricating data. record_test()'s
`source` column is forward-compatible for a real automated probe later
(mirrors species_profiles.source's own forward-declared-before-built
pattern) — but nothing here assumes that hardware exists.

Also deliberately NOT routed through contracts.mia_homestead_contract's
control-loop machinery (MiaHomesteadModule.run_cycle(), the 10-minute
STALE_THRESHOLD, the recovery ladder) — that's built for continuous,
frequently-polled readings feeding real-time dosing decisions. A
weekly manual test read through that pipeline would either constantly
false-alarm as "stale" or need awkward per-sensor-type staleness
overrides. This is a purpose-built table and service instead, same
precedent as automated_action_log getting its own table rather than
repurposing dosing_events for non-dosing rationale.
"""

import logging
import sqlite3
from datetime import datetime, timedelta

from contracts.capability import Describable
from contracts.mia_homestead_contract import Severity, raise_alert

logger = logging.getLogger("mia_homestead.biofilter_model")

# Standard "detectable" threshold for aquarium/aquaponics liquid test
# kits — below this, a reading reads as visually indistinguishable from
# zero on the kit's own color chart, so treating it as "present" would
# overclaim precision the test itself doesn't have.
DETECTABLE_PPM = 0.25

# How many consecutive clean tests are required before declaring a cell
# cycled — one lucky/noisy reading shouldn't be enough, same
# "don't overclaim from N=1" discipline as MIN_CONSISTENT_READINGS_FOR_DOSE
# and the closed-loop species-learning self-gating rule.
CONSECUTIVE_CLEAN_TESTS_REQUIRED = 2

# How long a stocked, not-yet-cycled cell can go without a fresh test
# before it's worth a gentle reminder.
OVERDUE_TEST_DAYS = 14


class BiofilterModel(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    # ---------- Recording ----------

    def record_test(self, cell_id: int, ammonia_ppm: float = None, nitrite_ppm: float = None,
                     nitrate_ppm: float = None, tested_by: str = "human", notes: str = None) -> int:
        if ammonia_ppm is None and nitrite_ppm is None and nitrate_ppm is None:
            raise ValueError("record_test needs at least one of ammonia_ppm/nitrite_ppm/nitrate_ppm")
        cur = self.db.execute(
            "INSERT INTO water_quality_tests (cell_id, ammonia_ppm, nitrite_ppm, nitrate_ppm, "
            "tested_by, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (cell_id, ammonia_ppm, nitrite_ppm, nitrate_ppm, tested_by, notes),
        )
        self.db.commit()
        logger.info(
            "Water test logged for cell %s: ammonia=%s nitrite=%s nitrate=%s",
            cell_id, ammonia_ppm, nitrite_ppm, nitrate_ppm,
        )
        return cur.lastrowid

    # ---------- Cycle status ----------

    def _recent_tests(self, cell_id: int, limit: int = 5) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute(
            "SELECT * FROM water_quality_tests WHERE cell_id = ? ORDER BY id DESC LIMIT ?",
            (cell_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_cycle_status(self, cell_id: int) -> dict:
        tests = self._recent_tests(cell_id, limit=CONSECUTIVE_CLEAN_TESTS_REQUIRED + 1)
        total_tests = self.db.execute(
            "SELECT COUNT(*) FROM water_quality_tests WHERE cell_id = ?", (cell_id,)
        ).fetchone()[0]

        if not tests:
            return {
                "stage": "not_started", "latest_test": None, "tests_logged": 0,
                "days_since_first_test": None,
                "rough_estimate": "No water tests logged yet — log one to start tracking.",
            }

        latest = tests[0]
        first_test_ts = self.db.execute(
            "SELECT MIN(timestamp) FROM water_quality_tests WHERE cell_id = ?", (cell_id,)
        ).fetchone()[0]
        days_since_first = None
        if first_test_ts:
            days_since_first = (datetime.utcnow() - datetime.fromisoformat(first_test_ts)).days

        # "cycled" is the only stage that needs CONSECUTIVE_CLEAN_TESTS_REQUIRED
        # readings — a single ammonia or nitrite reading well above the
        # detectable threshold is real, immediately usable evidence on
        # its own (that's what a positive test result IS), so those two
        # phases don't need a multi-test gate the way "confirmed clean"
        # does — declaring victory from one lucky/noisy clean reading is
        # the overclaiming risk; declaring "ammonia is present" from one
        # reading that clearly shows ammonia is not.
        if len(tests) >= CONSECUTIVE_CLEAN_TESTS_REQUIRED and all(
            self._is_clean(t) for t in tests[:CONSECUTIVE_CLEAN_TESTS_REQUIRED]
        ):
            stage = "cycled"
        elif (latest["nitrite_ppm"] or 0) >= DETECTABLE_PPM:
            stage = "nitrite_phase"
        elif (latest["ammonia_ppm"] or 0) >= DETECTABLE_PPM:
            stage = "ammonia_phase"
        elif total_tests < 2:
            # Latest test reads near-zero on everything, but only one
            # test exists total — too early to tell "cycled" (needs the
            # consecutive-test guard above) from "just hasn't started
            # producing ammonia yet."
            stage = "insufficient_data"
        else:
            # Near-zero latest reading, 2+ tests exist, but not
            # CONSECUTIVE_CLEAN_TESTS_REQUIRED in a row — genuinely
            # ambiguous (noise vs. the real start of cycling completing).
            stage = "insufficient_data"

        rough_estimate = (
            "Standard aquaponics cycling typically takes 4-6 weeks total. "
            f"{days_since_first if days_since_first is not None else '?'} day(s) since the first "
            "logged test — no confident ETA without more logged tests; this is a rough reference "
            "point, not a prediction."
        )
        if stage == "cycled":
            rough_estimate = f"Cycled — confirmed by {CONSECUTIVE_CLEAN_TESTS_REQUIRED} consecutive clean tests."

        return {
            "stage": stage,
            "latest_test": latest,
            "tests_logged": total_tests,
            "days_since_first_test": days_since_first,
            "rough_estimate": rough_estimate,
        }

    def _is_clean(self, test: dict) -> bool:
        """A test counts as 'clean' only if ammonia AND nitrite were
        BOTH actually measured (not None) and both below the detectable
        threshold, AND nitrate is present (real evidence nitrification
        is happening, not just that nothing was measured)."""
        if test["ammonia_ppm"] is None or test["nitrite_ppm"] is None:
            return False
        return (
            test["ammonia_ppm"] < DETECTABLE_PPM
            and test["nitrite_ppm"] < DETECTABLE_PPM
            and (test["nitrate_ppm"] or 0) > 0
        )

    # ---------- Livestock readiness ----------

    def check_livestock_readiness(self, cell_id: int) -> dict:
        status = self.get_cycle_status(cell_id)
        tank = self.db.execute(
            "SELECT species, stocked_date FROM tanks WHERE cell_id = ? AND stocked_date IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (cell_id,),
        ).fetchone()
        stocked = tank is not None

        if stocked and status["stage"] != "cycled":
            return {
                "ready": False, "stocked": True, "stage": status["stage"],
                "message": (
                    f"Fish ({tank[0] or 'unspecified species'}) already stocked since {tank[1]}, "
                    f"but this cell is NOT confirmed cycled (stage: {status['stage']}) — "
                    f"elevated ammonia/nitrite risk. Log a water test to check."
                ),
            }
        if stocked:
            return {"ready": True, "stocked": True, "stage": status["stage"],
                    "message": "Fish stocked and cycle confirmed complete."}
        if status["stage"] == "cycled":
            return {"ready": True, "stocked": False, "stage": status["stage"],
                    "message": "Cycled and no fish stocked yet — safe to stock."}
        return {
            "ready": False, "stocked": False, "stage": status["stage"],
            "message": f"Not yet confirmed cycled (stage: {status['stage']}) — wait and keep testing before stocking.",
        }

    # ---------- Periodic check ----------

    def check_overdue_water_tests(self) -> list[dict]:
        """Called periodically (main.py) — a stocked, not-yet-cycled
        cell that hasn't had a fresh test in a while gets a gentle
        reminder alert. Never fabricates a data point — just nudges
        toward running the real test kit."""
        findings = []
        cells = self.db.execute(
            "SELECT DISTINCT cell_id FROM tanks WHERE stocked_date IS NOT NULL"
        ).fetchall()
        for (cell_id,) in cells:
            status = self.get_cycle_status(cell_id)
            if status["stage"] == "cycled":
                continue
            latest = status["latest_test"]
            overdue = latest is None or (
                datetime.utcnow() - datetime.fromisoformat(latest["timestamp"]) > timedelta(days=OVERDUE_TEST_DAYS)
            )
            if not overdue:
                continue
            message = (
                f"cell {cell_id}: fish stocked, biofilter not yet confirmed cycled, and no water "
                f"test logged in over {OVERDUE_TEST_DAYS} days — log one to confirm cycling status"
            )
            raise_alert(self.db, "biofilter_model", Severity.WARNING, message, self.notifier)
            findings.append({"cell_id": cell_id, "stage": status["stage"]})
        return findings

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="biofilter_model",
            display_name="Digital Biofilter / Nitrogen-Cycle Model",
            purpose=(
                "Tracks the classic aquaponics nitrogen cycle (ammonia -> nitrite -> nitrate) "
                "from periodically logged manual water test results, and warns if livestock is "
                "present on a cell that isn't confirmed cycled yet — the most on-brand "
                "'aquaponics scientist' gap that wasn't built yet."
            ),
            data_produced=["water quality test history", "cycle stage classification", "livestock readiness"],
            actions_possible=[
                "log a water test result (ammonia/nitrite/nitrate ppm)",
                "classify current cycle stage from real logged tests",
                "check whether a cell is safe to stock livestock, or already at risk if stocked early",
                "remind (via a real, deduplicated alert) when a stocked, uncycled cell is overdue for a test",
            ],
            limits_and_safety=(
                "Built entirely on PERIODIC MANUAL test-kit readings, never a continuous sensor — "
                "none exists in this system's sensor types. Never invents a cycle stage from "
                "elapsed time alone; only classifies from real logged values, with an honest "
                "'insufficient_data' state when there aren't enough tests yet. Requires "
                f"{CONSECUTIVE_CLEAN_TESTS_REQUIRED} CONSECUTIVE clean tests before declaring "
                "'cycled', not one lucky reading. Purely read/log/alert — never touches dosing, "
                "never blocks or approves anything; a human decides when to actually add fish."
            ),
            example_questions=[
                "Is cell A's biofilter cycled yet?",
                "Is it safe to add fish to the pilot cell?",
                "Log a water test: ammonia 0.5, nitrite 0.1, nitrate 5",
            ],
            verification_evidence=[
                "scenarios.py::scenario_biofilter_cycle_tracking — confirmed the classic "
                "ammonia-phase -> nitrite-phase -> cycled progression classifies correctly as "
                "real tests are logged in sequence; confirmed a single clean test alone does NOT "
                "yet report 'cycled' (the consecutive-tests overclaiming guard); confirmed "
                "check_livestock_readiness() correctly warns when fish are stocked on an uncycled "
                "cell and reports safe once cycled; confirmed check_overdue_water_tests() raises "
                "a real alert for a stocked, uncycled, test-overdue cell and stays silent for a "
                "cell with a recent test.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="API Freshwater Master Test Kit (or equivalent liquid ammonia/nitrite/nitrate/pH test kit)",
                category="other", quantity=1,
                purpose="the actual, periodic manual measurement this model is built from — no "
                        "continuous ammonia/nitrite/nitrate sensor is priced or planned anywhere "
                        "in this project",
                est_unit_cost=38.99,
                notes="Confirmed 2026-08-31 via live vendor search (Pet Supermarket listing; "
                      "another retailer lists $35.98) — over 800 tests per kit, refills "
                      "available separately once exhausted.",
            ),
        ]
