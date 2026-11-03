"""
core.work_loop
================

A task, worked by an agent, from claim to the approval queue (DEC-0068/0070,
step 3 of `docs/DEV_ECOSYSTEM_AUDIT.md`). It's MIA's lab (`core/dev_lab.py`)
with the task records around it, not a second engine:

1. **claim**: the task, by its role, for the files it names.
2. **lab**: a lab proposal from the task: its own git worktree and branch,
   no real data, no credentials.
3. **write**: the role's provider writes the change there.
4. **check**: the lab's rules (protected files refused) and the full suite
   against the suite at the starting commit.
5. **review**: the task waits for an independent review (step 4), then
   Zac's approval, which is the lab's `approve`: nothing reaches the running
   copy otherwise.

Every step is recorded in `work/activity.jsonl` as it finishes, and the
task's `branch` names its lab, so a run stopped halfway (a crash, a usage
limit) resumes from the next step instead of starting over.
"""

from __future__ import annotations

from typing import Callable, Optional

from core import work_activity as activity
from core import work_tasks as tasks_mod
from core.work_agents import AgentError, Registry

STEPS = ("claim", "lab", "write", "check", "review")
STEP_ACTION = "loop"


class LoopError(RuntimeError):
    """A run that stopped, and why; the task keeps its place."""


def done_steps(task_id: str, path=activity.ACTIVITY) -> list[str]:
    """Pure-ish. The loop steps this task has finished, in order."""
    out = []
    for e in activity.search(task_id=task_id, path=path):
        if e.get("action") == STEP_ACTION and e.get("detail", "").split(":", 1)[0] in STEPS:
            step = e["detail"].split(":", 1)[0]
            if step not in out:
                out.append(step)
    return out


def proposal_id(task) -> str:
    return task.branch[len("lab/"):] if task.branch.startswith("lab/") else ""


def run(task_id: str, role_name: str, registry: Registry, *, lab=None, coder: Optional[Callable] = None,
        suite: Optional[Callable] = None, folder=tasks_mod.TASKS_DIR, log=activity.ACTIVITY) -> str:
    """Work `task_id` as far as review. Returns where it stopped."""
    if lab is None:
        from core import dev_lab as lab
    tasks = tasks_mod.load(folder)
    task = tasks_mod._get(tasks, task_id)
    role = registry.role(role_name)
    who = f"{role.role} ({role.provider})"
    registry.may(role_name, "write")
    done = done_steps(task.id, log)

    def step(name: str, detail: str = "") -> None:
        activity.record(who, STEP_ACTION, task.id, f"{name}: {detail}".rstrip(": "), log)
        tasks_mod.save(task, folder)

    if "claim" not in done:
        tasks_mod.claim(tasks, task.id, who)
        step("claim", ", ".join(task.files))
    if "lab" not in done:
        p = lab.create(task.title, task.body or task.title, evidence=f"Task {task.id}", plan=f"Files: {', '.join(task.files)}")
        task.branch = p.branch
        step("lab", p.proposal_id)
    pid = proposal_id(task)
    if not pid:
        raise LoopError(f"{task.id} has no lab yet.")
    if "write" not in done:
        p = lab.write(pid, coder=coder)
        if p.status == lab.NOT_READY:
            tasks_mod.note(task, who, f"Stopped at write: {p.note}")
            tasks_mod.save(task, folder)
            raise LoopError(p.note)
        step("write", (p.coder_said or "")[:300])
    if "check" not in done:
        p = lab.check(pid, suite=suite)
        if p.status != lab.READY:
            tasks_mod.note(task, who, f"Stopped at check: {p.note}")
            tasks_mod.save(task, folder)
            raise LoopError(p.note)
        step("check", p.tests.get("summary", ""))
    if "review" not in done:
        p = lab.get(pid)
        tasks_mod.note(task, who, f"Ready for review: lab {pid}, {p.tests.get('summary', '')}; files {', '.join(p.files)}")
        task.status = "review"
        step("review", pid)
    return "review"


__all__ = ["run", "done_steps", "STEPS", "LoopError", "AgentError"]
