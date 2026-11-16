"""
core.opportunity
==================

Opportunity scoring and recommendations (Procurement P3, DEC-0172; `docs/mia_os/MIA_OS_PROCUREMENT_PROPOSAL.md`
section 8). A find from World Intelligence that meets one of a project's needs becomes an **opportunity**: the
find, the need it meets, nine dimensions each with its value and the reason for it, and one recommendation.
Everything here is worked out in code from records; the model never scores, and nothing is invented: a dimension
MIA has no record for says "not known", never a guess.

**Which finds:** new or saved finds whose `refs` name an open need (`requirement:<id>`, from core/relevance.py), or
whose watch was made for one.

**The dimensions** (`assess`):
- *project relevance*: the need it meets, its project and its priority;
- *price advantage*: the listing's price (read from its title and summary: only with a currency sign, and only
  when it is the one amount there) judged against the prices MIA has seen
  for the same product (core/price_book.judge): a verified low, usual, high, or "not yet verified" with fewer than
  three seen;
- *compatibility*: the need's specs found in the listing's words: met, partly (some not mentioned), or not stated;
- *quality*: not known (no seller or product records yet);
- *urgency*: the need's needed-by date;
- *geographic accessibility*: not known (no location on finds yet);
- *total cost*: core/price_book.total_cost for the quantity still needed, with each unknown part named;
- *strategic value*: the need's priority as the project set it;
- *confidence*: where the price and the match came from.

**The recommendation** (`recommend`), in order:
- *skip*: the need is already met (on hand or acquired), or the price is over the need's ceiling, or a spec the need
  names is contradicted;
- *wait*: the price is higher than any MIA has seen in 90 days;
- *buy when ready*: a verified saving (lower than every price seen in 90 days), within the ceiling, and every spec
  the need names found;
- *investigate*: everything else (attractive but something unverified).
"Bargain" is never said: a saving is called one only when `judge` verified it.

Nothing here buys, bids or messages anyone (DEC-0172's governed purchasing): an opportunity is read, and acting on
one is the person's.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

RECOMMENDATIONS = ("buy_when_ready", "investigate", "wait", "skip")
SAID = {"buy_when_ready": "Buy when ready", "investigate": "Investigate", "wait": "Wait", "skip": "Skip"}
_ORDER = {r: i for i, r in enumerate(RECOMMENDATIONS)}
_PRIORITY = {"first": "first priority", "soon": "wanted soon", "later": "wanted later", "someday": "someday"}
_SPEC = re.compile(r"[a-z0-9.]+", re.I)
_NO_WORDS = re.compile(r"\b(?:no|not|without|non)[\s-]+([a-z0-9.]+)", re.I)
_PRICE = re.compile(r"[$£€]\s?(\d[\d,]*(?:\.\d{1,2})?)")


def price_in(text: str) -> Optional[float]:
    """Pure logic. A listing's price: the one amount written with a currency sign ("$45", "£ 12.50"). A bare number
    is never taken for one, since listings are full of them ("12V", "1200 rpm"); and a listing with several different
    amounts ("was $80, now $45", "$5 off") has no price MIA can trust, so it gives None."""
    found = amounts_in(text)
    return found[0] if len(found) == 1 else None


def amounts_in(text: str) -> list[float]:
    """Pure logic. Every different amount of money in a listing's words, in order."""
    out = []
    for m in _PRICE.finditer(str(text or "")):
        value = float(m.group(1).replace(",", ""))
        if value not in out:
            out.append(value)
    return out


def _need_of(context, discovery, book) -> Optional[object]:
    """The open need a find meets: one named in its refs, else one its watch was made for; None when neither."""
    reqs = getattr(context, "requirements", None)
    if reqs is None:
        return None
    refs = list(getattr(discovery, "refs", []) or [])
    for w in getattr(book, "watches", []) if book is not None else []:
        if w.watch_id in (discovery.watch_ids or []):
            refs += list(w.refs or [])
    for ref in refs:
        if str(ref).startswith("requirement:"):
            need = reqs.get(str(ref).split(":", 1)[1])
            if need is not None:
                return need
    return None


def _spec_words(specs: str) -> list[str]:
    """Pure logic. The words of a need's specs worth looking for: numbers with their units, and words of three
    letters or more ("12 V", "1200 W" -> ["12v", "1200w"]; "galvanised" stays)."""
    text = re.sub(r"(\d)\s+([a-z]+)", r"\1\2", str(specs or "").lower())
    return [w for w in _SPEC.findall(text) if len(w) >= 3 or any(c.isdigit() for c in w)]


def compatibility(specs: str, text: str) -> dict:
    """Pure logic. The need's specs against a listing's words: {state: met | partly | failed | unstated, found,
    missing, reason}. A spec named after "no", "not" or "without" in the listing is a contradiction (failed)."""
    wanted = _spec_words(specs)
    if not wanted:
        return {"state": "unstated", "found": [], "missing": [], "reason": "the need names no specs"}
    words = re.sub(r"(\d)\s+([a-z]+)", r"\1\2", str(text or "").lower())
    denied = {m.lower() for m in _NO_WORDS.findall(words)}
    have = set(_SPEC.findall(words))
    found = [w for w in wanted if w in have and w not in denied]
    against = [w for w in wanted if w in denied]
    missing = [w for w in wanted if w not in found and w not in against]
    if against:
        return {"state": "failed", "found": found, "missing": missing,
                "reason": "the listing says it isn't " + ", ".join(against)}
    if not missing:
        return {"state": "met", "found": found, "missing": [], "reason": "every spec found: " + ", ".join(found)}
    return {"state": "partly", "found": found, "missing": missing,
            "reason": "not mentioned: " + ", ".join(missing) + (f" (found: {', '.join(found)})" if found else "")}


def recommend(need_met: bool, over_ceiling: bool, compat: str, verdict: str) -> tuple[str, str]:
    """Pure logic. The recommendation and its reason (see the module's opening)."""
    if need_met:
        return "skip", "you already have or ordered what this need asks for"
    if over_ceiling:
        return "skip", "it's over the most you said you'd pay"
    if compat == "failed":
        return "skip", "it doesn't meet the specs you need"
    if verdict == "high":
        return "wait", "it's higher than any price I've seen in 90 days"
    if verdict == "low" and compat == "met":
        return "buy_when_ready", "a verified low price, within your ceiling, and every spec found"
    if verdict == "low":
        return "investigate", "a verified low price, but not every spec is confirmed"
    return "investigate", ("the price isn't verified yet" if verdict in ("too_few", "") else
                           "a usual price; check the details before deciding")


def assess(context, discovery, book=None, now: Optional[datetime] = None) -> Optional[dict]:
    """One find as an opportunity (see the module's opening), or None when it meets no open need. A listing with
    several amounts has no price here, and its price dimension says so."""
    from core import price_book
    from core.region import money

    now = now or datetime.now()
    book = book if book is not None else getattr(context, "world_intel", None)
    need = _need_of(context, discovery, book)
    if need is None:
        return None
    text = f"{discovery.title} {discovery.summary}"
    price = price_in(text)
    still = max(0.0, float(need.quantity or 0) - float(need.have or 0))
    need_met = need.status in ("acquired", "owned", "ordered") or still <= 0
    prices = getattr(context, "prices", None)
    seen = prices.for_product(price_book.product_key(need.item, need.specs)) if prices is not None else []
    verdict = price_book.judge(seen, price, now) if price is not None else {"verdict": "", "said": ""}
    compat = compatibility(need.specs, text)
    ceiling = float(need.max_price or 0)
    over = bool(ceiling and price is not None and price > ceiling)
    rec, why = recommend(need_met, over, compat["state"], verdict["verdict"])

    project = ""
    projects = getattr(context, "projects", None)
    if projects is not None:
        try:
            p = projects.get_project(need.project_id)
            project = getattr(p, "name", "") if p else ""
        except Exception:  # noqa: BLE001 - a project that can't be read is only unnamed
            project = ""
    urgency = "no date set"
    if need.needed_by:
        try:
            days = (date.fromisoformat(need.needed_by[:10]) - now.date()).days
            urgency = (f"needed in {days} day{'s' if days != 1 else ''}" if days >= 0
                       else f"needed {-days} day{'s' if days != -1 else ''} ago")
        except ValueError:
            urgency = "needed by " + need.needed_by
    total = (price_book.total_cost(price, quantity=still or 1.0, cost_per_mile=price_book.cost_per_mile(context))
             if price is not None else None)
    if price is None:
        several = len(amounts_in(text)) > 1
        advantage = ("several amounts in the listing, so I haven't taken any as its price" if several
                     else "no price in the listing")
    elif verdict["verdict"] == "too_few":
        advantage = money(price) + ": not yet verified (" + verdict["said"] + ")"
    else:
        advantage = money(price) + ": " + verdict["said"]
    dims = [
        {"name": "Project relevance", "value": f"{need.item} for {project or 'a project'}",
         "reason": _PRIORITY.get(need.priority, need.priority) + (f"; {still:g} still needed" if still else "")},
        {"name": "Price advantage", "value": advantage, "reason": f"{verdict.get('seen', 0)} prices seen for it"
         if price is not None else "read from the listing's title and summary"},
        {"name": "Compatibility", "value": compat["state"], "reason": compat["reason"]},
        {"name": "Quality", "value": "not known", "reason": "no seller or product records yet"},
        {"name": "Urgency", "value": urgency, "reason": "from the need's date" if need.needed_by else "the need has no date"},
        {"name": "Geographic accessibility", "value": "not known", "reason": "finds don't carry a location yet"},
        {"name": "Total cost", "value": (money(total["known_total"]) + (" + unknown " + ", ".join(total["unknown"])
                                                                         if total["unknown"] else ""))
         if total else "not known", "reason": f"for the {still or 1:g} still needed" if total else "no price"},
        {"name": "Strategic value", "value": _PRIORITY.get(need.priority, need.priority),
         "reason": "the priority the project gives it"},
        {"name": "Confidence", "value": "read from the listing" if price is not None else "matched by words",
         "reason": f"from {discovery.source_name}; matched to the need by its words"},
    ]
    if over:
        dims[1]["reason"] += f"; your ceiling is {money(ceiling)}"
    return {"discovery_id": discovery.discovery_id, "title": discovery.title, "link": discovery.link,
            "source": discovery.source_name, "requirement_id": need.requirement_id, "need": need.item,
            "project": project, "price": price, "recommendation": rec, "said": SAID[rec], "why": why,
            "dimensions": dims, "score": discovery.score}


def opportunities(context, now: Optional[datetime] = None, limit: int = 20) -> list[dict]:
    """Every new or saved find that meets an open need, as opportunities, best first: by recommendation (buy when
    ready, investigate, wait, skip), then the find's own score."""
    book = getattr(context, "world_intel", None)
    if book is None:
        return []
    out = []
    for d in book.discoveries:
        if d.status not in ("new", "saved"):
            continue
        try:
            got = assess(context, d, book, now)
        except Exception:  # noqa: BLE001 - one find that can't be assessed never hides the others
            log.exception("Couldn't assess find %s", d.discovery_id)
            continue
        if got is not None:
            out.append(got)
    out.sort(key=lambda o: (_ORDER[o["recommendation"]], -o["score"]))
    return out[:limit]


def sentence(found: list[dict], limit: int = 3) -> str:
    """Opportunities in words for voice: the best few with their recommendation and why."""
    worth = [o for o in found if o["recommendation"] != "skip"]
    if not worth:
        return ("Nothing I've found meets one of your projects' needs yet." if not found else
                f"I found {len(found)} for your projects' needs, but each one is a skip: " + found[0]["why"] + ".")
    lines = []
    for o in worth[:limit]:
        price = o["dimensions"][1]["value"]
        lines.append(f"{o['said']}: {o['title']} from {o['source']}, for {o['need']}"
                     + (f" ({o['project']})" if o["project"] else "") + f". {price}. Why: {o['why']}.")
    more = len(worth) - limit
    return " ".join(lines) + (f" And {more} more on the World page's Opportunities tab." if more > 0 else "")
