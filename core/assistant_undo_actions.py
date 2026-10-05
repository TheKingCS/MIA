"""
core.assistant_undo_actions
==============================

"Undo that" and "what did you just change?" (core/undo_log.py), plus
"why did you tell me that?" and "stop telling me about ..."
(core/message_reasons.py, core/communication_gate.py), and "is
everything set up?" (core/system_check.py). 2026-10-01.
"""

from __future__ import annotations

from datetime import datetime

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.message_reasons import explain, find_topic, name_of
from core.person_settings import person_id
from core.undo_log import undo_last



def _clock(when: datetime) -> str:
    """Pure logic. "2:05 PM". By hand: "%-I" doesn't exist on Windows."""
    return f"{when.hour % 12 or 12}:{when:%M %p}"

def _words(label: str) -> str:
    return label.replace("_", " ")


def _action_undo_last_change(context, arguments: dict) -> str:
    change = undo_last(context, person_id(context))
    if change is None:
        return "There's nothing of mine to undo right now."
    return f"Undone: I put things back the way they were before \"{_words(change.label)}\"."


def _action_get_recent_changes(context, arguments: dict) -> str:
    undo = getattr(context, "undo", None)
    changes = undo.recent(person_id(context)) if undo is not None else []
    if not changes:
        return "I haven't changed anything for you since MIA started."
    items = "; ".join(f"{_words(c.label)} at {_clock(datetime.fromisoformat(c.at))}" for c in changes[:5])
    return f"Most recent first: {items}. Say \"undo that\" to take back the latest."


def _action_why_that_message(context, arguments: dict) -> str:
    gate = getattr(context, "communication", None)
    entry = gate.last_sent() if gate is not None else None
    if entry is None:
        return "I haven't sent you anything on my own lately."
    return explain(entry)


def _action_mute_message_topic(context, arguments: dict) -> str:
    gate = getattr(context, "communication", None)
    if gate is None:
        return "I can't change that on this device."
    topic = find_topic(str(arguments.get("topic") or ""))
    if topic is None:
        last = gate.last_sent()
        if last is None or not last.get("topic"):
            return "Which kind of message? For example budget check-ins, check-ins, or suggestions."
        topic = last["topic"]
    days = int(arguments.get("days") or 30)
    until = gate.mute(topic, days)
    return (f"Okay, no more {name_of(topic)} until {until:%B} {until.day}. Urgent things still come through. "
            f"Say \"you can tell me about {name_of(topic)}\" to bring them back sooner.")


def _action_check_my_setup(context, arguments: dict) -> str:
    from core.system_check import run_checks, summary

    return summary(run_checks(context))


def register_undo_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="check_my_setup", domain="system",
        description="Check what's set up on this MIA (model, voice, reading photos, phone, data, account) and what to fix.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_check_my_setup,
        trigger_phrases=("is everything set up", "check my setup", "check your setup", "what's not working",
                         "whats not working", "what is missing", "what's missing", "setup check"),
    ))
    registry.register(AssistantAction(
        name="undo_last_change", domain="undo",
        description="Undo the most recent change MIA made for the user (an item added, a chore checked off...).",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_undo_last_change,
        trigger_phrases=("undo that", "undo it", "undo the last", "take that back", "take it back", "revert that",
                         "that was wrong, undo", "put it back", "undo what you"),
    ))
    registry.register(AssistantAction(
        name="get_recent_changes", domain="undo",
        description="List what MIA recently changed for the user, newest first.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_recent_changes,
        trigger_phrases=("what did you change", "did you just change", "what did you just do", "what have you changed", "what did you do"),
    ))
    registry.register(AssistantAction(
        name="get_message_reason", domain="communication",
        description="Explain why MIA sent her most recent message on her own, and how to stop that kind.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_why_that_message,
        trigger_phrases=("why did you tell me", "why are you telling me", "why did you send", "why did i get",
                         "why are you suggesting", "why did you suggest", "why that message", "why the notification"),
    ))
    registry.register(AssistantAction(
        name="mute_message_topic", domain="communication",
        description="Stop one kind of message MIA sends on her own (e.g. budget check-ins) for a while.",
        parameters={"type": "object", "properties": {
            "topic": {"type": "string", "description": "Which kind, in the user's words."},
            "days": {"type": "integer", "description": "How many days; 30 if not said."},
        }, "required": []},
        handler=_action_mute_message_topic,
        trigger_phrases=("stop telling me about", "stop sending me", "don't tell me about", "dont tell me about",
                         "stop the check-ins", "stop checking in", "stop reminding me about",
                         "stop suggesting"),
    ))
