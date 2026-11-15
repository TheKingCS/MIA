"""
core.closet_actions
=====================

Smart Closet's actions (DEC-0162, core/smart_closet.py) on the action
contract: proposed in plain words, approved, run, undoable.

- `closet_piece.add/edit/delete`: a piece of clothing.
- `closet.outfit`: save pieces worn together as an outfit.
- `closet.outfit_delete`: forget a saved outfit (its pieces stay).
- `closet.rate`: rate an outfit, 1 to 5 stars, with a note.
- `closet.wore`: mark an outfit, or some pieces, worn on a day.
- `closet.laundry`: pieces into the wash, or "laundry's done" (all clean).
"""

from __future__ import annotations

from datetime import date

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_kinds
from core.smart_closet import CATEGORIES, CONDITIONS, WARMTH

PIECE = Record("closet_piece", "piece", "piece_id", "get_piece", "add_piece", "update_piece", "delete_piece",
               store="closet", fields=(
                   Field("name", "Name (navy hoodie, black boots…)", "text", True),
                   Field("category", "Kind", "choice", options=CATEGORIES, default="top", say="kind"),
                   Field("color", "Colour", "text", say="colour"),
                   Field("warmth", "Warmth", "choice", options=WARMTH, default="medium", quiet_default=True),
                   Field("occasions", "For (everyday, work, gym, date, dressy, outdoors, lounge)", "text",
                         default="everyday", say="occasions", quiet_default=True),
                   Field("waterproof", "Waterproof", "choice", options=("no", "yes"), default="no",
                         quiet_default=True),
                   Field("condition", "Condition", "choice", options=CONDITIONS, default="good", quiet_default=True),
                   Field("notes", "Notes", "textarea")))


def _book(context):
    """The person's closet, or ActionError when this MIA doesn't have one."""
    return _need(context, "closet")


def _ids(raw) -> list[str]:
    """Piece ids from a list or a comma-separated string."""
    items = raw if isinstance(raw, (list, tuple)) else str(raw or "").split(",")
    return [str(x).strip() for x in items if str(x).strip()]


def _pieces(context, params, need: int = 1) -> list:
    """The pieces the params name (`piece_ids`, or `pieces` as words), checked; ActionError when fewer than `need`."""
    book = _book(context)
    found = [p for p in (book.get_piece(i) for i in _ids(params.get("piece_ids"))) if p]
    for words in _ids(params.get("pieces")):
        p = book.find_piece(words)
        if p is None:
            raise ActionError(f"I couldn't find \"{words}\" in the closet.")
        found.append(p)
    found = list({p.piece_id: p for p in found}.values())
    if len(found) < need:
        raise ActionError("Which pieces?" if need == 1 else "An outfit needs at least two pieces from the closet.")
    return found


def _day(params) -> str:
    """The date in the params (blank or "today" is today), or ActionError."""
    raw = str(params.get("date") or "").strip().lower()
    if raw in ("", "today"):
        return date.today().isoformat()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        raise ActionError("Which day? (YYYY-MM-DD, or today)") from None


def _outfit(context, params):
    """The saved outfit the params name, or ActionError."""
    o = _book(context).get_outfit(str(params.get("outfit_id") or ""))
    if o is None:
        raise ActionError("That outfit isn't saved anymore.")
    return o


def _names(pieces) -> str:
    """Pieces as a list in words."""
    names = [p.name for p in pieces]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _outfit_describe(context, params) -> str:
    """The approval sentence for `closet.outfit`."""
    pieces = _pieces(context, params, need=2)
    name = str(params.get("name") or "").strip()
    return f"Save an outfit{f' called {name}' if name else ''}: {_names(pieces)}"


def _outfit_execute(context, params) -> str:
    """Does `closet.outfit`."""
    pieces = _pieces(context, params, need=2)
    o = _book(context).add_outfit(str(params.get("name") or ""), [p.piece_id for p in pieces])
    return f"Saved {o.name}. Rate it after you've worn it."


def _odelete_describe(context, params) -> str:
    """The approval sentence for `closet.outfit_delete`."""
    return f"Forget the outfit {_outfit(context, params).name} (its pieces stay in the closet)"


def _odelete_execute(context, params) -> str:
    """Does `closet.outfit_delete`."""
    o = _outfit(context, params)
    _book(context).delete_outfit(o.outfit_id)
    return f"Forgot {o.name}."


def _stars(params) -> int:
    """The stars in the params, 1 to 5, or ActionError."""
    try:
        n = int(float(params.get("stars")))
    except (TypeError, ValueError):
        raise ActionError("How many stars, 1 to 5?") from None
    if not 1 <= n <= 5:
        raise ActionError("How many stars, 1 to 5?")
    return n


def _rate_describe(context, params) -> str:
    """The approval sentence for `closet.rate`."""
    note = str(params.get("note") or "").strip()
    return f"Rate {_outfit(context, params).name} {_stars(params)} of 5" + (f": \"{note}\"" if note else "")


def _rate_execute(context, params) -> str:
    """Does `closet.rate`."""
    o = _outfit(context, params)
    o = _book(context).rate_outfit(o.outfit_id, _stars(params), str(params.get("note") or ""))
    return f"Rated {o.name}: {o.stars:g} stars on average." if len(o.ratings) > 1 else f"Rated {o.name}."


def _worn(context, params) -> tuple:
    """The pieces and outfit a `closet.wore` names (an outfit, or pieces)."""
    if params.get("outfit_id"):
        o = _outfit(context, params)
        book = _book(context)
        return [p for p in (book.get_piece(i) for i in o.piece_ids) if p], o
    return _pieces(context, params), None


def _wore_describe(context, params) -> str:
    """The approval sentence for `closet.wore`."""
    pieces, o = _worn(context, params)
    what = o.name if o else _names(pieces)
    day = _day(params)
    return f"Mark {what} worn " + ("today" if day == date.today().isoformat() else f"on {day}")


def _wore_execute(context, params) -> str:
    """Does `closet.wore`."""
    pieces, o = _worn(context, params)
    _book(context).wear([p.piece_id for p in pieces], _day(params), o.outfit_id if o else "")
    return f"Marked {o.name if o else _names(pieces)} worn." + (" Rate it when you get a chance." if o else "")


def _laundry_describe(context, params) -> str:
    """The approval sentence for `closet.laundry`."""
    into = str(params.get("into_wash") or "").strip().lower() in ("yes", "true", "1")
    if not _ids(params.get("piece_ids")) and not _ids(params.get("pieces")):
        if into:
            raise ActionError("Which pieces went in the wash?")
        return "Mark everything clean (laundry's done)"
    pieces = _pieces(context, params)
    return f"Mark {_names(pieces)} " + ("in the wash" if into else "clean")


def _laundry_execute(context, params) -> str:
    """Does `closet.laundry`."""
    into = str(params.get("into_wash") or "").strip().lower() in ("yes", "true", "1")
    ids = None
    if _ids(params.get("piece_ids")) or _ids(params.get("pieces")):
        ids = [p.piece_id for p in _pieces(context, params)]
    n = _book(context).laundry(ids, in_wash=into)
    return (f"{n} piece{'s' if n != 1 else ''} in the wash." if into
            else f"{n} piece{'s' if n != 1 else ''} back in the closet." if n else "Everything was already clean.")


def _register() -> None:
    """Adds the closet's kinds to ACTION_TYPES. Runs once, when this module is imported."""
    kinds = list(record_kinds(PIECE)) + [
        ActionType("closet.outfit", "Save Outfit", {"piece_ids": "the pieces", "pieces": "or the pieces in words",
                                                   "name": "a name (optional)"}, _outfit_describe, _outfit_execute),
        ActionType("closet.outfit_delete", "Forget Outfit", {"outfit_id": "the outfit"},
                   _odelete_describe, _odelete_execute),
        ActionType("closet.rate", "Rate", {"outfit_id": "the outfit", "stars": "1 to 5", "note": "a note"},
                   _rate_describe, _rate_execute),
        ActionType("closet.wore", "Wore It", {"outfit_id": "the outfit", "piece_ids": "or the pieces",
                                             "pieces": "or the pieces in words", "date": "the day (blank: today)"},
                   _wore_describe, _wore_execute),
        ActionType("closet.laundry", "Laundry", {"piece_ids": "the pieces (blank: all)", "pieces": "or in words",
                                                "into_wash": "yes: into the wash; else clean"},
                   _laundry_describe, _laundry_execute),
    ]
    for k in kinds:
        ACTION_TYPES[k.kind] = k


_register()
