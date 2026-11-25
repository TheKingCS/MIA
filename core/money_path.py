"""
core.money_path
=================

Money basics, a learning program on core/paths.py's method (Zac's goal: "the ultimate tool ... for my businesses
skills, finance skills"; brainstorm round 13, drills for money): where it goes, a cushion, debt in the right order, and
saving for later. Stages of lessons with why and what to watch for, checks said, and a drill
(core/drills.py: "a surprise bill"). His own numbers live in the Money app (the budget, the debts, the freedom date);
this is the method, practised on them. No amounts are given here: a cushion is counted in months of his own expenses,
and money is said in his region's way where it's said at all (core/region.money).

Written from: the US Consumer Financial Protection Bureau's guides on budgeting, emergency savings and paying down
debt, and FINRA's investor education (employer matches, low-cost diversified funds); general guidance, never advice
about his own taxes or a particular investment. Its XP goes to the Finance skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "finance"  # her skill tree's Finance skill (data/skill_definitions.json)

STAGES: tuple = (
    Stage(1, "Where it goes", "seeing a month of spending and planning the next", (
        Lesson("money_track", "See where it goes", (
            "Take one month of statements (or bring them into the Money app) and list every expense.",
            "Sort each into needs (housing, food, utilities, transport), wants, and saving or debt.",
            "Divide the yearly bills (insurance, registration, memberships) by twelve, so they count every month.",
            "Name the three biggest categories, and the one that surprised you."),
            "You can't steer what you can't see; most people find a category far bigger than they guessed.",
            ("Guessing instead of looking at the statements.", "Leaving out the bills that come once a year.")),
        Lesson("money_plan", "A plan for the month", (
            "Start from what comes in, take out the fixed bills, and give the rest a job: needs first, then saving or "
            "debt, then wants.",
            "Check it once a week against what you've spent.",
            "At the month's end, change next month's plan from what really happened, not from what you hoped."),
            "A plan made before the month decides where money goes; without one, the month decides.",
            ("A plan so tight it breaks in the first week.",)),
    ), (
        Check("money_seen", "Sort a month of your spending and tell MIA the three biggest categories", "said"),
        Check("money_planned", "Keep to a month's plan within a tenth, and tell MIA how it went", "said"),
    )),
    Stage(2, "A cushion", "an emergency fund, so a surprise isn't a crisis", (
        Lesson("money_cushion", "The emergency fund", (
            "Start with a small buffer: enough for a minor repair or about a month of bare-bones expenses.",
            "Then build it toward three to six months of essential expenses, more if your income swings.",
            "Keep it in a separate savings account you can reach in a day, not in your everyday account and not in "
            "investments that can fall.",
            "Use it only for emergencies (a job loss, a repair, a medical bill), and refill it first afterwards."),
            "With a cushion, a surprise bill is an inconvenience; without one, it goes on a card at high interest.",
            ("Investing the cushion, so it's down when you need it.", "Dipping into it for wants.")),
    ), (
        Check("money_cushion_started", "Open a separate savings for emergencies and put the first month's amount in it",
              "said"),
    )),
    Stage(3, "Debt", "paying it down in the right order", (
        Lesson("money_debt", "Paying debt down", (
            "List every debt: what's owed, the interest rate, and the minimum payment.",
            "Pay every minimum, on time, every month.",
            "Put anything extra on the highest-rate debt first (the avalanche: the least interest paid overall), or "
            "on the smallest balance first if quick wins keep you going (the snowball).",
            "Stay away from payday loans and cash advances: their fees work out to very high rates."),
            "Interest compounds against you; the highest rate costs the most every month it's left.",
            ("Paying only the minimum on a credit card.", "Taking on new debt while paying the old down.")),
    ), (
        Check("money_debt_listed", "List every debt with its rate and minimum, and tell MIA which you'll pay first",
              "said"),
    )),
    Stage(4, "For later", "saving and investing once the basics hold", (
        Lesson("money_later", "Saving for later", (
            "If your employer matches what you put into a retirement account, put in at least enough to get the whole "
            "match: it's an immediate return.",
            "Keep the cushion full and the high-rate debt gone before investing much more.",
            "For most people, low-cost, broad index funds beat picking stocks.",
            "Make it automatic on payday, so saving happens before spending."),
            "Time does most of the work: money saved early grows far more than money saved late.",
            ("Leaving an employer match unclaimed.", "Investing money you'll need within a few years.")),
    ), (
        Check("money_auto_saving", "Set up an automatic transfer to savings or investing on payday, and tell MIA",
              "said"),
    )),
)

PROGRAM = register(Program(
    "money", "Money basics", SKILL, "💵", "Where your money goes, a cushion for surprises, debt paid down in the right "
    "order, and saving for later: the method, practised on your own numbers.",
    ("money basics", "personal finance", "budgeting skills", "get out of debt", "emergency fund", "money skills"),
    STAGES, plan=(15, 3)))
