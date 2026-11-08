"""
MIA Homestead — Code Deploy Watch & Auto-Rollback
v0.1

The literal "safe and backed up updates with... auto rebooting to
previous update if system failure" half of the project's own stated
vision (see the user's 2026-08-30 framing) — core/backup_manager.py
already does exactly this shape of thing for CONFIG (snapshot before a
change, watch for a critical-alert spike, auto-revert). This is the
same mechanism applied to CODE, via git, since a config revert
explicitly does NOT touch code (see that module's own restore_snapshot()
docstring: "code changes... were NOT touched. If the issue is in code
rather than config, this rollback won't fix it.") — that gap is exactly
what this module closes.

Two layers work together, deliberately, not two competing designs:

1. THIS module (pure Python, testable without any real hardware) —
   after a deploy, start_deploy_watch() records the previous
   known-good commit and a critical-alert baseline; check_deploy_watches()
   (called periodically from main.py) reverts the working tree to that
   commit if a real spike follows, exactly like backup_manager's config
   watch. It does NOT restart the running process itself — checking out
   old files on disk doesn't retroactively change code a Python process
   already has loaded in memory.
2. A systemd unit (deploy/mia-homestead.service, deploy/README.md) —
   Restart=on-failure + crash-loop limits, so once main.py's control
   loop sees this module's watch result and exits (main.py's own
   decision, not this module's — a service method shouldn't unilaterally
   kill the process it's called from), systemd brings the process back
   up running whatever code is now actually on disk — the reverted
   version, after a rollback. This also covers the case layer 1 cannot:
   a deploy so broken the process won't even start, where no Python is
   running to watch itself at all.

Never silently discards uncommitted work to force a rollback through —
see _rollback_to_commit()'s docstring.
"""

import logging
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.deploy_manager")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DeployManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None, repo_path: str = None):
        self.db = db_conn
        self.notifier = notifier
        # repo_path is overridable specifically so this can be tested
        # against a disposable scratch git repo rather than ever
        # running a real checkout against the actual project working
        # tree during a test.
        self.repo_path = Path(repo_path) if repo_path else _PROJECT_ROOT

    # ---------- Git primitives ----------

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.repo_path), *args],
            capture_output=True, text=True, timeout=10, check=check,
        )

    def current_commit(self) -> str | None:
        try:
            result = self._run_git("rev-parse", "HEAD", check=False)
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.SubprocessError, OSError):
            return None

    def _rollback_to_commit(self, commit: str) -> bool:
        """Reverts the working tree to `commit`. Never silently
        discards uncommitted work to get there: if the tree is dirty,
        stashes everything first (including untracked files) with a
        message naming why, THEN force-checks-out — a human can
        `git stash pop` to recover it later if it turns out to matter.
        A plain non-force checkout could silently no-op on a dirty
        tree, which would be worse than either option for a mechanism
        whose entire job is to reliably guarantee recovery. Returns
        whether a stash was created."""
        status = self._run_git("status", "--porcelain")
        stashed = bool(status.stdout.strip())
        if stashed:
            self._run_git(
                "stash", "push", "--include-untracked",
                "-m", f"deploy_manager auto-rollback safety stash before reverting to {commit}",
            )
        self._run_git("checkout", "--force", commit)
        return stashed

    # ---------- Marking known-good ----------

    def mark_last_known_good(self, note: str = None) -> int:
        """Records the CURRENT commit as known-good — what a future
        rollback reverts TO. Call this once manually after confirming a
        fresh deploy is healthy, or automatically once a deploy watch's
        validation window passes clean (see check_deploy_watches())."""
        commit = self.current_commit()
        if commit is None:
            raise RuntimeError(f"{self.repo_path} is not a git repository (or git isn't available)")
        cur = self.db.execute(
            "INSERT INTO code_deploys (git_commit, note) VALUES (?, ?)",
            (commit, note),
        )
        self.db.commit()
        logger.info("Marked commit %s as last known-good%s", commit[:8], f" ({note})" if note else "")
        return cur.lastrowid

    def get_last_known_good(self) -> str | None:
        row = self.db.execute("SELECT git_commit FROM code_deploys ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else None

    # ---------- Deploy watch (mirrors backup_manager's config watch) ----------

    def start_deploy_watch(self, validation_window_minutes: int = 30, critical_alert_threshold: int = 2) -> int:
        """Call this right after deploying new code (git pull/checkout +
        process restart) — establishes a critical-alert baseline and
        watches for a spike over the validation window, rolling back to
        the last-known-good commit immediately if one happens. Requires
        mark_last_known_good() to have been called at least once before
        (there must be a real commit to roll back TO) — raises rather
        than silently watching toward nothing."""
        rollback_target = self.get_last_known_good()
        if rollback_target is None:
            raise ValueError(
                "No last-known-good commit recorded yet — call mark_last_known_good() "
                "once, manually, after confirming the current code is healthy, before "
                "the first deploy watch can have anything real to roll back to."
            )
        baseline = self.db.execute("SELECT COUNT(*) FROM alerts WHERE severity = 'critical'").fetchone()[0]
        cur = self.db.execute(
            "INSERT INTO code_update_watches (rollback_git_commit, validation_window_minutes, "
            "critical_alert_baseline, critical_alert_threshold) VALUES (?, ?, ?, ?)",
            (rollback_target, validation_window_minutes, baseline, critical_alert_threshold),
        )
        self.db.commit()
        logger.info(
            "Deploy watch #%s started (rollback target: %s, baseline: %d critical alerts, window: %dmin)",
            cur.lastrowid, rollback_target[:8], baseline, validation_window_minutes,
        )
        return cur.lastrowid

    def check_deploy_watches(self) -> list[dict]:
        """Call periodically (main.py) — same logic as
        backup_manager.check_update_watches(): if the window passed
        clean, mark it confirmed AND record the current commit as the
        new last-known-good (a clean deploy becomes the new rollback
        target for whatever comes next). If a critical-alert spike
        happens within the window, roll back immediately — don't make a
        real problem wait out the rest of the window.

        Returns one dict per resolved watch this call, each with an
        'outcome' key main.py uses to decide whether to exit the
        process (this method deliberately does NOT do that itself —
        see the module docstring for why that decision belongs to the
        control loop, not a service method)."""
        results = []
        rows = self.db.execute(
            "SELECT id, rollback_git_commit, applied_at, validation_window_minutes, "
            "critical_alert_baseline, critical_alert_threshold FROM code_update_watches "
            "WHERE status = 'watching'"
        ).fetchall()

        for watch_id, rollback_commit, applied_at, window_min, baseline, threshold in rows:
            current_critical = self.db.execute(
                "SELECT COUNT(*) FROM alerts WHERE severity = 'critical' AND timestamp >= ?",
                (applied_at,),
            ).fetchone()[0]

            if current_critical >= threshold:
                stashed = self._rollback_to_commit(rollback_commit)
                self.db.execute(
                    "UPDATE code_update_watches SET status = 'auto_rolled_back', resolved_at = datetime('now'), "
                    "resolution_note = ? WHERE id = ?",
                    (f"{current_critical} critical alert(s) since deploy, threshold was {threshold}"
                     + (" — uncommitted changes were stashed, not lost" if stashed else ""), watch_id),
                )
                self.db.commit()
                logger.critical(
                    "Deploy watch #%s: AUTO-ROLLED BACK to %s — %d critical alert(s) since deploy "
                    "(threshold %d). Process restart required to run the reverted code.",
                    watch_id, rollback_commit[:8], current_critical, threshold,
                )
                if self.notifier:
                    self.notifier.dispatch(
                        "critical",
                        f"Automatically rolled back a recent code deploy — {current_critical} critical "
                        f"alert(s) appeared since it went live. Reverted the working tree to "
                        f"{rollback_commit[:8]}. Restarting to run the reverted code.",
                        source="deploy_manager",
                    )
                results.append({"watch_id": watch_id, "outcome": "auto_rolled_back", "critical_count": current_critical})
                continue

            applied_dt = datetime.fromisoformat(applied_at)
            if datetime.utcnow() - applied_dt > timedelta(minutes=window_min):
                self.db.execute(
                    "UPDATE code_update_watches SET status = 'confirmed_good', resolved_at = datetime('now'), "
                    "resolution_note = 'validation window passed with no critical alert spike' WHERE id = ?",
                    (watch_id,),
                )
                self.db.commit()
                self.mark_last_known_good(note=f"deploy watch #{watch_id} confirmed good")
                logger.info("Deploy watch #%s: confirmed good, new last-known-good commit recorded", watch_id)
                results.append({"watch_id": watch_id, "outcome": "confirmed_good"})

        return results

    def emergency_rollback_to_last_known_good(self) -> str | None:
        """The systemd-layer trigger (deploy/mia-homestead-rollback.service's
        OnFailure= target, run by core/deploy_cli.py --emergency-rollback) —
        distinct from check_deploy_watches()'s alert-spike judgment because
        THIS path exists precisely for when there's no live Python process
        stable enough to make that judgment at all (a crash-loop at
        startup, not a process that's up and misbehaving). No threshold,
        no watch record needed — just revert to whatever's recorded as
        last known-good, unconditionally, the moment systemd's own
        StartLimitBurst decides the process is crash-looping. Returns the
        commit reverted to, or None if there's no known-good commit
        recorded at all (nothing to do — a human needs to investigate
        directly in that case, this can't invent a target)."""
        target = self.get_last_known_good()
        if target is None:
            logger.critical(
                "Emergency rollback triggered but no last-known-good commit is recorded — "
                "cannot revert. Manual investigation required."
            )
            return None
        stashed = self._rollback_to_commit(target)
        logger.critical(
            "Emergency rollback: reverted working tree to %s%s (triggered by systemd "
            "crash-loop detection, not an alert-spike watch).",
            target[:8], " (uncommitted changes stashed, not lost)" if stashed else "",
        )
        if self.notifier:
            self.notifier.dispatch(
                "critical",
                f"Emergency auto-rollback: the control loop was crash-looping at startup. "
                f"Reverted the working tree to {target[:8]} and restarted.",
                source="deploy_manager",
            )
        return target

    def get_status(self) -> dict:
        """Read-only summary — what get_deploy_status (the assistant
        tool) exposes conversationally. mark_last_known_good()/
        start_deploy_watch() are deliberately NOT exposed to chat at
        all, only this: deploying and confirming a deploy healthy are
        deliberate terminal/CLI actions (core/deploy_cli.py) a person
        takes intentionally, same reasoning CLAUDE.md gives for never
        exposing bare dosing pulses as assistant tools — this is a
        write action on the running system's own code, not a casual
        chat request."""
        last_good = self.get_last_known_good()
        watching = self.db.execute(
            "SELECT id, rollback_git_commit, applied_at, validation_window_minutes, critical_alert_threshold "
            "FROM code_update_watches WHERE status = 'watching'"
        ).fetchall()
        return {
            "last_known_good_commit": last_good,
            "current_commit": self.current_commit(),
            "active_watches": [
                {"watch_id": w[0], "rollback_commit": w[1], "applied_at": w[2],
                 "validation_window_minutes": w[3], "critical_alert_threshold": w[4]}
                for w in watching
            ],
        }

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="deploy_manager",
            display_name="Code Deploy Watch & Auto-Rollback",
            purpose=(
                "The code-level counterpart to core/backup_manager.py's config watch, which "
                "explicitly does not touch code: after a deploy, watches for a critical-alert "
                "spike and automatically reverts the working tree to the last known-good git "
                "commit if one appears, requesting a process restart (via main.py, which then "
                "relies on the systemd layer, deploy/mia-homestead.service, to actually come "
                "back up) rather than leaving broken code running."
            ),
            data_produced=["deploy history (marked-good commits)", "deploy watch outcomes"],
            actions_possible=[
                "mark the current commit as known-good",
                "start a watch after deploying new code",
                "check active watches and auto-roll-back on a critical-alert spike",
            ],
            limits_and_safety=(
                "Never silently discards uncommitted work to force a rollback through — a dirty "
                "working tree gets stashed (git stash push --include-untracked) before the "
                "force-checkout, recoverable later via git stash pop. Only reverts the WORKING "
                "TREE — does not restart the running process itself (a Python process already "
                "has old code loaded in memory; that decision belongs to main.py's control loop, "
                "which relies on the systemd layer to actually bring the process back up running "
                "the reverted files). Requires mark_last_known_good() to have been called at "
                "least once before a watch can start — refuses to watch toward nothing. "
                "mark_last_known_good() and start_deploy_watch() are deliberately NOT exposed as "
                "assistant tools — deploying and confirming a deploy healthy are intentional "
                "terminal/CLI actions (core/deploy_cli.py), same reasoning this project already "
                "applies to never exposing bare dosing pulses conversationally. Only get_status() "
                "(read-only) is chat-reachable, via get_deploy_status."
            ),
            example_questions=[
                "Has a deploy ever been auto-rolled-back?", "What commit would a rollback revert to right now?",
            ],
            verification_evidence=[
                "Live manual test 2026-08-31, against a disposable scratch git repo (never the "
                "real project repo): start_deploy_watch() with no known-good commit yet correctly "
                "raises rather than watching toward nothing; marked a real 'v1 good' commit as "
                "known-good, deployed a real 'v2 buggy' commit, started a watch; one critical "
                "alert (below threshold=2) correctly produced no rollback; a second critical "
                "alert correctly triggered auto-rollback — confirmed the actual file content on "
                "disk reverted to v1's real content, not just a DB status change. Separately "
                "confirmed the stash-safety path: seeded real uncommitted changes (a modified "
                "tracked file + a new untracked file) at rollback time, confirmed both were "
                "stashed (recoverable via git stash pop, visible in git stash list) rather than "
                "destroyed, and the rollback still correctly completed. Separately confirmed the "
                "confirmed_good path: backdated a watch's applied_at past its validation window "
                "with no critical alerts, confirmed it resolved to confirmed_good and recorded a "
                "genuine new last-known-good commit (code_deploys count incremented by exactly 1).",
                "The systemd layer (deploy/mia-homestead.service, deploy/mia-homestead-rollback.service) "
                "was separately verified for real against disposable test units in this machine's "
                "actual systemd --user session (cleaned up immediately after, never touching this "
                "repo's own unit namespace) — see deploy/README.md for the two real design bugs "
                "that testing caught and fixed, and the final clean end-to-end result.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software
