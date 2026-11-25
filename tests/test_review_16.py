"""
tests.test_review_16
======================

The sixteenth review's fixes (2026-11-25): a part or a mileage is a real need ("a new fuel filter", "4 new tires");
a need is already listed only as the same task ("a new battery" is never the Battery check); an LED's resistor is
rated twice its heat, a 5 V wall adapter is no mains, and a current or several LEDs said are the model's; a made-up
call whose arguments carry a description is still caught.
"""

from types import SimpleNamespace

from core import assistant_turn

LISTED = ("Maintenance tasks:\n- Battery check (Truck): due in 3 days\n- Oil Change (Truck): due in 40 days\n"
          "- Air filter (Truck): due in 9 days")


def _context():
    """His truck with three tasks, and what a tool would run."""
    ran = []
    book = SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Truck"), SimpleNamespace(name="Generator")])
    return ran, SimpleNamespace(maintenance=book, assistant_actions=SimpleNamespace(
        execute=lambda c, n, a: ran.append((n, a)) or (LISTED if n == "list_maintenance_tasks" else "Added it.")))


def test_a_part_or_a_mileage_is_a_real_need():
    for words in ("the truck needs a new fuel filter", "the generator needs a new gas cap", "the truck needs body work",
                  "the truck needs 4 new tires", "the truck needs its 30,000 mile service",
                  "the truck needs a new battery", "the truck needs a new filter"):
        ran, context = _context()
        assert assistant_turn._upkeep_reply(context, words) == "Added it.", words
    ran, context = _context()
    assert assistant_turn._upkeep_reply(context, "the truck needs gas") is None
    assert "already on your list" in assistant_turn._upkeep_reply(context, "the truck needs an oil change")


def test_an_leds_resistor_is_rated_for_its_heat():
    assert "2 W resistor" in assistant_turn._led_reply(None, "what resistor for an LED on 48 volts")
    for words in ("what resistor do I need for an LED on a 5V wall adapter", "resistor for an LED on 12V from a USB outlet"):
        assert "ohm" in assistant_turn._led_reply(None, words), words
    for words in ("what resistor for an LED on 5 volts at 10 mA", "what resistor for an LED on 5 volts at 10 milliamps",
                  "what resistor for two LEDs on 5V"):
        assert assistant_turn._led_reply(None, words) is None, words


def test_a_made_up_call_with_a_description_argument_is_still_caught():
    context = SimpleNamespace(assistant_actions=SimpleNamespace(_actions={}))
    assert assistant_turn._garbled('{"name": "create_reminder", "arguments": {"title": "Call mom", "description": '
                                   '"call her at 5"}}', context)
    assert not assistant_turn._garbled('{"name": "get_weather", "description": "Gets it", "parameters": {}}', context)
