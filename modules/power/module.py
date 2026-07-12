"""
modules.power.module
======================

Power — docs/ROADMAP.md milestone 7.2. Surfaces `AppContext.power`
(core/power_manager.py)'s current battery/UPS status. This is the
generic OS-battery-reporting view available today; the fuller Power
section scope from docs/ROADMAP.md's top-level module list (solar,
generator, charge controllers, usage, fuel) is future work once real
hardware (docs/HARDWARE.md's still-open "Battery/UPS HAT choice") is
chosen and given its own backend in core/power_manager.py.

format_power_status() is a free function (not a method), same
pure-formatting-logic shape as modules/diagnostics/module.py's
format_system_health() — testable without Qt, see
tests/test_power_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.power_manager import PowerStatus
from modules.module_base import ModuleBase

_REFRESH_MS = 5000


def format_power_status(status: Optional[PowerStatus]) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_power_module.py)."""
    if status is None:
        return "No battery or UPS detected on this system."

    lines = [
        f"Battery: {status.percent:.0f}%",
        "Power: Plugged in" if status.plugged_in else "Power: On battery",
    ]
    if not status.plugged_in and status.seconds_left is not None:
        minutes_left = status.seconds_left // 60
        lines.append(f"Estimated time remaining: {minutes_left} min")
    return "\n".join(lines)


class PowerModule(ModuleBase):
    module_id = "power"
    display_name = "Power"
    description = "Battery and power status."
    icon = "\U0001F50B"  # battery

    def __init__(self, context) -> None:
        super().__init__(context)
        self._status_label: Optional[QLabel] = None
        self._timer: Optional[QTimer] = None

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

        self._status_label = QLabel("")
        self._status_label.setObjectName("ReadoutLabel")
        layout.addWidget(self._status_label)
        layout.addStretch()

        self._refresh()

        self._timer = QTimer(widget)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(_REFRESH_MS)

        return widget

    def _refresh(self) -> None:
        if self._status_label is None:
            return
        status = self.context.power.read() if self.context.power is not None else None
        self._status_label.setText(format_power_status(status))
