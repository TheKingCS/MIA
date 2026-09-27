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
format_active_mission_line() are free functions (not methods) —
testable without Qt, see tests/test_home_dashboard.py. (Volume's own
format_volume_line() moved out to gui/widgets/volume_quick_control.py
2026-07-18 along with the rest of Volume's dashboard presence — see
that module's docstring, and this file's 2026-09-11 cleanup-pass entry
below for the dead code that removal left behind here.)

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
from core.talk_it_out import after_fixed_reply, apply_followup, plan_followup, pre_turn
from core.safety_floor import detect_danger
from core.chat_worker import ChatWorker
from core.context_assembler import assemble_life_state, format_life_state_glance_line
from core.conversation_manager import DEFAULT_TITLE
from core.budget_manager import Bill, days_until_bill_due
from core.real_estate_manager import Property, equity as property_equity
from core.daily_occasions import calendar_events_today
from core.dashboard_widgets import WidgetDescriptor
from core.finance_manager import FinancialSnapshot
from core.homestead_manager import HomesteadSnapshot
from core.data_logger_manager import Reading
from core.insight_manager import Insight
from core.leveling import compute_prestige_level_progress
from core.rewards_manager import is_attributed_to
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
from core.music_manager import NowPlaying
from core.kitchen_manager import days_until_expiration
from core.power_manager import PowerStatus
from core.project_manager import Project
from core.push_to_talk_trigger import PushToTalkTrigger
from core.startup_briefing import build_stat_highlights, build_startup_briefing, greeting_for_hour
from core.tts_worker import TTSWorker
from gui.dashboard_customize_dialog import DashboardCustomizeDialog
from gui.widgets.avatar_camera_widget import AvatarCameraWidget
from gui.widgets.blueprint_frame import BlueprintFrame
from gui.widgets.glow import apply_panel_glow
from gui.widgets.photo_background_frame import PhotoBackgroundFrame
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

# Thresholds for the spoken/written briefing's own highlight providers
# (below, on HomeDashboard) — deliberately more conservative than the
# dashboard TILES' own always-show-the-latest-fact thresholds
# (format_workout_line/format_relationships_line above show ANY days-
# since-last-workout or ANY upcoming birthday, however far off), since
# a highlight is spoken/read aloud every single launch and needs a real
# "is this actually worth mentioning right now" bar, not just "is there
# data."
_BRIEFING_WORKOUT_STALE_AFTER_DAYS = 3
_BRIEFING_BIRTHDAY_LEAD_DAYS = 7  # same lead time core.smart_suggestions' gift reminder already uses


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


def format_net_worth_line(
    snapshots: list[FinancialSnapshot], property_portfolio_equity: Optional[float] = None
) -> str:
    """Pure formatting logic — testable without Qt. Deliberately sums
    each snapshot's own `summary.total_value` rather than reusing any
    snapshot's self-reported `combined_net_worth` field — per
    docs/VISION.md, that field is the real-estate export's own
    approximation using manually-entered placeholder values for
    whatever it didn't have real data for, not a value meant to be
    re-summed across sources. Snapshots missing `total_value` are
    excluded (not treated as zero) and the source count is shown so
    this never silently overstates itself as more complete than it is.

    property_portfolio_equity (2026-09-09) adds the NATIVE Real Estate
    module's own tracked-property equity as one more contribution —
    without this, a user who never imports an external real-estate/
    Kraken/Plaid snapshot saw a flatly wrong "No financial snapshots
    imported yet." even with real tracked properties. Pass None (never
    0.0) when there are no properties at all, same "missing means
    excluded, not a fabricated zero" convention every contribution here
    already follows."""
    contributions = [
        (snapshot.source, snapshot.data.get("summary", {}).get("total_value")) for snapshot in snapshots
    ]
    contributions = [(source, value) for source, value in contributions if value is not None]
    if property_portfolio_equity is not None:
        contributions.append(("property_portfolio", property_portfolio_equity))
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


def format_observations_line(open_insights: list["Insight"]) -> str:
    """Pure formatting logic — testable without Qt. Same "surface the
    summary, distinct empty-vs-caught-up states" stance as
    format_maintenance_line above — modules/observations/module.py has
    the real per-item detail; this is just the dashboard glance."""
    if not open_insights:
        return "All caught up"
    noun = "thing" if len(open_insights) == 1 else "things"
    return f"{len(open_insights)} {noun} noticed"


def format_lite_captures_line(pending_count: int) -> str:
    """Pure formatting logic — testable without Qt. Same "surface the
    summary, distinct empty-vs-caught-up states" stance as
    format_observations_line above — modules/toolbox/tools/
    lite_captures_tool.py has the real per-item review; this is just
    the dashboard glance."""
    if not pending_count:
        return "Nothing waiting"
    noun = "capture" if pending_count == 1 else "captures"
    return f"{pending_count} {noun} to review"


def format_budget_line(bills: list[Bill], today: date) -> str:
    """Pure formatting logic — testable without Qt. Same "surface the
    summary before the detail, distinct empty-vs-caught-up states" stance
    as format_maintenance_line above."""
    if not bills:
        return "No bills tracked yet."

    overdue = sum(1 for b in bills if (remaining := days_until_bill_due(b, today)) is not None and remaining < 0)
    due_today_or_later_within_week = sum(
        1 for b in bills
        if (remaining := days_until_bill_due(b, today)) is not None and 0 <= remaining <= 7
    )
    if overdue:
        noun = "bill" if overdue == 1 else "bills"
        return f"{overdue} overdue {noun}"
    if due_today_or_later_within_week:
        noun = "bill" if due_today_or_later_within_week == 1 else "bills"
        return f"{due_today_or_later_within_week} {noun} due within 7 days"
    return "All bills paid"


def format_property_portfolio_line(properties: list[Property]) -> str:
    """Pure formatting logic — testable without Qt. Total equity across
    every tracked property — the one number that answers "how's the
    portfolio doing" at a glance; per-property/cap-rate detail lives in
    the module itself, not squeezed into a dashboard card."""
    if not properties:
        return "No properties tracked yet."
    total_equity = sum(property_equity(p) for p in properties)
    noun = "property" if len(properties) == 1 else "properties"
    return f"{len(properties)} {noun}  —  ${total_equity:,.0f} total equity"


def format_music_line(now_playing: Optional[NowPlaying]) -> str:
    """Pure formatting logic — testable without Qt. Deliberately terse
    (title + artist only, no position/duration) — this is a glance
    card, not a transport bar; modules/music/module.py's own
    format_now_playing_line() covers the fuller live view, one click
    away via this card's on_click."""
    if now_playing is None:
        return "Nothing playing"
    artist_part = f" — {now_playing.artist}" if now_playing.artist else ""
    state = "Playing" if now_playing.is_playing else "Paused"
    return f"{state}: {now_playing.title}{artist_part}"


def format_kitchen_line(expiring_count: int, makeable_count: int, has_pantry: bool) -> str:
    """Pure formatting logic — testable without Qt. Leads with the
    most urgent real fact, same "critical beats routine status"
    precedent format_homestead_line() already established: pantry
    items expiring within 3 days first (a real, actionable nudge),
    else how many recipes are fully makeable right now, else an honest
    "nothing tracked yet" for a pantry with zero items — never a
    fabricated "0 recipes ready" when there's no real data behind it."""
    if expiring_count > 0:
        noun = "item" if expiring_count == 1 else "items"
        return f"{expiring_count} pantry {noun} expiring soon"
    if not has_pantry:
        return "No pantry items tracked yet"
    noun = "recipe" if makeable_count == 1 else "recipes"
    return f"{makeable_count} {noun} ready to make right now"


def format_workout_line(last_session_date: Optional[str], today: date) -> str:
    """Pure formatting logic — testable without Qt. Leads with days
    since the last logged session — a real, honest nudge — else "No
    workouts logged yet" for a fresh install, same
    format_kitchen_line()/format_homestead_line() "critical/actionable
    fact first, never a fabricated status" precedent."""
    if not last_session_date:
        return "No workouts logged yet"
    try:
        days = (today - date.fromisoformat(last_session_date)).days
    except ValueError:
        return "No workouts logged yet"
    if days <= 0:
        return "Worked out today"
    noun = "day" if days == 1 else "days"
    return f"{days} {noun} since last workout"


def format_relationships_line(nearest_birthday: Optional[tuple]) -> str:
    """Pure formatting logic — testable without Qt. nearest_birthday is
    (Person, days_until) or None — the real fact this widget leads
    with, same "one real, actionable fact" precedent as
    format_workout_line()/format_kitchen_line()."""
    if nearest_birthday is None:
        return "No birthdays tracked yet"
    person, days = nearest_birthday
    if days == 0:
        return f"{person.name}'s birthday is today!"
    noun = "day" if days == 1 else "days"
    return f"{person.name}'s birthday in {days} {noun}"


def format_dashboard_hero_tagline(level: int, missions_available: int, active_projects: int) -> str:
    """Pure formatting logic — testable without Qt. Multi-user pass
    (2026-09-14, personalized dashboard slice) — replaces the generic
    "Another day to build the life you want." with the active
    profile's own real numbers, the vision doc's own "Level 14 · 3
    missions available · 2 active projects" example. Deliberately
    omits "recipes mastered"/streak-style metrics this pass — there's
    no defined "mastered" threshold anywhere in this codebase yet, and
    inventing one here would be a fabricated number, not a real one."""
    return f"Level {level} · {missions_available} missions available · {active_projects} active projects"


def format_party_activity_line(profile_name: str, mission_name: str) -> str:
    """Pure formatting logic — testable without Qt. The vision doc's
    own "Zac completed 'Mow the Homestead'" example."""
    return f"{profile_name} completed \"{mission_name}\""


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
        self._interview_memory_worker: Optional[GenerateWorker] = None
        self._capture_memory_worker: Optional[GenerateWorker] = None
        self._conversation = None
        self._recording = False
        self._widget_bodies: dict[str, QLabel] = {}
        self._avatar_camera_widget: Optional[AvatarCameraWidget] = None
        self._widget_builders = {
            "power": self._build_power_widget,
            "mission": self._build_mission_widget,
            "current_project": self._build_current_project_widget,
            "activity_log": self._build_activity_log_widget,
            "quick_bus": self._build_quick_bus_widget,
            "avatar_camera": self._build_avatar_camera_widget,
            "real_estate": self._build_real_estate_widget,
            "kraken_agent": self._build_kraken_agent_widget,
            "net_worth": self._build_net_worth_widget,
            "homestead": self._build_homestead_widget,
            "maintenance": self._build_maintenance_widget,
            "budget": self._build_budget_widget,
            "property_portfolio": self._build_property_portfolio_widget,
            "music": self._build_music_widget,
            "kitchen": self._build_kitchen_widget,
            "workout": self._build_workout_widget,
            "relationships": self._build_relationships_widget,
            "observations": self._build_observations_widget,
            "lite_captures": self._build_lite_captures_widget,
            "life_state": self._build_life_state_widget,
        }
        self._widget_highlight_providers: dict[str, Callable[[], Optional[str]]] = {
            "power": self._power_highlight,
            "mission": self._mission_highlight,
            "current_project": self._current_project_highlight,
            "homestead": self._homestead_highlight,
            "budget": self._budget_highlight,
            "maintenance": self._maintenance_highlight,
            "kitchen": self._kitchen_highlight,
            "workout": self._workout_highlight,
            "relationships": self._relationships_highlight,
            "observations": self._observations_highlight,
            "lite_captures": self._lite_captures_highlight,
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
            # property_portfolio deliberately has no highlight provider
            # either, same "not yet meaningful" bar as net_worth/
            # real_estate above — nothing about it is routinely
            # actionable at a glance the way an overdue bill or an
            # expiring pantry item is.
            # music deliberately has no highlight provider — unlike
            # every other highlight here, "what's currently playing"
            # isn't a persisted fact known at construction time; the
            # briefing is computed once per launch, before the user has
            # started anything.
            # life_state deliberately has no highlight provider — it
            # synthesizes signals (open Insights, overdue Maintenance,
            # active Missions) that observations/maintenance/mission's
            # OWN highlight providers already speak in the briefing;
            # adding a second highlight for the same underlying signals
            # would just repeat them, not add anything.
        }

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(24)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        outer.addWidget(self._build_overview_row())
        party_activity_card = self._build_party_activity_card()
        if party_activity_card is not None:
            outer.addWidget(party_activity_card)
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
        self._extract_interview_notes_if_needed()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(_CLOCK_TICK_MS)

        self._data_timer = QTimer(self)
        self._data_timer.timeout.connect(self._refresh_data)
        self._data_timer.start(_DATA_REFRESH_MS)

        self.context.events.subscribe("dashboard.widgets_changed", self._on_widgets_changed)
        # MIA Lite (2026-09-14) — a capture can be accepted from
        # modules/toolbox/tools/lite_captures_tool.py while Home isn't
        # even the visible screen; Home stays alive across module
        # navigation (a QStackedWidget hides it, doesn't destroy it),
        # so subscribing here reacts correctly regardless of which
        # screen the user was actually on when they clicked Accept.
        self.context.events.subscribe("capture.accepted", self._on_capture_accepted)

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

    def _build_overview_row(self) -> QWidget:
        """Nature re-skin, hero-only pass (2026-09-14) — same scope
        Missions/Skills got: a photo hero replaces the old plain
        "SYSTEM OVERVIEW" / "● ALL SYSTEMS NOMINAL" row, with that
        status chip relocated into it rather than dropped. A real,
        personalized greeting — `core.startup_briefing.greeting_for_hour()`
        (already built, already used by the briefing banner below) +
        the real active profile's name, not a fabricated "Good
        morning, Zac" the way the reference mockup's own copy is.
        Everything below this (clock, widgets grid, briefing banner,
        chat bar) is untouched — this screen already went through its
        own earlier, separate design pass rather than starting plain.

        **Personalized dashboard, multi-user slice (2026-09-14)**: the
        tagline itself is now real per-profile data (level, real
        missions available, real active projects —
        `format_dashboard_hero_tagline()`) instead of a generic line,
        the vision doc's own "Level 14 · 3 missions available · 2
        active projects" example. Falls back to the old generic line
        with no active profile (nothing real to report)."""
        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(120)
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(28, 16, 28, 16)
        layout.setSpacing(12)

        icon_badge = QLabel("\U0001F3E0")  # house
        icon_badge.setObjectName("NatureIconBadge")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_badge)

        profile_name = "there"
        active_profile = None
        if self.context.profiles is not None:
            active_profile = self.context.profiles.get_active_profile()
            if active_profile is not None:
                profile_name = active_profile.name

        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title = QLabel(f"{greeting_for_hour(datetime.now().hour)}, {profile_name}")
        title.setObjectName("NatureHeaderTitle")
        title_column.addWidget(title)
        tagline = QLabel(self._hero_tagline_text(active_profile))
        tagline.setObjectName("NatureHeaderTagline")
        title_column.addWidget(tagline)
        layout.addLayout(title_column, stretch=1)

        status_chip = QLabel("● ALL SYSTEMS NOMINAL")
        status_chip.setObjectName("DashboardStatusChip")
        layout.addWidget(status_chip, alignment=Qt.AlignmentFlag.AlignVCenter)

        return hero

    def _hero_tagline_text(self, active_profile) -> str:
        """Real per-profile numbers for the hero tagline — level (via
        core.leveling, prestige-aware), real missions currently
        available to this profile (is_attributed_to() — today mostly
        the same shared count for everyone, since an active Mission
        only carries a real profile_id when explicitly pre-assigned;
        still a real, honest number, not fabricated personalization),
        and real active household projects (Project has no per-profile
        concept yet, so this is the real household total). Falls back
        to the old generic line with no active profile at all."""
        if active_profile is None:
            return "Another day to build the life you want."
        level, _xp_into, _xp_needed = compute_prestige_level_progress(active_profile.total_xp, active_profile.prestige_tier)
        missions_available = 0
        if self.context.missions is not None:
            missions_available = sum(
                1 for mission in self.context.missions.all_missions()
                if mission.status == "active" and is_attributed_to(mission.profile_id, active_profile.profile_id)
            )
        active_projects = 0
        if self.context.projects is not None:
            active_projects = sum(
                1 for project in self.context.projects.all_projects() if project.status in ("Planning", "Active", "On Hold")
            )
        return format_dashboard_hero_tagline(level, missions_available, active_projects)

    def _build_party_activity_card(self) -> Optional[QWidget]:
        """Multi-user pass (2026-09-14) — the vision doc's own "Party
        Activity: Zac completed 'Mow the Homestead'" example. Derived
        entirely from real completed Missions' own profile_id (no new
        storage — same "derive it" stance everything else in this
        codebase follows), filtered to profiles OTHER than whoever's
        active. None (card omitted entirely) with fewer than 2 real
        profiles on this device — "party activity" implies there's
        someone else to report on; showing an empty card to a
        single-profile household would just be confusing chrome."""
        if self.context.profiles is None or self.context.missions is None:
            return None
        profiles = self.context.profiles.list_profiles()
        if len(profiles) < 2:
            return None
        active_profile = self.context.profiles.get_active_profile()
        active_id = active_profile.profile_id if active_profile is not None else None
        names_by_id = {p.profile_id: p.name for p in profiles}

        other_completions = sorted(
            (
                mission for mission in self.context.missions.all_missions()
                if mission.status == "completed" and mission.profile_id is not None and mission.profile_id != active_id
            ),
            key=lambda m: m.updated_at,
            reverse=True,
        )[:3]

        card = BlueprintFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        eyebrow = QLabel("PARTY ACTIVITY")
        eyebrow.setObjectName("DashboardSectionTitle")
        layout.addWidget(eyebrow)

        if not other_completions:
            empty = QLabel("No recent activity from the rest of your household yet.")
            layout.addWidget(empty)
        else:
            for mission in other_completions:
                name = names_by_id.get(mission.profile_id, "Someone")
                line = QLabel(format_party_activity_line(name, mission.name))
                layout.addWidget(line)

        apply_panel_glow(card)
        return card

    def _build_clock(self) -> QWidget:
        """A real card (eyebrow "CLOCK" label + big time, left; date,
        right) — re-comparing against the ForMIA mockup found this had
        shipped as a bare centered label stack with no card/eyebrow at
        all, unlike every other widget's card treatment.

        **2026-09-12 design restyle, phase 1**: one of two proof-of-
        concept cards for the "MIA Smart User OS Design" handoff's v2
        HUD layer — BlueprintFrame's corner marks + a colored glow
        (gui/widgets/glow.py) replace the plain QFrame + generic black
        drop-shadow this card used before."""
        card = BlueprintFrame()
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

        apply_panel_glow(card)

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

        # 2026-09-12 design restyle, phase 1 — the second proof-of-concept
        # card for the v2 HUD layer (see _build_clock()'s own comment).
        # The clickable card itself stays a QPushButton (this app's own
        # "never :hover a descendant QLabel" rule — see
        # gui/widgets/module_button.py's docstring), so it's wrapped in a
        # transparent BlueprintFrame for the corner marks + glow rather
        # than trying to make the button itself paint them.
        wrapper = BlueprintFrame(accent=True)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(6, 6, 6, 6)
        wrapper_layout.addWidget(card)
        apply_panel_glow(wrapper)
        return wrapper

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

    def _build_observations_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("observations"),
        )
        self._widget_bodies["observations"] = body
        return card

    def _build_life_state_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        # core.context_assembler's own first GUI consumer beyond the
        # Assistant action (2026-09-14) — a synthesized "what's going on
        # right now" glance. No on_click: unlike every other widget
        # here, there's no dedicated module screen this summarizes down
        # from (it spans several), same "no related page" reasoning
        # Activity Log/Real Estate/Kraken Agent already establish.
        card, body = self._build_simple_card(descriptor.icon, descriptor.display_name)
        self._widget_bodies["life_state"] = body
        return card

    def _build_lite_captures_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        # Field Captures is a Toolbox tool, not a top-level module —
        # there's no deep-link mechanism into a specific tool (unlike
        # ModuleBase.focus_record()'s cross-MODULE navigation), so this
        # opens Toolbox itself; the user picks Field Captures from
        # there. A real, honest limitation, not worth a new navigation
        # mechanism just for this one card.
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("toolbox"),
        )
        self._widget_bodies["lite_captures"] = body
        return card

    def _build_budget_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("budget"),
        )
        self._widget_bodies["budget"] = body
        return card

    def _build_property_portfolio_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("real_estate"),
        )
        self._widget_bodies["property_portfolio"] = body
        return card

    def _build_music_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("music"),
        )
        self._widget_bodies["music"] = body
        return card

    def _build_kitchen_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("kitchen"),
        )
        self._widget_bodies["kitchen"] = body
        return card

    def _build_workout_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("workout"),
        )
        self._widget_bodies["workout"] = body
        return card

    def _build_relationships_widget(self, descriptor: WidgetDescriptor) -> QWidget:
        card, body = self._build_simple_card(
            descriptor.icon,
            descriptor.display_name,
            on_click=lambda: self._open_module("relationships"),
        )
        self._widget_bodies["relationships"] = body
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
        """Shared by every widget card builder — the eyebrow-label+
        stretch+optional "⋯" menu button row every widget card starts
        with.

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

    def _build_briefing_banner(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)

        self._briefing_label = QLabel(self._build_briefing_text())
        self._briefing_label.setObjectName("DashboardBriefingText")
        self._briefing_label.setWordWrap(True)
        layout.addWidget(self._briefing_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._replay_briefing_button = QPushButton("\U0001F50A  Replay")
        self._replay_briefing_button.setObjectName("ReplayBriefingButton")
        self._replay_briefing_button.setToolTip("Have MIA read the briefing above aloud again")
        self._replay_briefing_button.clicked.connect(self._on_replay_briefing)
        button_row.addWidget(self._replay_briefing_button)
        layout.addLayout(button_row)

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

    def _budget_highlight(self) -> Optional[str]:
        """Mirrors format_budget_line()'s own overdue-count computation
        above — deliberately not that function's full return value,
        since build_startup_briefing() joins every highlight into one
        sentence ("You have {a}, {b}, and {c}.") and needs a bare noun
        phrase, not format_budget_line()'s "All bills paid"/"N bills due
        within 7 days" branches, which would read oddly mid-sentence.
        Silent unless something's actually overdue — a due-soon bill
        isn't urgent enough to interrupt a launch greeting for."""
        if self.context.budget is None:
            return None
        today = date.today()
        overdue = sum(
            1 for bill in self.context.budget.all_bills()
            if (remaining := days_until_bill_due(bill, today)) is not None and remaining < 0
        )
        if not overdue:
            return None
        noun = "bill" if overdue == 1 else "bills"
        return f"{overdue} overdue {noun}"

    def _maintenance_highlight(self) -> Optional[str]:
        """Mirrors format_maintenance_line()'s own "overdue" bucket
        above — calendar tasks past due plus any meter/sensor task
        that's crossed its trigger — same reasoning as
        _budget_highlight() for why this isn't that function's full
        return value. Silent unless something needs real attention;
        "due soon" isn't worth a launch-greeting mention."""
        if self.context.maintenance is None:
            return None
        today = date.today()
        overdue = 0
        for task in self.context.maintenance.all_tasks():
            if task.trigger_type == "calendar":
                remaining = days_until_due(task, today)
                if remaining is not None and remaining < 0:
                    overdue += 1
            elif task.is_meter_task:
                if is_meter_task_due(task, self.context.maintenance.readings_for_task(task.task_id)):
                    overdue += 1
            elif task.is_sensor_task:
                if is_sensor_task_due(task, self.context.maintenance.readings_for_task(task.task_id)):
                    overdue += 1
        if not overdue:
            return None
        noun = "task" if overdue == 1 else "tasks"
        return f"{overdue} maintenance {noun} needing attention"

    def _observations_highlight(self) -> Optional[str]:
        """Same "silent unless something needs real attention"
        restraint as every other highlight provider here — an open
        Insight is exactly that by construction (see
        core/insight_manager.py), so any nonzero count qualifies."""
        if self.context.insights is None:
            return None
        count = len(self.context.insights.open_insights())
        if not count:
            return None
        noun = "thing" if count == 1 else "things"
        return f"{count} {noun} MIA has noticed"

    def _lite_captures_highlight(self) -> Optional[str]:
        """Same "silent unless something needs real attention"
        restraint as every other highlight provider here — a pending
        field capture is exactly that by construction."""
        if self.context.lite_captures is None:
            return None
        count = len(self.context.lite_captures.pending_proposals())
        if not count:
            return None
        noun = "field capture" if count == 1 else "field captures"
        return f"{count} {noun} to review"

    def _kitchen_highlight(self) -> Optional[str]:
        """Same expiring-within-3-days computation _refresh_kitchen()
        already does for the widget tile (format_kitchen_line()'s own
        leading branch) — reused verbatim here since that branch is
        already a bare noun phrase, unlike budget/maintenance above."""
        if self.context.kitchen is None:
            return None
        today = date.today()
        expiring = sum(
            1 for item in self.context.kitchen.all_pantry_items()
            if (days := days_until_expiration(item, today)) is not None and days <= 3
        )
        if not expiring:
            return None
        noun = "item" if expiring == 1 else "items"
        return f"{expiring} pantry {noun} expiring soon"

    def _workout_highlight(self) -> Optional[str]:
        """Same days-since-last-session math as format_workout_line()
        above, but gated to _BRIEFING_WORKOUT_STALE_AFTER_DAYS — that
        tile shows ANY days-since count (a routine, always-on fact
        worth glancing at); the spoken briefing only mentions it once
        it's genuinely been a while, never "1 day since your last
        workout" as a nag the morning after a normal rest day."""
        if self.context.workout is None:
            return None
        last_session_date = self.context.workout.last_session_date()
        if not last_session_date:
            return None
        try:
            days = (date.today() - date.fromisoformat(last_session_date)).days
        except ValueError:
            return None
        if days <= _BRIEFING_WORKOUT_STALE_AFTER_DAYS:
            return None
        return f"{days} days since your last workout"

    def _relationships_highlight(self) -> Optional[str]:
        """Same nearest_upcoming_birthday() call format_relationships_line()
        above already makes, but gated to _BRIEFING_BIRTHDAY_LEAD_DAYS —
        that tile always shows the nearest birthday, however far off;
        the spoken briefing only mentions one close enough to actually
        act on, same lead time core.smart_suggestions' own gift-reminder
        check already uses."""
        if self.context.relationships is None:
            return None
        nearest = self.context.relationships.nearest_upcoming_birthday(date.today())
        if nearest is None:
            return None
        person, days = nearest
        if days > _BRIEFING_BIRTHDAY_LEAD_DAYS:
            return None
        if days == 0:
            return f"{person.name}'s birthday today"
        noun = "day" if days == 1 else "days"
        return f"{person.name}'s birthday in {days} {noun}"

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
        ticker. 11 of the 20 registered dashboard widgets have a real
        highlight provider as of 2026-09-14 (power/mission/current_project/
        homestead from 2026-07-15, budget/maintenance/kitchen/workout/
        relationships/observations/lite_captures added once those
        modules existed; life_state deliberately has none, see that
        comment in self._widget_highlight_providers) — the rest are
        deliberate exclusions, see the comments in
        self._widget_highlight_providers itself, right where each one is
        registered (or pointedly isn't), for the reasoning per widget.
        Extend this as a new subsystem lands: add a _<widget_id>_highlight()
        method and register it there alongside the widget's builder."""
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
        if not prompt or self._worker is not None:
            return
        if self.context.llm is None and not detect_danger(prompt):
            return

        self._input.clear()
        conversation = self.context.conversations.get_or_create_active_conversation()
        self._conversation = conversation
        prepared = pre_turn(self.context, conversation, prompt)
        self.context.conversations.add_message(conversation.conversation_id, "user", prompt)
        if prepared.fixed_reply is not None:
            # Safety floor (core/safety_floor.py): a fixed reply, never the model.
            self.context.conversations.add_message(conversation.conversation_id, "assistant", prepared.fixed_reply)
            self._speak(prepared.fixed_reply)
            after_fixed_reply(self.context, conversation)
            return
        if prepared.notice:
            self.context.conversations.add_message(conversation.conversation_id, "assistant", prepared.notice)
            self._speak(prepared.notice)
        if self.context.llm is None:
            return
        self._set_busy(True)

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
        if not conversation.current_privacy():
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
        # Memory extraction, or organizing a journal session, or nothing
        # off the record — core/talk_it_out.py decides.
        if self._memory_worker is not None:
            return
        followup = plan_followup(self.context, conversation, user_message)
        if followup is None:
            return
        self._memory_worker = GenerateWorker(self.context.llm, followup.prompt)
        self._memory_worker.result_ready.connect(lambda raw: apply_followup(self.context, conversation, followup, raw))
        self._memory_worker.finished.connect(self._on_memory_worker_finished)
        self._memory_worker.start()

    def _extract_interview_notes_if_needed(self) -> None:
        """"Any user, any hobby" vision (2026-09-14) — the profile-
        creation interview's free-text notes were captured but never
        acted on until now. Runs them through the exact same
        extraction pipeline a real chat message already goes through
        (build_memory_extraction_prompt()/parse_extracted_memories()),
        once per profile ever (Profile.interview_notes_extracted gates
        it) — Home is the first stable, long-lived widget a profile
        reaches after either first-run setup or "Add Profile," so
        starting the worker here (rather than from the transient setup
        wizard/interview dialog itself) means it isn't orphaned by that
        dialog closing before a real LLM reply comes back.

        Inherits the same pre-existing limitation every other
        extraction call site in this app already has: UserMemory has
        no profile_id field, so extracted facts land in one shared
        pool, not scoped to just this profile — not a new gap this
        introduces, see core/user_memory_manager.py."""
        if self.context.user_memories is None or self.context.llm is None or self.context.profiles is None:
            return
        profile = self.context.profiles.get_active_profile()
        if profile is None or profile.interview_notes_extracted or not profile.interview_notes.strip():
            return
        prompt = build_memory_extraction_prompt(profile.interview_notes)
        self._interview_memory_worker = GenerateWorker(self.context.llm, prompt)
        profile_id = profile.profile_id
        self._interview_memory_worker.result_ready.connect(
            lambda raw: self._on_interview_notes_extracted(profile_id, raw)
        )
        self._interview_memory_worker.finished.connect(self._on_interview_memory_worker_finished)
        self._interview_memory_worker.start()

    def _on_interview_notes_extracted(self, profile_id: str, raw_text: Optional[str]) -> None:
        for category, fact in parse_extracted_memories(raw_text):
            self.context.user_memories.add_memory(fact, category=category)
        self.context.profiles.mark_interview_notes_extracted(profile_id)

    def _on_interview_memory_worker_finished(self) -> None:
        if self._interview_memory_worker is not None:
            self._interview_memory_worker.deleteLater()
            self._interview_memory_worker = None

    def _on_capture_accepted(self, proposal_id: str) -> None:
        """MIA Lite (2026-09-14) — the "MIA notices things silently in
        the background" step core.lite_capture_manager.py's own
        docstring describes: real personal facts extracted from an
        accepted field capture's transcript, same pipeline/worker
        shape as _extract_interview_notes_if_needed() above, just
        triggered by the "capture.accepted" event instead of at
        construction time."""
        if self.context.user_memories is None or self.context.llm is None or self.context.lite_captures is None:
            return
        proposal = self.context.lite_captures.get_proposal(proposal_id)
        if proposal is None or not proposal.transcript.strip():
            return
        prompt = build_memory_extraction_prompt(proposal.transcript)
        self._capture_memory_worker = GenerateWorker(self.context.llm, prompt)
        self._capture_memory_worker.result_ready.connect(self._on_capture_memories_extracted)
        self._capture_memory_worker.finished.connect(self._on_capture_memory_worker_finished)
        self._capture_memory_worker.start()

    def _on_capture_memories_extracted(self, raw_text: Optional[str]) -> None:
        for category, fact in parse_extracted_memories(raw_text):
            self.context.user_memories.add_memory(fact, category=category)

    def _on_capture_memory_worker_finished(self) -> None:
        if self._capture_memory_worker is not None:
            self._capture_memory_worker.deleteLater()
            self._capture_memory_worker = None

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
        self._replay_briefing_button.setEnabled(False)

    def _on_tts_finished(self) -> None:
        if self._tts_worker is not None:
            self._tts_worker.deleteLater()
            self._tts_worker = None
        self._stop_speaking_button.setEnabled(False)
        self._replay_briefing_button.setEnabled(True)

    def _on_replay_briefing(self) -> None:
        self._speak(self._briefing_label.text())

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
        if "budget" in self._widget_bodies:
            self._refresh_budget()
        if "property_portfolio" in self._widget_bodies:
            self._refresh_property_portfolio()
        if "music" in self._widget_bodies:
            self._refresh_music()
        if "kitchen" in self._widget_bodies:
            self._refresh_kitchen()
        if "workout" in self._widget_bodies:
            self._refresh_workout()
        if "relationships" in self._widget_bodies:
            self._refresh_relationships()
        if "observations" in self._widget_bodies:
            self._refresh_observations()
        if "lite_captures" in self._widget_bodies:
            self._refresh_lite_captures()
        if "life_state" in self._widget_bodies:
            self._refresh_life_state()

    def _refresh_life_state(self) -> None:
        line = "No active profile"
        if self.context.profiles is not None:
            active_profile = self.context.profiles.get_active_profile()
            if active_profile is not None:
                snapshot = assemble_life_state(self.context, active_profile.profile_id, date.today())
                line = format_life_state_glance_line(snapshot)
        self._set_widget_body_text("life_state", line)

    def _refresh_observations(self) -> None:
        open_insights = self.context.insights.open_insights() if self.context.insights else []
        self._set_widget_body_text("observations", format_observations_line(open_insights))

    def _refresh_lite_captures(self) -> None:
        pending_count = len(self.context.lite_captures.pending_proposals()) if self.context.lite_captures else 0
        self._set_widget_body_text("lite_captures", format_lite_captures_line(pending_count))

    def _refresh_budget(self) -> None:
        bills = self.context.budget.all_bills() if self.context.budget else []
        self._set_widget_body_text("budget", format_budget_line(bills, date.today()))

    def _refresh_property_portfolio(self) -> None:
        properties = self.context.real_estate.all_properties() if self.context.real_estate else []
        self._set_widget_body_text("property_portfolio", format_property_portfolio_line(properties))

    def _refresh_music(self) -> None:
        now_playing = self.context.music.now_playing() if self.context.music else None
        self._set_widget_body_text("music", format_music_line(now_playing))

    def _refresh_kitchen(self) -> None:
        kitchen = self.context.kitchen
        expiring, makeable, has_pantry = (0, 0, False)
        if kitchen is not None:
            today = date.today()
            expiring = sum(
                1 for item in kitchen.all_pantry_items()
                if (days := days_until_expiration(item, today)) is not None and days <= 3
            )
            makeable = sum(1 for _, missing in kitchen.recipes_makeable_now() if not missing)
            has_pantry = bool(kitchen.all_pantry_items())
        self._set_widget_body_text("kitchen", format_kitchen_line(expiring, makeable, has_pantry))

    def _refresh_workout(self) -> None:
        last_session_date = self.context.workout.last_session_date() if self.context.workout else None
        self._set_widget_body_text("workout", format_workout_line(last_session_date, date.today()))

    def _refresh_relationships(self) -> None:
        nearest_birthday = (
            self.context.relationships.nearest_upcoming_birthday(date.today()) if self.context.relationships else None
        )
        self._set_widget_body_text("relationships", format_relationships_line(nearest_birthday))

    def _refresh_real_estate(self) -> None:
        snapshot = self.context.finance.latest_snapshot(_REAL_ESTATE_SOURCE) if self.context.finance else None
        self._set_widget_body_text("real_estate", format_real_estate_line(snapshot))

    def _refresh_kraken_agent(self) -> None:
        snapshot = self.context.finance.latest_snapshot(_KRAKEN_SOURCE) if self.context.finance else None
        self._set_widget_body_text("kraken_agent", format_kraken_line(snapshot))

    def _refresh_net_worth(self) -> None:
        snapshots = self.context.finance.all_latest_snapshots() if self.context.finance else []
        properties = self.context.real_estate.all_properties() if self.context.real_estate else []
        property_equity_total = sum(property_equity(p) for p in properties) if properties else None
        self._set_widget_body_text("net_worth", format_net_worth_line(snapshots, property_equity_total))

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
