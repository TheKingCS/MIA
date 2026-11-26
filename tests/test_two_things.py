"""
tests.test_two_things
=======================

Two things in one sentence (core/assistant_turn._two_things_reply, brainstorm round 18): "I spent $40 on screws and 2
hours on the shed" logs both, each through its own code, and says them together; one never swallows the other.
"""

from types import SimpleNamespace

from core import assistant_turn, project_time


def _context(monkeypatch, done):
    """A context whose actions record what ran, with one project (the Shed)."""
    shed = SimpleNamespace(name="Shed", time_log=[])
    monkeypatch.setattr(project_time, "project_named",
                        lambda c, w, whole=False: shed if "shed" in w.lower() else None)
    actions = SimpleNamespace(execute=lambda c, name, args: done.append((name, args)) or f"[{name} {args}]")
    return SimpleNamespace(assistant_actions=actions, flock=None, budget=None)


def test_money_and_hours_are_both_logged(monkeypatch):
    done = []
    said = assistant_turn._two_things_reply(_context(monkeypatch, done),
                                            "I spent $40 on screws and 2 hours on the shed yesterday")
    names = [n for n, _a in done]
    assert names == ["add_expense", "log_project_time"], done
    assert done[0][1]["amount"] == 40.0 and done[1][1]["hours"] == 2 and done[1][1].get("date")
    assert said.count("[") == 2


def test_two_amounts_split(monkeypatch):
    done = []
    assistant_turn._two_things_reply(_context(monkeypatch, done), "I paid $5 for coffee and $10 for gas")
    assert [a["amount"] for _n, a in done] == [5.0, 10.0]


def test_one_kind_never_swallows_the_other(monkeypatch):
    done = []
    context = _context(monkeypatch, done)
    monkeypatch.setattr(assistant_turn, "_assets", lambda c: [])
    assistant_turn._two_things_reply(context, "I spent $40 on screws and 2 hours on the porch")
    assert [n for n, _a in done] == ["add_expense", "log_project_time"] and done[1][1]["project"] == "the porch"
    done.clear()
    assert assistant_turn._spent_reply(context, "I spent $40 on screws and 2 hours on the porch") is None
    assert assistant_turn._project_time_reply(context, "I spent 2 hours on the shed and $40 on screws") is None
    assert assistant_turn._two_things_reply(context, "I spent $40 on nuts and bolts") is None
    assert done == []
