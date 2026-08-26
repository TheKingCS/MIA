"""
MIA Homestead — Aquaponics Cell Module
v0.1

Concrete implementation of MiaHomesteadModule for a single aquaponics
cell (fish tank + grow bed + shared biofilter). Handles pH and EC
correction dosing within the hard limits enforced by the base contract.

Placeholder target ranges are passed in via config/modules.yaml — tune
these once fish/plant species are finalized. Tilapia + leafy greens is
a forgiving starting combo (pH 6.6-7.2, EC 800-1500 uS/cm is a
reasonable general range, not species-specific gospel).
"""

import logging
from datetime import datetime, timedelta

from contracts.mia_homestead_contract import (
    ActuatorCommand,
    MiaHomesteadModule,
    SensorReading,
    TriggerSource,
)

logger = logging.getLogger("mia_homestead.aquaponics_cell")


class AquaponicsCell(MiaHomesteadModule):

    def __init__(
        self,
        module_id: str,
        cell_id: int,
        db_conn,
        ph_target_min: float,
        ph_target_max: float,
        ec_target_min: float,
        ec_target_max: float,
        notifier=None,
    ):
        super().__init__(module_id, cell_id, db_conn, notifier=notifier)
        self.ph_target_min = ph_target_min
        self.ph_target_max = ph_target_max
        self.ec_target_min = ec_target_min
        self.ec_target_max = ec_target_max
        # Rolling readings buffer used to require N-consistent-readings
        # before triggering a dose (see SAFETY_SPEC.md).
        self._ph_history: list[float] = []
        self._ec_history: list[float] = []

    def read_sensors(self) -> list[SensorReading]:
        """
        Pulls the most recent reading per active sensor for this cell
        from the sensor_readings table. Actual hardware polling happens
        in a separate driver layer that writes into sensor_readings —
        this module only reads what's already been logged, keeping
        control logic decoupled from hardware I/O.
        """
        rows = self.db.execute(
            """
            SELECT sr.sensor_id, s.type, sr.value, sr.timestamp,
                   sr.is_stale, sr.is_out_of_range
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.cell_id = ? AND s.active = 1
            AND sr.id IN (
                SELECT MAX(id) FROM sensor_readings GROUP BY sensor_id
            )
            """,
            (self.cell_id,),
        ).fetchall()

        readings = []
        self._type_by_sensor = {}
        for sensor_id, sensor_type, value, ts, is_stale, is_oor in rows:
            readings.append(
                SensorReading(
                    sensor_id=sensor_id,
                    value=value,
                    timestamp=datetime.fromisoformat(ts),
                    is_stale=bool(is_stale),
                    is_out_of_range=bool(is_oor),
                )
            )
            self._type_by_sensor[sensor_id] = sensor_type
        return readings

    def evaluate(self, readings: list[SensorReading]) -> list[ActuatorCommand]:
        commands = []
        ph_reading = self._latest_of_type(readings, "ph")
        ec_reading = self._latest_of_type(readings, "ec")
        # (see _latest_of_type below — now correctly filters by real sensor type)

        if ph_reading is None:
            self._raise_alert(
                "warning",
                f"{self.module_id}: no pH reading available at all "
                f"(sensor missing or producing zero data) — pH dosing held",
            )
        else:
            commands += self._evaluate_ph(ph_reading)

        if ec_reading is None:
            self._raise_alert(
                "warning",
                f"{self.module_id}: no EC reading available at all "
                f"(sensor missing or producing zero data) — nutrient dosing held",
            )
        else:
            commands += self._evaluate_ec(ec_reading)

        return commands

    def _evaluate_ph(self, reading: SensorReading) -> list[ActuatorCommand]:
        self._ph_history.append(reading.value)
        self._ph_history = self._ph_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._ph_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return []  # not enough history yet to trust a correction

        avg = sum(self._ph_history) / len(self._ph_history)
        spread = max(self._ph_history) - min(self._ph_history)
        if spread > 0.5:
            # Readings disagree with each other too much — don't trust
            # any single average, flag and skip this cycle.
            self._raise_alert(
                "warning",
                f"{self.module_id}: pH readings inconsistent "
                f"(spread {spread:.2f}) — skipping correction this cycle",
            )
            return []

        if avg < self.ph_target_min:
            return [self._dose_command("ph_up", reading.value)]
        if avg > self.ph_target_max:
            return [self._dose_command("ph_down", reading.value)]
        return []

    def _evaluate_ec(self, reading: SensorReading) -> list[ActuatorCommand]:
        self._ec_history.append(reading.value)
        self._ec_history = self._ec_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._ec_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return []

        avg = sum(self._ec_history) / len(self._ec_history)
        if avg < self.ec_target_min:
            return [self._dose_command("nutrient_concentrate", reading.value)]
        # No auto-correction for EC too high — diluting requires a water
        # change action, which should stay a human-approved/manual step
        # in v0.1 rather than an automated dump of fresh water.
        return []

    def _dose_command(self, dose_type: str, current_value: float) -> ActuatorCommand:
        # Actuator ID lookup would come from the actuators table in a
        # real implementation, keyed by cell_id + dose_type.
        actuator_id = self._actuator_id_for(dose_type)
        logger.info(
            "%s: proposing dose %s (current reading %.2f)",
            self.module_id, dose_type, current_value,
        )
        return ActuatorCommand(
            actuator_id=actuator_id,
            action="pulse",
            duration_seconds=None,  # duration resolved by dosing_limits
            triggered_by=TriggerSource.AUTO_CONTROL,
        )

    def _actuator_id_for(self, dose_type: str) -> int:
        cur = self.db.execute(
            "SELECT id FROM actuators WHERE cell_id = ? AND type = 'dosing_pump' "
            "AND name LIKE ? LIMIT 1",
            (self.cell_id, f"%{dose_type}%"),
        )
        row = cur.fetchone()
        return row[0] if row else -1

    def _latest_of_type(self, readings: list[SensorReading], type_name: str):
        matches = [
            r for r in readings
            if self._type_by_sensor.get(r.sensor_id) == type_name
        ]
        if not matches:
            return None
        return max(matches, key=lambda r: r.timestamp)

    def _safety_fallback_commands(self) -> list[ActuatorCommand]:
        """All sensors stale/invalid: freeze dosing, keep circulation
        and aeration running via their independent safety-MCU defaults
        (those actuators aren't touched here at all — they stay on
        because their safe_default_state is 'on', enforced at the MCU,
        not by this module deciding anything)."""
        return super()._safety_fallback_commands()

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id=self.module_id,
            display_name="Aquaponics Cell Control",
            purpose=(
                "Monitors pH and EC in one aquaponics cell and issues dosing "
                "corrections to keep both within target range, using multiple "
                "consistent readings before acting and hard dosing limits "
                "enforced downstream by the safety MCU."
            ),
            data_produced=[
                "pH reading history", "EC reading history",
                "dosing event log (what was dosed, when, why)",
            ],
            actions_possible=[
                "pulse the pH-up dosing pump",
                "pulse the pH-down dosing pump",
                "pulse the nutrient concentrate dosing pump",
            ],
            limits_and_safety=(
                f"Targets: pH {self.ph_target_min}-{self.ph_target_max}, "
                f"EC {self.ec_target_min}-{self.ec_target_max}. Requires "
                f"{self.MIN_CONSISTENT_READINGS_FOR_DOSE} consistent readings "
                "before dosing. Never auto-dilutes high EC (requires manual "
                "water change). Freezes dosing entirely if sensors are stale "
                "or missing, rather than guessing."
            ),
            example_questions=[
                "How's the pH in Cell A?", "Has it been dosing much lately?",
                "Why didn't it correct the EC this morning?",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="Atlas Scientific pH kit (KIT-101P or equivalent — circuit + probe)",
                category="sensor", quantity=1,
                purpose="pH monitoring for dosing decisions", est_unit_cost=175.0,
                notes="Do not substitute cheap pH probes — drift within weeks feeds bad data into dosing logic. "
                      "Priced as full starter kit; circuit alone is ~$46-51 if you already have a compatible probe. "
                      "See docs/HARDWARE_BOM_CURRENT.md.",
            ),
            HardwareRequirement(
                item="Atlas Scientific EC kit (EC-KIT-1.0 or equivalent — circuit + probe)",
                category="sensor", quantity=1,
                purpose="EC monitoring for nutrient dosing decisions", est_unit_cost=230.0,
                notes="Circuit alone is ~$68-86 if you already have a compatible probe. See docs/HARDWARE_BOM_CURRENT.md.",
            ),
            HardwareRequirement(
                item="Peristaltic dosing pump", category="actuator",
                quantity=3, purpose="pH-up, pH-down, and nutrient concentrate dosing",
                est_unit_cost=12.0,
                notes="One per chemical — never share a pump line between chemicals. "
                      "~$10-15 for a basic 12V DC unit (INTLLAB/Kamoer NKP class). See docs/HARDWARE_BOM_CURRENT.md.",
            ),
            HardwareRequirement(
                item="DS18B20 waterproof temp probe", category="sensor",
                quantity=1, purpose="water temperature monitoring", est_unit_cost=8.0,
            ),
        ]
