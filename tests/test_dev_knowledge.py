"""The Development Knowledge Vault (DEC-0073, core/dev_knowledge.py): what the
team learned, each entry tied to where it came from, MIA's own notes kept as
derived until someone confirms them, and given to agents before they work."""

import json
from types import SimpleNamespace

import pytest

from core import dev_knowledge as dk
from core import work_activity as activity
from core import work_tasks as tasks_mod


def test_an_entry_says_where_it_came_from_or_isnt_kept(tmp_path):
    e = dk.add("debugging", "Tesseract on PATH masks the missing-binary test", "The test patched which() but core/ocr.py "
               "falls back to _WINDOWS_DEFAULT; patch both.", ["task:T-0019", "review:T-0019@2026-11-03T15:22:00+00:00"],
               ["core/ocr.py", "tests/test_ocr.py"], folder=tmp_path)
    assert e["id"] == "K-0001" and e["status"] == "derived"
    found = dk.entries(tmp_path)[0]
    assert found["concerns"] == ["core/ocr.py", "tests/test_ocr.py"] and found["from"][0] == "task:T-0019"
    for refs in ([], ["somewhere"], ["task:T-1 rm -rf"]):
        with pytest.raises(dk.KnowledgeError, match="where it came from"):
            dk.add("lesson", "x", "y", refs, folder=tmp_path)
    with pytest.raises(dk.KnowledgeError, match="already an entry"):
        dk.add("debugging", "Tesseract on PATH masks the missing-binary test", "again", ["task:T-0019"], folder=tmp_path)
    with pytest.raises(dk.KnowledgeError, match="kind is one of"):
        dk.add("gossip", "x", "y", ["task:T-1"], folder=tmp_path)


def test_better_knowledge_supersedes_and_a_person_confirms(tmp_path):
    old = dk.add("method", "Run the suite once", "One run is enough.", ["task:T-0001"], folder=tmp_path)
    new = dk.add("method", "Run the suite on both copies", "Compare with the running copy's own failures.",
                 ["task:T-0019"], supersedes=old["id"], folder=tmp_path)
    statuses = {e["id"]: e["status"] for e in dk.entries(tmp_path)}
    assert statuses == {old["id"]: "superseded", new["id"]: "derived"}
    dk.confirm(new["id"], "zac", folder=tmp_path)
    assert dk.entries(tmp_path)[1]["status"] == "confirmed"


def test_agents_get_what_bears_on_their_task(tmp_path):
    dk.add("debugging", "Patch both lookups in OCR tests", "which() and the Windows default both find Tesseract.",
           ["task:T-0019"], ["core/ocr.py"], folder=tmp_path)
    dk.add("method", "Glasses cards come from core", "Never logic in web/glasses.js.", ["dec:DEC-0013"],
           ["web/glasses.js"], folder=tmp_path)
    task = SimpleNamespace(title="OCR fails on the phone", body="", files=["core/ocr.py"])
    assert dk.for_task(task, tmp_path) == []  # MIA's own note, not yet confirmed: not handed on (K-0033)
    assert [e["title"] for e in dk.for_task(task, tmp_path, derived=True)] == ["Patch both lookups in OCR tests"]
    dk.confirm("K-0001", "zac", folder=tmp_path)
    text = dk.briefing(task, tmp_path)
    assert "confirmed entries" in text and "K-0001" in text
    assert dk.briefing(SimpleNamespace(title="Money", body="", files=["core/budget_manager.py"]), tmp_path) == ""


def test_the_retrospective_cites_only_what_the_record_holds(tmp_path):
    folder, log, know = tmp_path / "tasks", tmp_path / "activity.jsonl", tmp_path / "knowledge"
    tasks_mod.save(tasks_mod.Task(id="T-0019", title="A shared baseline", status="done", files=["tests/test_ocr.py"],
                                  decisions=["DEC-0071"], body="Fix the failures."), folder)
    activity.record("QA Engineer (ollama-coder)", "review", "T-0019", "changes: _WINDOWS_DEFAULT unused", log)
    activity.record("zac", "approve", "T-0019", "merged abc1234567; commit abc1234", log)
    seen = {}

    def model(prompt, schema):
        seen["prompt"] = prompt
        return json.dumps({"entries": [
            {"kind": "lesson", "title": "Check a name's callers before calling it unused", "body": "The reviewer missed core/ocr.py.",
             "concerns": ["core/ocr.py"], "from": ["dec:DEC-0071", "commit:deadbeef"]},  # one real, one invented
            {"kind": "gossip", "title": "x", "body": "y", "from": []}]})

    kept = dk.retrospective("T-0019", ask=model, tasks_dir=folder, log=log, folder=know)
    assert [e["title"] for e in kept] == ["Check a name's callers before calling it unused"]
    assert kept[0]["from"] == "task:T-0019, dec:DEC-0071"  # the invented commit was dropped, the task added
    assert "_WINDOWS_DEFAULT unused" in seen["prompt"] and "commit:abc1234" in seen["prompt"]
    assert dk.retrospective("T-0019", ask=model, tasks_dir=folder, log=log, folder=know) == []  # once per task


def test_the_reviewer_lessons_fold_in_once(tmp_path):
    lessons = {"ollama-coder": [{"task": "T-0019", "lesson": "Search the whole repo before calling a name unused."}]}
    assert len(dk.fold_lessons(lessons, tmp_path)) == 1 and dk.fold_lessons(lessons, tmp_path) == []
    assert dk.entries(tmp_path)[0]["status"] == "derived" and dk.entries(tmp_path)[0]["by"] == "review"


def test_a_thin_record_teaches_nothing_and_wrong_entries_are_withdrawn(tmp_path):
    folder, log, know = tmp_path / "tasks", tmp_path / "activity.jsonl", tmp_path / "knowledge"
    tasks_mod.save(tasks_mod.Task(id="T-0005", title="Done in one go", status="done"), folder)
    activity.record("claude", "claim", "T-0005", "files: x", log)
    activity.record("claude", "done", "T-0005", "tests passed", log)
    asked = []
    assert dk.retrospective("T-0005", ask=lambda p, s: asked.append(p) or "{}", tasks_dir=folder, log=log, folder=know) == []
    assert asked == []  # the model isn't even asked: there's no process to describe
    e = dk.add("debugging", "An invented failure", "It failed first.", ["task:T-0005"], folder=know)
    dk.withdraw(e["id"], "claude", "the record shows no failure", folder=know)
    assert dk.entries(know)[0]["status"] == "withdrawn" and "Withdrawn by claude" in dk.entries(know)[0]["body"]
    assert dk.for_task(SimpleNamespace(title="invented failure first", body="", files=[]), know, derived=True, min_hits=1) == []