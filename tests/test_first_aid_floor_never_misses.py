"""
tests.test_first_aid_floor_never_misses
=========================================

Every real emergency phrasing the reviews found (2026-11-25, the sixth to ninth) reaches the emergency floor
(core/first_aid_floor.detect). Narrowing its words to quiet a false alarm had twice silenced real ones ("grandma fell
off the horse and isn't breathing", "dad has collapsed", "she choked at soccer practice and can't breathe"), so a
false alarm is the accepted cost (one careful message with the number), and this list only ever grows.
"""

from core import first_aid_floor as floor

REAL = (
    # Fable's check of the home kinds' widening (2026-11-25)
    "the apartment is burning", "my bedroom is burning", "the attic is burning", "our home is burning",
    "the woods behind my house are burning", "the smoke alarm is blaring and there are flames",
    "smoke alarm going and I see fire", "the smoke alarm woke me up and there's smoke", "he's on fire tonight help",
    "flames are coming out of the oven", "there are flames in the kitchen", "a fire started in the garage",
    "the outlet is smoking", "it smells like smoke in here", "theres smoke everywhere", "my husband's sleeve is burning",
    "we dug into a gas line", "the gas pipe is broken", "gas main ruptured", "the car was left running in the garage",
    "i ran the generator inside", "using a charcoal grill inside the house", "a wire is down and sparking",
    "the electric line fell", "a power line is on my truck and I'm inside", "the power line is on him",
    "why is he not breathing?",
    # the Fable review of the home kinds (2026-11-25)
    "the toaster is on fire", "the couch is on fire", "the pan caught fire", "the outlet is on fire",
    "the roof is on fire", "the space heater caught fire", "the christmas tree is on fire",
    "the electrical panel is on fire", "the grass is on fire", "the propane tank is on fire", "fire", "help fire",
    "house fire", "garage fire", "fire in garage", "we have a fire", "kitchens on fire", "the barns burning",
    "the fire is spreading", "i cant put the fire out", "i smell smoke", "i see flames", "the house is full of smoke",
    "my house is filling with smoke", "something is burning in the walls", "the smoke alarm is going off",
    "my clothes are on fire", "im on fire", "theres a gas smell", "strong gas smell", "gas is leaking",
    "the propane tank is leaking", "the gas line is broken", "i hit a gas line", "i left the gas on",
    "the house reeks of gas", "theres gas in the house", "rotten egg smell in the house", "carbon monoxide alarm",
    "the carbon monoxide alarm wont stop", "the monoxide alarm is going off", "i think we have carbon monoxide",
    "the co detector says 200 ppm", "co2 alarm is going off", "the generator is running in the garage and i feel dizzy",
    "why is my carbon monoxide alarm going off", "why is my co detector beeping", "why does my house smell like gas",
    "why do i smell gas", "is it bad that i smell gas in the kitchen", "is it safe to stay inside if i smell gas",
    "why is smoke coming out of my outlet", "a power line is broken in my yard",
    # the home's own (2026-11-25): fire, a gas leak, carbon monoxide
    "I smell gas in the house", "it smells like rotten eggs in the kitchen", "there's a propane leak",
    "my carbon monoxide alarm is going off", "the CO detector is beeping", "there is a fire in the kitchen",
    "the house is on fire", "grease fire on the stove", "the barn is on fire and the horses are inside",
    "smoke is pouring out of the dryer", "smoke alarm going off and I see smoke in the hallway ceiling",
    # Fable's check of the fixes, 2026-11-25
    "my son is drowning in my pool", "my son is drowning in the neighbor's pool", "she's drowning in the hot tub",
    "he's drowning in the stock pond", "my son is drowning in the swimming pool",
    "his car's brakes failed, he's bleeding badly", "the power line fell on him and he's bleeding heavily",
    "the hydraulic line burst and he's bleeding", "he fell off the tractor unresponsive",
    "my husband is on the phone not responding", "the baby, it's not responding", "my dad is seizing up and shaking",
    "i'm burning the pile and my sleeve caught fire", "wont wake up", "he aint breathing", "he cant breath",
    "why isn't she breathing", "grandpa is seizing", "my son is turning blue", "the baby is blue",
    "his shirt caught fire", "baby went limp", "he's knocked out",
    # the Fable review, 2026-11-25: a figure, a past clause, a missing apostrophe or a person without "my"
    "my son is drowning in the pool", "he is drowning in the lake help",
    "he was burning brush and his clothes caught fire", "he was burning leaves and now he is on fire",
    "he fell off the mower and is unresponsive", "he rolled the tractor and is not responding",
    "dad collapsed in front of the tv and is not responding", "he took it and is now unresponsive",
    "he was bleeding the brakes and the truck fell on him he's not breathing",
    "he touched the electric fence and collapsed", "she almost drowned and now she isn't breathing",
    "he nearly choked and now he can't breathe", "hes passed out", "hes collapsed", "he's turning blue",
    "she's turning blue", "im bleeding", "how do you do cpr hes not breathing", "he fell and won't wake up",
    "grandpa fell and wont wake up", "my wife is on the floor and wont wake up", "he isnt waking up",
    "husband collapsed in the kitchen", "our son collapsed", "my toddler passed out", "the neighbor collapsed",
    "a man collapsed at the store", "dad had a heart attack last year and just collapsed",
    "my dad choked last week and today he choked again and can't breathe", "husband kicked by horse unconscious",
    "she took all her pills", "she took a whole bottle of tylenol", "my kid ate a tide pod",
    "he drank some weed killer", "there's so much blood", "he cut his leg open with the chainsaw",
    "she's got food stuck in her throat", "my chest is tight and my arm hurts", "no heartbeat",
    "she went under and isn't coming up", "boiling water spilled on the baby", "he fell off the ladder and isn't moving",
    # at practice, with a drill (the sixth review)
    "she choked at soccer practice and can't breathe", "he collapsed at football practice and isn't breathing",
    "kid not breathing at swim practice", "coach collapsed at practice not breathing call 911",
    "my son got stung at baseball practice and his throat is swelling", "someone collapsed during the fire drill, no pulse",
    "I cut my hand with the drill and it won't stop bleeding", "my husband got hurt with the power drill, blood everywhere",
    # right after asking for a drill (the seventh)
    "give me a choking drill, baby can't breathe", "quiz me on first aid, my son fell and is unconscious",
    "start the first aid drill, someone's unconscious", "try a choking scenario, my kid can't breathe",
    # family words, every way they're said (the seventh and ninth)
    "grandma collapsed", "mom collapsed", "dad has collapsed", "DAD HAS COLLAPSED", "mom's collapsed", "mom's passed out",
    "mom's not waking up", "grandma's fainted", "dad collapsed help", "mom collapsed please help",
    "mom collapsed what do i do", "dad collapsed 911", "grandpa collapsed outside", "mom blacked out driving",
    "grandmother collapsed", "grandfather passed out", "my stepdad collapsed", "my stepmom passed out",
    # on the homestead, an animal named beside the person (the ninth)
    "grandma fell off the horse and isn't breathing", "mom got bit by a snake while feeding the chickens",
    "dad got kicked by the horse and is bleeding badly", "mom collapsed while feeding the chickens",
    # bleeding, every way it's said (the seventh and ninth)
    "bleeding won't stop", "cut my finger off", "my arm is gushing blood", "she cut her finger off a minute ago help",
    "he cut his finger off my god", "dad cut his thumb off the saw", "he cut his hand off of the bandsaw",
    "she's pouring blood in the scene of the accident",
    "we were watching a movie and he started gushing blood from his nose",
)


def test_every_real_emergency_the_reviews_found_reaches_the_floor():
    missed = [words for words in REAL if floor.detect(words) is None]
    assert missed == []


def test_a_drill_asked_for_alone_stays_practice():
    for words in ("give me a choking drill", "quiz me on first aid", "try a choking scenario", "run the deep cut drill"):
        assert floor.detect(words) is None, words
