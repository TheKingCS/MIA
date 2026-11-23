"""
tests.test_feed_runway
========================

How long the hens' feed will last (core/feed_runway.py): from the last bag, at his flock's own rate once two weeks of
purchases show it (the last 90 days, after the flock last changed, never under half the usual), else the usual
quarter pound a hen a day; said when it's down to a few days, once a bag; a bag without pounds is unknown.
"""

from datetime import date
from types import SimpleNamespace

from core import feed_runway as fr

TODAY = date(2026, 11, 23)
FLOCK = SimpleNamespace(flock_id="f1", name="The girls", hens=8, roosters=0)


def _feed(day, lb):
    return SimpleNamespace(flock_id="f1", kind="feed", date=day, pounds=lb)


def test_one_bag_uses_the_quarter_pound_rule():
    found = fr.runway([_feed("2026-11-13", 50)], FLOCK, TODAY)
    # 8 hens x 0.25 = 2 lb a day; 10 days gone: 30 lb left, 15 days
    assert found["rate"] == 2 and found["left_lb"] == 30 and found["days_left"] == 15 and not found["from_history"]
    assert "quarter pound a hen a day" in fr.words("The girls", found)


def test_his_own_rate_once_two_weeks_of_purchases_show_it():
    entries = [_feed("2026-10-01", 50), _feed("2026-10-26", 50), _feed("2026-11-20", 50)]
    found = fr.runway(entries, FLOCK, TODAY)
    # 100 lb lasted the 50 days from Oct 1 to Nov 20: 2 lb a day, so 44 lb left, 22 days
    assert found["from_history"] and found["rate"] == 2 and found["days_left"] == 22
    assert "your flock has been going through" in fr.words("The girls", found)


def test_running_low_is_said_once_a_bag_and_run_out_says_so():
    book = SimpleNamespace(flocks=[FLOCK], entries=[_feed("2026-11-02", 50)])
    [low] = fr.soon(SimpleNamespace(flock=book), TODAY)
    assert low["key"] == "feed-f1-2026-11-02" and "runs out around" in low["text"]
    book.entries = [_feed("2026-10-01", 20)]
    assert "has likely run out" in fr.soon(SimpleNamespace(flock=book), TODAY)[0]["text"]


def test_no_feed_logged_or_no_birds_says_nothing():
    assert fr.runway([], FLOCK, TODAY) is None
    assert fr.runway([_feed("2026-11-13", 50)], SimpleNamespace(flock_id="f1", hens=0, roosters=0), TODAY) is None


def test_a_bag_logged_without_pounds_makes_it_unknown_never_a_stale_figure():
    entries = [_feed("2026-10-01", 50), _feed("2026-10-21", 50), _feed("2026-11-22", 0)]
    found = fr.runway(entries, FLOCK, TODAY)
    assert found["unknown"] and "without its pounds" in fr.words("The girls", found)
    assert fr.soon(SimpleNamespace(flock=SimpleNamespace(flocks=[FLOCK], entries=entries)), TODAY) == []


def test_bags_bought_the_same_day_are_one_purchase():
    entries = [_feed("2026-10-01", 50), _feed("2026-11-01", 50), _feed("2026-11-01", 50)]
    found = fr.runway(entries, FLOCK, TODAY)
    # 50 lb lasted Oct 1 to Nov 1 (31 days, 1.61 lb a day, under half of 2 lb is 1: so 1.61); 100 lb bought Nov 1
    assert found["rate"] == 1.61 and found["left_lb"] == round(100 - 50 / 31 * 22, 1)


def test_his_rate_starts_after_the_flock_changed_and_never_falls_under_half_the_usual():
    grown = SimpleNamespace(flock_id="f1", name="The girls", hens=20, roosters=0)
    entries = [_feed("2026-09-01", 50), _feed("2026-10-01", 50),
               SimpleNamespace(flock_id="f1", kind="birds", date="2026-10-15", pounds=0), _feed("2026-11-20", 50)]
    found = fr.runway(entries, grown, TODAY)
    assert not found["from_history"] and found["rate"] == 5  # 20 hens: the usual, not the old small flock's
    old = [_feed("2025-11-20", 50), _feed("2026-11-20", 50)]
    assert fr.runway(old, FLOCK, TODAY)["rate"] == 2  # a year apart is outside the window: the usual
