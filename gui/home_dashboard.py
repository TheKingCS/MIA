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
`_speak()` runs the greeting through `core/tts_worker.py` (same
fire-and-forget QThread pattern `modules/assistant/module.py` already
uses for spoken replies) once, right after construction — the same
`_speak()` also used for the chat bar's replies below (2026-07-19).
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

**2026-07-16: Companion Avatar widget** — a new registered dashboard
widget (`avatar_camera`) showing a live camera feed via
`gui/widgets/avatar_camera_widget.py`, built for VMagicMirror's Virtual
Camera Output but generic to any virtual-camera source (see
`core/avatar_manager.py`'s docstring for why no VMagicMirror-specific
code exists at all). Device selection lives in the widget's own "⋯"
menu (`_avatar_camera_menu_actions()`), same self-contained-config
pattern as the Volume widget's mute button — no Settings-module page
needed. Unverified end-to-end in this dev sandbox (no camera devices
exist here, and VMagicMirror only runs on Windows) — re-test on the
real machine once VMagicMirror's Virtual Camera Output is enabled.
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
    QLineEdit,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.activity_log_manager import ActivityLogEntry
from core.app_context import AppContext
from core.assistant_chat import (
    build_chat_request,
    build_memory_extraction_prompt,
    build_title_generation_prompt,
    clean_generated_title,
    parse_extracted_memories,
    split_safe_tool_calls,
)
from core.chat_worker import ChatWorker
from core.conversation_manager import DEFAULT_TITLE
from core.daily_occasions import calendar_events_today
from core.dashboard_widgets import WidgetDescriptor
from core.finance_manager import FinancialSnapshot
from core.homestead_manager import HomesteadSnapshot
from core.data_logger_manager import Reading
from core.maintenance_manager import (
    MaintenanceTask,
    days_until_due,
    is_meter_task_due,
    is_overdue,
    is_sensor_task_due,
)
from core.generate_worker import GenerateWorker
from core.llm_manager import ChatReply
from core.mission_manager import Mission
from core.power_manager import PowerStatus
from core.project_manager import Project
from core.push_to_talk_trigger import PushToTalkTrigger
from core.startup_briefing import build_stat_highlights, build_startup_briefing
from core.tts_worker import TTSWorker
from core.volume_manager import VolumeStatus
from gui.dashboard_customize_dialog import DashboardCustomizeDialog
from gui.widgets.avatar_camera_widget import AvatarCameraWidget
from gui.widgets.toggle_switch import ToggleSwitch

_DATA_REFRESH_MS = 5000  # matches modules/power/module.py's own polling cadence
_CLOCK_TICK_MS = 1000
_ACTIVITY_LOG_LIMIT = 3

# Widgets that should span more than one grid column — everything else
# defaults to span 1. 2026-07-15 "ForMIA" handoff: Activity Log is a
# full-width "log/feed" card per WIDGET_STENCIL.md.
_WIDGET_COLUMN_SPANS: dict[str, int] = {
    "activity_log": 3,
    # A live camera feed reads as cramped at the default 1-column card
    # width every other widget uses.
    "avatar_camera": 2,
}
_GRID_COLUMNS = 3

# core.finance_manager.FinancialSnapshot.source values these widgets
# look up. "real_estate_portfolio" is confirmed directly from
# docs/VISION.md's worked example export. "kraken_trading_agent" is
# this project's own best-guess placeholder — the real Kraken agent's
# exact source tag isn't confirmed anywhere yet (see
# core/finance_manager.py's docstring); re-verify this string against
# the actual Kraken export code once it's available, and update it
# here (and in any already-dropped-in real snapshot files) if it
# differs.
_REAL_ESTATE_SOURCE = "real_estate_portfolio"
_KRAKEN_SOURCE = "kraken_trading_agent"
# Confirmed directly from mia-homestead's own
# viewer/export_home_snapshot.py — unlike Kraken's guessed tag above,
# this one is real since both sides of this integration are this
# user's own projects.
_HOMESTEAD_SOURCE = "mia_homestead"


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
    return f"{mission.name}  —  {completed} of {total} objectives complete"


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


def format_activity_log_line(entries: list[ActivityLogEntry]) -> str:
    """Pure formatting logic — testable without Qt. Matches the
    "ForMIA" design handoff's log/feed stencil: "HH:MM summary //
    HH:MM summary". `entries` is expected newest-first (same order
    core.activity_log_manager.ActivityLogManager.recent() returns)."""
    if not entries:
        return "No recent activity."
    return "  //  ".join(f"{entry.timestamp[11:16]} {entry.summary}" for entry in entries)


def format_real_estate_line(snapshot: Optional[FinancialSnapshot]) -> str:
    """Pure formatting logic — testable without Qt. Reads
    docs/VISION.md's documented real-estate export shape directly
    (`summary.total_equity`/`monthly_cash_flow`) — this is the one
    fully-confirmed worked example, unlike Kraken's (see
    format_kraken_line() below)."""
    if snapshot is None:
        return "No snapshot imported yet."
    summary = snapshot.data.get("summary", {})
    equity = summary.get("total_equity")
    if equity is None:
        return "Snapshot imported, but no summary data found."
    line = f"${equity:,.0f} equity"
    cash_flow = summary.get("monthly_cash_flow")
    if cash_flow is not None:
        line += f"  —  ${cash_flow:,.0f}/mo cash flow"
    return line


def format_kraken_line(snapshot: Optional[FinancialSnapshot]) -> str:
    """Pure formatting logic — testable without Qt. Deliberately reads
    only the fields docs/VISION.md documents as *shared* between both
    export sources (summary.total_value/gain_loss_pct) — the real
    Kraken agent's exact export schema isn't confirmed yet (see
    core/finance_manager.py's docstring), so this degrades to "no
    summary data" rather than assuming any field beyond that shared
    shape is actually present."""
    if snapshot is None:
        return "No snapshot imported yet."
    summary = snapshot.data.get("summary", {})
    total_value = summary.get("total_value")
    if total_value is None:
        return "Snapshot imported, but no summary data found."
    line = f"${total_value:,.0f}"
    gain_loss_pct = summary.get("gain_loss_pct")
    if gain_loss_pct is not None:
        sign = "+" if gain_loss_pct >= 0 else ""
        line += f"  ({sign}{gain_loss_pct:.1f}%)"
    return line


def format_net_worth_line(snapshots: list[FinancialSnapshot]) -> str:
    """Pure formatting logic — testable without Qt. Deliberately sums
    each snapshot's own `summary.total_value` rather than reusing any
    snapshot's self-reported `combined_net_worth` field — per
    docs/VISION.md, that field is the real-estate export's own
    approximation using manually-entered placeholder values for
    whatever it didn't have real data for, not a value meant to be
    re-summed across sources. Snapshots missing `total_value` are
    excluded (not treated as zero) and the source count is shown so
    this never silently overstates itself as more complete than it is."""
    contributions = [
        (snapshot.source, snapshot.data.get("summary", {}).get("total_value")) for snapshot in snapshots
    ]
    contributions = [(source, value) for source, value in contributions if value is not None]
    if not contributions:
        return "No financial snapshots imported yet."
    total = sum(value for _, value in contributions)
    count = len(contributions)
    noun = "source" if count == 1 else "sources"
    return f"${total:,.0f}  —  from {count} {noun}"


def format_homestead_line(snapshot: Optional[HomesteadSnapshot]) -> str:
    """Pure formatting logic — testable without Qt. Reads
    mia-homestead's `viewer/export_home_snapshot.py` shape directly
    (`docs/MIA_HOME_SYNC_PLAN.md` in that repo). Leads with the most
    urgent real fact — a critical alert beats a warning beats "all
    clear plus this week's yield" — matching this dashboard's general
    "surface the summary before the detail" stance for glance-level
    widgets, same reasoning as format_power_line's plugged-in/on-battery
    lead. Alert messages are module-authored and can run long, so the
    widget line is capped rather than risking a card that grows to fit
    one unusually verbose alert."""
    if snapshot is None:
        return "No snapshot imported yet."
    summary = snapshot.data.get("summary", {})
    critical = summary.get("critical_alert_count")
    if critical is None:
        return "Snapshot imported, but no summary data found."
    if critical:
        noun = "critical alert" if critical == 1 else "critical alerts"
        line = f"{critical} {noun}"
        top_alert = snapshot.data.get("top_alert") or {}
        message = top_alert.get("message")
        if message:
            if len(message) > 60:
                message = message[:57] + "..."
            line += f"  —  {message}"
        return line
    warning = summary.get("warning_alert_count") or 0
    if warning:
        noun = "warning" if warning == 1 else "warnings"
        return f"{warning} {noun}, no critical alerts"
    yield_kg = summary.get("yield_this_week_kg")
    if yield_kg is not None:
        return f"All clear  —  {yield_kg:.1f} kg harvested this week"
    return "All clear"


_MAINTENANCE_DUE_SOON_DAYS = 7


def format_maintenance_line(
    tasks: list[MaintenanceTask],
    today: date,
    readings_by_task: Optional[dict[str, list[Reading]]] = None,
) -> str:
    """Pure formatting logic — testable without Qt. Leads with overdue
    (most urgent), then due-soon, then an honest "all caught up" —
    same "surface the summary before the detail" stance as
    format_homestead_line/format_power_line above. Never fabricates a
    count from an empty task list; "no tasks tracked yet" is a
    distinct, honest state from "all caught up".

    readings_by_task supplies logged meter/sensor readings per
    task_id — only consulted for non-calendar tasks (calendar tasks
    ignore it entirely). Meter/sensor tasks only ever contribute to the
    "overdue" bucket here, not "due soon" — there's no day-based unit to
    measure "soon" against for a cumulative meter or a threshold
    reading, so this deliberately doesn't guess one."""
    if not tasks:
        return "No maintenance tasks tracked yet."

    readings_by_task = readings_by_task or {}
    overdue = 0
    due_soon = 0
    for task in tasks:
        if task.trigger_type == "calendar":
            remaining = days_until_due(task, today)
            if remaining is None:
                continue
            if remaining < 0:
                overdue += 1
            elif remaining <= _MAINTENANCE_DUE_SOON_DAYS:
                due_soon += 1
        elif task.is_meter_task:
            if is_meter_task_due(task, readings_by_task.get(task.task_id, [])):
                overdue += 1
        elif task.is_sensor_task:
            if is_sensor_task_due(task, readings_by_task.get(task.task_id, [])):
                overdue += 1

    if overdue:
        noun = "task" if overdue == 1 else "tasks"
        line = f"{overdue} overdue {noun}"
        if due_soon:
            line += f", {due_soon} due soon"
        return line
    if due_soon:
        noun = "task" if due_soon == 1 else "tasks"
        return f"{due_soon} {noun} due within {_MAINTENANCE_DUE_SOON_DAYS} days"
    return "All caught up"


class HomeDashboard(QFrame):
    """The post-login home screen — see module docstring."""

    open_apps_requested = Signal()

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setObjectName("HomeDashboard")
        self._tts_worker: Optional[TTSWorker] = None
        self._worker: Optional[ChatWorker] = None
        self._title_worker: Optional[GenerateWorker] = None
        self._memory_worker: Optional[GenerateWorker] = None
        self._conversation = None
        self._recording = False
        self._widget_bodies: dict[str, QLabel] = {}
        self._volume_slider: Optional[QSlider] = None
        self._mute_button: Optional[QPushButton] = None
        self._avatar_camera_widget: Optional[AvatarCameraWidget] = None
        self._widget_builders = {
            "power": self._build_power_widget,
            "mission": self._build_mission_widget,
            "volume": self._build_volume_widget,
            "current_project": self._build_current_project_widget,
            "activity_log": self._build_activity_log_widget,
            "quick_bus": self._build_quick_bus_widget,
            "avatar_camera": self._build_avatar_camera_widget,
            "real_estate": self._build_real_estate_widget,
            "kraken_agent": self._build_kraken_agent_widget,
            "net_worth": self._build_net_worth_widget,
            "homestead": self._build_homestead_widget,
            "maintenance": self._build_maintenance_widget,
        }
        self._widget_highlight_providers: dict[str, Callable[[], Optional[str]]] = {
            "power": self._power_highlight,
            "mission": self._mission_highlight,
            "volume": self._volume_highlight,
            "current_project": self._current_project_highlight,
            "homestead": self._homestead_highlight,
            # real_estate/kraken_agent/net_worth deliberately have no
            # highlight provider yet — same reasoning as
            # activity_log/quick_bus below: this is genuinely new,
            # possibly-empty data (no snapshot imported at all is the
            # common case until the user actually drops an export file
            # in), not yet a meaningful spoken-briefing highlight.
            # activity_log/quick_bus deliberately have no highlight
            # provider — "3 recent activity items" isn't a meaningful
            # spoken briefing highlight the way a mission/project count
            # is, same reasoning as volume's None provider below.
        }

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(24)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        outer.addLayout(self._build_overview_row())
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

        widgets_label = QLabel("WIDGETS")
        widgets_label.setObjectName("DashboardOverlineLabel")
        outer.addWidget(widgets_label)
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

        outer.addWidget(self._build_chat_bar())

        # GPIO path is a no-op unless voice.push_to_talk_gpio_pin is
        # configured and gpiozero + real hardware are present — see
        # core/push_to_talk_trigger.py. Both paths fire the exact same
        # handlers as the on-screen Talk button, same precedent as
        # modules/assistant/module.py's own wiring.
        self._ptt_trigger = PushToTalkTrigger(self.context, parent=self)
        self._ptt_trigger.pressed.connect(self._on_talk_pressed)
        self._ptt_trigger.released.connect(self._on_talk_released)

        self.context.conversations.start_new_active_conversation()
        self._speak(self._briefing_label.text())

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
        if self._avatar_camera_widget is not None:
            self._avatar_camera_widget.stop()
        self.context.events.unsubscribe("dashboard.widgets_changed", self._on_widgets_changed)

    def showEvent(self, event) -> None:
        """
        2026-07-18: real "sizing issue with the dashboard widgets when
        going from the Assistant to the Home Screen" report. Root
        cause: `_data_timer` keeps firing every `_DATA_REFRESH_MS`
        regardless of whether this widget is the currently-visible
        stack page (`gui/main_window.py`'s `QStackedWidget` just hides
        it, doesn't stop it) — and `_set_widget_body_text()`'s
        min-height recompute reads `label.width()` at whatever moment
        the timer happens to fire. If that's while this page is
        hidden, or right in the middle of the stack/scroll-area
        settling into its new geometry after a page switch, the width
        read can be stale, producing a wrong minimum height that then
        persists — visibly clipped/oversized card text — until the
        next 5-second tick happens to catch a good width. Forcing a
        refresh on every showEvent() (real Qt event fired exactly when
        this page becomes visible again, width already final by then)
        means the correction is immediate instead of "eventually,
        maybe up to 5 seconds later."
        """
        super().showEvent(event)
        self._refresh_data()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_overview_row(self) -> QHBoxLayout:
        """The "SYSTEM OVERVIEW" / "● ALL SYSTEMS NOMINAL" header row —
        a real gap found re-comparing against the ForMIA mockup
        (`Dashboard.dc.html`), missing entirely before this pass. The
        status chip is static ambient copy, same precedent as
        gui/main_window.py's own status-bar default message ("M.I.A.
        core online.") — not a live health check standing behind it."""
        row = QHBoxLayout()
        overview_label = QLabel("SYSTEM OVERVIEW")
        overview_label.setObjectName("DashboardOverlineLabel")
        row.addWidget(overview_label)
        row.addStretch()
        status_chip = QLabel("● ALL SYSTEMS NOMINAL")
        status_chip.setObjectName("DashboardStatusChip")
        row.addWidget(status_chip)
        return row

    def _build_clock(self) -> QWidget:
        """A real card (eyebrow "CLOCK" label + big time, left; date,
        right) — re-comparing against the ForMIA mockup found this had
        shipped as a bare centered label stack with no card/eyebrow at
        all, unlike every other widget's card treatment."""
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)

        time_column = QVBoxLayout()
        time_column.setSpacing(6)
        clock_eyebrow = QLabel("CLOCK")
        clock_eyebrow.setObjectName("DashboardSectionTitle")
        time_column.addWidget(clock_eyebrow)

        self._clock_time_label = QLabel()
        self._clock_time_label.setObjectName("DashboardClockTime")
        time_column.addWidget(self._clock_time_label)
        layout.addLayout(time_column)
        layout.addStretch()

        self._clock_date_label = QLabel()
        self._clock_date_label.setObjectName("DashboardClockDate")
        self._clock_date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self._clock_date_label)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        card.setGraphicsEffect(shadow)

        return card

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
            # 2026-07-18: real report — dashboard widgets "spaced very far
            # apart" after navigating away and back. self's outer layout
            # already guards against this at the top level (AlignTop
            # above), but this inner grid had no alignment of its own —
            # if self._widgets_container ever gets handed more height
            # than its cards need (e.g. via gui/main_window.py's
            # self._stack_scroll wrapping the whole stack), a grid with
            # no alignment set grows the gaps between fixed-size cards
            # to fill it rather than leaving it as blank margin.
            self._widgets_grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

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
        if self._avatar_camera_widget is not None:
            # A live QCamera has no Qt-parent-driven cleanup — unlike
            # every other widget cleared above, it needs an explicit
            # stop() or the device stays open after this rebuild
            # discards the card around it, same "stop before discard"
            # reasoning as gui/presence_widget.py's animation timer.
            self._avatar_camera_widget.stop()
            self._avatar_camera_widget = None

        registry = self.context.dashboard_widgets
        widgets = registry.enabled_widgets_in_order() if registry is not None else []
        row = col = 0
        for descriptor in widgets:
            builder = self._widget_builders.get(descriptor.widget_id)
            if builder is None:
                continue
            # Most widgets are span 1; a few (e.g. Activity Log) span
            # the full grid width per _WIDGET_COLUMN_SPANS — wrap to a
            # fresh row if the current one doesn't have room left,
            # rather than silently overlapping/clipping a wide card.
            span = min(_WIDGET_COLUMN_SPANS.get(descriptor.widget_id, 1), _GRID_COLUMNS)
            if col + span > _GRID_COLUMNS:
                row += 1
                col = 0
            widget = builder(descriptor)
            self._widgets_grid.addWidget(widget, row, col, 1, span)
            # A widget added to an already-visible parent's layout isn't
            # always auto-shown by Qt on every platform — confirmed via
            # a real headless-Qt test: after the first rebuild, new
            # cards reported isVisible()=False and a default unlaid-out
            # size until explicitly shown. Harmless to call this during
            # the initial construction-time build too (the parent isn't
            # shown yet then anyway).
            widget.show()
            col += span
            if col >= _GRID_COLUMNS:
                row += 1
                col = 0

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
            on_click=lambda: self._open_module("power"),
        )
        self._widget_bodies["power"] = body
        return card

    def _build_mission_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("missions"),
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
            on_click=lambda: self._open_module("toolbox"),
        )
        self._widget_bodies["current_project"] = body
        return card

    def _build_real_estate_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        # No on_click — there's no dedicated Finance module/screen to
        # open yet (this pass is dashboard-only, per docs/ROADMAP.md),
        # same reasoning Activity Log's card has none.
        card, body = self._build_simple_card(descriptor.icon, descriptor.display_name)
        self._widget_bodies["real_estate"] = body
        return card

    def _build_kraken_agent_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(descriptor.icon, descriptor.display_name)
        self._widget_bodies["kraken_agent"] = body
        return card

    def _build_net_worth_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(descriptor.icon, descriptor.display_name)
        self._widget_bodies["net_worth"] = body
        return card

    def _build_homestead_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        # No on_click — same reasoning as real_estate/kraken_agent
        # above: no dedicated Homestead module/screen exists in this
        # repo (the real detail view is mia-homestead's own
        # viewer/dashboard.html, a separate project/machine, not
        # something this dashboard opens).
        card, body = self._build_simple_card(descriptor.icon, descriptor.display_name)
        self._widget_bodies["homestead"] = body
        return card

    def _build_maintenance_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("maintenance"),
        )
        self._widget_bodies["maintenance"] = body
        return card

    def _build_volume_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        # No on_click here — the dedicated mute button already covers
        # this widget's one real action, and there's no related module
        # to open (unlike Power/Mission/Current Project); making the
        # whole card a button would conflict with the slider/mute
        # button already living inside it.
        card, body, slider, mute_button = self._build_volume_card(descriptor.icon, descriptor.display_name)
        self._widget_bodies["volume"] = body
        self._volume_slider = slider
        self._mute_button = mute_button
        return card

    def _build_activity_log_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(descriptor.icon, descriptor.display_name)
        # The "ForMIA" stencil's log/feed variant is monospace, unlike
        # every other widget's body text — a distinct object name so
        # gui/styles.py can style just this one differently.
        body.setObjectName("DashboardActivityLogBody")
        self._widget_bodies["activity_log"] = body
        return card

    def _build_quick_bus_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        """The one widget with no single body label — see
        core/notification_manager.py's notify() and
        modules/assistant/module.py's _on_talk_pressed() for the real
        (not cosmetic) behavior these two toggles gate, per the "ForMIA"
        handoff's explicit "wire to real feature flags" instruction."""
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(self._build_widget_header(descriptor.icon, descriptor.display_name))

        layout.addLayout(self._build_toggle_row(
            "Voice input",
            self.context.config.get("voice.push_to_talk_enabled", True),
            self._on_voice_input_toggled,
        ))
        layout.addLayout(self._build_toggle_row(
            "Notifications",
            self.context.config.get("notifications.enabled", True),
            self._on_notifications_toggled,
        ))
        layout.addStretch()
        return card

    def _build_avatar_camera_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        """A live camera feed of a VMagicMirror-rendered companion
        avatar (or any other virtual-camera source) — see
        core/avatar_manager.py's docstring for the full reasoning.
        Unlike every other widget here, this one starts/stops a real
        QCamera rather than just reading a config value or polling a
        manager, so it's built once at construction (and again on
        camera selection) rather than on the 5s _refresh_data() timer —
        restarting a camera every 5 seconds would be wasteful and would
        visibly glitch the feed, same reasoning quick_bus's toggles
        already established for skipping that poll."""
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addLayout(
            self._build_widget_header(
                descriptor.icon, descriptor.display_name, menu_actions=self._avatar_camera_menu_actions()
            )
        )

        self._avatar_camera_widget = AvatarCameraWidget()
        layout.addWidget(self._avatar_camera_widget, stretch=1)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        card.setGraphicsEffect(shadow)

        self._refresh_avatar_camera()
        return card

    def _avatar_camera_menu_actions(self) -> list[tuple[str, Callable[[], None]]]:
        if self.context.avatar is None:
            return []
        devices = self.context.avatar.list_devices()
        if not devices:
            return [("No cameras found", lambda: None)]
        return [
            (f"Use {device.description}", lambda _checked=False, d=device: self._on_avatar_camera_selected(d))
            for device in devices
        ]

    def _on_avatar_camera_selected(self, device) -> None:
        if self.context.avatar is not None:
            self.context.avatar.set_selected_device_id(device.device_id)
        self._refresh_avatar_camera()

    def _refresh_avatar_camera(self) -> None:
        if self._avatar_camera_widget is None or self.context.avatar is None:
            return
        if not self.context.avatar.is_available():
            self._avatar_camera_widget.show_unavailable()
            return
        device_id = self.context.avatar.selected_device_id()
        if device_id is None:
            self._avatar_camera_widget.show_not_selected()
            return
        self._avatar_camera_widget.start(device_id)

    def _build_toggle_row(self, label_text: str, checked: bool, on_toggled: Callable[[bool], None]) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setObjectName("DashboardSectionBody")
        row.addWidget(label)
        row.addStretch()
        toggle = ToggleSwitch()
        toggle.setChecked(checked)
        toggle.toggled.connect(on_toggled)
        row.addWidget(toggle)
        return row

    def _on_voice_input_toggled(self, checked: bool) -> None:
        self.context.config.set("voice.push_to_talk_enabled", checked)
        self.context.config.save()

    def _on_notifications_toggled(self, checked: bool) -> None:
        self.context.config.set("notifications.enabled", checked)
        self.context.config.save()

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
        self, icon: str, title: str, on_click: Optional[Callable[[], None]] = None
    ) -> tuple[QFrame, QLabel]:
        """Builds one icon+title+body card and returns (card, body_label)
        — the widget builders above add it to the grid themselves.

        **2026-07-16**: replaces the old "⋯" menu-button-with-one-item
        pattern (which just opened the card's related module page) with
        the whole card being clickable, per the user's explicit ask:
        "Instead of the menu buttons on the widgets I want to be able to
        click on a widget like a button and it bring me to its
        page/menu while still displaying the data it needs to." When
        `on_click` is given, the card itself is a `QPushButton` (same
        "QPushButton with QLabel children, no text of its own" shape as
        `gui/widgets/module_button.py`'s `ModuleButton` and
        `gui/widgets/conversation_card.py`'s `ConversationCard` — avoids
        that pattern's documented Qt bug where `:hover` on a descendant
        QLabel makes its text vanish, by only ever styling the button
        itself in QSS, never a QLabel inside it). Widgets with no
        related page to open (Activity Log, Real Estate, Kraken Agent,
        Net Worth — see each builder's own comment) pass no `on_click`
        and get the original plain, non-clickable `QFrame` card.
        """
        card: QWidget
        if on_click is not None:
            card = QPushButton()
            card.setObjectName("DashboardCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setToolTip(f"Open {title}")
            card.clicked.connect(on_click)
            # Confirmed via a real headless-Qt screenshot, not assumed:
            # a bare QPushButton relying on its children's natural
            # sizeHint collapses to a sliver on this platform (same
            # "This plugin does not support propagateSizeHints()" Qt
            # bug gui/widgets/conversation_card.py's docstring already
            # documents) — a plain QFrame card never had this problem,
            # only the new clickable QPushButton variant.
            card.setMinimumHeight(96)
        else:
            card = QFrame()
            card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        layout.addLayout(self._build_widget_header(icon, title))

        body_label = QLabel()
        body_label.setObjectName("DashboardSectionBody")
        body_label.setWordWrap(True)
        # A QLabel can't receive mouse events meant for its QPushButton
        # parent's click — but it doesn't need to: word-wrapped body
        # text under a click-through label already works fine for
        # ModuleButton's description label, same shape here.
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

        # 2026-07-16: this used to show a bare, never-updated "🔇"
        # regardless of actual mute state — the user couldn't tell what
        # it did or whether they were currently muted. _refresh_volume()
        # now swaps the icon (🔊 unmuted / 🔇 muted) and sets an explicit
        # tooltip on every refresh, same "state should be visible, not
        # just clickable" bar the recording-state Talk button and the
        # notification bell's hasUnread accent already set elsewhere.
        mute_button = QPushButton("\U0001F50A")
        mute_button.setObjectName("HeaderButton")
        mute_button.setToolTip("Mute")
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

    def _homestead_highlight(self) -> Optional[str]:
        """Unlike the other finance-style snapshot widgets, this one
        DOES get a highlight provider — a critical greenhouse alert is
        exactly the kind of proactive, briefing-worthy fact
        docs/VISION.md's Startup Dashboard Briefing exists for (unlike
        net worth, which nothing about it is actionable at a glance).
        Deliberately silent on warnings/all-clear/no-snapshot-yet —
        only a real critical count is worth interrupting the briefing
        for, same "silent unless it matters" restraint as the other
        providers above returning None for their non-notable states."""
        if self.context.homestead is None:
            return None
        snapshot = self.context.homestead.latest_snapshot(_HOMESTEAD_SOURCE)
        if snapshot is None:
            return None
        critical = snapshot.data.get("summary", {}).get("critical_alert_count")
        if not critical:
            return None
        noun = "critical alert" if critical == 1 else "critical alerts"
        return f"{critical} {noun} at the greenhouse"

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

    # ------------------------------------------------------------------
    # Chat bar — same shared core.assistant_chat/core.chat_worker logic
    # as gui/character_panel.py and modules/assistant/module.py. Kept on
    # this screen alongside the always-visible sidebar Assistant chat
    # (restored 2026-07-19) as a real, already-built second surface, not
    # a duplicate to remove — same "keep both chat surfaces" precedent
    # as the 2026-07-14 aesthetic pass part 4 decision.
    # ------------------------------------------------------------------

    def _build_chat_bar(self) -> QWidget:
        # No suggestion chips here (unlike the full-width console this
        # bar was originally added for) — the always-visible sidebar
        # (gui/character_panel.py, restored 2026-07-19) already shows
        # its own suggested prompts, and with the sidebar now
        # permanently taking width, an extra chip row here forced this
        # whole screen into an unwanted horizontal scrollbar (found via
        # a real screenshot at 1491px, not assumed).
        bar = QFrame()
        bar.setObjectName("DashboardChatBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("HeaderSearchBar")
        self._input.setPlaceholderText("Ask Mia anything…")
        self._input.returnPressed.connect(self._on_send)
        layout.addWidget(self._input, stretch=1)

        self._talk_button = QPushButton("\U0001F3A4  Hold to Talk")
        self._talk_button.setObjectName("TalkButton")
        self._talk_button.pressed.connect(self._on_talk_pressed)
        self._talk_button.released.connect(self._on_talk_released)
        layout.addWidget(self._talk_button)

        self._stop_speaking_button = QPushButton("⏹  Stop")
        self._stop_speaking_button.setObjectName("StopSpeakingButton")
        self._stop_speaking_button.setEnabled(False)
        self._stop_speaking_button.clicked.connect(self._on_stop_speaking)
        layout.addWidget(self._stop_speaking_button)

        self._send_button = QPushButton("Send")
        self._send_button.setObjectName("AppsLaunchButton")
        self._send_button.clicked.connect(self._on_send)
        layout.addWidget(self._send_button)

        return bar

    def _on_send(self) -> None:
        prompt = self._input.text().strip()
        if not prompt or self._worker is not None or self.context.llm is None:
            return

        self._input.clear()
        self._set_busy(True)
        conversation = self.context.conversations.get_or_create_active_conversation()
        self._conversation = conversation
        self.context.conversations.add_message(conversation.conversation_id, "user", prompt)

        messages, tools = build_chat_request(self.context, conversation, prompt)
        self._worker = ChatWorker(self.context.llm, messages, tools)
        self._worker.result_ready.connect(self._on_reply)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_reply(self, reply: Optional[ChatReply]) -> None:
        if reply is None:
            return

        conversation = self._conversation

        if reply.tool_calls:
            calls_to_execute, skipped_calls = split_safe_tool_calls(reply.tool_calls, self.context.assistant_actions)
            if skipped_calls:
                skipped_names = ", ".join(tc.name for tc in skipped_calls)
                self.context.conversations.add_message(
                    conversation.conversation_id,
                    "assistant",
                    f"(Skipped a possibly unintended action for safety: {skipped_names}. Ask for that on its own if you really want it.)",
                )
            for tool_call in calls_to_execute:
                confirmation = self.context.assistant_actions.execute(self.context, tool_call.name, tool_call.arguments)
                self.context.conversations.add_message(conversation.conversation_id, "assistant", confirmation)
                self._speak(confirmation)
            return

        user_message = conversation.messages[-1].content if conversation.messages else ""
        self.context.conversations.add_message(conversation.conversation_id, "assistant", reply.content)
        self._speak(reply.content)
        self._maybe_generate_title(conversation, user_message, reply.content)
        self._extract_memories(conversation, user_message)

    def _on_worker_finished(self) -> None:
        self._set_busy(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        self._talk_button.setEnabled(not busy)

    def _maybe_generate_title(self, conversation, user_message: str, assistant_message: str) -> None:
        if conversation.title != DEFAULT_TITLE or self._title_worker is not None:
            return
        prompt = build_title_generation_prompt(user_message, assistant_message)
        self._title_worker = GenerateWorker(self.context.llm, prompt)
        conversation_id = conversation.conversation_id
        self._title_worker.result_ready.connect(lambda raw: self._on_title_generated(conversation_id, raw))
        self._title_worker.finished.connect(self._on_title_worker_finished)
        self._title_worker.start()

    def _on_title_generated(self, conversation_id: str, raw_title: Optional[str]) -> None:
        title = clean_generated_title(raw_title)
        if title is not None:
            self.context.conversations.set_title(conversation_id, title)

    def _on_title_worker_finished(self) -> None:
        if self._title_worker is not None:
            self._title_worker.deleteLater()
            self._title_worker = None

    def _extract_memories(self, conversation, user_message: str) -> None:
        if self._memory_worker is not None or self.context.user_memories is None:
            return
        prompt = build_memory_extraction_prompt(user_message)
        self._memory_worker = GenerateWorker(self.context.llm, prompt)
        conversation_id = conversation.conversation_id
        self._memory_worker.result_ready.connect(lambda raw: self._on_memories_extracted(conversation_id, raw))
        self._memory_worker.finished.connect(self._on_memory_worker_finished)
        self._memory_worker.start()

    def _on_memories_extracted(self, conversation_id: str, raw_text: Optional[str]) -> None:
        for fact in parse_extracted_memories(raw_text):
            self.context.user_memories.add_memory(fact, source_conversation_id=conversation_id)

    def _on_memory_worker_finished(self) -> None:
        if self._memory_worker is not None:
            self._memory_worker.deleteLater()
            self._memory_worker = None

    def _speak(self, text: str) -> None:
        if self.context.voice is None or self._tts_worker is not None:
            return
        output_path = Path(tempfile.gettempdir()) / "mia_dashboard_reply.wav"
        self._tts_worker = TTSWorker(self.context.voice, text, output_path)
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.start()
        self._stop_speaking_button.setEnabled(True)

    def _on_tts_finished(self) -> None:
        if self._tts_worker is not None:
            self._tts_worker.deleteLater()
            self._tts_worker = None
        self._stop_speaking_button.setEnabled(False)

    def _on_stop_speaking(self) -> None:
        """Cuts MIA off mid-sentence — same real ask (2026-07-18) already
        answered on the full Assistant module, brought to this bar too.
        Only stops playback; synthesis (if still running) finishes
        harmlessly with nothing left to play."""
        if self.context.voice is not None:
            self.context.voice.stop_playback()

    def _on_talk_pressed(self) -> None:
        if self.context.voice is None or self._worker is not None or self._recording:
            return
        if not self.context.config.get("voice.push_to_talk_enabled", True):
            return
        if not self.context.voice.start_recording():
            return
        self._recording = True
        self._set_talk_button_recording(True)

    def _on_talk_released(self) -> None:
        if self.context.voice is None or not self._recording:
            return
        self._recording = False
        self._set_talk_button_recording(False)

        wav_path = self.context.voice.stop_recording()
        if wav_path is None:
            return

        transcript = self.context.voice.transcribe(wav_path)
        if not transcript:
            return

        self._input.setText(transcript)
        self._on_send()

    def _set_talk_button_recording(self, recording: bool) -> None:
        """Dynamic property, not a second object name — same QSS
        re-polish pattern as modules/assistant/module.py's own
        `_set_talk_button_recording()`."""
        self._talk_button.setProperty("recording", recording)
        self._talk_button.style().unpolish(self._talk_button)
        self._talk_button.style().polish(self._talk_button)

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

    def _set_widget_body_text(self, widget_id: str, text: str) -> None:
        """setText() plus an explicit height fix — word-wrapped QLabels
        have a documented Qt bug (see gui/widgets/chat_bubble.py's
        docstring for the fullest writeup): heightForWidth()/sizeHint()
        can disagree with the label's actual allocated height, clipping
        wrapped text. Confirmed here too via direct measurement (not
        assumed) once the 2026-07-16 font-size increase pushed the
        Mission card's body onto two lines for the first time: label
        height was 26px, sizeHint reported 34px. Recomputed on *every*
        call (not once at construction, unlike ChatBubble) since these
        labels' text changes on every 5s refresh."""
        label = self._widget_bodies[widget_id]
        label.setText(text)
        width = label.width()
        if width > 0:
            label.setMinimumHeight(max(label.heightForWidth(width), label.sizeHint().height()) + 4)

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
        if "activity_log" in self._widget_bodies:
            self._refresh_activity_log()
        # quick_bus has no refresh — its two toggles reflect config
        # state set at construction and via their own toggled signal,
        # not the 5s poll every other widget uses.
        if "real_estate" in self._widget_bodies:
            self._refresh_real_estate()
        if "kraken_agent" in self._widget_bodies:
            self._refresh_kraken_agent()
        if "net_worth" in self._widget_bodies:
            self._refresh_net_worth()
        if "homestead" in self._widget_bodies:
            self._refresh_homestead()
        if "maintenance" in self._widget_bodies:
            self._refresh_maintenance()

    def _refresh_real_estate(self) -> None:
        snapshot = self.context.finance.latest_snapshot(_REAL_ESTATE_SOURCE) if self.context.finance else None
        self._set_widget_body_text("real_estate", format_real_estate_line(snapshot))

    def _refresh_kraken_agent(self) -> None:
        snapshot = self.context.finance.latest_snapshot(_KRAKEN_SOURCE) if self.context.finance else None
        self._set_widget_body_text("kraken_agent", format_kraken_line(snapshot))

    def _refresh_net_worth(self) -> None:
        snapshots = self.context.finance.all_latest_snapshots() if self.context.finance else []
        self._set_widget_body_text("net_worth", format_net_worth_line(snapshots))

    def _refresh_homestead(self) -> None:
        snapshot = self.context.homestead.latest_snapshot(_HOMESTEAD_SOURCE) if self.context.homestead else None
        self._set_widget_body_text("homestead", format_homestead_line(snapshot))

    def _refresh_maintenance(self) -> None:
        if not self.context.maintenance:
            self._set_widget_body_text("maintenance", format_maintenance_line([], date.today()))
            return

        tasks = self.context.maintenance.all_tasks()
        today = date.today()
        readings_by_task = {
            task.task_id: self.context.maintenance.readings_for_task(task.task_id)
            for task in tasks
            if task.trigger_type != "calendar"
        }
        self._set_widget_body_text("maintenance", format_maintenance_line(tasks, today, readings_by_task))
        self._auto_schedule_due_maintenance(tasks, today, readings_by_task)

    def _auto_schedule_due_maintenance(
        self, tasks: list[MaintenanceTask], today: date, readings_by_task: dict[str, list[Reading]]
    ) -> None:
        """Opt-in (task.auto_schedule, off by default — see
        core/maintenance_manager.py) real Calendar event creation for a
        task that's become due and doesn't already have one. Runs on
        the same 5s tick every other dashboard widget refreshes on, no
        new timer. Silently no-ops for a task that isn't due, has
        auto_schedule off, or already has a calendar_event_id — never
        creates a duplicate event."""
        for task in tasks:
            if not task.auto_schedule or task.calendar_event_id is not None:
                continue
            if task.trigger_type == "calendar":
                due = is_overdue(task, today) or days_until_due(task, today) == 0
            elif task.is_meter_task:
                due = is_meter_task_due(task, readings_by_task.get(task.task_id, []))
            elif task.is_sensor_task:
                due = is_sensor_task_due(task, readings_by_task.get(task.task_id, []))
            else:
                due = False
            if due:
                self.context.maintenance.schedule_task(task.task_id, today.isoformat())

    def _refresh_activity_log(self) -> None:
        entries = self.context.activity_log.recent(limit=_ACTIVITY_LOG_LIMIT) if self.context.activity_log else []
        self._set_widget_body_text("activity_log", format_activity_log_line(entries))

    def _refresh_power(self) -> None:
        status = self.context.power.read() if self.context.power else None
        self._set_widget_body_text("power", format_power_line(status))

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
        self._set_widget_body_text("mission", format_active_mission_line(mission, completed, total))

    def _refresh_current_project(self) -> None:
        project = None
        active_count = 0
        if self.context.projects is not None:
            active_projects = [p for p in self.context.projects.all_projects() if p.status != "Complete"]
            active_count = len(active_projects)
            if active_projects:
                project = active_projects[0]
        self._set_widget_body_text("current_project", format_current_project_line(project, active_count))

    def _refresh_volume(self) -> None:
        if self._volume_slider is None or self._mute_button is None:
            return
        available = self.context.volume is not None and self.context.volume.is_available()
        status = self.context.volume.read() if available else None
        self._set_widget_body_text("volume", format_volume_line(status))
        self._volume_slider.setEnabled(available)
        self._mute_button.setEnabled(available)
        if status is not None and not self._volume_slider.isSliderDown():
            self._volume_slider.setValue(status.percent)

        muted = status is not None and status.muted
        self._mute_button.setText("\U0001F507" if muted else "\U0001F50A")
        self._mute_button.setToolTip("Unmute" if muted else "Mute")

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
