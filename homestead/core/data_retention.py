"""
MIA Homestead — Data Retention
v0.1

Real gap found live 2026-09-02: schema/mia_homestead_schema.sql's own
header promises "this node may run for weeks with no human interaction
— nothing here should require manual cleanup to keep working," but
sensor_readings, actuator_events, power_telemetry, and system_heartbeat
— the four highest-frequency tables, all append-only, all with zero
pruning anywhere in the codebase (confirmed by grep: no DELETE, no
VACUUM, nothing) — would grow completely unbounded forever.
sensor_readings alone had 148,240 rows after roughly two days of
(heavily test-churned) development, not even a real deployment yet. A
real multi-month unattended deployment would eventually mean a
multi-gigabyte SQLite file and degrading query performance, with
nothing telling anyone it was happening — silent, not loud, which is
the worst kind of failure for a system meant to run itself.

Deliberately simple: periodic DELETE of rows past a retention window,
not aggregation/downsampling. Checked what actually reads these tables
first, not guessed: core/trend_analyzer.py and modules/power_monitor.py
both look back by READING COUNT (a fixed number of recent rows), never
by date; core/leak_detector.py only ever needs the 2 most recent
readings; every assistant history tool takes a `days` parameter that
defaults to 7-30. Nothing currently built looks back further than a
few weeks for any real analytical purpose, so a 90-day window is
generous, not a guess dressed up as analysis. If a future feature
genuinely needs long-term historical trends, that's real new scope (a
rollup/aggregation table) — not something to half-build here.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.data_retention")

DEFAULT_RETENTION_DAYS = 90

# (table, timestamp_column) — the four unbounded, append-only,
# high-frequency tables found with zero pruning anywhere. Every other
# table in this schema is either bounded by nature (one row per real
# entity) or already has its own real lifecycle (alerts via
# core/alert_manager.py, maintenance_tasks via status transitions).
RETAINED_TABLES = [
    ("sensor_readings", "timestamp"),
    ("actuator_events", "timestamp"),
    ("power_telemetry", "timestamp"),
    ("system_heartbeat", "last_seen"),
]


class DataRetentionManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def prune_old_data(self, retention_days: int = DEFAULT_RETENTION_DAYS) -> dict:
        """Called periodically (main.py's existing 60-cycle block —
        this is a long-timescale housekeeping pass, not a per-cycle
        safety check). Deletes rows older than retention_days from each
        of the four unbounded tables. Returns {table: rows_deleted},
        only including tables that actually had something to delete."""
        deleted = {}
        for table, ts_col in RETAINED_TABLES:
            cur = self.db.execute(
                f"DELETE FROM {table} WHERE {ts_col} < datetime('now', ?)",
                (f"-{retention_days} days",),
            )
            if cur.rowcount > 0:
                deleted[table] = cur.rowcount
        if deleted:
            self.db.commit()
            from core.action_log import log_action
            log_action(
                self.db, "data_retention", "old_data_pruned",
                f"Pruned data older than {retention_days} days: "
                + ", ".join(f"{t}={n}" for t, n in deleted.items()),
            )
            logger.info("Pruned old data (retention=%dd): %s", retention_days, deleted)
        return deleted

    def get_table_sizes(self) -> dict:
        """Read-only visibility into what's actually accumulating —
        the same check that found this gap live, made a real,
        repeatable tool instead of a one-off manual query."""
        return {
            table: self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table, _ in RETAINED_TABLES
        }

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="data_retention",
            display_name="Data Retention",
            purpose=(
                f"Periodically prunes the four unbounded, append-only, high-frequency tables "
                f"(sensor_readings, actuator_events, power_telemetry, system_heartbeat) — "
                f"nothing else in this codebase ever cleaned these up, and they'd otherwise grow "
                f"forever on a system meant to run for weeks/months unattended."
            ),
            data_produced=["current row count per retained table, for real visibility into growth"],
            actions_possible=[f"delete rows older than a configurable window (default {DEFAULT_RETENTION_DAYS} days)"],
            limits_and_safety=(
                f"Deletes are permanent — this trades old raw telemetry for bounded disk/query "
                f"cost, on the confirmed basis that nothing currently built (trend_analyzer, "
                f"leak_detector, power forecasting, every history tool) looks back further than "
                f"a few weeks. {DEFAULT_RETENTION_DAYS} days is a real, deliberate choice, not a "
                f"calibrated one — widen it if a future feature needs longer history. Only prunes "
                f"the four tables confirmed to have no other lifecycle management; never touches "
                f"alerts (core/alert_manager.py), maintenance_tasks, or any other real record."
            ),
            example_questions=["How big is the sensor history getting?", "When was old data last cleaned up?"],
            verification_evidence=[
                "scenarios.py::scenario_data_retention_prunes_old_rows — confirmed a real row "
                "older than the retention window is deleted, a recent one is kept",
                "scenarios.py::scenario_data_retention_noop_when_nothing_old — confirmed a run "
                "with nothing past the window deletes nothing and logs nothing",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure housekeeping, no hardware of its own
