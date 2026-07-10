"""
modules.maps.module
=====================

Placeholder for the Maps module — offline maps and navigation data.
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class MapsModule(ModuleBase):
    module_id = "maps"
    display_name = "Maps"
    description = "Offline maps and navigation."
    icon = "\U0001F5FA"  # world map

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
