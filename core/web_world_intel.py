"""
core.web_world_intel
======================

The World page (DEC-0170, W1): what World Intelligence found, the watches, and the sources it reads, assembled here
so the web only draws (DEC-0017) and the voice tools say the same thing (DEC-0125).

`world_page(context)`: whether it's on; the finds, best first (new ones, then saved), each with its source named,
its link, when it was found and published, which watches found it and why; the watches with their words, areas,
how often, last run, what they found and any source waiting for the person; and the areas a watch can read. Changes
are actions in core/world_intel_actions.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

SHOWN = 60  # at most this many finds on the page


def _find(d, names: dict, now: datetime) -> dict:
    """One find as the page shows it, always with its source."""
    from core.web_changes import when_words  # here: core.web_changes imports the action contract, which loads pages

    return {"id": d.discovery_id, "title": d.title, "link": d.link, "summary": d.summary,
            "source": d.source_name + (f" ({d.site})" if d.site else ""), "status": d.status,
            "found": when_words(d.found_at, now), "published": d.published[:10],
            "watches": [names.get(w, "") for w in d.watch_ids if names.get(w)], "why": list(d.why)}


def _watch(w, now: datetime) -> dict:
    """One watch as the page shows it."""
    from core import world_sources
    from core.web_changes import when_words

    return {"id": w.watch_id, "name": w.name, "words": w.words, "made_by": w.made_by, "reason": w.reason,
            "areas": [world_sources.AREA_NAMES.get(a, a) for a in w.areas] or ["every source"],
            "search": w.search, "every_hours": w.every_hours, "max_price": w.max_price, "paused": w.paused,
            "last_run": when_words(w.last_run, now) if w.last_run else "not yet", "found": w.found,
            "refused": [getattr(world_sources.source(s), "name", s) for s in w.refused]}


def world_page(context, now: Optional[datetime] = None) -> dict:
    """The World page's data (see the module's opening)."""
    from core import world_sources
    from core.world_intel import is_on

    now = now or datetime.now()
    book = getattr(context, "world_intel", None)
    if book is None:
        return {"available": False}
    names = {w.watch_id: w.name for w in book.watches}
    order = {"new": 0, "saved": 1}
    finds = sorted((d for d in book.discoveries if d.status in order),
                   key=lambda d: (order[d.status], -d.score, d.found_at), reverse=False)
    return {"available": True, "on": is_on(context),
            "finds": [_find(d, names, now) for d in finds[:SHOWN]],
            "counts": {s: sum(1 for d in book.discoveries if d.status == s) for s in ("new", "saved", "not_for_me")},
            "watches": [_watch(w, now) for w in book.watches],
            "areas": [{"id": a, "name": world_sources.AREA_NAMES[a],
                       "sources": [s.name for s in world_sources.for_areas([a])]} for a in world_sources.AREAS]}


def found_sentence(page: dict, limit: int = 3) -> str:
    """What MIA says for "what have you found?": the best new finds, each with its source, or why there are none."""
    if not page.get("available"):
        return "World Intelligence isn't on this MIA."
    new = [f for f in page["finds"] if f["status"] == "new"]
    if not page["watches"]:
        return "I'm not watching for anything yet. Tell me what to watch for."
    if not new:
        return ("Nothing new from your watches." if page["on"]
                else "World Intelligence is off, so I'm not looking. Say \"turn on world intelligence\".")
    said = "; ".join(f"{f['title']} (from {f['source']})" for f in new[:limit])
    more = f" And {len(new) - limit} more on the World page." if len(new) > limit else ""
    return f"{len(new)} new: {said}.{more}"
