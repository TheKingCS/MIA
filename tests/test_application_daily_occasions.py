"""
tests.test_application_daily_occasions
==========================================

Unit tests for core.application.MIAApplication._check_daily_occasions()
and its per-check exception isolation (2026-09-14 stabilization pass).

Constructs a bare MIAApplication instance via __new__ (skipping
__init__'s full Qt/service boot entirely) with just `.context` and
`.module_manager` set — the only two attributes any _check_* method
touches — same "test the method, not the whole app boot" approach
test_assistant_action_handlers.py already uses for MIAApplication's
other @staticmethod action handlers, extended here since these are
real instance methods.
"""

from __future__ import annotations

import pytest

from core.app_context import AppContext
from core.application import MIAApplication
from core.config_manager import ConfigManager
from core.event_bus import EventBus


@pytest.fixture
def bare_app(tmp_path, monkeypatch):
    import core.config_manager as config_manager_module

    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")

    app = MIAApplication.__new__(MIAApplication)
    app.context = AppContext(config=ConfigManager(), events=EventBus())
    app.module_manager = None
    return app


def test_check_daily_occasions_runs_with_no_optional_services_wired(bare_app):
    """Every _check_* method guards its own optional services — this
    must run clean with nothing but config wired, same as before the
    refactor."""
    bare_app._check_daily_occasions()  # must not raise


def test_a_broken_check_does_not_prevent_later_checks_from_running(bare_app, monkeypatch):
    """The whole point of the refactor: one check raising must not
    starve the checks that come after it in the list."""
    calls = []

    def _broken(now, today_iso):
        calls.append("calendar_digest")
        raise RuntimeError("simulated bug in a daily check")

    def _tracks(name):
        def _inner(now, today_iso):
            calls.append(name)
        return _inner

    # calendar_digest is the SECOND check in the list — a real
    # regression of the old code would have prevented birthday (first,
    # unaffected either way) and everything after calendar_digest from
    # running.
    monkeypatch.setattr(bare_app, "_check_birthday", _tracks("birthday"))
    monkeypatch.setattr(bare_app, "_check_calendar_digest", _broken)
    monkeypatch.setattr(bare_app, "_check_checkin", _tracks("checkin"))
    monkeypatch.setattr(bare_app, "_check_walkthrough_suggestion", _tracks("walkthrough_suggestion"))

    bare_app._check_daily_occasions()  # must not raise, even though one check does

    assert "birthday" in calls
    assert "calendar_digest" in calls  # the broken one still got its chance to run
    assert "checkin" in calls  # ran despite calendar_digest raising before it
    assert "walkthrough_suggestion" in calls  # the very last check still ran


def test_every_check_runs_exactly_once_per_call(bare_app, monkeypatch):
    calls = []
    for name in [
        "_check_birthday", "_check_calendar_digest", "_check_checkin", "_check_budget_nudge",
        "_check_smart_suggestion", "_check_maintenance_insight", "_check_mission_insight",
        "_check_pattern_insight", "_check_skill_pattern_insight", "_check_skill_decline_insight",
        "_check_skill_momentum_insight", "_check_recurring_missions", "_check_rewards",
        "_check_walkthrough_suggestion",
    ]:
        monkeypatch.setattr(bare_app, name, (lambda n: lambda now, today_iso: calls.append(n))(name))

    bare_app._check_daily_occasions()

    assert len(calls) == 14
    assert len(set(calls)) == 14  # each ran exactly once, none skipped or duplicated
