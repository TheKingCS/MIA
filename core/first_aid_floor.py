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

**The home's own** (2026-11-25): a fire, a gas leak and carbon monoxide are kinds too, first in `KINDS`: get out,
then call from outside (`HOME`), and an animal named is never a reason to stay quiet about them ("the barn is on
fire and the horses are inside").

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

**Missing one is worse than a false alarm** (the ninth review, 2026-11-25): narrowing these words to quiet a false
alarm ("mom passed out the cookies") had silenced real ones ("grandma fell off the horse and isn't breathing", "dad
has collapsed", "he cut his finger off a minute ago help"), so the words stay wide, and a false alarm is the accepted
cost; tests/test_first_aid_floor_never_misses.py holds every real phrasing the reviews found.
A figure of speech ("drowning in work") or a past clause ("had a heart attack last year") takes out only its own
words, and the rest is checked again (`_without`, the Fable review, 2026-11-25: one everyday phrase had silenced the
emergency beside it, "he was burning brush and his clothes caught fire"); words typed or heard without their
apostrophes are read as said (`normalised`: "hes passed out", "im bleeding"); and a follow-up naming an emergency the
last reply didn't cover is answered.

**Scope, honestly:** a floor, not a medic. It catches clear words and misses some indirect ones (the tests list both);
a false positive costs one careful message with the number in it. Reviewed 2026-11-23 against a corpus of panicked
phrasings and everyday sentences (tests/test_first_aid_floor.py).
"""

from __future__ import annotations

import re
from typing import Optional

_PEOPLE = (r"wife|husband|son|daughter|dad|father|mom|mother|friend|kid|kids|baby|child|toddler|infant|brother|"
           r"sister|grandpa|grandma|grandfather|grandmother|neighbou?r|partner|boy|girl|uncle|aunt|cousin|man|woman|guy|"
           r"lady|person|worker|coworker|boss|teenager|nephew|niece")
# the person (the Fable review, 2026-11-25: "husband collapsed in the kitchen", "our son collapsed", "a man
# collapsed at the store" had been missed for want of "my")
_WHO = (r"(?:he|she|they|i|we|someone|somebody|the baby|baby|grandma|grandpa|granny|mom|mum|dad|mother|father|"
        r"(?:my|our|the|a|his|her|their) (?:\w+ ){0,2}(?:" + _PEOPLE + r")|(?:" + _PEOPLE + r"))")
_CPR_SHORT = "If they stop responding and aren't breathing normally, start CPR: push hard and fast in the center of the chest."

# Each kind: (id, the words that say it, what to do after "Call {number} now."). Most time-critical first; when several
# match, the first two are said.
KINDS: list[tuple[str, re.Pattern, str]] = [
    # the home's own emergencies, first: get out, then call (2026-11-25: "I smell gas", "my carbon monoxide alarm is
    # going off" and "there's a fire in the kitchen" had reached nothing). From the US Fire Administration's and the
    # NFPA's home fire guidance, gas utilities' leak steps and the CDC's on carbon monoxide.
    # wide on purpose (the Fable review of the home kinds: "the toaster is on fire", "i smell smoke", "help fire" had
    # been missed): anything on fire, smoke seen or smelled, a fire named; "I'm on fire today" is the accepted false alarm
    ("fire", re.compile(r"\bon fire\b|\bin flames\b|\bcaught fire\b|\bcatching fire\b|\bburning (?:down|up)\b|"
                        r"\b(?:barn|house|shed|garage|kitchen|shop|trailer|coop)s?\s+(?:is |'s )?burning\b|"
                        r"^\s*(?:help\W*)?fire\b|\b(?:house|garage|kitchen|barn|shop|brush|grass|chimney|grease|"
                        r"electrical|car|truck|wood ?stove|attic|basement|field|wild) ?fire\b|\bfire in (?:the |my |our )?\w+|"
                        r"\b(?:we|i) (?:have|got) a fire\b|\bthere'?s (?:a )?fire\b|\bthe fire is (?:spreading|growing|"
                        r"getting bigger|out of control|in the)\b|\bcan'?t (?:put|get) (?:the |it )?(?:fire )?out\b|"
                        r"\b(?:smell|smells|see|seeing) (?:smoke|flames|something burning)\b|\b(?:full of|filling (?:up )?"
                        r"with) smoke\b|\bsmoke (?:is )?(?:coming|pouring|rising) (?:out|from|through)\b|\bsmoke alarms?\b"
                        r".{0,25}\b(?:going off|went off|beeping|won'?t stop|screaming|sounding)\b|\bsomething(?:'s| is)? "
                        r"burning\b|\bflames? (?:coming|shooting) (?:out|from)\b|\bsparks? (?:and|with) smoke\b"),
     "Get everyone out and stay out; don't stop for things. Crawl low under smoke, and feel a door with the back of "
     "your hand before you open it: if it's hot, use another way out. Close doors behind you, meet outside, and never "
     "go back in. A grease fire on the stove, only if it's small and you can: slide a lid over it and turn off the "
     "heat; never water."),
    ("gas", re.compile(r"\b(?:smell|smells|smelling|smelled|reeks?|reeking|stinks?|odor|odour)\b.{0,15}\b(?:gas|propane|"
                       r"natural gas|rotten eggs?)\b(?!\s+(?:station|prices?|mileage|tank fill))|\b(?:gas|propane)\s+"
                       r"(?:smell|odou?r|leak\w*|is leaking|leaking)\b|\bleaking (?:gas|propane)\b|\bhissing (?:from|at|by) "
                       r"the (?:gas|propane)\b|\b(?:hit|cut|broke|nicked|damaged) (?:a |the |our )?gas line\b|\bgas line "
                       r"(?:is )?(?:broken|broke|cut|hit|damaged|leaking)\b|\bleft the gas on\b|\bgas (?:is )?in the "
                       r"(?:house|kitchen|basement|room)\b|\brotten egg (?:smell|odou?r)\b|\b(?:propane|gas) tank\b.{0,15}"
                       r"\b(?:leak\w*|hissing)\b"),
     "Leave now, everyone and the pets, and leave the door open behind you. Don't switch any light or appliance on or "
     "off, don't light anything, and don't use a phone until you're well away outside. Call from outside, and the gas "
     "or propane company's emergency line too. Don't go back in until they say it's safe."),
    ("co", re.compile(r"\b(?:carbon monoxide|monoxide|co2?)\s+(?:alarm|detector|monitor|sensor|meter)s?\b|"
                      r"\bcarbon monoxide\b|\b(?:generator|grill|engine|car|truck|heater) (?:is |was )?(?:running|on) in "
                      r"the (?:garage|house|basement|shop|tent|camper)\b|\b\d+ ?ppm\b"),
     "Get everyone, the pets too, out into fresh air now, and leave the door open. Call from outside. Anyone with a "
     "headache, dizziness, sleepiness, nausea or confusion needs care now: tell the operator. Don't go back in until "
     "the fire department says it's clear."),
    ("choking", re.compile(r"\bchok(?:ing|es|ed)\b|"
                           r"\b(?:something|food|a \w+|it) (?:is )?(?:stuck|caught|lodged) in (?:his|her|their|my|the "
                           r"baby'?s) throat\b|\bheimlich\b"),
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
    ("drowning", re.compile(r"\bdrown(?:ing|ed)?\b|\bwent under\b.{0,25}\b(?:isn'?t|not|hasn'?t|didn'?t) "
                            r"(?:coming|come|came) (?:back )?up\b|\b(?:pulled|got) (?:him|her|them|my \w+) out of the (?:water|pond|"
                            r"pool|lake|river|creek)\b|\bfell (?:in|into) the (?:pond|pool|lake|river|creek|water)\b"),
     "Get them out of the water without going in yourself if you can: reach with a pole or throw something that "
     "floats. If they aren't breathing normally, start CPR; drowning is a lack of air, so give rescue breaths too if "
     "you know how. Keep them warm."),
    ("shock", re.compile(r"\belectrocut\w*|\b(?:got|been|was|is) (?:shocked|zapped)\b|\belectric(?:al)? shock\b|"
                         r"\btouched (?:a|the) (?:live|power) (?:wire|line)\b|\bpower lines?\b.{0,25}\b(?:down|touch\w*|"
                         r"hit|broke|broken|fell|fallen|snapped|on the ground|sparking|arcing|in (?:my|the|our) (?:yard|"
                         r"driveway|road|field))\b|\bdowned (?:power )?lines?\b|\blive wires?\b.{0,20}\b(?:down|on the "
                         r"ground|sparking)\b"),
     "Don't touch them until the power is off: switch it off at the breaker or unplug it, or push the source away with "
     "something dry that isn't metal (a wooden broom handle). Stay well back from a downed power line. Once it's off, "
     "if they aren't breathing normally, start CPR; cover any burns loosely."),
    ("cpr", re.compile(r"\b(?:not|isn'?t|aren'?t|ain'?t|stopped|no longer|quit) breathing\b|"
                       r"\b(?:isn'?t|aren'?t) (?:he|she|they|the baby|baby|it) breathing\b|\bno (?:pulse|heartbeat|heart "
                       r"beat)\b|\bcan'?t (?:find|feel) (?:a|his|her|their) (?:pulse|heartbeat)\b|"
                       r"\b(?:his|her|their|baby'?s|the baby'?s) heart (?:has )?stopped\b|\bcardiac arrest\b|"
                       r"\b(?:lips|face|he|she|baby|they|(?:my|the|our|his|her) (?:" + _PEOPLE + r"))(?:'s|'re| is| are)? "
                       r"(?:turning|turned|going) blue\b|\b(?:baby|he|she|lips|face)(?:'s| is| are) (?:blue|purple)\b"),
     "If they don't respond and aren't breathing normally, start CPR: kneel beside them, heel of one hand in the "
     "center of the chest, the other on top; push hard and fast, about 2 inches deep, 100 to 120 times a minute, "
     "letting the chest come back up each time. A baby: about 1.5 inches deep, with two thumbs or the heel of one "
     "hand. Keep going until help takes over. If there's an AED, turn it on and do what it says."),
    ("breathing", re.compile(r"\b(?:can'?t|cannot|can not|struggling to|having trouble) breath(?:e|ing)?\b"
                             r"(?! through (?:my|his|her|their) nose)|"
                             r"\basthma attack\b|\bgasping\b"),
     "Sit them upright, leaning a little forward, and keep them calm. If they have a rescue inhaler, help them use it "
     "as it's prescribed. Loosen anything tight. If their lips go blue or they can't speak, tell the operator."),
    ("bleeding", re.compile(r"\b(?:won'?t|will not|can'?t|doesn'?t|isn'?t|not) stop(?:ping)? bleeding\b|"
                            r"\bbleeding (?:really |so |very )?(?:a lot|badly|bad|heavily|everywhere|out|hard)\b|"
                            r"\b(?:he|she|they|i|baby|it)(?:'s| is| am| are|'m|'re)? (?:still )?bleeding\b"
                            r"(?! (?:the|my|our|his|her|a) (?:brakes?|radiators?|lines?|air|pipes?|system|hydraulics))|"
                            r"\bblood (?:is )?(?:spurting|pouring|everywhere|gushing)\b|"
                            r"\bbleeding (?:won'?t|will not|doesn'?t|isn'?t|is not) stop\w*\b|"
                            r"\b(?:gushing|spurting|pouring) blood\b|"
                            r"\bcut (?:my|his|her|their|the baby'?s|a) (?:\w+ )?(?:finger|thumb|toe|hand|arm|leg|foot)s? "
                            r"(?:off|clean off)\b|"
                            r"\b(?:severe|heavy|serious|bad) bleeding\b|\bdeep (?:cut|gash|wound)\b|"
                            r"\b(?:so much|a lot of|lots of) blood\b|\bcut (?:his|her|my|their) \w+ open\b|"
                            r"\b(?:chainsaw|saw|axe|knife|machete|blade)\b.{0,30}\b(?:cut|sliced|went into|got)\b.{0,20}"
                            r"\b(?:leg|arm|hand|foot|neck|thigh)\b|"
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
    ("heart", re.compile(r"\bchest (?:pain|pains|hurts|pressure|tightness)\b|\bchest (?:is |feels )?(?:tight|heavy|"
                         r"crushing)\b|\bpain in (?:my|his|her|their) chest\b|"
                         r"\bcrushing (?:pain|feeling)\b.{0,20}\bchest\b|\b(?:having|has|is having) a heart attack\b|"
                         r"\bheart attack\b|\bpain (?:down|in) (?:his|her|their|my) (?:left )?arm\b"),
     "Have them stop and sit down, resting; loosen anything tight. Tell the operator about any medicines they take: "
     "they may tell you to have them chew an aspirin. If they stop responding and aren't breathing normally, start "
     "CPR."),
    ("unconscious", re.compile(_WHO + r"\b(?:'s|'re| is| are| has| just| was)?\s?(?:just |suddenly )?(?:collapsed|"
                               r"won'?t wake up|not waking up|not responding|unresponsive|unconscious|fainted|"
                               r"blacked out|passed out)\b|(?:\bgot|\bwas|\bbeen|\bis|'s) knocked (?:out|unconscious)\b|"
                               r"\b(?:went|gone|is|'s) limp\b|\b" + _WHO + r"\b.{0,40}\bnot responding\b|^\s*(?:won'?t|will not|not|isn'?t) (?:wake|waking) up\b|"
                               r"\bunconscious\b(?! (?:bias|mind|thoughts?))|\bunresponsive\b|"
                               r"\b(?:is|are|isn'?t|aren'?t) (?:not )?responding\b|"
                               # anywhere in the sentence (the Fable review: "he fell and won't wake up", "touched the
                               # fence and collapsed", "fell off the ladder and isn't moving")
                               r"\b" + _WHO + r"\b.{0,40}\b(?:won'?t|will not|isn'?t|is not|not|can'?t get (?:him|her|"
                               r"them) to) (?:wake|waking) up\b|\b(?:and|then|just|suddenly|has|had) (?:\w+ )?(?:collapsed|fainted|blacked out|"
                               r"passed out|went limp)\b|\bfell\b.{0,40}\b(?:isn'?t|is not|not|won'?t|stopped) "
                               r"(?:moving|waking|answering|talking)\b"),
     "Check if they're breathing. If they are, roll them onto their side, top knee bent, head tilted back so the "
     "airway stays open, and watch the breathing. If they fell or may have hurt the neck or back, don't move them "
     "unless you must to keep the airway open or get them out of danger. If they aren't breathing normally, start "
     "CPR."),
    ("seizure", re.compile(r"\bseizures?\b|\b(?:he|she|they|baby|grandpa|grandma|mom|dad|(?:my|the|our|his|her) \w+)"
                           r"(?:'s| is| are|'re) seizing\b|\bconvuls\w*|\b(?:having|has) a fit\b|\bshaking (?:all over|and "
                           r"won'?t stop)\b"),
     "Don't hold them down and don't put anything in their mouth. Move hard things away, cushion the head, and time "
     "it. When the shaking stops, roll them onto their side and stay with them. Tell the operator if it lasts more "
     "than 5 minutes or happened in water."),
    ("poison", re.compile(r"\boverdos\w*|\bpoisoned\b|\btook too many\b|\btook (?:all|a whole bottle|the whole bottle|"
                          r"a bunch) (?:of )?(?:her|his|my|their|the)?\s*(?:\w+\s+)?(?:pills|tablets|meds|medicine|"
                          r"tylenol|advil|aspirin)\b|\b(?:tide|laundry|dishwasher|detergent) pods?\b|"
                          r"\bswallowed\b.{0,30}\b(?:pills?|tablets?|"
                          r"bleach|poison|chemicals?|antifreeze|batter(?:y|ies)|medicine|cleaner|lye|gas(?:oline)?|"
                          r"detergent|pods?|rat poison)\b|\bdrank\b.{0,20}\b(?:bleach|antifreeze|gas(?:oline)?|poison|"
                          r"cleaner|lye|chemicals?|weed killer|roundup|pesticide|herbicide|kerosene|paint thinner|"
                          r"windshield fluid)\b|\bate\b.{0,20}\b(?:rat poison|mushrooms? from the yard|pills)\b"),
     "Don't make them throw up. Keep whatever they took (the bottle or package) to tell the operator; a swallowed "
     "button battery needs the emergency room right away. If they stop responding, roll them onto their side; if they "
     "aren't breathing normally, start CPR."),
    ("snakebite", re.compile(r"\bsnake ?bit\w*|\bbit(?:ten)? by a\b.{0,15}\b(?:snake|rattlesnake|rattler|copperhead|"
                             r"cottonmouth|viper|adder|water moccasin)\b|\b(?:snake|rattlesnake|rattler|copperhead|cottonmouth|viper|adder|"
                             r"water moccasin)\b.{0,15}\bbit\b"),
     "Keep them still and calm, the bitten part still and at or below the heart. Take off rings, watches and tight "
     "things near the bite before it swells. Don't cut it, suck it, ice it or put a tourniquet on it."),
    ("burn", re.compile(r"\bburn(?:ed|t)\b.{0,25}\b(?:badly|bad|all over|blister\w*|skin)\b|"
                        r"\b(?:bad|badly|severe|serious|deep) burns?\b|\b(?:clothes|clothing|sleeve|shirt|pants|jeans|hair|jacket|coat|dress|hoodie)\s+(?:caught|are on|is on|on|lit) fire\b|"
                        r"\b(?:he|she|they|baby|my \w+|i)(?:'s| is| are|'re|'m| am) on fire\b|\bon fire\b.{0,15}\b(?:he|she|"
                        r"him|her)\b|\b(?:boiling|hot) (?:water|oil|grease)\b.{0,25}\b(?:on|over) (?:the baby|him|her|"
                        r"me|them|my|his|her)\b|\bscald(?:ed|ing)?\b"),
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
                    r"identify)|is it (?:true|bad|safe)|why (?:do|does|is)\b)", re.I)
# Words that say it's happening, which win over a question's opening: "what do I do, my baby is choking right now".
_HAPPENING = re.compile(r"\bright now\b|\bhelp\b|!|\b(?:he|she|they)(?:'s| is| are|'re)\b|\bi'm\b|\bi am\b|"
                        r"\bmy (?:\w+ ){0,2}(?:is|are|has|just)\b|\bjust (?:now|happened)\b|"
                        # today's, beside a past one (the Fable review: "had a heart attack last year and just
                        # collapsed", "choked last week and today he choked again")
                        r"\bjust (?:collapsed|passed out|fainted|fell|stopped|choked)\b|\b(?:now|today|tonight|again)\b",
                        re.I)
# Something from the past: "had a heart attack in 2019", "years ago".
_PAST = re.compile(r"\bin (?:19|20)\d\d\b|\b(?:years?|months?|weeks?) ago\b|\blast (?:year|month|week)\b|"
                   r"\bwhen (?:i|he|she) was (?:a )?(?:kid|young|little|child)\b", re.I)
# A figure of speech: "I'm drowning in work", "choking on all this paperwork", "almost had a heart attack".
_FIGURE = re.compile(r"\b(?:i'm|i am|we're|you're|he's|she's|they're|you are)\s+on fire\s+(?:today|tonight|lately|"
                     r"this (?:week|month|season|year)|at work|at the gym|right now with)\b|\bdrowning in\b(?!\s+(?:[\w']+\s+){0,3}(?:pool|lake|pond|river|creek|water|ocean|sea|tub|"
                     r"bath\w*|canal|tank|trough|reservoir|quarry|surf|waves?))|\bchok(?:ing|ed) on (?:all )?(?:this|that|the|my|these) (?:paperwork|work|news|"
                     r"traffic|emails?|bills?|deadlines?)\b|\b(?:almost|nearly) (?:had a (?:heart attack|stroke|cow|fit)|had|died|choked|drowned)\b|"
                     r"\bgave me a heart attack\b|\bmy heart (?:almost |nearly )?stopped when\b|\bunresponsive "
                     r"(?:app|page|website|computer|laptop|screen|server)\b|\b(?:app|page|website|site|computer|"
                     r"laptop|screen|server|program|phone|printer|mouse|keyboard|browser|tv)(?:'s| is| was| keeps| "
                     r"seems| still)+\s*(?:not responding|unresponsive)\b|"
                     # the homestead's own words (review 2026-11-23): engines, fences, plants, cooking, lines
                     r"\bchok\w*\s+(?:the\s+|my\s+)?(?:engine|carb\w*|saw|chainsaw|mower|motor|truck|tractor)\b|\bthe choke\b|"
                     r"\b(?:engine|motor|mower|pump|bearing|piston|chainsaw|saw|bolt|brake|caliper|it)s?(?:'s| is| was| "
                     r"keeps| has| had)*\s+seiz\w*(?:\s+up)?\b|\bseiz\w*\s+the\s+(?:engine|bolt|motor)\b|\b(?:shock|zap)\w*\b.{0,40}\belectric fence\b|\belectric fence\b.{0,40}\b(?:shock|zap)\w*\b|\belectric fence\b|\bfence (?:charger|energi[sz]er)\b|"
                     r"\bdrown\w*\s+(?:the\s+|my\s+)?(?:\w+\s+)?(?:seedlings?|plants?|tomato(?:es)?|garden|roots|"
                     r"crops?|lawn|beds?|starts|transplants)\b|"
                     r"\bburn\w*\s+(?:the\s+|my\s+)?(?:rice|toast|food|dinner|pan|pot|beans|bread|cookies|meat|steak|"
                     r"sauce|brush|pile|trash|wood|leaves)\b|"
                     # bleeding a line is the verb with its object, never a sentence with brakes in it (Fable's check:
                     # "his car's brakes failed, he's bleeding badly")
                     r"\bbleed\w*\s+(?:the\s+|my\s+|a\s+|out\s+)?(?:\w+\s+)?(?:lines?|brakes?|radiators?|hydraulics?|air|"
                     r"system)\b|\b(?:lines?|brakes?|radiators?)\s+(?:need|needs|needed)\s+(?:to be\s+)?(?:bled|bleeding)\b|"
                     r"\b(?:throttle|mower|engine|tractor|truck|pump|controller|sensor|remote|valve)"
                     r"(?:'s| is| was| keeps| seems| still)+\s*(?:unresponsive|not responding)\b|\boverdos\w*\s+(?:the\s+|my\s+)?(?:tomatoes|plants?|"
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
def _without(pattern: re.Pattern, text: str) -> str:
    """Pure logic. The words with `pattern`'s own spans taken out, so what's left is checked again: an everyday
    phrase never silences an emergency said beside it (the Fable review, 2026-11-25: "he was burning brush and his
    clothes caught fire", "she almost drowned and now she isn't breathing" had gone quiet)."""
    return pattern.sub(" ", text)


# An animal and no person: the vet's work, not these words ("my dog is choking", "the hens are gasping").
_ANIMAL = re.compile(r"\b(?:dog|dogs|puppy|cat|cats|kitten|chickens?|hens?|rooster|horse|goat|cow|calf|pig|sheep|"
                     r"lamb|duck|rabbit|bird|birds|chicks?)\b", re.I)
_PERSON = re.compile(_WHO + r"\b|\b(?:me|him|her|them|us|i'm|i've|i)\b", re.I)
# The floor's own reply, found again in the conversation (`floor_kind_of`).
MARK = "or have someone else call while you help."


_SPOKEN = {"hes": "he's", "shes": "she's", "theyre": "they're", "im": "i'm", "wont": "won't", "isnt": "isn't",
           "cant": "can't", "doesnt": "doesn't", "arent": "aren't", "didnt": "didn't", "wasnt": "wasn't",
           "hasnt": "hasn't", "aint": "ain't", "thats": "that's", "whats": "what's", "dont": "don't"}


def normalised(prompt: str) -> str:
    """Pure logic. The words lowercased, curly apostrophes straight, spaces single, and contractions typed or
    transcribed without the apostrophe restored ("hes passed out", "im bleeding", "wont wake up": the Fable review)."""
    text = " ".join(str(prompt or "").lower().replace("’", "'").replace("‘", "'").split())
    return re.sub(r"\b[a-z]+\b", lambda m: _SPOKEN.get(m.group(0), m.group(0)), text)


def kinds(prompt: str) -> list[str]:
    """Pure logic. Every kind of emergency these words say is happening now, most time-critical first ([] for none).
    A drill asked for (core/drills.requested) isn't one, unless the words also say it's happening or real, or an
    emergency is left once the drill's own words are out (`_left_after_drill`); a bare "practice" or "drill" never
    turns the floor off.
    A figure of speech or a past clause takes out only its own words, and the rest is checked again (the Fable
    review, 2026-11-25); the words are `normalised` first ("hes", "im", "wont").
    An animal named never quiets the home's own kinds (a fire, gas, carbon monoxide).
    The home's own are never quieted by a question's opening or a past clause; a person on fire gets the burn's
    steps first."""
    text = normalised(prompt)
    if not text:
        return []
    text = _without(_FIGURE, text)  # a figure of speech's own words out; what's left still counts
    found = [kind for kind, words, _do in KINDS if words.search(text)]
    if not found:
        return []
    if _ANIMAL.search(text) and not _PERSON.search(text) and not any(k in HOME for k in found):
        return []
    happening = bool(_HAPPENING.search(text))
    home = any(k in HOME for k in found)  # "why is my carbon monoxide alarm going off?" is still one (the Fable review)
    if _ABOUT.search(text) and not happening and not home:
        return []
    if _PAST.search(text) and not happening and not home:
        rest = _without(re.compile(r"[^,.;]*" + _PAST.pattern + r"[^,.;]*", re.I), text)
        found = [kind for kind, words, _do in KINDS if words.search(rest)]  # the past clause out, not the sentence
        if not found:
            return []
    if "burn" in found and "fire" in found and re.search(r"\b(?:i'm|i am|he's|she's|clothes|shirt|sleeve|hair|"
                                                        r"pants|jacket|they're)\b", text):
        found = ["burn"] + [k for k in found if k != "burn"]  # a person on fire: stop, drop and roll first
    if _practice_asked(text) and not _REAL.search(text) and not _HAPPENING.search(re.sub(r"\bhelp me\b", " ", text)) \
            and not _left_after_drill(text):
        return []  # "help me practice the choking drill" is practice; "help, he's choking" never is
    return found


def detect(prompt: str) -> Optional[str]:
    """Pure logic. The most time-critical kind of emergency these words say is happening now, or None."""
    found = kinds(prompt)
    return found[0] if found else None


HOME = ("fire", "gas", "co")  # the home's own: get out first, then call; never an animal's to the vet


def reply(kind, where=None) -> str:
    """Pure logic. The fixed words for a kind (or a list of kinds, the first two said): call the emergency number
    first (the person's country's), then what to do now, then that she's staying with him. A fire, a gas leak or
    carbon monoxide (`HOME`) says to get out first and call from outside."""
    from core.region import DEFAULT, REGIONS

    region = where or REGIONS[DEFAULT]
    wanted = [kind] if isinstance(kind, str) else list(kind)[:2]
    steps = [do for k in wanted for kk, _w, do in KINDS if kk == k]
    if wanted[0] in HOME:  # a fire, gas or carbon monoxide: out first, then the call from outside
        return (f"Get out now and call {region.emergency} from outside, {MARK} " + " ".join(steps)
                + " Tell me what's happening and I'll stay with you and help.")
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
                            r"engine|motor|mower|carb\w*)\b|\bwound up\b|\bwind(?:ing)? up\b|"
                            # (the Fable review: these had been given the tourniquet or "stop, drop and roll")
                            r"\b(?:freezer|razor|sun|wind|rug|carpet|tip|leaf) ?burn\w*|\bwounds? on (?:my |the |a |an |our )?"
                            r"(?:\w+ )?(?:trees?|bark|plants?|branch\w*|trunk)\b|\b(?:nose ?bleeds?|bleeding nose|nose (?:is )?bleeding)\b")
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
    reply for the same emergency, so his next words in it go on to the model. A kind none of its replies in this
    conversation covered ("he's unconscious and not breathing" after "dad collapsed") is answered, the new kinds
    first; a how-to's answer ("how do you use a tourniquet?") never counts as one."""
    found = kinds(prompt)
    if not found:
        return None
    # what the floor already said in this conversation, every reply of its own (Fable's check: covering only the last
    # had alternated its fixed words turn after turn and kept the model out); a how-to's answer is never one
    said = [str(getattr(m, "content", "") or "") for m in (history or []) if getattr(m, "role", "") == "assistant"]
    floor_said = [s for s in said if MARK in s and not s.startswith("The standard first aid")]
    covered = {k for k, _w, do in KINDS if any(do in s for s in floor_said)}
    new = [k for k in found if k not in covered]
    if not new:
        return None  # the same emergency, already answered: his next words go on to the model
    return reply(new, where)  # one it didn't cover ("he's not breathing now") is answered (the Fable review)
