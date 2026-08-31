"""
MIA Homestead Node — Module Contract
v0.1

This defines the interface every homestead subsystem (aquaponics cell,
power monitor, future modules like poultry/irrigation) must implement.

Design principle: the base class enforces safety-first defaults. A subclass
CANNOT accidentally skip staleness checks or dosing limits — those live here,
not in each module's implementation.

This runs on the Pi ("brain" tier). It talks to the Safety MCU ("spinal cord"
tier) via a serial/I2C heartbeat + command protocol defined separately in
safety_mcu_protocol.md (TODO once MCU hardware is chosen). The Pi proposes
actions; the MCU is the final authority on whether they execute.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from contracts.capability import Capability, Describable

logger = logging.getLogger("mia_homestead.contract")


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TriggerSource(str, Enum):
    AUTO_CONTROL = "auto_control"
    MANUAL_OVERRIDE = "manual_override"
    SAFETY_FALLBACK = "safety_fallback"
    SCHEDULE = "schedule"
    SELF_PRESERVATION = "self_preservation"


@dataclass
class SensorReading:
    sensor_id: int
    value: float
    timestamp: datetime
    is_stale: bool = False
    is_out_of_range: bool = False


@dataclass
class ActuatorCommand:
    actuator_id: int
    action: str              # 'on' | 'off' | 'pulse'
    duration_seconds: Optional[float] = None
    triggered_by: TriggerSource = TriggerSource.AUTO_CONTROL


class StaleReadingError(Exception):
    """Raised when a control decision would require a stale/missing reading."""


class DosingLimitExceeded(Exception):
    """Raised when a proposed dose would exceed configured hard limits."""


def raise_alert(db, source: str, severity: str, message: str, notifier=None) -> None:
    """The one place an unresolved (source, message) condition gets
    deduplicated before hitting the alerts table and a live
    notification. Lives here (contracts/, not core/) so both
    MiaHomesteadModule subclasses (modules/*.py, via
    MiaHomesteadModule._raise_alert() below) and core/*.py services
    (core/trend_analyzer.py first) can call it without core/ needing to
    import contracts/ backwards — this project's existing convention is
    core/ depends on contracts/, never the reverse (contracts/ itself
    never imports from core/ anywhere).

    Real bug fixed here (2026-08-30): this used to INSERT a fresh row
    and dispatch a fresh notification EVERY call, even for the exact
    same still-unresolved condition — a control loop re-evaluating
    every cycle meant one ongoing problem spammed dozens of identical
    alert rows and notifications. Now: an unresolved alert with the
    same (source, message) gets its occurrence_count bumped and
    last_seen touched instead of a new row, and does NOT re-notify —
    the human/assistant already knows about it. A genuinely new/
    different message still inserts and notifies exactly as before.
    `timestamp` is deliberately never updated on a repeat —
    core/backup_manager.py's post-update critical-alert-spike check
    reads `timestamp >= applied_at` to mean "genuinely new since this
    change", and repeat occurrences of a pre-existing condition must
    not count toward that."""
    existing = db.execute(
        "SELECT id FROM alerts WHERE resolved = 0 AND source = ? AND message = ? "
        "ORDER BY id DESC LIMIT 1",
        (source, message),
    ).fetchone()
    if existing is not None:
        db.execute(
            "UPDATE alerts SET occurrence_count = occurrence_count + 1, "
            "last_seen = datetime('now') WHERE id = ?",
            (existing[0],),
        )
        db.commit()
        logger.debug("Alert still ongoing, not re-notifying: %s: %s", source, message)
        return
    db.execute(
        "INSERT INTO alerts (severity, source, message) VALUES (?, ?, ?)",
        (severity, source, message),
    )
    db.commit()
    if notifier is not None:
        notifier.dispatch(severity, message, source=source)
    else:
        print(f"[{severity.upper()}] {source}: {message}")


class MiaHomesteadModule(Describable, ABC):
    """
    Base class for any homestead subsystem module (aquaponics cell,
    power monitor, irrigation zone, etc).

    Subclasses implement the domain-specific logic in `evaluate()` AND
    `describe_capabilities()`. Both are enforced by ABC — a subclass
    missing either one cannot be instantiated. This is deliberate: it's
    structurally impossible to add a new control module to this system
    without also declaring what it does, in a form the assistant can
    read. See contracts/capability.py for why this exists.
    """

    STALE_THRESHOLD = timedelta(minutes=10)
    MIN_CONSISTENT_READINGS_FOR_DOSE = 3
    # How many consecutive cycles a degraded sensor gets to recover (via
    # force-reread or a healthy redundant sibling) before the WARNING/
    # CRITICAL alert that fires today fires here too. Mirrors
    # MIN_CONSISTENT_READINGS_FOR_DOSE's existing precedent. Never
    # affects dosing itself — a cell with no valid reading still doses
    # nothing the entire time, retrying or not.
    MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT = 3

    def __init__(self, module_id: str, cell_id: int, db_conn, notifier=None,
                 force_read_fn=None, recovery_log_fn=None):
        self.module_id = module_id
        self.cell_id = cell_id
        self.db = db_conn
        self.notifier = notifier  # core.notifications.NotificationDispatcher, optional
        # force_read_fn(sensor_id) -> bool: optional hook to request an
        # immediate fresh read of one sensor from whatever driver is
        # live (real hardware or a physics sim), before giving up on a
        # stale/missing reading. None in any context with no in-process
        # driver (e.g. main.py today — see main.py's own comment on
        # this) — the rest of the recovery ladder still works without it.
        self.force_read_fn = force_read_fn
        # recovery_log_fn(action: str, rationale: str) -> None: optional
        # hook so every ladder attempt (recovered, substituted, retry
        # pending) shows up in automated_action_log / the Activity
        # Journal, same as any other automated decision in this system.
        self.recovery_log_fn = recovery_log_fn
        # sensor_id -> consecutive degraded-cycle count. In-memory,
        # same precedent as AquaponicsCell._ph_history below — resets on
        # restart, which only delays a WARNING by a few cycles at worst;
        # nothing safety-relevant depends on it surviving a restart.
        self._consecutive_failures: dict[int, int] = {}

    # ---------- Required overrides ----------

    @abstractmethod
    def read_sensors(self) -> list[SensorReading]:
        """Pull current readings for this module's sensors."""
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, readings: list[SensorReading]) -> list[ActuatorCommand]:
        """
        Domain logic: given fresh, validated readings, decide what actuator
        commands (if any) to propose. Must NOT be called directly with
        unvalidated readings — always go through `run_cycle()`.
        """
        raise NotImplementedError

    # ---------- Base-class enforced safety behavior ----------

    def run_cycle(self) -> list[ActuatorCommand]:
        """
        Main entry point for one control-loop iteration. Handles staleness
        filtering (with a bounded recovery ladder — see _filter_stale)
        before handing off to subclass logic, then validates any proposed
        dosing actions against hard limits before returning them for
        execution by the safety MCU layer.
        """
        raw_readings = self.read_sensors()
        valid_readings, still_degraded = self._filter_stale(raw_readings)

        if not valid_readings:
            if still_degraded:
                # At least one sensor is still within its retry budget —
                # stay quiet this cycle rather than alert prematurely.
                # Net effect on actuation is identical either way: no
                # valid readings means no dosing happens regardless.
                return []
            self._raise_alert(
                Severity.CRITICAL,
                f"{self.module_id}: all sensors stale/invalid — "
                f"freezing non-essential actuation for cell {self.cell_id}",
            )
            return self._safety_fallback_commands()

        proposed = self.evaluate(valid_readings)
        return [self._validate_command(cmd) for cmd in proposed]

    def _filter_stale(self, readings: list[SensorReading]) -> tuple[list[SensorReading], bool]:
        """Returns (valid_readings, still_degraded) — still_degraded is
        True if any reading is mid-retry (not yet escalated to an alert),
        so run_cycle() can tell "genuinely nothing valid, retries
        exhausted" apart from "nothing valid yet, still trying"."""
        now = datetime.utcnow()
        valid = []
        still_degraded = False
        for r in readings:
            if now - r.timestamp > self.STALE_THRESHOLD:
                r.is_stale = True
                recovered, degraded = self._attempt_recovery(r, "stale", readings)
            elif r.is_out_of_range:
                recovered, degraded = self._attempt_recovery(r, "out of physically plausible range", readings)
            else:
                self._consecutive_failures.pop(r.sensor_id, None)
                valid.append(r)
                continue
            if recovered is not None:
                valid.append(recovered)
            still_degraded = still_degraded or degraded
        return valid, still_degraded

    def _attempt_recovery(self, r: SensorReading, reason: str,
                           all_readings: list[SensorReading]) -> tuple[SensorReading | None, bool]:
        """The self-correction ladder for one degraded reading. Tries a
        few different, genuinely safe recovery methods — never anything
        touching dosing/actuation — before letting the original
        immediate-alert behavior happen. Returns (recovered_reading_or_
        None, still_degraded)."""
        sensor_type = self._sensor_type_label(r.sensor_id)

        # Step 1 — force an immediate fresh read, if a live driver is
        # wired up to do so (real hardware or a physics sim; None in any
        # context with no in-process driver — see force_read_fn's own
        # comment).
        if self.force_read_fn is not None:
            try:
                requested = self.force_read_fn(r.sensor_id)
            except Exception:
                requested = False
            if requested:
                fresh = self._refetch_one(r.sensor_id)
                if fresh is not None and self._is_healthy(fresh):
                    self._consecutive_failures.pop(r.sensor_id, None)
                    self._log_recovery(
                        "force_reread_recovered",
                        f"{sensor_type} sensor (id {r.sensor_id}) was {reason} — "
                        f"forced an immediate reread and it recovered, no alert needed",
                    )
                    return fresh, False
                # A fresh row that's STILL bad is not a recovery — falls
                # through to the retry-count gate below. A persistently
                # miscalibrated/failed probe must still escalate.

        # Step 2 — prefer a healthy redundant sensor of the same type on
        # this cell, if one exists (today, no cell configures two same-
        # type sensors — see AquaponicsCell's verification_evidence for
        # the honest caveat — but this is correct and free to have ready).
        sibling = self._healthy_sibling_of_type(sensor_type, r.sensor_id, all_readings)
        if sibling is not None:
            self._consecutive_failures.pop(r.sensor_id, None)
            self._log_recovery(
                "redundant_sensor_substituted",
                f"{sensor_type} sensor (id {r.sensor_id}) was {reason} — using healthy "
                f"redundant sensor (id {sibling.sensor_id}) instead this cycle",
            )
            return None, False  # sibling lands in `valid` on its own turn through the loop

        # Step 3 — retry-count gate: give it a few consecutive cycles
        # before escalating to the same alert that fired immediately
        # before this ladder existed. The counter is capped at MAX (not
        # incremented forever) and the escalation message below is
        # DELIBERATELY constant text once exhausted — real bug caught by
        # live-testing against the running system: an earlier version
        # embedded the ever-growing retry count in the message, which
        # defeated raise_alert()'s (source, message) dedup and caused a
        # brand-new alert row (and a brand-new auto-filed maintenance
        # task) every single cycle forever instead of one alert with its
        # occurrence_count bumping, exactly the runaway-noise failure
        # mode this whole feature was supposed to prevent.
        n = self._consecutive_failures.get(r.sensor_id, 0)
        if n < self.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT:
            n += 1
            self._consecutive_failures[r.sensor_id] = n
            if n < self.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT:
                self._log_recovery(
                    "retry_pending",
                    f"{sensor_type} sensor (id {r.sensor_id}) {reason} — retry {n}/"
                    f"{self.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT}, holding off on an alert",
                )
                return None, True

        # Genuinely exhausted (whether just now or on a prior cycle) —
        # the original alert, delayed by the retry window but otherwise
        # unchanged, and safe to repeat every cycle since the text never
        # changes.
        self._raise_alert(
            Severity.WARNING,
            f"{self.module_id}: {sensor_type} sensor (id {r.sensor_id}) {reason} "
            f"— retries exhausted",
        )
        return None, False

    def _is_type_mid_retry(self, sensor_type: str) -> bool:
        """True if some sensor of this type has reported before and is
        currently within its retry budget (excluded from valid_readings
        this cycle, but not yet escalated to an alert). Subclasses whose
        evaluate() raises its own 'no {type} reading available' alert
        when a type is entirely absent from valid_readings should check
        this first — otherwise that alert fires every retry cycle,
        completely bypassing the ladder above. A sensor that has NEVER
        reported at all (no row ever, e.g. pilot_cell's missing EC
        sensor) correctly returns False here — there's nothing to retry
        against, so that alert fires immediately, unchanged."""
        return any(
            count < self.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT and self._sensor_type_label(sensor_id) == sensor_type
            for sensor_id, count in self._consecutive_failures.items()
        )

    def _refetch_one(self, sensor_id: int) -> SensorReading | None:
        for r in self.read_sensors():
            if r.sensor_id == sensor_id:
                return r
        return None

    def _is_healthy(self, r: SensorReading) -> bool:
        return (datetime.utcnow() - r.timestamp <= self.STALE_THRESHOLD) and not r.is_out_of_range

    def _healthy_sibling_of_type(self, sensor_type: str, exclude_sensor_id: int,
                                   all_readings: list[SensorReading]) -> SensorReading | None:
        # Checked against ALL readings, re-tested for health directly,
        # not against readings processed earlier in this same pass —
        # otherwise a healthy sibling later in the list would be missed
        # by iteration order alone. A sibling found healthy here will
        # still land in `valid` on its own turn through the loop, so
        # nothing else needs to happen with it here.
        for r in all_readings:
            if r.sensor_id == exclude_sensor_id:
                continue
            if self._sensor_type_label(r.sensor_id) == sensor_type and self._is_healthy(r):
                return r
        return None

    def _log_recovery(self, action: str, rationale: str) -> None:
        if self.recovery_log_fn:
            try:
                self.recovery_log_fn(action, rationale)
            except Exception:
                logger.exception("recovery_log_fn failed — continuing without it")

    def _sensor_type_label(self, sensor_id: int) -> str:
        """Looks up the sensor's type so alert messages are specific
        enough for the diagnostic engine to pattern-match against —
        'pH sensor stale' is diagnosable, 'sensor 3 stale' isn't."""
        try:
            row = self.db.execute("SELECT type FROM sensors WHERE id = ?", (sensor_id,)).fetchone()
            return row[0] if row else "unknown"
        except Exception:
            return "unknown"

    def _validate_command(self, cmd: ActuatorCommand) -> ActuatorCommand:
        """
        Placeholder for dosing-limit validation. Real implementation queries
        dosing_limits + recent dosing_events from the DB and raises
        DosingLimitExceeded if the proposed action would breach max-per-dose,
        max-per-day, or min-interval constraints. Left as a stub here since
        it needs the live schema wired in — see mia_homestead_schema.sql.
        """
        # TODO: query dosing_limits table, compare against dosing_events
        # for this cell/dose_type within the rolling window.
        return cmd

    def _safety_fallback_commands(self) -> list[ActuatorCommand]:
        """
        Called when this module cannot make a safe decision. Returns the
        minimal set of commands to keep the cell alive: maintain aeration
        and circulation, halt everything else. Subclasses can override to
        add module-specific fallbacks but should call super() first.
        """
        return []

    def _raise_alert(self, severity, message: str) -> None:
        sev = severity.value if isinstance(severity, Severity) else severity
        raise_alert(self.db, self.module_id, sev, message, self.notifier)
