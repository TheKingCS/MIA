"""
core.work_dashboard
=====================

The development dashboard's data (DEC-0068/0070, step 5 of
`docs/DEV_ECOSYSTEM_AUDIT.md`), served as `/api/dev` to `web/dev.html`: one
view over the work and the contributors. Read-only: it shows the tasks, the
agents and whether each is here, the review and approval queue, and the
activity history, searchable. Changing anything stays in `tools/work.py`, and
approving stays Zac at the keyboard (core/work_review.py), not a button.

Only the device's owner sees it: the first real person who set this MIA up,
never a child. It reads the repo's `work/` folder, so on a device without
the repo (the phone) it says so.
"""

from __future__ import annotations

from typing import Optional

from core import work_activity as activity
from core import work_tasks as tasks_mod

RECENT = 40


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
    from core.work_review import latest_verdict

    def row(t) -> dict:
        waiting = [d for d in t.depends if tasks.get(d) is None or tasks[d].status != "done"]
        return {"id": t.id, "title": t.title, "status": "ready" if tasks_mod.ready(t, tasks) else t.status,
                "owner": t.owner, "role": t.role, "waiting_on": waiting if t.status == "open" else [],
                "branch": t.branch, "decisions": t.decisions, "updated": t.updated,
                "verdict": latest_verdict(t.id, log) if t.status == "review" else ""}

    rows = [row(t) for t in tasks.values()]
    open_rows = [r for r in rows if r["status"] not in tasks_mod.FINISHED]
    order = {"review": 0, "claimed": 1, "ready": 2, "blocked": 3, "open": 4}
    open_rows.sort(key=lambda r: (order.get(r["status"], 9), r["id"]))
    try:
        from core.work_agents import load as load_agents

        registry = load_agents()
        agents = [{"role": r.role, "tier": r.tier, "provider": r.provider,
                   "here": registry.providers[r.provider].available()} for r in registry.roles.values()]
    except Exception:  # a broken registry file still shows the work
        agents = []
    events = activity.search(query, path=log) if query else activity.events(log)
    return {
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
