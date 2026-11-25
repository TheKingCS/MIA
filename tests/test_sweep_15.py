"""
tests.test_sweep_15
=====================

The ninth live sweep's fixes (2026-11-25): "remind me to change the furnace filter every month" is a monthly event on
his calendar (never a bill, never a task for a furnace he hasn't listed); a bill is never added with no amount, no
real day or no name ("Can you automate my bill reminders?" had added a $0.00 bill due "null"); automating his bills
is answered by what already watches them.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn


def _recorder():
    """A context whose tools record what they'd run."""
    ran = []
    return ran, SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "ok"))


def test_a_monthly_reminder_goes_on_the_calendar():
    ran, context = _recorder()
    assert assistant_turn._monthly_reminder_reply(context, "Remind me to change the furnace filter every month") == "ok"
    assert ran[-1] == ("add_calendar_event", {"title": "Change the furnace filter", "date": date.today().isoformat(),
                                              "recurrence": "monthly"})
    assistant_turn._monthly_reminder_reply(context, "remind me to check the smoke alarms every month on the 1st")
    assert date.fromisoformat(ran[-1][1]["date"]).day == 1
    for words in ("remind me to pay the electric bill every month", "remind me every Monday to check the filter",
                  "remind me to call mom"):
        assert assistant_turn._monthly_reminder_reply(context, words) is None, words


def test_a_bill_is_never_added_from_nothing():
    from core.assistant_tools import AssistantTools

    added = []
    context = SimpleNamespace(budget=SimpleNamespace(add_bill=lambda **k: added.append(k)))
    for arguments in ({"name": "bill reminders", "amount": 0, "due_date": "null"},
                      {"name": "Electric", "amount": 120, "due_date": "null"},
                      {"name": "bill reminders", "amount": 50, "due_date": "2026-12-15"}):
        assert AssistantTools._action_add_bill(context, arguments).endswith(("?", ".", "\"")), arguments
    assert added == []


def test_automating_his_bills_says_what_already_watches_them():
    from core.assistant_app_registry_actions import AUTOMATE

    assert "Bills you've added are watched every day" in AUTOMATE
