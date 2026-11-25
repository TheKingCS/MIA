"""
tests.test_esp32_lab
======================

The ESP32 lab bench (core/esp32_lab.py): a lab's PlatformIO project written (its libraries, its sketch, a Wi-Fi
secrets file with placeholders he fills in himself), never flashed with the placeholders still there or without
PlatformIO or a board; a flash runs pio's upload on the board's port; the board's serial output read and the lab's
checks passed from it; the next lab on his path when none is named.
With two boards plugged in, nothing is flashed or read until he says which; and each lab's read runs as long as its
markers need.
"""

from types import SimpleNamespace

import pytest

from core import esp32_lab as lab
from core import paths
from core.actions import ActionError
from core.esp32_path import PROGRAM


def test_a_labs_project_and_its_secrets_placeholder(tmp_path):
    """The dht lab's libraries in platformio.ini, its sketch in main.cpp; the wifi lab's secrets.h with placeholders,
    never overwritten once he's filled it in."""
    folder = lab.project("dht", tmp_path)
    assert "adafruit/DHT sensor library" in (folder / "platformio.ini").read_text()
    assert "MIA TEMP" in (folder / "src" / "main.cpp").read_text()
    wifi = lab.project("wifi", tmp_path)
    assert lab.needs_secrets(wifi)
    (wifi / "src" / "secrets.h").write_text('#define WIFI_NAME "home"\n#define WIFI_PASSWORD "x"\n')
    lab.project("wifi", tmp_path)
    assert not lab.needs_secrets(wifi)
    with pytest.raises(ValueError):
        lab.project("nope", tmp_path)


def test_flashing_needs_his_wifi_platformio_and_a_board_then_runs_the_upload(tmp_path, monkeypatch):
    """Placeholders: refused; no PlatformIO: refused; then pio's upload on the board's port."""
    from core import greenhouse_provision as gp

    monkeypatch.setattr(gp, "serial_ports", lambda: [{"device": "COM5", "description": "CP2102", "vid": 0x10C4,
                                                      "pid": 0xEA60}])
    with pytest.raises(ActionError, match="secrets.h"):
        lab.flash(None, "wifi", pio=["pio"], base=tmp_path)
    with pytest.raises(ActionError, match="PlatformIO"):
        lab.flash(None, "blink", pio=[], base=tmp_path)
    ran = []
    said = lab.flash(None, "blink", run=lambda cmd, timeout: (ran.append(cmd) or (0, "ok")), pio=["pio"],
                     base=tmp_path)
    assert ran[0][:4] == ["pio", "run", "-t", "upload"] and ran[0][-1] == "COM5" and "Flashed the blink lab" in said


def test_with_two_boards_plugged_in_nothing_is_flashed_or_read_until_he_says_which(monkeypatch):
    """Two ESP32-style USB chips: no port is picked, the flash card is refused with both ports named; one board: the
    card names its port and chip. "Hello MIA, flash the relay lab" is the relay lab, and "spot" isn't the pot lab."""
    from core import greenhouse_provision as gp

    two = [{"device": "COM5", "description": "CP2102", "vid": 0x10C4, "pid": 0xEA60},
           {"device": "COM7", "description": "CH340", "vid": 0x1A86, "pid": 0x7523}]
    monkeypatch.setattr(gp, "serial_ports", lambda: two)
    assert lab.board(pio=[])["port"] == "" and "COM5, COM7" in lab.board(pio=[])["missing"]
    with pytest.raises(ActionError, match="say which port"):
        lab.ACTIONS["esplab.flash"].describe(None, {"lesson": "blink"})
    monkeypatch.setattr(gp, "serial_ports", lambda: two[:1])
    assert "on COM5 (CP2102)" in lab.ACTIONS["esplab.flash"].describe(None, {"lesson": "blink"})
    assert lab.lesson_for(None, "hello MIA, flash the relay lab") == "relay"
    assert lab.lesson_for(None, "check the spot where it was") != "pot"


def test_a_labs_read_runs_as_long_as_its_markers_need(tmp_path):
    """The sleep lab's read is 25 seconds, the web lab's 20, the rest 8; a web lab not yet passed says to open its
    address while it reads."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(PROGRAM, goal="a soil node")
    asked = []
    reader = lambda port, seconds: (asked.append(seconds) or "MIA WIFI 192.168.1.50\n")  # noqa: E731
    got = lab.read_and_check(SimpleNamespace(paths=book), "web", "COM5", reader=reader)
    lab.read_and_check(SimpleNamespace(paths=book), "sleep", "COM5", reader=reader)
    lab.read_and_check(SimpleNamespace(paths=book), "blink", "COM5", reader=reader)
    assert asked == [20.0, 25.0, 8.0] and "Open http://<its address>/reading" in got["said"]


def test_checking_a_lab_reads_the_board_and_keeps_the_pass(tmp_path, monkeypatch):
    """The button lab, the board saying three presses: passed and kept; nothing said: told to flash it."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(PROGRAM, goal="a soil node")
    context = SimpleNamespace(paths=book)
    said = lab.check(context, "button", "COM5", reader=lambda port, seconds: "MIA BUTTON 1\nMIA BUTTON 3\n")
    assert said.startswith("Passed:") and book.passed("esp32", "esp_button")
    assert "said nothing" in lab.check(context, "pot", "COM5", reader=lambda port, seconds: "")


def test_the_next_lab_on_his_path_or_the_one_named(tmp_path):
    """Named by id or title; not started: the first lab; after the blink passes, still stage 1's hello."""
    book = paths.PathBook(None, data_dir=tmp_path)
    context = SimpleNamespace(paths=book)
    assert lab.lesson_for(context, "flash the dht lab") == "dht"
    assert lab.lesson_for(context, "") == "blink"
    book.start(PROGRAM, goal="")
    book.attempt(PROGRAM, "esp_blink", True, how="board")
    assert lab.lesson_for(context, "") == "hello"
