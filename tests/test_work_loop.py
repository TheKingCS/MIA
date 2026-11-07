"""The agent registry and the loop (DEC-0068/0069, core/work_agents.py and
core/work_loop.py): a task worked from claim to review through the lab,
resumed where it stopped, and only by a role whose tier allows it."""

import json
from types import SimpleNamespace

import pytest

from core import work_agents as agents
from core import work_loop as loop
from core import work_tasks as tasks_mod

REGISTRY = {
    "providers": {"claude-code": {"kind": "cli", "command": "claude", "can": ["write", "review"]},
                  "ollama": {"kind": "local", "can": ["review"]}},
    "roles": [{"role": "Software Engineer", "provider": "claude-code", "tier": "experiment"},
              {"role": "QA Engineer", "provider": "ollama", "tier": "review"}],
}


class FakeLab:
    """The lab's interface (core/dev_lab.py), without git or a real coder."""
    NOT_READY, READY = "not ready", "ready"

    def __init__(self, fail_check_once=False):
        """No proposals yet; it can fail one check (as if the computer slept)."""
        self.proposals, self.created, self.fail_check_once = {}, 0, fail_check_once

    def create(self, title, problem, evidence="", plan=""):
        """Makes a numbered proposal on its own branch."""
        self.created += 1
        pid = f"20261103-{self.created:06d}"
        self.proposals[pid] = SimpleNamespace(proposal_id=pid, branch=f"lab/{pid}", status="drafted", note="",
                                              coder_said="", tests={}, files=[])
        return self.proposals[pid]

    def write(self, pid, coder=None):
        """The coder's turn: written, changing core/x.py."""
        p = self.proposals[pid]
        p.status, p.coder_said, p.files = "written", "changed core/x.py", ["core/x.py"]
        return p

    def check(self, pid, suite=None):
        """The tests pass (after failing once when asked)."""
        if self.fail_check_once:
            self.fail_check_once = False
            raise RuntimeError("the computer went to sleep")
        p = self.proposals[pid]
        p.status, p.tests = self.READY, {"summary": "10 passed"}
        return p

    def get(self, pid):
        """A proposal by id."""
        return self.proposals[pid]


@pytest.fixture
def place(tmp_path):
    """A task, its activity log and the agent registry in a temporary folder."""
    folder, log = tmp_path / "tasks", tmp_path / "activity.jsonl"
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="A fix", files=["core/x.py"], body="Make x right."), folder)
    return folder, log, agents.parse(REGISTRY)


def test_a_task_goes_from_claim_to_review(place):
    folder, log, registry = place
    lab = FakeLab()
    assert loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log) == "review"
    task = tasks_mod.load(folder)["T-0001"]
    assert task.status == "review" and task.branch == "lab/20261103-000001"
    assert loop.done_steps("T-0001", log) == list(loop.STEPS)
    assert "Ready for review: lab 20261103-000001, 10 passed" in task.body


def test_an_interrupted_run_resumes_without_redoing_steps(place):
    folder, log, registry = place
    lab = FakeLab(fail_check_once=True)
    with pytest.raises(RuntimeError):
        loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log)
    assert loop.done_steps("T-0001", log) == ["claim", "lab", "write"]
    loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log)
    assert lab.created == 1 and tasks_mod.load(folder)["T-0001"].status == "review"


def test_a_reviewer_cant_write_and_nobody_is_given_approve(place):
    folder, log, registry = place
    with pytest.raises(agents.AgentError, match="review: it can't write"):
        loop.run("T-0001", "QA Engineer", registry, lab=FakeLab(), folder=folder, log=log)
    with pytest.raises(agents.AgentError, match="Zac"):
        registry.may("Software Engineer", "approve")
    with pytest.raises(agents.AgentError):
        agents.parse({**REGISTRY, "roles": [{"role": "Boss", "provider": "ollama", "tier": "approve"}]})


def test_a_stopped_check_says_why_on_the_task(place):
    folder, log, registry = place
    lab = FakeLab()
    lab.check = lambda pid, suite=None: SimpleNamespace(status="not ready", note="New failures: tests/test_x.py",
                                                         tests={})
    with pytest.raises(loop.LoopError, match="New failures"):
        loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log)
    assert "Stopped at check: New failures" in tasks_mod.load(folder)["T-0001"].body


def test_the_repos_registry_reads_and_grants_no_approval():
    registry = agents.load()
    assert "Software Engineer" in registry.roles and registry.providers["claude-code"].kind == "cli"
    assert all(r.tier in agents.TIERS for r in registry.roles.values())
    assert json.loads(agents.REGISTRY.read_text(encoding="utf-8"))["roles"]
