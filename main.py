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
from core.mcu_transport import McuTransportManager
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
from core.activity_journal import ActivityJournal
from core.biofilter_model import BiofilterModel
from core.sensor_confidence import SensorConfidence
from core.fish_health import FishHealth
from core.leak_detector import LeakDetector
from core.pest_disease import PestDisease
from core.weather_awareness import WeatherAwareness
from core.finance_tracker import FinanceTracker
from core.traceability import TraceabilityManager
from core.sustainability_report import SustainabilityReport
from core.succession_planner import SuccessionPlanner
from core.yield_forecaster import YieldForecaster
from core.dosing_recommendations import RecommendationEngine
from core.voice_briefing import VoiceBriefing
from core.reference_library import ReferenceLibrary
from core.irrigation import IrrigationScheduler
from core.circulation_monitor import CirculationMonitor
from core.alert_manager import AlertManager
from core.data_retention import DataRetentionManager
from core.mia_home_sync import MiaHomeSync
from modules.power_monitor import PowerMonitor, SOC_FORECAST_WARNING_HOURS
from viewer.export_state import export_state
from viewer.export_dashboard_state import export_dashboard_state
from viewer.export_home_snapshot import export_home_snapshot
from viewer.export_journal_state import export_journal_state
from viewer.export_planting_state import export_planting_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mia_homestead.main")


def execute_command(db: sqlite3.Connection, cmd, mcu_transport=None) -> None:
    """Real MCU dispatch, added 2026-09-02 (docs/DAY_ONE_READINESS.md,
    item #2) — this used to be a permanent "v0.1 stand-in," logging
    only, with no code anywhere that could actually reach real
    hardware. Now tries a real send first (core/mcu_transport.py,
    correctly a no-op when no MCU is paired for this actuator — every
    actuator, in this environment, today), falling back to the exact
    same simulated-log line as before when it isn't. The
    actuator_events row is written either way — that's the historical
    record of what was commanded, real hardware or not, and other
    modules (e.g. modules/aquaponics_cell.py's dosing-interval check)
    read from it regardless."""
    db.execute(
        "INSERT INTO actuator_events (actuator_id, action, duration_seconds, triggered_by) "
        "VALUES (?, ?, ?, ?)",
        (cmd.actuator_id, cmd.action, cmd.duration_seconds, cmd.triggered_by.value),
    )
    db.commit()
    sent_real = mcu_transport.dispatch_command(cmd) if mcu_transport else False
    logger.info(
        "EXECUTE (%s): actuator=%s action=%s duration=%s trigger=%s",
        "real MCU" if sent_real else "simulated",
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
    parser.add_argument("--journal-state-out", default="viewer/journal_state.json")
    parser.add_argument("--no-journal-export", action="store_true",
                         help="Skip auto-exporting the activity journal state")
    parser.add_argument("--planting-state-out", default="viewer/planting_state.json")
    parser.add_argument("--no-planting-export", action="store_true",
                         help="Skip auto-exporting the planting planner state")
    args = parser.parse_args()

    # Notifications are optional and inert until SMTP creds are filled in —
    # safe to run with defaults during development.
    notifier = NotificationDispatcher(NotificationConfig.from_config())

    # force_read_fn=None: main.py and drivers/simulator.py --run are
    # separate processes sharing only the sqlite file, so there's no
    # live driver object here for a module's recovery ladder to call
    # for an on-demand reread. Steps 2-4 of the ladder (redundant-sensor
    # preference, retry-delay, auto-diagnosis) work fully regardless;
    # step 1 (force-reread) is inert here until real hardware runs
    # in-process (see docs — driver + control loop share one process on
    # real hardware, so this gap disappears there for free).
    registry = ModuleRegistry(args.config, args.db, notifier=notifier, force_read_fn=None)
    registry.load()
    logger.info("Loaded %d module(s): %s", len(registry.modules), list(registry.modules))

    db = registry.db_conn
    maintenance = MaintenanceManager(db, notifier=notifier)
    inventory = InventoryManager(db, notifier=notifier)
    devices = DeviceRegistry(db, notifier=notifier)
    mcu_transport = McuTransportManager(db, devices, notifier=notifier)
    species = SpeciesRegistry(db)
    bed_planting = BedPlantingManager(db, species, notifier=notifier)
    experiments = ExperimentManager(db, notifier=notifier, species_registry=species)
    infrastructure = InfrastructureRegistry(db)
    diagnostics = DiagnosticEngine(db, infrastructure, maintenance=maintenance, notifier=notifier)
    backups = BackupManager(db, notifier=notifier)
    deploys = DeployManager(db, notifier=notifier)
    deadmans = DeadMansSwitchMonitor(db, notifier=notifier)
    reports = ReportGenerator(db, notifier=notifier)
    trend_analyzer = TrendAnalyzer(db, notifier=notifier)
    journal = ActivityJournal(db)
    biofilter = BiofilterModel(db, notifier=notifier)
    sensor_confidence = SensorConfidence(db)
    fish_health = FishHealth(db, notifier=notifier)
    leak_detector = LeakDetector(db, notifier=notifier)
    pest_disease = PestDisease(db)
    weather = WeatherAwareness(db, notifier=notifier)
    finance = FinanceTracker(db)
    irrigation = IrrigationScheduler.from_config("config/irrigation_schedules.yaml", db, notifier=notifier)
    circulation_monitor = CirculationMonitor(db, notifier=notifier)
    alert_manager = AlertManager(db, notifier=notifier)
    data_retention = DataRetentionManager(db, notifier=notifier)
    mia_home_sync = MiaHomeSync(db, notifier=notifier)
    traceability = TraceabilityManager(db)
    sustainability = SustainabilityReport(db)
    succession = SuccessionPlanner(db)
    yield_forecaster = YieldForecaster(db)
    recommendations = RecommendationEngine(db)
    voice_briefing = VoiceBriefing(db)
    reference_library = ReferenceLibrary(db)

    # Every module and service declares what it does; this rebuilds the
    # assistant's self-knowledge from the live code every time the
    # system starts, so it's never taught anything by hand.
    all_describables = [(mod, mid) for mid, mod in registry.modules.items()] + [
        (inventory, "inventory"), (maintenance, "maintenance"),
        (notifier, "notifications"), (devices, "device_registry"), (mcu_transport, "mcu_transport"),
        (species, "species_registry"), (bed_planting, "bed_planting"),
        (experiments, "experiment_manager"),
        (infrastructure, "infrastructure_registry"), (diagnostics, "diagnostics"),
        (backups, "backup_manager"), (deadmans, "deadmans_switch"),
        (reports, "report_generator"), (trend_analyzer, "trend_analyzer"),
        (deploys, "deploy_manager"), (journal, "activity_journal"),
        (biofilter, "biofilter_model"), (sensor_confidence, "sensor_confidence"),
        (fish_health, "fish_health"), (leak_detector, "leak_detector"),
        (pest_disease, "pest_disease"), (weather, "weather_awareness"),
        (finance, "finance_tracker"), (irrigation, "irrigation_scheduler"),
        (circulation_monitor, "circulation_monitor"), (alert_manager, "alert_manager"),
        (data_retention, "data_retention"), (mia_home_sync, "mia_home_sync"),
        (traceability, "traceability"), (sustainability, "sustainability_report"),
        (succession, "succession_planner"), (yield_forecaster, "yield_forecaster"),
        (recommendations, "dosing_recommendations"), (voice_briefing, "voice_briefing"),
        (reference_library, "reference_library"),
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
            # Real reliability gap found live 2026-09-02: this whole
            # section (dosing/control decisions, diagnostics, leak/
            # circulation checks, the 60-cycle maintenance/backup/report
            # block) had NO exception handling at all, unlike the 5
            # export calls below which already log-and-continue on
            # failure. drivers/simulator.py's own tick() loop hit this
            # exact gap first and crashed outright on a transient
            # 'database is locked' error (two independent 5-second-interval
            # processes writing the same SQLite file — see core/module_
            # registry.py's WAL-mode fix for the root cause), leaving the
            # whole system's sensor feed dead for over an hour with nothing
            # restarting it. This loop is meant to run for weeks unattended
            # (schema/mia_homestead_schema.sql's own promise) — the same
            # 'log and continue' discipline already used for the exports
            # below now covers the rest of one cycle's work too. Individual
            # module isolation (core/module_registry.py's run_all_cycles())
            # stays as the finer-grained first line of defense; this is the
            # safety net behind it for everything else in one cycle.
            try:
                record_heartbeat(db, "pi_main_loop")

                # Real MCU transport, added 2026-09-02 (docs/DAY_ONE_
                # READINESS.md, item #2). Self-paced (scan_for_new_
                # devices() only actually opens/listens on ports once
                # its own interval has elapsed) and always a correct
                # no-op today — zero serial hardware exists in this
                # environment, so every actuator command below still
                # falls back to the exact same simulated-log behavior
                # as before.
                paired = mcu_transport.scan_for_new_devices()
                if paired:
                    logger.info("Paired %d new device(s) over a real MCU link: %s",
                                len(paired), [p["hardware_id"][:8] for p in paired])
                mcu_transport.send_heartbeats()
                mcu_transport.poll_status()

                results = registry.run_all_cycles()
                for module_id, commands in results.items():
                    for cmd in commands:
                        execute_command(db, cmd, mcu_transport=mcu_transport)
                    if not commands:
                        logger.debug("%s: no actions this cycle", module_id)

                # Auto-diagnose any alert that survived the recovery ladder,
                # every cycle (not gated to the 60-cycle block below) — the
                # whole point is reacting the instant a real alert exists,
                # not up to 60 cycles later. Cheap: a handful of indexed
                # SELECTs, bounded by the tiny number of genuinely new
                # unresolved alerts (usually zero). Read/diagnose/file-a-task
                # only — see core/diagnostics.py's own docstring on this.
                newly_diagnosed = diagnostics.auto_diagnose_new_alerts()
                if newly_diagnosed:
                    logger.info("Auto-diagnosed %d new alert(s): %s", len(newly_diagnosed),
                                [d.get("likely_cause") for d in newly_diagnosed])

                # Also every cycle, not gated to the 60-cycle block below — a
                # real leak needs detection within one cycle, not up to 60
                # cycles later; that delay is the whole gap this module exists
                # to close (see core/leak_detector.py's own docstring).
                leak_findings = leak_detector.check_for_leaks()
                if leak_findings:
                    logger.critical("Possible leak detected in %d cell(s)", len(leak_findings))

                # Same urgency reasoning as leak detection above, not the
                # 60-cycle block below — a stalled circulation pump risks a
                # biofilter ammonia spike (SAFETY_SPEC.md's #2 priority load)
                # and needs to surface within one cycle, not up to 60 later.
                circulation_findings = circulation_monitor.check_circulation()
                if circulation_findings:
                    logger.critical("Circulation stall detected in %d cell(s)", len(circulation_findings))

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
                        voice_result = voice_briefing.synthesize_latest_report()
                        if voice_result.get("synthesized"):
                            logger.info("Voice briefing synthesized: %s", voice_result["output_path"])
                        # else: honestly no-ops when voice_model_path isn't configured —
                        # not logged as a warning, same "nice when connected, never
                        # required" posture as weather/cloud-escalation/SMS.
                    drift_findings = trend_analyzer.check_all_sensors()
                    if drift_findings:
                        logger.info("Trend analyzer found %d sensor(s) drifting", len(drift_findings))
                    for module in registry.modules.values():
                        if isinstance(module, PowerMonitor):
                            forecast = module.check_soc_forecast()
                            if forecast and forecast["hours_to_threshold"] <= SOC_FORECAST_WARNING_HOURS:
                                logger.info("%s: SOC forecast warning — %s", module.module_id, forecast)
                    overdue_tests = biofilter.check_overdue_water_tests()
                    if overdue_tests:
                        logger.info("Biofilter model: %d cell(s) overdue for a water test", len(overdue_tests))
                    mortality_spikes = fish_health.check_mortality_spike()
                    if mortality_spikes:
                        logger.warning("Fish health: mortality spike in %d cell(s)", len(mortality_spikes))
                    if weather.should_check_now():
                        weather_result = weather.check_weather()
                        if weather_result:
                            logger.info("Weather check: %s", weather_result)
                    watered = irrigation.check_scheduled_irrigation()
                    if watered:
                        logger.info("Irrigation scheduler watered %d bed(s): %s",
                                    len(watered), [w["grow_bed_name"] for w in watered])
                    auto_resolved = alert_manager.check_stale_alerts()
                    if auto_resolved:
                        logger.info("Auto-resolved %d stale alert(s) not re-raised recently: %s",
                                    len(auto_resolved), [a["alert_id"] for a in auto_resolved])
                    pruned = data_retention.prune_old_data()
                    if pruned:
                        logger.info("Pruned old data past the retention window: %s", pruned)
            except Exception:
                logger.exception("Control loop cycle failed — logged, continuing to the next cycle")

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

            # Automated 2026-09-02 (docs/MIA_HOME_SYNC_PLAN.md's own
            # "manual-first, automate later" transport question,
            # resolved by the user) — core/mia_home_sync.py pushes this
            # file to MIA Home's watched folder via rsync once
            # config/mia_home_sync.yaml's destination is set, pacing
            # itself on interval_minutes; a no-op call every cycle
            # otherwise (destination unset, or not due yet).
            if not args.no_home_snapshot_export:
                try:
                    export_home_snapshot(args.db, args.home_snapshot_out)
                    mia_home_sync.maybe_sync(args.home_snapshot_out)
                except Exception:
                    logger.exception("MIA Home snapshot export/sync failed this cycle — continuing control loop regardless")

            if not args.no_journal_export:
                try:
                    export_journal_state(args.db, args.journal_state_out)
                except Exception:
                    logger.exception("Journal state export failed this cycle — continuing control loop regardless")

            if not args.no_planting_export:
                try:
                    export_planting_state(args.db, args.layout, args.planting_state_out)
                except Exception:
                    logger.exception("Planting planner state export failed this cycle — continuing control loop regardless")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nControl loop stopped.")


if __name__ == "__main__":
    main()
