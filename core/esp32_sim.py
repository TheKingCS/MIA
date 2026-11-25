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
"""

from __future__ import annotations

import random
import re
from typing import Callable, Optional

BOARD_LEFT = ("EN", "GPIO 36", "GPIO 39", "GPIO 34", "GPIO 35", "GPIO 32", "GPIO 33", "GPIO 25", "GPIO 26", "GPIO 27",
              "GPIO 14", "GPIO 12", "GPIO 13", "GND", "VIN")
BOARD_RIGHT = ("GPIO 23", "GPIO 22", "GPIO 1", "GPIO 3", "GPIO 21", "GPIO 19", "GPIO 18", "GPIO 5", "GPIO 17",
               "GPIO 16", "GPIO 4", "GPIO 2", "GPIO 15", "GND 2", "3V3")
BOARD = BOARD_LEFT + BOARD_RIGHT
_PRINTED = {"GPIO 36": "VP", "GPIO 39": "VN", "GPIO 1": "TX0", "GPIO 3": "RX0", "GPIO 17": "TX2", "GPIO 16": "RX2",
            "GND 2": "GND"}
INPUT_ONLY = {34, 35, 36, 39}
SERIAL = {1, 3}
RAILS = ("3V3", "VIN", "GND")

# kind -> (its name, its terminals (id, what it is on the part))
KINDS = {
    "led": ("LED", (("anode", "long leg (+)"), ("cathode", "short leg (-)"))),
    "resistor": ("220 ohm resistor", (("a", "one end"), ("b", "the other end"))),
    "pot": ("10k potentiometer", (("end1", "one outer leg"), ("wiper", "middle leg (wiper)"),
                                  ("end2", "the other outer leg"))),
    "dht22": ("DHT22 module", (("vcc", "VCC (+)"), ("data", "DATA"), ("gnd", "GND (-)"))),
    "soil": ("soil moisture sensor", (("vcc", "VCC"), ("gnd", "GND"), ("aout", "AOUT"))),
    "relay": ("relay module", (("vcc", "VCC"), ("gnd", "GND"), ("in", "IN"))),
}
SWAPS = {"resistor": ("a", "b"), "pot": ("end1", "end2")}  # ends that work either way round

# For "what will it print?" (the lab's own circuit): the inputs that show it passing, how long, and what they are in
# words; and on the page, what to do in the simulator for the check.
SHOW = {
    "button": ({"presses": [1.0, 2.0, 3.0]}, 5.0, "with BOOT pressed three times"),
    "pot": ({"pot": [[0, 0], [5, 1]]}, 5.0, "with the knob turned end to end"),
    "soil": ({"moisture": [[0, 0], [3, 0], [4, 1]]}, 8.0, "dry, then into the cup of water"),
    "sleep": ({"moisture": [[0, 0], [31, 1]]}, 31.0, "for half a minute, the soil watered as it goes"),
    "web": ({"requests": [3.0]}, 5.0, "with one request from a browser"),
}
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


def label(pin: str) -> str:
    """Pure logic. What's printed beside a board pin: D2 for GPIO 2, VP, TX0, GND."""
    if pin in _PRINTED:
        return _PRINTED[pin]
    return "D" + pin[5:] if pin.startswith("GPIO ") else pin


def _gpio(terminal: str) -> Optional[int]:
    """A board pin's GPIO number, or None."""
    return int(terminal[5:]) if terminal.startswith("GPIO ") else None


def _parts(lesson_id: str) -> dict:
    """{part id: kind} for a lab."""
    return dict(CIRCUITS[lesson_id]["parts"])


def words_for(lesson_id: str, terminal: str) -> str:
    """Pure logic. A terminal in words: "D2 (GPIO 2)", "3V3", "the LED's long leg (+)"."""
    if "." not in terminal:
        printed = label(terminal)
        return f"{printed} ({terminal})" if terminal.startswith("GPIO ") else printed
    part, pin = terminal.split(".", 1)
    name, pins = KINDS[_parts(lesson_id)[part]]
    what = dict(pins)[pin]
    return f"{what} of the {name}" if what.startswith(("one ", "the ")) else f"the {name}'s {what}"


def circuit_of(lesson_id: str) -> Optional[dict]:
    """The circuit page's data for a lab, or None for one without: the pin its sketch uses, its parts (with their
    terminals), the board's pins on each side (each with what's printed), the build steps and a note."""
    circuit = CIRCUITS.get(lesson_id)
    if circuit is None:
        return None
    parts = [{"id": pid, "kind": kind, "name": KINDS[kind][0],
              "pins": [{"id": f"{pid}.{t}", "name": n} for t, n in KINDS[kind][1]]} for pid, kind in circuit["parts"]]
    side = lambda pins: [{"id": p, "label": label(p)} for p in pins]  # noqa: E731
    return {"pin": circuit["pin"], "parts": parts, "left": side(BOARD_LEFT), "right": side(BOARD_RIGHT),
            "steps": [{"n": i, "a": a, "b": b, "words": f"{words_for(lesson_id, a)} to {words_for(lesson_id, b)}",
                       "why": why} for i, (a, b, why) in enumerate(circuit["build"], 1)],
            "note": circuit["note"]}


def terminals(lesson_id: str) -> set:
    """Every terminal a wire may join in a lab: the board's pins and its parts' terminals."""
    return set(BOARD) | {f"{pid}.{t}" for pid, kind in CIRCUITS[lesson_id]["parts"] for t, _ in KINDS[kind][1]}


def clean_wires(lesson_id: str, wires) -> list:
    """Pure logic. His wires as (a, b) pairs, each joining two different terminals of the lab. ValueError for a lab
    without a circuit or a terminal it hasn't."""
    if lesson_id not in CIRCUITS:
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
        """The rail (3V3, VIN or GND) a terminal's net is on, or None (a short between rails names the first)."""
        return next((r for r in RAILS if self.same(terminal, r)), None)

    def pins_on(self, terminal: str) -> list:
        """The board's GPIO pins on a terminal's net."""
        root = self.find(terminal)
        return [p for p in BOARD if p.startswith("GPIO ") and self.find(p) == root]


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
    """An LED's state from its loop: lit, overdriven (no resistor), backwards, on (to 3V3, not the pin) or off."""
    anode, cathode = f"{part}.anode", f"{part}.cathode"
    if nets.same(anode, cathode):
        say("warn", "The LED's two legs are joined: the current goes around it, so it stays dark.")
        return "off"
    to_a, to_c = _reach(nets, anode, resistors), _reach(nets, cathode, resistors)
    ground, supply = nets.find("GND"), nets.find("3V3")
    gpios = [p for p in BOARD if p.startswith("GPIO ")]
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
    if supply in to_a and ground in to_c:
        say("note", "The LED runs from 3V3, not the pin: it's on all the time, whatever the sketch does.")
        return "on"
    if touched & {anode, cathode} or any(t.startswith(r + ".") for r in resistors for t in touched):
        say("warn", f"The LED isn't in a loop from {label(pin)} to GND yet.")
    return "off"


def _pot(nets: _Nets, part: str, pin: str, say: Callable) -> dict:
    """A pot's state: ok (and reversed), stuck at a value, or floating."""
    ends = (nets.rail(f"{part}.end1"), nets.rail(f"{part}.end2"))
    wiper = nets.pins_on(f"{part}.wiper")
    state = {"ok": False, "reversed": ends == ("GND", "3V3"), "stuck": None, "floating": False}
    if "VIN" in ends:
        say("stop", "5 V on the pot: turned up, its wiper reaches 5 V, over the ESP32's 3.3 V limit. Use 3V3.")
        return state
    if not wiper:
        say("warn", f"The wiper (the middle leg) isn't on {label(pin)} yet: that's the reading.")
        state["floating"] = True
        return state
    if pin not in wiper:
        say("warn", f"The wiper is on {label(wiper[0])}, but the sketch reads {label(pin)} ({pin}).")
        state["floating"] = True
        return state
    if sorted(e or "" for e in ends) == ["3V3", "GND"]:
        state["ok"] = True
        return state
    if ends[0] and ends[0] == ends[1]:
        say("warn", f"Both outer legs are on {ends[0]}: the wiper reads the same wherever you turn it.")
        state["stuck"] = 4095 if ends[0] == "3V3" else 0
    elif "3V3" in ends or "GND" in ends:
        say("warn", "Each outer leg needs a rail, one 3V3 and one GND: with one loose, the reading sits at one end.")
        state["stuck"] = 4095 if "3V3" in ends else 0
    else:
        say("warn", "The outer legs aren't on 3V3 and GND yet: with nothing across it, the reading wanders.")
        state["floating"] = True
    return state


def _module(nets: _Nets, part: str, kind: str, signal: str, pin: str, say: Callable) -> bool:
    """A three-wire module (DHT22, soil sensor, relay): powered, grounded and its signal on the sketch's pin."""
    name = KINDS[kind][0]
    power, ground, on = nets.rail(f"{part}.vcc"), nets.rail(f"{part}.gnd"), nets.pins_on(f"{part}.{signal}")
    ok = True
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
        number = _gpio(on[0])
        if kind in ("dht22", "relay") and number in INPUT_ONLY:
            say("warn", f"{label(on[0])} is input-only (GPIO 34 to 39): the {name} needs a pin that can drive it.")
        else:
            say("warn", f"The {name}'s {what} is on {label(on[0])}, but the sketch uses {label(pin)} ({pin}).")
        return False
    return ok


def analyse(lesson_id: str, wires) -> dict:
    """Pure logic. His circuit judged (see the module's opening): {ok, problems [{level, text}], state {part: ...,
    "reset": EN held low, "short": a rail shorted}}. ValueError for a lab or terminal it hasn't."""
    wires = clean_wires(lesson_id, wires)
    circuit = CIRCUITS[lesson_id]
    nets = _Nets(wires)
    problems: list = []

    def say(level: str, text: str) -> None:
        """One problem, once."""
        if not any(p["text"] == text for p in problems):
            problems.append({"level": level, "text": text})

    touched = {t for w in wires for t in w}
    state: dict = {"reset": False, "short": False}
    for supply in ("3V3", "VIN"):
        if nets.same(supply, "GND"):
            say("stop", f"{supply} is wired straight to GND: a short. A real board browns out and its regulator heats; "
                        "pull that wire.")
            state["short"] = True
    if nets.same("3V3", "VIN"):
        say("stop", "3V3 and VIN (5 V) are joined: that pushes 5 V into the 3.3 V side. Pull that wire.")
        state["short"] = True
    if nets.same("EN", "GND"):
        say("stop", "EN to GND holds the board in reset: nothing runs until it's free.")
        state["reset"] = True
    pin = circuit["pin"]
    drives = any(kind in ("led", "relay") for _, kind in circuit["parts"])
    for gpio in sorted({t for t in touched if t.startswith("GPIO ")}, key=lambda p: int(p[5:])):
        rail = nets.rail(gpio)
        if rail and gpio == pin and drives:
            say("stop", f"{label(gpio)} is tied straight to {rail}: when the sketch drives it the other way, it "
                        "shorts through the pin.")
            state["short"] = True
        elif rail:
            say("warn", f"{label(gpio)} is tied straight to {rail}: it reads {'0' if rail == 'GND' else '4095'} and "
                        "nothing else.")
        if _gpio(gpio) in SERIAL:
            say("warn", f"{label(gpio)} carries the USB serial: anything on it garbles the monitor and can block "
                        "uploads. Leave TX0 and RX0 free.")
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
    return {"ok": not any(p["level"] in ("stop", "warn") for p in problems), "problems": problems, "state": state}


def build_progress(lesson_id: str, wires) -> dict:
    """Pure logic. The lab's build against his wires: {steps [{n, a, b, words, why, done}], next (the first step not
    done, or None), done (all of them)}. A resistor's or a pot's two ends count either way round."""
    circuit = circuit_of(lesson_id)
    if circuit is None:
        raise ValueError("There's no lab by that name.")
    nets = _Nets(clean_wires(lesson_id, wires))
    flips = [(pid, SWAPS[kind]) for pid, kind in CIRCUITS[lesson_id]["parts"] if kind in SWAPS]
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
    """Tool build_along: one step of a lab's build, where he is kept on his path (so "next step" follows)."""
    from core.esp32_lab import lesson_for
    from core.esp32_path import PROGRAM

    book = getattr(context, "paths", None)
    if book is None:
        return "Learning paths aren't on this MIA."
    words = str(arguments.get("lab", "") or "") + " " + str(arguments.get("question", "") or "")
    at = book.build_at(PROGRAM.id) if book.path(PROGRAM.id) is not None else None
    named = any(lesson.id in words.lower() or lesson.title.lower() in words.lower()
                for stage in PROGRAM.stages for lesson in stage.lessons)
    lesson = lesson_for(context, words) if named or not at else at["lesson"]
    if lesson not in CIRCUITS:
        return "That lab has nothing to build."
    step, fresh = _where(words if not named or (at and at.get("lesson") == lesson) else "", at, lesson)
    step = min(step, len(CIRCUITS[lesson]["build"]) + 1)
    if book.path(PROGRAM.id) is not None:
        book.set_build(PROGRAM, lesson, step)
    return build_step(lesson, step, fresh)


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
    lab named starts it ("walk me through building the pot lab", "how do I wire the relay lab?"), and right after a
    step, "next step", "go back", "repeat that" or "done" moves it, when nothing else is said ("what's my next step on
    the shed?" stays the plans'). None when the words aren't for it."""
    from core.esp32_path import PROGRAM

    said = " ".join(str(text or "").lower().replace("’", "'").split())
    if getattr(context, "paths", None) is None:
        return None
    names_a_lab = any(re.search(rf"\b{lesson.id} lab\b", said) or lesson.title.lower() in said
                      for stage in PROGRAM.stages for lesson in stage.lessons if lesson.id in CIRCUITS)
    if names_a_lab and _BUILD_VERB.search(said) and not re.search(r"\b(flash|upload|simulat\w*|print|check)\b", said):
        return _build_tool(context, {"question": said})
    left = _FILLER.sub(" ", _STEP_WORD.sub(" ", re.sub(r"[^\w' ]+", " ", said))).split()
    if _STEP_WORD.search(said) and not left and _last_was_a_step(conversation):
        return _build_tool(context, {"question": said})
    return None


def _simulate_tool(context, arguments: dict) -> str:
    """Tool simulate_lab: the lab's own circuit run in the simulator, what it prints and whether the check would pass."""
    from core.esp32_lab import lesson_for

    lesson = lesson_for(context, str(arguments.get("lab", "") or "") + " " + str(arguments.get("question", "") or ""))
    if lesson not in CIRCUITS:
        return "That lab isn't in the simulator."
    return simulate(lesson)["said"]


def register_sim_tools(registry) -> None:
    """Registers build_along and simulate_lab (called from core/esp32_lab.register_esp32_lab_actions); simulate_lab
    takes only his words (the lab is read from them), so code answers "what will the pot lab print?" itself
    (direct_lookup: the model, with a build in the conversation, answered from memory)."""
    from core.assistant_actions import AssistantAction

    lab = {"type": "string", "description": "which lab (blink, hello, button, pot, dht, soil, fade, relay, wifi, web, "
                                            "sleep), only if he named one"}
    words = {"type": "string", "description": "his words"}
    registry.register(AssistantAction(
        name="build_along", domain="learning",
        description="Walk him through wiring an ESP32 lab's circuit one step at a time (which wire, and why), and "
                    "the next step when he says it's in: \"walk me through building the pot lab\", \"next step\".",
        parameters={"type": "object", "properties": {"lab": lab, "question": words}, "required": []},
        handler=_build_tool, trigger_phrases=("walk me through building", "walk me through wiring", "help me wire",
                                             "build it with me", "build along", "how do i wire", "wire up the",
                                             "next wiring step", "repeat that step", "previous step"),
    ))
    registry.register(AssistantAction(
        name="simulate_lab", domain="learning",
        description="What an ESP32 lab will or should print, and what to expect, from MIA's simulator with no board "
                    "needed: \"what will the dht lab print?\", \"simulate the blink lab\". Only the real board passes "
                    "a check.",
        parameters={"type": "object", "properties": {"question": words}, "required": []}, prompt_arg="question",
        handler=_simulate_tool, trigger_phrases=("simulate the", "simulate my", "in the simulator", "lab print",
                                                "lab output", "board print", "board say"),
    ))


def reference_wires(lesson_id: str) -> list:
    """The lab's own circuit as wires (its build), for "what will it print?"."""
    return [(a, b) for a, b, _ in CIRCUITS[lesson_id]["build"]]


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
    """A 12-bit ADC reading."""
    return max(0, min(4095, int(round(x))))


def _run(lesson_id: str, state: dict, inputs: dict, seconds: float, rng: random.Random) -> tuple:
    """What the lab's sketch does in `seconds`: ([(t, line)], [(t, {output: value})])."""
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
        lines.append((0.5, "MIA HELLO"))
        t = 0.5
        while t <= seconds:
            lines.append((t, f"MIA UPTIME {int(t)}"))
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
                value = _clamp((1 - x if pot.get("reversed") else x) * 4095 + rng.uniform(-6, 6))
            elif pot.get("stuck") is not None:
                value = _clamp(pot["stuck"] + rng.uniform(-6, 6))
            else:
                value = rng.randint(0, 4095)
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
            return rng.randint(0, 4095)
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


def simulate(lesson_id: str, wires=None, inputs: Optional[dict] = None, seconds: float = 10.0, seed: int = 0) -> dict:
    """Pure logic. Runs a lab in the simulator (see the module's opening) on his wires, or the lab's own circuit when
    none are given: {ok, problems, ran (False when a stop problem kept it from running), serial (the text), trace
    [{t, line}], outputs [{t, ...}], checks [{check, what, would_pass, how}], said}. The lab's own circuit with no
    inputs given runs as SHOW has it (the knob turned, BOOT pressed). Never a pass on his path."""
    from core.esp32_lab import checks_of
    from core.esp32_path import judge

    if lesson_id not in CIRCUITS:
        raise ValueError("There's no lab by that name.")
    shown = ""
    if wires is None and not inputs and lesson_id in SHOW:
        inputs, seconds, shown = SHOW[lesson_id]
    seconds = max(1.0, min(60.0, float(seconds or 10.0)))
    found = analyse(lesson_id, reference_wires(lesson_id) if wires is None else wires)
    inputs = dict(inputs or {})
    stopped = [p["text"] for p in found["problems"] if p["level"] == "stop"]
    lines, outs = ([], []) if stopped else _run(lesson_id, found["state"], inputs, seconds, random.Random(seed))
    serial = "".join(line + "\n" for _, line in lines)
    checks = []
    for check in checks_of(lesson_id):
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
