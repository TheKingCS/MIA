"""
MIA Homestead — Main Orchestrator
v0.1

Runs the control loop: load modules -> tick sensors (simulator, for now)
-> run each module's cycle -> execute resulting actuator commands.

In this v0.1, "executing" a command means logging it to actuator_events
and printing it — there's no real Safety MCU yet. When the MCU exists,
this is the one place that changes: swap the local `execute_command`
function for one that sends the command over the Pi<->MCU serial link
per docs/MCU_PROTOCOL.md. Nothing in modules/ or core/module_registry.py
needs to change.

Usage:
    python drivers/simulator.py --db mia_homestead.db --setup
    python main.py --db mia_homestead.db
"""

import argparse
import logging
import sqlite3
import sys
import time
from datetime import datetime

from core.module_registry import ModuleRegistry
from core.notifications import NotificationConfig, NotificationDispatcher
from core.maintenance import MaintenanceManager
from core.inventory import InventoryManager
from core.capability_registry import CapabilityRegistry
from core.hardware_registry import HardwareRegistry
from core.device_registry import DeviceRegistry
from core.species_registry import SpeciesRegistry
from core.bed_planting import BedPlantingManager
from core.experiment_manager import ExperimentManager
from core.infrastructure_registry import InfrastructureRegistry
from core.diagnostics import DiagnosticEngine
from core.backup_manager import BackupManager
from core.generate_capabilities_doc import generate_and_write as write_capabilities_doc
from core.generate_bom_doc import generate_and_write as write_bom_doc
from core.deadmans_switch import DeadMansSwitchMonitor
from core.report_generator import ReportGenerator
from core.trend_analyzer import TrendAnalyzer
from core.deploy_manager import DeployManager
from modules.power_monitor import PowerMonitor, SOC_FORECAST_WARNING_HOURS
from viewer.export_state import export_state
from viewer.export_dashboard_state import export_dashboard_state
from viewer.export_home_snapshot import export_home_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mia_homestead.main")


def execute_command(db: sqlite3.Connection, cmd) -> None:
    """v0.1 stand-in for real MCU dispatch — logs the action that WOULD
    be sent to the Safety MCU. Replace this function's body only, once
    real hardware exists."""
    db.execute(
        "INSERT INTO actuator_events (actuator_id, action, duration_seconds, triggered_by) "
        "VALUES (?, ?, ?, ?)",
        (cmd.actuator_id, cmd.action, cmd.duration_seconds, cmd.triggered_by.value),
    )
    db.commit()
    logger.info(
        "EXECUTE (simulated): actuator=%s action=%s duration=%s trigger=%s",
        cmd.actuator_id, cmd.action, cmd.duration_seconds, cmd.triggered_by.value,
    )


def record_heartbeat(db: sqlite3.Connection, component: str) -> None:
    db.execute(
        "INSERT INTO system_heartbeat (component, last_seen) VALUES (?, datetime('now'))",
        (component,),
    )
    db.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--config", default="config/modules.yaml")
    parser.add_argument("--interval", type=float, default=10.0, help="seconds between control cycles")
    parser.add_argument("--layout", default="config/layout.json")
    parser.add_argument("--viewer-state-out", default="viewer/state.json")
    parser.add_argument("--no-viewer-export", action="store_true", help="Skip auto-exporting digital twin state")
    parser.add_argument("--dashboard-state-out", default="viewer/dashboard_state.json")
    parser.add_argument("--no-dashboard-export", action="store_true", help="Skip auto-exporting ops dashboard state")
    parser.add_argument("--home-snapshot-out", default="viewer/home_snapshot.json")
    parser.add_argument("--no-home-snapshot-export", action="store_true",
                         help="Skip auto-exporting the summarized MIA Home snapshot")
    args = parser.parse_args()

    # Notifications are optional and inert until SMTP creds are filled in —
    # safe to run with defaults during development.
    notifier = NotificationDispatcher(NotificationConfig())

    registry = ModuleRegistry(args.config, args.db, notifier=notifier)
    registry.load()
    logger.info("Loaded %d module(s): %s", len(registry.modules), list(registry.modules))

    db = registry.db_conn
    maintenance = MaintenanceManager(db, notifier=notifier)
    inventory = InventoryManager(db, notifier=notifier)
    devices = DeviceRegistry(db, notifier=notifier)
    species = SpeciesRegistry(db)
    bed_planting = BedPlantingManager(db, species, notifier=notifier)
    experiments = ExperimentManager(db, notifier=notifier)
    infrastructure = InfrastructureRegistry(db)
    diagnostics = DiagnosticEngine(db, infrastructure, maintenance=maintenance, notifier=notifier)
    backups = BackupManager(db, notifier=notifier)
    deploys = DeployManager(db, notifier=notifier)
    deadmans = DeadMansSwitchMonitor(db, notifier=notifier)
    reports = ReportGenerator(db, notifier=notifier)
    trend_analyzer = TrendAnalyzer(db, notifier=notifier)

    # Every module and service declares what it does; this rebuilds the
    # assistant's self-knowledge from the live code every time the
    # system starts, so it's never taught anything by hand.
    all_describables = [(mod, mid) for mid, mod in registry.modules.items()] + [
        (inventory, "inventory"), (maintenance, "maintenance"),
        (notifier, "notifications"), (devices, "device_registry"),
        (species, "species_registry"), (bed_planting, "bed_planting"),
        (experiments, "experiment_manager"),
        (infrastructure, "infrastructure_registry"), (diagnostics, "diagnostics"),
        (backups, "backup_manager"), (deadmans, "deadmans_switch"),
        (reports, "report_generator"), (trend_analyzer, "trend_analyzer"),
        (deploys, "deploy_manager"),
    ]
    capabilities = CapabilityRegistry(db)
    registered = capabilities.register_all([item for item, _ in all_describables])
    logger.info("Registered %d capability description(s)", len(registered))

    # Same discipline for hardware needs — every module that requires
    # physical hardware declared it the moment it was written, so the
    # BOM is never reconstructed after the fact.
    hardware = HardwareRegistry(db)
    hw_count = hardware.register_all(all_describables)
    logger.info("Registered %d hardware requirement(s) across all modules", hw_count)

    # The running, provable features/capabilities doc — regenerated
    # from live data every startup, so it can never drift from what
    # the code actually does or claim proof that doesn't exist.
    write_capabilities_doc(args.db)
    write_bom_doc(args.db)
    coverage = CapabilityRegistry.get_verification_coverage(db)
    logger.info("Verification coverage: %d/%d modules have proof behind their capabilities",
                coverage["verified"], coverage["total"])

    print(f"\nMIA Homestead control loop running. Cycle every {args.interval}s. Ctrl+C to stop.\n")
    cycle_count = 0
    try:
        while True:
            record_heartbeat(db, "pi_main_loop")
            results = registry.run_all_cycles()
            for module_id, commands in results.items():
                for cmd in commands:
                    execute_command(db, cmd)
                if not commands:
                    logger.debug("%s: no actions this cycle", module_id)

            # Maintenance/calibration/reorder checks don't need to run every
            # cycle — every 60 cycles is plenty (tune once real interval is set)
            cycle_count += 1
            if cycle_count % 60 == 0:
                created = maintenance.generate_calibration_tasks() + maintenance.generate_recurring_tasks()
                if created:
                    logger.info("Maintenance scan created %d new task(s)", created)
                proposed = inventory.auto_propose_reorders()
                if proposed:
                    logger.info("Inventory scan proposed %d new order(s) — check the to-order list", proposed)
                due_experiments = experiments.check_due_experiments()
                if due_experiments:
                    logger.info("Completed %d experiment(s): %s — check results", len(due_experiments), due_experiments)
                proposed_from_patterns = experiments.propose_experiments_for_underperformance(species, args.config)
                if proposed_from_patterns:
                    logger.info("Proposed %d experiment(s) from an observed underperformance "
                                "pattern — review before starting: %s", len(proposed_from_patterns), proposed_from_patterns)
                watch_results = backups.check_update_watches()
                if watch_results:
                    logger.info("Update watch results: %s", watch_results)
                deploy_watch_results = deploys.check_deploy_watches()
                for result in deploy_watch_results:
                    if result["outcome"] == "auto_rolled_back":
                        # deploy_manager already reverted the working tree — the
                        # decision to actually exit belongs HERE (see that
                        # module's own docstring for why), so the systemd layer
                        # (deploy/mia-homestead.service, Restart=on-failure) can
                        # bring the process back up running the reverted code.
                        # A non-systemd/dev run just stops; a human reruns it.
                        logger.critical(
                            "Exiting after an automatic code rollback (watch #%s) — "
                            "restart required to run the reverted code.", result["watch_id"],
                        )
                        sys.exit(1)
                forecasted = inventory.check_forecasted_shortages()
                if forecasted:
                    logger.info("Forecasted %d shortage(s) proposed early", forecasted)
                deadmans_result = deadmans.check_escalation()
                if deadmans_result.get("escalated"):
                    logger.warning("Dead-man's-switch escalated: %s", deadmans_result)
                hours_since_report = reports.hours_since_last_report()
                if hours_since_report is None or hours_since_report >= 24:
                    reports.generate_and_send()
                    logger.info("Periodic report generated and sent")
                drift_findings = trend_analyzer.check_all_sensors()
                if drift_findings:
                    logger.info("Trend analyzer found %d sensor(s) drifting", len(drift_findings))
                for module in registry.modules.values():
                    if isinstance(module, PowerMonitor):
                        forecast = module.check_soc_forecast()
                        if forecast and forecast["hours_to_threshold"] <= SOC_FORECAST_WARNING_HOURS:
                            logger.info("%s: SOC forecast warning — %s", module.module_id, forecast)

            # The digital twin is a live feature, not a manual dev tool —
            # keep it current every cycle so anyone walking up to the
            # viewer sees real-time "go here" status, not stale data.
            if not args.no_viewer_export:
                try:
                    export_state(args.db, args.layout, args.viewer_state_out)
                except Exception:
                    logger.exception("Viewer state export failed this cycle — continuing control loop regardless")

            # Same reasoning as the digital twin export above — the ops
            # dashboard should read live, not stale, state.
            if not args.no_dashboard_export:
                try:
                    export_dashboard_state(args.db, args.dashboard_state_out)
                except Exception:
                    logger.exception("Dashboard state export failed this cycle — continuing control loop regardless")

            # Local file only — getting this onto MIA Home's watched
            # folder is a deliberately separate, still-manual step (see
            # docs/MIA_HOME_SYNC_PLAN.md). Cheap enough to just run
            # every cycle like the other two exports.
            if not args.no_home_snapshot_export:
                try:
                    export_home_snapshot(args.db, args.home_snapshot_out)
                except Exception:
                    logger.exception("MIA Home snapshot export failed this cycle — continuing control loop regardless")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nControl loop stopped.")


if __name__ == "__main__":
    main()
