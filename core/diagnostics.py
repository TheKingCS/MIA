"""
MIA Homestead — Diagnostic Engine
v0.1

The point of everything in infrastructure_registry.py existing: when
something's wrong, point at the SPECIFIC physical thing, not a generic
troubleshooting checklist. "Check the pH sensor" is not useful at 6am
with a cold coffee; "the pH sensor feeds dosing decisions for the pH
Dosing MCU at PORT 2, mounted next to the pH-up/pH-down bottles — check
the I2C cable there first" is.

This does pattern-matching against known fault types (stale sensor,
out-of-range reading, actuator not responding) crossed with the
infrastructure map — it does NOT diagnose novel failure modes it
hasn't been told the shape of. Treat its output as a strong first
guess, not a guaranteed root cause.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.diagnostics")

# Maps a sensor type to the actuator(s) whose dosing decisions depend
# on it — used to find the relevant MCU/wiring even when the fault is
# reported against a sensor, not an actuator directly.
SENSOR_TO_DEPENDENT_ACTUATORS = {
    "ph": ["ph_up_pump", "ph_down_pump"],
    "ec": ["nutrient_concentrate_pump"],
}


class DiagnosticEngine(Describable):
    # How recent a same-type fault on a DIFFERENT cell/module has to be
    # to count as "probably the same shared cause" rather than an
    # unrelated coincidence.
    CORRELATION_WINDOW_MINUTES = 5

    def __init__(self, db_conn: sqlite3.Connection, infrastructure, maintenance=None, notifier=None):
        self.db = db_conn
        self.infrastructure = infrastructure
        self.maintenance = maintenance
        self.notifier = notifier

    def diagnose_alert(self, alert_id: int, create_task: bool = False) -> dict:
        """Takes an existing alert row and produces a specific diagnosis
        by pattern-matching its message/source against known fault
        shapes and the infrastructure map. Optionally files a
        maintenance task with the diagnosis pre-filled."""
        row = self.db.execute(
            "SELECT severity, source, message FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if not row:
            return {"error": f"no alert {alert_id}"}
        severity, source, message = row

        # Multi-cell correlation checked FIRST — the same fault type
        # appearing on 2+ different cells/modules within a short window
        # is almost certainly one shared cause (power, the Pi itself,
        # a shared bus), not that many coincidental independent probe
        # failures. A much more specific, more useful diagnosis than
        # "sensor stale" repeated once per cell.
        diagnosis = self._check_multi_cell_correlation(alert_id, source, message)
        if diagnosis is None:
            diagnosis = self._pattern_match(source, message)

        actionable = diagnosis.get("actuator_name") or diagnosis.get("correlated_with")
        if create_task and self.maintenance and actionable:
            title = f"Investigate: {diagnosis['likely_cause']}"
            description = diagnosis["guidance"]
            task_id = self.maintenance.create_task(
                title=title, task_type="repair", priority="high" if severity == "critical" else "medium",
                description=description, related_asset_type="actuator", created_by="system",
            )
            diagnosis["maintenance_task_id"] = task_id

        return diagnosis

    def _check_multi_cell_correlation(self, alert_id: int, source: str, message: str) -> dict | None:
        """Looks for another currently-unresolved alert, on a DIFFERENT
        source (module/cell), mentioning the same sensor type, raised
        within CORRELATION_WINDOW_MINUTES of this one. Returns None (no
        correlation, fall through to the normal per-sensor diagnosis) if
        nothing matches — never a confident wrong guess, same discipline
        as _pattern_match's own fallback."""
        msg_lower = message.lower()
        for sensor_type in SENSOR_TO_DEPENDENT_ACTUATORS:
            if sensor_type not in msg_lower:
                continue
            if not ("stale" in msg_lower or "missing" in msg_lower or f"no {sensor_type}" in msg_lower):
                continue
            others = self.db.execute(
                "SELECT DISTINCT source FROM alerts WHERE resolved = 0 AND id != ? AND source != ? "
                "AND lower(message) LIKE ? "
                "AND timestamp >= datetime('now', ?)",
                (alert_id, source, f"%{sensor_type}%", f"-{self.CORRELATION_WINDOW_MINUTES} minutes"),
            ).fetchall()
            if not others:
                continue
            other_sources = sorted(r[0] for r in others)
            return {
                "likely_cause": f"Shared infrastructure fault (correlated {sensor_type} failure across cells)",
                "guidance": (
                    f"The same {sensor_type} fault is also currently affecting: {', '.join(other_sources)}. "
                    f"{len(other_sources) + 1} independent probe failures at once is unlikely — check shared "
                    f"infrastructure first (power, the Pi itself, a shared I2C/serial bus) before investigating "
                    f"each sensor individually."
                ),
                "actuator_name": None,
                "correlated_with": other_sources,
                "source_alert": message,
            }
        return None

    def auto_diagnose_new_alerts(self) -> list[dict]:
        """Scans for unresolved, not-yet-auto-diagnosed alerts and
        diagnoses each one, filing a maintenance task where the pattern
        match is specific enough to. Called every control-loop cycle by
        main.py (and directly by scenarios.py's recovery-ladder
        scenario) — the concrete "expanded autonomy" change: diagnosis +
        a filed maintenance task now happen the moment an alert survives
        the recovery ladder, instead of only when a human/assistant
        thinks to ask via diagnose_alert(). Read/diagnose/file-a-task
        only — never touches dosing, orders, or config rollback."""
        rows = self.db.execute(
            "SELECT id FROM alerts WHERE resolved = 0 AND auto_diagnosed_at IS NULL "
            "AND severity IN ('warning', 'critical')"
        ).fetchall()
        results = []
        for (alert_id,) in rows:
            diagnosis = self.diagnose_alert(alert_id, create_task=True)
            self.db.execute(
                "UPDATE alerts SET auto_diagnosed_at = datetime('now') WHERE id = ?", (alert_id,)
            )
            self.db.commit()
            results.append(diagnosis)
        return results

    def _pattern_match(self, source: str, message: str) -> dict:
        msg_lower = message.lower()

        # Stale/missing sensor pattern
        for sensor_type, actuators in SENSOR_TO_DEPENDENT_ACTUATORS.items():
            if sensor_type in msg_lower and ("stale" in msg_lower or "no " + sensor_type in msg_lower
                                              or "missing" in msg_lower):
                return self._build_sensor_diagnosis(sensor_type, actuators, message)

        # Out-of-range / fault pattern
        for sensor_type, actuators in SENSOR_TO_DEPENDENT_ACTUATORS.items():
            if sensor_type in msg_lower and ("fault" in msg_lower or "implausible" in msg_lower
                                              or "out of range" in msg_lower or "out_of_range" in msg_lower):
                return self._build_sensor_diagnosis(sensor_type, actuators, message,
                                                      likely_cause_prefix="Probe fault or miscalibration")

        # Power/telemetry pattern
        if "power" in source.lower() or "battery" in msg_lower or "soc" in msg_lower:
            return {
                "likely_cause": "Power telemetry unavailable or battery critically low",
                "guidance": (
                    "Check the solar charge controller's RS485/Modbus connection to the Pi first — "
                    "this is the most common cause of 'no telemetry' vs an actual power problem. "
                    "If telemetry IS present and battery is genuinely low, check panel orientation/"
                    "shading and battery age/health."
                ),
                "actuator_name": None,
                "source_alert": message,
            }

        # Fallback — no specific pattern matched
        return {
            "likely_cause": "No specific pattern matched — this fault type isn't in the diagnostic engine's known shapes yet",
            "guidance": f"Original alert: {message}. Manual investigation needed; consider adding "
                        f"this pattern to DiagnosticEngine once the root cause is known, so it's "
                        f"recognized automatically next time.",
            "actuator_name": None,
            "source_alert": message,
        }

    def _build_sensor_diagnosis(self, sensor_type: str, dependent_actuators: list[str],
                                  message: str, likely_cause_prefix: str = "Sensor stale or disconnected") -> dict:
        # Use the first dependent actuator's wiring as the representative
        # location — in practice pH/EC sensors and their dosing pumps
        # are on the same MCU, so this correctly points at one place.
        actuator_name = dependent_actuators[0]
        wiring = self.infrastructure.get_wiring_for_actuator(actuator_name)
        plumbing = self.infrastructure.get_plumbing_for_actuator(actuator_name)

        if wiring:
            location = (
                f"The {sensor_type} sensor's dosing chain runs through the "
                f"{wiring['role_display_name']} ({wiring['port_label']}, relay channel "
                f"{wiring['relay_channel']}), mounted: {wiring['mount_location']}"
            )
        else:
            location = f"No wiring record found for {actuator_name} — check config/devices/roles/*.yaml is current."

        plumbing_note = ""
        if plumbing:
            seg = plumbing[0]
            plumbing_note = f" This actuator drives the '{seg['segment_name']}' plumbing segment ({seg['from_component']} -> {seg['to_component']})."

        return {
            "likely_cause": f"{likely_cause_prefix} ({sensor_type})",
            "guidance": f"{location}.{plumbing_note} Check the physical connection there first.",
            "actuator_name": actuator_name,
            "source_alert": message,
        }

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="diagnostics",
            display_name="Diagnostic Engine",
            purpose=(
                "Cross-references alerts against the infrastructure map (wiring, plumbing) "
                "to produce specific repair guidance — which MCU, which port, which pipe "
                "segment — instead of generic troubleshooting steps."
            ),
            data_produced=["diagnosis: likely cause + specific physical location + guidance"],
            actions_possible=[
                "diagnose an alert", "optionally file a maintenance task with the diagnosis attached",
                "auto-diagnose every unresolved alert automatically, every control-loop cycle, "
                "the moment it survives the recovery ladder — not only when asked",
                "correlate the same fault type appearing on 2+ different cells within a short "
                "window as one likely shared-infrastructure cause, instead of diagnosing each "
                "cell's alert in isolation",
            ],
            limits_and_safety=(
                "Pattern-matches against known fault shapes only — a novel failure mode it "
                "hasn't been told about falls through to a generic 'manual investigation "
                "needed' response rather than a confident wrong guess. Never attempts an "
                "autonomous fix, only points a human at the right place — the only side effect "
                "of automatic invocation is filing a maintenance task, exactly what "
                "diagnose_alert(create_task=True) already does on request; never touches "
                "dosing targets, orders, or config rollback."
            ),
            example_questions=["Why is the pH sensor stale?", "Diagnose this alert for me"],
            verification_evidence=[
                "Live manual test 2026-08-26: full real-code-path proof — backdated a real "
                "sensor reading, ran the actual control cycle, let the base contract raise a "
                "genuine staleness alert, then confirmed the diagnosis correctly traced it to "
                "the exact MCU (pH Dosing Controller, PORT 2, relay channel 1) and physical "
                "mounting location, and auto-filed a maintenance task with that diagnosis attached",
                "scenarios.py::scenario_sensor_recovery_exhausted_escalates — confirmed "
                "auto_diagnose_new_alerts(), called automatically from the control loop with "
                "zero manual trigger, produces a real diagnosis (not the generic fallback) and "
                "auto-files a system-created maintenance task the same cycle the alert survives "
                "the recovery ladder",
                "scenarios.py::scenario_multi_cell_fault_correlation — confirmed a pH sensor "
                "failing simultaneously on two independent cells (cell_a_aquaponics + pilot_cell) "
                "produces a 'shared infrastructure' diagnosis referencing both cells rather than "
                "two independent per-sensor diagnoses",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure reasoning layer over existing data, no hardware of its own
