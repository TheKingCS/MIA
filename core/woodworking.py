"""
core.woodworking
==================

Woodworking, a learning program on core/paths.py's method (DEC-0289; Zac, 2026-11-23: "Woodworking / building"), beside
the carpentry apprentice (core/carpentry.py, framing and site work): this one is the bench: sharp tools, reading the
wood, joinery and finishing. Stages of lessons with why and what to watch for, checks said or counted, homework
missions from the practice log. Safety first; never a claim of certification.

Written from: Albert Jackson and David Day, The Complete Manual of Woodworking (Knopf); Leonard Lee, The Complete Guide
to Sharpening (Taunton); US Forest Products Laboratory, Wood Handbook (FPL-GTR-282, wood movement and moisture);
OSHA 29 CFR 1910.213 (woodworking machinery). Its XP goes to the Woodworking skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "woodworking"  # her skill tree's Woodworking skill (data/skill_definitions.json)

STAGES: tuple[Stage, ...] = (
    Stage(1, "Safety, the wood and a sharp edge", "working the machines safely, reading grain, and sharpening", (
        Lesson("machine_safety", "Safe at the machines", (
            "Safety glasses on whenever anything spins; hearing protection at the saws, planer and router; a dust mask "
            "or extraction for sanding.",
            "Table saw: the blade guard, riving knife or splitter on; a push stick for anything narrower than 6 in; "
            "stand to the side of the blade's line, never behind it; never cut freehand: always the fence or the "
            "miter gauge, never both at once for a crosscut.",
            "Router: feed against the bit's rotation: handheld, that's left to right along an edge you face; on a "
            "router table it's right to left. Take shallow passes.",
            "Unplug a tool before changing a blade or bit, and wait for anything spinning to stop before reaching in."),
            "Most shop injuries come from kickback and from reaching near a moving blade; these habits are what "
            "prevent them.",
            ("Loose sleeves, gloves or jewellery near a spinning blade.",
             "Ripping without a riving knife: the wood can pinch the blade and throw the piece back.")),
        Lesson("reading_wood", "Reading the wood", (
            "Look at the grain on the edge: plane and cut 'downhill', with the fibres, to avoid tearout.",
            "Wood moves across the grain as its moisture changes, very little along it: leave room for a panel to "
            "move in its frame, and never glue a wide board across another's grain.",
            "Let lumber sit in the shop a week or two before you work it, so it settles to the room's moisture "
            "(about 6 to 8% indoors in most homes).",
            "Mark a face side and a face edge on every part, and measure everything from them."),
            "A joint that fits today can crack or gap next season if the wood's movement was ignored.",
            ("Cutting the moment boards come home from a damp store.",
             "Planing against the grain and blaming a dull blade for the tearout.")),
        Lesson("sharpening", "Sharpening a chisel and a plane iron", (
            "Flatten the back near the edge first, on a coarse stone, until it's flat and shiny right to the edge.",
            "Hone the bevel at about 25 degrees (a honing guide holds it), working up the grits, coarse to fine, "
            "until a small burr forms along the whole edge.",
            "Add a small microbevel at about 30 degrees on the finest stone, then remove the burr by a few light "
            "strokes on the back.",
            "Test: it should pare a thin, clean shaving from end grain."),
            "A sharp tool cuts cleaner and is safer: a dull one needs force, and force is what slips.",
            ("Rocking the bevel, which rounds it.", "Skipping the back: an edge is only as sharp as both faces.")),
    ), (
        Check("safety_said", "Walk MIA through making a rip cut on the table saw safely, step by step", "said"),
        Check("sharp_chisel", "Sharpen a chisel until it pares a clean shaving from end grain, and tell MIA", "said"),
        Check("grain_read", "Plane three boards with no tearout by reading their grain", "counted", passes_at=3,
              unit="boards"),
    )),
    Stage(2, "Marking, cutting and joinery", "cutting to a line and making joints that fit straight from the saw", (
        Lesson("marking", "Marking out", (
            "Use a marking knife and a square, not a pencil, for joints: a knife line is finer and gives the chisel "
            "and saw a place to start.",
            "A marking gauge, set once, marks the same distance on every part: set it from the actual piece, not "
            "the ruler, when you can.",
            "Mark the waste side of every line with an X so you cut on the right side of it."),
            "Accuracy is set when you mark; sawing and chiselling only follow the line.",
            ("Measuring each part from a ruler instead of from its mate: small errors add up.",)),
        Lesson("sawing", "Sawing to a line", (
            "Start the cut on the waste side of the knife line, the saw at a low angle, guided by your thumb.",
            "Let the saw's weight do the work; long, light strokes; watch the line, not the saw.",
            "Saw square: check the cut with the square, front and side."),
            "A cut that's square and on the line needs no fixing; one off the line becomes a gap in the joint.",
            ("Forcing the saw, which makes it wander.",)),
        Lesson("joints", "Three joints to start with", (
            "Butt joint with screws: drill a pilot hole and a clearance hole, countersink, and glue the long grain.",
            "Dado and rabbet: the dado holds a shelf in a groove; cut its walls to the knife lines, then clear the "
            "waste with a chisel or router plane, checking the depth.",
            "Mortise and tenon: cut the mortise first, then fit the tenon to it, paring until it slides in with hand "
            "pressure: snug, not hammered.",
            "Glue up: a dry fit first, clamps ready, glue on both faces, even clamp pressure, and wipe squeeze-out or "
            "let it skin and pare it off."),
            "These three joints build most furniture; a mortise and tenon is among the strongest frame joints there is.",
            ("Too tight a tenon: it can split the mortise.", "Gluing end grain and expecting it to hold.")),
    ), (
        Check("square_cuts", "Crosscut ten boards by hand, each square within 1/32 in", "counted", passes_at=10,
              unit="square cuts"),
        Check("mortise_tenon", "Make a mortise and tenon that slides together with hand pressure, and show MIA", "said"),
        Check("glue_up", "Glue up a flat panel from three boards, flat within 1/32 in across its width", "said"),
    )),
    Stage(3, "Finishing and a first piece", "sanding, a finish that lasts, and a piece made start to end", (
        Lesson("sanding", "Sanding", (
            "Sand with the grain, through the grits in order (for example 120, 150, 180), never skipping more than one.",
            "Remove the dust between grits; wipe with a damp cloth to raise the grain, let it dry, then a last light "
            "sanding.",
            "Stop at 180 to 220 for most finishes: finer can keep stain from taking."),
            "Scratches from a coarser grit show through the finish; each grit removes the last one's.",
            ("Sanding across the grain, which leaves scratches the finish magnifies.",)),
        Lesson("finishes", "Finishes and their danger", (
            "An oil finish (Danish or boiled linseed) is easy and repairable; wipe-on polyurethane is tougher; "
            "shellac dries fast and seals.",
            "Thin coats, wiped on and off; let each dry fully, a light sanding between coats.",
            "Rags with oil finish can catch fire by themselves as they dry: lay them flat outside to dry, or keep "
            "them in a closed metal can of water."),
            "A finish protects the wood; oily rags are one of the most common causes of shop fires.",
            ("A wadded oily rag in the trash.", "Thick coats that never cure.")),
        Lesson("first_piece", "A first piece", (
            "Pick something small with real joints: a step stool, a box, a cutting board.",
            "Cut list first, parts marked from their face side, dry fit, then glue and finish.",
            "Keep notes and photos: what fit, what didn't, what you'd change."),
            "Finishing a whole piece teaches the order of work that no single joint does.",
            ("Starting with a big project that never gets finished.",)),
    ), (
        Check("oily_rags", "Tell MIA how you'll handle oily rags after finishing", "said"),
        Check("first_piece_done", "Finish a first piece, start to end, and show MIA", "said"),
    )),
)

PROGRAM = register(Program(
    "woodworking", "Woodworking at the bench", SKILL, "🪵", "From a sharp edge and reading the grain, through marking, "
    "sawing and joinery, to finishing a first piece.",
    ("woodworking", "woodwork", "joinery", "furniture making", "sharpening chisels", "fine woodworking"), STAGES,
    plan=(30, 3)))
