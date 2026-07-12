"""
modules.lab.module
====================

The Lab — docs/ROADMAP.md milestone 8.2, the UI home of the Data
Logger shared service (top-level module section 14: "sensor testing,
experiments, calibration, graphs"). Pick or create a series, add a
manual reading (value/unit/note), see it charted via `QtCharts`
(bundled with PySide6 already — no new dependency) and listed below.

Manual entry only — no real sensor/multimeter hardware exists to
auto-log from yet. A future real-sensor integration is just another
caller of `context.data_logger.add_reading()`, not a different backend
to plug in here (see core/data_logger_manager.py's docstring).

The chart's x-axis is reading index (0, 1, 2, ...), not real elapsed
time — simpler than parsing/formatting a QDateTimeAxis for a first cut,
and every reading is already returned oldest-first by
`readings_for()`. A real-time x-axis is a reasonable future
enhancement, not needed to satisfy this milestone's "graphs" ask.

format_reading_row() is a free function (not a method), same
pure-formatting-logic shape as modules/notes/module.py's
format_entry_row() — testable without Qt, see tests/test_lab_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.data_logger_manager import Reading
from modules.module_base import ModuleBase


def format_reading_row(reading: Reading) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_lab_module.py)."""
    value_part = f"{reading.value:g}{' ' + reading.unit if reading.unit else ''}"
    time_part = reading.timestamp.replace("T", " ") if reading.timestamp else ""
    note_part = f"  — {reading.note}" if reading.note else ""
    return f"{time_part}   {value_part}{note_part}"


class LabModule(ModuleBase):
    module_id = "lab"
    display_name = "The Lab"
    description = "Sensor testing, experiments, calibration, and graphs."
    icon = "\U0001F9EA"  # test tube

    def __init__(self, context) -> None:
        super().__init__(context)
        self._series_combo: Optional[QComboBox] = None
        self._value_edit: Optional[QLineEdit] = None
        self._unit_edit: Optional[QLineEdit] = None
        self._note_edit: Optional[QLineEdit] = None
        self._chart_view: Optional[QChartView] = None
        self._readings_list: Optional[QListWidget] = None
        self._current_readings: list[Reading] = []

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        series_row = QHBoxLayout()
        series_row.addWidget(QLabel("Series:"))
        self._series_combo = QComboBox()
        self._series_combo.setEditable(True)
        self._series_combo.setPlaceholderText("Pick or type a new series name…")
        self._series_combo.addItems(self.context.data_logger.list_series())
        self._series_combo.setCurrentIndex(-1)
        self._series_combo.currentTextChanged.connect(self._refresh_series)
        series_row.addWidget(self._series_combo, stretch=1)
        layout.addLayout(series_row)

        entry_row = QHBoxLayout()
        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("Value")
        entry_row.addWidget(self._value_edit)

        self._unit_edit = QLineEdit()
        self._unit_edit.setPlaceholderText("Unit (optional)")
        entry_row.addWidget(self._unit_edit)

        self._note_edit = QLineEdit()
        self._note_edit.setPlaceholderText("Note (optional)")
        entry_row.addWidget(self._note_edit, stretch=1)

        add_button = QPushButton("Add Reading")
        add_button.clicked.connect(self._on_add_reading)
        entry_row.addWidget(add_button)
        layout.addLayout(entry_row)

        self._chart_view = QChartView()
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumHeight(220)
        layout.addWidget(self._chart_view, stretch=1)

        self._readings_list = QListWidget()
        layout.addWidget(self._readings_list, stretch=1)

        delete_button = QPushButton("Delete Selected Reading")
        delete_button.clicked.connect(self._on_delete_reading)
        layout.addWidget(delete_button)

        return widget

    # ------------------------------------------------------------------
    # Adding
    # ------------------------------------------------------------------

    def _on_add_reading(self) -> None:
        series_id = self._series_combo.currentText().strip()
        if not series_id:
            QMessageBox.information(None, "No Series", "Pick or type a series name first.")
            return

        value_text = self._value_edit.text().strip()
        try:
            value = float(value_text)
        except ValueError:
            QMessageBox.information(None, "Invalid Value", "Enter a numeric value.")
            return

        self.context.data_logger.add_reading(
            series_id,
            value,
            unit=self._unit_edit.text().strip(),
            note=self._note_edit.text().strip(),
        )
        self._value_edit.clear()
        self._note_edit.clear()

        if self._series_combo.findText(series_id) == -1:
            self._series_combo.addItem(series_id)
        self._refresh_series(series_id)

    # ------------------------------------------------------------------
    # Deleting
    # ------------------------------------------------------------------

    def _on_delete_reading(self) -> None:
        row = self._readings_list.currentRow()
        if row < 0 or row >= len(self._current_readings):
            QMessageBox.information(None, "No Reading Selected", "Select a reading to delete.")
            return
        reading = self._current_readings[row]
        self.context.data_logger.delete_reading(reading.reading_id)
        self._refresh_series(self._series_combo.currentText())

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_series(self, series_id: str) -> None:
        series_id = series_id.strip()
        self._current_readings = self.context.data_logger.readings_for(series_id) if series_id else []

        self._readings_list.clear()
        for reading in self._current_readings:
            self._readings_list.addItem(QListWidgetItem(format_reading_row(reading)))

        self._update_chart()

    def _update_chart(self) -> None:
        chart = QChart()
        chart.legend().hide()

        line_series = QLineSeries()
        for index, reading in enumerate(self._current_readings):
            line_series.append(index, reading.value)
        chart.addSeries(line_series)

        x_axis = QValueAxis()
        x_axis.setTitleText("Reading #")
        x_axis.setLabelFormat("%d")
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        line_series.attachAxis(x_axis)

        y_axis = QValueAxis()
        y_axis.setTitleText("Value")
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        line_series.attachAxis(y_axis)

        self._chart_view.setChart(chart)
