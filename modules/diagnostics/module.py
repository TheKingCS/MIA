"""
modules.diagnostics.module
============================

Diagnostics: system health and the in-app log viewer.

The log viewer was the first genuinely useful piece of this module (per
docs/ROADMAP.md's v0.2 milestone 2.6) — it tails core/logger.py's
logs/mia.log so a field deployment can be debugged without pulling out
a laptop or hunting for the file on a headless Pi. The System Health
panel (v0.7 milestone 7.1) is the second: live CPU/RAM/disk/network/
temperature via `psutil` (cross-platform, no stdlib equivalent).

Stats-reading (read_system_health()/format_system_health()) is free
functions (not methods), same shape as tail_lines()/filter_lines(), so
they're unit-testable without a Qt event loop — see
tests/test_diagnostics_system_health.py. This data is kept as plain functions
here rather than promoted to a core/ service because it's Diagnostics'
own exclusive concern (not shared across module sections the way
Calculator Engine/Reference Library are) and it's stateless
point-in-time reads with no persistence — a core manager would be pure
ceremony. A widget-owned QTimer refreshes the panel while it's on
screen, same timer-owned-by-the-widget pattern as
gui/character_panel.py's idle timer. The QWidget-building side of
get_widget() is exercised manually instead; see
docs/testing/2.6_system_logs_viewer.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.logger import get_logger
from modules.module_base import ModuleBase

log = get_logger(__name__)

_LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "mia.log"
_MAX_DISPLAY_LINES = 1000
_LOG_LEVELS = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_HEALTH_REFRESH_MS = 3000
_BYTES_PER_GB = 1024 ** 3
_BYTES_PER_MB = 1024 ** 2


@dataclass
class SystemHealthSnapshot:
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    temperature_celsius: Optional[float]
    network_sent_mb: float
    network_recv_mb: float


def read_system_health(disk_path: str = "/") -> SystemHealthSnapshot:
    """
    Read a point-in-time system health snapshot via psutil.

    `psutil.cpu_percent(interval=None)` is non-blocking — it reports
    usage since the *previous* call in this process, not a fresh
    measurement, so the very first call after import is meaningless
    (usually 0.0). Callers that display this on a periodic timer (this
    module's get_widget()) should prime it with one throwaway call
    before the first real reading, rather than passing a blocking
    `interval` here and stalling the GUI thread on every refresh tick.
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_path)
    net = psutil.net_io_counters()
    return SystemHealthSnapshot(
        cpu_percent=cpu_percent,
        memory_percent=vm.percent,
        memory_used_gb=vm.used / _BYTES_PER_GB,
        memory_total_gb=vm.total / _BYTES_PER_GB,
        disk_percent=disk.percent,
        disk_used_gb=disk.used / _BYTES_PER_GB,
        disk_total_gb=disk.total / _BYTES_PER_GB,
        temperature_celsius=_read_cpu_temperature(),
        network_sent_mb=net.bytes_sent / _BYTES_PER_MB,
        network_recv_mb=net.bytes_recv / _BYTES_PER_MB,
    )


def _read_cpu_temperature() -> Optional[float]:
    """
    First available sensor reading, or None. `sensors_temperatures()`
    isn't implemented on every platform (raises on Windows/macOS) and
    returns an empty dict on systems with no exposed thermal zone (true
    in this project's own dev sandbox/WSL2) — both degrade to None
    here rather than raising, same defensive pattern as every other
    "external system state might just not be there" read in this app.
    """
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    for entries in temps.values():
        for entry in entries:
            if entry.current is not None:
                return entry.current
    return None


def format_system_health(snapshot: SystemHealthSnapshot) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_diagnostics_system_health.py)."""
    temperature_line = (
        f"Temperature: {snapshot.temperature_celsius:.1f}°C"
        if snapshot.temperature_celsius is not None
        else "Temperature: not available on this system"
    )
    return "\n".join([
        f"CPU: {snapshot.cpu_percent:.1f}%",
        f"Memory: {snapshot.memory_percent:.1f}%  "
        f"({snapshot.memory_used_gb:.1f} / {snapshot.memory_total_gb:.1f} GB)",
        f"Disk: {snapshot.disk_percent:.1f}%  "
        f"({snapshot.disk_used_gb:.1f} / {snapshot.disk_total_gb:.1f} GB)",
        temperature_line,
        f"Network: {snapshot.network_sent_mb:.1f} MB sent / "
        f"{snapshot.network_recv_mb:.1f} MB received (since boot)",
    ])


def tail_lines(path: Path, max_lines: int) -> list[str]:
    """
    Return up to the last `max_lines` lines of `path`, oldest first.
    Returns an empty list if the file doesn't exist yet (e.g. a very
    first run before anything has logged).
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-max_lines:]]


def filter_lines(lines: list[str], level: str, query: str) -> list[str]:
    """
    Filter log lines by level and a case-insensitive substring query.

    Matches against the "[LEVELNAME ]" field core.logger's formatter
    (fmt="...[%(levelname)-8s]...") pads every line to — level="ALL" or
    a falsy value disables the level filter.
    """
    result = lines
    if level and level != "ALL":
        needle = f"[{level:<8}]"
        result = [line for line in result if needle in line]
    if query:
        query_lower = query.lower()
        result = [line for line in result if query_lower in line.lower()]
    return result


class DiagnosticsModule(ModuleBase):
    module_id = "diagnostics"
    display_name = "Diagnostics"
    description = "System health, logs, and hardware status."
    icon = "\U0001FA7A"  # stethoscope

    def __init__(self, context) -> None:
        super().__init__(context)
        self._log_view: QPlainTextEdit | None = None
        self._level_combo: QComboBox | None = None
        self._search_edit: QLineEdit | None = None
        self._info_label: QLabel | None = None
        self._health_label: QLabel | None = None
        self._health_timer: QTimer | None = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        outer.addWidget(subtitle)

        health_title = QLabel("System Health")
        health_title.setObjectName("SubtitleLabel")
        outer.addWidget(health_title)

        self._health_label = QLabel("")
        self._health_label.setObjectName("ReadoutLabel")
        outer.addWidget(self._health_label)

        # Prime cpu_percent() — see read_system_health()'s docstring for
        # why the very first reading is otherwise meaningless.
        psutil.cpu_percent(interval=None)
        self._refresh_health()

        self._health_timer = QTimer(widget)
        self._health_timer.timeout.connect(self._refresh_health)
        self._health_timer.start(_HEALTH_REFRESH_MS)

        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Level:"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(_LOG_LEVELS)
        self._level_combo.currentTextChanged.connect(self._refresh)
        toolbar.addWidget(self._level_combo)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter log text…")
        self._search_edit.textChanged.connect(self._refresh)
        toolbar.addWidget(self._search_edit, stretch=1)

        refresh_button = QPushButton("\U0001F504 Refresh")
        refresh_button.setObjectName("ModuleButton")
        refresh_button.clicked.connect(self._refresh)
        toolbar.addWidget(refresh_button)

        outer.addLayout(toolbar)

        self._info_label = QLabel("")
        self._info_label.setObjectName("SubtitleLabel")
        outer.addWidget(self._info_label)

        self._log_view = QPlainTextEdit()
        self._log_view.setObjectName("LogView")
        self._log_view.setReadOnly(True)
        self._log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        outer.addWidget(self._log_view, stretch=1)

        self._refresh()
        return widget

    def _refresh_health(self) -> None:
        if self._health_label is None:
            return
        try:
            snapshot = read_system_health()
        except Exception:
            log.exception("Failed to read system health via psutil.")
            self._health_label.setText("System health unavailable on this system.")
            return
        self._health_label.setText(format_system_health(snapshot))

    def _refresh(self) -> None:
        if self._log_view is None:
            return

        all_lines = tail_lines(_LOG_FILE, _MAX_DISPLAY_LINES)
        level = self._level_combo.currentText() if self._level_combo else "ALL"
        query = self._search_edit.text() if self._search_edit else ""
        shown = filter_lines(all_lines, level, query)

        if not all_lines:
            self._info_label.setText(f"No log file found yet at {_LOG_FILE}.")
        else:
            self._info_label.setText(
                f"Showing {len(shown)} of {len(all_lines)} lines "
                f"(most recent {_MAX_DISPLAY_LINES} lines of {_LOG_FILE})."
            )

        self._log_view.setPlainText("\n".join(shown))
        scrollbar = self._log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
