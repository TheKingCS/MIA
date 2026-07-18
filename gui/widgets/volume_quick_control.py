"""
gui.widgets.volume_quick_control
===================================

A compact mute-button + slider, meant to live inside a `QWidgetAction`
in `gui/main_window.py`'s new profile-avatar dropdown menu.

**2026-07-18: moved out of the Home dashboard grid entirely.** Real
user report traced the dashboard's recurring "spacing/wording is off"
complaint to the old volume widget there: it was the only 3-element
card (header + slider + body) among otherwise-uniform 2-element cards,
and it happened to land in the grid's first row right next to Power/
Mission, forcing that whole row taller than the others. Quick access
to volume belongs in the header now instead, alongside Notifications/
Settings — `refresh()` is called explicitly right before the menu
opens (`QMenu.aboutToShow`) rather than on a running timer, since a
closed menu's contents don't need to stay live.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QWidget

from core.app_context import AppContext
from core.volume_manager import VolumeStatus


def format_volume_line(status: Optional[VolumeStatus]) -> str:
    """Same formatting gui/home_dashboard.py's old volume card used — kept here since that's its only caller now."""
    if status is None:
        return "Not available on this device."
    return f"{status.percent}%  —  Muted" if status.muted else f"{status.percent}%"


class VolumeQuickControl(QWidget):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self._mute_button = QPushButton("\U0001F50A")
        self._mute_button.setObjectName("HeaderButton")
        self._mute_button.setFixedSize(32, 32)
        self._mute_button.clicked.connect(self._on_mute_clicked)
        layout.addWidget(self._mute_button)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setMinimumWidth(140)
        self._slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self._slider, stretch=1)

        self._label = QLabel("")
        self._label.setObjectName("SubtitleLabel")
        self._label.setMinimumWidth(90)
        layout.addWidget(self._label)

        self.refresh()

    def refresh(self) -> None:
        available = self.context.volume is not None and self.context.volume.is_available()
        status = self.context.volume.read() if available else None
        self._label.setText(format_volume_line(status))
        self._slider.setEnabled(available)
        self._mute_button.setEnabled(available)
        if status is not None and not self._slider.isSliderDown():
            self._slider.setValue(status.percent)

        muted = status is not None and status.muted
        self._mute_button.setText("\U0001F507" if muted else "\U0001F50A")
        self._mute_button.setToolTip("Unmute" if muted else "Mute")

    def _on_slider_released(self) -> None:
        if self.context.volume is not None:
            self.context.volume.set_volume(self._slider.value())
        self.refresh()

    def _on_mute_clicked(self) -> None:
        if self.context.volume is not None:
            self.context.volume.toggle_mute()
        self.refresh()
