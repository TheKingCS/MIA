"""
core.assistant_life_event_actions
====================================

"What did I get done this week?", "what changed this month?", "what bills
did I pay?" (core/life_events.py, 2026-10-05). Facts from the log,
counted in code; the model only phrases them.
"""

from __future__ import annotations

from core import life_events
from core.assistant_actions import AssistantAction, AssistantActionRegistry

# Words people use -> the event types they mean.
_KINDS = {
    "bill": ("bill_paid",), "debt": ("debt_payment",), "mission": ("mission_completed",),
    "skill": ("skill_evidence",), "workout": ("workout_logged",), "exercise": ("workout_logged",),
    "meal": ("meal_logged",), "cook": ("meal_logged",), "maintenance": ("maintenance_done",),
    "rent": ("rent_received",), "task": ("task_done",), "project": ("project_completed",),
    "spend": ("expense_added", "bill_paid", "debt_payment", "property_expense"),
    "expense": ("expense_added", "property_expense"), "income": ("income_added", "income_received", "rent_received"),
    "import": ("imported",), "undo": ("undone",),
}


def _period(text: str) -> str:
    text = (text or "").lower()
    for period in ("today", "month", "year"):
        if period in text:
            return period
    return "week"


def _action_get_life_events(context, arguments: dict) -> str:
    period = _period(str(arguments.get("period") or ""))
    kind = str(arguments.get("kind") or "").lower().strip()
    types = None
    for word, wanted in _KINDS.items():
        if word in kind:
            types = wanted
            break
    events = life_events.events_for(context, since=life_events.period_start(period), types=types)
    return life_events.describe(events, period)


def register_life_event_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="get_life_events", domain="life_events",
        description="What happened in the user's life over a period, from MIA's history: bills paid, missions "
                    "completed, workouts, maintenance done, rent received, tasks done, and so on. For 'what did I get "
                    "done', 'what changed', 'what did I pay'.",
        parameters={"type": "object", "properties": {
            "period": {"type": "string", "description": "today, week, month or year (default week)."},
            "kind": {"type": "string", "description": "Optional: bills, debts, missions, workouts, meals, "
                                                      "maintenance, rent, tasks, projects, spending, income."},
        }, "required": []},
        handler=_action_get_life_events,
        trigger_phrases=("get done", "got done", "accomplish", "what changed", "what happened", "what did i pay",
                         "bills did i pay", "this week so far", "my progress this", "what have i finished",
                         "how many workouts", "wins this"),
    ))
