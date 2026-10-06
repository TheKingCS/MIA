"""
core.web_progress
===================

Missions, Skills and Character on the web (2026-10-06, DEC-0017/0018,
answering H-0013): everything the PC app's screens show, assembled here
so `web/` holds no logic. Served as `/api/missions`, `/api/skills` and
`/api/character`; changes are the action kinds in core/mission_actions.py.

Every number is the stores' own: levels from core.leveling and
core.skill_leveling (derived from total XP, never stored), objective
progress from MissionManager (trip and task objectives count themselves),
challenge chains and hidden achievements from core.rewards_manager.
Rarity (Common to Legendary) is only ever the rewards' own; missions
carry their difficulty, never an invented rarity (H-0013 item 4).
Reading a page never changes anything (no unlock scans here).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

RECENT_DAYS = 60


def _person(context):
    from core.person_settings import person_id

    return person_id(context)


def _profile(context):
    pid = _person(context)
    profiles = getattr(context, "profiles", None)
    return profiles.get_profile(pid) if profiles is not None and pid else None


def level_block(profile) -> dict:
    """The person's level, as every screen shows it."""
    from core.leveling import compute_prestige_level_progress, is_eligible_to_prestige, prestige_color_for_tier

    if profile is None:
        return {"level": 1, "xp_into_level": 0, "xp_for_level": 100, "total_xp": 0, "credits": 0, "prestige_tier": 0,
                "prestige_color": None, "can_prestige": False, "name": ""}
    tier = profile.prestige_tier
    level, into, needed = compute_prestige_level_progress(profile.total_xp, tier)
    return {"level": level, "xp_into_level": into, "xp_for_level": needed, "total_xp": profile.total_xp,
            "credits": profile.total_credits, "prestige_tier": tier,
            "prestige_color": prestige_color_for_tier(tier) if tier > 0 else None,
            "next_prestige_color": prestige_color_for_tier(tier + 1),
            "can_prestige": is_eligible_to_prestige(profile.total_xp, tier), "name": profile.name}


def _rarity(index: int) -> dict:
    from core.rarity import rarity_name_for_index

    return {"rarity": index, "rarity_name": rarity_name_for_index(index)}


# ------------------------------------------------------------------ Missions


def missions_page(context, today: Optional[date] = None) -> dict:
    from core.mission_actions import ABANDON_LABELS, RECORDS, form_spec, is_mine

    today = today or date.today()
    missions = getattr(context, "missions", None)
    profile = _profile(context)
    pid = profile.profile_id if profile is not None else None
    page = {"available": missions is not None, "forms": form_spec(), "as_of": today.isoformat(),
            "me": level_block(profile)}
    if missions is None:
        return page
    skills = getattr(context, "skills", None)
    page["skills"] = [{"id": s.skill_id, "name": f"{s.icon} {s.name}"} for s in
                      sorted(skills.all_skills(), key=lambda s: (s.category, s.name))] if skills is not None else []
    names = {p.profile_id: p.name for p in context.profiles.list_profiles()} if getattr(context, "profiles", None) else {}
    pathway_of = _pathway_steps(context, pid)
    recurring = getattr(context, "recurring_missions", None)
    maintenance, tasks, kitchen = (getattr(context, a, None) for a in ("maintenance", "tasks", "kitchen"))

    def card(m) -> dict:
        objectives = []
        for i, o in enumerate(m.objectives):
            progress = missions.objective_progress(m.mission_id, i) or 0.0
            objectives.append({"index": i, "description": o.description, "progress": round(progress, 2),
                               "target": o.target, "done": progress >= o.target, "counts_itself": o.metric_type != "tally",
                               "for": names.get(o.assigned_profile_id) if o.assigned_profile_id else None})
        done, total = missions.group_objective_progress(m.mission_id)
        skill_rewards = []
        for w in m.skill_rewards:
            skill = skills.get_skill(w.skill_id) if skills is not None else None
            skill_rewards.append({"id": w.skill_id, "name": skill.name if skill else w.skill_id,
                                  "icon": skill.icon if skill else "", "xp": w.xp})
        asset = maintenance.get_asset(m.maintenance_asset_id) if maintenance is not None and m.maintenance_asset_id else None
        task = tasks.get_task(m.task_id) if tasks is not None and m.task_id else None
        recipes = [r.name for r in (kitchen.get_recipe(rid) for rid in m.recipe_unlocks) if r is not None] \
            if kitchen is not None else []
        streak = recurring.current_streak_for_template(m.recurring_template_id, today) \
            if recurring is not None and m.recurring_template_id and m.recurring_kind == "daily" else None
        mine = missions.individual_objective_progress(m.mission_id, pid) if pid and m.participant_profile_ids else None
        return {
            "id": m.mission_id, "name": m.name, "icon": m.icon, "summary": m.summary, "area": m.region,
            "difficulty": m.difficulty, "type": m.mission_type, "status": m.status,
            "from_mia": m.assigned_by == "mia", "abandon_reason": ABANDON_LABELS.get(m.abandon_reason),
            "reward_xp": m.reward_xp, "reward_credits": m.reward_credits, "skill_rewards": skill_rewards,
            "rewards_given": m.rewards_credited, "objectives": objectives, "done": done, "total": total,
            "percent": round(100 * done / total) if total else (100 if m.status == "completed" else 0),
            "ready": bool(total) and done == total and m.status == "active",
            "daily": m.recurring_kind == "daily", "weekly": m.recurring_kind == "weekly", "streak": streak,
            "party": [names.get(p, "someone") for p in m.participant_profile_ids],
            "my_part": {"done": mine[0], "total": mine[1]} if mine and mine[1] else None,
            "pathway": pathway_of.get(m.mission_id),
            "asset": {"id": asset.asset_id, "name": asset.name} if asset is not None else None,
            "task": task.title if task is not None else None, "unlocks_recipes": recipes,
            "updated": (m.updated_at or m.created_at or "")[:10],
            "values": {f.name: getattr(m, f.name) for f in RECORDS["mission"].fields},
        }

    mine = [m for m in missions.all_missions() if is_mine(m, pid)]
    since = (today - timedelta(days=RECENT_DAYS)).isoformat()
    cards = [card(m) for m in mine if m.status == "active" or (m.updated_at or "")[:10] >= since]
    order = {"HARD": 0, "NORMAL": 1, "EASY": 2}
    active = [c for c in cards if c["status"] == "active"]
    page["daily"] = [c for c in active if c["daily"] or c["weekly"]]
    page["active"] = sorted((c for c in active if not (c["daily"] or c["weekly"])),
                            key=lambda c: (not c["ready"], c["from_mia"], order.get(c["difficulty"], 1), c["name"].lower()))
    page["completed"] = sorted((c for c in cards if c["status"] == "completed"), key=lambda c: c["updated"], reverse=True)
    page["set_aside"] = sorted((c for c in cards if c["status"] == "abandoned"), key=lambda c: c["updated"], reverse=True)
    page["counts"] = {"active": len(page["active"]) + len(page["daily"]), "ready": sum(c["ready"] for c in active),
                      "completed": sum(1 for m in mine if m.status == "completed")}
    return page


def _pathway_steps(context, pid) -> dict:
    """mission id -> "Pathway name · step 2 of 5", for the person's active pathways."""
    pathways = getattr(context, "pathways", None)
    if pathways is None or not pid:
        return {}
    found = {}
    for progress in pathways.progress_for_profile(pid):
        pathway = pathways.get_pathway(progress.pathway_id)
        if pathway is not None and progress.status == "active" and progress.current_mission_id:
            found[progress.current_mission_id] = f"{pathway.name} · step {progress.current_step_index + 1} of {len(pathway.steps)}"
    return found


# ------------------------------------------------------------------ Skills


def skills_page(context, today: Optional[date] = None) -> dict:
    from core.skill_leveling import compute_skill_level_progress, next_honest_step

    today = today or date.today()
    skills = getattr(context, "skills", None)
    profile = _profile(context)
    pid = profile.profile_id if profile is not None else None
    page = {"available": skills is not None, "as_of": today.isoformat(), "me": level_block(profile)}
    if skills is None:
        return page
    definitions = skills.all_skills()
    totals = {d.skill_id: (skills.get_progress(pid, d.skill_id).total_xp if pid else 0) for d in definitions}
    by_id = {d.skill_id: d for d in definitions}
    focus = next_honest_step(definitions, totals) if pid else None
    pathways = getattr(context, "pathways", None)
    week_ago = today - timedelta(days=6)

    def pathway_rows(skill_id):
        rows = []
        for p in (pathways.pathways_for_skill(skill_id) if pathways is not None else []):
            status = pathways.status_for(pid, p.pathway_id) if pid else None
            step = p.steps[status.current_step_index] if status is not None and status.status == "active" \
                and status.current_step_index < len(p.steps) else None
            rows.append({"id": p.pathway_id, "name": p.name, "description": p.description, "steps": len(p.steps),
                         "status": status.status if status is not None else "not_started",
                         "step": status.current_step_index + 1 if step is not None else None,
                         "step_name": step.name if step is not None else None,
                         "first_step": p.steps[0].name if p.steps else None})
        return rows

    rows = []
    for d in definitions:
        level, into, needed = compute_skill_level_progress(totals[d.skill_id])
        unlocked = skills.is_unlocked(pid, d.skill_id) if pid else not d.prerequisite_skill_ids
        rows.append({
            "id": d.skill_id, "name": d.name, "icon": d.icon, "category": d.category, "tier": d.tier,
            "level": level, "xp_into_level": into, "xp_for_level": needed, "total_xp": totals[d.skill_id],
            "status": skills.capability_status(pid, d.skill_id) if pid else ("learning" if unlocked else "locked"),
            "unlocked": unlocked, "focus": d.skill_id == focus,
            "needs": [by_id[r].name if r in by_id else r for r in d.prerequisite_skill_ids],
            "this_week": skills.xp_earned_between(pid, d.skill_id, week_ago, today + timedelta(days=1)) if pid else 0,
            "pathways": pathway_rows(d.skill_id),
        })
    from core.skill_patterns import declining_categories, momentum_categories, untouched_interests

    interests = list(getattr(profile, "interests", []) or []) if profile is not None else []
    categories = skills.categories()
    # their windows end before the day given; counting today's work too
    tomorrow = today + timedelta(days=1)
    growing = set(momentum_categories(skills, pid, tomorrow)) if pid else set()
    declining = set(declining_categories(skills, pid, tomorrow)) if pid else set()
    untouched = set(untouched_interests(skills, profile)) if profile is not None else set()

    def trend(c):
        return "growing" if c in growing else "declining" if c in declining else "not started" if c in untouched else None

    page["categories"] = [{"name": c, "interest": c in interests, "trend": trend(c)} for c in
                          [c for c in categories if c in interests] + [c for c in categories if c not in interests]]
    page["skills"] = sorted(rows, key=lambda r: (r["category"], r["tier"], r["name"]))
    page["focus"] = next(({"id": r["id"], "name": r["name"], "icon": r["icon"],
                           "to_next": r["xp_for_level"] - r["xp_into_level"]} for r in rows if r["focus"]), None)
    page["counts"] = {"skills": len(rows), "touched": sum(1 for r in rows if r["total_xp"] > 0),
                      "demonstrated": sum(1 for r in rows if r["status"] == "demonstrated"),
                      "unlocked": sum(r["unlocked"] for r in rows)}
    page["rewards"] = rewards_block(context, pid)
    notifications = getattr(context, "notifications", None)
    recent = [n for n in notifications.list_all() if n.source == "achievements"][:5] if notifications is not None else []
    page["achievements"] = [{"title": n.title, "message": n.message, "when": (n.created_at or "")[:10]} for n in recent]
    return page


def rewards_block(context, pid) -> dict:
    """Challenge chains (earned title, progress toward the next tier),
    hidden achievements found, prestige emblems. Read only."""
    from core.rewards_manager import CHALLENGE_CHAINS, STAT_DEFINITIONS, highest_unlocked_tier, next_locked_tier, \
        reward_progress_fraction

    rewards = getattr(context, "rewards", None)
    if rewards is None or not pid:
        return {"available": False, "chains": [], "hidden": [], "emblems": []}
    values = rewards.all_stat_values(pid)
    unlocked = set(rewards.unlocked_reward_ids(pid))
    stats = {s.stat_id: s for s in STAT_DEFINITIONS}
    chains = []
    for chain in CHALLENGE_CHAINS:
        stat = stats.get(chain.stat_id)
        earned, upcoming = highest_unlocked_tier(chain.tiers, unlocked), next_locked_tier(chain.tiers, unlocked)
        value = values.get(chain.stat_id, 0.0)
        chains.append({
            "stat": stat.name if stat else chain.chain_id, "icon": stat.icon if stat else "", "unit": stat.unit if stat else "",
            "value": round(value, 1),
            "earned": {"name": earned.name, "icon": earned.icon, **_rarity(earned.rarity_index)} if earned else None,
            "next": {"name": upcoming.name, "icon": upcoming.icon, "description": upcoming.description,
                     "threshold": upcoming.threshold, "percent": round(100 * reward_progress_fraction(value, upcoming.threshold)),
                     **_rarity(upcoming.rarity_index)} if upcoming else None,
            "maxed": upcoming is None,
        })
    hidden = [{"name": h.name, "icon": h.icon, "description": h.description, **_rarity(h.rarity_index)}
              for h in rewards.unlocked_hidden_achievements(pid)]
    return {"available": True, "chains": chains, "hidden": hidden, "emblems": rewards.prestige_rewards_for_profile(pid)}


# ------------------------------------------------------------------ Character


def character_page(context, today: Optional[date] = None) -> dict:
    from core.rarity import RARITY_NAMES
    from core.rewards_manager import STAT_DEFINITIONS

    today = today or date.today()
    profile = _profile(context)
    pid = profile.profile_id if profile is not None else None
    page = {"available": profile is not None, "as_of": today.isoformat(), "me": level_block(profile)}
    rewards = getattr(context, "rewards", None)
    if profile is None:
        return page
    if rewards is not None:
        values = rewards.all_stat_values(pid)
        page["stats"] = [{"icon": s.icon, "name": s.name, "unit": s.unit, "value": round(values.get(s.stat_id, 0.0), 1)}
                         for s in STAT_DEFINITIONS]
        entries = list(rewards.all_unlocked_tiers(pid)) + list(rewards.unlocked_hidden_achievements(pid))
        page["collection"] = [{"name": e.name, "icon": e.icon, "description": e.description, **_rarity(e.rarity_index)}
                              for e in sorted(entries, key=lambda e: (-e.rarity_index, e.name))]
        tally = [0] * len(RARITY_NAMES)
        for e in entries:
            tally[min(max(e.rarity_index, 0), len(tally) - 1)] += 1
        page["rarity"] = [{"rarity": i, "rarity_name": name, "count": tally[i]} for i, name in enumerate(RARITY_NAMES)]
        page["emblems"] = rewards.prestige_rewards_for_profile(pid)
    else:
        page.update(stats=[], collection=[], rarity=[], emblems=[])
    skills = getattr(context, "skills", None)
    if skills is not None:
        from core.skill_leveling import compute_skill_level_progress

        top = sorted(((compute_skill_level_progress(p.total_xp)[0], p.total_xp, skills.get_skill(p.skill_id))
                      for p in skills.progress_for_profile(pid)), key=lambda t: (-t[0], -t[1]))
        page["top_skills"] = [{"name": s.name, "icon": s.icon, "level": lvl} for lvl, _xp, s in top if s is not None][:5]
    missions = getattr(context, "missions", None)
    if missions is not None:
        from core.mission_actions import is_mine

        done = [m for m in missions.all_missions() if m.status == "completed" and is_mine(m, pid)]
        page["missions_completed"] = len(done)
        page["latest_missions"] = [{"name": m.name, "icon": m.icon, "when": (m.updated_at or "")[:10]}
                                   for m in sorted(done, key=lambda m: m.updated_at or "", reverse=True)[:5]]
    page["member_since"] = (profile.created_at or "")[:10]
    return page
