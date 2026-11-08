"""Projects on the web (core/web_projects.py, DEC-0125: they were voice-only): each project with its money, reason
and tasks, underway first; started, edited, budgeted, finished and deleted, and tasks added, ticked, reopened and taken
off, all as actions the voice tools agree with; and the glasses' Project Tasks panel."""

from __future__ import annotations

from datetime import date

import pytest

from core.actions import ActionCenter, ActionError
from core.project_manager import ProjectManager
from core.task_manager import TaskManager
from core.web_projects import projects_page
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.projects = ProjectManager(context, data_dir=tmp_path / "pj")
    context.tasks = TaskManager(context, data_dir=tmp_path / "pj")
    return context


def do(world, kind, **params):
    """Proposes and approves an action; returns (summary, result)."""
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal.summary, done.result


def test_a_project_with_its_budget_spending_and_tasks(world):
    from types import SimpleNamespace

    assert projects_page(SimpleNamespace(projects=None)) == {"available": False}
    do(world, "project.add", name="Chicken run", status="Complete")
    do(world, "project.add", name="Greenhouse", status="Active", due_date="2026-12-15")
    page = projects_page(world)
    assert [p["name"] for p in page["projects"]] == ["Greenhouse", "Chicken run"]  # underway first
    green = page["projects"][0]
    said, done = do(world, "project.budget", project_id=green["id"], budget="2500")
    assert said == "Set the Greenhouse budget to $2,500.00" and done == "Greenhouse's budget is $2,500.00."
    world.budget.add_expense(1840.0, "Supplies", "Hoops and poly", date.today().isoformat(), project_id=green["id"])
    do(world, "task.add", project_id=green["id"], title="Level the ground")
    said, _ = do(world, "task.add", project_id=green["id"], title="Frame the door", due_date="2026-11-14")
    assert said == "Add \"Frame the door\" to Greenhouse"
    green = projects_page(world)["projects"][0]
    assert (green["budget_text"], green["spent_text"], green["left_text"], green["percent"]) == \
        ("$2,500.00", "$1,840.00", "$660.00", 73.6)
    assert [t["title"] for t in green["tasks"]] == ["Frame the door", "Level the ground"]  # dated first
    first = green["tasks"][1]
    do(world, "task.done", task_id=first["id"])
    assert projects_page(world)["projects"][0]["tasks_done"] == 1
    do(world, "task.reopen", task_id=first["id"])
    with pytest.raises(ActionError, match="isn't done yet"):
        world.actions.propose(world, "task.reopen", {"task_id": first["id"]})
    do(world, "task.delete", task_id=first["id"])
    assert projects_page(world)["counts"] == {"underway": 1, "open_tasks": 1}
    do(world, "project.edit", project_id=green["id"], **{**green["values"], "status": "Complete"})
    assert projects_page(world)["projects"][0]["status"] == "Complete"
    with pytest.raises(ActionError, match="negative"):
        world.actions.propose(world, "project.budget", {"project_id": green["id"], "budget": "-5"})


def test_the_glasses_list_open_project_tasks_with_done(world):
    from datetime import timedelta

    from core.glasses import GLASSES_KINDS, _project_tasks

    assert _project_tasks(world, date.today())["empty"].startswith("No open tasks")
    do(world, "project.add", name="Greenhouse", status="Active")
    green = projects_page(world)["projects"][0]
    late = (date.today() - timedelta(days=2)).isoformat()
    do(world, "task.add", project_id=green["id"], title="Frame the door", due_date=late)
    do(world, "task.add", project_id=green["id"], title="Pull the poly")
    panel = _project_tasks(world, date.today())
    first = panel["lines"][0]
    assert (first["text"], first["tone"], first["action"]["kind"]) == ("Frame the door", "attention", "task.done")
    assert first["detail"].startswith("Greenhouse · by ") and "task.done" in GLASSES_KINDS
    assert [line["text"] for line in panel["lines"]] == ["Frame the door", "Pull the poly"]
