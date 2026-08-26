"""
MIA Homestead — Backup & Rollback Manager
v0.1

Two related things this does:

1. Snapshot/restore of CONFIGURATION — not operational history. Files
   (config/modules.yaml, config/layout.json, device role YAMLs,
   plumbing.yaml) plus the DB tables that represent live control
   parameters (target_overrides, dosing_limits, device_registrations,
   maintenance_schedules). Deliberately does NOT touch alerts,
   sensor_readings, yield_events, experiments, or species_profiles —
   those are history and earned knowledge, not configuration, and
   rolling them back would be actively dishonest about what happened.

2. Automatic rollback when an update looks like it made things worse —
   snapshot before applying a change, watch for a spike in critical
   alerts within a validation window, and revert on its own if the
   spike is real. This is the "notices issues after an update" half of
   the request, and it's the same self-preservation instinct as the
   rest of this system: fail toward the last known-good state, not
   toward hoping it's fine.
"""

import json
import logging
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.backup_manager")

ROOT = Path(__file__).parent.parent
BACKUPS_DIR = ROOT / "backups"

CONFIG_FILES = [
    "config/modules.yaml",
    "config/layout.json",
    "config/infrastructure/plumbing.yaml",
]

# DB tables that represent live CONTROL PARAMETERS, not history —
# these are what gets exported/restored. Deliberately excludes alerts,
# sensor_readings, yield_events, experiments, species_profiles.
CONFIG_TABLES = ["target_overrides", "dosing_limits", "device_registrations", "maintenance_schedules"]


class BackupManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier
        BACKUPS_DIR.mkdir(exist_ok=True)

    # ---------- Snapshotting ----------

    def create_snapshot(self, label: str, reason: str = None, is_auto_pre_update: bool = False) -> int:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        snapshot_name = f"{timestamp}_{label.replace(' ', '_')}"
        snapshot_dir = BACKUPS_DIR / snapshot_name
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        for rel_path in CONFIG_FILES:
            src = ROOT / rel_path
            if src.exists():
                dst = snapshot_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        for src in ROOT.glob("config/devices/roles/*.yaml"):
            rel = src.relative_to(ROOT)
            dst = snapshot_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        db_export = {}
        for table in CONFIG_TABLES:
            self.db.row_factory = sqlite3.Row
            rows = self.db.execute(f"SELECT * FROM {table}").fetchall()
            db_export[table] = [dict(r) for r in rows]
        (snapshot_dir / "db_config_export.json").write_text(json.dumps(db_export, indent=2, default=str))

        git_commit = self._current_git_commit()

        cur = self.db.execute(
            "INSERT INTO config_snapshots (label, reason, git_commit, snapshot_dir, is_auto_pre_update) "
            "VALUES (?, ?, ?, ?, ?)",
            (label, reason, git_commit, str(snapshot_dir), int(is_auto_pre_update)),
        )
        self.db.commit()
        snapshot_id = cur.lastrowid
        logger.info("Snapshot #%s created: %s (git: %s)", snapshot_id, label, git_commit or "not a git repo")
        return snapshot_id

    def _current_git_commit(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT,
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    # ---------- Restoring ----------

    def restore_snapshot(self, snapshot_id: int) -> dict:
        row = self.db.execute(
            "SELECT label, snapshot_dir, git_commit FROM config_snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"no snapshot {snapshot_id}")
        label, snapshot_dir, git_commit = row
        snapshot_path = Path(snapshot_dir)

        restored_files = []
        for rel_path in CONFIG_FILES:
            src = snapshot_path / rel_path
            if src.exists():
                dst = ROOT / rel_path
                shutil.copy2(src, dst)
                restored_files.append(rel_path)

        for src in snapshot_path.glob("config/devices/roles/*.yaml"):
            rel = src.relative_to(snapshot_path)
            dst = ROOT / rel
            shutil.copy2(src, dst)
            restored_files.append(str(rel))

        db_export_path = snapshot_path / "db_config_export.json"
        restored_tables = []
        if db_export_path.exists():
            db_export = json.loads(db_export_path.read_text())
            for table, rows in db_export.items():
                self.db.execute(f"DELETE FROM {table}")
                for row_dict in rows:
                    cols = ", ".join(row_dict.keys())
                    placeholders = ", ".join("?" for _ in row_dict)
                    self.db.execute(
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                        list(row_dict.values()),
                    )
                restored_tables.append(table)
            self.db.commit()

        logger.warning("Restored snapshot #%s (%s) — files: %s, tables: %s",
                        snapshot_id, label, restored_files, restored_tables)
        if self.notifier:
            self.notifier.dispatch(
                "warning",
                f"Configuration restored from snapshot #{snapshot_id} ({label}). "
                f"Note: this reverted CONFIG only — code changes (git commit at snapshot "
                f"time: {git_commit or 'unknown'}) were NOT touched. If the issue is in "
                f"code rather than config, this rollback won't fix it.",
                source="backup_manager",
            )
        return {"restored_files": restored_files, "restored_tables": restored_tables, "git_commit_at_snapshot": git_commit}

    def list_snapshots(self) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM config_snapshots ORDER BY created_at DESC"
        ).fetchall()]

    # ---------- Automatic post-update watch ----------

    def start_update_watch(self, pre_update_snapshot_id: int, validation_window_minutes: int = 30,
                            critical_alert_threshold: int = 2) -> int:
        """Call this right after applying a config change you've
        already snapshotted. Establishes a baseline critical-alert
        count and watches for a spike over the validation window."""
        baseline = self.db.execute(
            "SELECT COUNT(*) FROM alerts WHERE severity = 'critical'"
        ).fetchone()[0]
        cur = self.db.execute(
            "INSERT INTO update_watches (pre_update_snapshot_id, validation_window_minutes, "
            "critical_alert_baseline, critical_alert_threshold) VALUES (?, ?, ?, ?)",
            (pre_update_snapshot_id, validation_window_minutes, baseline, critical_alert_threshold),
        )
        self.db.commit()
        logger.info("Update watch #%s started (baseline: %d critical alerts, window: %dmin)",
                    cur.lastrowid, baseline, validation_window_minutes)
        return cur.lastrowid

    def check_update_watches(self) -> list[dict]:
        """Call periodically (main.py). For each active watch: if the
        validation window has passed with no critical-alert spike, mark
        it confirmed good. If a spike happened WITHIN the window,
        auto-rollback immediately — don't wait for the window to close,
        a real problem shouldn't get 30 minutes to keep going wrong."""
        results = []
        rows = self.db.execute(
            "SELECT id, pre_update_snapshot_id, applied_at, validation_window_minutes, "
            "critical_alert_baseline, critical_alert_threshold FROM update_watches WHERE status = 'watching'"
        ).fetchall()

        for watch_id, snapshot_id, applied_at, window_min, baseline, threshold in rows:
            current_critical = self.db.execute(
                "SELECT COUNT(*) FROM alerts WHERE severity = 'critical' AND timestamp >= ?",
                (applied_at,),
            ).fetchone()[0]

            if current_critical >= threshold:
                self.restore_snapshot(snapshot_id)
                self.db.execute(
                    "UPDATE update_watches SET status = 'auto_rolled_back', resolved_at = datetime('now'), "
                    "resolution_note = ? WHERE id = ?",
                    (f"{current_critical} critical alert(s) since update, threshold was {threshold}", watch_id),
                )
                self.db.commit()
                logger.critical("Update watch #%s: AUTO-ROLLED BACK — %d critical alerts since update (threshold %d)",
                                 watch_id, current_critical, threshold)
                if self.notifier:
                    self.notifier.dispatch(
                        "critical",
                        f"Automatically rolled back a recent config change — {current_critical} critical "
                        f"alert(s) appeared since it was applied. Restored snapshot #{snapshot_id}.",
                        source="backup_manager",
                    )
                results.append({"watch_id": watch_id, "outcome": "auto_rolled_back", "critical_count": current_critical})
                continue

            applied_dt = datetime.fromisoformat(applied_at)
            if datetime.utcnow() - applied_dt > timedelta(minutes=window_min):
                self.db.execute(
                    "UPDATE update_watches SET status = 'confirmed_good', resolved_at = datetime('now'), "
                    "resolution_note = 'validation window passed with no critical alert spike' WHERE id = ?",
                    (watch_id,),
                )
                self.db.commit()
                results.append({"watch_id": watch_id, "outcome": "confirmed_good"})

        return results

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="backup_manager",
            display_name="Backup & Rollback Manager",
            purpose=(
                "Snapshots configuration (files + live control parameters, not history) "
                "before changes, restores on demand, and automatically rolls back a "
                "recent config change if critical alerts spike shortly after it was applied."
            ),
            data_produced=["snapshot history", "update watch status"],
            actions_possible=["create a snapshot", "restore a snapshot", "start an update watch"],
            limits_and_safety=(
                "Only restores CONFIGURATION (files + control-parameter DB tables) — never "
                "alerts, sensor history, yield/experiment records, or species knowledge. "
                "Auto-rollback triggers on a critical-alert spike within a validation "
                "window, then stops watching — it does not repeatedly roll back the same "
                "thing. A rollback reverts config only, never code — if a code change is "
                "the actual cause, this won't fix it, and says so explicitly."
            ),
            example_questions=["What snapshots exist?", "Roll back to before the last change",
                                "Did the last update trigger an auto-rollback?"],
            verification_evidence=[
                "Live manual test 2026-08-26: full end-to-end proof — applied a deliberately "
                "dangerous dosing limit change (10ml -> 500ml max per dose), simulated the "
                "resulting critical alert spike, and confirmed automatic detection and rollback "
                "to the correct baseline value (500 -> 10) with a clear notification",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software — file/DB backup, no hardware of its own
