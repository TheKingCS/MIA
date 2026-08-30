"""
MIA Homestead — Experiment Manager
v0.1

This is the "gets better over time" mechanism, built honestly. What it
actually does: proposes a controlled change to one variable on one
cell, applies it via target_overrides (live, no restart needed), tracks
yield outcomes during the window, and compares against a baseline
period. It does NOT silently adopt what it learns — every "this seems
to work better" conclusion goes through parameter_change_proposals,
the same human-approval pattern as the inventory reorder queue, because
changing what a cell doses toward is safety-relevant.

Honest limitation, stated plainly rather than hidden: a home system has
one tank per cell and no true replication. A single experiment's result
is suggestive, not statistically rigorous — the comparison here is a
straightforward before/after mean, not a controlled trial with
confidence intervals. The right way to build real confidence is running
the same experiment again later, or on the pilot AND the full-scale
cell over time (see docs/PILOT_VS_SCALE.md) — this module tracks enough
history to make that possible, but doesn't pretend one run proves
anything on its own.
"""

import logging
import sqlite3
from datetime import datetime, timedelta

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.experiment_manager")

VALID_PARAMS = ("ph_target_min", "ph_target_max", "ec_target_min", "ec_target_max")


class ExperimentManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    # ---------- Proposing and starting ----------

    def propose_experiment(
        self, cell_id: int, hypothesis: str, variable_changed: str,
        baseline_value: float, test_value: float, duration_days: int = 14,
        created_by: str = "human",
    ) -> int:
        if variable_changed not in VALID_PARAMS:
            raise ValueError(f"variable_changed must be one of {VALID_PARAMS}")

        planned_end = (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
        cur = self.db.execute(
            "INSERT INTO experiments (cell_id, hypothesis, variable_changed, baseline_value, "
            "test_value, planned_end_date, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cell_id, hypothesis, variable_changed, baseline_value, test_value, planned_end, created_by),
        )
        self.db.commit()
        logger.info("Experiment #%s proposed: %s", cur.lastrowid, hypothesis)
        return cur.lastrowid

    def start_experiment(self, experiment_id: int) -> None:
        """Human/assistant-approved go-ahead — this is the point where
        the change actually takes effect on the live control loop, via
        a target_overrides row the cell reads every cycle."""
        exp = self._get(experiment_id)
        if not exp:
            raise ValueError(f"no experiment {experiment_id}")

        self.db.execute(
            "INSERT INTO target_overrides (cell_id, param_name, value, set_by, reference_id, active) "
            "VALUES (?, ?, ?, 'experiment', ?, 1) "
            "ON CONFLICT(cell_id, param_name, active) DO UPDATE SET "
            "value = excluded.value, set_by = excluded.value, reference_id = excluded.reference_id, "
            "set_at = datetime('now')",
            (exp["cell_id"], exp["variable_changed"], exp["test_value"], experiment_id),
        )
        self.db.execute(
            "UPDATE experiments SET status = 'running', started_at = datetime('now') WHERE id = ?",
            (experiment_id,),
        )
        self.db.commit()
        logger.info("Experiment #%s started — cell %s %s now targeting %.2f",
                    experiment_id, exp["cell_id"], exp["variable_changed"], exp["test_value"])
        if self.notifier:
            self.notifier.dispatch(
                "info",
                f"Experiment started: {exp['hypothesis']} (cell {exp['cell_id']}, "
                f"{exp['variable_changed']} -> {exp['test_value']})",
                source="experiment_manager",
            )

    # ---------- Completing and evaluating ----------

    def check_due_experiments(self) -> list[int]:
        """Call periodically (main.py) — finds running experiments past
        their planned end date and completes them automatically. Doesn't
        auto-apply any conclusion — just moves from 'running' to
        'completed' with a result summary and a proposal in the queue."""
        rows = self.db.execute(
            "SELECT id FROM experiments WHERE status = 'running' AND planned_end_date <= datetime('now')"
        ).fetchall()
        completed = []
        for (exp_id,) in rows:
            self.complete_experiment(exp_id)
            completed.append(exp_id)
        return completed

    def complete_experiment(self, experiment_id: int) -> dict:
        exp = self._get(experiment_id)
        if not exp or exp["status"] != "running":
            raise ValueError(f"experiment {experiment_id} is not running")

        baseline_yield = self._avg_yield_before(exp["cell_id"], exp["started_at"])
        test_yield = self._avg_yield_during(exp["cell_id"], exp["started_at"], datetime.utcnow().isoformat())

        summary, suggestion = self._evaluate(baseline_yield, test_yield)

        self.db.execute(
            "UPDATE experiments SET status = 'completed', completed_at = datetime('now'), "
            "result_summary = ?, suggested_action = ? WHERE id = ?",
            (summary, suggestion, experiment_id),
        )
        self.db.commit()

        if suggestion == "adopt":
            self._create_parameter_proposal(exp, summary)

        logger.info("Experiment #%s completed: %s (suggestion: %s)", experiment_id, summary, suggestion)
        return {"summary": summary, "suggestion": suggestion,
                "baseline_yield": baseline_yield, "test_yield": test_yield}

    def _avg_yield_before(self, cell_id: int, started_at: str, window_days: int = 14) -> float | None:
        window_start = (datetime.fromisoformat(started_at) - timedelta(days=window_days)).isoformat()
        row = self.db.execute(
            "SELECT AVG(quantity) FROM yield_events WHERE cell_id = ? "
            "AND timestamp >= ? AND timestamp < ?",
            (cell_id, window_start, started_at),
        ).fetchone()
        return row[0]

    def _avg_yield_during(self, cell_id: int, started_at: str, ended_at: str) -> float | None:
        row = self.db.execute(
            "SELECT AVG(quantity) FROM yield_events WHERE cell_id = ? "
            "AND timestamp >= ? AND timestamp <= ?",
            (cell_id, started_at, ended_at),
        ).fetchone()
        return row[0]

    def _evaluate(self, baseline: float | None, test: float | None) -> tuple[str, str]:
        if baseline is None or test is None:
            return (
                "Not enough yield data on one or both sides of the change to compare — "
                "no harvests logged during the window.",
                "inconclusive",
            )
        if baseline == 0:
            return ("Baseline period had zero recorded yield — comparison isn't meaningful.", "inconclusive")

        pct_change = ((test - baseline) / baseline) * 100
        summary = (
            f"Average yield per harvest: {baseline:.2f} before vs {test:.2f} during the change "
            f"({pct_change:+.1f}%). Based on a single before/after comparison, not a controlled "
            f"trial — treat as suggestive, not conclusive. See docs on repeating experiments "
            f"across the pilot and full-scale cells to build real confidence."
        )
        if pct_change > 10:
            return summary, "adopt"
        if pct_change < -10:
            return summary, "revert"
        return summary, "inconclusive"

    def _create_parameter_proposal(self, exp: dict, rationale: str) -> None:
        self.db.execute(
            "INSERT INTO parameter_change_proposals "
            "(experiment_id, cell_id, param_name, current_value, proposed_value, rationale) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (exp["id"], exp["cell_id"], exp["variable_changed"],
             exp["baseline_value"], exp["test_value"], rationale),
        )
        self.db.commit()
        if self.notifier:
            self.notifier.dispatch(
                "info",
                f"Experiment #{exp['id']} suggests adopting {exp['variable_changed']}="
                f"{exp['test_value']} permanently for cell {exp['cell_id']} — awaiting your approval.",
                source="experiment_manager",
            )

    # ---------- Parameter change approval (mirrors the order queue) ----------

    def approve_parameter_change(self, proposal_id: int) -> None:
        row = self.db.execute(
            "SELECT cell_id, param_name, proposed_value FROM parameter_change_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"no proposal {proposal_id}")
        cell_id, param_name, value = row

        self.db.execute(
            "INSERT INTO target_overrides (cell_id, param_name, value, set_by, active) "
            "VALUES (?, ?, ?, 'manual', 1) "
            "ON CONFLICT(cell_id, param_name, active) DO UPDATE SET "
            "value = excluded.value, set_by = 'manual', set_at = datetime('now')",
            (cell_id, param_name, value),
        )
        self.db.execute(
            "UPDATE parameter_change_proposals SET status = 'approved', decided_at = datetime('now') "
            "WHERE id = ?", (proposal_id,),
        )
        self.db.commit()

    def deny_parameter_change(self, proposal_id: int) -> None:
        self.db.execute(
            "UPDATE parameter_change_proposals SET status = 'denied', decided_at = datetime('now') "
            "WHERE id = ?", (proposal_id,),
        )
        self.db.commit()

    def get_pending_proposals(self) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM parameter_change_proposals WHERE status = 'proposed'"
        ).fetchall()]

    def get_active_experiments(self) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM experiments WHERE status IN ('proposed', 'approved', 'running')"
        ).fetchall()]

    def _get(self, experiment_id: int) -> dict | None:
        self.db.row_factory = sqlite3.Row
        row = self.db.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
        return dict(row) if row else None

    # ---------- Proactive proposals from observed patterns ----------

    def _current_target(self, cell_id: int, param_name: str, config_path: str = "config/modules.yaml") -> float | None:
        """The real current effective target for a cell/param — checks
        target_overrides first (an active experiment/approved change),
        falls back to config/modules.yaml's baseline, same precedence
        modules/aquaponics_cell.py's own _current_targets() uses. A
        proposed experiment's baseline_value must be the REAL current
        target, not a guess — logging the wrong baseline would make the
        eventual before/after comparison meaningless."""
        row = self.db.execute(
            "SELECT value FROM target_overrides WHERE cell_id = ? AND param_name = ? AND active = 1",
            (cell_id, param_name),
        ).fetchone()
        if row:
            return row[0]
        import yaml
        from pathlib import Path
        raw = yaml.safe_load(Path(config_path).read_text())
        for entry in raw.get("modules", []):
            if entry.get("cell_id") == cell_id and param_name in entry.get("params", {}):
                return entry["params"][param_name]
        return None

    def propose_experiments_for_underperformance(self, species_registry, config_path: str = "config/modules.yaml") -> list[int]:
        """Called periodically (main.py) — the proactive half of this
        module's "gets better over time" purpose. Everything before this
        method required a HUMAN to notice underperformance and propose
        an experiment by hand; this notices the pattern itself. Still
        stops at proposing, same as every human-authored proposal — the
        result is a 'proposed' row a human must call start_experiment()
        on, same safety gate, no bypass.

        Deliberately conservative about what counts as a real signal,
        to avoid becoming noise:
        - Only plantings at least 50% through their expected time to
          harvest — too early to judge a slow start from a real problem.
        - Only when actual yield-so-far is under half of what a linear
          pace toward the expected total would predict by now — a
          meaningful shortfall, not normal variance.
        - Never proposes a second experiment for a cell that already has
          one in a non-terminal state (proposed/approved/running) —
          one live proposal at a time per cell.
        - The proposed test value is always the species' OWN documented
          baseline midpoint (core/species_registry.py), never an
          invented number — this doesn't claim to know a better value
          than the species knowledge base already records, it only
          proposes moving toward it when the cell isn't there yet, and
          skips entirely (nothing to propose) when the cell is already
          within 1 unit of that midpoint.
        - Picks EC over pH as the one variable tested per pass — EC is
          the more commonly cited lever for a yield shortfall
          specifically (nutrient availability) versus pH's broader
          water-chemistry role; keeping this to one variable per
          proposal keeps each experiment interpretable, matching this
          module's own stated "one variable at a time" design."""
        proposed_ids = []
        self.db.row_factory = sqlite3.Row
        for row in self.db.execute(
            "SELECT * FROM bed_plantings WHERE status = 'active' "
            "AND expected_yield_amount IS NOT NULL AND expected_harvest_date IS NOT NULL"
        ).fetchall():
            p = dict(row)
            try:
                planted = datetime.fromisoformat(p["planted_date"])
                harvest = datetime.fromisoformat(p["expected_harvest_date"])
            except (TypeError, ValueError):
                continue
            total_days = (harvest - planted).total_seconds() / 86400
            if total_days <= 0:
                continue
            elapsed_fraction = (datetime.utcnow() - planted).total_seconds() / 86400 / total_days
            if elapsed_fraction < 0.5:
                continue

            actual = self.db.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM yield_events WHERE cell_id = ? AND timestamp >= ?",
                (p["cell_id"], p["planted_date"]),
            ).fetchone()[0]
            expected_by_now = p["expected_yield_amount"] * min(elapsed_fraction, 1.0)
            if expected_by_now <= 0 or actual >= 0.5 * expected_by_now:
                continue  # on pace, or no real shortfall signal

            already_active = self.db.execute(
                "SELECT COUNT(*) FROM experiments WHERE cell_id = ? AND status IN ('proposed', 'approved', 'running')",
                (p["cell_id"],),
            ).fetchone()[0]
            if already_active:
                continue

            species = species_registry.get_profile(p["species_id"])
            if not species or species.get("ec_min") is None or species.get("ec_max") is None:
                continue
            current_ec = self._current_target(p["cell_id"], "ec_target_max", config_path)
            if current_ec is None:
                continue
            species_mid_ec = (species["ec_min"] + species["ec_max"]) / 2
            if abs(current_ec - species_mid_ec) < 1:
                continue  # already at the species' own documented midpoint — nothing to propose

            unit = p["expected_yield_unit"] or ""
            exp_id = self.propose_experiment(
                cell_id=p["cell_id"],
                hypothesis=(
                    f"System-observed pattern, not a confirmed cause — review before starting. "
                    f"Planting #{p['id']} ({species['common_name']}) is at {actual:.2f} {unit} vs. "
                    f"an expected-by-now pace of {expected_by_now:.2f} {unit} "
                    f"({elapsed_fraction * 100:.0f}% of its time to harvest elapsed). Current EC "
                    f"target ({current_ec}) sits away from {species['common_name']}'s own documented "
                    f"midpoint ({species_mid_ec:.0f}, from ec_min {species['ec_min']}-ec_max "
                    f"{species['ec_max']}) — proposing to test moving toward it."
                ),
                variable_changed="ec_target_max",
                baseline_value=current_ec,
                test_value=species_mid_ec,
                created_by="system",
            )
            proposed_ids.append(exp_id)
            logger.info(
                "Proposed experiment #%s for underperforming planting #%s (%s): "
                "EC %s -> %s", exp_id, p["id"], species["common_name"], current_ec, species_mid_ec,
            )
        return proposed_ids

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="experiment_manager",
            display_name="Experiment Manager (Aquaponics Scientist)",
            purpose=(
                "Proposes and runs controlled changes to one cell's dosing targets, tracks "
                "yield outcomes during the window, and recommends evidence-based permanent "
                "changes — through the same human-approval pattern as the inventory reorder queue. "
                "Also proactively proposes an experiment itself when a planting's yield is "
                "significantly behind pace, rather than waiting for a human to notice."
            ),
            data_produced=["experiment history with before/after yield comparisons"],
            actions_possible=[
                "propose an experiment (change one target variable for a duration)",
                "start an approved experiment (applies live via target_overrides, no restart)",
                "complete an experiment and generate a result summary",
                "propose a permanent parameter change for human approval",
                "scan active plantings for a significant yield shortfall and proactively propose "
                "an experiment nudging EC toward the species' own documented midpoint",
            ],
            limits_and_safety=(
                "NEVER applies a permanent target change without human approval. Comparisons "
                "are single before/after means, not statistically rigorous controlled trials — "
                "presented as suggestive evidence, explicitly not overstated as proof. Only "
                "changes pH/EC targets within a cell, never dosing hard limits, which remain "
                "enforced independently by the safety MCU regardless of any experiment. The "
                "proactive proposal path is deliberately conservative — at least 50% through the "
                "expected time to harvest, actual yield under half of pace, never proposes a "
                "second experiment for a cell that already has one live, and only ever proposes "
                "moving toward a value already recorded in the species knowledge base, never an "
                "invented number. It still only PROPOSES — start_experiment() still requires a "
                "human, same gate as every other experiment."
            ),
            example_questions=[
                "Any experiments running right now?",
                "What did the last EC experiment find?",
                "Should I approve raising the pH target for Cell A?",
                "Why did the system propose this experiment?",
            ],
            verification_evidence=[
                "Live manual test 2026-08-26: full lifecycle proven end to end — proposed a "
                "target change, confirmed live effect on the control loop with zero restart, "
                "logged before/after yield data, completed the experiment, got a correct "
                "evidence-based +32.3% adopt recommendation, approved it, and confirmed the "
                "change promoted from set_by='experiment' to set_by='manual'",
                "Live manual test 2026-08-30 (proactive proposals): seeded a real planting 60% "
                "through its time to harvest with yield at 20% of expected-by-now pace and a "
                "config EC target away from the species' documented midpoint — confirmed exactly "
                "one experiment proposed, correctly attributing baseline_value to the REAL "
                "config-read current target and test_value to the species' real recorded "
                "midpoint. Confirmed 3 negative cases produce zero proposals: a planting on pace, "
                "a planting only 30% through its cycle (too early to judge), and a cell that "
                "already has a live (non-terminal) experiment — no duplicate proposal.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software — reads existing sensor/yield data, no hardware of its own
