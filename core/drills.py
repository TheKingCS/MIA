"""
core.drills
=============

Scenario drills: the simulator for a course without a board (docs/future/INTERACTIVE_LABS_PLAN.md, step 4; Zac,
2026-11-25: the ESP32 labs "could be used as a standard for other teaching areas", and what he liked most was trying
it in a simulator first). A drill puts him in a situation and asks a few decisions in order; each choice is judged
best, fine or wrong, with why, written from the course's own sources (a survival drill from core/bushcraft.py's:
US Army ATP 3-50.21, the BSA Fieldbook, the CDC and the EPA, and for a power outage the CDC on generators and
carbon monoxide and the USDA on food in a fridge and freezer without power; the flock from land-grant extension
backyard poultry guides; first aid (a deep cut, choking) from the American Red Cross and the American Heart
Association, in the same words as the emergency floor (core/first_aid_floor.py), so a drill never teaches what the
floor wouldn't say, and with no medicine doses; money from core/money_path.py's (the CFPB's guides on emergency savings and debt); a market day from
core/business_path.py's (the SBA's guides); canning from core/gardening_path.py's, the USDA Complete
Guide to Home Canning and the NCHFP; a saw cut and a cut list from core/carpentry.py's lessons, OSHA Subpart I
among them; a first jam from core/guitar.py's own lessons). Pure
logic; nothing kept.

- **The drills** (`DRILLS`, `of_program`, `find`): each a `Drill` of `Question`s, each with its `Choice`s.
- **Judging** (`judge`): a choice's verdict, why, and the best choice when it wasn't.
- **By voice** (`reply`, taken in code before the question plans, core/assistant_turn.py): "give me a survival
  drill" starts one; "B", "I think C" or "the second one" answers it ("repeat" says it again, and any other short
  reply is asked for the letter: the model, given "I think C", made up a boiling rule). Where he is rides in MIA's own last message, "(Drill
  lost_at_dusk: question 2 of 4, 1 best so far. ...)", so it needs no store and stays with the conversation; "stop
  the drill" ends it. `start_drill` is the tool for it.
- **On screen** (`page_of`): the course page's Drills (web/course.js), each choice's verdict shown once picked.

A drill is rehearsal, like the ESP32 simulator: it never passes a check on his path. Only doing it does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

LETTERS = "ABCD"


@dataclass(frozen=True)
class Choice:
    """One answer to a drill's question: its words, its verdict (best, fine or wrong) and why."""
    text: str
    verdict: str
    why: str


@dataclass(frozen=True)
class Question:
    """One decision in a drill: what's asked and the choices."""
    ask: str
    choices: tuple


@dataclass(frozen=True)
class Drill:
    """A scenario: its id, the course it practises, its title, the situation, the decisions in order, and the lesson
    to read again."""
    id: str
    program: str
    title: str
    situation: str
    questions: tuple
    lesson: str = ""


def _q(ask: str, *choices) -> Question:
    """A question from (text, verdict, why) triples."""
    return Question(ask, tuple(Choice(*c) for c in choices))


DRILLS: tuple = (
    Drill("lost_at_dusk", "bushcraft", "Lost at dusk",
          "A day hike in late fall. You've lost the trail, it's an hour before dark, about 40 °F (4 °C) with a "
          "drizzle, and you have your Ten Essentials. Your partner at home knows your route and when you're due back.",
          (
              _q("What's your first move?",
                 ("Hurry on to find the trail before dark", "wrong",
                  "A rushed move is how most bad outcomes start: you go further from where they'll look, tired and "
                  "in the dark."),
                 ("STOP: stop, think, observe, then plan", "best",
                  "Sitting down and thinking turns panic into a plan; nothing about the next ten minutes needs speed."),
                 ("Shout and head toward any sound you hear", "wrong",
                  "Sound carries strangely in the woods; chasing it is moving without a plan.")),
              _q("Dark is coming. What do you work on first?",
                 ("Food, while there's light to forage", "wrong",
                  "You can go about three weeks without food; it's last on the list."),
                 ("Water: find a stream before dark", "fine",
                  "Water matters within days, and you carry some; tonight, the cold and wet are the danger."),
                 ("Shelter and warmth: out of the wind and wet, off the cold ground, layers on", "best",
                  "About three hours exposed in cold rain can kill; staying dry and insulated comes first.")),
              _q("Stay where you are, or move?",
                 ("Stay put near where you are", "best",
                  "Someone knows your route and return time, so searchers will start where you were going; staying "
                  "makes you easier to find."),
                 ("Walk downhill along a stream through the night", "wrong",
                  "Moving at night in the wet risks a fall or injury, and takes you away from the search."),
                 ("Climb to a ridge in the dark for a phone signal", "wrong",
                  "Climbing in the dark risks a fall; try for a signal from where you are, and in daylight.")),
              _q("How do you signal?",
                 ("Three blasts on your whistle, repeated", "best",
                  "Three of anything is the distress signal, and a whistle carries further than a voice for a "
                  "fraction of the effort."),
                 ("Shout for help every few minutes", "fine",
                  "It helps, but your voice tires fast and doesn't carry far; the whistle does more with less."),
                 ("Stay quiet and save your strength until morning", "wrong",
                  "Searchers may pass close in the night; signal while you can be heard.")),
          ), "priorities"),
    Drill("water_day_two", "bushcraft", "Water on day two",
          "You're waiting out a storm at a remote camp. Your water ran out this morning. There's a stream nearby, "
          "running clear after the rain, and you have a pot, a stove and unscented household bleach.",
          (
              _q("The stream looks clean. Do you drink it as it is?",
                 ("Yes: clear, running water is safe", "wrong",
                  "Clear isn't safe: the germs that make you sick can't be seen, and rain washes more of them in."),
                 ("No: treat it first", "best",
                  "Every source in the wild gets treated, however clean it looks."),
                 ("Only if it's from near the source", "wrong",
                  "Upstream animals carry the same germs; treat it anyway.")),
              _q("How long do you boil it?",
                 ("A rolling boil for 1 minute (3 minutes above 6,500 ft)", "best",
                  "That's the CDC's time: enough to kill the germs, without burning extra fuel."),
                 ("Until it starts to steam", "wrong",
                  "Steam comes well before a boil; it has to reach a rolling boil."),
                 ("A full 10 minutes to be safe", "fine",
                  "It works, but the CDC's minute does the job; the rest is fuel you may need later.")),
              _q("After the storm the stream is muddy. What now?",
                 ("Let it settle or strain it through a cloth, then treat it", "best",
                  "Mud shields germs from boiling and bleach alike; clear it first, then treat it (for bleach, "
                  "the dose for cloudy water is twice the clear one)."),
                 ("Treat it as it is, the same way", "wrong",
                  "Cloudy water needs clearing first, and for bleach, a double dose."),
                 ("Skip it and wait for the rain to stop", "fine",
                  "If you have time it's reasonable, but settling and treating it works now.")),
          ), "water"),
    Drill("wet_fire", "bushcraft", "A fire in the wet",
          "Evening, after a day of light rain. You're cold, and you want a fire before dark. You have a ferro rod "
          "and a knife; the ground and the fallen wood are soaked.",
          (
              _q("Where do you find dry fuel?",
                 ("Dead twigs still on standing trees, the ones that snap", "best",
                  "Dead wood off the ground dries fast; if it snaps cleanly, it's dry enough to burn."),
                 ("Fallen branches from the forest floor", "wrong",
                  "Ground wood soaks up water; it smokes and smothers a small fire."),
                 ("Green branches cut from a live tree", "wrong",
                  "Green wood is full of sap and water; it won't catch from a small flame.")),
              _q("When do you strike the ferro rod?",
                 ("Once the tinder, kindling and fuel are all gathered and laid out", "best",
                  "A new flame lasts seconds: everything it needs has to be within reach before you strike."),
                 ("Right away, then gather kindling while it catches", "wrong",
                  "The tinder burns out before you're back with kindling."),
                 ("After gathering tinder only", "wrong",
                  "Tinder alone burns out in seconds; the kindling has to be ready to feed it.")),
              _q("All the wood is wet on the outside. What do you do?",
                 ("Split it open and make feather sticks from the dry centre", "best",
                  "The inside of a split stick is often dry; thin curls of it catch from a spark."),
                 ("Use bigger logs: they burn longer", "wrong",
                  "Big wet logs smother a young fire; build up from pencil-lead thin to wrist thick."),
                 ("Dry the wood by the fire first", "fine",
                  "It works once a fire is going, for the next load, not to start one.")),
          ), "fire"),
    Drill("power_out", "bushcraft", "The power's out",
          "A winter storm takes the power out in the evening; the forecast says it could be two days. You have a "
          "portable generator, a full chest freezer and a half-full fridge.",
          (
              _q("Where do you run the generator?",
                 ("In the garage with the door open", "wrong",
                  "Carbon monoxide builds up even with the door open; you can't see or smell it, and it kills. Never "
                  "in a garage, a basement or any part of the house."),
                 ("Outside, at least 20 feet from the house, its exhaust away from windows and doors", "best",
                  "That's the CDC's distance: far enough that the exhaust doesn't drift in."),
                 ("On the porch, under the roof out of the snow", "wrong",
                  "Right by the house the exhaust comes in through windows and doors; keep it 20 feet away.")),
              _q("What do you do with the fridge and freezer?",
                 ("Keep the doors shut", "best",
                  "Shut, a fridge keeps food safe about 4 hours, a full freezer about 48 and a half-full one about 24 "
                  "(the USDA's times)."),
                 ("Check inside every hour to see how they're holding", "wrong",
                  "Every opening lets the cold out; keep them shut and use a thermometer when you do look."),
                 ("Move everything into coolers right away", "fine",
                  "It works for what's in the fridge once it's been out a few hours, with ice; the freezer is better "
                  "left shut.")),
              _q("The power comes back the next afternoon. The fridge thermometer reads 50 °F. What about the milk "
                 "and leftovers?",
                 ("Smell them, and keep what seems fine", "wrong",
                  "The germs that make you sick don't always change the smell or look."),
                 ("Throw out the perishables that sat above 40 °F for more than 2 hours", "best",
                  "That's the USDA's rule: when in doubt, throw it out."),
                 ("Cook them well and eat them today", "wrong",
                  "Cooking doesn't undo every toxin some germs leave behind; above 40 °F for over 2 hours, out it "
                  "goes.")),
              _q("It's getting cold in the house tonight. How do you keep warm?",
                 ("Run the gas oven with its door open", "wrong",
                  "An oven isn't a heater: it's a fire risk and a source of carbon monoxide."),
                 ("Bring the camp stove or a charcoal grill inside", "wrong",
                  "Burning fuel indoors without a vent fills the house with carbon monoxide."),
                 ("Close off one room, layer up, and keep a working CO alarm with fresh batteries", "best",
                  "A small room holds its warmth, layers hold yours, and the alarm guards against any fuel burning "
                  "nearby.")),
          ), "priorities"),
    Drill("deep_cut", "bushcraft", "A deep cut",
          "You're working in the shop with a friend when a chisel slips and opens a deep cut on their forearm. Blood "
          "is flowing steadily, and town is 30 minutes away. (A drill: the real thing starts with the emergency "
          "number.)",
          (
              _q("What do you do first?",
                 ("Rinse it under the tap to see how deep it is", "wrong",
                  "Every minute it bleeds matters more than seeing it: pressure first, the cleaning comes later."),
                 ("Have someone call the emergency number, and press hard on the wound with a clean cloth", "best",
                  "Firm, steady pressure stops most bleeding, and help is on its way while you hold it."),
                 ("Get them in the truck and drive to town", "wrong",
                  "Driving, nobody is holding pressure for 30 minutes; call, press, and let help come to you or tell "
                  "you where to meet.")),
              _q("Blood soaks through the cloth. What now?",
                 ("Lift it off to see if it's slowing", "wrong",
                  "Lifting pulls away the clot that's starting to form; don't lift it to look."),
                 ("Swap it for a fresh, clean cloth", "wrong",
                  "Taking the first one off undoes the pressure and the clot; leave it there."),
                 ("Put more cloth on top and keep pressing hard", "best",
                  "That's the Red Cross's way: add more on top, never take the first off, and keep the pressure on.")),
              _q("It's still bleeding hard through steady pressure. It's an arm. What do you do?",
                 ("A tourniquet 2 to 3 inches above the wound, tight until the bleeding stops, and note the time",
                  "best",
                  "Above the wound, between it and the heart, and tight enough to stop it; the time tells the medics "
                  "how long it's been on."),
                 ("A tourniquet right over the cut", "wrong",
                  "On the wound it can't close off the vessel feeding it: 2 to 3 inches above."),
                 ("Tie it loosely so it doesn't hurt, and loosen it every few minutes", "wrong",
                  "Loose, it can make bleeding worse; once it's on, leave it tight and leave it for the medics to "
                  "take off.")),
              _q("While you wait for help, what about them?",
                 ("Have them walk around so they stay alert", "wrong",
                  "Moving makes the heart work harder and they may faint; keep them still."),
                 ("Keep them lying down and warm, and keep watching them", "best",
                  "Blood loss can bring on shock: lying down, a blanket, and you watching their breathing until help "
                  "takes over."),
                 ("Give them a drink and a painkiller for the pain", "wrong",
                  "Nothing by mouth: they may need surgery, and medicine is for the medics to give.")),
          ), "priorities"),
    Drill("choking", "bushcraft", "Choking at dinner",
          "At dinner, a friend suddenly grabs their throat. (A drill: the real thing starts with the emergency "
          "number.)",
          (
              _q("They're coughing hard and can still say a few words. What do you do?",
                 ("Give back blows right away", "wrong",
                  "A strong cough is the best way to clear it: blows are for when they can't cough, speak or "
                  "breathe."),
                 ("Tell them to keep coughing, and stay right with them", "best",
                  "While air still moves, coughing does the work; you're there the moment it stops."),
                 ("Give them water to wash it down", "wrong",
                  "Water can't get past a blocked airway and can make it worse.")),
              _q("Now they can't cough, speak or breathe. What do you do?",
                 ("Sweep your finger in their mouth to hook it out", "wrong",
                  "A blind sweep can push it further down; only take out something you can see."),
                 ("Have someone call, then 5 firm back blows between the shoulder blades and 5 quick thrusts in and "
                  "up just above the belly button, switching until it comes out", "best",
                  "That's the Red Cross's five and five: back blows with the heel of your hand, then abdominal "
                  "thrusts, and keep going."),
                 ("Wait a minute to see if it clears on its own", "wrong",
                  "With no air moving, there's no time to wait: start now.")),
              _q("They go limp and stop responding. What now?",
                 ("Keep doing thrusts while holding them up", "wrong",
                  "Once they stop responding, get them down and onto CPR."),
                 ("Lower them to the floor, make sure help is called, and start CPR, taking out the object only if "
                  "you can see it", "best",
                  "Chest compressions can push it out; look in the mouth before breaths, never a blind sweep."),
                 ("Lay them on their side and wait for help", "wrong",
                  "Not breathing, they need CPR now, not waiting.")),
              _q("It comes out, and they say they feel fine. Anything else?",
                 ("No, they're fine now", "wrong",
                  "Abdominal thrusts can hurt inside, and a bit can stay behind: they should be checked."),
                 ("Have a doctor check them, even if they feel fine", "best",
                  "The Red Cross says to get medical care after thrusts were needed."),
                 ("Give them something to eat to settle their throat", "wrong",
                  "Let them be checked first; a sore or swollen throat can make swallowing harder.")),
          ), "priorities"),
    Drill("canning_day", "gardening", "Putting up green beans",
          "A Saturday with a bushel of green beans from the garden. You have a boiling-water canner, a pressure "
          "canner, new lids, and your grandmother's recipe card.",
          (
              _q("Which recipe do you follow?",
                 ("Grandma's card: it's been made for years", "wrong",
                  "Only tested recipes are safe to can from; years without trouble isn't a test, and the risk is "
                  "botulism."),
                 ("A tested one: the USDA guide, the National Center for Home Food Preservation or a Ball book", "best",
                  "A tested recipe's times and pressures were measured in the jar; that's what makes it safe."),
                 ("A popular one online with good reviews", "wrong",
                  "Reviews say it tastes good, not that it was tested; can only from a tested recipe.")),
              _q("Which canner do the green beans go in?",
                 ("The pressure canner, at the pressure and time for your altitude", "best",
                  "Green beans are low-acid: only a pressure canner reaches the 240 °F that makes them safe; "
                  "boiling water stops at 212 °F."),
                 ("The boiling-water canner, just for longer", "wrong",
                  "Boiling water never gets past 212 °F, however long it runs, and low-acid food needs 240 °F, "
                  "which only a pressure canner reaches."),
                 ("Either, as long as the lids seal", "wrong",
                  "A sealed jar of low-acid food canned wrong can still carry botulism; the seal doesn't make it "
                  "safe.")),
              _q("The next day, one lid flexes up and down when you press it. What now?",
                 ("It's fine: put it on the shelf with the rest", "wrong",
                  "An unsealed jar isn't shelf-stable; it spoils."),
                 ("Put it in the fridge and eat it soon, or reprocess it within 24 hours", "best",
                  "That's what the USDA says to do with a jar that didn't seal."),
                 ("Throw it out", "fine",
                  "Safe, but the food is good: refrigerate it or reprocess it within the day.")),
              _q("Months later a jar's lid is bulging, and it spurts when you open it. What do you do?",
                 ("Taste a little to see if it's off", "wrong",
                  "Never taste it: botulism can't be seen, smelled or tasted, and a little can kill."),
                 ("Don't taste it: get rid of it carefully, as the USDA describes", "best",
                  "A bulging lid is a sign of spoilage, and maybe botulism; the jar and its food are handled with "
                  "care, never eaten."),
                 ("Boil it hard for a while and then eat it", "wrong",
                  "Food from a bulging jar is never eaten, boiled or not.")),
          ), "canning_safe"),
    Drill("flock_night", "gardening", "A night at the coop",
          "Late fall. Your hens are laying, the nights are dropping below freezing, and last week a neighbour lost "
          "birds to a raccoon.",
          (
              _q("It's getting dark. What do you do?",
                 ("Shut the coop door once they're all in", "best",
                  "Most losses to predators happen at night; a closed, solid coop is the first defence."),
                 ("Leave the door open so they can go out at first light", "wrong",
                  "An open door at night is how a raccoon gets in."),
                 ("Leave a light on to scare things off", "wrong",
                  "Predators learn a light quickly; only a shut, solid coop keeps them out.")),
              _q("You're closing up gaps around the run. What do you use?",
                 ("Chicken wire: it's what it's for", "wrong",
                  "Chicken wire keeps chickens in, but raccoons and dogs tear it or reach through it."),
                 ("Hardware cloth, buried or skirted at the base", "best",
                  "Small, welded mesh stops reaching paws, and the buried edge stops digging."),
                 ("Netting over the top only", "fine",
                  "It stops hawks, but not anything on the ground; the sides and base need hardware cloth.")),
              _q("A hard freeze is coming. How do you keep them comfortable?",
                 ("A heat lamp over the roost", "wrong",
                  "Heat lamps start coop fires, and birds used to them suffer if the power fails."),
                 ("Ventilation high up, no drafts at roost level, and dry bedding", "best",
                  "Damp air makes frostbite far more likely in the cold; venting the moisture keeps them dry and "
                  "their feathers do "
                  "the rest."),
                 ("Seal every vent to keep the warmth in", "wrong",
                  "Sealed, the coop fills with moisture and ammonia: worse frostbite and sick birds.")),
              _q("In the morning one hen is hunched, fluffed up and won't eat. What now?",
                 ("Leave her with the flock: she'll perk up", "wrong",
                  "If it's catching, the rest of the flock gets it."),
                 ("Separate her somewhere warm and quiet, with water, and watch her", "best",
                  "Separated, she can't spread anything and you can see if she eats and drinks; if she doesn't pick "
                  "up, a vet who treats poultry."),
                 ("Give her some of your own antibiotics", "wrong",
                  "Never: the wrong drug and dose, and some aren't allowed at all in birds whose eggs you eat.")),
          ), "flock_care"),
    Drill("surprise_bill", "money", "A surprise bill",
          "The truck needs a repair that costs about two weeks of your take-home pay. You have a small cushion saved, "
          "a credit card, and rent from the rentals coming in at the month's end.",
          (
              _q("How do you pay for the repair?",
                 ("Put it on the credit card and pay the minimum each month", "wrong",
                  "Paying only the minimum, a card's interest makes the repair cost far more and for far longer."),
                 ("Use the cushion, then rebuild it", "best",
                  "That's what the cushion is for: no interest, and the plan for next month refills it."),
                 ("A payday loan until the rent comes in", "wrong",
                  "A payday loan's fees work out to a very high rate, and they're easy to roll over into more.")),
              _q("Next month, what comes first?",
                 ("Refill the cushion, from the month's plan", "best",
                  "The next surprise is coming too; a refilled cushion keeps it off a card."),
                 ("Stop saving for a while: you've earned a break", "wrong",
                  "With the cushion low, the next surprise lands on a card."),
                 ("Raise the cushion's target if repairs keep coming", "fine",
                  "Reasonable once it's refilled; first get it back where it was.")),
              _q("A slow month: the rentals bring in a third less. What first?",
                 ("Skip the mortgage payment and catch up later", "wrong",
                  "A missed payment brings late fees and a mark on your credit; it's the last thing to let go."),
                 ("Cut the wants in this month's plan, cover the essentials and the bills, and use the cushion for any "
                  "gap", "best",
                  "Essentials and on-time payments first; the cushion bridges the rest, and gets refilled when it "
                  "picks up."),
                 ("Take money out of a retirement account", "wrong",
                  "In many places that costs taxes and penalties, and the growth it would have had is gone.")),
              _q("Then a tax refund arrives. Where does it go first?",
                 ("Top up the cushion if it's low, then the highest-rate debt", "best",
                  "A full cushion, then the debt that costs the most: the most good per unit of money."),
                 ("Some to something you'll enjoy, the rest to the plan", "fine",
                  "Fair, as long as most of it goes to the cushion and the dearest debt."),
                 ("The lowest-rate debt first", "wrong",
                  "The highest rate costs you the most every month, so start there (or with the smallest balance, if "
                  "you're working the snowball on purpose); the lowest rate is last.")),
          ), "money_cushion"),
    Drill("market_day", "business", "Market day",
          "A Saturday at the farmers' market with your goods. You've worked out each one's full cost, your time "
          "included, and you have a cash box and a card reader.",
          (
              _q("A customer says the stall across the way sells the same for less. What do you do?",
                 ("Drop your price below your cost to make the sale", "wrong",
                  "A sale under your cost loses money every time; busy isn't the same as earning."),
                 ("Keep your price, and say what makes yours worth it", "best",
                  "Your price covers your cost, your time and a margin; tell them why yours is the one to buy."),
                 ("Knock a little off, staying above your cost", "fine",
                  "It can make the sale, but haggle every time and the floor becomes your ceiling.")),
              _q("Before the market opens, what about the cash box?",
                 ("Count the starting change and write it down", "best",
                  "With the starting amount noted, the day's cash sales are the difference at the end."),
                 ("Just bring whatever's in it", "wrong",
                  "Without knowing what you started with, you can't tell what you sold or if anything's missing."),
                 ("Leave it at home and take cards only", "fine",
                  "Simpler, but you'll lose the customers who carry cash.")),
              _q("A customer brings back something that broke after a week. What now?",
                 ("Follow your stated policy and the law where you sell, and make it right quickly and kindly", "best",
                  "A stated policy, applied quickly, keeps a customer who'll come back and tell others; where the law "
                  "gives a buyer more for a faulty item, the law comes first."),
                 ("Argue it was their fault", "wrong",
                  "Even if it was, arguing in front of the stall costs you more than the item."),
                 ("Refund anyone anything, no questions", "fine",
                  "Generous, but without a policy it's hard to keep fair or affordable.")),
              _q("At the end of the day, what do you do with the takings?",
                 ("Record every sale and expense today, and put the money in the business account", "best",
                  "Recorded today and kept apart, the numbers show what's really earning, and tax time is adding up."),
                 ("Use the cash for the week's groceries", "wrong",
                  "Mixed with the household money, the business's numbers stop meaning anything."),
                 ("Note the total and sort the details out at the end of the year", "wrong",
                  "Records rebuilt from memory miss things; the day it happens is when it's easy.")),
          ), "biz_price"),
    Drill("first_jam", "guitar", "A first jam",
          "A friend hands you a guitar at a campfire and asks for the four-chord song: G, E minor, C, D. (From the "
          "Guitar course's own lessons.)",
          (
              _q("You tune up first. Which way do the strings go, thickest to thinnest?",
                 ("E B G D A E", "wrong", "That's thinnest to thickest: the high E is string 1."),
                 ("E A D G B E (\"Eddie Ate Dynamite, Good Bye Eddie\")", "best",
                  "The low E is string 6, the high E string 1; and tune up to each note, not down to it: it holds."),
                 ("A D G B E A", "wrong", "A guitar's lowest and highest strings are both E.")),
              _q("You're on E minor and the next chord is A minor. What do your fingers do?",
                 ("Lift everything and build A minor from scratch", "fine",
                  "It works, but slowly: the two chords share a shape."),
                 ("The same two fingers move down one string each, and your first finger goes on the B string's 1st "
                  "fret", "best", "That's the lesson's shortcut: one move, and the change comes back in dozens of "
                                  "songs."),
                 ("Slide the whole shape up a fret", "wrong", "That's a different chord entirely; A minor moves down a "
                                                          "string, not up a fret.")),
              _q("You're late getting to C. What do you do?",
                 ("Stop, find the chord, then start again", "wrong",
                  "The song stops with you; the beat goes on without your fingers."),
                 ("Slow down until your fingers are there", "wrong", "Everyone else keeps the tempo: you'd drift apart."),
                 ("Let the last strum before the change go on open strings, and land the change on beat 1", "best",
                  "Keeping the beat matters more than a clean chord: change on beat 1, every time.")),
              _q("The D chord: which strings do you strum?",
                 ("All six", "wrong", "The low E isn't in a D chord and muddies it; strum from the D string so D is "
                                      "the lowest note."),
                 ("Only the top four, from the D string down", "best", "That's how the D shape is played."),
                 ("From the A string down", "fine", "That's how C is strummed; D wants just the top four.")),
              _q("Someone calls for a power chord with your first finger on the 3rd fret of the low E. What chord is it?",
                 ("G5", "best", "The note under your first finger names it: the 3rd fret of the low E is G."),
                 ("A5", "wrong", "A5 is at the 5th fret of the low E."),
                 ("C5", "wrong", "C is the 8th fret of the low E, or the 3rd fret of the A string.")),
          ), "progression"),
    Drill("first_cut", "carpentry", "Cutting a 2x6 to length",
          "You're cutting a 2x6 to length with a circular saw, the board across two sawhorses, the cut near the "
          "middle.",
          (
              _q("How do you support the board for the cut?",
                 ("Across both sawhorses, cutting between them", "wrong",
                  "Supported at both ends, the board sags as you cut and pinches the blade: that's kickback."),
                 ("So the offcut can fall free", "best",
                  "With nothing holding the cut closed, the kerf stays open and the blade can't bind."),
                 ("Have a helper hold the offcut up", "wrong",
                  "Holding it up closes the kerf on the blade, the same as a board supported at both ends.")),
              _q("How deep do you set the blade?",
                 ("About 1/4 inch deeper than the board is thick", "best",
                  "Enough to cut through, with as little blade showing as possible."),
                 ("As deep as it goes", "wrong",
                  "More blade showing is more to catch, and a worse angle on the wood."),
                 ("Exactly the board's thickness", "wrong",
                  "It won't cut all the way through, and you'll be tempted to force it.")),
              _q("Which side of your line do you cut on?",
                 ("The waste side", "best",
                  "The blade's width comes out of the offcut, so the piece you keep is the length you marked."),
                 ("Right on the line", "fine",
                  "Close, but half the blade's width comes off the piece you keep."),
                 ("The side you're keeping", "wrong",
                  "The whole blade's width comes off your piece: it ends up short.")),
              _q("Halfway through, the blade starts to bind. What do you do?",
                 ("Push harder to get through it", "wrong",
                  "A binding blade is how kickback starts; forcing it is the worst thing to do."),
                 ("Let go of the trigger, let the blade stop, back it out and fix the support", "best",
                  "Stopped and out of the cut, nothing can kick; then fix what pinched it."),
                 ("Lift the saw out while it's still spinning", "wrong",
                  "Lifting a spinning blade out of a cut can throw the saw; let it stop first.")),
          ), "circular_saw"),
    Drill("cut_list", "carpentry", "Shelves from a cut list",
          "A bookcase from 1x12 boards, 8 feet long: two sides at 48 in and four shelves at 34-1/2 in, your circular "
          "saw's blade about 1/8 in thick.",
          (
              _q("Which parts do you cut first?",
                 ("The shortest, to get them out of the way", "wrong",
                  "Cut short parts first and the long ones may not fit in what's left."),
                 ("The longest, so the offcuts can become the short parts", "best",
                  "Longest first, then the shorter parts come out of what's left: less waste, fewer boards."),
                 ("Whichever board is on top of the pile", "wrong",
                  "Without an order, a board ends up too short for the one long part you still need.")),
              _q("Can both 48 in sides come out of one 8 ft board?",
                 ("Yes: 48 and 48 is exactly 96", "wrong",
                  "The blade turns about 1/8 in into sawdust at every cut, and a factory end may not be square: the "
                  "second side comes up short."),
                 ("Measure the board first: with a square end and the blade's 1/8 in, two 48s need a little over 96 "
                  "in", "best",
                  "Boards are often a touch over 8 ft; measure it, square one end, and see whether both fit."),
                 ("Cut one, and see what's left", "fine",
                  "You'll find out, but measuring first tells you before you've cut, while you can still choose a "
                  "board.")),
              _q("Four shelves all at 34-1/2 in. How do you cut them alike?",
                 ("Measure each new one from the last piece you cut", "wrong",
                  "Any error in one is copied into the next, and they creep."),
                 ("Clamp a stop block at 34-1/2 in and cut each one against it", "best",
                  "Every piece is set by the same block, so all four match."),
                 ("Mark each with the tape and cut to the lines", "fine",
                  "It works with care, but four marks are four chances to be off; a stop block makes them identical.")),
              _q("You've cut the first shelf against the block. Now what?",
                 ("Cut the other three, then check them all", "wrong",
                  "If the block is off, all four are wrong before you know it."),
                 ("Measure the first one and check it before cutting the rest", "best",
                  "Measure twice, cut once: the first part proves the setup, then the rest follow it."),
                 ("Trust the block: it was set with the tape", "wrong",
                  "A block can be set from the wrong side of a mark or slip as it's clamped; one check catches it.")),
          ), "cut_list"),
)


def of_program(program_id: str) -> list:
    """The drills for a course, in order."""
    return [d for d in DRILLS if d.program == program_id]


def by_id(drill_id: str) -> Optional[Drill]:
    """A drill by its id, or None."""
    return next((d for d in DRILLS if d.id == drill_id), None)


# Words that name a drill besides its title's ("the power outage drill", "a blackout drill").
# never the bare "power" (the Fable review: "quiz me on the power rule for calculus" had started the outage drill)
ALSO = {"power_out": ("power outage", "outage", "blackout", "power out", "generator", "power cut", "no power"),
        "flock_night": ("flock", "chicken", "chickens", "hens", "coop", "poultry"),
        "surprise_bill": ("money", "finance", "budget", "surprise bill", "debt"),
        "market_day": ("market day", "market", "business", "farmers market", "pricing"),
        "canning_day": ("canning", "green beans"), "first_cut": ("circular saw", "saw"),
        "first_jam": ("guitar", "jam", "chord", "chords"),
        "cut_list": ("cut list", "cut-list", "stop block", "bookcase", "shelves"),
        "deep_cut": ("deep cut", "bad cut", "bleeding", "tourniquet", "wound"),
        "choking": ("choking", "heimlich")}


def named(words: str) -> Optional[Drill]:
    """Pure logic. The drill his words name by its own words (`ALSO`: "the power outage drill") or its title or a word
    of it ("the water drill"), or None. "Fire drill" alone is the house's kind, not this."""
    said = re.sub(r"\bfire drill\b", " ", str(words or "").lower())
    for drill in DRILLS:
        if any(re.search(rf"\b{re.escape(w)}\b", said) for w in ALSO.get(drill.id, ())):
            return drill
    for drill in DRILLS:
        title = drill.title.lower()
        if title in said or any(re.search(rf"\b{w}\b", said) for w in title.split() if len(w) > 3):
            return drill
    return None


FIRST_AID = ("deep_cut", "choking")  # "a first aid drill": one of these, by the day
FOR_KIND = {"bleeding": "deep cut", "choking": "choking"}  # an emergency floor kind's drill, said to start it
_COURSE_WORDS = {"gardening": r"\b(canning|preserving|food safety)\b",
                 "carpentry": r"\b(carpentry|circular saw|saw|woodworking)\b"}


def find(words: str, today: Optional[date] = None) -> Optional[Drill]:
    """Pure logic. The drill his words name (`named`), else one of the course his words mean (a canning drill, a
    carpentry drill, a first aid one), else a survival one; by the day among them (so asking each day brings a
    different one)."""
    drill = named(words)
    if drill is not None:
        return drill
    said = str(words or "").lower()
    if re.search(r"\bfirst[ -]aid\b", said):
        return by_id(FIRST_AID[(today or date.today()).toordinal() % len(FIRST_AID)])
    course = next((c for c, w in _COURSE_WORDS.items() if re.search(w, said)), "bushcraft")
    survival = of_program(course)
    if not survival:
        return None
    return survival[(today or date.today()).toordinal() % len(survival)]


def lesson_title(drill: Drill) -> str:
    """The title of the lesson behind a drill, from its course ("" when it names none)."""
    from core import paths

    program = paths.program_of(None, drill.program)
    found = next((lesson for stage in program.stages for lesson in stage.lessons if lesson.id == drill.lesson),
                 None) if program is not None else None
    return found.title if found else ""


def judge(drill: Drill, n: int, pick: int) -> dict:
    """Pure logic. Question n (from 1), choice pick (from 0): {verdict, why, best (the best choice's words)}.
    IndexError for one the drill hasn't."""
    question = drill.questions[n - 1]
    choice = question.choices[pick]
    best = next(c for c in question.choices if c.verdict == "best")
    return {"verdict": choice.verdict, "why": choice.why, "best": best.text}


def _asked(drill: Drill, n: int, right: int) -> str:
    """Question n said, with its choices and where he is."""
    question = drill.questions[n - 1]
    letters = LETTERS[:len(question.choices)]
    options = " ".join(f"{letters[i]}) {c.text}." for i, c in enumerate(question.choices))
    return (f"{question.ask} {options} (Drill {drill.id}: question {n} of {len(drill.questions)}, {right} best so far. "
            f"Say {', '.join(letters[:-1])} or {letters[-1]}.)")


def start(drill: Drill) -> str:
    """A drill's opening: its title, the situation and the first question."""
    return f"Drill: {drill.title}. {drill.situation}\n\n" + _asked(drill, 1, 0)


_WHERE = re.compile(r"\(Drill (\w+): question (\d+) of (\d+), (\d+) best so far\.")
# Words around a letter that still make it an answer ("I think C", "probably b, final answer"); any other word makes it
# a sentence ("a minute"), not a pick.
_FILLER = {"i", "i'd", "id", "i'll", "ill", "would", "will", "think", "guess", "say", "pick", "picking", "go", "going",
           "with", "choose", "take", "option", "answer", "letter", "choice", "maybe", "probably", "definitely",
           "hmm", "um", "uh", "ok", "okay", "then", "it's", "its", "is", "the", "let's", "lets", "please", "final",
           "my", "sure", "yeah"}
_ORDINAL = {"first": 0, "1st": 0, "one": 0, "second": 1, "2nd": 1, "two": 1, "third": 2, "3rd": 2, "three": 2,
            "fourth": 3, "4th": 3, "four": 3}
_SURVIVAL = re.compile(r"\b(survival|bushcraft|wilderness|outdoor|outdoors|woods)\b")
# A drill is started only when one is asked for, its subject right beside the word: "a canning drill", "run the water
# drill", "drill me on survival" (the review: "can I drill into the stud?", "worst case scenario for water" and "a drill
# at work today" had each started one).
_REQUEST = re.compile(r"\b(give me|run|start|do|try|let's|lets|i want|i'd like|how about|another|new|drill me|quiz me|practi[cs]e|"
                      r"test me)\b")
_SUBJECTS = sorted({"survival", "bushcraft", "wilderness", "outdoor", "canning", "preserving", "food safety",
                    "first aid", "first-aid",
                    "carpentry", "circular saw", "saw", "green beans", "dusk"}
                   | {w for d in DRILLS for w in d.title.lower().split() if len(w) > 3 and w != "fire"}
                   | {w for words in ALSO.values() for w in words}, key=len,
                   reverse=True)
_SUBJECT = "(?:" + "|".join(re.escape(s) for s in _SUBJECTS) + ")"
_ASKED_FOR = re.compile(rf"\b{_SUBJECT}\s+(?:drill|scenario)s?\b|\b(?:drill|scenario|quiz)\s+(?:me\s+)?(?:on|about|for)\s+"
                        rf"(?:the\s+|my\s+|a\s+)?{_SUBJECT}\b")
# While a drill waits, only an attempt at an answer gets "which one?" back; anything else ("lights off", "thanks") is
# his to say, and the drill ends there.
_TRYING = re.compile(r"^(?:(?:hmm+|um+|uh+|well|ok|okay|oh)\s+)*(?:[a-z]|not sure|dunno|i don't know|i dont know|"
                     r"idk|no idea|pass|skip|hmm+|um+|uh+|(?:the )?(?:fifth|last) one)$")
_NOT_THIS = re.compile(r"\b(drill bits?|drill press|power drill|cordless|hammer drill|drill (?:a|the|some|holes?)|"
                       r"drilling)\b")
_STOP = re.compile(r"^(?:stop|end|quit|cancel|skip) (?:the |this )?(?:drill|scenario|quiz)\b")


def where(conversation) -> Optional[tuple]:
    """(drill, question n, best so far) when MIA's last message was a drill's question, else None."""
    for message in reversed(list(getattr(conversation, "messages", None) or [])):
        if getattr(message, "role", "") == "assistant":
            found = _WHERE.search(str(getattr(message, "content", "") or ""))
            drill = by_id(found.group(1)) if found else None
            return (drill, int(found.group(2)), int(found.group(4))) if drill else None
    return None


def picked(words: str, choices: int) -> Optional[int]:
    """Pure logic. The choice his words pick ("B", "I'd go with b", "the second one"), or None."""
    said = re.sub(r"[^\w' ]+", " ", str(words or "").lower()).strip()
    tokens = said.split()
    letters = [t for t in tokens if t in LETTERS.lower()[:choices]]
    if len(letters) == 1 and all(t in _FILLER or t == letters[0] for t in tokens):
        return LETTERS.lower().index(letters[0])
    found = re.fullmatch(r"(?:the )?(\w+)(?: one| option| answer)?", said)
    if found and found.group(1) in _ORDINAL and _ORDINAL[found.group(1)] < choices:
        return _ORDINAL[found.group(1)]
    return None


def answer(drill: Drill, n: int, right: int, pick: int) -> str:
    """What MIA says to a choice: the verdict and why, then the next question, or at the end how it went."""
    got = judge(drill, n, pick)
    right += got["verdict"] == "best"
    opening = {"best": "Right.", "fine": "Close.", "wrong": "Not that one."}[got["verdict"]]
    said = f"{opening} {got['why']}"
    if got["verdict"] != "best":
        said += f" Best: {got['best']}."
    if n < len(drill.questions):
        return said + "\n\nNext: " + _asked(drill, n + 1, right)
    total = len(drill.questions)
    lesson = lesson_title(drill)
    close = ("Every call the best one." if right == total else
             f"{right} of {total} best. The lesson behind it is worth a read again" + (f": {lesson}." if lesson
                                                                                         else "."))
    return f"{said}\n\nThat's the drill: {close} A drill is practice; the real thing is the course's own check."


def reply(context, conversation, text: str) -> Optional[str]:
    """Drills by voice, in code, before the question plans: an answer to the question MIA just asked, "stop the drill",
    or "give me a survival drill"; None when the words aren't for a drill. A drill starts only when one is asked for,
    its subject beside the word ("a canning drill", "drill me on survival"); while one waits, only an attempt at an
    answer ("e", "not sure") is asked for the letter again, and anything else ends it.
    A money or business drill needs the word "drill": "a budget scenario" is his own planning.
    Which drill is asked for is `requested`'s."""
    said = " ".join(str(text or "").lower().replace("’", "'").split())
    live = where(conversation)
    if live is not None:
        drill, n, right = live
        if _STOP.match(said):
            return f"Drill stopped: {right} of {n - 1} best so far. Ask for another whenever you like."
        pick = picked(said, len(drill.questions[n - 1].choices))
        if pick is not None:
            return answer(drill, n, right, pick)
        if re.search(r"^(?:repeat|again|say (?:that|it) again|what were the (?:options|choices)|repeat (?:that|the "
                     r"question))\b", said):
            return _asked(drill, n, right)
        if _TRYING.match(re.sub(r"[^\w' ]+", "", said).strip()):
            letters = LETTERS[:len(drill.questions[n - 1].choices)]
            return (f"Which one: {', '.join(letters[:-1])} or {letters[-1]}? Or \"repeat\" to hear it again, or "
                    f"\"stop the drill\". (Drill {drill.id}: question {n} of {len(drill.questions)}, {right} best so "
                    f"far.)")
    drill = requested(said)
    return start(drill) if drill is not None else None


def requested(words: str) -> Optional[Drill]:
    """Pure logic. The drill his words ask for, or None: asked for with its subject beside the word ("a canning drill",
    "quiz me on first aid"), never "a drill at work" or "drill the holes"; a money or business one only with the word
    "drill" ("a budget scenario" is his own planning). The quiz and study modes step aside for one
    (core/conversation_modes.py: "quiz me on first aid" had gone to the textbooks)."""
    said = " ".join(str(words or "").lower().replace("’", "'").split())
    if not (_REQUEST.search(said) and _ASKED_FOR.search(said)) or _NOT_THIS.search(said) \
            or re.search(r"\b(fire drill|drill at work|drills? at work|at work)\b", said):
        return None
    drill = find(said)
    if drill is not None and drill.program in ("money", "business") and not re.search(r"\bdrills?\b", said):
        return None  # "a budget scenario", "quiz me on my budget": his own planning, not a drill (fourth review)
    return drill


def courses() -> list:
    """The courses with drills, in the order their drills come: [program id, ...]."""
    return list(dict.fromkeys(d.program for d in DRILLS))


def page_of(program_id: str) -> list:
    """The course page's Drills: each drill whole, its choices' verdicts included (shown once one is picked)."""
    return [{"id": d.id, "title": d.title, "situation": d.situation, "lesson": d.lesson,
             "questions": [{"ask": q.ask, "choices": [{"text": c.text, "verdict": c.verdict, "why": c.why}
                                                      for c in q.choices]} for q in d.questions]}
            for d in of_program(program_id)]


def _start_tool(context, arguments: dict) -> str:
    """Tool start_drill: a drill's opening and first question."""
    drill = find(str(arguments.get("question", "") or ""))
    return start(drill) if drill else "There's no drill for that yet."


def register_drill_tools(registry) -> None:
    """Registers start_drill (its answers are taken in code, `reply`).
    Its words cover the canning and carpentry drills too."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="start_drill", domain="learning",
        description="Start a scenario drill: a situation and a few decisions, each judged with why (survival, "
                    "canning safety, a saw cut: \"give me a survival drill\", \"a canning drill\").",
        parameters={"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                    "required": []}, prompt_arg="question",
        handler=_start_tool, trigger_phrases=("survival drill", "survival scenario", "bushcraft drill",
                                             "canning drill", "carpentry drill", "give me a drill", "run a drill",
                                             "another drill", "scenario drill"),
    ))
