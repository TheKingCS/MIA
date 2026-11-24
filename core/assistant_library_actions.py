"""
core.assistant_library_actions
================================

Her offline library, by voice (core/offline_library.py): "how do I purify water", "how deep should fence posts go",
"what's wrong with my tomato leaves" are looked up in the packs on this computer, with no internet (`look_up_offline`,
observe: it only reads); "tell me more about that" reads one source further (`read_reference`, observe); "fetch the essentials" puts up a card to download packs (`fetch_reference_packs`, his yes:
gigabytes from Kiwix). The Knowledge page does both too (DEC-0125).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction

DOMAIN = "library"
# How a how-to or factual question is asked: these bring the one look-up tool, never the whole knowledge shelf.
ASKING = ("how do i", "how do you", "how to", "how should i", "how deep", "how much", "how long", "how many",
          "how often", "what causes", "why does", "why is my", "is it safe", "what's the best way", "purify",
          "first aid", "symptoms", "troubleshoot", "step by step", "edible", "forage", "foraging", "wild plants",
          "identify", "explain how")


def _look_up(context, arguments: dict) -> str:
    """The best passages from her offline packs for the question, framed as outside text."""
    from core.offline_library import look_up

    return look_up(getattr(context, "reference_library", None), str(arguments.get("question", "")))


def _read(context, arguments: dict) -> str:
    """One source from a look-up read at length, around what's asked."""
    from core.offline_library import read_further

    return read_further(getattr(context, "reference_library", None), str(arguments.get("ref", "")),
                        str(arguments.get("focus", "")))


def _fetch(context, arguments: dict) -> str:
    """A card to download packs: a set, or the packs named."""
    from core.actions import ActionError

    actions = getattr(context, "actions", None)
    if actions is None:
        return "I can't put that to you from here: it's on the Knowledge page."
    keys = arguments.get("keys") or []
    params = {"set": str(arguments.get("set") or "").strip().lower(),
              "keys": [str(k) for k in (keys if isinstance(keys, list) else [keys])]}
    try:
        card = actions.propose(context, "library.fetch", params)
    except ActionError as problem:
        return str(problem)
    return f"{card.summary}. It's waiting for your yes: press Approve, or say \"approve it\"."


def register_library_actions(registry) -> None:
    """Registers look_up_offline and read_reference (in their own domain, brought by how a how-to question is
    asked) and fetch_reference_packs."""
    registry.register_domain_keywords(DOMAIN, ASKING)
    registry.register(AssistantAction(
        name="look_up_offline", domain=DOMAIN,
        description="Look something up in MIA's offline reference library (homesteading, gardening, building and "
                    "repair, food preserving, water, first aid and medicine, preparedness, energy, animals, "
                    "vehicles, electronics, Linux, Wikipedia and more), with no internet. Use it for how-to and "
                    "factual questions, and say which pack each part came from.",
        parameters={"type": "object", "properties": {"question": {"type": "string",
                    "description": "What to look up, in a few plain words."}}, "required": ["question"]},
        handler=_look_up,
        trigger_phrases=("offline library", "look it up offline", "in the library", "in your library",
                         "reference library", "reference packs"),
    ))
    registry.register(AssistantAction(
        name="read_reference", domain=DOMAIN,
        description="Read one source from a look_up_offline result further (its ref), around what he wants to know "
                    "more about; for 'tell me more', 'what else does it say', or a detail the passage cut off.",
        parameters={"type": "object", "properties": {
            "ref": {"type": "string", "description": "The passage's ref, as look_up_offline gave it."},
            "focus": {"type": "string", "description": "What to read about in it, in a few words (optional)."}},
            "required": ["ref"]},
        handler=_read, trigger_phrases=("tell me more about that", "what else does it say", "read more"),
    ))
    registry.register(AssistantAction(
        name="fetch_reference_packs", domain="knowledge",
        description="Put up a card to download offline reference packs into MIA's library: a set (essential, "
                    "standard or all) or packs by key.",
        parameters={"type": "object", "properties": {
            "set": {"type": "string", "description": "essential, standard or all"},
            "keys": {"type": "array", "items": {"type": "string"}, "description": "Packs by key, instead of a set."}}},
        handler=_fetch,
        trigger_phrases=("fetch the packs", "download the library", "get the reference packs", "offline packs"),
    ))
