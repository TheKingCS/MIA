"""
core.maintenance_insights
============================

The Maintenance-domain scan for "connective infrastructure" phase 3
(Insight + Recommendation) — see core/insight_manager.py's own
docstring for why these are real, new persisted entities. Pure
decision logic, no Qt, no manager instance of its own, wired into
core/application.py's existing daily-check timer — same "pure
functions, unit-testable without a real clock, wired into the
daily-check loop" shape core/smart_suggestions.py already established.

Deliberately invents NO new due-date/trend math — every "is this task
flagged" decision reuses core.maintenance_manager's own existing pure
functions verbatim (is_overdue/days_until_due for calendar tasks,
is_meter_task_due for runtime/mileage/cycles/condition tasks,
is_sensor_task_due for sensor tasks, predicted_due_date for a
forward-looking "trending toward due soon" signal on meter tasks).
This pass is about proving the Insight/Recommendation machinery and
the observe->understand->insight->recommend->act->result loop, not
re-deriving analysis that's already real and tested.

A real subtlety worth remembering: predicted_due_date() only ever
returns a projection when the task is NOT already due (it explicitly
returns None once is_meter_task_due() would be true — there's nothing
left to project). So it's used here as its own forward-looking
"due_soon" signal for meter tasks, mirroring calendar tasks' own
due_soon concept — never as a decoration folded onto an already-"due"
message, which would never actually have a value to show.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.insight_manager import Insight
from core.maintenance_manager import (
    METER_TRIGGER_TYPES,
    THRESHOLD_TRIGGER_TYPES,
    MaintenanceTask,
    days_until_due,
    is_meter_task_due,
    is_overdue,
    is_sensor_task_due,
    predicted_due_date,
)

# Same 3-day window core.smart_suggestions.py's _EXPIRING_WITHIN_DAYS already uses.
_DUE_SOON_WITHIN_DAYS = 3


def _task_flag(task: MaintenanceTask, readings: list, today: date) -> Optional[tuple[str, str]]:
    """Returns (kind, detail) if `task` is currently flagged, else
    None. `detail` is the trigger-specific reason text (e.g. "overdue
    by 3 days") that _build_message() below turns into the full
    Insight message — not the message itself."""
    if task.trigger_type == "calendar":
        remaining = days_until_due(task, today)
        if is_overdue(task, today):
            days_over = abs(remaining)
            return "overdue", f"overdue by {days_over} day{'s' if days_over != 1 else ''}"
        if remaining is not None and 0 <= remaining <= _DUE_SOON_WITHIN_DAYS:
            return "due_soon", f"due in {remaining} day{'s' if remaining != 1 else ''}"
        return None

    if task.trigger_type in METER_TRIGGER_TYPES:
        if is_meter_task_due(task, readings):
            return "due", "due now"
        projection = predicted_due_date(task, readings, today)
        if projection is not None:
            estimated_date, caveat = projection
            days_out = (estimated_date - today).days
            if 0 <= days_out <= _DUE_SOON_WITHIN_DAYS:
                return "due_soon", f"projected to be due in {caveat}"
        return None

    if task.trigger_type in THRESHOLD_TRIGGER_TYPES:
        if is_sensor_task_due(task, readings):
            return "due", "reading has crossed its threshold"
        return None

    return None


def scan_maintenance_insights(context, today: date) -> list[Insight]:
    """Real, deterministic daily scan over every Maintenance task —
    creates a new Insight (+ a linked Recommendation) for any task
    that's newly flagged, resolves any open Insight for a task that's
    no longer flagged or whose flagged kind has changed (e.g.
    due_soon -> overdue). Resolution is the loop's RESULT step, closed
    automatically the moment a real completion happens through the
    existing Maintenance UI — no new "mark resolved" interaction
    needed for this pass. Returns only the Insights newly created THIS
    run, for batching into one notification — see
    format_maintenance_insights_message()."""
    if context.maintenance is None or context.insights is None:
        return []

    new_insights: list[Insight] = []
    for task in context.maintenance.all_tasks():
        readings = context.maintenance.readings_for_task(task.task_id)
        flag = _task_flag(task, readings, today)
        existing_open = context.insights.open_insights_for_source("maintenance", task.task_id)

        if flag is None:
            for insight in existing_open:
                context.insights.resolve_insight(insight.insight_id)
            continue

        kind, detail = flag
        title = f"\U0001F527 {task.title}"
        message = f"'{task.title}' is {detail}."
        insight = context.insights.create_insight_if_new(
            source_type="maintenance", source_id=task.task_id, kind=kind, title=title, message=message,
        )
        if insight is not None:
            context.insights.add_recommendation(
                insight.insight_id, f"Mark '{task.title}' complete in Maintenance, or reschedule it."
            )
            new_insights.append(insight)
        # A previously-flagged kind that no longer applies (e.g. was
        # due_soon, is now overdue) is stale -- resolve it. The insight
        # just created/found above for the CURRENT kind is untouched
        # since it was never part of this snapshot.
        for insight in existing_open:
            if insight.kind != kind:
                context.insights.resolve_insight(insight.insight_id)

    return new_insights


def format_maintenance_insights_message(insights: list[Insight]) -> Optional[str]:
    """Pure formatting logic — testable without Qt. Joins newly-created
    Insights into one message, same "join multiple true sub-checks
    into one notification, None when there's nothing to say" shape
    core.smart_suggestions.build_smart_suggestions_message() already
    uses."""
    if not insights:
        return None
    return " ".join(insight.message for insight in insights)
