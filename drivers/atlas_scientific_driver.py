"""
MIA Homestead — Atlas Scientific EZO Driver
v0.1

Real hardware driver for Atlas Scientific EZO circuits (pH, EC/TDS,
DO — same protocol family, different I2C address and calibration
commands) over I2C on a Raspberry Pi. This replaces drivers/simulator.py
for these two sensor types once hardware exists — same contract
(writes into sensor_readings), so nothing in modules/ or contracts/
needs to change.

Requires: smbus2 (`pip install smbus2 --break-system-packages`) and I2C
enabled on the Pi (`sudo raspi-config` -> Interface Options -> I2C).

Default I2C addresses (Atlas Scientific factory defaults):
    pH:  0x63
    EC:  0x64
    DO:  0x61
These can be changed on the device itself if you're running multiple
probes of the same type — see Atlas's datasheet for the "I2C" command.

Protocol basics (same across the EZO family):
- Write an ASCII command (e.g. b"R" for read, b"Cal,mid,7.00" for
  calibration) to the device's I2C address.
- Wait — reads take up to ~900ms depending on circuit type. Don't poll
  faster than that or you'll read a "still processing" status.
- Read up to 32 bytes back. First byte is a status code:
    1   = success, remaining bytes are the ASCII value, null-terminated
    2   = syntax error in the command sent
    254 = still processing, try reading again after a short wait
    255 = no data to send
"""

import argparse
import logging
import sqlite3
import time
from datetime import datetime

try:
    import smbus2
except ImportError:
    smbus2 = None  # allows this file to be imported/inspected without hardware present

logger = logging.getLogger("mia_homestead.atlas_driver")

STATUS_SUCCESS = 1
STATUS_SYNTAX_ERROR = 2
STATUS_STILL_PROCESSING = 254
STATUS_NO_DATA = 255

READ_DELAY_SECONDS = 0.9  # worst-case across the EZO family; safe default


class AtlasReadError(Exception):
    pass


class AtlasEZODriver:
    """Base driver for one EZO circuit. Subclass per probe type for
    range-plausibility checking (see AtlasPHDriver/AtlasECDriver below)."""

    i2c_address: int = None       # set by subclass
    plausible_range: tuple = None  # (min, max) — set by subclass

    def __init__(self, sensor_id: int, db_conn: sqlite3.Connection, bus_number: int = 1, i2c_address: int = None):
        if smbus2 is None:
            raise RuntimeError(
                "smbus2 is not installed. This driver requires real I2C hardware "
                "and the smbus2 package — install with: pip install smbus2 --break-system-packages"
            )
        self.sensor_id = sensor_id
        self.db = db_conn
        self.address = i2c_address or self.i2c_address
        self.bus = smbus2.SMBus(bus_number)

    def _send_command(self, command: str) -> None:
        data = list(command.encode("ascii"))
        self.bus.write_i2c_block_data(self.address, 0, data)

    def _read_response(self) -> str:
        data = self.bus.read_i2c_block_data(self.address, 0, 32)
        status = data[0]
        if status == STATUS_SUCCESS:
            raw = bytes(data[1:]).split(b"\x00")[0]
            return raw.decode("ascii").strip()
        elif status == STATUS_SYNTAX_ERROR:
            raise AtlasReadError(f"Syntax error sent to device at {hex(self.address)}")
        elif status == STATUS_STILL_PROCESSING:
            raise AtlasReadError("Device still processing — read too soon after command")
        elif status == STATUS_NO_DATA:
            raise AtlasReadError("Device has no data to send")
        else:
            raise AtlasReadError(f"Unknown status code: {status}")

    def read(self) -> float:
        """Sends the read command, waits the required delay, and returns
        the parsed float value. Raises AtlasReadError on any failure —
        callers should treat that the same as a stale/missing reading,
        NOT retry-until-success in a tight loop (that's how you end up
        polling faster than the device can respond)."""
        self._send_command("R")
        time.sleep(READ_DELAY_SECONDS)
        raw = self._read_response()
        try:
            value = float(raw)
        except ValueError:
            raise AtlasReadError(f"Could not parse response as float: {raw!r}")
        return value

    def read_and_store(self) -> None:
        """One full cycle: read the probe, validate against the
        physically plausible range for this probe type, write into
        sensor_readings. This is the method the main control loop calls
        — same 'write into sensor_readings' contract as the simulator,
        so modules/aquaponics_cell.py doesn't know or care whether it's
        reading simulated or real data."""
        try:
            value = self.read()
        except AtlasReadError as e:
            logger.warning("Sensor %s read failed: %s — no row written (correctly treated as stale)", self.sensor_id, e)
            return

        out_of_range = 0
        if self.plausible_range and not (self.plausible_range[0] <= value <= self.plausible_range[1]):
            out_of_range = 1
            logger.warning(
                "Sensor %s reading %.3f outside plausible range %s — flagging out_of_range",
                self.sensor_id, value, self.plausible_range,
            )

        self.db.execute(
            "INSERT INTO sensor_readings (sensor_id, value, is_stale, is_out_of_range) VALUES (?, ?, 0, ?)",
            (self.sensor_id, value, out_of_range),
        )
        self.db.commit()

    # ---------- Calibration ----------
    # Calibration procedure differs meaningfully by probe type (pH is a
    # 3-point cal against known buffer solutions; EC is typically a
    # single or dual-point cal against known conductivity standards) —
    # deliberately NOT automated here. Sending the wrong calibration
    # command silently miscalibrates the probe, which then feeds bad
    # data straight into dosing decisions. This stays a guided, manual,
    # one-command-at-a-time process. See Atlas's datasheet for your
    # specific probe before running any Cal command.

    def send_raw_command(self, command: str) -> str:
        """Escape hatch for calibration and other admin commands — sends
        exactly what you give it and returns the raw response. Use this
        interactively (see --calibrate mode below), never in the
        automated control loop."""
        self._send_command(command)
        time.sleep(READ_DELAY_SECONDS)
        return self._read_response()


class AtlasPHDriver(AtlasEZODriver):
    i2c_address = 0x63
    plausible_range = (0.0, 14.0)


class AtlasECDriver(AtlasEZODriver):
    i2c_address = 0x64
    plausible_range = (0.0, 20000.0)  # uS/cm, generous upper bound


PROBE_TYPES = {"ph": AtlasPHDriver, "ec": AtlasECDriver}


def interactive_calibration(probe_type: str, sensor_id: int, db_path: str):
    """Walks through calibration one command at a time, printing the raw
    device response after each step so a human confirms it looks right
    before proceeding — never runs a calibration sequence unattended."""
    conn = sqlite3.connect(db_path)
    driver_cls = PROBE_TYPES[probe_type]
    driver = driver_cls(sensor_id=sensor_id, db_conn=conn)

    print(f"\n=== Calibrating {probe_type.upper()} probe (sensor_id={sensor_id}) ===")
    print("Follow Atlas Scientific's calibration guide for your exact probe.")
    print("This will send whatever command you type, one at a time, and show the raw response.\n")
    print("Type 'done' when finished.\n")

    while True:
        cmd = input("Command to send (e.g. 'Cal,mid,7.00'): ").strip()
        if cmd.lower() == "done":
            break
        try:
            response = driver.send_raw_command(cmd)
            print(f"  -> {response}")
        except AtlasReadError as e:
            print(f"  -> ERROR: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--probe-type", choices=["ph", "ec"], required=True)
    parser.add_argument("--sensor-id", type=int, required=True, help="matching row id in the sensors table")
    parser.add_argument("--i2c-address", type=lambda x: int(x, 0), help="override default I2C address, e.g. 0x63")
    parser.add_argument("--interval", type=float, default=10.0, help="seconds between reads")
    parser.add_argument("--once", action="store_true", help="single read instead of continuous loop")
    parser.add_argument("--calibrate", action="store_true", help="interactive calibration mode")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    if args.calibrate:
        interactive_calibration(args.probe_type, args.sensor_id, args.db)
        return

    conn = sqlite3.connect(args.db)
    driver_cls = PROBE_TYPES[args.probe_type]
    driver = driver_cls(sensor_id=args.sensor_id, db_conn=conn, i2c_address=args.i2c_address)

    if args.once:
        driver.read_and_store()
        return

    print(f"Reading {args.probe_type} every {args.interval}s. Ctrl+C to stop.")
    try:
        while True:
            driver.read_and_store()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
