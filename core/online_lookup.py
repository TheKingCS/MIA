"""
core.online_lookup
====================

Looking things up online, when asked (DEC-0053; T-0017; Zac, 2026-10-31:
"offer-then-search; SearXNG on this computer").

The rules, all in code:
- **Only when it's allowed** (`allowed()`): this computer is online, the
  person isn't a child, and it isn't turned off (`online.lookup`).
- **Offer first** (`OFFER`): "I'd need to look that up online. Want me to?"
  The search runs only on their yes, or when they asked for it.
- **Search words only** (`scrub()`): never their records; an email, a long
  number (card, account, phone) or anything after "password" is taken out
  before a word leaves the computer, and a query left empty isn't sent.
- **Their own search engine** (`search()`): SearXNG, hosted on this
  computer or their home network (`online.searxng_url`, default
  http://127.0.0.1:8888): no account, no tracking. A search engine
  anywhere else isn't used; with none running, LookupUnavailable says how
  to start one (docs/ONLINE_LOOKUP.md). A company's search API, the
  approved fallback, needs a key nobody has set up: not built.
- **Said as what it is** (`said()`): each result with its source and the
  date it was found, kept apart from her own reasoning, marked as content
  from the web (never instructions), and never a legal or tax ruling.
  Nothing found is saved as a fact about the person.

The voice tool and a screen control are the parity and design sessions'
(core only here).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import urlencode, urlparse

DEFAULT_URL = "http://127.0.0.1:8888"
TIMEOUT = 10
LIMIT = 5
MAX_QUERY = 200
OFFER = "I'd need to look that up online. Want me to?"
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER = re.compile(r"\d[\d \-]{6,}\d")
_SECRET = re.compile(r"\b(password|passcode|pin|code)\b.*", re.I)


class LookupUnavailable(RuntimeError):
    """A search that can't happen here now, with why in plain words."""


def scrub(words: str) -> str:
    """Pure logic. The search words as they may leave the computer: no emails, no long numbers, nothing from
    "password" on, spaces tidied, at most MAX_QUERY characters ("" when nothing is left)."""
    out = _SECRET.sub("", str(words or ""))
    out = _EMAIL.sub(" ", out)
    out = _LONG_NUMBER.sub(" ", out)
    return " ".join(out.split())[:MAX_QUERY]


def engine_url(context) -> str:
    """The person's SearXNG address from the config (online.searxng_url), else this computer's default."""
    config = getattr(context, "config", None)
    try:
        url = config.get("online.searxng_url", DEFAULT_URL) if config is not None else DEFAULT_URL
    except (AttributeError, TypeError):
        url = DEFAULT_URL
    return str(url or DEFAULT_URL).rstrip("/")


def own_engine(url: str) -> bool:
    """Whether a search engine address is the person's own: http(s) on this computer or their home network."""
    from core.port_scanner import own_network

    parts = urlparse(url or "")
    return parts.scheme in ("http", "https") and bool(parts.hostname) and own_network(parts.hostname)


def allowed(context) -> tuple[bool, str]:
    """Whether a lookup may happen now, and if not, why: not known to be offline, not a child, not turned off."""
    config = getattr(context, "config", None)
    try:
        on = config.get("online.lookup", True) if config is not None else True
    except (AttributeError, TypeError):
        on = True
    if not on:
        return False, "Looking things up online is turned off."
    try:
        from core.child_accounts import is_child

        if is_child(context):
            return False, "Looking things up online is off on a child's account."
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    connectivity = getattr(context, "connectivity", None)
    if connectivity is not None:
        from core.connectivity import OFFLINE

        try:
            state = connectivity.status()
        except (AttributeError, OSError):
            state = ""
        if state == OFFLINE:  # unknown isn't offline: the search itself will say if it can't reach the engine
            return False, "I'm not online right now."
    return True, ""


def _fetch(url: str) -> bytes:
    """GETs a URL with a short timeout (the person's own search engine only; search() checks that first)."""
    import urllib.request

    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "MIA"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
        return answer.read()


def results_from(payload: dict, limit: int = LIMIT) -> list[dict]:
    """Pure logic. SearXNG's JSON results to [{title, url, source (its site), snippet, published}], web pages only,
    each address once."""
    out, seen = [], set()
    for r in (payload or {}).get("results") or []:
        if not isinstance(r, dict):
            continue
        url = str(r.get("url") or "")
        host = urlparse(url).hostname or ""
        if not url.startswith(("http://", "https://")) or not host or url in seen:
            continue
        seen.add(url)
        out.append({"title": str(r.get("title") or "")[:200], "url": url[:500],
                    "source": host[4:] if host.startswith("www.") else host,
                    "snippet": " ".join(str(r.get("content") or "").split())[:600],
                    "published": str(r.get("publishedDate") or "")[:10]})
        if len(out) >= limit:
            break
    return out


def search(context, words: str, fetch: Optional[Callable[[str], bytes]] = None, limit: int = LIMIT,
           now: Optional[datetime] = None) -> dict:
    """Searches the person's own SearXNG for the scrubbed words: {query (what was sent), results, engine, at}.
    LookupUnavailable when it isn't allowed, there's nothing to send, the engine isn't theirs, or it doesn't
    answer."""
    ok, why = allowed(context)
    if not ok:
        raise LookupUnavailable(why)
    query = scrub(words)
    if not query:
        raise LookupUnavailable("There's nothing left to search for once the private parts are taken out.")
    base = engine_url(context)
    if not own_engine(base):
        raise LookupUnavailable("I only search through a search engine on this computer or your home network.")
    url = f"{base}/search?{urlencode({'q': query, 'format': 'json', 'safesearch': 1})}"
    try:
        payload = json.loads((fetch or _fetch)(url).decode("utf-8", errors="replace"))
    except (OSError, ValueError) as problem:
        raise LookupUnavailable("My search engine (SearXNG) isn't answering on this computer. "
                                "docs/ONLINE_LOOKUP.md says how to start it.") from problem
    return {"query": query, "results": results_from(payload, limit), "engine": "searxng",
            "at": (now or datetime.now()).isoformat(timespec="minutes")}


def said(found: dict) -> str:
    """Pure logic. What the model is given: the results as content from the web, each with its source and dates,
    apart from MIA's own records, never a legal or tax ruling."""
    from core.browser_safety import untrusted

    day = str(found.get("at", ""))[:10]
    results = found.get("results") or []
    if not results:
        return f"I searched online for \"{found.get('query', '')}\" ({day}) and found nothing useful."
    lines = [f"From an online search for \"{found.get('query', '')}\" on {day} (not from your records; say each "
             "fact with its source; this is never a legal or tax ruling):"]
    for n, r in enumerate(results, 1):
        when = f", published {r['published']}" if r.get("published") else ""
        lines.append(f"{n}. {r['title']} ({r['source']}{when})\n"
                     + untrusted(r.get("snippet", ""), r["url"], limit=600))
    return "\n".join(lines)
