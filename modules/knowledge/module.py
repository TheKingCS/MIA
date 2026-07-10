"""
modules.knowledge.module
==========================

Placeholder for the Knowledge module — personal knowledge management
(offline reference material, wikis, manuals).
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class KnowledgeModule(ModuleBase):
    module_id = "knowledge"
    display_name = "Knowledge"
    description = "Offline reference material and personal knowledge base."
    icon = "\U0001F4DA"  # books

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
