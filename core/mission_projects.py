"""
core.mission_projects
=======================

Projects and Missions, connected (Zac's handoff, 2026-11-09, DEC-0152): "Projects represent what the user is working
toward. Missions represent how MIA helps the user accomplish it."

**One source of truth.** A mission names its project by `Mission.project_id` (core/mission_manager.py); nothing is
copied. A project's missions are the missions that name it (`missions_for`), and a mission's project is the project
it names (`project_of`), so the Projects page and the Missions page read the same records. A mission needn't have a
project: most don't.

**Progress, derived, never stored** (`progress`): each of the project's tasks counts done or not, each of its
missions counts the share of its objectives done (all of it once completed; a mission set aside doesn't count), and
the two are weighed by `modules.projects.progress_weights` ({"task": 1, "mission": 1} by default). A project marked
Complete is 100. So a mission's progress shows in its project the moment it's made.

**Changing it**: the action `mission.project` (Part Of A Project, or "" to take it out of one), on the mission's sheet
and by voice (`set_mission_project`), the same check either way.
"""

from __future__ import annotations

from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.logger import get_logger

log = get_logger(__name__)

DEFAULT_WEIGHTS = {"task": 1.0, "mission": 1.0}


def missions_for(context, project_id: str) -> list:
    """The missions that name this project, active first ([] without missions here)."""
    missions = getattr(context, "missions", None)
    if missions is None or not project_id:
        return []
    order = {"active": 0, "completed": 1, "abandoned": 2}
    return sorted(missions.missions_for_project(project_id), key=lambda m: (order.get(m.status, 3), m.created_at))


def project_of(context, mission) -> Optional[object]:
    """The project a mission names, or None (none named, or it's gone)."""
    projects = getattr(context, "projects", None)
    if projects is None or not getattr(mission, "project_id", None):
        return None
    return projects.get_project(mission.project_id)


def mission_share(context, mission) -> float:
    """Pure-ish. How much of a mission is done, 0 to 1: all of it once completed, else its objectives done over all
    (0 with none yet)."""
    if mission.status == "completed":
        return 1.0
    done, total = context.missions.group_objective_progress(mission.mission_id)
    return done / total if total else 0.0


def _weights(context) -> dict:
    """The progress weights from config (modules.projects.progress_weights), falling back to 1 each."""
    raw = {}
    config = getattr(context, "config", None)
    if config is not None:
        try:
            raw = config.get("modules.projects.progress_weights", {}) or {}
        except Exception:
            log.exception("Couldn't read the projects' progress weights")
    out = dict(DEFAULT_WEIGHTS)
    for key in out:
        try:
            if key in raw and float(raw[key]) >= 0:
                out[key] = float(raw[key])
        except (TypeError, ValueError):
            continue  # a weight that isn't a number keeps its default
    return out


def progress(context, project) -> dict:
    """A project's progress from its tasks and missions: {"percent" (None with nothing to count), "tasks_done",
    "tasks_total", "missions_done", "missions_total"}; 100 for a project marked Complete."""
    tasks_store = getattr(context, "tasks", None)
    tasks = tasks_store.tasks_for_project(project.project_id) if tasks_store is not None else []
    missions = [m for m in missions_for(context, project.project_id) if m.status != "abandoned"]
    w = _weights(context)
    shares = [(w["task"], 1.0 if t.done else 0.0) for t in tasks] + [(w["mission"], mission_share(context, m))
                                                                     for m in missions]
    total = sum(weight for weight, _ in shares)
    percent = 100 if project.status == "Complete" else (round(100 * sum(wt * s for wt, s in shares) / total)
                                                         if total else None)
    return {"percent": percent, "tasks_done": sum(1 for t in tasks if t.done), "tasks_total": len(tasks),
            "missions_done": sum(1 for m in missions if m.status == "completed"), "missions_total": len(missions)}


def mission_card(context, mission) -> dict:
    """A mission as a card on its project's page: its id, name, icon, status, how far along, and what's next."""
    done, total = context.missions.group_objective_progress(mission.mission_id)
    nxt = next((o.description for i, o in enumerate(mission.objectives)
                if (context.missions.objective_progress(mission.mission_id, i) or 0) < o.target), "")
    return {"id": mission.mission_id, "name": mission.name, "icon": mission.icon, "status": mission.status,
            "done": done, "total": total, "percent": round(100 * mission_share(context, mission)),
            "next": nxt if mission.status == "active" else ""}


# ------------------------------------------------------------------ the action


def _mission(context, params):
    """The mission the params name, or ActionError."""
    found = _need(context, "missions").get_mission(str(params.get("mission_id") or ""))
    if found is None:
        raise ActionError("That mission isn't here anymore.")
    return found


def _target(context, params):
    """The project the params name (None for "" to take the mission out of its project), or ActionError."""
    project_id = str(params.get("project_id") or "")
    if not project_id:
        return None
    found = _need(context, "projects").get_project(project_id)
    if found is None:
        raise ActionError("That project isn't here anymore.")
    return found


def _describe(context, params) -> str:
    """The approval sentence for mission.project."""
    mission, project = _mission(context, params), _target(context, params)
    if project is None:
        current = project_of(context, mission)
        if current is None:
            raise ActionError(f"“{mission.name}” isn't part of a project.")
        return f"Take “{mission.name}” out of {current.name}"
    if mission.project_id == project.project_id:
        raise ActionError(f"“{mission.name}” is already part of {project.name}.")
    return f"Make “{mission.name}” part of {project.name}"


def _execute(context, params) -> str:
    """Does mission.project."""
    mission, project = _mission(context, params), _target(context, params)
    context.missions.set_project(mission.mission_id, project.project_id if project is not None else None)
    if project is None:
        return f"“{mission.name}” stands on its own now."
    return f"“{mission.name}” is part of {project.name}; its progress counts toward it."


ACTION_TYPES["mission.project"] = ActionType(
    "mission.project", "Part Of A Project", {"mission_id": "the mission", "project_id": "the project, or none"},
    _describe, _execute, True)


def project_choices(context) -> list[dict]:
    """The projects a mission can be part of, underway first: [{id, name}]."""
    projects = getattr(context, "projects", None)
    if projects is None:
        return []
    order = {"Active": 0, "Planning": 1, "On Hold": 2, "Complete": 3}
    return [{"id": p.project_id, "name": p.name}
            for p in sorted(projects.all_projects(), key=lambda p: (order.get(p.status, 4), p.name.lower()))]
