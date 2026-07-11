"""
tests.test_alarm_manager
===========================

Unit tests for core.alarm_manager. Isolates _DATA_DIR/_ALARMS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_calendar_manager.py's isolated_paths). check_due() takes `now`
as a plain datetime rather than reading the real clock, so firing
behavior is tested with fixed timestamps — no waiting, no real QTimer.

context.notifications is replaced with a small fake that just records
calls, rather than wiring up (and isolating the file paths of) a real
NotificationManager — these tests only care that AlarmManager calls
notify() with the right arguments, not how NotificationManager itself
stores or displays it.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import core.alarm_manager as alarm_manager_module
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus


class _FakeNotifications:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def notify(self, title: str, message: str, level: str = "info", source: str = "system") -> None:
        self.calls.append({"title": title, "message": message, "level": level, "source": source})


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    alarms_file = data_dir / "alarms.json"
    monkeypatch.setattr(alarm_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(alarm_manager_module, "_ALARMS_FILE", alarms_file)
    return data_dir, alarms_file


def _make_manager() -> tuple[AlarmManager, _FakeNotifications]:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = _FakeNotifications()
    return AlarmManager(context), context.notifications


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager, _ = _make_manager()
    assert manager.all_alarms() == []


def test_add_alarm_persists_across_a_fresh_load(isolated_paths):
    manager, _ = _make_manager()
    added = manager.add_alarm(label="Wake up", time="07:00", days=[0, 2, 4])

    reloaded, _ = _make_manager()
    alarms = reloaded.all_alarms()
    assert len(alarms) == 1
    assert alarms[0].alarm_id == added.alarm_id
    assert alarms[0].label == "Wake up"
    assert alarms[0].time == "07:00"
    assert alarms[0].days == [0, 2, 4]
    assert alarms[0].enabled is True


def test_update_alarm_unknown_id_raises(isolated_paths):
    manager, _ = _make_manager()
    with pytest.raises(ValueError):
        manager.update_alarm("does-not-exist", label="X")


def test_update_alarm_unknown_field_raises(isolated_paths):
    manager, _ = _make_manager()
    alarm = manager.add_alarm(label="X", time="07:00")
    with pytest.raises(ValueError):
        manager.update_alarm(alarm.alarm_id, bogus_field="X")


def test_delete_alarm_removes_it_and_is_idempotent(isolated_paths):
    manager, _ = _make_manager()
    alarm = manager.add_alarm(label="Gone soon", time="07:00")

    manager.delete_alarm(alarm.alarm_id)
    assert manager.get_alarm(alarm.alarm_id) is None

    manager.delete_alarm(alarm.alarm_id)  # already gone — must not raise


def test_get_alarm_returns_none_for_unknown_id(isolated_paths):
    manager, _ = _make_manager()
    assert manager.get_alarm("does-not-exist") is None


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, alarms_file = isolated_paths
    data_dir.mkdir(parents=True)
    alarms_file.write_text("{not valid json", encoding="utf-8")

    manager, _ = _make_manager()
    assert manager.all_alarms() == []


def test_check_due_fires_matching_one_time_alarm_and_auto_disables(isolated_paths):
    manager, notifications = _make_manager()
    manager.add_alarm(label="Wake up", time="07:00")  # no days => one-time

    now = datetime(2026, 7, 13, 7, 0)
    fired = manager.check_due(now)

    assert len(fired) == 1
    assert fired[0].label == "Wake up"
    assert fired[0].enabled is False
    assert len(notifications.calls) == 1
    assert notifications.calls[0]["title"] == "Alarm: Wake up"
    assert notifications.calls[0]["level"] == "warning"


def test_check_due_ignores_disabled_alarms(isolated_paths):
    manager, notifications = _make_manager()
    alarm = manager.add_alarm(label="Wake up", time="07:00")
    manager.update_alarm(alarm.alarm_id, enabled=False)

    fired = manager.check_due(datetime(2026, 7, 13, 7, 0))

    assert fired == []
    assert notifications.calls == []


def test_check_due_does_not_refire_within_the_same_day(isolated_paths):
    manager, notifications = _make_manager()
    manager.add_alarm(label="Standup", time="08:00", days=[0, 1, 2, 3, 4])
    now = datetime(2026, 7, 13, 8, 0)  # a Monday
    assert now.weekday() == 0

    first = manager.check_due(now)
    second = manager.check_due(now)

    assert len(first) == 1
    assert second == []
    assert len(notifications.calls) == 1


def test_check_due_respects_repeat_days(isolated_paths):
    manager, notifications = _make_manager()
    now = datetime(2026, 7, 13, 8, 0)
    tomorrow = now + timedelta(days=1)
    manager.add_alarm(label="Standup", time="08:00", days=[now.weekday()])

    fired_wrong_day = manager.check_due(tomorrow)
    assert fired_wrong_day == []
    assert notifications.calls == []

    fired_right_day = manager.check_due(now)
    assert len(fired_right_day) == 1
    assert fired_right_day[0].enabled is True  # repeating alarms stay enabled


def test_check_due_repeating_alarm_fires_again_on_the_next_matching_day(isolated_paths):
    manager, notifications = _make_manager()
    now = datetime(2026, 7, 13, 8, 0)
    manager.add_alarm(label="Standup", time="08:00", days=[now.weekday()])

    manager.check_due(now)
    fired_next_week = manager.check_due(now + timedelta(days=7))

    assert len(fired_next_week) == 1
    assert len(notifications.calls) == 2
