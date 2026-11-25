"""
core.esp32_path
=================

Build With ESP32, MIA's first interactive lab course (Zac, 2026-11-25: "an interactive environment made for learning
how to build with esp32's ... this could be used as a standard for other teaching areas"; the standard is
docs/future/INTERACTIVE_LABS_PLAN.md). A learning path (core/paths.py: stages, lessons, checks, practice, homework,
stats), whose labs are worked on a real board on his desk.

- **The course** (`STAGES`, registered as `PROGRAM`): seven stages, from the first blink to a sensor node that sleeps
  and, the capstone, a watchdog that goes safe on its own (the greenhouse's safety board in small:
  homestead/firmware/safety_mcu, the PC proposes and the board decides; an LED stands in for the pump, never a real one),
  each lab a lesson with its steps, why it matters and what to watch for.
- **Each lab** (`LABS`): the parts, the wiring (pin to pin), the libraries and the sketch (Arduino on the ESP32, for
  PlatformIO's `esp32dev` board), shown with the lesson (`_extra`) and built and flashed by core/esp32_lab.py.
- **The check** (`board_says`, the verifier): every sketch prints lines like `MIA BLINK 5` on its serial port; the
  check passes from what the board itself said, read from its serial output (core/esp32_lab.py reads it, or he
  pastes it): a marker seen, a value at least a mark (`min`), a spread between readings (`spread`, a pot turned end
  to end, soil dry then wet), or a value within a range (`range`, a temperature a real room could have).

Safety in the lessons, never left to the model: 3.3 V logic, the pins not to use, and low voltage only on a relay
(anything on mains is a qualified electrician's). Wi-Fi details are typed by him into the sketch's own secrets file,
never by MIA. Its XP goes to the Engineering skill.
"""

from __future__ import annotations

import re
from typing import Optional

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "engineering"
BOARD = "esp32dev"  # PlatformIO's ESP32 DevKit (ESP32-WROOM-32); most 30- and 38-pin dev boards
VERIFIER = "board_says"

# ------------------------------------------------------------------ each lab: parts, wiring, libraries, sketch

LABS: dict[str, dict] = {
    "blink": {
        "parts": ("ESP32 dev board", "USB cable (data, not charge-only)"),
        "wiring": (("onboard LED", "GPIO 2 (on most dev boards; else an LED and 220 ohm resistor from GPIO 2 to GND)"),),
        "libs": (),
        "code": """#include <Arduino.h>

const int LED = 2;   // the onboard LED on most ESP32 dev boards
int blinks = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
}

void loop() {
  digitalWrite(LED, HIGH);
  delay(500);
  digitalWrite(LED, LOW);
  delay(500);
  blinks++;
  Serial.printf("MIA BLINK %d\\n", blinks);   // MIA reads this to check the lab
}
""",
    },
    "hello": {
        "parts": ("ESP32 dev board", "USB cable"),
        "wiring": (),
        "libs": (),
        "code": """#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  delay(500);
}

void loop() {
  Serial.printf("MIA HELLO %lu\\n", millis() / 1000);   // hello, and the seconds since it started
  delay(2000);
}
""",
    },
    "button": {
        "parts": ("ESP32 dev board",),
        "wiring": (("the BOOT button", "GPIO 0 (already on the board: nothing to wire)"),),
        "libs": (),
        "code": """#include <Arduino.h>

const int BUTTON = 0;   // the BOOT button, pulled up: it reads LOW while pressed
int presses = 0;
bool last = HIGH;
unsigned long changed = 0;

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON, INPUT_PULLUP);
}

void loop() {
  bool now = digitalRead(BUTTON);
  if (now != last && millis() - changed > 50) {   // 50 ms of debounce
    changed = millis();
    if (now == LOW) {
      presses++;
      Serial.printf("MIA BUTTON %d\\n", presses);
    }
    last = now;
  }
}
""",
    },
    "pot": {
        "parts": ("ESP32 dev board", "10k potentiometer", "3 jumper wires"),
        "wiring": (("pot outer leg", "3V3"), ("pot other outer leg", "GND"), ("pot middle leg (wiper)", "GPIO 34")),
        "libs": (),
        "code": """#include <Arduino.h>

const int POT = 34;   // an input-only pin on ADC1, which keeps working when Wi-Fi is on

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);   // 0 to 4095
}

void loop() {
  Serial.printf("MIA ADC %d\\n", analogRead(POT));
  delay(250);
}
""",
    },
    "dht": {
        "parts": ("ESP32 dev board", "DHT22 (AM2302) sensor", "10k resistor (if your DHT22 isn't on a module)",
                  "3 jumper wires"),
        "wiring": (("DHT22 VCC (+)", "3V3"), ("DHT22 DATA", "GPIO 4 (and the 10k from DATA to 3V3 on a bare sensor)"),
                   ("DHT22 GND (-)", "GND")),
        "libs": ("adafruit/DHT sensor library", "adafruit/Adafruit Unified Sensor"),
        "code": """#include <Arduino.h>
#include <DHT.h>

DHT dht(4, DHT22);   // the data pin, and the sensor's type

void setup() {
  Serial.begin(115200);
  dht.begin();
}

void loop() {
  delay(2500);   // the DHT22 reads at most every 2 seconds
  float c = dht.readTemperature();
  float h = dht.readHumidity();
  if (isnan(c) || isnan(h)) {
    Serial.println("MIA SENSOR_ERROR");   // check the wiring and the pull-up
    return;
  }
  Serial.printf("MIA TEMP %.1f\\n", c);
  Serial.printf("MIA HUMIDITY %.1f\\n", h);
}
""",
    },
    "soil": {
        "parts": ("ESP32 dev board", "capacitive soil moisture sensor (v1.2 or v2.0)", "3 jumper wires",
                  "a cup of water and a pot of dry soil"),
        "wiring": (("sensor VCC", "3V3"), ("sensor GND", "GND"), ("sensor AOUT", "GPIO 35")),
        "libs": (),
        "code": """#include <Arduino.h>

const int SOIL = 35;   // ADC1, input only

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
}

void loop() {
  int raw = analogRead(SOIL);   // higher is drier on most capacitive sensors
  Serial.printf("MIA SOIL %d\\n", raw);
  delay(1000);
}
""",
    },
    "fade": {
        "parts": ("ESP32 dev board", "LED and 220 ohm resistor (or the onboard LED)"),
        "wiring": (("LED long leg (through the 220 ohm resistor)", "GPIO 2"), ("LED short leg", "GND")),
        "libs": (),
        "code": """#include <Arduino.h>

const int LED = 2;
int fades = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
}

void loop() {
  for (int duty = 0; duty <= 255; duty += 5) { analogWrite(LED, duty); delay(15); }   // PWM: brighter
  for (int duty = 255; duty >= 0; duty -= 5) { analogWrite(LED, duty); delay(15); }   // and dimmer
  fades++;
  Serial.printf("MIA FADE %d\\n", fades);
}
""",
    },
    "relay": {
        "parts": ("ESP32 dev board", "1-channel 3.3 V relay module (low-voltage loads only)", "3 jumper wires",
                  "a 12 V or lower load to switch, like a small pump or LED strip"),
        "wiring": (("relay VCC", "3V3 (or 5V/VIN if the module needs 5 V; its IN still takes 3.3 V)"),
                   ("relay GND", "GND"), ("relay IN", "GPIO 26")),
        "libs": (),
        "code": """#include <Arduino.h>

const int RELAY = 26;
int switches = 0;

void setup() {
  Serial.begin(115200);
  pinMode(RELAY, OUTPUT);
}

void loop() {
  digitalWrite(RELAY, switches % 2 == 0 ? HIGH : LOW);   // some modules switch on LOW: watch which
  switches++;
  Serial.printf("MIA RELAY %d\\n", switches);
  delay(2000);
}
""",
    },
    "wifi": {
        "parts": ("ESP32 dev board", "your Wi-Fi's name and password, typed by you into src/secrets.h"),
        "wiring": (),
        "libs": (),
        "secrets": True,
        "code": """#include <Arduino.h>
#include <WiFi.h>
#include "secrets.h"   // #define WIFI_NAME "..." and #define WIFI_PASSWORD "...": yours, typed by you

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_NAME, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.println("MIA WIFI_WAITING"); }
  Serial.printf("MIA WIFI %s\\n", WiFi.localIP().toString().c_str());
}

void loop() {
  Serial.printf("MIA RSSI %d\\n", WiFi.RSSI());   // signal strength, in dBm
  delay(5000);
}
""",
    },
    "web": {
        "parts": ("ESP32 dev board", "the soil sensor from the soil lab, still wired to GPIO 35", "src/secrets.h"),
        "wiring": (("sensor AOUT", "GPIO 35"),),
        "libs": (),
        "secrets": True,
        "code": """#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "secrets.h"

WebServer server(80);
int served = 0;

void reading() {
  served++;
  server.send(200, "application/json", String("{\\"soil\\": ") + analogRead(35) + "}");
  Serial.printf("MIA WEB %d\\n", served);
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_NAME, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  server.on("/reading", reading);
  server.begin();
  Serial.printf("MIA WIFI %s\\n", WiFi.localIP().toString().c_str());   // open http://<this>/reading
}

void loop() {
  server.handleClient();
}
""",
    },
    "sleep": {
        "parts": ("ESP32 dev board", "the soil sensor on GPIO 35"),
        "wiring": (("sensor AOUT", "GPIO 35"),),
        "libs": (),
        "code": """#include <Arduino.h>

RTC_DATA_ATTR int wakes = 0;   // kept through deep sleep in the RTC's memory
const uint64_t SLEEP_US = 10ULL * 1000000ULL;   // 10 seconds; a real node sleeps for minutes

void setup() {
  Serial.begin(115200);
  delay(200);
  wakes++;
  Serial.printf("MIA WAKE %d\\n", wakes);
  Serial.printf("MIA SOIL %d\\n", analogRead(35));
  Serial.flush();
  esp_sleep_enable_timer_wakeup(SLEEP_US);
  esp_deep_sleep_start();   // nothing after this runs: it starts again from setup
}

void loop() {}
""",
    },
    "watchdog": {
        "parts": ("ESP32 dev board", "LED and 220 ohm resistor (or just the onboard LED)"),
        "wiring": (("LED long leg, through the resistor", "GPIO 2"), ("LED short leg", "GND"),
                   ("the BOOT button", "GPIO 0 (already on the board)")),
        "libs": (),
        "code": """#include <Arduino.h>

// A small copy of the greenhouse's safety board (homestead/firmware/safety_mcu): the PC proposes, this board decides,
// and silence means safe. The LED stands in for a dosing pump: never wire a real pump or valve to this lab.
const int PUMP = 2;                       // the "pump": an LED (the onboard one lights too)
const int STOP_BUTTON = 0;                // BOOT: the stop by hand
const unsigned long SILENCE_MS = 15000;   // no heartbeat this long: go safe
const unsigned long DOSE_MS = 1000;       // a dose is a pulse, never left on

unsigned long lastHeard = 0, doseStarted = 0;
bool safe = false, stopped = false, dosing = false;
int heartbeats = 0, doses = 0, fallbacks = 0;
String line = "";

void goSafe(const char* why) {
  digitalWrite(PUMP, LOW);   // a dosing pump's safe state is always off
  dosing = false;
  safe = true;
  fallbacks++;
  Serial.printf("MIA FALLBACK %d %s\\n", fallbacks, why);
}

void handle(String said) {
  said.trim();
  if (said == "hb") {                 // the PC's heartbeat
    lastHeard = millis();
    heartbeats++;
    Serial.printf("MIA HEARTBEAT %d\\n", heartbeats);
    if (safe && !stopped) { safe = false; Serial.println("MIA RECOVERED"); }
  } else if (said == "dose") {        // the PC asks; the board decides
    if (safe) { Serial.println("MIA REFUSED safe"); return; }
    if (dosing) { Serial.println("MIA REFUSED busy"); return; }
    dosing = true;
    doseStarted = millis();
    digitalWrite(PUMP, HIGH);
    doses++;
    Serial.printf("MIA DOSE %d\\n", doses);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PUMP, OUTPUT);
  digitalWrite(PUMP, LOW);            // start off: the safest default
  pinMode(STOP_BUTTON, INPUT_PULLUP);
  lastHeard = millis();
  Serial.println("MIA SAFE_START");
}

void loop() {
  while (Serial.available()) {        // never blocking: it keeps listening, even mid-dose
    char c = Serial.read();
    if (c == '\\n') { handle(line); line = ""; }
    else if (line.length() < 32) line += c;
  }
  if (dosing && millis() - doseStarted >= DOSE_MS) {
    digitalWrite(PUMP, LOW);
    dosing = false;
    Serial.printf("MIA DOSED %d\\n", doses);
  }
  if (!safe && millis() - lastHeard >= SILENCE_MS) goSafe("silence");
  if (!stopped && digitalRead(STOP_BUTTON) == LOW) {   // a stop by hand is only undone by hand (EN restarts it)
    stopped = true;
    Serial.println("MIA STOP 1");
    if (!safe) goSafe("stop");
    else { digitalWrite(PUMP, LOW); dosing = false; }
  }
}
""",
    },
}

def _tied(stages: tuple) -> tuple:
    """Pure logic. Each lesson tied to the checks its own sketch prints the marker of (its `about`), so the next step
    names the lesson behind a check (core/paths.next_step), not the stage's first."""
    from dataclasses import replace

    return tuple(replace(s, lessons=tuple(
        replace(l, about=tuple(c.about for c in s.checks
                               if l.id in LABS and f"MIA {c.about.split()[0]}" in LABS[l.id]["code"]))
        for l in s.lessons)) for s in stages)


STAGES: tuple[Stage, ...] = _tied((
    Stage(1, "First light", "the board on USB, flashing a sketch, an LED and the serial monitor", (
        Lesson("blink", "Blink the LED", (
            "Plug the board in with a data USB cable; MIA finds its serial port (the course page, or \"which board is "
            "plugged in?\").",
            "Read the sketch: setup() runs once, loop() over and over; pinMode makes GPIO 2 an output.",
            "Say \"flash the blink lab\" (or press Flash This Lab on the course page) and approve it: MIA builds it with "
            "PlatformIO and writes it to the board.",
            "Watch the LED blink once a second, and the serial monitor count MIA BLINK 1, 2, 3.",
            "Change delay(500) to delay(100), flash again, and see it blink faster."),
            "Every project starts here: proving the board, the cable, the upload and your code all work.",
            ("A charge-only USB cable: the board lights but no port appears.",
             "A board that won't take the upload: hold BOOT while it starts uploading.")),
        Lesson("hello", "Talk over serial", (
            "Flash the hello lab; open the serial monitor at 115200 baud.",
            "Serial.begin sets the speed; both ends must agree, or you see garbage.",
            "Watch MIA HELLO count the seconds since it started; press EN (reset) and see it start over."),
            "The serial monitor is your window into the board: every later lab tells you what it's doing through it.",
            ("The wrong baud rate: gibberish on the monitor.", "Printing too fast, which floods the monitor.")),
    ), (
        Check("esp_blink", "Blink the LED five times, the board saying so", VERIFIER, about="BLINK min",
              passes_at=5, unit="blinks"),
        Check("esp_hello", "Have the board say hello over serial", VERIFIER, about="HELLO"),
    )),
    Stage(2, "Inputs", "reading a button and an analog voltage", (
        Lesson("button", "Read a button", (
            "The BOOT button is on GPIO 0, pulled up inside: it reads HIGH, and LOW while pressed.",
            "Flash the button lab and press BOOT a few times: MIA BUTTON counts each press once.",
            "Comment out the debounce (the 50 ms) and see one press counted several times: that's switch bounce."),
            "Buttons, limit switches and float switches are all read this way.",
            ("Holding BOOT while the board starts: it goes into download mode instead.",)),
        Lesson("pot", "Read a voltage", (
            "Wire the pot: outer legs to 3V3 and GND, the middle (wiper) to GPIO 34.",
            "Flash the pot lab and turn the knob end to end: MIA ADC goes from about 0 to 4095.",
            "That's the voltage from 0 to 3.3 V in 4096 steps; the ends aren't perfectly linear on an ESP32."),
            "Soil moisture, light, a tank's level and a battery's voltage are all read as an analog voltage.",
            ("Using an ADC2 pin (like 4, 12 to 15, 25 to 27): those stop working when Wi-Fi is on; GPIO 32 to 39 "
             "are ADC1.", "More than 3.3 V on any pin can kill the board.")),
    ), (
        Check("esp_button", "Press the button three times, each counted once", VERIFIER, about="BUTTON min",
              passes_at=3, unit="presses"),
        Check("esp_pot", "Turn the pot end to end, the readings spreading at least 3000", VERIFIER,
              about="ADC spread", passes_at=3000, unit="counts"),
    )),
    Stage(3, "Sensors", "a temperature and humidity sensor and a soil moisture sensor", (
        Lesson("dht", "Temperature and humidity", (
            "Wire the DHT22: VCC to 3V3, DATA to GPIO 4, GND to GND (a bare sensor needs 10k from DATA to 3V3).",
            "Flash the dht lab (MIA adds the DHT libraries), and watch MIA TEMP and MIA HUMIDITY every 2.5 s.",
            "Breathe on it: the humidity jumps, then settles."),
            "The greenhouse runs on readings like these: knowing a sensor's limits is knowing when to trust it.",
            ("MIA SENSOR_ERROR: the data wire or the pull-up.", "Reading faster than every 2 s gives old values.")),
        Lesson("soil", "Soil moisture", (
            "Wire the capacitive sensor: VCC to 3V3, GND to GND, AOUT to GPIO 35.",
            "Flash the soil lab; hold it in dry air, then dry soil, then a cup of water (only up to the line).",
            "Note your dry and wet numbers: they're your sensor's own calibration."),
            "Watering on a reading beats watering on a schedule; every sensor needs its own dry and wet numbers.",
            ("The cheap resistive (two-prong) sensors corrode in weeks: use capacitive.",
             "Water over the line on the sensor shorts the electronics.")),
    ), (
        Check("esp_dht", "Read a room's temperature from the DHT22", VERIFIER, about="TEMP range -10 50",
              unit="°C"),
        Check("esp_soil", "Read dry and wet soil, the readings spreading at least 500", VERIFIER,
              about="SOIL spread", passes_at=500, unit="counts"),
    )),
    Stage(4, "Outputs", "PWM brightness and switching a load with a relay", (
        Lesson("fade", "Fade an LED", (
            "Flash the fade lab: analogWrite sets the duty cycle from 0 to 255 (PWM: on and off very fast).",
            "Watch the LED breathe, and MIA FADE count each full cycle.",
            "The same signal sets a motor's speed or a fan's."),
            "Dimming lights, running pumps and fans at a speed: PWM is how a microcontroller does it.",
            ("An LED with no resistor burns out (and can hurt the pin).",)),
        Lesson("relay", "Switch a load", (
            "Wire the relay module: VCC, GND, and IN to GPIO 26.",
            "Flash the relay lab: it clicks every 2 seconds; MIA RELAY counts the switches.",
            "Only a low-voltage load (12 V or less) on the relay's contacts: anything on mains is a qualified "
            "electrician's job, never a lab."),
            "Pumps, lights and heaters are switched with relays; the ESP32's pins can't drive them directly.",
            ("Some modules switch on LOW: if it's backwards, that's why.",
             "A relay switching mains on a breadboard: never.")),
    ), (
        Check("esp_fade", "Fade the LED up and down three times", VERIFIER, about="FADE min", passes_at=3,
              unit="cycles"),
        Check("esp_relay", "Switch the relay four times", VERIFIER, about="RELAY min", passes_at=4,
              unit="switches"),
    )),
    Stage(5, "Connected", "Wi-Fi and a little web server", (
        Lesson("wifi", "Join your Wi-Fi", (
            "Make src/secrets.h with your Wi-Fi's name and password (you type them; MIA never does, and it isn't "
            "shared).", "Flash the wifi lab: it prints MIA WIFI and the address your router gave it.",
            "Watch MIA RSSI: the signal in dBm (-50 is strong, -80 weak). Walk it away and see it drop."),
            "A connected board can report to MIA from the greenhouse, the coop or the well house.",
            ("Only 2.4 GHz networks: the ESP32 can't see 5 GHz.", "A password typo: it waits forever.")),
        Lesson("web", "Serve a reading", (
            "Keep the soil sensor on GPIO 35; flash the web lab.",
            "Open http://<its address>/reading in a browser on the same network: it answers with the soil reading "
            "as JSON.", "MIA WEB counts every request it answers."),
            "This is how a node shares what it measures: the greenhouse node's exports work the same way.",
            ("A phone on mobile data instead of your Wi-Fi can't reach it.",)),
    ), (
        Check("esp_wifi", "Join your Wi-Fi, the board saying its address", VERIFIER, about="WIFI"),
        Check("esp_web", "Answer a web request with a reading", VERIFIER, about="WEB min", passes_at=1,
              unit="requests"),
    )),
    Stage(6, "A real node", "deep sleep, the start of a battery sensor node", (
        Lesson("sleep", "Sleep and wake", (
            "Flash the sleep lab: it wakes, reads the soil, says MIA WAKE, and sleeps 10 seconds.",
            "RTC_DATA_ATTR keeps the count through sleep; everything else starts fresh each wake.",
            "Asleep it draws microamps, awake tens of milliamps: that's what makes a battery last months."),
            "A sensor node out in the garden lives on a battery: deep sleep is how.",
            ("The serial monitor drops while it sleeps: that's expected.",
             "To flash it again, press BOOT while it's awake.")),
    ), (
        Check("esp_sleep", "Wake from deep sleep three times", VERIFIER, about="WAKE min", passes_at=3,
              unit="wakes"),
    )),
    Stage(7, "The greenhouse's safety brain", "a watchdog that goes safe on its own: the capstone", (
        Lesson("watchdog", "Go safe on your own", (
            "Flash the watchdog lab: the LED on GPIO 2 is a dosing pump, the BOOT button the stop by hand.",
            "In the serial monitor (115200, newline on) type hb: that's the PC's heartbeat, and MIA HEARTBEAT counts "
            "it. Type dose: the pump pulses for one second and turns itself off, never left on.",
            "Stop typing. 15 seconds later it says MIA FALLBACK, holds the pump off and refuses a dose until it hears "
            "hb again.",
            "Press BOOT: MIA STOP, and it stays stopped even when hb comes back. A stop by hand is only undone by "
            "hand: EN restarts it."),
            "The heartbeat guards against the PC failing, not the board: if the PC crashes, freezes or its cable is "
            "pulled, nothing would ever tell a pump to stop, so the board takes silence to mean the worst and goes "
            "safe on its own. It refuses a dose while it's safe, because the PC asking may be the broken part, and "
            "while one is still running, because two at once would double it. This is how the greenhouse's own "
            "safety board works (homestead/firmware/safety_mcu): the PC proposes, the board decides, and silence "
            "means safe. That firmware's own LED test, on a board like this one, is the greenhouse's next milestone.",
            ("A dose done with delay() stops the board listening, even to the stop button: this one never blocks.",
             "Safe means the pump off: a dosing pump's safe state is always off, never on.",
             "An LED stands in for the pump: never a real pump or valve on this lab.")),
    ), (
        Check("esp_fallback", "Go safe on its own when the PC goes quiet", VERIFIER, about="FALLBACK"),
        Check("esp_stop", "Stop it by hand with BOOT", VERIFIER, about="STOP"),
    )),
))


# ------------------------------------------------------------------ the check: what the board said

_LINE = re.compile(r"^[ \t]*MIA ([A-Z_]+)(?:[ \t]+(\S+))?", re.M)  # one line each: never a value from the next


def said_by_board(text: str) -> dict:
    """Pure logic. {MARKER: [values]} from a board's serial output: each `MIA <MARKER> <value>` line (a value that
    isn't a number kept as None, so a marker alone, `MIA HELLO`, still counts)."""
    out: dict = {}
    for marker, value in _LINE.findall(str(text or "")):
        try:
            number = float(value) if value else None
        except ValueError:
            number = None
        out.setdefault(marker, []).append(number)
    return out


def judge(check: Check, text: str) -> tuple:
    """Pure logic. (passed, the value that counts, in words) for a check from what the board said: its `about` is
    the marker and how it passes (seen; `min` a value at least the mark; `spread` the readings at least the mark
    apart; `range lo hi` a value within it)."""
    parts = check.about.split()
    marker, mode = parts[0], (parts[1] if len(parts) > 1 else "seen")
    values = said_by_board(text).get(marker)
    if not values:
        return False, None, f"the board didn't say MIA {marker} yet"
    numbers = [v for v in values if v is not None]
    if mode == "seen":
        return True, None, f"the board said MIA {marker}"
    if not numbers:
        return False, None, f"MIA {marker} came without a number"
    if mode == "min":
        best = max(numbers)
        return best >= check.passes_at, best, f"{best:g} {check.unit} (it passes at {check.passes_at:g})"
    if mode == "spread":
        spread = max(numbers) - min(numbers)
        return (spread >= check.passes_at, spread,
                f"the readings spread {spread:g} {check.unit} (it passes at {check.passes_at:g})")
    if mode == "range":
        low, high = float(parts[2]), float(parts[3])
        inside = [v for v in numbers if low <= v <= high]
        last = numbers[-1]
        return (bool(inside), last, f"{last:g} {check.unit}" + ("" if inside else
                                                                    f", outside {low:g} to {high:g}"))
    return False, None, "a check this lab doesn't know how to read"


def _board_says(context, program: Program, check: Check, payload) -> dict:
    """Verifier board_says: the check judged from the board's serial output (payload {"serial": text}, or the
    text), the attempt kept either way."""
    text = payload.get("serial") if isinstance(payload, dict) else payload
    if not str(text or "").strip():
        raise ValueError("No serial output to check: flash the lab, then read the board (or paste what it said).")
    passed, value, how = judge(check, str(text))
    done = context.paths.attempt(program, check.id, passed, value=value, how="board", detail=how[:120])
    said = (f"Passed: {check.what} ({how})." if passed else f"Not yet: {how}.")
    return {"check": check.id, "passed": passed, "value": value, "said": said, "stage_done": done["stage_done"]}


def lab_of(lesson_id: str) -> Optional[dict]:
    """The lab a lesson is worked on, or None."""
    return LABS.get(lesson_id)


def _extra(lesson: Lesson) -> str:
    """A lesson's lab, for teaching it: the parts, the wiring and the sketch."""
    lab = LABS.get(lesson.id)
    if lab is None:
        return ""
    parts = "Parts: " + ", ".join(lab["parts"]) + "."
    wiring = (" Wiring: " + "; ".join(f"{a} to {b}" for a, b in lab["wiring"]) + ".") if lab["wiring"] else ""
    return f"{parts}{wiring} The sketch:\n{lab['code']}"


PROGRAM = register(Program(
    "esp32", "Build With ESP32", SKILL, "🔌", "From the first blink to a sensor node that sleeps on a battery: "
    "real labs on a real ESP32, each one checked by what the board itself says.",
    ("esp32", "microcontroller", "electronics", "build with esp32"), STAGES,  # "arduino" is Build With Arduino's
    verifiers={VERIFIER: _board_says}, extra=_extra, plan=(30, 3)))
