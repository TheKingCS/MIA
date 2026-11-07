"""
core.web_browser
==================

The Browser screen's data (DEC-0117, 2026-11-07): MIA's own browser as the
person sees it on the web, so held steps and taught tasks aren't only
reachable by talking to her.

- `screen()`: the page her browser is on; the steps waiting for the
  person's OK, each with why it waits, its site and whether there's a
  screenshot (approved or cancelled through the action contract's own
  proposal, `browser.commit`); whether she's learning a task right now; and
  each taught task with its steps, how practised it is and how its last
  run went.
- `shot_path()`: a waiting step's screenshot, only from her own shots
  folder, so a request can't name any other file.

Nothing here changes anything: running or forgetting a task is the
`browser.run_task` / `browser.forget_task` actions
(core/assistant_browser_actions.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from core.logger import get_logger

log = get_logger(__name__)


def _session(context):
    """The person's browser session, or None where MIA has no browser."""
    from core.browser import browser_for

    try:
        return browser_for(context)
    except Exception:
        log.exception("Browser screen: no session")
        return None


def _still_waiting(context) -> set:
    """The ids of this person's proposals still waiting for a decision (a held step cancelled on screen is gone)."""
    actions = getattr(context, "actions", None)
    if actions is None:
        return set()
    from core.person_settings import person_id

    return {p.proposal_id for p in actions.pending(person_id(context))}


def screen(context) -> dict:
    """The Browser screen: the open page, the steps waiting for the person, the task being learned, and the taught
    tasks. Not available where MIA has no browser."""
    from core.browser_routines import describe, state_of, step_words

    session = _session(context)
    if session is None:
        return {"available": False}
    waiting_ids = _still_waiting(context)
    session._expire()
    waiting = []
    for pending in sorted(session.pending.values(), key=lambda p: p.at, reverse=True):
        if pending.proposal_id and pending.proposal_id not in waiting_ids:
            continue
        waiting.append({"id": pending.pending_id, "proposal_id": pending.proposal_id, "summary": pending.summary(),
                        "why": pending.why, "site": urlparse(pending.page_url).netloc or pending.page_title,
                        "shot": bool(pending.screenshot and Path(pending.screenshot).is_file())})
    store = getattr(context, "browser_routines", None)
    tasks = []
    for routine in (store.all() if store is not None else []):
        runs = routine.get("runs", [])
        last = runs[-1] if runs else None
        tasks.append({"id": routine["id"], "name": routine["name"], "start": routine.get("start", ""),
                      "state": state_of(routine), "summary": describe(routine),
                      "steps": [step_words(s) for s in routine["steps"]],
                      "last": ({"at": last.get("at", ""), "clean": last.get("clean", False),
                                "note": last.get("note", "")} if last else None)})
    page = session.page
    return {
        "available": True,
        "open": {"title": page.title, "url": page.url} if session.driver is not None and page.url else None,
        "learning": (session.teaching or {}).get("name"),
        "waiting": waiting,
        "tasks": tasks,
    }


def shot_path(context, pending_id: str) -> Optional[Path]:
    """A waiting step's screenshot, only when it sits in her own shots folder; None otherwise."""
    session = _session(context)
    pending = session.pending.get(pending_id) if session is not None else None
    if pending is None or not pending.screenshot:
        return None
    folder = (session.profile_dir.parent / "browser_shots").resolve()
    path = Path(pending.screenshot).resolve()
    if not path.is_relative_to(folder) or not path.is_file():
        return None
    return path
