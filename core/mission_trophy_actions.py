"""
core.mission_trophy_actions
=============================

A mission's rewards beyond XP, and its objectives counted from records, from the screen and by voice (the game
layer, step 2; DEC-0125, both ways). The actions `mission.trophy` (add an item, structure, song, knowledge, recipe or
skill as a reward) and `objective.count` (an objective that counts a lifetime stat from now on: "put up 20 jars")
are the Missions page's; the tools `add_mission_reward` and `count_toward_mission` say the same by voice. The logic
is core/mission_trophies.py; the store is core/mission_manager.py.
"""

from __future__ import annotations

import re

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction


def _mission(context, params):
    """The person's own active mission the params name (core/mission_actions._mission); ActionError otherwise."""
    from core.mission_actions import _mission as mine

    return mine(context, params, active=True)


def _target(params) -> float:
    """The objective's target from the params: a number above 0, else ActionError."""
    try:
        target = float(params.get("target"))
    except (TypeError, ValueError):
        raise ActionError("How many?") from None
    if target <= 0:
        raise ActionError("The target has to be more than 0.")
    return target


# What he says for a stat that its words don't hold.
ALIASES = {"pounds": "produce_pounds", "harvest": "produce_pounds", "harvested": "produce_pounds",
           "vegetables": "produce_pounds", "canning": "jars_canned", "canned": "jars_canned", "jars": "jars_canned",
           "meals": "meals_cooked", "cooking": "meals_cooked", "workouts": "workout_hours_logged",
           "exercise": "workout_hours_logged", "songs": "songs_learned", "song": "songs_learned",
           "fish": "fish_caught", "catches": "fish_caught"}


def _stat(params) -> str:
    """The lifetime stat the params name (core/mission_trophies.STATS, by id or its words); ActionError otherwise."""
    from core.mission_trophies import STATS

    said = str(params.get("stat", "") or "").strip().lower()
    if said in ALIASES:
        return ALIASES[said]
    for stat_id, words in STATS.items():
        if said in (stat_id, words) or said and said in words.split():
            return stat_id
    raise ActionError("Count one of: " + ", ".join(STATS.values()) + ".")


def _describe_trophy(context, params) -> str:
    """What mission.trophy says: the reward added to which mission (a bad kind or name refused here)."""
    from core.mission_trophies import said, trophy

    mission = _mission(context, params)
    try:
        t = trophy(params.get("kind"), params.get("name"), params.get("ref", ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"{mission.name} also rewards {said(t)}"


def _trophy(context, params) -> str:
    """Does mission.trophy: the reward is on the mission, earned when it's completed."""
    from core.mission_trophies import said, trophy

    mission = _mission(context, params)
    t = trophy(params.get("kind"), params.get("name"), params.get("ref", ""))
    context.missions.add_trophy(mission.mission_id, t["kind"], t["name"], t["ref"])
    return f"{mission.name} now rewards {said(t)}."


def _description(params, stat_id: str, target: float) -> str:
    """Pure logic. The objective's words: what was given, else "20 jars put up"."""
    from core.mission_trophies import STATS

    given = " ".join(str(params.get("description", "") or "").split())
    return given or f"{target:g} {STATS[stat_id]}"


def _describe_count(context, params) -> str:
    """What objective.count says: the objective, counted from what's logged from now on."""
    mission, stat_id, target = _mission(context, params), _stat(params), _target(params)
    return f"Add to {mission.name}: {_description(params, stat_id, target)}, counted from what you log from now on"


def _count(context, params) -> str:
    """Does objective.count: a records objective starting from the stat's value now."""
    mission, stat_id, target = _mission(context, params), _stat(params), _target(params)
    words = _description(params, stat_id, target)
    context.missions.add_objective(mission.mission_id, words, "records", target, stat_id=stat_id)
    return f"{mission.name} counts {words} from what you log."


TROPHY_ACTIONS = {k.kind: k for k in (
    ActionType("mission.trophy", "Add reward", {"mission_id": "the mission", "kind": "item/structure/song/knowledge/"
               "recipe/skill", "name": "what it is", "ref": "a recipe or skill id (optional)"},
               _describe_trophy, _trophy),
    ActionType("objective.count", "Count from records", {"mission_id": "the mission", "stat": "what to count",
               "target": "how many", "description": "(optional)"}, _describe_count, _count),
)}
ACTION_TYPES.update(TROPHY_ACTIONS)


_FILLER = re.compile(r"^(?:my|the|our|that)\s+|\s+(?:mission|quest)$")


def _named(context, name: str):
    """The person's active mission whose name matches (exactly, else the one containing it), or None. The model says
    "my canning mission" for a mission called "Canning": "my"/"the" in front and "mission" after are dropped."""
    from core.mission_actions import is_mine
    from core.person_settings import person_id

    name = " ".join(str(name or "").lower().split())
    name = _FILLER.sub("", _FILLER.sub("", name))
    who = person_id(context)
    mine = [m for m in context.missions.all_missions() if m.status == "active" and is_mine(m, who)]
    exact = [m for m in mine if m.name.lower() == name]
    near = [m for m in mine if name and name in m.name.lower()]
    return exact[0] if exact else near[0] if len(near) == 1 else None


def _run(context, kind: str, params: dict) -> str:
    """Runs an action as a tool: its description first (refusals said), then the change."""
    try:
        ACTION_TYPES[kind].describe(context, params)
        return ACTION_TYPES[kind].execute(context, params)
    except ActionError as problem:
        return str(problem)


def _add_reward(context, arguments: dict) -> str:
    """Tool add_mission_reward: a reward beyond XP on a mission (mission.trophy)."""
    mission = _named(context, arguments.get("mission_name", ""))
    if mission is None:
        return f"I don't have an active mission called '{arguments.get('mission_name', '')}'."
    return _run(context, "mission.trophy", {"mission_id": mission.mission_id, "kind": arguments.get("kind", ""),
                                            "name": arguments.get("name", ""), "ref": arguments.get("ref", "")})


def _count_toward(context, arguments: dict) -> str:
    """Tool count_toward_mission: an objective counted from his records (objective.count)."""
    mission = _named(context, arguments.get("mission_name", ""))
    if mission is None:
        return f"I don't have an active mission called '{arguments.get('mission_name', '')}'."
    return _run(context, "objective.count", {"mission_id": mission.mission_id, "stat": arguments.get("stat", ""),
                                             "target": arguments.get("target"),
                                             "description": arguments.get("description", "")})


def register_mission_trophy_actions(registry) -> None:
    """Registers add_mission_reward and count_toward_mission."""
    from core.mission_trophies import KINDS, STATS

    registry.register(AssistantAction(
        name="add_mission_reward", domain="missions",
        description="Make a mission reward something besides XP: an item crafted, a structure built, a song "
                    "unlocked, knowledge mastered, a recipe or a skill learned. Earned when the mission is completed.",
        parameters={"type": "object", "properties": {
            "mission_name": {"type": "string", "description": "the mission's name"},
            "kind": {"type": "string", "description": "one of " + ", ".join(KINDS)},
            "name": {"type": "string", "description": "what it is, e.g. 'Chicken coop'"},
            "ref": {"type": "string", "description": "a recipe or skill id, only if known"}},
            "required": ["mission_name", "kind", "name"]},
        handler=_add_reward, trigger_phrases=("mission reward", "reward for the mission", "mission should reward",
                                              "as the reward", "unlocks the song", "unlock the song"),
    ))
    registry.register(AssistantAction(
        name="count_toward_mission", domain="missions",
        description="Add an objective that counts itself from his records from now on (pounds harvested, eggs, "
                    "jars put up, meals cooked, workout hours...), e.g. 'put up 20 jars' on his canning mission.",
        parameters={"type": "object", "properties": {
            "mission_name": {"type": "string", "description": "the mission's name"},
            "stat": {"type": "string", "description": "what to count: " + ", ".join(STATS.values())},
            "target": {"type": "number", "description": "how many"},
            "description": {"type": "string", "description": "the objective's words, only if he gave them"}},
            "required": ["mission_name", "stat", "target"]},
        handler=_count_toward, trigger_phrases=("count toward the mission", "counts toward the mission",
                                                "count it from my", "count from my harvest", "count my jars",
                                                "count my eggs"),
    ))
