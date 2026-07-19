"""
core.system_health
=====================

Point-in-time system health readings (CPU/RAM/disk/network/temperature)
via `psutil` — originally lived in modules/diagnostics/module.py (v0.7
milestone 7.1) as that module's "own exclusive concern", deliberately
not promoted to core/ at the time since nothing else needed it. Moved
here when milestone 5.7 (Assistant action-registry expansion) needed
the exact same reading for a `get_system_health` assistant action:
core/ (specifically core/application.py's `_register_assistant_actions()`)
must never import from modules/ per this project's layering rule (see
CLAUDE.md), so a shared reader has to live in core/ for both
modules/diagnostics/module.py's UI panel and the assistant action to
import — same "shared core service" shape as Journal/Alarm/Inventory/
Waypoint managers.

Plain functions, not a class/manager — this is stateless point-in-time
reads with no persistence, so a manager class would be pure ceremony.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import psutil

_BYTES_PER_GB = 1024 ** 3
_BYTES_PER_MB = 1024 ** 2


@dataclass
class SystemHealthSnapshot:
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    temperature_celsius: Optional[float]
    network_sent_mb: float
    network_recv_mb: float


def read_system_health(disk_path: str = "/") -> SystemHealthSnapshot:
    """
    Read a point-in-time system health snapshot via psutil.

    `psutil.cpu_percent(interval=None)` is non-blocking — it reports
    usage since the *previous* call in this process, not a fresh
    measurement, so the very first call after import is meaningless
    (usually 0.0). Callers that display this on a periodic timer
    (modules/diagnostics/module.py's get_widget()) should prime it with
    one throwaway call before the first real reading, rather than
    passing a blocking `interval` here and stalling the GUI thread on
    every refresh tick.
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_path)
    net = psutil.net_io_counters()
    return SystemHealthSnapshot(
        cpu_percent=cpu_percent,
        memory_percent=vm.percent,
        memory_used_gb=vm.used / _BYTES_PER_GB,
        memory_total_gb=vm.total / _BYTES_PER_GB,
        disk_percent=disk.percent,
        disk_used_gb=disk.used / _BYTES_PER_GB,
        disk_total_gb=disk.total / _BYTES_PER_GB,
        temperature_celsius=_read_cpu_temperature(),
        network_sent_mb=net.bytes_sent / _BYTES_PER_MB,
        network_recv_mb=net.bytes_recv / _BYTES_PER_MB,
    )


def read_uptime_seconds() -> float:
    """Seconds since boot — 2026-07-18 design handoff (CCH.zip's Dashboard
    console "Uptime" stat tile). Kept alongside read_system_health()
    rather than in gui/home_dashboard.py directly, same "all psutil
    calls live in core/system_health.py" convention that module's
    docstring already establishes."""
    return time.time() - psutil.boot_time()


def _read_cpu_temperature() -> Optional[float]:
    """
    First available sensor reading, or None. `sensors_temperatures()`
    isn't implemented on every platform (raises on Windows/macOS) and
    returns an empty dict on systems with no exposed thermal zone (true
    in this project's own dev sandbox/WSL2) — both degrade to None
    here rather than raising, same defensive pattern as every other
    "external system state might just not be there" read in this app.
    """
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    for entries in temps.values():
        for entry in entries:
            if entry.current is not None:
                return entry.current
    return None


def format_system_health(snapshot: SystemHealthSnapshot) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_system_health.py)."""
    temperature_line = (
        f"Temperature: {snapshot.temperature_celsius:.1f}°C"
        if snapshot.temperature_celsius is not None
        else "Temperature: not available on this system"
    )
    return "\n".join([
        f"CPU: {snapshot.cpu_percent:.1f}%",
        f"Memory: {snapshot.memory_percent:.1f}%  "
        f"({snapshot.memory_used_gb:.1f} / {snapshot.memory_total_gb:.1f} GB)",
        f"Disk: {snapshot.disk_percent:.1f}%  "
        f"({snapshot.disk_used_gb:.1f} / {snapshot.disk_total_gb:.1f} GB)",
        temperature_line,
        f"Network: {snapshot.network_sent_mb:.1f} MB sent / "
        f"{snapshot.network_recv_mb:.1f} MB received (since boot)",
    ])
