"""
core.greenhouse_setup
=======================

The greenhouse's setup from start to hand-over, as one sequence MIA keeps track of (DEC-0150; Zac, 2026-11-08: "if we
are setting up the greenhouse and I ask what is next is she able to tell me what device to flash, how to set it up,
what i need to ask next"). The pieces already exist: the build jobs (core/trade_jobs.py), flashing the safety MCU and
preparing and pushing the Pi (core/greenhouse_provision.py), taking it over (core/greenhouse_link.py). This puts them
in order and says where you are.

Each step (`STEPS`) says what it is, why it comes now, what it needs, and exactly what to say to MIA to do it; and
how MIA knows it's done, from what's already recorded: a job walked to its end (a `trade_finished` life event), the
firmware flashed, the node pushed or its email password sent (`mcu_flashed`, `node_pushed`, `node_secret_sent`,
recorded by core/greenhouse_provision.py),
PlatformIO found on this PC, the Pi's configs prepared, the node read. A step that only the person can see done (the
SD card written, the node started) is done when they say so ("done", "the Pi is ready") or when a later step proves
it.

"Let's set up the greenhouse", "what's next for the greenhouse", or "what's next?" while setting it up (and no job in
progress) say the next step; "skip that" moves past a step the person has done another way.

**As a mission, not on Today** (Zac, 2026-11-09: "these should be ready to generate Missions that only show in the
Missions tab and maybe under Greenhouse"). Starting the setup makes the mission "Set up the greenhouse", one objective
a step (`ensure_mission`). It's the way without voice (DEC-0125): ticking a step's objective on the Missions screen
counts as saying it's done, and a step MIA sees done herself (a job finished, the firmware flashed) ticks its
objective. The Greenhouse page's What's Next tab shows the step you're on (`page_card`). Facts in code; nothing here
acts on a device.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class SetupStep:
    """One step of the setup: its id, what it is, why now, what it needs, what to say to MIA, and how it's done
    (`done_when`: "job:<id>", "event:<type>", "pio", "prepared", "read", or "said")."""
    id: str
    what: str
    why: str
    needs: str
    say: str
    done_when: str


STEPS: tuple[SetupStep, ...] = (
    SetupStep("build", "Build the aquaponics system: the tank, the grow bed, the plumbing, the pump and aeration.",
              "Everything else sits on a system that's proven to hold water and cycle.",
              "the 55-gallon tank and stand, a grow bed and media, PVC and fittings, a pump, an air pump with a check "
              "valve, a GFCI outlet", "walk me through building the aquaponics system", "job:aquaponics_system"),
    SetupStep("pio", "Install PlatformIO on this PC, so I can build and flash the safety MCU's firmware.",
              "The safety MCU is programmed from here over USB.", "a terminal: `pip install platformio`",
              "(install it, then say “done”)", "pio"),
    SetupStep("flash", "Flash the safety MCU: the ESP32 that's the final authority over every pump and doser.",
              "It's flashed and tested on the bench, with LEDs in place of relays, before it touches water.",
              "the ESP32 board on a USB cable, an LED and a resistor for each relay", "flash the safety MCU",
              "event:mcu_flashed"),
    SetupStep("controls", "Install the controls: the bench test with LEDs, the enclosure, the relay outlets, the "
              "override switch, the probes and the dosing pumps.",
              "With the firmware on the board, the safety chain can be proven and then installed.",
              "the parts on the node's parts list, the override switch, the probes and their calibration solutions",
              "walk me through installing the controller", "job:aquaponics_controls"),
    SetupStep("prepare", "Prepare the Pi: I make its SSH key and its preloaded configs, and give you the Raspberry Pi "
              "Imager steps.", "The Pi runs the node; it's set up from what I write so nothing is typed twice.",
              "a Raspberry Pi and an SD card", "prepare the Pi", "prepared"),
    SetupStep("card", "Write the Pi's SD card with Raspberry Pi Imager (hostname, user, my key, your Wi-Fi), put it in "
              "the Pi and power it on.", "Imager is where you type the Wi-Fi password, never me.",
              "Raspberry Pi Imager on this PC", "(write it, then say “the Pi is ready”)", "said"),
    SetupStep("push", "Push the greenhouse node to the Pi: its code, the configs, and its service.",
              "The node is installed the same way every time, with its rollback.", "the Pi on your network",
              "push the greenhouse to mia-greenhouse", "event:node_pushed"),
    SetupStep("secret", "Send the node its email password from your password vault, so its alerts can go out by "
              "email (say “skip that” if you don't want email alerts).",
              "It goes from the vault to the node, never through a conversation or a config file here.",
              "your vault unlocked, with the node's email login saved in it",
              "send the greenhouse its email password", "event:node_secret_sent"),
    SetupStep("start", "Start the node on the Pi and its export server "
              "(`python viewer/serve_exports.py --bind <the Pi's address>`).",
              "The export server is how I read the node; it serves only two read-only files.",
              "an SSH session to the Pi", "(start them, then say “take over the greenhouse at <its address>”)",
              "read"),
    SetupStep("take_over", "Hand the greenhouse to me: I watch every sensor and send you its alerts.",
              "From here I watch it with you, and the commissioning job checks every probe I see.",
              "the Pi's address", "take over the greenhouse at <the Pi's address>", "read"),
    SetupStep("commission", "Commission and cycle it: calibrate the probes, cycle the biofilter, then stock the fish.",
              "Fish go in only once ammonia and nitrite read zero.", "a test kit, dechlorinator, ammonia, the fish",
              "walk me through the fishless cycle", "job:aquaponics_commission"),
)


def _finished_jobs(context) -> set:
    """The jobs walked to their end (their ids), from the history."""
    from core.life_events import events_for

    try:
        return {(e.payload or {}).get("id") for e in events_for(context, types=("trade_finished",))}
    except Exception:
        log.exception("Couldn't read the history for the greenhouse setup")
        return set()


def _events(context) -> set:
    """Which provisioning steps the history records (mcu_flashed, node_pushed, node_secret_sent)."""
    from core.life_events import events_for

    try:
        return {e.type for e in events_for(context, types=("mcu_flashed", "node_pushed", "node_secret_sent"))}
    except Exception:
        return set()


def is_done(step: SetupStep, context, said: set, finished: set, events: set,
            pio: Optional[Callable] = None) -> bool:
    """Whether a step is done, from what's recorded (or what the person said)."""
    from core import greenhouse_provision as gp

    kind, _, arg = step.done_when.partition(":")
    link = getattr(context, "greenhouse_link", None)
    if step.id in said:
        return True
    if kind == "job":
        return arg in finished
    if kind == "event":
        return arg in events
    if kind == "pio":
        return bool((pio or gp.platformio)())
    if kind == "prepared":
        return gp.KEY.exists() and (gp.BUNDLE / "PI_SETUP.md").exists()
    if kind == "read":
        return bool(link is not None and link.taken_over and link.state)
    return False


MISSION = "Set up the greenhouse"


def title_of(step: SetupStep) -> str:
    """Pure logic. A step's short name, as its mission objective: "Flash the safety MCU", "Write the Pi's SD card"
    (the sentence up to its first colon, and up to where it starts saying why or how)."""
    title = step.what.split(":")[0].rstrip(".")
    for cut in (", so ", " (", " with ", ", put ", " from "):
        title = title.split(cut)[0]
    return title


def mission(context):
    """The active setup mission, or None (no missions here, or none made yet)."""
    missions = getattr(context, "missions", None)
    if missions is None:
        return None
    return next((m for m in missions.all_missions() if m.status == "active" and m.name == MISSION), None)


def ensure_mission(context):
    """The setup's mission, made when there's none: one objective a step, each ticked once it's done. None without
    missions on this MIA."""
    found = mission(context)
    missions = getattr(context, "missions", None)
    if found is not None or missions is None:
        return found
    made = missions.add_mission(MISSION, summary="From the build to stocking fish, one step at a time. Ask MIA "
                                                 "“what's next for the greenhouse?” for any step.",
                                icon="🌱")
    for step in STEPS:
        missions.add_objective(made.mission_id, title_of(step), "tally", 1)
    _join_project(context, made.mission_id)
    return missions.get_mission(made.mission_id)


def _join_project(context, mission_id: str) -> None:
    """Makes the setup mission part of the person's greenhouse project (DEC-0152) when exactly one unfinished
    project has "greenhouse" in its name; with none, or more than one, it stands on its own until they choose."""
    projects = getattr(context, "projects", None)
    if projects is None:
        return
    found = [p for p in projects.all_projects() if "greenhouse" in p.name.lower() and p.status != "Complete"]
    if len(found) == 1:
        context.missions.set_project(mission_id, found[0].project_id)


def _ticked(context) -> set:
    """The steps whose objective the person ticked on the Missions screen (the same as saying they're done)."""
    found = mission(context)
    if found is None:
        return set()
    return {step.id for step, o in zip(STEPS, found.objectives) if o.progress >= 1}


def _sync(context, done: list) -> None:
    """Ticks the mission's objectives for the steps done (and no others), so Missions shows what MIA knows."""
    found = mission(context)
    if found is None or len(found.objectives) != len(STEPS):
        return
    try:
        context.missions.set_objective_progress(found.mission_id, [1 if d else 0 for d in done])
    except ValueError:
        log.exception("Couldn't tick the greenhouse setup's mission")


def where(context, pio: Optional[Callable] = None) -> tuple[int, Optional[SetupStep]]:
    """How many steps are done, and the next one (None when every step is done). A step only the person sees done
    counts as done once a later step is; a step ticked on its mission counts as said. The mission's ticks follow."""
    link = getattr(context, "greenhouse_link", None)
    said = set(getattr(link, "setup_said", []) or []) | _ticked(context)
    finished, events = _finished_jobs(context), _events(context)
    done = [is_done(s, context, said, finished, events, pio) for s in STEPS]
    last = max((i for i, d in enumerate(done) if d), default=-1)
    done = [d or (s.done_when == "said" and i < last) for i, (s, d) in enumerate(zip(STEPS, done))]
    _sync(context, done)
    for i, step in enumerate(STEPS):
        if not done[i]:
            return sum(done), step
    return len(STEPS), None


def say_next(context, pio: Optional[Callable] = None) -> str:
    """The next step in words: where you are, what it is, why now, what it needs, and what to say."""
    count, step = where(context, pio)
    if step is None:
        return "The greenhouse is set up and handed over: every step is done. Ask me “how's the greenhouse?” any time."
    say = step.say if step.say.startswith("(") else f"Say “{step.say}”."
    return (f"Step {STEPS.index(step) + 1} of {len(STEPS)}: {step.what} Why now: {step.why} You'll need: {step.needs}. "
            f"{say}")


def mark(context, step_id: str) -> str:
    """Marks a step done by the person's word (or skipped), the same as saying "done" or "skip that"; ValueError for
    a step that isn't next."""
    link = getattr(context, "greenhouse_link", None)
    _count, step = where(context)
    if link is None or step is None or step.id != step_id:
        raise ValueError("That isn't the greenhouse setup's next step.")
    link.setup_said = list(getattr(link, "setup_said", []) or []) + [step.id]
    link.save()
    return "Got it. " + say_next(context)


def page_card(context) -> Optional[dict]:
    """The Greenhouse page's setup card (its What's Next tab), once the setup has started: the step you're on, what
    it needs and what to say, and the mission it's ticked on; None before it starts or once it's all done."""
    link = getattr(context, "greenhouse_link", None)
    if link is None or not getattr(link, "setup_started", False):
        return None
    count, step = where(context)
    if step is None:
        return None
    found = mission(context)
    return {"step": STEPS.index(step) + 1, "of": len(STEPS), "done": count, "title": title_of(step),
            "why": step.why, "needs": step.needs, "say": step.say, "mission_id": found.mission_id if found else ""}

_START = re.compile(r"\b(?:let'?s set up|set up|start setting up|help me set up) (?:the )?greenhouse\b")
_NEXT = re.compile(r"\bwhat'?s next (?:for|with|on) (?:the )?greenhouse(?: setup)?\b|\bgreenhouse setup\b|"
                   r"\bwhere are we (?:on|with) the greenhouse\b")
_BARE_NEXT = re.compile(r"^\s*(?:ok(?:ay)?[, ]+)?(?:what'?s next|what now|what do i do next|now what)\??\s*$")
_DONE = re.compile(r"^\s*(?:done|it'?s done|that'?s done|finished|the pi is ready|pi'?s ready|installed it)[.!]*\s*$")
_SKIP = re.compile(r"^\s*(?:skip (?:that|it|this)(?: step)?)[.!]*\s*$")


def reply(context, text: str, pio: Optional[Callable] = None) -> Optional[str]:
    """What MIA says, in code, about the greenhouse's setup: starting it, the next step, "done" for a step only the
    person can see, "skip that"; None when the words aren't for it (or the setup isn't started and they're just
    "what's next?")."""
    link = getattr(context, "greenhouse_link", None)
    if link is None:
        return None
    said = (text or "").lower().replace("’", "'")
    started = bool(getattr(link, "setup_started", False))
    if _START.search(said):
        link.setup_started = True
        link.save()
        made = mission(context) is None and ensure_mission(context) is not None
        return ("Let's set up the greenhouse. " + ("It's in your Missions as \u201cSet up the greenhouse\u201d, one "
                                                     "step at a time. " if made else "") + say_next(context, pio))
    if _NEXT.search(said) or (started and _BARE_NEXT.match(said)):
        return say_next(context, pio)
    if started and (_DONE.match(said) or _SKIP.match(said)):
        _count, step = where(context, pio)
        if step is None:
            return None  # the setup is finished: "done" is for something else
        if _DONE.match(said) and step.done_when == "pio":
            return ("I can't find PlatformIO on this PC yet (`pip install platformio`, or `pio` on the PATH). "
                    "Say “done” again once it's in, or “skip that” to go on without it.")
        if _DONE.match(said) and step.done_when != "said":
            how = step.say if step.say.startswith("(") else f"say “{step.say}”"
            return (f"I'll know “{step.what.split(':')[0]}” is done when it's recorded: {how}. "
                    "Or say “skip that” if you did it another way.")
        link.setup_said = list(getattr(link, "setup_said", []) or []) + [step.id]
        link.save()
        return "Got it. " + say_next(context, pio)
    return None
