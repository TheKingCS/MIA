"""
core.show_source
==================

"Show me where it says that" (Jarvis brainstorm 3.2; Zac, 2026-11-22: "really good at reading through these references
and talking naturally but factually about what knowledge they contain"): after she answers from her offline library,
the page she read opens on the Knowledge page, at that article, so he can read it himself.

- **What she read** (`remember`): each library lookup in a turn (core/tool_loop.py, `LIBRARY_TOOLS`) names its sources
  as `From <pack>, "<article>"` then `ref: <pack|path|page>` (core/offline_library.look_up); `sources_in` reads them
  out of the result and `remember` keeps the last few for the person (in memory only, for this run: never a record).
- **Showing it** (`wants_source`, `reply`): words like "show me where it says that", "open that article", "show me the
  source" open `knowledge.html?ref=...` (web/knowledge.js reads it and shows the article); with nothing read lately
  they aren't taken, so the turn goes on as usual. A PDF's page is named with its page number (the page opens where
  the Knowledge page can show it).
"""

from __future__ import annotations

import re
import threading
from typing import Optional
from urllib.parse import quote

KEEP = 4
_SOURCE = re.compile(r'From (?P<pack>[^\n]+?), "(?P<article>[^"\n]+)"\s*\nref: (?P<ref>[^\s]+)')
_ASKS = re.compile(r"\b(?:show|open|let me see|pull up|bring up)\b.{0,25}\b(?:where (?:it|that|you) (?:says?|said|read)|"
                   r"(?:that|the|your) (?:source|article|page|guide|reference)|it)\b|\bwhere does it say\b|"
                   r"\bwhere did you (?:read|get|find) that\b", re.I)
_lock = threading.Lock()
_read: dict = {}  # person -> [{pack, article, ref}], newest first


def sources_in(text: str) -> list[dict]:
    """Pure logic. The sources a library result names, in order: each {pack, article, ref}."""
    return [m.groupdict() for m in _SOURCE.finditer(str(text or ""))]


def remember(person: Optional[str], found: list[dict]) -> None:
    """Keeps the sources she just read for this person, newest first (KEEP at most)."""
    if not found:
        return
    with _lock:
        kept = [s for s in _read.get(person, []) if s["ref"] not in {f["ref"] for f in found}]
        _read[person] = (list(found) + kept)[:KEEP]


def last(person: Optional[str]) -> Optional[dict]:
    """The source she read most recently for this person, or None."""
    with _lock:
        got = _read.get(person) or []
        return dict(got[0]) if got else None


def wants_source(prompt: str) -> bool:
    """Pure logic. Whether the words ask to see where her answer came from."""
    text = " ".join(str(prompt or "").split())
    return bool(text) and len(text) < 120 and bool(_ASKS.search(text)) and \
        bool(re.search(r"\b(?:says?|said|source|article|page|guide|reference|read|where)\b", text, re.I))


def reply(person: Optional[str], prompt: str) -> Optional[tuple[str, str]]:
    """(what she says, the page to open) when he asks to see her source and she has read one lately; else None."""
    if not wants_source(prompt):
        return None
    source = last(person)
    if source is None:
        return None
    page = (source["ref"].split("|") + ["", "", "0"])[2]
    where = f", page {int(page) + 1}" if page.isdigit() and int(page) > 0 else ""
    said = f"Here's where it says it: \"{source['article']}\" in {source['pack']}{where}."
    return said, f"knowledge.html?ref={quote(source['ref'], safe='')}"


def reset() -> None:
    """Forgets every source read (tests)."""
    with _lock:
        _read.clear()
