"""
MIA Homestead — Physics-Informed Simulator (Tier 2)
v0.1

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

# Dosing effect: how much a pulse moves the reading, roughly proportional
# to pulse duration. Placeholder until real pump flow rate is known.
DOSE_EFFECT_PER_SECOND = {
    "ph_up": 0.08,
    "ph_down": -0.08,
    "nutrient_concentrate": 15.0,   # uS/cm per second of pulse
}
DEFAULT_PULSE_SECONDS = 2.0  # used when duration_seconds is None (MVP dosing)


class PhysicsSimulator:
    def __init__(self, conn: sqlite3.Connection, cell_id: int):
        self.conn = conn
        self.cell_id = cell_id
        self.sensors: dict[str, int] = {}   # type -> sensor_id
        self.state: dict[str, float] = {}   # type -> current value
        self.dropped: set[str] = set()      # sensor types not being updated
        self.frozen_stale_since: dict[str, datetime] = {}
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

        self._write_readings()

    def apply_pending_actuator_events(self):
        """Reads actuator_events written since last check and applies
        their physical effect to simulated state — this is the closed
        loop. Call this after the control loop has run a cycle."""
        rows = self.conn.execute(
            """
            SELECT ae.id, ae.actuator_id, ae.action, ae.duration_seconds, a.name
            FROM actuator_events ae
            JOIN actuators a ON a.id = ae.actuator_id
            WHERE ae.id > ? AND a.cell_id = ?
            ORDER BY ae.id ASC
            """,
            (self._last_actuator_event_id, self.cell_id),
        ).fetchall()

        for event_id, actuator_id, action, duration, name in rows:
            self._last_actuator_event_id = event_id
            if action != "pulse":
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
