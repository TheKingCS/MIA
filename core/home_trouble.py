"""
core.home_trouble
===================

The house's trouble that can't wait but isn't a call to the emergency number (brainstorm round 15, 2026-11-25): a
burst or frozen pipe and a flooded basement, answered in fixed words, the first thing first, the same idea as the
emergency floor (core/first_aid_floor.py, which has a fire, a gas leak and carbon monoxide): the first words never
wait on a model that may be slow or wrong. Water and electricity together are the danger, so the power comes first
wherever water may reach it.

How: `reply(words)` (pure) gives the steps for the trouble the words say is happening ("a pipe burst in the
basement", "water's pouring from the ceiling", "my pipes are frozen", "the basement is flooding"), or None for
anything else, a question about the topic ("how do I keep pipes from freezing?") included, which is the library's or
the model's. Written from the American Red Cross's flood safety, FEMA's Ready.gov, and plumbers' and insurers' common
burst-pipe steps.
"""

from __future__ import annotations

import re
from typing import Optional

_POWER = ("If water is near outlets, cords, appliances or the electrical panel, don't walk into it: switch that power "
          "off at the breaker only if you can reach the panel standing somewhere dry; if you can't, stay out and call "
          "the power company.")
TROUBLE = (
    # a water pipe only: a power line is the emergency floor's, a brake or fuel line the shop's (the Fable review)
    ("burst", re.compile(r"\b(?:water )?pipes?\b(?!\s+tobacco).{0,20}\b(?:burst|bursted|broke|broken|split|cracked|"
                         r"leaking badly)\b|\b(?:water|supply|main) (?:line|main)s?\b.{0,20}\b(?:burst|broke|broken|split|"
                         r"cracked)\b|\bburst (?:water )?(?:pipe|main)s?\b|\bwater(?:'s| is)? (?:pouring|spraying|gushing|"
                         r"shooting|everywhere)\b"),
     "Shut off the water at the main valve first: usually where the water line comes into the house, by the meter or "
     "the water heater (turn it clockwise, or the lever across the pipe); a well's is at the pressure tank, and switch "
     "off the well pump's breaker too. " + _POWER + " Then open a faucet at the lowest point to drain the lines, "
     "move what you can out of the water, take photos for insurance, and call a plumber."),
    ("frozen", re.compile(r"\b(?:pipes?|water lines?|faucets?)\b.{0,15}\b(?:are |is )?froze(?:n)?\b(?!\s+(?:yogurt|food|"
                          r"pizza|treat|dinner))|\bno water\b.{0,30}\b(?:froze|frozen|freezing)\b|\bfrozen (?:pipes?|"
                          r"water lines?)\b"),
     "Open the faucet the frozen pipe feeds, so water can move as it thaws. Warm the pipe slowly, from the faucet end "
     "back: a hair dryer, a heating pad, towels soaked in hot water, or a space heater kept well away from anything that "
     "burns. Never an open flame or a torch. If it's split or you can't reach it, shut off the main and call a "
     "plumber."),
    ("flooding", re.compile(r"\b(?:basement|cellar|crawl ?space|house|garage|shop)'?s?\s+(?:is |'s )?(?:flooding|flooded|"
                            r"filling (?:up )?with water|under water|underwater|full of water)\b(?!\s+with\s+(?!water))|"
                            r"\b(?:basement|cellar|crawl ?space)\b.{0,40}\bit'?s (?:flooding|filling)\b|\b(?:water|inches of water|a foot of "
                            r"water)\s+in (?:the |my |our )?(?:basement|cellar|crawl ?space)\b|\bsump pump\b.{0,25}"
                            r"\b(?:failed|died|stopped|isn'?t working|not working|quit)\b"),
     _POWER + " Stay out of water that could be touching anything electrical, and out of floodwater outside: it can "
     "carry sewage and hide what's under it. Then find the source: a burst pipe (shut off the main), a sump pump (check "
     "its breaker and float), or water coming in from outside (move what you can up high). Take photos for insurance "
     "before you clean up."),
)
# a question about the topic, or one about later, is the library's or the model's
_ABOUT = re.compile(r"^\s*(?:how (?:do|can|should) (?:i|you|we) (?:keep|stop|prevent|avoid|protect)|how to (?:keep|"
                    r"prevent|avoid)|how much|what (?:causes|happens|does)|why do|is it (?:normal|bad)|is (?:water|a|"
                    r"it)\b.{0,30}\bcovered|can pipes|remind me|add\b|note\b)\b|\bprevent\b|\bwinteriz|\binsurance\b|"
                    r"\bcost\b|\blast (?:year|week|month|winter)\b|\b(?:my |a )?neighbou?r\b|\bbought\b|\bused to\b",
                    re.I)
# happening now, whatever the question's opening: "how do I keep it from flooding? it's flooding right now"
_NOW = re.compile(r"\bright now\b|\bit'?s (?:flooding|pouring|spraying)\b|\bhelp\b|!", re.I)


def reply(words: str) -> Optional[str]:
    """Pure logic. The fixed steps for the house's trouble his words say is happening, the first said (a burst pipe
    and a flooded basement together: the pipe's steps, which end with the power), or None (see the module's
    opening).
    A question about the cost, insurance or a neighbor's is the model's, unless it's happening right now."""
    said = " ".join(str(words or "").lower().replace("’", "'").split())
    if not said or (_ABOUT.search(said) and not _NOW.search(said)):
        return None
    return next((steps for _kind, pattern, steps in TROUBLE if pattern.search(said)), None)
