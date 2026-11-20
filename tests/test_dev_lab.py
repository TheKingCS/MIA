"""MIA's development lab (DEC-0058, core/dev_lab.py): a proposal is written
in an isolated worktree, checked against rules the lab can't touch and
against the suite at the start, and reaches the running copy only on
approval, reverting itself if it breaks something there. A coder's steps
are kept as its method trace: tools and targets only. A change to code needs a
test that fails before it and passes after (DEC-0224), and its merge names it."""

import subprocess
from pathlib import Path

import pytest

import core.dev_lab as lab


def git(cwd, *args):
    """Runs git in a folder as a test identity."""
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=str(cwd), check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A small git repository standing in for MIA, with the lab pointed at it."""
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


def proven(cwd: Path) -> dict:
    """A stand-in suite where the start fails the test the change fixes and the lab passes it (DEC-0224)."""
    failed = ["tests/test_thing.py::value"] if cwd.name.startswith("_base-") else []
    return {"summary": f"{len(failed)} failed, 10 passed in 1.0s", "failed": failed, "finished": True}


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
    lab.check(p.proposal_id, suite=proven)
    runs = iter([[], ["tests/test_c.py::only_here"]])  # fine before the merge, broken after
    p = lab.approve(p.proposal_id, suite=lambda cwd: {"summary": "", "failed": next(runs), "finished": True})
    assert p.status == lab.REVERTED and (repo / "core" / "thing.py").read_text() == "VALUE = 1\n"
    log = subprocess.run(["git", "log", "--format=%s"], cwd=str(repo), capture_output=True, text=True).stdout
    assert log.startswith("Revert") and "From the lab: Looks fine" in log  # history keeps both


def test_nothing_written_and_rejecting(repo):
    p = lab.create("Nothing", "x")
    assert lab.write(p.proposal_id, coder=lambda t, cwd, py: "I looked.").status == lab.NOT_READY
    p = lab.reject(p.proposal_id, "not needed")
    assert p.status == lab.REJECTED and not lab.folder(p).exists()


def test_the_rules():
    """Protected paths are caught, a suite's result is read from its output, and only new failures count."""
    assert lab.touches_protected(["core/thing.py", "core/dev_lab.py", "deploy/x.sh", "docs/DECISIONS.md"]) == \
        ["core/dev_lab.py", "deploy/x.sh", "docs/DECISIONS.md"]
    out = "FAILED tests/test_a.py::one - assert 1\nFAILED tests/test_b.py::two\n== 2 failed, 9 passed in 3.1s =="
    assert lab.suite_result(out) == {"summary": "2 failed, 9 passed in 3.1s", "failed":
                                     ["tests/test_a.py::one", "tests/test_b.py::two"], "finished": True}
    assert lab.new_failures({"failed": ["a", "b"]}, {"failed": ["a"]}) == ["b"]
    assert not lab.suite_result("Traceback...")["finished"]


def test_a_failure_already_in_the_running_copy_doesnt_revert(repo):
    """Work in progress here the lab never saw: failing before and after the merge isn't the merge's doing."""
    p = lab.create("Fine", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 5\n"))
    lab.check(p.proposal_id, suite=proven)
    already = ["tests/test_plaid.py::work_in_progress"]
    p = lab.approve(p.proposal_id, suite=lambda cwd: {"summary": "", "failed": list(already), "finished": True})
    assert p.status == lab.MERGED and (repo / "core" / "thing.py").read_text() == "VALUE = 5\n"


def test_a_reverted_proposal_can_be_retried_on_the_running_copy(repo):
    p = lab.create("Try again", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 6\n"))
    lab.check(p.proposal_id, suite=proven)
    runs = iter([[], ["tests/test_c.py::flaky_here"]])
    assert lab.approve(p.proposal_id, suite=lambda cwd: {"summary": "", "failed": next(runs), "finished": True}).status == lab.REVERTED
    p = lab.retry(p.proposal_id)
    assert p.status == lab.WRITTEN and "-again-" in p.branch
    p = lab.check(p.proposal_id, suite=proven)
    assert p.status == lab.READY and p.files == ["core/thing.py"]
    p = lab.approve(p.proposal_id, suite=lambda cwd: {"summary": "", "failed": [], "finished": True})
    assert p.status == lab.MERGED and (repo / "core" / "thing.py").read_text() == "VALUE = 6\n"




def test_a_second_try_goes_on_top_of_the_first(repo):
    p = lab.create("Make VALUE 2", "VALUE should be 2", "Night School", "change core/thing.py")
    p = lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 3\n"))
    seen = []

    def again(task, cwd, python):
        seen.append(task)
        (Path(cwd) / "core" / "thing.py").write_text("VALUE = 2\n")
        return "Fixed it."

    p = lab.write(p.proposal_id, coder=again, again="It didn't pass its test yet: expected 2. Fix it.")
    assert p.status == lab.WRITTEN and "expected 2" in seen[0] and p.coder_said.endswith("Second try: Fixed it.")
    assert (lab.folder(p) / "core" / "thing.py").read_text() == "VALUE = 2\n"
    p = lab.write(p.proposal_id, coder=lambda t, cwd, py: "I looked again.", again="Still failing.")
    assert p.status == lab.WRITTEN  # a second try that changed nothing leaves the first standing
    with pytest.raises(ValueError):
        lab.write(p.proposal_id, coder=lambda t, cwd, py: "")  # without `again`, a written one isn't rewritten


def test_a_suite_run_that_crashed_is_run_once_more():
    runs = iter([lab.suite_result("Fatal Python error: Aborted"), lab.suite_result("1 failed, 9 passed in 3.1s")])
    got = lab.run_suite(Path("."), once=lambda cwd: next(runs))
    assert got["finished"] and got["summary"] == "1 failed, 9 passed in 3.1s (run twice: the first didn't finish)"
    both_bad = lab.run_suite(Path("."), once=lambda cwd: lab.suite_result("Fatal Python error: Aborted"))
    assert not both_bad["finished"]  # twice: it stands as not finished
    ok = lab.run_suite(Path("."), once=lambda cwd: lab.suite_result("9 passed in 3.1s"))
    assert ok["summary"] == "9 passed in 3.1s"


def test_a_coders_stream_becomes_steps_with_tools_and_targets_only():
    """Each tool the coder used and on what (a lab path made relative, a command's first words), never the content
    it wrote; what it said at the end; lines that aren't JSON are skipped."""
    import json

    cwd = Path("C:/lab/20261108-abc")
    stream = "\n".join([
        "not json",
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Looking."},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "C:\\lab\\20261108-abc\\core\\thing.py"}},
            {"type": "tool_use", "name": "Grep", "input": {"pattern": "VALUE", "path": "core"}}]}}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "C:/lab/20261108-abc/core/thing.py",
                                                          "old_string": "SECRET OLD", "new_string": "SECRET NEW"}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "python -m pytest -q tests/test_thing.py -x --tb=short"}}]}}),
        json.dumps({"type": "result", "result": "Changed VALUE to 2."})])
    said, steps = lab.trace_steps(stream, cwd)
    assert said == "Changed VALUE to 2."
    assert steps == [{"tool": "Read", "target": "core/thing.py"}, {"tool": "Grep", "target": "core"},
                     {"tool": "Edit", "target": "core/thing.py"},
                     {"tool": "Bash", "target": "python -m pytest -q tests/test_thing.py -x"}]
    assert "SECRET" not in json.dumps(steps)


def test_a_coders_steps_are_kept_beside_its_proposal_and_summed_up(repo):
    """A coder that says its steps has them kept per attempt; the summary says a repeated step once with a count; a
    plain-string coder keeps no trace."""
    p = lab.create("Make VALUE 2", "VALUE should be 2", "", "change core/thing.py")

    def coder(task, cwd, python):
        """Writes the change and says what it did, step by step."""
        (Path(cwd) / "core" / "thing.py").write_text("VALUE = 2\n")
        return lab.CoderSaid("Done.", [{"tool": "Read", "target": "core/thing.py"},
                                       {"tool": "Read", "target": "core/thing.py"},
                                       {"tool": "Edit", "target": "core/thing.py"}])

    p = lab.write(p.proposal_id, coder=coder)
    assert p.coder_said == "Done." and [a["attempt"] for a in lab.trace(p.proposal_id)] == ["first"]
    assert (repo / "data" / "lab" / "traces" / f"{p.proposal_id}.json").exists()
    assert lab.trace_summary(p.proposal_id) == (f"The coder's steps (lab {p.proposal_id}, first try): "
                                                "Read core/thing.py x2; Edit core/thing.py")
    q = lab.create("Another", "x", "", "y")
    lab.write(q.proposal_id, coder=lambda t, cwd, py: "I looked.")
    assert lab.trace(q.proposal_id) == [] and lab.trace_summary(q.proposal_id) == ""
    assert lab.trace("../../etc") == []


def test_a_code_change_with_no_test_showing_the_problem_isnt_ready(repo):
    """DEC-0224: nothing fails at the start and passes after, so the change shows nothing and stays out."""
    p = lab.create("Tidy", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "core" / "thing.py").write_text("VALUE = 7\n"))
    p = lab.check(p.proposal_id, suite=suite({"*": []}))
    assert p.status == lab.NOT_READY and "DEC-0224" in p.note and p.tests["shown_by"] == []


def test_a_change_to_docs_alone_needs_no_proving_test(repo):
    """Only a change to code needs the proof; notes and data don't."""
    p = lab.create("A note", "x")
    lab.write(p.proposal_id, coder=lambda t, cwd, py: (Path(cwd) / "NOTES.md").write_text("a note\n"))
    assert lab.check(p.proposal_id, suite=suite({"*": []})).status == lab.READY


def test_the_changes_own_test_failing_on_the_starting_code_is_its_proof(repo):
    """A new test file is run against the start with the lab's tests laid over it; failing there and passing in the
    lab makes it the proof, and the merge's message names it."""
    def coder(task, cwd, python):
        """Fixes VALUE and adds the test that shows it."""
        (Path(cwd) / "core" / "thing.py").write_text("VALUE = 2\n")
        (Path(cwd) / "tests").mkdir(exist_ok=True)
        (Path(cwd) / "tests" / "test_thing.py").write_text("def test_value():\n    assert True\n")
        return "Fixed VALUE, with its test."

    p = lab.create("Make VALUE 2", "x")
    lab.write(p.proposal_id, coder=coder)
    seen = []

    def proof(cwd, files):
        """Records where and what was run, and fails the new test there."""
        seen.append((cwd.name, files, (cwd / "tests" / "test_thing.py").exists(),
                     (cwd / "core" / "thing.py").read_text()))
        return {"summary": "1 failed", "failed": ["tests/test_thing.py::test_value"], "finished": True}

    p = lab.check(p.proposal_id, suite=suite({"*": []}), proof=proof)
    assert len(seen) == 1 and seen[0][0].startswith(f"_proof-{p.proposal_id}-")
    assert seen[0][1:] == (["tests/test_thing.py"], True, "VALUE = 1\n")  # the old code, new test
    assert not list((repo.parent / "MIA-lab").glob("_proof-*"))  # put away afterwards
    assert p.status == lab.READY and p.tests["shown_by"] == ["tests/test_thing.py::test_value"]
    assert "Shown by: tests/test_thing.py::test_value" in lab.describe(p)
    p = lab.approve(p.proposal_id, suite=lambda cwd: {"summary": "", "failed": [], "finished": True})
    body = subprocess.run(["git", "log", "-1", "--format=%B", p.merged_as], cwd=str(repo), capture_output=True,
                          text=True).stdout
    assert p.status == lab.MERGED and "Shown by: tests/test_thing.py::test_value" in body


def test_the_merge_message_names_what_shows_it_helped():
    """Pure logic: the title and id, then up to ten proving tests."""
    p = lab.Proposal("p1", "Fix it", "x", tests={"shown_by": [f"tests/t.py::{i}" for i in range(12)]})
    message = lab.merge_message(p)
    assert message.startswith("From the lab: Fix it (p1)\n\nShown by: tests/t.py::0") and message.endswith("and more")
    assert lab.merge_message(lab.Proposal("p2", "Docs", "x")) == "From the lab: Docs (p2)"
    assert lab.needs_proof(["core/a.py"]) and not lab.needs_proof(["tests/test_a.py", "docs/A.md"])
