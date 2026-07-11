"""
tests.test_alarm_tool
========================

Unit test for modules.toolbox.tools.alarm_tool.format_alarm_row — pure
formatting logic, no Qt event loop needed.
"""

from __future__ import annotations

from core.alarm_manager import Alarm
from modules.toolbox.tools.alarm_tool import format_alarm_row


def test_formats_one_time_alarm():
    alarm = Alarm(alarm_id="a1", label="Wake up", time="07:00", days=[])
    assert format_alarm_row(alarm) == "07:00  —  Wake up  [Once]"


def test_formats_every_day_alarm():
    alarm = Alarm(alarm_id="a1", label="Standup", time="08:00", days=[0, 1, 2, 3, 4, 5, 6])
    assert format_alarm_row(alarm) == "08:00  —  Standup  [Every day]"


def test_formats_specific_days_in_order_regardless_of_input_order():
    alarm = Alarm(alarm_id="a1", label="Gym", time="18:00", days=[4, 0, 2])
    assert format_alarm_row(alarm) == "18:00  —  Gym  [Mon, Wed, Fri]"


def test_defaults_label_when_blank():
    alarm = Alarm(alarm_id="a1", label="", time="07:00", days=[])
    assert format_alarm_row(alarm) == "07:00  —  Alarm  [Once]"
