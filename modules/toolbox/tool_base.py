"""
modules.toolbox.tool_base
============================

Defines ToolboxTool, the base for a "real tool" living inside Toolbox
— Calendar, and eventually Alarm/Stopwatch and Inventory per
docs/ROADMAP.md's v0.3 breakdown. Deliberately separate from
core.calculator_engine.CalculatorPlugin: a calculator is a pure
"give inputs, get an output" formula, while these tools are stateful
CRUD screens with their own data (see core/calendar_manager.py) that
doesn't fit the calculator shape.

Unlike CalculatorPlugin (any module can register one into the shared
CalculatorEngine — see core/application.py._register_calculators),
ToolboxTools are intrinsic, built-in Toolbox features, not something
other modules register from the outside. So there's no separate
registry/engine class here — modules/toolbox/module.py just
constructs its known list of tools directly, the same way
_register_calculators hardcodes the app's two built-in calculators.

Shaped like modules.module_base.ModuleBase on purpose (context passed
into __init__, abstract build_widget()) since tools need
self.context (e.g. self.context.calendar) the same way modules do —
unlike CalculatorPlugin, which needs no context at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.app_context import AppContext


class ToolboxTool(ABC):
    """
    Base for a single built-in Toolbox tool.

    Class attributes (override these in your subclass):
        tool_id       -- unique, stable, snake_case identifier (e.g. "calendar")
        display_name  -- human-readable name shown on its row (e.g. "Calendar")
        description   -- one-line description shown under the name
        icon          -- a short emoji/glyph placeholder

    build_widget() -- same lazy-construction contract as
        ModuleBase.get_widget()/CalculatorPlugin.build_widget(): cheap
        __init__, expensive work deferred until the tool is actually opened.
    """

    tool_id: str = "base"
    display_name: str = "Base Tool"
    description: str = ""
    icon: str = "\U0001F527"  # wrench

    def __init__(self, context: AppContext) -> None:
        self.context = context

    @abstractmethod
    def build_widget(self) -> Any:
        """Return a widget (e.g. a QWidget) presenting this tool."""
        raise NotImplementedError
