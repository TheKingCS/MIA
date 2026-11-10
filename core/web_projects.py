"""
core.web_projects
===================

Projects on the web (DEC-0125: projects and their tasks were voice-only;
the desktop has them in the Toolbox's Project Manager). A project is a
bounded build or job of the person's own ("Greenhouse", "Fix the fence"),
with a status, a due date, a budget, what's been spent on it (the expenses
tagged to it: core/homestead_costs.build_cost), the tools bought for it, the
reason it serves (core/intent_manager.py) and its tasks
(core/task_manager.py).

`projects_page()` gives them underway first (Active, Planning, On Hold),
then the finished; each with its tasks, open ones first, its missions as
cards (each opens on the Missions page) and its progress, worked out from
both (core/mission_projects.py, DEC-0152: one source of truth, never a
copy). Changes are actions, so the page and voice agree and "undo that"
takes each back:

- `project.add` / `project.edit` / `project.delete` (the shared record
  table in core/more_actions.py; by voice add_project, delete_project);
- `project.budget`: its budget (set_build_budget);
- `task.add`, `task.done` (core/actions.py), `task.reopen`, `task.delete`
  (add_task, mark_task_done, delete_task).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

ORDER = {"Active": 0, "Planning": 1, "On Hold": 2, "Complete": 3}


def _card(context, project, tasks_store, names: dict) -> dict:
    """One project for the page: status, due, description, money (budget, spent, left, percent, the biggest kinds of
    spending), tools bought, the reason it serves, its tasks (open first), its missions, its progress from both, and
    its form values."""
    from core.mission_projects import mission_card, missions_for, progress
    from core.homestead_costs import build_cost
    from core.region import money

    try:
        cost = build_cost(context, project)
    except Exception:
        cost = None
    tasks = sorted(tasks_store.tasks_for_project(project.project_id) if tasks_store is not None else [],
                   key=lambda t: (t.done, t.due_date or "9999", t.title.lower()))
    spent = cost.spent if cost else 0.0
    return {"id": project.project_id, "name": project.name, "status": project.status, "due": project.due_date,
            "description": project.description, "why": names.get(project.intent_id or "", ""),
            "budget": project.budget, "budget_text": money(project.budget) if project.budget else "",
            "spent_text": money(spent) if spent else "", "left_text": money(cost.remaining) if cost and cost.remaining is not None else "",
            "over": bool(cost and cost.remaining is not None and cost.remaining < 0),
            "percent": cost.percent_used if cost else None,
            "by_category": [{"kind": k, "text": money(v)} for k, v in list((cost.by_category if cost else {}).items())[:3]],
            "tools": list(cost.tools_bought) if cost else [],
            "tasks": [{"id": t.task_id, "title": t.title, "done": t.done, "due": t.due_date, "notes": t.notes}
                      for t in tasks],
            "tasks_done": sum(1 for t in tasks if t.done), "tasks_total": len(tasks),
            "missions": [mission_card(context, m) for m in missions_for(context, project.project_id)],
            "progress": progress(context, project),
            "values": {"name": project.name, "status": project.status, "due_date": project.due_date,
                       "description": project.description}}


def projects_page(context) -> dict:
    """The Projects screen: every project, underway first (Active, Planning, On Hold) then finished, each as `_card`;
    counts (underway, open tasks, all, and each status's, for the filter tabs); the forms. {"available": False} without
    the projects store."""
    from core.more_actions import forms

    projects = getattr(context, "projects", None)
    if projects is None:
        return {"available": False}
    intents = getattr(context, "intents", None)
    names = {i.intent_id: i.name for i in intents.all_intents()} if intents is not None else {}
    tasks = getattr(context, "tasks", None)
    cards = [_card(context, p, tasks, names)
             for p in sorted(projects.all_projects(), key=lambda p: (ORDER.get(p.status, 9), p.due_date or "9999",
                                                                    p.name.lower()))]
    every = forms()
    return {"available": True, "projects": cards,
            "counts": {"underway": sum(1 for c in cards if c["status"] != "Complete"), "all": len(cards),
                       "by_status": {s: sum(1 for c in cards if c["status"] == s) for s in ORDER},
                       "open_tasks": sum(c["tasks_total"] - c["tasks_done"] for c in cards)},
            "forms": {"project": every["project"], "task": TASK_FORM}}


# ------------------------------------------------------------------ actions

TASK_FORM = {"noun": "task", "id_param": "task_id", "fields": [
    {"name": "title", "label": "What needs doing", "type": "text", "required": True, "options": [], "default": None},
    {"name": "due_date", "label": "By when (optional)", "type": "date", "required": False, "options": [], "default": None},
]}


def _project(context, params):
    """The project the params name; ActionError when it's gone."""
    project = _need(context, "projects").get_project(str(params.get("project_id") or ""))
    if project is None:
        raise ActionError("That project isn't there anymore.")
    return project


def _task(context, params):
    """The task the params name; ActionError when it's gone."""
    task = _need(context, "tasks").get_task(str(params.get("task_id") or ""))
    if task is None:
        raise ActionError("That task isn't there anymore.")
    return task


def _budget_of(params) -> float:
    """The budget asked for, checked: a number, 0 (none) or more."""
    try:
        value = float(str(params.get("budget", "")).replace(",", "").lstrip("$").strip() or 0)
    except ValueError:
        raise ActionError("The budget has to be a number.") from None
    if value < 0:
        raise ActionError("The budget can't be negative.")
    return round(value, 2)


def _describe_budget(context, params) -> str:
    """The approval sentence for project.budget."""
    from core.region import money

    project, value = _project(context, params), _budget_of(params)
    return f"Set the {project.name} budget to {money(value)}" if value else f"Clear the {project.name} budget"


def _budget(context, params) -> str:
    """Does project.budget."""
    from core.region import money

    project, value = _project(context, params), _budget_of(params)
    context.projects.update_project(project.project_id, budget=value)
    return f"{project.name}'s budget is {money(value)}." if value else f"{project.name} has no budget now."


def _title(params) -> str:
    """The task's words, tidied; ActionError when there are none."""
    title = " ".join(str(params.get("title") or "").split())
    if not title:
        raise ActionError("What needs doing?")
    return title


def _describe_task_add(context, params) -> str:
    """The approval sentence for task.add."""
    return f"Add \"{_title(params)}\" to {_project(context, params).name}"


def _task_add(context, params) -> str:
    """Does task.add: a task on the project, with its due date when given."""
    project = _project(context, params)
    due = str(params.get("due_date") or "").strip()[:10]
    _need(context, "tasks").add_task(project.project_id, _title(params), due_date=due)
    return f"Added \"{_title(params)}\" to {project.name}."


def _describe_reopen(context, params) -> str:
    """The approval sentence for task.reopen; a task not done is refused."""
    task = _task(context, params)
    if not task.done:
        raise ActionError(f"\"{task.title}\" isn't done yet.")
    return f"Mark \"{task.title}\" not done"


def _reopen(context, params) -> str:
    """Does task.reopen."""
    task = _task(context, params)
    context.tasks.update_task(task.task_id, done=False)
    return f"\"{task.title}\" is open again."


def _task_delete(context, params) -> str:
    """Does task.delete."""
    task = _task(context, params)
    context.tasks.delete_task(task.task_id)
    return f"Took \"{task.title}\" off."


PROJECT_ACTIONS = {a.kind: a for a in (
    ActionType("project.budget", "Budget", {"project_id": "the project", "budget": "how much (0 for none)"},
               _describe_budget, _budget),
    ActionType("task.add", "Add a task", {"project_id": "the project", "title": "what needs doing",
                                          "due_date": "by when (optional)"}, _describe_task_add, _task_add),
    ActionType("task.reopen", "Not done", {"task_id": "the task"}, _describe_reopen, _reopen),
    ActionType("task.delete", "Delete", {"task_id": "the task"},
               lambda c, p: f"Take \"{_task(c, p).title}\" off", _task_delete),
)}
ACTION_TYPES.update(PROJECT_ACTIONS)
