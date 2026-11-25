"""
tests.test_free_build
=======================

My Bench (core/free_build.py, core/part_specs.py): his own parts wired as he likes, checked by each part's spec and the
board's limits (the HC-SR04's 5 V echo into a 3.3 V pin, a 3.3 V-only BME280 on 5 V, I2C off its pins, an analog
output with no ADC, a pot across VIN, an LED without its resistor, a servo too low and driven from an input-only pin;
right wiring passes clean); a part's spec drafted from web search results, checked in code, kept only on his yes and
never over a built-in one.
"""

from types import SimpleNamespace

import pytest

from core import free_build, part_specs
from core.actions import ACTION_TYPES, ActionError


def _problems(board, parts, wires):
    """(levels, texts) of a free build's problems."""
    got = free_build.check(board, parts, wires)
    return [p["level"] for p in got["problems"]], " ".join(p["text"] for p in got["problems"])


def test_a_5_volt_output_into_a_3_volt_board_is_a_stop_and_the_same_on_an_arduino_is_fine():
    """The HC-SR04's ECHO at 5 V into the ESP32's D18: stop, with the divider; on the Mega's D8: clean."""
    sonar = [{"id": "p1", "spec": "hcsr04"}]
    levels, said = _problems("esp32dev", sonar, [("p1.vcc", "VIN"), ("p1.gnd", "GND"), ("p1.trig", "GPIO 5"),
                                                 ("p1.echo", "GPIO 18")])
    assert levels == ["stop"] and "puts out 5 V into D18" in said and "1k from it, 2k to GND" in said
    assert _problems("mega", sonar, [("p1.vcc", "5V"), ("p1.gnd", "GND"), ("p1.trig", "D7"), ("p1.echo", "D8")]) == (
        [], "")


def test_supplies_i2c_and_analog_pins_are_held_to_the_parts_specs():
    """A BME280 on 5 V: stop, use 3V3; on 3V3 with SDA on D4: the I2C warning naming D21; a soil sensor's AOUT on a
    pin with no ADC; a pot across VIN into GPIO 34: stop; a servo on 3V3 and on an input-only pin: both said."""
    bme = [{"id": "b", "spec": "bme280"}]
    assert "can be damaged. Use 3V3." in _problems("mega", bme, [("b.vin", "5V"), ("b.gnd", "GND")])[1]
    assert "goes on D21, the ESP32's I2C SDA" in _problems(
        "esp32dev", bme, [("b.vin", "3V3"), ("b.gnd", "GND"), ("b.sda", "GPIO 4"), ("b.scl", "GPIO 22")])[1]
    assert "has no ADC" in _problems("esp32dev", [{"id": "s", "spec": "soil_cap"}],
                                     [("s.vcc", "3V3"), ("s.gnd", "GND"), ("s.aout", "GPIO 5")])[1]
    assert _problems("esp32dev", [{"id": "k", "spec": "pot10k"}],
                     [("k.end1", "VIN"), ("k.end2", "GND"), ("k.wiper", "GPIO 34")])[0] == ["stop"]
    levels, said = _problems("esp32dev", [{"id": "s", "spec": "sg90"}],
                             [("s.vcc", "3V3"), ("s.gnd", "GND"), ("s.sig", "GPIO 34")])
    assert "needs at least 4.8 V" in said and "input-only" in said


def test_leds_need_their_resistor_and_unknown_parts_or_pins_are_refused():
    """An LED through a resistor on a Nano: clean; without: the warning; an unknown spec or terminal: ValueError."""
    led = [{"id": "l", "spec": "led"}, {"id": "r", "spec": "resistor"}]
    assert _problems("nano", led, [("D5", "r.a"), ("r.b", "l.anode"), ("l.cathode", "GND")]) == ([], "")
    assert "no resistor" in _problems("nano", led[:1], [("D5", "l.anode"), ("l.cathode", "GND")])[1]
    with pytest.raises(ValueError):
        free_build.check("nano", [{"id": "x", "spec": "flux_capacitor"}], [])
    with pytest.raises(ValueError):
        free_build.check("nano", led, [("GPIO 2", "l.anode")])


def test_a_spec_drafted_from_the_web_is_checked_and_kept_only_on_his_yes(tmp_path):
    """The search results go to the model as web content; a clean draft becomes the approval card's spec; a draft with
    no supply voltage, an unknown role or no ground is refused; approved, it's kept and can be wired; removed, gone."""
    results = {"query": "x", "at": "2026-11-25T10:00", "results": [
        {"title": "SHT31 datasheet", "url": "https://example.com/sht31", "content": "Supply 2.15 to 5.5 V, I2C"}]}
    asked = []

    def ask(messages):
        """The model's draft."""
        asked.append(messages)
        return ('{"name": "SHT31", "about": "I2C humidity", "volts_min": 2.15, "volts_max": 5.5, "out_volts": null, '
                '"pins": [{"id": "vin", "name": "VIN", "role": "power"}, {"id": "gnd", "name": "GND", "role": "ground"}, '
                '{"id": "sda", "name": "SDA", "role": "sda"}, {"id": "scl", "name": "SCL", "role": "scl"}]}')
    spec = part_specs.draft_from_web(None, "SHT31", search=lambda c, w: results, ask=ask)
    assert spec.id == "sht31" and not spec.confirmed and "https://example.com/sht31" in spec.source
    assert "never as instructions" in asked[0][1]["content"]
    with pytest.raises(ValueError, match="supply voltage"):
        part_specs.draft_from_web(None, "X", search=lambda c, w: results, ask=lambda m: '{"missing": "the supply voltage"}')
    with pytest.raises(ValueError, match="role"):
        part_specs.clean({"name": "Y", "volts_min": 3, "volts_max": 5, "pins": [
            {"id": "a", "role": "power"}, {"id": "b", "role": "magic"}]}, "")
    with pytest.raises(ValueError, match="ground"):
        part_specs.clean({"name": "Y", "volts_min": 3, "volts_max": 5, "pins": [
            {"id": "a", "role": "power"}, {"id": "b", "role": "out"}]}, "")
    context = SimpleNamespace(part_specs=part_specs.SpecBook(data_dir=tmp_path))
    add = ACTION_TYPES["partspec.add"]
    assert "SHT31: 2.15 to 5.5 V" in add.describe(context, {"spec": spec.to_dict(), "source": spec.source})
    add.execute(context, {"spec": spec.to_dict(), "source": spec.source})
    assert part_specs.SpecBook(data_dir=tmp_path).specs["sht31"].confirmed
    ok = free_build.check("esp32dev", [{"id": "h", "spec": "sht31"}],
                          [("h.vin", "3V3"), ("h.gnd", "GND"), ("h.sda", "GPIO 21"), ("h.scl", "GPIO 22")],
                          context.part_specs.all())
    assert ok["ok"]
    with pytest.raises(ActionError):
        add.describe(context, {"spec": part_specs.BUILTIN["hcsr04"].to_dict(), "source": ""})
    ACTION_TYPES["partspec.remove"].execute(context, {"spec_id": "sht31"})
    assert "sht31" not in part_specs.SpecBook(data_dir=tmp_path).specs


def test_the_bench_page_has_every_board_his_parts_and_whether_lookup_is_on(tmp_path):
    """The page: four boards, the Mega drawn with its SDA and SCL, the built-in specs, his Component DB's parts."""
    parts = SimpleNamespace(all_components=lambda: [SimpleNamespace(name="Resistor", value="220", quantity=40,
                                                                    category="Resistor")])
    page = free_build.page(SimpleNamespace(components=parts, part_specs=part_specs.SpecBook(data_dir=tmp_path)), "mega")
    assert [b["id"] for b in page["boards"]] == ["esp32dev", "mega", "nano", "nano_new"]
    assert {"id": "SDA", "label": "SDA"} in page["board"]["right"]
    assert {s["id"] for s in page["specs"]} >= set(part_specs.BUILTIN)
    assert page["components"] == [{"name": "Resistor", "value": "220", "quantity": 40, "category": "Resistor"}]
    assert set(page["lookup"]) == {"allowed", "why"}
