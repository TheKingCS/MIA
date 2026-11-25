"""
tests.test_sweep_11
=====================

The fifth live sweep's fixes (2026-11-25, hobbies and the truck): "I caught 3 bass" logs three catches; "when is my
truck due for an oil change?" is that task's line from his own maintenance, and "the truck needs new brakes" adds the
task, only for an asset of his (never "the garden needs water"); "what resistor for an LED on 5 volts?" is worked out
in code.
"""

from types import SimpleNamespace

from core import assistant_turn
from core.catch_actions import _log_tool


def _context(listed=""):
    """His truck among his assets, and what a tool would run."""
    ran = []
    book = SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Truck")])
    return ran, SimpleNamespace(maintenance=book, assistant_actions=SimpleNamespace(
        execute=lambda c, n, a: ran.append((n, a)) or (listed if n == "list_maintenance_tasks" else "Added it.")))


def test_when_a_task_is_due_is_his_own_line():
    ran, context = _context("Maintenance tasks:\n- Renew Tags (Truck): due in 37 days\n- Oil Change (Truck): no readings logged")
    said = assistant_turn._upkeep_reply(context, "When is my truck due for an oil change?")
    assert said.startswith("Oil Change (Truck): no readings logged.") and "Log its reading" in said
    assert assistant_turn._upkeep_reply(context, "When is my truck due for tags?") == "Renew Tags (Truck): due in 37 days."


def test_a_need_is_a_task_only_for_an_asset_of_his():
    ran, context = _context()
    assert assistant_turn._upkeep_reply(context, "The truck needs new brakes") == "Added it."
    assert ran[-1] == ("add_maintenance_task", {"asset_name": "truck", "title": "Brakes"})
    for words in ("the garden needs water", "the truck needs to be washed", "my dog needs a bath"):
        assert assistant_turn._upkeep_reply(context, words) is None, words


def test_an_leds_resistor_is_worked_out():
    said = assistant_turn._led_reply(None, "What resistor do I need for an LED on 5 volts?")
    assert "150 ohm" in said and ".;" not in said
    assert assistant_turn._led_reply(None, "what's an LED?") is None


def test_three_bass_are_three_catches(monkeypatch):
    from core import catch_actions

    logged = []
    action = SimpleNamespace(describe=lambda c, p: "", execute=lambda c, p: logged.append(p) or "Logged: a bass. 3 fish "
                             "logged in all.")
    monkeypatch.setitem(catch_actions.ACTION_TYPES, "catch.log", action)
    said = _log_tool(None, {"species": " largemouth bass", "count": 3, "where": "the pond"})
    assert len(logged) == 3 and said == "Logged 3 largemouth bass at the pond. 3 fish logged in all."
