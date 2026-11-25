"""
core.first_aid_floor
======================

A floor for emergencies happening now (Jarvis brainstorm 4.2; Zac, 2026-11-23: "the ultimate tool offline and online
for survival skills"), the same idea as core/safety_floor.py: a deterministic check before the model, so the first
words he gets in an emergency never wait on a model that may be slow, offline, or wrong. It runs even when no model
is set up (the desktop's three chat boxes ask `detect` before giving up on a turn).

**When** (`detect`): the words name an emergency (each kind's own pattern in `KINDS`) and don't read as a question
about the topic or a past one. A question ("what are the signs of a stroke?", "how do you treat a snakebite?") goes
to her library as usual, unless the same words say it's happening ("what do I do, my baby is choking right now").
Something from the past ("my dad had a heart attack in 2019") isn't one, nor practice asked for ("give me a choking
drill", core/drills.py), unless the same words say it's real ("he's choking, this is not a drill"). Panicked words are short, so no pronoun is
needed: "baby not breathing" counts. Each pattern asks for a person or body where an everyday sentence could match
("my laptop won't wake up", "a 2-stroke chainsaw", "the power got cut off", "my heart stopped when I saw the bill").

**What she says** (`reply`): fixed, human-written words: call the emergency number first (by his country,
core/region.py, never a number that might be wrong), then the first thing to do now for each kind that matched, most
time-critical first (choking before CPR, so "she's choking and can't breathe" gets the thrusts), from the standard
first-aid guidance (American Red Cross and American Heart Association). No medicine doses: those come from the
emergency operator. Then that she'll stay with him.

**A first-aid answer from her library** (`library_floor`, core/tool_loop.py): when the question is about one of
these emergencies (`topic_kinds`, happening now or not), the answer ends with when to call and the number, unless it
already gives it.

**After it** (`floor_kind_of`): his next words in the same emergency go on to the model, which reads the conversation
with the floor's reply in it; the fixed words are said again only for a different emergency.

**Scope, honestly:** a floor, not a medic. It catches clear words and misses some indirect ones (the tests list both);
a false positive costs one careful message with the number in it. Reviewed 2026-11-23 against a corpus of panicked
phrasings and everyday sentences (tests/test_first_aid_floor.py).
"""

from __future__ import annotations

import re
from typing import Optional

_WHO = (r"(?<![a-z'])(?:he|she|they|i|we|someone|somebody|the baby|baby|my (?:\w+ ){0,2}(?:wife|husband|son|daughter|dad|father|"
        r"mom|mother|friend|kid|baby|child|brother|sister|grandpa|grandma|grandfather|grandmother|neighbou?r|partner|"
        r"boy|girl|uncle|aunt|cousin))")
# A family member named bare ("grandma collapsed"): only with the emergency at the end of its clause, never an object
# after it ("mom passed out the cookies", "dad collapsed the tent": the eighth review)
_FAMILY = r"(?<![a-z'])(?:grandma|grandpa|granny|nana|mom|mum|dad|mother|father)"
_CPR_SHORT = "If they stop responding and aren't breathing normally, start CPR: push hard and fast in the center of the chest."

# Each kind: (id, the words that say it, what to do after "Call {number} now."). Most time-critical first; when several
# match, the first two are said.
KINDS: list[tuple[str, re.Pattern, str]] = [
    ("choking", re.compile(r"\bchok(?:ing|es|ed)\b|"
                           r"\bsomething (?:stuck|caught) in (?:his|her|their|my|the baby'?s) throat\b|\bheimlich\b"),
     "If they can't cough, speak or breathe: give 5 firm back blows between the shoulder blades with the heel of your "
     "hand, then 5 quick thrusts in and up with your fist just above the belly button; keep switching until it comes "
     "out. A baby under one year: face down along your forearm, 5 back blows, then face up, 5 chest thrusts in the "
     "center of the chest. If they stop responding, lower them down and start CPR."),
    ("anaphylaxis", re.compile(r"\banaphyla\w*|\b(?:throat|tongue|lips?|face) (?:is |are |keeps )?(?:swelling|closing|"
                               r"swollen|swelling up)\b|\ballergic reaction\b|\bepi-?pen\b"),
     "If they have an epinephrine auto-injector (an EpiPen), use it now: press it hard into the outer thigh and hold it "
     "there for a few seconds; through clothes is fine. Keep them lying down with legs raised, or sitting up if "
     "breathing is easier. A second dose may be needed if they're no better after 5 to 15 minutes and help hasn't "
     "come."),
    ("drowning", re.compile(r"\bdrown(?:ing|ed)?\b|\b(?:pulled|got) (?:him|her|them|my \w+) out of the (?:water|pond|"
                            r"pool|lake|river|creek)\b|\bfell (?:in|into) the (?:pond|pool|lake|river|creek|water)\b"),
     "Get them out of the water without going in yourself if you can: reach with a pole or throw something that "
     "floats. If they aren't breathing normally, start CPR; drowning is a lack of air, so give rescue breaths too if "
     "you know how. Keep them warm."),
    ("shock", re.compile(r"\belectrocut\w*|\b(?:got|been|was|is) (?:shocked|zapped)\b|\belectric(?:al)? shock\b|"
                         r"\btouched (?:a|the) (?:live|power) (?:wire|line)\b|\bpower line\b.{0,20}\b(?:down|touch\w*|"
                         r"hit)\b"),
     "Don't touch them until the power is off: switch it off at the breaker or unplug it, or push the source away with "
     "something dry that isn't metal (a wooden broom handle). Stay well back from a downed power line. Once it's off, "
     "if they aren't breathing normally, start CPR; cover any burns loosely."),
    ("cpr", re.compile(r"\b(?:not|isn'?t|aren'?t|stopped|no longer|quit) breathing\b|\bno pulse\b|"
                       r"\b(?:his|her|their|baby'?s|the baby'?s) heart (?:has )?stopped\b|\bcardiac arrest\b|"
                       r"\b(?:lips|face|he|she|baby|they) (?:is |are |'s )?(?:turning|turned|going) blue\b"),
     "If they don't respond and aren't breathing normally, start CPR: kneel beside them, heel of one hand in the "
     "center of the chest, the other on top; push hard and fast, about 2 inches deep, 100 to 120 times a minute, "
     "letting the chest come back up each time. A baby: about 1.5 inches deep, with two thumbs or the heel of one "
     "hand. Keep going until help takes over. If there's an AED, turn it on and do what it says."),
    ("breathing", re.compile(r"\b(?:can'?t|cannot|can not|struggling to|having trouble) breath(?:e|ing)\b"
                             r"(?! through (?:my|his|her|their) nose)|"
                             r"\basthma attack\b|\bgasping\b"),
     "Sit them upright, leaning a little forward, and keep them calm. If they have a rescue inhaler, help them use it "
     "as it's prescribed. Loosen anything tight. If their lips go blue or they can't speak, tell the operator."),
    ("bleeding", re.compile(r"\b(?:won'?t|will not|can'?t|doesn'?t|isn'?t|not) stop(?:ping)? bleeding\b|"
                            r"\bbleeding (?:really |so |very )?(?:a lot|badly|bad|heavily|everywhere|out|hard)\b|"
                            r"\b(?:he|she|they|i|baby|it)(?:'s| is| am| are|'m|'re)? (?:still )?bleeding\b"
                            r"(?! (?:the|my|our|his|her|a) (?:brakes?|radiators?|lines?|air|pipes?|system|hydraulics))|"
                            r"\bblood (?:is )?(?:spurting|pouring|everywhere|gushing)\b|"
                            r"\bbleeding (?:won'?t|will not|doesn'?t|isn'?t|is not) stop\w*\b"
                            r"(?! (?:on|in) (?:this|the|my) (?:paint|stain|print|shirt|wash|dye))|"
                            r"\b(?:gushing|spurting|pouring) blood\b(?! in (?:the|a|that) (?:movie|film|show|game|scene))|"
                            r"\bcut (?:my|his|her|their|the baby'?s|a) (?:\w+ )?(?:finger|thumb|toe|hand|arm|leg|foot)s? "
                            r"(?:off|clean off)\b(?! (?:the|a|my|of) )|"
                            r"\b(?:severe|heavy|serious|bad) bleeding\b|\bdeep (?:cut|gash|wound)\b|"
                            r"\bcut (?:my |his |her |their |the baby'?s |a )?(?:hand|finger|thumb|leg|arm|foot|"
                            r"toe|head|face|wrist|knee|neck|palm|shin)\b.{0,25}\b(?:deep|to the bone|bad|badly)\b|\b(?:been|got|was|i'?m) (?:shot|stabbed)\b|"
                            r"\b(?:shot|stabbed) (?:him|her|me|them)\b"),
     "Press hard on the wound with a cloth or your hand, and keep pressing; don't lift it to look. If blood soaks "
     "through, add more on top. If it's an arm or leg and pressure doesn't stop it, put a tourniquet (a belt or strip "
     "of cloth, tightened with a stick) 2 to 3 inches above the wound, tight until the bleeding stops, and note the "
     "time."),
    ("heat", re.compile(r"\b(?:heat|sun)[\s-]?stroke\b|\b(?:overheated|overheating) and (?:confused|not making sense|"
                        r"passed out)\b"),
     "Move them somewhere cool, and cool them fast: cold water over the body, or wet cloths and a fan, ice packs at "
     "the neck, armpits and groin. Nothing to drink unless they're fully awake."),
    ("stroke", re.compile(r"\b(?:having|had|has|is|it'?s|maybe|think it'?s|think (?:he|she|they)'?s? (?:having|had)) "
                          r"a stroke\b(?! of)|\b(?:face|mouth|smile) (?:is )?droop(?:ing|s|y)?\b|"
                          r"\b(?:speech|words) (?:is |are )?slurr(?:ed|ing)\b|\bslurr(?:ing|ed) (?:his|her|their|my) "
                          r"(?:words|speech)\b|\bcan'?t (?:raise|lift) (?:his|her|their|my|one) arm\b|"
                          r"\bone side (?:of (?:his|her|their|my) (?:face|body) )?(?:is )?(?:numb|weak|drooping)\b"),
     "Note the time it started: the hospital needs it. Keep them lying down with the head a little raised, and give "
     "nothing to eat or drink. If they stop responding and aren't breathing normally, start CPR."),
    ("heart", re.compile(r"\bchest (?:pain|pains|hurts|pressure|tightness)\b|\bpain in (?:my|his|her|their) chest\b|"
                         r"\bcrushing (?:pain|feeling)\b.{0,20}\bchest\b|\b(?:having|has|is having) a heart attack\b|"
                         r"\bheart attack\b|\bpain (?:down|in) (?:his|her|their|my) (?:left )?arm\b"),
     "Have them stop and sit down, resting; loosen anything tight. Tell the operator about any medicines they take: "
     "they may tell you to have them chew an aspirin. If they stop responding and aren't breathing normally, start "
     "CPR."),
    ("unconscious", re.compile(_FAMILY + r"\s+(?:just |suddenly )?(?:collapsed|passed out|fainted|blacked out|"
                               r"won'?t wake up|is unconscious|is unresponsive|isn'?t responding)(?=\s*(?:[.!,?]|$|and\b|on\b|"
                               r"in\b|at\b|while\b|again\b|just\b|when\b))|"
                               + _WHO + r"\b(?:'s|'re| is| are| has| just| was)?\s?(?:just |suddenly )?(?:collapsed|"
                               r"won'?t wake up|not waking up|not responding|unresponsive|unconscious|fainted|"
                               r"blacked out|passed out)\b|\b(?:got|was|been|is) knocked (?:out|unconscious)\b|"
                               r"\bunconscious\b(?! (?:bias|mind|thoughts?))|\bunresponsive\b|"
                               r"\b(?:is|are|isn'?t|aren'?t) (?:not )?responding\b"),
     "Check if they're breathing. If they are, roll them onto their side, top knee bent, head tilted back so the "
     "airway stays open, and watch the breathing. If they fell or may have hurt the neck or back, don't move them "
     "unless you must to keep the airway open or get them out of danger. If they aren't breathing normally, start "
     "CPR."),
    ("seizure", re.compile(r"\bseizures?\b|\b(?:he|she|they|baby|my \w+)(?:'s| is| are|'re) seizing\b|\bconvuls\w*|\b(?:having|has) a fit\b|\bshaking (?:all over|and "
                           r"won'?t stop)\b"),
     "Don't hold them down and don't put anything in their mouth. Move hard things away, cushion the head, and time "
     "it. When the shaking stops, roll them onto their side and stay with them. Tell the operator if it lasts more "
     "than 5 minutes or happened in water."),
    ("poison", re.compile(r"\boverdos\w*|\bpoisoned\b|\btook too many\b|\bswallowed\b.{0,30}\b(?:pills?|tablets?|"
                          r"bleach|poison|chemicals?|antifreeze|batter(?:y|ies)|medicine|cleaner|lye|gas(?:oline)?|"
                          r"detergent|pods?|rat poison)\b|\bdrank\b.{0,20}\b(?:bleach|antifreeze|gas(?:oline)?|poison|"
                          r"cleaner|lye|chemicals?)\b|\bate\b.{0,20}\b(?:rat poison|mushrooms? from the yard|pills)\b"),
     "Don't make them throw up. Keep whatever they took (the bottle or package) to tell the operator; a swallowed "
     "button battery needs the emergency room right away. If they stop responding, roll them onto their side; if they "
     "aren't breathing normally, start CPR."),
    ("snakebite", re.compile(r"\bsnake ?bit\w*|\bbit(?:ten)? by a\b.{0,15}\b(?:snake|rattlesnake|rattler|copperhead|"
                             r"cottonmouth|viper|adder|water moccasin)\b|\b(?:snake|rattlesnake|rattler|copperhead|cottonmouth|viper|adder|"
                             r"water moccasin)\b.{0,15}\bbit\b"),
     "Keep them still and calm, the bitten part still and at or below the heart. Take off rings, watches and tight "
     "things near the bite before it swells. Don't cut it, suck it, ice it or put a tourniquet on it."),
    ("burn", re.compile(r"\bburn(?:ed|t)\b.{0,25}\b(?:badly|bad|all over|blister\w*|skin)\b|"
                        r"\b(?:bad|badly|severe|serious|deep) burns?\b|\bclothes (?:caught|are on|on) fire\b|"
                        r"\b(?:he|she|they|baby|my \w+)(?:'s| is| are|'re) on fire\b"),
     "Stop the burning: stop, drop and roll, or smother it. Cool the burn under cool (not icy) running water for 10 "
     "to 20 minutes. Take off rings and anything tight, but not clothing stuck to the skin. Cover it loosely with "
     "clean plastic wrap or a clean cloth."),
    ("hypothermia", re.compile(r"\bhypotherm\w*\b|\b(?:shivering|freezing|so cold) and (?:confused|not making sense|"
                               r"won'?t wake|slurring)\b|\bfrostbit\w*\b"),
     "Get them out of the cold and out of wet clothes, into dry layers and blankets, covering the head. Warm the "
     "middle of the body first; move them gently. Warm sweet drinks only if they're fully awake."),
]

# A question about the topic, not one happening: "what are the signs", "how do you treat", "what to do if".
_ABOUT = re.compile(r"^\s*(?:what (?:are|is) (?:the )?(?:signs?|symptoms?|causes?|difference)|how (?:do|does|would|"
                    r"should|can) (?:you|one|people|someone) |what (?:should|do) (?:you|one|people) do (?:if|when)|"
                    r"what to do (?:if|when)|tell me about|explain|teach me|how to (?:treat|tell|recognize|prevent|"
                    r"identify)|is it (?:true|bad|safe)|why (?:do|does|is))", re.I)
# Words that say it's happening, which win over a question's opening: "what do I do, my baby is choking right now".
_HAPPENING = re.compile(r"\bright now\b|\bhelp\b|!|\b(?:he|she|they)(?:'s| is| are|'re)\b|\bi'm\b|\bi am\b|"
                        r"\bmy (?:\w+ ){0,2}(?:is|are|has|just)\b|\bjust (?:now|happened)\b", re.I)
# Something from the past: "had a heart attack in 2019", "years ago".
_PAST = re.compile(r"\bin (?:19|20)\d\d\b|\b(?:years?|months?|weeks?) ago\b|\blast (?:year|month|week)\b|"
                   r"\bwhen (?:i|he|she) was (?:a )?(?:kid|young|little|child)\b", re.I)
# A figure of speech: "I'm drowning in work", "choking on all this paperwork", "almost had a heart attack".
_FIGURE = re.compile(r"\b(?:movie|film|show|episode|game|scene|book|video)\b.{0,30}\b(?:gushing|spurting|pouring) "
                     r"blood\b|\bdrowning in\b|\bchok(?:ing|ed) on (?:all )?(?:this|that|the|my|these) (?:paperwork|work|news|"
                     r"traffic|emails?|bills?|deadlines?)\b|\b(?:almost|nearly) (?:had|died|choked|drowned)\b|"
                     r"\bgave me a heart attack\b|\bmy heart (?:almost |nearly )?stopped when\b|\bunresponsive "
                     r"(?:app|page|website|computer|laptop|screen|server)\b|\b(?:app|page|website|site|computer|"
                     r"laptop|screen|server|program|phone|printer|mouse|keyboard|browser|tv|it)\b.{0,15}"
                     r"\b(?:not responding|unresponsive)\b|"
                     # the homestead's own words (review 2026-11-23): engines, fences, plants, cooking, lines
                     r"\bchok\w*\s+(?:the\s+|my\s+)?(?:engine|carb\w*|saw|chainsaw|mower|motor|truck|tractor)\b|\bthe choke\b|"
                     r"\b(?:engine|motor|pump|bearing|piston|chainsaw|saw|bolt|brake|caliper)s?\s+seiz\w*|"
                     r"\bseiz\w*\s+(?:up|the\s+(?:engine|bolt|motor))|\belectric fence\b|\bfence (?:charger|energi[sz]er)\b|"
                     r"\bdrown\w*\s+(?:the\s+|my\s+)?(?:\w+\s+)?(?:seedlings?|plants?|tomato(?:es)?|garden|roots|"
                     r"crops?|lawn|beds?|starts|transplants)\b|"
                     r"\bburn\w*\s+(?:the\s+|my\s+)?(?:rice|toast|food|dinner|pan|pot|beans|bread|cookies|meat|steak|"
                     r"sauce|brush|pile|trash|wood|leaves)\b|"
                     r"\b(?:lines?|brakes?|hydraulics?|radiators?)\b.{0,25}\bbleed\w*|\bbleed\w*\b.{0,15}\b(?:lines?|"
                     r"brakes?|air)\b|\b(?:throttle|mower|engine|tractor|truck|pump|controller|sensor|remote|valve)\b"
                     r".{0,25}\b(?:unresponsive|not responding)\b|\boverdos\w*\s+(?:the\s+|my\s+)?(?:tomatoes|plants?|"
                     r"garden|lawn|soil|seedlings?)\b|\bon (?:fertili[sz]er|nitrogen)\b", re.I)
# Practice asked for, not an emergency: only a drill actually asked for ("give me a choking drill", "quiz me on
# bleeding": core/drills.requested, the same words that start one), never the bare noun (the sixth review: "she choked
# at soccer practice and can't breathe", "I cut my hand with the drill and it won't stop bleeding" had gone quiet);
# "this is not a drill" and anything that says it's happening still are emergencies.
_REAL = re.compile(r"\b(?:not|isn'?t|no|ain'?t) (?:a |no )?drill\b|\bfor real\b|\breal(?:ly)? happening\b")


def _left_after_drill(text: str) -> bool:
    """Pure logic. Whether an emergency is still named once the drill's own words are taken out ("give me a choking
    drill, baby can't breathe" still says baby can't breathe: the seventh review). Any doubt is an emergency."""
    try:
        from core.drills import _ASKED_FOR, _REQUEST

        rest = _REQUEST.sub(" ", _ASKED_FOR.sub(" ", text))
    except Exception:  # noqa: BLE001 - if it can't tell, the floor answers
        return True
    return any(words.search(rest) for _kind, words, _do in KINDS)


def _practice_asked(text: str) -> bool:
    """Pure logic. Whether the words ask for a drill (core/drills.requested), so they're practice, not an
    emergency."""
    try:
        from core.drills import requested

        return requested(text) is not None
    except Exception:  # noqa: BLE001 - if it can't tell, it's never practice: the floor answers
        return False
# An animal and no person: the vet's work, not these words ("my dog is choking", "the hens are gasping").
_ANIMAL = re.compile(r"\b(?:dog|dogs|puppy|cat|cats|kitten|chickens?|hens?|rooster|horse|goat|cow|calf|pig|sheep|"
                     r"lamb|duck|rabbit|bird|birds|chicks?)\b", re.I)
_PERSON = re.compile(_WHO + r"\b|\b(?:me|him|her|them|us|i'm|i've|i)\b", re.I)
# The floor's own reply, found again in the conversation (`floor_kind_of`).
MARK = "or have someone else call while you help."


def kinds(prompt: str) -> list[str]:
    """Pure logic. Every kind of emergency these words say is happening now, most time-critical first ([] for none).
    A drill asked for (core/drills.requested) isn't one, unless the words also say it's happening or real, or an
    emergency is left once the drill's own words are out (`_left_after_drill`); a bare "practice" or "drill" never
    turns the floor off."""
    text = " ".join(str(prompt or "").lower().replace("’", "'").split())
    if not text:
        return []
    found = [kind for kind, words, _do in KINDS if words.search(text)]
    if not found:
        return []
    if _FIGURE.search(text) or (_ANIMAL.search(text) and not _PERSON.search(text)):
        return []
    happening = bool(_HAPPENING.search(text))
    if (_ABOUT.search(text) or _PAST.search(text)) and not happening:
        return []
    if _practice_asked(text) and not _REAL.search(text) and not _HAPPENING.search(re.sub(r"\bhelp me\b", " ", text)) \
            and not _left_after_drill(text):
        return []  # "help me practice the choking drill" is practice; "help, he's choking" never is
    return found


def detect(prompt: str) -> Optional[str]:
    """Pure logic. The most time-critical kind of emergency these words say is happening now, or None."""
    found = kinds(prompt)
    return found[0] if found else None


def reply(kind, where=None) -> str:
    """Pure logic. The fixed words for a kind (or a list of kinds, the first two said): call the emergency number
    first (the person's country's), then what to do now, then that she's staying with him."""
    from core.region import DEFAULT, REGIONS

    region = where or REGIONS[DEFAULT]
    wanted = [kind] if isinstance(kind, str) else list(kind)[:2]
    steps = [do for k in wanted for kk, _w, do in KINDS if kk == k]
    if len(wanted) == 1 and wanted[0] not in ("cpr", "choking", "drowning", "shock", "unconscious", "stroke", "heart",
                                              "poison", "seizure"):
        steps.append(_CPR_SHORT)  # the kinds whose own words don't already say when to start CPR
    return f"Call {region.emergency} now, {MARK} " + " ".join(steps) + " Tell me what's happening and I'll stay with you and help."


def _says_number(region, answer: str) -> bool:
    """Pure logic. Whether an answer already gives the region's emergency number, as a whole number ("000" isn't in
    "1,000 mg"); never for a region without a listed number."""
    if not region.emergency[:1].isdigit():
        return False
    return any(re.search(rf"(?<!\d)(?<!\d[,.]){re.escape(n)}(?!\d|[,.]\d)", answer)  # "911," yes; "1,000" no
               for n in re.findall(r"\d+", region.emergency))


def topic_kinds(prompt: str) -> list[str]:
    """Pure logic. The emergencies a question is about, happening now or not ("how do you treat a snakebite?" is
    snakebite), leaving out figures of speech and animals: for `library_floor`."""
    text = " ".join(str(prompt or "").lower().replace("\u2019", "'").split())
    if not text or _FIGURE.search(text) or (_ANIMAL.search(text) and not _PERSON.search(text)):
        return []
    return [kind for kind, words, _do in KINDS if words.search(text)]


def library_floor(prompt: str, answer: str, where=None) -> str:
    """Pure logic. A first-aid answer from her library (brainstorm 4.2): when the question is about one of the
    emergencies here, the answer ends with when to call for help and the number (his country's), unless it already
    gives the number as a whole number (`_says_number`; never assumed for a country without one listed). Every other
    answer is left as it is."""
    from core.region import DEFAULT, REGIONS

    found = topic_kinds(prompt)
    if not found:
        return answer
    region = where or REGIONS[DEFAULT]
    number = region.emergency
    if _says_number(region, str(answer or "")):
        return answer
    return (str(answer or "").rstrip() + f" If it's happening now, or it's severe, call {number} first; this is "
            "first aid until help comes, not instead of it.")


# A first-aid question's subject, in plainer words than an emergency's ("how do you use a tourniquet?")
_TOPIC: list[tuple[str, re.Pattern]] = [
    ("choking", re.compile(r"\bchok\w*|\bheimlich\b|\babdominal thrusts?\b")),
    ("bleeding", re.compile(r"\btourniquets?\b|\bbleed\w*|\b(?:deep|bad) cuts?\b|\bwounds?\b")),
    ("cpr", re.compile(r"\bcpr\b|\bchest compressions?\b")),
    ("anaphylaxis", re.compile(r"\banaphyla\w*|\bepi-?pens?\b|\ballergic reactions?\b")),
    ("heat", re.compile(r"\b(?:heat|sun)[\s-]?stroke\b|\bheat exhaustion\b")),
    ("hypothermia", re.compile(r"\bhypotherm\w*|\bfrostbit\w*")),
    ("burn", re.compile(r"\bburns?\b")),
    ("drowning", re.compile(r"\bdrown\w*")),
    ("snakebite", re.compile(r"\bsnake ?bites?\b")),
]
# A how-to whose words aren't first aid (the sixth review): bleeding a radiator or maple trees, burning stumps or a CD,
# choking a chainsaw or up on a bat, a spring wound up
_NOT_FIRST_AID = re.compile(r"\bbleed\w*\s+(?:the\s+|a\s+|my\s+)?(?:radiators?|brakes?|lines?|air|maples?|trees?|"
                            r"sap|syrup|hydraulics?|injectors?|fuel|system)\b|\bburn\w*\s+(?:the\s+|a\s+|my\s+|off\s+)?"
                            r"(?:stumps?|brush|piles?|cds?|dvds?|discs?|calories|fat|wood|trash|leaves|fields?|"
                            r"rubber|clutch|in\b)|\bchok\w*\s+up\b|\bchok\w*\s+(?:the\s+|a\s+|my\s+)?(?:chainsaw|saw|"
                            r"engine|motor|mower|carb\w*)\b|\bwound up\b|\bwind(?:ing)? up\b")
_HOWTO = re.compile(r"^\s*(?:how (?:do|should|would|can|could) (?:i|you|one|we|people|someone) |how to |what (?:should|"
                    r"do|would) (?:i|you|one|we) do (?:if|when|for|about|with)|what to do (?:if|when|for|about)|"
                    r"what'?s the (?:right |best )?way to |teach me (?:how )?to )")


def teach(prompt: str, where=None) -> Optional[str]:
    """Pure logic. A how-to question about first aid ("how do you use a tourniquet?", "what do you do if someone is
    choking?") answered in the floor's own words, from the Red Cross's and the AHA's guidance, with the number to call
    when it's real (live check, 2026-11-25: the model refused the tourniquet). None for anything else: one happening
    now is `respond`'s, signs and symptoms are the library's, an animal's is the vet's, and a how-to in other words
    (bleeding the brakes, burning stumps, choking a chainsaw: `_NOT_FIRST_AID`) isn't first aid."""
    from core.region import DEFAULT, REGIONS

    text = " ".join(str(prompt or "").lower().replace("’", "'").split())
    # an animal named is the vet's, whoever asks ("how do I treat a wound on my horse?": "I" is always a person here)
    if not _HOWTO.search(text) or detect(text) or _FIGURE.search(text) or _ANIMAL.search(text) \
            or _NOT_FIRST_AID.search(text):
        return None
    kind = next((k for k, words in _TOPIC if words.search(text)), None)
    do = next((d for k, _w, d in KINDS if k == kind), None)
    if do is None:
        return None
    number = (where or REGIONS[DEFAULT]).emergency
    return (f"The standard first aid, from the American Red Cross and the American Heart Association: {do} When it's "
            f"real, call {number} first, or have someone else call while you help.")


def floor_kind_of(text: str) -> Optional[str]:
    """Pure logic. Which kind of emergency a reply of the floor's was about (its first steps), or None when it isn't
    one."""
    if MARK not in str(text or ""):
        return None
    return next((k for k, _w, do in KINDS if do in text), None)


def respond(prompt: str, history: list, where=None) -> Optional[str]:
    """The floor's reply for this turn, or None: None too when MIA's last words in this conversation were the floor's
    reply for the same emergency, so his next words in it go on to the model."""
    found = kinds(prompt)
    if not found:
        return None
    last = next((m for m in reversed(history or []) if getattr(m, "role", "") == "assistant"), None)
    if last is not None and floor_kind_of(getattr(last, "content", "")) in found:
        return None
    return reply(found, where)
