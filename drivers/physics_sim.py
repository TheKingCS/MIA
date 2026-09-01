"""
MIA Homestead — Physics-Informed Simulator (Tier 2)
v0.2

Extends the basic simulator with real cause-and-effect:
- pH drifts down over time from nitrification (real aquaponics behavior —
  fish waste -> ammonia -> nitrite -> nitrate via bacteria, which is
  net acidifying). This is WHY periodic pH-up dosing is needed for real.
- EC drifts up slowly from evaporation concentrating dissolved solids,
  and down slowly from plant nutrient uptake.
- Water level drops from evaporation.
- Dosing pulses issued by the control loop actually move pH/EC in the
  correct direction by a plausible amount — this is what makes it a
  real test of the control logic, not just a data generator.

v0.2 (2026-09-01, user request — "improve physics_sim.py's realism")
closes the SAME kind of loop for this session's newer actuators, which
had none at all until now — a scenario driving the heater/fan/water
heater/grow light/CO2 injector could confirm a COMMAND was issued, but
never that it actually changed anything, unlike pH/EC's real recovery
already being provable (see scenario_ph_crash_response's "closed-loop
physics shows pH recovering from the correction"):
- Air temp slowly loses heat without active heating (why the heater is
  occasionally needed); the heater/fan push it back the other way while
  commanded on. Water temp is thermally buffered — it just slowly
  follows air temp, plus the water heater while commanded on.
- Humidity and CO2 both slowly rise without ventilation (transpiration/
  evaporation; fish and bacterial respiration) — why the fan matters for
  both, not just temperature. The fan vents both down while commanded on.
- Dissolved oxygen relaxes toward a temperature-dependent equilibrium
  (warmer water holds less DO) — a real, simple, physically-grounded
  relationship, not a fixed constant.
- The grow light sets light level toward a real target (ambient vs.
  ambient+boosted) rather than never changing at all.
- A CO2 injector pulse raises CO2 by a plausible amount, same
  effect-proportional-to-duration shape as pH/EC dosing.

Unlike ph_up/ph_down/nutrient_concentrate (one-shot PULSE dosing),
heater/fan/water_heater/grow_light are ON/OFF states that persist until
changed — modeling their effect correctly means tracking CURRENT
commanded state (self.actuator_states), not just reacting to the
moment a command was issued. See apply_pending_actuator_events().

Also provides fault injection methods used by scenarios/scenarios.py:
sensor dropout, stale data, out-of-range spikes, power loss simulation.

Usage as a library (see scenarios/scenarios.py for real usage):
    sim = PhysicsSimulator(conn, cell_id=1)
    sim.tick()                          # one time step, natural dynamics
    sim.apply_pending_actuator_events()  # apply any new dosing commands
    sim.inject_sensor_dropout('ph')      # fault: stop updating pH sensor
"""

import logging
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger("mia_homestead.physics_sim")

# Physical model constants — starting estimates, NOT calibrated against
# real hardware. Tune once real sensors/dosing pumps exist and you can
# compare simulated vs actual response.
NITRIFICATION_PH_DRIFT_PER_TICK = -0.01      # natural acidification
EVAPORATION_EC_DRIFT_PER_TICK = 0.4          # concentration effect
NUTRIENT_UPTAKE_EC_DRIFT_PER_TICK = -0.6     # plant consumption
EVAPORATION_LEVEL_DRIFT_PER_TICK = -0.02     # inches per tick

# Environmental drift/actuation — same "starting estimate, not
# calibrated" honesty as above. Explains WHY heater/fan/water_heater
# occasionally need to act, the same way nitrification explains
# periodic pH-up dosing.
AIR_HEAT_LOSS_PER_TICK = -0.05           # °F/tick — greenhouses lose heat without active heating
HEATER_WARMING_PER_TICK = 0.3            # °F/tick while the heater is commanded on
FAN_COOLING_PER_TICK = 0.25              # °F/tick while the fan is commanded on
HUMIDITY_RISE_PER_TICK = 0.15            # %RH/tick — transpiration/evaporation without venting
FAN_DRYING_PER_TICK = 0.4                # %RH/tick removed while the fan is commanded on
WATER_HEATER_WARMING_PER_TICK = 0.15     # °F/tick while the water heater is commanded on — slower than air, water's thermal mass
WATER_AIR_COUPLING_RATE = 0.02           # fraction of the water/air temp gap closed per tick — water slowly follows air, buffered
CO2_RESPIRATION_RISE_PER_TICK = 3.0      # ppm/tick — fish/bacterial respiration without venting
FAN_CO2_VENTING_PER_TICK = 5.0           # ppm/tick removed while the fan is commanded on
CO2_AMBIENT_FLOOR_PPM = 300.0            # never drifts below real outdoor-ish ambient
DO_TEMP_EQUILIBRIUM_AT_74F = 7.8         # mg/L — real DO saturation is temperature-dependent
DO_TEMP_COEFFICIENT = 0.04               # mg/L equilibrium shift per °F away from 74°F (warmer water holds less DO)
DO_RELAXATION_RATE = 0.03                # fraction of the gap to equilibrium closed per tick
AMBIENT_LIGHT_LUX = 2000.0               # baseline without supplemental lighting
GROW_LIGHT_BOOST_LUX = 6000.0            # added on top of ambient while the grow light is commanded on

# Actuator types tracked as ongoing ON/OFF STATE (not one-shot pulses) —
# see apply_pending_actuator_events()'s own docstring for why this is a
# different mechanism from dosing.
TRACKED_ACTUATOR_TYPES = ("heater", "fan", "water_heater", "grow_light")

# Dosing effect: how much a pulse moves the reading, roughly proportional
# to pulse duration. Placeholder until real pump flow rate is known.
DOSE_EFFECT_PER_SECOND = {
    "ph_up": 0.08,
    "ph_down": -0.08,
    "nutrient_concentrate": 15.0,   # uS/cm per second of pulse
}
CO2_INJECTION_PPM_PER_SECOND = 10.0   # ppm per second of a co2_valve pulse
DEFAULT_PULSE_SECONDS = 2.0  # used when duration_seconds is None (MVP dosing)


class PhysicsSimulator:
    def __init__(self, conn: sqlite3.Connection, cell_id: int):
        self.conn = conn
        self.cell_id = cell_id
        self.sensors: dict[str, int] = {}   # type -> sensor_id
        self.state: dict[str, float] = {}   # type -> current value
        self.dropped: set[str] = set()      # sensor types not being updated
        self.frozen_stale_since: dict[str, datetime] = {}
        # Current commanded state for ON/OFF actuators (see
        # TRACKED_ACTUATOR_TYPES) — starts "off" for all of them,
        # regardless of real history before this simulator instance
        # existed, same "ignore history before I started" precedent
        # self._last_actuator_event_id already sets for dosing pulses.
        self.actuator_states: dict[str, str] = {t: "off" for t in TRACKED_ACTUATOR_TYPES}
        self._last_actuator_event_id = 0
        self._load()

    def _load(self):
        rows = self.conn.execute(
            "SELECT id, type FROM sensors WHERE cell_id = ? AND active = 1",
            (self.cell_id,),
        ).fetchall()
        for sensor_id, sensor_type in rows:
            self.sensors[sensor_type] = sensor_id
        # seed initial state from most recent reading, or a sane default
        defaults = {
            "ph": 6.9, "ec": 950, "temp_water": 74.0,
            "temp_air": 78.0, "humidity": 55.0, "level": 24.0,
            "do": 7.5, "flow": 350.0, "co2": 1000.0, "light": AMBIENT_LIGHT_LUX,
        }
        for sensor_type, sensor_id in self.sensors.items():
            row = self.conn.execute(
                "SELECT value FROM sensor_readings WHERE sensor_id = ? "
                "ORDER BY id DESC LIMIT 1", (sensor_id,),
            ).fetchone()
            self.state[sensor_type] = row[0] if row else defaults.get(sensor_type, 0.0)
        last_id = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM actuator_events"
        ).fetchone()[0]
        self._last_actuator_event_id = last_id

    # ---------- Natural dynamics ----------

    def tick(self):
        if "ph" in self.state and "ph" not in self.dropped:
            self.state["ph"] += NITRIFICATION_PH_DRIFT_PER_TICK
        if "ec" in self.state and "ec" not in self.dropped:
            self.state["ec"] += EVAPORATION_EC_DRIFT_PER_TICK
            self.state["ec"] += NUTRIENT_UPTAKE_EC_DRIFT_PER_TICK
        if "level" in self.state and "level" not in self.dropped:
            self.state["level"] += EVAPORATION_LEVEL_DRIFT_PER_TICK

        if "temp_air" in self.state and "temp_air" not in self.dropped:
            self.state["temp_air"] += AIR_HEAT_LOSS_PER_TICK
            if self.actuator_states["heater"] == "on":
                self.state["temp_air"] += HEATER_WARMING_PER_TICK
            if self.actuator_states["fan"] == "on":
                self.state["temp_air"] -= FAN_COOLING_PER_TICK

        if "temp_water" in self.state and "temp_water" not in self.dropped:
            # Buffered by thermal mass — relaxes toward air temp rather
            # than jumping, real behavior for a tank's worth of water.
            air = self.state.get("temp_air", self.state["temp_water"])
            self.state["temp_water"] += (air - self.state["temp_water"]) * WATER_AIR_COUPLING_RATE
            if self.actuator_states["water_heater"] == "on":
                self.state["temp_water"] += WATER_HEATER_WARMING_PER_TICK

        if "humidity" in self.state and "humidity" not in self.dropped:
            self.state["humidity"] += HUMIDITY_RISE_PER_TICK
            if self.actuator_states["fan"] == "on":
                self.state["humidity"] -= FAN_DRYING_PER_TICK
            self.state["humidity"] = max(0.0, min(100.0, self.state["humidity"]))

        if "co2" in self.state and "co2" not in self.dropped:
            self.state["co2"] += CO2_RESPIRATION_RISE_PER_TICK
            if self.actuator_states["fan"] == "on":
                self.state["co2"] -= FAN_CO2_VENTING_PER_TICK
            self.state["co2"] = max(CO2_AMBIENT_FLOOR_PPM, self.state["co2"])

        if "do" in self.state and "do" not in self.dropped:
            # Real, simple relationship: warmer water holds less
            # dissolved oxygen — DO relaxes toward a temp-dependent
            # equilibrium rather than sitting at a fixed constant.
            water_temp = self.state.get("temp_water", 74.0)
            equilibrium = DO_TEMP_EQUILIBRIUM_AT_74F - (water_temp - 74.0) * DO_TEMP_COEFFICIENT
            self.state["do"] += (equilibrium - self.state["do"]) * DO_RELAXATION_RATE

        if "light" in self.state and "light" not in self.dropped:
            # No thermal-mass-style lag for light — it's effectively
            # instant in reality, so this sets toward the real target
            # directly rather than gradually relaxing like temperature.
            self.state["light"] = AMBIENT_LIGHT_LUX + (
                GROW_LIGHT_BOOST_LUX if self.actuator_states["grow_light"] == "on" else 0.0
            )

        self._write_readings()

    def apply_pending_actuator_events(self):
        """Reads actuator_events written since last check and applies
        their physical effect to simulated state — this is the closed
        loop. Call this after the control loop has run a cycle.

        Two genuinely different mechanisms, both handled here:
        - Dosing/CO2 injection: one-shot PULSE actions, effect
          proportional to pulse duration, applied once at the moment
          the command lands (matches real peristaltic-pump/solenoid
          behavior — a pulse moves a bounded amount then stops).
        - Heater/fan/water_heater/grow_light: ON/OFF STATES that
          persist until explicitly changed. Their physical effect isn't
          a one-shot nudge — it's ongoing for as long as they're
          commanded on, so this only records the CURRENT state
          (self.actuator_states); tick() is what actually applies the
          per-cycle effect for as long as that state holds.
        """
        rows = self.conn.execute(
            """
            SELECT ae.id, ae.actuator_id, ae.action, ae.duration_seconds, a.name, a.type
            FROM actuator_events ae
            JOIN actuators a ON a.id = ae.actuator_id
            WHERE ae.id > ? AND a.cell_id = ?
            ORDER BY ae.id ASC
            """,
            (self._last_actuator_event_id, self.cell_id),
        ).fetchall()

        for event_id, actuator_id, action, duration, name, actuator_type in rows:
            self._last_actuator_event_id = event_id

            if actuator_type in TRACKED_ACTUATOR_TYPES and action in ("on", "off"):
                self.actuator_states[actuator_type] = action
                logger.info("physics_sim: %s now %s", actuator_type, action)
                continue

            if action != "pulse":
                continue

            if actuator_type == "co2_valve":
                if "co2" in self.state:
                    seconds = duration if duration else DEFAULT_PULSE_SECONDS
                    self.state["co2"] += CO2_INJECTION_PPM_PER_SECOND * seconds
                    logger.info(
                        "physics_sim: applied CO2 injection pulse -> CO2 now %.0f",
                        self.state["co2"],
                    )
                continue

            dose_type = self._dose_type_from_actuator_name(name)
            if dose_type is None:
                continue
            seconds = duration if duration else DEFAULT_PULSE_SECONDS
            effect = DOSE_EFFECT_PER_SECOND.get(dose_type, 0.0) * seconds

            if dose_type in ("ph_up", "ph_down") and "ph" in self.state:
                self.state["ph"] += effect
                logger.info(
                    "physics_sim: applied %s pulse -> pH now %.3f",
                    dose_type, self.state["ph"],
                )
            elif dose_type == "nutrient_concentrate" and "ec" in self.state:
                self.state["ec"] += effect
                logger.info(
                    "physics_sim: applied nutrient dose -> EC now %.1f",
                    self.state["ec"],
                )

    @staticmethod
    def _dose_type_from_actuator_name(name: str) -> str | None:
        for dose_type in DOSE_EFFECT_PER_SECOND:
            if dose_type in name:
                return dose_type
        return None

    def _write_readings(self):
        now_is_dropout = self.dropped
        for sensor_type, sensor_id in self.sensors.items():
            if sensor_type in now_is_dropout:
                continue  # simulate total sensor silence — no row written
            value = self.state.get(sensor_type)
            if value is None:
                continue
            self.conn.execute(
                "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) "
                "VALUES (?, ?, 0, 0)",
                (sensor_id, round(value, 3)),
            )
        self.conn.commit()

    # ---------- Fault injection ----------

    def force_read(self, sensor_type: str) -> bool:
        """Writes one fresh reading for this sensor type immediately,
        outside the normal tick cadence — the physics-sim side of the
        recovery ladder's 'force an immediate reread' step
        (contracts.MiaHomesteadModule._attempt_recovery). Returns False
        (refuses to recover) for an unknown type or one that's been
        deliberately dropped via inject_sensor_dropout — a real total
        sensor failure shouldn't be silently un-dropped by a reread
        request."""
        if sensor_type not in self.sensors or sensor_type in self.dropped:
            return False
        value = self.state.get(sensor_type)
        if value is None:
            return False
        self.conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) "
            "VALUES (?, ?, 0, 0)",
            (self.sensors[sensor_type], round(value, 3)),
        )
        self.conn.commit()
        return True

    def inject_sensor_dropout(self, sensor_type: str):
        """Simulates total sensor failure — no new readings written at
        all, so existing rows naturally age past the staleness threshold."""
        self.dropped.add(sensor_type)
        logger.info("FAULT INJECTED: %s sensor dropout for cell %s", sensor_type, self.cell_id)

    def clear_sensor_dropout(self, sensor_type: str):
        self.dropped.discard(sensor_type)

    def inject_out_of_range(self, sensor_type: str, bad_value: float):
        """Writes one physically implausible reading directly, flagged
        out_of_range, mimicking a probe glitch/failure."""
        sensor_id = self.sensors.get(sensor_type)
        if sensor_id is None:
            return
        self.conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) "
            "VALUES (?, ?, 0, 1)",
            (sensor_id, bad_value),
        )
        self.conn.commit()
        logger.info("FAULT INJECTED: out-of-range %s reading (%.2f)", sensor_type, bad_value)

    def inject_ph_crash(self, delta: float):
        """Simulates a real disturbance — e.g. heavy rain diluting an
        outdoor sump, or a large fish die-off spiking ammonia — that
        would genuinely require dosing correction."""
        if "ph" in self.state:
            self.state["ph"] += delta
            logger.info("FAULT INJECTED: pH shifted by %.2f -> now %.3f", delta, self.state["ph"])

    def force_stale_backdate(self, sensor_type: str, minutes_ago: int):
        """Backdates the most recent reading for a sensor type to simulate
        staleness without waiting real time — useful for fast scenario runs."""
        sensor_id = self.sensors.get(sensor_type)
        if sensor_id is None:
            return
        past = (datetime.utcnow() - timedelta(minutes=minutes_ago)).isoformat()
        self.conn.execute(
            "UPDATE sensor_readings SET timestamp = ? WHERE id = "
            "(SELECT MAX(id) FROM sensor_readings WHERE sensor_id = ?)",
            (past, sensor_id),
        )
        self.conn.commit()
