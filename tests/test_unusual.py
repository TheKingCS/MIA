"""
tests.test_unusual
====================

Noticing what's unusual (core/unusual.py, brainstorm 2.3): the hens' laying against their own normal, judged only
on days he logged before today (today's count is still coming in), said once a week through the gate with the
causes worth checking.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from core import unusual


def _log(per_day: dict, flock="f1", birds_on=None):
    out = [SimpleNamespace(flock_id=flock, kind="eggs", date=d.isoformat(), count=n) for d, n in per_day.items()]
    if birds_on:
        out.append(SimpleNamespace(flock_id=flock, kind="birds", date=birds_on.isoformat(), count=-1))
    return out


TODAY = date(2026, 11, 23)


def _days(values_oldest_first):
    """Egg counts by day, oldest first, ending yesterday (None: a day not logged)."""
    start = TODAY - timedelta(days=len(values_oldest_first))
    return {start + timedelta(days=i): v for i, v in enumerate(values_oldest_first) if v is not None}


def test_a_real_fall_in_laying_is_found():
    found = unusual.egg_drop(_log(_days([6] * 14 + [2, 3, 2])), "f1", TODAY)
    assert found == {"recent": 2.3, "usual": 6.0, "fall": 0.61, "birds_changed": False}


def test_an_ordinary_dip_is_not():
    assert unusual.egg_drop(_log(_days([6] * 14 + [5, 4, 5])), "f1", TODAY) is None


def test_days_he_did_not_log_are_not_days_of_zero_eggs():
    # he didn't log the last two days but today: read as zeros, that would be a fall of two thirds
    assert unusual.egg_drop(_log(_days([6] * 14 + [None, None, 6])), "f1", TODAY) is None


def test_too_little_history_or_an_old_log_says_nothing():
    assert unusual.egg_drop(_log(_days([6, 6, 6, 1, 1, 1])), "f1", TODAY) is None  # under five usual days
    stale = _days([6] * 14 + [1, 1, 1])
    old = {d - timedelta(days=10): n for d, n in stale.items()}
    assert unusual.egg_drop(_log(old), "f1", TODAY) is None  # the low days aren't recent


def test_a_bird_lost_lately_is_named_first():
    found = unusual.egg_drop(_log(_days([6] * 14 + [2, 2, 2]), birds_on=TODAY - timedelta(days=4)), "f1", TODAY)
    assert found["birds_changed"] is True
    said = unusual._egg_words("The girls", found)
    assert said.index("birds lost or added") < said.index("shorter days")


def test_it_is_said_once_a_week_through_the_gate():
    book = SimpleNamespace(flocks=[SimpleNamespace(flock_id="f1", name="The girls", hens=6, roosters=0)],
                           entries=_log(_days([6] * 14 + [2, 3, 2])))
    ctx = SimpleNamespace(flock=book)
    [said] = unusual.offer(ctx, datetime(2026, 11, 23, 8))
    assert said.topic == "unusual" and said.urgency == "ambient" and said.title == "The girls: fewer eggs"
    assert said.fingerprint == "eggs-f1-2026-W48"
    assert "6 eggs a day" not in said.message and "usual 6" in said.message


def test_a_flock_with_no_hens_or_no_flock_says_nothing():
    assert unusual.findings(SimpleNamespace(flock=None), TODAY) == []
    book = SimpleNamespace(flocks=[SimpleNamespace(flock_id="f1", name="Roos", hens=0, roosters=2)], entries=[])
    assert unusual.findings(SimpleNamespace(flock=book), TODAY) == []
    assert "Nothing in your records" in unusual.say(SimpleNamespace(flock=None))


def test_todays_unfinished_count_never_makes_a_drop():
    log = _days([6] * 17)
    log[TODAY] = 1  # a morning's first log
    assert unusual.egg_drop(_log(log), "f1", TODAY) is None
