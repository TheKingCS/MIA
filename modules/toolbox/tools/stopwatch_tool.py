"""
modules.toolbox.tools.stopwatch_tool
=======================================

Stopwatch — a ToolboxTool (modules/toolbox/tool_base.py), part of
milestone 3.3 in docs/ROADMAP.md (paired with alarm_tool.py). Purely
ephemeral, in-memory state — unlike Calendar/Alarm, a stopwatch reading
has no reason to survive an app restart, so there's no core/ manager
or data/ file here.

Elapsed time is tracked via time.monotonic() deltas (never
datetime.now(), which can jump on a system clock adjustment) plus an
accumulated total, so Start -> Stop -> Start again keeps adding to the
same run rather than restarting it. Because modules/toolbox/module.py
caches built tool widgets and reuses the same instance, a stopwatch
left running keeps ticking in the background even while a different
Toolbox item (or a different module entirely) is on screen — the
QTimer driving the display update fires regardless of visibility.

format_elapsed() is a free function, unit-testable without Qt — see
tests/test_stopwatch_format.py.
"""

from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from modules.toolbox.tool_base import ToolboxTool

_DISPLAY_INTERVAL_MS = 100


def format_elapsed(total_ms: int) -> str:
    """
    "MM:SS.t" for under an hour, "HH:MM:SS.t" once it runs past one —
    tenths of a second, not milliseconds, since that's all a 100ms
    display refresh can meaningfully show anyway.
    """
    if total_ms < 0:
        raise ValueError("total_ms must be non-negative.")

    total_tenths = total_ms // 100
    tenths = total_tenths % 10
    total_seconds = total_tenths // 10
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{tenths}"
    return f"{minutes:02d}:{seconds:02d}.{tenths}"


class StopwatchTool(ToolboxTool):
    tool_id = "stopwatch"
    display_name = "Stopwatch"
    description = "Start, stop, lap, and reset a simple stopwatch."
    icon = "⏱"  # stopwatch

    def __init__(self, context) -> None:
        super().__init__(context)
        self._elapsed_ms = 0
        self._running = False
        self._start_monotonic: Optional[float] = None
        self._laps: list[int] = []

        self._display_timer = QTimer()
        self._display_timer.setInterval(_DISPLAY_INTERVAL_MS)
        self._display_timer.timeout.connect(self._update_display)

        self._readout: Optional[QLabel] = None
        self._start_stop_button: Optional[QPushButton] = None
        self._lap_button: Optional[QPushButton] = None
        self._reset_button: Optional[QPushButton] = None
        self._laps_list: Optional[QListWidget] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._readout = QLabel(format_elapsed(0))
        self._readout.setObjectName("ReadoutLabel")
        self._readout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._readout.setStyleSheet("font-size: 42px; padding: 24px;")
        layout.addWidget(self._readout)

        button_row = QHBoxLayout()
        self._start_stop_button = QPushButton("Start")
        self._start_stop_button.setMinimumHeight(40)
        self._start_stop_button.clicked.connect(self._on_start_stop)
        button_row.addWidget(self._start_stop_button)

        self._lap_button = QPushButton("Lap")
        self._lap_button.setMinimumHeight(40)
        self._lap_button.setEnabled(False)
        self._lap_button.clicked.connect(self._on_lap)
        button_row.addWidget(self._lap_button)

        self._reset_button = QPushButton("Reset")
        self._reset_button.setMinimumHeight(40)
        self._reset_button.clicked.connect(self._on_reset)
        button_row.addWidget(self._reset_button)

        layout.addLayout(button_row)

        self._laps_list = QListWidget()
        layout.addWidget(self._laps_list, stretch=1)

        return widget

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def _current_elapsed_ms(self) -> int:
        if self._running:
            return self._elapsed_ms + int((time.monotonic() - self._start_monotonic) * 1000)
        return self._elapsed_ms

    def _update_display(self) -> None:
        self._readout.setText(format_elapsed(self._current_elapsed_ms()))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_start_stop(self) -> None:
        if self._running:
            self._elapsed_ms = self._current_elapsed_ms()
            self._running = False
            self._display_timer.stop()
            self._start_stop_button.setText("Start")
            self._lap_button.setEnabled(False)
            self._reset_button.setEnabled(True)
            self._update_display()
        else:
            self._start_monotonic = time.monotonic()
            self._running = True
            self._display_timer.start()
            self._start_stop_button.setText("Stop")
            self._lap_button.setEnabled(True)
            self._reset_button.setEnabled(False)

    def _on_lap(self) -> None:
        self._laps.append(self._current_elapsed_ms())
        self._refresh_laps()

    def _on_reset(self) -> None:
        self._elapsed_ms = 0
        self._laps = []
        self._update_display()
        self._refresh_laps()

    def _refresh_laps(self) -> None:
        self._laps_list.clear()
        for idx in range(len(self._laps) - 1, -1, -1):
            lap_ms = self._laps[idx]
            previous_ms = self._laps[idx - 1] if idx > 0 else 0
            delta_ms = lap_ms - previous_ms
            self._laps_list.addItem(
                f"Lap {idx + 1}: {format_elapsed(lap_ms)}  (+{format_elapsed(delta_ms)})"
            )
