"""
gui.widgets.module_button
==========================

A single button representing one module on the main menu grid.

Pulled out as its own widget (rather than inlined in main_window.py) so
its appearance and behavior can evolve — e.g. showing a live status
badge, or a different look for disabled/unavailable modules — without
touching MainWindow's layout code.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton

from modules.module_base import ModuleBase


class ModuleButton(QPushButton):
    """A clickable button representing a module on the main menu."""

    activated = Signal(str)  # emits the module_id when clicked

    def __init__(self, module: ModuleBase) -> None:
        label = f"{module.icon}   {module.display_name}"
        super().__init__(label)
        self.setObjectName("ModuleButton")
        self.setToolTip(module.description or module.display_name)
        self.setMinimumHeight(72)
        self._module_id = module.module_id
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        self.activated.emit(self._module_id)
