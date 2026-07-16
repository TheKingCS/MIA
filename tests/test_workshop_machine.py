"""
tests.test_workshop_machine
==============================

Unit tests for core.workshop_machine — same shape as
tests/test_calculator_engine.py, since WorkshopMachineRegistry is
deliberately modeled on CalculatorEngine's registry pattern (see that
module's docstring for why). LaserEngraverMachine's own tests confirm
it behaves as a real, honest stub — reports "offline" rather than
raising on get_status(), but raises WorkshopMachineError on every
method that would need a real device connection.
"""

from __future__ import annotations

import pytest

from core.app_context import AppContext
from core.event_bus import EventBus
from core.workshop_machine import (
    LaserEngraverMachine,
    MachineJobHandle,
    MachineStatusReport,
    WorkshopMachine,
    WorkshopMachineError,
    WorkshopMachineRegistry,
)


class _FakeMachine(WorkshopMachine):
    def __init__(self, machine_id: str, display_name: str) -> None:
        self.machine_id = machine_id
        self.display_name = display_name
        self.description = f"{display_name} description"

    def get_status(self) -> MachineStatusReport:
        return MachineStatusReport(state="idle")

    def send_job(self, job_data: dict) -> MachineJobHandle:
        return MachineJobHandle(job_id="job-1", machine_id=self.machine_id)

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass


def _make_registry() -> WorkshopMachineRegistry:
    context = AppContext(config=None, events=EventBus())
    return WorkshopMachineRegistry(context)


# ----------------------------------------------------------------------
# WorkshopMachineRegistry
# ----------------------------------------------------------------------

def test_register_and_get():
    registry = _make_registry()
    machine = _FakeMachine("cnc", "CNC Router")
    registry.register(machine)

    assert registry.get("cnc") is machine


def test_get_unknown_returns_none():
    registry = _make_registry()
    assert registry.get("does_not_exist") is None


def test_duplicate_machine_id_raises():
    registry = _make_registry()
    registry.register(_FakeMachine("dup", "First"))
    with pytest.raises(ValueError):
        registry.register(_FakeMachine("dup", "Second"))


def test_all_machines_returns_every_registered_machine():
    registry = _make_registry()
    registry.register(_FakeMachine("cnc", "CNC Router"))
    registry.register(_FakeMachine("printer_3d", "3D Printer"))

    ids = {m.machine_id for m in registry.all_machines()}
    assert ids == {"cnc", "printer_3d"}


def test_all_machines_empty_registry_returns_empty_list():
    assert _make_registry().all_machines() == []


# ----------------------------------------------------------------------
# LaserEngraverMachine — a real, honest stub
# ----------------------------------------------------------------------

def test_laser_engraver_reports_offline_status():
    machine = LaserEngraverMachine()
    status = machine.get_status()
    assert status.state == "offline"
    assert "no real driver" in status.message.lower()


def test_laser_engraver_send_job_raises():
    machine = LaserEngraverMachine()
    with pytest.raises(WorkshopMachineError):
        machine.send_job({})


def test_laser_engraver_pause_raises():
    with pytest.raises(WorkshopMachineError):
        LaserEngraverMachine().pause()


def test_laser_engraver_stop_raises():
    with pytest.raises(WorkshopMachineError):
        LaserEngraverMachine().stop()


def test_laser_engraver_has_expected_identity():
    machine = LaserEngraverMachine()
    assert machine.machine_id == "laser_engraver"
    assert machine.display_name == "Laser Engraver"
