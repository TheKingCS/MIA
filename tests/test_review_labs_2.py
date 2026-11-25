"""
tests.test_review_labs_2
==========================

The second review of the labs (2026-11-25), each finding as its failing input: the Mega's I2C on its own header,
never A4/A5; power backwards a stop in the free build and the course simulator; a part's input held to its range and an
output tied to a rail warned; a lab named as one deciding the course before a stray word; a chip both kinds of board
use said on the card; a malformed spec draft a ValueError, two GND pins numbered.
"""

from types import SimpleNamespace

import pytest

from core import esp32_lab, esp32_sim, free_build, part_specs, paths


def _said(board, parts, wires):
    """(levels, texts) of a free build's problems."""
    got = free_build.check(board, parts, wires)
    return [p["level"] for p in got["problems"]], " ".join(p["text"] for p in got["problems"])


def test_the_megas_i2c_is_its_own_header_and_a_nano_has_no_sda_pin():
    """A BME280 on the Mega's A4/A5: the I2C warning naming SDA; on its SDA/SCL: clean; SDA on VIN: a stop; a wire to
    "SDA" on a Nano: refused (it has none)."""
    bme = [{"id": "b", "spec": "bme280"}]
    base = [("b.vin", "3V3"), ("b.gnd", "GND")]
    assert "goes on SDA" in _said("mega", bme, base + [("b.sda", "A4"), ("b.scl", "A5")])[1]
    assert _said("mega", bme, base + [("b.sda", "SDA"), ("b.scl", "SCL")]) == ([], "")
    assert "stop" in _said("mega", [], [("SDA", "VIN")])[0]
    with pytest.raises(ValueError):
        free_build.check("nano", bme, base + [("b.sda", "SDA")])


def test_power_backwards_is_a_stop_in_the_free_build_and_the_course_simulator():
    """An HC-SR04 with VCC on GND and GND on 5V: stops; the Arduino's distance lab and the ESP32's dht lab reversed:
    stopped, not run."""
    levels, said = _said("mega", [{"id": "p", "spec": "hcsr04"}], [("p.vcc", "GND"), ("p.gnd", "5V")])
    assert levels.count("stop") == 2 and "power backwards" in said
    run = esp32_sim.simulate("distance", [("sonar1.vcc", "GND"), ("sonar1.gnd", "5V"), ("sonar1.trig", "D7"),
                                          ("sonar1.echo", "D8")], course="arduino")
    assert not run["ran"] and "power backwards" in run["said"]
    esp = esp32_sim.simulate("dht", [("dht1.vcc", "GND"), ("dht1.gnd", "3V3"), ("dht1.data", "GPIO 4")])
    assert not esp["ran"] and "power is backwards" in esp["said"]


def test_a_parts_input_is_held_to_its_range_and_an_output_on_a_rail_is_warned():
    """A buzzer's + on a Nano's VIN: a stop (up to 12 V into a 5.5 V part); an HC-SR04's ECHO tied to 5V: warned."""
    assert _said("nano", [{"id": "b", "spec": "buzzer"}], [("b.plus", "VIN"), ("b.minus", "GND")])[0] == ["stop"]
    levels, said = _said("mega", [{"id": "p", "spec": "hcsr04"}],
                         [("p.vcc", "5V"), ("p.gnd", "GND"), ("p.echo", "5V")])
    assert "tied straight to 5V" in said


def test_a_lab_named_as_one_decides_the_course_before_a_stray_word(tmp_path):
    """"Flash the blink lab so the light blinks", with the ESP32 course started: the ESP32's; "the servo lab": the
    Arduino's."""
    book = paths.PathBook(None, data_dir=tmp_path)
    from core.esp32_path import PROGRAM

    book.start(PROGRAM)
    context = SimpleNamespace(paths=book)
    assert esp32_lab.course_in(context, "flash the blink lab so the light blinks") == "esp32"
    assert esp32_lab.course_in(context, "read the pot lab, the servo next to it is unplugged") == "esp32"
    assert esp32_lab.course_in(context, "check the servo lab") == "arduino"


def test_a_chip_both_kinds_of_board_use_is_said_on_the_card(monkeypatch):
    """One CH340 port, the Arduino course: the description says ESP32 boards use it too."""
    from core import greenhouse_provision as gp

    monkeypatch.setattr(gp, "serial_ports", lambda: [{"device": "COM5", "description": "CH340", "vid": 0x1A86,
                                                      "pid": 0x7523}])
    assert "both ESP32 and Arduino boards use" in esp32_lab.board(pio=[], course="arduino")["description"]


def test_a_malformed_draft_is_a_valueerror_and_two_gnd_pins_are_numbered():
    """Pins as strings, or a spec that isn't a dict: ValueError; a module with two GND pins: gnd and gnd_2."""
    with pytest.raises(ValueError):
        part_specs.clean({"name": "X", "volts_min": 3, "volts_max": 5, "pins": ["vcc", "gnd"]}, "")
    with pytest.raises(ValueError):
        part_specs.clean("not a spec", "")
    spec = part_specs.clean({"name": "Relay", "volts_min": 4.5, "volts_max": 5.5, "pins": [
        {"id": "vcc", "name": "VCC", "role": "power"}, {"id": "gnd", "name": "GND", "role": "ground"},
        {"id": "gnd", "name": "GND", "role": "ground"}, {"id": "in", "name": "IN", "role": "in"}]}, "")
    assert [p.id for p in spec.pins] == ["vcc", "gnd", "gnd_2", "in"]
