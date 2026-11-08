"""
MIA Homestead — Alert Lifecycle Manager
v0.1

Real gap found live 2026-09-01: alerts.acknowledged/acknowledged_at/
resolved/resolved_at have existed in the schema since the start, and
contracts.mia_homestead_contract.raise_alert() reads/writes resolved=0
on every call — but nothing anywhere ever WROTE resolved=1 or
acknowledged=1 for a real alert (only the separate help_requests table,
self_preservation.py's beacon system, ever got real ack/resolve logic).
Alerts just accumulated forever once raised, even long after the real
underlying condition cleared — the live DB had 50+ permanently
"unresolved" alerts, several genuinely stale, when this was found.

Two real mechanisms, not one — precise per-condition resolution would
mean touching every raise_alert() call site across every module
(dozens, across nearly every file in modules/ and core/) to detect
exactly when ITS OWN condition clears, a much larger and riskier change
than this pass calls for:
- Manual: a human (via the assistant) can acknowledge or resolve any
  specific alert directly — always correct, since a human is looking
  at it. This is the primary, precise mechanism.
- Automatic: a periodic sweep resolves any alert that hasn't been
  RE-RAISED (its last_seen bumped via raise_alert's own dedup path) in
  a while. A real, HONEST heuristic, not a guarantee the underlying
  condition is actually gone — logged distinguishably from a human
  resolving it, so it's never mistaken for a confirmed fix. This is
  what keeps the alert list from growing forever unattended.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.alert_manager")

# Starting point, not calibrated against a real deployment's control-
# loop interval (matches every other placeholder threshold in this
# project) — an alert not re-raised in this long probably means its
# condition cleared, but a crashed/stopped module would look identical.
# Scale this up if a real deployment runs a much longer --interval than
# this project's 5s dev default.
DEFAULT_STALE_AFTER_MINUTES = 30


class AlertManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def acknowledge_alert(self, alert_id: int) -> dict:
        row = self.db.execute("SELECT id FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            raise ValueError(f"no alert {alert_id}")
        self.db.execute(
            "UPDATE alerts SET acknowledged = 1, acknowledged_at = datetime('now') WHERE id = ?",
            (alert_id,),
        )
        self.db.commit()
        return {"alert_id": alert_id, "acknowledged": True}

    def resolve_alert(self, alert_id: int, notes: str = None) -> dict:
        """Human-driven, precise resolution. Refuses an alert that's
        already resolved — same 'don't let a stale/duplicate action
        silently rewrite real history' discipline as
        core/bed_planting.py's convert_to_active()."""
        row = self.db.execute("SELECT id, resolved FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            raise ValueError(f"no alert {alert_id}")
        if row[1]:
            raise ValueError(f"alert {alert_id} is already resolved")
        self.db.execute(
            "UPDATE alerts SET resolved = 1, resolved_at = datetime('now') WHERE id = ?",
            (alert_id,),
        )
        self.db.commit()
        from core.action_log import log_action
        log_action(
            self.db, "alert_manager", "alert_resolved_by_human",
            f"Alert {alert_id} marked resolved" + (f" — {notes}" if notes else ""),
        )
        return {"alert_id": alert_id, "resolved": True}

    def check_stale_alerts(self, stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES) -> list[dict]:
        """Called periodically (main.py's existing 60-cycle block, not
        every cycle — this is a long-timescale cleanup, not a safety-
        critical check). Auto-resolves any unresolved alert whose
        (source, message) condition hasn't been re-raised in
        stale_after_minutes. Explicitly logged as a heuristic auto-
        resolution, distinct from resolve_alert()'s human-driven kind —
        never claims certainty the condition is actually gone."""
        rows = self.db.execute(
            "SELECT id, source, message FROM alerts WHERE resolved = 0 "
            "AND last_seen < datetime('now', ?)",
            (f"-{stale_after_minutes} minutes",),
        ).fetchall()
        if not rows:
            return []
        resolved = [{"alert_id": r[0], "source": r[1], "message": r[2]} for r in rows]
        for alert_id, _, _ in rows:
            self.db.execute(
                "UPDATE alerts SET resolved = 1, resolved_at = datetime('now') WHERE id = ?",
                (alert_id,),
            )
        self.db.commit()
        from core.action_log import log_action
        log_action(
            self.db, "alert_manager", "stale_alerts_auto_resolved",
            f"Auto-resolved {len(resolved)} alert(s) not re-raised in over "
            f"{stale_after_minutes} min (heuristic, not a confirmed fix): "
            f"{[r['alert_id'] for r in resolved]}",
        )
        return resolved

    def get_alert_history(self, source: str | None = None, days: int = 7) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        q = "SELECT * FROM alerts WHERE last_seen >= datetime('now', ?)"
        params = [f"-{days} days"]
        if source is not None:
            q += " AND source = ?"
            params.append(source)
        q += " ORDER BY last_seen DESC"
        return [dict(r) for r in self.db.execute(q, params).fetchall()]

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="alert_manager",
            display_name="Alert Lifecycle Manager",
            purpose=(
                "Closes the alert lifecycle that raise_alert() only ever opened: acknowledge "
                "or resolve a specific alert (human-driven, precise), and auto-resolve alerts "
                "that haven't recurred in a while (periodic, heuristic) — so unresolved alerts "
                "don't just accumulate forever once their real condition has cleared."
            ),
            data_produced=["alert history over a real time window, optionally by source"],
            actions_possible=["acknowledge a specific alert", "resolve a specific alert",
                               "auto-resolve alerts not re-raised in a configurable window"],
            limits_and_safety=(
                "resolve_alert() refuses an already-resolved alert rather than silently "
                "re-writing resolved_at. The automatic sweep is an honest HEURISTIC, not a "
                "guarantee — an alert not re-raised in the window usually means its condition "
                "cleared, but a crashed or stopped module would look identical; auto-resolved "
                "alerts are logged distinguishably from human-resolved ones so this is never "
                "mistaken for a confirmed fix. A genuinely recurring condition raises a real, "
                "fresh alert after resolution (raise_alert()'s dedup only matches unresolved "
                "rows) — resolving never permanently suppresses anything."
            ),
            example_questions=["What alerts fired this week?", "Resolve the stale sensor alert from Cell A."],
            verification_evidence=[
                "scenarios.py::scenario_alert_manager_resolve — confirmed resolve_alert() sets "
                "resolved/resolved_at on a real alert, and refuses an already-resolved one",
                "scenarios.py::scenario_alert_manager_acknowledge — confirmed acknowledge_alert() "
                "sets acknowledged/acknowledged_at on a real alert",
                "scenarios.py::scenario_alert_manager_stale_sweep — confirmed check_stale_alerts() "
                "resolves a real alert whose last_seen is past the window, and leaves a "
                "recently-seen one alone",
                "scenarios.py::scenario_alert_manager_recurrence_after_resolution — confirmed a "
                "genuinely recurring (source, message) condition raises a real NEW alert after "
                "the prior one was resolved, rather than being silently suppressed forever",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # record-keeping only, no hardware of its own
