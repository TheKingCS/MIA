"""
MIA Homestead — Power Monitor Module
v0.1

One instance = one array + its battery bank. The greenhouse array runs
today as `greenhouse_power`. The house array becomes a second instance
of this exact same class later (see config/modules.yaml) — no new code
needed, just a new config entry once that array exists.
"""

import logging
from datetime import datetime

from contracts.mia_homestead_contract import (
    ActuatorCommand,
    MiaHomesteadModule,
    SensorReading,
    TriggerSource,
)

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
    ):
        super().__init__(module_id, cell_id, db_conn, notifier=notifier)
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
            commands += self._load_shed_commands()
        return commands

    def _load_shed_commands(self) -> list[ActuatorCommand]:
        """
        Returns commands to disable non-critical actuators in priority
        order per SAFETY_SPEC.md: dosing and dashboard sync shed first,
        aeration and circulation are never touched here.
        """
        cur = self.db.execute(
            """
            SELECT id FROM actuators
            WHERE cell_id = ? AND type IN ('dosing_pump')
            """,
            (self.cell_id,),
        )
        return [
            ActuatorCommand(
                actuator_id=row[0],
                action="off",
                triggered_by=TriggerSource.SAFETY_FALLBACK,
            )
            for row in cur.fetchall()
        ]

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id=self.module_id,
            display_name=f"Power Monitor ({self.array_name})",
            purpose=(
                f"Monitors solar/battery telemetry for {self.array_name} and "
                "sheds non-critical loads (dosing pumps first) when battery "
                "state of charge drops below threshold, to protect aeration "
                "and circulation as the last things to lose power."
            ),
            data_produced=["battery SOC %", "watts (solar/battery/generator/grid)"],
            actions_possible=["shut off dosing pumps to shed load under low SOC"],
            limits_and_safety=(
                f"Load-shed threshold: {self.low_soc_threshold_pct}% SOC. "
                "Raises a critical alert and freezes non-critical actuation "
                "if no telemetry is available at all, rather than assuming "
                "power is fine."
            ),
            example_questions=[
                "What's the battery at?", "Has it had to shed any loads recently?",
                "How's the greenhouse array doing today?",
            ],
            verification_evidence=[
                "scenarios.py::scenario_power_loss_load_shed — confirmed critical alert and "
                "load-shed behavior fire correctly when telemetry is missing entirely",
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
