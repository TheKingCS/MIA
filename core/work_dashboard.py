"""
core.work_dashboard
=====================

The development dashboard's data (DEC-0068/0070, step 5 of
`docs/DEV_ECOSYSTEM_AUDIT.md`), served as `/api/dev` to `web/dev.html`: one
view over the work and the contributors. Read-only: it shows the tasks, the
agents and whether each is here, the review and approval queue, and the
activity history, searchable. Changing anything stays in `tools/work.py`, and
approving stays Zac at the keyboard (core/work_review.py), not a button.

The board (Zac, 2026-11-03: "a window that makes it all easy to view and
understand the workflow and what is going on, what is building, who is
building it"): each task has a stage, Up Next, Building, In Review, Your
Turn or Done, with who is on it, its reviews against the two it needs, what
happens next in a sentence, and its own timeline. `tools/dev_window.py`
opens it as its own window.

Only the device's owner sees it: the first real person who set this MIA up,
never a child. It reads the repo's `work/` folder, so on a device without
the repo (the phone) it says so.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core import work_activity as activity
from core import work_tasks as tasks_mod

RECENT = 40
TIMELINE = 30  # events per task on its card
STAGES = ("next", "building", "review", "yours", "done")


def signed_in(provider) -> Optional[bool]:
    """Whether a provider's account is signed in on this computer, from the
    file its CLI keeps when it is (never its contents); None when unknown."""
    if provider.kind in ("local", "mia"):
        return provider.available()
    home = Path.home()
    marks = {"claude": home / ".claude" / ".credentials.json", "codex": home / ".codex" / "auth.json"}
    if provider.command in marks:
        return marks[provider.command].exists()
    if provider.command == "copilot":
        return None if (home / ".copilot").exists() else False
    return None


def _usage(provider: str, seen: dict) -> dict:
    """A provider's usage state (core/dev_usage.py), once per page."""
    from core import dev_usage

    try:
        seen[provider] = dev_usage.state(provider)
    except OSError:
        seen[provider] = {"state": "ready", "until": "", "calls": 0}
    return seen[provider]


def _council(n: int = 60) -> list[dict]:
    """The council chat's latest messages (core/council.py)."""
    from core import council

    try:
        return council.recent(n)
    except OSError:
        return []


def _missions(events: list[dict]) -> list[dict]:
    """The council's missions (core/work_runner.py): what each may do, what it's used, its latest steps."""
    from core import work_runner

    try:
        found = work_runner.missions()
    except OSError:
        return []
    out = []
    for m in found.values():
        steps = [e for e in events if e.get("who") == "runner" and str(e.get("detail", "")).startswith(m.id + " ")]
        out.append({"id": m.id, "goal": m.goal, "status": m.status, "scope": m.scope, "budget":
                    {"tasks": m.tasks, "hours": m.hours, "calls": m.calls}, "used": work_runner.spent(m),
                    "steps": [{"at": e["at"], "task": e.get("task", ""), "what": e["detail"][len(m.id) + 1:]}
                              for e in steps[-8:]][::-1]})
    return out


_MAP: dict = {}  # the architecture map, rebuilt every ten minutes (it reads the whole repo: ~2 s)


def _architecture() -> dict:
    """MIA's architecture and growth (core/dev_map.py), derived from the code."""
    import time

    from core import dev_map

    if not _MAP or time.monotonic() - _MAP["at"] > 600:
        try:
            _MAP.update(at=time.monotonic(), map=dev_map.architecture())
        except (OSError, SyntaxError):
            return {}
    return _MAP["map"]


def _independence() -> dict:
    """The ledger (core/dev_ledger.py): what each provider has shown it can do, by skill."""
    from core import dev_ledger

    try:
        found = dev_ledger.ledger()
    except OSError:
        return {"stages": list(dev_ledger.STAGES), "rows": []}
    rows = [{"provider": p, "skill": s, **{k: v for k, v in r.items() if k != "recent"},
             "recent": [o["why"] + (" ✓" if o["passed"] else " ✗") for o in r["recent"]]}
            for p, skills in found.items() for s, r in skills.items() if r["attempts"] or p == "ollama-coder"]
    return {"stages": list(dev_ledger.STAGES), "rows": rows}


def _members() -> list[dict]:
    """The council's members and their voices (work/agents.json, DEC-0082)."""
    try:
        from core.council import members

        return [{"id": k, "name": m["name"], "provider": m.get("provider", ""), "about": m.get("about", ""),
                 "voice": m.get("voice", ""), "chosen": m.get("voice_chosen_by") == "zac"} for k, m in members().items()]
    except (OSError, ValueError):
        return []


def _knowledge() -> dict:
    """What the team learned (core/dev_knowledge.py): MIA's notes waiting for someone to confirm them."""
    from core import dev_knowledge

    try:
        found = dev_knowledge.entries()
    except OSError:
        return {"waiting": [], "confirmed": 0, "withdrawn": 0}
    count = lambda s: sum(1 for e in found if e.get("status") == s)  # noqa: E731
    return {"waiting": [{"id": e["id"], "kind": e["kind"], "title": e["title"], "body": e["body"][:600],
                         "from": e.get("from") or []} for e in found if e.get("status") == "derived"][-10:][::-1],
            "confirmed": count("confirmed"), "withdrawn": count("withdrawn")}


def _saga(shown: int = 12) -> dict:
    """The Chronicle Archive (core/saga.py): what's waiting for Zac, most significant and newest first,
    and the latest events kept."""
    from core import saga

    try:
        waiting = saga.candidates()
        kept = saga.events()
    except OSError:
        return {"waiting": 0, "candidates": [], "events": []}
    ranked = sorted(waiting, key=lambda c: (c["significance"], c["at"]), reverse=True)
    return {"waiting": len(waiting), "candidates": ranked[:shown], "events": list(reversed(kept))[:20]}


def _reviews(task_id: str, events: list[dict]) -> list[dict]:
    """The reviews of the current change (a rewrite starts again), oldest first."""
    from core.work_review import provider_of

    out: list[dict] = []
    for e in events:
        if e.get("task") != task_id:
            continue
        if e.get("action") == "loop" and str(e.get("detail", "")).startswith("write"):
            out = []
        elif e.get("action") == "review":
            said = str(e.get("detail", ""))
            out.append({"who": e.get("who", ""), "provider": provider_of(e.get("who", "")),
                        "verdict": said.split(":", 1)[0], "said": said.split(":", 1)[-1].strip()[:400],
                        "at": e.get("at", "")})
    return out


def review_state(task, log, needed: int) -> dict:
    """Where a task in review stands, and whose move it is, in words."""
    from core import work_review as rv

    objections = rv.open_objections(task.id, log)
    have = rv.approvals(task.id, log)
    latest = rv.latest_verdict(task.id, log)
    settled = rv.settled_by_zac(task.id, log)
    approve = f"python -m tools.work approve {task.id}"
    if objections:
        raised = ", ".join(sorted({e.get("who", "") for e in objections}))
        return {"stage": "review", "next": f"{raised} asked for changes. The builder fixes it or answers why not "
                f"(resolve), and the reviewer looks again.", "command": ""}
    if settled:
        return {"stage": "yours", "next": "You settled the review. It's ready for your approval.", "command": approve}
    if not latest:
        return {"stage": "review", "next": f"Waiting for its first review ({needed} needed, from different "
                "providers).", "command": ""}
    if latest == "changes":
        return {"stage": "yours", "next": "The builder answered the objection but the reviewer still says no. "
                "Read both and decide.", "command": f'python -m tools.work resolve {task.id} --by zac --how "..."'}
    if len(have) < needed:
        return {"stage": "review", "next": f"{len(have)} of {needed} reviews approve. Waiting for a reviewer on "
                "another provider.", "command": ""}
    return {"stage": "yours", "next": f"{len(have)} of {needed} reviewers approve. Ready for your approval.",
            "command": approve}


def owner_id(context) -> str:
    """The device's owner: its first real account (a password or an email)."""
    profiles = getattr(context, "profiles", None)
    if profiles is None:
        return ""
    real = [p for p in profiles.list_profiles() if getattr(p, "has_password", False) or getattr(p, "email", "")]
    return min(real, key=lambda p: p.created_at or "").profile_id if real else ""


def allowed(context, profile_id: str) -> bool:
    from core.child_accounts import is_child

    return bool(profile_id) and profile_id == owner_id(context) and not is_child(context, profile_id)


def page(context, query: str = "", tasks_dir=tasks_mod.TASKS_DIR, log=activity.ACTIVITY) -> dict:
    if not tasks_dir.exists():
        return {"available": False}
    tasks = tasks_mod.load(tasks_dir)
    from core import work_review as rv
    from core.work_loop import STEPS, done_steps

    try:
        from core.work_agents import load as load_agents

        registry = load_agents()
    except Exception:  # a broken registry file still shows the work
        registry = None
    all_events = activity.events(log)

    def row(t) -> dict:
        waiting = [d for d in t.depends if tasks.get(d) is None or tasks[d].status != "done"]
        status = "ready" if tasks_mod.ready(t, tasks) else t.status
        out = {"id": t.id, "title": t.title, "status": status,
               "owner": t.owner, "role": t.role, "waiting_on": waiting if t.status == "open" else [],
               "branch": t.branch, "decisions": t.decisions, "updated": t.updated,
               "verdict": rv.latest_verdict(t.id, log) if t.status == "review" else "",
               "stage": "done" if status in tasks_mod.FINISHED else "building" if status == "claimed" else "next",
               "next": "", "command": "", "reviews": [], "needed": 0, "approvals": [], "steps": [],
               "timeline": []}
        if status in tasks_mod.FINISHED:
            return out
        if status in ("claimed", "review"):
            done = done_steps(t.id, log)
            out["steps"] = [{"step": s, "done": s in done} for s in STEPS]
        if status == "claimed":
            left = [s for s in STEPS if s not in done_steps(t.id, log)]
            out["next"] = f"{t.owner or 'Someone'} is on it" + (f": next, {left[0]}." if left else ".")
        elif status == "review":
            needed = rv.reviewers_needed(registry, rv.author_of(t.id, log)) if registry else rv.REVIEWS_NEEDED
            out.update(review_state(t, log, needed), reviews=_reviews(t.id, all_events), needed=needed,
                       approvals=rv.approvals(t.id, log))
        elif status == "ready":
            out["next"], out["command"] = "Ready to start.", f'python -m tools.work run {t.id} --as "<role>"'
        elif status == "blocked":
            out["next"] = "Blocked. See its notes for why."
        elif waiting:
            out["next"] = "Starts after " + ", ".join(waiting) + "."
        out["timeline"] = [e for e in all_events if e.get("task") == t.id][-TIMELINE:]
        return out

    rows = [row(t) for t in tasks.values()]
    open_rows = [r for r in rows if r["status"] not in tasks_mod.FINISHED]
    order = {"review": 0, "claimed": 1, "ready": 2, "blocked": 3, "open": 4}
    open_rows.sort(key=lambda r: (order.get(r["status"], 9), r["id"]))
    agents, usage = [], {}
    for r in (registry.roles.values() if registry else []):
        provider = registry.providers[r.provider]
        who = f"{r.role} ({r.provider})"
        on = [x["id"] for x in open_rows if x["owner"] == who and x["status"] in ("claimed", "review")]
        last = next((e for e in reversed(all_events) if e.get("who") == who), None)
        agents.append({"role": r.role, "tier": r.tier, "provider": r.provider, "model": provider.model,
                       "here": provider.available(), "signed_in": signed_in(provider), "working_on": on,
                       "last": last, "usage": usage.get(r.provider) or _usage(r.provider, usage)})
    events = activity.search(query, path=log) if query else all_events
    board = {stage: [x for x in rows if x["stage"] == stage] for stage in STAGES}
    board["done"] = sorted(board["done"], key=lambda r: r["updated"], reverse=True)[:8]
    return {
        "board": board,
        "latest": all_events[-1] if all_events else None,
        "lessons": rv._lessons(),
        "council": _council(),
        "saga": _saga(),
        "missions": _missions(all_events),
        "knowledge": _knowledge(),
        "members": _members(),
        "independence": _independence(),
        "architecture": _architecture(),
        "available": True,
        "summary": {s: sum(1 for r in rows if r["status"] == s) for s in ("ready", "claimed", "review", "blocked", "done")},
        "queue": [r for r in open_rows if r["status"] == "review"],
        "tasks": open_rows,
        "done": sorted((r for r in rows if r["status"] == "done"), key=lambda r: r["updated"], reverse=True)[:20],
        "agents": agents,
        "activity": list(reversed(events))[:RECENT if not query else 200],
        "query": query,
    }


def for_person(context, profile_id: str, query: str = "") -> Optional[dict]:
    """The page, or None when this person may not see it."""
    return page(context, query) if allowed(context, profile_id) else None
