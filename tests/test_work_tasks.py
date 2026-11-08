"""Development tasks as records (DEC-0068, core/work_tasks.py): files that
round-trip, ready only after their dependencies, claims that can't overlap,
and done only with evidence."""

from datetime import date

import pytest

from core import work_tasks as w

DAY = date(2026, 11, 3)


def _tasks():
    """Two tasks, the second depending on the first."""
    a = w.Task(id="T-0001", title="Build the map", files=["core/links.py"], body="What it is.")
    b = w.Task(id="T-0002", title="Use the map", depends=["T-0001"], files=["core/capabilities.py"])
    return {a.id: a, b.id: b}


def test_a_task_file_round_trips():
    task = w.Task(id="T-0007", title="A thing", owner="claude", depends=["T-0001", "T-0002"],
                  files=["core/*.py"], decisions=["DEC-0068"], body="Notes here.")
    again = w.parse(task.to_text())
    assert again == task


def test_a_bad_file_is_refused():
    with pytest.raises(w.TaskError):
        w.parse("no header")
    with pytest.raises(w.TaskError):
        w.parse("---\nid: T-0001\ntitle: x\nstatus: maybe\n---\n")
    with pytest.raises(w.TaskError):
        w.parse("---\nid: T-0001\ntitle: x\nsecret: y\n---\n")


def test_ready_waits_for_dependencies():
    tasks = _tasks()
    assert w.ready(tasks["T-0001"], tasks) and not w.ready(tasks["T-0002"], tasks)
    with pytest.raises(w.TaskError, match="waiting on T-0001"):
        w.claim(tasks, "T-0002", "claude")
    w.claim(tasks, "T-0001", "claude")
    w.finish(tasks, "T-0001", "claude", "tests: 10 passed; commit abc", DAY)
    assert w.ready(tasks["T-0002"], tasks)


def test_two_claims_on_the_same_files_cant_run_at_once():
    tasks = _tasks()
    tasks["T-0003"] = w.Task(id="T-0003", title="Also links", files=["core/link*.py"])
    w.claim(tasks, "T-0001", "claude")
    with pytest.raises(w.TaskError, match="T-0001"):
        w.claim(tasks, "T-0003", "chatgpt")
    assert w.claim(tasks, "T-0003", "chatgpt", files=["web/dev.html"]).status == "claimed"


def test_done_needs_evidence():
    """A task is finished only with evidence, which goes in its body."""
    tasks = _tasks()
    with pytest.raises(w.TaskError, match="evidence"):
        w.finish(tasks, "T-0001", "claude", "  ")
    task = w.finish(tasks, "T-0001", "claude", "tests: 10 passed", DAY)
    assert task.status == "done" and "Evidence: tests: 10 passed" in task.body


def test_moving_needs_a_reason():
    tasks = _tasks()
    with pytest.raises(w.TaskError, match="why"):
        w.move(tasks, "T-0001", "blocked", "claude", "")
    assert w.move(tasks, "T-0001", "blocked", "claude", "needs a login", DAY).status == "blocked"


def test_new_ids_count_up_and_dependencies_must_exist():
    tasks = _tasks()
    assert w.new(tasks, "Next", DAY).id == "T-0003"
    with pytest.raises(w.TaskError):
        w.new(tasks, "Next", DAY, depends=["T-0999"])


def test_saving_and_loading(tmp_path):
    """Tasks saved to a folder load back with their dependencies."""
    tasks = _tasks()
    for task in tasks.values():
        w.save(task, tmp_path, DAY)
    again = w.load(tmp_path)
    assert set(again) == {"T-0001", "T-0002"} and again["T-0002"].depends == ["T-0001"]


def test_the_repos_own_tasks_all_read():
    tasks = w.load()
    for task in tasks.values():
        assert all(d in tasks for d in task.depends), task.id
