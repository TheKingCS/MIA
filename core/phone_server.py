"""
core.phone_server
====================

Turning phone access on and off from Settings (2026-09-28), instead of
hand-editing `server.enabled` in config/config.json (one missing comma
there and MIA won't read its config).

`PhoneServer` (context.phone_server) owns the phone API server
(server/app.py) that used to be started inline in core/application.py:
start, stop (live, no restart), and a plain-language status for the
Settings page:
- running or not, and why not (FastAPI missing, port already in use);
- the phone address from Tailscale (`tailscale status --json`) and
  whether `tailscale serve` already forwards to MIA, with the exact
  command to run when it doesn't;
- whether any profile has a password (the phone login needs one);
- when a phone last used MIA.

Why it runs in-process on a thread, loopback-only, is unchanged; see
start() below.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

DEFAULT_PORT = 8765
_START_WAIT_SECONDS = 5.0


# ---------------------------------------------------------------------------
# Tailscale (pure parsing + a thin runner)
# ---------------------------------------------------------------------------


@dataclass
class TailscaleInfo:
    installed: bool = False
    running: bool = False  # signed in and connected
    address: str = ""  # https://mia-home.tail1234.ts.net
    serving_mia: bool = False  # `tailscale serve` forwards to MIA's port
    problem: str = ""


def parse_tailscale_status(text: str) -> tuple[bool, str]:
    """Pure logic. (connected, https address) from `tailscale status --json`."""
    try:
        data = json.loads(text)
    except ValueError:
        return False, ""
    running = data.get("BackendState") == "Running"
    dns_name = str((data.get("Self") or {}).get("DNSName") or "").rstrip(".")
    return running, f"https://{dns_name}" if dns_name else ""


def serve_forwards_to(text: str, port: int) -> bool:
    """Pure logic. Whether `tailscale serve status --json` output forwards to MIA."""
    return any(f"{host}:{port}" in text for host in ("127.0.0.1", "localhost"))


def serve_command(port: int) -> str:
    return f"sudo tailscale serve --bg http://127.0.0.1:{port}"


def tailscale_info(port: int, run: Callable = subprocess.run, which: Callable = shutil.which) -> TailscaleInfo:
    exe = which("tailscale")
    if exe is None:
        return TailscaleInfo(problem="Tailscale isn't installed on this computer (docs/SETUP_GUIDE.md, Part 8).")
    info = TailscaleInfo(installed=True)
    try:
        status = run([exe, "status", "--json"], capture_output=True, text=True, timeout=5)
        info.running, info.address = parse_tailscale_status(status.stdout)
        if not info.running:
            info.problem = "Tailscale is installed but not connected. Run: sudo tailscale up"
            return info
        serve = run([exe, "serve", "status", "--json"], capture_output=True, text=True, timeout=5)
        info.serving_mia = serve_forwards_to(serve.stdout or "", port)
    except (OSError, subprocess.SubprocessError) as exc:
        info.problem = f"Couldn't ask Tailscale: {exc}"
    return info


# ---------------------------------------------------------------------------
# The server
# ---------------------------------------------------------------------------


@dataclass
class PhoneServerStatus:
    enabled: bool
    running: bool
    host: str
    port: int
    error: str = ""
    profiles_with_password: int = 0
    phones: list[tuple[str, float]] = field(default_factory=list)  # (profile_id, last seen), newest first


def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name == "posix":
            # Like uvicorn itself: a port just released by switching off
            # (TIME_WAIT) is free to use again; one still listening isn't.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
            return True
        except OSError:
            return False


class PhoneServer:
    def __init__(self, context) -> None:
        self.context = context
        self._server = None  # uvicorn.Server
        self._thread: Optional[threading.Thread] = None
        self._app = None
        self._relay_registered = False
        self._local = False  # the desktop's own web view uses it (ensure_local)
        self._local_tokens: set[str] = set()
        self.last_error = ""

    @property
    def config(self):
        return self.context.config

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("server.enabled", False))

    @property
    def host(self) -> str:
        return str(self.config.get("server.host", "127.0.0.1") or "127.0.0.1")

    @property
    def port(self) -> int:
        return int(self.config.get("server.port", DEFAULT_PORT) or DEFAULT_PORT)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def set_enabled(self, enabled: bool) -> bool:
        """The Settings switch: saves the choice and starts/stops now.
        Returns whether the server is running afterwards."""
        self.config.set("server.enabled", bool(enabled))
        self.config.save()
        if enabled:
            return self.start()
        if self._local:
            # The desktop's web view still needs it; with phone access off,
            # server/app.py turns away anything forwarded from outside.
            return self.running
        self.stop()
        return False

    def start(self) -> bool:
        """Mobile access (2026-09-12): the phone API server (server/app.py)
        on a daemon thread in this process, on the same context every
        screen shares, so events raised anywhere reach the phone (web push
        relay). The server thread reads/writes the same managers as the
        GUI thread with no new locking, an accepted simplification scoped
        to this opt-in feature. Loopback by default: the phone reaches MIA
        through `tailscale serve`, which adds HTTPS (needed for the phone's
        microphone). Never raises: problems land in last_error."""
        if self.running:
            return True
        self.last_error = ""
        try:
            import uvicorn

            from core.web_push import register_notification_relay
            from server.app import create_app
        except ImportError:
            self.last_error = "The phone server's packages aren't installed. Run: pip install -r requirements.txt"
            log.warning("Phone server: fastapi/uvicorn/pywebpush aren't installed.")
            return False
        host, port = self.host, self.port
        if not port_free(host, port):
            self.last_error = f"Port {port} is already in use (is another copy of MIA running?)."
            log.warning("Phone server: %s", self.last_error)
            return False
        self._app = create_app(self.context)
        self._server = uvicorn.Server(uvicorn.Config(self._app, host=host, port=port, log_level="warning"))
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="mia-mobile-server")
        self._thread.start()
        deadline = time.monotonic() + _START_WAIT_SECONDS
        while time.monotonic() < deadline and self._thread.is_alive() and not self._server.started:
            time.sleep(0.05)
        if not (self._thread.is_alive() and self._server.started):
            self.last_error = f"The phone server couldn't start on port {port}; see logs/."
            log.warning("Phone server: didn't start on %s:%d.", host, port)
            return False
        log.info("Phone server started on %s:%d.", host, port)
        if not self._relay_registered:
            # Notifications also go out as phone push (Mobile Phase 2).
            register_notification_relay(self.context)
            self._relay_registered = True
        return True

    def ensure_local(self) -> bool:
        """For the desktop's own web view (Phase 2, DEC-0012): make sure
        the server runs, even with phone access off. With phone access
        off, server/app.py turns away anything forwarded from outside, so
        this doesn't open MIA to the phone. Returns whether it's running."""
        self._local = True
        return self.start()

    def local_session(self, profile_id: str) -> Optional[str]:
        """A sign-in token for the person already signed in at the
        desktop, so the web view needs no second password. None if the
        server isn't running."""
        if self._app is None:
            return None
        import secrets

        token = secrets.token_urlsafe(32)
        self._app.state.sessions[token] = profile_id
        self._local_tokens.add(token)  # the desktop, not a phone: left out of "phone last connected"
        return token

    @property
    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._server = self._thread = self._app = None
        log.info("Phone server stopped.")

    def status(self) -> PhoneServerStatus:
        profiles = getattr(self.context, "profiles", None)
        with_password = sum(1 for p in profiles.list_profiles() if p.has_password) if profiles else 0
        phones: list[tuple[str, float]] = []
        if self._app is not None and self.running:
            sessions, last_seen = self._app.state.sessions, getattr(self._app.state, "last_seen", {})
            phones = sorted(((sessions[t], seen) for t, seen in list(last_seen.items())
                             if t in sessions and t not in self._local_tokens),
                            key=lambda pair: -pair[1])
        return PhoneServerStatus(
            enabled=self.enabled, running=self.running, host=self.host, port=self.port, error=self.last_error,
            profiles_with_password=with_password, phones=phones,
        )


def describe_last_seen(seconds_ago: float) -> str:
    """Pure logic. 'just now', '5 minutes ago', '2 hours ago', '3 days ago'."""
    if seconds_ago < 90:
        return "just now"
    minutes = int(seconds_ago // 60)
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    return f"{hours // 24} days ago"


def describe_status(status: PhoneServerStatus, tailscale: Optional[TailscaleInfo], now: float) -> list[str]:
    """Pure logic. The Settings page's checklist, one line each, in the
    order the owner fixes things."""
    lines: list[str] = []
    if not status.enabled:
        return ["Phone access is off."]
    if status.running:
        lines.append(f"✓ MIA is listening for your phone (port {status.port}).")
    else:
        lines.append(f"✕ Not running: {status.error or 'starting…'}")
    if status.profiles_with_password:
        lines.append("✓ A profile has a password for signing in from the phone.")
    else:
        lines.append("✕ Give your profile a password (Change Password, above): the phone sign-in needs one.")
    if tailscale is not None:
        if tailscale.problem:
            lines.append(f"✕ {tailscale.problem}")
        elif not tailscale.serving_mia:
            lines.append(f"✕ Tailscale isn't forwarding to MIA yet. Run once: {serve_command(status.port)}")
        else:
            lines.append(f"✓ Your phone address: {tailscale.address}")
    if status.phones:
        _, seen = status.phones[0]
        lines.append(f"✓ Phone last connected {describe_last_seen(now - seen)}.")
    elif status.running:
        lines.append("… No phone has signed in since MIA started.")
    return lines
