"""
core.ambient
==============

MIA's ambient view (DEC-0231; Zac, 2026-11-17, Q-80: "yes", with "MIA should be adaptable and understanding of
available monitors so if I turn one off she flows with just 1"). A screen to glance at, not to work in: shown full
screen on his second monitor by the desktop window (gui/ambient_screens.py), and folded back into Home when that
monitor goes (Home already shows all of it). Served as `/api/ambient`, drawn by `web/ambient.html`.

**What it shows** (`view`), all from Home's own assembler (`core/web_surfaces.dashboard`), so nothing here is new
data or a guess: the date, the weather card, the few things due now (`DUE_SHOWN`), the next one coming, what's
playing, the mission in play, and what she's doing or did lately (Agent Activity's running runs and her own changes),
each kept short. The clock is the page's own; her presence comes on the live stream like every page's orb.
A part that can't be read is left out, never filled in.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DUE_SHOWN = 4  # due now, at most
ACTIVITY_SHOWN = 3  # lines of what she's doing


def view(context, now: Optional[datetime] = None) -> dict:
    """The ambient view's data (see the module's opening): {date, weather, due, next, music, mission, activity,
    briefing}; empty parts as None or []."""
    from core.web_surfaces import dashboard

    try:
        home = dashboard(context, now)
    except Exception:  # noqa: BLE001 - an ambient screen that can't be read shows the clock alone
        log.exception("The ambient view couldn't be put together")
        return {"date": "", "weather": None, "due": [], "next": None, "music": None, "mission": None,
                "activity": [], "briefing": ""}
    return shape(home)


def shape(home: dict) -> dict:
    """Pure logic. The ambient view from Home's data: only what's glanceable, each line short."""
    due = [{"title": d.get("title", ""), "when": d.get("kind") or d.get("when", ""), "time": d.get("time") or ""}
           for d in (home.get("focus") or [])[:DUE_SHOWN] if d.get("title")]
    upcoming = [d for d in (home.get("upcoming") or []) if d.get("title")]
    nxt = {"title": upcoming[0]["title"], "when": upcoming[0].get("kind") or upcoming[0].get("when", ""),
           "time": upcoming[0].get("time") or ""} if upcoming else None
    weather = home.get("weather") or {}
    life = home.get("life") or {}
    mission = home.get("mission")
    activity = home.get("activity") or {}
    doing = [{"what": r.get("what", ""), "status": r.get("status", "")} for r in (activity.get("running") or [])]
    doing += [{"what": r.get("what", ""), "status": "done"} for r in (activity.get("mine") or [])]
    return {
        "date": home.get("date", ""),
        "weather": {"place": weather.get("place"), "text": weather.get("text")} if weather.get("text") else None,
        "due": due,
        "next": nxt,
        "music": life.get("music"),
        "mission": {"name": mission.get("name", ""), "next": mission.get("next", ""), "done": mission.get("done", 0),
                    "total": mission.get("total", 0)} if mission else None,
        "activity": [d for d in doing if d["what"]][:ACTIVITY_SHOWN],
        "briefing": home.get("briefing", ""),
    }
