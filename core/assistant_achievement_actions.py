"""
core.assistant_achievement_actions
====================================

Achievements by voice and from the screen (the game layer, 2026-11-24; DEC-0125, both ways). The tool
`my_achievements` says what the Achievements page shows (core/achievement_cards.say): how many he's unlocked, the
latest, and the next he's closest to. The action `achievement.seen` is the card's Close button
(core/achievement_cards.mark_seen): it changes only when he last saw a card, so it runs at a press, like
dismissing a notification.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction


def _seen(context, params) -> str:
    """Action achievement.seen: the cards up to `upto` were shown."""
    from core.achievement_cards import mark_seen

    try:
        return mark_seen(context, str(params.get("upto", "") or ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from None


def _describe_seen(context, params) -> str:
    """What achievement.seen says: the cards were seen (a bad time is refused here, before anything changes)."""
    from datetime import datetime

    upto = str(params.get("upto", "") or "").strip()[:19]
    if upto:
        try:
            datetime.fromisoformat(upto)
        except ValueError:
            raise ActionError("That isn't a time.") from None
    return "Mark the achievement cards seen"


ACHIEVEMENT_ACTIONS = {k.kind: k for k in (
    ActionType("achievement.seen", "Close", {"upto": "the newest card's time"}, _describe_seen, _seen),
)}
ACTION_TYPES.update(ACHIEVEMENT_ACTIONS)


def _mine(context, arguments: dict) -> str:
    """Tool my_achievements: the achievements unlocked, the latest, and the next closest (core/achievement_cards)."""
    from core.achievement_cards import say

    return say(context)


def register_achievement_actions(registry) -> None:
    """Registers my_achievements (reached by "my achievements" and the like; a bare "achievement" isn't enough)."""
    registry.register(AssistantAction(
        name="my_achievements", domain="skills",
        description="His achievements log: how many he's unlocked (harvest, eggs, jars, structures built, missions, "
                    "workouts...), the latest with their dates, and the next tier he's closest to.",
        parameters={"type": "object", "properties": {}},
        handler=_mine, trigger_phrases=("my achievements", "achievements have i", "achievements log",
                                        "what have i unlocked", "what achievements", "closest achievement",
                                        "next achievement", "my milestones"),
    ))
