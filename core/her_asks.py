"""
core.her_asks
===============

His bare answer to her own last question, finished in code (brainstorm round 19; the live check 2026-11-26: "5
gallons" after "How much fuel?" got the question echoed back, "Springfield, Illinois" after "I don't know your town
yet" a made-up forecast). Each ask is known by its own words in her last message, and each answer is read strictly:

- the firewood a winter takes him ("about 4 cords": core/firewood.answer_to_ask);
- the fuel for the generator ("5 gallons", "20 lb of propane", "a half gallon": core/homestead_sums.generator_runtime);
- the generator's burn rate ("half a gallon an hour": kept as prepared.generator_gph, then the runtime for the fuel
  he'd already given);
- his town ("Springfield, Illinois", or one or two capitalised words): set only when the weather service finds it,
  never a command or a sentence of his (the Fable review: "remind me to call mom" or "undo that" after her ask had
  become a town).

- a build she offered to work out ("I'm thinking about building a shed" got "Good project. I can work out the
  materials ... at your size"): its size ("a 10 by 12", "what about 10x12?") is its materials, "how much would it
  cost?" asks the size, and "add it to my projects" adds it (the conversation check, 2026-11-26: the size had gone to
  a running-costs plan's guess, and "add it" nowhere).

Anything else is None, and the turn goes on as if she hadn't asked. `reply(context, last_reply, prompt)` is the one
call (core/assistant_turn._follow_through_reply).
"""

from __future__ import annotations

import re
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

FUEL_ASK = "How much fuel? Say it in gallons"
RATE_ASK = 'like "my generator burns half a gallon an hour"'
TOWN_ASK = "I don't know your town yet"
# the build she offered to work out, in her own words (core/assistant_turn's "thinking of building" reply, or her size ask)
_BUILD = re.compile(r"materials and cuts for an? (?P<kind>[\w' -]+?) at your size|For the (?P<kind2>[\w' -]+?), what size\?")
_SIZE = re.compile(r"^\s*(?:(?:ok(?:ay)?|so|and|hmm|well),?\s+)?(?:what about|how about|make it|let'?s (?:do|say)|maybe|say|about|"
                   r"go with)?\s*(?:an?\s+)?(?P<size>\d+(?:\.\d+)?\s*(?:'|ft|feet|foot)?\s*(?:by|x)\s*\d+(?:\.\d+)?)\s*"
                   r"(?:'|ft|feet|foot)?(?:\s+(?:one|size|feet))?\s*[?.!]*\s*$", re.I)
_BUILD_COST = re.compile(r"^\s*(?:and\s+|so\s+)?(?:how much|what)\s+(?:would|will|does|do)\s+(?:the\s+)?(?:it|that|one|lumber|"
                         r"materials|wood)\s+(?:cost|run(?: me)?|be)\b.{0,20}[?.!]*\s*$", re.I)
_BUILD_ADD = re.compile(r"^\s*(?:ok(?:ay)?,?\s+|great,?\s+|yes,?\s+)?(?:please\s+)?(?:add|put|make)\s+(?:it|that|this)\s+"
                        r"(?:to|in|on|as)\s+(?:my|the|a)\s+(?:projects?|project list)\s*[.!]*\s*$", re.I)

_FUEL_ONLY = re.compile(r"^\s*(?:about |around |maybe |probably |like |i have |we have |i'?ve got |we'?ve got )?(?:\d+(?:\.\d+)?|"
                        r"a couple(?: of)?|half an?|a half|an?|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
                        r"(?:gallons?|gal|lbs?|pounds?|liters?|litres?)(?: of (?:gas|gasoline|diesel|propane|lp|fuel))?"
                        r"\s*[.!]?\s*$", re.I)
_RATE_ONLY = re.compile(r"^\s*(?:about |around |maybe |probably |it'?s |it burns )?(?P<n>\d*\.?\d+|half an?|a half|a quarter "
                        r"(?:of )?an?|an?|one)\s*(?:gallons?|gal)\s*(?:an|per|a|each) hour\s*[.!]?\s*$", re.I)
_RATE_WORDS = {"half a": 0.5, "half an": 0.5, "a half": 0.5, "a quarter of a": 0.25, "a quarter a": 0.25, "a": 1.0,
               "an": 1.0, "one": 1.0}
# a town: "Name, Region" or one or two capitalised words, never a word that's his answer to something else
_TOWN = re.compile(r"^\s*(?:(?i:it'?s |i'?m in |i live in |we'?re in |we live in ))?(?P<x>[A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+)?"
                   r"(?:,\s*[A-Za-z][A-Za-z .]{1,30})?)\s*[.!]?\s*$")
_NOT_A_TOWN = re.compile(r"^(?:home|here|there|work|the farm|same|idk|skip|cancel|maybe|yes|yeah|yep|no|nope|ok|okay|"
                         r"thanks|hello|hi|hey|later|never mind|nevermind|undo|stop)\b", re.I)


def reply(context, last_reply: str, prompt: str, recent: tuple = ()) -> Optional[str]:
    """His answer to her last question, kept or worked out in code; None when she didn't ask, or his words aren't
    that answer. `recent` is her last few replies, newest last: the build she offered is found there too, so "add it
    to my projects" after its materials list still means the shed."""
    asked, said = str(last_reply or ""), str(prompt or "").strip()
    if not asked or not said or len(said) > 60:
        return None
    from core import firewood

    kept = firewood.answer_to_ask(context, asked, said)
    if kept:
        return kept
    if FUEL_ASK in asked and _FUEL_ONLY.match(said):
        from core.homestead_sums import generator_runtime

        words = re.sub(r"\ba half\b", "half a", said, flags=re.I)
        answer = generator_runtime(context, words)
        return None if answer.startswith("How much fuel?") else answer
    rate = _RATE_ONLY.match(said) if RATE_ASK in asked else None
    if rate:
        n = rate.group("n").lower()
        gph = _RATE_WORDS.get(n) if n in _RATE_WORDS else float(n)
        if not gph or not 0.05 <= gph <= 5:
            return None
        from core.assistant_today_actions import _action_set_preparedness

        kept = _action_set_preparedness(context, {"generator_gph": gph})
        fuel = re.search(r"to work out (.+?):", asked)  # the fuel he'd given before her ask: its runtime now
        if fuel and str(kept).startswith("Set:"):
            from core.homestead_sums import generator_runtime

            kept = f"{kept} {generator_runtime(context, fuel.group(1))}"
        return kept
    build = _BUILD.search(asked) or next((found for found in (_BUILD.search(r) for r in reversed(recent[-3:])) if found),
                                         None)
    if build:
        kind = (build.group("kind") or build.group("kind2")).strip()
        if _BUILD.search(asked) is None and not _BUILD_ADD.match(said):
            return None  # a size or a price leans only on her last reply; adding it, on the last few
        sized = _SIZE.match(said)
        if sized:  # "a 10 by 12": the calculators' list for it (core/assistant_plan_actions.materials_reply)
            from core.assistant_plan_actions import materials_reply

            size = re.sub(r"\s*(?:'|ft|feet|foot)\s*", " ", sized.group("size")).strip()
            size = re.sub(r"\s*(?:by|x)\s*", " by ", size, flags=re.I)
            return materials_reply(context, f"materials for a {size} {kind}")
        if _BUILD_COST.match(said):
            return (f"For the {kind}, what size? Say it like \"a 10 by 12\" and I'll work out the materials and price "
                    f"them from your records.")
        if _BUILD_ADD.match(said):
            actions = getattr(context, "assistant_actions", None)
            if actions is None:
                return None
            return actions.execute(context, "add_project", {"name": kind[:1].upper() + kind[1:]})
    town = _TOWN.match(said) if TOWN_ASK in asked else None
    if town and not _NOT_A_TOWN.match(said) and not said.lower().startswith(("my town is", "set my town")):
        actions = getattr(context, "assistant_actions", None)
        if actions is None:
            return None
        try:
            answer = actions.execute(context, "set_weather_place", {"place": town.group("x").strip()})
        except Exception:
            log.exception("Couldn't set his town")
            return None
        found = str(answer or "").startswith("The weather is for")
        return answer if found or "," in town.group("x") else None  # a word that isn't a town is the model's
    return None
