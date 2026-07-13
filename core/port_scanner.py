"""
core.port_scanner
====================

Pure-Python TCP connect-scan port scanner — docs/ROADMAP.md milestone
11.5, Field Kit's Security/Network Toolkit. Deliberately doesn't wrap
`nmap`: `nmap` isn't installed in this dev sandbox and can't be added
without sudo (the same "no sudo" wall as every other missing system
package this project has hit — Ollama's portable binary, `gh`'s
workaround). A plain TCP connect scan needs no privileged raw sockets
and no external binary, unlike a SYN scan or OS fingerprinting (both
genuinely need `nmap`/root, and stay out of scope until this can be
tested somewhere that has it — same "confirmed blocked, not just
deferred" reasoning as Media/Music's missing `libpulse`).
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_TIMEOUT_SECONDS = 0.5

#: A short, common-ports default so a scan without an explicit port list
#: doesn't take forever — not exhaustive, same "good enough, not an
#: exhaustive database" reasoning as core/hash_identifier.py's format
#: table and core/device_framework.py's board-identification table.
COMMON_PORTS: tuple[int, ...] = (21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 8080, 8443)


@dataclass
class PortScanResult:
    host: str
    open_ports: list[int] = field(default_factory=list)
    scanned_count: int = 0
    error: str = ""  # set (and open_ports/scanned_count left empty) if `host` couldn't be resolved


def scan_ports(host: str, ports: Optional[list[int]] = None, timeout: float = _DEFAULT_TIMEOUT_SECONDS) -> PortScanResult:
    """
    Attempts a real TCP connection to each port; success means "open."
    Sequential, not threaded/async — fine for a field tool checking a
    handful of common ports on one host at a time, not a fast parallel
    sweep (that's a different tool: `nmap` itself, not what this
    reimplements). Resolves `host` once upfront rather than letting a
    bad hostname fail identically on every single port attempt.
    """
    target_ports = list(ports) if ports else list(COMMON_PORTS)

    try:
        resolved_ip = socket.gethostbyname(host)
    except socket.gaierror as exc:
        return PortScanResult(host=host, error=f"Could not resolve '{host}': {exc}")

    open_ports = []
    for port in target_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            if sock.connect_ex((resolved_ip, port)) == 0:
                open_ports.append(port)

    return PortScanResult(host=host, open_ports=open_ports, scanned_count=len(target_ports))
