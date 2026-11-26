"""
tests.test_vehicle_kit
========================

"What should be in my truck's emergency kit?" (core/ready_kit.say_vehicle, the full sweep 2026-11-26): Ready.gov's car
kit against his inventory, never the house's 72-hour bag.
"""

from types import SimpleNamespace

from core import assistant_turn, ready_kit


def test_the_car_kit_against_his_records():
    inventory = SimpleNamespace(all_items=lambda: [SimpleNamespace(name="Jumper Cables"),
                                                   SimpleNamespace(name="LED Flashlight")])
    said = ready_kit.say_vehicle(SimpleNamespace(inventory=inventory))
    assert said.startswith("Ready.gov's kit for a vehicle has 10 things; your records hold 2.")
    assert "jumper cables (or a jump starter) (Jumper Cables)" in said
    assert "Not in your records: a first aid kit" in said


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(ready_kit, "say_vehicle", lambda c: "car kit")
    for words in ("What should be in my truck's emergency kit?", "what should I keep in my car for emergencies",
                  "check my truck kit"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "car kit", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "check my emergency kit") != "car kit"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what lift kit for my truck should I get") != "car kit"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what winter kit for my car should I have?") == "car kit"
