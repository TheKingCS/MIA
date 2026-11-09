"""
core.carpentry
================

Carpentry, the first of Trade Master's apprentice programs (DEC-0149; Zac, 2026-11-08: "She should become a Trade
master and be able to teach an entry level Apprentice"). A learning path on core/paths.py's method, the same as guitar
(core/guitar.py): stages of lessons, each with steps, why and what to watch for, and checks said or counted, with
homework missions from the practice log. It teaches the trade's basics in the order an apprentice learns them, safety
first; it never claims a licence or certification.

Three stages to begin: safety, tools and measuring; layout and cutting; framing basics. The jobs in core/trade_jobs.py
(the coop, the workshop) are where the stages are practised for real. Its XP goes to the Carpentry skill.

Written from: Floyd Vogt, Carpentry (Cengage); American Wood Council, Wood Frame Construction Manual (WFCM) 2018;
International Code Council, IRC 2021, Section R602 (wood wall framing) and Table R602.3(1) (fastening schedule);
OSHA 29 CFR 1926 Subpart I (tools: hand and power).
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "carpentry"  # her skill tree's Carpentry skill (data/skill_definitions.json)

STAGES: tuple[Stage, ...] = (
    Stage(1, "Safety, tools and measuring", "working safely and measuring and marking to 1/16 in", (
        Lesson("safety", "Shop and site safety", (
            "Wear safety glasses whenever a tool is running, hearing protection for saws and nailers, and gloves for "
            "rough material, but never near a spinning blade or bit.",
            "Keep the floor clear where you walk and work: cords, offcuts and tools put away as you go.",
            "Unplug the saw (or take the battery out) before changing a blade or clearing a jam.",
            "Let the blade stop before lifting the saw from the cut, and never reach across a running blade.",
            "Know where the first-aid kit is, and don't run power tools alone or tired."),
            "Most carpentry injuries come from a few habits: no eye protection, hands near a blade, clutter underfoot.",
            ("Loose sleeves, jewellery and dangling cords near blades.", "Gloves catching in a drill or a table saw.")),
        Lesson("tape", "Reading a tape measure", (
            "Find the inch, then count the marks: the longest between inches is 1/2, then 1/4, 1/8, and the shortest "
            "1/16.", "The hook slides by its own thickness, so a measure is true pushed against something or hooked "
            "over its end.", "Mark with a V (a crow's foot) whose point is the measurement, then square a line through it.",
            "Measure twice, cut once; read the measurement back to yourself before you cut.",
            "Note the red marks every 16 in (stud spacing) and the small diamonds every 19.2 in (joists)."),
            "Every cut, wall and roof starts with a measurement; an eighth off on each stud adds up across a wall.",
            ("Reading 5/8 as 3/8: count from the nearest whole inch.", "Starting at the 1 in mark (burning an inch) "
             "and forgetting to take it off.")),
        Lesson("square_level", "Square, level and plumb", (
            "Use a speed square against the board's edge to mark 90 and 45 degree lines.",
            "Check a level is true: set it on a flat surface, read the bubble, turn it end for end; it should read the "
            "same.", "Level is horizontal, plumb is vertical: check walls and posts plumb on two faces.",
            "For a big square (a slab, a wall layout), use 3-4-5: 3 ft one way, 4 ft the other, and the diagonal "
            "between the marks is exactly 5 ft (or 6-8-10 for more accuracy)."),
            "Square, level and plumb are what make doors close, floors flat and roofs sit true.",
            ("A dropped level may no longer be true: check it.",)),
        Lesson("circular_saw", "The circular saw", (
            "Set the blade about 1/4 in deeper than the board is thick.",
            "Support the board so the offcut falls free and the kerf can't close on the blade.",
            "Cut on the waste side of the line, so the piece you keep is the right length.",
            "Stand to the side of the saw's path, let it reach full speed before it touches the wood, and keep the "
            "guard working."),
            "Set up right, a circular saw is accurate and safe; set up wrong, it kicks back.",
            ("Kickback comes from a pinched blade: never cut a board supported at both ends with the cut between.",
             "A dull blade burns and wanders.")),
    ), (
        Check("safety_said", "Tell MIA what to wear running a circular saw, and what to do before changing its blade",
              "said"),
        Check("ten_marks", "Measure and mark ten lengths MIA reads out, then check each with her, to 1/16 in",
              "counted", passes_at=10, unit="marks within 1/16 in"),
        Check("square_cuts", "Cut five boards to a line, each square (checked with a speed square)", "counted",
              passes_at=5, unit="square cuts"),
    )),
    Stage(2, "Layout and cutting", "laying work out square and cutting parts to a list", (
        Lesson("lumber", "Lumber: nominal sizes and the crown", (
            "A 2x4 is 1-1/2 by 3-1/2 in, a 2x6 is 1-1/2 by 5-1/2, a 2x8 is 1-1/2 by 7-1/4: the name is the rough "
            "size before drying and planing.", "Sight down each board's edge: the bow upward is its crown.",
            "Install joists and rafters crown up, and keep studs' crowns all facing one way.",
            "Use treated lumber where wood touches concrete or the ground, and fasteners rated for it."),
            "Plans are drawn in nominal sizes; cuts and layouts use the actual ones.",
            ("Setting a joist crown down: it sags more over time.",)),
        Lesson("chalk_layout", "Laying out with a chalk line and 3-4-5", (
            "Measure both ends of a line, hold the chalk line tight on the marks, lift it straight up and let it snap.",
            "Square a layout with 3-4-5, then check it by its diagonals: equal diagonals mean square.",
            "Mark which side of each line the part goes on (an X on that side)."),
            "Walls, slabs and decks are built on their layout lines: an error here is in everything after.",
            ("A chalk line snapped while bowed by the wind isn't straight.",)),
        Lesson("cut_list", "Cutting to a cut list", (
            "Work from a cut list: every part's size and count, longest first, so offcuts become the short parts.",
            "Clamp a stop block for repeated lengths so each one matches.",
            "Label each part as it's cut.", "Measure the first one and check it before cutting the rest."),
            "A cut list turns a plan into parts without waste or mistakes; stop blocks make them identical.",
            ("Measuring each repeat separately instead of using a stop block.",)),
    ), (
        Check("lumber_said", "Tell MIA the actual sizes of a 2x4, a 2x6 and a 2x8, and which way a joist's crown goes",
              "said"),
        Check("square_layout", "Lay out a rectangle at least 8 by 10 ft whose diagonals match within 1/8 in", "counted",
              passes_at=1, unit="square layouts"),
        Check("cut_list_done", "Cut a six-part cut list, each part within 1/16 in", "counted", passes_at=6,
              unit="parts to length"),
    )),
    Stage(3, "Framing basics", "framing a stud wall with an opening, square and plumb", (
        Lesson("wall_parts", "The parts of a framed wall", (
            "Bottom plate and double top plate; studs (usually 16 in on center).",
            "At an opening: king studs full height, jack (trimmer) studs carrying the header, cripples above and "
            "below, and a sill under a window.", "The header spans the opening and carries the load above it down "
            "through the jacks: its size comes from the code's header tables or an engineer."),
            "Knowing each part's job is how you know what you can and can't cut.",
            ("Never notch or drill a header, or a bearing stud beyond what the code allows.",)),
        Lesson("plate_layout", "Plate layout at 16 in on center", (
            "Tack the bottom and top plates together, edges flush.",
            "Hook the tape on the end and mark every 16 in, then mark the stud's edge 3/4 in back from each mark so "
            "the center lands on 16.", "Mark an X beside each line where the stud goes, and mark the kings, jacks and "
            "cripples at openings."), "Sheathing and drywall edges land on studs at 16 in centers; a drifting layout "
            "leaves them unsupported.", ("Restarting the measurement from each stud instead of from the end.",)),
        Lesson("build_raise", "Building and raising a wall", (
            "Lay the plates and studs out flat on the deck, crowns one way.",
            "Nail each stud through the plates (two 16d nails at each end, or per the code's fastening schedule).",
            "Square the wall by its diagonals before it's sheathed or raised.",
            "Raise it with help, set it on its line, plumb it on two faces, and brace it before letting go."),
            "Walls are built flat because it's faster and truer; they're braced because an unbraced wall falls.",
            ("Raising in wind, or without enough people for its weight.",)),
    ), (
        Check("parts_said", "Name every part of a framed door opening to MIA and say which carries the load", "said"),
        Check("practice_wall", "Frame a practice wall with a door opening, square within 1/8 in and plumb, and tell "
              "MIA", "said"),
        Check("layout_marks", "Lay out a 12 ft plate at 16 in on center, every mark within 1/16 in", "counted",
              passes_at=1, unit="plates laid out"),
    )),
)

PROGRAM = register(Program(
    "carpentry", "Carpentry apprentice", SKILL, "🪚", "From working safely and measuring to 1/16 in, through layout "
    "and cutting, to framing a wall: an apprentice's first steps, practised on real jobs.",
    ("carpentry", "carpenter", "framing", "woodworking basics", "apprentice"), STAGES, plan=(30, 3)))
