"""
core.journal_reflection
==========================

The opt-in weekly journal reflection (2026-09-28), the follow-up to
Cognitive Extension slice C: once a week (Sunday evening by default), if
the owner journaled that week, MIA says a reflection is ready. The
details (what came up most, how the mood moved) are given only when the
owner asks ("how was my week?"), from the unlocked journal: the notice
itself never carries journal content, because notifications can show on
the phone's lock screen.

Facts in code, not the model: counts, the most frequent themes, and the
owner's own mood words from the organized entries (core/talk_it_out.py).

Settings: `journal.weekly_reflection` (off by default, the owner turns
it on in Settings → When MIA Speaks Up) and `journal.reflection_weekday`
(0 = Monday ... 6 = Sunday).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from core.assistant_actions import AssistantAction

REFLECTION_HOUR = 18  # evening: the week is mostly behind


def _week_start(now: datetime) -> str:
    return (now - timedelta(days=7)).isoformat(timespec="seconds")


def reflection_due(now: datetime, weekday: int, last_date: Optional[str]) -> bool:
    """Pure logic. The chosen day, evening, not yet done today."""
    return now.weekday() == weekday and now.hour >= REFLECTION_HOUR and last_date != now.date().isoformat()


def reflection_notice(count: int) -> Optional[tuple[str, str]]:
    """Pure logic. (title, message) for the weekly notice, or None when
    there's nothing to reflect on. No journal content, on purpose."""
    if count <= 0:
        return None
    sessions = f"{count} journal session{'s' if count != 1 else ''}"
    return ("\U0001F4D3 Your week", f"You had {sessions} this week. Your reflection is ready: ask me \"how was my week?\"")


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def weekly_reflection(entries, now: datetime) -> str:
    """Pure logic. The spoken reflection from this week's entries
    (newest first, as the journal returns them)."""
    since = _week_start(now)
    week = sorted((e for e in entries if e.created_at >= since), key=lambda e: e.created_at)
    if not week:
        return "You didn't journal this week. I'm here whenever you want to talk it out."
    parts = [f"This week you journaled {len(week)} time{'s' if len(week) != 1 else ''}."]
    themes = Counter(t for e in week for t in e.themes)
    if themes:
        parts.append("What came up most: " + _and([t for t, _ in themes.most_common(3)]) + ".")
    moods = [e.mood.strip().lower() for e in week if e.mood.strip()]
    if len(set(moods)) >= 2:
        parts.append(f"You started the week feeling {moods[0]} and your latest entry sounds {moods[-1]}.")
    elif moods:
        parts.append(f"You mostly sounded {moods[0]}.")
    parts.append("Want to talk about any of it?")
    return " ".join(parts)


def _action_journal_reflection(context, arguments: dict) -> str:
    journal = getattr(context, "private_journal", None)
    if journal is None or not journal.is_set_up():
        return "You haven't set up a private journal yet. You can do that in Notes under Private Journal."
    if not journal.is_unlocked():
        return "Your private journal is locked. Unlock it in Notes under Private Journal, then ask me again."
    return weekly_reflection(journal.all_entries(), datetime.now())


def journal_reflection_action() -> AssistantAction:
    return AssistantAction(
        name="get_journal_reflection", domain="journal",
        description="Reflect on the user's week from their private journal: how often they journaled, what came up most, "
                    "how their mood moved.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_journal_reflection,
        trigger_phrases=("how was my week", "my week in my journal", "journal reflection", "weekly reflection",
                         "reflect on my week"),
    )
