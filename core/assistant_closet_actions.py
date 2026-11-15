"""
core.assistant_closet_actions
===============================

Smart Closet by voice (DEC-0162):
- "What should I wear today?"
- "Add my navy hoodie to the closet"
- "Save the hoodie and jeans as an outfit"
- "I wore the hoodie and jeans"
- "Rate that outfit 4 stars"
- "Laundry's done"
- "What haven't I worn in ages?"

Each runs the same code as the screen: the action kinds are in
`core/closet_actions.py` and the suggestion comes from
`core/web_closet.py`. So the answer matches the page, and "undo that"
works.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run


def _what_to_wear(context, arguments: dict) -> str:
    """Tool what_to_wear: today's outfit suggestion with why (the weather, the day's occasion, what's rested), from
    the Smart Closet page."""
    from core.web_closet import closet_page, suggestion_sentence

    return suggestion_sentence(closet_page(context))


def _closet_report(context, arguments: dict) -> str:
    """Tool closet_report: what the closet says about itself: pieces unworn for months, the most worn, the best rated
    outfits, what's in the wash or needs a repair, and what's missing."""
    from core.web_closet import closet_page

    page = closet_page(context)
    if not page.get("available"):
        return "There's no closet on this MIA."
    if not page["count"]:
        return "Your closet is empty so far."
    i = page["insights"]
    said = [f"{page['count']} pieces and {len(page['outfits'])} saved outfits."]
    if i["unworn"]:
        names = ", ".join(x["name"] for x in i["unworn"][:4])
        said.append(f"Not worn in six months or more: {names}. Worth keeping?")
    if i["most_worn"]:
        said.append("Most worn: " + ", ".join(f"{x['name']} ({x['times']})" for x in i["most_worn"]) + ".")
    if i["top_rated"]:
        said.append("Best rated: " + ", ".join(f"{x['name']} ({x['stars']:g}★)" for x in i["top_rated"]) + ".")
    if i["in_wash"]:
        said.append(f"In the wash: {', '.join(i['in_wash'])}.")
    if i["needs_repair"]:
        said.append(f"Needs a repair: {', '.join(i['needs_repair'])}.")
    if i["gaps"]:
        said.append(f"The closet has no {', '.join(i['gaps'])} yet.")
    return " ".join(said)


def _add_piece(context, arguments: dict) -> str:
    """Tool add_clothing: proposes `closet_piece.add` for a piece with what they said about it."""
    params = {k: arguments.get(k) for k in ("name", "category", "color", "warmth", "occasions", "waterproof")
              if arguments.get(k) not in (None, "")}
    return _run(context, "closet_piece.add", params)


def _last_outfit(context):
    """The most recently saved outfit, or None."""
    book = getattr(context, "closet", None)
    return book.outfits[-1] if book is not None and book.outfits else None


def _save_outfit(context, arguments: dict) -> str:
    """Tool save_outfit: proposes `closet.outfit` from the pieces named in words."""
    return _run(context, "closet.outfit", {"pieces": arguments.get("pieces") or "", "name": arguments.get("name") or ""})


def _wore(context, arguments: dict) -> str:
    """Tool wore_outfit: proposes `closet.wore` for the pieces named (in words), today unless they said a day."""
    return _run(context, "closet.wore", {"pieces": arguments.get("pieces") or "", "date": arguments.get("day") or ""})


def _rate(context, arguments: dict) -> str:
    """Tool rate_outfit: proposes `closet.rate` for the outfit named, or the last one saved."""
    book = getattr(context, "closet", None)
    wanted = str(arguments.get("outfit") or "").strip().lower()
    outfit = None
    if book is not None and wanted:
        outfit = next((o for o in book.outfits if wanted in o.name.lower()), None)
    outfit = outfit or _last_outfit(context)
    if outfit is None:
        return "There's no saved outfit to rate yet: save one first (\"save the hoodie and jeans as an outfit\")."
    return _run(context, "closet.rate", {"outfit_id": outfit.outfit_id, "stars": arguments.get("stars"),
                                         "note": arguments.get("note") or ""})


def _laundry(context, arguments: dict) -> str:
    """Tool closet_laundry: proposes `closet.laundry`: pieces into the wash, or everything clean."""
    return _run(context, "closet.laundry", {"pieces": arguments.get("pieces") or "",
                                            "into_wash": "yes" if arguments.get("into_wash") else ""})


def register_closet_actions(registry: AssistantActionRegistry) -> None:
    """Registers the Smart Closet tools: what_to_wear, closet_report, add_clothing, save_outfit, wore_outfit,
    rate_outfit and closet_laundry."""
    registry.register(AssistantAction(
        name="what_to_wear", domain="closet",
        description="Smart Closet: what to wear today, from the weather, the day's plans and what hasn't been worn lately.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_what_to_wear,
        trigger_phrases=("what should i wear", "what do i wear", "what to wear", "pick an outfit", "outfit for today",
                         "outfit for tonight", "smart closet", "my closet"),
        subjects=("outfit", "wear", "closet", "clothes"),
    ))
    registry.register(AssistantAction(
        name="closet_report", domain="closet",
        description="Smart Closet's own picture: pieces not worn in months, the most worn, best-rated outfits, what's in the wash, gaps.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_closet_report,
        trigger_phrases=("haven't i worn", "havent i worn", "never wear", "clothes i don't wear", "closet report",
                         "my clothes"),
        subjects=("clothes", "closet"),
    ))
    registry.register(AssistantAction(
        name="add_clothing", domain="closet",
        description="Add a piece of clothing to the Smart Closet.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "What it is, e.g. navy hoodie."},
            "category": {"type": "string", "description": "top, bottom, dress, layer, outerwear, shoes or accessory."},
            "color": {"type": "string", "description": "Its colour, only if said."},
            "warmth": {"type": "string", "description": "light, medium or warm, only if said."},
            "occasions": {"type": "string", "description": "everyday, work, gym, date, dressy, outdoors, lounge (comma-separated), only if said."},
            "waterproof": {"type": "boolean", "description": "True only if they said it's waterproof."},
        }, "required": ["name"]}, handler=_add_piece,
        trigger_phrases=("to my closet", "to the closet", "add a shirt", "add my shirt", "new shirt", "new jacket",
                         "new shoes", "bought a"),
        subjects=("closet", "clothes"),
    ))
    registry.register(AssistantAction(
        name="save_outfit", domain="closet",
        description="Save pieces from the closet as an outfit.",
        parameters={"type": "object", "properties": {
            "pieces": {"type": "string", "description": "The pieces in words, comma-separated (\"navy hoodie, jeans\")."},
            "name": {"type": "string", "description": "A name for the outfit, only if given."},
        }, "required": ["pieces"]}, handler=_save_outfit,
        trigger_phrases=("as an outfit", "save this outfit", "save the outfit", "save that outfit"),
        subjects=("outfit",),
    ))
    registry.register(AssistantAction(
        name="wore_outfit", domain="closet",
        description="Mark clothes as worn (today unless a day is said).",
        parameters={"type": "object", "properties": {
            "pieces": {"type": "string", "description": "The pieces in words, comma-separated."},
            "day": {"type": "string", "description": "YYYY-MM-DD or today. Blank: today."},
        }, "required": ["pieces"]}, handler=_wore,
        trigger_phrases=("i wore", "i'm wearing", "im wearing", "wearing today"),
        subjects=("outfit", "wore"),
    ))
    registry.register(AssistantAction(
        name="rate_outfit", domain="closet",
        description="Rate a saved outfit 1 to 5 stars (the one named, or the last saved).",
        parameters={"type": "object", "properties": {
            "stars": {"type": "number", "description": "1 to 5."},
            "outfit": {"type": "string", "description": "The outfit's name, if said."},
            "note": {"type": "string", "description": "What they said about it, if anything."},
        }, "required": ["stars"]}, handler=_rate,
        trigger_phrases=("rate the outfit", "rate this outfit", "rate that outfit", "rate my outfit", "outfit stars"),
        subjects=("outfit", "rating"),
    ))
    registry.register(AssistantAction(
        name="closet_laundry", domain="closet",
        description="Laundry in the Smart Closet: pieces into the wash, or everything clean when laundry's done.",
        parameters={"type": "object", "properties": {
            "pieces": {"type": "string", "description": "The pieces in words (blank with into_wash false: all clean)."},
            "into_wash": {"type": "boolean", "description": "True when the pieces went into the wash."},
        }, "required": []}, handler=_laundry,
        trigger_phrases=("laundry's done", "laundry is done", "in the wash", "into the wash", "in the laundry"),
        subjects=("laundry",),
    ))
