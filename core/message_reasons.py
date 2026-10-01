"""
core.message_reasons
======================

"Why are you telling me this?" (2026-10-01, accounts stage 5): a plain
answer for each kind of message MIA sends on her own
(core/communication_gate.py topics), plus finding the kind someone means
by their own words ("stop telling me about the budget").
"""

from __future__ import annotations

from typing import Optional

# topic -> (short name, why MIA sends it)
REASONS: dict[str, tuple[str, str]] = {
    "calendar_digest": ("today's calendar", "you have events today, and I mention them once in the morning"),
    "checkin": ("check-ins", "I hadn't heard from you today; I check in at most once a day"),
    "birthday": ("birthdays", "a birthday is coming up for someone in People & Pets or your profile"),
    "budget_nudge": ("budget check-ins", "a bill is due soon, a payday is coming, or a category is near its limit"),
    "smart_suggestion": ("suggestions", "it's been a while since a workout, something in the pantry is running out "
                                         "or expiring, or a birthday is near"),
    "maintenance_insight": ("maintenance tips", "something you track is due or overdue for maintenance"),
    "mission_insight": ("mission reminders", "a mission you accepted hasn't moved in a while"),
    "pattern_insight": ("patterns I notice", "I noticed a pattern in how things have been going"),
    "skill_pattern_insight": ("skill patterns", "I noticed a pattern in the skills you've been building"),
    "skill_decline_insight": ("skills slipping", "a skill you used to practice hasn't had attention lately"),
    "skill_momentum_insight": ("skill streaks", "you've been on a roll with a skill"),
    "walkthrough_suggestion": ("app tips", "there's an app you haven't opened yet; I suggest each one only once"),
    "mission_auto_assigned": ("new missions", "I picked a mission that fits what you've been working on"),
    "inbox": ("the document inbox", "new documents arrived in your inbox"),
    "connectivity": ("internet changes", "the internet went down or came back"),
    "warranty": ("warranty reminders", "a warranty on something you own is ending soon"),
    "journal_reflection": ("the weekly reflection", "you turned on the weekly journal reflection"),
}


def name_of(topic: str) -> str:
    return REASONS.get(topic, (topic.replace("_", " "), ""))[0]


def explain(entry: dict) -> str:
    """Pure logic. Why a logged message was sent and how to stop that kind."""
    topic = entry.get("topic", "")
    name, why = REASONS.get(topic, (topic.replace("_", " "), "it looked useful"))
    said = entry.get("title") or "that"
    return (f"I told you \"{said}\" because {why}. If you'd rather not hear about {name}, say "
            f"\"stop telling me about {name}\" and I'll take a break from it.")


def _stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def find_topic(words: str, topics: Optional[list[str]] = None) -> Optional[str]:
    """Pure logic. The kind of message someone named in their own words."""
    said = {w.strip(".,!?'\"") for w in (words or "").lower().replace("-", "").split()}
    said = {w for w in said if len(w) > 2} - {"the", "about", "telling", "tell", "stop", "me", "those", "these", "messages"}
    if not said:
        return None
    best, score = None, 0
    for topic in (topics or list(REASONS)):
        name, why = REASONS.get(topic, (topic.replace("_", " "), ""))
        vocabulary = set(f"{name} {topic.replace('_', ' ')}".lower().replace("-", "").split())
        vocabulary |= {_stem(v) for v in vocabulary}
        hits = len({w for w in said if w in vocabulary or _stem(w) in vocabulary})
        if hits > score:
            best, score = topic, hits
    return best
