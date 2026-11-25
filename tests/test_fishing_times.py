"""
tests.test_fishing_times
==========================

"When's the best time to fish?" (core/fishing_times.py): dawn and dusk around the real sunrise and sunset, the moon
overhead and underfoot about twelve and a half hours apart, moonrise and moonset as the minors, the phase said near a
new or full moon, the week's best days, his own log's best time, and a town asked for first; the moon tonight in
words, with the next full and new moon (core/sun_moon.py).
Only one day is the full or new moon, each day's times use that day's offset, and dawn and dusk are kept far north.
"""

from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from core import fishing_times as ft

TZ = ZoneInfo("America/Chicago")
LAT, LON = 39.8, -89.6  # a stand-in town (Springfield, Illinois)


def test_the_days_windows_come_from_the_sun_and_moon():
    """Dawn and dusk, two majors 11 to 14 hours apart, and the minors, in time order."""
    found = ft.windows(LAT, LON, date(2026, 11, 24), TZ)
    kinds = [w["kind"] for w in found]
    assert kinds.count("dawn") == 1 and kinds.count("dusk") == 1 and kinds.count("major") == 2
    assert [w["start"] for w in found] == sorted(w["start"] for w in found)
    dawn = next(w for w in found if w["kind"] == "dawn")
    assert 5 <= dawn["start"].hour <= 7  # sunrise near 6:50 am in late November
    majors = sorted(w["start"] for w in found if w["kind"] == "major")
    assert 10.5 <= (majors[1] - majors[0]).total_seconds() / 3600 <= 13.5
    # a day before full, the moon is highest near midnight and lowest near noon (astral read in UTC)
    over = next(w for w in found if w["what"] == "moon overhead")["start"] + ft.timedelta(hours=1)
    under = next(w for w in found if w["what"] == "moon underfoot")["start"] + ft.timedelta(hours=1)
    assert over.hour <= 1 or over.hour >= 22, over
    assert 10 <= under.hour <= 14, under


def test_the_phase_is_said_by_its_nearest_new_or_full_moon():
    """2026-11-24 is near full (the strong stretch); a week later it isn't."""
    words, strong = ft.phase_word(date(2026, 11, 24))
    assert "full moon" in words and strong
    words, strong = ft.phase_word(date(2026, 12, 1))
    assert not strong


def test_the_answer_for_a_day_and_a_week(monkeypatch):
    """Today's says the phase, dawn and dusk and the honesty line; the week names its best days; his log leads once it
    has three timed catches."""
    from core import catch_log, weather

    monkeypatch.setattr(weather, "place", lambda context: {"name": "Springfield", "lat": LAT, "lon": LON})
    monkeypatch.setattr(catch_log, "catches", lambda context: [{"at": "2026-06-01T06:30:00", "species": "bass"}] * 3)
    said = ft.say(None, "today", date(2026, 11, 24), TZ)
    assert said.startswith("Today in Springfield, with") and "Dawn and dusk:" in said
    assert "Your own log says dawn (5-9)" in said and "mixed evidence" in said
    week = ft.say(None, "this week", date(2026, 11, 24), TZ)
    assert week.startswith("The best days: ") or week.startswith("Nothing stands out from the moon")


def test_without_a_town_its_asked_for(monkeypatch):
    """No town: asked, nothing worked out."""
    from core import weather

    monkeypatch.setattr(weather, "place", lambda context: None)
    assert ft.say(SimpleNamespace(), "today").startswith("I don't know your town yet")



def test_the_moon_tonight_in_words():
    """The full moon of 2026-11-24 (astral's phase 13.8 of its 0-28 scale): said as today, with its rise and set, and
    the next new moon (core/sun_moon.moon_tonight)."""
    from core.sun_moon import moon_tonight

    said = moon_tonight(LAT, LON, date(2026, 11, 24), TZ)
    assert said.startswith("Moon: ") and "full moon" in said and "rises 4:24 pm" in said and "sets 7:07 am" in said
    assert "Full moon today" in said and "next new moon around Wednesday, December 9" in said



def test_only_one_day_is_the_full_or_new_moon_and_the_answer_never_contradicts_itself():
    """The day after a new moon is "1 day past" it, and its next new moon is the month after; the day after the full
    moon isn't a full moon too; the day before a new moon says it's tomorrow."""
    from core.sun_moon import moon_tonight, next_moons

    assert ft.phase_word(date(2026, 11, 25))[0] == "1 day past the full moon"
    after = moon_tonight(LAT, LON, date(2026, 12, 10), TZ)
    assert "1 day past the new moon" in after and "New moon today" not in after
    assert dict(next_moons(date(2026, 12, 10)))["new"].month == 1
    before = dict(next_moons(date(2026, 12, 8)))
    assert ft.phase_word(date(2026, 12, 8))[0] == "1 day before the new moon" and before["new"] == date(2026, 12, 9)


def test_each_days_times_use_that_days_offset_and_the_sun_far_north():
    """A day after the spring clock change gets that day's offset; at 61° N in June dawn and dusk are still there."""
    assert ft._tz(date(2027, 3, 20)).utcoffset(None) is not None
    found = ft.windows(61.2, -149.9, date(2026, 6, 21), TZ)
    assert {"dawn", "dusk"} <= {w["kind"] for w in found}
