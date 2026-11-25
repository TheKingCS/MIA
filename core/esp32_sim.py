"""
core.esp32_sim
================

The ESP32 lab simulator (docs/future/INTERACTIVE_LABS_PLAN.md, step 3; Zac, 2026-11-25: build and test the hardware
in a simulator, and MIA walking him through building alongside it). Pure logic: no board, no network, nothing kept.

- **The board** (`BOARD_LEFT`, `BOARD_RIGHT`, `label`): the pins of a 30-pin ESP32 DevKit (the DOIT V1 layout), as
  printed beside them (D2 for GPIO 2, VP, TX0).
- **A lab's circuit** (`CIRCUITS`, `circuit_of`): its parts, the pin its sketch uses, and the build in steps, each one
  wire with why it goes there.
- **Checking a circuit** (`analyse`): his wires (pairs of terminals, "led1.anode" or "GPIO 2") joined into nets, then
  each part judged the way it would behave: an LED lit, in backwards, or with no resistor; a pot on 5 V; a sensor's
  data on the wrong pin; 3V3 shorted to GND. Each problem says why, the way MIA would at the bench, at a level: stop
  (it would damage something or not run), warn (it won't do what the lab means), note (fine, worth knowing).
- **Building along** (`build_progress`, `build_step`, `reply`): which steps his wires already make (a resistor's or a
  pot's ends either way round) and the next; a step said in words, for the voice, taken in code before the question
  plans (core/assistant_turn.py) when he names a lab to build or says "next step" right after one.
- **Running it** (`simulate`): what the lab's sketch would print over serial and what the parts would do (the LED's
  brightness, the relay), from his circuit (or the lab's own, for "what will it print?") and the inputs he sets (the
  knob, the room, the soil, button presses, web requests), judged by the same checks as the real board
  (core/esp32_path.judge). A run in the simulator is never a pass: only the board's own words pass a check.

Tools (registered in core/esp32_lab.py): `build_along` ("walk me through building the pot lab", "next step") and
`simulate_lab` ("what will the dht lab print?").
Any board (2026-11-25): the board and course ride in a context set by a public call that names one (`course`,
`board_id`; core/boards.py), so the ESP32's labs run unchanged and Build With Arduino's (ARDUINO_CIRCUITS: a button,
a light divider, the HC-SR04, a DHT11, a servo, a buzzer) run on the Arduino's 5 V and 10-bit ADC; a part with no
rules of its own is judged against its build steps (`_by_build`).
"""

from __future__ import annotations

import functools
import random
import re
from contextvars import ContextVar
from typing import Callable, Optional

from core import boards as _boards

_BOARD = ContextVar("lab_board", default=_boards.ESP32)
_COURSE = ContextVar("lab_course", default="esp32")


def B() -> "_boards.Board":
    """The board the lab being judged runs on (core/boards.py): the ESP32 unless a call named another course."""
    return _BOARD.get()


def _in_course(fn):
    """A public call taking `course` (and `board_id`): run on that course's board; with none, on the one already set
    (the ESP32 by default)."""
    @functools.wraps(fn)
    def run(*args, course: str = "", board_id: str = "", **kwargs):
        """The call, on its course's board."""
        if not course:
            return fn(*args, **kwargs)
        tokens = (_COURSE.set(course), _BOARD.set(_boards.board_for(course, board_id)))
        try:
            return fn(*args, **kwargs)
        finally:
            _COURSE.reset(tokens[0])
            _BOARD.reset(tokens[1])
    return run

BOARD_LEFT, BOARD_RIGHT = _boards.ESP32.left, _boards.ESP32.right  # the ESP32 DevKit's pins (core/boards.py)
BOARD = BOARD_LEFT + BOARD_RIGHT

# kind -> (its name, its terminals (id, what it is on the part))
KINDS = {
    "led": ("LED", (("anode", "long leg (+)"), ("cathode", "short leg (-)"))),
    "resistor": ("220 ohm resistor", (("a", "one end"), ("b", "the other end"))),
    "pot": ("10k potentiometer", (("end1", "one outer leg"), ("wiper", "middle leg (wiper)"),
                                  ("end2", "the other outer leg"))),
    "dht22": ("DHT22 module", (("vcc", "VCC (+)"), ("data", "DATA"), ("gnd", "GND (-)"))),
    "soil": ("soil moisture sensor", (("vcc", "VCC"), ("gnd", "GND"), ("aout", "AOUT"))),
    "relay": ("relay module", (("vcc", "VCC"), ("gnd", "GND"), ("in", "IN"))),
    # the Arduino course's (core/arduino_path.py)
    "button": ("push button", (("a", "one leg"), ("b", "the leg across from it"))),
    "ldr": ("photoresistor", (("a", "one leg"), ("b", "the other leg"))),
    "resistor10k": ("10k resistor", (("a", "one end"), ("b", "the other end"))),
    "hcsr04": ("HC-SR04", (("vcc", "VCC"), ("trig", "TRIG"), ("echo", "ECHO"), ("gnd", "GND"))),
    "dht11": ("DHT11 module", (("vcc", "VCC (+)"), ("data", "DATA"), ("gnd", "GND (-)"))),
    "servo": ("SG90 servo", (("gnd", "brown wire (GND)"), ("vcc", "red wire (+)"), ("sig", "orange wire (signal)"))),
    "buzzer": ("buzzer", (("plus", "+ leg"), ("minus", "- leg"))),
}
SWAPS = {"resistor": ("a", "b"), "pot": ("end1", "end2"), "button": ("a", "b"), "ldr": ("a", "b"),
         "resistor10k": ("a", "b")}  # ends that work either way round

# For "what will it print?" (the lab's own circuit): the inputs that show it passing, how long, and what they are in
# words; and on the page, what to do in the simulator for the check.
SHOW = {
    "button": ({"presses": [1.0, 2.0, 3.0]}, 5.0, "with BOOT pressed three times"),
    "pot": ({"pot": [[0, 0], [5, 1]]}, 5.0, "with the knob turned end to end"),
    "soil": ({"moisture": [[0, 0], [3, 0], [4, 1]]}, 8.0, "dry, then into the cup of water"),
    "sleep": ({"moisture": [[0, 0], [31, 1]]}, 31.0, "for half a minute, the soil watered as it goes"),
    "web": ({"requests": [3.0]}, 5.0, "with one request from a browser"),
}
ARDUINO_SHOW = {
    "button": ({"presses": [1.0, 2.0, 3.0]}, 5.0, "with the button pressed three times"),
    "pot": ({"pot": [[0, 0], [5, 1]]}, 5.0, "with the knob turned end to end"),
    "light": ({"light": [[0, 0.05], [3, 0.05], [4, 0.95]]}, 7.0, "covered, then in bright light"),
    "distance": ({"distance": [[0, 10], [4, 60]]}, 5.0, "with your hand moving from 10 to 60 cm away"),
    "servo": ({}, 7.0, ""),
}
ARDUINO_TRY = {
    "button": "Press the button three times.",
    "pot": "Turn the knob from one end to the other while it runs.",
    "light": "Run it dark, then bright: the readings need to spread at least 200.",
    "distance": "Move your hand nearer and farther: the distances need to spread 20 cm.",
    "dht": "Set the room's temperature and humidity, then run it.",
}


def try_for(lesson_id: str, course: str = "esp32") -> str:
    """What to do in the simulator for a lab's check, on its course."""
    return (ARDUINO_TRY if course == "arduino" else TRY).get(lesson_id, "")


TRY = {
    "button": "Press BOOT three times.",
    "pot": "Turn the knob from one end to the other while it runs.",
    "dht": "Set the room's temperature and humidity, then run it.",
    "soil": "Run it dry, then in water: the readings need to spread at least 500.",
    "web": "Send a request, as a browser opening its address would.",
    "sleep": "Run it for half a minute: it wakes every 10 seconds.",
}

_LED_BUILD = (
    ("GPIO 2", "r1.a", "The pin drives the LED through the resistor, which limits the current: without it the LED and "
                       "the pin take far more than they should."),
    ("r1.b", "led1.anode", "The LED's long leg (+) faces the pin: an LED passes current one way only."),
    ("led1.cathode", "GND", "The short leg (-) to ground closes the loop."),
)
_SOIL = {"pin": "GPIO 35", "parts": (("soil1", "soil"),), "build": (
    ("soil1.vcc", "3V3", "The sensor runs on 3.3 V, so its output stays inside what the ESP32 can read."),
    ("soil1.gnd", "GND", "Ground: the reference every reading is measured from."),
    ("soil1.aout", "GPIO 35", "AOUT is the reading, a voltage; GPIO 35 is input-only, on ADC1, which keeps working "
                              "with Wi-Fi on.")), "note": ""}

CIRCUITS = {
    "blink": {"pin": "GPIO 2", "parts": (("r1", "resistor"), ("led1", "led")), "build": _LED_BUILD,
              "note": "The onboard LED on GPIO 2 blinks too, with nothing wired: this build is your own LED on the "
                      "same pin."},
    "hello": {"pin": "", "parts": (), "build": (), "note": "Nothing to wire: just the USB cable."},
    "button": {"pin": "GPIO 0", "parts": (), "build": (),
               "note": "The BOOT button is already on the board, on GPIO 0: press it in the simulator."},
    "pot": {"pin": "GPIO 34", "parts": (("pot1", "pot"),), "build": (
        ("pot1.end1", "3V3", "One outer leg at 3.3 V: the top of the range."),
        ("pot1.end2", "GND", "The other outer leg at ground: the bottom."),
        ("pot1.wiper", "GPIO 34", "The wiper is the voltage in between, what the ADC reads; GPIO 34 is input-only, "
                                  "on ADC1.")), "note": ""},
    "dht": {"pin": "GPIO 4", "parts": (("dht1", "dht22"),), "build": (
        ("dht1.vcc", "3V3", "Power at 3.3 V, so its DATA line stays at a level the ESP32 is safe with."),
        ("dht1.gnd", "GND", "Ground."),
        ("dht1.data", "GPIO 4", "DATA is a one-wire conversation on GPIO 4, the pin the sketch's dht(4, DHT22) "
                                "talks on.")),
        "note": "A module has its pull-up resistor on it; a bare sensor also needs 10k from DATA to 3V3."},
    "soil": _SOIL,
    "fade": {"pin": "GPIO 2", "parts": (("r1", "resistor"), ("led1", "led")), "build": _LED_BUILD,
             "note": "The onboard LED on GPIO 2 fades too."},
    "relay": {"pin": "GPIO 26", "parts": (("relay1", "relay"),), "build": (
        ("relay1.vcc", "3V3", "Power for the module's driver (VIN instead, if your module needs 5 V)."),
        ("relay1.gnd", "GND", "Ground, shared with the board, so its signal means something."),
        ("relay1.in", "GPIO 26", "IN is the signal: GPIO 26 is a pin that can drive, and the one the sketch switches.")),
        "note": "Low-voltage loads only: never mains on a breadboard."},
    "wifi": {"pin": "", "parts": (), "build": (),
             "note": "Nothing to wire. In the simulator it joins a pretend network; your real board joins yours."},
    "web": dict(_SOIL, note="The soil sensor from the soil lab, still wired. In the simulator the network is pretend."),
    "sleep": dict(_SOIL, note="The soil sensor from the soil lab, still wired."),
}


_ARD_LED = (
    ("D13", "r1.a", "The pin drives the LED through the resistor, which limits the current: without it the LED and "
                    "the pin take far more than they should."),
    ("r1.b", "led1.anode", "The LED's long leg (+) faces the pin: an LED passes current one way only."),
    ("led1.cathode", "GND", "The short leg (-) to ground closes the loop."),
)
ARDUINO_CIRCUITS = {
    "blink": {"pin": "D13", "parts": (("r1", "resistor"), ("led1", "led")), "build": _ARD_LED,
              "note": "The onboard LED on pin 13 blinks too, with nothing wired: this build is your own LED on the "
                      "same pin."},
    "hello": {"pin": "", "parts": (), "build": (), "note": "Nothing to wire: just the USB cable."},
    "button": {"pin": "D2", "parts": (("button1", "button"),), "build": (
        ("button1.a", "D2", "The pin reads the button; INPUT_PULLUP holds it at 5 V until the button is pressed."),
        ("button1.b", "GND", "Pressed, the button joins the pin to ground: it reads LOW.")),
        "note": "Put the button across the breadboard's middle gap, and use legs across from each other."},
    "pot": {"pin": "A0", "parts": (("pot1", "pot"),), "build": (
        ("pot1.end1", "5V", "One outer leg at 5 V: the top of the range."),
        ("pot1.end2", "GND", "The other outer leg at ground: the bottom."),
        ("pot1.wiper", "A0", "The wiper is the voltage in between, what analogRead(A0) turns into 0 to 1023.")),
        "note": ""},
    "light": {"pin": "A1", "parts": (("ldr1", "ldr"), ("r10k1", "resistor10k")), "build": (
        ("ldr1.a", "5V", "The photoresistor is the top of a divider, from 5 V."),
        ("ldr1.b", "A1", "The middle of the divider is the reading."),
        ("r10k1.a", "A1", "The 10k resistor is the divider's bottom half, from the middle..."),
        ("r10k1.b", "GND", "...to ground: without it, A1 floats and the reading wanders.")), "note": ""},
    "distance": {"pin": "D7", "parts": (("sonar1", "hcsr04"),), "build": (
        ("sonar1.vcc", "5V", "The HC-SR04 runs on 5 V."),
        ("sonar1.gnd", "GND", "Ground, shared with the board."),
        ("sonar1.trig", "D7", "TRIG: the board's 10 microsecond pulse that sends a ping."),
        ("sonar1.echo", "D8", "ECHO: high for as long as the sound took there and back.")), "note": ""},
    "dht": {"pin": "D3", "parts": (("dht1", "dht11"),), "build": (
        ("dht1.vcc", "5V", "The DHT11 runs on 3.3 to 5 V; 5 V on an Arduino."),
        ("dht1.gnd", "GND", "Ground."),
        ("dht1.data", "D3", "DATA is a one-wire conversation on D3, the pin the sketch's dht(3, DHT11) talks on.")),
        "note": "A module has its pull-up resistor on it; a bare sensor also needs 10k from DATA to 5V."},
    "fade": {"pin": "D5", "parts": (("r1", "resistor"), ("led1", "led")), "build": (
        ("D5", "r1.a", "D5 is a PWM pin (marked ~): it can dim the LED. Through the resistor, to limit the current."),
        ("r1.b", "led1.anode", "The LED's long leg (+) faces the pin."),
        ("led1.cathode", "GND", "The short leg (-) to ground closes the loop.")), "note": ""},
    "servo": {"pin": "D6", "parts": (("servo1", "servo"),), "build": (
        ("servo1.gnd", "GND", "Brown is ground."),
        ("servo1.vcc", "5V", "Red is power: 5 V for one small servo, unloaded."),
        ("servo1.sig", "D6", "Orange is the signal: the pulse from the Servo library that sets the angle.")),
        "note": "A loaded servo, or several, need their own 5 V supply, its GND joined to the board's."},
    "buzzer": {"pin": "D4", "parts": (("buzzer1", "buzzer"),), "build": (
        ("buzzer1.plus", "D4", "The + leg to the pin tone() drives."),
        ("buzzer1.minus", "GND", "The - leg to ground.")), "note": ""},
}
COURSE_CIRCUITS = {"esp32": CIRCUITS, "arduino": ARDUINO_CIRCUITS}


def _circ() -> dict:
    """The circuits of the course being judged."""
    return COURSE_CIRCUITS[_COURSE.get()]


def label(pin: str) -> str:
    """Pure logic. What's printed beside a board pin (on the board being judged): D2 for the ESP32's GPIO 2, VP, TX0,
    GND; an Arduino's as it's named."""
    return B().label(pin)


def _parts(lesson_id: str) -> dict:
    """{part id: kind} for a lab.
    In the course being judged."""
    return dict(_circ()[lesson_id]["parts"])


def words_for(lesson_id: str, terminal: str) -> str:
    """Pure logic. A terminal in words: "D2 (GPIO 2)", "3V3", "the LED's long leg (+)"."""
    if "." not in terminal:
        printed = label(terminal)
        return f"{printed} ({terminal})" if terminal.startswith("GPIO ") else printed
    part, pin = terminal.split(".", 1)
    name, pins = KINDS[_parts(lesson_id)[part]]
    what = dict(pins)[pin]
    return f"{what} of the {name}" if what.startswith(("one ", "the ")) else f"the {name}'s {what}"


@_in_course
def circuit_of(lesson_id: str) -> Optional[dict]:
    """The circuit page's data for a lab, or None for one without: the pin its sketch uses, its parts (with their
    terminals), the board's pins on each side (each with what's printed), the build steps and a note; and the board
    it's drawn on ({id, name})."""
    circuit = _circ().get(lesson_id)
    if circuit is None:
        return None
    parts = [{"id": pid, "kind": kind, "name": KINDS[kind][0],
              "pins": [{"id": f"{pid}.{t}", "name": n} for t, n in KINDS[kind][1]]} for pid, kind in circuit["parts"]]
    side = lambda pins: [{"id": p, "label": label(p)} for p in pins]  # noqa: E731
    return {"pin": circuit["pin"], "parts": parts, "left": side(B().left), "right": side(B().right),
            "board": {"id": B().id, "name": B().name, "label": B().short.replace("the ", "").upper()},
            "steps": [{"n": i, "a": a, "b": b, "words": f"{words_for(lesson_id, a)} to {words_for(lesson_id, b)}",
                       "why": why} for i, (a, b, why) in enumerate(circuit["build"], 1)],
            "note": circuit["note"]}


@_in_course
def terminals(lesson_id: str) -> set:
    """Every terminal a wire may join in a lab: its board family's pins and its parts' terminals."""
    return set(_boards.FAMILY_PINS[B().family]) | {f"{pid}.{t}" for pid, kind in _circ()[lesson_id]["parts"]
                                                   for t, _ in KINDS[kind][1]}


@_in_course
def clean_wires(lesson_id: str, wires) -> list:
    """Pure logic. His wires as (a, b) pairs, each joining two different terminals of the lab. ValueError for a lab
    without a circuit or a terminal it hasn't.
    In the course given: its board family's pins."""
    if lesson_id not in _circ():
        raise ValueError("There's no lab by that name.")
    known = terminals(lesson_id)
    out = []
    for wire in wires or ():
        a, b = (str(x).strip() for x in wire)
        for t in (a, b):
            if t not in known:
                raise ValueError(f"{t} isn't on the board or a part in this lab.")
        if a != b:
            out.append((a, b))
    return out


class _Nets:
    """Terminals joined by wires into nets (union-find); the board's two GND pins are one net."""

    def __init__(self, wires):
        """Joins each wire's ends."""
        self.parent: dict = {}
        self.union("GND", "GND 2")
        for a, b in wires:
            self.union(a, b)

    def find(self, x: str) -> str:
        """The net a terminal is on (its root)."""
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        """Puts two terminals on one net."""
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb

    def same(self, a: str, b: str) -> bool:
        """Whether two terminals are on one net."""
        return self.find(a) == self.find(b)

    def rail(self, terminal: str) -> Optional[str]:
        """The rail (a supply of the board, or GND) a terminal's net is on, or None (a short between rails names the
        first)."""
        return next((r for r in B().supplies + ("GND",) if self.same(terminal, r)), None)

    def pins_on(self, terminal: str) -> list:
        """The board's signal pins on a terminal's net."""
        root = self.find(terminal)
        return [p for p in B().signals if self.find(p) == root]


def _reach(nets: _Nets, start: str, resistors: list) -> dict:
    """{net: the fewest resistors on the way} reachable from a terminal's net through the resistors."""
    best = {nets.find(start): 0}
    frontier = [nets.find(start)]
    while frontier:
        nxt = []
        for net in frontier:
            for r in resistors:
                a, b = nets.find(f"{r}.a"), nets.find(f"{r}.b")
                for x, y in ((a, b), (b, a)):
                    if x == net and y not in best:
                        best[y] = best[net] + 1
                        nxt.append(y)
        frontier = nxt
    return best


def _led(nets: _Nets, part: str, pin: str, resistors: list, touched: set, say: Callable) -> str:
    """An LED's state from its loop: lit, overdriven (no resistor), backwards, on (to 3V3, not the pin) or off.
    An LED straight across a rail with no resistor is overdriven, like one on the pin.
    The pins and rails are the board's."""
    anode, cathode = f"{part}.anode", f"{part}.cathode"
    if nets.same(anode, cathode):
        say("warn", "The LED's two legs are joined: the current goes around it, so it stays dark.")
        return "off"
    to_a, to_c = _reach(nets, anode, resistors), _reach(nets, cathode, resistors)
    ground = nets.find("GND")
    gpios = list(B().signals)
    forward = [(q, to_a[nets.find(q)] + to_c[ground]) for q in gpios if nets.find(q) in to_a and ground in to_c]
    backward = [q for q in gpios if nets.find(q) in to_c and ground in to_a]
    mine = [n for q, n in forward if q == pin]
    if mine:
        if min(mine) == 0:
            say("warn", f"There's no resistor in the LED's loop: it lights, too bright, drawing more current than "
                        f"{label(pin)} or the LED should take. Put the 220 ohm resistor in series.")
            return "overdriven"
        return "lit"
    if forward:
        say("warn", f"The LED is on {label(forward[0][0])}, but the sketch drives {label(pin)} ({pin}): it stays dark.")
        return "off"
    if pin in backward:
        say("warn", "The LED is in backwards: its long leg (+) goes toward the pin, the short leg (-) toward GND. The "
                    "serial monitor still counts, but the LED stays dark.")
        return "backwards"
    for rail_name in B().supplies:
        rail_net = nets.find(rail_name)
        if rail_net in to_a and ground in to_c:
            if to_a[rail_net] + to_c[ground] == 0:
                say("warn", f"The LED goes straight from {rail_name} to GND with no resistor: it takes far more "
                            "current than it should and burns out. Put the 220 ohm resistor in series.")
                return "overdriven"
            say("note", f"The LED runs from {rail_name}, not the pin: it's on all the time, whatever the sketch does.")
            return "on"
    if touched & {anode, cathode} or any(t.startswith(r + ".") for r in resistors for t in touched):
        say("warn", f"The LED isn't in a loop from {label(pin)} to GND yet.")
    return "off"


def _pot(nets: _Nets, part: str, pin: str, say: Callable) -> dict:
    """A pot's state: ok (and reversed), stuck at a value, or floating.
    Across the board's logic rail (3V3 on the ESP32, 5V on an Arduino), read on its own ADC."""
    ends = (nets.rail(f"{part}.end1"), nets.rail(f"{part}.end2"))
    wiper = nets.pins_on(f"{part}.wiper")
    logic, top = B().logic_rail, B().adc_max
    state = {"ok": False, "reversed": ends == ("GND", logic), "stuck": None, "floating": False}
    if "VIN" in ends:
        say("stop", ("5 V" if B().family == "esp32" else "VIN, up to 12 V from a wall supply,") + " on the pot: turned "
            f"up, its wiper reaches it, over {B().short}'s {B().logic_volts:g} V limit. Use {logic}.")
        return state
    if not wiper:
        say("warn", f"The wiper (the middle leg) isn't on {label(pin)} yet: that's the reading.")
        state["floating"] = True
        return state
    if pin not in wiper:
        say("warn", f"The wiper is on {label(wiper[0])}, but the sketch reads {label(pin)} ({pin}).")
        state["floating"] = True
        return state
    if sorted(e or "" for e in ends) == sorted([logic, "GND"]):
        state["ok"] = True
        return state
    if ends[0] and ends[0] == ends[1]:
        say("warn", f"Both outer legs are on {ends[0]}: the wiper reads the same wherever you turn it.")
        state["stuck"] = top if ends[0] != "GND" else 0
    elif logic in ends or "GND" in ends:
        say("warn", f"Each outer leg needs a rail, one {logic} and one GND: with one loose, the reading sits at one "
                    "end.")
        state["stuck"] = top if logic in ends else 0
    else:
        say("warn", f"The outer legs aren't on {logic} and GND yet: with nothing across it, the reading wanders.")
        state["floating"] = True
    return state


def _module(nets: _Nets, part: str, kind: str, signal: str, pin: str, say: Callable) -> bool:
    """A three-wire module (DHT22, soil sensor, relay): powered, grounded and its signal on the sketch's pin.
    An input-only pin is the board's own (core/boards.py).
    Power backwards is a stop: it can destroy the module."""
    name = KINDS[kind][0]
    power, ground, on = nets.rail(f"{part}.vcc"), nets.rail(f"{part}.gnd"), nets.pins_on(f"{part}.{signal}")
    ok = True
    if power == "GND" or ground in ("3V3", "VIN"):
        say("stop", f"The {name}'s power is backwards (VCC on {power or 'nothing'}, GND on {ground or 'nothing'}): it "
                    "can destroy it. VCC goes to 3V3, GND to GND.")
        return False
    if power not in ("3V3", "VIN"):
        say("warn", f"The {name}'s VCC isn't on 3V3 yet: it has no power.")
        ok = False
    elif power == "VIN" and kind == "dht22":
        say("warn", "On 5 V the DHT22's DATA pulls up to 5 V, more than an ESP32 pin should take: use 3V3.")
    elif power == "VIN" and kind == "soil":
        say("warn", "On 5 V some soil sensors put out more than 3.3 V when dry, over what the ESP32 can read: use 3V3.")
    elif power == "VIN":
        say("note", "VIN is right if your relay module needs 5 V; its IN still takes the 3.3 V signal.")
    if ground != "GND":
        say("warn", f"The {name}'s GND isn't on ground: without a shared ground there's no signal.")
        ok = False
    what = dict(KINDS[kind][1])[signal]
    if not on:
        say("warn", f"The {name}'s {what} isn't on {label(pin)} yet.")
        return False
    if pin not in on:
        if kind in ("dht22", "relay") and on[0] in B().input_only:
            say("warn", f"{label(on[0])} is input-only (GPIO 34 to 39): the {name} needs a pin that can drive it.")
        else:
            say("warn", f"The {name}'s {what} is on {label(on[0])}, but the sketch uses {label(pin)} ({pin}).")
        return False
    return ok


def _by_build(nets: _Nets, part: str, kind: str, say: Callable) -> bool:
    """A part judged against its own build steps: each terminal on the rail or pin its step names (a button's,
    photoresistor's or resistor's legs either way round); the closer way round is the one said.
    Power backwards (a supply terminal on GND, or ground on a supply) is a stop."""
    name = KINDS[kind][0]
    steps = [(a, b) if a.startswith(part + ".") else (b, a) for a, b, _ in _circ()[_COURSE_LESSON.get()]["build"]
             if a.startswith(part + ".") or b.startswith(part + ".")]
    ways = [steps]
    if kind in SWAPS:
        x, y = (f"{part}.{t}" for t in SWAPS[kind])
        ways.append([({x: y, y: x}.get(t, t), target) for t, target in steps])
    best: Optional[list] = None
    for way in ways:
        found = []
        for terminal, target in way:
            what = dict(KINDS[kind][1])[terminal.split(".", 1)[1]]
            if target in B().supplies or target == "GND":
                actual = nets.rail(terminal)
                if actual == target:
                    continue
                if actual is None:
                    found.append(("warn", f"The {name}'s {what} isn't on {target} yet."))
                elif (target == "GND" and actual in B().supplies) or (target in B().supplies and actual == "GND"):
                    found.append(("stop", f"The {name}'s {what} is on {actual}: power backwards can destroy it. It "
                                          f"goes to {target}."))
                elif actual == "VIN":
                    found.append(("stop", f"The {name}'s {what} is on VIN: from a wall supply that's up to 12 V, too "
                                          f"much for it. Use {target}."))
                elif target == "5V" and actual == "3V3":
                    found.append(("warn", f"The {name}'s {what} is on 3V3: it needs 5V to work reliably."))
                else:
                    found.append(("warn", f"The {name}'s {what} is on {actual}: it goes to {target}."))
            else:
                on = nets.pins_on(terminal)
                if not on:
                    found.append(("warn", f"The {name}'s {what} isn't on {label(target)} yet."))
                elif target not in on:
                    found.append(("warn", f"The {name}'s {what} is on {label(on[0])}, but the sketch uses "
                                          f"{label(target)}."))
        if best is None or len(found) < len(best):
            best = found
    for level, text in best or []:
        say(level, text)
    return not best


_COURSE_LESSON = ContextVar("lab_lesson", default="")


@_in_course
def analyse(lesson_id: str, wires) -> dict:
    """Pure logic. His circuit judged (see the module's opening): {ok, problems [{level, text}], state {part: ...,
    "reset": EN held low, "short": a rail shorted}}. ValueError for a lab or terminal it hasn't.
    A GPIO wired to VIN (5 V) is a stop: it can damage the chip.
    On any board (`course`, `board_id`): its supplies, reset pin, serial pins and limits."""
    wires = clean_wires(lesson_id, wires)
    circuit = _circ()[lesson_id]
    nets = _Nets(wires)
    lesson_token = _COURSE_LESSON.set(lesson_id)
    problems: list = []

    def say(level: str, text: str) -> None:
        """One problem, once."""
        if not any(p["text"] == text for p in problems):
            problems.append({"level": level, "text": text})

    touched = {t for w in wires for t in w}
    state: dict = {"reset": False, "short": False}
    for supply in B().supplies:
        if nets.same(supply, "GND"):
            say("stop", f"{supply} is wired straight to GND: a short. A real board browns out and its regulator heats; "
                        "pull that wire.")
            state["short"] = True
    supplies = B().supplies
    for i, a in enumerate(supplies):
        for b in supplies[i + 1:]:
            if nets.same(a, b):
                say("stop", f"{a} and {b} are joined: two supplies at different voltages, pushing one into the other. "
                            "Pull that wire.")
                state["short"] = True
    reset = "EN" if B().family == "esp32" else "RST"
    if nets.same(reset, "GND"):
        say("stop", f"{reset} to GND holds the board in reset: nothing runs until it's free.")
        state["reset"] = True
    pin = circuit["pin"]
    drives = any(kind in ("led", "relay", "servo", "buzzer") for _, kind in circuit["parts"])
    for gpio in [p for p in B().signals if p in touched]:
        rail = nets.rail(gpio)
        if rail == "VIN":
            vin = "5 V" if B().family == "esp32" else "up to 12 V from a wall supply"
            say("stop", f"{label(gpio)} is wired to VIN, {vin}: over {B().short}'s {B().logic_volts:g} V limit, which "
                        "can damage the chip. Pull that wire.")
            state["short"] = True
        elif rail and gpio == pin and drives:
            say("stop", f"{label(gpio)} is tied straight to {rail}: when the sketch drives it the other way, it "
                        "shorts through the pin.")
            state["short"] = True
        elif rail:
            say("warn", f"{label(gpio)} is tied straight to {rail}: it reads "
                        f"{'0' if rail == 'GND' else B().adc_max} and nothing else.")
        if gpio in B().serial:
            say("warn", f"{label(gpio)} carries the USB serial: anything on it garbles the monitor and can block "
                        "uploads. Leave those two pins free.")
        others = [p for p in nets.pins_on(gpio) if p != gpio]
        if others and gpio < others[0]:
            say("warn", f"{label(gpio)} and {label(others[0])} are joined: two pins on one wire fight each other.")
    resistors = [pid for pid, kind in circuit["parts"] if kind == "resistor"]
    for part, kind in circuit["parts"]:
        if kind == "led":
            state[part] = _led(nets, part, pin, resistors, touched, say)
        elif kind == "pot":
            state[part] = _pot(nets, part, pin, say)
        elif kind == "dht22":
            state[part] = _module(nets, part, kind, "data", pin, say)
        elif kind == "soil":
            state[part] = _module(nets, part, kind, "aout", pin, say)
        elif kind == "relay":
            state[part] = _module(nets, part, kind, "in", pin, say)
        elif kind not in ("resistor",):
            state[part] = _by_build(nets, part, kind, say)
    _COURSE_LESSON.reset(lesson_token)
    return {"ok": not any(p["level"] in ("stop", "warn") for p in problems), "problems": problems, "state": state}


@_in_course
def build_progress(lesson_id: str, wires) -> dict:
    """Pure logic. The lab's build against his wires: {steps [{n, a, b, words, why, done}], next (the first step not
    done, or None), done (all of them)}. A resistor's or a pot's two ends count either way round.
    In the course given (`course`)."""
    circuit = circuit_of(lesson_id)
    if circuit is None:
        raise ValueError("There's no lab by that name.")
    nets = _Nets(clean_wires(lesson_id, wires))
    flips = [(pid, SWAPS[kind]) for pid, kind in _circ()[lesson_id]["parts"] if kind in SWAPS]
    best: list = []
    for mask in range(2 ** len(flips)):
        swap = {}
        for i, (pid, (x, y)) in enumerate(flips):
            if mask >> i & 1:
                swap.update({f"{pid}.{x}": f"{pid}.{y}", f"{pid}.{y}": f"{pid}.{x}"})
        done = [nets.same(swap.get(s["a"], s["a"]), swap.get(s["b"], s["b"])) for s in circuit["steps"]]
        if sum(done) > sum(best) or not best:
            best = done
    steps = [dict(s, done=d) for s, d in zip(circuit["steps"], best)]
    following = next((s["n"] for s in steps if not s["done"]), None)
    return {"steps": steps, "next": following, "done": bool(steps) and following is None}


@_in_course
def build_step(lesson_id: str, n: int, fresh: bool = True) -> str:
    """Pure logic. Step n of a lab's build as MIA says it (the parts first, starting fresh at step 1), or that it's
    built."""
    circuit = circuit_of(lesson_id)
    steps = circuit["steps"] if circuit else []
    if not steps:
        return ((circuit or {}).get("note") or "This lab has nothing to wire.") + " Say \"flash the " + lesson_id + \
            " lab\" when you're ready."
    if n > len(steps):
        return (f"That's the whole {lesson_id} circuit: {len(steps)} wires. Try it on the course page's simulator, "
                f"or say \"flash the {lesson_id} lab\" to run it on your board.")
    step = steps[n - 1]
    first = ""
    if n == 1 and fresh:
        names = " and ".join(p["name"] for p in circuit["parts"])
        first = f"Building the {lesson_id} lab: you'll need the {names} and {len(steps)} jumper wires. "
    tail = " Say \"next step\" when it's in." if n < len(steps) else " Say \"next step\" when it's in, and that's all."
    return f"{first}Step {n} of {len(steps)}: {step['words']}. Why: {step['why']}{tail}"


def _where(words: str, at: Optional[dict], lesson_id: str) -> tuple:
    """Pure logic. (the step his words ask for, whether it's a fresh start): step N; next (or done, it's in); back;
    again; else the first, fresh (as is a lab he isn't on)."""
    said = " " + re.sub(r"[^\w' ]+", " ", str(words or "").lower().replace("\u2019", "'")) + " "
    current = int(at["step"]) if at and at.get("lesson") == lesson_id else 0
    number = re.search(r"\bstep (\d+)\b", said)
    if number:
        return max(1, int(number.group(1))), False
    if not current:
        return 1, True
    if any(w in said for w in (" back ", " previous ", " last step ", " go back")):
        return max(1, current - 1), False
    if any(w in said for w in (" again ", " repeat ", " say that ", " what was ")):
        return current, False
    if any(w in said for w in (" next ", " done ", " it's in ", " its in ", " got it ", " ok ", " okay ", " then ")):
        return current + 1, False
    return 1, True


def _build_tool(context, arguments: dict) -> str:
    """Tool build_along: one step of a lab's build, where he is kept on his path (so "next step" follows), on the
    course his words or his build so far mean (core/esp32_lab.course_in)."""
    from core import paths
    from core.esp32_lab import course_in, lesson_for

    book = getattr(context, "paths", None)
    if book is None:
        return "Learning paths aren't on this MIA."
    words = str(arguments.get("lab", "") or "") + " " + str(arguments.get("question", "") or "")
    course = course_in(context, words, building=True)
    program = paths.program_of(context, course)
    at = book.build_at(program.id) if book.path(program.id) is not None else None
    named = any(re.search(rf"\b{re.escape(lesson.id)}\b", words.lower()) or lesson.title.lower() in words.lower()
                for stage in program.stages for lesson in stage.lessons)
    lesson = lesson_for(context, words, course=course) if named or not at else at["lesson"]
    if lesson not in COURSE_CIRCUITS[course]:
        return "That lab has nothing to build."
    step, fresh = _where(words if not named or (at and at.get("lesson") == lesson) else "", at, lesson)
    step = min(step, len(COURSE_CIRCUITS[course][lesson]["build"]) + 1)
    if book.path(program.id) is not None:
        book.set_build(program, lesson, step)
    return build_step(lesson, step, fresh, course=course)


_BUILD_VERB = re.compile(r"\b(build|building|wire|wiring|hook up|hooking up|connect|connecting|put together)\b")
_STEP_WORD = re.compile(r"\b(next|what's next|whats next|go back|back|previous|repeat|again|say that|done|it's in|"
                        r"its in|got it|step \d+)\b")
_LAST_STEP = re.compile(r"^(Building the \w+ lab:|Step \d+ of \d+:)")
_FILLER = re.compile(r"\b(ok|okay|wait|so|then|and|the|it|that|now|alright|cool|great|yes|yeah|yep|please|step|one|"
                     r"what|is|to|me|go|on|with|hold|hang|sorry|oops|whoops|all|right)\b")


def _last_was_a_step(conversation) -> bool:
    """Whether MIA's last message in this conversation was a build step."""
    for message in reversed(list(getattr(conversation, "messages", None) or [])):
        if getattr(message, "role", "") == "assistant":
            return bool(_LAST_STEP.match(str(getattr(message, "content", "") or "")))
    return False


def reply(context, conversation, text: str) -> Optional[str]:
    """Building along, in code, before the question plans (as a trade job's walk-through is): a build verb with a
    lab named as one starts it ("walk me through building the pot lab", "how do I wire the relay lab?"; never "the
    soil moisture sensor in the greenhouse"), and right after a
    step, "next step", "go back", "repeat that" or "done" moves it, when nothing else is said ("what's my next step on
    the shed?" stays the plans'). None when the words aren't for it.
    A lab of either board course named as one starts it."""
    from core import paths

    said = " ".join(str(text or "").lower().replace("’", "'").split())
    if getattr(context, "paths", None) is None:
        return None
    from core.esp32_lab import next_lab_reply

    upcoming = next_lab_reply(context, said)  # "what's my next Arduino lesson?"
    if upcoming is not None:
        return upcoming
    names_a_lab = any(re.search(rf"\b(?:{re.escape(lesson.id)}|{re.escape(lesson.title.lower())}) lab\b", said)
                      for course, circuits in COURSE_CIRCUITS.items()
                      for stage in paths.program_of(context, course).stages for lesson in stage.lessons
                      if lesson.id in circuits)
    if names_a_lab and _BUILD_VERB.search(said) and not re.search(r"\b(flash|upload|simulat\w*|print|check)\b", said):
        return _build_tool(context, {"question": said})
    left = _FILLER.sub(" ", _STEP_WORD.sub(" ", re.sub(r"[^\w' ]+", " ", said))).split()
    if _STEP_WORD.search(said) and not left and _last_was_a_step(conversation):
        return _build_tool(context, {"question": said})
    return None


def _simulate_tool(context, arguments: dict) -> str:
    """Tool simulate_lab: the lab's own circuit run in the simulator, what it prints and whether the check would pass.
    On the course his words mean (core/esp32_lab.course_in)."""
    from core.esp32_lab import course_in, lesson_for

    words = str(arguments.get("lab", "") or "") + " " + str(arguments.get("question", "") or "")
    course = course_in(context, words)
    lesson = lesson_for(context, words, course=course)
    if lesson not in COURSE_CIRCUITS[course]:
        return "That lab isn't in the simulator."
    return simulate(lesson, course=course)["said"]


def register_sim_tools(registry) -> None:
    """Registers build_along and simulate_lab (called from core/esp32_lab.register_esp32_lab_actions; "in the
    simulator" isn't simulate_lab's, so "what parts can I wire in the simulator?" stays part_specs'); simulate_lab
    takes only his words (the lab is read from them), so code answers "what will the pot lab print?" itself
    (direct_lookup: the model, with a build in the conversation, answered from memory).
    Both take the Arduino course's labs too."""
    from core.assistant_actions import AssistantAction

    lab = {"type": "string", "description": "which lab (blink, hello, button, pot, dht, soil, fade, relay, wifi, web, "
                                            "sleep; on the Arduino light, distance, servo, buzzer), only if he named "
                                            "one"}
    words = {"type": "string", "description": "his words"}
    registry.register(AssistantAction(
        name="build_along", domain="learning",
        description="Walk him through wiring an ESP32 or Arduino lab's circuit one step at a time (which wire, and "
                    "why), and "
                    "the next step when he says it's in: \"walk me through building the pot lab\", \"next step\".",
        parameters={"type": "object", "properties": {"lab": lab, "question": words}, "required": []},
        handler=_build_tool, trigger_phrases=("walk me through building", "walk me through wiring", "help me wire",
                                             "build it with me", "build along", "how do i wire", "wire up the",
                                             "next wiring step", "repeat that step", "previous step"),
    ))
    registry.register(AssistantAction(
        name="simulate_lab", domain="learning",
        description="What an ESP32 or Arduino lab will or should print, and what to expect, from MIA's simulator "
                    "with no board "
                    "needed: \"what will the dht lab print?\", \"simulate the blink lab\". Only the real board passes "
                    "a check.",
        parameters={"type": "object", "properties": {"question": words}, "required": []}, prompt_arg="question",
        handler=_simulate_tool, trigger_phrases=("simulate the", "simulate my", "lab print",
                                                "lab output", "board print", "board say"),
    ))


@_in_course
def reference_wires(lesson_id: str) -> list:
    """The lab's own circuit as wires (its build), for "what will it print?".
    In the course given (`course`)."""
    return [(a, b) for a, b, _ in _circ()[lesson_id]["build"]]


def _series(value, default: float) -> Callable:
    """An input over time: a number, or [[t, v], ...] joined in straight lines (held before the first and after the
    last)."""
    if value is None or value == "":
        return lambda t: default
    if isinstance(value, (int, float, str)):
        number = float(value)
        return lambda t: number
    points = sorted((float(t), float(v)) for t, v in value)
    if not points:
        return lambda t: default

    def at(t: float) -> float:
        """The input at t seconds."""
        if t <= points[0][0]:
            return points[0][1]
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            if t <= t1:
                return v0 + (v1 - v0) * ((t - t0) / (t1 - t0) if t1 > t0 else 1)
        return points[-1][1]
    return at


def _clamp(x: float) -> int:
    """A 12-bit ADC reading.
    On the board's own ADC (4095 on the ESP32, 1023 on an Arduino)."""
    return max(0, min(B().adc_max, int(round(x))))


def _run_arduino(lesson_id: str, state: dict, inputs: dict, seconds: float, rng: random.Random) -> Optional[tuple]:
    """The Arduino course's labs that run differently from the ESP32's (core/arduino_path.py's sketches); None for
    one they share (blink, hello, pot, fade)."""
    lines, outs = [], []
    if lesson_id == "button":
        last, count = -1.0, 0
        for t in sorted(float(x) for x in inputs.get("presses") or ()):
            if state.get("button1") and 0 <= t <= seconds and t - last > 0.05:
                count += 1
                lines.append((t, f"MIA BUTTON {count}"))
                last = t
    elif lesson_id == "light":
        light = _series(inputs.get("light"), 0.5)
        t = 0.0
        while t <= seconds:
            if state.get("ldr1") and state.get("r10k1"):
                ohms = 1000 * 100 ** (1 - max(0.0, min(1.0, light(t))))  # about 100k in the dark to 1k in bright light
                lines.append((t, f"MIA LIGHT {_clamp(1023 * 10000 / (ohms + 10000) + rng.uniform(-3, 3))}"))
            else:
                lines.append((t, f"MIA LIGHT {rng.randint(0, 1023)}"))
            t += 0.5
    elif lesson_id == "distance":
        far = _series(inputs.get("distance"), 30.0)
        t = 0.0
        while t <= seconds:
            d = far(t)
            if state.get("sonar1") and 2 <= d <= 400:
                lines.append((t, f"MIA DIST {int(d + rng.uniform(-0.5, 0.5))}"))
            else:
                lines.append((t, "MIA DIST_NONE"))
            t += 0.3
    elif lesson_id == "dht":
        temp, humidity = _series(inputs.get("temp"), 21.5), _series(inputs.get("humidity"), 45.0)
        t = 2.0
        while t <= seconds:
            if state.get("dht1"):
                lines.append((t, f"MIA TEMP {temp(t) + rng.uniform(-0.05, 0.05):.1f}"))
                lines.append((t, f"MIA HUMIDITY {humidity(t) + rng.uniform(-0.2, 0.2):.1f}"))
            else:
                lines.append((t, "MIA SENSOR_ERROR"))
            t += 2.0
    elif lesson_id == "servo":
        angles = list(range(0, 181, 30)) + list(range(180, -1, -30))
        t, i = 0.0, 0
        while t <= seconds:
            angle = angles[i % len(angles)]
            lines.append((t, f"MIA SERVO {angle}"))
            outs.append((t, {"box": bool(state.get("servo1")), "angle": angle if state.get("servo1") else None}))
            t, i = t + 0.5, i + 1
    elif lesson_id == "buzzer":
        t, beeps = 0.0, 0
        while t <= seconds:
            beeps += 1
            lines.append((t, f"MIA BEEP {beeps}"))
            outs += [(t, {"box": bool(state.get("buzzer1"))}), (t + 0.2, {"box": False})]
            t += 1.0
    else:
        return None
    return [x for x in lines if x[0] <= seconds], [x for x in outs if x[0] <= seconds]


def _run(lesson_id: str, state: dict, inputs: dict, seconds: float, rng: random.Random) -> tuple:
    """What the lab's sketch does in `seconds`: ([(t, line)], [(t, {output: value})]).
    The hello lab says MIA HELLO with its seconds every loop, as its sketch does. The Arduino course's own labs run
    in `_run_arduino`; the ones it shares with the ESP32's run here, on its board's ADC."""
    if _COURSE.get() == "arduino":
        ran = _run_arduino(lesson_id, state, inputs, seconds, rng)
        if ran is not None:
            return ran
    lines, outs = [], []
    led = state.get("led1")
    glow = 1.0 if led in ("lit", "overdriven") else 0.0
    if lesson_id == "blink":
        k = 1
        while k <= seconds:
            outs += [(k - 1.0, {"onboard": 1.0, "led": glow if led != "on" else 1.0}),
                     (k - 0.5, {"onboard": 0.0, "led": 0.0 if led != "on" else 1.0})]
            lines.append((float(k), f"MIA BLINK {k}"))
            k += 1
    elif lesson_id == "hello":
        t = 0.5
        while t <= seconds:
            lines.append((t, f"MIA HELLO {int(t)}"))
            t += 2.0
    elif lesson_id == "button":
        last, count = -1.0, 0
        for t in sorted(float(x) for x in inputs.get("presses") or ()):
            if 0 <= t <= seconds and t - last > 0.05:
                count += 1
                lines.append((t, f"MIA BUTTON {count}"))
                last = t
    elif lesson_id == "pot":
        pot, position = state.get("pot1") or {}, _series(inputs.get("pot"), 0.5)
        t = 0.0
        while t <= seconds:
            if pot.get("ok"):
                x = max(0.0, min(1.0, position(t)))
                value = _clamp((1 - x if pot.get("reversed") else x) * B().adc_max + rng.uniform(-6, 6))
            elif pot.get("stuck") is not None:
                value = _clamp(pot["stuck"] + rng.uniform(-6, 6))
            else:
                value = rng.randint(0, B().adc_max)
            lines.append((t, f"MIA ADC {value}"))
            t += 0.25
    elif lesson_id == "dht":
        temp, humidity = _series(inputs.get("temp"), 21.5), _series(inputs.get("humidity"), 45.0)
        t = 2.5
        while t <= seconds:
            if state.get("dht1"):
                lines.append((t, f"MIA TEMP {temp(t) + rng.uniform(-0.05, 0.05):.1f}"))
                lines.append((t, f"MIA HUMIDITY {humidity(t) + rng.uniform(-0.2, 0.2):.1f}"))
            else:
                lines.append((t, "MIA SENSOR_ERROR"))
            t += 2.5
    elif lesson_id in ("soil", "sleep"):
        wet = _series(inputs.get("moisture"), 0.3)

        def soil(t: float) -> int:
            """The sensor's reading: about 3300 dry to 1400 wet, or noise when it isn't wired."""
            if state.get("soil1"):
                return _clamp(3300 - max(0.0, min(1.0, wet(t))) * 1900 + rng.uniform(-15, 15))
            return rng.randint(0, B().adc_max)
        if lesson_id == "soil":
            t = 0.0
            while t <= seconds:
                lines.append((t, f"MIA SOIL {soil(t)}"))
                t += 1.0
        else:
            t, wakes = 0.2, 0
            while t <= seconds:
                wakes += 1
                lines += [(t, f"MIA WAKE {wakes}"), (t, f"MIA SOIL {soil(t)}")]
                t += 10.2
    elif lesson_id == "fade":
        cycle, t, fades = 52 * 2 * 0.015, 0.0, 0
        while t + cycle <= seconds:
            for i in range(11):
                level = 1 - abs(i - 5) / 5
                outs.append((t + cycle * i / 10, {"onboard": level, "led": level * glow if led != "on" else 1.0}))
            fades += 1
            t += cycle
            lines.append((t, f"MIA FADE {fades}"))
    elif lesson_id == "relay":
        k = 0
        while 2.0 * k <= seconds:
            outs.append((2.0 * k, {"relay": bool(state.get("relay1")) and k % 2 == 0}))
            lines.append((2.0 * k, f"MIA RELAY {k + 1}"))
            k += 1
    elif lesson_id in ("wifi", "web"):
        if lesson_id == "wifi":
            lines += [(0.5, "MIA WIFI_WAITING"), (1.0, "MIA WIFI_WAITING")]
        lines.append((1.5, "MIA WIFI 192.168.1.50"))
        if lesson_id == "wifi":
            t = 1.5
            while t <= seconds:
                lines.append((t, f"MIA RSSI {-58 + rng.randint(-3, 3)}"))
                t += 5.0
        else:
            served = 0
            for t in sorted(float(x) for x in inputs.get("requests") or ()):
                if 1.5 <= t <= seconds:
                    served += 1
                    lines.append((t, f"MIA WEB {served}"))
    return [x for x in lines if x[0] <= seconds], [x for x in outs if x[0] <= seconds]


@_in_course
def simulate(lesson_id: str, wires=None, inputs: Optional[dict] = None, seconds: float = 10.0, seed: int = 0) -> dict:
    """Pure logic. Runs a lab in the simulator (see the module's opening) on his wires, or the lab's own circuit when
    none are given: {ok, problems, ran (False when a stop problem kept it from running), serial (the text), trace
    [{t, line}], outputs [{t, ...}], checks [{check, what, would_pass, how}], said}. The lab's own circuit with no
    inputs given runs as SHOW has it (the knob turned, BOOT pressed). Never a pass on his path.
    Each input's list is cut to 500 entries.
    On any board course (`course`, `board_id`): the Arduino's runs as its sketches do (ARDUINO_SHOW)."""
    from core.esp32_lab import checks_of
    from core.esp32_path import judge

    if lesson_id not in _circ():
        raise ValueError("There's no lab by that name.")
    shown = ""
    inputs = {k: (v[:500] if isinstance(v, list) else v) for k, v in dict(inputs or {}).items()}
    show = ARDUINO_SHOW if _COURSE.get() == "arduino" else SHOW
    if wires is None and not inputs and lesson_id in show:
        inputs, seconds, shown = show[lesson_id]
    seconds = max(1.0, min(60.0, float(seconds or 10.0)))
    found = analyse(lesson_id, reference_wires(lesson_id) if wires is None else wires)
    inputs = dict(inputs or {})
    stopped = [p["text"] for p in found["problems"] if p["level"] == "stop"]
    lines, outs = ([], []) if stopped else _run(lesson_id, found["state"], inputs, seconds, random.Random(seed))
    serial = "".join(line + "\n" for _, line in lines)
    checks = []
    for check in checks_of(lesson_id, course=_COURSE.get()):
        passed, _, how = judge(check, serial)
        checks.append({"check": check.id, "what": check.what, "would_pass": passed, "how": how})
    if stopped:
        said = "Stop: " + stopped[0]
    else:
        warns = [p["text"] for p in found["problems"] if p["level"] == "warn"]
        verdicts = "; ".join(f"\"{c['what']}\" would pass" if c["would_pass"] else f"\"{c['what']}\": not yet, {c['how']}"
                             for c in checks)
        opening = ("It runs, but: " + warns[0] + " " if warns else "Your circuit works. ") if wires is not None \
            else f"The {lesson_id} lab, wired as built{', ' + shown if shown else ''}, prints " + \
            ", ".join(line for _, line in lines[:4]) + (", and so on" if len(lines) > 4 else "") + ". "
        said = opening + (verdicts + "." if verdicts else "")
        said += " (In the simulator: only your real board passes the check.)"
    return {"ok": found["ok"], "problems": found["problems"], "ran": not stopped, "serial": serial,
            "trace": [{"t": round(t, 3), "line": line} for t, line in lines],
            "outputs": [dict(o, t=round(t, 3)) for t, o in outs], "checks": checks, "said": said.strip()}
