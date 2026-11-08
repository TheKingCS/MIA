"""
core.assistant_world_actions
==============================

Living Worlds by voice (DEC-0134 Phase 1, DEC-0125's both-ways rule; the screen is web/worlds.html): "what worlds do
I have?", "make a world called Emberfall, a fantasy frontier", "start a campaign in Emberfall called The Salt Road",
"set a quest in The Salt Road: find the lost cartographer", "I finished the cartographer quest", "pause The Salt
Road". Each runs the same world.* action as the screen (core/web_worlds.py), so it's undoable, and everything stays
fiction (no real XP, fictional events). Playing a turn with MIA as Dungeon Master is Phase 2 and waits on Zac.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry

_S = {"type": "string"}


def _run(context, kind: str, params: dict) -> str:
    """Runs a world action as the screen would (describe's checks, then execute); the problem as a line."""
    from core.actions import ACTION_TYPES, ActionError

    try:
        ACTION_TYPES[kind].describe(context, params)
        return ACTION_TYPES[kind].execute(context, params)
    except ActionError as problem:
        return str(problem)


def _action_list(context, arguments: dict) -> str:
    """Tool list_worlds: the person's worlds, each with its campaigns and their state."""
    from core.web_worlds import screen

    page = screen(context)
    if not page.get("available"):
        return "Living Worlds isn't set up on this MIA."
    if not page["worlds"]:
        return "You haven't made a world yet. Say \"make a world called…\" and tell me what it's like."
    parts = []
    for w in page["worlds"]:
        runs = ", ".join(f"{c['name']} ({c['status_word'].lower()}, {c['open']} open quests)" for c in w["campaigns"])
        parts.append(f"{w['name']}" + (f", {w['genre']}" if w["genre"] else "") + (f": {runs}" if runs else ": no campaign yet"))
    return "Your worlds: " + "; ".join(parts) + "."


def _action_make_world(context, arguments: dict) -> str:
    """Tool make_world: a new fictional world."""
    return _run(context, "world.universe_add", {k: arguments.get(k, "") for k in ("name", "genre", "premise", "rules")})


def _action_start_campaign(context, arguments: dict) -> str:
    """Tool start_campaign: a new campaign in one of the person's worlds."""
    from core.web_worlds import find_world

    world = find_world(context, arguments.get("world"))
    if world is None:
        return "Which world? Say its name (\"what worlds do I have?\" lists them)."
    return _run(context, "world.campaign_add", {"universe_id": world.universe_id, "name": arguments.get("name", ""),
                                                "summary": arguments.get("summary", "")})


def _action_add_quest(context, arguments: dict) -> str:
    """Tool add_world_quest: a quest the person sets in one of their campaigns (the last played when none is named)."""
    from core.web_worlds import find_campaign

    campaign = find_campaign(context, arguments.get("campaign"))
    if campaign is None:
        return "Which campaign? Say its name."
    return _run(context, "world.quest_add", {"campaign_id": campaign.campaign_id, "name": arguments.get("name", ""),
                                             "objective": arguments.get("objective", "")})


def _action_finish_quest(context, arguments: dict) -> str:
    """Tool finish_world_quest: an open fictional quest marked finished, by words from its name."""
    book = getattr(context, "living_worlds", None)
    said = " ".join(str(arguments.get("quest") or "").lower().split())
    found = [q for q in (book.quests if book is not None else []) if q.status == "open" and said and
             (said in q.name.lower() or q.name.lower() in said)]
    if not found:
        return "Which quest? Say a word from its name."
    return _run(context, "world.quest_done", {"quest_id": found[-1].quest_id})


def _action_campaign_status(context, arguments: dict) -> str:
    """Tool set_campaign_status: pause, pick back up or end a campaign."""
    from core.web_worlds import find_campaign

    campaign = find_campaign(context, arguments.get("campaign"))
    if campaign is None:
        return "Which campaign? Say its name."
    words = str(arguments.get("status") or "").lower()
    status = ("paused" if "pause" in words else "ended" if any(w in words for w in ("end", "finish", "close"))
              else "active")
    return _run(context, "world.campaign_status", {"campaign_id": campaign.campaign_id, "status": status})


def register_world_actions(registry: AssistantActionRegistry) -> None:
    """Registers Living Worlds' tools: list, make a world, start a campaign, set and finish quests, campaign status."""
    registry.register(AssistantAction(
        name="list_worlds", domain="worlds",
        description="List the user's fictional Living Worlds: each world with its campaigns and their open quests.",
        parameters={"type": "object", "properties": {}}, handler=_action_list,
        trigger_phrases=("my worlds", "what worlds", "my campaigns", "living worlds"),
    ))
    registry.register(AssistantAction(
        name="make_world", domain="worlds",
        description="Make a new fictional world for the user's Living Worlds (a setting for campaigns; fiction only).",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "the world's name."},
            "genre": {"type": "string", "description": "optional: fantasy, sci-fi, frontier..."},
            "premise": {"type": "string", "description": "optional: the premise in a sentence."},
            "rules": {"type": "string", "description": "optional: tone and house rules."}}, "required": ["name"]},
        handler=_action_make_world,
        trigger_phrases=("make a world", "create a world", "new world called", "build a world"),
    ))
    registry.register(AssistantAction(
        name="start_campaign", domain="worlds",
        description="Begin a new campaign in one of the user's Living Worlds.",
        parameters={"type": "object", "properties": {
            "world": {"type": "string", "description": "the world's name."},
            "name": {"type": "string", "description": "the campaign's name."},
            "summary": {"type": "string", "description": "optional: where it starts."}}, "required": ["world", "name"]},
        handler=_action_start_campaign,
        trigger_phrases=("start a campaign", "begin a campaign", "new campaign"),
    ))
    registry.register(AssistantAction(
        name="add_world_quest", domain="worlds",
        description="Set a fictional quest in one of the user's campaigns (the last played if none is named). "
                    "Fiction only: no real XP.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "the quest."},
            "objective": {"type": "string", "description": "optional: what finishing it means."},
            "campaign": {"type": "string", "description": "optional: the campaign's name."}}, "required": ["name"]},
        handler=_action_add_quest,
        trigger_phrases=("set a quest in", "add a quest to the campaign", "quest in my campaign"),
    ))
    registry.register(AssistantAction(
        name="finish_world_quest", domain="worlds",
        description="Mark one of the user's open fictional quests finished.",
        parameters={"type": "object", "properties": {"quest": {"type": "string", "description": "words from its name."}},
                    "required": ["quest"]},
        handler=_action_finish_quest,
        trigger_phrases=("finished the quest", "quest is done", "completed the quest"),
    ))
    registry.register(AssistantAction(
        name="set_campaign_status", domain="worlds",
        description="Pause a campaign, pick it back up, or end it.",
        parameters={"type": "object", "properties": {
            "campaign": {"type": "string", "description": "the campaign's name."},
            "status": {"type": "string", "description": "pause, resume or end."}}, "required": ["campaign", "status"]},
        handler=_action_campaign_status,
        trigger_phrases=("pause the campaign", "resume the campaign", "end the campaign", "pick the campaign back up"),
    ))
