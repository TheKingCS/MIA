"""
core.device_framework
========================

Connected Device Framework — docs/ROADMAP.md milestone 11.1, the first
piece of Field Kit. Detects and identifies devices physically attached
to this Pi: USB storage (drives, SD cards, other Pis in USB
mass-storage mode) via `lsblk`, and serial/MCU boards (Arduino, ESP32,
etc.) via `pyserial`'s port enumeration. This is the shared core
service `docs/ROADMAP.md`'s "Connected Device Framework" row already
named (previously only earmarked for Fleet/Smart Home/Vehicle OBD, none
of which are built yet) — built generally from the start rather than
Fleet-specific, so Field Kit's Device Manager (11.2) can be its first
real consumer.

Detection only — no actions (browse/flash/eject) here; those are 11.2+
and live in `modules/field_kit/module.py`, since acting on a device
(e.g. opening the Files module at its mount point) is a GUI-facing
concern, not this service's.

Storage detection shells out to `lsblk` (present on any Linux target,
including the Pi) rather than a Python binding — parsing `lsblk -J`'s
JSON output is simpler and more portable than wrapping `pyudev` (which
needs libudev, a system package, same "no sudo" risk class as
`sounddevice`'s PortAudio dependency). Only external-looking devices
are returned (`removable` flag or `tran == "usb"`) — this deliberately
excludes the Pi's own boot media and any internal/virtual disks (this
dev sandbox's WSL2 environment reports several "Virtual Disk" block
devices with no transport at all; none of those should ever show up as
an "attached device").

**`is_boot_device()` is a second, independent exclusion, always
applied on top of the `is_external` filter — found while designing
milestone 11.3's OS-flashing confirmation flow.** SD/MMC card readers
commonly report `rm: 1` (removable) for the card itself, which means a
Raspberry Pi's own boot microSD could satisfy `is_external` too if it
were ever queried the same way a USB stick is — `is_external` alone is
not a safe enough guarantee that a device isn't the one this OS is
currently running from. `is_boot_device()` instead asks the kernel
directly (`findmnt -no SOURCE /` -> `lsblk -no PKNAME` to resolve a
partition back to its parent disk) and fails **closed**: if either
command errors or returns something unparseable, the device is treated
as *if it were* the boot device (excluded), never the reverse — an
unrecoverable mistake here is a bricked Pi, so an uncertain "maybe"
must resolve to "don't touch it," not "probably fine." This filter is
applied inside `list_block_devices()` itself, not just at the future
flashing UI, so it retroactively protects 11.2's already-shipped
"Eject Safely"/"Browse Files" actions too — those should never have
been able to target the boot device either.

Serial detection uses `pyserial`'s `serial.tools.list_ports.comports()`
— pure enumeration, no port is ever opened here — filtered to ports
with a USB vid/pid (`SerialDevice.is_external`), same reasoning as
`BlockDevice.is_external`: this dev sandbox's WSL2 environment always
reports `/dev/ttyS0`-`/dev/ttyS7` (virtual legacy COM-port passthrough)
whether or not anything is actually plugged in, and none of those have
a vid/pid — a real USB-attached board always does, from its USB
descriptor. Board identification is a small built-in VID:PID lookup
table for common boards (FTDI/CH340 -> Arduino-family, CP210x -> ESP32)
— "good enough", deliberately not an exhaustive hardware database (same
"don't over-engineer" reasoning as `docs/ROADMAP.md`'s other
identification tables).

`DeviceFramework` itself owns no timer — core/ services don't do
async/threading (see CLAUDE.md's "known intentional simplifications").
`refresh()` is a plain, repeatable poll-and-diff method meant to be
called from a widget-owned `QTimer` (`modules/field_kit/module.py`,
same pattern as `modules/diagnostics/module.py`'s System Health panel),
not from here.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import serial.tools.list_ports

from core.logger import get_logger

if TYPE_CHECKING:
    from core.app_context import AppContext

log = get_logger(__name__)

_LSBLK_COLUMNS = "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,TRAN,RM"
_LSBLK_TIMEOUT_SECONDS = 5.0

# (vid, pid) exact matches checked before vid-only fallbacks below —
# some vendors (FTDI, Espressif) reuse one VID across many boards, so a
# pid-specific entry is more precise where it exists.
_VID_PID_BOARDS: dict[tuple[int, int], str] = {
    (0x1A86, 0x7523): "CH340 USB-Serial (common on Arduino Uno/Nano clones)",
    (0x10C4, 0xEA60): "CP210x USB-Serial (common on ESP32/ESP8266 dev boards)",
}
_VID_ONLY_BOARDS: dict[int, str] = {
    0x2341: "Arduino (official board)",
    0x0403: "FTDI USB-Serial (common on many Arduino-family boards)",
    0x303A: "Espressif native USB (ESP32-S2/S3)",
}


def identify_serial_board(vid: Optional[int], pid: Optional[int]) -> Optional[str]:
    if vid is None:
        return None
    if pid is not None and (vid, pid) in _VID_PID_BOARDS:
        return _VID_PID_BOARDS[(vid, pid)]
    return _VID_ONLY_BOARDS.get(vid)


@dataclass
class BlockDevice:
    name: str
    size: str
    mountpoint: Optional[str]
    fstype: Optional[str]
    model: str
    tran: Optional[str]
    removable: bool

    @property
    def is_external(self) -> bool:
        """
        The filter that separates "an attached USB drive/SD card" from
        every internal/virtual disk `lsblk` also reports — without
        this, the Pi's own boot media (and this dev sandbox's WSL2
        virtual disks) would show up as "connected devices".
        """
        return self.removable or self.tran == "usb"

    @property
    def display_name(self) -> str:
        label = self.model.strip() if self.model else self.name
        return f"{label} ({self.size})"


@dataclass
class SerialDevice:
    device: str
    description: str
    vid: Optional[int]
    pid: Optional[int]

    @property
    def is_external(self) -> bool:
        """
        Real-hardware finding: this dev sandbox's WSL2 environment
        always reports /dev/ttyS0-ttyS7 (virtual legacy COM-port
        passthrough) with no vid/pid at all, regardless of whether
        anything is actually plugged in — without this filter, "no
        serial devices attached" could never actually happen here.
        A real USB-attached board (FTDI/CH340/CP210x adapter, or a
        native-USB board like Arduino) always has vid/pid populated
        from its USB descriptor; a native/virtual UART never does —
        same "removable/USB transport" reasoning as
        BlockDevice.is_external.
        """
        return self.vid is not None

    @property
    def identified_as(self) -> Optional[str]:
        return identify_serial_board(self.vid, self.pid)

    @property
    def display_name(self) -> str:
        identified = self.identified_as
        label = identified if identified else self.description
        return f"{label} ({self.device})"


def is_boot_device(disk_name: str) -> bool:
    """
    True if `disk_name` (e.g. "sdd", "mmcblk0") is the disk this OS is
    currently running from — resolved via `findmnt -no SOURCE /`
    (the device/partition backing root) and `lsblk -no PKNAME` (walks a
    partition back to its parent disk; empty output means root is
    mounted directly on a whole disk with no partition table, so the
    disk name is read straight from the findmnt result instead).

    **Fails closed on any uncertainty**: if either command errors,
    times out, or returns unparseable output, this returns True (i.e.
    "assume every device might be the boot device") rather than False.
    A false positive here just means a legitimate device is
    (temporarily) refused for flashing/ejecting — annoying, but safe.
    A false negative could mean writing an OS image straight over the
    disk this code is running from. See this module's docstring for
    the specific real-world risk (SD card readers commonly report
    `removable`) that made this check necessary on top of
    `BlockDevice.is_external`.
    """
    try:
        root_source = subprocess.run(
            ["findmnt", "-no", "SOURCE", "/"],
            capture_output=True, text=True, timeout=_LSBLK_TIMEOUT_SECONDS, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        log.warning("findmnt failed — treating '%s' as the boot device to be safe.", disk_name)
        return True
    if not root_source:
        return True

    try:
        pkname = subprocess.run(
            ["lsblk", "-no", "PKNAME", root_source],
            capture_output=True, text=True, timeout=_LSBLK_TIMEOUT_SECONDS, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        log.warning("lsblk PKNAME lookup failed — treating '%s' as the boot device to be safe.", disk_name)
        return True

    root_disk_name = pkname if pkname else root_source.removeprefix("/dev/")
    return root_disk_name == disk_name


def list_block_devices() -> list[BlockDevice]:
    """External (USB/removable), non-boot storage devices only — see BlockDevice.is_external and is_boot_device()."""
    try:
        result = subprocess.run(
            ["lsblk", "-J", "-o", _LSBLK_COLUMNS],
            capture_output=True,
            text=True,
            timeout=_LSBLK_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        log.warning("lsblk unavailable or failed — no storage devices detected.")
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        log.warning("lsblk returned unparseable JSON — no storage devices detected.")
        return []

    devices = []
    for entry in data.get("blockdevices", []):
        if entry.get("type") != "disk":
            continue
        device = BlockDevice(
            name=entry.get("name", ""),
            size=entry.get("size") or "",
            mountpoint=entry.get("mountpoint"),
            fstype=entry.get("fstype"),
            model=(entry.get("model") or "").strip(),
            tran=entry.get("tran"),
            removable=bool(entry.get("rm", False)),
        )
        if device.is_external and not is_boot_device(device.name):
            devices.append(device)
    return devices


def device_still_matches(disk_name: str, expected_model: str, expected_size: str) -> bool:
    """
    Milestone 11.3's OS-flashing confirmation flow, Rail 4: re-checks
    that `disk_name` is still the *same physical device* the user
    selected and confirmed against — not just that a device with that
    Linux name (e.g. "sdb") still exists. Device names aren't stable
    across hotplug events: if the user's real target was unplugged and
    a *different* drive happened to be assigned the same name before
    the write started, model/size would no longer match and this
    returns False, so the caller can abort instead of writing an image
    to the wrong physical device. Also returns False (not just "doesn't
    match") if the device has since become the boot device somehow, or
    disappeared entirely, or is no longer external — same fail-closed
    posture as `is_boot_device()`.
    """
    for device in list_block_devices():
        if device.name == disk_name:
            return device.model == expected_model and device.size == expected_size
    return False


def flash_confirmation_matches(typed_text: str, disk_name: str) -> bool:
    """
    Rail 3: the exact, case-sensitive text a user must type to enable
    the "Flash" button in `gui/flash_confirm_dialog.py` — the disk's
    own Linux device name (e.g. "sdb"), not a generic "yes"/"confirm".
    Extracted as its own function (unlike `gui/delete_confirm_dialog.py`'s
    inline `text == self._item_name` check) so this one comparison, on
    the more dangerous of this project's two "type to confirm" flows,
    is unit-tested without needing a live Qt dialog.
    """
    return typed_text == disk_name


def list_serial_devices() -> list[SerialDevice]:
    """External (USB-attached) serial devices only — see SerialDevice.is_external."""
    try:
        ports = serial.tools.list_ports.comports()
    except Exception:
        log.warning("Serial port enumeration failed — no serial devices detected.")
        return []
    devices = [
        SerialDevice(device=p.device, description=p.description or p.device, vid=p.vid, pid=p.pid)
        for p in ports
    ]
    return [d for d in devices if d.is_external]


def _list_mounted_partitions(disk_name: str) -> list[tuple[str, str]]:
    """(partition_device_path, mountpoint) for every currently-mounted partition of the given disk — or the disk itself, if mounted directly with no partition table."""
    try:
        result = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,MOUNTPOINT,TYPE", f"/dev/{disk_name}"],
            capture_output=True,
            text=True,
            timeout=_LSBLK_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    mounted = []
    for entry in data.get("blockdevices", []):
        if entry.get("type") == "disk" and entry.get("mountpoint"):
            mounted.append((f"/dev/{entry['name']}", entry["mountpoint"]))
        for child in entry.get("children", []) or []:
            if child.get("type") == "part" and child.get("mountpoint"):
                mounted.append((f"/dev/{child['name']}", child["mountpoint"]))
    return mounted


def eject_storage_device(disk_name: str) -> tuple[bool, str]:
    """
    Unmounts every mounted partition of `disk_name` (e.g. "sdb") so it's
    safe to physically remove. Prefers `udisksctl unmount` — works for
    the logged-in user via polkit with no special permissions on any
    desktop Linux with udisks2 installed (present on Raspberry Pi OS
    Desktop by default) — falling back to plain `umount` if udisksctl
    isn't on PATH (this dev sandbox: it isn't); that fallback may need
    elevated permissions depending on how the partition was originally
    mounted.

    **Real-hardware verification pending**: this dev sandbox has no
    removable media attached to test an actual eject against — the
    unmount call itself is exercised only with mocked subprocess calls
    in tests/test_device_framework.py. Verify against a real USB drive
    on the Pi before relying on this in the field.
    """
    partitions = _list_mounted_partitions(disk_name)
    if not partitions:
        return True, f"'{disk_name}' has nothing mounted — already safe to remove."

    use_udisksctl = shutil.which("udisksctl") is not None
    failures = []
    for device_path, mountpoint in partitions:
        command = ["udisksctl", "unmount", "-b", device_path] if use_udisksctl else ["umount", mountpoint]
        try:
            subprocess.run(command, capture_output=True, text=True, timeout=10.0, check=True)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            failures.append(f"{mountpoint}: {exc}")

    if failures:
        return False, "Failed to unmount: " + "; ".join(failures)
    return True, f"'{disk_name}' safely ejected — {len(partitions)} partition(s) unmounted."


class DeviceFramework:
    def __init__(self, context: "AppContext") -> None:
        self.context = context
        self._known_storage: dict[str, BlockDevice] = {}
        self._known_serial: dict[str, SerialDevice] = {}

    def list_block_devices(self) -> list[BlockDevice]:
        return list_block_devices()

    def list_serial_devices(self) -> list[SerialDevice]:
        return list_serial_devices()

    def refresh(self) -> tuple[list[BlockDevice], list[SerialDevice]]:
        """
        Polls both device types, publishes "device.attached" /
        "device.detached" (kind, identifier, display_name) for anything
        that changed since the last call on `context.events` — the same
        event bus every other cross-component reaction in this app
        already uses — and returns the full current lists. Meant to be
        called on a timer owned by the caller (see this module's
        docstring); this class does not schedule its own polling.
        """
        current_storage = {d.name: d for d in self.list_block_devices()}
        current_serial = {d.device: d for d in self.list_serial_devices()}

        for name, device in current_storage.items():
            if name not in self._known_storage:
                self.context.events.publish(
                    "device.attached", kind="storage", identifier=name, display_name=device.display_name
                )
        for name in self._known_storage:
            if name not in current_storage:
                self.context.events.publish("device.detached", kind="storage", identifier=name)

        for path, device in current_serial.items():
            if path not in self._known_serial:
                self.context.events.publish(
                    "device.attached", kind="serial", identifier=path, display_name=device.display_name
                )
        for path in self._known_serial:
            if path not in current_serial:
                self.context.events.publish("device.detached", kind="serial", identifier=path)

        self._known_storage = current_storage
        self._known_serial = current_serial
        return list(current_storage.values()), list(current_serial.values())
