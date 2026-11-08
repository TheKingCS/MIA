"""Self-enablement (build plan step 9, core/capability_gaps.py): requests no tool matched become gaps with
what they'd take, worked out in code; a repeated one is offered through the gate; "build it" opens a task that
names the gap by id, never the person's words; "bring it back" shows a tucked-away app."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from core import capability_gaps as cg
from core import loops
from core.actions import ActionCenter
from core.failure_log import FailureLog

BY_ID = {l.id: l for l in loops.LOOPS}


@pytest.fixture
def person(tmp_path, monkeypatch):
    """A stand-in person: a failure log in a temporary folder, an action center, and every request's app allowed."""
    from core import actions

    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    monkeypatch.setattr(cg, "_hidden_app", lambda context, request: None)
    return SimpleNamespace(failures=FailureLog(None, data_dir=tmp_path / "me"), actions=ActionCenter(), config=None,
                           undo=None, tmp=tmp_path)


def test_what_a_request_would_take(person):
    assert cg.need_of(person, "What am I looking at right now?")["need"] == "device"
    assert cg.need_of(person, "Remind me every Sunday to water the seedlings")["need"] == "workflow"
    assert cg.need_of(person, "Keep track of how many eggs each hen lays")["need"] == "screen"
    assert cg.need_of(person, "Translate this recipe into Spanish")["need"] == "code"


def test_a_tucked_away_app_is_found_by_its_own_words(monkeypatch):
    import core.focus_presets as fp

    monkeypatch.setattr(fp, "current", lambda context: ("", [], ["greenhouse"]))
    found = cg.need_of(SimpleNamespace(), "How are my greenhouse seedlings doing?")
    assert found["need"] == "app" and found["app"] == "greenhouse"


def test_requests_alike_are_one_gap_and_each_event_counts_once(person):
    for said in ("Translate this recipe into Spanish", "translate the recipe into spanish please",
                 "What's the weather on Mars?"):
        person.failures.record("no_tool", prompt=said)
    gaps = cg.refresh(person)
    assert [(g["count"], g["need"]) for g in gaps] == [(2, "code"), (1, "code")]
    assert cg.refresh(person)[0]["count"] == 2  # read again: the same events aren't counted twice


def test_a_repeated_gap_is_offered_once_a_fortnight(person):
    for _ in range(2):
        person.failures.record("no_tool", prompt="Translate this recipe into Spanish")
    person.failures.record("no_tool", prompt="What's the weather on Mars?")
    now = datetime.now(timezone.utc)
    offered = cg.offers(person, now)
    assert len(offered) == 1 and offered[0].topic == "capability_gap" and "ask for it to be built" in offered[0].message
    assert cg.offers(person, now + timedelta(days=3)) == []
    assert len(cg.offers(person, now + timedelta(days=15))) == 1


def test_build_it_opens_a_task_without_their_words(person, monkeypatch):
    from core import work_tasks

    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    monkeypatch.setattr(work_tasks, "TASKS_DIR", person.tmp / "tasks")
    import core.work_activity as wa

    monkeypatch.setattr(wa, "ACTIVITY", person.tmp / "activity.jsonl")
    for _ in range(2):
        person.failures.record("no_tool", prompt="Translate my grandmother's recipe into Spanish")
    cg.offers(person)
    assert cg.reply(person, "what's for dinner") is None
    said = cg.reply(person, "Yes, build it")
    assert "on the development list" in said
    task = next(iter(work_tasks.load(person.tmp / "tasks").values()))
    assert task.source == "gap:G-0001" and "grandmother" not in task.body and "Spanish" not in task.body
    assert cg.get(person, "G-0001")["status"] == "accepted"
    assert cg.reply(person, "build it") is None  # nothing waiting any more


def test_bring_it_back_shows_the_app(person, monkeypatch):
    import core.focus_presets as fp

    shown = []
    monkeypatch.setattr(cg, "_hidden_app", lambda context, request: {"module_id": "greenhouse", "name": "Greenhouse"})
    monkeypatch.setattr(fp, "set_app_visible", lambda context, module_id, visible: shown.append((module_id, visible)))
    for _ in range(2):
        person.failures.record("no_tool", prompt="How are my seedlings doing?")
    assert "want it back" in cg.offers(person)[0].message
    cg.reply(person, "bring it back")
    assert shown == [("greenhouse", True)] and cg.get(person, "G-0001")["status"] == "done"


def test_the_loop_counts_repeated_gaps(person):
    for said in ("Translate this recipe into Spanish", "translate this recipe into spanish", "What's on Mars?"):
        person.failures.record("no_tool", prompt=said)
    cg.refresh(person)
    reading = BY_ID["gaps.repeated"].measure(person)
    assert (reading.value, reading.n) == (1, 2) and "code 2" in reading.detail
