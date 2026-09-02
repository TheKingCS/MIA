"""
MIA Homestead — Self-Preservation Module
v0.1

The idea: most of this system is designed to survive WITHOUT a human
around. This module is the inverse case — if something is critically
wrong AND a human happens to be physically present (detected via a
presence sensor near the greenhouse entrance), it actively asks for
help rather than silently logging an alert that might not get checked
for hours. This is a last line of defense: the system doesn't just wait
to be checked on, it calls out the moment someone's actually there to
hear it.

Requires: a presence sensor (type='presence', e.g. a PIR motion sensor
at the entrance) and a "help beacon" actuator (type='alert_beacon' —
could be a light, speaker, or both) registered to the same cell as
this module.

This deliberately does NOT try to do anything clever — no diagnosis, no
autonomous fix attempt beyond what the normal control loop already
does. It just makes the existing critical state loud and visible the
moment a human is there to act on it, and stops being loud once either
a human acknowledges it or the underlying issue resolves itself.
"""

import logging
from datetime import datetime, timedelta

from contracts.mia_homestead_contract import (
    ActuatorCommand,
    MiaHomesteadModule,
    SensorReading,
    TriggerSource,
)

logger = logging.getLogger("mia_homestead.self_preservation")

NUDGE_INTERVAL_MINUTES = 5  # how often to re-signal if help hasn't come yet


class SelfPreservationModule(MiaHomesteadModule):
    """
    Not tied to dosing/power logic — this watches the WHOLE system's
    critical alert state, not just its own cell, and reacts to presence.
    """

    def __init__(self, module_id: str, cell_id: int, db_conn, notifier=None,
                 force_read_fn=None, recovery_log_fn=None):
        super().__init__(module_id, cell_id, db_conn, notifier=notifier,
                          force_read_fn=force_read_fn, recovery_log_fn=recovery_log_fn)

    def run_cycle(self) -> list[ActuatorCommand]:
        """Overrides the base class's staleness-panic entry point on
        purpose. This module's only sensor (presence) is genuinely
        optional hardware (see describe_hardware_requirements) that most
        cells will simply never have installed — read_sensors()
        returning [] here almost always means "no PIR sensor
        configured," not "sensor went stale/invalid." The base
        run_cycle() couldn't tell those apart and raised a false
        CRITICAL "all sensors stale/invalid — freezing non-essential
        actuation" alert every single cycle, forever, on any cell
        without one. Real bug found live 2026-09-02: cell 1 has no
        presence sensor and never has, and this alert had already fired
        21,000+ times continuously since 2026-08-31 with nothing
        actually wrong — a scary, permanently-unresolvable false
        CRITICAL that also drowned out genuine critical alerts in the
        same list. evaluate() already treats an empty or unreadable
        presence reading as presence_detected=False, the correct safe
        default, so the staleness ladder built for dosing-relevant
        sensors (where a stale reading changes what's safe to actuate)
        doesn't apply here — there's nothing to freeze."""
        readings = self.read_sensors()
        proposed = self.evaluate(readings)
        return [self._validate_command(cmd) for cmd in proposed]

    def read_sensors(self) -> list[SensorReading]:
        row = self.db.execute(
            """
            SELECT sr.sensor_id, sr.value, sr.timestamp
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.cell_id = ? AND s.type = 'presence' AND s.active = 1
            ORDER BY sr.id DESC LIMIT 1
            """,
            (self.cell_id,),
        ).fetchone()
        if not row:
            return []
        sensor_id, value, ts = row
        return [SensorReading(sensor_id=sensor_id, value=value, timestamp=datetime.fromisoformat(ts))]

    def evaluate(self, readings: list[SensorReading]) -> list[ActuatorCommand]:
        presence_detected = bool(readings) and readings[0].value >= 0.5

        open_critical = self.db.execute(
            "SELECT id, source, message FROM alerts WHERE severity = 'critical' AND resolved = 0"
        ).fetchall()

        open_help_request = self.db.execute(
            "SELECT id FROM help_requests WHERE resolved = 0 ORDER BY id DESC LIMIT 1"
        ).fetchone()

        # Critical issue resolved on its own — clear any open help request
        # and turn the beacon off, regardless of whether anyone's there.
        if not open_critical and open_help_request:
            self._resolve_help_request(open_help_request[0])
            from core.action_log import log_action
            log_action(self.db, self.module_id, "beacon_off",
                       "Critical condition that triggered the help request has cleared — silencing beacon.")
            return [self._beacon_command("off")]

        if not open_critical or not presence_detected:
            return []  # nothing wrong, or nothing wrong that a human needs to hear about right now

        if not open_help_request:
            request_id = self._create_help_request(open_critical)
            logger.warning("SELF-PRESERVATION: help requested (request #%s), human detected nearby", request_id)
            from core.action_log import log_action
            log_action(self.db, self.module_id, "beacon_on",
                       f"Critical alert(s) open AND human presence detected — signaling for help "
                       f"(help request #{request_id}).")
            return [self._beacon_command("on")]

        # Already an open request — nudge periodically rather than spam
        # every cycle while someone's standing right there.
        request_id, last_nudge = self._get_request_nudge_state(open_help_request[0])
        if self._should_nudge(last_nudge):
            self._update_nudge_time(request_id)
            from core.action_log import log_action
            log_action(self.db, self.module_id, "beacon_nudge",
                       f"Help request #{request_id} still unresolved and presence still detected — "
                       f"re-signaling ({NUDGE_INTERVAL_MINUTES}min since last nudge).")
            return [self._beacon_command("on")]
        return []

    # ---------- Help request lifecycle ----------

    def _create_help_request(self, open_critical_alerts) -> int:
        summary = "; ".join(f"{source}: {message}" for _, source, message in open_critical_alerts[:3])
        message = self._build_spoken_message(open_critical_alerts)
        cur = self.db.execute(
            "INSERT INTO help_requests (cell_id, trigger_summary, message) VALUES (?, ?, ?)",
            (self.cell_id, summary, message),
        )
        self.db.commit()
        if self.notifier:
            self.notifier.dispatch("critical", f"Help requested at greenhouse: {message}", source=self.module_id)
        return cur.lastrowid

    def _build_spoken_message(self, open_critical_alerts) -> str:
        """This is deliberately simple/deterministic, not LLM-generated —
        the physical beacon needs to work even if the assistant/API is
        unreachable. The assistant can still elaborate conversationally
        once someone checks in via chat."""
        if len(open_critical_alerts) == 1:
            _, source, msg = open_critical_alerts[0]
            return f"I need help — {source}: {msg}"
        return (
            f"I need help — {len(open_critical_alerts)} critical issues right now. "
            f"Most recent: {open_critical_alerts[0][2]}"
        )

    def _resolve_help_request(self, request_id: int) -> None:
        self.db.execute(
            "UPDATE help_requests SET resolved = 1, resolved_at = datetime('now') WHERE id = ?",
            (request_id,),
        )
        self.db.commit()
        logger.info("SELF-PRESERVATION: help request #%s auto-resolved (critical state cleared)", request_id)

    def _get_request_nudge_state(self, request_id: int):
        row = self.db.execute(
            "SELECT id, last_nudge_at FROM help_requests WHERE id = ?", (request_id,)
        ).fetchone()
        return row[0], row[1]

    def _should_nudge(self, last_nudge_at: str | None) -> bool:
        if last_nudge_at is None:
            return True
        last = datetime.fromisoformat(last_nudge_at)
        return datetime.utcnow() - last > timedelta(minutes=NUDGE_INTERVAL_MINUTES)

    def _update_nudge_time(self, request_id: int) -> None:
        self.db.execute(
            "UPDATE help_requests SET last_nudge_at = datetime('now') WHERE id = ?", (request_id,)
        )
        self.db.commit()

    def _beacon_command(self, action: str) -> ActuatorCommand:
        row = self.db.execute(
            "SELECT id FROM actuators WHERE cell_id = ? AND type = 'alert_beacon' LIMIT 1",
            (self.cell_id,),
        ).fetchone()
        actuator_id = row[0] if row else -1
        return ActuatorCommand(actuator_id=actuator_id, action=action, triggered_by=TriggerSource.SELF_PRESERVATION)

    # ---------- Human-facing acknowledgment (called by the assistant) ----------

    @staticmethod
    def acknowledge_help_request(db_conn, request_id: int) -> None:
        """A human confirming 'yes, I'm helping' — doesn't resolve the
        underlying issue (the control loop or the human still has to
        actually fix it), just stops the beacon nudging every 5 minutes
        while someone's already on it."""
        db_conn.execute(
            "UPDATE help_requests SET acknowledged = 1, acknowledged_at = datetime('now') WHERE id = ?",
            (request_id,),
        )
        db_conn.commit()

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id=self.module_id,
            display_name="Self-Preservation / Help Request",
            purpose=(
                "Watches for a human presence near the greenhouse while any "
                "critical alert is open, and actively signals for help via "
                "a physical beacon rather than waiting to be checked on. "
                "Not a diagnosis or repair system — it makes an existing "
                "critical state impossible to miss when someone's there."
            ),
            data_produced=["human presence sensor reading", "help request log"],
            actions_possible=[
                "turn on the help beacon (light/speaker)",
                "turn off the help beacon",
                "re-nudge every 5 minutes while unacknowledged and someone's present",
            ],
            limits_and_safety=(
                "Never attempts an autonomous fix — purely a signaling layer "
                "on top of the existing critical alert state. Auto-resolves "
                "and silences itself the moment the underlying critical "
                "condition clears, with or without human intervention."
            ),
            example_questions=[
                "Is the greenhouse asking for help right now?",
                "What's the beacon been triggered for recently?",
            ],
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed all three states — silent while critical "
                "and alone, beacon on the moment presence is detected, auto-resolved and beacon "
                "off once the critical condition cleared",
                "scenarios.py::scenario_self_preservation_no_presence_sensor_silent — confirmed a "
                "cell with no presence sensor stays silent (no false CRITICAL, no help request) "
                "even with a real critical alert open, fixing a bug that had fired 21,000+ times "
                "live before this",
                "scenarios.py::scenario_self_preservation_signals_with_presence — confirmed the "
                "fix didn't break the actual signal path: a real presence reading plus an open "
                "critical alert still creates a help request and turns the beacon on",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="PIR motion sensor", category="sensor",
                quantity=1, purpose="detects human presence near greenhouse entrance",
                est_unit_cost=5.0,
            ),
            HardwareRequirement(
                item="Alert beacon (light + speaker/buzzer combo)", category="actuator",
                quantity=1, purpose="physically signals for help when triggered",
                est_unit_cost=20.0,
                notes="A speaker is worth more than a light alone — an audible call for help works even out of sightline.",
            ),
        ]
