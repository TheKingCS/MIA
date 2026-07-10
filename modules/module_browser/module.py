"""
modules.module_browser.module
===============================

Backs the "Modules" button on the main menu.

Unlike the other v0.1 stubs, this one is genuinely functional now rather
than a placeholder: it lists every module the ModuleManager discovered,
along with its id, version, and description. This is useful immediately
during development — it doubles as a live sanity check that a new
module you just dropped into modules/ was actually picked up — and it's
the natural home for future module management features (enable/disable,
reload, per-module settings).

Note: this module intentionally reaches into
self.context via the ModuleBase contract only; it does NOT import
core.module_manager.ModuleManager itself. Instead, MainWindow (gui/main_window.py)
already holds the ModuleManager and could pass a read-only listing in via
AppContext in a future revision if this module needs live data beyond
what's available at get_widget() time. For v0.1, the simplest thing that
works is for the module to be handed the list of module metadata when
get_widget() is called, via the app context's config or a small
attribute set at construction time by whoever wires modules together.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from modules.module_base import ModuleBase


class ModuleBrowserModule(ModuleBase):
    module_id = "module_browser"
    display_name = "Modules"
    description = "View all modules currently loaded into M.I.A."
    icon = "\U0001F9E9"  # puzzle piece

    def __init__(self, context) -> None:
        super().__init__(context)
        # Populated by MainWindow right after discovery, so this module
        # can list its siblings without importing ModuleManager directly
        # (which would create a modules -> core -> modules import cycle
        # risk). See gui/main_window.py's _wire_module_browser().
        self.known_modules: list[ModuleBase] = []

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel("Loaded Modules")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        list_layout.setSpacing(8)

        modules_to_show = self.known_modules or [self]
        for module in modules_to_show:
            list_layout.addWidget(self._build_row(module))

        scroll.setWidget(list_container)
        outer.addWidget(scroll)
        return widget

    @staticmethod
    def _build_row(module: ModuleBase) -> QFrame:
        row = QFrame()
        row.setObjectName("CharacterPanel")  # reuse the dashed-panel style
        layout = QVBoxLayout(row)

        title = QLabel(f"{module.icon}  {module.display_name}  (v{module.version})")
        title.setStyleSheet("font-weight: 600;")
        subtitle = QLabel(f"id: {module.module_id} — {module.description}")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        return row
