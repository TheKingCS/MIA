"""MIA's development lab (DEC-0058, core/dev_lab.py): a proposal is written
in an isolated worktree, checked against rules the lab can't touch and
against the suite at the start, and reaches the running copy only on
approval, reverting itself if it breaks something there."""

import subprocess
from pathlib import Path

import pytest

import core.dev_lab as lab


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=str(cwd), check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "MIA"
    root.mkdir()
    git(root, "init", "-q", "-b", "master")
    (root / "core").mkdir()
    (root / "core" / "thing.py").write_text("VALUE = 1\n")
    (root / "core" / "actions.py").write_text("# approvals\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    monkeypatch.setattr(lab, "ROOT", root)
    monkeypatch.setattr(lab, "LAB_ROOT", tmp_path / "MIA-lab")
    monkeypatch.setattr(lab, "_STORE", root / "data" / "lab" / "proposals.json")
    return root


def suite(failed_in: dict):
    """A stand-in suite: which tests fail, by folder name."""
    def run(cwd: Path):
        failed = failed_in.get(cwd.name, failed_in.get("*", []))
        return {"summary": f"{len(failed)} failed, 10 passed in 1.0s", "failed": failed, "finished": True}
    return run


def test_the_whole_way_in(repo):
    p = lab.create("Make VALUE 2", "VALUE should be 2", "the Fix-It Log", "change core/thing.py")
    where = lab.folder(p)
    assert where.exists() and where.parent.name == "MIA-lab" and not (where / "data").exists()  # no real data there

    def coder(task, cwd, python):
        assert "Never change any of these" in task and "core/actions.py" in task
        (Path(cwd) / "core" / "thing.py").write_text("VALUE = 2\n")
        return "Changed VALUE to 2."

    p = lab.write(p.proposal_id, coder=coder)
    assert p.status == lab.WRITTEN and p.coder_said == "Changed VALUE to 2."
    assert (repo / "core" / "thing.py").read_text() == "VALUE = 1\n"  # the running copy is untouched
    p = lab.check(p.proposal_id, suite=suite({"*": ["tests/test_a.py::old"], p.proposal_id: []}))
    assert p.status == lab.READY and p.files == ["core/thing.py"] and p.tests["fixed"] == ["tests/test_a.py::old"]
    p = lab.approve(p.proposal_id, suite=suite({"*": []}))
    assert p.status == lab.MERGED and (repo / "core" / "thing.py").read_text() == "VALUE = 2\n"


def test_the_lab_never_changes_its_safeguards(repo):
    p = lab.create("Loosen approvals", "approvals are slow")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "actions.py").write_text("# gone\n"))
    p = lab.check(p.proposal_id, suite=suite({"*": []}))
    assert p.status == lab.NOT_READY and p.refused == ["core/actions.py"]
    with pytest.raises(ValueError):
        lab.approve(p.proposal_id)


def test_a_new_failure_isnt_ready(repo):
    p = lab.create("Break it", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 3\n"))
    p = lab.check(p.proposal_id, suite=suite({p.proposal_id: ["tests/test_b.py::new"], "*": []}))
    assert p.status == lab.NOT_READY and p.tests["new_failures"] == ["tests/test_b.py::new"]


def test_breaking_the_running_copy_reverts_itself(repo):
    p = lab.create("Looks fine", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 4\n"))
    lab.check(p.proposal_id, suite=suite({"*": []}))
    p = lab.approve(p.proposal_id, suite=suite({"MIA": ["tests/test_c.py::only_here"]}))
    assert p.status == lab.REVERTED and (repo / "core" / "thing.py").read_text() == "VALUE = 1\n"
    log = subprocess.run(["git", "log", "--format=%s"], cwd=str(repo), capture_output=True, text=True).stdout
    assert log.startswith("Revert") and "From the lab: Looks fine" in log  # history keeps both


def test_nothing_written_and_rejecting(repo):
    p = lab.create("Nothing", "x")
    assert lab.write(p.proposal_id, coder=lambda t, cwd, py: "I looked.").status == lab.NOT_READY
    p = lab.reject(p.proposal_id, "not needed")
    assert p.status == lab.REJECTED and not lab.folder(p).exists()


def test_the_rules():
    assert lab.touches_protected(["core/thing.py", "core/dev_lab.py", "deploy/x.sh", "docs/DECISIONS.md"]) == \
        ["core/dev_lab.py", "deploy/x.sh", "docs/DECISIONS.md"]
    out = "FAILED tests/test_a.py::one - assert 1\nFAILED tests/test_b.py::two\n== 2 failed, 9 passed in 3.1s =="
    assert lab.suite_result(out) == {"summary": "2 failed, 9 passed in 3.1s", "failed":
                                     ["tests/test_a.py::one", "tests/test_b.py::two"], "finished": True}
    assert lab.new_failures({"failed": ["a", "b"]}, {"failed": ["a"]}) == ["b"]
    assert not lab.suite_result("Traceback...")["finished"]
