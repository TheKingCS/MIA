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


SCENARIOS = {
    "stale_sensor_freeze": scenario_stale_sensor_freeze,
    "ph_crash_response": scenario_ph_crash_response,
    "power_loss_load_shed": scenario_power_loss_load_shed,
    "inconsistent_readings": scenario_inconsistent_readings,
    "sensor_recovery_ladder_recovers": scenario_sensor_recovery_ladder_recovers,
    "sensor_recovery_exhausted_escalates": scenario_sensor_recovery_exhausted_escalates,
    "multi_cell_fault_correlation": scenario_multi_cell_fault_correlation,
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
