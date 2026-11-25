"""
tests.test_code_routes_corpus
===============================

MIA's code routes (the answers taken in code before the model: a course's lesson, a materials list, a course's next
lesson, days of water, a reminder on a day or every week, a drill, a first-aid how-to, a lab to build or simulate)
each take only what they're for. Review after review (2026-11-25) found a new route taking someone else's message
("I built 200 feet of fence", "remind me to buy 14 days of water", "the next step for my money"), so this corpus of
everyday messages must reach none of them; add to it whenever one is found, and give each new route a line in
`ROUTES` and its own question in `MEANT`.
"""

from types import SimpleNamespace

import pytest

from core import assistant_turn as turn
from core import drills, esp32_sim, first_aid_floor, lesson_answer, paths
from core.assistant_path_actions import next_lesson_reply
from core.assistant_plan_actions import materials_reply

EVERYDAY = (
    # chat
    "hey, how's it going?", "thanks for the help earlier", "I'm tired today", "what do you think about that?",
    "tell me a story about a dragon", "that's a good point", "I had a rough day at work", "good night MIA",
    # the homestead's records
    "I fed the chickens this morning", "the hens laid 6 eggs today", "how many eggs this week?",
    "I built 50 feet of fence yesterday", "the water tank is at 300 gallons", "we used a lot of water this week",
    "I lit a fire in the wood stove", "the creek is up after the rain", "how's the garden doing?",
    "what's the weather tomorrow?", "is it going to freeze tonight?", "I started the tomato seeds today",
    "the fire pit project is going well", "how much feed is left?", "the goats got out again",
    "how do i tell if my dog has mites", "what should i do about head lice", "how do I clean the water tank",
    "how do I build a fire pit", "how do I water the tomatoes?", "When should I start tomato seeds?",
    # the business and money
    "I sold 3 cutting boards today", "Sarah paid her deposit", "what did I make this month?",
    "how much margin did the shop make?", "send Sarah her quote", "how much do I owe on the truck?",
    "I paid the electric bill", "what bills are due?", "how much did I spend on feed?",
    "how do i draw up an estimate of my taxes", "what is the margin on my cutting boards",
    "I built 200 feet of fence today, how many posts did that take", "how many posts for a barbed wire fence 1000 feet",
    # the calendar and reminders that aren't a new event
    "what's on my calendar?", "remind me why I started this", "remind me in 20 minutes to check the oven",
    "set an alarm for 6am", "did I miss any reminders?", "move the dentist to Friday",
    "remind me to buy 14 days of water", "set my water target to 30 days of water",
    # learning, his own
    "what's my next step?", "how's my guitar practice going?", "I practiced for 20 minutes",
    "what did I learn this week?", "what's next?", "what's the next step for my money",
    "what's my next lesson plan for the business meeting",
    # first aid talk that isn't a how-to
    "I watched a show about the Red Cross", "my CPR certification expires next month", "I bought a first aid kit",
    "I burned the toast", "how do I bleed a radiator", "how do I choke a chainsaw",
    # the workshop and the bench
    "I finished the bookshelf", "the saw is dull", "I need more 2x4s", "what tools do I have?",
    "can you simulate a day in the greenhouse like the web lab", "a drill at work today", "can I drill into the stud?",
    # money said that isn't an expense of his (bills, debts, people: their own tools)
    "I paid $120 for the electric bill", "I paid $500 on the truck loan", "I paid Sarah $40 back",
    "how much have I spent on groceries?", "I spent the day on the fence", "I paid the vet",
)


@pytest.fixture()
def routes(tmp_path):
    """Each code route, as a function of the words; a change route records instead of acting.
    What he spent is one of them."""
    context = SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path), kitchen=None, llm=None,
                              conversations=None,
                              assistant_actions=SimpleNamespace(execute=lambda c, n, a: f"ran {n}"))
    empty = SimpleNamespace(messages=[])
    return {
        "lesson": lambda w: lesson_answer.find(w),
        "materials": lambda w: materials_reply(None, w),
        "next lesson": lambda w: next_lesson_reply(context, w),
        "days of water": lambda w: turn._water_on_hand_reply(context, w),
        "reminder on a day": lambda w: turn._reminder_reply(context, w),
        "weekly reminder": lambda w: turn._weekly_reminder_reply(context, w),
        "drill": lambda w: drills.requested(w),
        "first-aid how-to": lambda w: first_aid_floor.teach(w),
        "spent": lambda w: turn._spent_reply(context, w),
        "lab": lambda w: esp32_sim.reply(context, empty, w),
    }


# Each route's own question, so a route that stops working fails here too
MEANT = {
    "lesson": "How do I sharpen a chisel?", "materials": "How many fence posts for 200 feet?",
    "next lesson": "What's my next guitar lesson?", "days of water": "How many days of water do I have?",
    "reminder on a day": "remind me to check the oil Saturday",
    "weekly reminder": "remind me every Monday to check the water filter", "drill": "give me a choking drill",
    "first-aid how-to": "how do you use a tourniquet?", "lab": "walk me through building the pot lab",
    "spent": "I spent $30 on groceries",
}


def test_no_everyday_message_is_taken_by_a_code_route(routes):
    taken = [(name, words) for words in EVERYDAY for name, route in routes.items() if route(words)]
    assert taken == []


def test_each_route_still_takes_its_own_question(routes, monkeypatch):
    from core import water_budget

    monkeypatch.setattr(water_budget, "say", lambda context: "No tank levels logged.")
    for name, words in MEANT.items():
        assert routes[name](words), name
