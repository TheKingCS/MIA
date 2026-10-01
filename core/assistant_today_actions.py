"""
core.assistant_today_actions
===============================

"What's on today?" (core/today.py, 2026-10-01): everything that needs
the person today, across every app, in one answer.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.today import describe, today_items


def _action_get_today(context, arguments: dict) -> str:
    return describe(today_items(context))


def register_today_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="get_today", domain="today",
        description=("Everything that needs the user today across all apps: overdue things, today's events, bills, "
                     "maintenance, tasks, birthdays, things waiting (inbox, drafts), and what's coming in 3 days."),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_today,
        trigger_phrases=("what's on today", "whats on today", "what's on for today", "what do i have today",
                         "what's my day", "whats my day", "my day look like", "plan for today", "what's today",
                         "anything due today", "what needs me today", "what do i need to do today"),
    ))
