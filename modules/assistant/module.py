"""
modules.assistant.module
=========================

Placeholder for the Assistant module — the conversational / local-AI
interface. Deliberately NOT implemented in v0.1 per the project brief
("Do NOT build AI yet"). This stub exists so the module appears in the
main menu and the plug-in point is established ahead of time.
"""

from __future__ import annotations

from gui.widgets.placeholder_widget import build_placeholder_widget
from modules.module_base import ModuleBase


class AssistantModule(ModuleBase):
    module_id = "assistant"
    display_name = "Assistant"
    description = "Conversational assistant and local AI (not yet implemented)."
    icon = "\U0001F5E8"  # speech balloon

    def get_widget(self):
        return build_placeholder_widget(self.display_name, self.description, self.icon)
