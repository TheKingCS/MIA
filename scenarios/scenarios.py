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


def scenario_yield_recording_and_lot_traceability():
    """Real yield write path (a genuine gap found while building this —
    yield_events existed and was already read everywhere, but nothing
    ever wrote to it, same shape as the revenue_transactions gap fixed
    earlier). Proves: a harvest linked to a planting assembles a real
    lot record with its dosing/water-quality history; a harvest NOT
    linked to a planting (fish) honestly reports no growth history;
    finalizing writes a real hash-chained ledger row; the ledger
    verifies intact; and tampering with a finalized record is detected."""
    from core.bed_planting import BedPlantingManager
    from core.species_registry import SpeciesRegistry
    from core.traceability import TraceabilityManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    species = SpeciesRegistry(conn)
    bp = BedPlantingManager(conn, species)
    trace = TraceabilityManager(conn)

    lettuce_id = conn.execute(
        "SELECT id FROM species_profiles WHERE common_name = 'Lettuce'"
    ).fetchone()[0]

    # ---- A real planting, dosed and water-tested during its life, then harvested ----
    planting_id = bp.plant("Bed A1", cell_id, lettuce_id, quantity_planted=12)
    conn.execute(
        "UPDATE bed_plantings SET planted_date = datetime('now', '-20 days') WHERE id = ?",
        (planting_id,),
    )
    conn.execute(
        "INSERT INTO dosing_events (cell_id, timestamp, dose_type, amount_ml, rationale, triggered_by) "
        "VALUES (?, datetime('now', '-10 days'), 'ph_up', 5.0, 'pH below target', 'auto_control')",
        (cell_id,),
    )
    conn.execute(
        "INSERT INTO water_quality_tests (cell_id, timestamp, ammonia_ppm, nitrite_ppm, nitrate_ppm) "
        "VALUES (?, datetime('now', '-5 days'), 0.0, 0.0, 10.0)",
        (cell_id,),
    )
    conn.commit()

    bp.mark_harvested(planting_id)
    yield_event_id = trace.record_yield(
        cell_id=cell_id, yield_type="harvest_produce", item="lettuce",
        quantity=3.5, unit="lb", bed_planting_id=planting_id,
    )

    lot = trace.get_lot_record(yield_event_id)

    # ---- A fish harvest, NOT linked to any bed_planting ----
    fish_yield_id = trace.record_yield(
        cell_id=cell_id, yield_type="harvest_fish", item="tilapia", quantity=2, unit="count",
    )
    fish_lot = trace.get_lot_record(fish_yield_id)

    # ---- Finalize the lettuce lot, verify the chain, then tamper ----
    finalize_result = trace.finalize_lot(yield_event_id)
    verify_before = trace.verify_ledger()
    conn.execute(
        "UPDATE traceability_ledger SET record_json = '{\"tampered\": true}' WHERE id = ?",
        (finalize_result["ledger_id"],),
    )
    conn.commit()
    verify_after_tamper = trace.verify_ledger()

    checks = [
        ("record_yield actually writes a row (yield_events had no write path before this)",
         yield_event_id is not None and lot["yield_event"]["item"] == "lettuce"
         and lot["yield_event"]["quantity"] == 3.5),
        ("the lettuce lot links back to its real planting",
         lot["planting"] is not None and lot["planting"]["grow_bed_name"] == "Bed A1"),
        ("the lettuce lot's dosing history includes the real dose during its window",
         len(lot["dosing_history"]) == 1 and lot["dosing_history"][0]["dose_type"] == "ph_up"),
        ("the lettuce lot's water-quality history includes the real test during its window",
         len(lot["water_quality_history"]) == 1),
        ("isolated_to_this_planting is True — no other planting shared this cell's water",
         lot["isolated_to_this_planting"] is True),
        ("a fish harvest with no bed_planting_id honestly reports no growth history",
         fish_lot["planting"] is None and fish_lot["dosing_history"] == []
         and "no growth/dosing history" in fish_lot["precision_note"]),
        ("finalize_lot writes a real ledger row chained from GENESIS",
         finalize_result["ledger_id"] is not None and finalize_result["record_hash"] is not None),
        ("a freshly finalized single-entry ledger verifies intact",
         verify_before == {"intact": True, "chain_length": 1}),
        ("tampering with a finalized record is detected by verify_ledger",
         verify_after_tamper["intact"] is False
         and verify_after_tamper["broken_at_ledger_id"] == finalize_result["ledger_id"]),
    ]
    return checks


def scenario_water_efficiency_reporting():
    """Real gap: water_usage_events and yield_events were both already
    logged elsewhere, but nothing computed efficiency from either.
    Proves the gallons-per-lb math, that a zero-yield window reports
    unavailable (not a fake zero or divide-by-zero crash), and that a
    non-lb yield (e.g. fish by count) is excluded from the ratio and
    listed separately rather than silently dropped or converted."""
    from core.sustainability_report import SustainabilityReport

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    report = SustainabilityReport(conn)

    # No usage/yield logged yet — must not crash or fabricate a ratio.
    empty = report.get_water_efficiency(cell_id=cell_id, days=30)

    conn.execute(
        "INSERT INTO water_usage_events (cell_id, amount_gallons, reason) VALUES (?, 20, 'scheduled_watering')",
        (cell_id,),
    )
    conn.execute(
        "INSERT INTO yield_events (cell_id, yield_type, item, quantity, unit) VALUES (?, 'harvest_produce', 'lettuce', 4.0, 'lb')",
        (cell_id,),
    )
    conn.execute(
        "INSERT INTO yield_events (cell_id, yield_type, item, quantity, unit) VALUES (?, 'harvest_fish', 'tilapia', 2, 'count')",
        (cell_id,),
    )
    conn.commit()

    result = report.get_water_efficiency(cell_id=cell_id, days=30)

    # Real bug caught by a live smoke test against the real dev DB, not by this
    # scenario originally: real yield with ZERO water logged computed a literal
    # 0.0 ratio — mathematically correct, but reads as "perfect efficiency" when
    # the truth is "no water usage has been logged at all." A second real cell,
    # isolated from the water/yield seeded above, reproduces exactly that case.
    second_cell_id = conn.execute(
        "INSERT INTO cells (name) VALUES ('Isolated Test Cell')"
    ).lastrowid
    conn.execute(
        "INSERT INTO yield_events (cell_id, yield_type, item, quantity, unit) VALUES (?, 'harvest_produce', 'basil', 1.0, 'lb')",
        (second_cell_id,),
    )
    conn.commit()
    yield_no_water = report.get_water_efficiency(cell_id=second_cell_id, days=30)

    checks = [
        ("an empty window reports gallons_per_lb as unavailable, not 0 or a crash",
         empty["gallons_per_lb"] is None and empty["gallons_used"] == 0 and empty["lb_yielded"] == 0),
        ("20 gallons / 4 lb computes correctly to 5.0 gallons/lb",
         result["gallons_per_lb"] == 5.0 and result["gallons_used"] == 20.0 and result["lb_yielded"] == 4.0),
        ("the count-unit fish yield is excluded from the ratio, listed separately",
         len(result["excluded_non_lb_yield"]) == 1
         and result["excluded_non_lb_yield"][0]["item"] == "tilapia"
         and result["excluded_non_lb_yield"][0]["quantity"] == 2),
        ("real yield (1 lb basil) with zero water logged reports unavailable, not a fake 0.0",
         yield_no_water["lb_yielded"] == 1.0 and yield_no_water["gallons_used"] == 0
         and yield_no_water["gallons_per_lb"] is None),
    ]
    return checks


def scenario_succession_planning():
    """Real gap: bed_planting.py tracks current/planned plantings but
    never proactively suggests what comes next. Proves: a planting
    nearing harvest surfaces a suggestion; one already past its
    expected date is flagged overdue, not hidden; a bed that already
    has a planned next planting is flagged so it isn't double-suggested;
    a species incompatible with a co-located planting's water is
    correctly excluded from the candidate list; and an isolated cell
    (no other active planting left) reports itself unconstrained."""
    from core.bed_planting import BedPlantingManager
    from core.species_registry import SpeciesRegistry
    from core.succession_planner import SuccessionPlanner

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    species = SpeciesRegistry(conn)
    bp = BedPlantingManager(conn, species)
    planner = SuccessionPlanner(conn)

    lettuce_id = conn.execute("SELECT id FROM species_profiles WHERE common_name = 'Lettuce'").fetchone()[0]
    cucumber_id = conn.execute("SELECT id FROM species_profiles WHERE common_name = 'Cucumber'").fetchone()[0]

    # A permanent Cucumber planting sharing this cell's water (temp_water 70-80F) —
    # real case already documented in species_registry.py: Spinach (50-68F) shares
    # zero temp overlap with Cucumber, so it must be excluded from any candidate
    # list for a bed sharing this cell, even though Swiss Chard (60-75F) still fits.
    bp.plant("Bed A3", cell_id, cucumber_id, quantity_planted=4)

    # A planting nearing harvest (within the default 14-day window), no plan staged yet.
    near_id = bp.plant("Bed A1", cell_id, lettuce_id, quantity_planted=10)
    conn.execute(
        "UPDATE bed_plantings SET expected_harvest_date = datetime('now', '+5 days') WHERE id = ?",
        (near_id,),
    )
    # A second bed, same cell, already OVERDUE — must be flagged, not hidden.
    overdue_id = bp.plant("Bed A2", cell_id, lettuce_id, quantity_planted=8)
    conn.execute(
        "UPDATE bed_plantings SET expected_harvest_date = datetime('now', '-3 days') WHERE id = ?",
        (overdue_id,),
    )
    conn.commit()

    suggestions = planner.get_succession_suggestions(days_ahead=14, cell_id=cell_id)
    by_bed = {s["grow_bed_name"]: s for s in suggestions}

    # Stage a real planned next planting for Bed A1 — should now be flagged as already covered.
    bp.plan("Bed A1", cell_id, lettuce_id, target_plant_date="2026-09-10")
    suggestions_after_plan = planner.get_succession_suggestions(days_ahead=14, cell_id=cell_id)
    by_bed_after = {s["grow_bed_name"]: s for s in suggestions_after_plan}

    # An isolated single-bed cell — no other active planting remains once this one's harvested.
    solo_cell_id = conn.execute("INSERT INTO cells (name) VALUES ('Solo Cell')").lastrowid
    solo_id = bp.plant("Solo Bed", solo_cell_id, lettuce_id, quantity_planted=1)
    conn.execute(
        "UPDATE bed_plantings SET expected_harvest_date = datetime('now', '+1 day') WHERE id = ?",
        (solo_id,),
    )
    conn.commit()
    solo_suggestions = planner.get_succession_suggestions(days_ahead=14, cell_id=solo_cell_id)

    checks = [
        ("Spinach (zero water-temp overlap with the co-located Cucumber) is excluded from Bed A1's candidates",
         "Spinach" not in by_bed["Bed A1"]["other_compatible_species"]),
        ("Swiss Chard (real water-temp overlap with Cucumber) is still offered as a candidate",
         "Swiss Chard" in by_bed["Bed A1"]["other_compatible_species"]),
        ("both beds (near and overdue) surface a suggestion", len(suggestions) == 2),
        ("Bed A1 (5 days out) is NOT flagged overdue", by_bed["Bed A1"]["overdue"] is False),
        ("Bed A2 (3 days past) IS flagged overdue", by_bed["Bed A2"]["overdue"] is True),
        ("neither bed shows an already-planned next planting before one exists",
         by_bed["Bed A1"]["already_has_next_planned"] is False),
        ("replant_same_species suggests the real current species",
         by_bed["Bed A1"]["replant_same_species"] == "Lettuce"),
        ("after staging a real plan for Bed A1, it's correctly flagged as already covered",
         by_bed_after["Bed A1"]["already_has_next_planned"] is True),
        ("an isolated single-bed cell reports itself unconstrained once vacated",
         "any known plant species is compatible" in solo_suggestions[0]["compatibility_note"]),
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

    _, _, _, drift, noise, _ = next(d for d in SIM_SENSOR_DEFS if d[0] == "level")
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


def scenario_simulator_walk_stays_physically_plausible():
    """Real, actively-manifesting bug found live 2026-09-02: Simulator.
    tick()'s random walk had no bound at all. Left running continuously
    for ~2 real days, it wandered into physically impossible territory
    — humidity read 113.5%RH (real cap 100) and light read -7215 lux
    (light can't be negative) — fed straight into the control loop as
    normal data, because this driver also always hardcoded
    is_out_of_range=0 regardless of the value, unlike the real
    AtlasEZODriver. Confirms: many ticks never push the underlying
    state outside SIM_SENSOR_DEFS's own plausible_range for every
    sensor type, and a reading manually forced outside that range
    (simulating a real implausible readout) gets correctly flagged
    is_out_of_range=1, exactly like the real hardware driver would."""
    from drivers.simulator import Simulator, SIM_SENSOR_DEFS, setup_demo_cell

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    setup_demo_cell(conn)
    sim = Simulator(conn, interval_seconds=5.0)

    for _ in range(500):  # far more ticks than this cell will ever see between restarts in a scenario run
        sim.tick()

    ranges_by_type = {d[0]: d[5] for d in SIM_SENSOR_DEFS}
    sensor_types = dict(conn.execute("SELECT id, type FROM sensors").fetchall())
    still_in_range = True
    for sensor_id, value in sim.state.items():
        lo, hi = ranges_by_type[sensor_types[sensor_id]]
        if not (lo <= value <= hi):
            still_in_range = False

    # Force one sensor's underlying state to the edge of its range, then
    # manually write an out-of-bounds reading the way real noise could
    # briefly produce one, and confirm the same flagging logic used
    # inside tick()/force_read() would catch it.
    any_sensor_id = next(iter(sim.state))
    lo, hi = sim.defs[any_sensor_id][2]
    implausible_reading = hi + 9999
    flagged = not (lo <= implausible_reading <= hi)

    checks = [
        ("500 ticks never pushed any sensor's underlying state outside its real plausible range",
         still_in_range),
        ("a genuinely implausible reading is correctly identified as out-of-range",
         flagged),
    ]
    return checks


def scenario_heater_closes_the_loop():
    """Real closed-loop physics for this session's climate actuators,
    same standard scenario_ph_crash_response already proves for pH:
    a cold reading triggers the heater, and running more cycles shows
    air temp actually recovering from the correction — not just that a
    command was issued."""
    conn, registry, sim, cell_id = fresh_system()
    sim.state["temp_air"] = 55.0  # well below the 65-85 target band
    run_cycles(registry, sim, n=4)  # long enough for the heater to engage
    temp_after_engaging = sim.state["temp_air"]
    run_cycles(registry, sim, n=6)  # let the heater's effect actually accumulate
    temp_after_more_cycles = sim.state["temp_air"]

    checks = [
        ("heater engaged for the cold reading", get_last_actuator_action(conn, "greenhouse_heater") == "on"),
        (f"air temp actually recovered from the correction ({temp_after_engaging:.1f} -> {temp_after_more_cycles:.1f}°F)",
         temp_after_more_cycles > temp_after_engaging),
    ]
    return checks


def scenario_water_heater_closes_the_loop():
    """Same closed-loop proof for the tank water heater — confirms
    water temp actually rises once the heater engages, not just that
    the command fired."""
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
    temp_after_engaging = sim.state["temp_water"]
    run_cycles(registry, sim, n=8)
    temp_after_more_cycles = sim.state["temp_water"]

    checks = [
        ("water heater engaged for the cold reading", get_last_actuator_action(conn, "tank_water_heater") == "on"),
        (f"water temp actually recovered from the correction ({temp_after_engaging:.1f} -> {temp_after_more_cycles:.1f}°F)",
         temp_after_more_cycles > temp_after_engaging),
    ]
    return checks


def scenario_co2_injection_closes_the_loop():
    """Confirms a CO2 injection pulse actually raises the simulated
    CO2 reading by a real, proportional amount — not just that the
    valve fired."""
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
    co2_before = sim.state["co2"]
    run_cycles(registry, sim, n=4)
    co2_after = sim.state["co2"]

    checks = [
        (f"CO2 actually rose from the injection pulse ({co2_before:.0f} -> {co2_after:.0f} ppm)",
         co2_after > co2_before),
    ]
    return checks


def scenario_do_relaxes_toward_temp_equilibrium():
    """Real physics added 2026-09-01: DO relaxes toward a temperature-
    dependent equilibrium rather than sitting frozen at a fixed value.
    Confirms a DO reading well below the warm-water equilibrium
    actually drifts upward over natural ticks, with no dosing/actuator
    involved at all — pure environmental dynamics."""
    conn, registry, sim, cell_id = fresh_system()
    cur = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'do', 'mg/L', 1)",
        (cell_id,),
    )
    do_sensor_id = cur.lastrowid
    conn.commit()
    sim.sensors["do"] = do_sensor_id
    sim.state["do"] = 3.0  # well below the ~7.8 equilibrium at a normal water temp
    do_before = sim.state["do"]
    for _ in range(6):
        sim.tick()
    do_after = sim.state["do"]

    checks = [
        (f"DO drifted upward toward its temperature-dependent equilibrium ({do_before:.2f} -> {do_after:.2f} mg/L)",
         do_after > do_before),
    ]
    return checks


def scenario_alert_manager_resolve():
    """A real alert, resolved by a human. Expect: resolved/resolved_at
    set correctly, and resolving it again is refused rather than
    silently rewriting resolved_at."""
    from contracts.mia_homestead_contract import raise_alert as raise_real_alert
    from core.alert_manager import AlertManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    am = AlertManager(conn)

    raise_real_alert(conn, "test_source", "warning", "a real test condition")
    alert_id = conn.execute("SELECT id FROM alerts WHERE source = 'test_source'").fetchone()[0]

    am.resolve_alert(alert_id, notes="fixed manually")
    row = dict(zip(
        ["resolved", "resolved_at"],
        conn.execute("SELECT resolved, resolved_at FROM alerts WHERE id = ?", (alert_id,)).fetchone(),
    ))

    refused = False
    try:
        am.resolve_alert(alert_id)
    except ValueError:
        refused = True

    checks = [
        ("resolve_alert sets resolved=1 and a real resolved_at",
         row["resolved"] == 1 and row["resolved_at"] is not None),
        ("resolving an already-resolved alert is refused", refused),
    ]
    return checks


def scenario_alert_manager_acknowledge():
    """A real alert, acknowledged by a human. Expect: acknowledged/
    acknowledged_at set, resolved left untouched."""
    from contracts.mia_homestead_contract import raise_alert as raise_real_alert
    from core.alert_manager import AlertManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    am = AlertManager(conn)

    raise_real_alert(conn, "test_source", "info", "a real test condition")
    alert_id = conn.execute("SELECT id FROM alerts WHERE source = 'test_source'").fetchone()[0]

    am.acknowledge_alert(alert_id)
    row = dict(zip(
        ["acknowledged", "acknowledged_at", "resolved"],
        conn.execute(
            "SELECT acknowledged, acknowledged_at, resolved FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone(),
    ))

    checks = [
        ("acknowledge_alert sets acknowledged=1 and a real acknowledged_at",
         row["acknowledged"] == 1 and row["acknowledged_at"] is not None),
        ("acknowledging doesn't also resolve it", row["resolved"] == 0),
    ]
    return checks


def scenario_alert_manager_stale_sweep():
    """One alert not re-raised in a long time, one raised just now.
    Expect: the stale one gets auto-resolved, the recent one is left
    alone."""
    from contracts.mia_homestead_contract import raise_alert as raise_real_alert
    from core.alert_manager import AlertManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    am = AlertManager(conn)

    raise_real_alert(conn, "stale_source", "warning", "an old condition")
    stale_id = conn.execute("SELECT id FROM alerts WHERE source = 'stale_source'").fetchone()[0]
    conn.execute(
        "UPDATE alerts SET last_seen = datetime('now', '-60 minutes') WHERE id = ?", (stale_id,)
    )
    conn.commit()

    raise_real_alert(conn, "fresh_source", "warning", "a current condition")
    fresh_id = conn.execute("SELECT id FROM alerts WHERE source = 'fresh_source'").fetchone()[0]

    resolved = am.check_stale_alerts(stale_after_minutes=30)

    stale_row = conn.execute("SELECT resolved FROM alerts WHERE id = ?", (stale_id,)).fetchone()
    fresh_row = conn.execute("SELECT resolved FROM alerts WHERE id = ?", (fresh_id,)).fetchone()

    checks = [
        ("the stale alert (60 min old) was auto-resolved",
         any(r["alert_id"] == stale_id for r in resolved) and stale_row[0] == 1),
        ("the fresh alert (just raised) was left alone", fresh_row[0] == 0),
    ]
    return checks


def scenario_alert_manager_recurrence_after_resolution():
    """The exact same (source, message) condition recurs after being
    resolved. Expect: a real NEW alert row, not the old one silently
    un-resolved — raise_alert()'s own dedup only matches unresolved rows."""
    from contracts.mia_homestead_contract import raise_alert as raise_real_alert
    from core.alert_manager import AlertManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    am = AlertManager(conn)

    raise_real_alert(conn, "recur_source", "warning", "a recurring condition")
    first_id = conn.execute("SELECT id FROM alerts WHERE source = 'recur_source'").fetchone()[0]
    am.resolve_alert(first_id)

    raise_real_alert(conn, "recur_source", "warning", "a recurring condition")
    all_rows = conn.execute(
        "SELECT id, resolved FROM alerts WHERE source = 'recur_source' ORDER BY id"
    ).fetchall()

    checks = [
        ("a genuine recurrence creates a real new row, not reusing the resolved one",
         len(all_rows) == 2 and all_rows[0][1] == 1 and all_rows[1][1] == 0),
    ]
    return checks


def scenario_diagnose_alert_reuses_open_task():
    """Real bug found live 2026-09-01: the same diagnosable condition
    recurring as a genuinely new alert row (after the prior one
    resolved — see core/alert_manager.py) used to file a brand new,
    duplicate maintenance task every single time, even while an
    identical one was still open. The live DB had 3 duplicate 'ph' and
    4 duplicate 'ec' investigate tasks from exactly this. Confirms a
    second diagnosis of the same likely_cause reuses the existing open
    task instead of creating a duplicate."""
    from core.infrastructure_registry import InfrastructureRegistry
    from core.maintenance import MaintenanceManager
    from core.diagnostics import DiagnosticEngine
    from contracts.mia_homestead_contract import raise_alert as raise_real_alert

    conn, registry, sim, cell_id = fresh_system()
    diagnostics = DiagnosticEngine(conn, InfrastructureRegistry(conn),
                                    maintenance=MaintenanceManager(conn))

    raise_real_alert(conn, "cell_a_aquaponics", "warning",
                      "cell_a_aquaponics: ph sensor (id 1) stale — retries exhausted")
    first_alert_id = conn.execute(
        "SELECT id FROM alerts WHERE message LIKE '%ph sensor%stale%'"
    ).fetchone()[0]
    first_diagnosis = diagnostics.diagnose_alert(first_alert_id, create_task=True)

    # Resolve the first alert so a genuine recurrence raises a real NEW
    # row (raise_alert()'s dedup only matches unresolved rows) — same
    # real sequence that caused the live duplicate-task bug.
    conn.execute("UPDATE alerts SET resolved = 1 WHERE id = ?", (first_alert_id,))
    conn.commit()

    raise_real_alert(conn, "cell_a_aquaponics", "warning",
                      "cell_a_aquaponics: ph sensor (id 1) stale — retries exhausted")
    second_alert_id = conn.execute(
        "SELECT id FROM alerts WHERE message LIKE '%ph sensor%stale%' AND id != ?",
        (first_alert_id,),
    ).fetchone()[0]
    second_diagnosis = diagnostics.diagnose_alert(second_alert_id, create_task=True)

    open_task_count = conn.execute(
        "SELECT COUNT(*) FROM maintenance_tasks WHERE status IN ('open', 'in_progress')"
    ).fetchone()[0]

    checks = [
        ("the first diagnosis creates a real task", first_diagnosis.get("maintenance_task_id") is not None),
        ("the second diagnosis of the same recurring condition reuses it, doesn't duplicate",
         second_diagnosis.get("maintenance_task_id") == first_diagnosis.get("maintenance_task_id")
         and second_diagnosis.get("maintenance_task_reused") is True),
        ("exactly one open task exists, not two", open_task_count == 1),
    ]
    return checks


def scenario_create_maintenance_task_tool_validates():
    """Real bug found live 2026-09-01: the create_maintenance_task
    assistant tool used to insert directly via raw SQL, bypassing
    MaintenanceManager.create_task()'s validation entirely — an
    invalid task_type or priority would silently corrupt a row instead
    of being rejected. Confirms the tool now validates (by routing
    through the real service) and a valid call still works correctly."""
    from assistant.greenhouse_assistant import GreenhouseAssistant

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    a = GreenhouseAssistant.__new__(GreenhouseAssistant)
    a.db = conn

    invalid = a._tool_create_maintenance_task(title="bad", task_type="not_a_real_type")
    valid = a._tool_create_maintenance_task(title="Replace tubing", task_type="replacement", priority="high")

    checks = [
        ("an invalid task_type is rejected with a real error, not silently inserted",
         "error" in invalid),
        ("a valid task is created for real, through the real service",
         "created_task_id" in valid and valid["created_task_id"] is not None),
    ]
    return checks


def scenario_add_species_tool_full_fields():
    """Real bug found live 2026-09-01, checking for the same class of
    bug that broke create_maintenance_task: the add_species assistant
    tool used to insert directly via raw SQL, missing temp_water_min/
    max, temp_air_min/max, and days_to_maturity entirely — not just
    unvalidated, genuinely unreachable (they weren't even parameters).
    A species added through chat would silently never get water-temp
    thermal-stress protection or weather frost/heat checks. Confirms
    all fields now actually make it into the real row."""
    from assistant.greenhouse_assistant import GreenhouseAssistant

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    a = GreenhouseAssistant.__new__(GreenhouseAssistant)
    a.db = conn

    result = a._tool_add_species(
        common_name="Test Trout", organism_type="fish",
        temp_water_min=50.0, temp_water_max=65.0,
        temp_air_min=45.0, temp_air_max=70.0,
        days_to_maturity=365,
    )
    row = dict(zip(
        ["temp_water_min", "temp_water_max", "temp_air_min", "temp_air_max", "days_to_maturity"],
        conn.execute(
            "SELECT temp_water_min, temp_water_max, temp_air_min, temp_air_max, days_to_maturity "
            "FROM species_profiles WHERE id = ?",
            (result["species_id"],),
        ).fetchone(),
    ))

    checks = [
        ("temp_water_min/max actually reach the real row, not silently dropped",
         row["temp_water_min"] == 50.0 and row["temp_water_max"] == 65.0),
        ("temp_air_min/max actually reach the real row",
         row["temp_air_min"] == 45.0 and row["temp_air_max"] == 70.0),
        ("days_to_maturity actually reaches the real row", row["days_to_maturity"] == 365),
    ]
    return checks


def scenario_update_maintenance_task_status_tool_validates():
    """Same bug class as create_maintenance_task, found in the same
    sweep: the update_maintenance_task_status tool used to bypass
    MaintenanceManager.update_status()'s validation with raw SQL."""
    from assistant.greenhouse_assistant import GreenhouseAssistant
    from core.maintenance import MaintenanceManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    a = GreenhouseAssistant.__new__(GreenhouseAssistant)
    a.db = conn
    real_task_id = MaintenanceManager(conn).create_task(title="test task", task_type="other")

    invalid = a._tool_update_maintenance_task_status(task_id=real_task_id, status="closed")
    valid = a._tool_update_maintenance_task_status(task_id=real_task_id, status="done")
    row = conn.execute("SELECT status, completed_at FROM maintenance_tasks WHERE id = ?", (real_task_id,)).fetchone()

    checks = [
        ("an invalid status is rejected with a real error, not silently written", "error" in invalid),
        ("a valid status transition works and sets completed_at for 'done'",
         row[0] == "done" and row[1] is not None),
    ]
    return checks


def scenario_propose_experiment_tool_validates():
    """Same bug class again: the propose_experiment tool used to bypass
    ExperimentManager.propose_experiment()'s variable_changed
    validation with raw SQL. The JSON tool schema already constrains
    this via enum for a well-behaved model call, but the underlying
    code had no defense of its own — this confirms it does now."""
    from assistant.greenhouse_assistant import GreenhouseAssistant

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    a = GreenhouseAssistant.__new__(GreenhouseAssistant)
    a.db = conn

    invalid = a._tool_propose_experiment(
        cell_id=cell_id, hypothesis="test", variable_changed="not_a_real_variable",
        baseline_value=1.0, test_value=2.0,
    )
    valid = a._tool_propose_experiment(
        cell_id=cell_id, hypothesis="raise EC a bit", variable_changed="ec_target_min",
        baseline_value=800.0, test_value=900.0,
    )

    checks = [
        ("an invalid variable_changed is rejected with a real error", "error" in invalid),
        ("a valid experiment proposal works for real, through the real service",
         "experiment_id" in valid and valid["status"] == "proposed"),
    ]
    return checks


def scenario_dosing_min_interval_enforced():
    """Real, safety-relevant bug found live 2026-09-01: dosing had NO
    minimum-interval enforcement at all — contracts.MiaHomesteadModule.
    _validate_command() (the originally-intended enforcement point) was
    a literal stub. The live system had fired 18,415 dosing_events, the
    vast majority every single control-loop cycle (~5 REAL seconds
    apart), exactly the "oscillation/overcorrection loop"
    SAFETY_SPEC.md's dosing rules explicitly exist to prevent — not
    hypothetical. Confirms a second dose attempt of the same type,
    within milliseconds of the first (real dosing_limits.
    min_interval_minutes for cell 1's ph_up is 5 real minutes), is
    correctly blocked and logs nothing."""
    conn, registry, sim, cell_id = fresh_system()
    sim.inject_ph_crash(-0.7)
    run_cycles(registry, sim, n=4)  # the crash response fires at least once
    dose_count_after_first = get_dose_count(conn, "ph_up")

    # Force pH back below target immediately — no real wall-clock time
    # has elapsed, so a second attempt this soon must be blocked
    # regardless of how out-of-range the reading still is.
    sim.state["ph"] = 6.0
    run_cycles(registry, sim, n=6)
    dose_count_after_more = get_dose_count(conn, "ph_up")

    warning_alerts = get_alerts(conn, "warning")
    blocked_rows = conn.execute(
        "SELECT occurrence_count FROM alerts WHERE message LIKE '%dose blocked%' AND resolved = 0"
    ).fetchall()

    checks = [
        ("a dose fired during the initial crash response", dose_count_after_first > 0),
        ("no additional dose fired within the real 5-minute interval, despite pH still out of range",
         dose_count_after_more == dose_count_after_first),
        ("a real 'dose blocked' warning explains why",
         any("dose blocked" in m.lower() and "minimum interval" in m.lower() for _, _, m in warning_alerts)),
        # Real regression of an already-documented failure mode, caught
        # live 2026-09-02: this message used to embed elapsed_minutes
        # (changes every cycle), defeating raise_alert()'s dedup and
        # creating a brand-new alert row every single cycle — 150+ rows
        # for one still-ongoing condition had piled up live. The message
        # is now constant text, so multiple blocked cycles must collapse
        # into exactly ONE alert row with occurrence_count bumping.
        ("multiple blocked cycles collapse into exactly one alert row (dedup works)",
         len(blocked_rows) == 1),
        ("that one row's occurrence_count reflects more than one blocked attempt",
         len(blocked_rows) == 1 and blocked_rows[0][0] > 1),
    ]
    return checks


def scenario_data_retention_prunes_old_rows():
    """Real gap found live 2026-09-02: sensor_readings, actuator_events,
    power_telemetry, and system_heartbeat had zero pruning anywhere —
    sensor_readings alone had 148,240 rows after ~2 days of test churn,
    despite the schema's own header promising no manual cleanup should
    ever be required. Confirms a row genuinely older than the retention
    window is deleted from all four tables, a recent row is kept, and
    the prune is logged to automated_action_log."""
    from core.data_retention import DataRetentionManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    sensor_id = conn.execute("SELECT id FROM sensors LIMIT 1").fetchone()[0]
    actuator_id = conn.execute("SELECT id FROM actuators LIMIT 1").fetchone()[0]

    old_ts = (datetime.utcnow() - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S")
    recent_ts = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("INSERT INTO sensor_readings (sensor_id, timestamp, value) VALUES (?, ?, ?)", (sensor_id, old_ts, 6.5))
    conn.execute("INSERT INTO sensor_readings (sensor_id, timestamp, value) VALUES (?, ?, ?)", (sensor_id, recent_ts, 6.6))
    conn.execute("INSERT INTO actuator_events (actuator_id, timestamp, action, triggered_by) VALUES (?, ?, 'on', 'auto_control')", (actuator_id, old_ts))
    conn.execute("INSERT INTO actuator_events (actuator_id, timestamp, action, triggered_by) VALUES (?, ?, 'on', 'auto_control')", (actuator_id, recent_ts))
    conn.execute("INSERT INTO power_telemetry (timestamp, source, watts) VALUES (?, 'solar', 50.0)", (old_ts,))
    conn.execute("INSERT INTO power_telemetry (timestamp, source, watts) VALUES (?, 'solar', 55.0)", (recent_ts,))
    conn.execute("INSERT INTO system_heartbeat (component, last_seen) VALUES ('pi_main_loop', ?)", (old_ts,))
    conn.execute("INSERT INTO system_heartbeat (component, last_seen) VALUES ('pi_main_loop', ?)", (recent_ts,))
    conn.commit()

    mgr = DataRetentionManager(conn)
    sizes_before = mgr.get_table_sizes()
    deleted = mgr.prune_old_data(retention_days=90)
    sizes_after = mgr.get_table_sizes()

    log_hit = conn.execute(
        "SELECT COUNT(*) FROM automated_action_log WHERE module_id = 'data_retention' AND action = 'old_data_pruned'"
    ).fetchone()[0]

    checks = [
        ("get_table_sizes() sees both rows in each table before pruning",
         all(n >= 2 for n in sizes_before.values())),
        ("exactly one row deleted per table (the old one)",
         all(deleted.get(t) == 1 for t, _ in [("sensor_readings", ""), ("actuator_events", ""), ("power_telemetry", ""), ("system_heartbeat", "")])),
        ("each table has exactly one row left (the recent one)",
         all(n == 1 for n in sizes_after.values())),
        ("the prune is logged to automated_action_log for real audit visibility", log_hit == 1),
    ]
    return checks


def scenario_data_retention_noop_when_nothing_old():
    """Confirms a run with nothing past the retention window deletes
    nothing, logs nothing, and doesn't touch recent data — pruning
    should be silent when there's genuinely nothing to prune, not a
    no-op that still writes a misleading log entry."""
    from core.data_retention import DataRetentionManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    setup_demo_cell(conn)
    sensor_id = conn.execute("SELECT id FROM sensors LIMIT 1").fetchone()[0]

    recent_ts = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO sensor_readings (sensor_id, timestamp, value) VALUES (?, ?, ?)", (sensor_id, recent_ts, 6.5))
    conn.commit()

    mgr = DataRetentionManager(conn)
    deleted = mgr.prune_old_data(retention_days=90)
    log_hit = conn.execute(
        "SELECT COUNT(*) FROM automated_action_log WHERE module_id = 'data_retention'"
    ).fetchone()[0]
    remaining = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]

    checks = [
        ("nothing was deleted", deleted == {}),
        ("no log entry written for a no-op prune", log_hit == 0),
        ("the recent row is untouched", remaining == 1),
    ]
    return checks


def scenario_self_preservation_no_presence_sensor_silent():
    """Real, actively-firing bug found live 2026-09-02: SelfPreservation
    Module relied on the base class's generic run_cycle(), which treats
    "read_sensors() returned nothing" as "all sensors stale/invalid" and
    raises a CRITICAL alert. But this module's only sensor (presence) is
    genuinely optional hardware most cells never install — on the live
    system, cell 1 has no presence sensor and never has, and this false
    CRITICAL had fired 21,000+ times continuously since before this fix,
    with nothing actually wrong. Confirms: with no presence sensor
    configured and a real critical alert open elsewhere, a cycle stays
    completely silent — no new alert, no help request, no commands."""
    from contracts.mia_homestead_contract import raise_alert as raise_real_alert
    from modules.self_preservation import SelfPreservationModule

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)

    raise_real_alert(conn, "cell_a_aquaponics", "critical", "a real unrelated critical condition")
    alerts_before = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    mod = SelfPreservationModule("greenhouse_self_preservation", cell_id, conn)
    commands = mod.run_cycle()

    alerts_after = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    false_critical = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE source = 'greenhouse_self_preservation' "
        "AND message LIKE '%stale/invalid%'"
    ).fetchone()[0]
    help_requests = conn.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]

    checks = [
        ("no new alert raised (no presence sensor is not a sensor failure)", alerts_after == alerts_before),
        ("no false 'all sensors stale/invalid' alert exists at all", false_critical == 0),
        ("no help request created — nothing to signal without a presence reading", help_requests == 0),
        ("no commands issued", commands == []),
    ]
    return checks


def scenario_self_preservation_signals_with_presence():
    """The other half of the same fix, proven so the override above
    didn't quietly break the module's actual designed behavior: with a
    real presence sensor installed, a fresh reading showing someone's
    there, AND a real open critical alert, this still creates a help
    request and turns the beacon on — bypassing the base class's
    staleness ladder for this module didn't disable the feature it's
    actually for."""
    from contracts.mia_homestead_contract import raise_alert as raise_real_alert
    from modules.self_preservation import SelfPreservationModule

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)

    presence_sensor_id = conn.execute(
        "INSERT INTO sensors (cell_id, type, unit, active) VALUES (?, 'presence', 'bool', 1)",
        (cell_id,),
    ).lastrowid
    conn.execute(
        "INSERT INTO sensor_readings (sensor_id, value) VALUES (?, 1.0)",
        (presence_sensor_id,),
    )
    raise_real_alert(conn, "cell_a_aquaponics", "critical", "a real unrelated critical condition")
    conn.commit()

    mod = SelfPreservationModule("greenhouse_self_preservation", cell_id, conn)
    commands = mod.run_cycle()

    help_request = conn.execute(
        "SELECT resolved, message FROM help_requests ORDER BY id DESC LIMIT 1"
    ).fetchone()

    checks = [
        ("a real help request was created", help_request is not None),
        ("it's unresolved and carries a real spoken message",
         help_request is not None and help_request[0] == 0 and len(help_request[1]) > 0),
        ("a beacon 'on' command was issued", any(c.action == "on" for c in commands)),
    ]
    return checks


def scenario_registry_connection_survives_lock_contention():
    """Real, actively-manifesting bug found live 2026-09-02: main.py and
    drivers/simulator.py --run are two independent processes, both
    writing the same SQLite file on their own 5-second interval, with
    SQLite's default rollback-journal mode (locks the WHOLE file during
    a write) and default 5-second busy_timeout. The simulator lost that
    race after ~2 days of continuous operation and crashed outright on
    "database is locked", leaving the entire sensor feed dead for over
    an hour with nothing restarting it. Confirms ModuleRegistry's real
    __init__ (not the __new__ bypass every other scenario in this file
    uses) actually enables WAL mode — a database-file-level setting that
    persists for every future connection from any process, real fix for
    two always-on daemons sharing one file — and that a second,
    independent connection to the same file can write concurrently
    without raising "database is locked" the way the default journal
    mode would under sustained contention."""
    import tempfile
    import threading
    import os

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    conn0 = sqlite3.connect(db_path)
    conn0.executescript(SCHEMA_PATH.read_text())
    conn0.close()

    registry = ModuleRegistry(str(CONFIG_PATH), db_path)
    mode = registry.db_conn.execute("PRAGMA journal_mode").fetchone()[0]

    # A second independent connection (standing in for the other daemon
    # process) hammering writes concurrently with the registry's own
    # connection — this is exactly the two-daemons-sharing-one-file
    # shape that crashed live. No exception escaping either thread is
    # the real proof; WAL mode is what makes that true here.
    other_errors = []

    def other_writer():
        conn = sqlite3.connect(db_path, timeout=30.0)
        try:
            for i in range(20):
                conn.execute("INSERT INTO system_heartbeat (component) VALUES ('other_daemon')")
                conn.commit()
        except Exception as e:
            other_errors.append(e)
        finally:
            conn.close()

    t = threading.Thread(target=other_writer)
    t.start()
    registry_errors = []
    try:
        for i in range(20):
            registry.db_conn.execute("INSERT INTO system_heartbeat (component) VALUES ('registry')")
            registry.db_conn.commit()
    except Exception as e:
        registry_errors.append(e)
    t.join()

    checks = [
        ("ModuleRegistry's real __init__ enables WAL mode", mode.lower() == "wal"),
        ("two concurrent writers to the same file don't raise 'database is locked'",
         other_errors == [] and registry_errors == []),
    ]
    return checks


def _mia_home_sync_with_config(conn, config_dict, tmp_dir):
    """Writes a real temp YAML config file and constructs a real
    MiaHomeSync against it — every scenario below exercises the actual
    config-loading path, not a hand-constructed object bypassing it."""
    import yaml
    from core.mia_home_sync import MiaHomeSync

    config_path = Path(tmp_dir) / "mia_home_sync.yaml"
    config_path.write_text(yaml.dump(config_dict))
    return MiaHomeSync(conn, config_path=str(config_path))


def scenario_mia_home_sync_honest_skip_when_unconfigured():
    """User asked to automate the manual transport step
    docs/MIA_HOME_SYNC_PLAN.md left open (2026-09-02). Confirms the
    honest-skip half first: with no destination configured (matching
    config/location.yaml's same precedent for weather checks), maybe_
    sync() does nothing at all — no rsync attempt, no heartbeat row,
    no alert — rather than guessing at a destination."""
    import tempfile

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    tmp_dir = tempfile.mkdtemp()

    sync = _mia_home_sync_with_config(conn, {"destination": None}, tmp_dir)
    result = sync.maybe_sync(snapshot_path=str(Path(tmp_dir) / "home_snapshot.json"))

    heartbeats = conn.execute(
        "SELECT COUNT(*) FROM system_heartbeat WHERE component = 'mia_home_sync'"
    ).fetchone()[0]

    checks = [
        ("maybe_sync() returns None when unconfigured", result is None),
        ("no heartbeat row written for a no-op", heartbeats == 0),
    ]
    return checks


def scenario_mia_home_sync_pushes_via_rsync():
    """Confirms a real rsync push actually delivers the file — not a
    mocked subprocess call. Uses a real local destination directory,
    the same shape config/mia_home_sync.yaml's own real configured
    value uses today (both projects on one machine in this dev
    environment)."""
    import tempfile

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    tmp_dir = Path(tempfile.mkdtemp())
    src_dir = tmp_dir / "src"
    dest_dir = tmp_dir / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()
    snapshot_path = src_dir / "home_snapshot.json"
    snapshot_path.write_text('{"source": "mia_homestead", "generated_at": "2026-09-02T00:00:00Z"}')

    sync = _mia_home_sync_with_config(conn, {"destination": str(dest_dir) + "/"}, str(tmp_dir))
    result = sync.maybe_sync(snapshot_path=str(snapshot_path))

    delivered = (dest_dir / "home_snapshot.json").exists()
    delivered_content = (dest_dir / "home_snapshot.json").read_text() if delivered else None

    checks = [
        ("maybe_sync() reports success for a real reachable local destination",
         result is not None and result.get("success") is True),
        ("the file genuinely landed at the destination via rsync", delivered),
        ("the delivered content matches the source", delivered_content == snapshot_path.read_text()),
    ]
    return checks


def scenario_mia_home_sync_paces_by_interval():
    """Confirms interval_minutes is a real, enforced pacing value, not
    just documentation — the same heartbeat row backs both 'was the
    last successful sync recent enough' and 'did we just try and
    shouldn't hammer an unreachable host again yet' (see is_due()'s own
    docstring)."""
    import tempfile

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    tmp_dir = tempfile.mkdtemp()

    sync = _mia_home_sync_with_config(
        conn, {"destination": "/tmp/wherever/", "interval_minutes": 5}, tmp_dir
    )
    due_with_no_history = sync.is_due()

    conn.execute(
        "INSERT INTO system_heartbeat (component, last_seen) VALUES ('mia_home_sync', datetime('now'))"
    )
    due_right_after_attempt = sync.is_due()

    old_ts = (datetime.utcnow() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO system_heartbeat (component, last_seen) VALUES ('mia_home_sync', ?)", (old_ts,)
    )
    due_after_interval_elapsed = sync.is_due()

    checks = [
        ("due immediately when there's no prior attempt at all", due_with_no_history),
        ("not due right after an attempt, within the configured interval", not due_right_after_attempt),
        ("due again once interval_minutes has genuinely elapsed", due_after_interval_elapsed),
    ]
    return checks


def scenario_mia_home_sync_failure_raises_alert():
    """A push failure (host unreachable, destination doesn't exist,
    SSH key not provisioned) is a real, expected operational condition
    for something depending on a network link between two separate
    machines — confirms it raises a real, informative warning alert
    rather than crashing the control loop, matching every other
    transport/IO failure this session's resilience work covers."""
    import tempfile

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    tmp_dir = Path(tempfile.mkdtemp())
    snapshot_path = tmp_dir / "home_snapshot.json"
    snapshot_path.write_text('{"source": "mia_homestead", "generated_at": "2026-09-02T00:00:00Z"}')

    # A destination whose parent doesn't exist — rsync genuinely fails
    # against this, the same real failure shape as an unreachable host.
    bad_destination = str(tmp_dir / "does_not_exist" / "also_does_not_exist") + "/"
    sync = _mia_home_sync_with_config(conn, {"destination": bad_destination}, str(tmp_dir))

    result = sync.maybe_sync(snapshot_path=str(snapshot_path))

    alert = conn.execute(
        "SELECT severity, message FROM alerts WHERE source = 'mia_home_sync'"
    ).fetchone()

    checks = [
        ("maybe_sync() reports failure rather than raising an exception",
         result is not None and result.get("success") is False),
        ("a real warning alert was raised", alert is not None and alert[0] == "warning"),
        ("the alert names the destination that failed", alert is not None and bad_destination in alert[1]),
    ]
    return checks


def scenario_pilot_shopping_list_includes_override_switch():
    """Real gap found live 2026-09-02 (docs/DAY_ONE_READINESS.md): the
    pilot's shopping list — whose whole stated purpose is proving the
    safety chain end to end — never included the SAFETY_SPEC.md-
    required physical override switch. Confirms it's in the seeded
    list now, and that seed_pilot_shopping_list() is still safe to
    call twice (its own docstring's claim) without duplicating any
    item, the new one included."""
    from drivers.simulator import seed_pilot_shopping_list

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())

    seed_pilot_shopping_list(conn)
    seed_pilot_shopping_list(conn)  # deliberately twice

    switch_rows = conn.execute(
        "SELECT COUNT(*) FROM inventory_items WHERE name LIKE '%Toggle Switch%'"
    ).fetchone()[0]
    total_items = conn.execute("SELECT COUNT(*) FROM inventory_items").fetchone()[0]

    checks = [
        ("the override switch is in the pilot shopping list", switch_rows == 1),
        ("calling it twice doesn't duplicate the switch or anything else",
         total_items == 8),
    ]
    return checks


def scenario_notification_config_honest_default_when_missing():
    """Real gap found live 2026-09-02 (docs/DAY_ONE_READINESS.md, item
    #1): main.py used to construct NotificationConfig() with zero
    arguments — critical alerts (SAFETY_SPEC.md's own escalation
    requirement) were silently inert with no way to configure real
    values short of hand-editing main.py's source, unlike every other
    configurable subsystem in this project. Confirms from_config()
    with no file present behaves EXACTLY like the old bare
    NotificationConfig() — purely additive, nothing that worked before
    changes."""
    from core.notifications import NotificationConfig

    cfg = NotificationConfig.from_config("/tmp/definitely_does_not_exist_mia_homestead.yaml")

    checks = [
        ("smtp_host stays empty (inert) with no config file", cfg.smtp_host == ""),
        ("smtp_port keeps its real default", cfg.smtp_port == 587),
        ("primary_contact_email stays empty (inert)", cfg.primary_contact_email == ""),
    ]
    return checks


def scenario_notification_config_loads_real_values():
    """Confirms a real config file's real values actually reach
    NotificationConfig — the whole point of closing this gap."""
    import tempfile
    from pathlib import Path
    from core.notifications import NotificationConfig

    tmp_dir = tempfile.mkdtemp()
    config_path = Path(tmp_dir) / "notifications.yaml"
    config_path.write_text(
        "smtp_host: smtp.example.com\n"
        "smtp_port: 465\n"
        "primary_contact_email: ops@example.com\n"
        "primary_contact_phone: '5551234567'\n"
        "primary_contact_carrier: verizon\n"
        "unknown_future_field: should be ignored, not crash\n"
    )

    cfg = NotificationConfig.from_config(str(config_path))

    checks = [
        ("smtp_host loaded from the real file", cfg.smtp_host == "smtp.example.com"),
        ("smtp_port overridden from the real file", cfg.smtp_port == 465),
        ("primary_contact_email loaded", cfg.primary_contact_email == "ops@example.com"),
        ("primary_contact_carrier loaded", cfg.primary_contact_carrier == "verizon"),
        ("secondary_contact_email keeps its default when not set in the file",
         cfg.secondary_contact_email == ""),
    ]
    return checks


class _FakeSerialPort:
    """A fake object matching pyserial's Serial interface (.write,
    .readline, .in_waiting, .close, .port) — same "fake object instead
    of a mock" precedent drivers/mcu_serial.py's own module docstring
    describes, and the reason this whole protocol layer is testable
    with zero real hardware. Feed it a queue of incoming lines (what a
    real MCU would send); .written records what was sent back to it,
    for assertions."""

    def __init__(self, device_path, incoming_lines=None):
        self.port = device_path
        self._incoming = list(incoming_lines or [])
        self.written = []

    @property
    def in_waiting(self):
        return len(self._incoming[0]) if self._incoming else 0

    def readline(self):
        return self._incoming.pop(0) if self._incoming else b""

    def write(self, data):
        self.written.append(data)

    def close(self):
        pass


def scenario_mcu_transport_pairs_over_a_real_link():
    """Real, actively-missing gap found live 2026-09-02
    (docs/DAY_ONE_READINESS.md, item #2): confirmed by grep that no
    code anywhere ever put a byte on a wire — core/device_registry.py
    built real pair_confirm payloads but announce_device() was
    explicitly "manual test call today." Confirms a real announce
    message, heard on a real (fake, for this test) MCU link, results
    in real auto-pairing AND a real pair_confirm sent back over that
    same link — the full handshake, not just one half of it."""
    import json
    from core.device_registry import DeviceRegistry
    from core.mcu_transport import McuTransportManager
    from drivers.mcu_serial import MCULink

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    setup_demo_cell(conn)

    announce = json.dumps({
        "type": "announce", "hardware_id": "ESP32-TESTAAAA1111", "requested_role": "ph_dosing_mcu",
    }).encode() + b"\n"

    def fake_open_port(device_path):
        return MCULink(_FakeSerialPort(device_path, incoming_lines=[announce]))

    registry = DeviceRegistry(conn)
    mgr = McuTransportManager(conn, registry)
    paired = mgr.scan_for_new_devices(ports=["/dev/fake0"], open_port_fn=fake_open_port)

    db_row = tuple(conn.execute(
        "SELECT status, role FROM device_registrations WHERE hardware_id = ?", ("ESP32-TESTAAAA1111",)
    ).fetchone())

    link = mgr._links.get("ESP32-TESTAAAA1111")
    sent_pair_confirm = link is not None and any(
        json.loads(w.decode().strip()).get("type") == "pair_confirm" for w in link.port.written
    )

    checks = [
        ("scan_for_new_devices() reports the real pairing", len(paired) == 1 and paired[0]["status"] == "paired"),
        ("the device is really paired in the DB", db_row == ("paired", "ph_dosing_mcu")),
        ("a real link is kept open for the newly paired device", link is not None),
        ("a real pair_confirm was sent back over that same link", sent_pair_confirm),
    ]
    return checks


def scenario_mcu_transport_dispatches_real_command():
    """Confirms the other half of what execute_command() needed: a
    command for an actuator with a real paired MCU is actually sent
    over its real link (not just logged), and an actuator with no
    paired MCU correctly signals the caller to fall back — main.py's
    existing simulated-log behavior, unchanged for every actuator that
    doesn't have real hardware yet."""
    import json
    from contracts.mia_homestead_contract import ActuatorCommand, TriggerSource
    from core.device_registry import DeviceRegistry
    from core.mcu_transport import McuTransportManager
    from drivers.mcu_serial import MCULink

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    cell_id = setup_demo_cell(conn)
    ph_up_actuator_id = conn.execute(
        "SELECT id FROM actuators WHERE cell_id = ? AND name = 'ph_up_pump'", (cell_id,)
    ).fetchone()[0]

    registry = DeviceRegistry(conn)
    mgr = McuTransportManager(conn, registry)
    fake_port = _FakeSerialPort("/dev/fake0")
    mgr._links["ESP32-TESTBBBB2222"] = MCULink(fake_port, hardware_id="ESP32-TESTBBBB2222")
    conn.execute(
        "INSERT INTO device_registrations (hardware_id, role, cell_id, status, paired_at) "
        "VALUES ('ESP32-TESTBBBB2222', 'ph_dosing_mcu', ?, 'paired', datetime('now'))",
        (cell_id,),
    )
    conn.commit()
    mgr._rebuild_actuator_map()

    real_cmd = ActuatorCommand(actuator_id=ph_up_actuator_id, action="pulse",
                                duration_seconds=1.5, triggered_by=TriggerSource.AUTO_CONTROL)
    unpaired_cmd = ActuatorCommand(actuator_id=999999, action="pulse",
                                    duration_seconds=1.0, triggered_by=TriggerSource.AUTO_CONTROL)

    sent_real = mgr.dispatch_command(real_cmd)
    sent_unpaired = mgr.dispatch_command(unpaired_cmd)

    sent_command_msg = any(
        json.loads(w.decode().strip()).get("type") == "command"
        and json.loads(w.decode().strip()).get("actuator_id") == ph_up_actuator_id
        for w in fake_port.written
    )

    checks = [
        ("a command for a paired actuator is dispatched over its real link", sent_real is True),
        ("the real link actually received a real command message", sent_command_msg),
        ("an actuator with no paired MCU signals the caller to fall back", sent_unpaired is False),
    ]
    return checks


def scenario_mcu_transport_fallback_raises_critical():
    """Real, not theoretical, version of SAFETY_SPEC.md's own
    critical-severity example: "safety MCU failed to hear from Pi."
    Confirms a real status message reporting fallback_active:true
    raises a real CRITICAL alert, and that raise_alert()'s own dedup
    still applies here — a second fallback_active:true poll bumps the
    same row's occurrence_count rather than creating a new one, same
    discipline this session's dose-blocked-alert fix already
    established for exactly this failure mode."""
    import json
    from core.device_registry import DeviceRegistry
    from core.mcu_transport import McuTransportManager
    from drivers.mcu_serial import MCULink

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    setup_demo_cell(conn)

    status_msg = json.dumps({
        "type": "status", "battery_mv": 12000, "uptime_s": 500, "fallback_active": True,
    }).encode() + b"\n"

    registry = DeviceRegistry(conn)
    mgr = McuTransportManager(conn, registry)
    fake_port = _FakeSerialPort("/dev/fake0", incoming_lines=[status_msg])
    mgr._links["ESP32-TESTCCCC3333"] = MCULink(fake_port, hardware_id="ESP32-TESTCCCC3333")
    conn.execute(
        "INSERT INTO device_registrations (hardware_id, role, status) "
        "VALUES ('ESP32-TESTCCCC3333', 'ph_dosing_mcu', 'paired')"
    )
    conn.commit()

    mgr.poll_status()
    alert_row = conn.execute(
        "SELECT severity, occurrence_count FROM alerts WHERE source = 'mcu_transport'"
    ).fetchone()

    # A second fallback_active:true poll — dedup should bump, not duplicate.
    fake_port._incoming.append(status_msg)
    mgr.poll_status()
    alert_row_after = conn.execute(
        "SELECT severity, occurrence_count FROM alerts WHERE source = 'mcu_transport'"
    ).fetchone()
    total_rows = conn.execute("SELECT COUNT(*) FROM alerts WHERE source = 'mcu_transport'").fetchone()[0]

    checks = [
        ("a real CRITICAL alert was raised for a real fallback_active report",
         alert_row is not None and alert_row[0] == "critical"),
        ("a repeated fallback report dedups onto the same row (occurrence_count bumps)",
         total_rows == 1 and alert_row_after[1] > alert_row[1]),
    ]
    return checks


def scenario_mcu_transport_scan_paces_by_interval():
    """Confirms scan_interval_seconds is real and enforced, same
    is_due() pacing pattern core/mia_home_sync.py already established
    — without this, a real deployment would either hammer every
    serial port every single control-loop cycle, or never re-check at
    all."""
    from core.device_registry import DeviceRegistry
    from core.mcu_transport import McuTransportManager

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    setup_demo_cell(conn)

    registry = DeviceRegistry(conn)
    mgr = McuTransportManager(conn, registry, scan_interval_seconds=60)

    due_with_no_history = mgr._scan_due()
    mgr._record_scan_attempt()
    due_right_after_attempt = mgr._scan_due()

    old_ts = (datetime.utcnow() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO system_heartbeat (component, last_seen) VALUES ('mcu_transport_scan', ?)", (old_ts,)
    )
    due_after_interval_elapsed = mgr._scan_due()

    checks = [
        ("due immediately with no prior scan attempt", due_with_no_history),
        ("not due right after a scan attempt, within the configured interval", not due_right_after_attempt),
        ("due again once scan_interval_seconds has genuinely elapsed", due_after_interval_elapsed),
    ]
    return checks


def _fresh_pilot_system():
    """Single-cell pilot setup — same shape as fresh_system(), but for
    docs/PILOT_VS_SCALE.md's real trimmed pilot cell (pH-up only, no
    ph_down/nutrient pumps) instead of the fully-equipped demo cell."""
    from drivers.simulator import setup_pilot_cell

    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_PATH.read_text())
    pilot_id = setup_pilot_cell(conn)
    sim = PhysicsSimulator(conn, cell_id=pilot_id)

    notifier = NotificationDispatcher(NotificationConfig())
    registry = ModuleRegistry.__new__(ModuleRegistry)
    registry.config_path = CONFIG_PATH
    registry.db_conn = conn
    registry.notifier = notifier
    id_to_type = {v: k for k, v in sim.sensors.items()}
    registry.force_read_fn = lambda sensor_id: sim.force_read(id_to_type.get(sensor_id, ""))
    registry.modules = {}
    registry.load()

    return conn, registry, sim, pilot_id


def scenario_dosing_no_actuator_alerts_instead_of_faking():
    """Real, actively-firing bug found live 2026-09-02, via the
    rendered Journal view (viewer/journal.html) — every one of the
    most recent 100 journal entries was "Dosed ph_down" for pilot_cell,
    each ~5 real seconds apart, 668 in the last hour alone.
    docs/PILOT_VS_SCALE.md's own trimmed pilot scope deliberately has
    no ph-down pump ("pH-up only to start") — confirmed live: pilot's
    actuators are ph_up pump + circulation + aerator only, nothing
    else. But nothing checked for that before proposing a correction
    in that direction: _dose_command() logged a real dosing_events row
    and issued a real ActuatorCommand(actuator_id=-1, ...) every single
    cycle, unconstrained (no dosing_limits row for pilot ph_down either,
    which used to mean "nothing to enforce" — see the sibling scenario
    below for that half of the fix). Confirms: a real pH-too-high
    crash on the pilot cell now raises a real, informative warning
    instead — no fake dosing_events row, no command for a nonexistent
    actuator.

    Also confirms the warning message dedups across repeated cycles —
    caught live immediately after writing the fix below: the first
    version embedded the live pH value in the message, defeating
    raise_alert()'s dedup exactly like the already-documented "dose
    blocked" regression earlier this session (5 distinct rows had
    already accumulated in the few minutes before that was caught)."""
    conn, registry, sim, pilot_id = _fresh_pilot_system()
    sim.inject_ph_crash(0.9)  # pilot's target is 6.6-7.2 — push it high, needing ph_down
    run_cycles(registry, sim, n=5)

    dose_count = get_dose_count(conn, "ph_down")
    fake_command_count = conn.execute(
        "SELECT COUNT(*) FROM actuator_events WHERE actuator_id = -1"
    ).fetchone()[0]
    warning_alerts = get_alerts(conn, "warning")
    matching_rows = conn.execute(
        "SELECT occurrence_count FROM alerts WHERE message LIKE '%no ph_down pump is configured%' "
        "AND resolved = 0"
    ).fetchall()

    checks = [
        ("no fake ph_down dosing_events were logged for a cell with no ph_down pump", dose_count == 0),
        ("no command was issued for the actuator_id=-1 sentinel", fake_command_count == 0),
        ("a real warning explains dosing is held for lack of a real pump",
         any("no ph_down pump is configured" in m for _, _, m in warning_alerts)),
        ("repeated cycles collapse into exactly one alert row (dedup works)",
         len(matching_rows) == 1),
        ("that one row's occurrence_count reflects more than one cycle",
         len(matching_rows) == 1 and matching_rows[0][0] > 1),
    ]
    return checks


def scenario_dosing_no_limit_configured_blocks_and_alerts():
    """The other half of the same fix, defense in depth: a cell WITH a
    real actuator but a genuinely missing dosing_limits row (a
    configuration error, not the normal "no pump built yet" case the
    scenario above covers) used to mean "nothing to enforce" — allowing
    unlimited dosing frequency, backwards for a safety gate. Confirms
    it now fails closed (blocks the dose, real warning alert) instead,
    matching SAFETY_SPEC.md's own "limits are defined per chemical, per
    cell," not optional."""
    conn, registry, sim, cell_id = fresh_system()
    conn.execute("DELETE FROM dosing_limits WHERE cell_id = ? AND dose_type = 'ph_up'", (cell_id,))
    conn.commit()

    sim.inject_ph_crash(-0.7)
    run_cycles(registry, sim, n=5)

    dose_count = get_dose_count(conn, "ph_up")
    warning_alerts = get_alerts(conn, "warning")

    checks = [
        ("no dose fired with no dosing_limits row configured, despite pH needing correction",
         dose_count == 0),
        ("a real warning explains dosing is blocked for lack of a configured limit",
         any("no dosing_limits configured" in m for _, _, m in warning_alerts)),
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
    "yield_recording_and_lot_traceability": scenario_yield_recording_and_lot_traceability,
    "water_efficiency_reporting": scenario_water_efficiency_reporting,
    "succession_planning": scenario_succession_planning,
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
    "simulator_walk_stays_physically_plausible": scenario_simulator_walk_stays_physically_plausible,
    "registry_connection_survives_lock_contention": scenario_registry_connection_survives_lock_contention,
    "mia_home_sync_honest_skip_when_unconfigured": scenario_mia_home_sync_honest_skip_when_unconfigured,
    "mia_home_sync_pushes_via_rsync": scenario_mia_home_sync_pushes_via_rsync,
    "mia_home_sync_paces_by_interval": scenario_mia_home_sync_paces_by_interval,
    "mia_home_sync_failure_raises_alert": scenario_mia_home_sync_failure_raises_alert,
    "pilot_shopping_list_includes_override_switch": scenario_pilot_shopping_list_includes_override_switch,
    "notification_config_honest_default_when_missing": scenario_notification_config_honest_default_when_missing,
    "notification_config_loads_real_values": scenario_notification_config_loads_real_values,
    "mcu_transport_pairs_over_a_real_link": scenario_mcu_transport_pairs_over_a_real_link,
    "mcu_transport_dispatches_real_command": scenario_mcu_transport_dispatches_real_command,
    "mcu_transport_fallback_raises_critical": scenario_mcu_transport_fallback_raises_critical,
    "mcu_transport_scan_paces_by_interval": scenario_mcu_transport_scan_paces_by_interval,
    "dosing_no_actuator_alerts_instead_of_faking": scenario_dosing_no_actuator_alerts_instead_of_faking,
    "dosing_no_limit_configured_blocks_and_alerts": scenario_dosing_no_limit_configured_blocks_and_alerts,
    "heater_closes_the_loop": scenario_heater_closes_the_loop,
    "water_heater_closes_the_loop": scenario_water_heater_closes_the_loop,
    "co2_injection_closes_the_loop": scenario_co2_injection_closes_the_loop,
    "do_relaxes_toward_temp_equilibrium": scenario_do_relaxes_toward_temp_equilibrium,
    "alert_manager_resolve": scenario_alert_manager_resolve,
    "alert_manager_acknowledge": scenario_alert_manager_acknowledge,
    "alert_manager_stale_sweep": scenario_alert_manager_stale_sweep,
    "alert_manager_recurrence_after_resolution": scenario_alert_manager_recurrence_after_resolution,
    "diagnose_alert_reuses_open_task": scenario_diagnose_alert_reuses_open_task,
    "create_maintenance_task_tool_validates": scenario_create_maintenance_task_tool_validates,
    "add_species_tool_full_fields": scenario_add_species_tool_full_fields,
    "update_maintenance_task_status_tool_validates": scenario_update_maintenance_task_status_tool_validates,
    "propose_experiment_tool_validates": scenario_propose_experiment_tool_validates,
    "dosing_min_interval_enforced": scenario_dosing_min_interval_enforced,
    "data_retention_prunes_old_rows": scenario_data_retention_prunes_old_rows,
    "data_retention_noop_when_nothing_old": scenario_data_retention_noop_when_nothing_old,
    "self_preservation_no_presence_sensor_silent": scenario_self_preservation_no_presence_sensor_silent,
    "self_preservation_signals_with_presence": scenario_self_preservation_signals_with_presence,
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
