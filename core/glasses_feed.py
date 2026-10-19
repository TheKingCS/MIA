"""
core.glasses_feed
===================

The glasses' Heads-Up screen (Zac, 2026-10-18): blank until something
happens, then a card ("+50 XP · Mission Complete", "Debt payment: Car
loan"), then clear again. This is what's new for the person since the
glasses last asked, wherever it happened (the phone, the PC, the glasses).

Two sources, newest last:
- **Notifications** (core/notification_manager.py): XP, missions done,
  levels, MIA's messages through the communication gate.
- **Wins in the history** (core/life_events.py) that don't notify on
  their own: payments, builds, harvests, catch-ups, questlines, new
  ground. A win within a few seconds of a notification about the same
  thing (a "Mission complete!" notification and the mission_completed
  win) is shown once. Money never reaches a child (MONEY_TYPES).

Third, **what you said to MIA through the glasses** (core/glasses_voice.py,
`said()`): your words and her answer, and the app to open. Kept in memory
only, a few minutes, never written anywhere.

The glasses keep a cursor (`since`, an ISO time from the engine), so a
card is shown once and nothing old is replayed when they start.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

MAX_TEXT = 90
MAX_ITEMS = 5
SAME_MOMENT = timedelta(seconds=10)

# Wins that don't raise a notification themselves: (icon, headline).
EVENT_CARDS = {
    "mission_completed": ("🎉", "Mission Complete"),  # also when notifications are switched off
    "debt_payment": ("💳", "Debt Payment"),
    "insurance_switched": ("☂️", "Insurance Switched"),
    "bill_paid": ("🧾", "Bill Paid"),
    "income_received": ("💵", "Income"),
    "rent_received": ("🏠", "Rent Received"),
    "build_finished": ("🪚", "Build Finished"),
    "harvest": ("🧺", "Harvest"),
    "batch_planted": ("🌱", "Planted"),
    "caught_up": ("🤝", "Caught Up"),
    "questline_finished": ("🏆", "Questline Complete"),
    "explored": ("🗺️", "New Ground"),
    "maintenance_done": ("🔧", "Upkeep Done"),
    "workout_logged": ("💪", "Workout"),
    "project_completed": ("✅", "Project Finished"),
}
LEVEL_ICONS = {"warning": "⚠️", "critical": "🚨"}
VOICE_KEEP = timedelta(minutes=5)
_voice: deque = deque(maxlen=50)  # (when, profile id, card): what was said through the glasses
_voice_lock = threading.Lock()
_voice_n = 0


def said(profile_id: str, turn: dict, now: Optional[datetime] = None) -> dict:
    """Tell the glasses about a voice turn: {"heard", "say", "open"?}."""
    global _voice_n
    now = now or datetime.now()
    with _voice_lock:
        _voice_n += 1
        card = {"id": f"v:{_voice_n}", "icon": "🎙", "headline": "MIA", "text": _short(turn.get("say", "")),
                "heard": _short(turn.get("heard", "")), "level": "voice", "source": "voice"}
        if "open" in turn:
            card["open"] = turn["open"]
        _voice.append((now, profile_id, card))
    return card


def _voice_cards(profile_id: Optional[str], start: datetime, now: datetime) -> list[tuple[datetime, dict]]:
    with _voice_lock:
        return [(at, card) for at, pid, card in _voice
                if pid == profile_id and start < at <= now and now - at <= VOICE_KEEP]


def _short(text: str) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 1].rstrip() + "…"


def _at(iso: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(iso)[:19])
    except ValueError:
        return None


def _split_title(title: str) -> tuple[str, str]:
    """Pure logic. "🎉 Mission complete!" -> ("🎉", "Mission Complete")."""
    title = str(title or "").strip()
    first, _, rest = title.partition(" ")
    if rest and not any(ch.isalnum() for ch in first):
        icon, words = first, rest
    else:
        icon, words = "✦", title
    words = words.rstrip("!.").strip()
    return icon, " ".join(w[:1].upper() + w[1:] for w in words.split())


def feed(context, since: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    """{"now": cursor, "items": [card, ...]} — the cards since `since`
    (oldest first, at most MAX_ITEMS). With no `since`, just the cursor."""
    from core.child_accounts import is_child
    from core.life_events import AUDIT_ONLY, MONEY_TYPES, events_for

    now = now or datetime.now()
    cursor = now.isoformat(timespec="seconds")
    start = _at(since) if since else None
    if start is None:
        return {"now": cursor, "items": []}
    child = getattr(context, "config", None) is not None and is_child(context)
    cards: list[tuple[datetime, dict]] = []

    notes = getattr(context, "notifications", None)
    note_times: list[tuple[datetime, str]] = []  # (when, its headline's first word)
    if notes is not None:
        for n in notes.list_all():
            at = _at(n.created_at)
            if at is None or not (start < at <= now):
                continue
            icon, headline = _split_title(n.title)
            note_times.append((at, headline.split(" ")[0].lower()))
            cards.append((at, {"id": "n:" + n.notification_id, "icon": LEVEL_ICONS.get(n.level, icon),
                               "headline": headline, "text": _short(n.message), "level": n.level,
                               "source": n.source}))

    try:
        events = events_for(context, start.date().isoformat(), now.date().isoformat())
    except Exception:
        events = []
    for e in events:
        if e.type not in EVENT_CARDS or e.type in AUDIT_ONLY or (child and e.type in MONEY_TYPES):
            continue
        at = _at(e.at)
        if at is None or not (start < at <= now):
            continue
        icon, headline = EVENT_CARDS[e.type]
        word = headline.split(" ")[0].lower()
        if any(abs(at - t) <= SAME_MOMENT and w == word for t, w in note_times):
            continue  # a notification about the same thing already says it
        xp = (e.payload or {}).get("xp") if isinstance(e.payload, dict) else None
        cards.append((at, {"id": "e:" + e.event_id, "icon": icon, "headline": headline, "text": _short(e.summary),
                           "level": "win", "source": e.type, "xp": xp or None}))

    from core.person_settings import person_id

    cards += _voice_cards(person_id(context), start, now)
    cards.sort(key=lambda c: c[0])
    return {"now": cursor, "items": [c for _at_, c in cards[-MAX_ITEMS:]]}
