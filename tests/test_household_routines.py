"""The Household's web screen (core/household_routines.py, the design canvas's Household): the household's routines,
each with its current occurrence, how far along, and its streak in words; paused ones apart; and routines added,
paused and resumed as actions (core/routine_actions.py) and by voice (core/assistant_household_actions.py)."""

from datetime import date
from types import SimpleNamespace

from core.household_routines import screen


def test_the_households_routines_today():
    """Each routine's occurrence, progress and streak in words, what's still to do first, and paused ones apart."""
    t = lambda tid, name, cat="Household", every="daily", active=True: SimpleNamespace(  # noqa: E731
        template_id=tid, name=name, category=cat, recurrence=every, active=active)
    templates = [t("t1", "Dishes"), t("t2", "Laundry", every="weekly"), t("t3", "Push-ups", cat="Fitness"),
                 t("t4", "Old one", active=False)]
    missions = {"t1": SimpleNamespace(status="completed", objectives=[SimpleNamespace(progress=1, target=1)]),
                "t2": SimpleNamespace(status="active", objectives=[SimpleNamespace(progress=1, target=2)])}
    asked = []
    book = SimpleNamespace(all_templates=lambda: templates,
                           ensure_current_missions=lambda tpl, today: (asked.append(tpl.template_id) or
                                                                       missions[tpl.template_id], None),
                           current_streak_for_template=lambda tid, today: {"t1": 6, "t2": 0}[tid])
    data = screen(SimpleNamespace(recurring_missions=book), date(2026, 11, 6))
    assert asked == ["t1", "t2"] and (data["done"], data["total"], data["pct"]) == (1, 2, 50)
    assert data["routines"][0] == {"id": "t2", "name": "Laundry", "every": "week", "when": "This week", "done": False,
                                   "progress": 1, "target": 2, "streak": 0, "streak_text": "a new streak"}  # to do first
    assert data["routines"][1]["streak_text"] == "6 days"
    assert data["paused"] == [{"id": "t4", "name": "Old one", "every": "day", "when": "Daily"}]
    empty = screen(SimpleNamespace(recurring_missions=None))
    assert (empty["routines"], empty["paused"], empty["total"]) == ([], [], 0)


def test_routines_are_added_paused_and_resumed_as_actions_and_by_voice(tmp_path, monkeypatch):
    import pytest

    from core.actions import ACTION_TYPES, ActionError
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_household_actions import register_household_actions
    from core.household_routines import streak_words
    from tests.engine_world import build_world

    context = build_world(tmp_path, monkeypatch)
    for t in context.recurring_missions.all_templates():  # start from none
        context.recurring_missions.set_active(t.template_id, False)

    def run(kind, **params):
        return ACTION_TYPES[kind].describe(context, params), ACTION_TYPES[kind].execute(context, params)

    assert run("routine.add", name="Trash to the road", every="week") == (
        "Add Trash to the road: 1 time a week", "Added Trash to the road. I'll track your streak.")
    with pytest.raises(ActionError):
        run("routine.add", name="trash to the road")  # already there
    with pytest.raises(ActionError):
        run("routine.add", name="Dishes", times="lots")
    [row] = screen(context)["routines"]
    assert (row["name"], row["every"], row["target"]) == ("Trash to the road", "week", 1)
    assert run("routine.pause", template_id=row["id"])[1] == "Trash to the road is paused."
    assert screen(context)["routines"] == [] and screen(context)["paused"][0]["name"] == "Trash to the road"
    registry = AssistantActionRegistry()
    register_household_actions(registry)
    tool = registry._actions["pause_household_routine"].handler
    assert tool(context, {"name": "the trash", "resume": "yes"}) == "Trash to the road is back on."
    assert tool(context, {"name": "laundry"}) == "I don't have a routine called 'laundry'."
    assert (streak_words(0, "day"), streak_words(1, "week"), streak_words(21, "day")) == ("a new streak", "1 week", "21 days")
