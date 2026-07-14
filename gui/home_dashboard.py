"""
gui.home_dashboard
====================

The screen shown immediately after login — a real "home screen," not
just the module grid. 2026-07-14 aesthetic pass, part 3 (docs/ROADMAP.md):
the user's own framing was "after logging in the menu should display a
dashboard" with system power, the current mission, the time, and volume
control — the module grid itself moves to a separate "Apps" screen
(`gui/main_window.py`'s existing `_build_menu()`, now reached via its
own header button rather than being the landing view).

Deliberately not `modules/dashboard/module.py` (the existing "recent
activity/missions/memories/events/projects/tasks" aggregation page,
reachable from Apps like any other module) — that page is a detailed
scrollable log, this one is a glanceable, always-visible home screen
with a handful of live-updating cards. The two are complementary, not
duplicates.

**"Currently playing song" from the original ask is deliberately not
here** — Music is a bare placeholder module with no real playback data
source (same reasoning `modules/dashboard/module.py` already gives for
omitting it). Add it once Media/Music is a real built module.

**Volume control targets real Pi audio hardware
(`core/volume_manager.py`'s `amixer`-based backend) but is unverified in
this dev sandbox**, which has no `amixer` binary at all — the slider
degrades to disabled + a "Not available on this device" note via
`VolumeManager.is_available()`, same graceful-degradation UI pattern as
the Power card below when no battery/UPS is present. Re-verify the
slider's live behavior on real Pi hardware before trusting it further
than "the code path is exercised."

format_clock_time()/format_clock_date()/format_power_line()/
format_active_mission_line()/format_volume_line() are free functions
(not methods) — testable without Qt, see tests/test_home_dashboard.py.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.mission_manager import Mission
from core.power_manager import PowerStatus
from core.volume_manager import VolumeStatus

_DATA_REFRESH_MS = 5000  # matches modules/power/module.py's own polling cadence
_CLOCK_TICK_MS = 1000

_POWER_ICON = "\U0001F50B"  # battery
_MISSION_ICON = "\U0001F3C6"  # trophy
_VOLUME_ICON = "\U0001F50A"  # speaker


def format_clock_time(now: datetime) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_home_dashboard.py)."""
    return now.strftime("%H:%M:%S")


def format_clock_date(today: date) -> str:
    """Pure formatting logic — testable without Qt. Avoids strftime's
    platform-specific no-leading-zero day codes (%-d/%#d) by just
    formatting the day number separately."""
    return f"{today.strftime('%A, %B')} {today.day}"


def format_power_line(status: Optional[PowerStatus]) -> str:
    """Pure formatting logic — testable without Qt."""
    if status is None:
        return "No battery or UPS detected on this system."
    state = "Plugged in" if status.plugged_in else "On battery"
    return f"{status.percent:.0f}%  —  {state}"


def format_active_mission_line(mission: Optional[Mission], completed: int, total: int) -> str:
    """Pure formatting logic — testable without Qt."""
    if mission is None:
        return "No active mission."
    if total == 0:
        return f"{mission.name}  (no objectives yet)"
    return f"{mission.name}  —  {completed}/{total} objectives complete"


def format_volume_line(status: Optional[VolumeStatus]) -> str:
    """Pure formatting logic — testable without Qt."""
    if status is None:
        return "Not available on this device."
    if status.muted:
        return f"{status.percent}%  —  Muted"
    return f"{status.percent}%"


class HomeDashboard(QFrame):
    """The post-login home screen — see module docstring."""

    open_apps_requested = Signal()

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setObjectName("HomeDashboard")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(24)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        outer.addWidget(self._build_clock())

        cards = QGridLayout()
        cards.setSpacing(16)
        self._power_body = self._add_card(cards, 0, 0, _POWER_ICON, "Power")
        self._mission_body = self._add_card(cards, 0, 1, _MISSION_ICON, "Mission")
        volume_card, self._volume_body, self._volume_slider, self._mute_button = self._build_volume_card()
        cards.addWidget(volume_card, 0, 2)
        outer.addLayout(cards)

        outer.addWidget(self._build_apps_launch_card())
        outer.addStretch()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(_CLOCK_TICK_MS)

        self._data_timer = QTimer(self)
        self._data_timer.timeout.connect(self._refresh_data)
        self._data_timer.start(_DATA_REFRESH_MS)

        self._tick_clock()
        self._refresh_data()

    def unsubscribe(self) -> None:
        """Must be called before this widget is destroyed — stops both
        timers, same cleanup reasoning as gui/character_panel.py's
        unsubscribe() (a QTimer left running would keep firing into a
        deleted Qt widget)."""
        self._clock_timer.stop()
        self._data_timer.stop()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_clock(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._clock_time_label = QLabel()
        self._clock_time_label.setObjectName("DashboardClockTime")
        self._clock_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._clock_time_label)

        self._clock_date_label = QLabel()
        self._clock_date_label.setObjectName("DashboardClockDate")
        self._clock_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._clock_date_label)

        return container

    def _add_card(self, grid: QGridLayout, row: int, col: int, icon: str, title: str) -> QLabel:
        """Builds one icon+title+body card, adds it to `grid`, and
        returns just the body QLabel — the piece each section's
        _refresh_data() actually needs to update."""
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)

        icon_badge = QLabel(icon)
        icon_badge.setObjectName("DashboardSectionIcon")
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setFixedSize(40, 40)
        header.addWidget(icon_badge)

        title_label = QLabel(title)
        title_label.setObjectName("DashboardSectionTitle")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        body_label = QLabel()
        body_label.setObjectName("DashboardSectionBody")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)
        layout.addStretch()

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        card.setGraphicsEffect(shadow)

        grid.addWidget(card, row, col)
        return body_label

    def _build_volume_card(self) -> tuple[QFrame, QLabel, QSlider, QPushButton]:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)

        icon_badge = QLabel(_VOLUME_ICON)
        icon_badge.setObjectName("DashboardSectionIcon")
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setFixedSize(40, 40)
        header.addWidget(icon_badge)

        title_label = QLabel("Volume")
        title_label.setObjectName("DashboardSectionTitle")
        header.addWidget(title_label)
        header.addStretch()

        mute_button = QPushButton("\U0001F507")
        mute_button.setObjectName("HeaderButton")
        mute_button.clicked.connect(self._on_mute_clicked)
        header.addWidget(mute_button)
        layout.addLayout(header)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.sliderReleased.connect(self._on_volume_slider_released)
        layout.addWidget(slider)

        body_label = QLabel()
        body_label.setObjectName("DashboardSectionBody")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        card.setGraphicsEffect(shadow)

        return card, body_label, slider, mute_button

    def _build_apps_launch_card(self) -> QWidget:
        button = QPushButton("▦  Open Apps")
        button.setObjectName("AppsLaunchButton")
        button.clicked.connect(self.open_apps_requested.emit)
        return button

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _tick_clock(self) -> None:
        now = datetime.now()
        self._clock_time_label.setText(format_clock_time(now))
        self._clock_date_label.setText(format_clock_date(now.date()))

    def _refresh_data(self) -> None:
        self._refresh_power()
        self._refresh_mission()
        self._refresh_volume()

    def _refresh_power(self) -> None:
        status = self.context.power.read() if self.context.power else None
        self._power_body.setText(format_power_line(status))

    def _refresh_mission(self) -> None:
        mission = None
        completed = total = 0
        if self.context.missions is not None:
            active = [m for m in self.context.missions.all_missions() if m.status == "active"]
            if active:
                mission = active[0]
                total = len(mission.objectives)
                completed = sum(
                    1
                    for index in range(total)
                    if self.context.missions.is_objective_complete(mission.mission_id, index)
                )
        self._mission_body.setText(format_active_mission_line(mission, completed, total))

    def _refresh_volume(self) -> None:
        available = self.context.volume is not None and self.context.volume.is_available()
        status = self.context.volume.read() if available else None
        self._volume_body.setText(format_volume_line(status))
        self._volume_slider.setEnabled(available)
        self._mute_button.setEnabled(available)
        if status is not None and not self._volume_slider.isSliderDown():
            self._volume_slider.setValue(status.percent)

    def _on_volume_slider_released(self) -> None:
        if self.context.volume is not None:
            self.context.volume.set_volume(self._volume_slider.value())
        self._refresh_volume()

    def _on_mute_clicked(self) -> None:
        if self.context.volume is not None:
            self.context.volume.toggle_mute()
        self._refresh_volume()
