"""
core.calculator_engine
=========================

CalculatorEngine: a pluggable formula registry with one shared
browsing UI (modules/toolbox/module.py), per docs/ROADMAP.md's "Shared
core services" table. The goal: every future calculator-shaped tool
(unit converter, Ohm's Law, wire gauge, antenna calculator, fuel
estimates, coordinate conversion, ...) is a small plugin registered
here, not a brand-new top-level module with its own bespoke screen —
this is what keeps the module count manageable as the feature list
grows, per docs/ARCHITECTURE.md's reasoning for shared services.

Modeled directly on core.module_manager/modules.module_base —
CalculatorPlugin is the "ModuleBase" of this smaller system:
build_widget() is the same lazy-construction contract as
ModuleBase.get_widget(), just one level deeper than a full module.
Any module can register its own calculator via
self.context.calculators.register(...) in on_load(); general-purpose
calculators with no obvious module home (Unit Converter, Ohm's Law)
are registered centrally in core/application.py instead.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CalculatorPlugin(ABC):
    """
    Base for a single calculator. Subclasses set the class attributes
    below and implement build_widget() — same lazy-construction
    contract as modules.module_base.ModuleBase.get_widget(): cheap
    __init__, expensive work deferred until the widget is actually
    shown (called the first time a user opens this calculator, not at
    registration time).
    """

    calculator_id: str = "base"
    display_name: str = "Base Calculator"
    category: str = "General"
    description: str = ""

    @abstractmethod
    def build_widget(self) -> Any:
        """Return a widget (e.g. a QWidget) presenting this calculator's inputs/outputs."""
        raise NotImplementedError


class CalculatorEngine:
    """Holds registered CalculatorPlugin instances, keyed by calculator_id."""

    def __init__(self) -> None:
        self._calculators: dict[str, CalculatorPlugin] = {}

    def register(self, calculator: CalculatorPlugin) -> None:
        """
        Register a calculator. Raises ValueError on a duplicate
        calculator_id — unlike module discovery (which scans untrusted
        filesystem content and must degrade gracefully), calculator
        registration is deterministic code running at app-init time, so
        a collision is a straightforward programming mistake worth
        failing fast on rather than silently keeping the first one.
        """
        if calculator.calculator_id in self._calculators:
            raise ValueError(f"Duplicate calculator_id: '{calculator.calculator_id}'")
        self._calculators[calculator.calculator_id] = calculator

    def get(self, calculator_id: str) -> CalculatorPlugin | None:
        return self._calculators.get(calculator_id)

    def all(self) -> list[CalculatorPlugin]:
        """All registered calculators, sorted by display name."""
        return sorted(self._calculators.values(), key=lambda c: c.display_name)

    def by_category(self) -> dict[str, list[CalculatorPlugin]]:
        """All registered calculators grouped by category, each list sorted by display name."""
        grouped: dict[str, list[CalculatorPlugin]] = {}
        for calculator in self.all():
            grouped.setdefault(calculator.category, []).append(calculator)
        return grouped
