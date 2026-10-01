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

**Learning from being ignored** (2026-09-28): each delivered message
remembers its notification. Closing one with its X (not "clear all", not
just opening the bell) counts as "not interested". When the owner has
dismissed 3 of the last 4 messages of one kind (budget check-ins,
insights, tips...), MIA takes a `PAUSE_DAYS` break from that kind,
logged like any other decision, reported by "what didn't you tell me",
and ended early with "you can tell me about budget again" or Settings.
Urgent messages are never paused.

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

PAUSE_DAYS = 14
_PAUSE_LOOKBACK = 4  # the last this-many messages of a kind...
_PAUSE_DISMISSED = 3  # ...of which this many were dismissed
_DISMISS_COUNTS_WITHIN = timedelta(days=2)  # a message closed weeks later isn't a reaction to it


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
    paused: dict = field(default_factory=dict)  # topic -> until (datetime), from paused_topics()


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


def paused_topics(log: list[dict], now: datetime, resumed: Optional[dict] = None) -> dict:
    """Pure logic. topic -> until (datetime) for kinds of message the
    owner keeps dismissing. `resumed`: topic -> ISO time the owner ended
    a break; dismissals before it don't count any more."""
    resumed = resumed or {}
    by_topic: dict[str, list[dict]] = {}
    for entry in log:
        if entry.get("action") != ACT or entry.get("urgency") == URGENT or not entry.get("topic"):
            continue
        if entry.get("at", "") <= resumed.get(entry["topic"], ""):
            continue
        by_topic.setdefault(entry["topic"], []).append(entry)
    paused = {}
    for topic, entries in by_topic.items():
        last = sorted(entries, key=lambda e: e.get("at", ""))[-_PAUSE_LOOKBACK:]
        dismissals = []
        for entry in last:
            sent_at, dismissed_at = _parse(entry.get("at", "")), _parse(entry.get("dismissed_at", ""))
            if sent_at and dismissed_at and dismissed_at - sent_at <= _DISMISS_COUNTS_WITHIN:
                dismissals.append(dismissed_at)
        if len(dismissals) >= _PAUSE_DISMISSED:
            until = max(dismissals) + timedelta(days=PAUSE_DAYS)
            if until > now:
                paused[topic] = until
    return paused


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
        until = state.paused.get(candidate.topic)
        if until is not None:
            decisions.append(Decision(candidate, DROP, f"you dismissed the last few, so I'm taking a break from these until {until:%b %d}"))
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

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or the
        # shared data/ folder by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _LOG_FILE.parent
        self._log_file = self.data_dir / _LOG_FILE.name if data_dir is not None else _LOG_FILE
        self.context = context
        self._log: list[dict] = []
        self._pending: list[dict] = []
        self._resumed: dict = {}  # topic -> ISO time the owner ended a break
        self.clock = datetime.now  # replaceable in tests
        self._load()
        events = getattr(context, "events", None)
        if events is not None:
            events.subscribe("notification.dismissed", self._on_notification_dismissed)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._log_file.exists():
            return
        try:
            data = json.loads(self._log_file.read_text(encoding="utf-8"))
            self._log = list(data.get("log", []))
            self._pending = list(data.get("pending", []))
            self._resumed = dict(data.get("resumed", {}))
        except (json.JSONDecodeError, OSError, AttributeError):
            log.exception("communication_log.json unreadable — starting fresh.")

    def _save(self, now: datetime) -> None:
        cutoff = (now - timedelta(days=_KEEP_LOG_DAYS)).isoformat()
        self._log = [e for e in self._log if e.get("at", "") >= cutoff]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._log_file, json.dumps({"log": self._log, "pending": self._pending, "resumed": self._resumed},
                                                indent=2))

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
        return GateState(sent=sent, user_busy=self._user_busy(now), paused=paused_topics(self._log, now, self._resumed))

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
        notification_ids: dict[int, str] = {}  # which notification carried each candidate
        for decision in decisions:
            if decision.action == ACT and decision.delivered_as == "alone" and notifications is not None:
                c = decision.candidate
                sent = notifications.notify(title=c.title, message=c.message, level=c.level, source=c.source)
                notification_ids[id(c)] = getattr(sent, "notification_id", "") or ""
        if digest_members and notifications is not None:
            title, message = compose_digest(digest_members)
            sent = notifications.notify(title=title, message=message, level="info", source="system")
            for c in digest_members:
                notification_ids[id(c)] = getattr(sent, "notification_id", "") or ""

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
                "notification_id": notification_ids.get(id(c), ""),
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

    # ------------------------------------------------------------------
    # Learning from being ignored
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Stop listening (a replaced store, core/personal_data.py)."""
        events = getattr(self.context, "events", None)
        if events is not None:
            events.unsubscribe("notification.dismissed", self._on_notification_dismissed)

    def _on_notification_dismissed(self, notification_id: str = "", **_kwargs) -> None:
        now = self.clock()
        changed = False
        for entry in self._log:
            if notification_id and entry.get("notification_id") == notification_id and not entry.get("dismissed_at"):
                entry["dismissed_at"] = now.isoformat(timespec="seconds")
                changed = True
        if changed:
            try:
                self._save(now)
            except OSError:
                log.exception("Couldn't save communication_log.json.")

    def paused(self, now: Optional[datetime] = None) -> list[dict]:
        """Kinds of message on a break: [{topic, label, until}], soonest first."""
        now = now or self.clock()
        labels = {e["topic"]: e.get("title", "") for e in self._log if e.get("topic")}
        return sorted(
            ({"topic": t, "label": labels.get(t) or t.replace("_", " "), "until": until}
             for t, until in paused_topics(self._log, now, self._resumed).items()),
            key=lambda p: p["until"],
        )

    def resume(self, topic: str, now: Optional[datetime] = None) -> None:
        """End a break early: past dismissals of this kind stop counting."""
        now = now or self.clock()
        self._resumed[topic] = now.isoformat(timespec="seconds")
        self._save(now)

    def entries_for_day(self, day: Optional[str] = None) -> list[dict]:
        day = day or datetime.now().date().isoformat()
        return [e for e in self._log if e.get("at", "").startswith(day)]

    def pending(self) -> list[dict]:
        return list(self._pending)
