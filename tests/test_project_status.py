"""
tests.test_project_status
===========================

"How's the shed coming along?" (core/project_status.py, brainstorm round 19): one project's picture from his records,
said in code, only for a project of his; and its whole cost (its money and his hours).
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, project_status


def test_status_due_tasks_and_hours():
    shed = SimpleNamespace(project_id="p1", name="Shed", status="Active", due_date="2026-12-06",
                           time_log=[{"date": "2026-11-20", "hours": 4}, {"date": "2026-11-24", "hours": 2.5}])
    tasks = SimpleNamespace(tasks_for_project=lambda pid: [SimpleNamespace(title="Frame walls", done=True, due_date=""),
                                                          SimpleNamespace(title="Roof", done=False, due_date="")])
    said = project_status.say(SimpleNamespace(tasks=tasks), shed, date(2026, 11, 26))
    assert said.startswith("Shed is active, due December 6 (10 days left).")
    assert "Tasks: 1 of 2 done; next up, Roof." in said
    assert "You've put 6.5 hours into it, last on November 24." in said
    needs = SimpleNamespace(for_project=lambda pid: [SimpleNamespace(quantity=3, have=0, unit="bundles",
                                                                     item="shingles", status="needed")])
    done = SimpleNamespace(project_id="p1", name="Shed", status="Complete", due_date="", time_log=[{"hours": 1}])
    said = project_status.say(SimpleNamespace(tasks=tasks, requirements=needs), done, date(2026, 11, 26))
    assert "next up" not in said and "1 hour into it" in said and "It still needs 3 bundles shingles." in said


def test_past_due_and_the_words_reach_it(monkeypatch):
    late = SimpleNamespace(project_id="p2", name="Garage Rewire", status="Active", due_date="2026-08-14", time_log=[])
    said = project_status.say(SimpleNamespace(), late, date(2026, 11, 26))
    assert "104 days past its due date (August 14)" in said and "No hours logged" in said
    from core import project_time

    monkeypatch.setattr(project_time, "project_named",
                        lambda c, w, whole=False: late if whole and "rewire" in w else None)
    monkeypatch.setattr(project_status, "say", lambda c, p, t=None: f"picture of {p.name}")
    for words in ("How's the garage rewire coming along?", "where am I on the garage rewire?",
                  "status of the garage rewire project"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "picture of Garage Rewire", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "how's the weather looking?") != "picture of Garage Rewire"


def test_the_whole_cost_is_its_money_and_his_hours_at_his_rate(monkeypatch):
    from core import homestead_costs

    shed = SimpleNamespace(project_id="p1", name="Shed", status="Active", budget=0.0, time_log=[{"hours": 10}])
    monkeypatch.setattr(homestead_costs, "build_cost", lambda c, p: SimpleNamespace(expense_count=2))
    monkeypatch.setattr(homestead_costs, "describe_build", lambda cost: "You've spent $400.00 on Shed.")
    config = SimpleNamespace(get=lambda k, d=None: 30 if k == "workshop.labor_rate_per_hour" else d)
    said = project_status.whole_cost(SimpleNamespace(budget=object(), config=config), shed)
    assert said == "You've spent $400.00 on Shed. You've put 10 hours into it, $300.00 of your time at your $30.00 an hour."
    from core import project_time

    monkeypatch.setattr(project_time, "project_named", lambda c, w, whole=False: shed if w == "shed" else None)
    monkeypatch.setattr(project_status, "whole_cost", lambda c, p: "whole")
    for words in ("what has the shed cost me so far?", "how much did the shed cost us?", "what's the total cost of the shed?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "whole", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what has the mower cost me?") != "whole"
