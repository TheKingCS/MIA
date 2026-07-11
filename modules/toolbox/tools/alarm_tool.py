"""
modules.toolbox.tools.alarm_tool
===================================

Alarm — a ToolboxTool (modules/toolbox/tool_base.py), part of
milestone 3.3 in docs/ROADMAP.md (paired with stopwatch_tool.py). A
flat list of alarms, each with an inline checkbox to enable/disable it
without opening a dialog, plus Add/Edit/Delete. Backed by
core.alarm_manager.AlarmManager for persistence and for actually
firing — this widget only manages alarm *data*; the firing itself
happens on MIAApplication's periodic timer (core/application.py) so it
works whether or not this screen is open.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.alarm_manager import Alarm
from gui.add_edit_alarm_dialog import AddEditAlarmDialog
from modules.toolbox.tool_base import ToolboxTool

_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def format_alarm_row(alarm: Alarm) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_alarm_manager.py)."""
    if not alarm.days:
        repeat = "Once"
    elif len(alarm.days) == 7:
        repeat = "Every day"
    else:
        repeat = ", ".join(_DAY_NAMES[d] for d in sorted(alarm.days))
    label = alarm.label or "Alarm"
    return f"{alarm.time}  —  {label}  [{repeat}]"


class AlarmTool(ToolboxTool):
    tool_id = "alarm"
    display_name = "Alarm"
    description = "Set alarms for a specific time, with optional repeat days."
    icon = "⏰"  # alarm clock

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list: Optional[QListWidget] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        hint = QLabel("Check an alarm to enable it, uncheck to disable.")
        hint.setObjectName("SubtitleLabel")
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Alarm")
        add_button.clicked.connect(self._on_add)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        self._list.blockSignals(True)  # rebuilding shouldn't re-trigger _on_item_changed
        self._list.clear()
        for alarm in self.context.alarms.all_alarms():
            item = QListWidgetItem(format_alarm_row(alarm))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if alarm.enabled else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, alarm.alarm_id)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def _selected_alarm_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        alarm_id = item.data(Qt.ItemDataRole.UserRole)
        enabled = item.checkState() == Qt.CheckState.Checked
        self.context.alarms.update_alarm(alarm_id, enabled=enabled)

    def _on_add(self) -> None:
        dialog = AddEditAlarmDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.alarms.add_alarm(
            label=dialog.entered_label,
            time=dialog.entered_time,
            days=dialog.entered_days,
        )
        self._refresh_list()

    def _on_edit(self) -> None:
        alarm_id = self._selected_alarm_id()
        if alarm_id is None:
            QMessageBox.information(None, "No Alarm Selected", "Select an alarm to edit.")
            return

        alarm = self.context.alarms.get_alarm(alarm_id)
        dialog = AddEditAlarmDialog(alarm=alarm)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Re-enable on edit: a one-time alarm auto-disables itself after
        # firing (see AlarmManager.check_due), and editing it is the
        # user's way of rescheduling it, not leaving it dormant.
        self.context.alarms.update_alarm(
            alarm_id,
            label=dialog.entered_label,
            time=dialog.entered_time,
            days=dialog.entered_days,
            enabled=True,
        )
        self._refresh_list()

    def _on_delete(self) -> None:
        alarm_id = self._selected_alarm_id()
        if alarm_id is None:
            QMessageBox.information(None, "No Alarm Selected", "Select an alarm to delete.")
            return

        alarm = self.context.alarms.get_alarm(alarm_id)
        confirm = QMessageBox.question(
            None,
            "Delete Alarm",
            f"Delete the alarm '{alarm.label or 'Alarm'}' at {alarm.time}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.alarms.delete_alarm(alarm_id)
        self._refresh_list()
