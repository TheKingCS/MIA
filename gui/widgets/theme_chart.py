"""
gui.widgets.theme_chart
==========================

apply_dark_chart_theme() — a small shared helper that themes a
`PySide6.QtCharts.QChart` to match `DARK_FIELD_THEME`
(`gui/styles.py`). Real, pre-existing gap this closes: `modules/lab
/module.py` and `modules/budget/module.py` already chart
`DataLoggerManager`/budget data via QtCharts, but neither themes it —
both render QtCharts' plain light-mode look, which would sit as a
jarring bright rectangle in an otherwise dark UI. QSS doesn't reach
into a QChart's own rendering (confirmed: no chart theming code
existed anywhere in this repo before this file), so this applies the
theme through QChart's own API instead.

Introduced for the Sensor Monitor screen's new chart
(`gui/widgets/sensor_chart.py`); a natural, separate follow-up (not
done here) would apply this same helper to Lab's/Budget's existing
charts.
"""

from __future__ import annotations

from PySide6.QtCharts import QChart, QValueAxis
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QColor, QPen

# Same v2 HUD "panel ground" token gui/widgets/glow.py's docstring and
# the design handoff's own token table both cite.
_PANEL_GROUND = QColor("#0a1219")
_AXIS_LABEL_COLOR = QColor("#5b6a80")  # this theme's "text dim" / mono-meta token
_GRIDLINE_COLOR = QColor("#161f2b")


def apply_dark_chart_theme(chart: QChart) -> None:
    """Applies once, right after building `chart` — same "call once per
    widget" convention as gui/widgets/glow.py's apply_panel_glow()."""
    chart.setBackgroundBrush(_PANEL_GROUND)
    chart.setBackgroundPen(QPen(Qt.PenStyle.NoPen))
    chart.legend().setVisible(False)
    chart.setMargins(QMargins(4, 4, 4, 4))

    for axis in chart.axes():
        if isinstance(axis, QValueAxis):
            axis.setLabelsColor(_AXIS_LABEL_COLOR)
            axis.setGridLineColor(_GRIDLINE_COLOR)
            axis.setLinePen(QPen(_GRIDLINE_COLOR))
