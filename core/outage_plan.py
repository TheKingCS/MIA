"""
core.outage_plan
==================

Ready for the power going out (the live sweep, 2026-11-25: "What do I do if the power goes out for a week?" got a
generic list that knew nothing of his own stores): the first things to do, in fixed words from Ready.gov and the
USDA's food safety guidance, then his own readiness from his records (core/preparedness.say: water against his
target, days of food from the staples, the generator's days on the fuel he has), then the outage clock for when it
happens (core/outage.py: "the power went out" starts it) and the drill that practises it.

How: `reply(context, words)` answers the question asked ahead ("what do I do if the power goes out for a week?",
"if we lose power for a few days...", "how do I prepare for a power outage?"), never the power going out now (the
outage clock's, core/outage.py) or his power bill, a solar panel or a power tool. Read-only.
"""

from __future__ import annotations

import re
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

STEPS = ("Keep the fridge and freezer shut: a closed fridge keeps food cold about 4 hours, a full freezer about 48 "
         "(half full, 24). Run a generator only outside, 20 feet from doors and windows, never in the garage or the "
         "house, and plug things into it with a heavy outdoor cord, never into a wall outlet. Use flashlights rather "
         "than candles, unplug electronics so the surge when it comes back doesn't take them, and report it to the "
         "power company.")
# asked ahead, never happening now ("the power went out" is the outage clock's, core/outage.py)
_ASKED = re.compile(r"\b(?:what (?:do|should|would|can) (?:i|we) do|how (?:do|should|can) (?:i|we) (?:prepare|get ready|be "
                    r"ready)|what (?:do|should) (?:i|we) (?:need|have))\b.{0,30}\b(?:if|when|for)\b.{0,25}\b(?:power|"
                    r"electricity|grid)\b|\bif (?:the )?(?:power|electricity|grid) (?:goes|go|were to go|went) (?:out|"
                    r"down)\b|\bif (?:we|i) (?:lose|lost) (?:the )?(?:power|electricity)\b|\b(?:prepare|get ready|be "
                    r"ready) for (?:a |the )?(?:long )?(?:power outage|blackout|outage)\b|\bpower outage (?:for|that lasts|"
                    r"of) (?:a |several |a few )?(?:days?|weeks?|week)\b", re.I)
_NOT = re.compile(r"\b(?:bill|bills|rate|rates|company'?s? number|solar panels?|power tools?|power steering|power "
                  r"washer|power supply|power bank|powerpoint|game|show|movie|drill)\b", re.I)


def reply(context, words: str) -> Optional[str]:
    """The first things to do with the power out, then his own readiness (core/preparedness.say), then the drill;
    None for anything else (see the module's opening)."""
    said = str(words or "")
    if not _ASKED.search(said) or _NOT.search(said):
        return None
    from core import preparedness

    try:
        ready = preparedness.say(context)
    except Exception:  # noqa: BLE001 - his records that can't be read never take the steps with them
        log.exception("The outage answer couldn't read his readiness")
        ready = ""
    out = STEPS + (f" From your records: {ready}" if ready else "")
    return out + (" When it does go out, say \"the power went out\" and I'll keep the clock for the fridge and "
                  "freezer. To practise it, say \"give me a power outage drill\".")
