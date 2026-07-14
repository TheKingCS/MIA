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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

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

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status,
            "due_date": self.due_date,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
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
        )


class ProjectManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._projects: list[Project] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _PROJECTS_FILE.exists():
            self._projects = []
            return
        try:
            raw = json.loads(_PROJECTS_FILE.read_text(encoding="utf-8"))
            self._projects = [Project.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load projects.json — starting with an empty list.")
            self._projects = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _PROJECTS_FILE.write_text(
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
        )
        self._projects.append(project)
        self._save()
        log.info("Project added: '%s'", name)
        return project

    def update_project(self, project_id: str, **fields) -> Project:
        project = self.get_project(project_id)
        if project is None:
            raise ValueError(f"No project with id '{project_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_project().")
            if not hasattr(project, key):
                raise ValueError(f"Project has no field '{key}'.")
            setattr(project, key, value)
        project.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
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
