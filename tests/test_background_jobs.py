"""MIA's scheduled jobs without the window (core/background_jobs.py, DEC-0155): the ten jobs and 43 daily checks
are pinned so none is lost on the way to MIA OS; they run with no Qt; and the desktop app runs the very same ones."""

import subprocess
import sys

from core.background_jobs import DAILY_CHECKS, JOBS, BackgroundJobs
from core.scheduler import Scheduler

# What the ten QTimers in core/application.py were on 2026-11-15, before they moved: name -> seconds; and the jobs
# added since (World Intelligence's watches, DEC-0170).
THE_TIMERS = {"alarms": 20, "power": 30, "daily_occasions": 300, "finance_snapshots": 60, "homestead_snapshots": 60,
              "lite_captures": 60, "inbox": 30, "inbox_mail": 600, "online": 60, "mission_auto_assignment": 300,
              "world_intel": 600, "self_repair": 300, "activity_watch": 30, "recall_index": 600}
THE_DAILY_CHECKS = (
    "birthday calendar_digest checkin budget_nudge smart_suggestion maintenance_insight mission_insight "
    "pattern_insight skill_pattern_insight skill_decline_insight skill_momentum_insight recurring_mission rewards "
    "walkthrough_suggestion journal_reflection warranty chronicle memory_callback grow_alert season "
    "insurance_renewal findings obligation_reminders loop fix_report workflows loops night_school self_report "
    "self_changes capability_gaps seasons_of_memory operating_journal good_news chronicle_issue promises vault_captions "
    "dependency_audit system_map direction_nudge capability_reminder momentum greenhouse auto_backup restore_drill update_waiting weather_watch unusual garden_week money_pulse condition_watch trip_eve standing_reports market_eve evening_wrap morning_briefing habit_offer").split()


def test_every_timer_the_desktop_had_is_a_job_with_the_same_interval():
    assert {name: seconds for name, seconds, _ in JOBS} == THE_TIMERS
    assert all(callable(getattr(BackgroundJobs, method)) for _, _, method in JOBS)


def test_every_daily_check_is_still_there_in_the_same_order():
    """The daily checks, in order: the 43 the desktop had, the summary of her own changes (DEC-0225) and the monthly
    restore drill (WP-09), the update waiting for his restart (Q-114), the weather against his plans, what's
    unusual, this week in the garden, his money this week (the Sunday pulse), what he asked her to watch, the day before a trip, his questions answered on a schedule, the day before a market, the evening wrap, the morning briefing he asks for and
    routines offered from his habits."""
    assert [name for name, _ in DAILY_CHECKS] == THE_DAILY_CHECKS and len(DAILY_CHECKS) == 57
    assert all(callable(getattr(BackgroundJobs, method)) for _, method in DAILY_CHECKS)
    assert len({method for _, method in DAILY_CHECKS}) == 57  # no check listed twice under two names


def test_the_jobs_need_no_qt_and_nothing_from_the_gui_or_the_modules():
    """In a fresh Python: importing the jobs and the scheduler loads no PySide6, gui or modules code."""
    code = ("import sys; import core.background_jobs, core.scheduler; "
            "bad = [m for m in sys.modules if m.split('.')[0] in ('PySide6', 'gui', 'modules')]; "
            "print(bad); sys.exit(1 if bad else 0)")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_desktop_app_runs_the_same_jobs_it_always_did():
    from core.application import MIAApplication

    assert issubclass(MIAApplication, BackgroundJobs)
    for _, _, method in JOBS:
        assert getattr(MIAApplication, method) is getattr(BackgroundJobs, method)
    source = open(MIAApplication.__init__.__code__.co_filename, encoding="utf-8").read()
    assert source.count("QTimer()") == 1  # one timer asks the scheduler; the ten are gone


def test_the_jobs_go_on_a_scheduler_and_the_daily_checks_run_headless(tmp_path, monkeypatch):
    """A headless MIA: a context with no window, its jobs on a scheduler by a clock the test moves; the daily tick
    runs every check (one that fails doesn't stop the rest) and hands what they offer to the communication gate."""
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    jobs = BackgroundJobs(world)
    ran, offered = [], []
    for name, method in DAILY_CHECKS:
        monkeypatch.setattr(jobs, method, lambda now, today, name=name: ran.append(name), raising=True)
    monkeypatch.setattr(jobs, "_check_warranties", lambda now, today: 1 / 0)
    monkeypatch.setattr(jobs, "_check_birthday", lambda now, today: (ran.append("birthday"), jobs._offer(
        topic="birthday", title="Happy birthday", message="It's today.", urgency="timely")))

    class Gate:
        """A stand-in for the communication gate."""

        def offer_batch(self, offers, now):
            """Keeps what the tick offered."""
            offered.extend(o.title for o in offers)
    world.communication = Gate()
    for name, _, method in JOBS:
        if name != "daily_occasions":
            monkeypatch.setattr(jobs, method, lambda name=name: ran.append(name))
    now = [0.0]
    scheduler = Scheduler(clock=lambda: now[0])
    jobs.schedule(scheduler)
    assert scheduler.names() == [name for name, _, _ in JOBS] and scheduler.run_due() == []
    now[0] = 600
    assert scheduler.run_due() == [name for name, _, _ in JOBS]
    assert [n for n in ran if n in THE_DAILY_CHECKS] == [n for n in THE_DAILY_CHECKS if n != "warranty"]
    assert offered == ["Happy birthday"]
    assert all(j["failures"] == 0 for j in scheduler.status())  # a failing check is the tick's own business
