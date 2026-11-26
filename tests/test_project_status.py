"""
tests.test_project_status
===========================

"How's the shed coming along?" (core/project_status.py, brainstorm round 19): one project's picture from his records,
said in code, only for a project of his.
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


def test_past_due_and_the_words_reach_it(monkeypatch):
    late = SimpleNamespace(project_id="p2", name="Garage Rewire", status="Active", due_date="2026-08-14", time_log=[])
    said = project_status.say(SimpleNamespace(), late, date(2026, 11, 26))
    assert "104 days past its due date (August 14)" in said and "No hours logged" in said
    from core import project_time

    monkeypatch.setattr(project_time, "project_named", lambda c, w, whole=False: late if "rewire" in w else None)
    monkeypatch.setattr(project_status, "say", lambda c, p, t=None: f"picture of {p.name}")
    for words in ("How's the garage rewire coming along?", "where am I on the garage rewire?",
                  "status of the garage rewire project"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "picture of Garage Rewire", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "how's the weather looking?") != "picture of Garage Rewire"
