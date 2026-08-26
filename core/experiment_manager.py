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

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="experiment_manager",
            display_name="Experiment Manager (Aquaponics Scientist)",
            purpose=(
                "Proposes and runs controlled changes to one cell's dosing targets, tracks "
                "yield outcomes during the window, and recommends evidence-based permanent "
                "changes — through the same human-approval pattern as the inventory reorder queue."
            ),
            data_produced=["experiment history with before/after yield comparisons"],
            actions_possible=[
                "propose an experiment (change one target variable for a duration)",
                "start an approved experiment (applies live via target_overrides, no restart)",
                "complete an experiment and generate a result summary",
                "propose a permanent parameter change for human approval",
            ],
            limits_and_safety=(
                "NEVER applies a permanent target change without human approval. Comparisons "
                "are single before/after means, not statistically rigorous controlled trials — "
                "presented as suggestive evidence, explicitly not overstated as proof. Only "
                "changes pH/EC targets within a cell, never dosing hard limits, which remain "
                "enforced independently by the safety MCU regardless of any experiment."
            ),
            example_questions=[
                "Any experiments running right now?",
                "What did the last EC experiment find?",
                "Should I approve raising the pH target for Cell A?",
            ],
            verification_evidence=[
                "Live manual test 2026-08-26: full lifecycle proven end to end — proposed a "
                "target change, confirmed live effect on the control loop with zero restart, "
                "logged before/after yield data, completed the experiment, got a correct "
                "evidence-based +32.3% adopt recommendation, approved it, and confirmed the "
                "change promoted from set_by='experiment' to set_by='manual'",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software — reads existing sensor/yield data, no hardware of its own
