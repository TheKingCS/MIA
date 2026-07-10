"""
modules.music.module
======================

Placeholder for the Music module — local audio playback.
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class MusicModule(ModuleBase):
    module_id = "music"
    display_name = "Music"
    description = "Local audio library and playback."
    icon = "\U0001F3B5"  # musical note

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
