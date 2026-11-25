"""
tests.test_tool_args
======================

A tool's arguments as he could have said them (core/tool_args.py, the Fable audit 2026-11-25): placeholders go,
for a change a time that isn't one, a negative amount and an update's zero go, and a date in words becomes its
YYYY-MM-DD; the tools the audit found saving them now ask instead.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from core.tool_args import a_time, cleaned, is_placeholder


def test_placeholders_go_from_every_call():
    assert cleaned("list_bills", {"question": "null", "name": "N/A"}, changes=False) == {}
    assert is_placeholder("Unknown") and is_placeholder(" null ") and not is_placeholder("Nully's Diner")


def test_a_change_never_keeps_a_bad_time_a_negative_or_an_updates_zero():
    assert cleaned("add_alarm", {"time": "25:99", "label": "x"}) == {"label": "x"}
    assert cleaned("add_alarm", {"time": "6:30 am"}) == {"time": "6:30 am"}
    assert cleaned("record_sale", {"quantity": -1, "amount": "-1"}) == {}
    assert cleaned("update_debt", {"name": "Visa", "balance": 0, "interest_rate": 0}) == {"name": "Visa"}
    assert cleaned("add_debt", {"name": "Visa", "balance": 0}) == {"name": "Visa", "balance": 0}
    assert cleaned("add_expense", {"date": "yesterday"}) == {"date": (date.today() - timedelta(days=1)).isoformat()}
    assert a_time("noon") and a_time("18:00") and not a_time("2026-12-01") and not a_time("13pm")


def test_the_alarm_and_the_receipts_ask_when_neither_is_said():
    from core.assistant_inbox_actions import _action_set_receipt_autofile
    from core.assistant_toolbox_actions import _switch_alarm

    alarm = SimpleNamespace(label="Wake up", alarm_id="a")
    context = SimpleNamespace(alarms=SimpleNamespace(all_alarms=lambda: [alarm]))
    assert _switch_alarm(context, {"label": "wake up"}) == "On or off, for 'Wake up'?"
    assert _action_set_receipt_autofile(SimpleNamespace(), {}).endswith("?")


def test_every_call_goes_through_it():
    from core.assistant_actions import AssistantAction, AssistantActionRegistry

    seen = []
    registry = AssistantActionRegistry()
    registry.register(AssistantAction(name="add_bill", domain="budget", description="d", parameters={},
                                      handler=lambda c, a: seen.append(a) or "ok"))
    registry.execute(SimpleNamespace(), "add_bill", {"name": "null", "amount": 0, "due_date": "N/A"})
    assert seen == [{"amount": 0}]


def test_the_audits_money_sleep_and_calendar_tools_ask_instead_of_saving_nothing():
    """A $0.00 expense, a sale of nothing, a $0.00 payment, an event called "Reminder" and 0 hours of sleep: each asks."""
    from core.assistant_tools import AssistantTools

    saved = []
    budget = SimpleNamespace(add_expense=lambda **k: saved.append(k), add_income=lambda **k: saved.append(k))
    context = SimpleNamespace(budget=budget)
    assert AssistantTools._action_add_expense(context, {"amount": 0}) == "I need an amount to record an expense."
    assert AssistantTools._action_add_income(context, {"amount": "0"}) == "I need an amount to record income."
    calendar = SimpleNamespace(add_event=lambda **k: saved.append(k))
    assert AssistantTools._action_add_calendar_event(SimpleNamespace(calendar=calendar),
                                                     {"title": "Reminder", "date": "2026-12-01"}).endswith("\"the dentist\".")
    assert saved == []
    import pytest

    from core.actions import ActionError
    from core.health_actions import _sleep_log

    with pytest.raises(ActionError):
        _sleep_log(SimpleNamespace(), {})
