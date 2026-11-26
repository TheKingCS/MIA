"""
tests.test_reshaped
=====================

A sentence put in the shape her routes read (core/assistant_turn.reshaped, the cross-route review 2026-11-26): a
greeting before a question set aside, a weekday first or a part of the day read as "remind me every X to ... at".
"""

from types import SimpleNamespace

from core import assistant_turn, motivation


def test_the_shapes():
    r = assistant_turn.reshaped
    assert r("Good morning, what's my week look like?") == "what's my week look like?"
    assert r("Good morning") == "Good morning"
    assert r("Every Monday remind me to take out the trash") == "Remind me every Monday to take out the trash"
    assert r("remind me every Saturday morning to collect eggs") == "Remind me every Saturday to collect eggs at 8am"
    assert r("every Sunday evening remind me to plan the week") == "Remind me every Sunday to plan the week at 6pm"
    assert r("remind me every Friday evening to check the oil at 5pm") == "Remind me every Friday to check the oil at 5pm"


def test_motivation_for_a_task(monkeypatch):
    from core import project_time, today

    monkeypatch.setattr(today, "today_items", lambda c, t=None: [])
    shed = SimpleNamespace(name="Shed", time_log=[{"date": "2026-11-20", "hours": 6}])
    monkeypatch.setattr(project_time, "project_named", lambda c, w, whole=False: shed)
    said = motivation.say(SimpleNamespace(), task="finish the shed")
    assert "For the shed: pick the smallest piece you can finish in twenty minutes" in said
    assert "You've put 6 hours into Shed so far." in said
    monkeypatch.setattr(motivation, "say", lambda c, t=None, task="": f"task={task}")
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "I need motivation to finish the shed") == \
        "task=finish the shed"
