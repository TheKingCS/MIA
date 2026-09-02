"""
MIA Homestead — MIA Home Sync
v0.1

Automates the transport half of docs/MIA_HOME_SYNC_PLAN.md that doc
deliberately left manual: getting viewer/home_snapshot.json from this
system onto MIA Home's watched folder
(core/homestead_manager.py, ~/Projects/MIA). Everything on both sides
of that plan was already real and working (verified 2026-09-02,
end-to-end, against a real export) — the only missing piece was a
human remembering to copy the file. User asked for this specifically
(2026-09-02): "we should automate transport."

Uses rsync, not a bare file copy, specifically because rsync already
handles BOTH forms of `destination` with the exact same command: a
plain local path (today's actual reality — Homestead and MIA Home live
on the same machine in this dev environment) and a `user@host:path`
remote (real deployment's actual reality — once Homestead's Pi and
Home's Ryzen/Radeon desktop, per that plan doc's own "Hardware
target — resolved" section, are physically separate machines). Moving
from dev to real deployment is a one-line config change, not a code
change.

Deliberately NOT a MiaHomesteadModule, same reasoning
core/irrigation.py's own docstring already gives for the identical
choice: this has no sensor "reading" that can go stale, so forcing it
through that base class's run_cycle() would mean either overriding it
(defeating the point) or a permanent, meaningless "all sensors
stale" CRITICAL every cycle — the exact wart
modules.self_preservation.SelfPreservationModule's presence-sensor-
optional design used to have, fixed earlier this same session, not
worth deliberately reintroducing here. This is a periodic check
instead, called from main.py's existing loop.

Config (config/mia_home_sync.yaml, same "config IS the source of
truth for physical/deployment setup" precedent as
config/irrigation_schedules.yaml and config/location.yaml): a null
`destination` means sync simply doesn't run — honestly skipped, never
guessed, same precedent as location.yaml's weather-check gate.
"""

import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from contracts.capability import Describable
from contracts.mia_homestead_contract import raise_alert

logger = logging.getLogger("mia_homestead.mia_home_sync")

DEFAULT_INTERVAL_MINUTES = 5
RSYNC_TIMEOUT_SECONDS = 15


class MiaHomeSync(Describable):
    def __init__(self, db_conn, config_path: str = "config/mia_home_sync.yaml", notifier=None):
        self.db = db_conn
        self.notifier = notifier
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        import yaml
        if not self.config_path.exists():
            return {}
        return yaml.safe_load(self.config_path.read_text()) or {}

    @property
    def destination(self) -> str | None:
        return self._config.get("destination") or None

    @property
    def interval_minutes(self) -> int:
        return self._config.get("interval_minutes", DEFAULT_INTERVAL_MINUTES)

    def is_due(self) -> bool:
        """The same heartbeat row backs BOTH pacing questions — 'was
        the last successful sync recent enough' and 'did we just try
        and shouldn't hammer an unreachable host again yet' — since
        _do_sync() below writes it on every attempt, not just success.
        A single mechanism, not two, for the same real question."""
        row = self.db.execute(
            "SELECT last_seen FROM system_heartbeat WHERE component = 'mia_home_sync' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return True
        last = datetime.fromisoformat(row[0])
        return datetime.utcnow() - last >= timedelta(minutes=self.interval_minutes)

    def maybe_sync(self, snapshot_path: str = "viewer/home_snapshot.json") -> dict | None:
        """Called every main.py cycle (cheap — a config check plus,
        usually, one date comparison; only shells out to rsync once
        interval_minutes has genuinely elapsed). Returns None when
        sync isn't configured or isn't due yet (both honest no-ops,
        not failures); a real result dict {"success": bool, ...}
        whenever a push was actually attempted."""
        if self.destination is None:
            return None
        if not self.is_due():
            return None
        return self._do_sync(snapshot_path)

    def _do_sync(self, snapshot_path: str) -> dict:
        # Written on every attempt, success or failure — see is_due()'s
        # own comment for why one heartbeat paces both cases.
        self.db.execute(
            "INSERT INTO system_heartbeat (component, last_seen) VALUES ('mia_home_sync', datetime('now'))"
        )
        self.db.commit()

        src = Path(snapshot_path)
        if not src.exists():
            # The export hasn't run yet this process's lifetime (e.g.
            # right at startup) — not a real failure, nothing to push.
            return {"success": False, "reason": "no snapshot file yet"}

        try:
            result = subprocess.run(
                ["rsync", "-az", str(src), self.destination],
                capture_output=True, text=True, timeout=RSYNC_TIMEOUT_SECONDS,
            )
        except (subprocess.SubprocessError, OSError) as e:
            self._record_failure(str(e))
            return {"success": False, "reason": str(e)}

        if result.returncode != 0:
            detail = result.stderr.strip() or f"rsync exited {result.returncode}"
            self._record_failure(detail)
            return {"success": False, "reason": detail}

        logger.info("Synced home_snapshot.json to MIA Home (%s)", self.destination)
        return {"success": True}

    def _record_failure(self, detail: str) -> None:
        # A real, expected operational condition for something that
        # depends on a network link between two separate machines
        # (host unreachable, SSH key not provisioned yet, disk full on
        # the other end) — surfaced as a warning, never a crash. Reuses
        # raise_alert()'s own dedup (same message = one row, occurrence_
        # count bumping) so a sustained outage doesn't spam the alerts
        # table, and alert_manager's existing stale sweep auto-resolves
        # it once pushes start succeeding again and it stops re-firing.
        raise_alert(
            self.db, "mia_home_sync", "warning",
            f"mia_home_sync: push to MIA Home ({self.destination}) failed — {detail}",
            self.notifier,
        )
        logger.warning("MIA Home sync failed: %s", detail)

    def get_status(self) -> dict:
        """Read-only — for conversational status checks. Never
        triggers a sync itself (same "a question shouldn't have a side
        effect" discipline as DeadMansSwitchMonitor.get_status())."""
        row = self.db.execute(
            "SELECT last_seen FROM system_heartbeat WHERE component = 'mia_home_sync' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return {
            "configured": self.destination is not None,
            "destination": self.destination,
            "interval_minutes": self.interval_minutes,
            "last_attempt": row[0] if row else None,
        }

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="mia_home_sync",
            display_name="MIA Home Sync",
            purpose=(
                "Automatically pushes this system's summarized state export "
                "(viewer/home_snapshot.json) to MIA Home's watched-folder ingestion "
                "(core/homestead_manager.py in ~/Projects/MIA), on a configurable interval — "
                "closes the one manual step docs/MIA_HOME_SYNC_PLAN.md's own transport "
                "design deliberately left for a human to do by hand."
            ),
            data_produced=["a system_heartbeat row per sync attempt, for real staleness visibility"],
            actions_possible=["push the current snapshot to the configured destination via rsync"],
            limits_and_safety=(
                "Does nothing at all when config/mia_home_sync.yaml's destination is unset — "
                "honestly skipped, never guessed. A push failure (host unreachable, SSH key not "
                "provisioned, destination full) raises a real, deduplicated warning alert and is "
                "retried on the next interval — never crashes the control loop over a transport "
                "problem. Read-only on the Homestead side: only ever reads viewer/home_snapshot.json, "
                "never writes to it or to anything on the remote end beyond the one file rsync pushes."
            ),
            example_questions=["Is the MIA Home sync working?", "When did we last successfully sync to MIA Home?"],
            verification_evidence=[
                "scenarios.py::scenario_mia_home_sync_honest_skip_when_unconfigured — confirmed "
                "maybe_sync() does nothing at all with no destination configured",
                "scenarios.py::scenario_mia_home_sync_pushes_via_rsync — confirmed a real rsync "
                "push to a real local destination actually delivers the file",
                "scenarios.py::scenario_mia_home_sync_paces_by_interval — confirmed is_due() "
                "correctly gates on interval_minutes using the real heartbeat row",
                "scenarios.py::scenario_mia_home_sync_failure_raises_alert — confirmed a real "
                "failed push (unreachable destination) raises a real warning alert rather than "
                "crashing",
                "Live-verified 2026-09-02 against the real running system and the real MIA repo — "
                "see CLAUDE.md's current-state entry for this fix.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # rsync/ssh are software already required on the Pi; no new part
