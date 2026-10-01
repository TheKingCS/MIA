"""
core.task_manager
====================

A single Task under a core.project_manager.Project — one concrete
to-do item, checked off when done. Same persisted-JSON pattern as
core/trip_manager.py, minus that module's photo/journal/gear
extensions, which don't apply to a plain task list.
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
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TASKS_FILE = _DATA_DIR / "tasks.json"


@dataclass
class Task:
    task_id: str
    project_id: str
    title: str
    done: bool = False
    due_date: str = ""  # ISO date
    notes: str = ""
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "title": self.title,
            "done": self.done,
            "due_date": self.due_date,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Task":
        return Task(
            task_id=data.get("task_id", uuid.uuid4().hex[:10]),
            project_id=data.get("project_id", ""),
            title=data.get("title", ""),
            done=bool(data.get("done", False)),
            due_date=data.get("due_date", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class TaskManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._tasks_file = self.data_dir / "tasks.json" if data_dir is not None else _TASKS_FILE
        self.context = context
        self._tasks: list[Task] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._tasks_file.exists():
            self._tasks = []
            return
        try:
            raw = json.loads(self._tasks_file.read_text(encoding="utf-8"))
            self._tasks = [Task.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load tasks.json — starting with an empty list.")
            notify_data_corruption(self.context, "tasks.json")
            self._tasks = []

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._tasks_file,
            json.dumps([t.to_dict() for t in self._tasks], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_task(
        self,
        project_id: str,
        title: str,
        due_date: str = "",
        notes: str = "",
    ) -> Task:
        now = datetime.now().isoformat(timespec="seconds")
        task = Task(
            task_id=uuid.uuid4().hex[:10],
            project_id=project_id,
            title=title,
            due_date=due_date,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._tasks.append(task)
        self._save()
        log.info("Task added: '%s'", title)
        return task

    def update_task(self, task_id: str, **fields) -> Task:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"No task with id '{task_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_task().")
            if not hasattr(task, key):
                raise ValueError(f"Task has no field '{key}'.")
            setattr(task, key, value)
        task.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return task

    def toggle_done(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"No task with id '{task_id}'.")
        return self.update_task(task_id, done=not task.done)

    def delete_task(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.task_id != task_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self._tasks:
            if task.task_id == task_id:
                return task
        return None

    def tasks_for_project(self, project_id: str) -> list[Task]:
        return [t for t in self._tasks if t.project_id == project_id]

    def all_tasks(self) -> list[Task]:
        return list(self._tasks)
