"""
core.outage_actions
=====================

The power outage clock from the screen and by voice (core/outage.py; DEC-0125, both ways). The actions
`outage.start` (the Power page's "The Power's Out", with an optional time) and `outage.end` ("The Power's Back"), and
the tool `power_outage` ("the power went out at 6 am", "how long is the food good?", "the power's back"); and the
tool `water_emergency` for a day without safe water (core/water_day.py, read only), and `storm_ready` for a storm
coming (core/storm_ready.py, read only).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionType
from core.assistant_actions import AssistantAction


def _describe_start(context, params) -> str:
    """What outage.start says."""
    when = str(params.get("when", "") or "").strip()
    return "Start the outage clock" + (f" from {when}" if when else " from now")


def _start(context, params) -> str:
    """Does outage.start."""
    from core.outage import start

    when = str(params.get("when", "") or "").strip()
    return start(context, f"at {when}" if when and "ago" not in when else when)


def _describe_end(context, params) -> str:
    """What outage.end says."""
    return "Stop the outage clock: the power's back"


def _end(context, params) -> str:
    """Does outage.end."""
    from core.outage import end

    return end(context)


OUTAGE_ACTIONS = {k.kind: k for k in (
    ActionType("outage.start", "The Power's Out", {"when": "when it went out, e.g. 6:30 am (optional)"},
               _describe_start, _start),
    ActionType("outage.end", "The Power's Back", {}, _describe_end, _end),
)}
ACTION_TYPES.update(OUTAGE_ACTIONS)


def _tool(context, arguments: dict) -> str:
    """Tool power_outage: start the clock, say where things stand, or end it."""
    from core.outage import end, start, status

    state = str(arguments.get("state", "") or "status").strip().lower()
    if state in ("out", "start", "went out"):
        return start(context, str(arguments.get("when", "") or ""))
    if state in ("back", "end", "on"):
        return end(context)
    return status(context)


def _water(context, arguments: dict) -> str:
    """Tool water_emergency: what he has and how to make water safe (core/water_day.say); a boil-water notice when
    he said so."""
    from core.water_day import say

    return say(context, boil=str(arguments.get("kind", "") or "").strip().lower().startswith("boil"))


def _storm(context, arguments: dict) -> str:
    """Tool storm_ready: a storm in the next three days and the checklist for it (core/storm_ready.say)."""
    from core.storm_ready import say

    return say(context)


def register_outage_actions(registry) -> None:
    """Registers power_outage, water_emergency (a day without safe water, core/water_day.py) and storm_ready (a storm
    coming, core/storm_ready.py).
    power_outage also hears "the power just went out" and "how long is the freezer good?" (live check through the
    whole turn, 2026-11-24)."""
    registry.register(AssistantAction(
        name="storm_ready", domain="today",
        description="Is a storm coming in the next three days (thunderstorms, freezing rain, heavy rain or snow, high "
                    "wind), and what to do before it from his records: generator fuel, water, hens, the greenhouse, "
                    "a build's lumber. The plain forecast is get_weather.",
        parameters={"type": "object", "properties": {}},
        handler=_storm, trigger_phrases=("storm coming", "storm on the way", "ready for the storm",
                                         "prepare for the storm", "storm prep", "get ready for the storm",
                                         "any storms", "big storm", "ice storm", "blizzard", "high winds"),
    ))
    registry.register(AssistantAction(
        name="water_emergency", domain="today",
        description="The water's off, or there's a boil-water notice: his drinking water in days, his tanks, the "
                    "hens' share, and how to make water safe (boil, or bleach drops). bleach_for_water is a dose for "
                    "a given amount.",
        parameters={"type": "object", "properties": {
            "kind": {"type": "string", "description": "off (no water) or boil (a boil-water notice)"}}},
        handler=_water, trigger_phrases=("water's off", "water is off", "water got shut off", "no water",
                                         "boil water", "boil-water", "water main", "water outage",
                                         "water isn't safe", "water is not safe"),
    ))
    registry.register(AssistantAction(
        name="power_outage", domain="power",
        description="How long food in the fridge or freezer stays good or safe without power, and the power outage "
                    "clock: start it when the power goes out (state 'out', with when if he said), say where things "
                    "stand: the fridge, the freezer, the generator's fuel, fish, hens, well (state 'status'), or end "
                    "it when it's back (state 'back'). get_power_status is the solar and battery readings.",
        parameters={"type": "object", "properties": {
            "state": {"type": "string", "description": "out, status or back"},
            "when": {"type": "string", "description": "when it went out, only if he said, e.g. 'at 6 am', '2 hours ago'"}},
            "required": ["state"]},
        handler=_tool, trigger_phrases=("power went out", "power just went out", "power's been out",
                                        "power has been out", "power is out", "power's out", "power outage",
                                        "lost power", "power's back", "power is back", "power came back",
                                        "food good", "fridge safe", "freezer safe", "food still safe", "blackout",
                                        "freezer still good", "fridge still good", "freezer good for",
                                        "fridge good for", "food last without power", "freezer good",
                                        "fridge good", "long is the freezer", "long is the fridge",
                                        "long will the freezer", "long will the fridge"),
    ))
