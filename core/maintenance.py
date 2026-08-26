"""
MIA Homestead — Maintenance Manager
v0.1

Two ways tasks get created:
1. Manually / via the assistant — "assign a task to swap the MCU",
   "log that the greenhouse roof is leaking."
2. Automatically — sensor calibration due dates and recurring
   maintenance schedules (e.g. "replace dosing tubing every 180 days")
   generate tasks on their own, so nothing falls through the cracks
   just because no one thought to check.
"""

import logging
import sqlite3
from datetime import datetime, timedelta

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.maintenance")

VALID_PRIORITIES = ("low", "medium", "high", "critical")
VALID_TASK_TYPES = ("repair", "replacement", "calibration", "inspection", "other")


class MaintenanceManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def create_task(
        self, title: str, task_type: str, description: str = None,
        priority: str = "medium", related_asset_type: str = None,
        related_asset_id: int = None, assigned_to: str = None,
        due_date: str = None, created_by: str = "human",
    ) -> int:
        if task_type not in VALID_TASK_TYPES:
            raise ValueError(f"task_type must be one of {VALID_TASK_TYPES}")
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {VALID_PRIORITIES}")

        cur = self.db.execute(
            """
            INSERT INTO maintenance_tasks
            (title, description, task_type, priority, related_asset_type,
             related_asset_id, assigned_to, due_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, task_type, priority, related_asset_type,
             related_asset_id, assigned_to, due_date, created_by),
        )
        self.db.commit()
        task_id = cur.lastrowid
        logger.info("Task created: #%s '%s' (priority=%s)", task_id, title, priority)

        if priority in ("high", "critical") and self.notifier:
            self.notifier.dispatch(
                "warning" if priority == "high" else "critical",
                f"Maintenance task created: {title}"
                + (f" — assigned to {assigned_to}" if assigned_to else ""),
                source="maintenance",
            )
        return task_id

    def assign_task(self, task_id: int, assigned_to: str) -> None:
        self.db.execute(
            "UPDATE maintenance_tasks SET assigned_to = ? WHERE id = ?",
            (assigned_to, task_id),
        )
        self.db.commit()

    def update_status(self, task_id: int, status: str) -> None:
        if status not in ("open", "in_progress", "done", "cancelled"):
            raise ValueError("invalid status")
        completed_at = "datetime('now')" if status == "done" else "NULL"
        self.db.execute(
            f"UPDATE maintenance_tasks SET status = ?, completed_at = {completed_at} WHERE id = ?",
            (status, task_id),
        )
        self.db.commit()

    def list_open_tasks(self, priority: str = None) -> list[dict]:
        q = "SELECT * FROM maintenance_tasks WHERE status IN ('open', 'in_progress')"
        params = ()
        if priority:
            q += " AND priority = ?"
            params = (priority,)
        q += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 " \
             "WHEN 'medium' THEN 2 ELSE 3 END, due_date IS NULL, due_date ASC"
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    # ---------- Automatic generation ----------

    def generate_calibration_tasks(self) -> int:
        """Scans sensors with an overdue calibration_due date and creates
        a task if one doesn't already exist for that sensor. Returns
        count of tasks created."""
        rows = self.db.execute(
            "SELECT id, type, cell_id FROM sensors "
            "WHERE active = 1 AND calibration_due IS NOT NULL "
            "AND calibration_due <= date('now')"
        ).fetchall()

        created = 0
        for sensor_id, sensor_type, cell_id in rows:
            existing = self.db.execute(
                "SELECT id FROM maintenance_tasks WHERE related_asset_type = 'sensor' "
                "AND related_asset_id = ? AND status IN ('open', 'in_progress') "
                "AND task_type = 'calibration'",
                (sensor_id,),
            ).fetchone()
            if existing:
                continue
            self.create_task(
                title=f"Calibrate {sensor_type} sensor (cell {cell_id})",
                task_type="calibration",
                priority="medium",
                related_asset_type="sensor",
                related_asset_id=sensor_id,
                created_by="system",
            )
            created += 1
        return created

    def generate_recurring_tasks(self) -> int:
        """Checks maintenance_schedules for anything due, creates a task,
        and advances next_due_at by the configured interval."""
        rows = self.db.execute(
            "SELECT id, title, task_type, related_asset_type, related_asset_id, interval_days "
            "FROM maintenance_schedules WHERE auto_create = 1 AND next_due_at <= datetime('now')"
        ).fetchall()

        created = 0
        for sched_id, title, task_type, asset_type, asset_id, interval_days in rows:
            self.create_task(
                title=title, task_type=task_type, priority="medium",
                related_asset_type=asset_type, related_asset_id=asset_id,
                created_by="system",
            )
            next_due = (datetime.utcnow() + timedelta(days=interval_days)).isoformat()
            self.db.execute(
                "UPDATE maintenance_schedules SET last_generated_at = datetime('now'), "
                "next_due_at = ? WHERE id = ?",
                (next_due, sched_id),
            )
            self.db.commit()
            created += 1
        return created

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="maintenance",
            display_name="Maintenance Manager",
            purpose=(
                "Tracks repair/replacement/calibration tasks — created "
                "manually (e.g. 'swap the MCU') or automatically from "
                "sensor calibration due-dates and recurring schedules "
                "(e.g. replace dosing tubing every 180 days)."
            ),
            data_produced=["open task list with priority and assignment"],
            actions_possible=[
                "create a task", "assign a task", "mark a task done",
                "auto-generate overdue calibration tasks",
                "auto-generate recurring maintenance tasks",
            ],
            limits_and_safety=(
                "Creating a task doesn't perform the repair — it's a "
                "tracking/reminder layer. High/critical priority tasks "
                "trigger a notification the same way safety alerts do."
            ),
            example_questions=[
                "Any open repair tasks?", "What's overdue for calibration?",
                "Assign someone to fix the leak by the sump",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software — task tracking needs no hardware of its own

    def add_recurring_schedule(
        self, title: str, task_type: str, interval_days: int,
        related_asset_type: str = None, related_asset_id: int = None,
        start_date: str = None,
    ) -> int:
        next_due = start_date or datetime.utcnow().isoformat()
        cur = self.db.execute(
            """
            INSERT INTO maintenance_schedules
            (title, task_type, related_asset_type, related_asset_id, interval_days, next_due_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, task_type, related_asset_type, related_asset_id, interval_days, next_due),
        )
        self.db.commit()
        return cur.lastrowid
