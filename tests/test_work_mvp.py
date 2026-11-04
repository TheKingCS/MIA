"""The MIA-DII MVP, end to end (DEC-0070; the acceptance list in
docs/DEV_ECOSYSTEM_AUDIT.md section 11 and the spec's section 9): one task
from creation to Zac's approval, through the real task records, activity
log, agent registry, loop, review and dashboard, with a stand-in lab so no
git or real coder is needed."""

from datetime import date

import pytest

from core import work_activity as activity
from core import work_agents as agents
from core import work_dashboard as dash
from core import work_loop as loop
from core import work_review as review
from core import work_tasks as tasks_mod
from tests.test_work_loop import REGISTRY, FakeLab

SECRET = "sk-planted-fake-secret-0000"


@pytest.fixture
def team(tmp_path):
    folder, log = tmp_path / "tasks", tmp_path / "activity.jsonl"
    lab = FakeLab()
    lab.MERGED = "merged"
    seen_prompts = []

    def merge(pid, suite=None):
        p = lab.proposals[pid]
        p.status, p.merged_as, p.note = "merged", "f00dfeed00", "In."
        return p

    lab.approve = merge
    return folder, log, lab, agents.parse(REGISTRY), seen_prompts


def test_one_task_from_creation_to_approval(team):
    folder, log, lab, registry, prompts = team
    tasks = tasks_mod.load(folder)
    base = tasks_mod.new(tasks, "Groundwork", date(2026, 11, 3), owner="claude")
    tasks[base.id] = base
    tasks_mod.save(base, folder)
    fix = tasks_mod.new(tasks, "The fix", date(2026, 11, 3), depends=[base.id], files=["core/x.py"],
                        body="Make x right.")
    tasks_mod.save(fix, folder)

    # Persistent tasks, with dependencies: not ready until the groundwork is done.
    with pytest.raises(loop.tasks_mod.TaskError, match="waiting on"):
        loop.run(fix.id, "Software Engineer", registry, lab=lab, folder=folder, log=log)
    tasks = tasks_mod.load(folder)
    tasks_mod.finish(tasks, base.id, "claude", "tests: 3 passed; commit abc")
    tasks_mod.save(tasks[base.id], folder)

    # Assigned to a role on a provider; worked through the lab to review; its branch recorded.
    assert loop.run(fix.id, "Software Engineer", registry, lab=lab, folder=folder, log=log) == "review"
    assert tasks_mod.load(folder)[fix.id].branch.startswith("lab/")

    # Independent review by another role and provider, which sees the change, not secrets.
    said = review.review(fix.id, "QA Engineer", registry, folder=folder, log=log,
                         diff=lambda pid: "+ x fixed",
                         ask=lambda provider, prompt: prompts.append(prompt) or "VERDICT: approve")
    assert said == "approve" and SECRET not in prompts[0]

    # Human-controlled approval: refused headless, granted to a person typing the id.
    with pytest.raises(review.ReviewError):
        review.approve(fix.id, confirm=lambda q: (_ for _ in ()).throw(EOFError()), lab=lab, folder=folder, log=log,
                       registry=registry)
    review.approve(fix.id, confirm=lambda q: fix.id, lab=lab, folder=folder, log=log, registry=registry)

    # Completion evidence, and a searchable history of every handoff.
    done = tasks_mod.load(folder)[fix.id]
    assert done.status == "done" and "merged as f00dfeed00" in done.body
    actions = [(e["action"], e["who"]) for e in activity.search(task_id=fix.id, path=log)]
    assert ("review", "QA Engineer (ollama)") in actions and ("approve", "zac") in actions
    assert any(a == "loop" for a, _ in actions)

    # One dashboard over it all.
    page = dash.page(None, "fixed", tasks_dir=folder, log=log)
    assert page["summary"]["done"] == 2 and page["queue"] == []
    assert SECRET not in str(page) and SECRET not in log.read_text(encoding="utf-8")


def test_an_interrupted_task_is_recovered(team):
    folder, log, _, registry, _ = team
    lab = FakeLab(fail_check_once=True)
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="Fix", files=["core/x.py"], body="x"), folder)
    with pytest.raises(RuntimeError):
        loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log)
    assert activity.last_step("T-0001", log)["detail"].startswith("write")
    assert loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log) == "review"
    assert lab.created == 1


def test_overlapping_work_waits(team):
    folder, log, lab, registry, _ = team
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="One", files=["core/x.py"], body="x"), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0002", title="Two", files=["core/x.py"], body="x"), folder)
    loop.run("T-0001", "Software Engineer", registry, lab=lab, folder=folder, log=log)
    tasks = tasks_mod.load(folder)
    tasks["T-0001"].status = "claimed"  # still being worked
    tasks_mod.save(tasks["T-0001"], folder)
    with pytest.raises(tasks_mod.TaskError, match="T-0001"):
        loop.run("T-0002", "Software Engineer", registry, lab=lab, folder=folder, log=log)


def test_the_lab_keeps_secrets_and_its_own_rules_out_of_reach():
    from core.dev_lab import PROTECTED

    for path in ("config/", "data/", "core/dev_lab.py", "core/actions.py", "core/safety_floor.py"):
        assert path in PROTECTED
