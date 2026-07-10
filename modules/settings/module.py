"""
modules.settings.module
=========================

Placeholder for the Settings module — editing config values (theme,
user name, module toggles) through the GUI instead of hand-editing
config/config.json.
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class SettingsModule(ModuleBase):
    module_id = "settings"
    display_name = "Settings"
    description = "Configure M.I.A. — theme, user info, module options."
    icon = "\u2699"  # gear

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
