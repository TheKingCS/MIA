"""
gui.home_dashboard
====================

The screen shown immediately after login — rebuilt 2026-07-18 against
a design handoff (CCH.zip's Dashboard.dc.html), a full replacement of
the previous customizable-widget-grid Home screen, not a restyle. The
new layout is a "console": a left telemetry panel (Processing Load
gauge, Power/Uptime, a tip card), a center console (state label, the
big animated presence orb, the last spoken reply), a narrow side gauge
rail (CPU/NET/SYS), a collapsible right rail (Assistant Profile,
Monitoring, Activity Log, Quick Toggles), and a bottom chat bar — MIA
talks to you directly on Home now, instead of needing a separate
Assistant screen or the sidebar for that.

**This is the third chat surface in this codebase** (alongside
`modules/assistant/module.py`'s full screen and `gui/character_panel.py`'s
sidebar) — reuses the exact same shared logic
(`core.assistant_chat.build_chat_request()`/`split_safe_tool_calls()`,
`core.chat_worker.ChatWorker`, `core.tts_worker.TTSWorker`) those two
already do, so all three can never silently drift apart in behavior.
The startup briefing (previously a separate spoken-once label) is now
this console's very first `lastMessage` — same
`core.startup_briefing.build_startup_briefing()` call as before, just
populating the console's own message bubble instead of a dedicated
banner widget.

**Telemetry**: Processing Load and the CPU side gauge both read
`core.system_health.read_system_health()`'s `cpu_percent` (the design's
own mockup shows these as two separate gauges too — this isn't
redundant, just two different visual placements of the same real
number). SYS reads `memory_percent`. NET needs an actual *rate*, not
the cumulative since-boot totals `SystemHealthSnapshot` carries — this
class holds the previous reading + timestamp itself and calls
`core.dashboard_telemetry.compute_network_mbps()` on every 5s refresh
tick, capped visually at `_NET_GAUGE_CEILING_MBPS` (an assumed display
ceiling — the raw Mbps number is still shown as text, only the ring's
fill fraction is capped).

**Right rail's "Assistant Profile" card is honest, not a literal port
of the mockup**: the design shows a "Mode" selector and a "Wake word"
row neither of which correspond to any real MIA feature (no
adaptive-mode concept, no wake-word detection — only push-to-talk
exists). Rather than fabricate non-functional UI for either, those
rows are replaced with real facts: the actual configured TTS voice
(`core.voice_catalog`), the always-on warm/curious personality trait,
and "Push-to-talk" as the honest name for the real voice-input
mechanism. Matches this project's own established stance against
building UI for features that don't exist yet.

**No longer rendered on Home at all** (no natural slot in the new
console layout, per the design's own fixed Monitoring-tile set):
Real Estate/Kraken Agent/Net Worth (MIA Home finance widgets) and the
Companion Avatar camera feed. Their pure formatting functions
(`format_real_estate_line()` etc.) and backing managers are untouched
and still tested — just not wired into any widget here anymore. Same
"left in place, unregistered rather than deleted" treatment
`core/application.py`'s docstring already gives the Avatar widget.
`core/dashboard_widgets.py`'s `DashboardWidgetRegistry` (the old
enable/disable/reorder mechanism) is likewise now unused by this
screen — left in place rather than torn out, since removing it also
means migrating away `dashboard.disabled_widgets`/
`dashboard.widget_order` config state, out of scope for this pass.

format_clock_time()/format_clock_date()/format_power_line()/
format_active_mission_line()/format_volume_line()/
format_activity_log_line() are free functions (not methods) — testable
without Qt, see tests/test_home_dashboard.py.
"""

from __future__ import annotations

import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
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
    suggested_prompts_for_module,
)
from core.chat_worker import ChatWorker
from core.conversation_manager import DEFAULT_TITLE
from core.daily_occasions import calendar_events_today
from core.push_to_talk_trigger import PushToTalkTrigger
from core.dashboard_telemetry import compute_network_mbps, format_uptime_line
from core.finance_manager import FinancialSnapshot
from core.generate_worker import GenerateWorker
from core.llm_manager import ChatReply
from core.mission_manager import Mission
from core.power_manager import PowerStatus
from core.project_manager import Project
from core.startup_briefing import build_stat_highlights, build_startup_briefing
from core.system_health import read_system_health, read_uptime_seconds
from core.tts_worker import TTSWorker
from core.voice_catalog import VOICE_CATALOG
from core.volume_manager import VolumeStatus
from gui.presence_widget import PresenceWidget
from gui.widgets.circular_gauge import CircularGauge
from gui.widgets.toggle_switch import ToggleSwitch

_DATA_REFRESH_MS = 5000  # matches modules/power/module.py's own polling cadence
_NET_GAUGE_CEILING_MBPS = 100.0  # assumed display ceiling for the NET ring's fill fraction only — the text label always shows the real uncapped number
_STATE_LABELS = {"idle": "Idle", "listening": "Listening…", "thinking": "Thinking…", "speaking": "Speaking…"}


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
    format_kraken_line() below). Not currently rendered on Home (see
    module docstring) but kept alive/tested for a future pass."""
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
    shape is actually present. Not currently rendered on Home (see
    module docstring) but kept alive/tested for a future pass."""
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
    this never silently overstates itself as more complete than it is.
    Not currently rendered on Home (see module docstring) but kept
    alive/tested for a future pass."""
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


class HomeDashboard(QFrame):
    """The post-login home screen — see module docstring."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setObjectName("HomeDashboard")

        self._mia_state = "idle"
        self._last_message = ""
        self._right_open = True
        self._prev_net_sent_mb = 0.0
        self._prev_net_recv_mb = 0.0
        self._prev_net_time = time.monotonic()

        self._worker: Optional[ChatWorker] = None
        self._tts_worker: Optional[TTSWorker] = None
        self._title_worker: Optional[GenerateWorker] = None
        self._memory_worker: Optional[GenerateWorker] = None
        self._conversation = None
        self._recording = False

        # psutil.cpu_percent(interval=None) reports usage since the
        # *previous* call in this process — the very first call is
        # meaningless (usually 0.0), see core/system_health.py's own
        # docstring. Primed here so the first real _refresh_telemetry()
        # tick already has something meaningful to show.
        read_system_health()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 2026-07-18: real user report ("the side menus are still too
        # small, bring them closer towards the center"), confirmed
        # against the design handoff's own reference screenshot
        # (MIAHome.png) — the design's CSS grid uses proportional flex
        # ratios for *all four* columns (minmax(150px,2.3fr)
        # minmax(260px,3.6fr) minmax(110px,1.6fr) minmax(170px,2.5fr)),
        # not fixed-pixel side panels next to a stretch=1 center that
        # soaks up 100% of whatever's left over. That's exactly what
        # made the sides look small on a wide window: they stayed a
        # fixed size while the center kept growing. Stretch factors
        # below are that same 2.3:3.6:1.6:2.5 ratio (x10 for clean
        # ints); each panel keeps a minimum width instead of a fixed
        # one, matching the design's own "minmax" — never below a
        # usable size, but free to grow proportionally with the window.
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._build_telemetry_panel(), stretch=23)
        body.addWidget(self._build_console_panel(), stretch=36)
        body.addWidget(self._build_gauge_rail(), stretch=16)
        self._right_rail = self._build_right_rail()
        body.addWidget(self._right_rail, stretch=25)
        outer.addLayout(body, stretch=1)

        outer.addWidget(self._build_chat_bar())

        # GPIO path is a no-op unless voice.push_to_talk_gpio_pin is
        # configured and gpiozero + real hardware are present — see
        # core/push_to_talk_trigger.py. Both paths fire the exact same
        # handlers as the on-screen Talk button, same precedent as
        # modules/assistant/module.py's own wiring.
        self._ptt_trigger = PushToTalkTrigger(self.context, parent=self)
        self._ptt_trigger.pressed.connect(self._on_talk_pressed)
        self._ptt_trigger.released.connect(self._on_talk_released)

        self._data_timer = QTimer(self)
        self._data_timer.timeout.connect(self._refresh_telemetry)
        self._data_timer.start(_DATA_REFRESH_MS)
        self._refresh_telemetry()

        self._greet()

    def showEvent(self, event) -> None:
        """Forces an immediate telemetry refresh on becoming visible
        again, rather than waiting for the next 5s timer tick — same
        real fix as this class's earlier "dashboard widgets sized wrong
        after navigating away and back" bug (stale readings computed
        while hidden)."""
        super().showEvent(event)
        self._refresh_telemetry()

    def unsubscribe(self) -> None:
        """Must be called before this widget is destroyed."""
        self._data_timer.stop()

    # ------------------------------------------------------------------
    # Left telemetry panel
    # ------------------------------------------------------------------

    def _build_telemetry_panel(self) -> QWidget:
        panel = QScrollArea()
        panel.setObjectName("DashboardTelemetryPanel")
        panel.setWidgetResizable(True)
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setMinimumWidth(220)
        # Belt-and-suspenders alongside the DashboardStatValue font fix
        # below — this is a fixed-width side panel, never meant to
        # scroll horizontally; if some future content is ever a few
        # pixels too wide again, it should just get clipped, not sprout
        # a scrollbar.
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 24, 18, 24)
        layout.setSpacing(22)

        load_card = QFrame()
        load_card.setObjectName("DashboardCard")
        load_layout = QVBoxLayout(load_card)
        load_layout.setContentsMargins(16, 18, 16, 18)
        load_layout.setSpacing(10)
        load_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        load_title = QLabel("PROCESSING LOAD")
        load_title.setObjectName("DashboardSectionTitle")
        load_layout.addWidget(load_title, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._load_gauge = CircularGauge(diameter=170, stroke_width=9)
        load_layout.addWidget(self._load_gauge)
        load_caption = QLabel("Overall system load")
        load_caption.setObjectName("DashboardSectionBody")
        load_layout.addWidget(load_caption, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(load_card)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        power_card, self._power_value_label, self._power_caption_label = self._build_stat_tile("POWER")
        stats_row.addWidget(power_card)
        uptime_card, self._uptime_value_label, self._uptime_caption_label = self._build_stat_tile("UPTIME")
        stats_row.addWidget(uptime_card)
        layout.addLayout(stats_row)

        tip_card = QFrame()
        tip_card.setObjectName("DashboardCard")
        tip_layout = QHBoxLayout(tip_card)
        tip_layout.setContentsMargins(16, 16, 16, 16)
        tip_layout.setSpacing(12)
        tip_icon = QLabel("\U0001F4A1")
        tip_icon.setObjectName("MissionDetailIcon")
        tip_layout.addWidget(tip_icon)
        tip_text = QLabel('Say "Hey Mia" to start talking — just click Hold to Talk on the Assistant screen for now.')
        tip_text.setObjectName("DashboardSectionBody")
        tip_text.setWordWrap(True)
        tip_layout.addWidget(tip_text, stretch=1)
        layout.addWidget(tip_card)

        layout.addStretch()
        panel.setWidget(container)
        return panel

    def _build_stat_tile(self, title: str) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setObjectName("DashboardSectionTitle")
        layout.addWidget(title_label)
        # Real bug found via a headless-Qt screenshot: reusing
        # MissionDetailTitle's 19px bold font here clipped "59h 18m" in
        # this tile's ~100px half-column width (side by side with its
        # sibling stat tile), which in turn forced this whole scroll
        # panel wider than its fixed column width — showing an
        # unintended horizontal scrollbar. A dedicated smaller font
        # (DashboardStatValue) plus word-wrap fixes both at once.
        value_label = QLabel("—")
        value_label.setObjectName("DashboardStatValue")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)
        caption_label = QLabel("")
        caption_label.setObjectName("DashboardSectionBody")
        caption_label.setWordWrap(True)
        layout.addWidget(caption_label)
        return card, value_label, caption_label

    # ------------------------------------------------------------------
    # Center console
    # ------------------------------------------------------------------

    def _build_console_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = QVBoxLayout()
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title = QLabel("M.I.A. CONSOLE")
        title.setObjectName("ConsoleTitle")
        header.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        eyebrow = QLabel("ASSISTANT MODE")
        eyebrow.setObjectName("DashboardSectionTitle")
        header.addWidget(eyebrow, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._state_label = QLabel(_STATE_LABELS["idle"])
        self._state_label.setObjectName("ConsoleStateLabel")
        header.addWidget(self._state_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(header)

        stage = QFrame()
        stage.setObjectName("ConsoleOrbStage")
        # Real user report #1: with `stretch=1` below, this frame filled
        # *all* leftover vertical space in the console column — a huge,
        # nearly-empty grey box around a 150px orb that made the fixed-
        # width side panels/rail read as small and squished by
        # comparison. Fixed height instead of stretch=1.
        # Real user report #2: "smaller from top to bottom but still
        # stretches a bit far across... can be a bit taller but less
        # wide" — taller, capped max-width + centered.
        # Real user report #3: "should be top to bottom and the text
        # underneath, and the same less wide width across so the side
        # menus don't look weird" — narrowed to a fixed 240px with the
        # message moved *inside* the tile.
        # Real user report #4 (this pass, checked directly against
        # MIAHome.png): report #3's fixed-240px read was wrong — once
        # the side panels were fixed to their correct proportional width
        # (see the body-layout comment above), the reference shows this
        # tile as *wide*, filling nearly the whole console column, and
        # *tall*, spanning most (not all) of the column's height — not
        # narrow to match the side panels. And the reference's message
        # bubble ("All systems nominal...") sits *outside/below* the
        # dark box as its own element, not nested inside it. So: no
        # width cap (fills the column like the reference), `stretch=1`
        # so it's tall like the side panels but stops short of the
        # very bottom, and the message label moved back out to be a
        # sibling below `stage`, not a child inside it.
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(20, 16, 20, 20)
        stage_layout.setSpacing(12)
        stage_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        toggle_row = QHBoxLayout()
        toggle_row.addStretch()
        self._right_toggle_button = QPushButton("☰")
        self._right_toggle_button.setObjectName("HeaderButton")
        self._right_toggle_button.setFixedSize(30, 30)
        self._right_toggle_button.setToolTip("Toggle the right rail")
        self._right_toggle_button.clicked.connect(self._on_toggle_right_rail)
        toggle_row.addWidget(self._right_toggle_button)
        stage_layout.addLayout(toggle_row)

        stage_layout.addStretch()

        # Back up to 190px (from 160) now that the tile is wide/tall
        # again instead of a narrow 240px column; pulse_amplitude 0.4
        # unchanged from the previous round.
        self._presence = PresenceWidget(diameter=190, pulse_amplitude=0.4)
        stage_layout.addWidget(self._presence, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 2026-07-18: "put MIA back somewhere under or above the orb,
        # big bold and outlined, the same blue used throughout" —
        # originally placed above the orb; follow-up report moved it
        # below instead. A separate labeled heading, not text drawn
        # inside the orb glyph itself (that was removed as redundant
        # clutter in an earlier pass; this is a deliberately distinct,
        # more prominent re-addition).
        mia_label = QLabel("MIA")
        mia_label.setObjectName("ConsoleOrbLabel")
        stage_layout.addWidget(mia_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        stage_layout.addStretch()

        layout.addWidget(stage, stretch=1)

        self._last_message_label = QLabel("")
        self._last_message_label.setObjectName("ConsoleLastMessage")
        self._last_message_label.setWordWrap(True)
        self._last_message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._last_message_label)

        return container

    def _on_toggle_right_rail(self) -> None:
        self._right_open = not self._right_open
        self._right_rail.setVisible(self._right_open)

    # ------------------------------------------------------------------
    # Side gauge rail
    # ------------------------------------------------------------------

    def _build_gauge_rail(self) -> QWidget:
        rail = QWidget()
        rail.setObjectName("DashboardTelemetryPanel")
        rail.setMinimumWidth(110)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(10, 24, 10, 24)
        layout.setSpacing(28)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("TELEMETRY")
        title.setObjectName("DashboardSectionTitle")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._cpu_gauge = self._build_small_gauge(layout, "CPU")
        self._net_gauge = self._build_small_gauge(layout, "NET")
        self._sys_gauge = self._build_small_gauge(layout, "SYS")

        layout.addStretch()
        return rail

    def _build_small_gauge(self, layout: QVBoxLayout, label_text: str) -> CircularGauge:
        column = QVBoxLayout()
        column.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        gauge = CircularGauge(diameter=116, stroke_width=10)
        column.addWidget(gauge)
        label = QLabel(label_text)
        label.setObjectName("DashboardSectionTitle")
        column.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(column)
        return gauge

    # ------------------------------------------------------------------
    # Right rail
    # ------------------------------------------------------------------

    def _build_right_rail(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("DashboardTelemetryPanel")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(230)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 22, 16, 22)
        layout.setSpacing(24)

        layout.addWidget(self._build_assistant_profile_card())
        layout.addWidget(self._build_monitoring_card())
        layout.addWidget(self._build_activity_log_card())
        layout.addWidget(self._build_quick_toggles_card())
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_assistant_profile_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("ASSISTANT PROFILE")
        title.setObjectName("DashboardSectionTitle")
        layout.addWidget(title)

        voice_id = self.context.voice.current_voice_id if self.context.voice is not None else None
        voice_option = VOICE_CATALOG.get(voice_id) if voice_id else None
        voice_name = voice_option.display_name if voice_option is not None else "Not available"
        layout.addLayout(self._build_info_row("Voice", voice_name))
        layout.addLayout(self._build_info_row("Personality", "Warm & curious"))
        layout.addLayout(self._build_info_row("Input", "Push-to-talk"))
        return card

    def _build_info_row(self, label_text: str, value_text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setObjectName("DashboardSectionBody")
        row.addWidget(label)
        row.addStretch()
        value = QLabel(value_text)
        value.setObjectName("ConsoleInfoValue")
        row.addWidget(value)
        return row

    def _build_monitoring_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("MONITORING")
        title.setObjectName("DashboardSectionTitle")
        layout.addWidget(title)

        grid_row_1 = QHBoxLayout()
        grid_row_1.setSpacing(10)
        power_tile, self._monitor_power_label = self._build_monitor_tile("POWER")
        grid_row_1.addWidget(power_tile)
        volume_tile, self._monitor_volume_label = self._build_monitor_tile("VOLUME")
        grid_row_1.addWidget(volume_tile)
        layout.addLayout(grid_row_1)

        grid_row_2 = QHBoxLayout()
        grid_row_2.setSpacing(10)
        network_tile, self._monitor_network_label = self._build_monitor_tile("NETWORK")
        grid_row_2.addWidget(network_tile)
        ram_tile, self._monitor_ram_label = self._build_monitor_tile("RAM")
        grid_row_2.addWidget(ram_tile)
        layout.addLayout(grid_row_2)

        return card

    def _build_monitor_tile(self, label_text: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setObjectName("MonitorTile")
        tile.setMinimumHeight(78)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        title = QLabel(label_text)
        title.setObjectName("DashboardSectionTitle")
        layout.addWidget(title)
        value = QLabel("—")
        value.setObjectName("MonitorTileValue")
        layout.addWidget(value)
        return tile, value

    def _build_activity_log_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("ACTIVITY LOG")
        title.setObjectName("DashboardSectionTitle")
        layout.addWidget(title)
        self._activity_log_label = QLabel("")
        self._activity_log_label.setObjectName("DashboardActivityLogBody")
        self._activity_log_label.setWordWrap(True)
        layout.addWidget(self._activity_log_label)
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("HeaderButton")
        refresh_button.clicked.connect(self._refresh_activity_log)
        layout.addWidget(refresh_button)
        self._refresh_activity_log()
        return card

    def _build_quick_toggles_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        title = QLabel("QUICK TOGGLES")
        title.setObjectName("DashboardSectionTitle")
        layout.addWidget(title)

        voice_row = QHBoxLayout()
        voice_label = QLabel("\U0001F3A4 Voice")
        voice_label.setObjectName("DashboardSectionBody")
        voice_row.addWidget(voice_label)
        voice_row.addStretch()
        voice_toggle = ToggleSwitch()
        voice_toggle.setChecked(self.context.config.get("voice.push_to_talk_enabled", True))
        voice_toggle.toggled.connect(self._on_voice_input_toggled)
        voice_row.addWidget(voice_toggle)
        layout.addLayout(voice_row)

        alerts_row = QHBoxLayout()
        alerts_label = QLabel("\U0001F514 Alerts")
        alerts_label.setObjectName("DashboardSectionBody")
        alerts_row.addWidget(alerts_label)
        alerts_row.addStretch()
        alerts_toggle = ToggleSwitch()
        alerts_toggle.setChecked(self.context.config.get("notifications.enabled", True))
        alerts_toggle.toggled.connect(self._on_notifications_toggled)
        alerts_row.addWidget(alerts_toggle)
        layout.addLayout(alerts_row)

        return card

    def _on_voice_input_toggled(self, checked: bool) -> None:
        self.context.config.set("voice.push_to_talk_enabled", checked)
        self.context.config.save()

    def _on_notifications_toggled(self, checked: bool) -> None:
        self.context.config.set("notifications.enabled", checked)
        self.context.config.save()

    # ------------------------------------------------------------------
    # Bottom chat bar
    # ------------------------------------------------------------------

    def _build_chat_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("DashboardChatBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        for prompt in suggested_prompts_for_module(None):
            chip = QPushButton(prompt)
            chip.setObjectName("SuggestionButton")
            chip.clicked.connect(lambda _checked=False, p=prompt: self._on_suggestion_clicked(p))
            layout.addWidget(chip)

        self._input = QLineEdit()
        self._input.setObjectName("HeaderSearchBar")
        self._input.setPlaceholderText("Ask Mia anything…")
        self._input.returnPressed.connect(self._on_send)
        layout.addWidget(self._input, stretch=1)

        # Same two buttons as the full Assistant module
        # (modules/assistant/module.py) — press-and-hold to talk, plus a
        # way to cut MIA off mid-reply — brought to this bar too since
        # it's a real chat surface of its own, not just suggestion chips.
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

    def _on_suggestion_clicked(self, prompt: str) -> None:
        self._input.setText(prompt)
        self._on_send()

    # ------------------------------------------------------------------
    # Chat — same shared core.assistant_chat/core.chat_worker logic as
    # gui/character_panel.py and modules/assistant/module.py.
    # ------------------------------------------------------------------

    def _greet(self) -> None:
        """Populates the console's first `lastMessage` with the real
        startup briefing (previously a separate spoken-once banner) and
        speaks it, same one-per-launch behavior as before."""
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

        highlights = []
        if self.context.power is not None:
            status = self.context.power.read()
            if status is not None:
                highlights.append(f"{status.percent:.0f}% battery")
        if self.context.missions is not None:
            count = sum(1 for m in self.context.missions.all_missions() if m.status == "active")
            if count:
                highlights.append(f"{count} active {'mission' if count == 1 else 'missions'}")
        highlights += build_stat_highlights(events_today_count, unread_notification_count)

        latest_memory_line = None
        if self.context.memories is not None:
            recaps = self.context.memories.all_recaps()
            if recaps:
                latest_memory_line = recaps[0].expedition.name

        briefing = build_startup_briefing(profile_name, datetime.now(), highlights, latest_memory_line)
        self._set_last_message(briefing)
        self.context.conversations.start_new_active_conversation()
        self._speak(briefing)

    def _set_last_message(self, text: str) -> None:
        self._last_message = text
        self._last_message_label.setText(text)

    def _set_state(self, state: str) -> None:
        self._mia_state = state
        self._state_label.setText(_STATE_LABELS.get(state, "Idle"))
        self._presence.set_state(state)

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
            self._set_last_message("Assistant unavailable — is Ollama running?")
            return

        conversation = self._conversation
        if conversation is None:
            return

        if reply.tool_calls:
            calls_to_execute, skipped_calls = split_safe_tool_calls(reply.tool_calls, self.context.assistant_actions)
            if skipped_calls:
                skipped_names = ", ".join(tc.name for tc in skipped_calls)
                message = f"(Skipped a possibly unintended action for safety: {skipped_names}. Ask for that on its own if you really want it.)"
                self.context.conversations.add_message(conversation.conversation_id, "assistant", message)
                self._set_last_message(message)
            for tool_call in calls_to_execute:
                confirmation = self.context.assistant_actions.execute(self.context, tool_call.name, tool_call.arguments)
                self.context.conversations.add_message(conversation.conversation_id, "assistant", confirmation)
                self._set_last_message(confirmation)
                self._speak(confirmation)
            return

        user_message = conversation.messages[-1].content if conversation.messages else ""
        self.context.conversations.add_message(conversation.conversation_id, "assistant", reply.content)
        self._set_last_message(reply.content)
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
        self._set_state("thinking" if busy else "idle")

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
        self._set_state("speaking")
        self._tts_worker.start()
        self._stop_speaking_button.setEnabled(True)

    def _on_tts_finished(self) -> None:
        if self._tts_worker is not None:
            self._tts_worker.deleteLater()
            self._tts_worker = None
        if self._mia_state == "speaking":
            self._set_state("idle")
        self._stop_speaking_button.setEnabled(False)

    def _on_stop_speaking(self) -> None:
        """Cuts MIA off mid-sentence — same real ask (2026-07-18) already
        answered on the full Assistant module, brought to this bar too.
        Only stops playback; synthesis (if still running) finishes
        harmlessly with nothing left to play."""
        if self.context.voice is not None:
            self.context.voice.stop_playback()

    # ------------------------------------------------------------------
    # Push-to-talk (speech in) — same pipeline as
    # modules/assistant/module.py's Hold to Talk button.
    # ------------------------------------------------------------------

    def _on_talk_pressed(self) -> None:
        if self.context.voice is None or self._worker is not None or self._recording:
            return
        if not self.context.config.get("voice.push_to_talk_enabled", True):
            self._set_last_message("Voice input is turned off (Settings).")
            return
        if not self.context.voice.start_recording():
            self._set_last_message("Microphone unavailable.")
            return
        self._recording = True
        self._set_talk_button_recording(True)
        self._set_state("listening")

    def _on_talk_released(self) -> None:
        if self.context.voice is None or not self._recording:
            return
        self._recording = False
        self._set_talk_button_recording(False)

        wav_path = self.context.voice.stop_recording()
        if wav_path is None:
            self._set_last_message("Microphone unavailable.")
            self._set_state("idle")
            return

        self._set_state("thinking")
        transcript = self.context.voice.transcribe(wav_path)
        if not transcript:
            self._set_last_message("Speech-to-text unavailable.")
            self._set_state("idle")
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

    # ------------------------------------------------------------------
    # Telemetry refresh
    # ------------------------------------------------------------------

    def _refresh_telemetry(self) -> None:
        snapshot = read_system_health()

        self._load_gauge.set_value(snapshot.cpu_percent, 100.0, value_text=f"{snapshot.cpu_percent:.0f}", unit_text="%")
        self._cpu_gauge.set_value(snapshot.cpu_percent, 100.0, value_text=f"{snapshot.cpu_percent:.0f}")
        self._sys_gauge.set_value(snapshot.memory_percent, 100.0, value_text=f"{snapshot.memory_percent:.0f}")

        now = time.monotonic()
        elapsed = now - self._prev_net_time
        mbps = compute_network_mbps(
            self._prev_net_sent_mb, self._prev_net_recv_mb, elapsed, snapshot.network_sent_mb, snapshot.network_recv_mb
        )
        self._prev_net_sent_mb = snapshot.network_sent_mb
        self._prev_net_recv_mb = snapshot.network_recv_mb
        self._prev_net_time = now
        self._net_gauge.set_value(mbps, _NET_GAUGE_CEILING_MBPS, value_text=f"{mbps:.0f}")

        power_status = self.context.power.read() if self.context.power is not None else None
        if power_status is not None:
            self._power_value_label.setText(f"{power_status.percent:.0f}%")
            self._power_caption_label.setText("Plugged in" if power_status.plugged_in else "On battery")
        else:
            self._power_value_label.setText("—")
            self._power_caption_label.setText("No battery or UPS detected")
        self._uptime_value_label.setText(format_uptime_line(read_uptime_seconds()))
        self._uptime_caption_label.setText("Since boot")

        self._monitor_power_label.setText(f"{power_status.percent:.0f}%" if power_status is not None else "—")
        volume_status = self.context.volume.read() if self.context.volume is not None and self.context.volume.is_available() else None
        self._monitor_volume_label.setText(f"{volume_status.percent}%" if volume_status is not None else "—")
        self._monitor_network_label.setText(f"{mbps:.1f} mbps")
        self._monitor_ram_label.setText(f"{snapshot.memory_percent:.1f}%")

    def _refresh_activity_log(self) -> None:
        entries = self.context.activity_log.recent(limit=3) if self.context.activity_log is not None else []
        self._activity_log_label.setText(format_activity_log_line(entries))
