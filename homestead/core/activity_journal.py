"""
MIA Homestead — Activity Journal
v0.1

The "what has it been doing and why, what's it doing now, what's next"
view — built almost entirely by aggregating data that already exists
for other reasons (core/action_log.py's automated_action_log,
dosing_events' own rationale column, experiment/maintenance/alert
timestamps) into one chronological narrative, rather than a new
tracking mechanism. If a real "why" wasn't already being recorded
somewhere, this doesn't invent one — see each _journal_from_* method's
own comment for exactly which column each entry's rationale comes from.

Three separate concerns, not one blob:
- get_journal(): PAST — a unified chronological feed across every
  domain that records a real rationale (dosing, alerts, experiments,
  maintenance, yield, other automated actions).
- get_current_status(): NOW — is the control loop actually alive
  (system_heartbeat), and what did it do most recently.
- get_whats_next(): FUTURE — the soonest of: a scheduled maintenance
  task, a running experiment's planned end, the next periodic report,
  an active deploy/config watch resolving. Only ever reports a real
  scheduled/computed time already living in the database — never
  invents a plan the system doesn't actually have.
"""

import sqlite3
from datetime import datetime

from contracts.capability import Describable


class ActivityJournal(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn
        self.db.row_factory = sqlite3.Row

    # ---------- PAST ----------

    def get_journal(self, days: int = 7, limit: int = 100) -> list[dict]:
        entries = []
        since = f"-{days} days"

        # automated_action_log — the general-purpose "why did you do
        # that" log (core/action_log.py), already rationale-first by design.
        for r in self.db.execute(
            "SELECT * FROM automated_action_log WHERE timestamp >= datetime('now', ?)", (since,)
        ).fetchall():
            entries.append({
                "timestamp": r["timestamp"], "category": "system", "source": r["module_id"],
                "title": r["action"].replace("_", " "), "detail": r["rationale"],
            })

        # dosing_events — rationale is already a required part of every
        # real dose (see modules/aquaponics_cell.py's _dose_command()).
        for r in self.db.execute(
            "SELECT * FROM dosing_events WHERE timestamp >= datetime('now', ?)", (since,)
        ).fetchall():
            amt = f"{r['amount_ml']}ml " if r["amount_ml"] is not None else ""
            entries.append({
                "timestamp": r["timestamp"], "category": "dosing", "source": f"cell {r['cell_id']}",
                "title": f"Dosed {amt}{r['dose_type']}", "detail": r["rationale"] or "",
            })

        # alerts — one entry when raised, a second when resolved, so the
        # journal shows the full arc ("X started" / "X resolved") rather
        # than only ever showing problems appearing, never clearing.
        for r in self.db.execute(
            "SELECT * FROM alerts WHERE timestamp >= datetime('now', ?)", (since,)
        ).fetchall():
            entries.append({
                "timestamp": r["timestamp"], "category": "alert", "source": r["source"],
                "title": f"{r['severity'].capitalize()} alert raised", "detail": r["message"],
                "severity": r["severity"],
            })
            if r["resolved"] and r["resolved_at"]:
                entries.append({
                    "timestamp": r["resolved_at"], "category": "alert", "source": r["source"],
                    "title": "Alert resolved", "detail": r["message"],
                })

        # experiments — the hypothesis IS the rationale, already written
        # for a human to read (core/experiment_manager.py). One entry
        # per real lifecycle timestamp that's actually set.
        for r in self.db.execute(
            "SELECT * FROM experiments WHERE proposed_at >= datetime('now', ?) "
            "OR started_at >= datetime('now', ?) OR completed_at >= datetime('now', ?)",
            (since, since, since),
        ).fetchall():
            if r["proposed_at"] and r["proposed_at"] >= _cutoff(self.db, days):
                entries.append({
                    "timestamp": r["proposed_at"], "category": "experiment", "source": f"cell {r['cell_id']}",
                    "title": f"Experiment proposed ({r['created_by']})", "detail": r["hypothesis"],
                })
            if r["started_at"]:
                entries.append({
                    "timestamp": r["started_at"], "category": "experiment", "source": f"cell {r['cell_id']}",
                    "title": "Experiment started",
                    "detail": f"{r['variable_changed']}: {r['baseline_value']} → {r['test_value']}",
                })
            if r["completed_at"]:
                entries.append({
                    "timestamp": r["completed_at"], "category": "experiment", "source": f"cell {r['cell_id']}",
                    "title": "Experiment completed", "detail": r["result_summary"] or r["hypothesis"],
                })

        # maintenance — created (with its own rationale-free title, but
        # priority/type say enough) and completed.
        for r in self.db.execute(
            "SELECT * FROM maintenance_tasks WHERE created_at >= datetime('now', ?)", (since,)
        ).fetchall():
            entries.append({
                "timestamp": r["created_at"], "category": "maintenance", "source": r["created_by"],
                "title": f"Maintenance task created: {r['title']}", "detail": r["description"] or f"priority {r['priority']}",
            })
            if r["completed_at"]:
                entries.append({
                    "timestamp": r["completed_at"], "category": "maintenance", "source": r["assigned_to"] or "human",
                    "title": f"Maintenance task completed: {r['title']}", "detail": "",
                })

        # yield_events — a real positive entry, not just problems/actions.
        for r in self.db.execute(
            "SELECT * FROM yield_events WHERE timestamp >= datetime('now', ?)", (since,)
        ).fetchall():
            entries.append({
                "timestamp": r["timestamp"], "category": "yield", "source": f"cell {r['cell_id']}",
                "title": f"Harvested {r['quantity']}{r['unit'] or ''} {r['item']}", "detail": r["notes"] or "",
            })

        entries.sort(key=lambda e: e["timestamp"], reverse=True)
        return entries[:limit]

    # ---------- NOW ----------

    def get_current_status(self) -> dict:
        heartbeat = self.db.execute(
            "SELECT component, last_seen FROM system_heartbeat ORDER BY id DESC LIMIT 1"
        ).fetchone()
        alive = False
        if heartbeat:
            last_seen = datetime.fromisoformat(heartbeat["last_seen"])
            alive = (datetime.utcnow() - last_seen).total_seconds() < 120  # 2x a typical control-loop interval

        latest_action = self.db.execute(
            "SELECT module_id, action, rationale, timestamp FROM automated_action_log "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        latest_dose = self.db.execute(
            "SELECT cell_id, dose_type, rationale, timestamp FROM dosing_events ORDER BY id DESC LIMIT 1"
        ).fetchone()

        most_recent = None
        for candidate, kind in ((latest_action, "action"), (latest_dose, "dose")):
            if candidate is None:
                continue
            if most_recent is None or candidate["timestamp"] > most_recent["timestamp"]:
                most_recent = {**dict(candidate), "kind": kind}

        cells = [dict(r) for r in self.db.execute("SELECT id, name FROM cells").fetchall()]

        return {
            "control_loop_alive": alive,
            "last_heartbeat": heartbeat["last_seen"] if heartbeat else None,
            "monitored_cells": [c["name"] for c in cells],
            "most_recent_action": most_recent,
        }

    # ---------- FUTURE ----------

    def get_whats_next(self) -> list[dict]:
        upcoming = []

        for r in self.db.execute(
            "SELECT title, next_due_at FROM maintenance_schedules WHERE auto_create = 1 ORDER BY next_due_at ASC LIMIT 3"
        ).fetchall():
            upcoming.append({
                "what": f"Scheduled maintenance: {r['title']}", "when": r["next_due_at"], "kind": "maintenance",
            })

        for r in self.db.execute(
            "SELECT cell_id, hypothesis, planned_end_date FROM experiments WHERE status = 'running' "
            "ORDER BY planned_end_date ASC LIMIT 3"
        ).fetchall():
            upcoming.append({
                "what": f"Experiment concludes (cell {r['cell_id']}): {r['hypothesis']}",
                "when": r["planned_end_date"], "kind": "experiment",
            })

        watch = self.db.execute(
            "SELECT applied_at, validation_window_minutes FROM update_watches WHERE status = 'watching' "
            "ORDER BY applied_at ASC LIMIT 1"
        ).fetchone()
        if watch:
            upcoming.append({
                "what": "Config update watch resolves (confirmed-good or auto-rollback)",
                "when": _add_minutes(watch["applied_at"], watch["validation_window_minutes"]), "kind": "deploy",
            })
        code_watch = self.db.execute(
            "SELECT applied_at, validation_window_minutes FROM code_update_watches WHERE status = 'watching' "
            "ORDER BY applied_at ASC LIMIT 1"
        ).fetchone()
        if code_watch:
            upcoming.append({
                "what": "Code deploy watch resolves (confirmed-good or auto-rollback)",
                "when": _add_minutes(code_watch["applied_at"], code_watch["validation_window_minutes"]), "kind": "deploy",
            })

        last_report = self.db.execute("SELECT generated_at FROM daily_reports ORDER BY id DESC LIMIT 1").fetchone()
        if last_report:
            upcoming.append({
                "what": "Next daily report", "when": _add_minutes(last_report["generated_at"], 24 * 60), "kind": "report",
            })

        upcoming = [u for u in upcoming if u["when"]]
        upcoming.sort(key=lambda u: u["when"])
        return upcoming

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="activity_journal",
            display_name="Activity Journal",
            purpose=(
                "Aggregates every domain that already records a real rationale (dosing, alerts, "
                "experiments, maintenance, yield, general automated actions) into one "
                "chronological narrative, plus a synthesized 'right now' status and 'what's next' "
                "forecast — all read-only, all from data other modules already produce for their "
                "own reasons."
            ),
            data_produced=["unified activity journal", "current control-loop status", "upcoming scheduled/planned items"],
            actions_possible=["view the journal", "check current status", "check what's planned next"],
            limits_and_safety=(
                "Purely a read/aggregation layer — never takes action, never writes anything. "
                "get_whats_next() only ever reports a real time already computed/stored elsewhere "
                "(a maintenance schedule's next_due_at, an experiment's planned_end_date, an "
                "active watch's window) — it does not guess or invent a plan the system doesn't "
                "actually have; an empty result honestly means nothing is currently scheduled."
            ),
            example_questions=[
                "What has the system been doing today?", "What's it working on right now?",
                "What's coming up next?", "Why did it dose pH-up this morning?",
            ],
            verification_evidence=[
                "2026-08-31: manually seeded real rows via the actual service methods "
                "(MaintenanceManager.create_task/update_status, ExperimentManager."
                "propose_experiment/start_experiment, plus a real dosing_event and "
                "yield_event) against mia_homestead.db, then ran "
                "viewer/export_journal_state.py and confirmed all 9 resulting journal "
                "entries appeared correctly categorized (dosing/experiment/yield/"
                "maintenance/alert) and correctly ordered newest-first; confirmed "
                "get_current_status() correctly reported control_loop_alive=false with "
                "an honest last_heartbeat when no live main.py process was running, and "
                "correctly flipped to the real most-recent dose once one was inserted; "
                "confirmed get_whats_next() correctly surfaced the started experiment's "
                "real planned_end_date and stayed empty before it existed — never "
                "fabricated a plan.",
                "2026-08-31: rendered viewer/journal.html via headless Chromium "
                "(Playwright) against the live exported journal_state.json, zero "
                "console/page errors, confirmed the Right Now / What's Next / Journal "
                "feed sections all render the real data correctly.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure read/aggregation layer, no hardware of its own


def _cutoff(db, days: int) -> str:
    return db.execute("SELECT datetime('now', ?)", (f"-{days} days",)).fetchone()[0]


def _add_minutes(timestamp: str, minutes: float) -> str | None:
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    from datetime import timedelta
    return (dt + timedelta(minutes=minutes)).isoformat(sep=" ")
