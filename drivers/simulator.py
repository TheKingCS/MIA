"""
MIA Homestead — Sensor Simulator Driver
v0.1

Generates realistic, slowly-drifting fake sensor data and writes it into
sensor_readings, standing in for real hardware drivers. This lets the
entire control loop, dosing logic, alerting, and assistant run and be
tested TODAY, before any hardware is purchased — and it's a genuine
value, not just a demo toy: it's how you'll validate control logic
changes safely before ever pointing them at a real fish tank.

Swapping this for real hardware later means writing one new driver file
matching this same "write into sensor_readings" contract — nothing in
modules/ or contracts/ needs to change.

Usage:
    python drivers/simulator.py --db mia_homestead.db --setup
    python drivers/simulator.py --db mia_homestead.db --run
"""

import argparse
import math
import random
import sqlite3
import time
from datetime import datetime

SIM_SENSOR_DEFS = [
    # (type, unit, start_value, drift_range, noise)
    ("ph", "pH", 6.9, 0.02, 0.03),
    ("ec", "uS/cm", 950, 5, 15),
    ("temp_water", "F", 74.0, 0.1, 0.3),
    ("temp_air", "F", 78.0, 0.3, 0.8),
    ("humidity", "%RH", 55.0, 0.5, 1.5),
    ("level", "in", 24.0, 0.05, 0.1),
]

# Power simulation is a real gap this used to leave entirely unfilled —
# modules/power_monitor.py reads power_telemetry, but nothing wrote to
# it (no driver, real or simulated), so the power panel of every viewer
# and any load-shed logic was permanently untestable and the dashboard
# could only ever show an honest "no data" state. These constants are
# a reasonable simulated array, not a real system's specs — same
# "starting point, not gospel" caveat this project already applies to
# core/species_registry.py's baseline values.
SOLAR_PANEL_WATT_PEAK = 400.0
BASE_LOAD_WATTS = 80.0          # aeration/circulation/electronics baseline draw
SIMULATED_BATTERY_CAPACITY_WH = 2000.0
SIMULATED_BATTERY_START_SOC = 70.0


def _solar_watts_now(now: datetime) -> float:
    """A simple daylight bell curve (sunrise ~6:00, sunset ~20:00,
    peak at solar noon) plus noise — not a real solar-position model,
    just enough day/night variation for load-shed logic and any
    future daylight-aware scheduling to have something real to react
    to, instead of flat noise around a constant."""
    hour = now.hour + now.minute / 60
    if hour < 6 or hour > 20:
        base = 0.0
    else:
        base = SOLAR_PANEL_WATT_PEAK * max(0.0, math.sin(math.pi * (hour - 6) / 14))
    return max(0.0, base + random.uniform(-20, 20))


def setup_demo_cell(conn: sqlite3.Connection) -> int:
    """Creates a demo cell + tank + sensors if none exist yet."""
    cur = conn.execute("SELECT id FROM cells LIMIT 1")
    row = cur.fetchone()
    if row:
        return row[0]

    cur = conn.execute(
        "INSERT INTO cells (name, description) VALUES (?, ?)",
        ("Cell A", "Demo/simulation cell"),
    )
    cell_id = cur.lastrowid

    conn.execute(
        "INSERT INTO tanks (cell_id, name, capacity_gallons, species, stocked_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (cell_id, "Tank A1", 500, "tilapia", datetime.utcnow().isoformat()),
    )
    conn.execute(
        "INSERT INTO grow_beds (cell_id, name, sqft, media_type) VALUES (?, ?, ?, ?)",
        (cell_id, "Bed A1", 100, "expanded clay"),
    )

    for sensor_type, unit, start, _, _ in SIM_SENSOR_DEFS:
        conn.execute(
            "INSERT INTO sensors (cell_id, type, unit, location_note, install_date, active) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (cell_id, sensor_type, unit, "simulated", datetime.utcnow().isoformat()),
        )

    # Demo actuators so dosing commands have somewhere to resolve to
    for name, atype, default in [
        ("ph_up_pump", "dosing_pump", "off"),
        ("ph_down_pump", "dosing_pump", "off"),
        ("nutrient_concentrate_pump", "dosing_pump", "off"),
        ("circulation_pump", "circulation_pump", "on"),
        ("aerator", "aerator", "on"),
    ]:
        conn.execute(
            "INSERT INTO actuators (cell_id, type, name, safe_default_state) "
            "VALUES (?, ?, ?, ?)",
            (cell_id, atype, name, default),
        )

    # Baseline dosing limits so validation logic has something to check
    for dose_type, max_dose, max_day, interval in [
        ("ph_up", 10, 40, 5),
        ("ph_down", 10, 40, 5),
        ("nutrient_concentrate", 20, 100, 10),
    ]:
        conn.execute(
            "INSERT INTO dosing_limits (cell_id, dose_type, max_per_dose_ml, "
            "max_per_day_ml, min_interval_minutes) VALUES (?, ?, ?, ?, ?)",
            (cell_id, dose_type, max_dose, max_day, interval),
        )

    conn.commit()
    print(f"Demo cell created (cell_id={cell_id}) with 6 sensors, 5 actuators.")
    return cell_id


def setup_pilot_cell(conn: sqlite3.Connection) -> int:
    """Creates the 5-gallon pilot cell (docs/PILOT_VS_SCALE.md) if it
    doesn't exist yet — a second, independent AquaponicsCell alongside
    the existing demo cell, deliberately trimmed to the exact hardware
    subset that doc's own shopping list names: a pH probe + DS18B20
    temp probe, one pH-up dosing pump, always-on aeration/circulation.
    No EC probe, no ph-down/nutrient pumps, no fish yet — matches
    "skip EC/nutrient dosing... none of that is needed to validate the
    core safety-critical loop" and "fishless-cycle the biofilter first."

    Deliberately NOT gated on real hardware existing — the pilot is
    buildable in software today (same reasoning the existing demo cell
    already proves out), and running two AquaponicsCell instances
    simultaneously in simulation is itself real validation that the
    modular registry actually handles more than one cell correctly,
    not just in theory (the doc's own stated reason for setting this
    up early)."""
    existing = conn.execute("SELECT id FROM cells WHERE name = 'Pilot Bucket'").fetchone()
    if existing:
        return existing[0]

    cur = conn.execute(
        "INSERT INTO cells (name, description) VALUES (?, ?)",
        ("Pilot Bucket", "5-gallon pilot cell — see docs/PILOT_VS_SCALE.md. "
                         "Real target hardware, not simulation-only like the demo cell."),
    )
    cell_id = cur.lastrowid

    conn.execute(
        "INSERT INTO tanks (cell_id, name, capacity_gallons, species, stocked_date) "
        "VALUES (?, ?, ?, NULL, NULL)",
        (cell_id, "Pilot Bucket Tank", 5),
    )
    conn.execute(
        "INSERT INTO grow_beds (cell_id, name, sqft, media_type) VALUES (?, ?, ?, ?)",
        (cell_id, "Pilot Tray", 1.5, "net pots"),
    )

    # Only pH + water temp — the trimmed pilot BOM doesn't include an EC
    # probe (PILOT_VS_SCALE.md: "the EC loop can wait for phase 2").
    # AquaponicsCell.evaluate() already handles a genuinely-missing
    # sensor correctly (a WARNING, dosing held for that variable, not a
    # crash) — see that method's own ec_reading is None branch.
    for sensor_type, unit, start, _, _ in SIM_SENSOR_DEFS:
        if sensor_type not in ("ph", "temp_water"):
            continue
        conn.execute(
            "INSERT INTO sensors (cell_id, type, unit, location_note, install_date, active) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (cell_id, sensor_type, unit, "pilot — real hardware target", datetime.utcnow().isoformat()),
        )

    # pH-up only to start (no ph-down, no nutrient/EC pump) — matches
    # the trimmed BOM exactly. Aeration/circulation always-on, same
    # safety stance as the demo cell.
    for name, atype, default in [
        ("pilot_ph_up_pump", "dosing_pump", "off"),
        ("pilot_circulation_pump", "circulation_pump", "on"),
        ("pilot_aerator", "aerator", "on"),
    ]:
        conn.execute(
            "INSERT INTO actuators (cell_id, type, name, safe_default_state) "
            "VALUES (?, ?, ?, ?)",
            (cell_id, atype, name, default),
        )

    # Deliberately conservative starting numbers, NOT derived from the
    # full-scale limits by any real ratio — PILOT_VS_SCALE.md priority
    # #2 is calibrating what a real pulse actually does in 5 real
    # gallons; these exist only so dosing_limits validation has
    # something to check before that real number exists, same
    # reasoning setup_demo_cell()'s own limits already document.
    conn.execute(
        "INSERT INTO dosing_limits (cell_id, dose_type, max_per_dose_ml, "
        "max_per_day_ml, min_interval_minutes) VALUES (?, 'ph_up', 0.5, 2, 10)",
        (cell_id,),
    )

    conn.commit()
    print(f"Pilot cell created (cell_id={cell_id}) with 2 sensors (pH, water temp), "
          f"3 actuators (pH-up pump, circulation, aeration).")
    return cell_id


class Simulator:
    """Maintains slowly-drifting state per sensor type and writes new
    readings on each tick — mimics real-world sensor behavior (gradual
    drift, small noise) rather than pure random jitter, so control logic
    gets tested against realistic conditions."""

    def __init__(self, conn: sqlite3.Connection, interval_seconds: float = 5.0):
        self.conn = conn
        self.state: dict[int, float] = {}  # sensor_id -> current value
        self.defs: dict[int, tuple] = {}    # sensor_id -> (drift, noise)
        self._load_sensors()
        self.interval_seconds = interval_seconds
        self.battery_soc = SIMULATED_BATTERY_START_SOC

    def _load_sensors(self):
        rows = self.conn.execute("SELECT id, type FROM sensors WHERE active = 1").fetchall()
        by_type = {d[0]: d for d in SIM_SENSOR_DEFS}
        for sensor_id, sensor_type in rows:
            if sensor_type not in by_type:
                continue
            _, _, start, drift, noise = by_type[sensor_type]
            self.state[sensor_id] = start
            self.defs[sensor_id] = (drift, noise)

    def tick(self):
        for sensor_id, value in self.state.items():
            drift, noise = self.defs[sensor_id]
            value += random.uniform(-drift, drift)
            reading = value + random.uniform(-noise, noise)
            self.state[sensor_id] = value
            self.conn.execute(
                "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) "
                "VALUES (?, ?, 0, 0)",
                (sensor_id, round(reading, 3)),
            )
        self._tick_power()
        self.conn.commit()

    def _tick_power(self):
        """Writes one 'solar' and one 'battery' power_telemetry row per
        tick — see the module-level comment above SOLAR_PANEL_WATT_PEAK
        for why this exists at all. Battery SOC is a simple running
        energy balance (solar in, BASE_LOAD_WATTS constant draw out),
        clamped to [0, 100] — good enough to exercise
        modules/power_monitor.py's load-shed logic realistically
        (charges by day, drains by night), not a claim of physical
        accuracy."""
        now = datetime.utcnow()
        solar_watts = _solar_watts_now(now)
        net_watts = solar_watts - BASE_LOAD_WATTS
        delta_wh = net_watts * (self.interval_seconds / 3600)
        delta_pct = (delta_wh / SIMULATED_BATTERY_CAPACITY_WH) * 100
        self.battery_soc = max(0.0, min(100.0, self.battery_soc + delta_pct))

        self.conn.execute(
            "INSERT INTO power_telemetry (source, watts, battery_soc_percent) VALUES ('solar', ?, NULL)",
            (round(solar_watts, 1),),
        )
        self.conn.execute(
            "INSERT INTO power_telemetry (source, watts, battery_soc_percent) VALUES ('battery', ?, ?)",
            (round(-BASE_LOAD_WATTS, 1), round(self.battery_soc, 2)),
        )

    def inject_event(self, sensor_type: str, delta: float):
        """Manually nudge a sensor type — useful for testing that dosing
        logic actually triggers (e.g. inject_event('ph', -0.5))."""
        for sensor_id in self.state:
            row = self.conn.execute(
                "SELECT type FROM sensors WHERE id = ?", (sensor_id,)
            ).fetchone()
            if row and row[0] == sensor_type:
                self.state[sensor_id] += delta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--setup-pilot", action="store_true", help="Also create the 5-gallon pilot cell (docs/PILOT_VS_SCALE.md)")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between ticks")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)

    if args.setup:
        setup_demo_cell(conn)

    if args.setup_pilot:
        setup_pilot_cell(conn)

    if args.run:
        sim = Simulator(conn, interval_seconds=args.interval)
        print(f"Simulating {len(sim.state)} sensors every {args.interval}s. Ctrl+C to stop.")
        try:
            while True:
                sim.tick()
                print(f"[{datetime.utcnow().isoformat()}] tick written")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
