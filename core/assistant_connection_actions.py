"""
core.assistant_connection_actions
===================================

Connections by voice (DEC-0146, DEC-0125's both-ways rule; the screen is web/connections.html): "don't bring that up"
after MIA ties something you said to a project from weeks ago (it runs `connection.decline` on the connection she just
raised, or the newest one waiting), and "what connections have you noticed?". Each change is the same action the
screen runs (core/web_connections.py), so it's undoable.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _action_decline(context, arguments: dict) -> str:
    """Tool dont_bring_that_up: the connection she just raised (or the newest waiting) is never raised again."""
    from core.actions import ACTION_TYPES, ActionError
    from core.web_connections import latest

    found = latest(context)
    if found is None:
        return "There's nothing I've been tying together to stop."
    try:
        ACTION_TYPES["connection.decline"].describe(context, {"connection_id": found["id"]})
        return ACTION_TYPES["connection.decline"].execute(context, {"connection_id": found["id"]})
    except ActionError as problem:
        return str(problem)


def _action_list(context, arguments: dict) -> str:
    """Tool list_connections: the ties MIA is holding, and the things she's been asked not to raise."""
    from core.web_connections import screen

    page = screen(context)
    if not page.get("available"):
        return "I'm not keeping connections on this MIA."
    parts = [f"you said “{c['said']}”, which ties into your {c['kind']} “{c['name']}”" for c in page["waiting"]]
    out = ("I'm holding " + "; ".join(parts) + ".") if parts else "I'm not holding any connections right now."
    if page["quiet"]:
        out += " You asked me not to bring up: " + ", ".join(q["name"] for q in page["quiet"]) + "."
    return out


def register_connection_actions(registry: AssistantActionRegistry) -> None:
    """Registers the connections tools: don't bring that up, and list them."""
    registry.register(AssistantAction(
        name="dont_bring_that_up", domain="connections",
        description="The user doesn't want MIA to bring up the connection she just made (or is holding) between what "
                    "they said and an older project, goal or idea; she never raises that thing again until allowed.",
        parameters={"type": "object", "properties": {}}, handler=_action_decline,
        trigger_phrases=("don't bring that up", "dont bring that up", "stop bringing that up", "don't mention that again",
                         "leave that project out of it", "stop connecting"),
    ))
    registry.register(AssistantAction(
        name="list_connections", domain="connections",
        description="List the connections MIA is holding between things the user said and their older projects, goals "
                    "and ideas, and the things they asked her not to raise.",
        parameters={"type": "object", "properties": {}}, handler=_action_list,
        trigger_phrases=("what connections", "connections have you noticed", "what are you tying together"),
    ))
