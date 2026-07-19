"""
gui.dashboard_customize_dialog
=================================

Lets the user enable/disable and reorder Home dashboard widgets —
2026-07-15, the UI half of core/dashboard_widgets.py's "framework
first" build (see that module's docstring for the full reasoning).
Deliberately a checkable list + up/down move buttons, not drag-and-drop
— matches this project's own "start boring" discipline elsewhere
(core/startup_briefing.py's docstring); revisit if plain reordering
ever feels insufficient.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from core.app_context import AppContext
from core.dashboard_widgets import WidgetDescriptor


class DashboardCustomizeDialog(QDialog):
    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Customize Dashboard")
        self.resize(360, 420)

        layout = QVBoxLayout(self)

        title = QLabel("Customize Dashboard")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Check the widgets you want to see, and use the arrows to reorder them.")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)
        self._populate()

        move_row = QHBoxLayout()
        up_button = QPushButton("↑ Move Up")
        up_button.clicked.connect(self._on_move_up)
        move_row.addWidget(up_button)
        down_button = QPushButton("↓ Move Down")
        down_button.clicked.connect(self._on_move_down)
        move_row.addWidget(down_button)
        layout.addLayout(move_row)

        done_button = QPushButton("Done")
        done_button.setObjectName("ModuleButton")
        done_button.clicked.connect(self._on_done)
        layout.addWidget(done_button)

    def _populate(self) -> None:
        self._list.clear()
        registry = self.context.dashboard_widgets
        enabled_descriptors = registry.enabled_widgets_in_order()
        enabled_ids = {d.widget_id for d in enabled_descriptors}
        for descriptor in enabled_descriptors:
            self._add_item(descriptor, checked=True)
        for descriptor in registry.all_widgets():
            if descriptor.widget_id not in enabled_ids:
                self._add_item(descriptor, checked=False)

    def _add_item(self, descriptor: WidgetDescriptor, checked: bool) -> None:
        item = QListWidgetItem(f"{descriptor.icon}  {descriptor.display_name}")
        item.setData(Qt.ItemDataRole.UserRole, descriptor.widget_id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._list.addItem(item)

    def _on_move_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row - 1, item)
        self._list.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row + 1, item)
        self._list.setCurrentRow(row + 1)

    def _on_done(self) -> None:
        registry = self.context.dashboard_widgets
        order: list[str] = []
        for index in range(self._list.count()):
            item = self._list.item(index)
            widget_id = item.data(Qt.ItemDataRole.UserRole)
            order.append(widget_id)
            enabled = item.checkState() == Qt.CheckState.Checked
            if registry.is_enabled(widget_id) != enabled:
                registry.set_enabled(widget_id, enabled)
        registry.set_order(order)
        self.accept()
