"""What he's working on: the app and title in front of him, with its safeguards (core/activity_watch.py, DEC-0197),
and how his focus holds her non-urgent offers once in the communication gate (DEC-0217)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import activity_watch as aw

T0 = datetime(2026, 11, 18, 9, 0, 0)


@pytest.mark.parametrize("app,title", [
    ("KeePassXC", "Database"), ("1Password", "Vault"), ("msedge", "New InPrivate tab - Microsoft Edge"),
    ("chrome", "New Incognito Tab"), ("firefox", "Sign in to your account"), ("Code", "password reset notes"),
    ("python", "MIA — Multifunctional Intelligent Assistant"), ("", ""),
])
def test_password_managers_private_windows_sign_ins_and_mia_herself_are_never_noted(app, title):
    assert not aw.keep_this(app, title)


def test_an_ordinary_window_is_noted():
    assert aw.keep_this("Code", "coop.py - garage - Visual Studio Code")


def test_the_same_window_again_soon_extends_one_span(tmp_path):
    log = aw.ActivityLog(None, tmp_path)
    log.note("Code", "coop.py", T0)
    log.note("Code", "coop.py", T0 + timedelta(seconds=30))
    log.note("firefox", "lumber prices", T0 + timedelta(seconds=60))
    spans = log.spans()
    assert [s["app"] for s in spans] == ["Code", "firefox"] and spans[0]["end"] == "2026-11-18T09:00:30"


def test_a_long_gap_starts_a_new_span(tmp_path):
    log = aw.ActivityLog(None, tmp_path)
    log.note("Code", "coop.py", T0)
    log.note("Code", "coop.py", T0 + timedelta(seconds=aw.JOIN_SECONDS + 1))
    assert len(log.spans()) == 2


def test_spans_older_than_seven_days_are_dropped(tmp_path):
    log = aw.ActivityLog(None, tmp_path)
    log.note("Code", "old", T0 - timedelta(days=8))
    log.note("Code", "new", T0)
    assert [s["title"] for s in log.spans()] == ["new"]


def test_titles_are_cut_and_kept_only_on_this_pc_in_his_folder(tmp_path):
    log = aw.ActivityLog(None, tmp_path)
    log.note("Code", "x" * 500, T0)
    assert len(log.spans()[0]["title"]) == aw.TITLE_CHARS
    from core import at_rest, personal_data

    assert [p.name for p in tmp_path.iterdir()] == ["activity.json"]  # one file, in his folder, no second copy
    assert "activity.json" in at_rest.SEALED  # sealed at rest wherever a key is set up
    assert any(cls is aw.ActivityLog for _name, cls in personal_data.PERSONAL_STORES)  # his own, never shared


def test_erase_forgets_everything_and_survives_a_reload(tmp_path):
    log = aw.ActivityLog(None, tmp_path)
    log.note("Code", "coop.py", T0)
    assert log.erase() == 1 and aw.ActivityLog(None, tmp_path).spans() == []


def test_the_main_thing_is_where_most_time_went():
    spans = [{"app": "Code", "title": "a", "start": "2026-11-18T09:00:00", "end": "2026-11-18T09:20:00"},
             {"app": "firefox", "title": "b", "start": "2026-11-18T09:20:00", "end": "2026-11-18T09:25:00"}]
    assert aw.main_thing(spans) == {"app": "Code", "title": "a", "minutes": 20} and aw.main_thing([]) is None


def test_a_title_naming_a_project_ties_the_work_to_it():
    projects = [SimpleNamespace(name="Chicken Coop"), SimpleNamespace(name="Garage")]
    assert aw.project_for("coop.py - chicken coop plans - Code", projects) == "Chicken Coop"
    assert aw.project_for("lumber prices", projects) is None


def _context(tmp_path, monkeypatch, on=True, projects=()):
    """A context with an activity store, noting on or off, and these projects."""
    monkeypatch.setattr("core.person_settings.get", lambda c, k, d=None: on if k == aw.SETTING else d)
    return SimpleNamespace(activity=aw.ActivityLog(None, tmp_path),
                           projects=SimpleNamespace(all_projects=lambda: list(projects)))


def test_sampling_notes_only_while_noting_is_on(tmp_path, monkeypatch):
    on = _context(tmp_path / "a", monkeypatch, on=True)
    assert aw.sample(on, T0, read=lambda: ("Code", "coop.py")) and on.activity.spans()
    off = _context(tmp_path / "b", monkeypatch, on=False)
    assert not aw.sample(off, T0, read=lambda: ("Code", "coop.py")) and off.activity.spans() == []


def test_where_was_i_names_the_app_and_its_project(tmp_path, monkeypatch):
    ctx = _context(tmp_path, monkeypatch, projects=[SimpleNamespace(name="Chicken Coop")])
    now = datetime.now()
    ctx.activity.note("Code", "chicken coop plans", now - timedelta(minutes=10))
    ctx.activity.note("Code", "chicken coop plans", now - timedelta(minutes=9))
    said = aw.said(ctx)
    assert "Code: chicken coop plans" in said and "Chicken Coop project" in said


def test_with_noting_off_she_says_so_instead_of_guessing(tmp_path, monkeypatch):
    assert "not noting" in aw.said(_context(tmp_path, monkeypatch, on=False))


def test_erasing_is_an_action_that_refuses_when_nothing_was_noted(tmp_path, monkeypatch):
    from core.actions import ACTION_TYPES, ActionError

    ctx = _context(tmp_path, monkeypatch)
    with pytest.raises(ActionError):
        ACTION_TYPES["activity.erase"].describe(ctx, {})
    ctx.activity.note("Code", "coop.py", T0)
    assert "1 stretch" in ACTION_TYPES["activity.erase"].describe(ctx, {})
    assert "Erased 1" in ACTION_TYPES["activity.erase"].execute(ctx, {})


def test_noting_is_a_personal_store_held_by_stop_everything():
    from core.personal_data import PERSONAL_ATTRIBUTES
    from core.stop import JOBS_THAT_WAIT

    assert "activity" in PERSONAL_ATTRIBUTES and "activity_watch" in JOBS_THAT_WAIT


def test_the_sidebar_indicator_follows_the_setting(tmp_path, monkeypatch):
    import sys

    from core.web_surfaces import _noting

    monkeypatch.setattr(sys, "platform", "win32")  # the one system a window can be read on, for now
    assert _noting(_context(tmp_path / "a", monkeypatch, on=True))
    assert not _noting(_context(tmp_path / "b", monkeypatch, on=False))
    assert not _noting(SimpleNamespace())
    monkeypatch.setattr(sys, "platform", "linux")  # where nothing is noted, the indicator doesn't claim it is
    assert not _noting(_context(tmp_path / "c", monkeypatch, on=True))


def _focused(tmp_path, monkeypatch, minutes, last_seen_ago=30, title="chicken coop plans", projects=()):
    """A context where he's been on one window for `minutes`, last seen `last_seen_ago` seconds ago."""
    ctx = _context(tmp_path, monkeypatch, projects=projects)
    now = datetime(2026, 11, 18, 10, 0, 0)
    end = now - timedelta(seconds=last_seen_ago)
    ctx.activity._spans = [{"app": "Code", "title": title, "start": (end - timedelta(minutes=minutes)).isoformat(),
                            "end": end.isoformat()}]
    return ctx, now


def test_ten_minutes_on_one_window_and_still_there_is_focus(tmp_path, monkeypatch):
    ctx, now = _focused(tmp_path, monkeypatch, 12, projects=[SimpleNamespace(name="Chicken Coop")])
    found = aw.focus(ctx, now)
    assert found["project"] == "Chicken Coop" and found["minutes"] >= aw.FOCUS_MIN


def test_a_few_minutes_or_having_walked_away_is_not_focus(tmp_path, monkeypatch):
    short, now = _focused(tmp_path / "a", monkeypatch, 4)
    gone, now2 = _focused(tmp_path / "b", monkeypatch, 12, last_seen_ago=600)
    assert aw.focus(short, now) is None and aw.focus(gone, now2) is None


def _decide(candidates, focus):
    """The gate's decisions for these candidates while he's focused on `focus`."""
    from core.communication_gate import GateState, decide_batch

    return decide_batch(candidates, datetime(2026, 11, 18, 10), GateState(focus=focus), {"daily_budget": 10})


def test_while_focused_an_unrelated_offer_waits_and_one_about_his_focus_comes():
    from core.communication_gate import ACT, DEFER, Candidate

    other = Candidate(topic="budget_nudge", title="Budget", message="You're near your grocery limit")
    mine = Candidate(topic="insight", title="Coop", message="Lumber for the chicken coop is cheaper this week")
    got = {d.candidate.topic: d for d in _decide([other, mine], "Chicken Coop")}
    assert got["budget_nudge"].action == DEFER and "focused on Chicken Coop" in got["budget_nudge"].reason
    assert got["insight"].action == ACT


def test_an_offer_waits_for_his_focus_only_once():
    from core.communication_gate import ACT, Candidate

    again = Candidate(topic="budget_nudge", title="Budget", message="near the limit", not_before="2026-11-18T09:30:00")
    assert _decide([again], "Chicken Coop")[0].action == ACT


def test_urgent_never_waits_for_focus():
    from core.communication_gate import ACT, URGENT, Candidate

    alarm = Candidate(topic="smoke", title="Smoke", message="Smoke in the garage", urgency=URGENT)
    assert _decide([alarm], "Chicken Coop")[0].action == ACT
