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


def reply(context, last_reply: str, prompt: str) -> Optional[str]:
    """His answer to her last question, kept or worked out in code; None when she didn't ask, or his words aren't
    that answer."""
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
