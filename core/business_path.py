"""
core.business_path
====================

Small business basics, a learning program on core/paths.py's method (Zac's goal: "my businesses skills"; brainstorm
round 13: a market-day drill): knowing your numbers, keeping the business's money apart, customers and their terms,
and growing what sells. Stages of lessons with why and what to watch for, checks said, and a drill (core/drills.py:
"market day"). His own records are the Business apps' (orders and quotes, products, what to make next, who owes him);
this is the method, practised on them. Tax and legal rules differ by place: the lessons say to check his own, never
what they are.

Written from: the US Small Business Administration's guides on pricing, record-keeping and separating business and
personal finances; general practice, never legal or tax advice. Its XP goes to the Business skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "business"  # her skill tree's Business skill (data/skill_definitions.json)

STAGES: tuple = (
    Stage(1, "Know your numbers", "what each thing costs to make, and a price that pays you", (
        Lesson("biz_cost", "What it really costs", (
            "Add up the materials for one item, a share of the supplies and tools it wears out, and the fees to sell "
            "it (market stall, card reader, listing fees).",
            "Count your own time too: the hours to make it, times what your hour is worth.",
            "That total is the floor: a price under it loses money on every sale, however busy it looks."),
            "Many small makers price by feel and find out later they've been paying to work.",
            ("Leaving your own time out of the cost.", "Forgetting the fees that come off each sale.")),
        Lesson("biz_price", "A price that works", (
            "Start from the cost, add a margin for the business itself (the slow months, the next tools), and look "
            "at what similar things sell for.",
            "Raise prices for what sells out; drop or rework what doesn't sell at a price that pays you.",
            "Write your prices down and keep to them: haggling every sale down makes the floor your ceiling."),
            "A price that covers cost, time and margin is what lets the business last.",
            ("Matching the cheapest seller instead of your own costs.",)),
    ), (
        Check("biz_costed", "Work out the full cost of one product, your time included, and tell MIA", "said"),
        Check("biz_priced", "Set a price for it that covers cost, time and a margin, and tell MIA", "said"),
    )),
    Stage(2, "Keep it separate", "the business's money apart from yours, and every sale recorded", (
        Lesson("biz_separate", "Separate money, every record", (
            "Use a separate account (or at least a separate card) for the business: what comes in and goes out stays "
            "clear.",
            "Record every sale and every expense the day it happens, and keep the receipts.",
            "Pay yourself from the business on purpose, as a set amount, instead of dipping in.",
            "Find out the tax and licence rules where you sell, and set money aside for the tax as you go."),
            "Clean records show what's really making money, and make tax time a matter of adding up.",
            ("Mixing the business and household money in one account.", "Records rebuilt from memory at year's end.")),
    ), (
        Check("biz_records", "Keep a week's sales and expenses recorded the day they happen, and tell MIA", "said"),
    )),
    Stage(3, "Customers", "clear terms, and being easy to buy from again", (
        Lesson("biz_terms", "Clear terms", (
            "Say up front what a customer gets, when, what it costs, and how to pay.",
            "Have a refund or exchange policy and show it; handle a problem quickly and kindly, within it.",
            "For custom work, a written quote and a deposit before you start.",
            "Ask happy customers how they found you, and to tell someone."),
            "Most small businesses grow from people who come back and send others.",
            ("Starting custom work without a deposit.", "A refund policy made up on the spot.")),
    ), (
        Check("biz_policy", "Write down your refund policy and how you take payment, and tell MIA", "said"),
    )),
    Stage(4, "Grow what sells", "learning from the numbers, then doing more of what works", (
        Lesson("biz_grow", "Grow what sells", (
            "Once a month, look at what sold, what it earned after costs, and what sat.",
            "Make more of what sells at a good margin; drop or change what doesn't.",
            "Try one new thing at a time, small, and see if it sells before making many."),
            "The numbers you've kept tell you where the next hour is best spent.",
            ("Adding many new products at once and not knowing which worked.",)),
    ), (
        Check("biz_review", "Do a month's review of what sold and what earned, and tell MIA what you'll change",
              "said"),
    )),
)

PROGRAM = register(Program(
    "business", "Small business basics", SKILL, "🏪", "Knowing your numbers, keeping the business's money apart, clear "
    "terms for customers, and growing what sells: the method, practised on your own business.",
    ("small business", "business skills", "run my business", "selling at the market", "pricing my products"),
    STAGES, plan=(15, 3)))
