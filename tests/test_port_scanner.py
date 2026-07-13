"""
tests.test_port_scanner
==========================

Unit tests for core.port_scanner. Uses a real local TCP server bound to
an ephemeral port (socket.bind(("127.0.0.1", 0))) rather than mocking
sockets or reaching out to a real remote host — deterministic (no
network/internet dependency) while still exercising the real
connect_ex() path, not a hand-copied simulation of it.
"""

from __future__ import annotations

import socket
import threading

import pytest

import core.port_scanner as port_scanner_module
from core.port_scanner import COMMON_PORTS, scan_ports


@pytest.fixture
def local_open_port():
    """Starts a real TCP listener on an OS-assigned free port, torn down after the test."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    stop = threading.Event()

    def accept_loop():
        server.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = server.accept()
                conn.close()
            except socket.timeout:
                continue

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()

    yield port

    stop.set()
    thread.join(timeout=2)
    server.close()


def _find_definitely_closed_port() -> int:
    """A port nothing is listening on: bind, grab the number, then close it immediately."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_scan_ports_detects_a_real_open_port(local_open_port):
    result = scan_ports("127.0.0.1", ports=[local_open_port], timeout=1.0)
    assert result.open_ports == [local_open_port]
    assert result.scanned_count == 1
    assert result.error == ""


def test_scan_ports_does_not_report_a_closed_port(local_open_port):
    closed_port = _find_definitely_closed_port()
    result = scan_ports("127.0.0.1", ports=[closed_port], timeout=0.3)
    assert result.open_ports == []
    assert result.scanned_count == 1


def test_scan_ports_mixed_open_and_closed(local_open_port):
    closed_port = _find_definitely_closed_port()
    result = scan_ports("127.0.0.1", ports=[local_open_port, closed_port], timeout=0.5)
    assert result.open_ports == [local_open_port]
    assert result.scanned_count == 2


def test_scan_ports_defaults_to_common_ports(local_open_port):
    result = scan_ports("127.0.0.1", timeout=0.1)
    assert result.scanned_count == len(COMMON_PORTS)


def test_scan_ports_unresolvable_host_returns_error_not_exception(monkeypatch):
    # Mocked rather than a real DNS lookup of a fake hostname: a real
    # lookup's failure mode (timeout duration, or a captive-portal/ISP
    # NXDOMAIN-hijack resolving it to *something*) isn't something this
    # test should depend on being fast or even actually failing.
    def _raise_gaierror(_host):
        raise socket.gaierror("mocked resolution failure")

    monkeypatch.setattr(port_scanner_module.socket, "gethostbyname", _raise_gaierror)

    result = scan_ports("this-host-does-not-matter", ports=[80], timeout=0.5)
    assert result.open_ports == []
    assert result.scanned_count == 0
    assert "could not resolve" in result.error.lower()
