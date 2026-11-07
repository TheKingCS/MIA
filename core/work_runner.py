"""
core.work_runner
==================

Missions, and the runner that works them (DEC-0076 and DEC-0079; Zac,
2026-11-03: "set the council on the mission to develop MIA and let them run
at it autonomously" and "delegating tasks based on time available to use
each model so that the dev team doesnt have to sit idle when one model is
unavailable"; `docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md` sections 6.1 and 6.4).

**A mission** is a file in `work/missions/` (`M-0001.md`): a goal, a
**scope** (the paths its changes may touch), a **budget** (tasks, hours,
calls per provider), the roles it may use, a **reserve** (how much of a
subscription to leave Zac) and `your_turn_limit` (how many tasks may wait
for Zac before it stops writing more). Its tasks are the ones whose
`source` is the mission's id. Only Zac starts one (`tools.work mission
start`, or the dev window); it's `active`, `paused` or `done`.

**The runner** takes one step at a time (`step()`), and every choice it
makes goes into the history with its reason:

1. Stops if `work/STOP` exists, the mission isn't active, or its budget is
   spent.
2. Doesn't write more while `your_turn_limit` tasks wait for Zac.
3. Picks the next ready task of the mission whose files are in scope and
   don't overlap work in progress.
4. **Picks who writes by who has time**: the role's providers in order
   (`providers` in `work/agents.json`), the first that's installed and not
   resting at a usage limit (core/dev_usage.py). A writer that hits a limit
   halfway is recorded as resting, and the next step hands the same task, in
   the same lab copy, to the next provider.
5. Runs the loop to review (core/work_loop.py), then refuses a change that
   touched anything outside the scope before any review is spent on it.
6. Asks for reviews from providers that aren't the author's and have time,
   until the task has what it needs (core/work_review.py).
7. With nothing to write (every writer resting, or the queue empty), does
   the local work instead: MIA's write-ups of finished tasks
   (core/dev_knowledge.py), on this PC, at no one's usage.

It **never approves**: a merge is still Zac at the keyboard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from core import work_activity as activity
from core import work_tasks as tasks_mod
from core.atomic_write import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
MISSIONS = ROOT / "work" / "missions"
STOP_FILE = ROOT / "work" / "STOP"
WHO = "runner"


@dataclass
class Mission:
    """One mission file (work/missions/M-0001.md): its goal, status (active, paused, done), scope, the roles it may
    use, its budget (tasks, hours, provider calls), how many tasks may wait for Zac, when it started, the sources a
    standing mission also takes tasks from, and its body text.
    """
    id: str
    goal: str
    status: str = "paused"
    scope: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    tasks: int = 5  # most tasks it writes
    hours: float = 8.0
    calls: int = 60  # most provider calls, all providers
    your_turn_limit: int = 3
    started: str = ""
    body: str = ""
    # A standing mission also works tasks from these sources (DEC-0094, step 6: "loop:" for the loops' tasks)
    takes: list[str] = field(default_factory=list)

    FIELDS = ("id", "goal", "status", "scope", "roles", "tasks", "hours", "calls", "your_turn_limit", "started", "takes")

    def works(self, task) -> bool:
        """Whether a task is this mission's: its source is the mission's id, or starts with one the mission takes."""
        return task.source == self.id or any(task.source.startswith(p) for p in self.takes)

    def to_text(self) -> str:
        """The mission file: a front matter block of its fields (lists comma-separated), then the body."""
        lines = ["---"] + [f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k in self.FIELDS
                           for v in [getattr(self, k)]] + ["---", self.body.strip(), ""]
        return "\n".join(lines)


def _parse(text: str) -> Optional[Mission]:
    """A Mission from a mission file, or None when there's no front matter, no id, or a number that won't read."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text.replace("\r\n", "\n"), re.S)
    if not m:
        return None
    raw = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        raw[k.strip()] = v.strip()
    try:
        return Mission(id=raw["id"], goal=raw.get("goal", ""), status=raw.get("status", "paused"),
                       scope=[s.strip() for s in raw.get("scope", "").split(",") if s.strip()],
                       roles=[s.strip() for s in raw.get("roles", "").split(",") if s.strip()],
                       tasks=int(raw.get("tasks", 5)), hours=float(raw.get("hours", 8)), calls=int(raw.get("calls", 60)),
                       your_turn_limit=int(raw.get("your_turn_limit", 3)), started=raw.get("started", ""),
                       takes=[s.strip() for s in raw.get("takes", "").split(",") if s.strip()],
                       body=m.group(2).strip())
    except (KeyError, ValueError):
        return None


def missions(folder: Path = MISSIONS) -> dict[str, Mission]:
    """Every mission in the folder (M-*.md) by id; a file that won't parse is left out."""
    out = {}
    for path in sorted(Path(folder).glob("M-*.md")) if Path(folder).exists() else []:
        found = _parse(path.read_text(encoding="utf-8"))
        if found:
            out[found.id] = found
    return out


def save(mission: Mission, folder: Path = MISSIONS) -> None:
    """Writes a mission file atomically."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    atomic_write_text(Path(folder) / f"{mission.id}.md", mission.to_text())


def new(goal: str, scope: list[str], roles: list[str] = (), tasks: int = 5, hours: float = 8.0, calls: int = 60,
        folder: Path = MISSIONS, log=activity.ACTIVITY) -> Mission:
    """A new paused mission with the next M-number, saved and recorded in the activity log as Zac's; it needs a goal
    and a scope (ValueError otherwise).
    """
    if not goal.strip() or not scope:
        raise ValueError("A mission needs a goal and a scope (the paths it may change).")
    taken = [int(m[2:]) for m in missions(folder)]
    mission = Mission(id=f"M-{(max(taken) + 1) if taken else 1:04d}", goal=goal.strip(), scope=list(scope),
                      roles=list(roles), tasks=tasks, hours=hours, calls=calls)
    save(mission, folder)
    activity.record("zac", "mission", mission.id, f"new: {mission.goal}", log)
    return mission


def set_status(mission_id: str, status: str, who: str, folder: Path = MISSIONS, log=activity.ACTIVITY,
               confirm: Optional[Callable[[str], str]] = None) -> Mission:
    """Start, pause or finish a mission. Starting one spends Zac's usage, so it's his, at the keyboard
    or in the dev window (which holds its own key)."""
    found = missions(folder).get(mission_id.upper())
    if found is None:
        raise ValueError(f"No mission {mission_id}.")
    if status not in ("active", "paused", "done"):
        raise ValueError("A mission is active, paused or done.")
    if status == "active":
        if who != "zac":
            raise ValueError("Only Zac starts a mission.")
        if confirm is not None:
            try:
                typed = confirm(f"Start {found.id} ({found.goal})? It spends your usage within its budget. Type {found.id}: ")
            except (EOFError, OSError):
                typed = ""
            if (typed or "").strip().upper() != found.id:
                raise ValueError("Not started: only Zac, at the keyboard, starts a mission.")
        found.started = found.started or datetime.now(timezone.utc).isoformat(timespec="seconds")
    found.status = status
    save(found, folder)
    activity.record(who, "mission", found.id, f"{status}", log)
    return found


# ------------------------------------------------------------------ the rules (pure)

def in_scope(paths: list[str], scope: list[str]) -> list[str]:
    """Pure logic. The paths outside the scope ("core/" covers everything under it)."""
    def inside(p: str) -> bool:
        return any(p == s or (s.endswith("/") and p.startswith(s)) or p.startswith(s.rstrip("/") + "/") for s in scope)
    return [p for p in paths if not inside(p)]


def spent(mission: Mission, log=activity.ACTIVITY, usage=None) -> dict:
    """What the mission has used: tasks written, hours since it started, provider calls since then."""
    written = {e.get("task") for e in activity.events(log) if e.get("who") == WHO and e.get("action") == "runner"
               and str(e.get("detail", "")).startswith(f"{mission.id} write")}
    hours = 0.0
    if mission.started:
        hours = (datetime.now(timezone.utc) - datetime.fromisoformat(mission.started)).total_seconds() / 3600
    calls = 0
    if usage is not None and mission.started:
        calls = sum(1 for u in usage.tail(2000) if u.get("at", "") >= mission.started)
    return {"tasks": len(written - {""}), "hours": round(hours, 2), "calls": calls}


def over_budget(mission: Mission, used: dict) -> str:
    """Pure logic. Why the mission must stop, or ""."""
    if used["tasks"] >= mission.tasks:
        return f"its {mission.tasks} tasks are written"
    if used["hours"] >= mission.hours:
        return f"its {mission.hours:g} hours are up"
    if used["calls"] >= mission.calls:
        return f"its {mission.calls} calls are spent"
    return ""


def resting(provider: str, state: Callable[[str], dict]) -> bool:
    """Whether a provider is resting at a usage limit (cooling); a state that can't be read counts as not resting."""
    try:
        return state(provider).get("state") == "cooling"
    except OSError:
        return False


def writer_for(role, registry, state: Callable[[str], dict]) -> Optional[str]:
    """The role's first provider that's here and has time (DEC-0079), or None."""
    for name in getattr(role, "providers", None) or [role.provider]:
        provider = registry.providers.get(name)
        if provider is not None and "write" in provider.can and provider.available() and not resting(name, state):
            return name
    return None


# ------------------------------------------------------------------ one step

def _with_provider(registry, role_name: str, provider: str):
    """The registry with that role run on `provider` for this step (the role keeps its tier)."""
    import copy

    swapped = copy.deepcopy(registry)
    swapped.roles[role_name].provider = provider
    return swapped


def step(mission_id: str, registry, *, loop=None, review=None, learn=None, shadow=None, state=None, lab=None, usage=None,
         folder: Path = MISSIONS, tasks_dir=tasks_mod.TASKS_DIR, log=activity.ACTIVITY,
         stop_file: Path = STOP_FILE) -> str:
    """One thing the mission allows now. Returns what it did, in words (also kept in the history)."""
    from core import work_review

    if loop is None:
        from core import work_loop as loop
    review = review or (lambda task_id, role: work_review.review(task_id, role, registry, ask=work_review.ask_provider,
                                                                 diff=work_review.lab_diff, folder=tasks_dir, log=log))
    if state is None:
        from core.dev_usage import state
    if learn is None:
        from core.dev_knowledge import retrospective as learn
    if shadow is None:
        from core.mia_coder import shadow

    def said(what: str, task_id: str = "") -> str:
        activity.record(WHO, "runner", task_id, f"{mission_id} {what}", log)
        return what

    mission = missions(folder).get(mission_id.upper())
    if mission is None:
        return f"No mission {mission_id}."
    if Path(stop_file).exists():
        return said("stop: work/STOP is there")
    if mission.status != "active":
        return f"{mission.id} is {mission.status}."
    why = over_budget(mission, spent(mission, log, usage))
    if why:
        mission.status = "paused"
        save(mission, folder)
        return said(f"stop: {why}")
    tasks = tasks_mod.load(tasks_dir)
    mine = [t for t in tasks.values() if mission.works(t)]

    # Reviews first: a written change waiting for its reviewers is the cheapest step forward.
    for task in [t for t in mine if t.status == "review"]:
        needed = work_review.reviewers_needed(registry, work_review.author_of(task.id, log))
        have = set(work_review.approvals(task.id, log))
        if work_review.open_objections(task.id, log) or len(have) >= needed:
            continue
        author = work_review.author_of(task.id, log)
        for role in [r for r in registry.roles.values() if r.tier == "review" and (not mission.roles or r.role in mission.roles)]:
            provider = registry.providers.get(role.provider)
            if role.provider in have or author.endswith(f"({role.provider})") or provider is None or \
                    not provider.available() or resting(role.provider, state):
                continue
            try:
                verdict = review(task.id, role.role)
            except Exception as problem:  # a reviewer that's out says so, and is recorded as resting if it's a limit
                return said(f"review {task.id} by {role.provider} didn't happen: {str(problem)[:200]}", task.id)
            return said(f"review {task.id} by {role.provider} ({role.role}): {verdict}", task.id)

    waiting = sum(1 for t in mine if t.status == "review")
    if waiting >= mission.your_turn_limit:
        return said(f"hold: {waiting} tasks wait for Zac; not writing more yet")

    busy = [f for t in tasks.values() if t.status in ("claimed", "review") for f in t.files]
    for task in sorted([t for t in mine if t.status in ("open", "claimed")], key=lambda t: t.id):
        if task.status == "open" and not tasks_mod.ready(task, tasks):
            continue
        outside = in_scope(task.files, mission.scope)
        if outside:
            continue
        if task.status == "open" and tasks_mod.overlaps(task.files, busy):
            continue
        role_name = task.role if task.role in registry.roles else next(
            (r.role for r in registry.roles.values() if r.tier == "experiment" and (not mission.roles or r.role in mission.roles)), "")
        if not role_name:
            return said("hold: no role may write for this mission")
        writer = writer_for(registry.roles[role_name], registry, state)
        if writer is None:
            break  # every writer is resting: local work below
        said(f"write {task.id} as {role_name} on {writer}"
             + ("" if writer == registry.roles[role_name].provider else " (the first choice is resting)"), task.id)
        try:
            stopped = loop.run(task.id, role_name, _with_provider(registry, role_name, writer), lab=lab,
                               folder=tasks_dir, log=log)
        except Exception as problem:
            from core.dev_usage import outcome, record

            if outcome(str(problem)) == "limit":  # resting now: the next step hands it to the next provider
                record(writer, "write", 0, 0, 0, error=str(problem), task=task.id, store=usage)
                return said(f"write {task.id} on {writer} hit its usage limit; handing it on next step", task.id)
            return said(f"write {task.id} stopped: {str(problem)[:200]}", task.id)
        if stopped == "review":
            proposal = (lab or _lab()).get(tasks_mod.load(tasks_dir)[task.id].branch[len("lab/"):])
            outside = in_scope(list(getattr(proposal, "files", []) or []), mission.scope)
            if outside:
                tasks = tasks_mod.load(tasks_dir)
                tasks_mod.move(tasks, task.id, "blocked", WHO, f"changed files outside {mission.id}'s scope: {', '.join(outside)}")
                tasks_mod.save(tasks[task.id], tasks_dir)
                return said(f"blocked {task.id}: outside the scope ({', '.join(outside)})", task.id)
        return said(f"wrote {task.id}: now {stopped}", task.id)

    # The local work, at no one's usage. First MIA's practice (DEC-0074): a task the council wrote that she
    # hasn't attempted, small enough for her (a few files).
    attempted = {e.get("task") for e in activity.events(log) if e.get("action") == "shadow"}
    written = {e.get("task") for e in activity.events(log) if e.get("action") == "loop"
               and str(e.get("detail", "")).startswith("write")}
    for task in sorted(tasks.values(), key=lambda t: t.id):
        if task.id in written and task.id not in attempted and 0 < len(task.files) <= 4:
            try:
                result = shadow(task.id)
            except Exception as problem:
                return said(f"MIA's attempt at {task.id} didn't run: {str(problem)[:200]}", task.id)
            return said(f"MIA's attempt at {task.id}: {result.get('outcome', '?')}", task.id)
    tried = {e.get("task") for e in activity.events(log) if e.get("action") == "learn"
             or (e.get("who") == WHO and " learned from " in f" {e.get('detail', '')}")}
    for task in [t for t in tasks.values() if t.status == "done" and t.id not in tried]:  # the local work
        try:
            kept = learn(task.id)
        except Exception:
            continue
        return said(f"learned from {task.id}: {len(kept)} entr{'y' if len(kept) == 1 else 'ies'}", task.id)
    return said("idle: nothing ready in scope, and nothing left to write up")


def _lab():
    """The dev lab module, imported late (the runner is used where the lab may not be needed)."""
    from core import dev_lab

    return dev_lab
