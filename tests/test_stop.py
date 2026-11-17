"""
tests.test_stop
=================

"Stop" and "stop everything" (REQ-AUT-010; core/stop.py), one test per row of the definition's table
(docs/mia_os/MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md section 4): the commands are recognised in code and nothing
else is mistaken for them ("stop all alarms", "bus stop"); a time is read from words and one that can't be read is
asked about, never held with no end; "stop" ends her speech, the skill she's running with the person, the job she's
walking him through and her browser task (a held step is never pressed) and undoes nothing, on the web and the desktop
panels alike; "stop everything" also makes background jobs that change records or reach outside wait, holds her
unprompted messages (urgent ones and reminders he set still come) and refuses anything she'd start herself; alarms,
reminders, backups and the greenhouse's watch never wait, and nothing here reaches the greenhouse; it survives a
restart, known from boot, and ends on "carry on" or at the time he named; every job and daily check is in exactly one
list.
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


def test_every_job_and_daily_check_is_in_exactly_one_of_the_lists():
    from core.background_jobs import DAILY_CHECKS, JOBS

    jobs = {name for name, _s, _m in JOBS}
    assert jobs == stop.JOBS_THAT_WAIT | stop.JOBS_THAT_RUN and not (stop.JOBS_THAT_WAIT & stop.JOBS_THAT_RUN)
    checks = {name for name, _m in DAILY_CHECKS}
    lists = (stop.CHECKS_THAT_WAIT, stop.CHECKS_THAT_ALWAYS_RUN, stop.CHECKS_THAT_ONLY_OFFER)
    assert set().union(*lists) == checks, "a daily check in none of the three lists, or one that's gone"
    assert sum(len(names) for names in lists) == len(checks), "a daily check in more than one list"


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
    assert stop.for_shell(person, now + timedelta(hours=1))["line"] == "Everything of MIA's own is stopped until 5:00 PM."
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


def test_stop_everything_takes_only_nothing_or_a_time_after_it_and_all_of_something_is_other_words():
    assert stop.recognise("stop it all") == ("everything", "") and stop.recognise("pause all of it!") == ("everything", "")
    assert stop.recognise("stop everything please") == ("everything", "")
    assert stop.recognise("Stop everything for two hours, please") == ("everything", "for two hours")
    assert stop.recognise("freeze everything tonight") == ("everything", "tonight")
    for other in ("stop all alarms", "pause all music", "stop all reminders", "freeze all my cards", "stop all",
                  "stop everything you're doing to the budget", "stop everything that's on the calendar"):
        assert stop.recognise(other) is None, other


def test_a_plain_stop_is_heard_with_please_her_name_or_this_and_look_alikes_are_left_alone():
    for said in ("stop please", "stop, MIA", "hey MIA, stop", "Hey, MIA, stop!", "stop this", "Stop now, please."):
        assert stop.recognise(said) == ("stop", ""), said
    for other in ("don't stop", "bus stop", "stop sign", "stop by the store", "where's the nearest bus stop",
                  "stop this alarm"):
        assert stop.recognise(other) is None, other


def test_tonight_and_morning_mean_the_next_ones_late_at_night_and_early_in_the_morning():
    late, small_hours = datetime(2026, 11, 16, 21, 30), datetime(2026, 11, 16, 1, 0)
    assert stop.until_from("until tonight", late) == datetime(2026, 11, 17, 8, 0)
    assert stop.until_from("until tonight", small_hours) == datetime(2026, 11, 16, 8, 0)
    assert stop.until_from("until morning", small_hours) == datetime(2026, 11, 16, 8, 0)
    assert stop.until_from("until morning", late) == datetime(2026, 11, 17, 8, 0)
    assert stop.until_from("until tonight", datetime(2026, 11, 16, 15, 0)) == datetime(2026, 11, 16, 20, 0)
    assert stop.until_from("until tomorrow night", late) == datetime(2026, 11, 17, 20, 0)


def test_numbers_in_words_clock_times_and_tomorrow_are_read_and_an_unreadable_time_is_refused():
    now = datetime(2026, 11, 16, 15, 0)
    for words, after in (("for seven minutes", timedelta(minutes=7)), ("for nine hours", timedelta(hours=9)),
                         ("for ten minutes", timedelta(minutes=10)), ("for fifteen minutes", timedelta(minutes=15)),
                         ("for twenty minutes", timedelta(minutes=20)), ("for thirty mins", timedelta(minutes=30)),
                         ("for twenty-five minutes", timedelta(minutes=25)), ("for half an hour", timedelta(minutes=30)),
                         ("for a couple of hours", timedelta(hours=2)), ("for an hour and a half", timedelta(hours=1.5)),
                         ("for one and a half hours", timedelta(hours=1.5)), ("for 2hrs", timedelta(hours=2))):
        assert stop.until_from(words, now) == now + after, words
    assert stop.until_from("until 5pm tomorrow", now) == datetime(2026, 11, 17, 17, 0)
    assert stop.until_from("until tomorrow at 9am", now) == datetime(2026, 11, 17, 9, 0)
    assert stop.until_from("until 5", now) == datetime(2026, 11, 16, 17, 0)  # the next 5 o'clock, in 12-hour terms
    assert stop.until_from("until 5", datetime(2026, 11, 16, 18, 0)) == datetime(2026, 11, 17, 5, 0)
    assert stop.until_from("until 4:30", now) == datetime(2026, 11, 16, 16, 30)
    assert stop.until_from("until noon", now) == datetime(2026, 11, 17, 12, 0)
    assert stop.until_from("for now", now) is None  # until he says
    for unreadable in ("for a bit", "for ages", "for five", "until 5:75", "until 13pm", "until the cows come home",
                       "for zero minutes"):
        with pytest.raises(ValueError):
            stop.until_from(unreadable, now)


def test_an_unreadable_time_never_becomes_a_hold_with_no_end_she_asks_instead(person):
    for said in ("stop everything for a bit", "stop everything until 5:75", "stop everything for ages"):
        reply = stop.handle(person, said)
        assert "I didn't catch how long" in reply and "nothing is held yet" in reply, said
        assert not stop.holding(person) and person.kept.get(stop.KEY) is None, said


def test_stop_ends_the_job_she_is_walking_him_through_and_stop_the_job_is_still_the_jobs(tmp_path, monkeypatch):
    from core import trade_session as ts
    from core.actions import ActionCenter
    from core.assistant_turn import instant_answer
    from core.trade_actions import reply
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.actions = ActionCenter()
    world.trade_session = ts.TradeStore(world, data_dir=world.my_dir)
    reply(world, "walk me through building the coop")
    reply(world, "next")
    said = instant_answer(world, SimpleNamespace(mode=None, journal=False), "stop it")
    assert said.startswith("Stopped: walking you through \"") and "at step 2" in said
    assert world.trade_session.live() is None and world.trade_session.session.status == ts.STOPPED
    assert stop.recognise("stop the job") is None  # the job's own words stay the job's
    source = inspect.getsource(stop)
    assert "step_plans" not in "\n".join(source.split('"""')[2::2])  # a step plan waits on him: never dropped here


def test_the_desktop_panels_quick_answer_asks_the_stop_first_even_in_a_personal_conversation(person):
    from core.assistant_turn import instant_answer
    from core.conversation_modes import PERSONAL_MODES

    for conversation in (SimpleNamespace(mode=None, journal=False), SimpleNamespace(mode=PERSONAL_MODES[0])):
        assert instant_answer(person, conversation, "stop").startswith("Nothing of mine was running")
    assert "stopped everything of my own" in instant_answer(person, SimpleNamespace(mode=None), "stop everything")
    assert stop.holding(person)


def test_the_reminders_he_set_still_come_while_everything_is_stopped():
    from core.communication_gate import DEFER, Candidate, GateState, decide_batch

    now = datetime(2026, 11, 16, 15, 0)
    for topic in sorted(stop.TOPICS_NEVER_HELD):
        candidate = Candidate(topic=topic, title="A reminder", message=f"Your {topic} today", source="system")
        assert decide_batch([candidate], now, GateState(stopped=True), {})[0].action != DEFER, topic
    held = Candidate(topic="pattern_insight", title="An idea", message="Something I noticed", source="system")
    assert decide_batch([held], now, GateState(stopped=True), {})[0].action == DEFER


def test_a_hold_kept_from_before_a_restart_is_known_from_the_start(person, monkeypatch):
    from core.background_jobs import BackgroundJobs

    stop.stop_everything(person)
    monkeypatch.setattr(stop, "_held_until", None)
    monkeypatch.setattr(stop, "_held_known", False)  # a new process
    assert stop.held_now() is False
    BackgroundJobs(person).schedule(SimpleNamespace(add=lambda *a, **k: None))
    assert stop.held_now() is True
