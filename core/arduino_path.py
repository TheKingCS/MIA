"""
core.arduino_path
===================

Build With Arduino, the second interactive lab course (Zac, 2026-11-25: "I also have an arduino ELEGOO MEGA R3 kit and
a bunch of arduino nanos that she should be able to teach me with"), on the standard Build With ESP32 set
(docs/future/INTERACTIVE_LABS_PLAN.md): real labs, each with its parts, wiring and sketch, each check passed only by
what his board prints over serial (`MIA <MARKER> <value>`, judged by core/esp32_path.judge), never by a simulator run.

One course for both his boards (core/boards.py): every lab uses only the pins the Mega and the Nano share (D2 to D13,
A0, A1, 5V, GND), so it's wired the same on either, and flashed for the one he names ("flash the blink lab to my
nano"; the Mega, his kit's board, otherwise). The parts are the ones an ELEGOO Mega starter kit carries: LEDs and
220 ohm resistors, a push button, a 10k potentiometer, a photoresistor with a 10k resistor, the HC-SR04 ultrasonic
sensor, a DHT11, an SG90 servo and a buzzer. The sketches use Serial.print (the AVR core has no printf) at 9600 baud.

Facts from: Arduino's own documentation (digitalRead with INPUT_PULLUP, analogRead's 0 to 1023 on 5 V, analogWrite's
PWM pins, the Servo library, pulseIn, tone()); the HC-SR04's datasheet (a 10 microsecond trigger pulse, an echo
whose length in microseconds divided by 58 is centimetres); the DHT11's (2 seconds between readings) and the SG90's
(5 V, 0 to 180 degrees).
"""

from __future__ import annotations

from dataclasses import replace

from core.esp32_path import VERIFIER, _board_says
from core.paths import Check, Lesson, Program, Stage, register

SKILL = "engineering"

LABS: dict = {
    "blink": {
        "parts": ("your Arduino (Mega or Nano)", "USB cable", "an LED and a 220 ohm resistor (optional: the onboard LED "
                  "blinks too)"),
        "wiring": (("D13", "220 ohm resistor, then the LED's long leg (+)"), ("the LED's short leg (-)", "GND")),
        "libs": (),
        "code": """#include <Arduino.h>

int blinks = 0;

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);   // pin 13 on the Mega and the Nano, with an LED on the board
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
  blinks++;
  Serial.print("MIA BLINK ");   // MIA reads this to check the lab
  Serial.println(blinks);
}
""",
    },
    "hello": {
        "parts": ("your Arduino", "USB cable"),
        "wiring": (),
        "libs": (),
        "code": """#include <Arduino.h>

void setup() {
  Serial.begin(9600);
}

void loop() {
  Serial.print("MIA HELLO ");   // hello, and the seconds since it started
  Serial.println(millis() / 1000);
  delay(2000);
}
""",
    },
    "button": {
        "parts": ("your Arduino", "a push button", "2 jumper wires"),
        "wiring": (("one leg of the button", "D2"), ("the leg across from it", "GND")),
        "libs": (),
        "code": """#include <Arduino.h>

const int BUTTON = 2;   // pulled up inside the chip: it reads LOW while pressed
int presses = 0;
int last = HIGH;
unsigned long changed = 0;

void setup() {
  Serial.begin(9600);
  pinMode(BUTTON, INPUT_PULLUP);
}

void loop() {
  int now = digitalRead(BUTTON);
  if (now != last && millis() - changed > 50) {   // 50 ms of debounce
    changed = millis();
    if (now == LOW) {
      presses++;
      Serial.print("MIA BUTTON ");
      Serial.println(presses);
    }
    last = now;
  }
}
""",
    },
    "pot": {
        "parts": ("your Arduino", "10k potentiometer", "3 jumper wires"),
        "wiring": (("pot outer leg", "5V"), ("pot other outer leg", "GND"), ("pot middle leg (wiper)", "A0")),
        "libs": (),
        "code": """#include <Arduino.h>

void setup() {
  Serial.begin(9600);
}

void loop() {
  Serial.print("MIA ADC ");   // 0 at GND to 1023 at 5 V
  Serial.println(analogRead(A0));
  delay(250);
}
""",
    },
    "light": {
        "parts": ("your Arduino", "a photoresistor", "a 10k resistor", "3 jumper wires"),
        "wiring": (("one leg of the photoresistor", "5V"), ("its other leg", "A1, and one end of the 10k resistor"),
                   ("the 10k resistor's other end", "GND")),
        "libs": (),
        "code": """#include <Arduino.h>

void setup() {
  Serial.begin(9600);
}

void loop() {
  Serial.print("MIA LIGHT ");   // more light, less resistance, a higher reading
  Serial.println(analogRead(A1));
  delay(500);
}
""",
    },
    "distance": {
        "parts": ("your Arduino", "HC-SR04 ultrasonic sensor", "4 jumper wires"),
        "wiring": (("HC-SR04 VCC", "5V"), ("HC-SR04 TRIG", "D7"), ("HC-SR04 ECHO", "D8"), ("HC-SR04 GND", "GND")),
        "libs": (),
        "code": """#include <Arduino.h>

const int TRIG = 7;
const int ECHO = 8;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
}

void loop() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);   // a 10 microsecond pulse sends the ping
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long echo = pulseIn(ECHO, HIGH, 30000);   // how long the echo took, waiting 30 ms at most (about 5 m)
  if (echo == 0) {
    Serial.println("MIA DIST_NONE");   // nothing came back in range
  } else {
    Serial.print("MIA DIST ");
    Serial.println(echo / 58);   // microseconds to centimetres, there and back
  }
  delay(300);
}
""",
    },
    "dht": {
        "parts": ("your Arduino", "DHT11 temperature and humidity sensor (a module, or bare with a 10k pull-up)",
                  "3 jumper wires"),
        "wiring": (("DHT11 VCC (+)", "5V"), ("DHT11 DATA", "D3"), ("DHT11 GND (-)", "GND")),
        "libs": ("adafruit/DHT sensor library", "adafruit/Adafruit Unified Sensor"),
        "code": """#include <Arduino.h>
#include <DHT.h>

DHT dht(3, DHT11);   // the data pin, and the sensor's type

void setup() {
  Serial.begin(9600);
  dht.begin();
}

void loop() {
  delay(2000);   // the DHT11 reads at most about once a second; two is safe
  float c = dht.readTemperature();
  float h = dht.readHumidity();
  if (isnan(c) || isnan(h)) {
    Serial.println("MIA SENSOR_ERROR");   // check the wiring
    return;
  }
  Serial.print("MIA TEMP ");
  Serial.println(c, 1);
  Serial.print("MIA HUMIDITY ");
  Serial.println(h, 1);
}
""",
    },
    "fade": {
        "parts": ("your Arduino", "an LED and a 220 ohm resistor", "2 jumper wires"),
        "wiring": (("D5", "220 ohm resistor, then the LED's long leg (+)"), ("the LED's short leg (-)", "GND")),
        "libs": (),
        "code": """#include <Arduino.h>

const int LED = 5;   // a PWM pin (marked ~) on the Mega and the Nano
int fades = 0;

void setup() {
  Serial.begin(9600);
  pinMode(LED, OUTPUT);
}

void loop() {
  for (int duty = 0; duty <= 255; duty += 5) { analogWrite(LED, duty); delay(15); }   // brighter
  for (int duty = 255; duty >= 0; duty -= 5) { analogWrite(LED, duty); delay(15); }   // and dimmer
  fades++;
  Serial.print("MIA FADE ");
  Serial.println(fades);
}
""",
    },
    "servo": {
        "parts": ("your Arduino", "SG90 micro servo", "3 jumper wires"),
        "wiring": (("servo brown (GND)", "GND"), ("servo red (+)", "5V"), ("servo orange (signal)", "D6")),
        "libs": (),
        "code": """#include <Arduino.h>
#include <Servo.h>

Servo arm;

void setup() {
  Serial.begin(9600);
  arm.attach(6);
}

void loop() {
  for (int angle = 0; angle <= 180; angle += 30) {   // across its range, a step at a time
    arm.write(angle);
    Serial.print("MIA SERVO ");
    Serial.println(angle);
    delay(500);
  }
  for (int angle = 180; angle >= 0; angle -= 30) {
    arm.write(angle);
    Serial.print("MIA SERVO ");
    Serial.println(angle);
    delay(500);
  }
}
""",
    },
    "buzzer": {
        "parts": ("your Arduino", "a buzzer (passive sounds best with tone())", "2 jumper wires"),
        "wiring": (("buzzer + (the longer leg, or marked +)", "D4"), ("buzzer -", "GND")),
        "libs": (),
        "code": """#include <Arduino.h>

const int BUZZER = 4;
int beeps = 0;

void setup() {
  Serial.begin(9600);
}

void loop() {
  tone(BUZZER, 1000, 200);   // 1000 Hz for 200 ms
  beeps++;
  Serial.print("MIA BEEP ");
  Serial.println(beeps);
  delay(1000);
}
""",
    },
}


def _tied(stages: tuple) -> tuple:
    """Pure logic. Each lesson tied to the checks its own sketch prints the marker of, so the next step names the
    lesson behind a check (core/paths.next_step)."""
    return tuple(replace(s, lessons=tuple(
        replace(l, about=tuple(c.about for c in s.checks
                               if l.id in LABS and f"MIA {c.about.split()[0]} " in LABS[l.id]["code"]))
        for l in s.lessons)) for s in stages)


def _lesson(id_, title, steps, why, watch=()) -> Lesson:
    """A lesson (the steps, the why, what to watch for)."""
    return Lesson(id_, title, tuple(steps), why, tuple(watch))


STAGES: tuple = _tied((
    Stage(1, "First light", "the board on USB, flashing a sketch, the LED and the serial monitor", (
        _lesson("blink", "Blink the LED", (
            "Plug the Arduino in with its USB cable; MIA finds its port (the course page, or \"is my arduino plugged "
            "in?\").",
            "Read the sketch: setup() runs once, loop() over and over; LED_BUILTIN is pin 13, with an LED on the board.",
            "Say \"flash the blink lab\" (\"to my nano\" for a Nano) and approve it: MIA builds it with PlatformIO and "
            "uploads it.",
            "Watch the LED blink once a second, and the serial monitor count MIA BLINK 1, 2, 3.",
            "Then wire your own LED to D13 through the 220 ohm resistor: it blinks with the onboard one."),
            "Every project starts here: proving the board, the cable, the upload and your code all work.",
            ("A Nano that won't take the upload: many clones need the old bootloader (MIA tries it first; say \"new "
             "bootloader\" if yours has it).", "The LED in backwards: the long leg goes toward the pin.")),
        _lesson("hello", "Talk over serial", (
            "Flash the hello lab; the serial monitor listens at 9600 baud, the speed in Serial.begin.",
            "Watch MIA HELLO count the seconds since it started; press the reset button and see it start over."),
            "The serial monitor is your window into the board: every later lab tells you what it's doing through it.",
            ("The wrong baud rate: gibberish on the monitor.",)),
    ), (
        Check("ard_blink", "Blink the LED five times, the board saying so", VERIFIER, about="BLINK min", passes_at=5,
              unit="blinks"),
        Check("ard_hello", "Have the board say hello over serial", VERIFIER, about="HELLO"),
    )),
    Stage(2, "Inputs", "reading a button and a voltage", (
        _lesson("button", "Read a button", (
            "Wire the button across the breadboard's middle gap: one leg to D2, the leg across from it to GND.",
            "INPUT_PULLUP holds D2 at 5 V inside the chip until the button connects it to GND: pressed reads LOW.",
            "Flash the button lab and press it; each press counts once (the 50 ms debounce)."),
            "A pull-up means no extra resistor and no floating pin: the simplest reliable input.",
            ("Both wires on the same side of a button's legs that are always joined: it never changes.",
             "No debounce: one press counted as several.")),
        _lesson("pot", "Read a voltage", (
            "Wire the pot: an outer leg to 5V, the other to GND, the middle (wiper) to A0.",
            "analogRead turns 0 to 5 V into 0 to 1023 (10 bits).",
            "Flash the pot lab and turn the knob end to end while the monitor reads."),
            "Knobs, light sensors and many others are all a voltage read like this.",
            ("The wiper on an outer leg: the reading never moves.",)),
    ), (
        Check("ard_button", "Press the button three times, each counted once", VERIFIER, about="BUTTON min",
              passes_at=3, unit="presses"),
        Check("ard_pot", "Turn the pot end to end, the readings spreading at least 800", VERIFIER, about="ADC spread",
              passes_at=800, unit="counts"),
    )),
    Stage(3, "Sensors", "light, distance, temperature and humidity", (
        _lesson("light", "Sense light", (
            "Build a divider: the photoresistor from 5V to A1, the 10k resistor from A1 to GND.",
            "More light, less resistance in the photoresistor, a higher reading at A1.",
            "Flash the light lab; cover it with your hand, then shine a light on it."),
            "A divider turns any resistance that changes into a voltage the board can read.",
            ("Leaving out the 10k: A1 floats and the reading wanders.",)),
        _lesson("distance", "Measure distance", (
            "Wire the HC-SR04: VCC to 5V, GND to GND, TRIG to D7, ECHO to D8.",
            "The sketch sends a 10 microsecond pulse; the sensor pings, and ECHO stays high as long as the sound "
            "took there and back. Microseconds divided by 58 is centimetres.",
            "Flash the distance lab and move your hand nearer and farther."),
            "Echo timing is how parking sensors, water-level gauges and robots see.",
            ("TRIG and ECHO swapped: nothing comes back.", "Soft or angled surfaces scatter the ping.")),
        _lesson("dht", "Temperature and humidity", (
            "Wire the DHT11: VCC to 5V, GND to GND, DATA to D3 (a module has its pull-up resistor on it).",
            "Flash the dht lab; it reads every two seconds, the sensor's pace.",
            "Breathe on it and watch the humidity climb."),
            "Temperature and humidity are the first two numbers of any greenhouse or coop monitor.",
            ("Reading faster than the sensor allows: errors or stale values.",)),
    ), (
        Check("ard_light", "Cover and light the sensor, the readings spreading at least 200", VERIFIER,
              about="LIGHT spread", passes_at=200, unit="counts"),
        Check("ard_dist", "Move your hand, the distances spreading at least 20 cm", VERIFIER, about="DIST spread",
              passes_at=20, unit="cm"),
        Check("ard_dht", "Read a room's temperature from the DHT11", VERIFIER, about="TEMP range -10 50",
              unit="°C"),
    )),
    Stage(4, "Outputs", "PWM, a servo and sound", (
        _lesson("fade", "Fade an LED", (
            "Wire an LED to D5 through the 220 ohm resistor (D5 is a PWM pin, marked ~).",
            "analogWrite switches the pin on and off fast; the share of time it's on (0 to 255) is the brightness.",
            "Flash the fade lab and watch it breathe."),
            "PWM is how a digital pin dims a light or slows a motor.",
            ("A pin without the ~ mark: it only switches fully on or off.",)),
        _lesson("servo", "Move a servo", (
            "Wire the SG90: brown to GND, red to 5V, orange to D6.",
            "The Servo library sends the pulse that sets its angle, 0 to 180 degrees.",
            "Flash the servo lab and watch it sweep. One small servo, unloaded, can run from the board's 5V; a "
            "loaded one or several need their own supply, with its GND joined to the board's."),
            "Servos turn a valve, open a vent or aim a sensor: the first step from reading the world to acting on it.",
            ("A servo stalled at its end: it hums and heats; don't force it past its range.",)),
        _lesson("buzzer", "Make a sound", (
            "Wire the buzzer: its + to D4, its - to GND.",
            "tone() makes a square wave at the pitch you ask (1000 Hz here) for a passive buzzer; an active one just "
            "beeps.",
            "Flash the buzzer lab and listen."),
            "An alarm you can hear is the simplest way a project can call for you.",
            ("The buzzer's legs swapped: a polarized one stays silent.",)),
    ), (
        Check("ard_fade", "Fade the LED up and down three times", VERIFIER, about="FADE min", passes_at=3,
              unit="fades"),
        Check("ard_servo", "Sweep the servo, its angles spreading at least 150 degrees", VERIFIER,
              about="SERVO spread", passes_at=150, unit="degrees"),
        Check("ard_beep", "Beep the buzzer three times", VERIFIER, about="BEEP min", passes_at=3, unit="beeps"),
    )),
))


def lab_of(lesson_id: str):
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
    "arduino", "Build With Arduino", SKILL, "🔧", "Your Mega or Nano from the first blink to sensors, a servo and "
    "sound: real labs with your kit's parts, each one checked by what the board itself says.",
    ("arduino", "arduino mega", "arduino nano", "elegoo", "build with arduino"), STAGES,
    verifiers={VERIFIER: _board_says}, extra=_extra, plan=(30, 3)))
