"""The plain-Python scheduler (core/scheduler.py, DEC-0155): jobs on intervals by a clock that's passed in, under
the store lock or not now, one failure never stopping the rest, and no catching up after a sleep."""

import threading

import pytest

from core.scheduler import Scheduler


class Clock:
    """A clock a test moves by hand."""

    def __init__(self):
        """Starts at 100 seconds."""
        self.now = 100.0

    def __call__(self):
        """The time now."""
        return self.now


def test_a_job_first_runs_one_interval_in_and_then_every_interval():
    clock, ran = Clock(), []
    s = Scheduler(clock)
    s.add("alarms", 20, lambda: ran.append("alarms"))
    s.add("daily", 300, lambda: ran.append("daily"))
    assert s.run_due() == [] and s.next_wait() == 5.0
    clock.now += 20
    assert s.run_due() == ["alarms"] and s.run_due() == []
    clock.now += 280
    assert s.run_due() == ["alarms", "daily"] and ran == ["alarms", "alarms", "daily"]
    assert s.names() == ["alarms", "daily"]


def test_a_job_can_be_asked_to_run_at_the_first_tick():
    clock, ran = Clock(), []
    s = Scheduler(clock)
    s.add("missions", 300, lambda: ran.append(1), first_after=0)
    assert s.run_due() == ["missions"] and s.run_due() == []


def test_after_a_long_sleep_a_job_runs_once_not_once_for_every_interval_missed():
    clock, ran = Clock(), []
    s = Scheduler(clock)
    s.add("alarms", 20, lambda: ran.append(1))
    clock.now += 8 * 3600  # the computer slept all night
    assert s.run_due() == ["alarms"] and s.run_due() == [] and len(ran) == 1
    clock.now += 20
    assert s.run_due() == ["alarms"]


def test_a_job_that_fails_is_recorded_and_the_others_still_run():
    clock, ran = Clock(), []
    s = Scheduler(clock, wall=lambda: "2026-11-15T09:00:00")
    s.add("broken", 10, lambda: 1 / 0)
    s.add("fine", 10, lambda: ran.append(1))
    clock.now += 10
    assert s.run_due() == ["broken", "fine"] and ran == [1]
    broken, fine = s.status()
    assert broken["failures"] == 1 and broken["last_error"].startswith("ZeroDivisionError") and broken["runs"] == 1
    assert fine == {"name": "fine", "every_seconds": 10.0, "runs": 1, "skips": 0, "failures": 0,
                    "last_run": "2026-11-15T09:00:00", "last_seconds": 0.0, "last_error": "", "due_in_seconds": 10.0}
    clock.now += 10
    assert s.run_due() == ["broken", "fine"]  # it keeps its place in the schedule


def test_a_job_waits_for_the_stores_and_runs_at_the_next_tick_not_the_next_interval():
    clock, lock, held = Clock(), threading.Lock(), []
    s = Scheduler(clock, lock=lock)
    s.add("inbox", 30, lambda: held.append(lock.locked()))
    clock.now += 30
    with lock:  # the phone's server is mid-request
        assert s.run_due() == [] and s.status()[0]["skips"] == 1 and s.next_wait() == 0.0
    assert s.run_due() == ["inbox"] and held == [True] and not lock.locked()  # it ran holding the lock, then let go


def test_two_callers_never_run_jobs_at_the_same_time():
    clock, order = Clock(), []
    s = Scheduler(clock)

    def slow():
        """A job during which someone else calls run_due."""
        order.append(s.run_due())  # a second caller while this one runs: nothing to do
    s.add("slow", 10, slow)
    clock.now += 10
    assert s.run_due() == ["slow"] and order == [[]]


def test_run_forever_runs_due_jobs_until_told_to_stop():
    ran, stop = [], threading.Event()
    s = Scheduler()
    s.add("quick", 0.01, lambda: (ran.append(1), len(ran) >= 3 and stop.set()))
    worker = threading.Thread(target=s.run_forever, args=(stop,), daemon=True)
    worker.start()
    worker.join(timeout=10)
    assert not worker.is_alive() and len(ran) >= 3


def test_a_name_used_twice_or_a_zero_interval_is_refused():
    s = Scheduler(Clock())
    s.add("a", 5, lambda: None)
    with pytest.raises(ValueError, match="already a job called a"):
        s.add("a", 5, lambda: None)
    with pytest.raises(ValueError, match="more than zero"):
        s.add("b", 0, lambda: None)
