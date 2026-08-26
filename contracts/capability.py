"""
MIA Homestead — Capability Declaration
v0.1

The core mechanism for this requirement: "the assistant should never need
to be taught what the system can do after the fact." Every module and
service — control modules, inventory, maintenance, notifications, and
anything added later — MUST implement `describe_capabilities()`. This
isn't a convention, it's enforced by inheritance: a class that doesn't
implement it cannot be instantiated at all (Python raises TypeError on
an incomplete ABC). Adding a new module without describing it is a
startup crash, not a silent gap.

This makes the capability registry (core/capability_registry.py) a
source of truth that's guaranteed current — not a doc that drifts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Capability:
    """A structured self-description. Written once, per module, at the
    same time the module itself is written — not backfilled later."""

    module_id: str
    display_name: str
    purpose: str                                   # 1-2 sentences: what this does and why it exists
    data_produced: list[str] = field(default_factory=list)      # what it reads/generates
    actions_possible: list[str] = field(default_factory=list)   # what it can actually DO
    limits_and_safety: str = ""                     # constraints, failsafes, what it will NOT do
    example_questions: list[str] = field(default_factory=list)  # what a user might ask about it


@dataclass
class HardwareRequirement:
    """A physical thing this module/service needs to actually run.
    Declared at the same time the module is written — this is how the
    hardware shopping list stays accurate without ever reconstructing
    it retroactively from scattered notes."""

    item: str
    category: str                    # 'sensor','actuator','mcu','structural','power','other'
    quantity: int
    purpose: str                     # why THIS module needs it
    est_unit_cost: float = None
    notes: str = ""


class Describable(ABC):
    """Base for anything that should be visible to the assistant's
    self-knowledge AND to the running hardware needs list. Both control
    modules (MiaHomesteadModule) and standalone services (inventory,
    maintenance, notifications, device registry) implement this."""

    @abstractmethod
    def describe_capabilities(self) -> Capability:
        raise NotImplementedError(
            "Every module/service must implement describe_capabilities(). "
            "This is not optional — it's how the assistant learns what "
            "the system can do without anyone teaching it after the fact."
        )

    @abstractmethod
    def describe_hardware_requirements(self) -> list:
        """Return a list of HardwareRequirement, or [] if this module
        needs no physical hardware of its own (e.g. inventory, which is
        a pure software service). Returning [] is a valid, deliberate
        answer — skipping the method entirely is not, since that's
        exactly the 'go back and reconstruct the BOM later' problem
        this exists to prevent."""
        raise NotImplementedError(
            "Every module/service must implement describe_hardware_requirements() "
            "— even if it just returns []. This is how the hardware shopping "
            "list stays accurate without reconstructing it after the fact."
        )
