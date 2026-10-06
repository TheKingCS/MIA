"""
core.mission_actions
======================

Every change the Missions, Skills and Character screens make (2026-10-06,
DEC-0017/0018), as action kinds on the contract in core/actions.py:
missions (add, edit, delete, complete, give up on with a reason, reopen),
their objectives (add, remove, count one more), the skill a mission
teaches, starting a skill's pathway, and prestige. Rewards are the
stores' own: completing a mission credits its XP, credits and skill XP
once (MissionManager.update_mission), to the person who approved it
(core.profile_manager.crediting). Missions, Skills and Character are in
CHILD_APPS, so these are child-safe, except deleting a mission.

A person only acts on missions that are theirs: their own, shared ones
(no owner), and group quests they're part of.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import (Field, Record, add_describe, delete_describe, delete_execute,
                                 edit_describe, edit_execute, field_dict, parse, record_form)


def _difficulties():
    from core.mission_manager import DIFFICULTY_LEVELS

    return tuple(DIFFICULTY_LEVELS)


ABANDON_LABELS = {"too_hard": "Too hard for now", "not_interested": "Not interested anymore",
                  "no_time": "No time right now", "other": "Something else"}

RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("mission", "mission", "mission_id", "get_mission", "add_mission", "update_mission", "delete_mission",
           store="missions", delete_note="Its rewards stay earned.", fields=(
               Field("name", "Name", "text", True),
               Field("icon", "Icon", "text", default="\U0001F4CB", quiet_default=True),
               Field("summary", "What it's about", "textarea"),
               Field("difficulty", "Difficulty", "choice", options=_difficulties(), default="NORMAL",
                     quiet_default=True),
               Field("region", "Area", "text", say="area"),
               Field("reward_xp", "XP reward", "int", default=0, say="XP"),
               Field("reward_credits", "Credits", "int", default=0, say="credits"),
           )),
)}

_OBJECTIVE = Field("description", "Objective", "text", True)
_TARGET = Field("target", "How many", "amount", default=1.0, say="target")
_TICK = Field("amount", "How many", "number", default=1.0)
_REASON = Field("reason", "Why", "choice", options=tuple(ABANDON_LABELS.values()), default="Something else")
_SKILL = Field("skill_id", "Skill", "pick", True, options=("skills",))
_SKILL_XP = Field("xp", "XP", "int", True)


# ------------------------------------------------------------------ whose missions


def _person(context):
    from core.person_settings import person_id

    return person_id(context)


def is_mine(mission, profile_id) -> bool:
    """Pure logic. Shared (no owner), mine, or a group quest I'm part of."""
    if not profile_id:
        return True
    return (mission.profile_id in (None, profile_id) or profile_id in mission.participant_profile_ids)


def _mission(context, params, active: bool = False):
    mission = _need(context, "missions").get_mission(str(params.get("mission_id", "")))
    if mission is None or not is_mine(mission, _person(context)):
        raise ActionError("That mission isn't there anymore.")
    if active and mission.status != "active":
        raise ActionError(f"{mission.name} is already {mission.status}.")
    return mission


def _guarded(fn):
    """A record kind, only on the person's own missions."""
    def run(context, params):
        _mission(context, params)
        return fn(context, params)
    return run


def _add(context, params) -> str:
    """A new mission is the person's own (not the whole household's)."""
    from core.record_actions import _store_call, title, values_of

    record = RECORDS["mission"]
    values = values_of(record, params, only_given=False, context=context)
    mission = _store_call(_need(context, "missions").add_mission, profile_id=_person(context), **values)
    return f"Added the mission {title(record, mission)}. Add its objectives next."


# ------------------------------------------------------------------ complete, give up, reopen


def _rewards_said(context, mission) -> str:
    if mission.rewards_credited:
        return "its rewards were already given"
    bits = []
    if mission.reward_xp:
        bits.append(f"+{mission.reward_xp} XP")
    if mission.reward_credits:
        bits.append(f"+{mission.reward_credits} credits")
    skills = getattr(context, "skills", None)
    for w in mission.skill_rewards:
        skill = skills.get_skill(w.skill_id) if skills is not None else None
        bits.append(f"+{w.xp} {skill.name if skill else w.skill_id}")
    return ", ".join(bits)


def _describe_complete(context, params) -> str:
    mission = _mission(context, params, active=True)
    done, total = context.missions.group_objective_progress(mission.mission_id)
    said = _rewards_said(context, mission)
    left = f" ({done} of {total} objectives done)" if total and done < total else ""
    return f"Complete the mission {mission.name}{left}" + (f": {said}" if said else "")


def _complete(context, params) -> str:
    mission = _mission(context, params, active=True)
    context.missions.update_mission(mission.mission_id, status="completed")
    return f"{mission.name} is complete. Well done."


def _reason(params) -> str:
    """The store's reason key, from the words on the form (or the key itself)."""
    raw = params.get("reason")
    if raw in ABANDON_LABELS:
        return raw
    label = parse(_REASON, raw)
    return next(k for k, v in ABANDON_LABELS.items() if v == label)


def _describe_abandon(context, params) -> str:
    mission = _mission(context, params, active=True)
    return f"Give up on {mission.name} for now ({ABANDON_LABELS[_reason(params)].lower()})"


def _abandon(context, params) -> str:
    mission = _mission(context, params, active=True)
    context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason=_reason(params))
    return f"{mission.name} is set aside. You can pick it back up any time."


def _describe_reopen(context, params) -> str:
    mission = _mission(context, params)
    if mission.status == "active":
        raise ActionError(f"{mission.name} is already active.")
    note = " (its rewards were already given, so they won't come twice)" if mission.rewards_credited else ""
    return f"Pick {mission.name} back up{note}"


def _reopen(context, params) -> str:
    mission = _mission(context, params)
    context.missions.update_mission(mission.mission_id, status="active", abandon_reason="")
    return f"{mission.name} is active again."


# ------------------------------------------------------------------ objectives


def _objective(context, params):
    mission = _mission(context, params)
    try:
        index = int(params.get("index"))
        objective = mission.objectives[index]
    except (TypeError, ValueError, IndexError):
        raise ActionError("That objective isn't there anymore.") from None
    return mission, index, objective


def _describe_objective_add(context, params) -> str:
    mission = _mission(context, params)
    what, target = parse(_OBJECTIVE, params.get("description")), parse(_TARGET, params.get("target"))
    return f"Add to {mission.name}: {what}" + (f" (×{target:g})" if target != 1 else "")


def _objective_add(context, params) -> str:
    mission = _mission(context, params)
    context.missions.add_objective(mission.mission_id, parse(_OBJECTIVE, params.get("description")), "tally",
                                   max(parse(_TARGET, params.get("target")), 1.0))
    return f"The objective is on {mission.name}."


def _describe_objective_delete(context, params) -> str:
    mission, _index, objective = _objective(context, params)
    return f"Take “{objective.description}” off {mission.name}"


def _objective_delete(context, params) -> str:
    mission, index, objective = _objective(context, params)
    context.missions.delete_objective(mission.mission_id, index)
    return f"“{objective.description}” is off {mission.name}."


def _describe_tick(context, params) -> str:
    mission, index, objective = _objective(context, params)
    if mission.status != "active":
        raise ActionError(f"{mission.name} is {mission.status}.")
    if objective.metric_type != "tally":
        raise ActionError("That one counts itself (from its task or trip).")
    amount = parse(_TICK, params.get("amount"))
    if not amount:
        raise ActionError("How many has to be more than nothing.")
    now = max(objective.progress + amount, 0)
    return f"{objective.description}: {objective.progress:g} → {now:g} of {objective.target:g}"


def _tick(context, params) -> str:
    mission, index, objective = _objective(context, params)
    amount = parse(_TICK, params.get("amount"))
    if objective.progress + amount < 0:
        amount = -objective.progress
    context.missions.increment_tally(mission.mission_id, index, amount)
    if context.missions.is_objective_complete(mission.mission_id, index):
        return f"“{objective.description}” is done."
    return "Counted."


# ------------------------------------------------------------------ the skill a mission teaches


def _skill(context, params):
    skill = _need(context, "skills").get_skill(str(params.get("skill_id", "")))
    if skill is None:
        raise ActionError("Pick a skill.")
    return skill


def _describe_skill_reward(context, params) -> str:
    mission = _mission(context, params)
    skill, xp = _skill(context, params), parse(_SKILL_XP, params.get("xp"))
    if xp <= 0:
        raise ActionError("XP has to be more than 0.")
    now = " (it's already complete, so it counts now)" if mission.status == "completed" else ""
    return f"{mission.name} also teaches {skill.name}: +{xp} XP{now}"


def _skill_reward(context, params) -> str:
    mission = _mission(context, params)
    skill = _skill(context, params)
    context.missions.add_skill_reward(mission.mission_id, skill.skill_id, parse(_SKILL_XP, params.get("xp")))
    return f"{mission.name} teaches {skill.name}."


# ------------------------------------------------------------------ pathways and prestige


def _pathway(context, params):
    pathways = _need(context, "pathways")
    pathway = pathways.get_pathway(str(params.get("pathway_id", "")))
    if pathway is None or not pathway.steps:
        raise ActionError("That pathway isn't there anymore.")
    who = _person(context)
    status = pathways.status_for(who, pathway.pathway_id) if who else None
    if status is not None and status.status == "active":
        raise ActionError(f"You're already on {pathway.name}.")
    return pathways, pathway, who


def _describe_pathway(context, params) -> str:
    _pathways, pathway, _who = _pathway(context, params)
    return f"Start the pathway {pathway.name}: first, {pathway.steps[0].name} ({len(pathway.steps)} steps)"


def _start_pathway(context, params) -> str:
    pathways, pathway, who = _pathway(context, params)
    if not who:
        raise ActionError("Pathways belong to a person; sign in first.")
    mission = pathways.start_pathway(who, pathway.pathway_id)
    if mission is None:
        raise ActionError("That pathway can't start right now.")
    if mission.profile_id is None:
        context.missions.update_mission(mission.mission_id, profile_id=who)
    return f"{pathway.name} has started. Your first mission: {mission.name}."


def _profile(context):
    who = _person(context)
    profile = _need(context, "profiles").get_profile(who) if who else None
    if profile is None:
        raise ActionError("Sign in first.")
    return profile


def _describe_prestige(context, params) -> str:
    from core.leveling import is_eligible_to_prestige, prestige_color_for_tier

    profile = _profile(context)
    if not is_eligible_to_prestige(profile.total_xp, profile.prestige_tier):
        raise ActionError("Prestige opens once you max out level 100.")
    return (f"Prestige: start again at level 1 with a {prestige_color_for_tier(profile.prestige_tier + 1)} badge. "
            "Your XP, skills and rewards all stay")


def _prestige(context, params) -> str:
    profile = _profile(context)
    tier = context.profiles.prestige(profile.profile_id)
    if tier is None:
        raise ActionError("Prestige opens once you max out level 100.")
    return f"Prestige {tier}! A new badge, the same you."


# ------------------------------------------------------------------ the kinds


def _kinds() -> list[ActionType]:
    record = RECORDS["mission"]
    names = {f.name: f.label for f in record.fields}
    return [
        ActionType("mission.add", "Add mission", dict(names), add_describe(record), _add, True),
        ActionType("mission.edit", "Edit", {"mission_id": "the mission", **names},
                   _guarded(edit_describe(record)), _guarded(edit_execute(record)), True),
        ActionType("mission.delete", "Delete", {"mission_id": "the mission"},
                   _guarded(delete_describe(record)), _guarded(delete_execute(record))),
        ActionType("mission.complete", "Complete", {"mission_id": "the mission"}, _describe_complete, _complete, True),
        ActionType("mission.abandon", "Give up for now", {"mission_id": "the mission", "reason": "/".join(ABANDON_LABELS)},
                   _describe_abandon, _abandon, True),
        ActionType("mission.reopen", "Pick back up", {"mission_id": "the mission"}, _describe_reopen, _reopen, True),
        ActionType("objective.add", "Add objective", {"mission_id": "the mission", "description": "", "target": "how many"},
                   _describe_objective_add, _objective_add, True),
        ActionType("objective.delete", "Remove", {"mission_id": "the mission", "index": "which objective (0 first)"},
                   _describe_objective_delete, _objective_delete, True),
        ActionType("objective.tick", "+1", {"mission_id": "the mission", "index": "which objective (0 first)",
                                            "amount": "default 1"}, _describe_tick, _tick, True),
        ActionType("mission.skill_reward", "Add skill", {"mission_id": "the mission", "skill_id": "", "xp": ""},
                   _describe_skill_reward, _skill_reward, True),
        ActionType("pathway.start", "Start", {"pathway_id": "the pathway"}, _describe_pathway, _start_pathway, True),
        ActionType("character.prestige", "Prestige", {}, _describe_prestige, _prestige, True),
    ]


MISSION_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(MISSION_ACTIONS)


def form_spec() -> dict:
    forms = {"mission": record_form(RECORDS["mission"])}
    forms["objective"] = {"noun": "objective", "id_param": "mission_id", "fields": [field_dict(_OBJECTIVE), field_dict(_TARGET)]}
    forms["abandon"] = {"noun": "mission", "id_param": "mission_id", "fields": [field_dict(_REASON)]}
    forms["skill_reward"] = {"noun": "skill", "id_param": "mission_id", "fields": [field_dict(_SKILL), field_dict(_SKILL_XP)]}
    return forms
