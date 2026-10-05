"""
core.project_manager
=======================

Project Manager — the v1.0+-bucket "Project Manager" tool listed in
docs/ROADMAP.md's Toolbox section, buildable with zero real hardware
(same rationale as Activity Log/Navigation/Field Kit/Expedition Mode
before it). Top-level container for a Project; each Project can hold
multiple core.task_manager.Task records. Same persisted-JSON pattern as
core/expedition_manager.py: data/projects.json, a dataclass with
to_dict/from_dict, a manager class wrapping load/save.

Deleting a Project unlinks (does not cascade-delete) its Tasks —
consistent with this project's non-destructive bias elsewhere (see
core/expedition_manager.py's own docstring for the same rationale); a
Task whose project_id no longer resolves just stops showing up under
any Project, but isn't deleted itself.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.gamification import SkillWeight, grant_xp
from core import life_events
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROJECTS_FILE = _DATA_DIR / "projects.json"

PROJECT_STATUSES = ("Planning", "Active", "On Hold", "Complete")


@dataclass
class Project:
    project_id: str
    name: str
    status: str = "Planning"
    due_date: str = ""  # ISO date
    description: str = ""
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime
    # Connective-infrastructure pass (2026-09-11) — both optional, both
    # empty/None by default so every existing data/projects.json row
    # deserializes unchanged, zero migration needed.
    intent_id: Optional[str] = None  # the "why" this Project serves, see core/intent_manager.py
    # "My Hero's Path" Phase 2 — same shape as Mission.skill_rewards,
    # granted once on the Planning/Active/On Hold -> Complete transition
    # (see ProjectManager.update_project()), plus retroactively via
    # add_skill_weight().
    skill_weights: list[SkillWeight] = field(default_factory=list)
    # True once skill_weights has been bulk-credited at least once.
    # Real, deliberately added after a test caught the gap:
    # PROJECT_STATUSES allows Complete -> Active -> Complete again —
    # without this flag, toggling status back and forth would re-grant
    # the same skill_weights every time, a real exploit vector, not a
    # theoretical one. Never reset once True. Doesn't gate
    # add_skill_weight()'s own single-new-weight crediting path — that
    # one's safe by construction (it only ever credits the ONE weight
    # just appended, never the whole list).
    #
    # 2026-09-12 correction: this comment used to claim Mission's
    # status was different ("active/completed/abandoned, no going
    # back"). That was wrong — gui/add_edit_mission_dialog.py's own
    # status combo lets a completed Mission go back to "active" too,
    # and Mission had the exact same re-grant exploit until
    # Mission.rewards_credited (added the same day, same reasoning)
    # closed it.
    skill_weights_credited: bool = False
    # 2026-09-28, Finance #2: what the owner plans to spend on this build.
    # 0 means no budget set. Spending is the sum of expenses tagged with
    # this project_id (core/homestead_costs.py), never stored here.
    budget: float = 0.0

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status,
            "due_date": self.due_date,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "intent_id": self.intent_id,
            "skill_weights": [{"skill_id": w.skill_id, "xp": w.xp} for w in self.skill_weights],
            "skill_weights_credited": self.skill_weights_credited,
            "budget": self.budget,
        }

    @staticmethod
    def from_dict(data: dict) -> "Project":
        return Project(
            project_id=data.get("project_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            status=data.get("status", "Planning"),
            due_date=data.get("due_date", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            intent_id=data.get("intent_id"),
            skill_weights=[
                SkillWeight(skill_id=d["skill_id"], xp=d["xp"]) for d in data.get("skill_weights", [])
            ],
            skill_weights_credited=bool(data.get("skill_weights_credited", False)),
            budget=float(data.get("budget", 0.0) or 0.0),
        )


class ProjectManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._projects_file = self.data_dir / "projects.json" if data_dir is not None else _PROJECTS_FILE
        self.context = context
        self._projects: list[Project] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._projects_file.exists():
            self._projects = []
            return
        try:
            raw = json.loads(self._projects_file.read_text(encoding="utf-8"))
            self._projects = [Project.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load projects.json — starting with an empty list.")
            notify_data_corruption(self.context, "projects.json")
            self._projects = []

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._projects_file,
            json.dumps([p.to_dict() for p in self._projects], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_project(
        self,
        name: str,
        status: str = "Planning",
        due_date: str = "",
        description: str = "",
        intent_id: Optional[str] = None,
        skill_weights: Optional[list[SkillWeight]] = None,
    ) -> Project:
        now = datetime.now().isoformat(timespec="seconds")
        project = Project(
            project_id=uuid.uuid4().hex[:10],
            name=name,
            status=status,
            due_date=due_date,
            description=description,
            created_at=now,
            updated_at=now,
            intent_id=intent_id,
            skill_weights=list(skill_weights) if skill_weights else [],
        )
        self._projects.append(project)
        self._save()
        log.info("Project added: '%s'", name)
        return project

    def update_project(self, project_id: str, **fields) -> Project:
        project = self.get_project(project_id)
        if project is None:
            raise ValueError(f"No project with id '{project_id}'.")
        was_complete = project.status == "Complete"
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_project().")
            if key == "skill_weights_credited":
                raise ValueError("'skill_weights_credited' can't be set through update_project().")
            if not hasattr(project, key):
                raise ValueError(f"Project has no field '{key}'.")
            setattr(project, key, value)
        project.updated_at = datetime.now().isoformat(timespec="seconds")
        # "My Hero's Path" Phase 2 (2026-09-11) — fires at most once per
        # Project, the first time it newly becomes Complete, same
        # "detect the transition, not just the state" pattern
        # core.mission_manager.MissionManager.update_mission() already
        # uses. Also gated on skill_weights_credited (not just the
        # transition) — unlike Mission's status, PROJECT_STATUSES
        # allows Complete -> Active -> Complete again, and without this
        # guard re-completing would re-grant the same weights every
        # time (a real exploit vector, caught by a test during
        # implementation, not theoretical).
        if not was_complete and project.status == "Complete" and not project.skill_weights_credited:
            self._credit_project_skill_weights(project)
            project.skill_weights_credited = True
            # Event-sourced groundwork (2026-09-14) — see
            # core/rewards_manager.py's own docstring for the full
            # design. Fires on this same real transition, not on every
            # update_project() call (a Project can go Complete ->
            # Active -> Complete again; this activity event fires only
            # for the first sighting of a genuine completion, mirroring
            # the skill_weights_credited guard right above).
            life_events.record(self, "project_completed", f"Finished the project {project.name}",
                               [f"project:{project.project_id}"])
            self.context.events.publish(
                "activity.logged", source="project", category="project_completed",
                timestamp=datetime.now().isoformat(timespec="seconds"),
                duration=None, quantity=1,
                metadata={"project_id": project.project_id},
            )
        self._save()
        return project

    def _credit_project_skill_weights(self, project: Project) -> None:
        if not project.skill_weights:
            return
        grant_xp(
            self.context,
            0,  # no flat profile XP for a Project completion — that stays Mission-exclusive
            "\U0001F3D7 Project complete!",
            f"'{project.name}' is done.",
            skill_weights=project.skill_weights,
        )

    def add_skill_weight(self, project_id: str, skill_id: str, xp: int) -> Project:
        """Declares (or retroactively adds) a skill this Project trains.
        If the Project is still in progress, this weight is simply
        appended and gets credited normally when it later transitions
        to Complete (see update_project()). If the Project is ALREADY
        Complete, this credits just this one new weight immediately —
        never the whole list, so an earlier completion's already-
        granted weights are never double-credited."""
        project = self.get_project(project_id)
        if project is None:
            raise ValueError(f"No project with id '{project_id}'.")
        weight = SkillWeight(skill_id=skill_id, xp=xp)
        project.skill_weights.append(weight)
        project.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        if project.status == "Complete":
            grant_xp(
                self.context,
                0,
                "\U0001F4DD Skill credited!",
                f"'{project.name}' also taught you something — crediting it now.",
                skill_weights=[weight],
            )
        return project

    def delete_project(self, project_id: str) -> None:
        self._projects = [p for p in self._projects if p.project_id != project_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_project(self, project_id: str) -> Optional[Project]:
        for project in self._projects:
            if project.project_id == project_id:
                return project
        return None

    def all_projects(self) -> list[Project]:
        return sorted(self._projects, key=lambda p: (p.due_date == "", p.due_date))
