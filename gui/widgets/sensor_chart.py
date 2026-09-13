"""
gui.widgets.sensor_chart
===========================

build_sensor_chart_view() — the Sensor Monitor screen's (Design
restyle Phase 3, 2026-09-12) reading-history chart. Reuses this
codebase's existing charting mechanism (`PySide6.QtCharts`, already
used by `modules/lab/module.py`/`modules/budget/module.py` — not a new
hand-rolled `QPainter` plot) rather than reinventing one, themed via
`gui/widgets/theme_chart.py`'s new `apply_dark_chart_theme()`.

Simplification, stated plainly: the design handoff's own mockup shows
the chart's last five points "restated" in a different color —
QtCharts has no cheap way to recolor individual points within one
`QLineSeries`. This instead highlights just the single latest reading
via a small `QScatterSeries` dot, which reads the same way (draws the
eye to "where things stand now") without a second data structure
tracking "which points count as recent."

Returns `None` when there are no readings — the design's own explicit
behavior spec for this screen ("with zero readings show an explicit
'no readings yet' empty state; never interpolate or fake a value"),
so the caller renders that empty state itself rather than this
function inventing a placeholder chart.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QScatterSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen

from core.data_logger_manager import Reading
from gui.widgets.theme_chart import apply_dark_chart_theme

_SERIES_COLOR = QColor("#38d9c9")
_THRESHOLD_COLOR = QColor("#e06666")
_LATEST_DOT_COLOR = QColor("#e06666")


def build_sensor_chart_view(
    readings: list[Reading],
    threshold_value: Optional[float] = None,
    threshold_direction: str = "below",
) -> Optional[QChartView]:
    if not readings:
        return None

    ordered = sorted(readings, key=lambda r: r.timestamp)

    chart = QChart()

    line_series = QLineSeries()
    line_pen = QPen(_SERIES_COLOR)
    line_pen.setWidth(2)
    line_series.setPen(line_pen)
    for index, reading in enumerate(ordered):
        line_series.append(index, reading.value)
    chart.addSeries(line_series)

    x_axis = QValueAxis()
    x_axis.setLabelFormat("%d")
    x_axis.setTitleText("Reading #")
    chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
    line_series.attachAxis(x_axis)

    y_axis = QValueAxis()
    y_axis.setTitleText("Value")
    chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
    line_series.attachAxis(y_axis)

    values = [r.value for r in ordered]
    if threshold_value is not None:
        threshold_series = QLineSeries()
        threshold_pen = QPen(_THRESHOLD_COLOR)
        threshold_pen.setWidth(1)
        threshold_pen.setStyle(Qt.PenStyle.DashLine)
        threshold_series.setPen(threshold_pen)
        threshold_series.append(0, threshold_value)
        threshold_series.append(len(ordered) - 1, threshold_value)
        chart.addSeries(threshold_series)
        threshold_series.attachAxis(x_axis)
        threshold_series.attachAxis(y_axis)
        # QValueAxis auto-ranges only from series already attached at
        # the moment it computes its range, which produced a real bug
        # caught in this phase's own manual verification: a threshold
        # not yet crossed sits outside the readings' own value range,
        # so it silently rendered off-chart. Explicit range, not
        # QChart's own auto-fit, is what actually keeps it visible.
        values = values + [threshold_value]

    value_span = max(values) - min(values) or 1.0
    padding = value_span * 0.1
    y_axis.setRange(min(values) - padding, max(values) + padding)

    latest_dot = QScatterSeries()
    latest_dot.setColor(_LATEST_DOT_COLOR)
    latest_dot.setMarkerSize(9)
    latest_dot.append(len(ordered) - 1, ordered[-1].value)
    chart.addSeries(latest_dot)
    latest_dot.attachAxis(x_axis)
    latest_dot.attachAxis(y_axis)

    apply_dark_chart_theme(chart)

    chart_view = QChartView(chart)
    chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
    chart_view.setMinimumHeight(150)
    return chart_view
