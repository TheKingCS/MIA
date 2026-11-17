"""
core.specialists
==================

MIA's specialists (DEC-0109; Zac, 2026-11-07: "she should be able to specialize
agents for each area of skill she is developing, like one that is catered
towards construction knowledge, one towards radio technologies, one towards
military strategy, one towards homesteading skills, one towards research, one
towards testing and auditing, etc. She could essentially specialize workers for
developing and maintaining her knowledge and skills").

**A specialist** (`SPECIALISTS`) is a worker with a charter: what it covers,
the skills it develops (her skill tree's categories), the curriculum tracks it
owns (core/curriculum.py), the loops it watches (core/loops.py), what it may
never do (`limits`), and the questions it starts from. Add one by adding it
here: the charter is code, so a test checks every skill, track and loop it
names is real.

**Its workbook** (`work/specialists/<id>.json`, versioned like the Knowledge
Vault): notes on what it knows, each with its sources (a book, a standard, an
article, a page in her reference library), and the open questions it hasn't
answered yet. A note starts **derived** (written by a model) and becomes
**confirmed** only when a person confirms it (`confirm()`); a wrong one is
**withdrawn**, kept so it isn't written again. MIA always says which a note
is.

**How it studies** (`study()`, from Night School, one specialist a night, the
one that studied longest ago): her teacher is given the specialist's charter,
its limits, its open questions, the titles it already has, and excerpts from
her own offline reference library (Kiwix packs) for those questions to cite
(`grounding()`), and writes up to `NOTES_PER_NIGHT` new notes, each with its
sources (a note without one is refused). The specialist's pages in `docs/specialists/` are rewritten after.

**How MIA uses it**: the `ask_specialist` tool answers from the workbooks (a
specialist named, or every one), with the note's sources and whether it's
confirmed. A question no note answers is never written into a workbook (they
are in the repo, and a person's words stay in their own folder): the
specialist only counts it, and study hall takes the most-asked one first; `python -m tools.specialists` lists, shows, confirms and runs them.

**As an agent** (DEC-0198, T1 of `docs/mia_os/MIA_OS_SPECIALIZED_AGENT_TEAMS.md`): each specialist is also a role a
team can use, set in `ROLES` beside its charter: its department, the kinds of task it takes (`TASK_TYPES`), the tools
it may call (only ones tiered observe or suggest: an agent changes nothing), how hard its thinking is
(`reasoning`) and what else its model must do (`needs`; one whose answers rest on figures works them out on the
worksheet, `work_it_out`), whose work it may review, and the caveat its output carries
where a qualified person must check it (Q-57). Its model is never named here: the router picks the best local
model the engineering bench (core/eng_bench.py) found good enough for the task (DEC-0197). An agent holds no grants and never talks to the person; only MIA does.
"""

from __future__ import annotations

from core.data_root import work_path

import json
import re
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
BOOKS = work_path("specialists")
PAGES = ROOT / "docs" / "specialists"
NOTES_PER_NIGHT = 3
MAX_BODY = 1800
STATUSES = ("derived", "confirmed", "withdrawn")

COMMON_LIMITS = ("Every note says where it comes from; a claim without a source isn't written. When the right answer "
                 "depends on where someone lives (a code, a law, a licence), the note says so and names who to check "
                 "with. Nothing about a real person's private life.")


@dataclass(frozen=True)
class Specialist:
    """One worker for one area of what MIA knows: its charter, the skills and curriculum tracks it develops, the
    loops it watches, its limits, and the questions it starts from; and, as an agent a team can use (DEC-0198, from
    ROLES), its department, task types, read-only tools, how hard its thinking is, what its model needs, whom it
    may review and the caveat its output carries."""
    id: str
    name: str
    charter: str
    skills: tuple[str, ...] = ()  # her skill tree's categories
    tracks: tuple[str, ...] = ()  # core/curriculum.py
    loops: tuple[str, ...] = ()  # core/loops.py
    limits: str = ""
    starts_from: tuple[str, ...] = ()
    words: tuple[str, ...] = ()  # what a question about its area sounds like
    # As an agent (DEC-0197; filled from ROLES below)
    department: str = ""
    task_types: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    reasoning: str = "medium"  # low | medium | high
    needs: tuple[str, ...] = ()  # of NEEDS
    reviews: tuple[str, ...] = ()  # specialist ids whose work it may review
    caveat: str = ""


SPECIALISTS: tuple[Specialist, ...] = (
    Specialist("construction", "Construction", "Building and fixing: carpentry, framing, concrete, plumbing, electrical, "
               "HVAC, roofing, drywall, finishing, tools, materials, estimating, and building codes and permits.",
               skills=("Construction",), limits="Work a code or a licence requires (structural, gas, electrical "
               "service, permits) is named as such, with who to call; safety first in every procedure.",
               starts_from=("How do you size a header for a load-bearing wall opening?",
                            "When does a project need a permit?", "How do you mix and cure concrete properly?"),
               words=("build", "frame", "framing", "concrete", "plumbing", "wiring", "drywall", "roof", "joist",
                      "stud", "permit", "code", "lumber", "deck", "foundation", "construction")),
    Specialist("homesteading", "Homesteading", "Growing and keeping: gardens, soil, seed starting, irrigation, "
               "hydroponics and aquaponics, chickens and other animals, preserving and storing food, and running a "
               "homestead through the seasons.", skills=("Homestead",),
               loops=(), limits="Food safety (canning, curing) follows tested guidance and says which; animal health "
               "beyond basics points to a vet.",
               starts_from=("What's a safe way to can low-acid vegetables?", "How do you keep hens laying in winter?",
                            "How do you build healthy soil in a new bed?"),
               words=("garden", "soil", "seed", "chicken", "hen", "egg", "compost", "canning", "harvest", "goat",
                      "aquaponic", "hydroponic", "homestead", "livestock", "preserv")),
    Specialist("radio", "Radio and communications", "Radio and how things talk: amateur (ham) radio and its licences, "
               "GMRS and FRS, Meshtastic and LoRa mesh, antennas and propagation, SDR, and keeping in touch without "
               "the internet or cell service.", skills=("Technology",), loops=("phone.link",),
               limits="Transmitting follows the licence and the band plan where it happens, and the note says which "
               "licence a thing needs; listening and receiving are described, never jamming or interference.",
               starts_from=("What licence does each kind of two-way radio need in the US?",
                            "How far can a Meshtastic node reach, and what improves it?",
                            "How do you build a simple dipole antenna for 2 metres?"),
               words=("radio", "ham", "antenna", "meshtastic", "lora", "gmrs", "frs", "frequency", "band", "sdr",
                      "repeater", "transmit", "callsign")),
    Specialist("strategy", "Strategy and preparedness", "Military history and strategy as ways of thinking: planning, "
               "logistics, decision making under pressure (the OODA loop), reading terrain and maps, leadership, and "
               "preparing a household for storms, outages and emergencies.", skills=("Social", "Outdoor"),
               limits="Strategy as history, principles, planning, logistics and protecting a household: never how to "
               "hurt people, make or modify weapons, or target anyone.",
               starts_from=("What is the OODA loop and how does it apply to everyday decisions?",
                            "How does a household plan for a week without power?",
                            "What did Sun Tzu mean by knowing yourself and your enemy?"),
               words=("strategy", "military", "tactic", "logistics", "ooda", "preparedness", "emergency", "plan",
                      "sun tzu", "clausewitz", "battle", "campaign", "contingency")),
    Specialist("maker", "Making and fabrication", "Making things: 3D printing, CAD, woodworking, metalwork, "
               "laser engraving, enclosures and prototyping (the electronics inside them are the embedded "
               "specialist's).", skills=("Maker", "Technology"),
               limits="Mains electricity and pressure systems are named as dangerous, with the safe way.",
               starts_from=("How do you choose a 3D-printing filament for an outdoor part?",
                            "How do you design a printed enclosure that keeps water out?"),
               words=("3d print", "cad", "laser", "cnc", "weld", "prototype", "filament", "woodwork", "enclosure",
                      "fabricat")),
    Specialist("embedded", "Embedded systems", "Small computers in real things: microcontrollers (ESP32, Arduino, "
               "Raspberry Pi Pico), sensors and actuators, I2C, SPI and serial, power budgets and batteries, "
               "regulators and level shifting, reading a datasheet, firmware structure, and getting a device to talk "
               "to MIA.", skills=("Technology", "Maker"),
               limits="Numbers come from her calculators (core/eng_calcs.py), never from memory. Mains voltage, "
               "lithium batteries and anything worn on the body are named as dangerous, with the safe way, and say a "
               "qualified person must check the design.",
               starts_from=("How do you work out a battery-powered sensor's life?",
                            "How do you choose between a linear and a switching regulator?",
                            "How do you connect a 5 volt sensor to a 3.3 volt microcontroller safely?"),
               words=("microcontroller", "esp32", "arduino", "pico", "firmware", "i2c", "spi", "uart", "gpio", "adc",
                      "pwm", "sensor node", "datasheet", "regulator", "pull-up", "embedded", "breadboard", "pcb")),
    Specialist("crafts", "Homestead crafts", "Making useful things by hand at home: fermenting and brining, candle and "
               "soap making, leather and sewing, basketry and cordage, natural dyes, woodcraft and carving, and "
               "keeping the tools for them.", skills=("Homestead", "Maker"),
               limits="Quantities come from her calculators (core/eng_calcs.py) or a named recipe. Canning, curing "
               "and anything eaten follow tested guidance and say which. Lye for soap is never sized from memory: it "
               "comes from a tested lye calculator, with the safety gear named.",
               starts_from=("How much salt does a vegetable ferment need?",
                            "How do you make a container candle that burns evenly?",
                            "What tools does a beginner need for leatherwork?"),
               words=("ferment", "brine", "sauerkraut", "candle", "wax", "soap", "lye", "leather", "sewing", "sew",
                      "basket", "cordage", "dye", "carving", "whittle", "craft", "knit", "weave")),
    # S4's first batch (the greenhouse pilot, DEC-0198: new specialists on a standing schedule).
    Specialist("greenhouse", "Greenhouse systems", "Running a greenhouse as a machine: glazing and heat loss, "
               "heaters and their fuel, ventilation and exhaust fans, shade and evaporative cooling, drip and "
               "misting, the sensors and controllers that run them (her greenhouse node), and keeping plants inside "
               "their temperature and humidity through every season.", skills=("Homestead", "Technology"),
               limits="Numbers come from her calculators (core/eng_calcs.py), never from memory. A heater burning "
               "fuel inside needs fresh air and a carbon monoxide alarm, and it says so; a controller that runs heat, "
               "water or fans fails safe; mains wiring for fans and heaters is the electrical specialist's and a "
               "licensed electrician's.",
               starts_from=("How big a heater does a greenhouse need for its coldest night?",
                            "How much exhaust fan does a greenhouse need for summer cooling?",
                            "What should a greenhouse controller do when a sensor stops answering?"),
               words=("greenhouse", "glazing", "polycarbonate", "heat loss", "exhaust fan", "shade cloth",
                      "evaporative", "swamp cooler", "misting", "drip", "emitter", "vent", "u-value", "propane heater",
                      "high tunnel", "hoop house")),
    # S4's second batch: the hoodie's (DEC-0198 Q-55: the hoodie is the second team's project). Embedded systems,
    # the fifth it names, is already here.
    Specialist("acoustics", "Acoustics and audio", "Sound in the air: speakers and their sensitivity, how loud they "
               "are at a distance, amplifier power, enclosures (sealed and ported boxes from Thiele-Small figures), "
               "placing and delaying speakers so sound arrives together, microphones, and keeping listening levels "
               "safe for hearing.", skills=("Technology", "Creative"),
               limits="Numbers come from her calculators (core/eng_calcs.py), never from memory. Sound close to the "
               "ears says how long it's safe to hear (NIOSH's limit), and hearing protection is named where it's "
               "needed; never anything to harm or harass with sound.",
               starts_from=("How loud does a small speaker need to be in a hood, and is that safe for hearing?",
                            "How do you choose an enclosure for a small full-range driver?",
                            "How do you place two speakers so their sound arrives together?"),
               words=("speaker", "loudspeaker", "woofer", "tweeter", "subwoofer", "amplifier", "decibel", "dba",
                      "sound pressure", "sealed box", "ported box", "thiele", "acoustics", "hearing",
                      "loudness", "microphone")),
    Specialist("audio_dsp", "Audio signal processing", "Sound as numbers: sample rates and bit depth, buffers and "
               "latency, filters and equalisers, FFTs, delays and mixing, codecs, I2S and audio on a "
               "microcontroller, and keeping audio smooth on small hardware.", skills=("Technology", "Creative"),
               limits="Numbers come from her calculators (core/eng_calcs.py), never from memory. A change that makes "
               "audio louder says how loud it ends up at the ears (the acoustics specialist's safe listening time).",
               starts_from=("How small can an audio buffer be on an ESP32 before it crackles?",
                            "What sample rate and bit depth does voice need, and what does music need?",
                            "How do you design a simple equaliser filter?"),
               words=("sample rate", "bit depth", "latency", "audio buffer", "fft", "dsp", "bitrate", "bit rate",
                      "equaliser", "equalizer", "biquad", "codec", "i2s", "audio delay", "aliasing", "nyquist")),
    Specialist("textiles", "Textiles and wearables", "Fabric and garments: fibres and weaves, fabric weight (GSM), "
               "patterns, yardage and layout, seams and shrinkage, sewing machines and stitches, and e-textiles: "
               "conductive thread, pockets and channels for electronics, washability and comfort against the body.",
               skills=("Maker", "Creative"),
               limits="Numbers come from her calculators (core/eng_calcs.py), never from memory. Anything electric "
               "worn on the body (a heated panel, a lit seam, a battery pocket) says how much heat it makes, names "
               "burns and lithium batteries as dangerous, and says a qualified person must check the design before "
               "it's worn.",
               starts_from=("How much fabric does a hoodie take, and how do you lay out the pieces?",
                            "How do you sew conductive thread so it survives washing?",
                            "Where can electronics sit in a garment so they're comfortable and safe?"),
               words=("fabric", "textile", "garment", "hoodie", "yardage", "seam allowance", "gsm", "fleece",
                      "conductive thread", "e-textile", "wearable", "pattern piece", "shrinkage", "stitch")),
    Specialist("power", "Portable power", "Batteries and power for things that move or are worn: lithium cells and "
               "packs (series and parallel), protection boards (BMS), charging and its time, C-rates, boost and buck "
               "converters, USB power, power budgets, and keeping a battery cool and safe.",
               skills=("Technology", "Maker"),
               limits="Numbers come from her calculators (core/eng_calcs.py), never from memory. Lithium cells are "
               "named as a fire risk every time: a pack needs a protection board and matched cells, a charger made "
               "for its chemistry, and a qualified person's review before it's built; house wiring is the electrical "
               "specialist's.",
               starts_from=("How do you size a battery pack for a wearable that runs all day?",
                            "How do you charge a lithium pack safely?",
                            "When do you need a boost converter, and what does it draw from the battery?"),
               words=("lipo", "li-ion", "lithium", "18650", "battery pack", "power bank", "bms", "c-rate",
                      "boost converter", "buck converter", "charge time", "charging", "usb-c power",
                      "cell pack")),
    Specialist("outdoors", "Outdoors and fieldcraft", "Being out there: navigation by map and compass and grid, "
               "hiking, camping, survival skills, weather, water, first aid in the field.", skills=("Outdoor",),
               limits="First aid is first aid: anything serious says to get emergency help.",
               starts_from=("How do you navigate with a map, a compass and MGRS?", "How do you make water safe to drink?"),
               words=("hike", "camp", "compass", "navigation", "survival", "trail", "weather", "fire", "shelter",
                      "first aid", "mgrs")),
    Specialist("music", "Music and guitar", "Playing and learning music: guitar technique, chords and scales, rhythm "
               "and timing, ear training, practice that works, and teaching a person step by step (core/guitar.py's "
               "program is its own).", skills=("Creative",),
               limits="Pain is a sign to stop and rest, never to push through; a lasting pain points to a doctor or "
               "a teacher in person.",
               starts_from=("What makes practice effective for a beginner guitarist?",
                            "How do you build calluses without hurting your fingers?",
                            "How do you learn to change chords on the beat?"),
               words=("guitar", "chord", "strum", "fret", "scale", "music", "song", "metronome", "tuning", "pick",
                      "riff", "practice")),
    Specialist("research", "Research", "Finding out: how to search, judge a source, check a claim against a second "
               "one, read a study, and keep what was learned with where it came from. It answers the other "
               "specialists' open questions when they need digging.", skills=("Mind",),
               limits="Says how strong the evidence is, and never presents one source as settled.",
               starts_from=("How do you tell a reliable source from an unreliable one?",
                            "How do you read a scientific study's results honestly?"),
               words=("research", "source", "study", "evidence", "citation", "fact check", "paper")),
    Specialist("testing", "Testing and auditing", "Proving things work and finding where they don't: her tests, her "
               "weekly self-audit, security reviews and pen testing on herself, and the curriculum's testing and "
               "security tracks.", skills=("Technology",), tracks=("testing", "security", "pentest"),
               loops=("dev.audit_code", "dev.connected", "dev.suite", "dev.vulnerable"),
               limits="Security testing is on MIA herself only (core/curriculum.SECURITY_RULES).",
               starts_from=("Which of her endpoints have no test that they refuse a stranger?",
                            "What makes a test flaky, and how do you make it steady?"),
               words=("test", "audit", "bug", "security", "pentest", "vulnerab", "flaky", "regression")),
    Specialist("engineering", "Software and AI engineering", "Building her: software engineering, web pages and apps, "
               "deploying, monitoring, documentation, and making her own models (DEC-0106).",
               skills=("Technology", "Mind"), tracks=("engineering", "documentation", "design", "web", "apps",
                                                      "deploying", "monitoring"),
               loops=("models.router_shadow", "dev.docs", "dev.loop_coverage"),
               limits="Changes go through the lab and Zac approves them.",
               starts_from=("How should a small router model be evaluated before it's used?",),
               words=("code", "software", "python", "deploy", "model", "api", "web page", "app", "programming")),
    # Trade Master (DEC-0149, Zac 2026-11-08: "one specialist per trade"): each studies its own trade for the jobs in
    # core/trade_jobs.py, with Construction as the general one.
    Specialist("carpentry", "Carpentry and framing", "Wood framing and finish carpentry: layout, walls, floors, roofs "
               "and rafters, stairs, decks, sheathing, trim, fasteners and connectors, and the span and header tables.",
               skills=("Construction",), loops=("trades.depth",), limits="Work a code or a licence requires is named as such, with who to call, and walked through only where a homeowner may legally do it under a permit (DEC-0149); safety first in every procedure; codes vary by place, so every code note says to check with the local building department.",
               starts_from=("How do you lay out and frame a stud wall with a door opening?",
                            "How do you cut and set common rafters for a gable roof?",
                            "What does the code's fastening schedule call for in wall and floor framing?"),
               words=("frame", "framing", "stud", "rafter", "joist", "header", "plate", "sheathing", "trim", "deck",
                      "carpentry", "lumber", "subfloor", "stairs")),
    Specialist("plumbing", "Plumbing", "Water supply and drains: pipe materials and joining (PEX, copper, PVC), "
               "drain, waste and vent sizing and slope, traps, fixtures, water heaters, wells and septic basics, "
               "pressure tests, and leaks.", skills=("Construction",), loops=("trades.depth",), limits="Work a code or a licence requires is named as such, with who to call, and walked through only where a homeowner may legally do it under a permit (DEC-0149); safety first in every procedure; codes vary by place, so every code note says to check with the local building department.",
               starts_from=("How do you size and slope a drain line and its vent?",
                            "How do you join PEX, copper and PVC correctly?",
                            "How do you pressure test new water supply lines?"),
               words=("plumbing", "pipe", "drain", "toilet", "faucet", "leak", "water heater", "pex", "copper",
                      "vent", "trap", "sewer", "septic", "shower")),
    Specialist("electrical", "Electrical", "Residential wiring: circuits and their sizing, breakers, GFCI and AFCI "
               "protection, boxes and fill, grounding and bonding, outlets, switches and lights, subpanels, proving "
               "a circuit dead, and the electrical code.", skills=("Construction",), loops=("trades.depth",),
               limits="Work a code or a licence requires is named as such, with who to call, and walked through only where a homeowner may legally do it under a permit (DEC-0149); safety first in every procedure; codes vary by place, so every code note says to check with the local building department. Never work on a circuit that hasn't been proven dead.",
               starts_from=("How do you size wire and breakers for a branch circuit?",
                            "Where does the code require GFCI and AFCI protection in a house?",
                            "How do you safely prove a circuit is dead before working on it?"),
               words=("electrical", "wiring", "wire", "circuit", "breaker", "outlet", "receptacle", "switch", "gfci",
                      "afci", "panel", "volt", "amp", "light fixture")),
    Specialist("hvac", "HVAC", "Heating, cooling and ventilation: load sizing, furnaces, heat pumps and mini-splits, "
               "ductwork and its sealing, filters and maintenance, thermostats, ventilation and moisture.",
               skills=("Construction",), loops=("trades.depth",),
               limits="Work a code or a licence requires is named as such, with who to call, and walked through only where a homeowner may legally do it under a permit (DEC-0149); safety first in every procedure; codes vary by place, so every code note says to check with the local building department. Refrigerant work needs a certified technician (EPA Section 608 in the US).",
               starts_from=("How do you size heating and cooling for a room or a building?",
                            "How do you install and seal ductwork so it delivers its airflow?",
                            "What can a homeowner maintain on a furnace or a heat pump, and what needs a technician?"),
               words=("hvac", "furnace", "heat pump", "air conditioner", "mini split", "minisplit", "duct", "filter",
                      "thermostat", "ventilation", "heating", "cooling")),
    Specialist("appliances", "Appliances", "Household appliances: how washers, dryers, refrigerators, ranges, "
               "dishwashers and water heaters work, diagnosing them in order, testing parts with a multimeter, and "
               "replacing common parts.", skills=("Construction",), loops=("trades.depth",),
               limits="Work a code or a licence requires is named as such, with who to call, and walked through only where a homeowner may legally do it under a permit (DEC-0149); safety first in every procedure; codes vary by place, so every code note says to check with the local building department. Unplug or switch off at the breaker before opening any appliance; gas appliances "
               "follow the gas stop rule.",
               starts_from=("How do you diagnose an electric dryer that runs but doesn't heat?",
                            "How do you diagnose a refrigerator that isn't cooling?",
                            "How do you safely test an appliance part with a multimeter?"),
               words=("appliance", "dryer", "washer", "fridge", "refrigerator", "dishwasher", "range", "oven",
                      "freezer", "ice maker", "multimeter")),
    Specialist("exterior", "Roofing, siding and windows", "The building's skin: roofing (underlayment, drip edge, "
               "shingles and metal), flashing, house wrap, siding, windows and doors, gutters, and keeping water out.",
               skills=("Construction",), loops=("trades.depth",), limits="Work a code or a licence requires is named as such, with who to call, and walked through only where a homeowner may legally do it under a permit (DEC-0149); safety first in every procedure; codes vary by place, so every code note says to check with the local building department. Fall protection on every roof.",
               starts_from=("How do you install underlayment, drip edge and asphalt shingles to the maker's specs?",
                            "How do you flash a window in a wall with house wrap?",
                            "How do you install lap siding so it sheds water?"),
               words=("roof", "roofing", "shingle", "siding", "flashing", "gutter", "window", "house wrap", "soffit",
                      "fascia", "metal roof", "drip edge")),
)

# ------------------------------------------------------------------ as agents (DEC-0198: the teams design's roles)

DEPARTMENTS = ("research", "engineering", "software", "fabrication", "trades", "homestead", "preparedness",
               "creative")
# Departments whose work can hurt someone or something: every agent in one carries a caveat (Q-57).
SAFETY_DEPARTMENTS = frozenset({"engineering", "fabrication", "trades", "homestead"})
TASK_TYPES = ("research", "compare", "design", "estimate", "review", "safety_review", "write", "build_code")
REASONING = ("low", "medium", "high")
NEEDS = ("code", "vision", "numbers")  # numbers: its answers rest on figures code should check

_PRO = "A draft for you to check, not a substitute for a licensed {who}; codes vary by place."
_READ = ("look_up_online", "search_textbook", "list_projects", "get_project_missions")
_FIGURES = ("work_it_out",)  # the worksheet: the model picks calculators, code computes (core/specialist_work.py)
_BUILD = ("find_plans", "show_plan", "list_materials", "get_build_costs", "check_price", "list_inventory")

ROLES: dict[str, dict] = {
    "construction": dict(department="trades", task_types=("research", "design", "estimate", "review", "safety_review"),
                         tools=_READ + _BUILD, reasoning="high", needs=("numbers",),
                         reviews=("carpentry", "plumbing", "electrical", "hvac", "appliances", "exterior"),
                         caveat=_PRO.format(who="contractor or engineer")),
    "homesteading": dict(department="homestead", task_types=("research", "design", "estimate", "review"),
                         tools=_READ + ("get_homestead_next_step", "list_sensors", "get_weather", "list_lab_readings"),
                         needs=("numbers",), reviews=("crafts",),
                         caveat="Food safety follows tested guidance; animal health beyond basics needs a vet."),
    "radio": dict(department="engineering", task_types=("research", "design", "compare", "review"),
                  tools=_READ, needs=("numbers",), reviews=("embedded",),
                  caveat="Transmitting needs the right licence where you are; check the band plan."),
    "strategy": dict(department="preparedness", task_types=("research", "compare", "write", "review"),
                     tools=_READ + ("get_weather", "get_energy", "list_inventory")),
    "maker": dict(department="fabrication", task_types=("research", "design", "compare", "review"),
                  tools=_READ + _BUILD, needs=("numbers",), reviews=("embedded", "crafts"),
                  caveat="A draft for you to check; mains power and pressure are dangerous."),
    "embedded": dict(department="engineering", task_types=("research", "design", "compare", "review",
                                                           "safety_review", "build_code"),
                     tools=_READ + ("list_sensors", "list_inventory", "check_price", "get_energy"), reasoning="high",
                     needs=("code", "numbers"), reviews=("maker", "radio", "electrical"),
                     caveat="A draft for you to check; mains voltage and lithium batteries need a qualified "
                            "person's review before they're built."),
    "greenhouse": dict(department="engineering", task_types=("research", "design", "estimate", "review",
                                                            "safety_review"),
                       tools=_READ + ("list_sensors", "get_weather", "get_homestead_next_step", "list_lab_readings",
                                      "check_price"),
                       reasoning="high", needs=("numbers",), reviews=("homesteading", "embedded", "hvac"),
                       caveat="A draft for you to check; a fuel-burning heater needs fresh air and a CO alarm, and "
                              "mains wiring for fans and heaters needs a licensed electrician."),
    "acoustics": dict(department="engineering", task_types=("research", "design", "estimate", "compare", "review"),
                      tools=_READ + ("list_inventory", "check_price"), reasoning="high", needs=("numbers",),
                      reviews=("audio_dsp", "textiles"),
                      caveat="A draft for you to check; sound close to the ears can damage hearing, so check the "
                             "safe listening time."),
    "audio_dsp": dict(department="engineering", task_types=("research", "design", "review", "build_code"),
                      tools=_READ + ("list_inventory",), reasoning="high", needs=("code", "numbers"),
                      reviews=("acoustics", "embedded"),
                      caveat="A draft for you to check; test levels quietly first, since a mistake can be very loud."),
    "textiles": dict(department="fabrication", task_types=("research", "design", "estimate", "review"),
                     tools=_READ + ("list_inventory", "check_price", "list_materials"), needs=("numbers",),
                     reviews=("crafts", "maker", "power"),
                     caveat="A draft for you to check; anything electric worn on the body needs a qualified person's "
                            "review before it's worn."),
    "power": dict(department="engineering", task_types=("research", "design", "estimate", "review", "safety_review"),
                  tools=_READ + ("list_inventory", "check_price", "get_energy"), reasoning="high", needs=("numbers",),
                  reviews=("embedded", "textiles", "electrical"),
                  caveat="A draft for you to check; lithium batteries can catch fire, and a pack needs a qualified "
                         "person's review before it's built."),
    "crafts": dict(department="homestead", task_types=("research", "design", "estimate", "write", "review"),
                   tools=_READ + ("list_inventory", "check_price", "list_materials"), needs=("numbers",),
                   reviews=("homesteading", "maker"),
                   caveat="Lye, hot wax and dyes are dangerous; follow a tested recipe and a lye calculator."),
    "outdoors": dict(department="preparedness", task_types=("research", "write", "review"),
                     tools=_READ + ("get_weather", "list_trail_maps"),
                     caveat="First aid is first aid: anything serious needs emergency help."),
    "music": dict(department="creative", task_types=("research", "write"), tools=_READ, reasoning="low"),
    "research": dict(department="research", task_types=("research", "compare", "review"),
                     tools=_READ + ("world_finds",),
                     reviews=("construction", "homesteading", "radio", "strategy", "maker", "embedded", "crafts",
                              "outdoors", "music", "engineering")),
    "testing": dict(department="software", task_types=("review", "safety_review", "build_code"), tools=_READ,
                    reasoning="high", needs=("code",), reviews=("engineering", "embedded")),
    "engineering": dict(department="software", task_types=("research", "design", "review", "build_code", "write"),
                        tools=_READ, reasoning="high", needs=("code",), reviews=("testing", "embedded")),
    "carpentry": dict(department="trades", task_types=("research", "design", "estimate", "review", "safety_review"),
                      tools=_READ + _BUILD, reasoning="high", needs=("numbers",), reviews=("construction", "exterior"),
                      caveat=_PRO.format(who="contractor, or an engineer for anything structural")),
    "plumbing": dict(department="trades", task_types=("research", "design", "estimate", "review"),
                     tools=_READ + _BUILD, needs=("numbers",), reviews=("construction",),
                     caveat=_PRO.format(who="plumber")),
    "electrical": dict(department="trades", task_types=("research", "design", "estimate", "review", "safety_review"),
                       tools=_READ + _BUILD, reasoning="high", needs=("numbers",),
                       reviews=("construction", "embedded", "appliances"), caveat=_PRO.format(who="electrician")),
    "hvac": dict(department="trades", task_types=("research", "design", "estimate", "review"), tools=_READ + _BUILD,
                 needs=("numbers",), reviews=("construction",),
                 caveat=_PRO.format(who="HVAC technician (refrigerant needs a certified one)")),
    "appliances": dict(department="trades", task_types=("research", "review"),
                       tools=_READ + ("list_asset_parts", "check_price"), reviews=("electrical",),
                       caveat=_PRO.format(who="appliance technician (gas work needs a qualified one)")),
    "exterior": dict(department="trades", task_types=("research", "design", "estimate", "review"),
                     tools=_READ + _BUILD, needs=("numbers",), reviews=("carpentry", "construction"),
                     caveat=_PRO.format(who="roofer or contractor")),
}

def _as_agent(spec: Specialist) -> Specialist:
    """Pure logic. A charter with its role (ROLES) on it; one whose answers rest on figures also gets the worksheet."""
    role = dict(ROLES.get(spec.id, {}))
    if "numbers" in role.get("needs", ()):
        role["tools"] = tuple(role.get("tools", ())) + _FIGURES
    return replace(spec, **role)


SPECIALISTS = tuple(_as_agent(s) for s in SPECIALISTS)
BY_ID = {s.id: s for s in SPECIALISTS}


def agents_for(task_type: str = "", department: str = "") -> list[Specialist]:
    """Pure logic. The specialists that take a kind of task (and are in a department, when one is given), in the
    registry's order."""
    return [s for s in SPECIALISTS if (not task_type or task_type in s.task_types)
            and (not department or s.department == department)]


def reviewers_of(sid: str) -> list[Specialist]:
    """Pure logic. The specialists qualified to review one's work (never itself)."""
    return [s for s in SPECIALISTS if sid in s.reviews and s.id != sid]


def describe_registry() -> str:
    """Pure logic. MIA's specialists as agents, by department, in plain words (the registry's spoken summary)."""
    lines = []
    for dept in DEPARTMENTS:
        members = [s.name for s in SPECIALISTS if s.department == dept]
        if members:
            lines.append(f"{dept.capitalize()}: {', '.join(members)}.")
    return (f"I have {len(SPECIALISTS)} specialists. " + " ".join(lines)
            + " Each one works only on what I give it, changes nothing, and I check its work before it reaches you.")


def _action_list(context, arguments: dict) -> str:
    """Tool list_specialists: the registry by department (describe_registry)."""
    return describe_registry()


# ------------------------------------------------------------------ the workbooks

def _book_path(sid: str, folder: Path = BOOKS) -> Path:
    """Where a specialist's workbook lives."""
    return Path(folder) / f"{sid}.json"


def book(sid: str, folder: Path = BOOKS) -> dict:
    """A specialist's workbook: its notes, its open questions (the charter's starting ones until it has its own),
    and when it last studied. A missing or unreadable workbook starts fresh."""
    spec = BY_ID[sid]
    try:
        data = json.loads(_book_path(sid, folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {"notes": list(data.get("notes") or []),
            "questions": list(data.get("questions") if "questions" in data else spec.starts_from),
            "studied": str(data.get("studied") or ""),
            "unanswered": int(data.get("unanswered") or 0)}


def _save(sid: str, data: dict, folder: Path = BOOKS) -> None:
    """Writes a workbook atomically."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    atomic_write_text(_book_path(sid, folder), json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def add_note(sid: str, title: str, body: str, sources: list[str], by: str = "mia", status: str = "derived",
             answers: str = "", folder: Path = BOOKS) -> dict:
    """Keeps one note in a specialist's workbook: refused (ValueError) without a title, a body or a source, as a
    repeat of a live note's title, or longer than MAX_BODY. A note that answers an open question takes it off the
    list."""
    if sid not in BY_ID:
        raise ValueError(f"No specialist {sid!r}.")
    title, body = " ".join((title or "").split())[:120], (body or "").strip()
    sources = [" ".join(str(s).split())[:300] for s in sources or [] if str(s).strip()]
    if not title or not body:
        raise ValueError("A note needs a title and what it says.")
    if not sources:
        raise ValueError("Every note says where it comes from.")
    if len(body) > MAX_BODY:
        raise ValueError(f"A note is at most {MAX_BODY} characters; split it.")
    if status not in STATUSES[:2]:
        raise ValueError("A new note is derived or confirmed.")
    data = book(sid, folder)
    if any(n["title"].lower() == title.lower() and n["status"] != "withdrawn" for n in data["notes"]):
        raise ValueError(f"There's already a note called {title!r}.")
    note = {"id": uuid.uuid4().hex[:8], "title": title, "body": body, "sources": sources, "status": status, "by": by,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    data["notes"].append(note)
    if answers:
        data["questions"] = [q for q in data["questions"] if q.strip().lower() != answers.strip().lower()]
    _save(sid, data, folder)
    return note


def add_question(sid: str, question: str, folder: Path = BOOKS) -> None:
    """Adds an open question for a specialist to study (a repeat is ignored)."""
    question = " ".join((question or "").split())[:300]
    data = book(sid, folder)
    if question and question.lower() not in {q.lower() for q in data["questions"]}:
        data["questions"].append(question)
        _save(sid, data, folder)


def _mark(sid: str, note_id: str, status: str, why: str = "", folder: Path = BOOKS) -> dict:
    """Sets a note's status (with why, for a withdrawal); ValueError when it isn't there."""
    data = book(sid, folder)
    note = next((n for n in data["notes"] if n["id"] == note_id), None)
    if note is None:
        raise ValueError(f"No note {note_id} for {sid}.")
    note["status"] = status
    if why:
        note["why"] = why[:300]
    _save(sid, data, folder)
    return note


def confirm(sid: str, note_id: str, folder: Path = BOOKS) -> dict:
    """A person read the note and its sources and says it's right."""
    return _mark(sid, note_id, "confirmed", folder=folder)


def withdraw(sid: str, note_id: str, why: str, folder: Path = BOOKS) -> dict:
    """The note is wrong: kept, so it isn't written again, and never used."""
    return _mark(sid, note_id, "withdrawn", why, folder)


# ------------------------------------------------------------------ answering

def _words(text: str) -> set[str]:
    """Pure logic. A text's words, small ones left out, with a crude stem."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(w) > 2 and w not in {"the", "and", "for", "how", "what", "you", "does", "with", "can", "your", "are"}:
            out.add(w[:-1] if len(w) > 4 and w.endswith("s") else w)
    return out


def who_knows(question: str) -> list[Specialist]:
    """Pure logic. The specialists whose area a question sounds like, best first."""
    q = (question or "").lower()
    scored = [(sum(1 for w in s.words if w in q), s) for s in SPECIALISTS]
    return [s for n, s in sorted(scored, key=lambda x: -x[0]) if n]


def search(question: str, sid: str = "", folder: Path = BOOKS, limit: int = 3) -> list[tuple[float, str, dict]]:
    """The live notes that best answer a question (in one specialist's workbook, or every one), as (score,
    specialist, note); confirmed notes count a little more than derived ones."""
    want = _words(question)
    found = []
    for spec in ([BY_ID[sid]] if sid in BY_ID else SPECIALISTS):
        for note in book(spec.id, folder)["notes"]:
            if note["status"] == "withdrawn":
                continue
            have = _words(note["title"]) | _words(note["body"])
            hits = len(want & have)
            if hits:
                score = hits / max(1, len(want)) + 0.5 * len(want & _words(note["title"])) / max(1, len(want))
                found.append((round(score * (1.2 if note["status"] == "confirmed" else 1.0), 3), spec.id, note))
    found.sort(key=lambda x: -x[0])
    return found[:limit]


def _asked_unanswered(sid: str, folder: Path = BOOKS) -> None:
    """Counts one question a specialist was asked and couldn't answer: never the words, which are the person's."""
    data = book(sid, folder)
    data["unanswered"] = data["unanswered"] + 1
    _save(sid, data, folder)


def answer(question: str, sid: str = "", folder: Path = BOOKS, keep_question: bool = False) -> str:
    """What MIA's specialists know about a question, in plain words: the best note, its sources, and whether a
    person has confirmed it; or that no specialist has a note on it yet. Then the specialist whose area it is is
    told: with keep_question (Zac adding one at the PC) the question goes on its list; otherwise (someone asking by
    voice) only that it was asked something it couldn't answer, because the workbooks are in the repo and a
    person's words stay in their own folder."""
    found = search(question, sid, folder)
    if not found:
        area = BY_ID.get(sid) or next(iter(who_knows(question)), None)
        if area is not None:
            if keep_question:
                add_question(area.id, question, folder)
            else:
                _asked_unanswered(area.id, folder)
            return (f"My {area.name.lower()} specialist doesn't have a note on that yet; it'll study its area "
                    "sooner for being asked.")
        return "None of my specialists has a note on that yet."
    _score, spec_id, note = found[0]
    status = "confirmed by a person" if note["status"] == "confirmed" else "written by a model, not confirmed yet"
    return (f"From my {BY_ID[spec_id].name.lower()} specialist ({status}): {note['title']}. {note['body']} "
            f"Sources: {'; '.join(note['sources'])}.")


# ------------------------------------------------------------------ studying (Night School)

STUDY_PROMPT = """You are writing notes for one of MIA's specialists: a worker that develops and maintains one area of
what MIA (a personal assistant) knows. Notes are kept in its workbook and MIA answers questions from them.

The specialist: {name}. What it covers: {charter}
Its limits: {limits} {common}

Its open questions (answer some of these first):
{questions}

From MIA's own offline reference library (prefer these; cite one as "Reference library: <pack>, '<article>'"):
{library}

Notes it already has (don't repeat them):
{titles}

Reply with only a JSON object:
{{"notes": [up to {count} of {{
    "title": "short",
    "body": "the note itself: clear, practical, correct, in plain words, at most {max_body} characters",
    "sources": ["where it comes from: a book with its author, a standard or code with its number, an official page,
                 a reference work; at least one, real ones only"],
    "answers": "the open question it answers, word for word, or empty"}}],
 "questions": ["up to 3 new questions this specialist should study next"]}}"""


def next_to_study(folder: Path = BOOKS) -> Specialist:
    """The specialist asked most often what it couldn't answer since it last studied; then the one that studied
    longest ago (never first, in the charter's order)."""
    def rank(s):
        b = book(s.id, folder)
        return (-b["unanswered"], b["studied"], SPECIALISTS.index(s))
    return min(SPECIALISTS, key=rank)


def _library_search() -> Optional[Callable[[str, int], list]]:
    """Her offline reference library's search across every pack (core/reference_library_manager.py), or None when
    it can't be opened here."""
    try:
        from core.app_context import AppContext
        from core.config_manager import ConfigManager
        from core.event_bus import EventBus
        from core.reference_library_manager import ReferenceLibraryManager

        library = ReferenceLibraryManager(AppContext(config=ConfigManager(), events=EventBus()))
        return library.search_all_packs if library.list_packs() else None
    except Exception:
        return None


def grounding(questions: list[str], search: Optional[Callable[[str, int], list]], per_question: int = 2,
              chars: int = 600) -> str:
    """Excerpts from her reference library for a specialist's first open questions, each labelled with its pack and
    article so a note can cite it; "(no reference packs installed)" without a library or a hit."""
    if search is None:
        return "(no reference packs installed)"
    lines = []
    for q in questions[:3]:
        try:
            hits = search(q, per_question)
        except Exception:
            continue
        for h in hits:
            lines.append(f"- {h.pack_title}, '{h.article_title}' (for: {q}): {' '.join(h.snippet.split())[:chars]}")
    return "\n".join(lines) or "(nothing in the reference packs for these questions)"


def study(ask: Callable[[str], str], sid: str = "", folder: Path = BOOKS, pages: Optional[Path] = PAGES,
          count: int = NOTES_PER_NIGHT, search: Optional[Callable[[str, int], list]] = None,
          use_library: bool = True) -> dict:
    """One study session for a specialist (the next in turn unless named): its teacher (`ask`, a prompt in and the
    reply out) writes notes from its charter and open questions, given excerpts from her offline reference library
    to cite when it has packs (`search`, else found here unless use_library is False); each valid note is kept as
    derived, a bad one is counted and skipped; new questions are added. Returns what happened."""
    from core.night_school import _json_in

    spec = BY_ID[sid] if sid else next_to_study(folder)
    data = book(spec.id, folder)
    live = [n["title"] for n in data["notes"] if n["status"] != "withdrawn"]
    if search is None and use_library:
        search = _library_search()
    said = _json_in(ask(STUDY_PROMPT.format(
        name=spec.name, charter=spec.charter, limits=spec.limits, common=COMMON_LIMITS,
        questions="\n".join(f"- {q}" for q in data["questions"][:8]) or "(none: choose what matters most)",
        library=grounding(data["questions"], search),
        titles="\n".join(f"- {t}" for t in live[-40:]) or "(none yet)", count=count, max_body=MAX_BODY)))
    kept, refused = [], []
    for raw in (said.get("notes") or [])[:count]:
        try:
            note = add_note(spec.id, str(raw.get("title", "")), str(raw.get("body", "")), list(raw.get("sources") or []),
                            by="teacher", answers=str(raw.get("answers") or ""), folder=folder)
            kept.append(note["title"])
        except (ValueError, AttributeError, TypeError) as problem:
            refused.append(str(problem)[:120])
    for q in (said.get("questions") or [])[:3]:
        add_question(spec.id, str(q), folder)
    data = book(spec.id, folder)
    data["studied"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data["unanswered"] = 0  # it has studied since
    _save(spec.id, data, folder)
    if pages is not None:
        write_pages(pages, folder)
    return {"specialist": spec.id, "kept": kept, "refused": refused}


# ------------------------------------------------------------------ their pages

def render(spec: Specialist, data: dict) -> str:
    """A specialist's page: its charter, limits, what it develops, its confirmed notes, its unconfirmed ones, and
    its open questions."""
    live = [n for n in data["notes"] if n["status"] != "withdrawn"]
    lines = [f"# {spec.name}", "",
             "*One of MIA's specialists (DEC-0109). Written by `core/specialists.py` from its workbook "
             f"(`work/specialists/{spec.id}.json`); don't edit by hand.*", "", spec.charter, "",
             f"**Limits:** {spec.limits} {COMMON_LIMITS}", ""]
    develops = [f"skills: {', '.join(spec.skills)}" if spec.skills else "",
                f"curriculum: {', '.join(spec.tracks)}" if spec.tracks else "",
                f"loops: {', '.join(spec.loops)}" if spec.loops else ""]
    if any(develops):
        lines += ["**Develops:** " + "; ".join(d for d in develops if d) + ".", ""]
    for heading, status in (("Notes, confirmed", "confirmed"), ("Notes, not confirmed yet", "derived")):
        these = [n for n in live if n["status"] == status]
        if these:
            lines += [f"## {heading}", ""]
            for n in these:
                lines += [f"### {n['title']}", "", n["body"], "", "Sources: " + "; ".join(n["sources"]), ""]
    if data["questions"]:
        lines += ["## Open questions", ""] + [f"- {q}" for q in data["questions"]] + [""]
    return "\n".join(lines)


def write_pages(out: Path = PAGES, folder: Path = BOOKS) -> str:
    """Writes every specialist's page and the index; returns a line saying what it wrote."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in SPECIALISTS:
        data = book(spec.id, folder)
        atomic_write_text(out / f"{spec.id}.md", render(spec, data))
        live = [n for n in data["notes"] if n["status"] != "withdrawn"]
        rows.append((spec, sum(n["status"] == "confirmed" for n in live), len(live), len(data["questions"])))
    index = ["# MIA's specialists", "", "*Workers that develop and maintain one area of what MIA knows (DEC-0109). "
             "Written by `core/specialists.py`.*", ""]
    index += [f"- [{s.name}]({s.id}.md): {n} notes ({c} confirmed), {q} open questions" for s, c, n, q in rows]
    atomic_write_text(out / "README.md", "\n".join(index) + "\n")
    return f"{len(rows)} specialists, {sum(r[2] for r in rows)} notes"


# ------------------------------------------------------------------ the Assistant's tool

def _action_ask(context, arguments: dict) -> str:
    """Tool ask_specialist: what her specialists know about a question (one named, or whichever's area it is)."""
    question = str(arguments.get("question") or "").strip()
    if not question:
        return "What should I ask?"
    named = str(arguments.get("specialist") or "").strip().lower()
    sid = next((s.id for s in SPECIALISTS if named and (named in s.id or named in s.name.lower())), "")
    return answer(question, sid)


def register_specialist_actions(registry) -> None:
    """Registers the ask_specialist and list_specialists tools, and work_it_out (a specialist's worksheet with her
    calculators, core/specialist_work.py)."""
    from core.assistant_actions import AssistantAction
    from core.specialist_work import register as register_worksheet

    register_worksheet(registry)

    registry.register(AssistantAction(
        name="ask_specialist", domain="knowledge",
        description=("Ask one of MIA's specialists (construction and the trades, homesteading, homestead crafts, "
                     "radio, embedded systems, strategy and preparedness, making, outdoors, research, testing, "
                     "engineering) what its workbook says about a question, "
                     "with its sources and whether a person has confirmed it."),
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "The question, in their words."},
            "specialist": {"type": "string", "description": "Which specialist, only if they named one."}},
            "required": ["question"]},
        handler=_action_ask, prompt_arg="question",
        trigger_phrases=("ask your specialist", "ask the specialist", "your construction specialist",
                         "your radio specialist", "your homesteading specialist", "your strategy specialist",
                         "what do your specialists", "ask the expert", "specialist say"),
        subjects=("specialist", "expert"),
    ))
    registry.register(AssistantAction(
        name="list_specialists", domain="knowledge",
        description="Which specialists MIA has, by department, and what each kind is for.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_list,
        trigger_phrases=("what specialists do you have", "which specialists", "list your specialists",
                         "who are your specialists"),
        subjects=("specialist", "specialists", "expert"),
    ))
