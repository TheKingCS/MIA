"""
tests.test_sweep_9_automation
===============================

The fourth live sweep's fixes (2026-11-25): "remind me every Monday to check the water filter" and "can you automate
a reminder every Monday to ..." go on the calendar as a weekly event in code (no tool had been called, and the
model promised a notification); a promise with words between ("I'll also make sure to send you") is held to the
claim check; the cut-list tool's own example is never taken as his parts; and "what can you automate for me?" is
answered from what she can really run.
"""

from types import SimpleNamespace

from core import assistant_turn
from core.assistant_app_registry_actions import AUTOMATE, _automate
from core.assistant_plan_actions import _action_cut_list
from core.claim_check import claims_done


def test_a_weekly_reminder_goes_on_the_calendar_repeating():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "ok"))
    for words, title in (("Can you automate a reminder every Monday to check the water filter?", "Check the water filter"),
                         ("remind me every Saturday to water the garden", "Water the garden"),
                         ("remind me to take out the trash every thursday at 7pm", "Take out the trash")):
        assert assistant_turn._weekly_reminder_reply(context, words) == "ok", words
        name, args = ran[-1]
        assert name == "add_calendar_event" and args["title"] == title and args["recurrence"] == "weekly"
    assert ran[-1][1]["time"] == "19:00"
    assert assistant_turn._weekly_reminder_reply(context, "remind me to call mom tomorrow") is None


def test_a_promise_with_words_between_is_a_claim():
    assert claims_done("I'll also make sure to send you a notification when it's time to pay your electric bill.")


def test_the_cut_lists_own_example_is_never_his_parts():
    said = _action_cut_list(None, {"parts": "4 legs at 30 in 2x4; 2 sides 11 1/4 x 72 in 3/4 plywood",
                                   "title": "deck job"})
    assert said.startswith("List the parts with their sizes")


def test_what_she_can_automate_is_said_from_what_she_runs():
    said = _automate(SimpleNamespace(), {})
    assert said.startswith(AUTOMATE) and "Right now:" in said
