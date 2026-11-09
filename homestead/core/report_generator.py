"""
MIA Homestead — Periodic Self-Report
v0.1

Compiles what would otherwise be several separate assistant questions
into one digest: yields, dosing pattern, open issues, pending
approvals, hardware needs, upcoming maintenance. Almost entirely a
matter of composing data sources that already exist — the
infrastructure work was already done by everything built before this.
"""

import json
import logging
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.report_generator")

# Deliberately shorter than assistant/greenhouse_assistant.py's
# OLLAMA_REQUEST_TIMEOUT_SECONDS (120s, generous for a cold model load
# in an interactive chat). This call happens inline in main.py's
# control loop, not a chat session someone is actively waiting on — a
# report is worth a bounded best-effort attempt, not worth stalling
# dosing-relevant work for up to two minutes once a day. Falls back to
# the structured digest either way, so a short timeout only costs a
# less-polished report, never a missing one.
NARRATIVE_TIMEOUT_SECONDS = 30


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

    def generate_narrative_report(self, days: int = 7, model: str = None, host: str = None) -> str:
        """Turns the structured digest into 2-4 short natural-language
        paragraphs via the local Ollama model — narrative instead of a
        bullet list, for the automated push notification a human reads
        rather than a chat they're actively driving. Never raises: on
        any failure (Ollama unreachable, timeout, empty response) logs
        a warning and returns the structured digest unchanged, so a
        report always goes out even with no model running.

        The digest is the single source of truth handed to the model,
        and the prompt explicitly forbids adding anything not already
        in it — same grounding stance as
        assistant/greenhouse_assistant.py's `_annotate_if_empty()` for
        empty tool results, applied here to the report as a whole."""
        digest = self.generate_report(days=days)

        from assistant.greenhouse_assistant import OLLAMA_HOST, OLLAMA_MODEL
        model = model or OLLAMA_MODEL
        host = host or OLLAMA_HOST

        prompt = (
            "Rewrite the following structured greenhouse status digest as 2-4 short, "
            "natural, conversational paragraphs a busy person could read at a glance. "
            "Use ONLY the facts given below — do not add, estimate, or infer any number, "
            "date, or claim that isn't explicitly present in the digest. If a section "
            "says 'none' or is missing, say so plainly rather than skipping it silently.\n\n"
            f"{digest}"
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0},
        }
        req = urllib.request.Request(
            f"{host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=NARRATIVE_TIMEOUT_SECONDS) as resp:
                result = json.loads(resp.read())
            narrative = result.get("message", {}).get("content", "").strip()
            if not narrative:
                logger.warning("Narrative report generation returned empty content — using structured digest")
                return digest
            return narrative
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            logger.warning("Narrative report generation failed (%s) — falling back to structured digest", e)
            return digest

    def generate_and_send(self, days: int = 7, narrative: bool = True) -> int:
        content = self.generate_narrative_report(days=days) if narrative else self.generate_report(days=days)
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
                "instead of requiring several separate questions. The automated push notification "
                "(generate_and_send(), no args) rewrites that digest as natural-language prose via "
                "the local Ollama model before sending, so what actually lands in a human's inbox "
                "reads like a briefing, not a bullet-list dump — with an always-safe fallback to "
                "the plain structured digest if the model isn't reachable."
            ),
            data_produced=["report history (narrative prose by default, or the raw structured digest as a fallback)"],
            actions_possible=[
                "generate a report on demand", "generate and send via notification",
                "generate a natural-language narrative version of the report via the local model",
            ],
            limits_and_safety=(
                "Purely a summarization/composition layer over existing data — never takes "
                "action, never makes a decision, just makes the existing picture easier to see at "
                "once. The narrative rewrite is explicitly told to use ONLY facts already in the "
                "structured digest and never raises on failure — an unreachable/slow model "
                "(bounded to a 30s timeout, deliberately shorter than the assistant's own 120s "
                "interactive-chat timeout, since this runs inline in main.py's control loop, not "
                "a chat someone is actively waiting on) silently falls back to the plain digest "
                "rather than skipping the report entirely."
            ),
            example_questions=["Give me a report", "What's the state of the greenhouse this week?"],
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed the report correctly compiles real "
                "yield, dosing, and alert data into one digest, and hours_since_last_report() "
                "correctly transitions from None (never sent) to a real elapsed time after "
                "generate_and_send()",
                "Live manual test 2026-08-30 (narrative rewrite): confirmed generate_narrative_report() "
                "against a real Ollama call produces genuine natural-language prose (not the raw "
                "digest verbatim) that still contains the real underlying numbers; confirmed "
                "pointing at an unreachable host (a closed port) falls back to the exact "
                "structured digest with a logged warning, not an exception or a missing report.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software
