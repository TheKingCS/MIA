"""
tests.test_esp32_sim
======================

The ESP32 lab simulator (core/esp32_sim.py): a circuit judged the way it would behave (an LED backwards, with no
resistor, or with the resistor on its other side; a short; 5 V on the pot; a sensor on the wrong pin; an input-only
pin asked to drive), the build along with MIA (steps ticked, a resistor's ends either way round; "next step" by voice
kept on his path), every lab's own circuit passing its checks in a run, and a run never passing anything on his path.
"""

from types import SimpleNamespace

import pytest

from core import esp32_sim as sim
from core import paths
from core.esp32_path import LABS, PROGRAM

GOOD_LED = [("GPIO 2", "r1.a"), ("r1.b", "led1.anode"), ("led1.cathode", "GND")]


def _levels(found) -> dict:
    """{level: [texts]} of an analysis's problems."""
    out: dict = {}
    for p in found["problems"]:
        out.setdefault(p["level"], []).append(p["text"])
    return out


def test_every_lab_has_a_circuit_and_its_own_wiring_passes_its_checks():
    """Each lab: a circuit; its own build has no problems; run as SHOW has it, every check would pass."""
    assert set(sim.CIRCUITS) == set(LABS)
    for lab in LABS:
        assert sim.analyse(lab, sim.reference_wires(lab))["ok"], lab
        run = sim.simulate(lab)
        assert run["ran"] and run["checks"] and all(c["would_pass"] for c in run["checks"]), (lab, run["said"])


def test_an_led_lit_backwards_without_a_resistor_or_with_it_on_the_ground_side():
    """Right: lit. Backwards: a warning, dark, while serial still counts. No resistor: overdriven. The resistor on the
    cathode's side, ends swapped and on the other GND pin: lit, no problems."""
    assert sim.analyse("blink", GOOD_LED)["state"]["led1"] == "lit"
    backwards = sim.analyse("blink", [("GPIO 2", "r1.a"), ("r1.b", "led1.cathode"), ("led1.anode", "GND")])
    assert backwards["state"]["led1"] == "backwards" and "backwards" in _levels(backwards)["warn"][0]
    run = sim.simulate("blink", [("GPIO 2", "r1.a"), ("r1.b", "led1.cathode"), ("led1.anode", "GND")])
    assert "MIA BLINK 5" in run["serial"] and all(o.get("led", 0) == 0 for o in run["outputs"])
    bare = sim.analyse("blink", [("GPIO 2", "led1.anode"), ("led1.cathode", "GND")])
    assert bare["state"]["led1"] == "overdriven" and "no resistor" in _levels(bare)["warn"][0]
    other_side = sim.analyse("fade", [("GPIO 2", "led1.anode"), ("led1.cathode", "r1.b"), ("r1.a", "GND 2")])
    assert other_side == {"ok": True, "problems": [], "state": {"reset": False, "short": False, "led1": "lit"}}
    wrong_pin = sim.analyse("blink", [("GPIO 4", "r1.a"), ("r1.b", "led1.anode"), ("led1.cathode", "GND")])
    assert "on D4, but the sketch drives D2" in _levels(wrong_pin)["warn"][0]


def test_a_short_or_five_volts_on_the_pot_stops_the_run():
    """3V3 to GND: stop, nothing runs. The pot's end on VIN: stop (the wiper could reach 5 V)."""
    shorted = sim.simulate("pot", [("3V3", "GND")])
    assert not shorted["ran"] and shorted["serial"] == "" and shorted["said"].startswith("Stop: 3V3 is wired straight")
    vin = sim.analyse("pot", [("pot1.end1", "VIN"), ("pot1.end2", "GND"), ("pot1.wiper", "GPIO 34")])
    assert "5 V on the pot" in _levels(vin)["stop"][0]
    held = sim.simulate("hello", [("EN", "GND 2")])
    assert not held["ran"] and "reset" in held["said"]


def test_sensors_and_the_relay_on_the_wrong_pin_or_unpowered():
    """DHT22 data on GPIO 5: a warning naming both pins, and the board says SENSOR_ERROR. The relay's IN on an
    input-only pin: it can't drive it. The soil sensor unpowered: no power. TX0 used: the serial warning."""
    dht = sim.simulate("dht", [("dht1.vcc", "3V3"), ("dht1.gnd", "GND"), ("dht1.data", "GPIO 5")])
    assert "on D5, but the sketch uses D4" in dht["said"] and "MIA SENSOR_ERROR" in dht["serial"]
    relay = sim.analyse("relay", [("relay1.vcc", "3V3"), ("relay1.gnd", "GND"), ("relay1.in", "GPIO 34")])
    assert "input-only" in _levels(relay)["warn"][0]
    soil = sim.analyse("soil", [("soil1.gnd", "GND"), ("soil1.aout", "GPIO 35")])
    assert "no power" in _levels(soil)["warn"][0] and soil["state"]["soil1"] is False
    serial = sim.analyse("relay", [("relay1.in", "GPIO 1")])
    assert any("TX0" in t for t in _levels(serial)["warn"])


def test_the_build_ticks_steps_with_a_resistors_ends_either_way_round():
    """The first wire on the resistor's other end still ticks step 1, and step 2 then wants the first end; unknown
    terminals are refused."""
    progress = sim.build_progress("blink", [("GPIO 2", "r1.b")])
    assert [s["done"] for s in progress["steps"]] == [True, False, False] and progress["next"] == 2
    assert sim.build_progress("blink", [("GPIO 2", "r1.b"), ("r1.a", "led1.anode"), ("led1.cathode", "GND 2")])["done"]
    with pytest.raises(ValueError):
        sim.build_progress("blink", [("GPIO 2", "pot1.wiper")])


def test_building_along_by_voice_follows_next_back_and_again_on_his_path(tmp_path):
    """"Walk me through building the pot lab": step 1 with the parts; "next step": 2; "go back": 1; "repeat that":
    1; past the end: the whole circuit, and it stays there; naming another lab starts it."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(PROGRAM, goal="a soil node")
    context = SimpleNamespace(paths=book)
    say = lambda q: sim._build_tool(context, {"question": q})  # noqa: E731
    assert say("walk me through building the pot lab").startswith("Building the pot lab: you'll need the 10k")
    assert say("done, next step").startswith("Step 2 of 3")
    assert say("go back").startswith("Step 1 of 3")
    assert say("repeat that step").startswith("Step 1 of 3")
    say("next step"), say("next step")
    assert say("next step").startswith("That's the whole pot circuit")
    assert book.build_at("esp32") == {"lesson": "pot", "step": 4, "date": book.build_at("esp32")["date"]}
    assert say("next step").startswith("That's the whole pot circuit")
    assert "Step 1 of 3: the DHT22 module's VCC (+) to 3V3" in say("help me wire the dht lab")


def test_building_along_is_taken_in_code_before_the_plans_only_right_after_a_step(tmp_path):
    """A build verb with a lab named starts it; "Got it, what's next?" right after a step moves it; after another
    reply, or with something else named ("what's my next step on the shed?"), it isn't the build's."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(PROGRAM)
    context = SimpleNamespace(paths=book)
    said = lambda *texts: SimpleNamespace(messages=[SimpleNamespace(role="assistant", content=t) for t in texts])  # noqa: E731
    first = sim.reply(context, said(), "How do I wire the relay lab?")
    assert first.startswith("Building the relay lab:")
    assert sim.reply(context, said(first), "Got it, what's next?").startswith("Step 2 of 3")
    assert sim.reply(context, said(first), "What's my next step on the shed?") is None
    assert sim.reply(context, said(first, "Your shed needs lumber."), "next step") is None
    assert sim.reply(context, said(), "Flash the relay lab") is None


def test_a_how_to_naming_a_lab_to_wire_is_the_worlds_not_a_question_about_mias_lab_app():
    """"How do I wire the relay lab?": only the learning tool's own phrase matched, the Data Logger only by the word
    "lab", so it's about the world (her tools), not a how-to about MIA's Lab (her help pages)."""
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_chat import about_mia
    from core.esp32_lab import register_esp32_lab_actions

    registry = AssistantActionRegistry()
    register_esp32_lab_actions(registry)
    registry.register_domain_keywords("lab", ("lab",))
    context = SimpleNamespace(assistant_actions=registry)
    assert about_mia("how do i wire the relay lab?", context) is False


def test_a_run_in_the_simulator_never_passes_a_check_on_his_path(tmp_path):
    """Every check would pass in the simulator, and his path still has no attempts."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(PROGRAM)
    assert "would pass" in sim._simulate_tool(SimpleNamespace(paths=book), {"question": "what will the blink lab print?"})
    assert book.path("esp32")["attempts"] == [] and not book.passed("esp32", "esp_blink")
