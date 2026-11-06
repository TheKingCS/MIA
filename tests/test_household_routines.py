"""The Household's web screen (core/household_routines.py): the household's routines, each with its current
occurrence, how far along, and its streak."""

from datetime import date
from types import SimpleNamespace

from core.household_routines import screen


def test_the_households_routines_today():
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
    assert asked == ["t1", "t2"] and (data["done"], data["total"]) == (1, 2)
    assert data["routines"][1] == {"id": "t2", "name": "Laundry", "every": "week", "done": False, "progress": 1,
                                   "target": 2, "streak": 0}
    assert screen(SimpleNamespace(recurring_missions=None)) == {"routines": [], "done": 0, "total": 0}
