"""
tests.test_review_7
=====================

The seventh review's findings (2026-11-25), each kept fixed: the claim check leaves alone a sentence about anything but
his records, a story, and a lookup's "your alarm is set"; a date his words state is never replaced by a weekday, a
weekday after "on" or "for" beats one in a title, "next Friday" is next week's, and "tonight at 9" is 9 pm; the
calendar's "this week", "next week" and "next Friday" are those days; the sums take a total over its breakdown, hours
only without days, and a month's eggs as a week's share.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, homestead_sums as sums
from core.calendar_move import _range
from core.claim_check import HONEST, honest

WED = date(2026, 11, 25)


def test_the_claim_check_leaves_alone_what_isnt_a_claim_about_his_records():
    for prompt, text in (("explain it", "In my example, I set the temperature to 350."),
                         ("make me a story", "I set sail at dawn, says the captain."),
                         ("what alarms do I have?", "Your alarm is set for 6:30 tomorrow."),
                         ("how are you?", "I changed my mind about the weather: it's lovely.")):
        assert honest(None, prompt, text) == text, text
    assert honest(None, "Remind me to check the oil Saturday", "You've been reminded to check the oil.") == HONEST


def test_a_claim_in_a_private_turn_is_never_logged():
    logged = []
    context = SimpleNamespace(failures=SimpleNamespace(record=lambda kind, **f: logged.append(kind)))
    honest(context, "remind me to call mom", "I've added a reminder.", keep=False)
    assert logged == []


def test_the_day_his_words_name():
    for words, day in (("add dinner on December 24 - it's a Thursday", None), ("add a call on 12/04, that's a Friday", None),
                       ("add the vet next week on the 3rd", None), ("add the dentist next Friday", date(2026, 12, 4)),
                       ("put Tuesday trivia night on my calendar for Thursday", date(2026, 11, 26)),
                       ("remind me to prep for the monday meeting on friday", date(2026, 11, 27))):
        assert assistant_turn.named_day(words, WED) == day, words
    assert assistant_turn.with_his_day("add_calendar_event", {"date": "2026-12-24"},
                                       "add dinner on December 24 - it's a Thursday", WED) == {"date": "2026-12-24"}


def test_tonight_at_nine_is_nine_pm():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "added"))
    assistant_turn._reminder_reply(context, "remind me to take meds tonight at 9")
    assert ran[0]["time"] == "21:00"


def test_the_calendars_ranges():
    assert _range("anything next week?", WED)[0] == date(2026, 11, 30) and len(_range("next week", WED)) == 7
    assert _range("going on this week", WED)[-1] == date(2026, 11, 29)
    assert _range("anything on my calendar next friday?", WED) == [date(2026, 12, 4)]


def test_the_sums_take_a_total_hours_only_without_days_and_a_months_eggs():
    assert sums.people_in("water for 4 people, 2 adults and 2 kids") == 4
    assert sums.people_in("family of 4 with 1 child under 5") == 4
    assert sums.days_in("one person staying 12 hours for 3 days") == 3
    assert round(sums.eggs_wanted("2 dozen eggs a month"), 1) == 5.5
