"""
core.assistant_comm_actions
==============================

Assistant tools for the communication gate (core/communication_gate.py,
Cognitive Extension slice C): asking what MIA chose not to say, and
changing how often she speaks up on her own.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.communication_gate import ACT, DEFER, DROP


def _action_get_held_back_messages(context: AppContext, arguments: dict) -> str:
    gate = getattr(context, "communication", None)
    if gate is None:
        return "I don't keep a log of my messages on this device."
    entries = gate.entries_for_day()
    sent = [e for e in entries if e["action"] == ACT]
    held = [e for e in entries if e["action"] in (DEFER, DROP)]
    limit = gate.settings()["daily_budget"]
    if not entries:
        return f"I haven't had anything to say on my own today. Your limit is {limit} a day."
    parts = [f"Today I spoke up {len(sent)} time{'s' if len(sent) != 1 else ''} (your limit is {limit})."]
    if not held:
        parts.append("I didn't hold anything back.")
    else:
        waiting = [e for e in held if e["action"] == DEFER]
        dropped = [e for e in held if e["action"] == DROP]
        if waiting:
            parts.append("Still waiting to tell you: " + "; ".join(f"{e['title']}: {e['message']}" for e in waiting[:3]) + ".")
        if dropped:
            parts.append("I let these go: " + "; ".join(f"{e['title']} ({e['reason']})" for e in dropped[:4]) + ".")
    return " ".join(parts)


def _action_set_message_limit(context: AppContext, arguments: dict) -> str:
    gate = getattr(context, "communication", None)
    if gate is None:
        return "I can't change that on this device."
    current = int(gate.settings()["daily_budget"])
    count = arguments.get("count")
    direction = str(arguments.get("direction") or "").lower()
    if count not in (None, ""):
        try:
            new = int(float(count))
        except (TypeError, ValueError):
            return f"How many times a day? Right now it's {current}."
    elif direction in ("less", "fewer", "down"):
        new = current - 1
    elif direction in ("more", "up"):
        new = current + 1
    else:
        return f"Right now I speak up on my own at most {current} times a day. Want more or fewer?"
    new = gate.set_daily_budget(new)
    return (
        f"Okay: at most {new} time{'s' if new != 1 else ''} a day on my own. "
        "Urgent things, alarms you set and answers to you don't count."
    )


def register_communication_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="get_held_back_messages", domain="communication",
        description="What MIA chose not to tell the user today (held back or waiting), and why, plus how often she spoke up.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_held_back_messages,
        trigger_phrases=(
            "didn't tell me", "didnt tell me", "didn't you tell me", "didnt you tell me", "not tell me",
            "what didn't you", "what didnt you", "anything you didn't", "held back", "hold back", "holding back",
            "chose not to", "decided not to", "what have you told me today", "keeping from me",
        ),
    ))
    registry.register(AssistantAction(
        name="set_message_limit", domain="communication",
        description=(
            "Change how many times a day MIA may message the user on her own. Give count for an exact number, "
            "or direction 'less'/'more' when they don't say a number."
        ),
        parameters={"type": "object", "properties": {
            "count": {"type": "integer", "description": "Messages per day, e.g. 3."},
            "direction": {"type": "string", "description": "'less' or 'more' when no number was given."},
        }, "required": []},
        handler=_action_set_message_limit,
        trigger_phrases=(
            "times a day", "message me less", "message me more", "speak up less", "speak up more",
            "fewer notifications", "more notifications", "fewer messages", "more messages", "bug me less",
            "stop bugging me", "how often do you message me",
        ),
    ))
