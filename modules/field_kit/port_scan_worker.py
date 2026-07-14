"""
modules.field_kit.port_scan_worker
=====================================

Runs core.port_scanner.scan_ports() off the GUI thread — docs/ROADMAP.md
milestone 11.5. Scanning even the short COMMON_PORTS default can block
for several seconds (each closed/firewalled port waits out its own
timeout), so this is the same scoped `QThread`-per-run pattern as
`modules/field_kit/script_worker.py`'s `ScriptWorker` and
`core/chat_worker.py`'s `ChatWorker` — a blocking call runs
here, never directly in a button's click handler.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.port_scanner import PortScanResult, scan_ports


class PortScanWorker(QThread):
    result_ready = Signal(object)  # PortScanResult

    def __init__(self, host: str, ports: Optional[list[int]] = None) -> None:
        super().__init__()
        self._host = host
        self._ports = ports

    def run(self) -> None:
        result: PortScanResult = scan_ports(self._host, ports=self._ports)
        self.result_ready.emit(result)
