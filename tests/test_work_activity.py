"""Who did what to the development work (DEC-0068, core/work_activity.py):
an append-only log, searchable, that says where an interrupted task got to,
and closing a task gathers its evidence."""

import json
from datetime import datetime, timezone

from core import work_activity as a

AT = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def test_events_are_appended_and_never_rewritten(tmp_path):
    log = tmp_path / "activity.jsonl"
    a.record("claude", "claim", "T-0002", "files: core/x.py", log, AT)
    before = log.read_text(encoding="utf-8")
    a.record("zac", "note", "T-0002", "looks good", log, AT)
    after = log.read_text(encoding="utf-8")
    assert after.startswith(before) and len(after.splitlines()) == 2
    assert json.loads(after.splitlines()[1])["who"] == "zac"


def test_history_is_searchable(tmp_path):
    log = tmp_path / "activity.jsonl"
    a.record("claude", "note", "T-0001", "the relay review", log, AT)
    a.record("chatgpt", "note", "T-0002", "the dashboard layout", log, AT)
    assert [e["task"] for e in a.search("relay", path=log)] == ["T-0001"]
    assert [e["task"] for e in a.search(who="chatgpt", path=log)] == ["T-0002"]
    assert a.search("dashboard", task_id="t-0002", path=log)


def test_an_interrupted_task_shows_its_last_step(tmp_path):
    log = tmp_path / "activity.jsonl"
    a.record("claude", "claim", "T-0003", "", log, AT)
    a.record("claude", "note", "T-0003", "half the tests written", log, AT)
    assert a.last_step("T-0003", log)["detail"] == "half the tests written"
    assert a.last_step("T-0999", log) is None


def test_a_broken_line_doesnt_lose_the_rest(tmp_path):
    log = tmp_path / "activity.jsonl"
    a.record("claude", "note", "T-0001", "one", log, AT)
    with open(log, "a", encoding="utf-8") as out:
        out.write("not json\n")
    a.record("claude", "note", "T-0001", "two", log, AT)
    assert [e["detail"] for e in a.events(log)] == ["one", "two"]


def test_evidence_names_the_commit():
    assert a.commit()  # "<hash> <subject>", plus anything uncommitted
