"""
core.workshop_machine
========================

WorkshopMachine: the interface every controllable workshop-hardware
device (laser engraver, CNC, 3D printer, ...) implements, plus
WorkshopMachineRegistry holding whichever machines are actually
registered. This reconciles a real architecture question from MIA
Home's expanded-scope handoff doc (`docs/VISION.md`) — that doc
proposed a "MIAModule" interface (`get_status()`/`send_job()`/
`pause()`/`stop()`, plus `StatusReport`/`JobHandle`/`ModuleError` data
shapes, with a `LaserEngraverModule` stub) for exactly this, and asked
how it relates to this repo's own `ModuleBase`.

**Answer: it's a sibling concept, not a specialization or replacement
of `ModuleBase`, and deliberately renamed (`WorkshopMachine`, not
"MIAModule") to remove the naming collision entirely.**
`modules/module_base.py`'s `ModuleBase` answers "what discoverable app
screens exist" — one per top-level `modules/` folder, `get_widget()`-
driven, found via `core/module_manager.py`'s `pkgutil` scan.
`WorkshopMachine` answers a completely different question: "what
physical fabrication devices can I send a job to and poll status on."
Structurally, that's much closer to `core/calculator_engine.py`'s
`CalculatorPlugin` (many pluggable things, registered by id, one
shared control surface) than to `ModuleBase` — modeled directly on that
precedent (an `ABC` + a registry) rather than
`core/volume_manager.py`'s `VolumeBackend`-style `Protocol`, since
multiple machines can coexist here the way multiple calculators can,
unlike Volume/Power's single-global-resource shape.

`modules/workshop/module.py`'s own docstring already flags "3D
printer/CNC/laser... waits for that hardware/tooling to exist" — this
file is the `core/`-level scaffolding that decision was waiting on, not
a GUI build. **No control-tab UI is wired into that module in this
pass** — that stays a deliberate later step once real hardware exists
to verify against, same "don't build blind" discipline as 11.3b/11.6.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)


class WorkshopMachineError(RuntimeError):
    """Raised by a WorkshopMachine method that can't complete right now — no real driver yet, the device is offline, busy, or doesn't support the requested action."""


@dataclass
class MachineStatusReport:
    state: str  # "idle" | "running" | "paused" | "error" | "offline"
    message: str = ""
    progress_pct: Optional[float] = None


@dataclass
class MachineJobHandle:
    job_id: str
    machine_id: str


class WorkshopMachine(ABC):
    """
    Base for a single controllable workshop-hardware device. Subclasses
    set the class attributes below and implement the four methods —
    same lazy/cheap-`__init__` discipline as `ModuleBase`/
    `CalculatorPlugin`, though "cheap" here means "don't open a real
    device connection until a method is actually called," not "defer
    widget construction" — there's no widget at this layer at all.
    """

    machine_id: str = "base"
    display_name: str = "Base Machine"
    description: str = ""

    @abstractmethod
    def get_status(self) -> MachineStatusReport:
        """Current status. Must not raise even if the machine is offline/unreachable — report that as a state, not an exception."""
        raise NotImplementedError

    @abstractmethod
    def send_job(self, job_data: dict) -> MachineJobHandle:
        """Start a new job. Raises WorkshopMachineError if the machine can't accept one right now (busy, offline, not implemented)."""
        raise NotImplementedError

    @abstractmethod
    def pause(self) -> None:
        """Pause the current job. Raises WorkshopMachineError if there's nothing running or pausing isn't supported."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop the current job. Raises WorkshopMachineError if there's nothing running."""
        raise NotImplementedError


class WorkshopMachineRegistry:
    """Holds registered WorkshopMachine instances, keyed by machine_id
    (`AppContext.workshop_machines`). Same "core/ owns the registry,
    gui/ owns rendering once a control screen is actually built" split
    as `core/dashboard_widgets.py`."""

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._machines: dict[str, WorkshopMachine] = {}

    def register(self, machine: WorkshopMachine) -> None:
        """Raises ValueError on a duplicate machine_id — same fail-loud
        stance as CalculatorEngine.register(), since every registration
        here is this project's own trusted startup code, not
        third-party input that needs to degrade gracefully."""
        if machine.machine_id in self._machines:
            raise ValueError(f"Machine id '{machine.machine_id}' is already registered.")
        self._machines[machine.machine_id] = machine
        log.info("Registered workshop machine: %s", machine.machine_id)

    def all_machines(self) -> list[WorkshopMachine]:
        return list(self._machines.values())

    def get(self, machine_id: str) -> Optional[WorkshopMachine]:
        return self._machines.get(machine_id)


class LaserEngraverMachine(WorkshopMachine):
    """
    Stub only — no real hardware driver exists yet. Mirrors the shape
    the original handoff doc's `LaserEngraverModule` example described,
    renamed to fit this file's `WorkshopMachine` contract. Registered by
    default in `core/application.py` so the registry/pattern has
    something real to demonstrate end-to-end (`all_machines()` isn't
    empty, `get_status()` returns a real report), without pretending to
    control real hardware — every method that would need a real
    connection either reports "offline" or raises, same "flag as stub,
    don't fake it" discipline as 11.3b/11.6.
    """

    machine_id = "laser_engraver"
    display_name = "Laser Engraver"
    description = "Stub only — no real driver implemented yet."

    def get_status(self) -> MachineStatusReport:
        return MachineStatusReport(state="offline", message="No real driver implemented yet.")

    def send_job(self, job_data: dict) -> MachineJobHandle:
        raise WorkshopMachineError("Laser engraver control isn't implemented yet — this is a stub.")

    def pause(self) -> None:
        raise WorkshopMachineError("Laser engraver control isn't implemented yet — this is a stub.")

    def stop(self) -> None:
        raise WorkshopMachineError("Laser engraver control isn't implemented yet — this is a stub.")
