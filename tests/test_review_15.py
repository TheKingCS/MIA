"""
tests.test_review_15
======================

The fifteenth review's fixes (2026-11-25): his upkeep answers with its own asset's line (never the Car's for the
truck) and adds a need only once, never from a remark, a repeat, a date or a non-task; an LED's resistor only for the
plain question, mains a warning; "every night at 2:30" is in the small hours; a function definition he asked for is an
answer; "the Joneses" are the Jones family; a catch of several keeps its "biggest yet" and gives a size to one fish.
"""

from types import SimpleNamespace

from core import assistant_turn

LISTED = ("Maintenance tasks:\n- Oil Change (Car): due in 3 days\n- Oil Change (Truck): due in 40 days")


def _context():
    """His truck and car, both with an oil change, and what a tool would run."""
    ran = []
    book = SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Truck"), SimpleNamespace(name="Car")])
    return ran, SimpleNamespace(maintenance=book, assistant_actions=SimpleNamespace(
        execute=lambda c, n, a: ran.append((n, a)) or (LISTED if n == "list_maintenance_tasks" else "Added it.")))


def test_the_truck_is_answered_with_its_own_line():
    ran, context = _context()
    assert assistant_turn._upkeep_reply(context, "When is my truck due for an oil change?") == \
        "Oil Change (Truck): due in 40 days."


def test_a_need_already_listed_is_never_added_twice():
    ran, context = _context()
    said = assistant_turn._upkeep_reply(context, "the truck needs an oil change")
    assert "Oil Change (Truck)" in said and not any(n == "add_maintenance_task" for n, _ in ran)


def test_a_remark_a_repeat_a_date_or_a_non_task_is_never_a_task():
    ran, context = _context()
    for words in ("my truck is due for an oil change", "the truck needs an oil change every 3 months",
                  "the truck needs brakes next week", "the truck needs new tires soon", "the truck needs nothing",
                  "my truck needs it", "my truck needs work", "the truck needs gas",
                  "the truck needs an oil change how often"):
        assert assistant_turn._upkeep_reply(context, words) is None, words
    assert not any(n == "add_maintenance_task" for n, _ in ran)


def test_an_led_only_for_the_plain_question():
    """Only the plain question is worked out; mains is a warning, and 12 V says to use a 1/2 W resistor."""
    for words in ("what resistor for an LED with a 3.3V forward voltage on 5V",
                  "LED forward voltage 2.2 V, supply 5 V, what resistor?",
                  "I have a 220 ohm resistor and an LED on 5V, how much current will it draw?",
                  "what resistor for 3 LEDs in series on 12 volts", "what resistor for an LED strip on 12V"):
        assert assistant_turn._led_reply(None, words) is None, words
    assert "mains" in assistant_turn._led_reply(None, "resistor for an LED on 120 volts")
    assert "1/2 W" in assistant_turn._led_reply(None, "what resistor for an LED on 12 volts")
    assert "1/2 W" not in assistant_turn._led_reply(None, "what resistor for an LED on 5 volts")


def test_every_night_at_half_two_is_in_the_small_hours():
    added = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: added.append(a) or "ok"))
    assistant_turn._daily_reminder_reply(context, "remind me every night at 2:30 to check the stove")
    assert added[-1].get("time") == "02:30"
    assistant_turn._daily_reminder_reply(context, "remind me every morning at 12:30 to check the stove")
    assert "time" not in added[-1]


def test_a_function_definition_he_asked_for_is_an_answer():
    text = '{"name": "get_weather", "description": "Gets the weather", "parameters": {"type": "object"}}'
    assert not assistant_turn._garbled(text, SimpleNamespace(assistant_actions=SimpleNamespace(_actions={})))


def test_a_catch_of_several_keeps_its_biggest_and_one_size(monkeypatch):
    from core import catch_actions

    logged = []

    def run(c, p):
        """Logs it; the first, with its weight, is his biggest."""
        logged.append(p)
        return ("Logged: a bass. That's your biggest bass yet. 3 fish logged in all." if len(logged) == 1
                else f"Logged: a bass. {len(logged) + 2} fish logged in all.")

    monkeypatch.setitem(catch_actions.ACTION_TYPES, "catch.log", SimpleNamespace(describe=lambda c, p: "", execute=run))
    said = catch_actions._log_tool(None, {"species": "bass", "count": 3, "weight": 5})
    assert [p.get("weight") for p in logged] == [5, None, None]
    assert said == "Logged 3 bass. That's your biggest bass yet. 5 fish logged in all."
