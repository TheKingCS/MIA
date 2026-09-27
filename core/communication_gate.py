"""
core.communication_gate
==========================

"Know when to speak", slice C of docs/COGNITIVE_EXTENSION_PROPOSAL.md:
the one path every proactive (unprompted) message from MIA goes
through, so a context-aware assistant never turns into a nag.

What goes through here: the daily checks in core/application.py
(birthday, calendar digest, evening check-in, budget nudge, smart
suggestions, the insight scans, feature tips) and missions MIA assigns
herself. What doesn't: replies to something the user just did (an
objective completed, an achievement unlocked, a file imported), alarms
the user set, and low battery. Those are answers or safety, not MIA
deciding to speak up.

The decision (proposal, question 5), for a batch of candidates offered
together:

1. **Urgent** goes out immediately, every time.
2. **Nothing new?** A candidate whose topic and facts match one sent in
   the last `repeat_days` is dropped.
3. **Is the user available?** Not while they're mid-conversation in a
   personal mode (venting, journaling, perspective): timely things wait
   30 minutes, ambient things are dropped.
4. **Spoken recently / daily budget.** At most `daily_budget` unprompted
   messages a day (owner's choice: 5) and `min_spacing_minutes` between
   them. Timely things that can't go now wait for the next opening;
   ambient things are dropped, never queued, so there's never a backlog.
5. **Consolidation.** Everything that passes in one batch goes out as
   **one** message and counts once against the budget.

No quiet hours: the owner uses the phone's Do Not Disturb instead
(2026-09-27 decision). Every decision, including "said nothing", is
logged with its reason (data/communication_log.json), so "what didn't
you tell me today?" has a real answer.

`decide_batch()` is pure (takes the clock, settings and history as
arguments) so every rule is testable with a fake clock; the
CommunicationGate class wraps it with persistence and delivery.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LOG_FILE = _DATA_DIR / "communication_log.json"

URGENT = "urgent"  # safety, money due today: always goes out
TIMELY = "timely"  # useful within hours: waits for an opening if it can't go now
AMBIENT = "ambient"  # nice to know: dropped rather than queued

ACT = "act"
DEFER = "defer"
DROP = "drop"

_BUSY_DEFER = timedelta(minutes=30)
_BUSY_WINDOW = timedelta(minutes=30)
_KEEP_LOG_DAYS = 30

DEFAULT_SETTINGS = {"daily_budget": 5, "min_spacing_minutes": 90, "repeat_days": 7}


@dataclass
class Candidate:
    """Something MIA could say without being asked."""

    topic: str  # stable kind, e.g. "calendar_digest", "budget_nudge"
    title: str
    message: str
    urgency: str = AMBIENT
    source: str = "system"
    level: str = "info"
    # What counts as "the same thing again". Defaults to topic + message;
    # a daily-by-design message (calendar, check-in) includes the date.
    fingerprint: str = ""
    not_before: str = ""  # ISO datetime, set when deferred
    # ISO datetime after which it's no longer true ("you have 2 events
    # today" is wrong tomorrow). A deferred candidate past this is dropped.
    expires: str = ""

    def key(self) -> str:
        raw = f"{self.topic}|{self.fingerprint or self.message}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class Decision:
    candidate: Candidate
    action: str  # act | defer | drop
    reason: str
    delivered_as: str = ""  # "alone" | "digest" when acted


@dataclass
class GateState:
    """What decide_batch() needs to know about the past."""

    sent: list[dict] = field(default_factory=list)  # {at, key, topic, urgency, digest_id}
    user_busy: bool = False


def _parse(iso: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def _unprompted_sends_today(state: GateState, now: datetime) -> list[datetime]:
    """Non-urgent deliveries today, one per digest (a digest counts once)."""
    seen_digests = set()
    times = []
    for entry in state.sent:
        at = _parse(entry.get("at", ""))
        if at is None or at.date() != now.date() or entry.get("urgency") == URGENT:
            continue
        digest = entry.get("digest_id") or entry.get("key")
        if digest in seen_digests:
            continue
        seen_digests.add(digest)
        times.append(at)
    return times


def decide_batch(candidates: list[Candidate], now: datetime, state: GateState, settings: dict) -> list[Decision]:
    """Pure logic. One Decision per candidate, in order."""
    budget = int(settings.get("daily_budget", DEFAULT_SETTINGS["daily_budget"]))
    spacing = timedelta(minutes=int(settings.get("min_spacing_minutes", DEFAULT_SETTINGS["min_spacing_minutes"])))
    repeat_window = timedelta(days=int(settings.get("repeat_days", DEFAULT_SETTINGS["repeat_days"])))

    recent_keys = {}
    for entry in state.sent:
        at = _parse(entry.get("at", ""))
        if at is not None and now - at <= repeat_window:
            recent_keys[entry.get("key")] = at

    decisions: list[Decision] = []
    passing: list[Candidate] = []
    passing_ids: set[int] = set()
    for candidate in candidates:
        if candidate.urgency == URGENT:
            decisions.append(Decision(candidate, ACT, "urgent", "alone"))
            continue
        sent_at = recent_keys.get(candidate.key())
        if sent_at is not None:
            decisions.append(Decision(candidate, DROP, f"nothing new since {sent_at:%b %d}"))
            continue
        if state.user_busy:
            if candidate.urgency == TIMELY:
                candidate.not_before = (now + _BUSY_DEFER).isoformat(timespec="seconds")
                decisions.append(Decision(candidate, DEFER, "you were in the middle of a conversation"))
            else:
                decisions.append(Decision(candidate, DROP, "you were in the middle of a conversation"))
            continue
        decisions.append(Decision(candidate, ACT, ""))  # provisional, settled below
        passing.append(candidate)
        passing_ids.add(id(candidate))

    if not passing:
        return decisions

    sends_today = _unprompted_sends_today(state, now)
    blocked_reason = ""
    next_opening = None
    if len(sends_today) >= budget:
        blocked_reason = f"already said {len(sends_today)} things today (your limit is {budget})"
        next_opening = datetime.combine(now.date() + timedelta(days=1), datetime.min.time()).replace(hour=7)
    elif sends_today and now - max(sends_today) < spacing:
        last = max(sends_today)
        blocked_reason = f"spoke up at {last:%H:%M}; waiting {int(spacing.total_seconds() // 60)} minutes between messages"
        next_opening = last + spacing

    delivered_as = "digest" if len(passing) > 1 else "alone"
    for decision in decisions:
        if id(decision.candidate) not in passing_ids:
            continue
        if not blocked_reason:
            decision.reason = "passed" if delivered_as == "alone" else f"passed, sent together with {len(passing) - 1} other(s)"
            decision.delivered_as = delivered_as
        elif decision.candidate.urgency == TIMELY:
            decision.action = DEFER
            decision.reason = blocked_reason
            decision.candidate.not_before = next_opening.isoformat(timespec="seconds")
        else:
            decision.action = DROP
            decision.reason = blocked_reason
    return decisions


def compose_digest(candidates: list[Candidate]) -> tuple[str, str]:
    """Pure logic. One title and message for several things said at once."""
    if len(candidates) == 1:
        return candidates[0].title, candidates[0].message
    parts = [f"{c.title}: {c.message}" for c in candidates]
    return f"MIA has {len(candidates)} things for you", "\n\n".join(parts)


class CommunicationGate:
    """Persistence + delivery around decide_batch(). Lives on
    AppContext.communication; delivery goes through the ordinary
    NotificationManager, so the toast, bell and phone push all work
    unchanged."""

    def __init__(self, context) -> None:
        self.context = context
        self._log: list[dict] = []
        self._pending: list[dict] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _LOG_FILE.exists():
            return
        try:
            data = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
            self._log = list(data.get("log", []))
            self._pending = list(data.get("pending", []))
        except (json.JSONDecodeError, OSError, AttributeError):
            log.exception("communication_log.json unreadable — starting fresh.")

    def _save(self, now: datetime) -> None:
        cutoff = (now - timedelta(days=_KEEP_LOG_DAYS)).isoformat()
        self._log = [e for e in self._log if e.get("at", "") >= cutoff]
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_LOG_FILE, json.dumps({"log": self._log, "pending": self._pending}, indent=2))

    # ------------------------------------------------------------------
    # Settings and state
    # ------------------------------------------------------------------

    def settings(self) -> dict:
        config = self.context.config
        return {key: config.get(f"communication.{key}", default) for key, default in DEFAULT_SETTINGS.items()}

    def set_daily_budget(self, count: int) -> int:
        count = max(1, min(20, int(count)))
        self.context.config.set("communication.daily_budget", count)
        self.context.config.save()
        return count

    def _user_busy(self, now: datetime) -> bool:
        """Mid-conversation in a personal mode: venting, journaling, perspective."""
        from core.conversation_modes import PERSONAL_MODES  # local: keeps this module's imports light

        conversations = getattr(self.context, "conversations", None)
        if conversations is None:
            return False
        active_id = conversations.get_active_conversation_id()
        conversation = conversations.get_conversation(active_id) if active_id else None
        if conversation is None or not (conversation.mode in PERSONAL_MODES or conversation.journal):
            return False
        updated = _parse(conversation.updated_at)
        return updated is not None and now - updated <= _BUSY_WINDOW

    def _state(self, now: datetime) -> GateState:
        sent = [e for e in self._log if e.get("action") == ACT]
        return GateState(sent=sent, user_busy=self._user_busy(now))

    # ------------------------------------------------------------------
    # Offering
    # ------------------------------------------------------------------

    def offer(self, candidate: Candidate, now: Optional[datetime] = None) -> list[Decision]:
        return self.offer_batch([candidate], now)

    def offer_batch(self, candidates: list[Candidate], now: Optional[datetime] = None) -> list[Decision]:
        """Decide, deliver, log. Also retries anything deferred that's now due."""
        now = now or datetime.now()
        pending_before = len(self._pending)
        candidates = self._take_due_pending(now) + list(candidates)
        if not candidates:
            if len(self._pending) != pending_before:
                self._save(now)  # expired ones were dropped and logged
            return []
        decisions = decide_batch(candidates, now, self._state(now), self.settings())

        digest_members = [d.candidate for d in decisions if d.action == ACT and d.delivered_as == "digest"]
        digest_id = hashlib.sha1(f"{now.isoformat()}|digest".encode()).hexdigest()[:12] if digest_members else ""
        notifications = getattr(self.context, "notifications", None)
        for decision in decisions:
            if decision.action == ACT and decision.delivered_as == "alone" and notifications is not None:
                c = decision.candidate
                notifications.notify(title=c.title, message=c.message, level=c.level, source=c.source)
        if digest_members and notifications is not None:
            title, message = compose_digest(digest_members)
            notifications.notify(title=title, message=message, level="info", source="system")

        for decision in decisions:
            c = decision.candidate
            self._log.append({
                "at": now.isoformat(timespec="seconds"),
                "key": c.key(),
                "topic": c.topic,
                "title": c.title,
                "message": c.message,
                "urgency": c.urgency,
                "action": decision.action,
                "reason": decision.reason,
                "digest_id": digest_id if decision.delivered_as == "digest" else "",
            })
            if decision.action == DEFER:
                self._pending.append(asdict(c))
        try:
            self._save(now)
        except OSError:
            log.exception("Couldn't save communication_log.json.")
        return decisions

    def _take_due_pending(self, now: datetime) -> list[Candidate]:
        due, waiting = [], []
        for raw in self._pending:
            expires = _parse(raw.get("expires", ""))
            if expires is not None and expires <= now:
                self._log.append({
                    "at": now.isoformat(timespec="seconds"), "key": "", "topic": raw.get("topic", ""),
                    "title": raw.get("title", ""), "message": raw.get("message", ""),
                    "urgency": raw.get("urgency", ""), "action": DROP,
                    "reason": "waited too long; it's no longer current", "digest_id": "",
                })
                continue
            not_before = _parse(raw.get("not_before", ""))
            (due if not_before is None or not_before <= now else waiting).append(raw)
        self._pending = waiting
        fields = Candidate.__dataclass_fields__
        return [Candidate(**{k: v for k, v in raw.items() if k in fields}) for raw in due]

    # ------------------------------------------------------------------
    # Looking back
    # ------------------------------------------------------------------

    def entries_for_day(self, day: Optional[str] = None) -> list[dict]:
        day = day or datetime.now().date().isoformat()
        return [e for e in self._log if e.get("at", "").startswith(day)]

    def pending(self) -> list[dict]:
        return list(self._pending)
