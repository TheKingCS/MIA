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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from contracts.capability import Capability, Describable


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

    def __init__(self, module_id: str, cell_id: int, db_conn, notifier=None):
        self.module_id = module_id
        self.cell_id = cell_id
        self.db = db_conn
        self.notifier = notifier  # core.notifications.NotificationDispatcher, optional

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
        filtering before handing off to subclass logic, then validates any
        proposed dosing actions against hard limits before returning them
        for execution by the safety MCU layer.
        """
        raw_readings = self.read_sensors()
        valid_readings = self._filter_stale(raw_readings)

        if not valid_readings:
            self._raise_alert(
                Severity.CRITICAL,
                f"{self.module_id}: all sensors stale/invalid — "
                f"freezing non-essential actuation for cell {self.cell_id}",
            )
            return self._safety_fallback_commands()

        proposed = self.evaluate(valid_readings)
        return [self._validate_command(cmd) for cmd in proposed]

    def _filter_stale(self, readings: list[SensorReading]) -> list[SensorReading]:
        now = datetime.utcnow()
        valid = []
        for r in readings:
            if now - r.timestamp > self.STALE_THRESHOLD:
                r.is_stale = True
                self._raise_alert(
                    Severity.WARNING,
                    f"{self.module_id}: sensor {r.sensor_id} stale "
                    f"(last update {r.timestamp.isoformat()})",
                )
                continue
            if r.is_out_of_range:
                self._raise_alert(
                    Severity.WARNING,
                    f"{self.module_id}: sensor {r.sensor_id} out of "
                    f"physically plausible range, discarding",
                )
                continue
            valid.append(r)
        return valid

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
        self.db.execute(
            "INSERT INTO alerts (severity, source, message) VALUES (?, ?, ?)",
            (sev, self.module_id, message),
        )
        self.db.commit()
        if self.notifier is not None:
            self.notifier.dispatch(sev, message, source=self.module_id)
        else:
            print(f"[{sev.upper()}] {self.module_id}: {message}")
