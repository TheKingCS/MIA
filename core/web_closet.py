"""
core.web_closet
=================

Smart Closet's screen data (DEC-0162), assembled here so the web page only
formats it (`/api/closet`, `MIA.closet()`). Everything comes from code:

- the day: the weather card (`core/weather.py`), today's calendar events,
  and whether the Loop says it's a work day;
- the suggestion (`core/smart_closet.suggest`);
- the pieces (grouped by category, with photo links);
- the saved outfits with their ratings;
- the insights;
- the form the page shows to add or edit a piece (from `core/closet_actions.PIECE`).

The voice tools read the same page (`core/assistant_closet_actions.py`),
so the two always agree.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Optional

from core.smart_closet import CATEGORIES, insights, occasion_for, suggest

_CATEGORY_SAY = {"top": "Tops", "bottom": "Bottoms", "dress": "Dresses", "layer": "Layers",
                 "outerwear": "Outerwear", "shoes": "Shoes", "accessory": "Accessories"}


def day_context(context, today: date) -> dict:
    """What today asks of the clothes: the weather card (or None), today's event titles, and whether it's a work
    day (a work rhythm in the Loop on today's weekday)."""
    weather = None
    try:
        from core import weather as weather_mod

        got = weather_mod.card(context)
        weather = got if got.get("text") else None
    except Exception:  # noqa: BLE001 - no town or offline: the suggestion says the weather is unknown
        weather = None
    titles = []
    cal = getattr(context, "calendar", None)
    if cal is not None:
        try:
            titles = [e.title for e in cal.events_for_date(today.isoformat())]
        except Exception:  # noqa: BLE001
            titles = []
    loop = getattr(context, "loop", None)
    work = bool(loop is not None and any(r.kind == "work" and today.weekday() in (r.days or [])
                                         for r in getattr(loop, "rhythms", [])))
    return {"weather": weather, "events": titles, "work_day": work}


def _piece(p, today: date) -> dict:
    """A piece as the page shows it, with its photo link when it has one."""
    d = asdict(p)
    d["photo_url"] = f"/api/closet/piece/{p.piece_id}/photo" if p.photo else ""
    return d


def _piece_form() -> dict:
    """The add/edit form for a piece (core/closet_actions.PIECE), as the page's form reads it."""
    from core.closet_actions import PIECE
    from core.record_actions import record_form

    return record_form(PIECE)


def closet_page(context, today: Optional[date] = None) -> dict:
    """The whole Smart Closet screen: the day, today's picks, the pieces by category, the outfits, the insights and
    the piece form. `available` is False when this MIA has no closet."""
    today = today or date.today()
    book = getattr(context, "closet", None)
    if book is None:
        return {"available": False}
    day = day_context(context, today)
    occasion = occasion_for(day["events"], day["work_day"])
    plan = suggest(book.pieces, book.outfits, day["weather"], occasion, today)
    by_id = {p.piece_id: p for p in book.pieces}
    for pick in plan["picks"]:
        pick["pieces"] = [_piece(by_id[i], today) for i in pick["piece_ids"] if i in by_id]
    groups = [{"category": c, "label": _CATEGORY_SAY[c],
               "pieces": [_piece(p, today) for p in sorted(book.pieces, key=lambda p: p.name.lower())
                          if p.category == c]} for c in CATEGORIES]
    outfits = [{"outfit_id": o.outfit_id, "name": o.name, "stars": o.stars, "ratings": len(o.ratings),
                "last_worn": o.last_worn, "times_worn": o.times_worn,
                "pieces": [_piece(by_id[i], today) for i in o.piece_ids if i in by_id]} for o in book.outfits]
    weather = day["weather"]
    return {
        "available": True,
        "today": today.isoformat(),
        "day": {"weather_text": weather.get("text") if weather else None,
                "place": weather.get("place") if weather else None,
                "events": day["events"], "work_day": day["work_day"], "occasion": occasion},
        "suggestion": plan,
        "groups": [g for g in groups if g["pieces"]],
        "count": len(book.pieces),
        "outfits": outfits,
        "insights": insights(book.pieces, book.outfits, today),
        "form": _piece_form(),
    }


def suggestion_sentence(page: dict) -> str:
    """Today's best pick in a sentence, with why, for voice and the glasses; or what's missing."""
    if not page.get("available"):
        return "There's no closet on this MIA."
    if not page["count"]:
        return "Your closet is empty so far: add a few pieces (Apps → Smart Closet, or tell me \"add my navy hoodie\")."
    plan = page["suggestion"]
    weather = page["day"]["weather_text"]
    lead = f"It's {weather}" if weather else "I don't have today's weather (tell me your town for it)"
    lead += f", and it's {_OCCASION_LEAD.get(plan['occasion'], 'an everyday day')}."
    if not plan["picks"]:
        missing = ", ".join(plan["missing"]) or "enough clean pieces"
        return f"{lead} I can't put an outfit together yet: the closet needs {missing}."
    best = plan["picks"][0]
    why = "; ".join(best["why"][:2])
    line = f"{lead} Try {best['name']}" + (f" ({why})" if why else "") + "."
    if len(plan["picks"]) > 1:
        line += f" Or: {plan['picks'][1]['name']}."
    return line


_OCCASION_LEAD = {"work": "a work day", "gym": "a gym day", "date": "a date day", "dressy": "a dressy day",
                  "outdoors": "a day outdoors", "lounge": "a day in", "everyday": "an everyday day"}
