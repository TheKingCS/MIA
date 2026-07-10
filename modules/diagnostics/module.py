"""
modules.diagnostics.module
============================

Placeholder for the Diagnostics module — system health, logs viewer,
and hardware status. Long-term, this is likely the first module to gain
real functionality (e.g. reading logs/mia.log) since it needs no
external dependencies.
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class DiagnosticsModule(ModuleBase):
    module_id = "diagnostics"
    display_name = "Diagnostics"
    description = "System health, logs, and hardware status."
    icon = "\U0001FA7A"  # stethoscope

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
