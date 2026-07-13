"""
tests.test_device_framework
==============================

Unit tests for core.device_framework (v0.11 milestone 11.1). No real
`lsblk`/serial hardware involved — `subprocess.run` and
`serial.tools.list_ports.comports` are monkeypatched to fakes, same
"fake the external dependency" approach as test_llm_manager.py mocking
urlopen. identify_serial_board() and BlockDevice.is_external are pure
logic, tested directly with constructed values.
"""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import core.device_framework as device_framework_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.device_framework import (
    BlockDevice,
    DeviceFramework,
    SerialDevice,
    identify_serial_board,
    list_block_devices,
    list_serial_devices,
)
from core.event_bus import EventBus


class _FakeCompletedProcess:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def _fake_lsblk(blockdevices: list[dict]):
    payload = json.dumps({"blockdevices": blockdevices})

    def fake_run(args, capture_output, text, timeout, check):
        return _FakeCompletedProcess(payload)

    return fake_run


# ----------------------------------------------------------------------
# BlockDevice.is_external
# ----------------------------------------------------------------------

def test_removable_disk_is_external():
    device = BlockDevice(name="sdb", size="32G", mountpoint=None, fstype="ext4", model="SanDisk", tran=None, removable=True)
    assert device.is_external is True


def test_usb_transport_disk_is_external():
    device = BlockDevice(name="sdb", size="32G", mountpoint=None, fstype="ext4", model="SanDisk", tran="usb", removable=False)
    assert device.is_external is True


def test_internal_non_removable_disk_is_not_external():
    device = BlockDevice(name="sda", size="1T", mountpoint="/", fstype="ext4", model="Virtual Disk", tran=None, removable=False)
    assert device.is_external is False


# ----------------------------------------------------------------------
# SerialDevice.is_external
# ----------------------------------------------------------------------

def test_serial_device_with_vid_is_external():
    device = SerialDevice(device="/dev/ttyUSB0", description="CH340", vid=0x1A86, pid=0x7523)
    assert device.is_external is True


def test_serial_device_without_vid_is_not_external():
    """
    Regression test: found via real integration testing (not mocks) —
    this dev sandbox's WSL2 environment always reports /dev/ttyS0-
    /dev/ttyS7 with no vid/pid, whether or not anything is plugged in.
    Without this filter, "no serial devices attached" could never
    actually happen here.
    """
    device = SerialDevice(device="/dev/ttyS0", description="n/a", vid=None, pid=None)
    assert device.is_external is False


# ----------------------------------------------------------------------
# identify_serial_board
# ----------------------------------------------------------------------

def test_identifies_ch340_by_exact_vid_pid():
    assert identify_serial_board(0x1A86, 0x7523) == "CH340 USB-Serial (common on Arduino Uno/Nano clones)"


def test_identifies_ftdi_by_vid_only():
    assert identify_serial_board(0x0403, 0x1234) == "FTDI USB-Serial (common on many Arduino-family boards)"


def test_unknown_vid_returns_none():
    assert identify_serial_board(0x9999, 0x0001) is None


def test_none_vid_returns_none():
    assert identify_serial_board(None, None) is None


# ----------------------------------------------------------------------
# list_block_devices
# ----------------------------------------------------------------------

def test_list_block_devices_filters_to_external_only(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_lsblk([
            {"name": "sda", "size": "1T", "type": "disk", "mountpoint": "/", "fstype": "ext4", "model": "Virtual Disk", "tran": None, "rm": False},
            {"name": "sdb", "size": "32G", "type": "disk", "mountpoint": None, "fstype": "ext4", "model": "SanDisk Ultra", "tran": "usb", "rm": True},
        ]),
    )
    devices = list_block_devices()
    assert [d.name for d in devices] == ["sdb"]
    assert devices[0].display_name == "SanDisk Ultra (32G)"


def test_list_block_devices_ignores_non_disk_entries(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_lsblk([
            {"name": "sdb", "size": "32G", "type": "disk", "mountpoint": None, "fstype": None, "model": "SanDisk", "tran": "usb", "rm": True},
            {"name": "sdb1", "size": "32G", "type": "part", "mountpoint": "/media/usb", "fstype": "ext4", "model": "", "tran": None, "rm": True},
        ]),
    )
    devices = list_block_devices()
    assert [d.name for d in devices] == ["sdb"]


def test_list_block_devices_returns_empty_when_lsblk_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        raise OSError("lsblk not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert list_block_devices() == []


def test_list_block_devices_returns_empty_on_malformed_json(monkeypatch):
    def fake_run(args, capture_output, text, timeout, check):
        return _FakeCompletedProcess("not json")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert list_block_devices() == []


# ----------------------------------------------------------------------
# list_serial_devices
# ----------------------------------------------------------------------

def test_list_serial_devices_maps_ports(monkeypatch):
    fake_port = SimpleNamespace(device="/dev/ttyUSB0", description="USB-SERIAL CH340", vid=0x1A86, pid=0x7523)
    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", lambda: [fake_port])

    devices = list_serial_devices()
    assert len(devices) == 1
    assert devices[0].device == "/dev/ttyUSB0"
    assert devices[0].identified_as == "CH340 USB-Serial (common on Arduino Uno/Nano clones)"
    assert "CH340" in devices[0].display_name


def test_list_serial_devices_filters_out_ports_without_vid(monkeypatch):
    real_board = SimpleNamespace(device="/dev/ttyUSB0", description="USB-SERIAL CH340", vid=0x1A86, pid=0x7523)
    virtual_com_port = SimpleNamespace(device="/dev/ttyS0", description="n/a", vid=None, pid=None)
    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", lambda: [real_board, virtual_com_port])

    devices = list_serial_devices()
    assert [d.device for d in devices] == ["/dev/ttyUSB0"]


def test_list_serial_devices_returns_empty_when_enumeration_fails(monkeypatch):
    def fake_comports():
        raise Exception("no ports")

    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", fake_comports)
    assert list_serial_devices() == []


# ----------------------------------------------------------------------
# DeviceFramework.refresh() — diffing + event publishing
# ----------------------------------------------------------------------

class _RecordingEvents:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish(self, event_name, **kwargs):
        self.published.append((event_name, kwargs))


def _make_framework() -> tuple[DeviceFramework, _RecordingEvents]:
    events = _RecordingEvents()
    context = AppContext(config=ConfigManager(), events=events)
    return DeviceFramework(context), events


def test_refresh_publishes_attached_event_for_new_storage_device(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_lsblk([{"name": "sdb", "size": "32G", "type": "disk", "mountpoint": None, "fstype": "ext4", "model": "SanDisk", "tran": "usb", "rm": True}]),
    )
    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", lambda: [])

    framework, events = _make_framework()
    framework.refresh()

    assert ("device.attached", {"kind": "storage", "identifier": "sdb", "display_name": "SanDisk (32G)"}) in events.published


def test_refresh_publishes_detached_event_when_storage_device_disappears(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_lsblk([{"name": "sdb", "size": "32G", "type": "disk", "mountpoint": None, "fstype": "ext4", "model": "SanDisk", "tran": "usb", "rm": True}]),
    )
    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", lambda: [])
    framework, events = _make_framework()
    framework.refresh()

    monkeypatch.setattr(subprocess, "run", _fake_lsblk([]))
    events.published.clear()
    framework.refresh()

    assert ("device.detached", {"kind": "storage", "identifier": "sdb"}) in events.published


def test_refresh_does_not_republish_for_unchanged_device(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_lsblk([{"name": "sdb", "size": "32G", "type": "disk", "mountpoint": None, "fstype": "ext4", "model": "SanDisk", "tran": "usb", "rm": True}]),
    )
    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", lambda: [])
    framework, events = _make_framework()
    framework.refresh()
    events.published.clear()
    framework.refresh()

    assert events.published == []


def test_refresh_publishes_attached_event_for_new_serial_device(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_lsblk([]))
    fake_port = SimpleNamespace(device="/dev/ttyUSB0", description="USB-SERIAL", vid=0x1A86, pid=0x7523)
    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", lambda: [fake_port])

    framework, events = _make_framework()
    framework.refresh()

    published_kinds = [kwargs["kind"] for _, kwargs in events.published if _ == "device.attached"]
    assert "serial" in published_kinds


def test_refresh_returns_current_device_lists(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_lsblk([{"name": "sdb", "size": "32G", "type": "disk", "mountpoint": None, "fstype": "ext4", "model": "SanDisk", "tran": "usb", "rm": True}]),
    )
    monkeypatch.setattr(device_framework_module.serial.tools.list_ports, "comports", lambda: [])

    framework, _ = _make_framework()
    storage, serial_devices = framework.refresh()

    assert [d.name for d in storage] == ["sdb"]
    assert serial_devices == []
