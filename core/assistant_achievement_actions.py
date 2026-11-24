"""
core.assistant_achievement_actions
====================================

Achievements by voice and from the screen (the game layer, 2026-11-24; DEC-0125, both ways). The tool
`my_achievements` says what the Achievements page shows (core/achievement_cards.say): how many he's unlocked, the
latest, and the next he's closest to. Closing a card isn't an action: marking it seen is bookkeeping
(POST /api/achievements/seen, core/achievement_cards.mark_seen), kept out of undo and Recent Changes.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _mine(context, arguments: dict) -> str:
    """Tool my_achievements: the achievements unlocked, the latest, and the next closest (core/achievement_cards)."""
    from core.achievement_cards import say

    return say(context)


def register_achievement_actions(registry) -> None:
    """Registers my_achievements (reached by "my achievements", "which achievement am I closest to" and the like; a
    bare "achievement" isn't enough)."""
    registry.register(AssistantAction(
        name="my_achievements", domain="skills",
        description="His achievements log: how many he's unlocked (harvest, eggs, jars, structures built, missions, "
                    "workouts...), the latest with their dates, and the next tier he's closest to.",
        parameters={"type": "object", "properties": {}},
        handler=_mine, trigger_phrases=("my achievements", "achievements have i", "achievements log",
                                        "what have i unlocked", "what achievements", "closest achievement",
                                        "next achievement", "my milestones", "achievement am i", "achievements am i",
                                        "which achievement", "close to unlocking", "closest to unlocking"),
    ))
