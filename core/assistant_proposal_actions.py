"""
core.assistant_proposal_actions
=================================

Mission ideas and field recordings by voice (DEC-0125; the screens are the
Missions page's idea card and the Journal's From the Field, core/
web_proposals.py). "Suggest a mission" asks the model for one idea (checked
in code before it's kept); "accept it" / "set it aside" decide it.
"Any field recordings?" reads the waiting ones; "keep the first one" or
"leave it out" decides one. The decisions are the same actions the screens
use, so undo takes them back.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _run(context, kind: str, params: dict) -> str:
    """Runs one of core/web_proposals.py's actions and says what happened (or why not)."""
    from core.actions import run_as_tool

    return run_as_tool(context, kind, params)


def _waiting_idea(context):
    """The person's pending mission idea, or None."""
    from core.web_proposals import _pid

    discovery = getattr(context, "discovery", None)
    return discovery.pending_proposal_for(_pid(context)) if discovery is not None else None


def _suggest(context, arguments: dict) -> str:
    """Tool suggest_mission: one mission idea from the person's own skills, projects and recent missions."""
    from core.web_proposals import suggest

    waiting = _waiting_idea(context)
    if waiting is not None:
        return f"There's already an idea waiting: {waiting.name}. {waiting.summary} Accept it, or set it aside."
    result = suggest(context)
    if "error" in result:
        return result["error"]
    idea = result["idea"]
    trains = ", ".join(idea["skills"])
    return (f"How about this: {idea['name']}. {idea['summary']}" + (f" It trains {trains}" if trains else "")
            + f" for {idea['xp']} XP. Want it?")


def _decide_idea(context, arguments: dict) -> str:
    """Tool decide_mission_idea: accepts the waiting idea, or sets it aside."""
    waiting = _waiting_idea(context)
    if waiting is None:
        return "There's no mission idea waiting. Ask me to suggest one."
    kind = "mission_idea.accept" if arguments.get("accept", True) else "mission_idea.reject"
    return _run(context, kind, {"proposal_id": waiting.proposal_id})


def _pending(context) -> list:
    """The person's field recordings waiting for review, oldest first (as the Journal page lists them)."""
    from core.web_proposals import field_captures

    return field_captures(context)["captures"]


def _list(context, arguments: dict) -> str:
    """Tool list_field_recordings: the MIA Lite recordings waiting, numbered, with their words."""
    rows = _pending(context)
    if not rows:
        return "No field recordings waiting."
    return (f"{len(rows)} waiting: " + " ".join(f"{n}. {r['title']}: \"{r['words'][:160]}\"" for n, r in enumerate(rows, 1))
            + " Say keep or leave out, with its number.")


def _decide_capture(context, arguments: dict) -> str:
    """Tool decide_field_recording: keeps one waiting recording in the journal, or leaves it out (by its number)."""
    rows = _pending(context)
    if not rows:
        return "No field recordings waiting."
    try:
        number = int(arguments.get("number") or 1)
    except (TypeError, ValueError):
        number = 1
    if not 1 <= number <= len(rows):
        return f"There are {len(rows)} waiting; which number?"
    kind = "capture.keep" if arguments.get("keep", True) else "capture.discard"
    return _run(context, kind, {"capture_id": rows[number - 1]["id"]})


def register_proposal_actions(registry) -> None:
    """Registers suggest_mission, decide_mission_idea (domain missions), list_field_recordings and
    decide_field_recording (domain journal)."""
    b = {"type": "boolean"}
    registry.register(AssistantAction(
        name="suggest_mission", domain="missions",
        description="MIA thinks up one new mission from the user's skills, projects and recent missions, for them to accept.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_suggest,
        trigger_phrases=("suggest a mission", "give me a mission", "mission idea", "what should i work on"),
    ))
    registry.register(AssistantAction(
        name="decide_mission_idea", domain="missions",
        description="Accepts the mission idea MIA suggested (making it a mission), or sets it aside.",
        parameters={"type": "object", "properties": {"accept": {**b, "description": "True to accept, false to set it aside."}},
                    "required": ["accept"]},
        handler=_decide_idea,
        trigger_phrases=("accept the mission", "accept that idea", "set the idea aside", "not that mission"),
    ))
    registry.register(AssistantAction(
        name="list_field_recordings", domain="journal",
        description="The voice notes from MIA Lite waiting to be kept in the journal or left out.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_list,
        trigger_phrases=("field recordings", "field captures", "voice notes from the field", "mia lite recordings"),
    ))
    registry.register(AssistantAction(
        name="decide_field_recording", domain="journal",
        description="Keeps one waiting field recording in the journal, or leaves it out.",
        parameters={"type": "object", "properties": {
            "number": {"type": "integer", "description": "Its number in the list, from 1."},
            "keep": {**b, "description": "True to keep it in the journal, false to leave it out."}},
            "required": ["keep"]},
        handler=_decide_capture,
        trigger_phrases=("keep the recording", "keep that recording", "leave the recording out"),
    ))
