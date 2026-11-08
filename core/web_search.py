"""
core.web_search
=================

Search on the web (Ctrl+K or "/" on any page; the Shell row in
docs/WEB_PARITY.md). The desktop's Ctrl+K searches apps, profiles and what a
few Qt modules registered; the web searches every kind of record MIA keeps,
through the catalog core/links.py already has (`links.KINDS`: assets, bills,
recipes, people, projects, waypoints, journal titles and the rest), each in
the signed-in person's own view.

- `score(name, words)` (pure): how well a name matches the words typed:
  every word must be in it; the whole query at the start beats a word at a
  word's start beats a word inside one.
- `search(context, query)`: the best matches, each with its kind, a line of
  detail and the page that shows it (`PAGES`: an id goes into the link where
  the page opens one record, like asset.html?id=). A kind with no web page
  isn't searched.

Apps are matched in the browser (the frame already has the person's apps);
the private journal is never searched (its words are encrypted).
"""

from __future__ import annotations

import re
from typing import Optional

LIMIT = 12
MIN_CHARS = 2

# Each record kind's web page; "{id}" is filled with the record's id for pages that open one record.
PAGES = {
    "property": "real-estate.html", "asset": "asset.html?id={id}", "maintenance_task": "maintenance.html",
    "bill": "money.html", "debt": "money.html", "income_source": "money.html", "business": "money.html",
    "project": "projects.html", "task": "projects.html", "intent": "why.html", "mission": "missions.html",
    "skill": "skills.html", "person": "people.html", "pet": "people.html", "recipe": "recipe.html?id={id}",
    "calendar_event": "calendar.html", "inventory_item": "toolbox.html", "component": "workshop.html",
    "material": "workshop.html", "product": "workshop.html", "job": "workshop.html", "craft_recipe": "workshop.html",
    "waypoint": "navigation.html", "trip": "expeditions.html", "expedition": "expeditions.html",
    "textbook": "classroom.html", "energy_source": "power.html", "journal_entry": "journal.html",
    "reward": "shop.html", "script": "field-kit.html", "place": "places.html", "obligation": "compliance.html",
    "policy": "insurance.html", "customer": "business.html", "flock": "flock.html",
}
_WORD = re.compile(r"[a-z0-9]+")


def words_of(text: str) -> list[str]:
    """Pure logic. The lowercase words in some text."""
    return _WORD.findall((text or "").lower())


def score(name: str, words: list[str]) -> int:
    """Pure logic. How well `name` matches the query's words: 0 when any word is missing; otherwise higher for the
    whole query at the start (300), then per word, one starting a word in the name (20) over one inside a word (5),
    and a shorter name breaks ties."""
    low = (name or "").lower()
    if not words or not all(w in low for w in words):
        return 0
    total = 300 if low.startswith(" ".join(words)) else 0
    starts = set()
    for m in _WORD.finditer(low):
        starts.add(m.start())
    for w in words:
        total += 20 if any(low.startswith(w, s) for s in starts) else 5
    return total + max(0, 40 - len(low)) // 4


def _detail(kind_label: str, record) -> str:
    """One line under a result: what kind of thing it is, and a date or category when the record has one."""
    extra = ""
    for attr in ("category", "date", "due_date", "status"):
        value = getattr(record, attr, None)
        if isinstance(value, str) and value.strip():
            extra = value.strip()[:24]
            break
    return kind_label[:1].upper() + kind_label[1:] + (f" · {extra}" if extra else "")


def search(context, query: str, limit: int = LIMIT, kinds: Optional[list[str]] = None) -> dict:
    """The person's records whose names match `query`, best first: {"query", "results": [{title, kind, detail,
    href}]}; no results for fewer than MIN_CHARS letters."""
    from core.links import KINDS, _records

    words = words_of(query)
    if len("".join(words)) < MIN_CHARS:
        return {"query": query, "results": []}
    found = []
    for kind_name in kinds or PAGES:
        kind = KINDS.get(kind_name)
        if kind is None or kind_name not in PAGES:
            continue
        for record in _records(context, kind):
            name = str(getattr(record, kind.name_attr, "") or "").strip()
            points = score(name, words)
            if points:
                record_id = str(getattr(record, kind.id_attr, ""))
                found.append((points, name.lower(), {
                    "title": name, "kind": kind_name, "detail": _detail(kind.label, record),
                    "href": PAGES[kind_name].replace("{id}", record_id)}))
    found.sort(key=lambda f: (-f[0], f[1]))
    return {"query": query, "results": [f[2] for f in found[:limit]]}
