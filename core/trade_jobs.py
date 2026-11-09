"""
core.trade_jobs
=================

The jobs and diagnoses MIA walks someone through (DEC-0149, the content for core/trades.py): Zac's first four builds,
in his order (2026-11-08): a hoop-house greenhouse, a chicken coop, a workshop on a slab, and a cold room for the
harvest; and the first diagnosis, a toilet that keeps running. Each is written from its sources (named on it) to the
standard in core/trades.problems(), and stays DRAFTED until a person confirms it.

Quantities aren't written here: a job with a plan gets them from that plan's calculator (core/build_calcs.py). The
greenhouse and the cold room have no calculator yet; theirs are on core/trades.WANTED.
"""

from __future__ import annotations

from core.trades import DiagCheck, Diagnosis, Job, Phase, Step, register

_LOCAL = ("Codes, snow and wind loads, and permit rules vary by place: check with your local building department "
          "before you start.")

register(Job(
    "hoop_house", "carpentry", "build", "Hoop-house greenhouse (high tunnel)",
    "A ground-post hoop house: steel bows on driven ground posts, wood baseboards and hip boards, framed end walls with "
    "a door and vents, and greenhouse film. The site prep (level, drained) is in. Heating, electrical and irrigation "
    "are separate jobs.",
    ("hoop house", "high tunnel", "greenhouse", "hoophouse", "poly tunnel"),
    ("utilities", "weather", "fall", "injury"),
    "Many places treat a high tunnel as a temporary agricultural structure, but some count it as a building that "
    "needs a permit, or limit its size and setbacks. " + _LOCAL,
    ("wind lifting film or the whole frame before it's anchored", "driving posts into buried lines",
     "ladder falls while setting purlins and film", "pinch points while raising bows"),
    ("work gloves", "safety glasses", "hearing protection when driving posts"),
    ("tape measure (100 ft)", "string line and stakes", "transit or laser level", "post driver or sledge with driving cap",
     "drill/driver", "ladders (two)", "socket set", "circular saw", "staple gun or wiggle-wire channel tools"),
    ("ground posts and steel bows (from the kit or bent to the width)", "purlins and cross-connectors",
     "pressure-treated baseboards and hip boards", "end-wall framing lumber, a door and vent hardware",
     "greenhouse film (UV-stabilized, 4-year or better)", "wiggle-wire channel or batten strips",
     "anchors suited to the soil (augers or concrete)", "fasteners rated for treated lumber"),
    (
        Phase("Plan, site and permit", (
            Step("Choose the site: full sun, the long side running east-west where you can, away from trees and "
                 "buildings that shade it or drop snow and limbs on it, with water and a path for wheelbarrows.",
                 "A tunnel's whole value is light; shade and falling debris cost harvests and film.",
                 ("Watch the winter sun, not the summer sun: it's lower and shades more.",)),
            Step("Check the rules: the permit question, setbacks from lot lines, and whether the kit's rated snow and "
                 "wind loads meet your area's (your building department or the kit maker can say).",
                 "A frame rated below your snow load is the most common way tunnels collapse.",
                 ("Note the rated loads; they decide bow spacing.",), "The kit's rated loads meet or beat your area's."),
            Step("Call 811 (in the US) and wait for the utility marks before any post goes in.",
                 "Ground posts go 2 ft or more down: right where buried lines run.",
                 ("Private lines (a well, a septic field, power to a barn) aren't marked by 811: find them too.",),
                 "Every line near the footprint is marked."),
        )),
        Phase("Prepare the ground", (
            Step("Clear and level the footprint plus 2 ft all round; grade it so water runs away from the tunnel.",
                 "A level, drained base keeps posts true and the beds from flooding.",
                 ("Fill low spots with compacted soil, not loose topsoil.",)),
            Step("Lay out the rectangle with stakes and string, and square it: the two diagonals must match.",
                 "An out-of-square layout racks the bows and the film never pulls tight.",
                 ("Measure diagonals to the same corners of the stakes.",),
                 "The diagonals match within 1/2 in."),
        )),
        Phase("Set the posts and bows", (
            Step("Mark the post spacing along both string lines (usually 4 ft on center, closer in heavy snow areas, "
                 "per the kit).", "The spacing is what the frame's snow rating assumes.",
                 ("Start from the same end on both sides so the bows line up.",)),
            Step("Drive each ground post plumb to the kit's depth, tops all at one height (use the level line).",
                 "Bows that start at different heights twist the frame and stress the purlins.",
                 ("Check plumb on two faces as you drive.", "Stop if a post meets something hard you can't identify."),
                 "Every post is plumb, at depth, and its top is on the level line."),
            Step("Set the bows into the posts with a helper, fasten them, and check each bow's height and plumb.",
                 "Uneven bows make low spots where snow and water collect on the film.",
                 ("Never raise bows in wind.",)),
            Step("Install the ridge purlin and side purlins with their cross-connectors, then any diagonal bracing "
                 "at the corners.", "Purlins and braces stop the frame racking and spread snow load between bows.",
                 ("Tighten the connectors evenly; don't crush the tubing.",),
                 "The frame stands square and doesn't rack when pushed at a corner."),
        )),
        Phase("Baseboards, hip boards and end walls", (
            Step("Fasten treated baseboards to the posts at grade, and hip boards at the height the roll-up sides "
                 "will start.", "They anchor the film's edges and the side vents.",
                 ("Use fasteners rated for treated lumber.",)),
            Step("Frame both end walls plumb, with the door (wide enough for a cart) and a vent high in each end.",
                 "Cross-ventilation high in the ends is what keeps a tunnel from overheating.",
                 ("Brace the end-wall studs back to the first bow.",), "The end walls are plumb and the door swings free."),
            Step("Install the wiggle-wire channel (or batten strips) along the baseboards, hip boards, end bows and "
                 "door frame.", "The channel holds the film evenly; nails through film tear in the first wind.",
                 ("Round over or tape any sharp edge the film will touch.",)),
        )),
        Phase("Cover with film", (
            Step("Pick a calm morning; unroll the film beside the tunnel, the inside face (the label says) down.",
                 "Film goes on in calm air or not at all: a sheet that size becomes a sail.",
                 ("Have at least three people for a tunnel over 20 ft.",)),
            Step("Pull the film over the bows, center it, and lock it into the end-wall channels first, then the "
                 "sides, working out from the middle.", "Working from the middle keeps the tension even and the "
                 "wrinkles out.", ("Warm film stretches tighter; cold film sags later.",),
                 "The film is drum-tight with no folds over a bow."),
            Step("Fit the roll-up side curtains and the end-wall film, and set the vents and door.",
                 "These are how heat and humidity leave.", ("Check the curtains roll all the way up and down.",)),
        )),
        Phase("Anchor and final inspection", (
            Step("Anchor the frame per the kit (augers, or posts set in concrete where the soil is soft) at every "
                 "corner and along the sides.", "Wind uplift, not snow, takes most tunnels.",
                 ("Anchors go into undisturbed soil.",), "Every anchor the kit calls for is in and tight."),
            Step("Walk the whole tunnel: fasteners, connectors, film tension, channels, door and vents, and nothing "
                 "sharp touching film.", "A loose part found now is a torn sheet found later.",
                 (), "Everything on the walk is tight and right."),
            Step("Write down how to vent it (open the sides above about 80 F, close them before dusk in cold "
                 "weather) and when to clear snow (before it builds past what the frame is rated for).",
                 "Most tunnel losses come from not venting or not clearing snow.", ()),
        )),
    ),
    ("USDA Natural Resources Conservation Service, Conservation Practice Standard 325, High Tunnel System",
     "Eliot Coleman, The Winter Harvest Handbook (Chelsea Green, 2009)",
     "The tunnel kit's own assembly instructions and its rated snow and wind loads",
     "International Code Council, International Residential Code (IRC) 2021, Section R301.2 (climatic design criteria)"),
    skill="Construction",
))

register(Job(
    "chicken_coop", "carpentry", "build", "Chicken coop and run",
    "A shed-roof coop on a framed floor, with a people door and a pop door, a roost, nest boxes and vents, and a run "
    "wrapped in 1/2 in hardware cloth. Sizes and quantities come from the coop plan (4 sq ft a hen inside, 10 in the "
    "run). Power and water lines are separate jobs.",
    ("chicken coop", "coop", "hen house", "chicken run", "henhouse"),
    ("utilities", "fall", "injury"),
    "A coop is usually a small accessory building; many places exempt one under 200 sq ft, but zoning may limit "
    "hens, setbacks and roosters. " + _LOCAL,
    ("saw and nail-gun injuries", "cut wire edges", "lifting walls and the roof"),
    ("safety glasses", "work gloves (for hardware cloth)", "hearing protection"),
    ("circular saw", "drill/driver", "speed square and framing square", "level (4 ft)", "tape measure",
     "tin snips", "staple gun or fence stapler", "shovel (for the apron)"),
    ("2x4 framing lumber (treated for the floor frame)", "3/4 in plywood floor", "T1-11 or plywood siding",
     "metal roof panels and screws with washers", "1/2 in hardware cloth (never chicken wire)", "hinges and "
     "two-step latches", "concrete blocks or treated skids", "vent covers with hardware cloth"),
    (
        Phase("Plan, site and permit", (
            Step("Size it for the flock with the coop plan (4 sq ft a hen inside, 10 in the run), and check how many "
                 "hens your zoning allows.", "Crowding is the root of pecking, disease and poor laying.",
                 ("Plan for the flock you'll have, not the one you start with.",)),
            Step("Choose high, well-drained ground with afternoon shade and the door away from the prevailing "
                 "winter wind; leave room to walk all round it to clean.",
                 "Wet ground breeds disease; a cold draft at roost height chills birds.",
                 ("Check the setback from lot lines and the neighbors.",),
                 "The site drains and the setbacks are met."),
            Step("Call 811 before setting blocks or digging the run apron.",
                 "The apron trench runs right through where lines are buried.", (), "The lines are marked."),
        )),
        Phase("Foundation and floor", (
            Step("Set level concrete blocks (or treated skids on gravel) at the corners and midspans.",
                 "A level base keeps the frame square and the doors closing.",
                 ("Check level across and diagonally.",), "The blocks are level to each other."),
            Step("Build the floor frame from treated 2x4s (joists at 16 in), check its diagonals, then glue and "
                 "screw the plywood floor.", "A square floor is the base every wall is built true on.",
                 ("Crown every joist up.",), "The floor's diagonals match within 1/4 in."),
        )),
        Phase("Walls, roof and openings", (
            Step("Frame the walls flat on the floor (studs at 24 in), with the people door, the pop door and window "
                 "openings framed with headers, then stand and brace them.",
                 "Framed openings keep doors from sagging and racking.",
                 ("The back wall is a foot lower than the front for the shed roof.",),
                 "Each wall is plumb and the corners are square."),
            Step("Set the rafters at 24 in with a 12 in overhang, then the metal roof panels, screwed through the "
                 "ribs into purlins or rafters.", "The overhang keeps rain off the walls and out of the vents.",
                 ("Screws snug, not crushing the washers.", "Work from a stable ladder, never the walls."),
                 "The roof sheds water with no gaps at the ridge or the eaves."),
            Step("Side it, and cut vents high on both sides (about 1 sq ft for every 10 birds), covered with "
                 "hardware cloth.", "Ammonia and moisture rise: high vents clear them without a draft on the roost.",
                 ("Vents above the roost height, not beside it.",)),
        )),
        Phase("Predator-proofing and the run", (
            Step("Frame the run and wrap it in 1/2 in hardware cloth, fastened every few inches with washers or "
                 "battens.", "Raccoons tear through chicken wire; hardware cloth stops them.",
                 ("Overlap seams at least 2 in.",)),
            Step("Bury an apron: hardware cloth 12 in down, or laid 2 ft out flat and pinned, all round the run.",
                 "Diggers (foxes, dogs) go under, not through.", (), "No gap anywhere along the base."),
            Step("Fit two-step latches on every door and the pop door.",
                 "Raccoons open one-step latches.", ("Test each latch from outside.",), "Every opening latches."),
        )),
        Phase("Fit out and final inspection", (
            Step("Install the roost (wide face up, 10 in a hen, higher than the nest boxes) and the nest boxes (one "
                 "per 4 hens, about 12 in cubes, dark and low).",
                 "Hens roost on the highest perch: a nest box higher than the roost gets slept in and dirtied.",
                 ("Roosts at least 12 in from the wall.",)),
            Step("Walk the coop at dusk with a light: any gap bigger than 1/2 in, any loose wire, any latch that "
                 "gives.", "Predators find what you miss, on the first night.", (),
                 "No gap, loose wire or weak latch is left."),
        )),
    ),
    ("Gail Damerow, Storey's Guide to Raising Chickens, 4th ed. (Storey, 2017)",
     "Gail Damerow, Building Chicken Coops (Storey Country Wisdom Bulletin)",
     "MIA's coop plan and calculator (core/build_calcs.chicken_coop, core/plan_library.py)"),
    plan="chicken-coop",
))

register(Job(
    "workshop", "carpentry", "build", "Workshop on a concrete slab",
    "A gable-roofed workshop framed on a concrete slab: the permit, layout, the slab (forms, base, reinforcement, pour, "
    "cure), stud walls with a header over the door, rafters, sheathing, underlayment and shingles, and siding. The "
    "slab's quantities come from the slab plan and the walls' and roof's from the gable-shed plan. Wiring is its own "
    "job.",
    ("workshop", "shop building", "work shop", "shop on a slab", "garage shop"),
    ("utilities", "structural", "fall", "weather", "injury"),
    "A workshop over 200 sq ft (or any with power) almost always needs a permit, with inspections of the footing or "
    "slab forms before the pour and of the framing. " + _LOCAL,
    ("concrete burns (wet cement is alkaline)", "silica dust cutting concrete", "falls from the roof and ladders",
     "raising walls", "saw injuries"),
    ("safety glasses", "waterproof gloves and boots for the pour", "hearing protection", "fall protection on the roof",
     "a respirator for cutting concrete"),
    ("transit or laser level", "string line and batter boards", "circular saw", "framing nailer and compressor",
     "framing square and speed square", "4 ft and 6 ft levels", "screed board, bull float, edger and groover",
     "wheelbarrow and shovels", "ladders and roof brackets"),
    ("form boards and stakes", "compactable gravel base", "vapor retarder (10 mil)", "rebar or wire mesh and chairs",
     "ready-mix concrete (strength per your code) or bagged mix", "anchor bolts or straps", "treated sill plates",
     "framing lumber, headers and rafters", "roof sheathing, underlayment, drip edge and shingles", "siding"),
    (
        Phase("Plan and permit", (
            Step("Draw the footprint, door and windows, and the roof pitch; get the permit and ask which "
                 "inspections are required.", "The inspector checks the forms before the pour: you can't fix a slab "
                 "after it's placed.", ("Ask what concrete strength and slab edge your area requires.",),
                 "The permit is in hand and you know each inspection."),
            Step("Call 811 and wait for the marks.", "The slab, its thickened edge and any trench for power sit "
                 "right on top of buried lines.", (), "Every line is marked."),
        )),
        Phase("Layout and slab", (
            Step("Set batter boards and string the outline; square it with the diagonals.",
                 "Every wall sits on this rectangle.", ("Re-check after the strings are tight.",),
                 "The diagonals match within 1/4 in."),
            Step("Excavate to the depth for gravel plus slab (and the thickened edge your code calls for), "
                 "on undisturbed soil.", "Soft or filled soil settles and cracks the slab.",
                 ("Soft spots: dig out and replace with compacted gravel.",)),
            Step("Set the forms level and square, place 4 in or more of compacted gravel, the vapor retarder, and "
                 "the reinforcement on chairs so it ends up in the middle of the slab.",
                 "Reinforcement lying on the ground does nothing.", ("Lap mesh and rebar per the plan.",),
                 "The forms are level and square, and the inspector has passed them if required."),
            Step("Pour, screed, bull float, then edge and cut control joints (no more than about 2 to 3 times the "
                 "slab's thickness in feet apart); set anchor bolts while it's wet.",
                 "Joints decide where it cracks; anchors tie the walls down.",
                 ("Don't add water to make it easier to place.", "Don't finish while bleed water is on the "
                  "surface."), "The anchor bolts are where the sill plates will go."),
            Step("Cure it moist for at least 7 days (wet burlap, plastic or curing compound) before framing on it.",
                 "Concrete gains strength by curing, not drying.", ("Protect it from freezing.",)),
        )),
        Phase("Walls", (
            Step("Snap the wall lines; lay out treated sill plates on the anchors with a sill seal under them.",
                 "Treated plates resist the moisture concrete holds.", ()),
            Step("Frame each wall flat: studs at 16 in, the header over the door sized for its span (from your "
                 "code's header table), then stand, plumb and brace it.",
                 "The header carries the roof over the opening.", ("Crown the studs the same way.",),
                 "Every wall is plumb and braced, and the corners are square."),
            Step("Add the double top plate with its joints offset, and sheath the walls if the plan calls for it.",
                 "The double plate ties the walls together and carries the rafters between studs.", ()),
        )),
        Phase("Roof", (
            Step("Cut a pattern rafter, test it at both ends, then cut the rest; set the ridge and the rafters at "
                 "24 in with the ties or ceiling joists your code requires.",
                 "Ties keep the rafters from pushing the walls out.", ("Never work on the roof alone.",),
                 "The ridge is straight and level and the rafters sit tight on the plates."),
            Step("Sheath the roof (staggered seams, clips between rafters if called for), then drip edge, "
                 "underlayment and shingles per the shingle maker's instructions.",
                 "The maker's nailing pattern is what its wind rating depends on.",
                 ("Fall protection on any pitch you can't stand on comfortably.",),
                 "The roof is dry-in: no exposed sheathing, the drip edge on every edge."),
        )),
        Phase("Close in and final inspection", (
            Step("Side the walls over the weather barrier, with flashing over the door and windows.",
                 "Water gets in at openings, not through the field.", ()),
            Step("Call for the final inspection if your permit has one; walk the building for loose fasteners, "
                 "gaps, and water paths.", "The inspection is what makes it legal; the walk is what makes it last.",
                 (), "The final inspection passed (or isn't required) and the walk found nothing left."),
        )),
    ),
    ("International Code Council, International Residential Code (IRC) 2021: R105 (permits), R403 (footings), "
     "R506 (concrete floors on ground), R602 (wall framing), R802 (roof framing), R905.2 (asphalt shingles)",
     "American Concrete Institute, ACI 302.1R, Guide to Concrete Floor and Slab Construction",
     "Portland Cement Association, Design and Control of Concrete Mixtures, 17th ed.",
     "OSHA 29 CFR 1926 Subpart M, Fall Protection",
     "MIA's slab and gable-shed plans and calculators (core/build_calcs.py)"),
    plan="shed-slab",
))

register(Job(
    "cold_room", "carpentry", "build", "Cold room for the harvest (an insulated walk-in cooler)",
    "A walk-in cold room framed inside a dry building (the workshop, a barn): insulated walls, ceiling and floor, a "
    "sealed vapor retarder on the warm side, a tight insulated door, and a window air conditioner run cold by a "
    "controller (CoolBot or similar). Its dedicated circuit is its own job and may need a permit and an electrician.",
    ("cold room", "cold storage", "walk-in cooler", "walk in cooler", "coolbot", "produce cooler"),
    ("live_power", "hazmat", "injury"),
    "Building a room inside an existing building may need a permit, and its new circuit almost always does. " + _LOCAL,
    ("cutting foam board (dust) and spray foam fumes", "saw injuries", "the electrical connection",
     "condensation and mold if the vapor retarder leaks"),
    ("safety glasses", "a respirator or dust mask for foam and spray foam", "gloves"),
    ("circular saw and a long blade or insulation knife", "drill/driver", "level and square", "tape measure",
     "caulk gun and spray-foam gun", "foil tape roller"),
    ("framing lumber (2x6 walls for the insulation depth)", "rigid foam board (polyiso or XPS) to R-25 walls and "
     "R-30 ceiling or better", "spray foam and foil tape for every seam", "a 6 mil poly or foil vapor retarder",
     "plywood or washable panels for the inside", "an insulated door and gaskets", "a window air conditioner sized "
     "for the room", "a cooler controller (CoolBot or similar) and its temperature sensor"),
    (
        Phase("Plan and prepare", (
            Step("Size the room for the harvest you store (about 1 cubic ft holds 20 to 30 lb of produce), and pick a "
                 "spot out of the sun with a dry, level floor and a place for the air conditioner to exhaust heat.",
                 "The air conditioner must throw its heat outside the room and the building can't trap it.",
                 ("Leave room to walk and to stack crates on pallets.",)),
            Step("Choose the target: most roots and greens keep best near 32 to 40 F and very humid; some crops "
                 "(potatoes, squash, onions) want warmer or drier storage, so plan a second spot for those.",
                 "Storing a crop at the wrong temperature ruins it faster than not cooling it.",
                 ("Check each crop's storage temperature before you put it in.",)),
            Step("In a building built before 1980, have any material you'll cut or remove tested for asbestos and lead.",
                 "Old floor tile, insulation and paint can carry both.", (), "Tested, or the building is newer."),
        )),
        Phase("Frame and insulate", (
            Step("Frame the walls and ceiling plumb and square, with the door opening framed and a framed hole for "
                 "the air conditioner high on the wall.", "Cold air falls: a high air conditioner cools the whole room.",
                 ("Frame the opening to the unit's exact size.",), "The framing is plumb and the openings are square."),
            Step("Insulate the floor with rigid foam under a plywood floor (or over a dry slab), then the walls and "
                 "ceiling in layers with their seams staggered.", "Staggered seams stop the gaps that frost forms in.",
                 ("Don't compress the foam.",)),
            Step("Tape every foam seam and fill every gap with spray foam, then hang the vapor retarder on the warm "
                 "(outside) face, lapped and taped.", "Warm moist air reaching cold surfaces turns to water and mold "
                 "inside the walls.", ("Seal around every fastener and the air conditioner opening.",),
                 "No seam, gap or tear is left open on the warm side."),
        )),
        Phase("Door, cooling and controls", (
            Step("Hang the insulated door with gaskets on all four sides and a latch that pulls it tight.",
                 "The door is the biggest leak in any cold room.", ("Check with a light from inside, lights off.",),
                 "No light shows round the door."),
            Step("Set the air conditioner in its opening, sealed all round, and fit the controller and its sensors "
                 "per the controller's instructions.", "The controller keeps the unit running below the temperature "
                 "a window unit normally stops at.", ("Its fin sensor must touch the fins as shown.",)),
            Step("Power it from its own circuit (a separate job): never an extension cord.",
                 "An air conditioner on a shared or extension cord overheats wiring.", (),
                 "A dedicated circuit is in and passed (or a permitted electrician did it)."),
        )),
        Phase("Test and final check", (
            Step("Run it empty for two days: log the room's temperature morning and evening, and look for frost or "
                 "sweating anywhere on the walls.", "A cold spot or sweat line marks a gap in the insulation or seal.",
                 ("Frost on the coil means the controller's setting or sensor needs adjusting.",),
                 "It holds the target temperature with no sweating."),
            Step("Add a thermometer you can read from outside and a hygrometer; keep produce off the floor on "
                 "pallets or slatted shelves.", "Air must move round the crates to cool them.", ()),
            Step("Load it a little at a time, and cool the harvest first where you can (in the shade, or rinsed in "
                 "cold water): a room full of warm produce at once overwhelms a small air conditioner.",
                 "Field heat is most of what a cooler has to remove; a small unit cools a full load slowly.",
                 ("Watch the temperature for a day after each big load.",)),
        )),
    ),
    ("Store It Cold, CoolBot owner's manual and installation instructions",
     "USDA Agriculture Handbook 66, The Commercial Storage of Fruits, Vegetables, and Florist and Nursery Stocks",
     "ASHRAE Handbook, Refrigeration (storage of fruits and vegetables)",
     "Mike and Nancy Bubel, Root Cellaring (Storey, 1991)"),
))

register(Diagnosis(
    "toilet_running", "plumbing", "A toilet that keeps running",
    ("toilet keeps running", "toilet running", "running toilet", "toilet won't stop", "toilet hisses",
     "toilet refills by itself"),
    ("injury",),
    "Nothing here is dangerous, but shut the water off at the valve behind the toilet before taking anything apart, "
    "and lift the tank lid carefully: it's heavy and breaks easily.",
    "dye",
    (
        DiagCheck("dye", "Put a few drops of food coloring in the tank (not the bowl) and wait 15 minutes without "
                  "flushing. Does color show up in the bowl?",
                  "It shows whether water leaks past the flapper, the most common cause, without taking anything "
                  "apart.", "flapper_seat", "overflow"),
        DiagCheck("flapper_seat", "Shut the water off, flush, and look at the flapper and the drain seat it closes on. "
                  "Is the flapper warped, cracked, slimy or stiff, or the seat rough?",
                  "A worn flapper or a pitted seat lets the tank leak into the bowl and refill over and over.",
                  "cause:the flapper (or its seat) is worn: replace the flapper with one that matches the flush "
                  "valve's size (2 or 3 in); a pitted seat takes a seat repair kit|", "chain"),
        DiagCheck("chain", "Is the flapper chain so short it holds the flapper open, or so long it catches under it?",
                  "A chain with the wrong slack keeps the flapper from seating even when the flapper is fine.",
                  "cause:the chain length: leave about 1/2 in of slack with the flapper closed|",
                  "pro:a plumber, if the flapper, seat and chain are all good and the bowl still takes dye; say the "
                  "flush valve may be cracked or its gasket leaking"),
        DiagCheck("overflow", "Turn the water back on and let the tank fill. Does the water rise above the top of the "
                  "overflow tube and run down it?",
                  "Water pouring into the overflow means the fill valve doesn't shut off at the right level.",
                  "float", "fill_valve"),
        DiagCheck("float", "Lower the float (the adjustment screw or clip on the fill valve) so the water stops about "
                  "1 in below the top of the overflow tube. Does it shut off there now?",
                  "A float set too high is the simplest fill-side fault.",
                  "cause:the float was set too high: keep it about 1 in below the overflow|",
                  "fill_valve"),
        DiagCheck("fill_valve", "With the water on, does the fill valve keep hissing or dripping after the tank is "
                  "full, or cycle on by itself every so often?",
                  "A fill valve that won't seal (worn seal, grit in it) runs even when the level is right.",
                  "cause:the fill valve is worn: flush the grit out or replace its seal, or replace the fill valve "
                  "(about 15 minutes, a universal one fits most toilets)|",
                  "pro:a plumber; say the tank runs with the flapper, chain, float and fill valve checked"),
    ),
    ("Fluidmaster, 400A fill valve and flapper installation and troubleshooting instructions",
     "Kohler and American Standard toilet repair guides (fill valve and flush valve)"),
))
