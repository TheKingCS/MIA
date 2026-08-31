"""
MIA Homestead — Scenario Test Harness (Tier 3)
v0.1

Scripts specific failure conditions against a fresh in-memory system and
asserts the safety spec's claims actually hold. Run this after any change
to control logic, before it goes anywhere near real hardware.

Usage:
    python scenarios/scenarios.py                 # run all scenarios
    python scenarios/scenarios.py --only ph_crash  # run one
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contracts.mia_homestead_contract import MiaHomesteadModule
from core.module_registry import ModuleRegistry
from core.notifications import NotificationConfig, NotificationDispatcher
from drivers.physics_sim import PhysicsSimulator
from drivers.simulator import setup_demo_cell


SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "mia_homestead_schema.sql"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "modules.yaml"


def fresh_system():
    """Fresh in-memory DB + registry + physics sim, isolated per scenario
    so scenarios never interfere with each other or with real data."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)

    sim = PhysicsSimulator(conn, cell_id=cell_id)

    # ModuleRegistry normally opens its own connection from a path; for
    # in-memory testing we patch it to reuse this exact connection.
    # force_read_fn is wired to the physics sim (keyed by sensor_type,
    # unlike sensor_id everywhere else) so the recovery ladder's
    # force-reread step is actually exercised by scenarios that need it
    # — must be set before .load() so _instantiate() sees it.
    notifier = NotificationDispatcher(NotificationConfig())
    registry = ModuleRegistry.__new__(ModuleRegistry)
    registry.config_path = CONFIG_PATH
    registry.db_conn = conn
    registry.notifier = notifier
    id_to_type = {v: k for k, v in sim.sensors.items()}
    registry.force_read_fn = lambda sensor_id: sim.force_read(id_to_type.get(sensor_id, ""))
    registry.modules = {}
    registry.load()

    return conn, registry, sim, cell_id


def run_cycles(registry, sim, n=4):
    """Runs n control cycles, applying physics effects between each."""
    all_results = []
    for _ in range(n):
        sim.tick()
        results = registry.run_all_cycles()
        for module_id, commands in results.items():
            for cmd in commands:
                registry.db_conn.execute(
                    "INSERT INTO actuator_events (actuator_id, action, "
                    "duration_seconds, triggered_by) VALUES (?, ?, ?, ?)",
                    (cmd.actuator_id, cmd.action, cmd.duration_seconds, cmd.triggered_by.value),
                )
        registry.db_conn.commit()
        sim.apply_pending_actuator_events()
        all_results.append(results)
    return all_results


def get_alerts(conn, severity=None):
    q = "SELECT severity, source, message FROM alerts"
    params = ()
    if severity:
        q += " WHERE severity = ?"
        params = (severity,)
    return conn.execute(q, params).fetchall()


def get_dose_count(conn, dose_type_substr):
    return conn.execute(
        "SELECT COUNT(*) FROM actuator_events ae JOIN actuators a "
        "ON a.id = ae.actuator_id WHERE a.name LIKE ?",
        (f"%{dose_type_substr}%",),
    ).fetchone()[0]


# ---------- Scenarios ----------

def scenario_stale_sensor_freeze():
    """A pH sensor goes silent after producing readings. Expect: NO
    ph_up/ph_down dosing commands are issued during the freeze, and once
    the recovery ladder's retry budget genuinely exhausts (it's dropped,
    so force-reread correctly can't recover it), a staleness/missing-data
    warning is raised — same end behavior as before the ladder existed,
    just after a bounded retry window instead of immediately."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=2)  # let it establish real readings first
    sim.inject_sensor_dropout("ph")
    run_cycles(registry, sim, n=3)
    sim.force_stale_backdate("ph", minutes_ago=15)  # age the last real reading
    # Enough cycles for the retry ladder to exhaust (dropped sensor, so
    # force-reread correctly refuses to recover it every time) and
    # escalate to the same alert that used to fire immediately.
    for _ in range(MiaHomesteadModule.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT):
        registry.run_all_cycles()

    alerts = get_alerts(conn, "warning")
    dose_count = get_dose_count(conn, "ph_")

    checks = [
        ("staleness/missing-data warning was raised",
         any("stale" in m.lower() or "no ph reading" in m.lower() for _, _, m in alerts)),
        ("no pH dosing occurred while stale", dose_count == 0),
    ]
    return checks


def scenario_ph_crash_response():
    """A real pH disturbance. Expect: after enough consistent readings,
    a ph_up dose is issued, and the closed-loop physics shows pH moving
    back toward target over subsequent cycles."""
    conn, registry, sim, cell_id = fresh_system()
    sim.inject_ph_crash(-0.7)
    ph_before = sim.state["ph"]
    run_cycles(registry, sim, n=5)
    ph_after = sim.state["ph"]

    dose_count = get_dose_count(conn, "ph_up")
    checks = [
        ("a ph_up dose was issued", dose_count > 0),
        (f"pH moved toward target ({ph_before:.2f} -> {ph_after:.2f})", ph_after > ph_before),
    ]
    return checks


def scenario_power_loss_load_shed():
    """No power telemetry at all (simulating a dead charge controller
    link). Expect: critical alert, and no assumptions made about power
    state — this exercises the 'freeze on missing data' path, not the
    SOC-threshold path, since no telemetry exists to threshold against."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=2)

    alerts = get_alerts(conn, "critical")
    checks = [
        ("critical alert raised for missing power telemetry",
         any("power" in s.lower() or "stale" in m.lower() for _, s, m in alerts)),
    ]
    return checks


def scenario_inconsistent_readings():
    """pH oscillates wildly between reads (simulating a failing/noisy
    probe). Expect: the spread check catches it, no dose is issued
    despite the average technically being out of range."""
    conn, registry, sim, cell_id = fresh_system()
    # Manually oscillate by alternating crashes across cycles
    for i in range(4):
        sim.inject_ph_crash(0.6 if i % 2 == 0 else -0.6)
        sim.tick()
        results = registry.run_all_cycles()
        for module_id, commands in results.items():
            for cmd in commands:
                conn.execute(
                    "INSERT INTO actuator_events (actuator_id, action, "
                    "duration_seconds, triggered_by) VALUES (?, ?, ?, ?)",
                    (cmd.actuator_id, cmd.action, cmd.duration_seconds, cmd.triggered_by.value),
                )
        conn.commit()
        sim.apply_pending_actuator_events()

    warnings = get_alerts(conn, "warning")
    dose_count = get_dose_count(conn, "ph_")
    checks = [
        ("inconsistent-reading warning raised",
         any("inconsistent" in m.lower() for _, _, m in warnings)),
        ("no dose issued on inconsistent data", dose_count == 0),
    ]
    return checks


def scenario_sensor_recovery_ladder_recovers():
    """A pH sensor's reading goes stale for one cycle, but it's still
    'alive' in the physics sim (not dropped) — the ladder's step 1
    (forced immediate reread) should recover it before any staleness
    warning fires at all."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=3)
    sim.force_stale_backdate("ph", minutes_ago=15)
    registry.run_all_cycles()

    alerts = get_alerts(conn, "warning")
    checks = [
        ("no pH staleness warning fired (force-reread recovered it)",
         not any("ph" in m.lower() and "stale" in m.lower() for _, _, m in alerts)),
    ]
    return checks


def scenario_sensor_recovery_exhausted_escalates():
    """A pH sensor is genuinely gone (dropped, so force-reread correctly
    can't recover it) and stale. Expect: no warning during the retry
    window, a warning once retries genuinely exhaust, a real diagnosis
    (not the generic fallback) auto-produced the same cycle, and a
    maintenance task auto-filed with it — the concrete proof that
    'expanded autonomy' (auto-diagnosis) actually fires end to end."""
    from core.infrastructure_registry import InfrastructureRegistry
    from core.maintenance import MaintenanceManager
    from core.diagnostics import DiagnosticEngine

    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=3)
    sim.inject_sensor_dropout("ph")
    sim.force_stale_backdate("ph", minutes_ago=15)

    diagnostics = DiagnosticEngine(conn, InfrastructureRegistry(conn),
                                    maintenance=MaintenanceManager(conn))

    for _ in range(MiaHomesteadModule.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT - 1):
        registry.run_all_cycles()
        diagnostics.auto_diagnose_new_alerts()
    early = get_alerts(conn, "warning")

    registry.run_all_cycles()
    diagnosed = diagnostics.auto_diagnose_new_alerts()
    late = get_alerts(conn, "warning")
    task_count = conn.execute(
        "SELECT COUNT(*) FROM maintenance_tasks WHERE created_by = 'system'"
    ).fetchone()[0]

    checks = [
        ("no pH staleness warning during the retry window",
         not any("ph" in m.lower() and "stale" in m.lower() for _, _, m in early)),
        ("staleness warning fires once retries genuinely exhaust",
         any("ph" in m.lower() and "stale" in m.lower() for _, _, m in late)),
        ("auto-diagnosis produced a real diagnosis, not the generic fallback",
         any(d.get("actuator_name") for d in diagnosed)),
        ("a maintenance task was auto-filed with created_by='system'", task_count > 0),
    ]
    return checks


def scenario_multi_cell_fault_correlation():
    """Two independent cells (cell_a_aquaponics + pilot_cell) lose their
    pH sensor at the same time — a shared-infrastructure symptom
    (power, the Pi itself, a shared bus), not two coincidental probe
    failures. Expect the diagnostic engine to recognize the correlation
    and file ONE 'shared infrastructure' diagnosis referencing both
    cells, instead of two independent 'sensor stale' diagnoses that
    would send someone chasing two separate probes."""
    from drivers.simulator import setup_pilot_cell
    from core.infrastructure_registry import InfrastructureRegistry
    from core.maintenance import MaintenanceManager
    from core.diagnostics import DiagnosticEngine

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_a_id = setup_demo_cell(conn)
    pilot_id = setup_pilot_cell(conn)

    sim_a = PhysicsSimulator(conn, cell_id=cell_a_id)
    sim_p = PhysicsSimulator(conn, cell_id=pilot_id)
    id_to_sim_and_type = {}
    for sim in (sim_a, sim_p):
        for sensor_type, sensor_id in sim.sensors.items():
            id_to_sim_and_type[sensor_id] = (sim, sensor_type)

    def force_read_fn(sensor_id):
        entry = id_to_sim_and_type.get(sensor_id)
        if not entry:
            return False
        sim, sensor_type = entry
        return sim.force_read(sensor_type)

    notifier = NotificationDispatcher(NotificationConfig())
    registry = ModuleRegistry.__new__(ModuleRegistry)
    registry.config_path = CONFIG_PATH
    registry.db_conn = conn
    registry.notifier = notifier
    registry.force_read_fn = force_read_fn
    registry.modules = {}
    registry.load()

    for _ in range(3):
        sim_a.tick(); sim_p.tick()
        registry.run_all_cycles()
        sim_a.apply_pending_actuator_events()
        sim_p.apply_pending_actuator_events()

    sim_a.inject_sensor_dropout("ph")
    sim_p.inject_sensor_dropout("ph")
    sim_a.force_stale_backdate("ph", minutes_ago=15)
    sim_p.force_stale_backdate("ph", minutes_ago=15)

    diagnostics = DiagnosticEngine(conn, InfrastructureRegistry(conn),
                                    maintenance=MaintenanceManager(conn))
    for _ in range(MiaHomesteadModule.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT):
        registry.run_all_cycles()
        diagnostics.auto_diagnose_new_alerts()

    exhausted_alerts = conn.execute(
        "SELECT source, message FROM alerts WHERE resolved = 0 AND message LIKE '%ph sensor%' "
        "AND message LIKE '%exhausted%'"
    ).fetchall()
    correlated_tasks = conn.execute(
        "SELECT COUNT(*) FROM maintenance_tasks WHERE title LIKE '%Shared infrastructure%'"
    ).fetchone()[0]
    isolated_ph_tasks = conn.execute(
        "SELECT COUNT(*) FROM maintenance_tasks WHERE title LIKE '%Investigate%(ph)%'"
    ).fetchone()[0]

    checks = [
        ("both cells' pH sensors independently escalated to a real alert",
         len({s for s, _ in exhausted_alerts}) == 2),
        ("a shared-infrastructure diagnosis was filed for the correlated fault",
         correlated_tasks >= 1),
        ("no separate isolated per-sensor 'ph' diagnosis task was ALSO filed for these",
         isolated_ph_tasks == 0),
    ]
    return checks


def scenario_closed_loop_species_learning():
    """A confirmed, human-approved experiment result on cell_a should
    both (a) extend the species' own knowledge base, not just that one
    cell's target, and (b) automatically inform a LATER proactive
    proposal on a completely different cell (pilot_cell) growing the
    same species — proving the closed loop actually closes, not just
    that refine_from_experiment() works in isolation."""
    from drivers.simulator import setup_pilot_cell
    from core.species_registry import SpeciesRegistry
    from core.bed_planting import BedPlantingManager
    from core.experiment_manager import ExperimentManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_a_id = setup_demo_cell(conn)
    pilot_id = setup_pilot_cell(conn)

    species_registry = SpeciesRegistry(conn)
    lettuce = species_registry.find_by_name("Lettuce")
    lettuce_id = lettuce["id"]
    baseline_ec_max = lettuce["ec_max"]  # 1400 per BASELINE_SPECIES

    planting_mgr = BedPlantingManager(conn, species_registry)
    experiments = ExperimentManager(conn, species_registry=species_registry)

    # ---- Cell A: run a real experiment to a confirmed, approved result ----
    planting_mgr.plant(
        grow_bed_name="Cell A Tray", cell_id=cell_a_id, species_id=lettuce_id,
        expected_harvest_date=(datetime.utcnow() + timedelta(days=25)).isoformat(),
        expected_yield_amount=20, expected_yield_unit="heads",
    )

    exp_id = experiments.propose_experiment(
        cell_id=cell_a_id, hypothesis="test EC above species baseline max",
        variable_changed="ec_target_max", baseline_value=1500, test_value=1600,
        duration_days=1,
    )
    experiments.start_experiment(exp_id)
    started_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
    conn.execute("UPDATE experiments SET started_at = ? WHERE id = ?", (started_at, exp_id))
    conn.commit()

    # Before window (baseline yield, lower) and during window (higher —
    # a real +40% improvement, comfortably past the >10% "adopt" bar).
    before_ts = (datetime.utcnow() - timedelta(days=5)).isoformat()
    during_ts = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    for ts, qty in [(before_ts, 10), (before_ts, 10), (during_ts, 14), (during_ts, 14)]:
        conn.execute(
            "INSERT INTO yield_events (cell_id, timestamp, yield_type, item, quantity) "
            "VALUES (?, ?, 'harvest_produce', 'lettuce', ?)",
            (cell_a_id, ts, qty),
        )
    conn.commit()

    result = experiments.complete_experiment(exp_id)
    proposal = conn.execute(
        "SELECT id FROM parameter_change_proposals WHERE experiment_id = ?", (exp_id,)
    ).fetchone()
    experiments.approve_parameter_change(proposal[0])

    refined = species_registry.get_profile(lettuce_id)

    # ---- Pilot cell: a different cell, same species, underperforming ----
    planting_mgr.plant(
        grow_bed_name="Pilot Tray", cell_id=pilot_id, species_id=lettuce_id,
        expected_harvest_date=(datetime.utcnow() + timedelta(days=15)).isoformat(),
        expected_yield_amount=10, expected_yield_unit="heads",
    )
    conn.execute(
        "UPDATE bed_plantings SET planted_date = ? WHERE cell_id = ?",
        ((datetime.utcnow() - timedelta(days=20)).isoformat(), pilot_id),
    )
    conn.commit()

    proposed_ids = experiments.propose_experiments_for_underperformance(species_registry, str(CONFIG_PATH))
    pilot_experiment = conn.execute(
        "SELECT test_value, hypothesis FROM experiments WHERE id IN ({})".format(
            ",".join("?" * len(proposed_ids))
        ) if proposed_ids else "SELECT test_value, hypothesis FROM experiments WHERE 0",
        proposed_ids,
    ).fetchone()

    # ---- Never-narrow guarantee ----
    narrow_attempt = species_registry.refine_from_experiment(lettuce_id, "ec_max", 1450)  # inside 1600, not extending

    checks = [
        ("experiment result was 'adopt' (real +40% yield improvement)", result["suggestion"] == "adopt"),
        ("species ec_max actually extended past the old baseline (1400 -> beyond)",
         refined["ec_max"] is not None and refined["ec_max"] > baseline_ec_max),
        ("species source flipped to 'experiment_derived'", refined["source"] == "experiment_derived"),
        ("a proposal was made for the underperforming pilot planting", len(proposed_ids) == 1),
        ("the pilot proposal's test_value matches the NEWLY refined midpoint, not the stale baseline",
         pilot_experiment is not None
         and abs(pilot_experiment[0] - (refined["ec_min"] + refined["ec_max"]) / 2) < 0.01),
        ("the pilot proposal's hypothesis cites the confirmed evidence, not a generic lookup",
         pilot_experiment is not None and "CONFIRMED EXPERIMENT RESULT" in pilot_experiment[1]),
        ("refine_from_experiment refuses to narrow the range (returns False, no update)",
         narrow_attempt is False and species_registry.get_profile(lettuce_id)["ec_max"] == refined["ec_max"]),
    ]
    return checks


def scenario_pair_confirm_payload_real_ids():
    """The pair_confirm payload firmware relies on to map actuator_id ->
    physical pin must carry the REAL DB actuator ids, not ids that
    happen to be sequential/small by coincidence. Deliberately inserts
    unrelated actuator rows first so the role's own actuators get
    non-trivial, out-of-order ids — a test that only passes if the
    lookup is real, not an accidental match against a 0/1/2 assumption."""
    from core.device_registry import DeviceRegistry

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)

    # Deliberately clear what setup_demo_cell already created, then
    # rebuild with padding rows first so ph_up/ph_down land on ids that
    # do NOT match the old index-assumption bug (which would silently
    # "work" only when ids happen to start at 0/1).
    conn.execute("DELETE FROM actuators WHERE cell_id = ?", (cell_id,))
    conn.commit()
    for i in range(7):
        conn.execute(
            "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'valve', ?, 'off')",
            (cell_id, f"padding_actuator_{i}"),
        )
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'dosing_pump', 'ph_up_pump', 'off')",
        (cell_id,),
    )
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'dosing_pump', 'ph_down_pump', 'off')",
        (cell_id,),
    )
    conn.commit()

    real_ph_up_id = conn.execute(
        "SELECT id FROM actuators WHERE cell_id = ? AND name = 'ph_up_pump'", (cell_id,)
    ).fetchone()[0]
    real_ph_down_id = conn.execute(
        "SELECT id FROM actuators WHERE cell_id = ? AND name = 'ph_down_pump'", (cell_id,)
    ).fetchone()[0]

    dr = DeviceRegistry(conn)
    payload = dr.build_pair_confirm_payload("ph_dosing_mcu", cell_id)
    by_name = {c["name"]: c["actuator_id"] for c in payload["controls"]}

    checks = [
        ("ph_up_pump's actuator_id is the real DB id, well past a 0/1 assumption",
         by_name.get("ph_up_pump") == real_ph_up_id and real_ph_up_id > 3),
        ("ph_down_pump's actuator_id is the real DB id, well past a 0/1 assumption",
         by_name.get("ph_down_pump") == real_ph_down_id and real_ph_down_id > 3),
        ("payload has the right message shape", payload["type"] == "pair_confirm" and payload["cell_id"] == cell_id),
    ]
    return checks


def scenario_biofilter_cycle_tracking():
    """The classic aquaponics nitrogen cycle (ammonia -> nitrite ->
    cycled), tracked from real logged manual test results. Proves the
    stage classification transitions correctly, the overclaiming guard
    (2 consecutive clean tests required) actually gates, livestock
    readiness reflects real cycle state, and the overdue-test reminder
    fires only when it should. cell_a_aquaponics comes pre-stocked with
    tilapia from setup_demo_cell() itself (a real, common scenario —
    fish-in cycling, not just fishless) — used for the "stocked" cases;
    pilot_cell starts genuinely unstocked — used for the "not stocked
    yet, safe to add" case."""
    from drivers.simulator import setup_pilot_cell
    from core.biofilter_model import BiofilterModel

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)  # already stocked (tilapia) per setup_demo_cell()
    pilot_id = setup_pilot_cell(conn)  # NOT stocked per setup_pilot_cell()
    bm = BiofilterModel(conn)

    # ---- cell_a: stage 1, ammonia rising, no nitrite yet ----
    bm.record_test(cell_id, ammonia_ppm=1.0, nitrite_ppm=0.0, nitrate_ppm=0.0)
    stage_1 = bm.get_cycle_status(cell_id)["stage"]

    # ---- cell_a: stage 2, ammonia falling, nitrite rising (Nitrosomonas established) ----
    bm.record_test(cell_id, ammonia_ppm=0.5, nitrite_ppm=1.5, nitrate_ppm=1.0)
    stage_2 = bm.get_cycle_status(cell_id)["stage"]

    # ---- cell_a: stocked + genuinely not cycled yet -> real warning ----
    ready_while_stocked_uncycled = bm.check_livestock_readiness(cell_id)

    # ---- cell_a: backdate the latest test so it reads as overdue, confirm
    # the reminder fires for a real stocked-and-uncycled-and-untested-
    # recently cell ----
    conn.execute(
        "UPDATE water_quality_tests SET timestamp = datetime('now', '-20 days') "
        "WHERE id = (SELECT MAX(id) FROM water_quality_tests WHERE cell_id = ?)",
        (cell_id,),
    )
    conn.commit()
    overdue_mid_cycle = {f["cell_id"] for f in bm.check_overdue_water_tests()}

    # ---- cell_a: stage 3, first clean test (ammonia+nitrite ~0, nitrate present) ----
    bm.record_test(cell_id, ammonia_ppm=0.0, nitrite_ppm=0.0, nitrate_ppm=10.0)
    single_clean_not_yet_cycled = bm.get_cycle_status(cell_id)["stage"] != "cycled"

    # ---- cell_a: stage 4, SECOND consecutive clean test -> genuinely cycled ----
    bm.record_test(cell_id, ammonia_ppm=0.0, nitrite_ppm=0.0, nitrate_ppm=15.0)
    now_cycled = bm.get_cycle_status(cell_id)["stage"] == "cycled"
    ready_while_stocked_cycled = bm.check_livestock_readiness(cell_id)
    overdue_after_cycled = {f["cell_id"] for f in bm.check_overdue_water_tests()}

    # ---- pilot: not stocked, cycled from 2 direct clean tests -> safe to stock ----
    bm.record_test(pilot_id, ammonia_ppm=0.0, nitrite_ppm=0.0, nitrate_ppm=8.0)
    bm.record_test(pilot_id, ammonia_ppm=0.0, nitrite_ppm=0.0, nitrate_ppm=9.0)
    ready_not_stocked_cycled = bm.check_livestock_readiness(pilot_id)

    checks = [
        ("ammonia-rising test classifies as ammonia_phase (real evidence from 1 reading)",
         stage_1 == "ammonia_phase"),
        ("nitrite-rising test classifies as nitrite_phase", stage_2 == "nitrite_phase"),
        ("fish already stocked + genuinely not cycled -> real warning, not silently OK",
         not ready_while_stocked_uncycled["ready"] and ready_while_stocked_uncycled["stocked"]),
        ("overdue reminder fires for a stocked, not-yet-cycled cell whose latest test is old",
         cell_id in overdue_mid_cycle),
        ("a single clean test alone does NOT yet report cycled (overclaiming guard)",
         single_clean_not_yet_cycled),
        ("two CONSECUTIVE clean tests correctly report cycled", now_cycled),
        ("fish stocked on a NOW-cycled cell -> reports ready/safe",
         ready_while_stocked_cycled["ready"] and ready_while_stocked_cycled["stocked"]),
        ("overdue reminder stays silent once the cell is confirmed cycled",
         cell_id not in overdue_after_cycled),
        ("cycled + no fish stocked yet -> ready to stock",
         ready_not_stocked_cycled["ready"] and not ready_not_stocked_cycled["stocked"]),
    ]
    return checks


def scenario_sensor_confidence():
    """Combines calibration-due proximity and current drift status into
    one high/medium/low trust signal per sensor. Purely informational —
    this scenario proves the classification is correct, not that it
    changes any dosing behavior (it never should, and doesn't)."""
    from core.sensor_confidence import SensorConfidence

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    sc = SensorConfidence(conn)

    ph_sensor_id = conn.execute(
        "SELECT id FROM sensors WHERE cell_id = ? AND type = 'ph'", (cell_id,)
    ).fetchone()[0]
    ec_sensor_id = conn.execute(
        "SELECT id FROM sensors WHERE cell_id = ? AND type = 'ec'", (cell_id,)
    ).fetchone()[0]
    temp_sensor_id = conn.execute(
        "SELECT id FROM sensors WHERE cell_id = ? AND type = 'temp_water'", (cell_id,)
    ).fetchone()[0]

    # ---- high: no calibration_due set, no drift ----
    high_conf = sc.get_confidence(ph_sensor_id)

    # ---- medium: calibration_due in 3 days ----
    conn.execute(
        "UPDATE sensors SET calibration_due = date('now', '+3 days') WHERE id = ?", (ec_sensor_id,)
    )
    conn.commit()
    medium_conf = sc.get_confidence(ec_sensor_id)

    # ---- low: calibration_due already 5 days past ----
    conn.execute(
        "UPDATE sensors SET calibration_due = date('now', '-5 days') WHERE id = ?", (temp_sensor_id,)
    )
    conn.commit()
    overdue_conf = sc.get_confidence(temp_sensor_id)

    # ---- low: currently drifting, regardless of calibration status ----
    # Seed 20 flat baseline readings + 6 readings shifted +5 stdevs,
    # same real pattern trend_analyzer's own verification uses.
    conn.execute("DELETE FROM sensor_readings WHERE sensor_id = ?", (ph_sensor_id,))
    for _ in range(20):
        conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value) VALUES (?, ?)", (ph_sensor_id, 6.4)
        )
    for _ in range(6):
        conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value) VALUES (?, ?)", (ph_sensor_id, 6.4755)
        )
    conn.commit()
    drifting_conf = sc.get_confidence(ph_sensor_id)

    checks = [
        ("no calibration due, no drift -> high confidence, no factors",
         high_conf["level"] == "high" and high_conf["factors"] == []),
        ("calibration due soon -> medium confidence with a real factor string",
         medium_conf["level"] == "medium" and len(medium_conf["factors"]) == 1
         and "3 day" in medium_conf["factors"][0]),
        ("calibration already overdue -> low confidence",
         overdue_conf["level"] == "low" and "overdue" in overdue_conf["factors"][0]),
        ("currently drifting -> low confidence regardless of calibration status, real z-score cited",
         drifting_conf["level"] == "low" and drifting_conf["drift_flagged"]
         and any("z-score" in f for f in drifting_conf["factors"])),
    ]
    return checks


SCENARIOS = {
    "stale_sensor_freeze": scenario_stale_sensor_freeze,
    "ph_crash_response": scenario_ph_crash_response,
    "power_loss_load_shed": scenario_power_loss_load_shed,
    "inconsistent_readings": scenario_inconsistent_readings,
    "sensor_recovery_ladder_recovers": scenario_sensor_recovery_ladder_recovers,
    "sensor_recovery_exhausted_escalates": scenario_sensor_recovery_exhausted_escalates,
    "multi_cell_fault_correlation": scenario_multi_cell_fault_correlation,
    "closed_loop_species_learning": scenario_closed_loop_species_learning,
    "pair_confirm_payload_real_ids": scenario_pair_confirm_payload_real_ids,
    "biofilter_cycle_tracking": scenario_biofilter_cycle_tracking,
    "sensor_confidence": scenario_sensor_confidence,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Run a single scenario by name")
    args = parser.parse_args()

    to_run = {args.only: SCENARIOS[args.only]} if args.only else SCENARIOS

    total_pass, total_fail = 0, 0
    for name, fn in to_run.items():
        print(f"\n=== {name} ===")
        try:
            checks = fn()
        except Exception as e:
            print(f"  ERROR running scenario: {e}")
            total_fail += 1
            continue
        for description, passed in checks:
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {description}")
            total_pass += passed
            total_fail += not passed

    print(f"\n{total_pass} passed, {total_fail} failed")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
