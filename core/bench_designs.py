"""
core.bench_designs
====================

"Build me a ..." on My Bench (brainstorm round 13, idea 2; Zac, 2026-11-25): he names a goal, MIA puts a design for
it on his board: the parts (checked against his Component DB: what he has and what he'd need), the wiring for his
board, and a sketch; the bench's checker (core/free_build.py) judges the wiring as it does his own. The designs are
written here, each wired and checked for the ESP32 and for the Arduino (Mega and Nano), never improvised by the model:
a circuit that could hurt a part or a board isn't something to guess. Flashing a design stays his to do.

- **The designs** (`DESIGNS`): a motion light (HC-SR501 and an LED), a greenhouse temperature alarm (DHT22 and an
  active buzzer), a dry-soil alert (capacitive sensor and an LED, calibrated by him) and a water-tank level gauge
  (HC-SR04; on the ESP32 its 5 V echo through a 1k/2k divider). Each has its words, its parts, its wiring and sketch
  per board family, and how to use it.
- **Choosing** (`find`): the design his words mean, or None (then the list of what MIA can design).
- **For his board** (`design`): {id, name, about, parts [{id, spec}], wires, sketch, steps, have, need, check} for a
  board (core/boards.py), with what his Component DB has of each part and the bench's check of the wiring.
- **By voice** (`reply`, in code before the plans; the tool `design_build`): "build me a motion light": the parts, what
  he has, the wiring as steps, and that it's on My Bench to see.
"""

from __future__ import annotations

import re
from typing import Optional

# Each design: its words, parts (id -> spec), and per board family the wires and the sketch.
DESIGNS: dict = {
    "motion_light": {
        "name": "A motion light", "words": ("motion light", "motion sensor light", "pir light", "motion detector",
                                            "light when someone walks"),
        "about": "An LED that lights for 10 seconds when the HC-SR501 sees something warm move.",
        "parts": (("pir", "hcsr501"), ("led", "led"), ("r1", "resistor")),
        "wires": {
            "esp32": (("pir.vcc", "VIN"), ("pir.gnd", "GND"), ("pir.out", "GPIO 27"), ("GPIO 2", "r1.a"),
                      ("r1.b", "led.anode"), ("led.cathode", "GND 2")),
            "arduino": (("pir.vcc", "5V"), ("pir.gnd", "GND"), ("pir.out", "D2"), ("D13", "r1.a"),
                        ("r1.b", "led.anode"), ("led.cathode", "GND 2")),
        },
        "pins": {"esp32": ("27", "2", "115200"), "arduino": ("2", "13", "9600")},
        "code": """#include <Arduino.h>

const int PIR = {0};    // the HC-SR501's OUT: HIGH while it sees motion (3.3 V, safe on any board)
const int LED = {1};
unsigned long lastSeen = 0;
int seen = 0;

void setup() {{
  Serial.begin({2});
  pinMode(PIR, INPUT);
  pinMode(LED, OUTPUT);
}}

void loop() {{
  if (digitalRead(PIR) == HIGH) {{
    if (millis() - lastSeen > 2000) {{   // a new movement, not the same one
      seen++;
      Serial.print("MIA MOTION ");
      Serial.println(seen);
    }}
    lastSeen = millis();
  }}
  digitalWrite(LED, millis() - lastSeen < 10000 ? HIGH : LOW);   // on for 10 s after the last movement
}}
""",
        "use": "The HC-SR501 takes about a minute to settle after power-up; its two knobs set how far it sees and how "
               "long its own output stays high.",
    },
    "temp_alarm": {
        "name": "A greenhouse temperature alarm", "words": ("temperature alarm", "temp alarm", "frost alarm",
                                                            "too hot alarm", "heat alarm", "greenhouse alarm"),
        "about": "A DHT22 reads the air every 2 seconds; an active buzzer beeps when it's over 35 °C or under 2 °C.",
        "parts": (("dht", "dht22"), ("buzz", "buzzer")),
        "wires": {
            "esp32": (("dht.vcc", "3V3"), ("dht.gnd", "GND"), ("dht.data", "GPIO 4"), ("buzz.plus", "GPIO 25"),
                      ("buzz.minus", "GND 2")),
            "arduino": (("dht.vcc", "5V"), ("dht.gnd", "GND"), ("dht.data", "D3"), ("buzz.plus", "D4"),
                        ("buzz.minus", "GND 2")),
        },
        "pins": {"esp32": ("4", "25", "115200"), "arduino": ("3", "4", "9600")},
        "libs": ("adafruit/DHT sensor library", "adafruit/Adafruit Unified Sensor"),
        "code": """#include <Arduino.h>
#include <DHT.h>

DHT dht({0}, DHT22);
const int BUZZER = {1};          // an active buzzer: it beeps on its own when its pin is HIGH
const float TOO_HOT = 35.0;      // degrees C: change these to your own limits
const float TOO_COLD = 2.0;

void setup() {{
  Serial.begin({2});
  pinMode(BUZZER, OUTPUT);
  dht.begin();
}}

void loop() {{
  delay(2000);   // the DHT22 reads at most every 2 seconds
  float c = dht.readTemperature();
  if (isnan(c)) {{
    Serial.println("MIA SENSOR_ERROR");
    return;
  }}
  Serial.print("MIA TEMP ");
  Serial.println(c, 1);
  bool alarm = c > TOO_HOT || c < TOO_COLD;
  digitalWrite(BUZZER, alarm ? HIGH : LOW);
}}
""",
        "use": "Use an active buzzer (it beeps with plain power; a passive one only clicks). Set TOO_HOT and TOO_COLD "
               "to your own limits.",
    },
    "soil_alert": {
        "name": "A dry-soil alert", "words": ("soil alert", "dry soil", "water the plants", "plant alarm",
                                             "soil moisture alarm", "when the soil is dry", "watering reminder"),
        "about": "A capacitive soil sensor read every second; an LED lights when the soil is drier than the level you "
                 "set.",
        "parts": (("soil", "soil_cap"), ("led", "led"), ("r1", "resistor")),
        "wires": {
            "esp32": (("soil.vcc", "3V3"), ("soil.gnd", "GND"), ("soil.aout", "GPIO 35"), ("GPIO 2", "r1.a"),
                      ("r1.b", "led.anode"), ("led.cathode", "GND 2")),
            "arduino": (("soil.vcc", "5V"), ("soil.gnd", "GND"), ("soil.aout", "A0"), ("D13", "r1.a"),
                        ("r1.b", "led.anode"), ("led.cathode", "GND 2")),
        },
        "pins": {"esp32": ("35", "2", "115200"), "arduino": ("A0", "13", "9600")},
        "code": """#include <Arduino.h>

const int SOIL = {0};
const int LED = {1};
int DRY = 0;   // set this: read it in air (dry) and in water (wet) on the serial monitor, then put DRY about a third
               // of the way from the dry reading toward the wet one. Higher readings are drier on these sensors.

void setup() {{
  Serial.begin({2});
  pinMode(LED, OUTPUT);
}}

void loop() {{
  int raw = analogRead(SOIL);
  Serial.print("MIA SOIL ");
  Serial.println(raw);
  digitalWrite(LED, DRY > 0 && raw > DRY ? HIGH : LOW);
  delay(1000);
}}
""",
        "use": "Calibrate first: note the reading with the sensor in air, then in a cup of water, and set DRY between "
               "them. Push it in only up to its line: the top's electronics aren't waterproof.",
    },
    "tank_level": {
        "name": "A water-tank level gauge", "words": ("tank level", "water level", "rain barrel", "cistern level",
                                                      "how full the tank", "tank gauge"),
        "about": "An HC-SR04 above the water measures down to it; the sketch says how full the tank is.",
        "parts": (("sonar", "hcsr04"), ("r1", "resistor"), ("r2", "resistor")),
        "wires": {
            # the ESP32: ECHO's 5 V through a divider (r1 1k from ECHO to the pin, r2 2k from the pin to GND)
            "esp32": (("sonar.vcc", "VIN"), ("sonar.gnd", "GND"), ("sonar.trig", "GPIO 5"), ("sonar.echo", "r1.a"),
                      ("r1.b", "GPIO 18"), ("GPIO 18", "r2.a"), ("r2.b", "GND 2")),
            "arduino": (("sonar.vcc", "5V"), ("sonar.gnd", "GND"), ("sonar.trig", "D7"), ("sonar.echo", "D8")),
        },
        "pins": {"esp32": ("5", "18", "115200"), "arduino": ("7", "8", "9600")},
        "code": """#include <Arduino.h>

const int TRIG = {0};
const int ECHO = {1};
const int EMPTY_CM = 100;   // set these: the distance from the sensor to the water when the tank is empty
const int FULL_CM = 20;     // and when it's full (keep the sensor at least 20 cm above the highest water)

void setup() {{
  Serial.begin({2});
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
}}

void loop() {{
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long echo = pulseIn(ECHO, HIGH, 30000);
  if (echo == 0) {{
    Serial.println("MIA DIST_NONE");
  }} else {{
    long cm = echo / 58;
    int full = constrain(map(cm, EMPTY_CM, FULL_CM, 0, 100), 0, 100);
    Serial.print("MIA DIST ");
    Serial.println(cm);
    Serial.print("MIA FULL ");
    Serial.println(full);
  }}
  delay(1000);
}}
""",
        "use": "On the ESP32, r1 is 1k and r2 is 2k: they bring the ECHO's 5 V down to about 3.3 V. Set EMPTY_CM and "
               "FULL_CM by measuring your tank; mount the sensor level, looking straight down.",
    },
}


def find(words: str) -> Optional[str]:
    """Pure logic. The design his words mean (by its own words, or its name), or None."""
    said = " ".join(str(words or "").lower().split())
    for design_id, d in DESIGNS.items():
        if any(w in said for w in d["words"]) or d["name"].lower().removeprefix("a ") in said:
            return design_id
    return None


def _have(context, spec) -> Optional[int]:
    """How many of a part his Component DB has, by its model or name (None when nothing there matches)."""
    store = getattr(context, "components", None)
    if store is None:
        return None
    model = re.sub(r"[^a-z0-9]+", "", spec.name.lower().split(" ")[0])
    found = [c for c in store.all_components()
             if model and model in re.sub(r"[^a-z0-9]+", "", f"{c.name} {c.category}".lower())]
    return sum(int(c.quantity or 0) for c in found) if found else None


def design(context, design_id: str, board_id: str = "esp32dev") -> dict:
    """A design for his board (see the module's opening): only the parts its wiring for that board uses (the
    Arduino's tank gauge needs no divider), a part used twice counted once with its number. KeyError for one there
    isn't; ValueError for a board."""
    from core import boards, free_build, part_specs

    d = DESIGNS[design_id]
    board = boards.BOARDS.get(board_id)
    if board is None:
        raise ValueError("Which board? The ESP32, the Mega or a Nano.")
    specs = part_specs.BUILTIN
    wires = [list(w) for w in d["wires"][board.family]]
    used = {t.split(".", 1)[0] for w in wires for t in w if "." in t}
    parts = [{"id": pid, "spec": spec} for pid, spec in d["parts"] if pid in used]  # this board's wiring's parts
    code = d["code"].format(*d["pins"][board.family])
    have, need = [], []
    counts: dict = {}
    for part in parts:
        counts[part["spec"]] = counts.get(part["spec"], 0) + 1
    for spec_id, n in counts.items():
        on_hand = _have(context, specs[spec_id])
        name = (f"{n} x " if n > 1 else "") + specs[spec_id].name
        (have if on_hand else need).append(name + (f" ({on_hand} on hand)" if on_hand else ""))
    checked = free_build.check(board.id, parts, [tuple(w) for w in wires], specs)
    steps = [f"{_words(a, parts, board)} to {_words(b, parts, board)}" for a, b in wires]
    return {"id": design_id, "name": d["name"], "about": d["about"], "use": d["use"], "board": board.id,
            "parts": parts, "wires": wires, "sketch": code, "libs": list(d.get("libs", ())), "steps": steps,
            "have": have, "need": need, "check": checked}


def _words(terminal: str, parts: list, board) -> str:
    """A terminal in words: a board pin as printed, a part's pin by its part and name."""
    from core import part_specs

    if "." not in terminal:
        return board.label(terminal)
    pid, pin = terminal.split(".", 1)
    spec = part_specs.BUILTIN[next(p["spec"] for p in parts if p["id"] == pid)]
    return f"the {spec.name.split(' (')[0]}'s {spec.pin(pin).name}"


def _design_tool(context, arguments: dict) -> str:
    """Tool design_build: a design for his goal, said: what it does, what he has and needs, the wiring, and where to
    see it."""
    from core import boards
    from core.esp32_lab import course_in

    words = str(arguments.get("goal", "") or "") + " " + str(arguments.get("question", "") or "")
    found = find(words)
    if found is None:
        names = ", ".join(d["name"].lower() for d in DESIGNS.values())
        return f"I don't have a design for that yet. I can put these on your bench: {names}."
    board_id = boards.named_in(words, "arduino") or ("mega" if course_in(context, words) == "arduino" else "esp32dev")
    got = design(context, found, board_id)
    said = f"{got['name']} on your {boards.BOARDS[board_id].name}: {got['about']}"
    if got["have"]:
        said += f" You have: {', '.join(got['have'])}."
    if got["need"]:
        said += f" You'd need: {', '.join(got['need'])}."
    said += " Wiring: " + "; ".join(got["steps"]) + ". " + got["use"]
    return said + " It's on My Bench to see, check and copy the sketch from."


_BUILD = re.compile(r"\b(build|make|design|wire up|put together|help me build|how (?:do|would) i build)\b")


def reply(context, conversation, text: str) -> Optional[str]:
    """"Build me a motion light", in code, before the question plans (live check, 2026-11-25: the model routed "build me
    a temperature alarm" to add_alarm): a build verb and one of the designs' own goals; None otherwise ("build me a
    shed" is the planner's)."""
    said = " ".join(str(text or "").lower().split())
    if not _BUILD.search(said) or find(said) is None:
        return None
    return _design_tool(context, {"goal": said})


def register_design_tools(registry) -> None:
    """Registers design_build."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="design_build", domain="learning",
        description="Design an electronics build for a goal on his board, from MIA's designs: the parts (what he has), "
                    "the wiring and a sketch: \"build me a motion light\", \"design a tank level gauge for my nano\".",
        parameters={"type": "object", "properties": {"goal": {"type": "string", "description": "what he wants to "
                                                                                             "build"}},
                    "required": []},
        # "build me a" only with a design's own goal named: "build me a shed" is the construction planner's
        handler=_design_tool, trigger_phrases=("design me a", "design a circuit", "design a build",
                                              *[f"{verb} {w}" for verb in ("build me a", "build a", "make me a",
                                                                           "wire up a")
                                                for d in DESIGNS.values() for w in d["words"]]),
    ))
