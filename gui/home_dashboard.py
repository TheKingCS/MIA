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

**2026-07-15: Startup Dashboard Briefing** (`docs/VISION.md`'s
companion-philosophy update — "greet the user with an intelligent
summary instead of simply opening the dashboard"). A short greeting
banner is built once per `HomeDashboard` construction (i.e. once per
app launch / login, not on the 5s data-refresh timer — this is meant to
read as "welcome back," not a live ticker) via
`core/startup_briefing.py`'s pure template functions, summarizing
active missions, today's calendar events, unread notifications, active
projects, and the most recent Memory. **This will need to grow** as
more of the companion-philosophy vision ships (weather, workout
recommendations, financial updates, smart home status are all named in
the vision but have no real module yet) — `_build_briefing_text()`
below is the one place to extend with new `context.*` sources as they
land, and `core.startup_briefing.build_stat_highlights()` is written to
take plain counts precisely so new sources slot in without restructuring
it.

**2026-07-15: the briefing is now spoken, not just displayed** — at the
user's explicit request ("I want this startup to be a spoken thing"),
`_speak_briefing()` runs the greeting through `core/tts_worker.py`
(same fire-and-forget QThread pattern `modules/assistant/module.py`
already uses for spoken replies) once, right after construction.
Degrades silently if Voice/TTS isn't available (no model fetched, no
PortAudio) — same graceful-degradation stance as everything else
Voice-adjacent in this project. Which voice speaks is chosen in
Settings (`modules/settings/module.py`'s Voice dropdown, backed by
`core/voice_catalog.py`'s curated multi-voice selection).

**2026-07-15: the fixed 3-card layout is now a real widget framework**
(`core/dashboard_widgets.py`'s "framework first" build, prompted by the
user wanting a "JARVIS-level dashboard" with more widgets — trading
bot, weather, music, current project — and the ability to add/remove
them). Power/Mission/Volume are now registered widgets like any other,
not hardcoded cards — `_build_widgets_grid()` renders whatever
`context.dashboard_widgets.enabled_widgets_in_order()` returns, and a
new gear button opens `gui/dashboard_customize_dialog.py` to toggle/
reorder them, live (no restart — same "rebuild on event" pattern
`gui/main_window.py` already uses for the Apps grid). New widgets only
need a `WidgetDescriptor` registration
(`core/application.py`'s `_register_dashboard_widgets()`) plus a
builder method here in `self._widget_builders` — the framework itself
doesn't change. First new widget built this pass: Current Project.

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

import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.daily_occasions import calendar_events_today
from core.dashboard_widgets import WidgetDescriptor
from core.mission_manager import Mission
from core.power_manager import PowerStatus
from core.project_manager import Project
from core.startup_briefing import build_stat_highlights, build_startup_briefing
from core.tts_worker import TTSWorker
from core.volume_manager import VolumeStatus
from gui.dashboard_customize_dialog import DashboardCustomizeDialog

_DATA_REFRESH_MS = 5000  # matches modules/power/module.py's own polling cadence
_CLOCK_TICK_MS = 1000


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


def format_current_project_line(project: Optional[Project], active_count: int) -> str:
    """Pure formatting logic — testable without Qt."""
    if project is None:
        return "No active projects."
    if active_count <= 1:
        return f"{project.name}  [{project.status}]"
    return f"{project.name}  [{project.status}]  (+{active_count - 1} more active)"


class HomeDashboard(QFrame):
    """The post-login home screen — see module docstring."""

    open_apps_requested = Signal()

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setObjectName("HomeDashboard")
        self._tts_worker: Optional[TTSWorker] = None
        self._widget_bodies: dict[str, QLabel] = {}
        self._volume_slider: Optional[QSlider] = None
        self._mute_button: Optional[QPushButton] = None
        self._widget_builders = {
            "power": self._build_power_widget,
            "mission": self._build_mission_widget,
            "volume": self._build_volume_widget,
            "current_project": self._build_current_project_widget,
        }
        self._widget_highlight_providers: dict[str, Callable[[], Optional[str]]] = {
            "power": self._power_highlight,
            "mission": self._mission_highlight,
            "volume": self._volume_highlight,
            "current_project": self._current_project_highlight,
        }

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(24)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        outer.addWidget(self._build_clock())

        # Built (and refreshed with real data) before the briefing
        # banner below, even though it's added to the layout after —
        # _build_briefing_text() reads live widget state via
        # self._widget_bodies/the highlight providers, so that needs to
        # already be populated with this launch's real values first.
        # Doesn't need to already be in `outer`'s layout for that.
        self._widgets_container = QWidget()
        self._widgets_grid: Optional[QGridLayout] = None
        self._build_widgets_grid()

        outer.addWidget(self._build_briefing_banner())
        self._speak_briefing()

        outer.addWidget(self._widgets_container)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._build_apps_launch_card(), stretch=1)
        customize_button = QPushButton("⚙")  # gear
        customize_button.setObjectName("HeaderButton")
        customize_button.setToolTip("Customize Dashboard")
        customize_button.clicked.connect(self._on_customize_clicked)
        toolbar.addWidget(customize_button)
        outer.addLayout(toolbar)
        outer.addStretch()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(_CLOCK_TICK_MS)

        self._data_timer = QTimer(self)
        self._data_timer.timeout.connect(self._refresh_data)
        self._data_timer.start(_DATA_REFRESH_MS)

        self.context.events.subscribe("dashboard.widgets_changed", self._on_widgets_changed)

        self._tick_clock()
        self._refresh_data()

    def unsubscribe(self) -> None:
        """Must be called before this widget is destroyed — stops both
        timers and unsubscribes from the event bus, same cleanup
        reasoning as gui/character_panel.py's unsubscribe() (a QTimer
        left running would keep firing into a deleted Qt widget, and a
        stale event subscriber would keep this dead widget alive in
        EventBus's callback list)."""
        self._clock_timer.stop()
        self._data_timer.stop()
        self.context.events.unsubscribe("dashboard.widgets_changed", self._on_widgets_changed)

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

    def _build_widgets_grid(self) -> None:
        """(Re)builds the dashboard's widget grid from
        context.dashboard_widgets.enabled_widgets_in_order() — called
        once at construction and again any time "dashboard.widgets_changed"
        fires (the Customize dialog), so this is always a full rebuild,
        not an in-place patch. Reuses one QGridLayout instance for
        self._widgets_container's whole lifetime rather than trying to
        replace the layout object itself each time — Qt refuses (with
        just a runtime warning, not an exception) to install a second
        layout on a widget unless the first is fully detached, and an
        early version of this method got that wrong: it silently left
        the container with no live layout at all after the first
        rebuild, so every widget was actually still present in
        self._widget_bodies but invisible on screen. Clearing/refilling
        the same grid sidesteps the problem entirely. Same explicit
        hide()+setParent(None) cleanup as this app's other layout-
        clearing code (modules/dashboard/module.py) — deleteLater()
        alone doesn't hide anything immediately and has left ghosted
        widgets on screen before in this codebase."""
        if self._widgets_grid is None:
            self._widgets_grid = QGridLayout(self._widgets_container)
            self._widgets_grid.setSpacing(16)

        while self._widgets_grid.count():
            item = self._widgets_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        self._widget_bodies = {}
        self._volume_slider = None
        self._mute_button = None

        registry = self.context.dashboard_widgets
        widgets = registry.enabled_widgets_in_order() if registry is not None else []
        for index, descriptor in enumerate(widgets):
            builder = self._widget_builders.get(descriptor.widget_id)
            if builder is None:
                continue
            widget = builder(descriptor)
            self._widgets_grid.addWidget(widget, index // 3, index % 3)
            # A widget added to an already-visible parent's layout isn't
            # always auto-shown by Qt on every platform — confirmed via
            # a real headless-Qt test: after the first rebuild, new
            # cards reported isVisible()=False and a default unlaid-out
            # size until explicitly shown. Harmless to call this during
            # the initial construction-time build too (the parent isn't
            # shown yet then anyway).
            widget.show()

        self._refresh_data()

    def _on_widgets_changed(self) -> None:
        self._build_widgets_grid()

    def _on_customize_clicked(self) -> None:
        dialog = DashboardCustomizeDialog(self.context, self)
        dialog.exec()

    def _build_power_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            menu_actions=[("Open Power", lambda: self._open_module("power"))],
        )
        self._widget_bodies["power"] = body
        return card

    def _build_mission_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            menu_actions=[("Open Missions", lambda: self._open_module("missions"))],
        )
        self._widget_bodies["mission"] = body
        return card

    def _build_current_project_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            # Projects live inside the Toolbox module (a "Project Manager"
            # tool tab), not a standalone module of their own — this opens
            # Toolbox, same one-level-deep limitation
            # gui/main_window.py's open_module() has for any nested tool.
            menu_actions=[("Open Projects", lambda: self._open_module("toolbox"))],
        )
        self._widget_bodies["current_project"] = body
        return card

    def _build_volume_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        # No menu_actions here — the dedicated mute button already
        # covers this widget's one real action, and there's no related
        # module to open (unlike Power/Mission/Current Project); a "⋯"
        # menu with only a redundant "Toggle Mute" item would be worse
        # than no menu at all.
        card, body, slider, mute_button = self._build_volume_card(descriptor.icon, descriptor.display_name)
        self._widget_bodies["volume"] = body
        self._volume_slider = slider
        self._mute_button = mute_button
        return card

    def _open_module(self, module_id: str) -> None:
        """Reuses the exact navigation mechanism the Assistant's own
        `open_module` action already uses (core/application.py) — a
        widget menu action and a chat command both end up going through
        the same one path, gui/main_window.py's open_module()."""
        self.context.events.publish("assistant.open_module_requested", module_id=module_id)

    def _build_widget_header(
        self, icon: str, title: str, menu_actions: Optional[list[tuple[str, Callable[[], None]]]] = None
    ) -> QHBoxLayout:
        """Shared by _build_simple_card()/_build_volume_card() — the
        eyebrow-label+stretch+optional "⋯" menu button row every widget
        card starts with.

        **2026-07-15 "ForMIA" design handoff**: widget cards no longer
        show an icon badge — just a small uppercase "eyebrow" label
        (`#DashboardSectionTitle`, restyled in gui/styles.py to match),
        the pattern the handoff's `WIDGET_STENCIL.md` specifies for
        every card. `icon` is kept as a parameter (not removed, callers
        still pass each widget's real glyph) and used as the eyebrow
        label's tooltip instead of being rendered directly — a module's
        icon identity isn't fully gone, just no longer taking up card
        space the way it used to. QSS has no text-transform, so the
        label text is uppercased here in Python.
        """
        header = QHBoxLayout()
        header.setSpacing(10)

        title_label = QLabel(title.upper())
        title_label.setObjectName("DashboardSectionTitle")
        title_label.setToolTip(f"{icon} {title}")
        header.addWidget(title_label)
        header.addStretch()

        if menu_actions:
            menu_button = QPushButton("⋯")
            menu_button.setObjectName("HeaderButton")
            menu_button.setFixedSize(28, 28)
            menu_button.setToolTip(f"{title} actions")
            menu = QMenu(menu_button)
            for label, callback in menu_actions:
                menu.addAction(label).triggered.connect(callback)
            menu_button.setMenu(menu)
            header.addWidget(menu_button)

        return header

    def _build_simple_card(
        self, icon: str, title: str, menu_actions: Optional[list[tuple[str, Callable[[], None]]]] = None
    ) -> tuple[QFrame, QLabel]:
        """Builds one icon+title+body card and returns (card, body_label)
        — the widget builders above add it to the grid themselves."""
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        layout.addLayout(self._build_widget_header(icon, title, menu_actions))

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

        return card, body_label

    def _build_volume_card(self, icon: str, title: str) -> tuple[QFrame, QLabel, QSlider, QPushButton]:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = self._build_widget_header(icon, title)

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

    def _build_briefing_banner(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)

        self._briefing_label = QLabel(self._build_briefing_text())
        self._briefing_label.setObjectName("DashboardBriefingText")
        self._briefing_label.setWordWrap(True)
        layout.addWidget(self._briefing_label)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        card.setGraphicsEffect(shadow)

        return card

    def _power_highlight(self) -> Optional[str]:
        if self.context.power is None:
            return None
        status = self.context.power.read()
        if status is None:
            return None
        return f"{status.percent:.0f}% battery"

    def _mission_highlight(self) -> Optional[str]:
        if self.context.missions is None:
            return None
        count = sum(1 for m in self.context.missions.all_missions() if m.status == "active")
        if not count:
            return None
        noun = "mission" if count == 1 else "missions"
        return f"{count} active {noun}"

    def _volume_highlight(self) -> Optional[str]:
        return None  # not meaningful for a spoken dashboard summary

    def _current_project_highlight(self) -> Optional[str]:
        if self.context.projects is None:
            return None
        count = sum(1 for p in self.context.projects.all_projects() if p.status != "Complete")
        if not count:
            return None
        noun = "project" if count == 1 else "projects"
        return f"{count} {noun} in progress"

    def _widget_highlights(self) -> list[str]:
        """The briefing's dashboard-specific content — one highlight
        per currently-*enabled* widget that actually has something to
        say, via self._widget_highlight_providers (populated alongside
        self._widget_builders). This is what keeps the briefing honest:
        adding/removing/reordering a widget changes what gets
        summarized automatically, since it reads the same
        enabled-widgets list gui/dashboard_customize_dialog.py writes
        to — no separate, easily-stale list to maintain by hand."""
        registry = self.context.dashboard_widgets
        if registry is None:
            return []
        highlights = []
        for descriptor in registry.enabled_widgets_in_order():
            provider = self._widget_highlight_providers.get(descriptor.widget_id)
            if provider is None:
                continue
            highlight = provider()
            if highlight:
                highlights.append(highlight)
        return highlights

    def _build_briefing_text(self) -> str:
        """Computed once at construction (not on the 5s data-refresh
        timer below) — this is a "welcome back" greeting, not a live
        ticker. See this module's docstring for what's deliberately
        omitted (weather/workout/finance/smart home — no real widget
        yet) and where to extend this as those subsystems land: add a
        _<widget_id>_highlight() method and register it in
        self._widget_highlight_providers alongside the widget's builder,
        same as the four already there."""
        profile_name = "there"
        if self.context.profiles is not None:
            active_profile = self.context.profiles.get_active_profile()
            if active_profile is not None:
                profile_name = active_profile.name

        events_today_count = 0
        if self.context.calendar is not None:
            today_iso = date.today().isoformat()
            events_today_count = len(calendar_events_today(self.context.calendar.all_events(), today_iso))

        unread_notification_count = self.context.notifications.unread_count() if self.context.notifications else 0

        latest_memory_line = None
        if self.context.memories is not None:
            recaps = self.context.memories.all_recaps()
            if recaps:
                latest_memory_line = recaps[0].expedition.name

        highlights = self._widget_highlights() + build_stat_highlights(events_today_count, unread_notification_count)
        return build_startup_briefing(profile_name, datetime.now(), highlights, latest_memory_line)

    def _speak_briefing(self) -> None:
        """Fire-and-forget, same pattern as modules/assistant/module.py's
        _speak() — degrades silently (logged in VoiceManager) if TTS
        isn't available, never blocks construction of this widget."""
        if self.context.voice is None:
            return
        output_path = Path(tempfile.gettempdir()) / "mia_startup_briefing.wav"
        self._tts_worker = TTSWorker(self.context.voice, self._briefing_label.text(), output_path)
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.start()

    def _on_tts_finished(self) -> None:
        if self._tts_worker is not None:
            self._tts_worker.deleteLater()
            self._tts_worker = None

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
        """Only refreshes widgets that are actually currently built —
        `self._widget_bodies` reflects whatever
        context.dashboard_widgets.enabled_widgets_in_order() produced
        last, so a disabled widget's refresh is simply skipped rather
        than erroring on a body label that doesn't exist."""
        if "power" in self._widget_bodies:
            self._refresh_power()
        if "mission" in self._widget_bodies:
            self._refresh_mission()
        if "current_project" in self._widget_bodies:
            self._refresh_current_project()
        if "volume" in self._widget_bodies:
            self._refresh_volume()

    def _refresh_power(self) -> None:
        status = self.context.power.read() if self.context.power else None
        self._widget_bodies["power"].setText(format_power_line(status))

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
        self._widget_bodies["mission"].setText(format_active_mission_line(mission, completed, total))

    def _refresh_current_project(self) -> None:
        project = None
        active_count = 0
        if self.context.projects is not None:
            active_projects = [p for p in self.context.projects.all_projects() if p.status != "Complete"]
            active_count = len(active_projects)
            if active_projects:
                project = active_projects[0]
        self._widget_bodies["current_project"].setText(format_current_project_line(project, active_count))

    def _refresh_volume(self) -> None:
        if self._volume_slider is None or self._mute_button is None:
            return
        available = self.context.volume is not None and self.context.volume.is_available()
        status = self.context.volume.read() if available else None
        self._widget_bodies["volume"].setText(format_volume_line(status))
        self._volume_slider.setEnabled(available)
        self._mute_button.setEnabled(available)
        if status is not None and not self._volume_slider.isSliderDown():
            self._volume_slider.setValue(status.percent)

    def _on_volume_slider_released(self) -> None:
        if self._volume_slider is None:
            return
        if self.context.volume is not None:
            self.context.volume.set_volume(self._volume_slider.value())
        self._refresh_volume()

    def _on_mute_clicked(self) -> None:
        if self.context.volume is not None:
            self.context.volume.toggle_mute()
        self._refresh_volume()
