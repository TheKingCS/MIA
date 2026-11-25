"""
tests.test_bench_designs
==========================

"Build me a ..." on My Bench (core/bench_designs.py): every design passes the bench's own check on the ESP32, the
Mega and the Nano; a design lists only the parts its wiring for that board uses (the Arduino's tank gauge has no
divider), with what his Component DB has; its sketch is filled in for the board; his words find it, and a goal with
no design is said plainly; "build me a shed" isn't a circuit.
And an ESP32 design reporting to MIA, its secrets his to type.
"""

from types import SimpleNamespace

from core import bench_designs as bd


def _context(*parts):
    """A context whose Component DB has these (name, quantity) parts."""
    items = [SimpleNamespace(name=n, category="", quantity=q) for n, q in parts]
    return SimpleNamespace(components=SimpleNamespace(all_components=lambda: items))


def test_every_design_passes_the_benchs_own_check_on_every_board():
    """No design has a problem on the ESP32, the Mega or the Nano, and its sketch has no unfilled pins."""
    for design_id in bd.DESIGNS:
        for board in ("esp32dev", "mega", "nano"):
            got = bd.design(_context(), design_id, board)
            assert got["check"]["ok"] and not got["check"]["problems"], (design_id, board, got["check"])
            assert "{" not in got["sketch"].split("void setup")[0] or "DHT dht(" in got["sketch"], design_id


def test_a_design_lists_only_its_boards_parts_with_what_he_has():
    """The tank gauge on the ESP32 needs 2 resistors (the divider), on the Nano none; his 2 HC-SR04s are said."""
    esp = bd.design(_context(("HC-SR04 sensor", 2)), "tank_level", "esp32dev")
    assert esp["have"] == ["HC-SR04 ultrasonic sensor (2 on hand)"] and esp["need"] == ["2 x resistor"]
    nano = bd.design(_context(), "tank_level", "nano")
    assert [p["spec"] for p in nano["parts"]] == ["hcsr04"] and "const int TRIG = 7;" in nano["sketch"]
    assert "Serial.begin(9600)" in nano["sketch"] and "Serial.begin(115200)" in esp["sketch"]


def test_his_words_find_a_design_and_a_goal_with_none_is_said():
    """"A water level gauge for my nano": the tank gauge on the Nano; "a robot": the list of what there is; "build me
    a shed" matches no design trigger."""
    said = bd._design_tool(_context(), {"goal": "a water level gauge for my nano"})
    assert said.startswith("A water-tank level gauge on your Arduino Nano") and "My Bench" in said
    assert bd._design_tool(_context(), {"goal": "a robot"}).startswith("I don't have a design for that yet.")
    assert bd.find("build me a shed") is None
    triggers = []
    bd.register_design_tools(SimpleNamespace(register=lambda a: triggers.extend(a.trigger_phrases)))
    assert not any(t in " build me a shed " for t in triggers)
    assert any(t in " build me a motion light " for t in triggers)


def test_a_design_asked_for_is_answered_in_code_and_a_shed_is_left_to_the_planner():
    """"Build me a temperature alarm for the greenhouse": the design, in code (the model had set an alarm); "build me
    a shed" and "what's the water level in the tank?" (no build verb): None."""
    said = bd.reply(_context(), None, "Build me a temperature alarm for the greenhouse")
    assert said.startswith("A greenhouse temperature alarm on your ESP32")
    assert bd.reply(_context(), None, "build me a shed") is None
    assert bd.reply(_context(), None, "what's the water level in the tank?") is None


def test_an_esp32_design_can_report_to_mia_and_its_secrets_are_his_to_type():
    """The tank gauge reporting: Wi-Fi joined in setup, its percent full sent with the sensor's key at most once a
    minute, the C string's quotes escaped, secrets.h only placeholders; on a Nano: not offered; by voice, "that reports
    to MIA" asks for it."""
    got = bd.design(_context(), "tank_level", "esp32dev", report=True)
    sketch = got["sketch"]
    assert got["reports"] and "WiFi.begin(WIFI_NAME, WIFI_PASSWORD);" in sketch and "reportToMia(full);" in sketch
    assert 'http.POST(String("{\\"value\\": ")' in sketch and "X-Sensor-Key" in sketch and "60000" in sketch
    assert "type-yours-here" in got["secrets"] and "8765/api/sensors/reading" in got["secrets"]
    assert not bd.design(_context(), "tank_level", "nano", report=True)["reports"]
    assert not bd.design(_context(), "motion_light", "esp32dev", report=True)["reports"]
    assert "It reports to MIA" in bd.reply(_context(), None, "build me a tank level gauge that reports to mia")
