"""
tests.test_rain_gauge
=======================

His rain gauge (core/weather_watch.py `rain_inches`, `rain_this_week`, tool log_rain): rainfall read as he says it
(inches, fractions, "a quarter of an inch", millimeters, a bare number), kept in the data logger in inches, the last seven days added up, and the
watering answer led by the week's real rain against the inch a week the garden wants.
"""

from datetime import date
from types import SimpleNamespace

from core import weather_watch as ww


def test_rain_is_read_as_he_says_it():
    """Inches, words, fractions written out, millimeters and centimeters, and a bare number alone."""
    assert ww.rain_inches("0.6 inches") == 0.6 and ww.rain_inches("half an inch") == 0.5
    assert ww.rain_inches("25.4 mm") == 1.0 and ww.rain_inches("an inch and a half") == 1.5
    assert ww.rain_inches("a lot") is None
    for said, inches in (("6/10 of an inch", 0.6), ("a tenth of an inch", 0.1), ("a quarter of an inch", 0.25),
                         ("three quarters of an inch", 0.75), ("an inch and a quarter", 1.25), ("1 1/2 inches", 1.5),
                         ("1/2 inch", 0.5), ("gauge says .3", 0.3), ("3 cm", 1.18)):
        assert ww.rain_inches(said) == inches, said


class _Logger:
    """The data logger, as much as the rain gauge uses of it."""

    def __init__(self, readings):
        """These readings, (day, inches)."""
        self.readings = [SimpleNamespace(series_id=ww.RAIN_SERIES, value=v, timestamp=f"{d}T07:00:00")
                         for d, v in readings]

    def readings_for(self, series_id):
        """The readings of one series."""
        return [r for r in self.readings if r.series_id == series_id]


def test_the_week_is_the_last_seven_days():
    ctx = SimpleNamespace(data_logger=_Logger([("2026-11-10", 2.0), ("2026-11-18", 0.5), ("2026-11-24", 0.25)]))
    assert ww.rain_this_week(ctx, date(2026, 11, 24)) == 0.75
    assert ww.rain_this_week(SimpleNamespace(data_logger=_Logger([])), date(2026, 11, 24)) is None
