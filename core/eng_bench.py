"""
core.eng_bench
================

"Can this model do engineering for MIA?" measured, not assumed (the local
specialists plan, S0a; DEC-0197). The existing model bench
(core/model_bench.py) only measures whether a model picks the right tool
in conversation; this one measures engineering answers.

What it is: `TASKS`, each a question in plain words with an answer that
**code can check**, because the expected value comes from one of MIA's own
calculators (core/eng_calcs.py). Some tasks leave out an input that
matters: the right answer to those is to ask for it, never to guess.

Each task is asked two ways (`MODES`), so the result shows how much the
method adds for a given model:
- **alone**: the model works it out itself and ends with `ANSWER: <number>
  <unit>` (or `NEED: <what's missing>`).
- **tools**: the model is shown the discipline's calculators and replies
  with which one to run and its inputs, as JSON (or what's missing). Code
  runs the calculator. This is how a specialist will really work.
(The full worksheet, with look-up and a second model's check, is the next
step and will be a third mode.)

What's counted per task: **right** (within the task's tolerance, with the
right unit), **wrong**, **guessed** (gave a number when an input was
missing: the dangerous one), **asked** (asked for the missing input),
**unreadable** (no answer in the form asked for), and the seconds it took.

`run(ask, mode)` takes any function from a prompt to a reply, so it runs
against a real local model (`python -m tools.eng_bench`, on the PC) or a
stand-in in tests. `summary()` groups the results by discipline. The model
for each specialist is chosen from these numbers.

Nothing a model replies is acted on: a reply only names a calculator and
inputs, which code checks before running.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Callable, Optional

from core.eng_calcs import BY_ID, CalcError, calculate, catalogue
from core.quantities import Quantity, UnitError, parse

MODES = ("alone", "tools")
RIGHT, WRONG, GUESSED, ASKED, UNREADABLE = "right", "wrong", "guessed", "asked", "unreadable"


@dataclass(frozen=True)
class Task:
    """One bench task: its id, the question in plain words, the calculator and inputs that give the expected answer,
    which of the calculator's values is the answer and the unit it's asked in, how close counts (a fraction), and
    for a task that leaves something out, the name of the missing input (then there's no answer: the right reply
    asks for it)."""
    id: str
    ask: str
    calculator: str
    inputs: dict
    answer: str = ""
    unit: str = ""
    within: float = 0.03
    missing: str = ""

    @property
    def discipline(self) -> str:
        """The discipline of the task's calculator."""
        return BY_ID[self.calculator].discipline


TASKS: tuple[Task, ...] = (
    # ---- electrical
    Task("e1", "A space heater draws 12.5 amps on a 120 volt circuit. How many watts is that?",
         "power", {"volts": "120 V", "amps": "12.5 A"}, "power", "W"),
    Task("e2", "A 15 amp load is at the end of 100 feet (one way) of 12 AWG copper on a 120 volt circuit. How many "
         "volts are lost in the wire?", "voltage_drop", {"volts": "120 V", "amps": "15 A", "length": "100 ft",
                                                         "gauge": 12}, "drop", "V"),
    Task("e3", "What is the smallest copper wire gauge (AWG) for a 16 amp load that runs all day, 75 feet one way "
         "from the panel, at 120 volts, keeping voltage drop to 3% or less?", "wire_gauge",
         {"volts": "120 V", "amps": "16 A", "length": "75 ft", "continuous": 1}, "gauge", "", 0.0),
    Task("e4", "How many watts can a 20 amp, 120 volt circuit carry for a load that runs longer than three hours?",
         "circuit_load", {"breaker": "20 A", "volts": "120 V"}, "continuous_watts", "W"),
    Task("e5", "A 100 amp-hour, 12 volt battery runs a 60 watt load through an inverter that is 90% efficient. Only "
         "80% of the battery may be used. How many hours does it run?", "battery_runtime",
         {"capacity": "100 Ah", "volts": "12 V", "load": "60 W", "usable": "80 %", "efficiency": "90 %"}, "runtime", "h"),
    Task("e6", "A 12 volt pump draws 20 amps and sits 30 feet (one way) from the battery. What is the smallest copper "
         "wire gauge (AWG) that keeps the voltage drop to 3% or less?", "wire_gauge",
         {"volts": "12 V", "amps": "20 A", "length": "30 ft"}, "gauge", "", 0.0),
    Task("e7", "What wire gauge do I need for a 30 amp load at 240 volts?", "wire_gauge",
         {"volts": "240 V", "amps": "30 A"}, missing="length"),
    # ---- embedded
    Task("m1", "What resistor (the exact value in ohms) puts 20 milliamps through an LED with a 2 volt forward voltage "
         "from a 5 volt supply?", "led_resistor", {"supply": "5 V", "forward": "2 V", "current": "20 mA"}, "exact", "ohm"),
    Task("m2", "A voltage divider has 10 kilohms on top and 20 kilohms on the bottom, fed with 5 volts. What is the "
         "voltage at the middle, with nothing connected to it?", "voltage_divider",
         {"vin": "5 V", "r1": "10 kohm", "r2": "20 kohm"}, "vout", "V"),
    Task("m3", "A sensor node wakes for 2 seconds every 10 minutes drawing 80 milliamps, and sleeps at 10 microamps "
         "the rest of the time. What is its average current in milliamps?", "battery_life",
         {"capacity": "2000 mAh", "active": "80 mA", "sleep": "10 uA", "awake": "2 s", "period": "600 s"},
         "average_current", "mA"),
    Task("m4", "A linear regulator turns 12 volts into 5 volts at 500 milliamps. How many watts of heat does it give "
         "off?", "regulator_heat", {"vin": "12 V", "vout": "5 V", "current": "500 mA", "theta": "50 degC/W"},
         "heat", "W"),
    Task("m5", "A 12-bit ADC uses a 3.3 volt reference. How many millivolts is one step?", "adc_step",
         {"vref": "3.3 V", "bits": 12}, "step", "mV"),
    Task("m6", "A linear regulator drops 9 volts to 3.3 volts at 300 milliamps in a package rated 62 degrees C per "
         "watt, in 25 degree C air. What temperature does its junction reach, in degrees C?", "regulator_heat",
         {"vin": "9 V", "vout": "3.3 V", "current": "300 mA", "theta": "62 degC/W", "ambient": "25 degC"},
         "junction", "degC"),
    Task("m7", "How long will my battery last in a sensor that wakes every 10 minutes for 2 seconds at 80 milliamps "
         "and sleeps at 10 microamps?", "battery_life",
         {"active": "80 mA", "sleep": "10 uA", "awake": "2 s", "period": "600 s"}, missing="capacity"),
    Task("m8", "What resistor do I need for an LED on a 5 volt supply at 20 milliamps?", "led_resistor",
         {"supply": "5 V", "current": "20 mA"}, missing="forward"),
    # ---- crafts
    Task("c1", "I'm fermenting 500 grams of cabbage in 1000 grams of water at 2% salt by total weight. How many grams "
         "of salt?", "brine_salt", {"water": "1000 g", "vegetables": "500 g", "strength": "2 %"}, "salt", "g"),
    Task("c2", "How many grams of wax fill a 250 millilitre candle jar, with wax at 0.86 grams per millilitre?",
         "candle_wax", {"volume": "0.25 L"}, "wax", "g"),
    Task("c3", "How much salt for my sauerkraut at 2%?", "brine_salt", {"strength": "2 %"}, missing="vegetables"),
    # ---- greenhouse (the greenhouse systems specialist, S4)
    Task("g1", "A greenhouse has 600 square feet of twin-wall polycarbonate glazing with a U-value of 0.7 BTU per hour "
         "per square foot per degree F. I keep it at 45 degrees F and plan for 5 degrees F outside. How many BTU per "
         "hour does it lose through the glazing?", "greenhouse_heat",
         {"area": "600 ft2", "u": "0.7 BTU/h/ft2/degF", "inside": "45 degF", "outside": "5 degF"}, "heat_loss", "BTU/h"),
    Task("g2", "How many cfm of exhaust fan does a 12 by 24 foot greenhouse floor need for summer cooling, at 8 cfm "
         "per square foot?", "vent_fan", {"floor": "288 ft2", "rate": 8}, "flow", "cfm"),
    Task("g3", "A drip zone has 40 emitters at half a gallon per hour each and runs for 2 hours. How many gallons "
         "does it use?", "drip_irrigation", {"emitters": 40, "rate": "0.5 gph", "hours": "2 h"}, "water", "gal"),
    Task("g4", "A propane heater has to make up 16,800 BTU per hour for 10 hours at 80% efficiency. How many gallons "
         "of propane is that?", "heater_fuel", {"load": "16800 BTU/h", "hours": "10 h", "efficiency": "80 %"},
         "propane", "gal"),
    Task("g5", "How big a heater does my greenhouse need for 5 degrees F outside? It has 600 square feet of glazing "
         "and I keep it at 45.", "greenhouse_heat", {"area": "600 ft2", "inside": "45 degF", "outside": "5 degF"},
         missing="u"),
)
BY_TASK = {t.id: t for t in TASKS}

_ALONE = """You are an engineer. Work this out carefully.
{ask}

End your reply with exactly one line in this form:
ANSWER: <number> <unit>
If something you need to know is missing from the question, do not guess: reply with only one line:
NEED: <what is missing>"""

_TOOLS = """You are an engineer. You never do arithmetic yourself: you choose a calculator and give it its inputs.
The calculators you have:
{calculators}

The question:
{ask}

Reply with only a JSON object, nothing else:
{{"calculator": "<id>", "inputs": {{"<name>": "<value> <unit>"}}}}
Use only values stated in the question. If a value a calculator must have (one with no default) is not in the
question, do not guess it: reply with only {{"need": "<what is missing>"}}"""

_ANSWER = re.compile(r"^\s*ANSWER\s*:\s*(.+?)\s*$", re.I | re.M)
_NEED = re.compile(r"^\s*NEED\s*:\s*(.+?)\s*$", re.I | re.M)


def prompt_for(task: Task, mode: str) -> str:
    """Pure logic. What the model is asked for a task in a mode."""
    if mode == "alone":
        return _ALONE.format(ask=task.ask)
    listing = "\n".join(
        f"- {c['id']}: {c['about']} Inputs: " + "; ".join(
            f"{name} ({spec['what']}, in {spec['unit'] or 'a plain number'}"
            + (f", default {spec['default']}" if spec["default"] is not None else ", must be given") + ")"
            for name, spec in c["inputs"].items())
        for c in catalogue(task.discipline))
    return _TOOLS.format(calculators=listing, ask=task.ask)


def expected(task: Task) -> Optional[Quantity]:
    """The right answer for a task, from MIA's own calculator (None for a task with an input left out)."""
    if task.missing:
        return None
    return calculate(task.calculator, task.inputs)["values"][task.answer]


def _judge(task: Task, got: Optional[Quantity], asked: bool) -> str:
    """Pure logic. The verdict from what the model ended up giving: a value, a request for what's missing, or
    neither."""
    if task.missing:
        return ASKED if asked else (GUESSED if got is not None else UNREADABLE)
    if asked:
        return WRONG  # nothing was missing: asking is a wrong answer here, though a safe one
    if got is None:
        return UNREADABLE
    want = expected(task)
    if task.within == 0:
        return RIGHT if got.dim == want.dim and round(got.si) == round(want.si) else WRONG
    return RIGHT if want.close_to(got, task.within) else WRONG


def score(task: Task, mode: str, reply: str) -> dict:
    """One reply's verdict: {"verdict", "got" (what was read from it, in words), "detail"}. In "tools" mode the
    named calculator is run by code with the inputs given; a calculator that refuses for a missing input counts as
    the model having asked only if the model itself said what's needed. A thinking model's <think> part is left
    out first (its working may hold an early ANSWER or a brace that isn't its answer); a reply cut off while still
    thinking has no answer."""
    reply = re.sub(r"<think>.*?(</think>|$)", "", str(reply or ""), flags=re.S | re.I)
    if mode == "alone":
        need, answer = _NEED.search(reply), _ANSWER.findall(reply)
        if need and not answer:
            return {"verdict": _judge(task, None, True), "got": f"NEED: {need.group(1)}", "detail": ""}
        if not answer:
            return {"verdict": _judge(task, None, False), "got": "", "detail": "no ANSWER line"}
        try:
            got = parse(answer[-1].replace("AWG", "").strip())
            if task.unit and got.unit == "":
                got = parse(f"{got.value} {task.unit}")
            return {"verdict": _judge(task, got, False), "got": str(got), "detail": ""}
        except UnitError as problem:
            return {"verdict": UNREADABLE if not task.missing else GUESSED, "got": answer[-1], "detail": str(problem)}
    try:
        raw = json.loads(reply[reply.find("{"): reply.rfind("}") + 1])
    except ValueError:
        raw = None
    if not isinstance(raw, dict):
        return {"verdict": _judge(task, None, False), "got": "", "detail": "no JSON object"}
    if raw.get("need") and not raw.get("calculator"):
        return {"verdict": _judge(task, None, True), "got": f"need: {raw['need']}", "detail": ""}
    try:
        result = calculate(str(raw.get("calculator") or ""), raw.get("inputs") if isinstance(raw.get("inputs"), dict) else {})
    except CalcError as problem:
        return {"verdict": UNREADABLE if not task.missing else GUESSED if raw.get("inputs") else UNREADABLE,
                "got": str(raw.get("calculator") or ""), "detail": str(problem)}
    if task.missing:  # it filled in something the question never gave
        return {"verdict": GUESSED, "got": result["said"], "detail": f"the question didn't give {task.missing}"}
    got = result["values"].get(task.answer) if result["calculator"] == task.calculator else None
    if got is None:
        return {"verdict": WRONG, "got": result["said"], "detail": f"expected the {task.calculator} calculator"}
    return {"verdict": _judge(task, got, False), "got": str(got), "detail": ""}


def run(ask: Callable[[str], str], mode: str, tasks: tuple = TASKS,
        progress: Optional[Callable[[dict], None]] = None) -> list[dict]:
    """Asks every task in a mode and scores each reply: a list of {"task", "discipline", "mode", "verdict", "got",
    "expected", "seconds", "detail"}. A model that fails to answer (an exception, or nothing) is unreadable for that
    task and the run goes on."""
    if mode not in MODES:
        raise ValueError(f"The modes are {', '.join(MODES)}.")
    rows = []
    for task in tasks:
        started = time.monotonic()
        try:
            reply = ask(prompt_for(task, mode))
        except Exception as problem:  # noqa: BLE001 - one failed call never ends the run
            reply, failed = "", f"{type(problem).__name__}: {problem}"
        else:
            failed = ""
        row = {"task": task.id, "discipline": task.discipline, "mode": mode, **score(task, mode, reply),
               "expected": str(expected(task).to(task.unit)) if not task.missing else f"ask for {task.missing}",
               "seconds": round(time.monotonic() - started, 2)}
        if failed:
            row["detail"] = failed
        rows.append(row)
        if progress is not None:
            progress(row)
    return rows


def summary(rows: list[dict]) -> dict:
    """The results by mode and discipline: for each, how many tasks, how many right (or asked, when something was
    missing), wrong, guessed and unreadable, the share that were good, and the mean seconds a task."""
    out: dict = {}
    for row in rows:
        cell = out.setdefault(row["mode"], {}).setdefault(row["discipline"], {
            "tasks": 0, RIGHT: 0, ASKED: 0, WRONG: 0, GUESSED: 0, UNREADABLE: 0, "seconds": 0.0})
        cell["tasks"] += 1
        cell[row["verdict"]] += 1
        cell["seconds"] += row["seconds"]
    for by_discipline in out.values():
        for cell in by_discipline.values():
            cell["good"] = round((cell[RIGHT] + cell[ASKED]) / cell["tasks"], 3)
            cell["seconds"] = round(cell["seconds"] / cell["tasks"], 2)
    return out
