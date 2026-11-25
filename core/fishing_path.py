"""
core.fishing_path
===================

Fishing basics, a learning program on core/paths.py's method (Zac's goal, 2026-11-25: "knowledgeable and integrated
with and about my hobbies"; fishing is one of his own, docs/VISION.md, and the live sweeps found her guessing at hook
sizes): the knots and the hooks, rigs and where fish hold, then handling, the rules and keeping a catch. Stages of
lessons with why and what to watch for; checks said, or read from his own catch log (core/catch_log.py: a catch logged
counts, and so does a new species). How-tos from these lessons are answered in code (core/lesson_answer.py: "what size
hook for bass?").

Written from: Take Me Fishing (the Recreational Boating & Fishing Foundation's knot, hook and rig guides); the US Fish
and Wildlife Service's and state wildlife agencies' angler education; FishSmart's and NOAA's catch-and-release best
practices; USDA food safety for fish. Seasons, sizes, limits and licenses are his state's, never said here: the lesson
sends him to its regulations. Its XP goes to the Fishing skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "fishing"  # her skill tree's Fishing skill (data/skill_definitions.json)

STAGES: tuple = (
    Stage(1, "Knots and hooks", "tying on so it holds and choosing the hook for the fish", (
        Lesson("knots", "Two knots that hold", (
            "The improved clinch knot, for mono and fluorocarbon: pass the line through the hook's eye, wrap it around "
            "itself 5 to 7 times, back through the small loop by the eye, then through the big loop you just made.",
            "The Palomar knot, for braid and for most lines: double the line, pass the loop through the eye, tie a loose "
            "overhand knot, pass the hook through the loop, then pull it snug.",
            "Wet every knot before you pull it tight (spit or water): friction heat weakens line.",
            "Pull hard on the knot to test it, then trim the tag end, leaving about an eighth of an inch."),
            "Most lost fish are a knot that slipped or broke, not line that broke; two knots tied well cover nearly "
            "everything.",
            ("Tightening a knot dry.", "Too few wraps on a clinch knot in slick line.", "Trimming the tag flush.")),
        Lesson("hooks", "Hook sizes", (
            "Hook sizes run backwards up to size 1: a number 10 is smaller than a number 2. Past 1 they grow with a "
            "slash: 1/0, 2/0, 3/0 and up get bigger.",
            "Panfish (bluegill, sunfish, crappie): small hooks, about size 6 to 10; their mouths are small.",
            "Trout with bait: about size 8 to 12. Bass: soft plastic worms on an offset worm hook, about 2/0 to 4/0 "
            "(bigger plastics, bigger hooks); live bait on about size 1 to 1/0.",
            "Catfish: circle hooks, about 2/0 to 6/0, bigger for bigger fish and baits. With a circle hook, don't jerk "
            "to set it: let the fish take it and reel steadily, and it hooks the corner of the mouth.",
            "Match the hook to the bait as much as the fish: with bait, the point should show past it (a Texas-rigged "
            "plastic hides it on purpose), and the bait should fit the fish's mouth."),
            "Too big a hook and fish won't take the bait; too small and they swallow it or it straightens; the right "
            "size hooks the mouth, which is what a release needs.",
            ("A hook too big for panfish.", "Setting hard on a circle hook.", "A dull hook: test the point on a "
                                                                              "fingernail, and sharpen or replace it.")),
    ), (
        Check("knots_tied", "Tie each knot ten times until it holds every time under a hard pull, and tell MIA",
              "said"),
        Check("catches_logged", "Log five catches with MIA (\"I caught a bass at the pond\")", "recorded",
              passes_at=5, unit="catches", source="catches"),
    )),
    Stage(2, "Rigs and where fish hold", "setting up for what you're after and finding where they are", (
        Lesson("rigs", "Three rigs", (
            "A bobber rig: a float on the line, the hook below it at the depth the fish are, a small split shot or two "
            "between to hold the bait down. Good for panfish and for watching a bite.",
            "A Texas rig for bass: a bullet weight sliding on the line, then the offset hook with the worm threaded on "
            "so the point is tucked back into the plastic, weedless.",
            "A bottom rig for catfish: a sliding egg sinker, a bead and a swivel, then a leader of a foot or two to the "
            "hook, so the fish can take the bait without feeling the weight.",
            "Start with the lightest weight that reaches the bottom or holds the depth."),
            "The rig puts the bait where the fish are and lets them take it; the wrong one hangs in weeds or never "
            "reaches them.",
            ("Too heavy a weight.", "A bobber set at the wrong depth: move it until you find them.")),
        Lesson("reading_water", "Where fish hold", (
            "Fish hold by cover and edges: weed lines, fallen trees, docks, rocks, drop-offs where shallow meets deep.",
            "In summer heat, try early and late, or deeper and in shade; in cold water, fish move slower: slow down.",
            "A wind-blown bank piles up food, and fish follow it.",
            "Moving water: fish wait behind rocks and in eddies, facing upstream, for food to come to them.",
            "Fish a spot a few casts, then move: cover water until you find them, then slow down there."),
            "Most of a lake holds few fish; finding where they are matters more than any lure.",
            ("Casting to open water with nothing near it.", "Staying all day where nothing bites.")),
    ), (
        Check("species_logged", "Catch and log three different species", "recorded", passes_at=3, unit="species",
              source="species"),
        Check("rigs_fished", "Fish each of the three rigs on a trip, and tell MIA which caught", "said"),
    )),
    Stage(3, "Handling, the rules and keeping a catch", "releasing a fish alive, fishing legally, and keeping one fresh", (
        Lesson("release", "A good release", (
            "Wet your hands before you touch the fish; keep it in or over the water as much as you can.",
            "Support its belly with a big fish; never squeeze it or hold it by the gills or eyes.",
            "Back the hook out with pliers or a hook remover; on a hook swallowed deep, cut the line close: it does "
            "less harm than digging.",
            "Hold it upright in the water, facing into any current, until it swims off by itself."),
            "A fish handled gently and quickly mostly lives; air time, dry hands and squeezing are what kill released "
            "fish.",
            ("A long photo session out of the water.", "Tossing a fish back from a height.")),
        Lesson("rules", "The rules", (
            "Buy a fishing license for your state before you fish (most need one from about age 16), and carry it.",
            "Read your state wildlife agency's regulations for the water you fish: the season, the size limit, the "
            "bag (daily) limit, and any special rules for that lake or river.",
            "Measure a fish you mean to keep the way the regulations say (often mouth closed, tail pinched).",
            "Some waters are catch-and-release only, or lures only: the posted rules win.",
            "Check your state's fish consumption advisories for the water before you eat what you keep, and whether "
            "fish must stay whole, or skin-on, until you're home (some states measure them at the check)."),
            "The limits are what keep fish in the water for next year, and a ticket costs more than the trip.",
            ("Keeping a fish without measuring it.", "Fishing a new water without reading its rules.")),
        Lesson("cleaning", "Keeping and cleaning a catch", (
            "Put a fish you keep on ice right away, or keep it alive on a stringer or in a livewell until you leave.",
            "Clean it within a few hours: scale it or skin it, then gut it, or fillet it off the backbone with a sharp, "
            "flexible knife.",
            "Rinse it in cold water and keep it at 40\u00b0F or below; cook within a day or two, or freeze it.",
            "Cook fish until it flakes and reaches 145\u00b0F inside."),
            "Fish spoils fast in the heat; cold, quick cleaning is the difference between a good dinner and a bad one.",
            ("A kept fish left in a warm bucket.", "A dull fillet knife.")),
    ), (
        Check("released_right", "Release three fish the right way (wet hands, quick, upright in the water), and tell "
              "MIA", "said"),
        Check("rules_read", "Read your state's fishing regulations for the water you fish most, and tell MIA its "
              "limits for one species", "said"),
    )),
)

PROGRAM = register(Program(
    "fishing", "Fishing basics", SKILL, "\U0001f3a3", "Two knots that hold and the right hook, three rigs and where fish "
    "hold, then a good release, the rules and keeping a catch.",
    ("fishing", "fish", "angling", "bass fishing", "catch more fish", "fishing skills"), STAGES, plan=(30, 2)))
