"""
MIA Homestead — Dead-Man's-Switch Escalation
v0.1

human_checkins and the 72h dead-man's-switch concept existed in the
schema and SAFETY_SPEC.md from early on; this is the actual escalation
logic. Two-stage: no check-in for THRESHOLD_1 hours notifies the
primary contact (warning); no check-in for THRESHOLD_2 hours escalates
to the secondary contact (critical) — matching the "surfaces the 'what
if something's wrong and no one's watching' case" language already in
SAFETY_SPEC.md.

Escalation state persists (deadmans_switch_state) so this doesn't
re-notify every single cycle once a level is reached — it escalates
once per level, then waits for either a check-in (resets to 0) or the
next threshold.
"""

import logging
import sqlite3
from datetime import datetime, timedelta

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.deadmans_switch")

THRESHOLD_1_HOURS = 48   # notify primary
THRESHOLD_2_HOURS = 72   # escalate to secondary — matches SAFETY_SPEC.md's stated default


class DeadMansSwitchMonitor(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def record_checkin(self, method: str = "manual_ping") -> None:
        """Call this whenever a human demonstrably interacts with the
        system — viewing the dashboard, acknowledging an alert, asking
        the assistant something. Resets escalation to 0."""
        self.db.execute("INSERT INTO human_checkins (method) VALUES (?)", (method,))
        self.db.execute(
            "UPDATE deadmans_switch_state SET escalation_level = 0, last_escalated_at = NULL WHERE id = 1"
        )
        self.db.commit()

    def get_status(self) -> dict:
        """Read-only — for conversational status checks. Never
        escalates or sends a notification, unlike check_escalation()
        which is the active periodic check main.py runs. A question
        shouldn't have the side effect of triggering a critical alert."""
        last_checkin = self.db.execute(
            "SELECT timestamp FROM human_checkins ORDER BY id DESC LIMIT 1"
        ).fetchone()
        hours_since = None
        if last_checkin:
            last_time = datetime.fromisoformat(last_checkin[0])
            hours_since = (datetime.utcnow() - last_time).total_seconds() / 3600
        level = self.db.execute(
            "SELECT escalation_level FROM deadmans_switch_state WHERE id = 1"
        ).fetchone()[0]
        return {"hours_since_checkin": hours_since, "escalation_level": level}

    def check_escalation(self) -> dict:
        last_checkin = self.db.execute(
            "SELECT timestamp FROM human_checkins ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if last_checkin is None:
            hours_since = None  # never checked in — treat as maximally overdue
        else:
            last_time = datetime.fromisoformat(last_checkin[0])
            hours_since = (datetime.utcnow() - last_time).total_seconds() / 3600

        current_level = self.db.execute(
            "SELECT escalation_level FROM deadmans_switch_state WHERE id = 1"
        ).fetchone()[0]

        overdue = hours_since is None or hours_since >= THRESHOLD_1_HOURS
        if not overdue:
            return {"escalated": False, "hours_since_checkin": hours_since, "level": current_level}

        target_level = 2 if (hours_since is None or hours_since >= THRESHOLD_2_HOURS) else 1

        if target_level <= current_level:
            return {"escalated": False, "hours_since_checkin": hours_since, "level": current_level,
                     "note": "already escalated to this level, waiting for check-in or next threshold"}

        self._escalate(target_level, hours_since)
        return {"escalated": True, "hours_since_checkin": hours_since, "level": target_level}

    def _escalate(self, level: int, hours_since: float | None) -> None:
        self.db.execute(
            "UPDATE deadmans_switch_state SET escalation_level = ?, last_escalated_at = datetime('now') WHERE id = 1",
            (level,),
        )
        self.db.commit()

        hours_str = f"{hours_since:.0f} hours" if hours_since is not None else "an unknown period (no check-in on record)"
        message = (
            f"No human check-in on this system in {hours_str}. This doesn't necessarily mean "
            f"anything is wrong, but no one has confirmed things are okay recently."
        )
        severity = "critical" if level == 2 else "warning"
        logger.log(logging.CRITICAL if level == 2 else logging.WARNING,
                   "Dead-man's-switch escalated to level %d: %s", level, message)
        if self.notifier:
            self.notifier.dispatch(severity, message, source="deadmans_switch")

        from core.action_log import log_action
        log_action(self.db, "deadmans_switch", f"escalate_level_{level}", message)

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="deadmans_switch",
            display_name="Dead-Man's-Switch Escalation",
            purpose=(
                f"Watches how long it's been since a human demonstrably interacted with the "
                f"system, and escalates in two stages if nobody has: {THRESHOLD_1_HOURS}h "
                f"notifies the primary contact, {THRESHOLD_2_HOURS}h escalates to secondary. "
                f"Catches the 'something's wrong and nobody's watching' case even absent any "
                f"other active fault."
            ),
            data_produced=["escalation level and hours since last check-in"],
            actions_possible=["record a check-in (resets escalation)",
                               "escalate a notification when overdue"],
            limits_and_safety=(
                "Escalates once per level, not every cycle — won't spam once a level is "
                "reached, waits for either a check-in or the next threshold. Never takes "
                "control action, purely a notification escalation."
            ),
            example_questions=["How long since anyone checked on the system?",
                                "Has the dead-man's switch escalated?"],
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed all states — no check-in ever escalates "
                "immediately to level 2, a fresh check-in resets to level 0, backdating past "
                "48h correctly escalates to level 1, checking again immediately does NOT "
                "re-escalate (stays at level 1), and backdating past 72h correctly escalates "
                "to level 2",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software
