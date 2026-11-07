"""
core.loop_coverage
====================

How MIA's improvement loops keep spreading to every process (DEC-0101; Zac,
2026-11-06: "She also needs a method for developing these loops into all
processes that could benefit from a self improvement loop and continue to do
so throughout her development").

**The inventory** (`processes()`) is read from the code itself, so it grows
when MIA does: every personal and household store (core/personal_data.py),
every family of actions (core/actions.py, by the part before the dot), every
daily check (core/application.py), every module folder, and the fixed flows
and development processes below.

**Every process is accounted for**, one of three ways:

- **covered**: a loop in core/loops.py names it in `covers`;
- **declined**: `work/loop_coverage.json` says why it needs no loop
  (`"none"`), with the reason;
- **to do**: `work/loop_coverage.json` lists it as `"todo"` (or
  `"proposed"`, with the task Night School opened for it).

A process that's none of these is **new and unaccounted**, and
`tests/test_loop_coverage.py` fails until whoever added it gives it a loop or
a line saying why not. That's the rule that keeps the loops growing: nothing
new joins MIA without someone deciding how it will be watched.

Night School (core/night_school.py) works through the to-do list, one
family at a time: the teacher drafts the loop, a task carries it, and the
usual paths build and approve it. `dev.loop_coverage` (core/loops.py) tracks
the share covered.

This file and `work/loop_coverage.json` are on the lab's protected list.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "work" / "loop_coverage.json"
STATUSES = ("todo", "proposed", "none")

# What isn't a store, an action, a check or a module, but runs all the same.
FLOWS = {
    "flow:talk": "a turn of conversation: understanding, answering, phrasing",
    "flow:tools": "choosing and using a tool in a turn",
    "flow:undo": "undoing what she did",
    "flow:gate": "unprompted messages through the communication gate",
    "flow:workflows": "her workflows running on their schedule",
    "flow:pc": "the PC she runs on: disk, uptime, the model server",
    "flow:phone": "the phone app and its sync with the PC",
    "flow:glasses": "the glasses: panels, voice, the relay",
    "flow:search": "Ctrl+K search across apps",
    "flow:email": "email drafts and what's sent",
    "flow:actions": "Propose, Approve, Execute, Record, Undo for every action",
    "flow:data": "every store's file: read, written, recovered when it's corrupt",
    "flow:sight": "looking at a photo: what is this, read this, inspect this part",
}
DEV = {
    "dev:code": "the code's shape: layering, docs that match",
    "dev:tasks": "the task queue: stuck, blocked, done",
    "dev:review": "reviews of each change",
    "dev:merge": "merges, and what's reverted after",
    "dev:suite": "the full test suite, against the known failures",
    "dev:dependencies": "the packages MIA depends on: outdated, unsafe",
    "dev:shadow": "MIA's own attempts at the council's tasks",
    "dev:knowledge": "MIA's notebook of what the team learned",
    "dev:usage": "each provider's usage and limits",
    "dev:council": "the council's turns",
    "dev:missions": "missions and the runner",
    "dev:chronicles": "the Chronicles",
    "dev:night_school": "Night School: her lessons, her choices, her teacher",
    "dev:loops": "the loops themselves and how far they reach",
    "dev:docs": "documentation for every file, class and function, enough for MIA to rebuild herself (DEC-0104)",
}
_CHECK = re.compile(r'\("([a-z_]+)", self\._check_[a-z_]+\)')


def _stores() -> dict[str, str]:
    """Each personal and household store as a process (store:name); none when personal_data can't be imported."""
    try:
        from core import personal_data
    except Exception:  # an install missing a store's package still lists the rest
        return {}
    out = {f"store:{name}": "a person's own store" for name, _ in personal_data.PERSONAL_STORES}
    out.update({f"store:{name}": "a household's store" for name, _ in personal_data.HOUSEHOLD_STORES})
    return out


def _actions() -> dict[str, str]:
    """Each action family as a process (action:family) with how many kinds it has; none when the actions can't be
    imported.
    """
    try:
        from core.actions import ACTION_TYPES
    except Exception:
        return {}
    families: dict[str, int] = {}
    for kind in ACTION_TYPES:
        families[kind.split(".")[0]] = families.get(kind.split(".")[0], 0) + 1
    return {f"action:{f}": f"{n} action kind{'s' if n != 1 else ''}" for f, n in families.items()}


def _checks(root: Path = ROOT) -> dict[str, str]:
    """Each daily check registered in core/application.py as a process (check:name), found in its source."""
    text = (root / "core" / "application.py").read_text(encoding="utf-8", errors="replace")
    return {f"check:{name}": "a daily check" for name in _CHECK.findall(text)}


def _modules(root: Path = ROOT) -> dict[str, str]:
    """Each app (a modules folder with a module.py) as a process (module:name)."""
    return {f"module:{p.parent.name}": "an app" for p in sorted((root / "modules").glob("*/module.py"))}


def processes(root: Path = ROOT) -> dict[str, str]:
    """Every process that could have a loop, read from the code: id -> what it is."""
    out = dict(FLOWS)
    out.update(DEV)
    out.update(_stores())
    out.update(_actions())
    out.update(_checks(root))
    out.update(_modules(root))
    return dict(sorted(out.items()))


def decisions(path: Path = DECISIONS) -> dict[str, dict]:
    """What's been decided about each process (work/loop_coverage.json): its status and why or its task; none when
    the file is missing or unreadable.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in (data.get("processes") or {}).items() if isinstance(v, dict)}


def save_decisions(found: dict[str, dict], path: Path = DECISIONS) -> None:
    """Writes the decisions atomically, sorted, with a note on what the file is."""
    body = {"about": "core/loop_coverage.py (DEC-0101): every process MIA has, with a loop or a reason. "
                     "status: todo (needs a loop), proposed (a task drafts it), none (why: no loop needed).",
            "processes": dict(sorted(found.items()))}
    atomic_write_text(path, json.dumps(body, indent=1, ensure_ascii=False) + "\n")


def covered_by(loops=None) -> dict[str, list[str]]:
    """process -> the loops that watch it."""
    if loops is None:
        from core.loops import LOOPS as loops
    out: dict[str, list[str]] = {}
    for loop in loops:
        for p in getattr(loop, "covers", ()) or ():
            out.setdefault(p, []).append(loop.id)
    # A corrections.<area> loop (core/corrections.py) watches every action family of its area for MIA's changes
    # being undone or corrected: it covers them, by the same area rule the loop counts with.
    areas = {loop.id.split(".", 1)[1]: loop.id for loop in loops if loop.id.startswith("corrections.")
             and loop.id != "corrections.all"}
    if areas:
        from core.corrections import area_of

        for pid in _actions():
            area = area_of(pid.split(":", 1)[1])
            if area in areas and areas[area] not in out.get(pid, []):
                out.setdefault(pid, []).append(areas[area])
        for pid, area in CORRECTED_IN.items():  # apps and stores whose records MIA changes through that area's actions
            if area in areas and areas[area] not in out.get(pid, []):
                out.setdefault(pid, []).append(areas[area])
    return out


# Apps and stores the corrections loops watch: chosen by hand, since a name alone misleads ("craft_recipes" isn't
# the kitchen's, "life_events" isn't the calendar's).
CORRECTED_IN = {
    "module:budget": "money", "store:insurance": "money", "store:freedom_log": "money",
    "module:inbox": "inbox",
    "module:maintenance": "maintenance", "store:maintenance": "maintenance",
    "module:missions": "missions", "store:quest_book": "missions", "store:boss_book": "missions",
    "store:reward_shop": "missions",
    "module:workout": "workouts", "store:workout": "workouts", "store:fitness": "workouts", "store:training": "workouts",
    "store:calendar": "calendar", "store:alarms": "calendar",
    "store:projects": "tasks", "store:tasks": "tasks",
    "store:products": "home", "store:materials": "home", "store:components": "home", "store:flock": "home",
    "store:grow_lab": "home", "store:jobs": "home", "store:expeditions": "home", "store:trips": "home",
    "module:expeditions": "home",
    "store:obligations": "money", "store:business": "money", "store:ledger": "money",
    "store:kitchen": "kitchen", "store:craft_recipes": "home", "store:real_estate": "home", "store:places": "home",
    "store:world_map": "home", "store:dungeon": "missions", "store:journal": "memories", "store:relationships": "people",
    "store:security": "home", "store:inventory": "home", "store:waypoints": "home",
    "store:record_sets": "creations", "store:my_record_sets": "creations",
}


def report(root: Path = ROOT, path: Path = DECISIONS, loops=None) -> dict:
    """Where every process stands: covered, declined, to do, proposed, or new and unaccounted."""
    every = processes(root)
    by_loop = covered_by(loops)
    said = decisions(path)
    rows = []
    for pid, what in every.items():
        if pid in by_loop:
            state = "covered"
        else:
            state = (said.get(pid) or {}).get("status", "new")
            state = "declined" if state == "none" else state if state in STATUSES else "new"
        rows.append({"id": pid, "what": what, "state": state, "loops": by_loop.get(pid, []),
                     "why": (said.get(pid) or {}).get("why", ""), "task": (said.get(pid) or {}).get("task", "")})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    needing = len(rows) - counts.get("declined", 0)  # a process declined with a reason needs no loop
    return {"rows": rows, "counts": counts, "total": len(rows),
            "share": round(counts.get("covered", 0) / needing, 3) if needing else 1.0,
            "unknown_covers": sorted(set(by_loop) - set(every))}  # a loop naming a process that isn't there


def next_family(root: Path = ROOT, path: Path = DECISIONS, limit: int = 6) -> list[dict]:
    """The next to-do processes to draft loops for, kept together by kind (all stores, then actions...)."""
    todo = [r for r in report(root, path)["rows"] if r["state"] == "todo"]
    if not todo:
        return []
    order = ("flow", "dev", "action", "store", "check", "module")
    todo.sort(key=lambda r: (order.index(r["id"].split(":")[0]) if r["id"].split(":")[0] in order else 9, r["id"]))
    kind = todo[0]["id"].split(":")[0]
    return [r for r in todo if r["id"].startswith(kind + ":")][:limit]


def mark(ids: list[str], status: str, why: str = "", task: str = "", path: Path = DECISIONS) -> None:
    """Records a status (todo, proposed, none) for processes, with why or the task drafting its loop; ValueError for
    another status.
    """
    if status not in STATUSES:
        raise ValueError(f"The status is one of {', '.join(STATUSES)}.")
    found = decisions(path)
    for pid in ids:
        entry = {"status": status}
        if why:
            entry["why"] = why
        if task:
            entry["task"] = task
        found[pid] = entry
    save_decisions(found, path)


def seed(root: Path = ROOT, path: Path = DECISIONS) -> int:
    """Every process with no loop and no line yet becomes a to-do. Returns how many were added."""
    found = decisions(path)
    by_loop = covered_by()
    added = 0
    for pid in processes(root):
        if pid not in by_loop and pid not in found:
            found[pid] = {"status": "todo"}
            added += 1
    save_decisions(found, path)
    return added


def share(root: Path = ROOT, path: Path = DECISIONS) -> Optional[float]:
    """The share of processes needing a loop that have one (from report()), or None when there are no processes."""
    r = report(root, path)
    return r["share"] if r["total"] else None
