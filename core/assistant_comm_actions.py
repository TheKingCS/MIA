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
    """Tool get_held_back_messages: how often she spoke up today (against the daily limit when one is set;
    otherwise paced per kind, DEC-0171), what's still waiting to be said, what she let go and why, and the
    kinds of message she's taking a break from.
    """
    gate = getattr(context, "communication", None)
    if gate is None:
        return "I don't keep a log of my messages on this device."
    entries = gate.entries_for_day()
    sent = [e for e in entries if e["action"] == ACT]
    held = [e for e in entries if e["action"] in (DEFER, DROP)]
    limit = int(gate.settings()["daily_budget"] or 0)
    breaks = _describe_breaks(gate)
    rule = f"Your limit is {limit} a day." if limit else "There's no fixed limit: I pace each kind by what you do with it."
    if not entries:
        return f"I haven't had anything to say on my own today. {rule}" + breaks
    parts = [f"Today I spoke up {len(sent)} time{'s' if len(sent) != 1 else ''}"
             + (f" (your limit is {limit})." if limit else ".")]
    if not held:
        parts.append("I didn't hold anything back.")
    else:
        waiting = [e for e in held if e["action"] == DEFER]
        dropped = [e for e in held if e["action"] == DROP]
        if waiting:
            parts.append("Still waiting to tell you: " + "; ".join(f"{e['title']}: {e['message']}" for e in waiting[:3]) + ".")
        if dropped:
            parts.append("I let these go: " + "; ".join(f"{e['title']} ({e['reason']})" for e in dropped[:4]) + ".")
    return " ".join(parts) + breaks


def _describe_breaks(gate) -> str:
    """The kinds of message on a break (dismissed several times in a row) and until when, with how to bring
    one back; empty when there are none.
    """
    paused = gate.paused()
    if not paused:
        return ""
    items = "; ".join(f"{p['label']} until {p['until']:%b %d}" for p in paused)
    return f" You dismissed these kinds of messages a few times in a row, so I'm taking a break from them: {items}. Say \"you can tell me about\" one to bring it back."


def _action_resume_message_topic(context: AppContext, arguments: dict) -> str:
    """Tool resume_message_topic: brings back the kinds of message on a break that the words name (the
    only one when there's one and nothing was named); asks which otherwise.
    """
    gate = getattr(context, "communication", None)
    if gate is None:
        return "I can't change that on this device."
    paused = gate.paused()
    if not paused:
        return "I'm not taking a break from anything right now."
    words = {w for w in str(arguments.get("topic") or "").lower().replace("-", " ").split() if len(w) > 2}
    matches = [p for p in paused if words & set(f"{p['label']} {p['topic'].replace('_', ' ')}".lower().split())]
    if not matches:
        if len(paused) == 1 and not words:
            matches = paused
        else:
            return "Which one? I'm taking a break from: " + "; ".join(p["label"] for p in paused) + "."
    for p in matches:
        gate.resume(p["topic"])
    return "Okay, I'll tell you about " + " and ".join(p["label"] for p in matches) + " again."


def _action_set_message_limit(context: AppContext, arguments: dict) -> str:
    """Tool set_message_limit: a fixed cap on how many times a day she may speak up on her own, to a number
    (0 for none: she paces each kind by what you do with it, DEC-0171) or one more or fewer; urgent things,
    alarms and answers never count.
    """
    gate = getattr(context, "communication", None)
    if gate is None:
        return "I can't change that on this device."
    current = int(gate.settings()["daily_budget"] or 0)
    count = arguments.get("count")
    direction = str(arguments.get("direction") or "").lower()
    if count not in (None, ""):
        try:
            new = int(float(count))
        except (TypeError, ValueError):
            return f"How many times a day? Right now it's {current or 'no fixed limit'}."
    elif direction in ("less", "fewer", "down"):
        new = (current or 5) - 1
    elif direction in ("more", "up"):
        new = current + 1 if current else 0
    else:
        if not current:
            return ("There's no fixed limit: I pace each kind of message by what you open, use or dismiss. "
                    "Want a cap?")
        return f"Right now I speak up on my own at most {current} times a day. Want more or fewer?"
    new = gate.set_daily_budget(new)
    if new == 0:
        return "Okay: no fixed limit. I'll pace each kind of message by what you open, use or dismiss."
    return (
        f"Okay: at most {new} time{'s' if new != 1 else ''} a day on my own. "
        "Urgent things, alarms you set and answers to you don't count."
    )


def _learned(context, arguments: dict) -> str:
    """Tool list_learned_habits: what she has learned on her own, each with its evidence (core/learned.py)."""
    from core.learned import habits

    found = habits(context)
    if not found:
        return "Nothing yet: I learn how often you want each kind of message and how you like answers."
    return "What I've learned: " + "; ".join(f"{h.what} ({h.evidence.rstrip('.')})" for h in found) + "."


def _forget_learned(context, arguments: dict) -> str:
    """Tool reset_learned_habit: forgets one habit she learned, through the action `learned.reset`."""
    from core.actions import run_as_tool

    return run_as_tool(context, "learned.reset", {"habit": arguments.get("habit") or ""})


def register_communication_actions(registry: AssistantActionRegistry) -> None:
    """Registers the gate's tools: resume_message_topic, get_held_back_messages and
    set_message_limit; and list_learned_habits and reset_learned_habit (core/learned.py, LS-10).
    """
    registry.register(AssistantAction(
        name="list_learned_habits", domain="communication",
        description=("What MIA has learned about the person on her own (how often to offer each kind of message, "
                     "breaks from kinds he dismissed, how he likes answers), each with its evidence."),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_learned,
        trigger_phrases=("what have you learned about me", "what have you learned", "what habits have you learned",
                         "what did you learn about me"),
        subjects=("habits", "learned"),
    ))
    registry.register(AssistantAction(
        name="reset_learned_habit", domain="communication",
        description=("Forget one thing MIA learned on her own, by what it is (a kind of message's pace, a break, an "
                     "answer style). Never touches what the person set himself."),
        parameters={"type": "object", "properties": {
            "habit": {"type": "string", "description": "What she learned, in words."}}, "required": ["habit"]},
        handler=_forget_learned, prompt_arg="habit",
        trigger_phrases=("forget what you learned", "unlearn", "stop doing that habit", "reset what you learned"),
        subjects=("habit",),
    ))
    registry.register(AssistantAction(
        name="resume_message_topic", domain="communication",
        description="Bring back a kind of message MIA stopped sending because the user kept dismissing it.",
        parameters={"type": "object", "properties": {
            "topic": {"type": "string", "description": "Which kind, in the user's words, e.g. 'budget check-ins'."},
        }, "required": []},
        handler=_action_resume_message_topic,
        trigger_phrases=("you can tell me about", "start telling me about", "tell me about my budget again",
                         "bring back the", "stop taking a break", "you can remind me about"),
    ))
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
