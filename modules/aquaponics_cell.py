"""
MIA Homestead — Aquaponics Cell Module
v0.1

Concrete implementation of MiaHomesteadModule for a single aquaponics
cell (fish tank + grow bed + shared biofilter). Handles pH and EC
correction dosing within the hard limits enforced by the base contract.

Placeholder target ranges are passed in via config/modules.yaml — tune
these once fish/plant species are finalized. Tilapia + leafy greens is
a forgiving starting combo (pH 6.6-7.2, EC 800-1500 uS/cm is a
reasonable general range, not species-specific gospel).
"""

import logging
from datetime import datetime, timedelta

from contracts.mia_homestead_contract import (
    ActuatorCommand,
    MiaHomesteadModule,
    SensorReading,
    TriggerSource,
)

logger = logging.getLogger("mia_homestead.aquaponics_cell")

# Dissolved oxygen thresholds (mg/L) — standard warmwater aquaculture
# reference points, not species-tuned. DO crashes are the leading real
# cause of catastrophic fish loss (docs/HARDWARE_BOM_FULL_TIERS.md,
# Fork 3 finding, 2026-08-31) — this is alert-only, not a dosing
# correction: there's no actuator to raise DO beyond the aerator that's
# already always running (safe_default_state 'on'), so the only
# meaningful automated response is telling a human fast. DO is real,
# optional hardware (not every real cell has a probe) — see
# _has_sensor_type() below for how that's kept from becoming permanent
# noise on a cell that was never meant to have one.
DO_WARNING_THRESHOLD_MGL = 5.0
DO_CRITICAL_THRESHOLD_MGL = 3.0
DO_SPREAD_TOLERANCE_MGL = 1.5  # wider than pH's 0.5 — DO probes drift more with agitation/temp


class AquaponicsCell(MiaHomesteadModule):

    def __init__(
        self,
        module_id: str,
        cell_id: int,
        db_conn,
        ph_target_min: float,
        ph_target_max: float,
        ec_target_min: float,
        ec_target_max: float,
        notifier=None,
        force_read_fn=None,
        recovery_log_fn=None,
    ):
        super().__init__(module_id, cell_id, db_conn, notifier=notifier,
                          force_read_fn=force_read_fn, recovery_log_fn=recovery_log_fn)
        self.ph_target_min = ph_target_min
        self.ph_target_max = ph_target_max
        self.ec_target_min = ec_target_min
        self.ec_target_max = ec_target_max
        # Rolling readings buffer used to require N-consistent-readings
        # before triggering a dose (see SAFETY_SPEC.md).
        self._ph_history: list[float] = []
        self._ec_history: list[float] = []
        self._do_history: list[float] = []

    def read_sensors(self) -> list[SensorReading]:
        """
        Pulls the most recent reading per active sensor for this cell
        from the sensor_readings table. Actual hardware polling happens
        in a separate driver layer that writes into sensor_readings —
        this module only reads what's already been logged, keeping
        control logic decoupled from hardware I/O.
        """
        rows = self.db.execute(
            """
            SELECT sr.sensor_id, s.type, sr.value, sr.timestamp,
                   sr.is_stale, sr.is_out_of_range
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.cell_id = ? AND s.active = 1
            AND sr.id IN (
                SELECT MAX(id) FROM sensor_readings GROUP BY sensor_id
            )
            """,
            (self.cell_id,),
        ).fetchall()

        readings = []
        self._type_by_sensor = {}
        for sensor_id, sensor_type, value, ts, is_stale, is_oor in rows:
            readings.append(
                SensorReading(
                    sensor_id=sensor_id,
                    value=value,
                    timestamp=datetime.fromisoformat(ts),
                    is_stale=bool(is_stale),
                    is_out_of_range=bool(is_oor),
                )
            )
            self._type_by_sensor[sensor_id] = sensor_type
        return readings

    def _current_targets(self) -> dict:
        """Live targets — checks target_overrides first (an active
        experiment or an approved evidence-based change), falls back to
        the config-file defaults this module was constructed with. This
        is what makes experiments possible without restarting the
        process: nothing here changes unless a row in target_overrides
        says so, and that row only exists because a human (or an
        approved experiment) put it there."""
        targets = {
            "ph_target_min": self.ph_target_min, "ph_target_max": self.ph_target_max,
            "ec_target_min": self.ec_target_min, "ec_target_max": self.ec_target_max,
        }
        rows = self.db.execute(
            "SELECT param_name, value FROM target_overrides WHERE cell_id = ? AND active = 1",
            (self.cell_id,),
        ).fetchall()
        for param_name, value in rows:
            if param_name in targets:
                targets[param_name] = value
        return targets

    def evaluate(self, readings: list[SensorReading]) -> list[ActuatorCommand]:
        self._targets = self._current_targets()  # refresh every cycle, not just at construction
        commands = []
        ph_reading = self._latest_of_type(readings, "ph")
        ec_reading = self._latest_of_type(readings, "ec")
        # (see _latest_of_type below — now correctly filters by real sensor type)

        if ph_reading is None:
            # If a pH sensor exists and has reported before but is mid-retry
            # (see contracts.MiaHomesteadModule's recovery ladder), stay
            # quiet — the ladder's own alert will fire if it genuinely
            # exhausts. Only raise immediately for a sensor that's never
            # produced a reading at all (nothing to retry against).
            if not self._is_type_mid_retry("ph"):
                self._raise_alert(
                    "warning",
                    f"{self.module_id}: no pH reading available at all "
                    f"(sensor missing or producing zero data) — pH dosing held",
                )
        else:
            commands += self._evaluate_ph(ph_reading)

        if ec_reading is None:
            if not self._is_type_mid_retry("ec"):
                self._raise_alert(
                    "warning",
                    f"{self.module_id}: no EC reading available at all "
                    f"(sensor missing or producing zero data) — nutrient dosing held",
                )
        else:
            commands += self._evaluate_ec(ec_reading)

        # DO is genuinely optional hardware (unlike pH/EC, which every
        # tier's real BOM assumes) — only evaluate/alert on it at all if
        # a DO sensor is actually registered for this cell, so a cell
        # that was never meant to have one stays silent instead of
        # alerting forever on hardware that was never bought.
        if self._has_sensor_type("do"):
            do_reading = self._latest_of_type(readings, "do")
            if do_reading is None:
                if not self._is_type_mid_retry("do"):
                    self._raise_alert(
                        "warning",
                        f"{self.module_id}: no DO reading available at all "
                        f"(sensor missing or producing zero data) — dissolved oxygen monitoring degraded",
                    )
            else:
                self._evaluate_do(do_reading)

        return commands

    def _evaluate_ph(self, reading: SensorReading) -> list[ActuatorCommand]:
        self._ph_history.append(reading.value)
        self._ph_history = self._ph_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._ph_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return []  # not enough history yet to trust a correction

        avg = sum(self._ph_history) / len(self._ph_history)
        spread = max(self._ph_history) - min(self._ph_history)
        if spread > 0.5:
            # Readings disagree with each other too much — don't trust
            # any single average, flag and skip this cycle.
            self._raise_alert(
                "warning",
                f"{self.module_id}: pH readings inconsistent "
                f"(spread {spread:.2f}) — skipping correction this cycle",
            )
            return []

        if avg < self._targets["ph_target_min"]:
            return [self._dose_command("ph_up", reading.value,
                    f"pH {avg:.2f} below target range {self._targets['ph_target_min']}-"
                    f"{self._targets['ph_target_max']}, correcting upward")]
        if avg > self._targets["ph_target_max"]:
            return [self._dose_command("ph_down", reading.value,
                    f"pH {avg:.2f} above target range {self._targets['ph_target_min']}-"
                    f"{self._targets['ph_target_max']}, correcting downward")]
        return []

    def _evaluate_ec(self, reading: SensorReading) -> list[ActuatorCommand]:
        self._ec_history.append(reading.value)
        self._ec_history = self._ec_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._ec_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return []

        avg = sum(self._ec_history) / len(self._ec_history)
        if avg < self._targets["ec_target_min"]:
            return [self._dose_command("nutrient_concentrate", reading.value,
                    f"EC {avg:.0f} below target range {self._targets['ec_target_min']}-"
                    f"{self._targets['ec_target_max']}, correcting upward")]
        # No auto-correction for EC too high — diluting requires a water
        # change action, which should stay a human-approved/manual step
        # in v0.1 rather than an automated dump of fresh water.
        return []

    def _evaluate_do(self, reading: SensorReading) -> None:
        """Alert-only — no actuator command exists to raise DO beyond
        the aerator, which is already always running regardless of what
        this decides (safe_default_state 'on', never touched by control
        logic). The value here is early/confident warning, same
        "consistent readings before acting" discipline as pH/EC."""
        self._do_history.append(reading.value)
        self._do_history = self._do_history[-self.MIN_CONSISTENT_READINGS_FOR_DOSE:]

        if len(self._do_history) < self.MIN_CONSISTENT_READINGS_FOR_DOSE:
            return

        avg = sum(self._do_history) / len(self._do_history)
        spread = max(self._do_history) - min(self._do_history)
        if spread > DO_SPREAD_TOLERANCE_MGL:
            self._raise_alert(
                "warning",
                f"{self.module_id}: DO readings inconsistent (spread {spread:.2f} mg/L) "
                f"— not confident enough to assess oxygen risk this cycle",
            )
            return

        if avg < DO_CRITICAL_THRESHOLD_MGL:
            self._raise_alert(
                "critical",
                f"{self.module_id}: dissolved oxygen critically low ({avg:.2f} mg/L, "
                f"below {DO_CRITICAL_THRESHOLD_MGL} mg/L) — fish suffocation risk, "
                f"confirm aeration is actually running",
            )
        elif avg < DO_WARNING_THRESHOLD_MGL:
            self._raise_alert(
                "warning",
                f"{self.module_id}: dissolved oxygen low ({avg:.2f} mg/L, "
                f"below {DO_WARNING_THRESHOLD_MGL} mg/L) — worth checking aeration",
            )

    def _has_sensor_type(self, type_name: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM sensors WHERE cell_id = ? AND type = ? AND active = 1 LIMIT 1",
            (self.cell_id, type_name),
        ).fetchone()
        return row is not None

    def _dose_command(self, dose_type: str, current_value: float, rationale: str) -> ActuatorCommand:
        # Actuator ID lookup would come from the actuators table in a
        # real implementation, keyed by cell_id + dose_type.
        actuator_id = self._actuator_id_for(dose_type)
        logger.info(
            "%s: proposing dose %s (current reading %.2f) — %s",
            self.module_id, dose_type, current_value, rationale,
        )
        # Log the dosing decision itself, with WHY — this is the
        # concrete answer to "how much of a nutrient and why," not just
        # a log line. amount_ml is left null: the Pi doesn't know the
        # exact volume until real flow-metering hardware exists, only
        # the MCU's pulse duration does — see dosing_events schema note.
        self.db.execute(
            "INSERT INTO dosing_events (cell_id, dose_type, reading_before, rationale, triggered_by) "
            "VALUES (?, ?, ?, ?, 'auto_control')",
            (self.cell_id, dose_type, current_value, rationale),
        )
        self.db.commit()
        return ActuatorCommand(
            actuator_id=actuator_id,
            action="pulse",
            duration_seconds=None,  # duration resolved by dosing_limits
            triggered_by=TriggerSource.AUTO_CONTROL,
        )

    def _actuator_id_for(self, dose_type: str) -> int:
        cur = self.db.execute(
            "SELECT id FROM actuators WHERE cell_id = ? AND type = 'dosing_pump' "
            "AND name LIKE ? LIMIT 1",
            (self.cell_id, f"%{dose_type}%"),
        )
        row = cur.fetchone()
        return row[0] if row else -1

    def _latest_of_type(self, readings: list[SensorReading], type_name: str):
        matches = [
            r for r in readings
            if self._type_by_sensor.get(r.sensor_id) == type_name
        ]
        if not matches:
            return None
        return max(matches, key=lambda r: r.timestamp)

    def _safety_fallback_commands(self) -> list[ActuatorCommand]:
        """All sensors stale/invalid: freeze dosing, keep circulation
        and aeration running via their independent safety-MCU defaults
        (those actuators aren't touched here at all — they stay on
        because their safe_default_state is 'on', enforced at the MCU,
        not by this module deciding anything)."""
        return super()._safety_fallback_commands()

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id=self.module_id,
            display_name="Aquaponics Cell Control",
            purpose=(
                "Monitors pH and EC in one aquaponics cell and issues dosing "
                "corrections to keep both within target range, using multiple "
                "consistent readings before acting and hard dosing limits "
                "enforced downstream by the safety MCU. Also monitors dissolved "
                "oxygen (DO), alert-only, if a DO sensor is configured for this cell."
            ),
            data_produced=[
                "pH reading history", "EC reading history", "DO reading history (if configured)",
                "dosing event log (what was dosed, when, why)",
            ],
            actions_possible=[
                "pulse the pH-up dosing pump",
                "pulse the pH-down dosing pump",
                "pulse the nutrient concentrate dosing pump",
                "before alerting on a stale/missing sensor reading: retry via a forced "
                "immediate reread, then a healthy redundant sensor of the same type if one "
                "exists, over up to MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT consecutive cycles",
                "raise a warning/critical alert on low dissolved oxygen — no automated "
                "correction exists beyond the aerator, which is already always running",
            ],
            limits_and_safety=(
                f"Targets: pH {self.ph_target_min}-{self.ph_target_max}, "
                f"EC {self.ec_target_min}-{self.ec_target_max}. Requires "
                f"{self.MIN_CONSISTENT_READINGS_FOR_DOSE} consistent readings "
                "before dosing. Never auto-dilutes high EC (requires manual "
                "water change). Freezes dosing entirely if sensors are stale "
                "or missing, rather than guessing — the recovery ladder "
                "(contracts.MiaHomesteadModule) only changes how fast a GOOD "
                "reading gets produced before this logic runs; it never loosens "
                "what counts as safe to dose on, and dosing stays frozen for the "
                "entire retry window exactly as if no retry existed at all. "
                f"DO: warns below {DO_WARNING_THRESHOLD_MGL} mg/L, critical below "
                f"{DO_CRITICAL_THRESHOLD_MGL} mg/L — but ONLY if a DO sensor is actually "
                "registered for this cell; DO is optional hardware and a cell without "
                "one stays completely silent rather than alerting on hardware that was "
                "never installed."
            ),
            example_questions=[
                "How's the pH in Cell A?", "Has it been dosing much lately?",
                "Why didn't it correct the EC this morning?", "What's the dissolved oxygen at?",
            ],
            verification_evidence=[
                "scenarios.py::scenario_ph_crash_response — confirmed dosing triggers after "
                "3 consistent readings, closed-loop physics shows pH recovering from the correction",
                "scenarios.py::scenario_inconsistent_readings — confirmed dosing withheld when "
                "readings disagree beyond tolerance",
                "scenarios.py::scenario_stale_sensor_freeze — confirmed dosing freezes when a "
                "sensor is missing/stale",
                "Live manual test 2026-08-26: confirmed target_overrides changes the live control "
                "target with zero restart (cell._current_targets() picked up an experiment change "
                "immediately)",
                "scenarios.py::scenario_sensor_recovery_ladder_recovers — confirmed a forced "
                "immediate reread recovers a stale-but-still-alive sensor with zero alert raised",
                "scenarios.py::scenario_sensor_recovery_exhausted_escalates — confirmed no alert "
                "fires during the retry window, the same alert fires once retries genuinely "
                "exhaust, and dosing stays frozen throughout (0 doses issued) either way",
                "Honest gap: the redundant-sensor-substitution step is implemented but genuinely "
                "untested — confirmed against the real dev DB that no cell currently configures "
                "two sensors of the same type (SELECT cell_id, type, count(*) FROM sensors GROUP "
                "BY cell_id, type HAVING count(*) > 1 returns zero rows), so this path has never "
                "actually executed against real data.",
                "scenarios.py::scenario_do_no_sensor_silent — confirmed a cell with no DO sensor "
                "configured raises zero DO-related alerts, ever (optional hardware, not noise)",
                "scenarios.py::scenario_do_critical_alert — confirmed a critically low DO reading "
                "(2.0 mg/L) raises a real critical alert citing the actual reading, once a DO "
                "sensor is configured",
                "scenarios.py::scenario_do_healthy_no_alert — confirmed a healthy DO reading "
                "(7.0 mg/L) raises nothing",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="Atlas Scientific pH kit (KIT-101P or equivalent — circuit + probe)",
                category="sensor", quantity=1,
                purpose="pH monitoring for dosing decisions", est_unit_cost=175.0,
                notes="Do not substitute cheap pH probes — drift within weeks feeds bad data into dosing logic. "
                      "Priced as full starter kit; circuit alone is ~$46-51 if you already have a compatible probe. "
                      "See docs/HARDWARE_BOM_CURRENT.md.",
            ),
            HardwareRequirement(
                item="Atlas Scientific EC kit (EC-KIT-1.0 or equivalent — circuit + probe)",
                category="sensor", quantity=1,
                purpose="EC monitoring for nutrient dosing decisions", est_unit_cost=230.0,
                notes="Circuit alone is ~$68-86 if you already have a compatible probe. See docs/HARDWARE_BOM_CURRENT.md.",
            ),
            HardwareRequirement(
                item="Peristaltic dosing pump", category="actuator",
                quantity=3, purpose="pH-up, pH-down, and nutrient concentrate dosing",
                est_unit_cost=12.0,
                notes="One per chemical — never share a pump line between chemicals. "
                      "~$10-15 for a basic 12V DC unit (INTLLAB/Kamoer NKP class). See docs/HARDWARE_BOM_CURRENT.md.",
            ),
            HardwareRequirement(
                item="DS18B20 waterproof temp probe", category="sensor",
                quantity=1, purpose="water temperature monitoring", est_unit_cost=8.0,
            ),
            HardwareRequirement(
                item="Atlas Scientific Dissolved Oxygen kit (circuit + probe)", category="sensor",
                quantity=1, purpose="dissolved oxygen monitoring — DO crashes are the leading real "
                "cause of catastrophic fish loss", est_unit_cost=354.99,
                notes="Confirmed live-fetch 2026-08-31, atlas-scientific.com. Optional at small "
                      "scale (low stocking density, continuous aeration substitutes adequately) — "
                      "recommended at full-scale real stocking density. See "
                      "docs/HARDWARE_BOM_FULL_TIERS.md. A cell with no DO sensor installed stays "
                      "completely silent about it, by design — see limits_and_safety above.",
            ),
            HardwareRequirement(
                item="Submersible aquarium air pump + airstone", category="actuator",
                quantity=1, purpose="aeration — the highest-priority load per SAFETY_SPEC.md's "
                "power-loss ordering; fish suffocate faster than anything else fails",
                est_unit_cost=10.0,
                notes="Safe default is always ON — never wired through a dosing-style pulse relay.",
            ),
            HardwareRequirement(
                item="Submersible circulation pump", category="actuator",
                quantity=1, purpose="moves water to the grow bed and biofilter — second priority "
                "after aeration per SAFETY_SPEC.md",
                est_unit_cost=15.0,
            ),
        ]
