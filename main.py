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
from viewer.export_state import export_state

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

    # Every module and service declares what it does; this rebuilds the
    # assistant's self-knowledge from the live code every time the
    # system starts, so it's never taught anything by hand.
    all_describables = [(mod, mid) for mid, mod in registry.modules.items()] + [
        (inventory, "inventory"), (maintenance, "maintenance"),
        (notifier, "notifications"), (devices, "device_registry"),
        (species, "species_registry"), (bed_planting, "bed_planting"),
        (experiments, "experiment_manager"),
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

            # The digital twin is a live feature, not a manual dev tool —
            # keep it current every cycle so anyone walking up to the
            # viewer sees real-time "go here" status, not stale data.
            if not args.no_viewer_export:
                try:
                    export_state(args.db, args.layout, args.viewer_state_out)
                except Exception:
                    logger.exception("Viewer state export failed this cycle — continuing control loop regardless")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nControl loop stopped.")


if __name__ == "__main__":
    main()
