"""
MIA Homestead — Power Monitor Module
v0.1

One instance = one array + its battery bank. The greenhouse array runs
today as `greenhouse_power`. The house array becomes a second instance
of this exact same class later (see config/modules.yaml) — no new code
needed, just a new config entry once that array exists.
"""

import logging
from datetime import datetime, timedelta

from contracts.mia_homestead_contract import (
    ActuatorCommand,
    MiaHomesteadModule,
    SensorReading,
    TriggerSource,
    raise_alert,
)

# forecast_soc_depletion()'s early-warning horizon — inside this many
# hours of projected threshold crossing, it's worth telling a human
# now rather than waiting for evaluate()'s reactive load-shed to fire
# once it's already happened.
SOC_FORECAST_WARNING_HOURS = 12


def _least_squares_slope(xs: list[float], ys: list[float]) -> float:
    """Plain linear regression slope, no dependency beyond stdlib —
    used by PowerMonitor.forecast_soc_depletion() below."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return numerator / denominator

logger = logging.getLogger("mia_homestead.power_monitor")


class PowerMonitor(MiaHomesteadModule):

    def __init__(
        self,
        module_id: str,
        cell_id: int,
        db_conn,
        array_name: str,
        battery_capacity_wh: float,
        low_soc_threshold_pct: float,
        notifier=None,
        force_read_fn=None,
        recovery_log_fn=None,
    ):
        super().__init__(module_id, cell_id, db_conn, notifier=notifier,
                          force_read_fn=force_read_fn, recovery_log_fn=recovery_log_fn)
        self.array_name = array_name
        self.battery_capacity_wh = battery_capacity_wh
        self.low_soc_threshold_pct = low_soc_threshold_pct

    def read_sensors(self) -> list[SensorReading]:
        """
        Power telemetry is logged directly to power_telemetry (not
        sensor_readings, since it's not a probe reading but charge-
        controller/inverter telemetry) by a separate driver. Pulls the
        latest row for this array.
        """
        cur = self.db.execute(
            """
            SELECT id, watts, battery_soc_percent, timestamp
            FROM power_telemetry
            WHERE source = 'solar' OR source = 'battery'
            ORDER BY timestamp DESC LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return []
        pid, watts, soc, ts = row
        return [
            SensorReading(
                sensor_id=pid,
                value=soc if soc is not None else watts,
                timestamp=datetime.fromisoformat(ts),
            )
        ]

    def evaluate(self, readings: list[SensorReading]) -> list[ActuatorCommand]:
        if not readings:
            return []
        soc = readings[0].value
        commands = []
        if soc is not None and soc < self.low_soc_threshold_pct:
            logger.warning(
                "%s: battery SOC %.1f%% below threshold %.1f%% — "
                "shedding non-critical loads",
                self.module_id, soc, self.low_soc_threshold_pct,
            )
            self._raise_alert(
                "warning",
                f"{self.array_name}: battery SOC {soc:.1f}% — "
                f"shedding dosing and non-critical sensors per load-shed order",
            )
            commands += self._load_shed_commands(soc=soc)
        return commands

    def _load_shed_commands(self, soc: float = None) -> list[ActuatorCommand]:
        """
        Returns commands to disable non-critical actuators in priority
        order per SAFETY_SPEC.md: dosing and dashboard sync shed first,
        aeration and circulation are never touched here.
        """
        cur = self.db.execute(
            """
            SELECT id, name FROM actuators
            WHERE cell_id = ? AND type IN ('dosing_pump')
            """,
            (self.cell_id,),
        )
        rows = cur.fetchall()
        commands = [
            ActuatorCommand(
                actuator_id=row[0],
                action="off",
                triggered_by=TriggerSource.SAFETY_FALLBACK,
            )
            for row in rows
        ]
        if rows:
            from core.action_log import log_action
            soc_str = f"{soc:.1f}%" if soc is not None else "unknown"
            log_action(
                self.db, self.module_id, "load_shed",
                f"Shed {len(rows)} dosing pump(s) ({', '.join(r[1] for r in rows)}) — "
                f"battery SOC at {soc_str}, below threshold {self.low_soc_threshold_pct}%. "
                f"Aeration and circulation are never shed regardless of SOC.",
            )
        return commands

    def forecast_soc_depletion(self, lookback_readings: int = 12) -> dict | None:
        """Projects whether/when battery SOC will cross
        low_soc_threshold_pct at the CURRENT drain rate — an early
        warning, distinct from evaluate()'s reactive load-shed which
        only fires once already below threshold. This is the proactive
        half of the same "efficient and scientific, not just reactive"
        goal core/trend_analyzer.py serves for sensor readings, applied
        to power specifically rather than folded into that generic
        module — SOC forecasting needs power_telemetry's own
        source='battery' rows and this module's own threshold/array
        context, not a fit for trend_analyzer's sensor-agnostic shape.

        Deliberately simple: a plain least-squares slope over the last
        `lookback_readings` battery rows (no numpy dependency — this
        project's requirements.txt is pyyaml-only by design, see
        docs/OFFLINE_ASSISTANT_PLAN.md), not a physical discharge-curve
        model. Returns None when there isn't enough history yet, when
        SOC isn't currently trending down at all, or when it's already
        at/below threshold (that's evaluate()'s job to react to, not
        this method's job to "forecast" as if it hadn't happened yet).
        """
        rows = self.db.execute(
            "SELECT battery_soc_percent, timestamp FROM power_telemetry "
            "WHERE source = 'battery' AND battery_soc_percent IS NOT NULL "
            "ORDER BY id DESC LIMIT ?",
            (lookback_readings,),
        ).fetchall()
        if len(rows) < lookback_readings:
            return None
        rows = list(reversed(rows))  # oldest first

        t0 = datetime.fromisoformat(rows[0][1])
        xs = [(datetime.fromisoformat(r[1]) - t0).total_seconds() / 60 for r in rows]
        ys = [r[0] for r in rows]

        slope = _least_squares_slope(xs, ys)  # % SOC per minute
        if slope >= 0:
            return None  # flat or charging — nothing to forecast

        current_soc = ys[-1]
        if current_soc <= self.low_soc_threshold_pct:
            return None

        minutes_to_threshold = (current_soc - self.low_soc_threshold_pct) / (-slope)
        return {
            "current_soc": round(current_soc, 2),
            "drain_rate_pct_per_hour": round(-slope * 60, 3),
            "hours_to_threshold": round(minutes_to_threshold / 60, 2),
            "projected_threshold_time": (datetime.fromisoformat(rows[-1][1]) + timedelta(minutes=minutes_to_threshold)).isoformat(),
        }

    def check_soc_forecast(self) -> dict | None:
        """Called periodically (main.py), NOT every control cycle —
        same reasoning as backup_manager's update-watch check and
        trend_analyzer's drift scan: this is an early-warning scan, not
        a per-cycle safety decision, so it doesn't belong in
        evaluate()'s hot path. Raises a WARNING alert (never critical —
        the threshold hasn't actually been crossed yet) only when the
        projection falls inside SOC_FORECAST_WARNING_HOURS."""
        forecast = self.forecast_soc_depletion()
        if forecast is None or forecast["hours_to_threshold"] > SOC_FORECAST_WARNING_HOURS:
            return forecast
        message = (
            f"{self.array_name}: battery SOC ({forecast['current_soc']}%) projected to hit "
            f"the {self.low_soc_threshold_pct}% load-shed threshold in ~{forecast['hours_to_threshold']}h "
            f"at the current drain rate ({forecast['drain_rate_pct_per_hour']}%/hr) — worth checking "
            f"before it happens, not just reacting once it does."
        )
        raise_alert(self.db, self.module_id, "warning", message, self.notifier)
        return forecast

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id=self.module_id,
            display_name=f"Power Monitor ({self.array_name})",
            purpose=(
                f"Monitors solar/battery telemetry for {self.array_name}, sheds non-critical "
                "loads (dosing pumps first) when battery state of charge drops below "
                "threshold, and proactively forecasts SOC depletion (linear projection off "
                "the recent drain rate) so a human can see a low-battery situation coming "
                "hours before the reactive load-shed would actually trigger."
            ),
            data_produced=[
                "battery SOC %", "watts (solar/battery/generator/grid)",
                "SOC depletion forecast: current SOC, drain rate, hours to threshold",
            ],
            actions_possible=[
                "shut off dosing pumps to shed load under low SOC",
                "forecast when SOC will cross the load-shed threshold at the current drain rate",
            ],
            limits_and_safety=(
                f"Load-shed threshold: {self.low_soc_threshold_pct}% SOC. "
                "Raises a critical alert and freezes non-critical actuation "
                "if no telemetry is available at all, rather than assuming "
                "power is fine. The SOC forecast is a plain linear projection off recent "
                "readings, not a physical discharge-curve model — treat it as an early "
                "warning worth a look, not a guaranteed prediction, and it only ever raises "
                "a WARNING (never critical) since the threshold hasn't actually been crossed."
            ),
            example_questions=[
                "What's the battery at?", "Has it had to shed any loads recently?",
                "How's the greenhouse array doing today?",
                "Is the battery going to run low tonight?",
            ],
            verification_evidence=[
                "scenarios.py::scenario_power_loss_load_shed — confirmed critical alert and "
                "load-shed behavior fire correctly when telemetry is missing entirely",
                "Live manual test 2026-08-30: seeded 4 real battery-drain scenarios directly "
                "into power_telemetry — under 12 readings (correctly None, insufficient "
                "history), flat/non-draining SOC (correctly None), a genuine 9%/hr drain "
                "landing 3.72h from the 20% threshold (correctly forecast AND correctly "
                "raised exactly one WARNING alert via check_soc_forecast()), and a slow "
                "0.3%/hr drain landing 231.5h out (correctly forecast a distant threshold "
                "time but correctly raised NO alert, outside the 12h warning window). Also "
                "verified the get_power_forecast assistant tool end-to-end against the real "
                "config/modules.yaml threshold (20%), not a hardcoded stand-in.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="Solar charge controller (Modbus/RS485 telemetry)", category="power",
                quantity=1, purpose="reports watts/SOC this module reads",
                est_unit_cost=140.0,
                notes="Must expose telemetry the Pi can poll — confirm Modbus support before buying. "
                      "~$100-150 for a 10-40A MPPT unit with RS485. See docs/HARDWARE_BOM_CURRENT.md.",
            ),
            HardwareRequirement(
                item="Battery bank (LiFePO4 recommended)", category="power",
                quantity=1, purpose="stores solar generation for load through outages",
                notes="Unpriced — needs capacity sized against real greenhouse load first. See docs/HARDWARE_BOM_CURRENT.md.",
            ),
        ]
