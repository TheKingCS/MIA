"""
tests.test_system_health
===========================

Unit tests for core.system_health (moved here from
modules.diagnostics.module in milestone 5.7 — see that module's own
docstring and core/system_health.py's docstring for why). format_system_health()
is tested with hand-built snapshots (pure, deterministic).
read_system_health()/_read_cpu_temperature() are tested against
monkeypatched psutil calls rather than real system state, so results
don't vary by machine/CI — same reasoning as test_llm_manager.py
mocking urlopen rather than hitting a real server.
"""

from __future__ import annotations

from types import SimpleNamespace

import core.system_health as system_health
from core.system_health import SystemHealthSnapshot, format_system_health, read_system_health, read_uptime_seconds


def _snapshot(**overrides) -> SystemHealthSnapshot:
    defaults = dict(
        cpu_percent=12.3,
        memory_percent=45.6,
        memory_used_gb=3.5,
        memory_total_gb=8.0,
        disk_percent=67.8,
        disk_used_gb=100.0,
        disk_total_gb=250.0,
        temperature_celsius=42.0,
        network_sent_mb=10.0,
        network_recv_mb=20.0,
    )
    defaults.update(overrides)
    return SystemHealthSnapshot(**defaults)


def test_format_system_health_includes_all_readings():
    text = format_system_health(_snapshot())
    assert "CPU: 12.3%" in text
    assert "Memory: 45.6%  (3.5 / 8.0 GB)" in text
    assert "Disk: 67.8%  (100.0 / 250.0 GB)" in text
    assert "Temperature: 42.0°C" in text
    assert "Network: 10.0 MB sent / 20.0 MB received (since boot)" in text


def test_format_system_health_handles_missing_temperature():
    text = format_system_health(_snapshot(temperature_celsius=None))
    assert "Temperature: not available on this system" in text


def test_read_system_health_converts_units_correctly(monkeypatch):
    monkeypatch.setattr(system_health.psutil, "cpu_percent", lambda interval=None: 55.0)
    monkeypatch.setattr(
        system_health.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=50.0, used=4 * system_health._BYTES_PER_GB, total=8 * system_health._BYTES_PER_GB),
    )
    monkeypatch.setattr(
        system_health.psutil,
        "disk_usage",
        lambda path: SimpleNamespace(percent=25.0, used=50 * system_health._BYTES_PER_GB, total=200 * system_health._BYTES_PER_GB),
    )
    monkeypatch.setattr(
        system_health.psutil,
        "net_io_counters",
        lambda: SimpleNamespace(bytes_sent=5 * system_health._BYTES_PER_MB, bytes_recv=15 * system_health._BYTES_PER_MB),
    )
    monkeypatch.setattr(system_health.psutil, "sensors_temperatures", lambda: {}, raising=False)

    snapshot = read_system_health()

    assert snapshot.cpu_percent == 55.0
    assert snapshot.memory_used_gb == 4.0
    assert snapshot.memory_total_gb == 8.0
    assert snapshot.disk_used_gb == 50.0
    assert snapshot.disk_total_gb == 200.0
    assert snapshot.network_sent_mb == 5.0
    assert snapshot.network_recv_mb == 15.0
    assert snapshot.temperature_celsius is None


def test_read_cpu_temperature_returns_first_reading(monkeypatch):
    monkeypatch.setattr(
        system_health.psutil,
        "sensors_temperatures",
        lambda: {"coretemp": [SimpleNamespace(current=61.5, label="Package")]},
        raising=False,  # psutil has no sensors_temperatures() on Windows
    )
    assert system_health._read_cpu_temperature() == 61.5


def test_read_cpu_temperature_returns_none_when_empty(monkeypatch):
    monkeypatch.setattr(system_health.psutil, "sensors_temperatures", lambda: {}, raising=False)
    assert system_health._read_cpu_temperature() is None


def test_read_cpu_temperature_returns_none_when_not_implemented(monkeypatch):
    def _raise():
        raise AttributeError("module 'psutil' has no attribute 'sensors_temperatures'")

    monkeypatch.setattr(system_health.psutil, "sensors_temperatures", _raise, raising=False)
    assert system_health._read_cpu_temperature() is None


def test_read_uptime_seconds(monkeypatch):
    monkeypatch.setattr(system_health.psutil, "boot_time", lambda: 1000.0)
    monkeypatch.setattr(system_health.time, "time", lambda: 4600.0)
    assert read_uptime_seconds() == 3600.0
