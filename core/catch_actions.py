"""
core.catch_actions
====================

His catch log from the screen and by voice (core/catch_log.py; DEC-0125, both ways): the action `catch.log`
(Expeditions, Log A Catch) and the tools `log_catch` ("caught an 18 inch bass on a jig at the pond") and
`whats_biting` ("what's been biting?"). Taking one back is "undo that".
`parse(text)` reads a catch said whole in code ("I caught a 3 pound bass at the pond this morning": the conversation
check, 2026-11-26, where the model logged three bass), the count, size, place and bait only as said.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction

FIELDS = ("species", "length", "weight", "where", "bait", "kept")


import re  # noqa: E402

_COUNTS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
           "nine": 9, "ten": 10}
_SPECIES = (r"(?:(?:largemouth|smallmouth|spotted|striped|white|rock|rainbow|brown|brook|lake|channel|flathead|blue|"
            r"yellow|black|white)\s+)?(?:bass|trout|catfish|bluegill|crappie|pike|perch|walleye|salmon|carp|muskie|musky|"
            r"sunfish|bream|panfish|cat|gill)")
_CATCH = re.compile(r"^\s*(?:i\s+)?(?:just\s+)?(?:caught|landed|reeled in|got)\s+(?P<count>an?|one|two|three|four|five|six|seven|"
                    r"eight|nine|ten|\d{1,2})\s+(?:(?P<size>\d+(?:\.\d+)?)\s*(?:-\s*)?(?P<unit>pounds?|lbs?|pound|inch(?:es)?|"
                    r"in|\")\s+)?(?P<species>" + _SPECIES + r")(?:es|s)?(?:\s+(?:at|in|on|from|off)\s+(?:the\s+|my\s+)"
                    r"(?P<where>[\w' -]{2,30}?))?(?:\s+(?:on|with)\s+an?\s+(?P<bait>[\w' -]{2,30}?))?(?:\s+(?:this "
                    r"(?:morning|afternoon|evening)|tonight|today|just now|earlier))?\s*[.!]*\s*$", re.I)


def parse(text: str):
    """Pure logic. A catch said whole as the log_catch tool's arguments ({species, count, length or weight, where,
    bait}), or None: never a day gone ("yesterday" isn't kept as one), a question, or a size that isn't the fish's."""
    found = _CATCH.match(str(text or "").replace("\u2019", "'"))
    if not found or "?" in text:
        return None
    count = found.group("count").lower()
    args = {"species": " ".join(found.group("species").lower().split()),
            "count": _COUNTS.get(count) or int(count)}
    if found.group("size"):
        size = float(found.group("size"))
        if args["count"] != 1:
            return None  # "two 3 pound bass": whose size? the model's to ask
        unit = found.group("unit").lower()
        args["weight" if unit.startswith(("p", "l")) else "length"] = size
    if found.group("where"):
        args["where"] = found.group("where").strip()
    if found.group("bait"):
        args["bait"] = found.group("bait").strip()
    return args


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
    he never said, the live check 2026-11-24); a zero length or weight is none; `count` logs that many, each its own
    catch ("I caught 3 bass").
    A size said is the first fish's, and "biggest yet" is kept in the summary."""
    params = {k: arguments.get(k) for k in FIELDS if k != "kept"}
    try:
        many = max(1, min(50, int(float(arguments.get("count") or 1))))
    except (TypeError, ValueError):
        many = 1
    try:
        ACTION_TYPES["catch.log"].describe(context, params)
        said, best = "", ""
        for n in range(many):  # "I caught 3 bass": three catches, each its own (the live sweep: it had been one)
            said = ACTION_TYPES["catch.log"].execute(context, params if n == 0 else {
                k: v for k, v in params.items() if k not in ("length", "weight")})  # a size said is one fish's
            best = best or next((s for s in said.split(". ") if "biggest" in s.lower()), "")
        if many > 1:
            where = f" at {params['where']}" if params.get("where") else ""
            total = said.rsplit(". ", 1)[-1] if ". " in said else ""
            what = " ".join(str(params.get("species") or "fish").split())
            best = f" {best.rstrip('.')}." if best and best not in total else ""
            return f"Logged {many} {what}{where}.{best}" + (f" {total}" if total else "")
        return said
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
    """Registers log_catch and whats_biting (reached by "my biggest bass" and the other species too, live check
    2026-11-24), and the fishing words that offer them (`FISH_WORDS`, whole words).
    "How many fish have I caught" reaches it, never "how many fish can I keep" (a limit).
    log_catch takes a count ("I caught 3 bass" is three catches)."""
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
            "bait": {"type": "string", "description": "the bait or lure, only if he said"},
            "count": {"type": "integer", "description": "how many, when he caught more than one (\"3 bass\" is 3)"}},
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
                                          "catch log", "biggest catch", "best catch", "biggest bass",
                                          "biggest trout", "biggest catfish", "biggest walleye", "biggest pike",
                                          "biggest crappie", "biggest bluegill", "biggest perch", "biggest salmon",
                                          "how many fish have i", "how many fish did i", "fish have i caught",
                                          "fish did i catch"),
        subjects=(*FISH_WORDS, "catch", "caught"),  # what the question is about, for named_action
    ))
