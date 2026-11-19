"""
core.sd_notify
==============

Telling systemd how MIA is doing (FW-04, REQ-ARC-002, REQ-REL-004): the `sd_notify` protocol, written here with the
standard library. Under a service with `Type=notify`, systemd sets `NOTIFY_SOCKET`; MIA sends `READY=1` once her core
is up, `STATUS=...` lines it shows in `systemctl status`, and, when the unit sets `WatchdogSec`, `WATCHDOG=1` often
enough (`watchdog_seconds()` says how often) or systemd restarts her. Anywhere else (Windows, a terminal, a test)
there's no socket and every call does nothing.

`READINESS` is the one vocabulary for how far up she is: `started` (the process runs), `core` (her stores and her
schedule are up: ready, as far as systemd is concerned), `models` (the model server answers too), `all` (and her
phone server is up where it's switched on).
"""

from __future__ import annotations

import os
import socket
from typing import Optional

READINESS = ("started", "core", "models", "all")


def _address() -> Optional[str]:
    """The socket systemd listens on, or None outside a notify service. An `@` name is Linux's abstract namespace."""
    where = os.environ.get("NOTIFY_SOCKET", "")
    if not where or not hasattr(socket, "AF_UNIX"):
        return None
    return "\0" + where[1:] if where.startswith("@") else where


def notify(*lines: str) -> bool:
    """Sends `KEY=value` lines to systemd; whether they went. Never raises."""
    where = _address()
    if where is None:
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.sendto("\n".join(lines).encode("utf-8"), where)
        return True
    except OSError:
        return False


def watchdog_seconds() -> float:
    """How often to ping the watchdog: half its timeout (`WATCHDOG_USEC`), or 0 when there's none for this process."""
    usec = os.environ.get("WATCHDOG_USEC", "")
    pid = os.environ.get("WATCHDOG_PID", "")
    if not usec.isdigit() or (pid and pid != str(os.getpid())):
        return 0.0
    return int(usec) / 2_000_000


def level(core: bool, models: bool, phone_wanted: bool, phone_up: bool) -> str:
    """Pure logic. How far up she is, from what's running (one of READINESS)."""
    if not core:
        return "started"
    if not models:
        return "core"
    return "all" if (phone_up or not phone_wanted) else "models"
