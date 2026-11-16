"""
tests.test_stop
=================

"Stop" and "stop everything" (REQ-AUT-010; core/stop.py), one test per row of the definition's table
(docs/mia_os/MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md section 4): the commands are recognised in code and nothing
else is mistaken for them; "stop" ends her speech, the skill she's running with the person and her browser task (a held
step is never pressed) and undoes nothing; "stop everything" also makes background jobs that change records or reach
outside wait, holds her unprompted messages (urgent ones still come) and refuses anything she'd start herself; alarms,
reminders, backups and the greenhouse's watch never wait, and nothing here reaches the greenhouse; it survives a
restart and ends on "carry on" or at the time he named; every job and daily check is decided one way or the other.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import grants, stop
from core.actions import ActionError
from core.runs import RunBook
from tests.test_browser import SHOP, edge, tool, world  # noqa: F401  (the browser test world)


@pytest.fixture
def person(monkeypatch):
    """A context whose person settings are a plain dict, with nothing running; the process's hold copy cleared."""
    from core import person_settings

    kept = {}
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: kept.get(key, default))
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: kept.__setitem__(key, value))
    monkeypatch.setattr(stop, "_held_until", None)
    monkeypatch.setattr(stop, "_held_known", False)
    return SimpleNamespace(kept=kept)


def test_the_commands_are_whole_messages_and_nothing_else_is_taken_for_them():
    assert stop.recognise("stop") == ("stop", "") and stop.recognise("Mia, stop!") == ("stop", "")
    assert stop.recognise("Hey MIA please stop it.") == ("stop", "")
    assert stop.recognise("stop everything") == ("everything", "")
    assert stop.recognise("Stop everything until tonight") == ("everything", "until tonight")
    for other in ("stop the timer", "stop the skill", "stop watching me", "can you stop by the store list",
                  "don't stop", "stop cooking", "carry on", "what happens if I say stop"):
        assert stop.recognise(other) is None, other
    assert stop.recognise("carry on", holding_now=True) == ("carry_on", "")
    assert stop.recognise("carry on with the recipe", holding_now=True) is None


def test_a_time_in_words_is_read_and_no_time_means_until_he_says():
    now = datetime(2026, 11, 16, 15, 0)
    assert stop.until_from("", now) is None
    assert stop.until_from("until tonight", now) == datetime(2026, 11, 16, 20, 0)
    assert stop.until_from("until tomorrow", now) == datetime(2026, 11, 17, 8, 0)
    assert stop.until_from("for two hours", now) == datetime(2026, 11, 16, 17, 0)
    assert stop.until_from("for 30 minutes", now) == datetime(2026, 11, 16, 15, 30)
    assert stop.until_from("until 5pm", now) == datetime(2026, 11, 16, 17, 0)
    assert stop.until_from("until 9am", now) == datetime(2026, 11, 17, 9, 0)


def test_stop_ends_her_browser_task_without_pressing_the_held_step_and_undoes_nothing(world):  # noqa: F811
    world.runs = RunBook(world, data_dir=Path(world.browser_routines.data_dir))
    world.browser_routines.add("Order widgets", SHOP, [{"kind": "open", "url": SHOP},
                                                      {"kind": "click", "role": "button", "name": "Place order"}])
    tool(world, "do_browser_task", name="Order widgets")
    [run] = world.runs.open_runs()
    said = stop.handle(world, "stop")
    assert said.startswith("Stopped:") and "not pressed" in said and "Nothing was undone" in said
    assert run.status == "stopped" and ("click", 5) not in edge(world).did
    assert not world.browsers.for_person(world).pending and not world.actions.pending(world.me.profile_id)
    assert ("open", SHOP) in edge(world).did or edge(world).url == SHOP  # what finished stays finished
    assert stop.holding(world) is False  # a plain stop holds nothing
    assert stop.handle(world, "stop").startswith("Nothing of mine was running")


def test_stop_ends_the_skill_she_is_running_with_the_person():
    from tests.test_taught_skills import RESET  # noqa: F401
    import core.taught_skills as ts

    stopped = []
    book = SimpleNamespace(active=SimpleNamespace(skill_id="s1", at=1, record_id=""), context=None,
                           get=lambda i: SimpleNamespace(name="Friday reset", last_run="", last_result=""),
                           _save_run=lambda: stopped.append("saved"))
    context = SimpleNamespace(taught_skills=book, voice=SimpleNamespace(stop_playback=lambda: stopped.append("voice")))
    done = stop.stop_now(context)
    assert done["stopped"] == ['"Friday reset" at step 2'] and book.active is None and "voice" in stopped
    assert ts.stop(context) is False


def test_stop_everything_makes_only_her_own_outward_and_record_changing_work_wait(person):
    assert stop.defer_reason(person, "world_intel") == ""
    said = stop.handle(person, "stop everything")
    assert "stopped everything of my own until you say" in said and stop.holding(person)
    for name in ("world_intel", "inbox_mail", "mission_auto_assignment", "workflows", "night_school", "good_news"):
        assert stop.defer_reason(person, name) == "you asked me to stop everything", name
    for name in ("alarms", "power", "online", "daily_occasions", "auto_backup", "greenhouse", "obligation_reminders",
                 "calendar_digest", "grow_alert"):
        assert stop.defer_reason(person, name) == "", name  # never stopped


def test_every_job_and_daily_check_is_decided_one_way_or_the_other():
    from core.background_jobs import DAILY_CHECKS, JOBS

    jobs = {name for name, _s, _m in JOBS}
    assert jobs == stop.JOBS_THAT_WAIT | stop.JOBS_THAT_RUN and not (stop.JOBS_THAT_WAIT & stop.JOBS_THAT_RUN)
    checks = {name for name, _m in DAILY_CHECKS}
    assert stop.CHECKS_THAT_WAIT <= checks and stop.CHECKS_THAT_ALWAYS_RUN <= checks
    assert not (stop.CHECKS_THAT_WAIT & stop.CHECKS_THAT_ALWAYS_RUN)


def test_her_messages_are_held_while_everything_is_stopped_and_urgent_ones_still_come():
    from core.communication_gate import ACT, DEFER, URGENT, Candidate, GateState, decide_batch

    now = datetime(2026, 11, 16, 15, 0)
    quiet = Candidate(topic="insight", title="An idea", message="Something I noticed", source="system")
    urgent = Candidate(topic="bill", title="Due today", message="The power bill is due today", source="system",
                       urgency=URGENT)
    held, came = decide_batch([quiet, urgent], now, GateState(stopped=True), {})
    assert held.action == DEFER and "stop everything" in held.reason and quiet.not_before
    assert came.action == ACT
    assert decide_batch([Candidate(topic="insight", title="An idea", message="Another", source="system")], now,
                        GateState(stopped=False), {})[0].action != DEFER


def test_nothing_she_starts_herself_changes_a_record_while_everything_is_stopped(person, monkeypatch):
    monkeypatch.setattr(grants, "tier_of", lambda capability: grants.WITHIN_GRANT)
    assert grants.require("records.add", grants.MIA, granted=True).allowed
    stop.stop_everything(person)
    with pytest.raises(ActionError, match="stop everything"):
        grants.require("records.add", grants.MIA, granted=True)
    assert grants.require("records.add", grants.PERSON).allowed  # what he asks or presses always runs
    stop.carry_on(person)
    assert grants.require("records.add", grants.MIA, granted=True).allowed


def test_it_survives_a_restart_and_ends_on_carry_on_or_at_the_time_he_named(person, monkeypatch):
    now = datetime(2026, 11, 16, 15, 0)
    stop.stop_everything(person, until=now + timedelta(hours=2), now=now)
    monkeypatch.setattr(stop, "_held_until", None)
    monkeypatch.setattr(stop, "_held_known", False)  # a new process: only the person's setting remains
    assert stop.held_now(now) is False and stop.holding(person, now + timedelta(hours=1)) is True
    assert stop.held_now(now + timedelta(hours=1)) is True
    assert stop.for_shell(person)["line"].startswith("Everything of MIA's own is stopped until")
    assert stop.holding(person, now + timedelta(hours=3)) is False and person.kept[stop.KEY] is None  # the time passed
    stop.stop_everything(person)
    assert stop.handle(person, "carry on").startswith("Carrying on") and not stop.holding(person)
    assert stop.handle(person, "carry on") is None  # with nothing stopped, "carry on" is an ordinary message


def test_the_stop_never_reaches_the_greenhouse_or_any_device():
    source = inspect.getsource(stop)
    code = "\n".join(line for line in source.split('"""')[2::2])  # the code between docstrings
    for reach in ("greenhouse_link", "home_link", "homestead_manager", "context.homestead", "device_framework", "serial", "set_target", "command("):
        assert reach not in code, reach
    assert "greenhouse" in stop.CHECKS_THAT_ALWAYS_RUN  # her watch of it keeps running too


def test_the_turn_pipeline_asks_the_stop_first_and_the_frame_has_the_control():
    root = Path(__file__).resolve().parent.parent
    turn = (root / "core" / "assistant_turn.py").read_text(encoding="utf-8")
    assert turn.index("stop.handle(context, prompt)") < turn.index("prepared = pre_turn(context, conversation, prompt)")
    shell = (root / "web" / "shell.js").read_text(encoding="utf-8")
    assert 'stopButton("side-stop")' in shell and "bottom-stop" in shell and "stoppedBanner(shell.stopped)" in shell
    assert '"/api/stop"' in (root / "web" / "mia.js").read_text(encoding="utf-8")
    assert '@app.post("/api/stop")' in (root / "server" / "app.py").read_text(encoding="utf-8")
