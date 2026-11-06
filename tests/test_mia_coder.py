"""MIA's own coder and her shadow attempts (DEC-0074, core/mia_coder.py): no
tools, only the files the task lists, never a protected one, graded by the
lab's own check, never merged."""

import json
from pathlib import Path

import pytest

import core.dev_lab as lab
from core import mia_coder, work_activity, work_tasks
from tests.test_dev_lab import repo, suite  # noqa: F401  (the fixture)


def reply(edits, said="Fixed it."):
    """edits: path -> (find, replace)."""
    return lambda prompt, schema: json.dumps({"edits": [{"path": p, "find": f, "replace": r} for p, (f, r) in edits.items()],
                                              "said": said})


def test_she_changes_only_the_listed_files(repo):
    p = lab.create("Make VALUE 2", "VALUE should be 2", plan="Files: core/thing.py")
    seen = {}

    def model(prompt, schema):
        seen["prompt"] = prompt
        return reply({"core/thing.py": ("VALUE = 1", "VALUE = 2"), "core/actions.py": ("# approvals", "# gone"),
                      "../evil.py": ("", "x")})(prompt, schema)
    p = lab.write(p.proposal_id, coder=mia_coder.coder(model))
    assert "=== core/thing.py\nVALUE = 1" in seen["prompt"] and "core/actions.py" not in seen["prompt"].split("===")[-1]
    where = lab.folder(p)
    assert (where / "core" / "thing.py").read_text() == "VALUE = 2\n"
    assert (where / "core" / "actions.py").read_text() == "# approvals\n"  # protected: never written
    assert not (where.parent / "evil.py").exists()
    assert p.status == lab.WRITTEN and "changed core/thing.py" in p.coder_said


def test_a_task_naming_only_protected_files_is_refused(repo):
    with pytest.raises(mia_coder.CoderError, match="no file MIA may change"):
        mia_coder.coder(reply({}))("Plan: Files: core/actions.py", repo, "python")


def test_a_shadow_attempt_is_graded_recorded_and_never_merged(repo, tmp_path):
    folder, log = tmp_path / "tasks", tmp_path / "activity.jsonl"
    work_tasks.save(work_tasks.Task(id="T-0001", title="Make VALUE 2", files=["core/thing.py"], body="VALUE should be 2"),
                    folder)
    result = mia_coder.shadow("T-0001", ask=reply({"core/thing.py": ("VALUE = 1", "VALUE = 2")}),
                              suite=suite({"*": ["tests/test_a.py::old"], "__lab__": []}), folder=folder, log=log)
    assert result["outcome"] == "pass", result
    assert (repo / "core" / "thing.py").read_text() == "VALUE = 1\n"  # the running copy untouched
    assert lab.get(result["proposal"]).status == lab.REJECTED  # graded, then put away
    event = [e for e in work_activity.events(log) if e["action"] == "shadow"][0]
    assert event["who"] == "MIA (ollama-coder)" and event["detail"].startswith("pass:")
    failed = mia_coder.shadow("T-0001", ask=reply({}), suite=suite({"*": []}), folder=folder, log=log)
    assert failed["outcome"] == "fail" and [e for e in work_activity.events(log) if e["action"] == "shadow"][-1][
        "detail"].startswith("fail:")


def test_the_files_a_task_lists():
    assert mia_coder.files_of("Task: x\n\nPlan: Files: core/ocr.py, tests/test_ocr.py\n\nWhat the team learned...") == \
        ["core/ocr.py", "tests/test_ocr.py"]
    assert mia_coder.files_of("no plan") == []


def test_an_edit_whose_passage_isnt_there_once_is_skipped(repo):
    (repo / "core" / "two.py").write_text("x = 1\nx = 1\n")
    said = mia_coder.coder(reply({"core/two.py": ("x = 1", "x = 2")}))("Plan: Files: core/two.py", repo, "python")
    assert "appears more than once" in said and (repo / "core" / "two.py").read_text() == "x = 1\nx = 1\n"


def test_she_can_write_a_new_file_the_task_lists(repo):
    p = lab.create("A new counter", "Add core/counter.py", plan="Files: core/counter.py, core/thing.py")
    p = lab.write(p.proposal_id, coder=mia_coder.coder(reply({"core/counter.py": ("", "def count():\n    return 1\n"),
                                                               "core/thing.py": ("", "wiped\n")})))
    where = lab.folder(p)
    assert (where / "core" / "counter.py").read_text() == "def count():\n    return 1\n"
    assert (where / "core" / "thing.py").read_text() == "VALUE = 1\n"  # a file with text in it is never replaced whole



def test_a_passage_with_its_spacing_wrong_is_still_found_once():
    """Night School, 2026-11-06: her edit to a table row was skipped for its spacing."""
    text = "# Loops\n\n| id   |  what |\n|------|-------|\n| a.b  | one   |\n| c.d  | two   |\n\nend\n"
    start, end = mia_coder.locate(text, "| a.b | one |")
    assert text[start:end] == "| a.b  | one   |"  # the whole row, its line break kept
    start, end = mia_coder.locate(text, "|  c.d |  two |\n")
    assert text[start:end] == "| c.d  | two   |\n"
    assert mia_coder.locate(text, "| x.y | three |") is None
    assert mia_coder.locate("    x = 1\ny = 2\n    x = 1\n", "x = 1") is None  # two of them, spacing aside
    exact = "def f():\n    return 1\n"
    assert mia_coder.locate(exact, "return 1") == (exact.index("return 1"), exact.index("return 1") + 8)


def test_her_edit_lands_on_the_one_matching_row(repo):
    (repo / "core" / "table.md").write_text("| a.b  | one   |\n| c.d  | two   |\n")
    said = mia_coder.coder(reply({"core/table.md": ("| a.b | one |", "| a.b | ONE |")}))(
        "Plan: Files: core/table.md", repo, "python")
    assert "changed core/table.md" in said
    assert (repo / "core" / "table.md").read_text() == "| a.b | ONE |\n| c.d  | two   |\n"
