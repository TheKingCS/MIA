"""
tests.test_upkeep_partial
===========================

"The mower needs new blades" is a task on his Riding Mower (core/assistant_turn._upkeep_reply, the vehicle
conversation check 2026-11-26: it went to the inventory and was refused), only when one asset has those words;
and "what has the truck cost me?" is that machine's costs.
"""

from types import SimpleNamespace

from core import assistant_turn


def test_a_partial_name_finds_the_one_asset(monkeypatch):
    ran = []
    monkeypatch.setattr(assistant_turn, "_assets", lambda c: ["riding mower", "truck"])
    monkeypatch.setattr(assistant_turn, "_task_line", lambda c, a, t, same=False: None)
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "Added."))
    assert assistant_turn._upkeep_reply(context, "the mower needs new blades") == "Added."
    assert ran == [("add_maintenance_task", {"asset_name": "riding mower", "title": "Blades"})]
    monkeypatch.setattr(assistant_turn, "_assets", lambda c: ["riding mower", "push mower"])
    assert assistant_turn._upkeep_reply(context, "the mower needs new blades") is None


def test_what_a_machine_has_cost(monkeypatch):
    from core import project_time

    monkeypatch.setattr(assistant_turn, "_assets", lambda c: ["truck", "riding mower"])
    monkeypatch.setattr(project_time, "project_named", lambda c, w, whole=False: None)
    monkeypatch.setattr(assistant_turn, "_run_own", lambda c, n, a: f"{n}[{a['tool']}]")
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what has the truck cost me?") == "get_tool_costs[truck]"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what has the mower cost me so far?") == \
        "get_tool_costs[riding mower]"
