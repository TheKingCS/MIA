"""
core.dashboard_telemetry
===========================

Pure telemetry math for the redesigned Home dashboard's gauges
(2026-07-18 design handoff, CCH.zip's Dashboard console) — no Qt, no
psutil calls of its own, testable in isolation (see
tests/test_dashboard_telemetry.py). `gui/home_dashboard.py` owns the
actual `core.system_health.read_system_health()` calls and passes
their numbers in here.

Network throughput needs a *rate* (Mbps), not the cumulative
since-boot totals `SystemHealthSnapshot` carries — `compute_network_mbps()`
diffs two readings taken `elapsed_seconds` apart (the dashboard's own
5-second refresh cadence supplies this naturally, one snapshot held
over from the previous tick).
"""

from __future__ import annotations


def format_uptime_line(seconds: float) -> str:
    """"3h 42m" style — matches the design's own "Since boot" stat tile."""
    total_minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def compute_network_mbps(prev_sent_mb: float, prev_recv_mb: float, elapsed_seconds: float, sent_mb: float, recv_mb: float) -> float:
    """
    Combined send+receive rate in Mbps between a previous reading
    (`prev_sent_mb`/`prev_recv_mb`, cumulative since-boot totals) and a
    current one (`sent_mb`/`recv_mb`), `elapsed_seconds` apart. Returns
    0.0 for a non-positive interval or an apparent decrease (counters
    reset, e.g. a network interface bounced) rather than a negative
    rate, which would just be confusing on a gauge.
    """
    if elapsed_seconds <= 0:
        return 0.0
    delta_mb = (sent_mb - prev_sent_mb) + (recv_mb - prev_recv_mb)
    if delta_mb <= 0:
        return 0.0
    return (delta_mb * 8.0) / elapsed_seconds
