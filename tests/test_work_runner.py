"""Missions and the runner (DEC-0076, DEC-0079; core/work_runner.py): the
council works a mission by itself, within its scope and budget, handing work
to whoever has time, and never approving anything."""

from types import SimpleNamespace

import pytest

from core import work_activity as activity
from core import work_agents as agents
from core import work_runner as runner
from core import work_tasks as tasks_mod

REGISTRY = {
    "providers": {"claude-code": {"kind": "cli", "command": "python", "can": ["write", "review"]},
                  "codex": {"kind": "cli", "command": "python", "can": ["write", "review"]},
                  "ollama-coder": {"kind": "cli", "command": "python", "can": ["review"]}},
    "roles": [{"role": "Software Engineer", "provider": "claude-code", "tier": "experiment",
               "providers": ["claude-code", "codex"]},
              {"role": "QA Engineer", "provider": "ollama-coder", "tier": "review"},
              {"role": "Security Auditor", "provider": "codex", "tier": "review"}],
}


@pytest.fixture
def place(tmp_path):
    """An active mission with two tasks, in temporary folders."""
    folders = SimpleNamespace(missions=tmp_path / "missions", tasks=tmp_path / "tasks", log=tmp_path / "activity.jsonl",
                              stop=tmp_path / "STOP")
    m = runner.new("Make the OCR tests pass everywhere", ["tests/", "core/ocr.py"], tasks=2, folder=folders.missions,
                   log=folders.log)
    runner.set_status(m.id, "active", "zac", folder=folders.missions, log=folders.log)
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="Fix OCR", files=["core/ocr.py"], source=m.id,
                                  role="Software Engineer"), folders.tasks)
    tasks_mod.save(tasks_mod.Task(id="T-0002", title="Out of scope", files=["core/budget_manager.py"], source=m.id),
                   folders.tasks)
    folders.mission = m.id
    return folders


class FakeLoop:
    """A stand-in work loop: records which provider ran each task and marks it for review, or fails as told."""
    def __init__(self, place, fail_with=""):
        """Where it works, how it fails, and nothing run yet."""
        self.place, self.fail_with, self.ran = place, fail_with, []

    def run(self, task_id, role_name, registry, lab=None, folder=None, log=None):
        """Records the run and puts the task in review on a lab branch, or raises."""
        provider = registry.roles[role_name].provider
        self.ran.append((task_id, provider))
        if self.fail_with:
            raise RuntimeError(self.fail_with)
        tasks = tasks_mod.load(folder)
        tasks[task_id].status, tasks[task_id].branch = "review", "lab/p1"
        tasks_mod.save(tasks[task_id], folder)
        activity.record(f"{role_name} ({provider})", "loop", task_id, "write: done", log)
        return "review"


def step(place, registry, **kw):
    """One runner step on the mission with everything outside held still (the lab, provider state, learning, shadow review)."""
    kw.setdefault("lab", SimpleNamespace(get=lambda pid: SimpleNamespace(files=["core/ocr.py"])))
    kw.setdefault("state", lambda provider: {"state": "ready"})
    kw.setdefault("learn", lambda task_id: [])
    kw.setdefault("shadow", lambda task_id: {"outcome": "pass"})
    return runner.step(place.mission, registry, folder=place.missions, tasks_dir=place.tasks, log=place.log,
                       stop_file=place.stop, **kw)


def test_only_zac_starts_a_mission_and_only_at_the_keyboard(tmp_path):
    m = runner.new("x", ["docs/"], folder=tmp_path, log=tmp_path / "a.jsonl")
    with pytest.raises(ValueError, match="Only Zac"):
        runner.set_status(m.id, "active", "claude", folder=tmp_path, log=tmp_path / "a.jsonl")
    with pytest.raises(ValueError, match="at the keyboard"):
        runner.set_status(m.id, "active", "zac", folder=tmp_path, log=tmp_path / "a.jsonl", confirm=lambda q: "yes")
    assert runner.set_status(m.id, "active", "zac", folder=tmp_path, log=tmp_path / "a.jsonl",
                             confirm=lambda q: m.id).status == "active"
    with pytest.raises(ValueError, match="needs a goal and a scope"):
        runner.new("x", [], folder=tmp_path)


def test_it_writes_in_scope_then_gets_reviews_from_who_has_time(place):
    registry = agents.parse(REGISTRY)
    loop = FakeLoop(place)
    reviewed = []
    review = lambda task_id, role: reviewed.append((task_id, role)) or "approve"  # noqa: E731
    said = step(place, registry, loop=loop, review=review)
    assert said == "wrote T-0001: now review" and loop.ran == [("T-0001", "claude-code")]
    assert "T-0002" not in [t for t, _ in loop.ran]  # outside the scope: never picked
    said = step(place, registry, loop=loop, review=review)
    assert said.startswith("review T-0001 by ollama-coder")
    activity.record("QA Engineer (ollama-coder)", "review", "T-0001", "approve: fine", place.log)
    said = step(place, registry, loop=loop, review=review)
    assert said.startswith("review T-0001 by codex")  # a second provider, not the author's
    assert [r for _, r in reviewed] == ["QA Engineer", "Security Auditor"]


def test_a_resting_writer_hands_the_work_to_the_next(place):
    registry = agents.parse(REGISTRY)
    loop = FakeLoop(place)
    said = step(place, registry, loop=loop, state=lambda p: {"state": "cooling" if p == "claude-code" else "ready"})
    assert loop.ran == [("T-0001", "codex")]
    history = [e["detail"] for e in activity.events(place.log) if e.get("who") == "runner"]
    assert any("on codex (the first choice is resting)" in d for d in history)
    assert said == "wrote T-0001: now review"


def test_with_every_writer_resting_it_does_the_local_work(place):
    registry = agents.parse(REGISTRY)
    tasks_mod.save(tasks_mod.Task(id="T-0009", title="Earlier", status="done"), place.tasks)
    learned = []
    said = step(place, registry, loop=FakeLoop(place), state=lambda p: {"state": "cooling"},
                learn=lambda task_id: learned.append(task_id) or [{"id": "K-1"}])
    assert said == "learned from T-0009: 1 entry" and learned == ["T-0009"]
    said = step(place, registry, loop=FakeLoop(place), state=lambda p: {"state": "cooling"},
                learn=lambda task_id: learned.append(task_id) or [])
    assert said.startswith("idle") and learned == ["T-0009"]  # tried once, not again every step


def test_a_change_outside_the_scope_is_stopped_before_any_review(place):
    registry = agents.parse(REGISTRY)
    said = step(place, registry, loop=FakeLoop(place), lab=SimpleNamespace(get=lambda pid: SimpleNamespace(
        files=["core/ocr.py", "core/actions.py"])))
    assert said == "blocked T-0001: outside the scope (core/actions.py)"
    assert tasks_mod.load(place.tasks)["T-0001"].status == "blocked"


def test_it_stops_for_the_stop_file_the_budget_and_zacs_queue(place):
    registry = agents.parse(REGISTRY)
    place.stop.write_text("")
    assert step(place, registry, loop=FakeLoop(place)) == "stop: work/STOP is there"
    place.stop.unlink()
    for n in range(2):  # the mission's two tasks are written
        activity.record("runner", "runner", f"T-01{n}", f"{place.mission} write T-01{n} as x on y", place.log)
    assert step(place, registry, loop=FakeLoop(place)) == "stop: its 2 tasks are written"
    assert runner.missions(place.missions)[place.mission].status == "paused"


def test_a_usage_limit_mid_write_is_a_rest_not_a_failure(place, monkeypatch):
    from core import dev_usage
    from core.dev_store import DevStore

    store = DevStore(place.missions.parent / "usage")
    registry = agents.parse(REGISTRY)
    said = step(place, registry, loop=FakeLoop(place, fail_with="5-hour limit reached, resets in 2 hours"), usage=store)
    assert "hit its usage limit; handing it on" in said
    assert dev_usage.state("claude-code", store)["state"] == "cooling"


def test_scope():
    """Files a mission didn't name are out of its scope."""
    assert runner.in_scope(["tests/test_ocr.py", "core/ocr.py", "core/ocr_extra.py"], ["tests/", "core/ocr.py"]) == \
        ["core/ocr_extra.py"]


def test_with_nothing_to_write_mia_practises_on_what_the_council_wrote(place):
    registry = agents.parse(REGISTRY)
    activity.record("Software Engineer (claude-code)", "loop", "T-0001", "write: done", place.log)
    tasks = tasks_mod.load(place.tasks)
    tasks["T-0001"].status = "review"
    tasks_mod.save(tasks["T-0001"], place.tasks)
    tried = []

    def shadow(task_id):
        tried.append(task_id)
        activity.record("MIA (ollama-coder)", "shadow", task_id, "fail: changed nothing", place.log)
        return {"outcome": "fail"}
    resting = lambda p: {"state": "cooling"}  # noqa: E731  nothing can review or write
    assert step(place, registry, loop=FakeLoop(place), state=resting, shadow=shadow) == "MIA's attempt at T-0001: fail"
    assert step(place, registry, loop=FakeLoop(place), state=resting, shadow=shadow).startswith("idle")
    assert tried == ["T-0001"]  # once per task
