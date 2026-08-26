"""
MIA Homestead — Periodic Self-Report
v0.1

Compiles what would otherwise be several separate assistant questions
into one digest: yields, dosing pattern, open issues, pending
approvals, hardware needs, upcoming maintenance. Almost entirely a
matter of composing data sources that already exist — the
infrastructure work was already done by everything built before this.
"""

import logging
import sqlite3
from datetime import datetime

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.report_generator")


class ReportGenerator(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def generate_report(self, days: int = 7) -> str:
        lines = [f"=== State of the Greenhouse — {datetime.utcnow().strftime('%Y-%m-%d')} ==="]

        yields = self.db.execute(
            "SELECT item, SUM(quantity) as total, unit FROM yield_events "
            "WHERE timestamp >= datetime('now', ?) GROUP BY item, unit",
            (f"-{days} days",),
        ).fetchall()
        if yields:
            lines.append(f"\nYield (last {days}d):")
            for item, total, unit in yields:
                lines.append(f"  {total}{unit or ''} {item}")
        else:
            lines.append(f"\nYield (last {days}d): none recorded")

        dosing = self.db.execute(
            "SELECT dose_type, COUNT(*) FROM dosing_events WHERE timestamp >= datetime('now', ?) "
            "GROUP BY dose_type",
            (f"-{days} days",),
        ).fetchall()
        if dosing:
            lines.append(f"\nDosing activity (last {days}d):")
            for dose_type, count in dosing:
                lines.append(f"  {dose_type}: {count} dose(s)")

        open_alerts = self.db.execute(
            "SELECT severity, COUNT(*) FROM alerts WHERE resolved = 0 GROUP BY severity"
        ).fetchall()
        if open_alerts:
            lines.append("\nOpen alerts:")
            for severity, count in open_alerts:
                lines.append(f"  {severity}: {count}")
        else:
            lines.append("\nOpen alerts: none")

        pending_orders = self.db.execute(
            "SELECT COUNT(*) FROM inventory_orders WHERE status = 'proposed'"
        ).fetchone()[0]
        pending_params = self.db.execute(
            "SELECT COUNT(*) FROM parameter_change_proposals WHERE status = 'proposed'"
        ).fetchone()[0]
        if pending_orders or pending_params:
            lines.append(f"\nAwaiting your approval: {pending_orders} order(s), "
                        f"{pending_params} experiment recommendation(s)")

        open_tasks = self.db.execute(
            "SELECT COUNT(*) FROM maintenance_tasks WHERE status IN ('open', 'in_progress')"
        ).fetchone()[0]
        if open_tasks:
            lines.append(f"\nOpen maintenance tasks: {open_tasks}")

        running_experiments = self.db.execute(
            "SELECT COUNT(*) FROM experiments WHERE status = 'running'"
        ).fetchone()[0]
        if running_experiments:
            lines.append(f"\nExperiments currently running: {running_experiments}")

        return "\n".join(lines)

    def generate_and_send(self, days: int = 7) -> int:
        content = self.generate_report(days=days)
        cur = self.db.execute("INSERT INTO daily_reports (content) VALUES (?)", (content,))
        self.db.commit()
        if self.notifier:
            self.notifier.dispatch("info", content, source="report_generator")
        logger.info("Report #%s generated and sent", cur.lastrowid)
        return cur.lastrowid

    def hours_since_last_report(self) -> float | None:
        row = self.db.execute("SELECT generated_at FROM daily_reports ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        last = datetime.fromisoformat(row[0])
        return (datetime.utcnow() - last).total_seconds() / 3600

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="report_generator",
            display_name="Periodic Self-Report",
            purpose=(
                "Compiles a state-of-the-greenhouse digest — yields, dosing pattern, open "
                "alerts, pending approvals, maintenance, running experiments — into one report "
                "instead of requiring several separate questions."
            ),
            data_produced=["report history"],
            actions_possible=["generate a report on demand", "generate and send via notification"],
            limits_and_safety=(
                "Purely a summarization/composition layer over existing data — never takes "
                "action, never makes a decision, just makes the existing picture easier to see at once."
            ),
            example_questions=["Give me a report", "What's the state of the greenhouse this week?"],
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed the report correctly compiles real "
                "yield, dosing, and alert data into one digest, and hours_since_last_report() "
                "correctly transitions from None (never sent) to a real elapsed time after "
                "generate_and_send()",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software
