"""
core.web_lookup
=================

Look It Up Online on the web (web/lookup.html; DEC-0053, T-0017's screen control; core/online_lookup.py is the
engine). Typing words and pressing Search is the person asking, so the search runs then: only the scrubbed words leave
the computer, through their own SearXNG, and the page shows exactly what was sent, each result with its site and date,
marked as from the web and never a ruling.

`screen(context)` is the page before a search: whether a lookup is allowed now (and why not), the search engine it
uses, and the rules in a line. `look(context, words)` runs one search and returns {query, results, at} or {problem}.
Nothing is kept: a result isn't saved as a fact about the person.
"""

from __future__ import annotations

RULES = ("Only your search words leave this computer, never your records; emails, long numbers and anything after "
         "\"password\" are taken out first. It searches through your own search engine, with no account and no "
         "tracking, and nothing it finds is saved as a fact about you.")


def screen(context) -> dict:
    """The page before a search: allowed now or why not, the engine's address (is it on this computer or the home
    network), and the rules."""
    from core.online_lookup import allowed, engine_url, own_engine

    ok, why = allowed(context)
    url = engine_url(context)
    return {"allowed": ok, "why": why, "engine": url, "own_engine": own_engine(url), "rules": RULES,
            "setup": "docs/ONLINE_LOOKUP.md"}


def look(context, words: str, fetch=None) -> dict:
    """One search, as asked: {query (what was actually sent), results [{title, url, source, snippet, published}], at},
    or {problem} with her sentence when it can't run (not allowed, nothing left to send, the engine not answering)."""
    from core.online_lookup import LookupUnavailable, search

    try:
        found = search(context, words, fetch=fetch)
    except LookupUnavailable as problem:
        return {"problem": str(problem)}
    return {"query": found["query"], "results": found["results"], "at": found["at"]}
