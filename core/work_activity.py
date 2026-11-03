"""
core.work_activity
====================

Who did what to the development work, and when (DEC-0068, step 2 of
`docs/DEV_ECOSYSTEM_AUDIT.md`): `work/activity.jsonl`, one line per event,
only ever added to. Every change `tools/work.py` makes to a task is recorded
here, so the history is searchable and a task interrupted halfway can be
picked up from its last step.

Evidence is gathered, not just written: closing a task can run its tests and
records the result with the commit the work is in, so "done" means something
anyone can check.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
ACTIVITY = ROOT / "work" / "activity.jsonl"
MAX_DETAIL = 2000


def record(who: str, action: str, task_id: str = "", detail: str = "", path: Path = ACTIVITY,
           at: Optional[datetime] = None) -> dict:
    """Add one event. Appended, never rewritten."""
    event = {"at": (at or datetime.now(timezone.utc)).isoformat(timespec="seconds"), "who": who,
             "action": action, "task": task_id, "detail": (detail or "")[:MAX_DETAIL]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def events(path: Path = ACTIVITY) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def search(text: str = "", task_id: str = "", who: str = "", path: Path = ACTIVITY) -> list[dict]:
    """Pure-ish. The events matching all of: words in `text`, a task, a person."""
    words = [w.lower() for w in text.split()]
    found = []
    for event in events(path):
        haystack = " ".join(str(v) for v in event.values()).lower()
        if task_id and event.get("task") != task_id.upper():
            continue
        if who and event.get("who") != who:
            continue
        if all(w in haystack for w in words):
            found.append(event)
    return found


def last_step(task_id: str, path: Path = ACTIVITY) -> Optional[dict]:
    """Where an interrupted task got to: its most recent event."""
    mine = search(task_id=task_id, path=path)
    return mine[-1] if mine else None


def commit(root: Path = ROOT) -> str:
    """The commit the work is on, and whether anything is left uncommitted."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, timeout=30,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout

    head = git("log", "-1", "--format=%h %s").strip()
    # Each status line is two status letters, a space, then the path: never strip the line first.
    dirty = [line[3:] for line in git("status", "--porcelain").splitlines() if line.strip()]
    return head + (f" (uncommitted: {', '.join(dirty[:8])}{'...' if len(dirty) > 8 else ''})" if dirty else "")


def run_tests(targets: list[str], root: Path = ROOT, timeout: int = 900) -> tuple[bool, str]:
    """Run pytest on `targets`; (passed, its summary line)."""
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *targets],
                          cwd=str(root), capture_output=True, text=True, timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    lines = [line for line in (done.stdout or "").splitlines() if line.strip()]
    return done.returncode == 0, (lines[-1] if lines else "pytest gave no summary")
