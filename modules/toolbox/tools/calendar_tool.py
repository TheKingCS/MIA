"""
modules.toolbox.tools.calendar_tool
======================================

Calendar — the first ToolboxTool (modules/toolbox/tool_base.py),
milestone 3.2 in docs/ROADMAP.md. A month grid (Qt's own
QCalendarWidget, reused rather than hand-rolled — same call as
QFileSystemModel/QTreeView for the Files module) with an agenda panel
for the selected date, backed by core.calendar_manager.CalendarManager
for persistence.

Dates with at least one event get a bold/colored QTextCharFormat via
setDateTextFormat(). QDate is an absolute calendar date (not scoped to
"the currently displayed month"), so a stale mark from an edited/
deleted event would otherwise persist when paging back to that month —
_refresh_markers() clears every custom format first (setDateTextFormat
with a default-constructed, i.e. invalid, QDate resets all of them)
before reapplying marks for the month currently on screen.

Recurring events (core.calendar_manager's `occurs_on()`): a recurring
event's agenda entry, on ANY of its virtual occurrence dates, is the
same real CalendarEvent object with the same event_id — there's no
separate "this occurrence" concept. Editing one always edits the true
stored anchor date/recurrence for the whole series (moves every future
occurrence), and deleting one removes the entire series, not just the
occurrence being viewed — no single-occurrence exception support,
by design (see the recurrence rollout's plan notes).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
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

from gui.add_edit_event_dialog import AddEditEventDialog
from modules.toolbox.tool_base import ToolboxTool

_ISO_DATE_FORMAT = "yyyy-MM-dd"
_MARKED_DATE_COLOR = "#4fd1c5"


class CalendarTool(ToolboxTool):
    tool_id = "calendar"
    display_name = "Calendar"
    description = "Add and browse dated events."
    icon = "\U0001F4C5"  # calendar

    def __init__(self, context) -> None:
        super().__init__(context)
        self._calendar: Optional[QCalendarWidget] = None
        self._agenda_label: Optional[QLabel] = None
        self._agenda_list: Optional[QListWidget] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._calendar = QCalendarWidget()
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._calendar.selectionChanged.connect(self._refresh_agenda)
        self._calendar.currentPageChanged.connect(lambda _year, _month: self._refresh_markers())
        layout.addWidget(self._calendar, stretch=2)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)

        self._agenda_label = QLabel()
        self._agenda_label.setObjectName("SubtitleLabel")
        self._agenda_label.setWordWrap(True)
        right_layout.addWidget(self._agenda_label)

        self._agenda_list = QListWidget()
        right_layout.addWidget(self._agenda_list, stretch=1)

        add_button = QPushButton("Add Event")
        add_button.clicked.connect(self._on_add)
        right_layout.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit)
        right_layout.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete)
        right_layout.addWidget(delete_button)

        layout.addWidget(right, stretch=1)

        self._refresh_markers()
        self._refresh_agenda()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_markers(self) -> None:
        self._calendar.setDateTextFormat(QDate(), QTextCharFormat())

        marked_format = QTextCharFormat()
        marked_format.setFontWeight(QFont.Weight.Bold)
        marked_format.setForeground(QColor(_MARKED_DATE_COLOR))

        year = self._calendar.yearShown()
        month = self._calendar.monthShown()
        events_by_date = self.context.calendar.events_for_month(year, month)
        for date_str in events_by_date:
            self._calendar.setDateTextFormat(QDate.fromString(date_str, _ISO_DATE_FORMAT), marked_format)

    def _refresh_agenda(self) -> None:
        selected = self._calendar.selectedDate()
        date_str = selected.toString(_ISO_DATE_FORMAT)
        self._agenda_label.setText(f"Events on {selected.toString('MMMM d, yyyy')}")

        self._agenda_list.clear()
        events = self.context.calendar.events_for_date(date_str)
        if not events:
            item = QListWidgetItem("No events.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._agenda_list.addItem(item)
            return

        for event in events:
            time_label = event.time if event.time else "All day"
            recurrence_suffix = f"  (repeats {event.recurrence})" if event.recurrence else ""
            item = QListWidgetItem(f"{time_label} — {event.title}{recurrence_suffix}")
            item.setData(Qt.ItemDataRole.UserRole, event.event_id)
            self._agenda_list.addItem(item)

    def _selected_event_id(self) -> Optional[str]:
        item = self._agenda_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        default_date = self._calendar.selectedDate().toString(_ISO_DATE_FORMAT)
        dialog = AddEditEventDialog(default_date=default_date)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.calendar.add_event(
            title=dialog.entered_title,
            date=dialog.entered_date,
            time=dialog.entered_time,
            notes=dialog.entered_notes,
            recurrence=dialog.entered_recurrence,
        )
        self._calendar.setSelectedDate(QDate.fromString(dialog.entered_date, _ISO_DATE_FORMAT))
        self._refresh_markers()
        self._refresh_agenda()

    def _on_edit(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            QMessageBox.information(None, "No Event Selected", "Select an event to edit.")
            return

        event = self.context.calendar.get_event(event_id)
        dialog = AddEditEventDialog(event=event)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.calendar.update_event(
            event_id,
            title=dialog.entered_title,
            date=dialog.entered_date,
            time=dialog.entered_time,
            notes=dialog.entered_notes,
            recurrence=dialog.entered_recurrence,
        )
        self._calendar.setSelectedDate(QDate.fromString(dialog.entered_date, _ISO_DATE_FORMAT))
        self._refresh_markers()
        self._refresh_agenda()

    def _on_delete(self) -> None:
        event_id = self._selected_event_id()
        if event_id is None:
            QMessageBox.information(None, "No Event Selected", "Select an event to delete.")
            return

        event = self.context.calendar.get_event(event_id)
        confirm = QMessageBox.question(
            None,
            "Delete Event",
            f"Delete '{event.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.calendar.delete_event(event_id)
        self._refresh_markers()
        self._refresh_agenda()
