"""
core.web_connections
======================

Connections (web/connections.html, DEC-0146): the ties MIA noticed between something said in passing and something
started weeks ago (core/connections.py), so the person can see what she's holding and say "don't bring that up". Shown:
the ones waiting to be raised (what was said, when, what it ties into and how), what happened to the recent ones
(brought up, let go, or declined), and the things she's been asked never to tie into, each with Allow Again.

Actions (approved and undoable, since the store writes through atomic_write_text):

- `connection.decline`: this connection settled as declined, and its thing added to the quiet list, so she never raises
  it again until it's allowed.
- `connection.allow`: a thing off the quiet list.

`screen(context)` is what `/api/connections` serves.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

KIND_WORDS = {"project": "project", "intent": "goal", "mission": "mission", "idea": "idea you set aside",
              "dropped_goal": "goal you set aside"}
STATE_WORDS = {"open": "Waiting", "mentioned": "Brought up", "expired": "Let go", "declined": "Not to be raised"}
RECENT = 12


def _book(context):
    """The person's ConnectionBook, or None."""
    return getattr(context, "connections", None)


def _row(c: dict) -> dict:
    """One connection as the page shows it: what was said, what it ties into, how, its state in words."""
    how = (f"through the {c['through']}" if c.get("via") == "link" and c.get("through")
           else ("both about " + ", ".join(c.get("shared") or [])) if c.get("shared") else "")
    return {"id": c["id"], "ref": c["ref"], "said": c.get("said", ""), "noticed": (c.get("noticed_at") or "")[:10],
            "name": c.get("name", ""), "kind": KIND_WORDS.get(c.get("kind", ""), c.get("kind", "")),
            "status": c.get("status", ""), "since": (c.get("since") or "")[:10], "how": how,
            "state": c.get("state", ""), "state_word": STATE_WORDS.get(c.get("state", ""), c.get("state", ""))}


def screen(context, today: Optional[date] = None) -> dict:
    """Connections: waiting ones newest first, the recent settled ones, and the quiet list (each thing with the name
    it had when declined)."""
    book = _book(context)
    if book is None:
        return {"available": False}
    waiting = [_row(c) for c in reversed(book.open_ones())]
    settled = [_row(c) for c in reversed(book.items) if c.get("state") != "open"][:RECENT]
    names = {}
    for c in book.items:
        names[c["ref"]] = c.get("name", "")
    quiet = [{"ref": ref, "name": names.get(ref, ref)} for ref in getattr(book, "quiet", [])]
    return {"available": True, "waiting": waiting, "recent": settled, "quiet": quiet}


def _need(context, params):
    """The connection the params name; ActionError when it isn't there."""
    book = _book(context)
    found = book.get(str(params.get("connection_id") or "")) if book is not None else None
    if found is None:
        raise ActionError("That connection isn't here.")
    return found


def _describe_decline(context, params) -> str:
    """The approval sentence for `connection.decline`."""
    c = _need(context, params)
    return f"Don't bring up “{c.get('name', '')}” again"


def _decline(context, params) -> str:
    """Does `connection.decline`."""
    c = _need(context, params)
    _book(context).decline(c["id"])
    return f"I won't tie things to “{c.get('name', '')}” again. Allow it on Connections any time."


def _describe_allow(context, params) -> str:
    """The approval sentence for `connection.allow`."""
    book = _book(context)
    ref = str(params.get("ref") or "")
    if book is None or ref not in getattr(book, "quiet", []):
        raise ActionError("That isn't on the quiet list.")
    name = next((c.get("name", "") for c in book.items if c["ref"] == ref), ref)
    return f"Let MIA tie things to “{name}” again"


def _allow(context, params) -> str:
    """Does `connection.allow`."""
    _describe_allow(context, params)
    _book(context).allow(str(params["ref"]))
    return "Allowed again. She'll only bring it up when it fits."


CONNECTION_ACTIONS = {a.kind: a for a in (
    ActionType("connection.decline", "Don't Bring It Up", {"connection_id": "the connection"},
               _describe_decline, _decline, child_ok=True),
    ActionType("connection.allow", "Allow Again", {"ref": "the thing, as kind:id"}, _describe_allow, _allow,
               child_ok=True),
)}
ACTION_TYPES.update(CONNECTION_ACTIONS)


def latest(context) -> Optional[dict]:
    """The connection "that" most likely means in "don't bring that up": the newest one brought up, else the newest
    still waiting; None when there's none."""
    book = _book(context)
    if book is None:
        return None
    for state in ("mentioned", "open"):
        found = [c for c in book.items if c.get("state") == state]
        if found:
            return found[-1]
    return None
