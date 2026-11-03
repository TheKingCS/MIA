"""
core.work_tasks
=================

Development tasks as records (DEC-0068, step 1 of `docs/DEV_ECOSYSTEM_AUDIT.md`):
one Markdown file per task in `work/tasks/`, so the team's to-do list is in
the repo, in git's history, readable by every session and by a program.
`tools/work.py` is the command line over it.

A task file is a small header, then free text:

    ---
    id: T-0001
    title: The self-knowledge map
    status: open
    owner: claude
    role: Software Engineer
    depends: T-0002, T-0003
    files: core/capabilities.py, core/links.py
    branch:
    decisions: DEC-0067
    source: docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md section C
    created: 2026-11-03
    updated: 2026-11-03
    ---
    What it is, then a log of notes and evidence below.

**Status** is one of `open`, `claimed`, `review`, `done`, `blocked`, `dropped`.
"Ready" is worked out, not stored: an open task whose dependencies are done.
**files** is what a claim expects to touch, as paths or patterns: two claimed
tasks that could touch the same file don't run at once (the overlap of
2026-11-02, when two sessions edited the same files unaware). A task only
closes with **evidence**: what shows it's done.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "work" / "tasks"

STATUSES = ("open", "claimed", "review", "done", "blocked", "dropped")
FINISHED = ("done", "dropped")
LISTS = ("depends", "files", "decisions")
FIELDS = ("id", "title", "status", "owner", "role", "depends", "files", "branch", "decisions", "source",
          "created", "updated")
ID = re.compile(r"T-(\d{4,})")


class TaskError(ValueError):
    """A task that can't be made, read or moved the way asked."""


@dataclass
class Task:
    id: str
    title: str
    status: str = "open"
    owner: str = ""
    role: str = ""
    depends: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    branch: str = ""
    decisions: list[str] = field(default_factory=list)
    source: str = ""
    created: str = ""
    updated: str = ""
    body: str = ""

    def to_text(self) -> str:
        lines = ["---"]
        for name in FIELDS:
            value = getattr(self, name)
            lines.append(f"{name}: {', '.join(value) if name in LISTS else value}".rstrip())
        lines.append("---")
        return "\n".join(lines) + "\n" + self.body.strip() + "\n"


def parse(text: str) -> Task:
    """Pure logic. A task from its file's text."""
    parts = text.replace("\r\n", "\n").split("---\n", 2)
    if len(parts) < 3 or parts[0].strip():
        raise TaskError("A task file starts with a --- header.")
    values: dict = {}
    for line in parts[1].splitlines():
        if not line.strip():
            continue
        name, sep, value = line.partition(":")
        name = name.strip()
        if not sep or name not in FIELDS:
            raise TaskError(f"Unknown header line: {line!r}")
        value = value.strip()
        values[name] = [v.strip() for v in value.split(",") if v.strip()] if name in LISTS else value
    if not ID.fullmatch(values.get("id", "")) or not values.get("title"):
        raise TaskError("A task needs an id like T-0001 and a title.")
    if values.get("status", "open") not in STATUSES:
        raise TaskError(f"Status is one of {', '.join(STATUSES)}.")
    return Task(**values, body=parts[2].strip())


def load(folder: Path = TASKS_DIR) -> dict[str, Task]:
    tasks = {}
    for path in sorted(Path(folder).glob("T-*.md")):
        task = parse(path.read_text(encoding="utf-8"))
        if path.stem != task.id:
            raise TaskError(f"{path.name} holds {task.id}.")
        tasks[task.id] = task
    return tasks


def save(task: Task, folder: Path = TASKS_DIR, today: Optional[date] = None) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    task.updated = (today or date.today()).isoformat()
    path = folder / f"{task.id}.md"
    path.write_text(task.to_text(), encoding="utf-8", newline="\n")
    return path


def next_id(tasks: dict[str, Task]) -> str:
    numbers = [int(ID.fullmatch(t).group(1)) for t in tasks]
    return f"T-{max(numbers, default=0) + 1:04d}"


def ready(task: Task, tasks: dict[str, Task]) -> bool:
    """Pure logic. Open, and every task it depends on is done."""
    return task.status == "open" and all(tasks.get(d) is not None and tasks[d].status == "done" for d in task.depends)


def overlaps(mine: Iterable[str], theirs: Iterable[str]) -> list[str]:
    """Pure logic. The patterns of `mine` that could touch a file of `theirs`."""
    theirs = list(theirs)
    hits = []
    for a in mine:
        for b in theirs:
            if a == b or fnmatch(a, b) or fnmatch(b, a) or a.startswith(b.rstrip("*")) or b.startswith(a.rstrip("*")):
                hits.append(a)
                break
    return hits


def new(tasks: dict[str, Task], title: str, today: Optional[date] = None, **values) -> Task:
    for d in values.get("depends", []) or []:
        if d not in tasks:
            raise TaskError(f"{d} isn't a task.")
    stamp = (today or date.today()).isoformat()
    return Task(id=next_id(tasks), title=title.strip(), created=stamp, updated=stamp, **values)


def claim(tasks: dict[str, Task], task_id: str, who: str, files: Optional[list[str]] = None) -> Task:
    """Take a ready task. Refused when it isn't ready, or when another claimed
    task could touch the same files."""
    task = _get(tasks, task_id)
    if not who:
        raise TaskError("Who's claiming it?")
    if task.status == "claimed" and task.owner == who:
        return task
    if not ready(task, tasks):
        waiting = [d for d in task.depends if tasks.get(d) is None or tasks[d].status != "done"]
        raise TaskError(f"{task.id} isn't ready" + (f": waiting on {', '.join(waiting)}." if waiting else f" ({task.status})."))
    wanted = files if files is not None else task.files
    for other in tasks.values():
        if other.id != task.id and other.status == "claimed":
            clash = overlaps(wanted, other.files)
            if clash:
                raise TaskError(f"{other.id} ({other.owner}) is working on {', '.join(clash)}. Wait, or pick other files.")
    task.status, task.owner, task.files = "claimed", who, list(wanted)
    return task


def note(task: Task, who: str, text: str, today: Optional[date] = None) -> Task:
    stamp = (today or date.today()).isoformat()
    task.body = task.body.rstrip() + f"\n\n- {stamp} {who}: {text.strip()}"
    return task


def finish(tasks: dict[str, Task], task_id: str, who: str, evidence: str, today: Optional[date] = None) -> Task:
    """Done, only with evidence: the tests run, the commit, what was checked."""
    task = _get(tasks, task_id)
    if not evidence.strip():
        raise TaskError("Done needs evidence: the test run, the commit, what was checked.")
    if task.status in FINISHED:
        raise TaskError(f"{task.id} is already {task.status}.")
    note(task, who, "Done. Evidence: " + evidence, today)
    task.status = "done"
    return task


def move(tasks: dict[str, Task], task_id: str, status: str, who: str, why: str, today: Optional[date] = None) -> Task:
    """Block, drop, send to review or reopen, always with a reason."""
    task = _get(tasks, task_id)
    if status not in STATUSES or status == "done":
        raise TaskError("Use done for done; otherwise one of open, review, blocked, dropped.")
    if not why.strip():
        raise TaskError("Say why.")
    note(task, who, f"{status.capitalize()}: {why}", today)
    task.status = status
    if status == "open":
        task.owner = task.owner if task.owner in ("zac",) else ""
    return task


def _get(tasks: dict[str, Task], task_id: str) -> Task:
    task = tasks.get(task_id.upper())
    if task is None:
        raise TaskError(f"No task {task_id}.")
    return task
