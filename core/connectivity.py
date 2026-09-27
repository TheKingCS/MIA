"""
core.connectivity
===================

What MIA can do with and without the internet, and whether she has it
right now — so if the connection drops she keeps acting sensibly
instead of promising things she can't deliver.

MIA is offline-first: her model (local Ollama), voice (Vosk/Piper), and
every record and action run on this computer. Only a handful of
features reach the internet, listed in `ONLINE_ONLY_CAPABILITIES` from
the code paths that actually make network requests
(`core/plaid_manager.py`, `core/web_push.py`, `core/map_tile_cache.py`,
`core/trail_map_library.py`, and phone access via Tailscale). Keep that
list in sync when a new network feature is added.

`ConnectivityMonitor` checks reachability with a bare TCP connect (no
data sent) to `network.probe_hosts`, on a background daemon thread so
it never blocks the GUI or a chat turn. Reading `.status` never blocks:
it returns the last result and quietly starts a fresh check when that
result is older than `CHECK_INTERVAL_SECONDS`, so every surface (GUI,
headless voice loop, phone server) stays current without its own timer.
Set `network.connectivity_check` to false to disable probing entirely
(status then stays "unknown" and MIA says nothing about it).
"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from core.app_context import AppContext
from core.assistant_actions import AssistantAction
from core.logger import get_logger

log = get_logger(__name__)

ONLINE = "online"
OFFLINE = "offline"
UNKNOWN = "unknown"

CHECK_INTERVAL_SECONDS = 60
STALE_AFTER_SECONDS = 600
_PROBE_TIMEOUT_SECONDS = 2.0
_DEFAULT_PROBE_HOSTS = ["1.1.1.1:443", "8.8.8.8:53"]
_default_connect: Callable[..., object] = socket.create_connection


@dataclass(frozen=True)
class OnlineCapability:
    name: str  # short label used in the system prompt
    what: str  # what needs the internet
    offline_fallback: str  # what still works without it


ONLINE_ONLY_CAPABILITIES: tuple[OnlineCapability, ...] = (
    OnlineCapability(
        "bank sync",
        "Syncing bank, card and investment accounts, or connecting new ones",
        "Your last synced balances and every manual budget entry still work.",
    ),
    OnlineCapability(
        "phone notifications",
        "Sending notifications to your phone",
        "Notifications still appear here on this computer.",
    ),
    OnlineCapability(
        "new map downloads",
        "Downloading map areas you haven't viewed before",
        "Map areas you've already viewed and your saved trail maps still work.",
    ),
    OnlineCapability(
        "adding trail maps from a web link",
        "Adding a trail map from a web link",
        "You can still add one from a file.",
    ),
    OnlineCapability(
        "phone access away from home",
        "Talking to MIA from your phone when you're away from home",
        "You can still talk to MIA here on this computer.",
    ),
)

OFFLINE_CAPABILITIES: tuple[str, ...] = (
    "conversation and thinking (my model runs on this computer)",
    "listening and speaking",
    "every record and action: budget, debts, missions, maintenance, notes, calendar, kitchen, workouts, people and pets",
    "reminders, alarms, daily briefings and suggestions",
    "installed reference packs, saved trail maps and map areas already viewed",
    "calculators, tools and backups",
)


def connectivity_prompt_block(status: str) -> str:
    """Pure logic. The system-prompt line(s) telling MIA her connection
    state. Deliberately short (small local models get less reliable as
    the system prompt grows). Empty for "unknown": saying nothing beats
    guessing."""
    online_only = ", ".join(c.name for c in ONLINE_ONLY_CAPABILITIES)
    if status == ONLINE:
        return f"Internet: connected. Online-only features ({online_only}) are available."
    if status == OFFLINE:
        return (
            "Internet: OFFLINE right now. You still run fully on this computer: conversation, voice, "
            "every record and action, reminders, briefings, saved maps, reference packs and last-synced "
            f"bank balances. Not possible until the internet is back: {online_only}. If asked for one of "
            "those, say plainly that it needs the internet, offer what you can do offline instead, and "
            "offer to remind them once they're back online."
        )
    return ""


def describe_capabilities(status: str) -> str:
    """Pure logic. A spoken-friendly answer to "what can you do
    offline?" / "are you online?" for the get_connectivity_status action."""
    if status == ONLINE:
        opening = "I'm online right now, so everything is available."
    elif status == OFFLINE:
        opening = "I'm offline right now, but almost everything still works because I run on this computer."
    else:
        opening = "I can't tell whether I'm online at the moment, but here's what depends on it."
    works = "Without the internet I can still do: " + "; ".join(OFFLINE_CAPABILITIES) + "."
    needs = "Only these need the internet: " + " ".join(
        f"{c.what} ({c.offline_fallback})" for c in ONLINE_ONLY_CAPABILITIES
    )
    return f"{opening} {works} {needs}"


def parse_probe_host(entry: str) -> Optional[tuple[str, int]]:
    """Pure logic. "host:port" -> (host, port); None if malformed."""
    host, sep, port = str(entry).rpartition(":")
    if not sep or not host:
        return None
    try:
        return host, int(port)
    except ValueError:
        return None


class ConnectivityMonitor:
    def __init__(
        self,
        context: AppContext,
        connect: Optional[Callable[..., object]] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.context = context
        # Looked up at call time so tests can swap _default_connect module-wide.
        self._connect = connect or (lambda *args, **kwargs: _default_connect(*args, **kwargs))
        self._clock = clock
        self._status = UNKNOWN
        self._checked_at: Optional[float] = None
        self._lock = threading.Lock()
        self._check_in_flight = False

    @property
    def enabled(self) -> bool:
        return bool(self.context.config.get("network.connectivity_check", True))

    def _probe_hosts(self) -> list[tuple[str, int]]:
        entries = self.context.config.get("network.probe_hosts", _DEFAULT_PROBE_HOSTS) or []
        return [parsed for parsed in (parse_probe_host(e) for e in entries) if parsed is not None]

    def check_now(self) -> str:
        """Blocking: try each probe host until one connects. Call from a
        background thread (refresh_async) or where a short wait is fine."""
        if not self.enabled:
            return UNKNOWN
        result = OFFLINE
        for host, port in self._probe_hosts():
            try:
                conn = self._connect((host, port), timeout=_PROBE_TIMEOUT_SECONDS)
                close = getattr(conn, "close", None)
                if close is not None:
                    close()
                result = ONLINE
                break
            except OSError:
                continue
        with self._lock:
            if result != self._status:
                log.info("Internet connection: %s", result)
            self._status = result
            self._checked_at = self._clock()
        return result

    def _run_check(self) -> None:
        try:
            self.check_now()
        finally:
            with self._lock:
                self._check_in_flight = False

    def refresh_async(self) -> None:
        """Starts one background check unless one is already running."""
        if not self.enabled:
            return
        with self._lock:
            if self._check_in_flight:
                return
            self._check_in_flight = True
        threading.Thread(target=self._run_check, name="mia-connectivity", daemon=True).start()

    @property
    def status(self) -> str:
        """Never blocks. Returns the last result, kicking off a background
        re-check when it's due; a result older than STALE_AFTER_SECONDS
        (e.g. checks keep failing to run) reads as "unknown"."""
        if not self.enabled:
            return UNKNOWN
        now = self._clock()
        with self._lock:
            checked_at, status = self._checked_at, self._status
        if checked_at is None or now - checked_at >= CHECK_INTERVAL_SECONDS:
            self.refresh_async()
        if checked_at is None or now - checked_at >= STALE_AFTER_SECONDS:
            return UNKNOWN
        return status


def _action_get_connectivity_status(context: AppContext, arguments: dict) -> str:
    monitor = context.connectivity
    if monitor is None:
        return describe_capabilities(UNKNOWN)
    status = monitor.status
    if status == UNKNOWN and monitor.enabled:
        status = monitor.check_now()  # the user asked directly: worth a brief wait
    return describe_capabilities(status)


def connectivity_action() -> AssistantAction:
    """One definition, registered by both the desktop app
    (core/application.py) and the headless runtime (core/core_runtime.py)."""
    return AssistantAction(
        name="get_connectivity_status",
        domain="system",
        description=(
            "Check whether MIA has an internet connection right now, and explain what she can "
            "still do offline versus what needs the internet."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_connectivity_status,
        # Specific phrases only: a bare "offline"/"online" would also fire
        # on unrelated questions ("how do offline maps work?") and pull
        # them off the help-doc answer path.
        trigger_phrases=(
            "are you online", "are you offline", "are we online", "are we offline",
            "are you connected", "connection status", "internet connection",
            "no internet", "without internet", "without the internet", "internet down",
            "work offline", "offline mode", "need the internet", "needs the internet",
            "need internet", "needs internet", "no signal", "no service",
        ),
    )
