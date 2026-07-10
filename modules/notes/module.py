"""
modules.notes.module
======================

Placeholder for the Notes module — quick text notes and logs.
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class NotesModule(ModuleBase):
    module_id = "notes"
    display_name = "Notes"
    description = "Quick notes and field logs."
    icon = "\U0001F4DD"  # memo

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
