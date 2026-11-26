"""
tests.test_outage_plan
========================

Ready for the power going out (core/outage_plan.py, 2026-11-25): the first things to do in fixed words, then his own readiness from his
records, then the drill; never his power bill, a solar panel or a power tool.
"""

from core import outage_plan as outage


def test_the_power_out_gets_the_first_things_and_his_stores(monkeypatch):
    from core import preparedness

    monkeypatch.setattr(preparedness, "say", lambda c: "Water: 5 days.")
    for words in ("What do I do if the power goes out for a week?", "if we lose power for a few days what should I do",
                  "how do I prepare for a power outage?", "what should we do if the grid goes down"):
        said = outage.reply(None, words)
        assert said.startswith("Keep the fridge and freezer shut") and "From your records: Water: 5 days." in said, words
        assert "never in the garage or the house" in said


def test_the_power_bill_or_a_power_tool_is_never_an_outage():
    for words in ("why is my power bill so high", "what power tools do I need", "the solar panels lost power output",
                  "the power steering is out on the truck", "I went out to buy a power drill"):
        assert outage.reply(None, words) is None, words


def test_the_power_going_out_now_is_the_clocks():
    """"The power went out" is the outage clock's (core/outage.py), never this answer."""
    for words in ("the power is out", "we lost power", "the power went out at 6", "power's back"):
        assert outage.reply(None, words) is None, words
