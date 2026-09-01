"""
MIA Homestead — Climate Control Module
v0.1

Concrete implementation of MiaHomesteadModule for greenhouse-zone air
temperature and humidity: drives an exhaust fan and a heater to keep a
cell's air within target range. This closes a real gap found during
hardware sourcing (docs/HARDWARE_BOM_FULL_TIERS.md, 2026-08-31):
`actuators.type` and `sensors.type` both forward-declared 'heater'/
'fan' and 'temp_air'/'humidity' in the schema, but nothing in
modules/*.py or config/devices/roles/*.yaml ever implemented them —
buying that hardware would have been inert without this.

Safe-default reasoning (documented once here, not scattered): a heater
stuck ON is a real fire/scorch hazard, the same category of danger as
a dosing pump stuck open — so heater follows dosing's precedent and
defaults OFF. A fan stuck ON is not dangerous (worst case: over-
ventilated, same non-hazard as aeration running when not strictly
needed) — so fan follows aeration's precedent and defaults ON. This
mapping is enforced in two places that must agree:
config/devices/roles/climate_mcu.yaml's safe_default_state (the
hardware-level fallback when the MCU loses the Pi entirely) and
_safety_fallback_commands() below (the software-level fallback when
sensor data can't be trusted but the MCU is still reachable).

Also monitors light and CO2, opt-in per cell (same pattern as
aquaponics_cell.py's DO monitoring) — supplemental grow lighting and
CO2 enrichment, the two `sensors.type` entries still flagged as
deliberately deferred in CLAUDE.md ("no clear actuation story yet")
until now. Grow light is a plain on/off actuator, same safety class as
fan (stuck-on is not dangerous). CO2 injection is genuinely different
from everything else in this module: unlike temperature or humidity,
too much CO2 is a real HUMAN safety hazard, not just a yield concern —
so injection is a short, cooldown-limited PULSE (dosing-pump style,
never a continuous "on"), and a reading at/above OSHA's 5000ppm PEL
raises a critical alert and refuses to inject further, regardless of
how low it was trending before.
"""

import logging
from datetime import datetime, timedelta

from contracts.mia_homestead_contract import (
    ActuatorCommand,
    MiaHomesteadModule,
    SensorReading,
    TriggerSource,
)

logger = logging.getLogger("mia_homestead.climate_control")

# Spread tolerances for the "don't trust one noisy reading" consistency
# check (contracts.MiaHomesteadModule.MIN_CONSISTENT_READINGS_FOR_DOSE
# readings required first, same principle SAFETY_SPEC.md states for
# dosing, reused here for actuation generally). Wider than pH's 0.5
# because air temp (°F, see core/species_registry.py's existing
# temp_air_min/max convention) and humidity (%RH) are both noisier,
# slower-moving signals than a calibrated pH probe.
TEMP_SPREAD_TOLERANCE_F = 5.0
HUMIDITY_SPREAD_TOLERANCE_PCT = 10.0

# Rough starting thresholds, not calibrated per species (same honesty
# as this module's temp/humidity targets) — supplemental lighting below
# this lux level, CO2 enrichment below this ppm level. Real horticultural
# targets vary a lot by crop; tune once real hardware/species data exists.
LIGHT_TARGET_MIN_LUX = 5000.0
LIGHT_SPREAD_TOLERANCE_LUX = 1000.0

CO2_TARGET_MIN_PPM = 800.0       # enclosed greenhouses run above outdoor ambient (~420ppm) already
CO2_SPREAD_TOLERANCE_PPM = 100.0
CO2_DANGER_PPM = 5000.0          # OSHA permissible exposure limit (8-hr TWA) — real, cited, not fabricated
CO2_INJECTION_PULSE_SECONDS = 30.0
# Minimum time between injections regardless of how low CO2 reads —
# same "never continuously pulse-spam" discipline as dosing_limits'
# min_interval_minutes, applied here since CO2 has no schema table of
# its own to enforce it the way dosing does.
CO2_INJECTION_COOLDOWN_MINUTES = 15


class ClimateControl(MiaHomesteadModule):

    def __init__(
        self,
        module_id: str,
        cell_id: int,
        db_conn,
        temp_min: float,
        temp_max: float,
        humidity_max: float,
        notifier=None,
        force_read_fn=None,
        recovery_log_fn=None,
    ):
        super().__init__(module_id, cell_id, db_conn, notifier=notifier,
                          force_read_fn=force_read_fn, recovery_log_fn=recovery_log_fn)
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.humidity_max = humidity_max
        self._temp_history: list[float] = []
        self._humidity_history: list[float] = []
        self._light_history: list[float] = []
        self._co2_history: list[float] = []
        self._last_co2_injection: datetime | None = None
        # Last action actually sent per actuator type — lets evaluate()
        # emit a command only on a real state change, same "don't log
        # steady state every cycle" discipline as AquaponicsCell only
        # dosing on a real correction. Cleared by _safety_fallback_commands()
        # so a real decision gets re-asserted fresh once sensors recover,
        # rather than staying suppressed by a stale dedup entry.
        self._last_action: dict[str, str] = {}

    def read_sensors(self) -> list[SensorReading]:
        rows = self.db.execute(
            """
            SELECT sr.sensor_id, s.type, sr.value, sr.timestamp,
                   sr.is_stale, sr.is_out_of_range
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.cell_id = ? AND s.active = 1 AND s.type IN ('temp_air', 'humidity', 'light', 'co2')
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

    def _current_targets(self) -> dict:
        """Same target_overrides mechanism as AquaponicsCell — live
        experiment/approved-change overrides win over the config-file
        defaults this module was constructed with, no restart needed."""
        targets = {
            "temp_min": self.temp_min, "temp_max": self.temp_max,
            "humidity_max": self.humidity_max,
        }
        rows = self.db.execute(
            "SELECT param_name, value FROM target_overrides WHERE cell_id = ? AND active = 1",
            (self.cell_id,),
        ).fetchall()
        for param_name, value in rows:
            if param_name in targets:
                targets[param_name] = value
        return targets

    def evaluate(self, readings: list[SensorReading]) -> list[ActuatorCommand]:
        self._targets = self._current_targets()
        temp_reading = self._latest_of_type(readings, "temp_air")
        humidity_reading = self._latest_of_type(readings, "humidity")

        # None = "not enough trustworthy data yet to decide" -> hold
        # whatever state the actuator is already in, rather than guess.
        heater_needed = None
        fan_needed_temp = None
        fan_needed_humidity = False  # absence of a humidity sensor never forces venting

        if temp_reading is None:
            if not self._is_type_mid_retry("temp_air"):
                self._raise_alert(
                    "warning",
                    f"{self.module_id}: no air temp reading available at all "
                    f"(sensor missing or producing zero data) — heater/fan held at current state",
                )
        else:
            heater_needed, fan_needed_temp = self._evaluate_temp(temp_reading)

        if humidity_reading is not None:
            fan_needed_humidity = self._evaluate_humidity(humidity_reading)
        # No alert for a missing humidity sensor: unlike temp_air, no
        # tier's hardware BOM requires one yet (see
        # describe_hardware_requirements below) — fan still works off
        # temperature alone.

        commands = []
        if heater_needed is not None:
            commands += self._set_actuator("heater", "on" if heater_needed else "off")

        if fan_needed_temp is not None or fan_needed_humidity:
            fan_on = bool(fan_needed_temp) or fan_needed_humidity
            commands += self._set_actuator("fan", "on" if fan_on else "off")

        # Light and CO2 are both genuinely optional hardware (not in any
        # tier's BOM yet) — opt-in per cell, same reasoning as
        # aquaponics_cell.py's DO monitoring, so a cell without either
        # sensor stays completely silent rather than alerting forever.
        if self._has_sensor_type("light"):
            light_reading = self._latest_of_type(readings, "light")
            if light_reading is None:
                if not self._is_type_mid_retry("light"):
                    self._raise_alert(
                        "warning",
                        f"{self.module_id}: no light reading available at all "
                        f"(sensor missing or producing zero data) — grow light held at current state",
                    )
            else:
                light_needed = self._evaluate_light(light_reading)
                if light_needed is not None:
                    commands += self._set_actuator("grow_light", "on" if light_needed else "off")

        if self._has_sensor_type("co2"):
            co2_reading = self._latest_of_type(readings, "co2")
            if co2_reading is None:
                if not self._is_type_mid_retry("co2"):
                    self._raise_alert(
                        "warning",
                        f"{self.module_id}: no CO2 reading available at all "
                        f"(sensor missing or producing zero data) — CO2 injection held",
                    )
            else:
                if self._evaluate_co2(co2_reading):
                    commands += self._inject_co2()

        return commands

    def _evaluate_temp(self, reading: SensorReading) -> tuple[bool | None, bool | None]:
        """Returns (heater_needed, fan_needed) — either can be None if
        there isn't enough consistent history yet to trust a decision."""
        self._temp_history.append(reading.value)
        self._temp_history = self._temp_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._temp_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return None, None

        avg = sum(self._temp_history) / len(self._temp_history)
        spread = max(self._temp_history) - min(self._temp_history)
        if spread > TEMP_SPREAD_TOLERANCE_F:
            self._raise_alert(
                "warning",
                f"{self.module_id}: air temp readings inconsistent "
                f"(spread {spread:.1f}°F) — holding heater/fan at current state this cycle",
            )
            return None, None

        return avg < self._targets["temp_min"], avg > self._targets["temp_max"]

    def _evaluate_humidity(self, reading: SensorReading) -> bool:
        """Returns whether humidity alone justifies venting. Never
        returns True from insufficient/inconsistent data — absence of
        a confident signal here just means fan_needed_humidity stays
        False, deferring entirely to temperature (see evaluate())."""
        self._humidity_history.append(reading.value)
        self._humidity_history = self._humidity_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._humidity_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return False

        avg = sum(self._humidity_history) / len(self._humidity_history)
        spread = max(self._humidity_history) - min(self._humidity_history)
        if spread > HUMIDITY_SPREAD_TOLERANCE_PCT:
            self._raise_alert(
                "warning",
                f"{self.module_id}: humidity readings inconsistent "
                f"(spread {spread:.1f}%RH) — not using humidity for venting this cycle",
            )
            return False

        return avg > self._targets["humidity_max"]

    def _evaluate_light(self, reading: SensorReading) -> bool | None:
        self._light_history.append(reading.value)
        self._light_history = self._light_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._light_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return None

        avg = sum(self._light_history) / len(self._light_history)
        spread = max(self._light_history) - min(self._light_history)
        if spread > LIGHT_SPREAD_TOLERANCE_LUX:
            self._raise_alert(
                "warning",
                f"{self.module_id}: light readings inconsistent (spread {spread:.0f} lux) "
                f"— holding grow light at current state this cycle",
            )
            return None

        return avg < LIGHT_TARGET_MIN_LUX

    def _evaluate_co2(self, reading: SensorReading) -> bool:
        """Returns whether injection is warranted. A dangerously-high
        reading always returns False (never inject into already-unsafe
        air) regardless of any prior low trend — checked before the
        consistency gate since a single genuinely dangerous reading is
        worth flagging immediately, unlike a routine low-CO2 correction."""
        if reading.value >= CO2_DANGER_PPM:
            self._raise_alert(
                "critical",
                f"{self.module_id}: CO2 dangerously high ({reading.value:.0f} ppm, at/above "
                f"the {CO2_DANGER_PPM:.0f} ppm OSHA 8-hr PEL) — human safety risk, ventilate "
                f"immediately, injection will not fire",
            )
            return False

        self._co2_history.append(reading.value)
        self._co2_history = self._co2_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._co2_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return False

        avg = sum(self._co2_history) / len(self._co2_history)
        spread = max(self._co2_history) - min(self._co2_history)
        if spread > CO2_SPREAD_TOLERANCE_PPM:
            self._raise_alert(
                "warning",
                f"{self.module_id}: CO2 readings inconsistent (spread {spread:.0f} ppm) "
                f"— not confident enough to inject this cycle",
            )
            return False

        return avg < CO2_TARGET_MIN_PPM

    def _inject_co2(self) -> list[ActuatorCommand]:
        """Pulse, not continuous — see this module's own docstring for
        why CO2 injection specifically needs to be conservative. Cooldown-
        limited regardless of how many consecutive cycles read low, same
        reasoning dosing_limits.min_interval_minutes enforces for real
        dosing pumps."""
        now = datetime.utcnow()
        if self._last_co2_injection is not None and \
                (now - self._last_co2_injection) < timedelta(minutes=CO2_INJECTION_COOLDOWN_MINUTES):
            return []
        actuator_id = self._actuator_id_for_type("co2_valve")
        if actuator_id == -1:
            return []  # sensor present but no injector configured — nothing to do
        self._last_co2_injection = now
        logger.info("%s: injecting CO2 (%ss pulse)", self.module_id, CO2_INJECTION_PULSE_SECONDS)
        return [ActuatorCommand(
            actuator_id=actuator_id,
            action="pulse",
            duration_seconds=CO2_INJECTION_PULSE_SECONDS,
            triggered_by=TriggerSource.AUTO_CONTROL,
        )]

    def _has_sensor_type(self, type_name: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM sensors WHERE cell_id = ? AND type = ? AND active = 1 LIMIT 1",
            (self.cell_id, type_name),
        ).fetchone()
        return row is not None

    def _set_actuator(self, actuator_type: str, action: str) -> list[ActuatorCommand]:
        if self._last_action.get(actuator_type) == action:
            return []  # no change - nothing to send, avoids spamming actuator_events every cycle
        self._last_action[actuator_type] = action
        actuator_id = self._actuator_id_for_type(actuator_type)
        logger.info("%s: setting %s -> %s", self.module_id, actuator_type, action)
        return [ActuatorCommand(
            actuator_id=actuator_id,
            action=action,
            duration_seconds=None,
            triggered_by=TriggerSource.AUTO_CONTROL,
        )]

    def _actuator_id_for_type(self, actuator_type: str) -> int:
        cur = self.db.execute(
            "SELECT id FROM actuators WHERE cell_id = ? AND type = ? LIMIT 1",
            (self.cell_id, actuator_type),
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
        """All sensors stale/invalid: force heater OFF (dangerous if
        stuck on — same reasoning as dosing pumps defaulting off) and
        fan ON (safe if stuck on — same reasoning as aeration/
        circulation never being shed). Unlike evaluate()'s steady-state
        path, this asserts every cycle the fault persists rather than
        deduping — matches PowerMonitor._load_shed_commands()'s existing
        precedent of reasserting a safety state continuously rather than
        once, so a dropped command doesn't leave the real actuator in an
        unsafe state. Clears _last_action so evaluate() re-decides fresh
        once real readings return, instead of a stale dedup entry
        suppressing the first real correction after recovery."""
        commands = super()._safety_fallback_commands()
        self._last_action.clear()
        heater_id = self._actuator_id_for_type("heater")
        fan_id = self._actuator_id_for_type("fan")
        light_id = self._actuator_id_for_type("grow_light")
        if heater_id != -1:
            commands.append(ActuatorCommand(
                actuator_id=heater_id, action="off", triggered_by=TriggerSource.SAFETY_FALLBACK,
            ))
        if fan_id != -1:
            commands.append(ActuatorCommand(
                actuator_id=fan_id, action="on", triggered_by=TriggerSource.SAFETY_FALLBACK,
            ))
        if light_id != -1:
            # No hazard either way (same non-hazard class as fan), but
            # nothing to gain running it blind either — off is just the
            # conservative no-op default. Unlike heater/fan, this is a
            # judgment call, not a hard safety requirement.
            commands.append(ActuatorCommand(
                actuator_id=light_id, action="off", triggered_by=TriggerSource.SAFETY_FALLBACK,
            ))
        # Deliberately no co2_valve fallback command: injecting blindly
        # while sensor data can't be trusted risks pushing an already-
        # elevated reading into CO2_DANGER_PPM territory unseen — the
        # only safe move when we can't verify current CO2 is to do
        # nothing, which omitting a command already achieves.
        return commands

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id=self.module_id,
            display_name="Climate Control",
            purpose=(
                "Monitors greenhouse air temperature and humidity for one cell/zone and "
                "drives a heater and exhaust fan to keep both within target range — heater "
                "for low temp, fan for high temp or high humidity, using multiple consistent "
                "readings before acting, same as pH/EC dosing. Also drives supplemental grow "
                "lighting and CO2 enrichment injection, opt-in per cell, if those sensors exist."
            ),
            data_produced=[
                "air temp reading history", "humidity reading history",
                "light reading history (if configured)", "CO2 reading history (if configured)",
            ],
            actions_possible=[
                "turn the heater on/off",
                "turn the exhaust fan on/off (temperature- or humidity-driven)",
                "turn supplemental grow lighting on/off",
                "pulse a CO2 injector valve, cooldown-limited, when CO2 reads low and isn't "
                "already at a dangerous level",
            ],
            limits_and_safety=(
                f"Targets: temp {self.temp_min}-{self.temp_max}°F, humidity below "
                f"{self.humidity_max}%RH, light above {LIGHT_TARGET_MIN_LUX:.0f} lux, CO2 above "
                f"{CO2_TARGET_MIN_PPM:.0f} ppm. Requires {self.MIN_CONSISTENT_READINGS_FOR_DOSE} "
                "consistent readings before acting on any sensor. Holds current actuator "
                "state (never guesses) when readings are missing, inconsistent, or insufficient. "
                "On totally stale/missing sensor data: forces heater OFF (stuck-on fire/scorch "
                "risk, same category as a stuck-open dosing pump), fan ON (safe if stuck on, "
                "same category as aeration), and grow light OFF (no hazard either way, just a "
                "conservative no-op) — never left in whatever state they happened to be in "
                f"before data was lost. CO2 is genuinely different: a reading at/above "
                f"{CO2_DANGER_PPM:.0f} ppm (OSHA's 8-hr PEL) raises a critical alert and refuses "
                f"to inject regardless of any prior low trend; injection is a "
                f"{CO2_INJECTION_PULSE_SECONDS:.0f}s pulse, never continuous, cooldown-limited to "
                f"once per {CO2_INJECTION_COOLDOWN_MINUTES} minutes; and on total sensor loss, "
                "CO2 injection is deliberately withheld entirely (not forced to any state) since "
                "injecting blind risks pushing an already-elevated reading into danger unseen. "
                "Light/CO2 are both opt-in per cell — a cell with neither sensor configured "
                "raises nothing about either, ever."
            ),
            example_questions=[
                "Is the heater on?", "How humid is it in the greenhouse?",
                "Why did the fan turn on?", "Is the CO2 level safe?", "Are the grow lights on?",
            ],
            verification_evidence=[
                "scenarios.py::scenario_climate_control_heater_trigger — confirmed heater turns "
                "on after 3 consistent below-range temp readings, fan stays off",
                "scenarios.py::scenario_climate_control_fan_trigger_temp — confirmed fan turns on "
                "after 3 consistent above-range temp readings, heater stays off",
                "scenarios.py::scenario_climate_control_fan_trigger_humidity — confirmed fan turns "
                "on from high humidity alone even with in-range temperature",
                "scenarios.py::scenario_climate_control_no_repeat_commands — confirmed a steady "
                "in-range state emits zero repeat commands across multiple cycles (only a real "
                "state change produces a command)",
                "scenarios.py::scenario_climate_control_safety_fallback — confirmed all-stale "
                "sensor data forces heater off, fan on, and light off unconditionally, every "
                "cycle the fault persists",
                "scenarios.py::scenario_climate_control_light_no_sensor_silent — confirmed a cell "
                "with no light sensor configured raises nothing about light, ever",
                "scenarios.py::scenario_climate_control_light_trigger — confirmed the grow light "
                "turns on after 3 consistent below-target lux readings",
                "scenarios.py::scenario_climate_control_co2_injection — confirmed a low, "
                "consistent CO2 reading triggers exactly one injection pulse, not one per cycle "
                "(cooldown enforced)",
                "scenarios.py::scenario_climate_control_co2_danger_no_inject — confirmed a "
                "reading at/above the OSHA PEL raises a critical alert and never injects",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="DHT22 / AM2302 air temp + humidity sensor", category="sensor",
                quantity=1, purpose="feeds both temp_air and humidity readings this module acts on",
                est_unit_cost=15.0,
                notes="Estimate, not independently live-fetched this session — typical current "
                      "market price for this class of sensor is ~$10-15 (e.g. Adafruit's AM2302). "
                      "Confirm at checkout. One physical part satisfies both sensor rows.",
            ),
            HardwareRequirement(
                item="24\" shutter-mount exhaust fan, 115V", category="actuator",
                quantity=1, purpose="vents excess heat or humidity",
                est_unit_cost=159.99,
                notes="Confirmed live-fetch 2026-08-31, Bootstrap Farmer — see "
                      "docs/HARDWARE_BOM_FULL_TIERS.md. A smaller/cheaper computer-style fan "
                      "may suffice below full-scale; not separately priced.",
            ),
            HardwareRequirement(
                item="Thermostatic propane greenhouse heater, 30,000-60,000 BTU", category="actuator",
                quantity=1, purpose="frost/cold protection",
                est_unit_cost=275.0,
                notes="Estimated $150-400 range, not confirmed via live fetch (2 attempts failed "
                      "technically, not because the product doesn't exist) — see "
                      "docs/HARDWARE_BOM_FULL_TIERS.md.",
            ),
            HardwareRequirement(
                item="Lux/light sensor (e.g. BH1750 I2C)", category="sensor",
                quantity=1, purpose="supplemental grow-light triggering", est_unit_cost=6.0,
                notes="Estimate, not independently live-fetched this session — typical current "
                      "market price for this class of hobbyist I2C lux sensor. Optional — a cell "
                      "without one never mentions light at all.",
            ),
            HardwareRequirement(
                item="Supplemental grow light fixture (relay-switched)", category="actuator",
                quantity=1, purpose="extends photoperiod / compensates for low ambient light",
                est_unit_cost=40.0,
                notes="Estimate, not independently live-fetched this session — wide real range "
                      "depending on fixture size/type; a small full-spectrum LED panel is a "
                      "reasonable starting point.",
            ),
            HardwareRequirement(
                item="CO2 sensor (NDIR, e.g. MH-Z19)", category="sensor",
                quantity=1, purpose="CO2 enrichment triggering and a real human-safety ceiling check",
                est_unit_cost=25.0,
                notes="Estimate, not independently live-fetched this session — typical current "
                      "market price for this class of hobbyist NDIR CO2 sensor (cheap MQ-135-style "
                      "sensors are NOT accurate enough for this — NDIR is the real requirement). "
                      "Optional — a cell without one never mentions CO2 at all.",
            ),
            HardwareRequirement(
                item="CO2 injector / regulator valve (solenoid, food-safe)", category="actuator",
                quantity=1, purpose="pulsed CO2 enrichment injection",
                est_unit_cost=35.0,
                notes="Estimate, not independently live-fetched this session — a real CO2 "
                      "enrichment system also needs a CO2 source tank/generator, not priced here. "
                      "This module only ever pulses it briefly, cooldown-limited — see "
                      "limits_and_safety above.",
            ),
        ]
