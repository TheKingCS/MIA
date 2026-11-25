"""
core.catch_actions
====================

His catch log from the screen and by voice (core/catch_log.py; DEC-0125, both ways): the action `catch.log`
(Expeditions, Log A Catch) and the tools `log_catch` ("caught an 18 inch bass on a jig at the pond") and
`whats_biting` ("what's been biting?"). Taking one back is "undo that".
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction

FIELDS = ("species", "length", "weight", "where", "bait", "kept")


def _describe(context, params) -> str:
    """What catch.log says (no species refused here)."""
    species = " ".join(str(params.get("species", "") or "").split())
    if not species:
        raise ActionError("What did you catch?")
    return f"Log a {species}"


def _execute(context, params) -> str:
    """Does catch.log."""
    from core.catch_log import log

    try:
        return log(context, **{k: params.get(k) for k in FIELDS})
    except ValueError as problem:
        raise ActionError(str(problem)) from None


CATCH_ACTIONS = {k.kind: k for k in (
    ActionType("catch.log", "Log A Catch", {"species": "what it was", "length": "inches (optional)",
                                            "weight": "pounds (optional)", "where": "optional", "bait": "optional",
                                            "kept": "kept or released (optional)"}, _describe, _execute),
)}
ACTION_TYPES.update(CATCH_ACTIONS)


def _log_tool(context, arguments: dict) -> str:
    """Tool log_catch: catch.log, its refusals said. Kept or released isn't asked of the model (it filled it in when
    he never said, the live check 2026-11-24); a zero length or weight is none."""
    params = {k: arguments.get(k) for k in FIELDS if k != "kept"}
    try:
        ACTION_TYPES["catch.log"].describe(context, params)
        return ACTION_TYPES["catch.log"].execute(context, params)
    except ActionError as problem:
        return str(problem)


def _biting(context, arguments: dict) -> str:
    """Tool whats_biting: his catches, what bait, time and place did best, and his personal bests."""
    from core.catch_log import say

    return say(context)


# Fishing words that bring the catch log in (never a bare "caught a": "I caught a cold", the live check 2026-11-24).
FISH_WORDS = ("fish", "fishing", "bass", "trout", "walleye", "catfish", "bluegill", "crappie", "pike", "perch",
              "salmon", "carp", "muskie", "sunfish", "lure", "jig", "spinnerbait", "crankbait", "nightcrawler")


def register_catch_actions(registry) -> None:
    """Registers log_catch and whats_biting, and the fishing words that offer them (`FISH_WORDS`, whole words)."""
    registry.register_domain_keywords("expeditions", FISH_WORDS)
    registry.register(AssistantAction(
        name="log_catch", domain="expeditions",
        description="He caught a fish: the species, and its length (inches), weight (pounds), where, and the bait or "
                    "lure, only as he said them. Kept in his catch log; a personal best is said.",
        parameters={"type": "object", "properties": {
            "species": {"type": "string", "description": "the fish, e.g. 'largemouth bass'"},
            "length": {"type": "number", "description": "inches, only if he said"},
            "weight": {"type": "number", "description": "pounds, only if he said"},
            "where": {"type": "string", "description": "the lake, river or spot, only if he said"},
            "bait": {"type": "string", "description": "the bait or lure, only if he said"}},
            "required": ["species"]},
        handler=_log_tool, trigger_phrases=("reeled in", "log a catch", "log my catch", "went fishing"),
    ))
    registry.register(AssistantAction(
        name="whats_biting", domain="expeditions",
        description="What his own catch log says: fish caught this year by species, the bait, time of day and spot "
                    "that did best, and his personal bests.",
        parameters={"type": "object", "properties": {}},
        handler=_biting, trigger_phrases=("what's biting", "what's been biting", "been biting", "my catches",
                                          "my personal best", "biggest fish", "best bait", "fishing log",
                                          "catch log"),
    ))
