from core.dashboard_telemetry import compute_network_mbps, format_uptime_line


def test_format_uptime_line_hours_and_minutes():
    assert format_uptime_line(3 * 3600 + 42 * 60) == "3h 42m"


def test_format_uptime_line_under_an_hour():
    assert format_uptime_line(42 * 60) == "0h 42m"


def test_format_uptime_line_zero():
    assert format_uptime_line(0) == "0h 0m"


def test_compute_network_mbps_basic_rate():
    # 1 MB sent + 1 MB received over 1 second = 2 MB/s = 16 Mbps.
    assert compute_network_mbps(0.0, 0.0, 1.0, 1.0, 1.0) == 16.0


def test_compute_network_mbps_zero_elapsed_returns_zero():
    assert compute_network_mbps(0.0, 0.0, 0.0, 5.0, 5.0) == 0.0


def test_compute_network_mbps_negative_elapsed_returns_zero():
    assert compute_network_mbps(0.0, 0.0, -1.0, 5.0, 5.0) == 0.0


def test_compute_network_mbps_counter_reset_returns_zero_not_negative():
    # Simulates a network interface bouncing (cumulative counters reset lower).
    assert compute_network_mbps(100.0, 100.0, 1.0, 1.0, 1.0) == 0.0


def test_compute_network_mbps_no_change_returns_zero():
    assert compute_network_mbps(10.0, 10.0, 1.0, 10.0, 10.0) == 0.0
