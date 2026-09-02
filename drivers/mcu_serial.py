"""
MIA Homestead — Pi <-> Safety MCU Serial Transport
v0.1

Implements docs/MCU_PROTOCOL.md's wire format: newline-delimited JSON
over a UART serial connection. Real, actively-missing gap found live
2026-09-02 (docs/DAY_ONE_READINESS.md, item #2) — confirmed by grep:
core/device_registry.py already builds real pair_confirm payloads
(build_pair_confirm_payload()) but nothing anywhere ever puts a byte
on a wire; announce_device() was explicitly documented as "manual test
call today," and main.py's execute_command() was explicitly a "v0.1
stand-in for real MCU dispatch," logging only. This sits squarely on
the critical path for docs/PILOT_VS_SCALE.md's own Priority #1 (flash
and prove the firmware) and #3 (run a real device pairing).

MCULink wraps a duck-typed "port" object (matching pyserial's Serial
interface: .write(bytes), .readline() -> bytes, .in_waiting) rather
than always constructing a real serial.Serial itself — the same
dependency-injection precedent this project already uses for
testability elsewhere (core/deploy_manager.py's repo_path override,
core/backup_manager.py's same pattern). This is what makes the whole
protocol layer testable today, against a fake in-memory port, with
zero real hardware — real hardware only needs to prove the physical
link (open_port() against a real device path) works, not validate the
protocol logic for the first time.

Never raises on a communication failure, matching
drivers/atlas_scientific_driver.py's own honest-failure convention —
a failed read/write, a missing/busy port, or a malformed line is a
real, expected operational condition for physical serial hardware, not
a bug to crash the control loop over.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("mia_homestead.mcu_serial")

DEFAULT_BAUDRATE = 115200
DEFAULT_READ_TIMEOUT_SECONDS = 1.0


class MCULink:
    """One open connection to one MCU — paired or not-yet-paired
    (hardware_id is only known once an announce message has actually
    been heard on it)."""

    def __init__(self, port, hardware_id: str | None = None):
        self.port = port
        self.hardware_id = hardware_id
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _send(self, message: dict) -> bool:
        try:
            line = (json.dumps(message) + "\n").encode("utf-8")
            self.port.write(line)
            return True
        except Exception as e:
            logger.warning("MCU link write failed (%s): %s", message.get("type"), e)
            return False

    def send_heartbeat(self) -> bool:
        return self._send({
            "type": "heartbeat",
            "seq": self._next_seq(),
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        })

    def send_command(self, actuator_id: int, action: str,
                      duration_ms: int | None = None, dose_type: str | None = None) -> bool:
        msg = {"type": "command", "seq": self._next_seq(), "actuator_id": actuator_id, "action": action}
        if duration_ms is not None:
            msg["duration_ms"] = duration_ms
        if dose_type is not None:
            msg["dose_type"] = dose_type
        return self._send(msg)

    def send_pair_confirm(self, role: str, cell_id: int, controls: list[dict]) -> bool:
        return self._send({"type": "pair_confirm", "role": role, "cell_id": cell_id, "controls": controls})

    def send_resume_control(self) -> bool:
        return self._send({"type": "resume_control"})

    def read_message(self) -> dict | None:
        """One read attempt — returns a parsed message dict, or None
        if nothing's waiting or the line failed to parse. A malformed/
        partial line on a real noisy serial link is a real, expected
        condition (see MCU_PROTOCOL.md's own open item on checksums —
        this is exactly why that matters), not a crash."""
        try:
            if hasattr(self.port, "in_waiting") and not self.port.in_waiting:
                return None
            raw = self.port.readline()
        except Exception as e:
            logger.warning("MCU link read failed: %s", e)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8").strip())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("MCU link received an unparseable line: %r", raw)
            return None

    def close(self) -> None:
        try:
            self.port.close()
        except Exception:
            pass


def open_port(device_path: str, baudrate: int = DEFAULT_BAUDRATE,
              timeout: float = DEFAULT_READ_TIMEOUT_SECONDS) -> MCULink | None:
    """Real hardware entry point — opens an actual serial.Serial.
    Never raises: a missing/busy port is a real, expected operational
    condition (device unplugged, wrong path, permissions) — returns
    None and logs rather than crashing whatever's calling this."""
    try:
        import serial
    except ImportError:
        logger.warning("pyserial not installed — cannot open a real MCU serial port")
        return None
    try:
        port = serial.Serial(device_path, baudrate=baudrate, timeout=timeout)
    except Exception as e:
        logger.warning("Could not open MCU serial port %s: %s", device_path, e)
        return None
    return MCULink(port)


def list_available_ports() -> list[str]:
    """Real hardware entry point — enumerates serial ports currently
    present on this machine. Device paths only; a port list alone
    never tells you what's plugged into it — that's only knowable by
    listening for that port's announce message, per
    MCU_PROTOCOL.md's own "hardware_id, never human-assigned" stance."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    return [p.device for p in list_ports.comports()]
