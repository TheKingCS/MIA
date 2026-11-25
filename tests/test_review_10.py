"""
tests.test_review_10
======================

The tenth review's findings (2026-11-25), each kept fixed: the pricing lesson never takes his own margin or another
store's markup, the flock lesson never a dog's mites or head lice, the terms lesson never a tax estimate or a
deposit; a real cut list with 30 in legs is his; a rate or "about a day" never cancels the span or the hours; a
two-digit year is the nearer century; a weekly reminder's aside and time come out of its title; "with 2 kids" is a
breakdown; and encouragement is no reminder promise.
"""

from types import SimpleNamespace

from core import assistant_turn
from core import homestead_sums as sums
from core.assistant_plan_actions import _action_cut_list
from core.budget_manager import read_date
from core.claim_check import claims_done
from core.lesson_answer import find


def test_the_lessons_never_take_his_own_numbers_or_someone_elses_question():
    for words in ("how much margin did the shop make", "what's the margin on the shop this month",
                  "what is the margin on my cutting boards", "how much markup does Home Depot charge",
                  "how do i tell if my dog has mites", "how do I get rid of dust mites in my mattress",
                  "what should i do about head lice", "how do i draw up an estimate of my taxes",
                  "how do I tell if the deposit for the job cleared"):
        assert find(words) is None, words
    assert find("What's the markup I should use for my woodworking?") == ("business", "biz_price")
    assert find("How do I know if my chickens have mites?") == ("gardening", "flock_care")


def test_a_real_cut_list_with_thirty_inch_legs_is_his():
    said = _action_cut_list(None, {"parts": "4 legs at 30 in 2x4\n2 sides 11 1/4 x 48 in 3/4 plywood\n"
                                            "1 top 24 x 48 in 3/4 plywood"})
    assert said.startswith("Cut list for")


def test_rates_and_about_never_decide_the_days_and_years_are_the_nearer_century():
    assert sums.days_in("72 hours, about a day of driving") == 3
    assert sums.days_in("we drink a gallon a day, how much water for a week?") == 7
    assert sums.people_in("4 people with 2 kids") == 4 and sums.people_in("for 2 people and 2 kids") == 4
    assert read_date("11/20/99") == "1999-11-20" and read_date("11/20/26") == "2026-11-20"


def test_a_weekly_reminders_aside_and_time_come_out_of_its_title():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "ok"))
    assistant_turn._weekly_reminder_reply(context, "remind me every Monday to check the water filter, or is that too much?")
    assert ran[-1]["title"] == "Check the water filter"
    assistant_turn._weekly_reminder_reply(context, "remind me every Monday to check the filter at 9 tonight")
    assert ran[-1]["title"] == "Check the filter" and ran[-1]["time"] == "21:00"
    assistant_turn._weekly_reminder_reply(context, "remind me every Monday to check the filter at noon")
    assert ran[-1]["time"] == "12:00"


def test_encouragement_is_no_reminder_promise():
    assert not claims_done("I'll always remind you how far you've come.")
    assert claims_done("I'll remind you on Friday.")
