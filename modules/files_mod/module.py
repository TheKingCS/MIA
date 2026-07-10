"""
modules.files_mod.module
==========================

Placeholder for the Files module — browsing and managing data/ and
other on-disk resources relevant to the field system.
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class FilesModule(ModuleBase):
    module_id = "files"
    display_name = "Files"
    description = "Browse and manage local files and data."
    icon = "\U0001F5C2"  # card index dividers

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
