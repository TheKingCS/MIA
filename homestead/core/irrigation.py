"""
MIA Homestead — Irrigation Scheduler
v0.1

Real gap found during the hardware-sourcing/schema audit (2026-08-31,
see CLAUDE.md's "Known, deliberately deferred hardware-anticipated
gaps"): config/devices/roles/watering_mcu.yaml describes "scheduled and
moisture-triggered watering pulses" for an irrigation_valve actuator,
and contracts.mia_homestead_contract.TriggerSource already declares
SCHEDULE — but nothing ever used either. Closing the honestly-buildable
half here: "moisture-triggered" stays unbuilt, because no moisture
sensor type exists in sensors.type at all (would need a real schema
addition and real hardware, not faked here). "Scheduled" is buildable
today with what already exists.

Deliberately NOT a MiaHomesteadModule. That base class's run_cycle()
assumes a sensor-reactive module with a real staleness/degradation
failure mode to protect against — a pure clock schedule has neither
(there's no "reading" to go stale). Forcing this through it would mean
either overriding run_cycle() (defeating the point of the base class's
structurally-enforced safety machinery) or a permanent, meaningless
"all sensors stale" CRITICAL alert every cycle, the same wart
modules.self_preservation.SelfPreservationModule's presence-sensor-
optional design already tolerates when no presence sensor exists — not
a pattern worth deliberately repeating here. This is a periodic check
instead, same shape as core/biofilter_model.py's
check_overdue_water_tests() or core/maintenance.py's recurring-task
scan, called from main.py's existing periodic block.

Only for grow beds that actually need flood/drain irrigation — which
beds those are is real physical knowledge, not something to infer from
grow_beds.media_type's free-text value. Comes from config (see
config/irrigation_schedules.yaml), same "config IS the source of truth
for physical wiring" precedent as config/plumbing.yaml. A DWC/NFT bed's
roots sit in continuously-circulated water via the always-on
circulation_pump already and never needs a separate flood cycle.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from contracts.capability import Capability, Describable

logger = logging.getLogger("mia_homestead.irrigation")


class IrrigationScheduler(Describable):
    def __init__(self, db_conn, schedules: list[dict], notifier=None):
        """schedules: list of {"grow_bed_name", "cell_id", "actuator_name",
        "interval_minutes", "pulse_seconds"}. An empty list is valid —
        a build with no flood/drain beds needs no schedule at all."""
        self.db = db_conn
        self.schedules = schedules
        self.notifier = notifier

    @classmethod
    def from_config(cls, path: str, db_conn, notifier=None) -> "IrrigationScheduler":
        import yaml
        p = Path(path)
        if not p.exists():
            logger.info("No irrigation schedule config at %s — starting with zero schedules", path)
            return cls(db_conn, [], notifier=notifier)
        raw = yaml.safe_load(p.read_text()) or {}
        return cls(db_conn, raw.get("schedules", []), notifier=notifier)

    def check_scheduled_irrigation(self) -> list[dict]:
        """Called periodically (main.py). For each configured schedule,
        pulses the valve if enough time has passed since its last pulse
        (or it's never been pulsed at all). Returns the beds actually
        watered this check, for logging."""
        watered = []
        for sched in self.schedules:
            actuator_id = self._actuator_id(sched["cell_id"], sched["actuator_name"])
            if actuator_id is None:
                logger.warning(
                    "irrigation schedule for %r references actuator %r on cell %s "
                    "that doesn't exist — skipping",
                    sched["grow_bed_name"], sched["actuator_name"], sched["cell_id"],
                )
                continue
            last = self._last_pulse_time(actuator_id)
            due = last is None or (datetime.utcnow() - last) >= timedelta(minutes=sched["interval_minutes"])
            if not due:
                continue
            self._pulse(actuator_id, sched["pulse_seconds"])
            watered.append({"grow_bed_name": sched["grow_bed_name"], "cell_id": sched["cell_id"]})
            from core.action_log import log_action
            age = "first pulse ever" if last is None else \
                f"last pulse {(datetime.utcnow() - last).total_seconds() / 60:.0f} min ago"
            log_action(
                self.db, "irrigation_scheduler", "scheduled_watering",
                f"Pulsed {sched['actuator_name']} for {sched['grow_bed_name']} "
                f"({sched['pulse_seconds']}s) — {sched['interval_minutes']} min interval, {age}",
            )
        return watered

    def _actuator_id(self, cell_id: int, actuator_name: str):
        row = self.db.execute(
            "SELECT id FROM actuators WHERE cell_id = ? AND name = ? LIMIT 1",
            (cell_id, actuator_name),
        ).fetchone()
        return row[0] if row else None

    def _last_pulse_time(self, actuator_id: int):
        row = self.db.execute(
            "SELECT timestamp FROM actuator_events WHERE actuator_id = ? AND action = 'pulse' "
            "ORDER BY id DESC LIMIT 1",
            (actuator_id,),
        ).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def _pulse(self, actuator_id: int, duration_seconds: float) -> None:
        from contracts.mia_homestead_contract import TriggerSource
        self.db.execute(
            "INSERT INTO actuator_events (actuator_id, action, duration_seconds, triggered_by) "
            "VALUES (?, 'pulse', ?, ?)",
            (actuator_id, duration_seconds, TriggerSource.SCHEDULE.value),
        )
        self.db.commit()
        logger.info("irrigation_scheduler: pulsed actuator %s for %ss", actuator_id, duration_seconds)

    def get_status(self) -> list[dict]:
        """Read-only view for the assistant — each configured schedule
        plus when it last actually fired, if ever."""
        out = []
        for sched in self.schedules:
            actuator_id = self._actuator_id(sched["cell_id"], sched["actuator_name"])
            last = self._last_pulse_time(actuator_id) if actuator_id is not None else None
            out.append({
                "grow_bed_name": sched["grow_bed_name"],
                "cell_id": sched["cell_id"],
                "interval_minutes": sched["interval_minutes"],
                "actuator_configured": actuator_id is not None,
                "last_pulse": last.isoformat() if last else None,
            })
        return out

    def describe_capabilities(self) -> Capability:
        return Capability(
            module_id="irrigation_scheduler",
            display_name="Irrigation Scheduler",
            purpose=(
                "Pulses a flood/drain grow bed's irrigation valve on a fixed schedule — "
                "closes the gap where config/devices/roles/watering_mcu.yaml described "
                "scheduled watering but no code ever implemented it. Only for beds "
                "configured to need it; a DWC/NFT bed's continuous circulation never needs "
                "a separate flood cycle."
            ),
            data_produced=["scheduled watering log (activity journal, via action_log)"],
            actions_possible=["pulse a configured irrigation valve when its interval is due"],
            limits_and_safety=(
                "Schedule-driven, not sensor-reactive — deliberately NOT a "
                "MiaHomesteadModule (see this file's own docstring for why). "
                "'Moisture-triggered' watering (also described in watering_mcu.yaml) is NOT "
                "implemented — no moisture sensor type exists in sensors.type yet; only the "
                "scheduled half is real. Which beds get scheduled irrigation is config-driven "
                "(config/irrigation_schedules.yaml), never inferred from grow_beds.media_type. "
                "A schedule referencing an actuator that doesn't exist is skipped with a logged "
                "warning, never a crash."
            ),
            example_questions=["Has Bed A1 been watered today?", "When was the grow bed last flooded?"],
            verification_evidence=[
                "scenarios.py::scenario_irrigation_scheduled_pulse — confirmed a due bed gets "
                "pulsed and logged, citing the real interval and actuator",
                "scenarios.py::scenario_irrigation_not_yet_due — confirmed a recently-pulsed bed "
                "is correctly skipped until its interval elapses",
                "scenarios.py::scenario_irrigation_missing_actuator — confirmed a misconfigured "
                "schedule (actuator that doesn't exist) is skipped with a logged warning, not a crash",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="12V solenoid irrigation valve, normally closed", category="actuator",
                quantity=1, purpose="flood/drain cycle for a media-bed grow bed",
                est_unit_cost=15.0,
                notes="Estimate, not independently live-fetched this session — typical current "
                      "market price for this class of valve. Only needed for a flood/drain media "
                      "bed — a DWC/NFT bed doesn't need one.",
            ),
        ]
