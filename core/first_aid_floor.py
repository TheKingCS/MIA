"""
core.first_aid_floor
======================

A floor for emergencies happening now (Jarvis brainstorm 4.2; Zac, 2026-11-23: "the ultimate tool offline and online
for survival skills"), the same idea as core/safety_floor.py: a deterministic check before the model, so the first
words he gets in an emergency never wait on a model that may be slow, offline, or wrong.

**When** (`detect`): the words say it's happening now to someone present ("he's not breathing", "she's choking",
"I cut my hand and it won't stop bleeding", "my dad has chest pain", "I got bit by a snake"): an emergency sign
together with a sign it's now (a person named, "I/he/she/my...", "right now", "just"). A question about the topic
("what are the signs of a stroke?", "how do you treat a snakebite?") isn't one: it goes to her library as usual,
where the reader answers from the first-aid pages.

**What she says** (`reply`): fixed, human-written words for each kind: call the emergency number first (by his
country, core/region.py, never a number that might be wrong), then the first thing to do now, in short steps, from
the standard first-aid guidance (American Red Cross and American Heart Association): CPR's rate and depth, abdominal
thrusts for choking, firm pressure and a tourniquet for bleeding a limb, the time a stroke began, an epinephrine
auto-injector, the recovery position, keeping a snakebite still. No medicine doses: those come from the emergency
operator. Then "tell me what's happening and I'll stay with you", so the conversation carries on.

**Scope, honestly:** a floor, not a medic. It catches clear words and misses indirect ones (tests list both); a
false positive costs one careful message with the number in it.
"""

from __future__ import annotations

import re
from typing import Optional

# Each kind: the words that say it, then what to do (after "Call {number} now."). Order matters: the first that
# matches is the one said, most time-critical first.
KINDS: list[tuple[str, re.Pattern, str]] = [
    ("cpr", re.compile(r"\b(?:not|isn'?t|stopped|no longer|can'?t|cannot) breath(?:ing|e)\b|\bno pulse\b|"
                       r"\bheart (?:stopped|has stopped)\b|\bcardiac arrest\b|\bturning blue\b"),
     "If they don't respond and aren't breathing normally, start CPR: kneel beside them, heel of one hand in the "
     "center of the chest, the other on top; push hard and fast, about 2 inches deep, 100 to 120 times a minute, "
     "letting the chest come back up each time. Keep going until help takes over. If there's an AED, turn it on and "
     "do what it says."),
    ("choking", re.compile(r"\bchok(?:ing|es|ed)\b|\bsomething (?:stuck|caught) in (?:his|her|their|my) throat\b"),
     "If they can't cough, speak or breathe: stand behind them, a fist just above the belly button, your other hand "
     "over it, and give quick hard thrusts in and up until it comes out. A baby under one year: 5 back slaps then 5 "
     "chest thrusts with two fingers. If they stop responding, lower them down and start CPR."),
    ("anaphylaxis", re.compile(r"\banaphyla\w*|\b(?:throat|tongue|lips?|face) (?:is |are )?(?:swelling|closing|"
                               r"swollen)\b|\ballergic reaction\b.*\b(?:breath|swell)"),
     "If they have an epinephrine auto-injector (an EpiPen), use it now: press it hard into the outer thigh and hold "
     "it there for a few seconds; through clothes is fine. Keep them lying down with legs raised, or sitting up if "
     "breathing is easier. A second dose may be needed if help is more than 5 to 15 minutes away and it's no better."),
    ("bleeding", re.compile(r"\b(?:won'?t|will not|can'?t|doesn'?t|isn'?t) stop(?:ping)? bleeding\b|"
                            r"\bbleeding (?:a lot|badly|heavily|everywhere|out|bad)\b|\bblood (?:is )?(?:spurting|"
                            r"pouring|everywhere)\b|\b(?:severe|heavy|serious) bleeding\b|\bcut (?:off|deep)\b"),
     "Press hard on the wound with a cloth or your hand, and keep pressing; don't lift it to look. If blood soaks "
     "through, add more on top. If it's an arm or leg and pressure doesn't stop it, put a tourniquet (a belt or "
     "strip of cloth, tightened with a stick) 2 to 3 inches above the wound, tight until the bleeding stops, and note "
     "the time."),
    ("stroke", re.compile(r"(?<!heat )\bstroke\b|\b(?:face|mouth|smile) (?:is )?droop(?:ing|s|y)?\b|\bslurr(?:ing|ed) (?:his|"
                          r"her|their|my) (?:words|speech)\b|\bcan'?t (?:raise|lift) (?:his|her|their|my) arm\b"),
     "Note the time it started: the hospital needs it. Keep them lying down with the head a little raised, and give "
     "nothing to eat or drink. If they stop responding and aren't breathing normally, start CPR."),
    ("heart", re.compile(r"\bchest (?:pain|pains|hurts|pressure|tightness)\b|\bheart attack\b|\bpain (?:down|in) "
                         r"(?:his|her|their|my) (?:left )?arm\b"),
     "Have them stop and sit down, resting, loosen anything tight. Tell the operator about any medicines they take: "
     "they may tell you to have them chew an aspirin. If they stop responding and aren't breathing normally, start "
     "CPR."),
    ("unconscious", re.compile(r"\b(?:unconscious|passed out|unresponsive|won'?t wake up|not waking up|"
                               r"collapsed|knocked out)\b"),
     "Check if they're breathing. If they are, roll them onto their side, top knee bent, head tilted back so the "
     "airway stays open, and watch the breathing. If they aren't breathing normally, start CPR."),
    ("poison", re.compile(r"\b(?:overdos\w+|swallowed (?:bleach|poison|pills|chemicals?|antifreeze|a battery)|"
                          r"poisoned|drank (?:bleach|antifreeze|gas(?:oline)?|poison))\b"),
     "Don't make them throw up. Keep whatever they took (the bottle or package) to tell the operator. If they stop "
     "responding, roll them onto their side; if they aren't breathing normally, start CPR."),
    ("snakebite", re.compile(r"\b(?:snake ?bit\w*|bit(?:ten)? by a (?:snake|rattlesnake|copperhead|cottonmouth))\b"),
     "Keep them still and calm, the bitten part still and at or below the heart. Take off rings, watches and tight "
     "things near the bite before it swells. Don't cut it, suck it, ice it or put a tourniquet on it."),
    ("burn", re.compile(r"\b(?:bad|badly|severe|serious) burn\w*|\bburn(?:ed|t) (?:badly|bad|all over)\b|"
                        r"\bon fire\b|\bclothes (?:caught|on) fire\b"),
     "Stop the burning: stop, drop and roll, or smother it. Cool the burn under cool (not icy) running water for 10 "
     "to 20 minutes. Take off rings and anything tight, but not clothing stuck to the skin. Cover it loosely with "
     "clean plastic wrap or a clean cloth."),
    ("heat", re.compile(r"\bheat ?stroke\b|\b(?:overheated|overheating) and (?:confused|not making sense)\b"),
     "Move them somewhere cool, and cool them fast: cold water over the body, or wet cloths and a fan, ice packs at "
     "the neck, armpits and groin. Nothing to drink unless they're fully awake."),
    ("hypothermia", re.compile(r"\bhypotherm\w*\b|\b(?:shivering|freezing) and (?:confused|not making sense|"
                               r"won'?t wake)\b"),
     "Get them out of the cold and out of wet clothes, into dry layers and blankets, covering the head. Warm the "
     "middle of the body first; move them gently. Warm sweet drinks only if they're fully awake."),
]

# Now, to someone here: a person named, or "right now", "just".
_NOW = re.compile(r"\b(?:i|i'm|im|i've|he|he's|his|she|she's|her|they|they're|their|we|we're|our|my|someone|somebody|my (?:wife|husband|son|"
                  r"daughter|dad|mom|friend|kid|baby)|right now|just)\b", re.I)
# A question about the topic, not one happening: "what are the signs", "how do you treat", "what to do if".
_ABOUT = re.compile(r"^\s*(?:what (?:are|is) (?:the )?(?:signs?|symptoms?|causes?|difference)|how (?:do|does|would|"
                    r"should) (?:you|one|people|someone) |what (?:should|do) (?:you|one) do (?:if|when)|"
                    r"what to do (?:if|when)|tell me about|explain|teach me|how to (?:treat|tell|recognize))", re.I)


def detect(prompt: str) -> Optional[str]:
    """Pure logic. The kind of emergency these words say is happening now ("cpr", "choking", ...), or None."""
    text = " ".join(str(prompt or "").lower().replace("’", "'").split())
    if not text or _ABOUT.search(text) or not _NOW.search(text):
        return None
    return next((kind for kind, words, _do in KINDS if words.search(text)), None)


def reply(kind: str, where=None) -> str:
    """Pure logic. The fixed words for this kind: call the emergency number first (the person's country's), then the
    first thing to do now, then that she's staying with him."""
    from core.region import DEFAULT, REGIONS

    region = where or REGIONS[DEFAULT]
    steps = next(do for k, _w, do in KINDS if k == kind)
    return (f"Call {region.emergency} now, or have someone else call while you help. {steps} "
            "Tell me what's happening and I'll stay with you and help.")
