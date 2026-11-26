"""
tests.live_sweep_corpus
=========================

The everyday phrasings tools/live_sweep.py asks through the whole turn on the PC's model, by area: the ones the
sweeps of 2026-11-25 found answered wrong, kept so each fix stays checked against the real model, plus a few
conversations (a list of turns in one conversation). Not a pytest test (no `test_` names); add a phrasing whenever a
sweep or Zac finds one answered wrong.
"""

CORPUS = {
    "money": [
        "How much did I spend on groceries this month?", "Am I over budget anywhere?", "What's my net worth?",
        "How much is my truck loan?", "If I pay an extra $100 a month on the truck, when is it paid off?",
        "Did I pay the electric bill?", "I spent $45 on chicken feed", "What's my biggest bill?",
        "Can you automate my bill reminders?", "Who do I owe money to?",
    ],
    "business": [
        "How do I price my firewood?", "I sold 2 cutting boards for $80", "How many cutting boards do I have?",
        "What should I build next for the shop?", "How much should I charge per dozen eggs?",
        "write a quote for a 12 by 16 deck",
    ],
    "home": [
        "Remind me tomorrow at 9 to call the vet", "Remind me to change the furnace filter every month",
        "Add milk and eggs to my grocery list", "We're out of milk", "What's on my grocery list?",
        "What's on my calendar this week?", "My freezer uses 150 watts", "a pipe burst in the basement",
        "What do I do if the power goes out for a week?", "How do I check the voltage at an outlet?",
        "When is my truck due for an oil change?", "Log 2 hours on the garage rewire",
    ],
    "safety": [
        "i smell gas", "the kitchen is on fire", "my co alarm keeps going off", "he's not breathing",
        "my dad isn't breathing and the house is full of smoke", "I'm on fire today, got so much done",
    ],
    "knowledge": [
        "What size hook should I use for catfish?", "How do I solder the headers on my nano?",
        "How do I start a fire without matches?", "When should I start my tomato seeds?",
        "What should be in a 72 hour bag?", "How do I keep my chickens warm in winter?", "convert 70 f to c",
        "When is Thanksgiving?", "How many days until Christmas?", "What time is it?",
        "What's the square footage of a 12 by 16 shed?", "Teach me how to tie a bowline",
    ],
    "hobbies": [
        "What's my next guitar lesson?", "Give me a chord progression to practice", "How do I tune my guitar?",
        "I practiced guitar for 20 minutes", "What woodworking project should I do next?",
        "How do I sharpen a chisel?", "I want to learn to weld", "What's a good workout for today?",
        "I did 3 sets of 10 squats at 185", "How's my training going this week?",
    ],
    "homestead": [
        "How many eggs did the hens lay this week?", "I collected 8 eggs today", "Why aren't my hens laying?",
        "How much feed do I have left?", "When should I plant garlic?", "Should I water the garden today?",
        "It rained an inch last night", "How long will my water last?", "How do I can tomatoes?",
        "How much firewood do I need for the winter?",
    ],
    "automation": [
        "What can you do on your own?", "Remind me every Friday to check the oil",
        "Every morning tell me the weather and my day", "Stop the morning briefing",
        "Watch me: the Friday reset", "What are you watching for me?",
    ],
    "anticipating": [
        "How's the homestead?", "How long could we last?", "How's my money this week?",
        "What did you learn this week?", "How are my hobbies going?", "What does my week look like?",
        "Tell me if it freezes tonight", "Let me know when we're low on coffee",
        "Tell me when the feed gets under 4 days", "What are you watching for me?",
    ],
    "conversation": [
        ["I'm thinking about getting goats", "What breed would be good for milk?", "How much space do they need?",
         "Thanks, that's helpful"],
        ["My truck has been making a squealing noise when I brake", "It's worse in the morning",
         "Add that to my maintenance list"],
        ["I had a rough day at work", "My boss yelled at me in front of everyone"],
        "Give me a quick survival tip", "Do you remember what I told you yesterday?", "Who are you?",
    ],
}
