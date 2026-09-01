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


def get_last_actuator_action(conn, actuator_name_substr):
    row = conn.execute(
        "SELECT ae.action FROM actuator_events ae JOIN actuators a "
        "ON a.id = ae.actuator_id WHERE a.name LIKE ? ORDER BY ae.id DESC LIMIT 1",
        (f"%{actuator_name_substr}%",),
    ).fetchone()
    return row[0] if row else None


def get_actuator_event_count(conn, actuator_name_substr):
    return conn.execute(
        "SELECT COUNT(*) FROM actuator_events ae JOIN actuators a "
        "ON a.id = ae.actuator_id WHERE a.name LIKE ?",
        (f"%{actuator_name_substr}%",),
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


def scenario_fish_health_tracking():
    """Feeding, mortality, and health-observation logging for the fish
    themselves — the biggest gap in an otherwise water-chemistry/plant-
    centric system. Proves feeding history/trend, mortality history,
    and both the population-relative and absolute-count mortality alert
    paths."""
    from core.fish_health import FishHealth

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)  # already stocked (tilapia) per setup_demo_cell()
    fh = FishHealth(conn)

    # ---- Feeding: insufficient data with too few logged ----
    for _ in range(3):
        fh.record_feeding(cell_id, amount=4.0, unit="oz")
    trend_insufficient = fh.get_feeding_trend(cell_id)

    # ---- Feeding: real baseline then a real increase -> 'increasing' ----
    for _ in range(7):
        fh.record_feeding(cell_id, amount=4.0, unit="oz")
    for _ in range(3):
        fh.record_feeding(cell_id, amount=6.5, unit="oz")  # +62% vs the 4.0 baseline
    trend_after_increase = fh.get_feeding_trend(cell_id)
    feeding_history = fh.get_feeding_history(cell_id)

    # ---- Mortality: below both thresholds -> silent ----
    fh.record_mortality(cell_id, count=1, cause="unknown")
    silent_findings = fh.check_mortality_spike()

    # ---- Mortality: quantity_stocked known, crosses the % threshold ----
    conn.execute("UPDATE tanks SET quantity_stocked = 20 WHERE cell_id = ?", (cell_id,))
    conn.commit()
    fh.record_mortality(cell_id, count=2, cause="observed disease symptoms")  # 3 total = 15% of 20
    pct_findings = fh.check_mortality_spike()
    pct_alert = conn.execute(
        "SELECT message FROM alerts WHERE source = 'fish_health' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # ---- Mortality: absolute-count fallback on a DIFFERENT stocked, unknown-quantity cell ----
    from drivers.simulator import setup_pilot_cell
    pilot_id = setup_pilot_cell(conn)
    conn.execute(
        "INSERT INTO tanks (cell_id, name, capacity_gallons, species, stocked_date) "
        "VALUES (?, ?, ?, ?, datetime('now'))",
        (pilot_id, "Pilot Tank", 5, "tilapia"),
    )
    conn.commit()
    fh.record_mortality(pilot_id, count=1)
    below_absolute = fh.check_mortality_spike()
    fh.record_mortality(pilot_id, count=2)  # 3 total, no quantity_stocked -> absolute fallback
    absolute_findings = fh.check_mortality_spike()
    absolute_alert = conn.execute(
        "SELECT message FROM alerts WHERE source = 'fish_health' AND message LIKE ? "
        "ORDER BY id DESC LIMIT 1",
        (f"%cell {pilot_id}%",),
    ).fetchone()

    # ---- Health observations ----
    fh.record_health_observation(cell_id, "Fish appear active and feeding normally")
    observations = fh.get_health_events(cell_id)

    checks = [
        ("too few feedings logged -> honestly reports insufficient_data",
         trend_insufficient["trend"] == "insufficient_data"),
        ("a real +62% feeding increase -> reports 'increasing'",
         trend_after_increase["trend"] == "increasing" and trend_after_increase["pct_change"] > 20),
        ("feeding history returns real logged events", len(feeding_history) == 13),
        ("mortality below both thresholds stays silent", len(silent_findings) == 0),
        ("mortality crossing the population-relative threshold (15% of 20) alerts",
         len(pct_findings) == 1 and pct_alert is not None and "15.0%" in pct_alert[0]),
        ("pilot cell below the absolute fallback threshold (1 death) doesn't itself trigger "
         "(only cell_a's still-standing spike from earlier shows up)",
         len(below_absolute) == 1 and below_absolute[0]["cell_id"] == cell_id),
        ("pilot cell crossing the absolute fallback threshold (3 deaths, no quantity_stocked) "
         "alerts too, honestly noting population size isn't tracked",
         len(absolute_findings) == 2 and absolute_alert is not None
         and "not tracked" in absolute_alert[0]),
        ("health observations log and retrieve correctly", len(observations) == 1),
    ]
    return checks


def scenario_leak_detection():
    """A water level dropping far faster than evaporation could explain
    should raise a real CRITICAL alert within one check — not the
    up-to-60-cycle delay every other periodic check tolerates. Uses
    real wall-clock timestamps (not simulator ticks), so this scenario
    directly controls elapsed time rather than relying on the
    simulator's own deliberately-compressed evaporation rate."""
    from core.leak_detector import LeakDetector

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    ld = LeakDetector(conn)

    level_sensor_id = conn.execute(
        "SELECT id FROM sensors WHERE cell_id = ? AND type = 'level'", (cell_id,)
    ).fetchone()[0]

    def seed_two_readings(older_value, newer_value, minutes_apart):
        conn.execute("DELETE FROM sensor_readings WHERE sensor_id = ?", (level_sensor_id,))
        older_ts = (datetime.utcnow() - timedelta(minutes=minutes_apart)).isoformat(sep=" ")
        newer_ts = datetime.utcnow().isoformat(sep=" ")
        conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value, timestamp) VALUES (?, ?, ?)",
            (level_sensor_id, older_value, older_ts),
        )
        conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value, timestamp) VALUES (?, ?, ?)",
            (level_sensor_id, newer_value, newer_ts),
        )
        conn.commit()

    # ---- Slow, evaporation-plausible drop over a real 10-minute gap ----
    seed_two_readings(older_value=24.0, newer_value=23.98, minutes_apart=10)  # 0.002 in/min
    slow_findings = ld.check_for_leaks()

    # ---- Fast drop over a real 2-minute gap — well past the threshold ----
    seed_two_readings(older_value=24.0, newer_value=22.5, minutes_apart=2)  # 0.75 in/min
    fast_findings = ld.check_for_leaks()
    critical_alert = conn.execute(
        "SELECT severity, message FROM alerts WHERE source = 'leak_detector' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # ---- A level RISE (e.g. after a refill) should never falsely trigger ----
    seed_two_readings(older_value=20.0, newer_value=24.0, minutes_apart=2)  # rising, not falling
    rise_findings = ld.check_for_leaks()

    checks = [
        ("a slow, evaporation-plausible drop does NOT trigger", len(slow_findings) == 0),
        ("a fast, leak-implausible drop DOES trigger", len(fast_findings) == 1
         and fast_findings[0]["cell_id"] == cell_id),
        ("the fast-drop alert is real and CRITICAL severity",
         critical_alert is not None and critical_alert[0] == "critical"),
        ("a level RISE never falsely triggers, regardless of magnitude", len(rise_findings) == 0),
    ]
    return checks


def scenario_pest_disease_tracking():
    """Baseline pest/disease knowledge (real, common aquaponics symptoms
    and guidance) seeds correctly, add_knowledge()/find_knowledge_by_name()
    work, and an observation can log either linked to known knowledge or
    as a genuinely novel unlinked one — both retrieve correctly."""
    from core.pest_disease import PestDisease

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    pd = PestDisease(conn)

    baseline = pd.list_knowledge()
    plant_only = pd.list_knowledge(organism_type="plant")
    fish_only = pd.list_knowledge(organism_type="fish")

    # ---- No duplicate seeding on a second construction ----
    PestDisease(conn)
    baseline_after_reinit = pd.list_knowledge()

    aphids = pd.find_knowledge_by_name("Aphids")

    # ---- Human-added knowledge entry ----
    new_id = pd.add_knowledge(
        organism_type="plant", name="Spider Mites",
        symptoms="Tiny webbing on leaf undersides, stippled/speckled yellowing leaves.",
        guidance="Increase humidity, introduce predatory mites, spray with water/neem oil.",
    )
    spider_mites = pd.find_knowledge_by_name("Spider Mites")

    # ---- Observation linked to known knowledge ----
    linked_obs_id = pd.record_observation(
        cell_id, description="Sticky residue and small insects on new lettuce growth",
        category="pest", knowledge_id=aphids["id"], severity="minor",
    )

    # ---- Observation with no linked knowledge (novel) ----
    novel_obs_id = pd.record_observation(
        cell_id, description="Unusual leaf spotting not matching anything known",
        category="disease",
    )

    history = pd.get_observation_history(cell_id)

    checks = [
        ("baseline knowledge seeds with 6 real entries (3 plant, 3 fish)",
         len(baseline) == 6 and len(plant_only) == 3 and len(fish_only) == 3),
        ("re-constructing PestDisease does NOT duplicate the baseline seed",
         len(baseline_after_reinit) == 6),
        ("find_knowledge_by_name finds a real baseline entry with real guidance",
         aphids is not None and "ladybugs" in aphids["guidance"].lower()),
        ("add_knowledge + find_knowledge_by_name round-trips a human-added entry",
         spider_mites is not None and spider_mites["id"] == new_id
         and spider_mites["source"] == "human_added"),
        ("an observation linked to known knowledge logs and retrieves with that link intact",
         any(o["id"] == linked_obs_id and o["knowledge_id"] == aphids["id"] for o in history)),
        ("a novel, unlinked observation logs and retrieves correctly too",
         any(o["id"] == novel_obs_id and o["knowledge_id"] is None for o in history)),
    ]
    return checks


def scenario_weather_awareness():
    """Frost/heat-wave forecast awareness, deliberately opportunistic —
    the real Open-Meteo network call is stubbed at exactly its own
    boundary (WeatherAwareness._fetch_forecast) so this scenario stays
    fast/deterministic like every other one here, while every other
    real code path (frost math, species-range comparison, alert
    raising, weather_checks logging) runs unmocked, through the real
    check_weather(). Real network reachability against the live
    Open-Meteo API is verified separately (see this module's own
    verification_evidence — a live, non-scenario test)."""
    import tempfile
    import yaml
    from core.species_registry import SpeciesRegistry
    from core.weather_awareness import WeatherAwareness, FROST_THRESHOLD_F

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    SpeciesRegistry(conn)  # seeds baseline species (Lettuce, Basil, Tilapia) into species_profiles

    # ---- No location configured -> honestly skips, no fabricated forecast ----
    wa_unconfigured = WeatherAwareness(conn, config_path="/nonexistent/location.yaml")
    unconfigured_result = wa_unconfigured.check_weather()

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump({"latitude": 39.0997, "longitude": -94.5786}, f)
        config_path = f.name

    # A real active planting with a real documented temp_air range —
    # lettuce, per core/species_registry.py's own BASELINE_SPECIES.
    lettuce = conn.execute("SELECT id FROM species_profiles WHERE common_name = 'Lettuce'").fetchone()[0]
    conn.execute(
        "INSERT INTO bed_plantings (grow_bed_name, cell_id, species_id, status) VALUES (?, ?, ?, 'active')",
        ("Cell A Tray", cell_id, lettuce),
    )
    conn.commit()

    # ---- A forecast comfortably within lettuce's real range -> no alert ----
    wa_ok = WeatherAwareness(conn, config_path=config_path)
    wa_ok._fetch_forecast = lambda lat, lon: {"daily": {"temperature_2m_min": [65.0], "temperature_2m_max": [72.0]}}
    ok_result = wa_ok.check_weather()

    # ---- A frost-risk forecast -> real WARNING alert, real logged row ----
    wa_frost = WeatherAwareness(conn, config_path=config_path)
    wa_frost._fetch_forecast = lambda lat, lon: {"daily": {"temperature_2m_min": [28.0], "temperature_2m_max": [45.0]}}
    frost_result = wa_frost.check_weather()
    frost_alert = conn.execute(
        "SELECT message FROM alerts WHERE source = 'weather_awareness' AND message LIKE '%Frost risk%'"
    ).fetchone()

    # ---- A forecast outside lettuce's real range but above freezing -> species-range warning ----
    wa_hot = WeatherAwareness(conn, config_path=config_path)
    wa_hot._fetch_forecast = lambda lat, lon: {"daily": {"temperature_2m_min": [65.0], "temperature_2m_max": [95.0]}}
    hot_result = wa_hot.check_weather()

    should_check = wa_ok.should_check_now()
    last_check = wa_ok.get_last_check()

    checks = [
        ("no location configured -> honestly returns None, no fabricated forecast",
         unconfigured_result is None),
        ("a forecast within lettuce's real documented range raises nothing",
         ok_result is not None and not ok_result["frost_risk"] and ok_result["species_range_violation"] is None),
        (f"a forecast at/below {FROST_THRESHOLD_F:.0f}F raises a real frost-risk WARNING",
         frost_result is not None and frost_result["frost_risk"] and frost_alert is not None),
        ("a forecast outside lettuce's real range (but above freezing) raises a real, "
         "correctly-worded species-range violation citing the actual documented max",
         hot_result is not None and hot_result["species_range_violation"] is not None
         and "temp_air_max" not in hot_result["species_range_violation"]  # real number cited, not the column name
         and not hot_result["frost_risk"]),
        ("get_last_check() and should_check_now() reflect real logged state",
         last_check is not None and should_check is False),
    ]
    return checks


def scenario_cost_profitability():
    """Real revenue write path (a genuine gap found while building this
    — revenue_transactions existed and was already read by the
    dashboard exporter, but nothing ever wrote to it) plus real
    consumable cost from inventory_transactions x inventory_items.unit_cost.
    Proves the unknown-cost-item exclusion doesn't silently treat it as
    $0, and that profitability nets real revenue minus real cost."""
    from core.finance_tracker import FinanceTracker

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    ft = FinanceTracker(conn)

    # ---- Revenue: a real recorded sale ----
    txn_id = ft.record_revenue(
        item="lettuce", quantity=5, unit="lb", unit_price=4.0,
        cell_id=cell_id, channel="farmers_market",
    )
    revenue_summary = ft.get_revenue_summary(days=30)

    # ---- Cost: seed two consumed items — one with a known unit_cost, one without ----
    conn.execute(
        "INSERT INTO inventory_items (name, category, unit, unit_cost) VALUES "
        "('pH-up solution', 'chemical', 'ml', 0.05), ('mystery additive', 'chemical', 'ml', NULL)"
    )
    conn.commit()
    ph_item_id, mystery_item_id = [
        r[0] for r in conn.execute(
            "SELECT id FROM inventory_items WHERE name IN ('pH-up solution', 'mystery additive') ORDER BY id"
        ).fetchall()
    ]
    conn.execute(
        "INSERT INTO inventory_transactions (item_id, change_qty, reason) VALUES (?, -200, 'dosing_consumption')",
        (ph_item_id,),  # 200ml consumed @ $0.05/ml = $10.00 real cost
    )
    conn.execute(
        "INSERT INTO inventory_transactions (item_id, change_qty, reason) VALUES (?, -50, 'dosing_consumption')",
        (mystery_item_id,),  # 50ml consumed, but unit_cost is unknown
    )
    conn.commit()
    cost_summary = ft.get_cost_summary(days=30)

    profitability = ft.get_profitability_summary(days=30)

    checks = [
        ("record_revenue computes total_amount correctly (5 x $4.00 = $20.00)",
         revenue_summary["total_revenue"] == 20.0 and len(revenue_summary["transactions"]) == 1
         and revenue_summary["transactions"][0]["id"] == txn_id),
        ("cost of the known-cost item is correctly computed (200ml x $0.05 = $10.00)",
         cost_summary["total_cost"] == 10.0 and cost_summary["by_category"].get("chemical") == 10.0),
        ("the unknown-cost item is excluded from the total, not silently treated as $0",
         "mystery additive" in cost_summary["items_with_unknown_cost"]),
        ("profitability nets real revenue minus real cost ($20.00 - $10.00 = $10.00)",
         profitability["net_margin"] == 10.0 and profitability["total_revenue"] == 20.0
         and profitability["total_cost"] == 10.0),
    ]
    return checks


def scenario_climate_control_heater_trigger():
    """Air temp drops well below target (55°F vs. a 65-85 target band).
    Expect: after enough consistent readings, the heater turns on and
    the fan does not."""
    conn, registry, sim, cell_id = fresh_system()
    sim.state["temp_air"] = 55.0
    run_cycles(registry, sim, n=4)

    checks = [
        ("heater turned on", get_last_actuator_action(conn, "greenhouse_heater") == "on"),
        ("fan did not turn on", get_last_actuator_action(conn, "greenhouse_exhaust_fan") != "on"),
    ]
    return checks


def scenario_climate_control_fan_trigger_temp():
    """Air temp climbs well above target (95°F vs. an 85°F max).
    Expect: after enough consistent readings, the fan turns on and the
    heater does not."""
    conn, registry, sim, cell_id = fresh_system()
    sim.state["temp_air"] = 95.0
    run_cycles(registry, sim, n=4)

    checks = [
        ("fan turned on", get_last_actuator_action(conn, "greenhouse_exhaust_fan") == "on"),
        ("heater did not turn on", get_last_actuator_action(conn, "greenhouse_heater") != "on"),
    ]
    return checks


def scenario_climate_control_fan_trigger_humidity():
    """Humidity climbs well above the 75%RH max while temp stays fully
    in-range (78°F). Expect: the fan turns on from humidity alone —
    venting isn't gated on temperature also being out of range."""
    conn, registry, sim, cell_id = fresh_system()
    sim.state["humidity"] = 90.0
    run_cycles(registry, sim, n=4)

    checks = [
        ("fan turned on from high humidity with in-range temp",
         get_last_actuator_action(conn, "greenhouse_exhaust_fan") == "on"),
        ("heater stayed off (temp was never out of range)",
         get_last_actuator_action(conn, "greenhouse_heater") != "on"),
    ]
    return checks


def scenario_climate_control_no_repeat_commands():
    """Temp/humidity stay steady and in-range across many cycles.
    Expect: each actuator gets exactly one command (the initial
    decision) — no repeat commands for an unchanged steady state,
    matching AquaponicsCell's own no-op-when-nothing-changed discipline."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=4)
    heater_count_after_first = get_actuator_event_count(conn, "greenhouse_heater")
    fan_count_after_first = get_actuator_event_count(conn, "greenhouse_exhaust_fan")
    run_cycles(registry, sim, n=4)
    heater_count_after_more = get_actuator_event_count(conn, "greenhouse_heater")
    fan_count_after_more = get_actuator_event_count(conn, "greenhouse_exhaust_fan")

    checks = [
        ("heater got exactly one command, not one per cycle",
         heater_count_after_first == 1 and heater_count_after_more == 1),
        ("fan got exactly one command, not one per cycle",
         fan_count_after_first == 1 and fan_count_after_more == 1),
    ]
    return checks


def scenario_climate_control_safety_fallback():
    """Both temp_air and humidity sensors go silent and age past
    staleness. Expect: once retries genuinely exhaust, the heater is
    forced off (stuck-on fire/scorch risk) and the fan is forced on
    (safe if stuck on) — never left in whatever state they happened to
    be in before data was lost."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=2)
    sim.inject_sensor_dropout("temp_air")
    sim.inject_sensor_dropout("humidity")
    sim.force_stale_backdate("temp_air", minutes_ago=15)
    sim.force_stale_backdate("humidity", minutes_ago=15)
    run_cycles(registry, sim, n=MiaHomesteadModule.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT + 1)

    checks = [
        ("heater forced off during total sensor loss",
         get_last_actuator_action(conn, "greenhouse_heater") == "off"),
        ("fan forced on during total sensor loss",
         get_last_actuator_action(conn, "greenhouse_exhaust_fan") == "on"),
    ]
    return checks


def scenario_do_no_sensor_silent():
    """The fresh demo cell has no DO sensor configured (real cell_1 in
    the live DB doesn't have one either, as of 2026-08-31 — DO is
    optional hardware). Expect: zero DO-related alerts, ever, across
    several cycles — not noise for hardware that was never installed."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=4)

    alerts = get_alerts(conn)
    do_alerts = [m for _, _, m in alerts if "dissolved oxygen" in m.lower() or "do reading" in m.lower()]
    checks = [
        ("zero DO-related alerts with no DO sensor configured", len(do_alerts) == 0),
    ]
    return checks


def scenario_do_critical_alert():
    """A DO sensor is added mid-run and fed a critically low reading
    (2.0 mg/L, well below the 3.0 mg/L critical threshold). Expect: a
    real critical alert citing the actual reading, once enough
    consistent readings land."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=2)

    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'do', 'mg/L', 1)",
        (cell_id,),
    )
    do_sensor_id = cur.lastrowid
    conn.execute(
        "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) VALUES (?, 2.0, 0, 0)",
        (do_sensor_id,),
    )
    conn.commit()
    run_cycles(registry, sim, n=3)

    critical_alerts = get_alerts(conn, "critical")
    checks = [
        ("critically low DO (2.0 mg/L) raises a real critical alert citing the actual reading",
         any("dissolved oxygen" in m.lower() and "2.0" in m for _, _, m in critical_alerts)),
    ]
    return checks


def scenario_do_healthy_no_alert():
    """A DO sensor reads a healthy value (7.0 mg/L, well above the 5.0
    mg/L warning threshold). Expect: no DO-related alert at all."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=2)

    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'do', 'mg/L', 1)",
        (cell_id,),
    )
    do_sensor_id = cur.lastrowid
    conn.execute(
        "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) VALUES (?, 7.0, 0, 0)",
        (do_sensor_id,),
    )
    conn.commit()
    run_cycles(registry, sim, n=3)

    alerts = get_alerts(conn)
    do_alerts = [m for _, _, m in alerts if "dissolved oxygen" in m.lower()]
    checks = [
        ("a healthy DO reading (7.0 mg/L) raises no DO alert", len(do_alerts) == 0),
    ]
    return checks


def scenario_irrigation_scheduled_pulse():
    """A configured schedule, never pulsed before. Expect: the check
    pulses the real irrigation_valve actuator and logs it, citing the
    real bed/interval."""
    conn, registry, sim, cell_id = fresh_system()
    from core.irrigation import IrrigationScheduler
    sched = IrrigationScheduler(conn, [
        {"grow_bed_name": "Bed A1", "cell_id": cell_id, "actuator_name": "irrigation_valve",
         "interval_minutes": 120, "pulse_seconds": 300},
    ])
    watered = sched.check_scheduled_irrigation()

    last_action = get_last_actuator_action(conn, "irrigation_valve")
    checks = [
        ("a due, never-pulsed bed gets watered this check",
         len(watered) == 1 and watered[0]["grow_bed_name"] == "Bed A1"),
        ("the real irrigation_valve actuator was pulsed", last_action == "pulse"),
    ]
    return checks


def scenario_irrigation_not_yet_due():
    """The same schedule, checked again immediately after a pulse.
    Expect: no second pulse — interval hasn't elapsed yet."""
    conn, registry, sim, cell_id = fresh_system()
    from core.irrigation import IrrigationScheduler
    sched = IrrigationScheduler(conn, [
        {"grow_bed_name": "Bed A1", "cell_id": cell_id, "actuator_name": "irrigation_valve",
         "interval_minutes": 120, "pulse_seconds": 300},
    ])
    sched.check_scheduled_irrigation()
    pulse_count_after_first = get_actuator_event_count(conn, "irrigation_valve")
    watered_again = sched.check_scheduled_irrigation()
    pulse_count_after_second_check = get_actuator_event_count(conn, "irrigation_valve")

    checks = [
        ("a recently-pulsed bed is skipped on an immediate re-check", len(watered_again) == 0),
        ("no second actuator_events row was written",
         pulse_count_after_first == 1 and pulse_count_after_second_check == 1),
    ]
    return checks


def scenario_irrigation_missing_actuator():
    """A schedule references an actuator name that doesn't exist on the
    cell. Expect: skipped gracefully, no crash, no pulse logged."""
    conn, registry, sim, cell_id = fresh_system()
    from core.irrigation import IrrigationScheduler
    sched = IrrigationScheduler(conn, [
        {"grow_bed_name": "Bed Nonexistent", "cell_id": cell_id, "actuator_name": "not_a_real_actuator",
         "interval_minutes": 120, "pulse_seconds": 300},
    ])
    watered = sched.check_scheduled_irrigation()  # must not raise

    checks = [
        ("a misconfigured schedule is skipped, not crashed on", watered == []),
    ]
    return checks


def scenario_circulation_stall_detected():
    """A flow sensor is added, the pump is commanded on, and flow reads
    near-zero for 2 consecutive readings. Expect: a real critical alert
    naming the actual cell."""
    conn, registry, sim, cell_id = fresh_system()
    conn.execute(
        "INSERT INTO actuator_events (actuator_id, action, triggered_by) "
        "SELECT id, 'on', 'auto_control' FROM actuators WHERE cell_id = ? AND type = 'circulation_pump'",
        (cell_id,),
    )
    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'flow', 'GPH', 1)",
        (cell_id,),
    )
    flow_sensor_id = cur.lastrowid
    for _ in range(2):
        conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) VALUES (?, 0.0, 0, 0)",
            (flow_sensor_id,),
        )
    conn.commit()

    from core.circulation_monitor import CirculationMonitor
    findings = CirculationMonitor(conn).check_circulation()

    critical_alerts = get_alerts(conn, "critical")
    checks = [
        ("a stalled, commanded-on pump is detected", len(findings) == 1 and findings[0]["cell_id"] == cell_id),
        ("a real critical alert is raised", any("circulation pump commanded on" in m.lower() for _, _, m in critical_alerts)),
    ]
    return checks


def scenario_circulation_off_no_alert():
    """The pump is deliberately commanded off (e.g. load-shed) and flow
    reads zero. Expect: no alert — zero flow is EXPECTED when the pump
    isn't running."""
    conn, registry, sim, cell_id = fresh_system()
    conn.execute(
        "INSERT INTO actuator_events (actuator_id, action, triggered_by) "
        "SELECT id, 'off', 'safety_fallback' FROM actuators WHERE cell_id = ? AND type = 'circulation_pump'",
        (cell_id,),
    )
    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'flow', 'GPH', 1)",
        (cell_id,),
    )
    flow_sensor_id = cur.lastrowid
    for _ in range(2):
        conn.execute(
            "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) VALUES (?, 0.0, 0, 0)",
            (flow_sensor_id,),
        )
    conn.commit()

    from core.circulation_monitor import CirculationMonitor
    findings = CirculationMonitor(conn).check_circulation()

    checks = [
        ("a deliberately-off pump with zero flow raises nothing", findings == []),
    ]
    return checks


def scenario_circulation_no_sensor_silent():
    """No flow sensor configured on the fresh demo cell. Expect: the
    check finds nothing at all — optional hardware, not noise."""
    conn, registry, sim, cell_id = fresh_system()

    from core.circulation_monitor import CirculationMonitor
    findings = CirculationMonitor(conn).check_circulation()

    checks = [
        ("no flow sensor configured -> zero findings", findings == []),
    ]
    return checks


def scenario_climate_control_light_no_sensor_silent():
    """No light sensor configured on the fresh demo cell. Expect: zero
    light-related alerts or commands, ever — optional hardware, not noise."""
    conn, registry, sim, cell_id = fresh_system()
    run_cycles(registry, sim, n=4)

    alerts = get_alerts(conn)
    light_alerts = [m for _, _, m in alerts if "light reading" in m.lower()]
    checks = [
        ("no light sensor configured -> zero light alerts", len(light_alerts) == 0),
        ("no light sensor configured -> zero light commands",
         get_actuator_event_count(conn, "greenhouse_grow_light") == 0),
    ]
    return checks


def scenario_climate_control_light_trigger():
    """A light sensor is added and fed a consistently low reading (2000
    lux vs. a 5000 lux target). Expect: the grow light turns on after
    enough consistent readings."""
    conn, registry, sim, cell_id = fresh_system()
    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'light', 'lux', 1)",
        (cell_id,),
    )
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'grow_light', 'greenhouse_grow_light', 'off')",
        (cell_id,),
    )
    light_sensor_id = cur.lastrowid
    conn.commit()
    sim.sensors["light"] = light_sensor_id
    sim.state["light"] = 2000.0
    run_cycles(registry, sim, n=4)

    checks = [
        ("grow light turned on from low, consistent light readings",
         get_last_actuator_action(conn, "greenhouse_grow_light") == "on"),
    ]
    return checks


def scenario_climate_control_co2_injection():
    """A CO2 sensor + injector are added and fed a consistently low
    reading (500 ppm vs. an 800 ppm target). Expect: exactly one
    injection pulse, not one per cycle (cooldown enforced)."""
    conn, registry, sim, cell_id = fresh_system()
    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'co2', 'ppm', 1)",
        (cell_id,),
    )
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'co2_valve', 'greenhouse_co2_injector', 'off')",
        (cell_id,),
    )
    co2_sensor_id = cur.lastrowid
    conn.commit()
    sim.sensors["co2"] = co2_sensor_id
    sim.state["co2"] = 500.0
    run_cycles(registry, sim, n=6)

    checks = [
        ("exactly one CO2 injection pulse across 6 cycles (cooldown enforced)",
         get_actuator_event_count(conn, "greenhouse_co2_injector") == 1),
        ("the pulse used the real actuator, action='pulse'",
         get_last_actuator_action(conn, "greenhouse_co2_injector") == "pulse"),
    ]
    return checks


def scenario_climate_control_co2_danger_no_inject():
    """A CO2 sensor reads at the OSHA danger threshold (5000 ppm).
    Expect: a real critical alert, and zero injection pulses — never
    inject into already-unsafe air."""
    conn, registry, sim, cell_id = fresh_system()
    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'co2', 'ppm', 1)",
        (cell_id,),
    )
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'co2_valve', 'greenhouse_co2_injector', 'off')",
        (cell_id,),
    )
    co2_sensor_id = cur.lastrowid
    conn.commit()
    sim.sensors["co2"] = co2_sensor_id
    sim.state["co2"] = 5200.0
    run_cycles(registry, sim, n=3)

    critical_alerts = get_alerts(conn, "critical")
    checks = [
        ("a dangerously high CO2 reading raises a real critical alert",
         any("co2 dangerously high" in m.lower() for _, _, m in critical_alerts)),
        ("zero injection pulses while CO2 is at a dangerous level",
         get_actuator_event_count(conn, "greenhouse_co2_injector") == 0),
    ]
    return checks


def scenario_temp_water_species_range():
    """The demo cell's real stocked tank (species='tilapia', seeded by
    setup_demo_cell) fed a water temp reading outside Tilapia's real
    documented range (species_registry's baseline: 75-85F). Expect: a
    real warning citing the actual reading and range."""
    conn, registry, sim, cell_id = fresh_system()
    from core.species_registry import SpeciesRegistry
    SpeciesRegistry(conn)  # seeds baseline species (incl. Tilapia) into species_profiles

    sim.state["temp_water"] = 60.0  # well below Tilapia's 75-85F range
    run_cycles(registry, sim, n=4)

    warning_alerts = get_alerts(conn, "warning")
    checks = [
        ("water temp outside the real stocked species' range raises a real warning",
         any("water temp" in m.lower() and "the stocked species'" in m.lower()
             for _, _, m in warning_alerts)),
    ]
    return checks


def scenario_temp_water_no_species_silent():
    """No tank stocked on this cell (species cleared). Expect: zero
    species-range alerts, ever — never guesses a target."""
    conn, registry, sim, cell_id = fresh_system()
    from core.species_registry import SpeciesRegistry
    SpeciesRegistry(conn)
    conn.execute("UPDATE tanks SET species = NULL WHERE cell_id = ?", (cell_id,))
    conn.commit()

    sim.state["temp_water"] = 60.0
    run_cycles(registry, sim, n=4)

    alerts = get_alerts(conn)
    range_alerts = [m for _, _, m in alerts if "the stocked species'" in m.lower()]
    checks = [
        ("an unstocked tank raises zero species-range alerts", len(range_alerts) == 0),
    ]
    return checks


def scenario_temp_water_in_range_no_alert():
    """A healthy water temp reading, well within Tilapia's real
    documented range. Expect: no species-range alert."""
    conn, registry, sim, cell_id = fresh_system()
    from core.species_registry import SpeciesRegistry
    SpeciesRegistry(conn)

    sim.state["temp_water"] = 80.0  # within Tilapia's 75-85F range
    run_cycles(registry, sim, n=4)

    alerts = get_alerts(conn)
    range_alerts = [m for _, _, m in alerts if "the stocked species'" in m.lower()]
    checks = [
        ("a healthy, in-range water temp raises no species-range alert", len(range_alerts) == 0),
    ]
    return checks


def scenario_temp_water_heater_engages():
    """A real water_heater actuator is configured on the demo cell
    (real stocked tilapia), fed a low reading. Expect: the heater turns
    on, with NO alert (it's being handled), and settles with no repeat
    commands once it's been on for a while."""
    conn, registry, sim, cell_id = fresh_system()
    from core.species_registry import SpeciesRegistry
    SpeciesRegistry(conn)
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'water_heater', 'tank_water_heater', 'off')",
        (cell_id,),
    )
    conn.commit()

    sim.state["temp_water"] = 60.0  # well below Tilapia's 75-85F range
    run_cycles(registry, sim, n=4)
    heater_count_after_first = get_actuator_event_count(conn, "tank_water_heater")
    run_cycles(registry, sim, n=3)
    heater_count_after_more = get_actuator_event_count(conn, "tank_water_heater")

    warning_alerts = get_alerts(conn, "warning")
    range_alerts = [m for _, _, m in warning_alerts if "below the stocked species" in m.lower()]
    checks = [
        ("a configured water heater turns on for a low reading",
         get_last_actuator_action(conn, "tank_water_heater") == "on"),
        ("no low-temp alert while a heater is actively handling it", len(range_alerts) == 0),
        ("no repeat commands once corrected",
         heater_count_after_first == 1 and heater_count_after_more == 1),
    ]
    return checks


def scenario_temp_water_no_cooling_above_max():
    """A configured water heater, fed a HIGH reading (above species
    max). Expect: a real 'no chiller' warning, and the heater forced
    off — never on, since heating further would make it worse."""
    conn, registry, sim, cell_id = fresh_system()
    from core.species_registry import SpeciesRegistry
    SpeciesRegistry(conn)
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'water_heater', 'tank_water_heater', 'off')",
        (cell_id,),
    )
    conn.commit()

    sim.state["temp_water"] = 95.0  # well above Tilapia's 75-85F range
    run_cycles(registry, sim, n=4)

    warning_alerts = get_alerts(conn, "warning")
    checks = [
        ("a high reading raises a real 'no chiller' warning",
         any("no chiller is built" in m.lower() for _, _, m in warning_alerts)),
        ("the heater is never turned on for a high reading",
         get_last_actuator_action(conn, "tank_water_heater") != "on"),
    ]
    return checks


def scenario_temp_water_heater_safety_fallback():
    """A configured water heater, all sensors go stale. Expect: the
    heater is forced off via the safety fallback path."""
    conn, registry, sim, cell_id = fresh_system()
    conn.execute(
        "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, 'water_heater', 'tank_water_heater', 'off')",
        (cell_id,),
    )
    conn.commit()
    run_cycles(registry, sim, n=2)
    for t in ("ph", "ec", "temp_water"):
        sim.inject_sensor_dropout(t)
        sim.force_stale_backdate(t, minutes_ago=15)
    run_cycles(registry, sim, n=MiaHomesteadModule.MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT + 1)

    checks = [
        ("water heater forced off during total sensor loss",
         get_last_actuator_action(conn, "tank_water_heater") == "off"),
    ]
    return checks


def scenario_power_monitor_sensor_id_no_collision():
    """A power_telemetry row's id is deliberately made to collide with
    a real sensors.id (the demo cell's real temp_water sensor). Expect:
    PowerMonitor.read_sensors() never reports that colliding id as its
    own sensor_id — real bug, live 2026-09-01: this exact collision
    made a stale-power alert incorrectly name the pilot cell's real
    temp_water sensor instead of the power telemetry it was actually
    about."""
    conn, registry, sim, cell_id = fresh_system()
    from modules.power_monitor import SYNTHETIC_SENSOR_ID
    real_temp_water_sensor_id = conn.execute(
        "SELECT id FROM sensors WHERE cell_id = ? AND type = 'temp_water'", (cell_id,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO power_telemetry (id, source, watts, battery_soc_percent) VALUES (?, 'battery', -80.0, 70.0)",
        (real_temp_water_sensor_id,),
    )
    conn.commit()

    pm = registry.modules["greenhouse_power"]
    readings = pm.read_sensors()

    checks = [
        ("a colliding power_telemetry id never becomes the reported sensor_id",
         len(readings) == 1 and readings[0].sensor_id != real_temp_water_sensor_id),
        ("read_sensors() uses the fixed synthetic sentinel, not a real table id",
         readings[0].sensor_id == SYNTHETIC_SENSOR_ID),
    ]
    return checks


def scenario_bed_planting_plan_and_convert():
    """A real planting is planned (staged, not yet real), then
    converted to active. Expect: the planned row has planted_date NULL
    and status 'planned'; after conversion, status 'active' with a
    real planted_date set."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    from core.bed_planting import BedPlantingManager
    from core.species_registry import SpeciesRegistry
    species = SpeciesRegistry(conn)
    bp = BedPlantingManager(conn, species)

    lettuce = species.find_by_name("Lettuce")
    planting_id = bp.plan("Bed A1", cell_id, lettuce["id"], target_plant_date="2026-09-15")

    conn.row_factory = sqlite3.Row
    planned_row = dict(conn.execute("SELECT * FROM bed_plantings WHERE id = ?", (planting_id,)).fetchone())

    bp.convert_to_active(planting_id, quantity_planted=12)
    active_row = dict(conn.execute("SELECT * FROM bed_plantings WHERE id = ?", (planting_id,)).fetchone())

    checks = [
        ("a planned planting has status 'planned' and no planted_date yet",
         planned_row["status"] == "planned" and planned_row["planted_date"] is None
         and planned_row["target_plant_date"] == "2026-09-15"),
        ("converting sets status 'active' with a real planted_date and the corrected quantity",
         active_row["status"] == "active" and active_row["planted_date"] is not None
         and active_row["quantity_planted"] == 12),
    ]
    return checks


def scenario_bed_planting_convert_guards_real_history():
    """Converting a planting that's already active (not 'planned')
    must refuse — it would otherwise silently rewrite real history."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    from core.bed_planting import BedPlantingManager
    from core.species_registry import SpeciesRegistry
    species = SpeciesRegistry(conn)
    bp = BedPlantingManager(conn, species)

    lettuce = species.find_by_name("Lettuce")
    planting_id = bp.plant("Bed A1", cell_id, lettuce["id"])  # already active, not planned

    raised = False
    try:
        bp.convert_to_active(planting_id)
    except ValueError:
        raised = True

    checks = [
        ("convert_to_active refuses an already-active planting", raised),
    ]
    return checks


def scenario_bed_planting_get_bed_layout():
    """A real bed with one active and one planned planting. Expect:
    get_bed_layout() groups both under the same real bed, by name."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    from core.bed_planting import BedPlantingManager
    from core.species_registry import SpeciesRegistry
    species = SpeciesRegistry(conn)
    bp = BedPlantingManager(conn, species)

    lettuce = species.find_by_name("Lettuce")
    basil = species.find_by_name("Basil")
    bp.plant("Bed A1", cell_id, lettuce["id"])
    bp.plan("Bed A1", cell_id, basil["id"], target_plant_date="2026-10-01")

    layout = bp.get_bed_layout(cell_id)
    bed_a1 = next((b for b in layout if b["name"] == "Bed A1"), None)

    checks = [
        ("Bed A1 is present in the layout", bed_a1 is not None),
        ("Bed A1 groups both the active and the planned planting",
         bed_a1 is not None and len(bed_a1["plantings"]) == 2
         and {p["status"] for p in bed_a1["plantings"]} == {"active", "planned"}),
    ]
    return checks


def scenario_simulator_level_realtime_safe():
    """Real bug, live 2026-09-01: drivers/simulator.py's Simulator class
    (used by --run for real continuous background operation, distinct
    from PhysicsSimulator which scenarios use) generated 'level' noise
    large enough that, at its real 5-second tick interval, consecutive
    readings implied a rate-of-change past core/leak_detector.py's real
    threshold — producing constant false 'possible leak' alerts with
    nothing actually wrong. Scenarios never caught this: they call
    Simulator.tick() directly with no real elapsed wall-clock time
    between ticks, so the rate-of-change math never actually engaged.
    This is an INVARIANT check instead of fixed data, so it can't
    silently regress if either constant changes later — confirms the
    worst-case possible consecutive-reading swing, interpreted at
    Simulator's real default interval, always stays safely under the
    real leak threshold."""
    from drivers.simulator import SIM_SENSOR_DEFS
    from core.leak_detector import LEAK_RATE_THRESHOLD_INCHES_PER_MINUTE

    _, _, _, drift, noise = next(d for d in SIM_SENSOR_DEFS if d[0] == "level")
    worst_case_swing_inches = 2 * (drift + noise)  # opposite-sign max draws on consecutive reads
    default_interval_seconds = 5.0
    implied_rate_per_minute = worst_case_swing_inches / (default_interval_seconds / 60)

    checks = [
        ("level sensor noise/drift can never imply a rate past the real leak threshold, "
         "even in the worst-case consecutive draw",
         implied_rate_per_minute < LEAK_RATE_THRESHOLD_INCHES_PER_MINUTE),
    ]
    return checks


def scenario_simulator_demo_cell_stays_base_sensors():
    """Real regression this session's SIM_SENSOR_DEFS additions (do/
    flow/light/co2) risked: setup_demo_cell() used to iterate the WHOLE
    list to create sensor rows, so adding entries for optional hardware
    would have silently auto-created those sensors on the demo cell too
    — invalidating every 'no sensor configured -> stays silent'
    scenario across DO/circulation/climate-control. Confirms the demo
    cell still only gets the original 6 base sensor types, regardless
    of how many types SIM_SENSOR_DEFS knows how to drift."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)

    types = {row[0] for row in conn.execute(
        "SELECT type FROM sensors WHERE cell_id = ?", (cell_id,)
    ).fetchall()}

    checks = [
        ("the demo cell only gets the 6 base sensor types, not every SIM_SENSOR_DEFS entry",
         types == {"ph", "ec", "temp_water", "temp_air", "humidity", "level"}),
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
    "fish_health_tracking": scenario_fish_health_tracking,
    "leak_detection": scenario_leak_detection,
    "pest_disease_tracking": scenario_pest_disease_tracking,
    "weather_awareness": scenario_weather_awareness,
    "cost_profitability": scenario_cost_profitability,
    "climate_control_heater_trigger": scenario_climate_control_heater_trigger,
    "climate_control_fan_trigger_temp": scenario_climate_control_fan_trigger_temp,
    "climate_control_fan_trigger_humidity": scenario_climate_control_fan_trigger_humidity,
    "climate_control_no_repeat_commands": scenario_climate_control_no_repeat_commands,
    "climate_control_safety_fallback": scenario_climate_control_safety_fallback,
    "do_no_sensor_silent": scenario_do_no_sensor_silent,
    "do_critical_alert": scenario_do_critical_alert,
    "do_healthy_no_alert": scenario_do_healthy_no_alert,
    "irrigation_scheduled_pulse": scenario_irrigation_scheduled_pulse,
    "irrigation_not_yet_due": scenario_irrigation_not_yet_due,
    "irrigation_missing_actuator": scenario_irrigation_missing_actuator,
    "circulation_stall_detected": scenario_circulation_stall_detected,
    "circulation_off_no_alert": scenario_circulation_off_no_alert,
    "circulation_no_sensor_silent": scenario_circulation_no_sensor_silent,
    "climate_control_light_no_sensor_silent": scenario_climate_control_light_no_sensor_silent,
    "climate_control_light_trigger": scenario_climate_control_light_trigger,
    "climate_control_co2_injection": scenario_climate_control_co2_injection,
    "climate_control_co2_danger_no_inject": scenario_climate_control_co2_danger_no_inject,
    "temp_water_species_range": scenario_temp_water_species_range,
    "temp_water_no_species_silent": scenario_temp_water_no_species_silent,
    "temp_water_in_range_no_alert": scenario_temp_water_in_range_no_alert,
    "temp_water_heater_engages": scenario_temp_water_heater_engages,
    "temp_water_no_cooling_above_max": scenario_temp_water_no_cooling_above_max,
    "temp_water_heater_safety_fallback": scenario_temp_water_heater_safety_fallback,
    "power_monitor_sensor_id_no_collision": scenario_power_monitor_sensor_id_no_collision,
    "bed_planting_plan_and_convert": scenario_bed_planting_plan_and_convert,
    "bed_planting_convert_guards_real_history": scenario_bed_planting_convert_guards_real_history,
    "bed_planting_get_bed_layout": scenario_bed_planting_get_bed_layout,
    "simulator_level_realtime_safe": scenario_simulator_level_realtime_safe,
    "simulator_demo_cell_stays_base_sensors": scenario_simulator_demo_cell_stays_base_sensors,
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
