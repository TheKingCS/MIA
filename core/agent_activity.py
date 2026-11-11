"""
core.agent_activity
=====================

The Dashboard's Agent Activity (DEC-0153, Zac 2026-11-11: "All of these"):
what MIA did on her own and what the agents that build her are doing, in
one card, each line opening where it came from.

What it gathers (each source read on its own; one that fails is left out):
- `mine`: her latest changes you can undo (core/web_changes), the ones she
  made, not yours;
- `held`: what she held back today rather than interrupt you
  (core/communication_gate through core/web_comms);
- `made`: the screens she built for you and you published
  (core/creations);
- `team`: the device owner only (core/work_dashboard.allowed): the
  Council's latest messages (core/council) and the development work's
  latest steps (core/work_activity), with who did each.

How: `activity(context, profile_id, now)` returns those lists, each at
most a few lines, newest first; nothing is copied, every line links to its
own page (Recent Changes, Communications, Made by MIA, the Council, the
Development board).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

LINES = 4  # per source


def _safe(name: str, gather) -> list:
    """One source's lines, [] if it fails (logged)."""
    try:
        return list(gather())
    except Exception:  # noqa: BLE001 - one source failing never empties the card
        log.exception("Agent activity: %s failed", name)
        return []


def _mine(context, now: datetime) -> list[dict]:
    """Her latest undoable changes: [{what, when, page}]."""
    from core.web_changes import changes_page

    rows = changes_page(context, now)["undoable"]
    return [{"what": r["what"], "when": r["when"], "page": "changes.html"} for r in rows if r.get("by") == "MIA"][:LINES]


def _held(context) -> list[dict]:
    """What she held back today: [{what, why, page}]."""
    from core.web_comms import _messages

    found = _messages(context)
    return [{"what": h["title"] or h["message"], "why": "waiting for a better moment" if h["waiting"] else "let go",
             "page": "communications.html"} for h in found.get("held", [])][:LINES]


def _made(context) -> list[dict]:
    """The screens she made and you published: [{what, page}], newest first."""
    store = getattr(context, "creations", None)
    if store is None:
        return []
    return [{"what": c["title"], "page": f"made.html?id={c['id']}"} for c in reversed(store.published())][:LINES]


def _team(context, profile_id: str, now: datetime) -> list[dict]:
    """The build team's latest, for the owner only: the Council's messages and the work's steps, merged newest first,
    as [{who, what, when, page}]."""
    from core import work_activity
    from core.web_changes import when_words
    from core.work_dashboard import allowed

    if not allowed(context, profile_id):
        return []
    out = []
    for e in work_activity.events()[-LINES:]:
        out.append({"who": e.get("who", ""), "what": " ".join(x for x in (e.get("task", ""), e.get("detail", "")) if x)
                    or e.get("action", ""), "at": e.get("at", ""), "page": "dev.html"})
    try:
        from core import council

        for m in council._store().tail(LINES):  # read only: council.recent() would bring in the repo's copy first
            out.append({"who": m.get("who", ""), "what": str(m.get("text", ""))[:160], "at": m.get("at", ""),
                        "page": "council.html"})
    except Exception:  # noqa: BLE001 - the Council's store unreadable: the work's steps still show
        log.exception("Agent activity: the Council failed")
    for r in out:  # the work log is in UTC: this computer's own time, so "2:05 PM" means here
        try:
            moment = datetime.fromisoformat(r["at"])
            r["at"] = (moment.astimezone().replace(tzinfo=None) if moment.tzinfo else moment).isoformat()
        except ValueError:
            r["at"] = ""
    out.sort(key=lambda r: r["at"], reverse=True)
    return [{**r, "when": when_words(r["at"], now) if r["at"] else ""} for r in out[:LINES]]


def activity(context, profile_id: Optional[str], now: Optional[datetime] = None) -> dict:
    """The card: {mine, held, made, team, any: whether there's anything to show}."""
    now = now or datetime.now()
    out = {"mine": _safe("her changes", lambda: _mine(context, now)),
           "held": _safe("held back", lambda: _held(context)),
           "made": _safe("made", lambda: _made(context)),
           "team": _safe("the team", lambda: _team(context, profile_id or "", now))}
    out["any"] = any(out[k] for k in ("mine", "held", "made", "team"))
    return out
