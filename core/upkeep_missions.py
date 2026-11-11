"""
core.upkeep_missions
======================

Upkeep as scheduled missions (DEC-0153, Zac 2026-11-11): "home upkeep
just like maintenance for cars and tools should be scheduled missions and
relevant ones will be attached to each property/asset as well as able to
be seen in the calendar and under a Your Week tab in Dashboard".

What it does: the maintenance schedule stays the record (core/
maintenance_manager.py: a task, its interval or meter, when it was last
done); each time a task comes due, MIA makes one mission for that
occurrence, attached to the task and its asset (`maintenance_task_id`,
`maintenance_asset_id`), so it shows in Missions, on the asset's own page
and (through the asset) on a property. The Calendar and Your Week already
show the same occurrence from the schedule, with Done.

Both ways, so nothing is done twice:
- the upkeep marked done (anywhere: Today, Your Week, the Calendar, the
  asset, by voice) completes its open mission (`settle`, called by the
  `maintenance.done` action and the daily check);
- the mission completed in Missions marks the upkeep done (`_on_completed`,
  on `mission.completed`), unless it already was since the mission was made.

How:
- `due_soon(context, today)` (read only): the person's tasks due within
  HORIZON_DAYS or overdue, each with its due date (someone else's asset in
  the household is left out, core/ownership.py).
- `ensure(context, today)`: one mission per task and due date; the
  occurrence key `upkeep:<task>:<date>` means a mission set aside isn't
  made again for the same date, and a done one isn't repeated.
- `settle(context, today)`: completes open upkeep missions whose task was
  done since, and sets aside ones whose task was deleted.
- `wire(context)`: listens for completed missions. Called at startup.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

HORIZON_DAYS = 7  # Your Week's span: a mission appears when its upkeep is due this week
PREFIX = "upkeep:"
MISSION_TYPE = "SCHEDULED MISSION"


def key_for(task_id: str, due: date) -> str:
    """Pure logic. The occurrence key of one task's one due date."""
    return f"{PREFIX}{task_id}:{due.isoformat()}"


def due_soon(context, today: date) -> list[tuple]:
    """[(task, asset or None, due date)] for the person's upkeep due within HORIZON_DAYS or already overdue."""
    from core.maintenance_manager import next_occurrence_date, task_urgency
    from core.ownership import is_for_me

    store = getattr(context, "maintenance", None)
    if store is None:
        return []
    assets = {a.asset_id: a for a in store.all_assets()}
    out = []
    for task in store.all_tasks():
        asset = assets.get(task.asset_id)
        if asset is not None and not is_for_me(context, asset.owner_profile_id):
            continue
        readings = [] if task.trigger_type == "calendar" else (store.readings_for_task(task.task_id) or [])
        due = next_occurrence_date(task, readings, today)
        if due is None and task_urgency(task, readings, today) == "overdue":
            due = today
        if due is not None and due <= today + timedelta(days=HORIZON_DAYS):
            out.append((task, asset, due))
    return out


def _upkeep(missions) -> list:
    """Every upkeep mission (by its occurrence key)."""
    return [m for m in missions.all_missions() if (m.occurrence_key or "").startswith(PREFIX)]


def ensure(context, today: Optional[date] = None) -> list:
    """Makes the missing upkeep missions for this week; returns the ones made. Idempotent."""
    missions = getattr(context, "missions", None)
    if missions is None:
        return []
    today = today or date.today()
    have = {m.occurrence_key for m in _upkeep(missions)}
    open_for = {m.maintenance_task_id for m in _upkeep(missions) if m.status == "active"}
    made = []
    for task, asset, due in due_soon(context, today):
        key = key_for(task.task_id, due)
        if key in have or task.task_id in open_for:  # this date's mission exists, or an earlier one is still open
            continue
        from core.gamification import SkillWeight

        where = f": {asset.name}" if asset is not None else ""
        when = "overdue" if due < today else ("due today" if due == today else f"due {due:%A, %b} {due.day}")
        mission = missions.add_mission(
            name=f"{task.title}{where}", maintenance_task_id=task.task_id,
            maintenance_asset_id=task.asset_id or None, assigned_by="mia", icon="\U0001F527",
            mission_type=MISSION_TYPE, occurrence_key=key,
            summary=f"Scheduled upkeep, {when}. Marking it done here marks the upkeep done too.",
            skill_rewards=[SkillWeight("home_maintenance", 10)])
        missions.add_objective(mission.mission_id, "Done", "tally", 1)
        made.append(mission)
        open_for.add(task.task_id)
    return made


def settle(context, today: Optional[date] = None) -> int:
    """Completes each open upkeep mission whose task was done since the mission was made, and sets aside one whose task
    is gone; returns how many changed."""
    missions, store = getattr(context, "missions", None), getattr(context, "maintenance", None)
    if missions is None or store is None:
        return 0
    changed = 0
    for m in _upkeep(missions):
        if m.status != "active":
            continue
        task = store.get_task(m.maintenance_task_id or "")
        if task is None:
            missions.update_mission(m.mission_id, status="abandoned", abandon_reason="The upkeep was removed.")
            changed += 1
        elif task.last_completed and task.last_completed >= (m.created_at or "")[:10]:
            missions.set_objective_progress(m.mission_id, [1.0 for _ in m.objectives])
            if missions.get_mission(m.mission_id).status == "active":
                missions.update_mission(m.mission_id, status="completed")
            changed += 1
    return changed


def _on_completed(context, mission_id: str = "", **_ignored) -> None:
    """On `mission.completed`: an upkeep mission done in Missions marks its upkeep done, unless it already was since the
    mission was made (then the upkeep's Done is what completed it)."""
    try:
        missions, store = getattr(context, "missions", None), getattr(context, "maintenance", None)
        mission = missions.get_mission(mission_id) if missions is not None else None
        if mission is None or store is None or not (mission.occurrence_key or "").startswith(PREFIX):
            return
        task = store.get_task(mission.maintenance_task_id or "")
        if task is not None and not (task.last_completed and task.last_completed >= (mission.created_at or "")[:10]):
            store.mark_complete(task.task_id)
    except Exception:  # noqa: BLE001 - a mission still completes when the upkeep can't be marked
        log.exception("Upkeep: marking the upkeep done after its mission failed")


def wire(context) -> None:
    """Listens for completed missions (once, at startup)."""
    context.events.subscribe("mission.completed", lambda **kw: _on_completed(context, **kw))
