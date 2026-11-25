"""
core.gardening_path
=====================

Gardening and homesteading, a learning program on core/paths.py's method (DEC-0289; Zac, 2026-11-23: "Gardening /
homesteading"): soil, seeds and transplants, growing through the season, and putting food by. Stages of lessons with
why and what to watch for, checks said or counted, homework missions from the practice log. His own garden plans
(the Planner, core/garden_plans.py) are where it's practised; canning follows the USDA only.

Written from: US land-grant extension vegetable gardening guides (soil testing, planting and watering); Mel
Bartholomew, All New Square Foot Gardening; USDA Complete Guide to Home Canning (2015) and the National Center for Home
Food Preservation; land-grant extension backyard poultry guides (predator-proofing, feed and water, winter ventilation,
the fire risk of heat lamps) for the flock. Its XP goes to the Gardening skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "gardening"  # her skill tree's Gardening skill (data/skill_definitions.json)

STAGES: tuple[Stage, ...] = (
    Stage(1, "Soil and site", "choosing the spot and building soil that grows", (
        Lesson("site", "Choosing the spot", (
            "Fruiting crops (tomatoes, peppers, squash) need 6 to 8 hours of direct sun; leafy greens manage with 4 "
            "to 6.",
            "Close to water and to the house: a garden you walk past is a garden you tend.",
            "Avoid low spots where cold air and water sit, and the roots of big trees."),
            "Sun is the one thing you can't add later; everything else can be built.",
            ("A shady corner chosen because it was free.",)),
        Lesson("soil", "Soil, tested and built", (
            "Get a soil test from the extension office: it gives pH and nutrients for your actual soil.",
            "Most vegetables like a pH of 6.0 to 7.0; lime raises it, sulfur lowers it, by the test's numbers.",
            "Work 2 to 3 inches of finished compost into the top 6 to 8 inches each year, or fill raised beds with a "
            "mix of topsoil and compost.",
            "Never work soil when it's wet enough to make a ball that won't crumble: it compacts."),
            "Plants live or fail by their roots; good soil fixes more problems than any spray.",
            ("Adding fertilizer by guesswork instead of the test.",)),
    ), (
        Check("soil_test", "Get a soil test and tell MIA its pH and what it recommends", "said"),
        Check("bed_built", "Build or prepare a bed with compost worked in", "said"),
    )),
    Stage(2, "Seeds and transplants", "starting seeds indoors, hardening off and planting out", (
        Lesson("seed_starting", "Starting seeds indoors", (
            "Use a sterile seed-starting mix, not garden soil; sow about two to three times as deep as the seed is "
            "wide.",
            "Keep them warm to sprout (most like 70 to 80°F), then give them 14 to 16 hours of light a day, the grow "
            "light a few inches above the leaves.",
            "Water from below or with a gentle mist; keep the mix moist, never soggy.",
            "The Planner's dates for each crop count back from your last frost."),
            "Too little light makes tall, weak seedlings; too much water rots them.",
            ("Seedlings stretching toward a window: they need more light, closer.",)),
        Lesson("transplant", "Hardening off and planting out", (
            "Over 7 to 10 days, set seedlings outside a little longer each day, shade first, then sun; bring them in "
            "on cold nights.",
            "Plant out on a cloudy day or in the evening, at the depth they grew (tomatoes can go deeper).",
            "Water them in well right away, and again the next day."),
            "Seedlings raised indoors scorch and stall if they go straight into full sun and wind.",
            ("Planting tender crops before the last frost has passed.",)),
    ), (
        Check("seeds_started", "Start a tray of seeds and keep them alive to transplant size", "counted", passes_at=1,
              unit="trays raised"),
        Check("planted_out", "Harden off and plant out a crop, and tell MIA how it took", "said"),
    )),
    Stage(3, "Through the season", "watering, feeding, pests and the harvest", (
        Lesson("water_feed", "Watering and mulch", (
            "Water deeply, about an inch a week including rain, at the base of the plants, in the morning.",
            "Mulch 2 to 3 inches (straw, shredded leaves) once the soil warms: it holds water and stops weeds.",
            "Side-dress heavy feeders (corn, squash, tomatoes) with compost mid-season."),
            "Deep, less frequent watering grows deep roots; wet leaves at night invite disease.",
            ("Light daily sprinkling, which keeps roots shallow.",)),
        Lesson("pests", "Pests and disease, the least harmful way first", (
            "Walk the garden often and look under leaves: catch a problem early.",
            "Hand-pick, use row covers, rotate where each family grows year to year, and remove diseased leaves.",
            "Only then the least-toxic treatment that names the pest, used exactly as its label says."),
            "Most damage is stopped by noticing early; sprays used first kill the insects that eat the pests.",
            ("Spraying without knowing what the pest is.",)),
        Lesson("flock_care", "Keeping a small flock", (
            "Close the coop at dusk, every night, once the birds are in: most predator losses happen after dark.",
            "Cover openings with hardware cloth, buried or skirted at the base: chicken wire keeps chickens in, but "
            "raccoons and dogs tear or reach through it.",
            "Fresh water every day and a complete layer feed, with oyster shell on the side for strong eggshells.",
            "In winter, ventilation high in the coop rather than heat: trapped moisture makes frostbite far likelier, "
            "and heat "
            "lamps start coop fires.",
            "Collect eggs every day. A bird that's hunched, off its feed or not like the others gets separated, "
            "watched, and seen by a vet who treats poultry if it doesn't pick up.",
            "Once a month, check each bird for mites and lice: part the feathers under the wings and around the vent "
            "and look for crawling specks or egg clusters at the feather bases. Red mites hide in roost cracks by day "
            "and feed at night, so check the roosts with a flashlight after dark. Treat with a product labelled for "
            "poultry, exactly as its label says, and clean out the coop's bedding at the same time."),
            "A flock does well on routine: shut in at night, clean water, the right feed, and an eye on each bird.",
            ("Chicken wire as predator protection.", "A heat lamp in the coop.")),
    ), (
        Check("first_harvest", "Bring in a first harvest from a crop you planned", "said"),
        Check("rotation_planned", "Plan next year's beds so no family grows where it grew this year", "said"),
    )),
    Stage(4, "Putting food by", "canning safely, drying and storing", (
        Lesson("canning_safe", "Canning, the safe way", (
            "Use only tested recipes: the USDA Complete Guide to Home Canning, the National Center for Home Food "
            "Preservation, or a Ball book; never an untested family recipe.",
            "High-acid foods (most fruit, pickles, jams, tomatoes with added acid) go in a boiling-water canner; "
            "low-acid foods (vegetables, beans, meat) only in a pressure canner, at the pressure and time the recipe "
            "gives for your altitude.",
            "Leave the headspace the recipe says, wipe the rims, use new lids, and check every seal after 24 hours."),
            "Low-acid food canned wrong can carry botulism, which you can't see, smell or taste.",
            ("Water-bathing green beans or other low-acid food.", "Skipping the altitude adjustment.")),
        Lesson("dry_store", "Drying and storing", (
            "Dry herbs and fruit in a dehydrator. Jerky: heat the meat to 160°F (poultry 165°F) before or after "
            "drying, as the USDA says: a dehydrator alone may not kill what's in it. Store dried food airtight, cool "
            "and dark.",
            "Potatoes, onions, squash and roots keep for months in a cool, dark, airy place, each at its own "
            "temperature and humidity.",
            "Label everything with what and when; eat the oldest first."),
            "Storing well stretches a harvest through the winter without a freezer.",
            ("Storing apples beside potatoes: the apples' gas sprouts them.",)),
    ), (
        Check("canned_batch", "Can a batch from a tested recipe and tell MIA how every jar sealed", "said"),
    )),
)

PROGRAM = register(Program(
    "gardening", "Gardening and homesteading", SKILL, "🌱", "From soil and seeds, through the season, to putting food "
    "by safely: a garden that feeds you.",
    ("gardening", "grow vegetables", "vegetable garden", "homesteading", "grow my own food", "seed starting"), STAGES,
    plan=(20, 4)))
