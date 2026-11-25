"""
tests.test_arduino_labs
=========================

Build With Arduino on his Mega or Nanos (core/arduino_path.py, core/boards.py, and the bench, simulator and course
page on any board): every check's marker is printed by a lab's sketch and only by its own; each lab wired as built
passes its checks in the simulator on the Arduino's 5 V and 10-bit ADC; a project built for the board he names; the
course read from his words; the flash card naming the board; building along by voice on the Arduino course.
"""

import re
from types import SimpleNamespace

import pytest

from core import arduino_path, boards, paths
from core import esp32_lab as bench
from core import esp32_sim as sim


def test_every_check_is_printed_by_its_own_lab_and_the_sketches_use_only_pins_both_boards_have():
    """Each check's marker comes from exactly the labs the bench says check it; no lab reaches a Mega-only pin."""
    for stage in arduino_path.PROGRAM.stages:
        for check in stage.checks:
            assert any(check in bench.checks_of(lab, "arduino") for lab in arduino_path.LABS), check.id
    for lab, spec in arduino_path.LABS.items():
        assert not re.search(r"\b(?:D|pin\s*)(1[4-9]|[2-5]\d)\b", spec["code"]), lab
        assert "printf" not in spec["code"] and "Serial.begin(9600)" in spec["code"], lab


def test_each_arduino_lab_wired_as_built_passes_its_checks_on_the_arduinos_adc():
    """The reference build of every lab: no problems, and every check would pass; the pot reads up to 1023."""
    for lab in sim.ARDUINO_CIRCUITS:
        assert sim.analyse(lab, sim.reference_wires(lab, course="arduino"), course="arduino")["ok"], lab
        run = sim.simulate(lab, course="arduino")
        assert run["ran"] and all(c["would_pass"] for c in run["checks"]), (lab, run["said"])
    pot = sim.simulate("pot", course="arduino")["serial"]
    assert max(int(v) for v in re.findall(r"MIA ADC (\d+)", pot)) <= 1023


def test_the_arduinos_own_faults_vin_on_a_pin_swapped_sonar_and_a_button_either_way():
    """A0 on VIN: a stop naming up to 12 V and the Mega's 5 V limit; TRIG and ECHO swapped: both named; a button's legs
    either way round: fine; the ESP32's rules unchanged in the same process."""
    stop = sim.simulate("pot", [("A0", "VIN")], course="arduino")
    assert not stop["ran"] and "up to 12 V" in stop["said"] and "the Mega's 5 V limit" in stop["said"]
    swapped = sim.analyse("distance", [("sonar1.vcc", "5V"), ("sonar1.gnd", "GND"), ("sonar1.trig", "D8"),
                                       ("sonar1.echo", "D7")], course="arduino")
    assert [p["text"] for p in swapped["problems"]] == ["The HC-SR04's TRIG is on D8, but the sketch uses D7.",
                                                        "The HC-SR04's ECHO is on D7, but the sketch uses D8."]
    assert sim.analyse("button", [("button1.b", "D2"), ("button1.a", "GND 2")], course="arduino")["ok"]
    assert "over the ESP32's 3.3 V limit" in sim.simulate("pot", [("GPIO 34", "VIN")])["said"]


def test_a_project_is_built_for_the_board_he_names(tmp_path):
    """The Nano's project: atmelavr and nanoatmega328 at 9600; the new bootloader's nanoatmega328new; the Mega's
    megaatmega2560; the dht lab's libraries."""
    nano = bench.project("blink", tmp_path, "arduino", "nano")
    assert "board = nanoatmega328\n" in (nano / "platformio.ini").read_text() and "monitor_speed = 9600" in (
        nano / "platformio.ini").read_text()
    assert "nanoatmega328new" in (bench.project("blink", tmp_path, "arduino", "nano_new") / "platformio.ini").read_text()
    mega = (bench.project("dht", tmp_path, "arduino") / "platformio.ini").read_text()
    assert "megaatmega2560" in mega and "adafruit/DHT sensor library" in mega
    with pytest.raises(ValueError):
        bench.project("relay", tmp_path, "arduino")


def test_the_course_and_board_are_read_from_his_words(tmp_path):
    """"Flash the blink lab to my nano": the Arduino course on the Nano; "the servo lab": Arduino (only it has one);
    "the relay lab": ESP32; nothing said: the course he's started."""
    book = paths.PathBook(None, data_dir=tmp_path)
    context = SimpleNamespace(paths=book)
    assert bench.course_in(context, "flash the blink lab to my nano") == "arduino"
    assert boards.named_in("flash the blink lab to my nano", "arduino") == "nano"
    assert bench.course_in(context, "check the servo lab") == "arduino"
    assert bench.course_in(context, "flash the relay lab") == "esp32"
    book.start(arduino_path.PROGRAM)
    assert bench.course_in(context, "check my lab") == "arduino"


def test_the_flash_card_names_the_board_and_its_port(monkeypatch):
    """One Arduino on CH340: the card says the Nano and the port; an Arduino-only lab on the ESP32 course is refused.
    It also says the CH340 is a chip ESP32 boards use too."""
    from core import greenhouse_provision as gp
    from core.actions import ActionError

    monkeypatch.setattr(gp, "serial_ports", lambda: [{"device": "COM9", "description": "USB-SERIAL CH340",
                                                      "vid": 0x1A86, "pid": 0x7523}])
    said = bench.ACTIONS["esplab.flash"].describe(None, {"lesson": "servo", "course": "arduino", "board": "nano"})
    assert "Arduino Nano" in said and "on COM9 (USB-SERIAL CH340" in said and "both ESP32 and Arduino" in said
    with pytest.raises(ActionError):
        bench.ACTIONS["esplab.flash"].describe(None, {"lesson": "servo"})


def test_the_next_lesson_on_a_board_course_is_answered_in_code(tmp_path):
    """"What's my next Arduino lesson?" names the next check and its lesson, and how to build it along; the ESP32's
    not started says so; a question about another course isn't this."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(arduino_path.PROGRAM)
    context = SimpleNamespace(paths=book)
    said = bench.next_lab_reply(context, "What's my next Arduino lesson?")
    assert said.startswith("Build With Arduino, stage 1 (First light): next is") and "the blink lab" in said
    assert bench.next_lab_reply(context, "what's my next esp32 lab?").startswith("You haven't started Build With ESP32")
    assert bench.next_lab_reply(context, "what's my next guitar lesson?") is None


def test_building_along_on_the_arduino_course_by_voice(tmp_path):
    """"Walk me through building the arduino distance lab": the HC-SR04's four wires, step by step, kept on the
    Arduino path; "next step" follows it."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(arduino_path.PROGRAM)
    context = SimpleNamespace(paths=book)
    first = sim._build_tool(context, {"question": "walk me through building the arduino distance lab"})
    assert first.startswith("Building the distance lab: you'll need the HC-SR04 and 4 jumper wires.")
    assert sim._build_tool(context, {"question": "next step"}).startswith("Step 2 of 4")
    assert book.build_at("arduino")["lesson"] == "distance"
