"""
core.morning_briefing
=======================

The morning briefing he asks for (brainstorm round 14; the live sweep, 2026-11-25: "every morning tell me the weather
and my day" got a one-off answer and nothing kept): once a morning, from the hour he sets, the day's weather and his
day, worked out in code from his records like the evening wrap (core/evening_wrap.py): the forecast kept
(core/weather.card, never fetched for this), today's list (core/today.py: how many things, and the first, a timed one
with its time). Through the communication gate like any of her messages (paced, mutable from the message itself).

Off until he asks (`morning_briefing.hour` unset): "every morning at 7, tell me the weather and my day" sets it
(`asked`, `set_hour`), "stop the morning briefing" clears it. `briefing(context, now)` is the words; `offer(context,
now)` the daily check's message (from his hour on, once a day, gone at noon when it's a morning's).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

HOUR_KEY = "morning_briefing.hour"
DEFAULT_HOUR = 7

# Only a briefing asked for, said either way round, never a sentence about his own morning ("every morning I read the
# Bible", "the morning report from the greenhouse": the eleventh review)
# what's in it, said: "tell me the weather and my day", never "tell me a joke" or "give me the egg count" (the Fable
# review, 2026-11-25)
_WHAT = r"\s+(?:the\s+|my\s+|a\s+|today'?s\s+)?(?:weather|day|schedule|calendar|briefing|brief|rundown|summary|agenda|plan)\b"
_ASK = r"(?:brief me\b|(?:tell|give|show|send|read)\s+me" + _WHAT + ")"
_SET = re.compile(r"\b(?:every|each)\s+morning\b.{0,40}\b" + _ASK + "|"
                  r"\b" + _ASK + r".{0,40}\b(?:every|each)\s+morning\b|"
                  r"\b(?:set up|start|turn on|i want)\s+(?:a\s+|my\s+)?(?:daily\s+)?morning\s+"
                  r"(?:briefing|brief|summary|rundown)\b|"
                  r"\bgive me\s+(?:a\s+|my\s+)?(?:daily\s+)?morning\s+(?:briefing|brief|summary|rundown)\s+(?:at|every)\b",
                  re.I)  # "give me a morning briefing at 8am" is a standing one; "give me my morning briefing" isn't
# a negation or a question is never a setting: "don't stop the morning briefing", "did you stop it?"
_NOT_A_SETTING = re.compile(r"\b(?:don'?t|do not|never|didn'?t|did you|why|won'?t|can'?t)\b|\?\s*$|"
                            r"^\s*(?:can|could|will|would|did|do|does|is|are|what|how|when)\b", re.I)
_OFF = re.compile(r"\b(?:stop|cancel|turn off|no more|end|pause)\s+(?:the\s+|my\s+)?(?:daily\s+)?morning\s+"
                  r"(?:briefing|brief|summary|report|rundown)s?\b", re.I)
_AT = re.compile(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", re.I)


def hour(context) -> Optional[int]:
    """The hour he set (4 to 11 in the morning), or None when he hasn't asked for one."""
    try:
        from core import person_settings

        value = person_settings.get(context, HOUR_KEY, None)
        if value in (None, ""):
            return None
        hour_of = int(value)
        return hour_of if 4 <= hour_of <= 11 else DEFAULT_HOUR
    except (TypeError, ValueError, AttributeError):
        return None


def set_hour(context, hour_of: Optional[int]) -> None:
    """Keeps his hour (None turns the briefing off)."""
    from core import person_settings

    person_settings.put(context, HOUR_KEY, hour_of if hour_of is None else int(hour_of))


def asked(words: str) -> Optional[tuple]:
    """Pure logic. ("on", hour) for "every morning at 7, tell me the weather and my day" (7 unless he says an hour
    from 4 to 11 am), ("off", None) for "stop the morning briefing", else None.
    Only a briefing asked for, either way round ("tell me the weather every morning"); never a sentence about his
    own morning or a reminder, a negation or a question ("don't stop the morning briefing"), or a one-off ("give me
    my morning briefing") or anything else every morning ("tell me a joke every morning": the Fable review)."""
    said = str(words or "")
    if _NOT_A_SETTING.search(said):
        return None
    if _OFF.search(said):
        return "off", None
    if not _SET.search(said) or re.search(r"\bremind me\b", said, re.I):
        return None  # "remind me every morning to give the dog his meds" is a reminder, never the briefing
    at = _AT.search(said)
    if not at:
        return "on", DEFAULT_HOUR
    hour_of = int(at.group(1))
    if (at.group(3) or "").lower().startswith("p") or not 4 <= hour_of <= 11:
        return "ask", None  # an evening or a night hour isn't a morning's
    return "on", hour_of


def weather_today(context) -> str:
    """Today's forecast in a few words, from the forecast already kept; "" without one."""
    from core import weather

    card = weather.card(context)
    if not card.get("text") or card.get("high") is None:
        return ""
    words = (card.get("today_words") or card.get("words") or "").lower()
    unit = card.get("unit", "")
    return f"{words + ', ' if words else ''}a high of {card['high']}{unit} and a low of {card['low']}{unit}"


def day_today(context, today) -> str:
    """Today's list in a few words: how many things and the first (a timed one with its time); "" for none.
    Alarms left out by `core/today.is_alarm`; tasks counted."""
    from core.today import is_alarm, today_items

    items = [i for i in today_items(context, today) if i.when in ("overdue", "today") and not is_alarm(i)]
    if not items:
        return ""
    first = items[0]
    first_words = first.title + (f" at {first.time}" if getattr(first, "time", "") else "")
    many = len(items)
    return f"{many} thing{'s' if many != 1 else ''} on today's list, first up {first_words}"


def briefing(context, now: datetime) -> str:
    """The briefing's words; "" when there's no weather and nothing on the list."""
    parts = []
    for read, name in ((lambda: weather_today(context), "weather"), (lambda: day_today(context, now.date()), "day")):
        try:
            parts.append(read())
        except Exception:  # noqa: BLE001 - one part that can't be read never stops the briefing
            log.exception("Morning briefing: the %s couldn't be read", name)
            parts.append("")
    sky, day = parts
    if not (sky or day):
        return ""
    said = "Good morning."
    if sky:
        said += f" Today: {sky}."
    said += f" {day[:1].upper() + day[1:]}." if day else " Nothing on today's list."
    return said


def offer(context, now: datetime) -> list:
    """The daily check's message: only when he asked for it, from his hour on, once a day, TIMELY until noon."""
    from core.communication_gate import TIMELY, Candidate

    at = hour(context)
    if at is None or now.hour < at or now.hour >= 12:
        return []
    said = briefing(context, now)
    if not said:
        return []
    noon = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=12)
    return [Candidate(topic="morning_briefing", title="Your morning briefing", message=said, urgency=TIMELY,
                      source="system", fingerprint=f"morning-briefing-{now.date().isoformat()}",
                      expires=noon.isoformat())]


def reply(context, words: str) -> Optional[str]:
    """His words about it, answered in code (core/assistant_turn.py): set from his hour, turned off, or asked again
    for a morning hour; None for anything else.
    A time with minutes is said as sent on the hour."""
    found = asked(words)
    if found is None:
        return None
    kind, hour_of = found
    if kind == "off":
        set_hour(context, None)
        return "Morning briefing off. Say \"every morning, tell me the weather and my day\" to start it again."
    if kind == "ask":
        return "What time in the morning? Say an hour from 4 to 11, like \"every morning at 7\"."
    set_hour(context, hour_of)
    on_the_hour = " (I send it on the hour)" if re.search(r"\bat\s+\d{1,2}:(?!00)\d{2}", str(words or "")) else ""
    return (f"Done: every morning from {hour_of} am{on_the_hour}, the day's weather and your day, in one message. Say "
            "\"stop the morning briefing\" to turn it off.")
