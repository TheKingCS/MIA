"""
tests.test_homeostasis
========================

MIA easing off her own work (the Living System doctrine's homeostasis, DEC-0173; core/homeostasis.py,
core/scheduler.py): deferrable jobs wait while the computer is busy, on a low battery, offline (the online ones) or
nearly out of disk (the heavy ones), essential jobs never do; a waiting job is tried again at its next turn and counted
as a deferral, not a failure; a job that keeps failing backs off and goes back to normal after a success; and each
time she starts easing off or backing off she says so once, with why, through the communication gate.
"""

from types import SimpleNamespace

from core.homeostasis import (BACKOFF_MOST, Homeostasis, backoff_seconds, conditions, reason_for)
from core.scheduler import Scheduler


class Clock:
    """A clock the test moves by hand."""

    def __init__(self):
        """Starts at zero."""
        self.now = 0.0

    def __call__(self):
        """The time now."""
        return self.now


class Gate:
    """A stand-in gate that keeps what was offered."""

    def __init__(self):
        """Nothing offered yet."""
        self.said = []

    def offer(self, candidate, now=None):
        """Keeps the candidate."""
        self.said.append(candidate)
        return []


def test_busy_means_the_last_three_readings_not_one_spike():
    assert conditions([90, 95], None, None, None, None) == {}
    assert "processor at 92%" in conditions([90, 95, 92], None, None, None, None)["busy"]
    assert "memory" in conditions([10], 6.0, None, None, None)["busy"]
    assert conditions([], None, (25.0, True), True, 50.0) == {}  # plugged in: the battery doesn't matter
    found = conditions([], None, (25.0, False), False, 3.0)
    assert set(found) == {"battery", "offline", "disk"}


def test_essential_work_never_waits_and_each_condition_holds_only_what_it_should():
    busy, offline, disk = {"busy": "busy"}, {"offline": "no internet"}, {"disk": "disk full"}
    assert reason_for("alarms", busy) == "" and reason_for("auto_backup", busy) == ""
    assert reason_for("world_intel", busy) == "busy" and reason_for("system_map", busy) == "busy"
    assert reason_for("world_intel", offline) == "no internet" and reason_for("system_map", offline) == ""
    assert reason_for("night_school", disk) == "disk full" and reason_for("world_intel", disk) == ""


def test_a_job_that_keeps_failing_backs_off_up_to_six_hours():
    assert [backoff_seconds(600, n) for n in (0, 1, 2)] == [600, 600, 600]
    assert [backoff_seconds(600, n) for n in (3, 4, 5)] == [1200, 2400, 4800]
    assert backoff_seconds(600, 30) == BACKOFF_MOST


def test_a_waiting_job_is_tried_at_its_next_turn_and_counted_as_a_deferral_not_a_failure():
    clock, ran = Clock(), []
    s = Scheduler(clock, wall=lambda: "t")
    s.add("world_intel", 600, lambda: ran.append("world"))
    s.add("alarms", 20, lambda: ran.append("alarm"))
    s.defer = lambda name: "the computer is busy" if name == "world_intel" else ""
    clock.now = 600
    assert s.run_due() == ["alarms"] and ran == ["alarm"]
    world = s.status()[0]
    assert world["deferrals"] == 1 and world["last_deferred"] == "the computer is busy" and world["failures"] == 0
    s.defer = lambda name: ""
    clock.now = 1200
    assert "world_intel" in s.run_due()


def test_backing_off_is_reported_once_and_a_success_resets_it():
    clock, told, fail = Clock(), [], [True]

    def job():
        """Fails while fail[0] is set."""
        if fail[0]:
            raise OSError("feed down")
    s = Scheduler(clock, wall=lambda: "t")
    s.add("world_intel", 600, job)
    s.on_backoff = lambda name, n, wait, error: told.append((name, n, wait, error))
    for _ in range(4):
        clock.now = s.status()[0]["due_in_seconds"] + clock.now
        s.run_due()
    assert told == [("world_intel", 3, 1200.0, "OSError: feed down")]  # once, at the third failure in a row
    assert s.status()[0]["due_in_seconds"] == 2400.0  # the fourth waits longer still
    fail[0] = False
    clock.now += 2400
    s.run_due()
    assert s.status()[0]["failures_in_a_row"] == 0 and s.status()[0]["due_in_seconds"] == 600.0


def test_she_says_once_when_she_starts_easing_off_and_again_only_after_things_cleared():
    readings = {"cpu": 95.0, "memory_free": 50.0, "battery": None, "online": True, "disk_free": 50.0}
    clock, gate = Clock(), Gate()
    h = Homeostasis(SimpleNamespace(communication=gate), read=lambda: dict(readings), clock=clock)
    for _ in range(3):  # three busy readings, 30 seconds apart
        h.refresh()
        clock.now += 30
    assert h.defer_reason("world_intel") and h.defer_reason("good_news") and h.defer_reason("alarms") == ""
    [notice] = gate.said
    assert notice.topic == "homeostasis" and notice.title == "Easing off for now"
    assert "processor at 95%" in notice.message and "World Intelligence's watches" in notice.message
    assert h.report()["deferrals"] == 2 and set(h.report()["waiting"]) == {"world_intel", "good_news"}
    readings["cpu"] = 10.0
    clock.now += 30
    assert h.defer_reason("world_intel") == "" and h.report()["waiting"] == {}
    readings["cpu"] = 99.0
    for _ in range(3):
        clock.now += 30
        h.refresh()
    assert h.defer_reason("night_school")
    assert len(gate.said) == 2  # a new episode, a new notice


def test_a_backoff_notice_says_what_and_how_often():
    gate = Gate()
    h = Homeostasis(SimpleNamespace(communication=gate), read=lambda: {})
    h.backing_off("world_intel", 3, 1200.0, "OSError: feed down")
    [notice] = gate.said
    assert notice.title == "Slowing down World Intelligence's watches"
    assert "failed 3 times in a row (OSError: feed down)" in notice.message and "every 20 minutes" in notice.message
