"""
core.needs_now
================

The front of "catch me up" (brainstorm 2.1, `docs/future/JARVIS_BRAINSTORM.md`; Zac, 2026-11-23: "aware"): before
the life state's wins and friction, what needs him first, what she's holding for him, and what she did on her own,
each from the record it lives in, worked out in code; the model only says it.

- **Needs you now** (`gather`), most pressing first: the greenhouse node's open critical then warning alerts
  (core/greenhouse_link.py, once she has taken it over), what tonight's weather means for his garden and flock
  (core/weather_watch.py, from the forecast already kept, never fetched here), and an MIA OS update waiting for his
  restart (core/update_notice.py, Q-114).
- **Holding for you**: the messages the communication gate is keeping until a better moment (its `pending`), by title.
- **On my own since yesterday**: the changes she made herself in the last day and not undone (the lasting change
  history, core/change_history.py, `by == "mia"`), newest first with their time, and how to take one back.

`describe` puts it in words: "" when there's nothing in any of the three, so a quiet day's report starts with the
life state as before. Each source that can't be read is left out, never the whole answer.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

ON_HER_OWN_HOURS = 24
SHOWN = 5  # at most this many of each, then "and N more"


def _alerts(context) -> list[str]:
    """The greenhouse node's open critical and warning alerts, critical first, in its own words."""
    link = getattr(context, "greenhouse_link", None)
    if link is None or not getattr(link, "taken_over", False):
        return []
    open_ = [a for a in (getattr(link, "state", None) or {}).get("alerts") or []
             if a.get("severity") in ("critical", "warning") and not a.get("resolved")]
    open_.sort(key=lambda a: 0 if a.get("severity") == "critical" else 1)
    return [f"Greenhouse ({a.get('severity')}): {str(a.get('message') or a.get('source') or 'an alert').strip()}"
            for a in open_]


def _weather(context, now: datetime) -> list[str]:
    """What tonight's weather means for his garden and flock, from the kept forecast."""
    from core import weather, weather_watch

    kept = weather.card(context)
    if not kept.get("text"):
        return []
    return [c["text"] for c in weather_watch.watch(context, now.date(), forecast=kept)]


def _update() -> list[str]:
    """An MIA OS update waiting for his restart."""
    from core.update_notice import waiting

    return ["An MIA OS update is ready; it goes in at your next restart (Settings, Restart To Update, to do it now)."] \
        if waiting() else []


def _held(context) -> list[str]:
    """The titles of the messages the gate is keeping for a better moment."""
    gate = getattr(context, "communication", None)
    if gate is None:
        return []
    return [str(p.get("title") or p.get("topic") or "a message") for p in gate.pending()]


def _on_her_own(context, now: datetime) -> list:
    """The changes she made herself in the last day, not undone, newest first (change history entries)."""
    from core import change_history
    from core.person_settings import person_id

    found = change_history.find(person_id(context), now - timedelta(hours=ON_HER_OWN_HOURS), now)
    return [e for e in found if e.by == "mia"]


def gather(context, now: Optional[datetime] = None) -> dict:
    """{"now": [sentences], "held": [titles], "own": [change history entries]}, each source that fails left empty."""
    now = now or datetime.now()
    out = {"now": [], "held": [], "own": []}
    for key, read in (("now", lambda: _alerts(context)), ("now", lambda: _weather(context, now)),
                      ("now", _update), ("held", lambda: _held(context)), ("own", lambda: _on_her_own(context, now))):
        try:
            out[key].extend(read())
        except Exception:  # noqa: BLE001 - one record that can't be read never stops the report
            log.exception("Needs now: a source couldn't be read")
    return out


def _more(items: list, said: list) -> str:
    """Pure logic. "; and 3 more" when the list was cut."""
    return f"; and {len(items) - len(said)} more" if len(items) > len(said) else ""


def describe(found: dict) -> str:
    """Pure logic. The three parts in words ("" when all are empty): needs you now, what she's holding, what she did
    on her own with how to take it back."""
    from core.change_history import say

    parts = []
    now = found.get("now") or []
    if now:
        rest = len(now) - SHOWN
        parts.append("Needs you now: " + " ".join(s if s.endswith(".") else s + "." for s in now[:SHOWN])
                     + (f" And {rest} more." if rest > 0 else ""))
    held = found.get("held") or []
    if held:
        parts.append(f"I'm holding {len(held)} message{'s' if len(held) != 1 else ''} for a better moment: "
                     + ", ".join(held[:SHOWN]) + _more(held, held[:SHOWN]) + ".")
    own = found.get("own") or []
    if own:
        parts.append("On my own since yesterday: " + say(own, SHOWN) + ". Say \"undo that\" or \"undo what you did "
                     "this morning\" to take one back.")
    return " ".join(parts)
