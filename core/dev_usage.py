"""
core.dev_usage
================

What each development model was used for, and when it ran out (DEC-0079,
Zac 2026-11-03: "understanding usage and delegating tasks based on time
available to use each model so that the dev team doesnt have to sit idle
when one model is unavailable"; review section 6.4).

Every provider call records who, why, which task, how long, how much text
went each way, and how it ended: ok, error, or *limit* (a usage limit,
recognized from what the CLI said, with the reset time when it gave one).
Never the prompt or the answer. Kept on this PC (`core/dev_store.py`,
`data/dev/usage/`). `state()` turns the record into what the runner and the
board need: is this provider resting, and until when.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.dev_store import DEV_DATA, DevStore

# What the CLIs say when a plan's usage runs out. An error that isn't one of
# these stays an error: a broken provider mustn't look like a resting one.
LIMIT = re.compile(r"usage limit|rate[- ]limit|limit (?:reached|exceeded)|quota|too many requests|\b429\b"
                   r"|out of (?:credits|premium requests)|hit your (?:usage )?limit", re.I)
RESETS = re.compile(r"(?:resets?|try again|available again)\s*(?:at|in)?\s*"
                    r"(?:(?P<n>\d+)\s*(?P<unit>minutes?|mins?|hours?|hrs?)\b"
                    r"|(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<half>am|pm)?)", re.I)
GUESS = timedelta(minutes=30)  # when a limit doesn't say when it lifts: look again after this


def _store() -> DevStore:
    return DevStore(DEV_DATA / "usage")


def outcome(error: str) -> str:
    """Pure logic. "limit" when the text is a usage limit, else "error"."""
    return "limit" if LIMIT.search(error or "") else "error"


def reset_at(text: str, now: datetime) -> Optional[datetime]:
    """Pure logic. When a limit message says it lifts ("resets 3pm", "try again in 20 minutes"), in UTC.
    A clock time is the computer's own local time, the next one after now."""
    m = RESETS.search(text or "")
    if not m:
        return None
    if m.group("n"):
        n, unit = int(m.group("n")), m.group("unit").lower()
        return now + (timedelta(hours=n) if unit.startswith("h") else timedelta(minutes=n))
    hour, minute, half = int(m.group("hour")), int(m.group("minute") or 0), (m.group("half") or "").lower()
    if half == "pm" and hour < 12:
        hour += 12
    if half == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    local = now.astimezone()
    when = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if when <= local:
        when += timedelta(days=1)
    return when.astimezone(timezone.utc)


def record(provider: str, purpose: str, seconds: float, sent: int, received: int, error: str = "",
           task: str = "", store: Optional[DevStore] = None, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    ended = "ok" if not error else outcome(error)
    entry = {"at": now.isoformat(timespec="seconds"), "provider": provider, "purpose": purpose, "task": task,
             "seconds": round(seconds, 1), "sent": sent, "received": received, "outcome": ended}
    if ended == "limit":
        lifts = reset_at(error, now)
        entry["resets"] = (lifts or now + GUESS).isoformat(timespec="seconds")
        entry["reset_said"] = bool(lifts)
    if ended == "error":
        entry["error"] = error[-200:]
    (store or _store()).append(entry)
    return entry


def state(provider: str, store: Optional[DevStore] = None, now: Optional[datetime] = None,
          recent: int = 400) -> dict:
    """Where a provider stands from its latest calls: resting until a time, or ready."""
    now = now or datetime.now(timezone.utc)
    calls = [e for e in (store or _store()).tail(recent) if e.get("provider") == provider]
    last_limit = next((e for e in reversed(calls) if e.get("outcome") == "limit"), None)
    since = [e for e in calls if last_limit and e["at"] > last_limit["at"] and e.get("outcome") == "ok"]
    if last_limit and not since:
        until = datetime.fromisoformat(last_limit["resets"])
        if until > now:
            return {"state": "cooling", "until": last_limit["resets"], "said": last_limit.get("reset_said", False),
                    "calls": len(calls)}
    return {"state": "ready", "until": "", "calls": len(calls),
            "last": calls[-1]["at"] if calls else ""}
