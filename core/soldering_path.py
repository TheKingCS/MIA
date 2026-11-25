"""
core.soldering_path
=====================

Soldering and the meter, a learning program on core/paths.py's method (2026-11-25: the live sweeps found soldering a
gap, and his Arduino Nanos often come with their headers loose; Build With Arduino and Build With ESP32 are breadboard
labs that need neither). Through-hole soldering (a good joint, then fixing a bad one), and the multimeter (voltage,
continuity and resistance), with what to watch for. Checks said. How-tos from these lessons are answered in code
(core/lesson_answer.py: "how do I solder the headers on my nano?").

Kept apart from the lab courses on purpose: their lessons are labs, each with a sketch that the board's serial output
checks (core/esp32_lab.py), and a lesson with no sketch would be offered as a lab to flash.

Written from: Adafruit's and SparkFun's soldering guides (the IPC's picture of a good joint: a small shiny cone that
wets both the pin and the pad) and Fluke's multimeter basics. Low-voltage electronics only: mains wiring is an
electrician's, never these lessons'. Its XP goes to the Soldering skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "soldering"  # her skill tree's Soldering skill (data/skill_definitions.json)

STAGES: tuple = (
    Stage(1, "A good joint", "soldering through-hole parts and headers, and fixing a bad joint", (
        Lesson("joints", "Solder a joint (a Nano's headers)", (
            "Push the header strips into a breadboard, long pins down, and set the board on them: the breadboard holds "
            "them straight while you solder.",
            "Heat the iron (about 350 °C / 660 °F for leaded solder, a little hotter for lead-free), melt a "
            "little solder on the tip and wipe it on a damp sponge or brass wool so it shines.",
            "Touch the tip to the pin and its pad together for a second or two, then feed the solder into the joint, "
            "not onto the iron; a little flows around the pin.",
            "Take the solder away first, then the iron. A good joint is a small shiny cone; a dull ball is a cold "
            "joint: heat it again.",
            "Do one pin at each end, check the board sits flat and straight, then the rest.",
            "Work with air moving past you, keep the iron in its stand, and wash your hands after: solder can hold "
            "lead."),
            "A bad joint is the most common reason a circuit works one minute and not the next; a good one is quick "
            "once the iron is clean and hot.",
            ("A cold joint (dull, balled up): reheat it.", "Holding the iron on a pad too long: it can lift off the "
             "board.", "Breathing the flux smoke.")),
        Lesson("fixing", "Fix a bad joint", (
            "A bridge (solder joining two pins): drag a clean, hot tip between them, or lay desoldering wick on it and "
            "press the iron on the wick until the solder soaks in.",
            "Too much solder, or a part to take out: wick it away, or melt it and pull it with a solder sucker.",
            "Add a touch of flux to an old joint before reheating it: it helps the solder flow.",
            "Let the board cool, then look at every joint again in good light."),
            "Everyone makes bridges; knowing how to clear one turns a ruined board into a two-minute fix.",
            ("Wick held on so long the pad lifts.", "Leaving a bridge you didn't look for.")),
    ), (
        Check("headers_soldered", "Solder a board's headers (or a practice kit), every joint a shiny cone, and tell "
              "MIA", "said"),
        Check("bridge_fixed", "Make a bridge on a practice board on purpose and clear it with wick, and tell MIA",
              "said"),
    )),
    Stage(2, "The multimeter", "measuring voltage, continuity and resistance safely", (
        Lesson("meter", "Use a multimeter", (
            "Black lead in COM, red in the V/Ω jack: that's for nearly everything. The amps jack is only for "
            "measuring current in a circuit; leave the red lead out of it otherwise.",
            "Voltage: set it to DC volts, touch black to ground and red to the point; a 5 V pin should read close to "
            "5. Volts are measured across, with the circuit on.",
            "Continuity: with the power off, set the beeper mode and touch both ends of a wire or joint: a beep means "
            "connected. It finds bridges and broken wires.",
            "Resistance: with the power off and the part out of the circuit if you can, set ohms and touch its legs: a "
            "220 ohm resistor reads close to 220."),
            "The meter turns a guess (\"it should be working\") into a fact; most problems are found in a minute with "
            "continuity and a voltage check.",
            ("Measuring resistance or continuity with the power on.", "The red lead left in the amps jack: it shorts "
             "whatever you touch.", "Low-voltage boards only: mains is an electrician's.")),
    ), (
        Check("meter_used", "Measure a board's 5 V and 3.3 V pins, a resistor and a wire's continuity, and tell MIA "
              "the readings", "said"),
    )),
)

PROGRAM = register(Program(
    "soldering", "Soldering and the meter", SKILL, "\U0001f50c", "A good joint (a Nano's headers) and fixing a bad "
    "one, then the multimeter: voltage, continuity and resistance.",
    ("soldering", "solder", "learn to solder", "multimeter", "electronics bench"), STAGES, plan=(20, 2)))
