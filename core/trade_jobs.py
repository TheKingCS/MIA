"""
core.trade_jobs
=================

The jobs and diagnoses MIA walks someone through (DEC-0149, the content for core/trades.py), in the order of
core/trades.WANTED. First Zac's four builds (2026-11-08): a hoop-house greenhouse, a chicken coop, a workshop on a slab
and a cold room for the harvest; then the aquaponics pilot's three jobs (DEC-0150), the workshop circuit and a root
cellar; then all of home building, in the order a house goes up: site layout, footings, slab, foundation wall, floor,
walls and roof framing, sheathing and dry-in, shingles or metal, windows and doors, house wrap and flashing, siding,
insulation, air sealing, drywall, trim, paint, flooring and tile, the plumbing and electrical rough-ins and finishes, a
water heater, ductwork, a mini-split, a deck, stairs and gutters. Then the second tier (2026-11-09): everyday jobs (a
ceiling fan, a vanity, cabinets, a shower, exterior paint, a fence, attic ventilation, a sump pump, a retaining wall,
replacement windows, a garage door opener), and the third (a drywall patch, a toilet, a receptacle or switch,
recaulking, weatherstripping), and the fourth (the plans shelf's builds as jobs: a raised bed, a gable shed,
a compost bin, a cold frame, a lean-to, garage shelving, a workbench, a firewood rack), and the fifth (the land and its water: a French drain, a
gravel driveway, a rain barrel, shocking a well, septic care, an electric fence), and the sixth (a feeder and
subpanel for the workshop). The diagnoses are worked as checks: a running toilet, a tripping breaker, no
hot water, AC that doesn't cool, a dryer that doesn't heat, a roof leak, a furnace that won't heat, a clogged drain, a
leaky faucet, a GFCI that won't reset, a frozen pipe, low water pressure, a chirping alarm, a jammed disposal, a sump
pump, a garage door, a leaking water heater, a clogged toilet, a dishwasher or washer that won't drain, a
warm fridge, a well with no water, ice dams, bathroom mold, a sticking door and a squeaky floor.

Each is written from its sources (named on it) to the standard in core/trades.problems(), and stays DRAFTED until a
person confirms it. Licensed work follows Zac's answer (B): an electrical, plumbing or HVAC job says a homeowner does it
only under a permit that allows it, and names the part that is always a licensed trade's (gas piping, refrigerant).

Quantities aren't written here: a job with a plan gets them from that plan's calculator (core/build_calcs.py).
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
     "International Code Council, International Residential Code (IRC) 2021, Section R301.2 (climatic design criteria)",
     "MIA's hoop-house plan and calculator (core/build_calcs.py)"),
    plan="hoop-house",
    skill="carpentry",
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
     "Mike and Nancy Bubel, Root Cellaring (Storey, 1991)",
     "MIA's cold-room plan and calculator (core/build_calcs.py)"),
    plan="cold-room",
    skill="carpentry",
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

register(Diagnosis(
    "breaker_tripping", "electrical", "A breaker that keeps tripping",
    ("breaker keeps tripping", "breaker trips", "tripping breaker", "breaker tripped", "breaker keeps going off",
     "circuit keeps tripping"),
    ("live_power", "injury"),
    "Never take the panel cover off, and reset a breaker no more than once or twice: a breaker that trips again is "
    "protecting the wiring. A hot, buzzing or scorched breaker, or a burning smell, means leave it off and call a "
    "licensed electrician now.",
    "empty",
    (
        DiagCheck("empty", "Unplug or switch off everything on that circuit, then reset the breaker. Does it trip again "
                  "right away, with nothing running?",
                  "A breaker that trips with nothing on it points at the wiring or the breaker, not what's plugged in.",
                  "pro:a licensed electrician; say the breaker trips with nothing plugged in or switched on (a short "
                  "or ground fault in the wiring, or a failed breaker)", "load"),
        DiagCheck("load", "Plug things back in one at a time. Does it trip when one appliance runs, or when several "
                  "heavy ones run at once (a space heater, a microwave, a hair dryer, a vacuum)?",
                  "Most nuisance trips are an overloaded circuit or one faulty appliance.", "which", "gfci"),
        DiagCheck("which", "Plug that appliance into a different circuit. Does that one trip too, or does the "
                  "appliance spark, smell hot, or have a damaged cord?",
                  "An appliance that trips any circuit is the fault; one that only trips this circuit means too much "
                  "on it.",
                  "cause:the appliance has a fault: stop using it and have it repaired or replaced|",
                  "cause:the circuit is overloaded: move heavy appliances to other circuits; one that often needs more "
                  "needs a new circuit from a licensed electrician, never a bigger breaker|"),
        DiagCheck("gfci", "Is it a GFCI or AFCI breaker (it has a TEST button), or does the circuit feed a bathroom, "
                  "kitchen, garage or outdoor outlet?",
                  "Ground-fault and arc-fault breakers trip on moisture and wiring faults, not only on load.",
                  "moisture", "warm"),
        DiagCheck("moisture", "Does it trip after rain, in damp weather, or when an outdoor or bathroom outlet gets wet?",
                  "Water in an outlet box or a cord's plug is the most common cause of ground-fault trips.",
                  "cause:moisture in an outdoor or damp-location outlet, box or cord: dry it and fit an in-use "
                  "(bubble) cover; a box that stays wet needs repair by a licensed electrician|",
                  "pro:a licensed electrician; say a GFCI or AFCI breaker trips with no load or moisture pattern "
                  "(a ground fault, an arc fault in the wiring, or a failing breaker)"),
        DiagCheck("warm", "Without opening anything, is the breaker warm to the touch, buzzing, or scorched, or does "
                  "the panel smell of burning?",
                  "Heat at a breaker means a loose connection or a failing breaker: a fire risk.",
                  "pro:a licensed electrician right away; leave the breaker off and say it's hot, buzzing or scorched",
                  "pro:a licensed electrician; say the breaker trips at random with normal loads (a loose connection "
                  "or a weak breaker)"),
    ),
    ("NFPA 70, National Electrical Code (NEC) 2023: Article 240 (overcurrent protection), 210.8 (GFCI) and 210.12 "
     "(AFCI)", "Electrical Safety Foundation International (ESFi), circuit breaker and home electrical safety guidance"),
))

register(Diagnosis(
    "no_hot_water", "plumbing", "No hot water",
    ("no hot water", "water heater not working", "water heater isn't working", "hot water is out",
     "water won't get hot", "only cold water"),
    ("gas", "live_power", "injury"),
    "If you smell gas, stop: leave and call the gas utility from outside. Switch an electric heater off at its breaker "
    "before opening any panel on it. Hot water and the relief valve can scald: keep clear of the valve's pipe.",
    "kind",
    (
        DiagCheck("kind", "Is the water heater electric (no gas line or flame, a heavy cable at the top)?",
                  "Electric and gas heaters fail in different places, so the checks split here.",
                  "elec_breaker", "gas_pilot"),
        DiagCheck("elec_breaker", "Is its breaker (usually a double 30 amp) off or tripped?",
                  "No power is the simplest cause, and a tripped breaker says something drew too much.",
                  "cause:the breaker was off or tripped: reset it once; if it trips again, leave it off and call a "
                  "licensed plumber or electrician|", "elec_reset"),
        DiagCheck("elec_reset", "With the breaker OFF, take off the upper access panel and fold back the insulation. "
                  "Is the red reset button (the high-limit) popped out?",
                  "The high-limit cuts power when the water gets too hot, usually from a failing thermostat.",
                  "cause:the high-limit tripped: press it in, close up and restore power; if it trips again, a "
                  "thermostat or element is failing and needs testing|",
                  "pro:a plumber or appliance technician; say an electric heater with power and its reset in still "
                  "makes no hot water (likely an element or thermostat, tested with a meter)"),
        DiagCheck("gas_pilot", "Look through the sight window at the bottom. Is the pilot (or the burner) out?",
                  "A pilot that's gone out is the most common gas heater fault.", "relight", "gas_supply"),
        DiagCheck("relight", "Follow the lighting instructions on the heater's label exactly. Does the pilot light "
                  "and stay lit after you let go of the control knob?",
                  "A pilot that lights but goes out when released usually means the thermocouple has failed.",
                  "cause:the pilot had gone out: it's relit; if it goes out again, the thermocouple or flame sensor "
                  "is likely failing|",
                  "pro:a licensed plumber or gas technician; say the pilot won't stay lit (likely the thermocouple, "
                  "or a gas supply or venting problem)"),
        DiagCheck("gas_supply", "The pilot is lit: is the gas valve to the heater open (handle in line with the pipe), "
                  "and do your other gas appliances work?",
                  "With the pilot lit but no heat, the gas control or thermostat is next, after the supply.",
                  "pro:a licensed plumber or gas technician; say the pilot is lit and gas is on but the water doesn't "
                  "heat (a gas control valve, thermostat or venting problem)",
                  "pro:the gas utility or a licensed plumber; say the gas supply to the heater (or the house) is off "
                  "or not working"),
    ),
    ("U.S. Department of Energy, Energy Saver: storage water heaters", "The water heater's own use and care manual "
     "(lighting instructions on its label)"),
))

register(Diagnosis(
    "ac_not_cooling", "hvac", "Air conditioning that runs but doesn't cool",
    ("ac not cooling", "ac isn't cooling", "ac won't cool", "air conditioner not cooling", "ac blowing warm",
     "air conditioning isn't cooling", "ac blowing hot air", "blowing warm",
     "blowing hot air", "ac is blowing", "ac isn't cold", "air conditioner isn't cooling"),
    ("live_power", "injury"),
    "Switch the outdoor unit off at its disconnect (and the breaker) before touching it: its capacitor holds a charge "
    "even then, so leave the electrical parts to a technician. Never open the refrigerant lines; that work needs a "
    "certified technician.",
    "thermostat",
    (
        DiagCheck("thermostat", "Is the thermostat set to Cool, a few degrees below the room, with fresh batteries?",
                  "A setting or a dead battery is the cheapest thing to rule out first.", "airflow",
                  "cause:the thermostat's setting or batteries: set it to Cool below the room temperature and fit new "
                  "batteries|"),
        DiagCheck("airflow", "Is air blowing from the vents?",
                  "No airflow points indoors (the blower); weak cool air points at the filter or the outdoor unit.",
                  "filter", "pro:an HVAC technician; say the system is on but no air moves from the vents (the blower "
                  "motor, its capacitor or the control board), after checking the indoor unit's switch and breaker"),
        DiagCheck("filter", "Pull the air filter: is it dirty or clogged, or is there ice on the refrigerant lines?",
                  "A clogged filter starves the coil of air until it freezes and stops cooling.",
                  "cause:a clogged filter (and possibly a frozen coil): replace the filter, and if there's ice, run "
                  "the fan only with cooling off until it melts|", "outdoor"),
        DiagCheck("outdoor", "Go to the outdoor unit: is its fan spinning and its compressor humming?",
                  "If the outdoor unit isn't running, the house moves air but nothing removes its heat.",
                  "coil", "outdoor_power"),
        DiagCheck("outdoor_power", "Is the outdoor unit's breaker tripped or its disconnect switched off?",
                  "Power to the outdoor unit is separate from the indoor one.",
                  "cause:the outdoor unit's power was off or tripped: reset it once; if it trips again, call an HVAC "
                  "technician|", "pro:an HVAC technician; say the outdoor unit doesn't start with power on (often a "
                  "failed capacitor or contactor, which hold a charge)"),
        DiagCheck("coil", "With the power off at the disconnect, is the outdoor coil packed with dirt, leaves or "
                  "cottonwood, or crowded by plants?",
                  "A blocked condenser coil can't shed heat, so the system runs without cooling.",
                  "cause:a dirty condenser coil: with the power off, rinse it gently from the inside out with a garden "
                  "hose, and clear 2 ft around the unit|",
                  "pro:an HVAC technician; say it runs and the coil is clean but it doesn't cool (often low refrigerant "
                  "from a leak, which needs a certified technician)"),
    ),
    ("U.S. Department of Energy, Energy Saver: maintaining your air conditioner",
     "U.S. EPA, Section 608 of the Clean Air Act (refrigerant handling by certified technicians)",
     "Air Conditioning Contractors of America (ACCA), homeowner maintenance guidance"),
))

register(Diagnosis(
    "dryer_no_heat", "appliances", "A dryer that runs but doesn't heat",
    ("dryer won't heat", "dryer not heating", "dryer isn't heating", "dryer no heat", "dryer doesn't heat",
     "dryer runs but no heat", "clothes won't dry"),
    ("live_power", "gas", "injury"),
    "Unplug the dryer (or switch off its breaker) before opening it: an electric dryer runs on 240 volts. A gas dryer "
    "follows the gas rule: a smell of gas means stop and leave. Lint is a fire risk, so clean it out as you go.",
    "fuel",
    (
        DiagCheck("fuel", "Is it a gas dryer (a gas line to the back)?",
                  "Gas and electric dryers heat differently, so the parts to check differ.",
                  "pro:an appliance technician experienced with gas; say a gas dryer runs but doesn't heat (igniter, "
                  "gas valve coils or flame sensor)", "breaker"),
        DiagCheck("breaker", "An electric dryer needs both halves of its double breaker. Switch it fully off and back "
                  "on: does it heat now?",
                  "Half a double breaker turns the drum but not the heater, the most common no-heat cause.",
                  "cause:a half-tripped double breaker: it heats now; if it trips again, call a licensed "
                  "electrician|", "vent"),
        DiagCheck("vent", "With it running, go outside: is the exhaust weak, or the vent hood or duct full of lint?",
                  "A blocked vent overheats the dryer until its safety fuse cuts the heat (and risks a fire).",
                  "cause:a clogged vent: clean the whole duct and hood, then check the thermal fuse, which a blocked "
                  "vent usually blows|", "fuse"),
        DiagCheck("fuse", "Unplugged, with the back panel off: does the thermal fuse (on the exhaust duct) show no "
                  "continuity on a multimeter?",
                  "A blown thermal fuse cuts the heat to protect against overheating.",
                  "cause:a blown thermal fuse: replace it with the model's part, after cleaning the vent|", "element"),
        DiagCheck("element", "Still unplugged: does the heating element show no continuity across its terminals?",
                  "A broken element coil is the next most common failure.",
                  "cause:a broken heating element: replace it with the model's part|",
                  "pro:an appliance technician; say the breaker, vent, thermal fuse and element test good (next are "
                  "the cycling thermostat, high-limit, and the timer or control board)"),
    ),
    ("U.S. Fire Administration, Clothes dryer fire safety", "The dryer maker's service manual and wiring diagram "
     "(the sheet inside the back panel)"),
))

register(Diagnosis(
    "roof_leak", "exterior", "A roof leak",
    ("roof leak", "roof is leaking", "leaking roof", "roof leaks", "water through the ceiling", "ceiling stain",
     "water coming through the ceiling"),
    ("fall", "weather", "injury"),
    "Look from the attic and the ground first, and stay off a wet, icy or steep roof: roof work needs fall protection "
    "and a second person. Keep water away from light fixtures and wiring below the leak.",
    "attic",
    (
        DiagCheck("attic", "In the attic with a light, during or right after rain: can you find wet wood, stains or "
                  "drips?",
                  "Water travels along rafters before it shows on a ceiling, so the attic shows where it really "
                  "enters.", "trace", "not_roof"),
        DiagCheck("trace", "Follow the wet trail uphill to where it starts: is it at something through the roof (a "
                  "plumbing vent, a chimney, a skylight, a roof vent)?",
                  "Penetrations are where most roof leaks begin.", "boot", "valley"),
        DiagCheck("boot", "Is the rubber boot round a vent pipe cracked, or the flashing round a chimney or skylight "
                  "lifted or its sealant gone?",
                  "Boots and flashing age faster than the shingles around them.",
                  "cause:a failed boot or flashing at a penetration: replace the boot or reflash it (sealant alone is "
                  "a stopgap); chimney step and counter flashing is often a roofer's job|",
                  "pro:a roofer; say water enters at a penetration whose boot and flashing look sound"),
        DiagCheck("valley", "Is it in a valley, where the roof meets a wall, or at the eaves in winter (ice dams)?",
                  "Valleys, wall flashing and ice dams need flashing or ice-and-water underlayment, not just shingles.",
                  "pro:a roofer; say where it enters (a valley, a wall's step flashing, or ice dams at the eaves)",
                  "shingles"),
        DiagCheck("shingles", "From the ground with binoculars, above where the water shows: are shingles missing, "
                  "lifted or cracked, or nails backed out?",
                  "Damaged shingles or popped nails let water under the courses above the leak.",
                  "cause:damaged or missing shingles: replace them (with fall protection) or have a roofer do it|",
                  "pro:a roofer; say where the leak shows in the attic and that the shingles look intact"),
        DiagCheck("not_roof", "No sign in the attic: is the stain under a bathroom, a pipe, or the air conditioner's "
                  "indoor unit?",
                  "Ceiling stains often come from plumbing or AC condensate, not the roof.",
                  "cause:not the roof: a plumbing leak or AC condensate (check the drain pan and its line) is the "
                  "likely source|",
                  "pro:a roofer or a home inspector; say there's a ceiling stain with no sign in the attic (possibly "
                  "only in wind-driven rain)"),
    ),
    ("Asphalt Roofing Manufacturers Association (ARMA), Residential Asphalt Roofing Manual",
     "National Roofing Contractors Association (NRCA), The NRCA Roofing Manual",
     "International Code Council, IRC 2021: R903 (weather protection) and R905.2.8 (flashing)"),
))

# ------------------------------------------------------------------ the aquaponics pilot (DEC-0150)
# Written from MIA Homestead's own design (homestead/docs/PILOT_VS_SCALE.md: a 55-gallon tank, 3 to 5 bluegill,
# fishless-cycled first; homestead/docs/SAFETY_SPEC.md: aeration first, dosing off by default, the safety MCU the final
# authority) and the published aquaponics guides named on each job.

_AQUA_SOURCES = ("FAO Fisheries and Aquaculture Technical Paper 589, Small-scale aquaponic food production "
                 "(Somerville et al., 2014)",
                 "Rakocy, Masser and Losordo, Recirculating Aquaculture Tank Production Systems: Aquaponics, SRAC "
                 "Publication 454 (2006)")

register(Job(
    "aquaponics_system", "aquaponics", "build", "Build the pilot aquaponics system",
    "The pilot from MIA Homestead's plan: a 55-gallon fish tank on a stand rated for it, a media grow bed above it "
    "draining back by gravity, the pump, the plumbing with an overflow so the bed can never flood the floor, and "
    "aeration that can't back-siphon. Leak-tested with water before any fish, sensor or controller. The controls and "
    "the fish are their own jobs.",
    ("aquaponics system", "aquaponics", "fish tank and grow bed", "aquaponic system", "build the aquaponics"),
    ("live_power", "structural", "injury"),
    "A small indoor or greenhouse system rarely needs a building permit, but a new outlet or circuit for it does, and "
    "some places regulate keeping fish. " + _LOCAL,
    ("water and electricity together", "the weight of a full tank (about 550 lb at 55 gallons) on the floor and stand",
     "lifting a heavy tank", "materials that poison fish (copper, zinc from galvanized parts, soap residue)"),
    ("gloves", "safety glasses when cutting pipe or drilling the bed"),
    ("level (2 ft)", "tape measure", "hacksaw or PVC cutter", "drill with a hole saw for the bulkhead",
     "deburring tool or file", "bucket and hose", "a marker for the water line"),
    ("a 55-gallon tank and a stand rated for its full weight", "a food-safe grow bed and its stand",
     "expanded clay or lava-rock media, rinsed", "a bulkhead (or uniseal) fitting, a standpipe or bell siphon, and an "
     "overflow", "schedule 40 PVC pipe and fittings (no copper or galvanized)", "a submersible circulation pump sized "
     "to move the tank's volume about once an hour", "an air pump, airline, a check valve and an airstone",
     "a GFCI-protected outlet and drip loops for every cord"),
    (
        Phase("Plan and prepare", (
            Step("Choose the spot: a level floor that can carry about 550 lb on the stand's footprint, out of direct "
                 "sun, near a GFCI-protected outlet, with somewhere for water to go if a pipe lets go.",
                 "A full 55-gallon tank weighs more than most people expect, and sun on the tank means algae and heat.",
                 ("On a wood floor, put the stand across the joists, near a bearing wall.",)),
            Step("Size the grow bed: for a media bed, roughly the tank's volume in bed is a common starting ratio "
                 "(start smaller and add beds as the fish grow).",
                 "The bed is the filter: too little bed for the fish and ammonia builds up.",
                 ("Plan the bed high enough that it drains to the tank by gravity.",)),
            Step("Check every part that touches water is fish-safe: no copper, no galvanized metal, no treated wood, "
                 "nothing washed with soap.", "Copper and zinc kill fish at very low levels.",
                 ("Rinse new parts in plain water only.",)),
        )),
        Phase("Stand, tank and bed", (
            Step("Set the tank stand level and shim it; fill the tank alone and leave it 24 hours.",
                 "A tank on an uneven stand stresses its seams; a slow leak is cheap to find before anything else is "
                 "connected.", ("Mark the water line and check it the next day.",),
                 "The tank held for 24 hours with the line unchanged and the stand level."),
            Step("Set the grow bed level on its own stand above the tank and drill it for the bulkhead at its low "
                 "point.", "The bulkhead is the drain that returns water to the tank.",
                 ("Deburr the hole so the gasket seals.",)),
            Step("Rinse the media until the water runs clear, then fill the bed.",
                 "Dust from new media clouds the water and clogs the pump.", ("Wear a mask while rinsing dusty media.",)),
        )),
        Phase("Plumbing", (
            Step("Fit the drain (a standpipe for constant flow, or a bell siphon for flood and drain) and an overflow "
                 "above it, both returning to the tank.",
                 "If the main drain clogs, the overflow sends the water back to the tank instead of onto the floor.",
                 ("The overflow must be lower than the bed's rim.",)),
            Step("Run the pump's line from the tank to the bed with a valve to set the flow; set the pump on the tank "
                 "floor on a block so it doesn't suck up debris.",
                 "Setting the flow is how the bed floods and drains in time with the pump.",
                 ("Use a union so the pump can come out without cutting pipe.",)),
            Step("Run water with the pump: watch the bed fill and drain several times. Then block the main drain on "
                 "purpose.", "A drain only proves itself when it fails: the overflow has to carry the full flow.",
                 ("Turn the flow down if the siphon won't start or won't stop.",),
                 "The bed fills and drains, and with the drain blocked the overflow returns all the water to the tank."),
        )),
        Phase("Aeration and power", (
            Step("Mount the air pump above the water line (or add a check valve in its line) and set the airstone on "
                 "the tank floor.", "Without that, a power cut lets the tank siphon back through the line into the "
                 "air pump.", ("Never set the air pump on the floor beside the tank without a check valve.",),
                 "The air pump is above the water or has a check valve."),
            Step("Plug the pump and air pump into a GFCI-protected outlet, with a drip loop in every cord.",
                 "Water running down a cord must drip off before it reaches the plug.",
                 ("Test the GFCI with its button.",), "Every cord has a drip loop and the GFCI trips on test."),
        )),
        Phase("Leak test and final inspection", (
            Step("Run the whole system for 48 hours with water only and the line marked on the tank.",
                 "Slow leaks and evaporation look alike for a day; two days shows the difference.",
                 ("Check every fitting with a dry paper towel.",), "Two days, no drips, and the level drop only "
                 "what evaporation explains."),
            Step("Write down the tank's water volume, the flow you set and how the bed cycles, for the node's "
                 "settings and for MIA.", "The controls and the cycling job start from these numbers.", ()),
        )),
    ),
    _AQUA_SOURCES + ("Sylvia Bernstein, Aquaponic Gardening (New Society, 2011)",
                     "MIA Homestead's pilot plan and safety spec (homestead/docs/PILOT_VS_SCALE.md, SAFETY_SPEC.md)"),
    skill="plumbing",
))

register(Job(
    "aquaponics_controls", "aquaponics", "install", "Install the greenhouse controller, safety MCU and sensors",
    "MIA Homestead's controls on the pilot: the Pi (the brain) and the ESP32 safety MCU (the final authority), bench-"
    "tested with LEDs first; probes for pH, EC, dissolved oxygen and temperature; the dosing pumps; pumps and heater "
    "switched through enclosed, listed relay outlets (no mains wiring done by hand); and the physical override "
    "switch. Each device goes in its labeled port. Flashing the MCU and preparing the Pi are MIA's provisioning steps.",
    ("aquaponics controls", "install the controller", "greenhouse controller", "install the sensors",
     "safety mcu", "install the probes"),
    ("live_power", "injury"),
    "Low-voltage controls need no permit, but a new outlet or circuit for the greenhouse does; mains wiring is a "
    "licensed electrician's work unless your permit lets a homeowner do it. " + _LOCAL,
    ("water and mains electricity in one place", "a pH probe or dosing chemical splashed in the eyes",
     "a relay that fails on and runs a pump or heater"),
    ("safety glasses and gloves with pH up and pH down", "dry hands for anything plugged in"),
    ("small screwdrivers", "a multimeter", "label maker or colored labels (the setup convention)",
     "zip ties and cable clips", "a USB cable for the MCU", "a measuring cup (for the dosing test)"),
    ("the parts on the node's live parts list (homestead/docs/HARDWARE_BOM_LIVE.md)", "a ventilated enclosure for "
     "the Pi, MCU and relay board, mounted above and away from water", "enclosed, listed relay-controlled outlets for "
     "the pumps and heater", "Atlas Scientific EZO circuits and probes, with their calibration solutions",
     "peristaltic dosing pumps and food-safe tubing", "a physical override switch (kill dosing, force aeration)"),
    (
        Phase("Plan and bench-test", (
            Step("Lay out every part from the node's live parts list and label each device and its port with the "
                 "setup convention's name and color.", "Labels and colors are how a device can't go in the wrong "
                 "port.", ("Label both ends of every cable.",)),
            Step("On the bench, flash the safety MCU (MIA does it from the PC over USB) and wire an LED with a "
                 "resistor in place of each relay.",
                 "LEDs prove the whole safety chain cheaply before anything touches water or chemicals.",
                 ("Nothing mains-powered on the bench.",)),
            Step("Run the node in simulation, then live with the LEDs: watch it announce, pair, take a command, pulse "
                 "and, when you unplug the Pi, fall back to safe defaults.",
                 "The fallback is the safety system's whole point; it has to be seen working.",
                 ("Time how long the fallback takes after the Pi goes quiet.",),
                 "Announce, pair, command, pulse and fallback all seen on the LEDs."),
        )),
        Phase("Mount the controls", (
            Step("Mount the enclosure above and away from the tank, with drip loops on every cable entering it.",
                 "Splash and condensation are the enemy of electronics by a tank.", ()),
            Step("Put the pumps and heater on enclosed, listed relay outlets, each plugged into a GFCI-protected "
                 "outlet, and connect only their low-voltage control leads to the relay board.",
                 "Switching mains through a listed enclosure means no exposed mains wiring by hand.",
                 ("Never open a relay outlet's mains side.",),
                 "No mains conductor is exposed anywhere, and every mains device is on a GFCI."),
            Step("Install and wire the physical override switch (dosing off, aeration forced on) where you can reach "
                 "it without the Pi.", "Safety must work with every screen dark.", (),
                 "The override kills dosing and forces aeration with the Pi unplugged."),
            Step("Power the Pi and the MCU from the battery-backed side, with the air pump first on it: per the safety "
                 "spec, aeration is the last load shed.", "Fish suffocate faster than anything else in the system "
                 "fails; aeration must outlast every other load.", ("Label which loads are on the backed-up side.",)),
        )),
        Phase("Sensors and dosing", (
            Step("Mount each probe per its maker (the pH probe never left dry, in its storage solution until "
                 "fitted), connect each EZO circuit to its labeled port, and the temperature probe to its own.",
                 "A dried-out pH probe is ruined; a probe in the wrong port reads as the wrong thing.",
                 ("Keep probes away from the dosing points and the airstone.",),
                 "The setup helper shows every device connected."),
            Step("Compare each probe's first readings with your test kit and a reference thermometer before the "
                 "node may act on them.", "A probe that reads wrong would dose wrong; the kit is the independent check.",
                 ("pH within 0.2 of the kit, temperature within 1 F.",)),
            Step("Run the dosing lines to a well-mixed spot away from the fish's favorite corner, and prime them "
                 "with water, not chemical.", "Priming with water lets you test volumes safely.",
                 ("Dosing pumps default off: every dose is a timed pulse.",)),
            Step("Command a test pulse of water from each pump into a measuring cup and compare with what the node "
                 "says it dosed.", "The node's dosing limits are only real if the volume per pulse is.",
                 ("Repeat three times; use the average.",), "Each pump's measured volume matches within 10 percent."),
        )),
        Phase("Final checks", (
            Step("Unplug the Pi with everything running: the MCU must stop dosing and keep aeration and circulation "
                 "on.", "This is the failure the system was designed around; prove it on the real build.",
                 (), "The MCU fell back to safe defaults on the real system."),
            Step("Photograph the wiring and the labels, and note anything changed from the parts list, for the node "
                 "and for MIA.", "The next diagnosis starts from how it's really wired.", ()),
        )),
    ),
    ("MIA Homestead's safety spec, MCU protocol, device setup guide and firmware README (homestead/docs/SAFETY_SPEC.md, "
     "MCU_PROTOCOL.md, DEVICE_SETUP_GUIDE.md, homestead/firmware/safety_mcu/README.md)",
     "Atlas Scientific EZO pH, EC and dissolved oxygen circuit datasheets",
     "NFPA 70, National Electrical Code (NEC) 2023, 210.8 (GFCI protection)"),
    skill="electrical_wiring",
))

register(Job(
    "aquaponics_commission", "aquaponics", "install", "Commission and cycle the system, then stock the fish",
    "From a built, leak-tested system with its controls in: calibrate every probe, hand the node to MIA so she "
    "watches every sensor, cycle the biofilter without fish (four to six weeks) until ammonia and nitrite read zero, "
    "plant, then stock bluegill gradually, testing every day at first, and set the node's species, dosing limits and "
    "alert contacts.",
    ("commission the aquaponics", "cycle the system", "fishless cycle", "stock the fish", "cycle the aquaponics",
     "commission the system"),
    ("live_power", "injury"),
    "Keeping, buying and moving live fish, and the species allowed, are set by your state's fish and wildlife "
    "agency; check before you buy. " + _LOCAL,
    ("ammonia and pH-adjusting chemicals (caustic or acidic)", "fish lost to a dissolved-oxygen crash or an ammonia "
     "spike", "chlorinated tap water"),
    ("gloves and safety glasses with ammonia and pH chemicals",),
    ("a freshwater test kit (ammonia, nitrite, nitrate, pH)", "Atlas calibration solutions (pH 4, 7, 10; EC; DO)",
     "a reference thermometer", "a dropper or syringe for dosing ammonia", "a fish net and a bucket"),
    ("dechlorinated water (a dechlorinator, which also handles chloramine)", "pure ammonia or ammonium chloride for "
     "the fishless cycle", "hardy plants to start (leafy greens)", "3 to 5 bluegill from a licensed source",
     "a quality floating fish feed"),
    (
        Phase("Prepare the water", (
            Step("Fill with dechlorinated water (a dechlorinator handles chloramine, which doesn't gas off), and let "
                 "the system run a day.", "Chlorine and chloramine kill the very bacteria the cycle grows.",
                 ("Ask your water supplier whether they use chloramine.",)),
            Step("Check your state's rules for keeping bluegill and where to buy them, before the cycle starts.",
                 "Four to six weeks is the time to line up a legal, healthy source.", ()),
            Step("Set up a quarantine tub with its own aeration, to hold new fish a week or two before they join the "
                 "system.", "A sick fish brought in can infect the system; a quarantine tub keeps it out until it's "
                 "clearly healthy.", ("Never share nets or buckets between the tub and the system.",)),
        )),
        Phase("Calibrate and hand over", (
            Step("Calibrate each probe as its maker says: pH at 7 then 4 and 10, EC dry then in solution, DO in air, "
                 "and the temperature probe against a reference thermometer.",
                 "Every dosing decision is only as good as the reading behind it.",
                 ("Rinse probes between solutions.",), "Every probe is calibrated and its readings make sense."),
            Step("Hand the node to MIA (\"take over the greenhouse\"): she lists every sensor she now watches and any "
                 "she can't.", "From here on she watches it with you, and alerts reach you when you're away.",
                 (), "MIA reports every sensor, with nothing missing."),
        )),
        Phase("Cycle the biofilter", (
            Step("Add ammonia to about 2 ppm and test ammonia, nitrite and nitrate every day; top it back up to 2 ppm "
                 "when it falls.", "Bacteria that turn ammonia into nitrite, then nitrate, grow on the media without "
                 "fish being harmed.", ("Keep pH near 7 and the water in the fish's range: the bacteria like it "
                                         "warm.",)),
            Step("Watch nitrite rise, then fall, and nitrate rise. The cycle is done when a 2 ppm dose of ammonia "
                 "reads zero ammonia and zero nitrite within a day.", "That's the proof the biofilter can handle "
                 "fish waste.", ("It usually takes four to six weeks; cold water takes longer.",),
                 "Ammonia and nitrite both read zero within 24 hours of a dose, and nitrate is rising."),
            Step("Keep a daily log through the cycle: your test kit's ammonia, nitrite and nitrate beside the node's "
                 "pH and temperature (MIA keeps the node's).", "The log shows the cycle's progress and catches a stalled "
                 "one early.", ("A cycle stalled for a week: check pH and temperature first.",)),
            Step("Plant hardy greens once nitrate shows.", "Plants are the other half of the filter.", ()),
        )),
        Phase("Stock and final checks", (
            Step("Float the fish's bag 15 to 20 minutes, then add tank water to the bag a little at a time before "
                 "netting them in; start with one or two.", "Sudden changes in temperature and pH shock fish.",
                 ("Never pour the bag's water into the tank.",)),
            Step("Feed lightly and test ammonia and nitrite every day for two weeks; add the rest of the fish over "
                 "the next weeks.", "The biofilter grows with the load: add fish faster than it grows and ammonia "
                 "spikes.", ("Any ammonia or nitrite: stop feeding a day and do a partial water change.",),
                 "Ammonia and nitrite stayed at zero through the two weeks."),
            Step("Set the node's tank species to Bluegill, review its dosing limits, set the alert contacts and the "
                 "dead-man check-in, and send a test critical alert.",
                 "The species turns on the right temperature watch; a test alert proves you'll hear about trouble.",
                 (), "A test critical alert reached your phone."),
        )),
    ),
    _AQUA_SOURCES + ("Atlas Scientific EZO calibration guides (pH, EC, dissolved oxygen)",
                     "MIA Homestead's pilot plan (homestead/docs/PILOT_VS_SCALE.md: fishless cycle first, bluegill)"),
    skill="home_building",
))

register(Job(
    "workshop_circuit", "electrical", "install", "A 20 A circuit to the workshop",
    "One 20 A, 120 V branch circuit from the house panel to a detached workshop: the permit, the route and trench, "
    "conduit or direct-burial cable at code depth, the disconnect at the workshop, GFCI-protected receptacles and a "
    "light, and the breaker landed in the panel with the power off. One circuit only: more than one (or 240 V tools) "
    "means a feeder and a subpanel, a different job. Where a homeowner may not do this work, the steps stay the same "
    "and a licensed electrician does them.",
    ("workshop circuit", "power to the workshop", "power to the shop", "run power to the shed",
     "wire the workshop", "circuit to the workshop"),
    ("live_power", "licensed", "utilities", "weather", "injury"),
    "A new circuit needs an electrical permit and inspections (the trench open with the conduit or cable in it, the "
    "rough-in, then the final). Many places let a homeowner do it on their own home under that permit; others "
    "require a licensed electrician. " + _LOCAL,
    ("electric shock: the panel's incoming lugs stay live with the main breaker off",
     "arc flash in the panel", "striking a buried line while trenching", "a receptacle wet in a damp building"),
    ("safety glasses", "insulated gloves rated for the voltage when testing in the panel", "work boots"),
    ("non-contact voltage tester and a two-lead tester (or multimeter)", "insulated screwdrivers and a torque "
     "screwdriver", "wire strippers and lineman's pliers", "trenching shovel or rented trencher", "PVC saw, primer "
     "and cement", "fish tape", "receptacle tester with a GFCI test button"),
    ("a 20 A breaker listed for your panel (its brand and type)", "12 AWG copper: UF-B for direct burial, or "
     "THWN-2 conductors (black, white, green) in Schedule 40/80 PVC", "PVC conduit, sweeps, a weatherproof entry and "
     "bushings", "a disconnect at the workshop (a listed switch, per your code)", "GFCI receptacles (20 A, "
     "weather-resistant where damp) and boxes", "a light fixture and switch", "cable staples or straps, connectors, "
     "warning tape for the trench"),
    (
        Phase("Plan and permit", (
            Step("Add up what the workshop will run at once (tools, lights, a heater): one 20 A circuit carries about "
                 "16 A continuous. If it's more, stop and plan a feeder and subpanel instead (say “walk me "
                 "through a workshop subpanel”).",
                 "A single circuit that trips every time the saw and the heater run is the wrong design.",
                 ("Big tools on 240 V need a feeder, not this job.",)),
            Step("Get the electrical permit; ask whether a homeowner may do this work where you live, and which "
                 "inspections come when.", "The trench inspection happens with it open: you can't bury first.",
                 ("Ask the required burial depth and whether UF or conduit is preferred.",),
                 "The permit is in hand and you know who does the work and each inspection."),
            Step("Check the panel has a free space for the breaker type it's listed for, and that its load can take "
                 "another circuit.", "A breaker not listed for the panel can fail to trip.",
                 ("No space: a tandem breaker only if the panel's label allows it.",)),
            Step("Call 811 and wait for the marks before you dig.", "The trench crosses the yard where gas, water "
                 "and power lines often run.", (), "Every line is marked along the route."),
        )),
        Phase("Trench and conduit", (
            Step("Trench along the marked route to the depth your code gives (NEC Table 300.5: commonly 24 in for "
                 "UF-B, 18 in for PVC, 12 in for a GFCI-protected 20 A residential circuit), hand-digging near any "
                 "mark.", "Depth is what protects the cable from a shovel or a post later.",
                 ("Hand-dig within 18 in of each mark.",)),
            Step("Lay the conduit (sweeps up at each end, glued joints, a bushing where wires leave it) or the UF-B "
                 "in sleeves where it rises out of the ground.", "Exposed cable where it comes up is where it gets "
                 "cut.", ("Support the risers; leave expansion where the code calls for it.",),
                 "The trench inspection has passed with the conduit or cable in place."),
            Step("Backfill with clean soil, the warning tape about 12 in above the cable, then compact.",
                 "The tape warns the next person who digs there.", ()),
        )),
        Phase("Wire the workshop", (
            Step("Mount the disconnect where the circuit enters the workshop, then the boxes for the receptacles "
                 "and the light.", "The code wants a way to shut off the building at the building.",
                 ("Damp location: weather-resistant receptacles and in-use covers.",)),
            Step("Pull the conductors (black, white, green) through the conduit, leaving 6 in or more in each "
                 "box.", "Short conductors are hard to terminate well.", ("Don't nick the insulation.",)),
            Step("Wire the first receptacle as a GFCI (line from the source, load to the rest), the others "
                 "downstream, the light and switch; ground every box and device.",
                 "GFCI protection is required in accessory buildings and is what saves a person in a damp shop.",
                 ("Line and load swapped means the GFCI won't reset or won't protect.",),
                 "Every connection is tight and the rough-in inspection has passed if required."),
        )),
        Phase("Connect at the panel", (
            Step("Turn the main breaker off, then prove it dead: test the tester on a known-live source, test the "
                 "panel's bus and terminals, then test the tester again.",
                 "A tester that has failed reads dead on a live wire.",
                 ("The service conductors and main lugs stay live with the main off: never touch them.",)),
            Step("Bring the circuit into the panel through a listed connector, land the white on the neutral bar, "
                 "the green on the ground bar, and the black on the new breaker, each torqued to its label.",
                 "Loose or under-torqued terminals are a leading cause of panel fires.",
                 ("Neutral and ground go where the panel's label says; in a subpanel they're kept apart.",),
                 "Every terminal is torqued and the breaker is seated, with the panel's cover still off for the "
                 "inspector if they want to see it."),
            Step("Put the cover back with every blank in place, turn the main on, then the new breaker; label it.",
                 "An open slot in a cover is a live opening.", ()),
        )),
        Phase("Test and final inspection", (
            Step("At each receptacle, check the wiring with the plug-in tester, then press its GFCI test: the "
                 "protected outlets must go dead and reset.", "A GFCI that doesn't trip protects no one.",
                 ("Any open ground or reversed polarity: power off and fix it before using it.",)),
            Step("Run the biggest tool and a light together for a few minutes and feel the breaker and the "
                 "disconnect for heat.", "Heat at a connection is a loose terminal.", ()),
            Step("Call for the final inspection and keep the permit card with the panel's records.",
                 "The final inspection makes the circuit legal and insurable.", (),
                 "The final inspection passed."),
        )),
    ),
    ("National Fire Protection Association, NFPA 70 National Electrical Code (NEC) 2023: 210.8 (GFCI), 225.30 to "
     "225.36 (outside branch circuits and the building disconnect), 250.32 (buildings supplied by a branch circuit), "
     "300.5 and Table 300.5 (underground installations), 334, 340 and 352 (NM, UF and PVC), 110.14(D) (torque)",
     "International Code Council, International Residential Code (IRC) 2021, Part VIII Electrical (E3601 to E4304)",
     "OSHA 29 CFR 1910.333, Selection and Use of Work Practices (de-energizing and testing before work)",
     "Mike Holt, Understanding the National Electrical Code, Vol. 1 (2023)"),
    skill="electrical_wiring",
))

register(Job(
    "root_cellar", "carpentry", "build", "Root cellar in a basement corner",
    "A root cellar framed into a corner of a basement, using two below-grade foundation walls as its cold sides: "
    "insulated partition walls and ceiling between it and the house, an insulated door, a low cold-air intake and a "
    "high exhaust to the outside, slatted shelving and bins, and a thermometer and hygrometer to run it at 32 to 40 F "
    "and 85 to 95% humidity. Not a dug-in or earth-bermed cellar outside: walls that hold back earth need an "
    "engineer's design.",
    ("root cellar", "basement root cellar", "build a root cellar", "storage cellar", "vegetable cellar"),
    ("structural", "hazmat", "injury"),
    "Interior partition walls usually need no permit, but cutting the house's rim or wall for vents can, and a "
    "finished-basement rule may apply. " + _LOCAL,
    ("dust and debris cutting into the house's rim or foundation", "old materials in a house built before 1980",
     "mold if the room runs wet without air moving", "saw injuries"),
    ("safety glasses", "hearing protection", "a dust mask or respirator for cutting and insulation"),
    ("tape measure, chalk line and a 4 ft level", "circular saw", "drill and hole saw", "powder-actuated or masonry "
     "fasteners (or construction adhesive)", "caulk gun and a can of spray foam", "thermometer and hygrometer"),
    ("treated bottom plates and framing lumber", "rigid foam or batt insulation for the partition walls and ceiling",
     "a vapor retarder for the house side (per your climate)", "an exterior-grade insulated door with weatherstrip",
     "two 4 in ducts with an exterior hood and screen, and a damper", "rot-resistant lumber for slatted shelves and "
     "bins", "a gravel or slatted floor cover if the slab stays damp"),
    (
        Phase("Plan before you build", (
            Step("Pick the corner: two foundation walls below grade, on the north or east side, away from the "
                 "furnace, water heater and laundry; measure its winter temperature for a week if you can.",
                 "A corner that stays cold by itself is half the cellar; a warm one never gets there.",
                 ("A wall with water stains or efflorescence needs its water fixed first.",),),
            Step("Plan the size (about 6 by 8 ft holds a family's winter roots), the door on the house side, and the "
                 "two vents: intake low near the floor, exhaust high near the ceiling, both through the rim or a "
                 "basement window.", "Cold air sinks in through the low duct and warm, damp air leaves through the "
                 "high one.", ("Keep the vents off the side the furnace or dryer vents out of.",)),
            Step("Check the house's age before cutting into the rim or old finishes, and test them if it's older "
                 "than 1980.", "Old caulk, paint and insulation can hold asbestos or lead.", (),),
        )),
        Phase("Frame and insulate the partitions", (
            Step("Snap the wall lines; fasten treated bottom plates to the slab and frame the two partition walls "
                 "with the door rough opening.", "Treated plates won't rot on a damp slab.",
                 ("Square the corner with the diagonals.",),
                 "The walls are plumb and fastened top and bottom, the opening fits the door."),
            Step("Insulate the partition walls and the ceiling (the joists above) to at least R-13, and put the vapor "
                 "retarder on the warm house side; leave the foundation walls bare.",
                 "The foundation walls are what keep it cold: insulating them warms the cellar.",
                 ("Seal every gap around pipes and joists with foam: warm house air is what spoils it.",)),
            Step("Hang the insulated door and weatherstrip it all around; add a threshold seal.",
                 "A leaky door lets the house's heat in all winter.", (),
                 "The door closes tight with no daylight around it."),
        )),
        Phase("Vents, shelves and floor", (
            Step("Cut the two vent holes through the rim or a window insert, set the ducts (intake run down to about "
                 "a foot off the floor, exhaust near the ceiling), add the screened hood outside and a damper, and "
                 "seal around each.", "The damper is how you hold temperature on the coldest nights.",
                 ("Screen both: mice come in through vents.",),
                 "Both vents are sealed to the wall and screened, and the damper works."),
            Step("Insulate and seal any length of duct that runs through the warm house side, and keep both runs "
                 "short and straight.", "A warm duct sweats inside and drips into the cellar.", ()),
            Step("Build slatted shelves and bins of rot-resistant wood, 2 in or more off the walls and floor.",
                 "Air has to move around stored food or it rots where it touches.", ()),
            Step("If the slab is dry, leave it; if it's damp, cover it with gravel or slatted boards you can wet to "
                 "raise the humidity.", "Roots keep in high humidity; a dry cellar shrivels them.", ()),
        )),
        Phase("Check it runs before you fill it", (
            Step("Put the thermometer and hygrometer at shelf height and read them twice a day for two weeks as the "
                 "weather cools; use the damper to steer toward 32 to 40 F and 85 to 95% humidity.",
                 "The numbers say whether it works before a harvest is in it.",
                 ("Below 32 F: close the intake. Above 40 F: open it on cold nights.",)),
            Step("Store apples and pears apart from potatoes and other roots, and check everything weekly for rot.",
                 "Apples give off ethylene that sprouts potatoes; one rotten one spreads.", (),
                 "It holds its range for two weeks and the first stores are in."),
        )),
    ),
    ("Mike and Nancy Bubel, Root Cellaring: Natural Cold Storage of Fruits and Vegetables, 2nd ed. (Storey, 1991)",
     "University of Minnesota Extension, Storing Vegetables at Home",
     "Building Science Corporation, Info-511: Basement Insulation",
     "International Code Council, International Residential Code (IRC) 2021: R702.7 (vapor retarders), R602 (wall "
     "framing)"),
    skill="carpentry",
))


# ------------------------------------------------------------------ home building, in order (DEC-0149 answer 2)

_IRC = "International Code Council, International Residential Code (IRC) 2021"

register(Job(
    "site_layout", "carpentry", "build", "Lay out the house on the site",
    "Putting a house's footprint on the ground before any digging: the plot plan and setbacks, the property corners, "
    "a benchmark elevation, batter boards and string lines squared by their diagonals, the height of the top of the "
    "foundation, and where the water will drain. Clearing and excavation are their own work.",
    ("site layout", "lay out the house", "layout the foundation", "batter boards", "stake out the house",
     "square the foundation"),
    ("utilities", "structural", "weather", "injury"),
    "The building permit comes with an approved plot plan; many places want the footprint checked against the "
    "setbacks (sometimes by a surveyor) before the footings are poured. " + _LOCAL,
    ("striking buried lines driving stakes", "swinging a sledge near people holding stakes",
     "tripping over strings and stakes"),
    ("work gloves", "safety glasses when driving stakes"),
    ("100 ft tape (two)", "builder's level, transit or laser level with a rod", "sledge and stakes", "mason's string "
     "and line levels", "framing square and a plumb bob", "marking paint"),
    ("2x4 stakes and 1x6 or 2x4 batter-board ledgers", "screws or nails", "mason's string (bright)",
     "the approved plot plan and the foundation plan"),
    (
        Phase("Plan and permit before you stake", (
            Step("Get the approved plot plan showing the house's corners, the setbacks from each property line, the "
                 "driveway, the septic or sewer, and the well or water line.", "Every stake comes from it; a house "
                 "over a setback can be ordered moved.", ("Ask whether a surveyor must locate it.",),
                 "The plot plan is approved with the permit."),
            Step("Find the property pins (or have the surveyor set them) and run lines between the ones you need.",
                 "Setbacks are measured from the real line, not a fence.", ("Never guess a pin.",)),
            Step("Call 811 and wait for the marks before driving anything deep.", "Batter-board stakes go 2 ft in, "
                 "right where service lines may run.", (), "Every line is marked."),
        )),
        Phase("Corners and batter boards", (
            Step("Measure in from the property lines and set a rough stake at each corner of the house.",
                 "These are the guide for the batter boards, not the final points.", ()),
            Step("Set a benchmark: a fixed point (a spike in a tree, a stake in concrete) that won't move, with its "
                 "elevation written down.", "Every height on the job is measured from it.",
                 ("Keep it out of the way of trucks and the dig.",)),
            Step("Build batter boards about 4 ft outside each corner, their ledgers level and all at the same "
                 "height above the benchmark.", "They hold the strings after the corner stakes are dug out.",
                 ("Brace them: a knocked batter board moves the house.",)),
            Step("Run strings for the outside faces of the foundation, pulled tight, and mark where each crosses its "
                 "ledger.", "The intersections are the corners.", ()),
            Step("Square it: a 3-4-5 triangle at one corner, then measure both diagonals and adjust the strings "
                 "until they match.", "A rectangle with equal diagonals is square.",
                 ("Re-check after every adjustment: moving one string moves two corners.",),
                 "The diagonals match within 1/4 in and every side matches the plan."),
        )),
        Phase("Heights and drainage", (
            Step("Decide the top of the foundation: at least 6 in of foundation showing above finished grade where "
                 "wood siding goes, and above the street or the high side of the lot.", "Water and wood don't mix; "
                 "a house set too low floods its own crawlspace.", ("Mark it on the batter boards.",)),
            Step("Plan the grade to fall away from the house: 6 in in the first 10 ft (or swales and drains where the "
                 "lot won't allow it).", "Water stopped at the wall is most basement leaks.", ()),
            Step("Mark the dig with paint along the strings, outside them by the over-dig the footings need.",
                 "The excavator works from paint, the footings from the strings.", ()),
        )),
        Phase("Check the layout and inspection", (
            Step("Measure every setback again from the strings to the property lines, and the diagonals again.",
                 "This is the last cheap moment to move the house.",
                 ("A setback short by inches still fails: fix it now, not after the pour.",)),
            Step("Have it checked if your permit asks for a setback or footprint survey, and photograph the batter "
                 "boards with their marks.", "Proof the house is where the plan says protects you later.", (),
                 "The setbacks match the plot plan and any required check has passed."),
        )),
    ),
    (_IRC + ": R105 (permits), R401.3 (drainage), R404.1.6 (height above finished grade)",
     "Rick Arnold, Building a Foundation (Taunton, For Pros by Pros, 2002)",
     "Larry Haun, The Very Efficient Carpenter (Taunton, 1992)"),
    skill="carpentry",
))

register(Job(
    "footings", "carpentry", "build", "Pour the footings",
    "Continuous concrete footings under a house's foundation walls: sized from the code's footing table for the soil "
    "and the floors above, set below the frost depth on undisturbed soil, formed, reinforced, inspected, poured level "
    "and keyed or doweled for the wall. Walls, slabs and piers for a deck are other jobs.",
    ("footings", "footing", "pour the footings", "foundation footings", "frost footing"),
    ("utilities", "structural", "weather", "injury"),
    "Footings need the building permit and almost always an inspection of the trench, forms and steel before the "
    "pour. " + _LOCAL,
    ("trench collapse in a deep excavation", "concrete burns (wet cement is alkaline)", "rebar ends (cap them)",
     "a ready-mix truck backing on soft ground"),
    ("safety glasses", "waterproof gloves and boots for the pour", "rebar caps", "a hard hat in a deep excavation"),
    ("builder's level or laser with a rod", "string lines from the batter boards", "shovels and a tamper",
     "rebar cutter and bender, tie wire and twister", "hammer and form stakes", "screed and float", "wheelbarrow"),
    ("form lumber (2x10 or 2x12) and stakes, or a trench to pour in", "rebar (size and count from the plan, "
     "commonly two #4 bars) with chairs or dobies", "ready-mix concrete to the strength your code asks",
     "keyway form or dowel bars for the wall", "curing blankets or plastic"),
    (
        Phase("Plan and permit before you dig", (
            Step("Find your frost depth and the soil's bearing value (the building department knows both), and size "
                 "the footing from the code's table for the stories it carries.", "A footing above the frost line "
                 "heaves; one too narrow for its soil settles.", ("Unknown or filled soil: get it tested.",),
                 "You have the footing's width, depth, steel and the depth below grade from the plan or table."),
            Step("Call 811 and wait for the marks.", "The trench runs right where service lines come in.", (),
                 "Every line is marked."),
            Step("Work out the concrete (length x width x depth of every run, in cubic yards, plus 10%), and book "
                 "the inspection and the truck with a day between them.", "A truck that arrives before the "
                 "inspection pass can't wait, and a short load leaves a cold joint.",
                 ("Ask the plant for the strength and slump your code calls for.",)),
        )),
        Phase("Excavate and form", (
            Step("Dig the trench from the strings to undisturbed soil below the frost depth, with the bottom level "
                 "(stepped where the grade drops, never sloped).", "A footing bears on what's under it; loose spoil "
                 "or a slope lets it slide or settle.", ("Hand-trim the bottom; remove anything soft.",
                                                          "A trench deeper than 5 ft needs shoring or a slope back.")),
            Step("Keep water out: pump or drain it, and never pour into standing water or mud.",
                 "Water at the bottom weakens the concrete and the soil.", ()),
            Step("Set the forms (or cut a clean trench) to the width and height, level along their tops to the "
                 "benchmark.", "The top of the footing sets the height of every wall on it.",
                 ("Stake and brace the forms: concrete is heavy.",)),
            Step("Place the rebar on chairs 3 in up from the soil, lapped where bars meet and bent around the "
                 "corners, tied.", "Steel touching the soil rusts; steel not lapped doesn't carry across.",
                 ("Lap length per the plan or code, commonly 40 bar diameters.",),
                 "The trench, forms and steel have passed the footing inspection."),
        )),
        Phase("Pour and finish", (
            Step("Pour the concrete in one go where you can, working it into the corners, and screed it level with "
                 "the form tops.", "A cold joint in a footing is a weak point.",
                 ("Don't add water at the truck to make it flow.",)),
            Step("Set the keyway or the dowels for the wall while it's wet, on the wall's center line.",
                 "They lock the wall to the footing.", ()),
            Step("Keep it moist and above freezing for at least 3 days; strip the forms after a day or two.",
                 "Concrete gains strength by curing; frozen fresh concrete is ruined.",
                 ("Below 40 F: blankets, and ask the plant about a cold-weather mix.",)),
        )),
        Phase("Check the footing and inspection", (
            Step("Shoot the top of the footing at each corner and along each run, and measure its width.",
                 "A footing more than about 1/2 in out of level shows up in every course of the wall.", ()),
            Step("Note any inspection the wall stage needs and keep the footing inspection record.",
                 "The record is part of the house's papers.", (),
                 "The footing is level within tolerance and its inspection is recorded."),
        )),
    ),
    (_IRC + ": R301.2(1) (frost depth), R401.4 (soil tests), R403.1 (footings, Table R403.1(1)), R403.1.3 "
     "(reinforcement)",
     "American Concrete Institute, ACI 332-20, Code Requirements for Residential Concrete",
     "OSHA 29 CFR 1926 Subpart P, Excavations",
     "Rick Arnold, Building a Foundation (Taunton, For Pros by Pros, 2002)"),
    skill="concrete",
))

register(Job(
    "slab_on_grade", "carpentry", "build", "A house slab on grade",
    "A concrete floor slab for a house, poured on the ground inside (or monolithic with) its footings: the base, the "
    "under-slab plumbing and conduit roughed in and inspected first, insulation and a vapor retarder, reinforcement, "
    "the pour and finish, joints and the cure. The slab's quantities come from the slab calculator; a workshop slab "
    "is the workshop job.",
    ("slab on grade", "house slab", "floor slab", "pour the slab", "monolithic slab"),
    ("utilities", "structural", "weather", "injury"),
    "A house slab is inspected before the pour: the plumbing under it, the base, the vapor retarder and the steel, "
    "and in many places the slab-edge insulation. " + _LOCAL,
    ("concrete burns (wet cement is alkaline)", "silica dust cutting joints", "a ready-mix truck and pump hose",
     "back strain screeding and floating"),
    ("safety glasses", "waterproof gloves and boots for the pour", "a respirator for cutting joints",
     "kneeboards"),
    ("builder's level or laser", "plate compactor", "screed board or power screed", "bull float, edgers, groovers "
     "and hand floats", "power trowel (rented) for a smooth floor", "early-entry or walk-behind joint saw",
     "rebar cutter and tie twister"),
    ("compactable gravel base", "rigid foam (XPS or EPS) for the edge and under the slab, per your energy code",
     "10 mil or heavier vapor retarder and seam tape", "rebar or wire reinforcement on chairs",
     "ready-mix concrete (strength and slump your code asks)", "curing compound or blankets",
     "isolation joint strip around posts and walls"),
    (
        Phase("Plan and permit before the base", (
            Step("Get the slab's thickness (3 1/2 in or more), base, insulation and steel from the plan and your "
                 "code, and the schedule of inspections.", "Each inspection happens with something about to be "
                 "covered.", ("Ask whether a radon vent pipe must go under it.",),
                 "You have the slab section and the inspection schedule."),
            Step("Call 811 before any digging for the base or the thickened edges.",
                 "The service lines come in under this slab's edge.", (), "Every line is marked."),
            Step("Work out the concrete from the slab calculator and book the inspection and the truck a day apart.",
                 "The truck can't wait for an inspector.", ()),
        )),
        Phase("Base, rough-ins and insulation", (
            Step("Strip topsoil and anything organic; fill and compact in lifts to the subgrade height.",
                 "Organic soil rots and settles under a slab.", ("Compact each lift no more than about 6 in thick.",)),
            Step("Rough in everything that goes under it: drain and supply lines, conduit, the radon pipe; pressure- "
                 "or water-test the plumbing.", "Nothing under a slab can be fixed without breaking it.",
                 ("Sleeve every pipe that passes through the slab.",),
                 "The under-slab plumbing has passed its inspection."),
            Step("Place and compact at least 4 in of gravel, then the edge and under-slab foam per your energy "
                 "code.", "The gravel breaks capillary water; the foam keeps the floor's edge warm.", ()),
            Step("Lay the vapor retarder over it, lapped 6 in and taped at every seam and pipe.",
                 "A torn or untaped retarder lets ground moisture into flooring and walls.",
                 ("Patch every tear before the steel goes on.",)),
        )),
        Phase("Steel and pour", (
            Step("Place the reinforcement on chairs so it sits near mid-depth of the slab; isolation strips at "
                 "posts and walls.", "Steel lying on the base does nothing.", (),
                 "The base, retarder and steel have passed the pre-pour inspection."),
            Step("Pour, screed to the forms or the laser, and bull float; wait for the bleed water to go.",
                 "Finishing over bleed water weakens the surface and it dusts.",
                 ("Don't add water at the truck.",)),
            Step("Edge, float and trowel to the finish the floor needs; cut control joints within about 12 hours "
                 "(about 2 to 3 times the slab's thickness in feet apart, a quarter of its depth).",
                 "The joints decide where it cracks.", ("Panels as square as you can make them.",)),
            Step("Cure it: curing compound, wet blankets or plastic, for at least 7 days, protected from freezing.",
                 "A slab that dries too fast curls and cracks.", ()),
        )),
        Phase("Check the slab and final inspection", (
            Step("Check its flatness with a straightedge and level, and the height at each wall line.",
                 "The walls and every floor finish sit on it.", ("A high spot over 1/4 in in 10 ft needs grinding.",)),
            Step("Record the inspections and photograph the plumbing and conduit before you cover anything else.",
                 "The photos are the only map of what's under the slab.", (),
                 "The slab is flat within tolerance and every inspection is recorded."),
        )),
    ),
    (_IRC + ": R506 (concrete floors on ground: R506.1 thickness, R506.2.2 base, R506.2.3 vapor retarder), "
     "N1102 (slab-edge insulation), Appendix F (radon control)",
     "American Concrete Institute, ACI 302.1R-15, Guide to Concrete Floor and Slab Construction",
     "American Concrete Institute, ACI 332-20, Code Requirements for Residential Concrete",
     "MIA's slab calculator (core/build_calcs.py concrete_slab)"),
    plan="shed-slab",
    skill="concrete",
))

register(Job(
    "foundation_wall", "carpentry", "build", "A block foundation wall",
    "A concrete masonry (block) foundation wall on a finished footing, for a crawlspace or basement: the layout on "
    "the footing, corner leads and coursed block, grouted cells with the steel the code table asks for, a bond beam, "
    "anchor bolts, dampproofing, the footing drain, and backfill only once the floor braces the top. A poured wall is "
    "a forming crew's work.",
    ("foundation wall", "block wall", "basement wall", "crawlspace wall", "cmu wall", "lay block"),
    ("utilities", "structural", "fall", "weather", "injury"),
    "Foundation walls are inspected with the steel in place before grouting in many places, and again before "
    "backfill. " + _LOCAL,
    ("a wall pushed over by backfill before the floor braces it", "lifting 35 to 40 lb blocks all day",
     "mortar and grout burns", "scaffold falls on taller walls"),
    ("safety glasses", "gloves for mortar", "steel-toe boots", "fall protection or guarded scaffold above 6 ft"),
    ("mason's trowels, jointer and level (4 ft and 2 ft)", "mason's line, line blocks and a story pole",
     "mortar mixer or tub and hoe", "masonry saw", "scaffold or planks on frames", "grout bucket or pump"),
    ("concrete masonry units (8 in or the width the table asks) and corner blocks", "Type S or M mortar",
     "grout (fine or coarse)", "rebar (size and spacing from the code table)", "bond-beam blocks or a bond beam "
     "course", "1/2 in anchor bolts", "dampproofing (or waterproofing for a basement)", "footing drain pipe, "
     "washed stone and filter fabric"),
    (
        Phase("Plan and permit before laying", (
            Step("Size the wall from the code table for its height and the depth of soil against it (the unbalanced "
                 "backfill), and get the steel size and spacing.", "A wall holding back more soil than its table "
                 "allows can crack and bow inward.", ("Tall or wet backfill: an engineer's design.",),
                 "You have the wall's thickness, steel and bolt layout from the plan or table."),
            Step("Check the footing: level, clean, the dowels where the steel cells will be.", "The first course "
                 "takes up any error, and only so much.",
                 ("More than about 3/4 in out over the run: talk to the inspector before shimming with mortar.",)),
        )),
        Phase("Lay the courses", (
            Step("Snap the wall lines on the footing from the strings and dry-lay the first course to set the "
                 "bond and the cuts.", "Laying it dry first avoids a sliver block at a corner.", ()),
            Step("Lay the corners first (the leads), level and plumb, checked against the story pole.",
                 "The corners guide every block between them.", ("Check plumb on two faces of each lead.",)),
            Step("Run the courses between the leads on a tight mason's line, full mortar on the face shells and "
                 "the cells to be grouted, joints tooled when thumbprint-hard.", "Even joints carry load evenly; "
                 "tooling seals the face.", ("Never move a block once the mortar has started to set.",)),
            Step("Place the vertical steel in its cells as you go (lapped to the dowels), clean out the mortar "
                 "fins, and leave cleanouts at the bottom of tall pours.", "Grout has to fill the whole cell around "
                 "the bar.", (), "The steel is in place and inspected if your code requires it before grouting."),
            Step("Lay the bond beam course with its horizontal steel, then grout the steel cells and the bond beam, "
                 "rodding each lift.", "The bond beam ties the wall into one piece.",
                 ("Grout lifts no taller than your code allows (commonly 5 ft).",)),
            Step("Set the anchor bolts in the top grout: 1/2 in, no more than 6 ft apart, within 12 in of each "
                 "end of every sill plate, 7 in into the grout.", "They hold the house to its foundation in wind.",
                 ("Keep a bolt out of where a stud or a door opening lands.",)),
        )),
        Phase("Dampproof, drain and backfill", (
            Step("Parge and dampproof (or waterproof) the outside from the footing to above grade.",
                 "Block soaks up groundwater without it.", ()),
            Step("Lay the footing drain beside the footing on washed stone, wrapped in fabric, sloped to daylight "
                 "or a sump.", "Water drained away never pushes on the wall.",
                 ("Holes down in perforated pipe; a drain that runs uphill holds water.",)),
            Step("Backfill only after the floor framing (or temporary bracing) holds the top of the wall, in lifts, "
                 "without driving machines against it.", "An unbraced wall fails under backfill.",
                 ("No heavy equipment within the wall's height of it.",),
                 "The floor or bracing is in before any backfill."),
        )),
        Phase("Check the wall and inspection", (
            Step("Check the top for level and the walls for plumb and square, and the bolt positions against the "
                 "sill layout.", "The floor framing needs a flat, square top.", ()),
            Step("Call for the foundation inspection your permit lists before backfill, and record it.",
                 "Once it's buried no one can see the steel or the dampproofing.", (),
                 "The foundation inspection passed."),
        )),
    ),
    (_IRC + ": R404.1 (concrete and masonry foundation walls, Table R404.1.1), R403.1.6 (anchorage), R405 "
     "(foundation drainage), R406 (dampproofing and waterproofing), R606 (masonry)",
     "The Masonry Society, TMS 402/602-16, Building Code Requirements and Specification for Masonry Structures",
     "National Concrete Masonry Association, TEK 3-11, Concrete Masonry Basement Wall Construction",
     "OSHA 29 CFR 1926 Subpart L, Scaffolds"),
    skill="concrete",
))

register(Job(
    "floor_framing", "carpentry", "build", "Frame the first floor",
    "A wood-framed floor on a foundation wall or crawlspace: sill seal and treated sills on the anchor bolts, a girder "
    "where the span needs one, rim and joists sized from the span table, blocking and hangers, holes and notches kept "
    "inside the code's limits, and a glued and screwed subfloor. The floor's lumber comes from the floor calculator.",
    ("floor framing", "frame the floor", "floor joists", "joists", "subfloor", "sill plate"),
    ("structural", "fall", "injury", "weather"),
    "Floor framing is part of the building permit; the framing inspection usually comes later with the walls, so "
    "photograph anything that will be covered. " + _LOCAL,
    ("falls from the open floor edge into the crawlspace or basement", "saw and nailer injuries",
     "joists and girders dropped while setting"),
    ("safety glasses", "hearing protection", "work gloves", "a guardrail or line at an open edge over 6 ft"),
    ("circular saw", "framing nailer and compressor", "drill with spade and auger bits", "chalk line, tape and "
     "framing square", "4 ft level and a string line", "caulk gun for subfloor adhesive"),
    ("sill seal and treated 2x6 sill plates", "washers and nuts for the anchor bolts", "joists and rim (size from "
     "the span table) and a built-up or engineered girder if the plan has one", "joist hangers and the nails listed "
     "for them", "blocking", "3/4 in tongue-and-groove subfloor", "subfloor adhesive and screws or ring-shank nails"),
    (
        Phase("Plan before you frame", (
            Step("Size the joists from the span table for their species, grade, spacing and span (and the girder "
                 "from its table or the plan), with the live load a floor carries (40 psf for living areas).",
                 "An undersized joist bounces, sags or fails.", ("Mark the crown of every joist before you lay out.",),
                 "You have the joist size, spacing, and any girder and its posts from the plan or table."),
            Step("Check the top of the foundation for level and square, and the anchor bolt positions.",
                 "Shimming a floor later is far harder than fixing the sill now.", ()),
            Step("Stage the lumber flat, off the ground on stickers, and covered, sorted by length.",
                 "Wet or twisted joists make a wavy floor.", ("Set aside any joist with a large knot on its edge.",)),
        )),
        Phase("Sills, girder and rim", (
            Step("Lay sill seal, drill the treated sills for the bolts, set them flush with the outside of the wall "
                 "and tighten the nuts and washers.", "The sill is what the house is bolted down through.",
                 ("Seal the sill gap: it's a major air leak.",)),
            Step("Set the girder on its posts or pockets, level and straight, with full bearing at each end.",
                 "The girder carries half the floor's weight in the middle of the span.",
                 ("Bearing at least 3 in on wood or metal, per your code.",),
                 "The girder is level and its posts sit on their concrete pads."),
            Step("Snap the joist layout on the sills (16 in on center from one end) and set the rim joists.",
                 "Every joist, and the subfloor's edges, follow that layout.", ()),
        )),
        Phase("Joists and blocking", (
            Step("Set each joist crown up, nailed through the rim and toenailed to the sill, lapped or spliced over "
                 "the girder as the plan shows.", "Crowns up flatten under load; crowns down sag more.",
                 ("Double the joists under parallel walls and around openings.",)),
            Step("Frame openings (stairs, chimneys) with doubled headers and trimmers in hangers.",
                 "The joists cut for an opening hang on the header.", ()),
            Step("Add blocking or bridging where the code or the plan asks, and at the girder.",
                 "Blocking keeps joists from rolling and stiffens the floor.", ()),
            Step("Bore and notch only inside the code's limits: holes no larger than a third of the depth and 2 in "
                 "from an edge, no notches in the middle third of the span.", "A joist cut in the wrong place loses "
                 "most of its strength.", ("Never cut an engineered joist except where its maker allows.",),
                 "Every joist is crowned up, fastened, and uncut outside the limits."),
        )),
        Phase("Subfloor and check", (
            Step("Glue and fasten the subfloor across the joists, tongue into groove, end joints staggered and "
                 "landing on joists, a 1/8 in gap at the ends.", "Glue and screws stop squeaks; the gap lets it "
                 "swell without buckling.", ("Fastener spacing per the panel's stamp, commonly 6 in edges, 12 in "
                                             "field.",)),
            Step("Check the floor for flat and square across its diagonals, and photograph the framing and hangers.",
                 "Walls need a flat, square deck, and the photos show the inspector what's covered.", (),
                 "The deck is flat and square and its framing is photographed for the inspection."),
        )),
    ),
    (_IRC + ": R502 (wood floor framing: R502.3 spans, R502.6 bearing, R502.8 cutting and notching), R503 (floor "
     "sheathing), Table R502.3.1(2) (floor joist spans)",
     "American Wood Council, Span Tables for Joists and Rafters (2018)",
     "Larry Haun, The Very Efficient Carpenter (Taunton, 1992)",
     "MIA's floor calculator (core/build_calcs.py floor_frame)"),
    skill="framing",
))

register(Job(
    "wall_framing", "carpentry", "build", "Frame the walls",
    "A house's stud walls framed flat on the deck and raised: plates laid out together, studs, corners and "
    "intersections, headers sized for their openings, the walls raised, plumbed, lined and braced, the top plate "
    "doubled and lapped, wall bracing (sheathing) to the code, and fire blocking. The walls' lumber comes from the "
    "stud-wall calculator.",
    ("wall framing", "frame the walls", "stud walls", "raise the walls", "frame a wall", "headers"),
    ("structural", "fall", "weather", "injury"),
    "Wall framing is part of the building permit, with a framing inspection before insulation covers it. Changing a "
    "bearing wall or a header needs the plan's sizes. " + _LOCAL,
    ("a raised wall falling before it's braced", "wind catching a sheathed wall", "nailer and saw injuries",
     "falls from the deck edge and from ladders"),
    ("safety glasses", "hearing protection", "work gloves", "steel-toe boots"),
    ("circular saw", "framing nailer and compressor", "framing square, speed square and chalk line", "6 ft level or "
     "a plumb bob", "string line and spacer blocks", "wall jacks or enough people to raise long walls", "ladders"),
    ("2x4 or 2x6 studs and plates (treated bottom plates on concrete)", "header stock (built-up, LVL, per the "
     "header table)", "sheathing panels for the wall bracing", "temporary bracing lumber", "16d and 8d nails (or the "
     "plan's schedule)", "fire-blocking lumber or listed material"),
    (
        Phase("Plan before you frame", (
            Step("From the plan, list each wall, which ones bear weight, every rough opening's size and its header "
                 "from the header table, and the wall bracing method.", "Headers and bracing are where walls fail.",
                 ("Header spans depend on the load above, not just the opening width.",),
                 "Every opening has its header size and every wall its bracing method."),
            Step("Snap the wall lines on the deck, outside walls first.", "The walls are built on their own lines.",
                 ()),
            Step("Check where each bearing wall lands: on a girder, a doubled joist or blocking, as the plan shows.",
                 "A bearing wall on a single joist mid-span pushes the floor down.",
                 ("No support under a bearing wall: stop and ask before framing it.",)),
        )),
        Phase("Lay out and frame flat", (
            Step("Tack the bottom and top plates together and lay out studs at 16 in (or 24 in) on center, with "
                 "every opening, corner and intersection marked on both.", "Laying both plates together keeps every "
                 "stud plumb when it's raised.", ("Start the layout so sheathing edges land on studs.",)),
            Step("Build the headers, cripples, king and jack studs for each opening, then nail the studs between "
                 "the plates, crowns all one way.", "Each piece carries the load around the opening down to the "
                 "floor.", ("Jacks are the length the header sits on, kings run full height.",)),
            Step("Frame corners and wall intersections with enough backing for the drywall inside.",
                 "Inside corners need wood to fasten to.", ()),
            Step("Square the wall on the deck (equal diagonals) and sheathe it flat if your bracing allows, nailing "
                 "to the schedule.", "Sheathing nailed square locks the wall square.",
                 ("Nail spacing on the panel edges is what the bracing strength comes from.",)),
        )),
        Phase("Raise, plumb and brace", (
            Step("Raise each wall with enough hands or wall jacks, set the bottom plate on its line, nail it down "
                 "and brace it right away.", "An unbraced wall in wind is the most common framing accident.",
                 ("Never raise in strong wind.",)),
            Step("Plumb every corner, then line the tops straight with a string and spacer blocks, bracing as you "
                 "go.", "A wall out of plumb or line shows in the roof and the drywall.",
                 ("Within 1/8 in in 8 ft is a good wall.",)),
            Step("Add the double top plate, lapped at corners and intersections, with joints offset at least 24 in "
                 "from the plate below.", "The lap ties the walls together into one box.", (),
                 "Every wall is plumb, lined and braced, with the top plate lapped."),
        )),
        Phase("Bracing, blocking and framing inspection", (
            Step("Finish the wall bracing to its method's length and nailing, and fire-block every concealed space "
                 "the code lists (floor and ceiling levels, soffits, at 10 ft heights).", "Bracing holds the house "
                 "against wind; fire blocking stops a fire racing up inside the walls.", ()),
            Step("Call for the framing inspection (often with the roof framed and dried in) before any insulation.",
                 "The inspector has to see the headers, bracing and blocking.", (),
                 "The framing inspection passed."),
        )),
    ),
    (_IRC + ": R602 (wood wall framing: R602.3 fastening, R602.7 headers, R602.8 fire blocking, R602.10 wall "
     "bracing), Tables R602.7(1) to (3) (header spans)",
     "APA, Engineered Wood Construction Guide (Form E30)",
     "Larry Haun, The Very Efficient Carpenter (Taunton, 1992)",
     "MIA's stud-wall calculator (core/build_calcs.py stud_wall)"),
    skill="framing",
))

register(Job(
    "roof_framing", "carpentry", "build", "Frame a gable roof",
    "A stick-framed gable roof on finished walls: rafters and a ridge sized from the span tables, a pattern rafter "
    "tested before the rest are cut, rafter ties or ceiling joists at the plate, uplift connectors, gable-end framing "
    "and the overhangs. Trusses come with their own drawings and bracing guide; the steps still apply around them.",
    ("roof framing", "frame the roof", "rafters", "ridge board", "stick frame a roof", "set trusses"),
    ("structural", "fall", "weather", "injury"),
    "Roof framing is part of the building permit and its framing inspection; trusses need their engineered drawings "
    "on site. " + _LOCAL,
    ("falls from the walls, the ridge and ladders", "a rafter or truss dropped while lifting", "wind on a partly "
     "framed roof", "saw and nailer injuries"),
    ("fall protection (anchors and harness, or guardrails) at the roof edge", "hard hat for work below",
     "safety glasses", "work gloves"),
    ("circular saw and a framing square with rafter tables", "speed square", "framing nailer and compressor",
     "chalk line and string", "ladders and scaffold or roof brackets", "temporary bracing lumber"),
    ("rafter and ridge stock (size from the span table)", "ceiling joists or rafter ties", "hurricane ties or "
     "other uplift connectors with their listed nails", "gable-end studs and blocking", "fascia and subfascia stock",
     "temporary braces"),
    (
        Phase("Plan and permit before cutting", (
            Step("Size the rafters from the span table for their spacing, the pitch, your snow load and dead load, "
                 "and the ridge one size deeper than the rafters.", "Rafters carry the snow; a short table entry "
                 "sags or fails under a heavy winter.", ("A vaulted ceiling with no ties needs a structural ridge "
                                                         "beam: an engineer's design.",),
                 "You have the rafter size, spacing, ridge and the tie or ceiling joist layout."),
            Step("Check the top plates for level, straight and parallel, and mark the rafter layout on both walls "
                 "matching the ceiling joists below.", "Rafters beside their ceiling joists make the tie that holds "
                 "the walls in.", ()),
        )),
        Phase("Pattern rafter and ridge", (
            Step("Lay out a pattern rafter: the ridge plumb cut, the birdsmouth seat cut, the tail; keep the seat cut "
                 "to no more than about a third of the rafter's depth.", "A deep birdsmouth weakens the rafter right "
                 "where it bears.", ("Shorten the length for half the ridge's thickness.",)),
            Step("Test it at both ends of the building (with a ridge scrap) before cutting the rest from it.",
                 "Walls are never perfectly equal; a test catches it on one rafter, not forty.", (),
                 "The pattern fits at both ends and the middle."),
            Step("Raise the ridge on temporary posts at its height, level and centered, with a pair of rafters at "
                 "each end.", "The ridge sets the roof's line; once it's straight the rest follow.",
                 ("Brace the ridge and the first pairs before letting go.",)),
        )),
        Phase("Rafters, ties and connectors", (
            Step("Set the rest in pairs, directly opposite each other, nailed to the ridge and the plate.",
                 "Opposite pairs keep the ridge straight under their push.", ("Sight the ridge as you go.",)),
            Step("Nail the ceiling joists or rafter ties to each rafter at the plate with the heel-joint nailing "
                 "from the code's table.", "That joint keeps the rafters from spreading the walls apart.",
                 ("Too few nails here is a common failure.",)),
            Step("Install the uplift connectors at every rafter to the plate, every nail hole filled with the "
                 "listed nail.", "Wind lifts roofs; the connector's rating depends on every nail.", ()),
            Step("Frame the gable ends (studs to the rafters at layout) and the rake overhangs, and brace the gable "
                 "walls.", "A tall gable wall is weak in wind until it's braced to the roof.", ()),
            Step("Snap the tail line and cut the rafter tails straight, then install the subfascia.",
                 "The fascia line is what everyone sees.", ("Check the tail line for level along the eave.",)),
        )),
        Phase("Check the frame and inspection", (
            Step("Check the ridge for straight and level, the rafters for plumb at the ridge, and the walls for "
                 "push-out along the plate.", "A roof that spread a wall shows at once in the plate line.", ()),
            Step("Leave the frame open for the framing inspection with the sheathing (or include it if your "
                 "inspector does it after dry-in).", "Connectors and heel joints have to be seen.", (),
                 "The roof frame is ready for (or has passed) its inspection."),
        )),
    ),
    (_IRC + ": R802 (roof framing: R802.3 ridge, R802.4 rafters, R802.5.2 rafter ties, R802.11 uplift), Tables "
     "R802.4.1(1) to (8) (rafter spans) and R802.5.2 (heel joint nailing)",
     "American Wood Council, Span Tables for Joists and Rafters (2018)",
     "Structural Building Components Association, BCSI: Guide to Good Practice for Handling, Installing, Restraining "
     "and Bracing of Metal Plate Connected Wood Trusses",
     "OSHA 29 CFR 1926 Subpart M, Fall Protection"),
    skill="framing",
))

register(Job(
    "roof_sheathing_underlayment", "carpentry", "build", "Sheathe and dry in the roof",
    "The roof deck and its first water layer: structural panels across the rafters with clips and the nailing the "
    "code asks, drip edge at the eaves, ice barrier where your climate needs it, underlayment lapped from the eave "
    "up, drip edge on the rakes over it, and the roof dried in until the roofing goes on.",
    ("roof sheathing", "sheathe the roof", "dry in the roof", "underlayment", "roof deck", "ice and water shield"),
    ("fall", "weather", "injury"),
    "Roof sheathing nailing is often checked at the framing inspection; the ice barrier requirement depends on your "
    "climate zone. " + _LOCAL,
    ("falls from the eave and rakes", "a panel caught by wind on the roof", "slipping on underlayment, dew or frost",
     "nailer injuries"),
    ("fall protection (anchors and harness, or guardrails)", "soft-soled boots", "safety glasses", "work gloves"),
    ("circular saw", "framing nailer or coil roofing nailer", "chalk line", "utility knife and hammer tacker",
     "roof brackets and planks", "ladders tied off at the top"),
    ("roof sheathing panels (thickness for the rafter spacing)", "panel edge clips (H-clips) where the span needs "
     "them", "8d ring-shank or common nails", "drip edge", "ice barrier (self-adhered membrane) where required",
     "synthetic or #30 felt underlayment", "cap nails or staples"),
    (
        Phase("Plan before you load the roof", (
            Step("Pick the panel thickness from its span rating for your rafter spacing and snow load, and check "
                 "whether your area requires an ice barrier and how far up.", "Thin panels between wide rafters "
                 "sag between them.", ("Ice barrier commonly runs from the eave to 24 in inside the warm wall.",),
                 "You know the panel, the nailing, and the ice barrier rule."),
            Step("Check the forecast for a dry, calm stretch long enough to sheathe and dry in.",
                 "Wet sheathing and wind-caught panels are the two ways this job goes wrong.", ()),
        )),
        Phase("Sheathe the deck", (
            Step("Snap a line 48 in up from the fascia and start the first course along it, long side across the "
                 "rafters.", "A straight first course keeps every course after it straight.",
                 ("Measure from the line, not the fascia: fascia is rarely straight.",)),
            Step("Stagger the end joints by at least one rafter, land every end on a rafter, leave 1/8 in gaps and "
                 "set clips between rafters on the long edges.", "The gap lets panels swell; clips stop edges "
                 "sagging.", ("Swollen panels touching each other buckle the roof.",)),
            Step("Nail to the schedule (commonly 6 in at edges, 12 in in the field, closer near the eaves and rakes "
                 "in high wind zones).", "Nails at the edges are what hold the deck down in wind.",
                 ("Nails that miss the rafter hold nothing: snap a line over each one.",)),
            Step("Leave the ridge vent slot open if the plan has one, and trim the rake edges flush.",
                 "Cutting the slot after is harder and less safe.", ()),
        )),
        Phase("Dry in", (
            Step("Nail drip edge along the eaves first, on the deck.", "At the eaves the underlayment laps over "
                 "the drip edge so water runs off its face.", ("Lap drip-edge pieces 2 in, uphill over downhill.",)),
            Step("Roll the ice barrier from the eave up as far as required, and into the valleys.",
                 "Ice dams push water up under shingles; the membrane seals around the nails.",
                 ("Self-adhered membrane can't be repositioned: dry-fit it first.",)),
            Step("Roll the underlayment from the bottom up, each course lapped over the one below by the maker's "
                 "lap (commonly 2 to 4 in, 6 in at ends), fastened to its pattern.", "Every lap sheds water down "
                 "the roof, never into it.", ("Never lap uphill.",),
                 "The deck is covered with no exposed sheathing and every lap runs downhill."),
            Step("Nail drip edge along the rakes, over the underlayment.", "At the rakes it laps over so wind-driven "
                 "rain can't get under it.", ()),
        )),
        Phase("Check the dry-in and inspection", (
            Step("Walk it for loose or missed fasteners, torn underlayment and laps facing the wrong way; patch "
                 "every tear.", "Dry-in has to keep rain out until the roofing goes on.", ()),
            Step("Get any sheathing inspection your permit lists, and keep the roof covered until roofing.",
                 "Synthetic underlayment's UV rating is limited: check how long it can be left.", (),
                 "The roof is dried in and any inspection passed."),
        )),
    ),
    (_IRC + ": R803 (roof sheathing, Table R803.1), R905.1.1 (underlayment), R905.1.2 (ice barrier), R905.2.8.5 "
     "(drip edge)",
     "APA, Engineered Wood Construction Guide (Form E30): roof sheathing",
     "Asphalt Roofing Manufacturers Association, Residential Asphalt Roofing Manual",
     "OSHA 29 CFR 1926 Subpart M, Fall Protection"),
    skill="framing",
))

register(Job(
    "asphalt_shingles", "exterior", "install", "Shingle a roof (asphalt)",
    "Asphalt shingles on a dried-in roof: the shingle's slope and wind rating checked, starter strips at the eaves and "
    "rakes, courses laid to the maker's offsets and nailed in the nailing zone, step and counter flashing at walls "
    "and chimneys, valleys, pipe boots, and the ridge vent and cap. Tear-off of an old roof is in the first phase.",
    ("asphalt shingles", "shingle the roof", "reroof", "new shingles", "roofing", "shingles"),
    ("fall", "hazmat", "weather", "injury"),
    "A new roof or a reroof usually needs a permit; many places allow no more than two layers and check the deck "
    "and ice barrier. " + _LOCAL,
    ("falls from the roof and ladders", "heat on a dark roof in summer", "slipping on granules and dew",
     "old roofing with asbestos (some roofs before 1980)"),
    ("fall protection (anchors and harness)", "soft-soled boots", "safety glasses", "gloves"),
    ("coil roofing nailer (or a hammer) set to drive flush", "utility knife with hook blades", "chalk line and "
     "tape", "tin snips", "roof brackets and planks", "a magnetic sweeper for nails", "pry bar and roofing shovel "
     "for tear-off"),
    ("shingles (bundles from the roof's squares plus waste)", "starter strip shingles", "ridge cap shingles and "
     "ridge vent", "step flashing and counterflashing", "valley metal or membrane", "pipe boots", "roofing nails "
     "long enough to go through the deck", "roofing sealant"),
    (
        Phase("Plan and permit before you start", (
            Step("Measure the roof in squares (100 sq ft), add waste for hips and valleys, and check the slope: "
                 "shingles need at least 2:12, and below 4:12 a double layer of underlayment.", "Shingles on too low "
                 "a slope leak however well they're nailed.", ("Read the maker's instructions: its warranty "
                                                               "depends on them.",),
                 "You have the materials, the permit and the maker's instructions."),
            Step("For a reroof, tear off down to the deck, replace any soft or rotted sheathing, and dry it in.",
                 "Shingles over a bad deck fail with it.", ("Asphalt felt or shingles from before 1980: test for "
                                                            "asbestos before tearing off.",)),
        )),
        Phase("Starter and field", (
            Step("Nail the starter strips along the eaves (sealant edge up at the eave) and up the rakes.",
                 "The starter seals the first course down and fills the gaps under its cutouts.",
                 ("Overhang the drip edge by about 1/4 to 3/4 in, per the maker.",)),
            Step("Snap horizontal lines for the courses and a vertical line for the offset.",
                 "Lines keep courses straight when the roof isn't.", ("Re-snap lines faded by rain or foot traffic.",)),
            Step("Lay the first course flush with the starter, then each course on its line with the maker's "
                 "offset, four nails a shingle (six in high wind) in the nailing zone, driven flush.",
                 "Nails above the zone miss the shingle below; overdriven nails cut through.",
                 ("Too high or angled nails are the most common shingle failure.",)),
        )),
        Phase("Flashing, valleys and vents", (
            Step("Weave step flashing in with each course where the roof meets a wall: one piece a course, nailed to "
                 "the deck only, the wall's weather barrier and siding lapped over it.", "Each piece sheds into the "
                 "shingle below it; nailing it to the wall tears it when the house moves.", ()),
            Step("Flash chimneys and skylights with their apron, step, counter and cricket pieces (a cricket on the "
                 "high side of any chimney over 30 in wide).", "Chimneys are where roofs leak most.",
                 ("Counterflashing goes into a mortar joint, not just sealant.",)),
            Step("Lay the valleys (open metal, or closed-cut over the ice barrier) to the maker's method, with no "
                 "nails within 6 in of the center.", "A nail in a valley is a hole where all the water runs.", ()),
            Step("Slide the pipe boots under the course above and over the course below.", "Every flashing "
                 "follows the same rule: the top edge under, the bottom edge over.", ()),
            Step("Cut the ridge vent slot if it isn't already open, install the vent, then the ridge cap shingles "
                 "facing away from the prevailing wind.", "Ridge venting with soffit intake keeps the attic dry.",
                 ("Balance intake and exhaust: intake at least as much as the ridge.",),
                 "Every wall, chimney, valley, pipe and the ridge is flashed and capped."),
        )),
        Phase("Check the roof and final inspection", (
            Step("Walk the roof for unsealed tabs, exposed nails, and flashing laps facing uphill; sweep every nail "
                 "from the yard with the magnet.", "One exposed nail is a leak; one in a tire is a flat.", ()),
            Step("Call for the final inspection and keep the shingle wrappers or the maker's warranty card.",
                 "The warranty needs the product and the date.", (), "The final inspection passed."),
        )),
    ),
    (_IRC + ": R905.1 (underlayment and ice barrier), R905.2 (asphalt shingles: R905.2.2 slope, R905.2.5 fasteners, "
     "R905.2.8 flashing), R908 (reroofing)",
     "Asphalt Roofing Manufacturers Association, Residential Asphalt Roofing Manual",
     "National Roofing Contractors Association, NRCA Roofing Manual: Steep-slope Roof Systems",
     "OSHA 29 CFR 1926 Subpart M, Fall Protection"),
    skill="framing",
))

register(Job(
    "metal_roof", "exterior", "install", "A metal roof (exposed-fastener panels)",
    "Exposed-fastener metal panels (corrugated or ribbed) on a dried-in deck or on purlins: the slope and panel "
    "checked, high-temperature underlayment, eave and rake trim, the first panel squared to the eave, side laps "
    "sealed, screws to the maker's pattern, wall and ridge flashing with closures, and pipe boots. Standing seam is a "
    "specialist's roll-formed system.",
    ("metal roof", "metal roofing", "tin roof", "corrugated roof", "r-panel", "steel roof"),
    ("fall", "weather", "injury"),
    "A metal roof needs the same permit as any roof; some places limit roofing over existing shingles. " + _LOCAL,
    ("panel edges and cut ends are razor sharp", "metal is slick when wet, dewy or frosty", "wind catching a panel "
     "on the roof", "falls from the roof and ladders", "lightning on a metal roof"),
    ("cut-resistant gloves", "fall protection (anchors and harness)", "soft-soled boots", "safety glasses and "
     "hearing protection when cutting"),
    ("impact driver with a magnetic hex bit and depth setting", "metal snips (left, right, straight) and a nibbler "
     "or metal-cutting circular blade", "chalk line and tape", "seaming or hand-bending tools", "caulk gun",
     "roof brackets"),
    ("panels cut to length for each run", "eave, rake, ridge, wall and valley trim", "inside and outside foam "
     "closures", "butyl sealant tape and sealant", "painted screws with sealing washers (length for the deck or "
     "purlins)", "high-temperature underlayment", "pipe boots for metal roofs"),
    (
        Phase("Plan and permit before ordering", (
            Step("Check the slope against the panel's minimum (lapped exposed-fastener panels commonly need 3:12) and "
                 "order the panels cut to each run's length with the trim.", "A panel on too low a slope leaks at "
                 "its end laps.", ("Measure every run; roofs are rarely square.",),
                 "You have the permit, the maker's guide, and panels cut to length."),
            Step("Dry in the deck with high-temperature underlayment (or set purlins at the maker's spacing).",
                 "Metal gets hot enough to melt ordinary felt.", ()),
        )),
        Phase("Trim and panels", (
            Step("Install the eave trim with sealant tape on top and the closures under where the panels land.",
                 "Closures keep out wind-driven rain, birds and insects.", ("Closures upside down leave gaps.",)),
            Step("Square the first panel to the eave (not the rake) with its overhang, and screw it.",
                 "A first panel off square fans every panel after it.", ("Check against a 3-4-5 from the eave.",)),
            Step("Lay each panel lapping the last by the maker's lap, sealant tape in the lap, screwed to the "
                 "pattern into the deck or purlins.", "The sealant and the pattern are what keep the laps dry.",
                 ("Screws snug: an overdriven washer splits, an underdriven one leaks.",)),
            Step("Cut panels with snips or a nibbler, never an abrasive wheel, and brush off every filing.",
                 "Hot filings burn the paint and rust spots appear within weeks.", ()),
        )),
        Phase("Flashing and ridge", (
            Step("Install the wall and end-wall flashing with closures and sealant, laps running downhill.",
                 "Where the roof meets a wall is where water gets behind.",
                 ("The wall's weather barrier laps over the flashing, never under.",)),
            Step("Set the outside closures and the ridge cap with its sealant, screwed into the high ribs.",
                 "The ridge sheds everything above it.", ("Vented ridge: use vented closures.",)),
            Step("Fit the rake trim over the panel edges, and the pipe boots sealed and screwed to the flat of the "
                 "panel.", "Boots sealed to the flat, never across a rib, stay dry.", ()),
            Step("Check the screws in a line across each panel, and tighten or replace any that missed the purlin.",
                 "A screw that missed is a hole.", ("Seal a missed hole with a slightly larger screw.",),
                 "Every lap, trim, closure and boot is sealed and screwed."),
        )),
        Phase("Check the roof and final inspection", (
            Step("Walk the roof (on the ribs over the purlins) for loose screws and leftover filings, and sweep the "
                 "screws and scraps from the ground.", "Filings rust; walking between ribs dents the panel.", ()),
            Step("Call for the final inspection and keep the panel maker's warranty and color code.",
                 "Touch-up paint and warranty claims need them.", (), "The final inspection passed."),
        )),
    ),
    (_IRC + ": R905.10 (metal roof panels: R905.10.2 slope), R905.1.1 (underlayment), R908 (reroofing)",
     "Metal Construction Association, Installation Manual for Exposed Fastener Metal Roof Panels",
     "National Roofing Contractors Association, NRCA Roofing Manual: Metal Panel and SPF Roof Systems",
     "OSHA 29 CFR 1926 Subpart M, Fall Protection"),
    skill="framing",
))

register(Job(
    "windows_doors", "carpentry", "install", "Install windows and exterior doors",
    "Flanged new-construction windows and prehung exterior doors in framed openings: sizes, egress and safety glass "
    "checked, openings checked plumb and square, a sloped sill or sill pan, each unit set in sealant and fastened, "
    "and the flashing taped in the right order with the weather barrier lapped over the top. Replacement windows in "
    "an old frame follow their maker's own method.",
    ("windows", "install windows", "install a door", "exterior door", "prehung door", "window install"),
    ("fall", "hazmat", "weather", "injury"),
    "New windows and doors are covered by the building permit; bedrooms need an egress window and some locations "
    "need safety glass. Replacing them in an older house may need a permit too. " + _LOCAL,
    ("a heavy unit dropped from a ladder or upper floor", "broken glass", "falls from ladders and scaffold",
     "old paint with lead (houses before 1978) when removing old units"),
    ("safety glasses", "cut-resistant gloves for glass", "fall protection or guardrails at upper openings"),
    ("4 ft and 2 ft levels", "framing square and tape", "utility knife", "caulk gun", "J-roller for flashing tape",
     "drill/driver and a nail gun or hammer", "shims", "ladders or scaffold"),
    ("the windows and doors (sizes from the plan, U-factor from your energy code)", "sill pan or sloped sill "
     "pieces", "flashing tape compatible with the weather barrier", "sealant the window maker lists",
     "galvanized roofing nails or screws for the flanges", "door installation screws (3 in)", "low-expansion "
     "window and door foam"),
    (
        Phase("Plan and permit before setting units", (
            Step("Check each unit against the plan: rough opening size, egress size for every bedroom (a clear "
                 "opening of 5.7 sq ft, sill no higher than 44 in), and safety glass where the code requires it.",
                 "Egress and safety glass are checked at the final; swapping a unit then is costly.",
                 ("Safety glass is commonly required within 24 in of a door and near tubs and stairs.",),
                 "Every unit's size, egress and glazing match the plan."),
            Step("Check each rough opening for plumb, level and square (equal diagonals), and 1/2 in larger than "
                 "the unit each way.", "A unit forced into a racked opening binds and leaks.", ()),
        )),
        Phase("Prepare the opening", (
            Step("With the weather barrier on the wall, cut it in the modified I pattern: across the top with a "
                 "head flap folded up, down the middle, folded into the opening at the sides and sill.",
                 "The head flap later laps over the head flashing so water stays outside.",
                 ("Tape the head flap up out of the way.",)),
            Step("Dry-fit each unit in its opening: check the fit, where the shims go, and that the flange sits flat "
                 "on the wall.", "Finding a problem before the sealant is down saves the unit and the tape.",
                 ("A flange that won't sit flat means the opening or the sheathing is out.",)),
            Step("Flash the sill first: a sill pan or flashing tape across the sill, up the jambs at least 6 in, "
                 "out over the barrier below; slope the sill out if you can.", "Every window eventually leaks a "
                 "little; the pan sends that water out instead of into the wall.", ()),
        )),
        Phase("Set and fasten", (
            Step("Run a continuous bead of sealant on the back of the opening at the jambs and head, and only "
                 "intermittently at the sill.", "Sealed sides and top keep water out; the gaps at the sill let any "
                 "water inside the pan drain out.", ("A solid bead at the sill traps water.",)),
            Step("Set the window, center it, shim the sill level, check the diagonals and the operation, then nail "
                 "the flanges to the maker's spacing.", "Fastened out of square, it sticks for good.",
                 ("Open and close it before the last nails.",)),
            Step("Tape the jamb flanges, then the head flange (over the jamb tape), rolled tight.", "Laps run like "
                 "shingles: each piece over the one below.", ()),
            Step("Fold the head flap down over the head flashing and tape its diagonal cuts.", "That's the last "
                 "lap: the barrier over the window, water running down its face.", (),
                 "Sill, jambs, head and flap are lapped in order with no reverse laps."),
            Step("Set each prehung door on its sill pan and sealant, shim at the hinges and the latch, put 3 in "
                 "screws through a hinge into the framing, and adjust for even gaps.", "The long hinge screws keep "
                 "a heavy door from sagging.", ("Check the gap at the top for even all the way across.",)),
        )),
        Phase("Seal, check and inspection", (
            Step("Fill the gaps between unit and framing with low-expansion foam, not stuffed batts.", "Regular foam "
                 "can bow a frame until it won't open.", ("Foam the sides and top; leave the sill pan's drain path "
                                                           "open.",)),
            Step("Open, close and lock every unit; check the weatherstrip contact and sill drainage with a little "
                 "water.", "A unit that works now is one that was set right.", (),
                 "Every unit opens, locks and drains, ready for the final inspection."),
        )),
    ),
    (_IRC + ": R308 (glazing and safety glass), R310 (emergency escape and rescue openings), R612 (exterior windows "
     "and doors), R703.4 (flashing)",
     "ASTM E2112-19, Standard Practice for Installation of Exterior Windows, Doors and Skylights",
     "Fenestration and Glazing Industry Alliance (FGIA), InstallationMasters training manual",
     "The window and door maker's installation instructions (they govern the warranty)"),
    skill="carpentry",
))

register(Job(
    "house_wrap_flashing", "exterior", "install", "House wrap and flashing",
    "The weather-resistive barrier and flashings behind the siding: house wrap lapped from the bottom up and "
    "fastened to its maker's pattern, seams taped, openings detailed, kickout flashing where a roof meets a wall, "
    "flashing over trim and between materials, the deck ledger flashed, and every penetration sealed. The siding is "
    "its own job.",
    ("house wrap", "housewrap", "weather barrier", "wrb", "tyvek", "flashing", "kickout flashing"),
    ("fall", "weather", "injury"),
    "The weather barrier is part of the building permit and some places inspect it before siding. " + _LOCAL,
    ("falls from ladders and scaffold", "wind catching a roll of wrap at height", "staple and nail guns"),
    ("fall protection or guarded scaffold above 6 ft", "safety glasses", "gloves"),
    ("hammer tacker or cap stapler", "utility knife", "J-roller", "chalk line and tape", "tin snips and a metal "
     "brake (or bought bends)", "ladders or scaffold"),
    ("house wrap (or a liquid-applied or integrated sheathing barrier)", "cap nails or cap staples", "seam tape "
     "made for the wrap", "kickout flashing", "Z flashing and head flashing", "deck-ledger flashing", "flashing "
     "blocks or tape for hose bibs, vents and wires"),
    (
        Phase("Plan before wrapping", (
            Step("Pick the barrier and read its maker's guide; plan the sequence so windows and doors fit into it "
                 "and every flashing laps the right way.", "The barrier works only as a shingled system.",
                 ("Wrap and window tape from makers that say they work together.",),
                 "You know the barrier, its laps and its fastening."),
            Step("Check the sheathing for nails sticking out and damage, and that the roof's step flashing is in.",
                 "Wrap over a proud nail tears.", ()),
        )),
        Phase("Wrap the walls", (
            Step("Start at the bottom: the first course lapped 2 in or more past the bottom of the sheathing onto "
                 "the concrete below, rolled level around the corners.", "Starting low lets every course above lap "
                 "over it.", ("Keep it level: a sloping course runs out of lap at one end.",)),
            Step("Lap each higher course over the one below by 6 in and vertical seams by 6 to 12 in, fastened with "
                 "cap nails or staples to the maker's spacing.", "Laps that run the wrong way funnel water into the "
                 "wall.", ("Never reverse-lap a course.",)),
            Step("Tape every vertical and horizontal seam with the maker's tape.", "Tape makes it an air barrier "
                 "too.", ("Press the tape with the roller, not your hand.",)),
            Step("At openings whose windows aren't set yet, cut the modified I pattern and tape the head flaps up.",
                 "The window job laps into these cuts.", ("Never cut a plain X: it leaves no head flap.",),
                 "Every wall is wrapped, lapped and taped, with every opening cut for its unit."),
        )),
        Phase("Flash the details", (
            Step("At each roof-to-wall line, set a kickout flashing at the bottom of the step flashing, then the "
                 "wrap over the step flashing.", "Without a kickout, the water off the roof runs into the wall "
                 "behind the siding.", ("Kickouts missing is a top cause of rotted walls.",)),
            Step("Flash the head of every door and window trim and every horizontal break (Z flashing), the wrap "
                 "lapped over each.", "Water running down the wall meets each piece and is sent out.",
                 ("Flashing with no end dams spills at the ends: turn them up.",)),
            Step("Flash the deck ledger: flashing over it and up behind the wrap, before the deck's joists go on.",
                 "A leaking ledger rots the rim joist and the deck falls.", ("Never wrap over the ledger flashing "
                                                                             "from below.",)),
            Step("Seal every penetration (hose bibs, vents, wires, lights) with flashing blocks or tape, shingle "
                 "lapped.", "Every hole in the barrier is a leak unless it's lapped.", (),
                 "Every kickout, head, ledger and penetration is flashed and lapped."),
        )),
        Phase("Check the barrier and inspection", (
            Step("Walk every wall for tears, missing tape and reverse laps; patch from the bottom up.",
                 "Once the siding is on, the barrier is invisible.", ()),
            Step("Call for the weather-barrier inspection if your permit lists one, and photograph every wall "
                 "and detail.", "The photos are the record of what's behind the siding.", (),
                 "The barrier is continuous and lapped, and any inspection passed."),
        )),
    ),
    (_IRC + ": R703.2 (water-resistive barrier), R703.4 (flashing), R903.2.1 (kickout flashing), R507.2.4 "
     "(deck ledger flashing)",
     "DuPont Tyvek, Weatherization Systems Installation Guidelines",
     "ASTM E2112-19, Standard Practice for Installation of Exterior Windows, Doors and Skylights",
     "Building Science Corporation, BSD-105: Understanding Drainage Planes"),
    skill="carpentry",
))

register(Job(
    "siding_lap", "exterior", "install", "Lap siding (fiber cement)",
    "Fiber-cement lap siding over a finished weather barrier: the maker's clearances, trim and corners first, a "
    "story pole to line courses up with the windows, a level starter, each board blind-nailed to its maker's "
    "schedule, butt joints flashed, gaps at trim sealed, and cut ends primed. Wood and vinyl lap follow the same "
    "steps with their own makers' nailing and gaps.",
    ("siding", "lap siding", "fiber cement siding", "hardie board", "hardieplank", "side the house"),
    ("fall", "hazmat", "weather", "injury"),
    "Siding is part of the building permit on a new house; residing an old one may need a permit and, before 1978, "
    "lead-safe work on the old paint. " + _LOCAL,
    ("silica dust cutting fiber cement", "falls from ladders and scaffold", "heavy, brittle boards carried at "
     "height", "old painted siding with lead (houses before 1978)"),
    ("a respirator rated for silica, or cutting outdoors with dust-collecting tools", "safety glasses",
     "hearing protection", "gloves", "fall protection or guarded scaffold above 6 ft"),
    ("fiber-cement shears or a circular saw with a fiber-cement blade and dust collection", "siding gauges (one "
     "person can hang a board)", "pneumatic siding nailer or a hammer", "4 ft level and chalk line", "story pole",
     "caulk gun", "scaffold or pump jacks"),
    ("lap siding boards", "trim and corner boards", "starter strip", "joint flashing (or the maker's joint pieces)",
     "corrosion-resistant siding nails the maker lists", "the maker's sealant", "primer and paint for cut ends"),
    (
        Phase("Plan and permit before siding", (
            Step("Read the maker's guide and check its clearances: commonly 6 in above the ground, 2 in above roofs, "
                 "decks and patios, and the gap at trim.", "Siding that sits in water or snow soaks up and fails, "
                 "and breaks the warranty.", ("Mark the clearance lines on the wall before anything goes up.",),
                 "You know the clearances, the nailing and the joint method."),
            Step("Check the weather barrier and all its flashings are done (kickouts, heads, ledger).",
                 "The siding covers them for good.",
                 ("A torn barrier patched now costs a roll of tape, not a wall.",)),
        )),
        Phase("Trim and layout", (
            Step("Install the corner boards and the trim around windows and doors, with flashing over the heads.",
                 "Siding butts to trim; trim set first gives clean, sealed edges.", ("Leave the maker's gap at "
                                                                                     "trim for sealant.",)),
            Step("Make a story pole: mark the course lines so a course lines up with the tops and bottoms of the "
                 "windows, with even exposure up the wall.", "Courses that meet the windows evenly need no thin "
                 "slivers.", ("Exposure within the maker's range.",)),
            Step("Snap a level line for the first course at the clearance height and nail the starter along it.",
                 "The first course sets every course above it.", (),
                 "The starter is level all the way around the house."),
        )),
        Phase("Hang the boards", (
            Step("Hang the first course on the starter and each course above at its story-pole line, blind-nailed "
                 "per the maker (commonly 1 in from the top edge into studs).", "Nails in the wrong place crack the "
                 "board or show.", ("Nails flush, never overdriven.",)),
            Step("Land butt joints on studs where the maker asks, with joint flashing behind each one, staggered "
                 "from the courses above and below.", "Every butt joint is a gap water finds.", ()),
            Step("Cut boards outdoors with the dust-collecting saw or shears, and prime every cut end.",
                 "Unprimed cut ends wick water and swell.", ("Never dry-cut fiber cement in a closed space.",)),
            Step("Fit around windows, vents and fixtures with mounting blocks, and leave the gap at every piece of "
                 "trim for sealant.", "Blocks give a flat, flashed edge for the siding.", (),
                 "Every wall is sided to its lines with every joint flashed."),
        )),
        Phase("Seal, paint and final inspection", (
            Step("Seal the gaps at trim with the maker's sealant (not the butt joints, unless the maker says to).",
                 "Sealed butt joints trap water behind them.",
                 ("Tool the sealant smooth into the gap, not smeared on the face.",)),
            Step("Paint within the maker's time if the boards are primed only, and touch up any nail or mark.",
                 "Primer alone isn't the finish.", ()),
            Step("Walk every wall for the clearances, nails and gaps; call for the final inspection.",
                 "Clearances are often checked at the final.", (), "The final inspection passed."),
        )),
    ),
    (_IRC + ": R703 (exterior covering: R703.10 fiber cement siding, Table R703.3(1) attachment)",
     "James Hardie, HardiePlank Lap Siding Installation Requirements",
     "OSHA 29 CFR 1926.1153, Respirable Crystalline Silica (Table 1: fiber-cement cutting)",
     "EPA Renovation, Repair and Painting Rule (40 CFR 745) for houses before 1978"),
    skill="carpentry",
))

register(Job(
    "insulation", "carpentry", "install", "Insulate walls, rim joists and attic",
    "Insulation to the energy code in a framed house: the R-values for your climate zone, baffles at the eaves, "
    "batts cut and split to fill every cavity without compression, foam at the rim joists, the attic hatch "
    "insulated and sealed, blown insulation in the attic to its depth markers, and the certificate posted. Air "
    "sealing comes first and is its own job.",
    ("insulation", "insulate", "insulate the walls", "insulate the attic", "batts", "blown in insulation"),
    ("hazmat", "fall", "injury"),
    "New insulation is inspected before drywall in most places, and a certificate of the R-values is posted near the "
    "panel. Adding attic insulation to an old house may need no permit. " + _LOCAL,
    ("fiberglass and cellulose dust", "attic heat in summer", "stepping through a ceiling between joists",
     "old vermiculite insulation (may hold asbestos)", "falls from the attic ladder"),
    ("a respirator (N95 or better)", "safety glasses", "long sleeves and gloves", "knee pads"),
    ("insulation knife and a straightedge", "tape measure", "staple gun (for faced batts)", "spray-foam gun",
     "blowing machine (rented with the bags) for the attic", "work light and planks for the attic"),
    ("batts sized for the wall and ceiling cavities (R-values from your code)", "rigid foam or spray foam for the "
     "rim joists", "eave baffles", "attic insulation (blown cellulose or fiberglass) and depth rulers",
     "an insulated, weatherstripped attic hatch cover", "the insulation certificate"),
    (
        Phase("Plan before insulating", (
            Step("Look up your climate zone's R-values (walls, ceiling, floor, rim) in the energy code, and plan "
                 "what goes where.", "The R-values are checked at the inspection.", ("Ask whether a vapor "
                                                                                     "retarder is required in "
                                                                                     "your zone.",),
                 "You have the R-value for every part of the house."),
            Step("Check that air sealing is done and the rough-in inspections (plumbing, electrical, framing) have "
                 "passed.", "Insulation covers what they need to see.",
                 ("Nothing insulated before its rough-in passes.",)),
            Step("In an older attic, look for vermiculite (gray-brown pebbles) and have it tested before disturbing "
                 "it.", "Some vermiculite holds asbestos.", ("Leave it untouched until the test says.",)),
        )),
        Phase("Walls and rim joists", (
            Step("Fit the rim joists: rigid foam cut snug and sealed at its edges with spray foam, or spray foam "
                 "itself.", "The rim is one of the leakiest, coldest parts of a house.",
                 ("Foam board needs its edges sealed or air goes around it.",)),
            Step("Insulate floors over unheated spaces (crawlspace, garage) with the batts held up against the "
                 "subfloor by supports.", "A batt hanging down leaves a cold gap under the floor.",
                 ("Supports every 18 to 24 in.",)),
            Step("Cut wall batts to the cavity's full height, split around pipes and cables, and cut around boxes; "
                 "fill every corner without compressing.", "A compressed or gapped batt loses much of its value.",
                 ("Faced batts: facing toward the warm side unless your zone says otherwise.",)),
            Step("Insulate behind tubs, showers and in the small spaces around windows and corners before they're "
                 "closed.", "The small spots are the cold ones.", (),
                 "Every wall cavity and rim is filled to its R-value."),
        )),
        Phase("Attic", (
            Step("Set baffles between the rafters at every eave, from the soffit up past where the insulation will "
                 "reach.", "Insulation blocking the soffit stops the attic venting and causes ice dams.", ()),
            Step("Staple depth rulers on the joists around the attic, then blow the insulation level to the depth "
                 "for its R-value.", "Depth is how the R-value is seen.", ("Keep it off recessed lights not "
                                                                            "rated IC, and 3 in from chimneys "
                                                                            "and flues.",)),
            Step("Insulate and weatherstrip the attic hatch, and build a dam around it so the insulation can't "
                 "fall in.", "An open hatch leaks more than the rest of the ceiling.", (),
                 "The attic is at its depth everywhere and the hatch is sealed."),
        )),
        Phase("Check it and the inspection", (
            Step("Walk every wall and the attic for gaps, voids and compressed spots; fill them.",
                 "The inspector looks for exactly those.", ("Use a flashlight across the face: gaps show as "
                                                            "shadows.",)),
            Step("Post the insulation certificate (R-values and areas) where your code says, and call for the "
                 "insulation inspection before drywall.", "The certificate is required and is the house's record.",
                 (), "The insulation inspection passed."),
        )),
    ),
    ("International Code Council, International Energy Conservation Code (IECC) 2021 / IRC Chapter 11: N1102.1.2 "
     "(insulation R-values), N1101.10 (certificate), R806 (attic ventilation and baffles)",
     "US Department of Energy, Guide to Home Insulation",
     "North American Insulation Manufacturers Association (NAIMA), Insulation installation guidance",
     "EPA, Protect Your Family from Exposures to Asbestos: Vermiculite Insulation"),
    skill="carpentry",
))

register(Job(
    "air_sealing", "carpentry", "install", "Air seal the house",
    "Sealing the air leaks in a framed house before insulation and drywall: the leakage target the energy code sets, "
    "the top plates, every hole for pipes, cables, ducts and flues, the sill and rim, the attic hatch, recessed "
    "lights, and the wall to the garage; then the blower-door test that proves it. Insulation is the next job.",
    ("air sealing", "air seal", "seal air leaks", "blower door", "drafts", "seal the attic"),
    ("hazmat", "injury"),
    "New houses must meet an air-leakage limit, shown by a blower-door test (and often a visual checklist) before "
    "the final. " + _LOCAL,
    ("spray foam fumes and skin contact", "fire: only noncombustible material touches a flue or chimney",
     "attic heat", "old vermiculite or other suspect material in an older attic"),
    ("a respirator for spray foam", "safety glasses", "gloves", "long sleeves"),
    ("spray-foam gun and cleaner", "caulk gun", "utility knife and tin snips", "a flashlight and a smoke pencil or "
     "incense stick", "a stapler for sheet goods"),
    ("low-expansion and fire-rated spray foam", "acoustical or acrylic sealant", "sheet-metal flashing and "
     "high-temperature sealant for flues", "rigid foam or drywall pieces for big openings", "sill gasket",
     "an insulated, gasketed attic hatch cover", "IC- and airtight-rated recessed lights or their covers"),
    (
        Phase("Plan before sealing", (
            Step("Find your code's air-leakage limit (commonly 3 air changes an hour at 50 pascals in colder zones, "
                 "5 in warm ones) and book the blower-door tester.", "The test is the pass or fail; sealing is how "
                 "you get there.", ("Ask whether a pre-drywall test is allowed: leaks are easy to fix then.",),
                 "You know the target and when the test is."),
            Step("List the leak points room by room: top plates, holes up into the attic, around tubs and stairs, "
                 "the rim, the garage wall, ducts and flues.", "The biggest leaks are hidden in the attic and "
                 "basement, not around windows.",
                 ("Look from the attic side with a light on below: light shows the holes.",)),
        )),
        Phase("Seal the big holes first", (
            Step("Cover large openings (chases, soffits, dropped ceilings, behind tubs) with rigid foam or drywall "
                 "pieces, sealed at their edges.", "Foam alone can't span a big hole.",
                 ("Seal every edge of the patch, not just the middle.",)),
            Step("Flash around flues and chimneys with sheet metal and high-temperature sealant only.",
                 "Foam or batts against a flue is a fire.", ("Keep the clearance the flue's listing gives.",)),
            Step("Seal the garage-to-house wall and ceiling completely, including every hole through it.",
                 "Car exhaust and fumes follow any gap into the house.",
                 ("Self-closing, tight door to the garage too.",)),
            Step("Seal around window and door frames inside (low-expansion foam already in) and the electrical "
                 "boxes on outside walls with gaskets or airtight boxes.", "Small leaks add up across a house.",
                 ()),
        )),
        Phase("Seal the small leaks", (
            Step("Foam or caulk every hole through the top plates and floors for pipes, cables and ducts.",
                 "Each is a chimney for warm air.", ("Fire-rated foam where your code calls for fire blocking.",)),
            Step("Seal the sill and rim (gasket or foam), and the bottom plates of outside walls to the subfloor.",
                 "The bottom of the house is where cold air comes in.", ()),
            Step("Seal the duct boots to the drywall or subfloor and every duct joint with mastic or listed tape.",
                 "Leaky ducts pull air from the attic and walls.", ("Ordinary cloth duct tape fails: use mastic.",)),
            Step("Gasket the attic hatch, and use airtight recessed lights (or covers rated for them).",
                 "A loose hatch is one big hole.", (), "Every listed leak point is sealed."),
        )),
        Phase("Test and inspection", (
            Step("Run a pre-drywall check if you can: the blower door on, a smoke pencil along the plates, boxes and "
                 "penetrations, and seal what moves the smoke.", "Leaks found now are minutes; after drywall, "
                 "hours.", ()),
            Step("Have the final blower-door test done, keep its report, and fix and retest if it misses.",
                 "The report is required at the final.", (), "The house meets its air-leakage limit."),
        )),
    ),
    ("International Code Council, International Energy Conservation Code (IECC) 2021 / IRC Chapter 11: N1102.4 "
     "(air leakage, Table N1102.4.1.1), N1103.3 (duct sealing)",
     "US Department of Energy, Building America Solution Center: air sealing guides",
     "ENERGY STAR, A Do-It-Yourself Guide to Sealing and Insulating with ENERGY STAR",
     "Building Science Corporation, BSI-097: The Five Things"),
    skill="carpentry",
))

register(Job(
    "drywall_hang_finish", "carpentry", "install", "Hang and finish drywall",
    "Gypsum board on walls and ceilings after the insulation inspection: the right board and thickness (fire-rated "
    "where the garage meets the house), ceilings first, walls horizontal, fastened to the code's schedule, joints "
    "planned off the corners of openings, corner bead, tape and three coats, sanded smooth and primed.",
    ("drywall", "sheetrock", "hang drywall", "tape and mud", "finish drywall", "gypsum board"),
    ("fall", "injury"),
    "Drywall itself rarely needs its own inspection, but the garage fire separation and fastening can be checked. " +
    _LOCAL,
    ("lifting sheets overhead", "falls from ladders, benches and scaffold", "joint-compound dust when sanding",
     "knife cuts"),
    ("a dust mask or respirator for sanding", "safety glasses", "gloves for carrying"),
    ("drywall T-square and utility knife", "drywall screw gun or driver with a dimpler bit", "drywall lift (rented) "
     "for ceilings", "rotary cutout tool or keyhole saw", "taping knives (6, 10 and 12 in) and a mud pan",
     "corner tools", "sanding pole and sponges", "benches or scaffold"),
    ("1/2 in board for walls, 5/8 in for ceilings at 24 in spacing", "5/8 in Type X where the garage meets the house",
     "moisture-resistant board in baths (cement board in showers)", "drywall screws (1 1/4 in for 1/2 in board)",
     "paper or mesh tape", "joint compound (setting type for the first coat, all-purpose or topping after)",
     "metal or paper-faced corner bead", "drywall primer"),
    (
        Phase("Plan before hanging", (
            Step("Plan each room's sheets: the longest sheets you can handle, walls hung horizontal, and joints that "
                 "don't land in line with the corners of doors and windows.", "Joints at an opening's corner crack.",
                 ("Fewer joints is less finishing.",), "Every room's layout and board type is decided."),
            Step("Check the insulation inspection has passed and mark every stud and joist on the floor and the top "
                 "plate.", "Screws that miss the framing pop later.", ()),
        )),
        Phase("Hang the board", (
            Step("Hang the ceilings first (with a lift), board perpendicular to the joists, screws at the schedule "
                 "(commonly 12 in on center).", "The walls then hold the ceiling's edges up.",
                 ("Fire-rated ceilings use the fastening their rating lists.",)),
            Step("Hang the walls, top sheet first tight to the ceiling, bottom sheet lifted with a foot lever, "
                 "screws at about 16 in on walls, 3/8 in from the edges.", "A tight top joint makes the corner "
                 "easy to tape.", ("Dimple each screw just below the paper without tearing it.",)),
            Step("Cut out boxes and openings with the rotary tool after the sheet is tacked, then finish fastening.",
                 "Cutting in place lines the holes up exactly.", ()),
            Step("Hang 5/8 in Type X on the garage side of every wall and ceiling that separates it from the house, "
                 "joints taped.", "It's the fire barrier between the car and the bedrooms.", (),
                 "Every wall and ceiling is hung and fastened, with the fire separation complete."),
        )),
        Phase("Tape and coat", (
            Step("Set corner bead on outside corners, then tape every joint and inside corner bedded in compound "
                 "(setting type first coat).", "Tape bedded with air under it blisters.",
                 ("Press out the excess with the knife.",)),
            Step("Second coat wider with the 10 in knife; third coat wider again with the 12 in, feathering the "
                 "edges.", "Wide, thin coats hide the joint.", ()),
            Step("Spot every screw three times along with the joints.", "Screw heads show through paint otherwise.",
                 ("Skip none: one missed screw shows.",)),
            Step("Sand smooth with a pole sander, checking with a light held flat against the wall.", "Raking light "
                 "shows every ridge the paint would.", ("Don't sand through to the tape.",),
                 "Every joint, corner and screw is smooth under raking light."),
        )),
        Phase("Prime and check", (
            Step("Prime with a drywall primer.", "Primer evens the paper and the compound so paint looks the same "
                 "everywhere.", ("Ordinary paint as a primer flashes over the joints.",)),
            Step("Look over every wall after priming and fix what shows; have the fire separation checked if your "
                 "inspector asks.", "Primer reveals what sanding missed.", (),
                 "The walls are primed and any inspection passed."),
        )),
    ),
    (_IRC + ": R702.3 (gypsum board: Table R702.3.5 fastening), R302.6 (garage separation)",
     "Gypsum Association, GA-216: Application and Finishing of Gypsum Panel Products",
     "Myron R. Ferguson, Drywall: Professional Techniques for Great Results (Taunton, 4th ed.)",
     "USG, The Gypsum Construction Handbook"),
    skill="drywall",
))

register(Job(
    "interior_trim", "carpentry", "install", "Hang interior doors and run the trim",
    "Finish carpentry after the drywall is primed: prehung interior doors set plumb with even gaps, door and window "
    "casing with consistent reveals and tight miters, and baseboard coped at inside corners and scarfed on long "
    "runs, all nailed to framing and filled for paint.",
    ("interior trim", "trim carpentry", "baseboard", "casing", "hang interior doors", "finish carpentry"),
    ("injury",),
    "Interior trim needs no permit of its own. " + _LOCAL,
    ("miter saw injuries", "nail gun injuries", "dust from MDF trim"),
    ("safety glasses", "hearing protection", "a dust mask for MDF"),
    ("miter saw", "coping saw or coping tool", "finish nailer (15 or 16 gauge) and brad nailer", "4 ft and 6 ft "
     "levels", "combination square and a reveal gauge", "block plane", "stud finder"),
    ("prehung interior doors", "door and window casing", "baseboard and shoe or quarter round", "shims",
     "finish nails and brads", "wood glue", "wood filler and paintable caulk"),
    (
        Phase("Plan before cutting", (
            Step("Let the trim acclimate in the house for a few days, and mark every stud at floor level.",
                 "Trim that shrinks after it's nailed opens its joints.", ("Store it flat, not leaning.",),
                 "The trim is acclimated and the studs are marked."),
            Step("Check the door openings for plumb and the floor for level where doors swing.", "A door hung in a "
                 "racked opening drifts open or shut.", ()),
        )),
        Phase("Doors", (
            Step("Set each prehung door: shim the hinge side plumb behind each hinge, then the latch side for an "
                 "even 1/8 in gap, nailing through the shims.", "Shims behind the hinges carry the door's weight.",
                 ("Check the gap at the head: it shows any twist.",)),
            Step("Replace one screw in the top hinge with a long screw into the framing, and test the swing and "
                 "latch.", "The long screw stops the door sagging over the years.", (),
                 "Every door swings freely, latches and stays where it's left."),
        )),
        Phase("Casing", (
            Step("Mark a 3/16 in reveal on each jamb, cut the head casing's miters, and dry-fit them before nailing.",
                 "An even reveal is what makes casing look right.", ("Walls not flat: plane the back of the casing "
                                                                     "to sit tight.",)),
            Step("Nail the casing to the jamb with brads and to the framing with finish nails, gluing the miters.",
                 "Glued miters stay closed when the wood moves.", ("Pin the miter across the corner.",)),
            Step("Case the windows the same way (with the stool and apron if the design has them).",
                 "Matching reveals across a room look intentional.", (),
                 "Every opening is cased with tight miters and even reveals."),
        )),
        Phase("Baseboard", (
            Step("Run the baseboard: square cut into one inside corner, cope the next piece to it, miter outside "
                 "corners, scarf joints on long walls over a stud.", "A coped joint stays tight as the walls move; "
                 "a miter opens.", ("Back-cut the cope slightly so the face closes.",)),
            Step("Nail into the studs and the bottom plate; add shoe molding to cover gaps at the floor.",
                 "Nailing into framing holds it; drywall alone doesn't.", ()),
            Step("Check every joint and reveal before filling.", "A bad joint is easier to recut than hide.", (),
                 "Every corner is tight and every piece is nailed to framing."),
        )),
        Phase("Fill and check for paint", (
            Step("Set and fill the nail holes, caulk the trim to the wall (not the miters), and sand the filler flush.",
                 "Caulk in a miter cracks; filled miters sand smooth.", ("Caulk the gap between trim and wall only.",)),
            Step("Look over every room in raking light and fix what shows before paint.", "Paint shows every hole "
                 "and gap left now.", (), "Every room's trim is filled, caulked and ready for paint."),
        )),
    ),
    ("Gary Katz, The Doorhanger's Handbook (Taunton, 1998)",
     "Craig Savage, Trim Carpentry Techniques (Taunton, 1989)",
     "Fine Homebuilding, Trim Carpentry: The Complete Guide"),
    skill="carpentry",
))

register(Job(
    "paint_interior", "carpentry", "install", "Paint the interior",
    "Painting the walls, ceilings and trim of a house: testing old paint for lead first, protecting floors, repairing "
    "and sanding, priming, cutting in and rolling ceilings then walls, then trim with an enamel, in the right sheen "
    "for each room, with the drying and recoat times respected.",
    ("paint", "paint the walls", "interior painting", "paint the house inside", "paint a room", "paint trim"),
    ("hazmat", "fall", "injury"),
    "Painting needs no permit, but in a house built before 1978 the EPA's lead-safe rules apply to anyone paid to "
    "disturb old paint, and the same methods keep a family safe. " + _LOCAL,
    ("lead dust from sanding old paint (houses before 1978)", "solvent fumes in a closed room",
     "falls from ladders and planks", "eye splashes rolling ceilings"),
    ("safety glasses", "a respirator for sanding and solvent-based products", "gloves"),
    ("angled sash brush (2 1/2 in)", "roller frames, 3/8 in and 1/2 in covers, an extension pole", "trays or a "
     "5-gallon bucket and grid", "putty knife and sanding sponges", "drop cloths and painter's tape", "a stepladder "
     "and a plank", "a lead test kit (houses before 1978)"),
    ("primer (stain-blocking where needed)", "ceiling paint (flat)", "wall paint (eggshell or satin; satin or "
     "semi-gloss in baths and kitchens)", "trim enamel (semi-gloss)", "spackle and caulk", "drop cloths and tape"),
    (
        Phase("Plan and prepare before painting", (
            Step("In a house built before 1978, test the old paint for lead before sanding or scraping.",
                 "Lead dust is a serious hazard and spreads through a house.", ("Positive: follow lead-safe "
                                                                                "methods or hire certified help.",),
                 "You know whether the paint has lead."),
            Step("Choose the products and sheens for each room, and work out the paint: a gallon covers about 350 "
                 "to 400 sq ft a coat.", "Two coats over a primer is the normal finish.", ()),
            Step("Empty or center the room, cover the floor, remove plates and hardware, and tape what won't be "
                 "painted.", "Paint on a floor or a switch plate is the mark of a rushed job.", ()),
        )),
        Phase("Repair and prime", (
            Step("Fill holes and cracks, sand them flush, and clean the walls (degrease kitchens and baths).",
                 "Paint doesn't stick to grease or dust.", ("Wet-sand or use a vacuum sander for less dust.",)),
            Step("Prime new drywall, repairs, stains and any glossy surface.", "Primer evens the surface and blocks "
                 "stains from bleeding through.", ("Water stains need a stain-blocking primer.",),
                 "Every repair is sanded and primed."),
        )),
        Phase("Paint", (
            Step("Ventilate while you paint and while it dries: a window open and a fan blowing out.",
                 "Fumes build up in a closed room, and paint dries better with air moving.",
                 ("Below about 50 F, most paints won't cure: check the can.",)),
            Step("Ceilings first: cut in the edges with a brush, then roll in one direction while the cut-in is "
                 "still wet.", "Rolling into a wet edge hides the brush marks.", ("Keep a wet edge: stop only at a "
                                                                                  "corner.",)),
            Step("Walls next: cut in a wall, then roll it top to bottom in a W pattern, finishing in one direction; "
                 "second coat after the recoat time.", "The second coat is what makes the color even.",
                 ("Don't recoat early: the first coat lifts.",)),
            Step("Trim last with enamel: doors, casing, baseboard, light coats brushed along the grain.",
                 "Trim painted last can be cut in cleanly against the walls.", ("Thin coats: enamel runs.",),
                 "Ceilings, walls and trim have their full coats."),
        )),
        Phase("Check, clean up and finish", (
            Step("Pull the tape while the paint is still slightly soft, at an angle.", "Dry paint tears with the "
                 "tape.", ()),
            Step("Check every wall in daylight and lamplight for thin spots and holidays; touch them up.",
                 "Different light shows different misses.", ()),
            Step("Replace plates and hardware, clean the brushes and rollers, and label leftover paint by room.",
                 "Touch-ups years later need the exact color.", (),
                 "Every room is painted, checked and put back."),
        )),
    ),
    ("EPA, Renovation, Repair and Painting Rule (40 CFR 745) and its Steps to Lead Safe Renovation guide",
     "Paint Quality Institute, Interior Painting guidance",
     "Brian Santos, Painting and Wallpapering (Taunton, 2004)"),
    skill="carpentry",
))

register(Job(
    "flooring_lvp", "carpentry", "install", "Lay a floating vinyl plank floor",
    "Click-together luxury vinyl plank (LVP) floated over a flat subfloor: the subfloor checked flat and dry, old "
    "flooring tested before removal, the planks acclimated, the room laid out so the first and last rows aren't "
    "slivers, rows clicked with staggered ends, expansion gaps kept at every wall, and transitions and trim fitted.",
    ("vinyl plank", "lvp", "luxury vinyl", "floating floor", "install flooring", "click flooring"),
    ("hazmat", "injury"),
    "Flooring needs no permit in most places. Old sheet vinyl, tile or their adhesive in a house before 1980 can "
    "hold asbestos. " + _LOCAL,
    ("asbestos in old sheet vinyl, 9 in tiles or black mastic", "utility-knife and saw cuts", "knee strain"),
    ("knee pads", "safety glasses when cutting", "gloves"),
    ("utility knife and straightedge", "tapping block and pull bar", "rubber mallet", "jigsaw or oscillating tool "
     "for door jambs", "6 ft straightedge", "spacers", "a moisture meter (concrete or wood)", "tape and square"),
    ("vinyl planks (area plus 10% waste)", "underlayment if the planks have none attached", "a vapor retarder over "
     "concrete if the maker asks", "floor leveler for low spots", "transitions and reducers", "baseboard or shoe "
     "molding"),
    (
        Phase("Plan and prepare before laying", (
            Step("In a house before 1980, test any old sheet vinyl, tile or black adhesive before pulling it up.",
                 "Disturbing asbestos flooring releases fibers.", ("Positive: leave it and float over, or have it "
                                                                   "abated.",), "You know what the old floor is."),
            Step("Check the subfloor is flat (commonly within 3/16 in over 10 ft), dry by the meter, and clean; "
                 "fill low spots and grind or sand high ones.", "Floating floors telegraph every dip and clicks "
                 "apart over bumps.", ("Concrete moisture above the maker's limit: a vapor retarder first.",)),
            Step("Acclimate the planks in the room as the maker says, and undercut the door jambs so planks slide "
                 "under.", "Undercut jambs give a clean edge with no caulk.",
                 ("Use a plank on its underlayment as the saw's height guide.",)),
        )),
        Phase("Layout", (
            Step("Measure the room's width in planks and adjust the first row's width so the last row is at least "
                 "a third of a plank.", "Thin rows break at the clicks.", ("Run planks along the longest wall or "
                                                                            "toward the main light.",)),
            Step("Snap a straight line for the first row (walls are rarely straight) and set spacers for the "
                 "maker's expansion gap at every wall.", "A floor pinned at a wall buckles when it grows.", (),
                 "The first row's line and the gaps are set."),
        )),
        Phase("Lay the floor", (
            Step("Lay the first row tongue toward the wall as the maker shows, cutting the end so the next row's "
                 "joints stagger at least 6 in.", "Staggered ends lock the rows together.", ("No H-patterns "
                                                                                            "(joints lined up "
                                                                                            "every other row).",)),
            Step("Click each row in at its angle, tap the ends with the block, and keep checking the line.",
                 "A row that drifts off line opens gaps three rows later.", ("Never hit the plank's edge "
                                                                            "directly.",)),
            Step("Scribe and cut around jambs, vents and corners, leaving the gap.", "Every fixed object needs its "
                 "gap too.", ("Pipes: drill a hole a little bigger than the pipe and fill the gap with a collar.",)),
            Step("Rip the last row to width, leaving the gap, and lock it with the pull bar.", "The last row is "
                 "where most floors are rushed.", (), "Every row is clicked tight with gaps at every wall."),
        )),
        Phase("Finish and check", (
            Step("Fit transitions at doorways and other floors, fastened to the subfloor, not the planks.",
                 "A floating floor must stay free to move.", ()),
            Step("Install the baseboard or shoe nailed to the wall, never to the floor, covering the gaps.",
                 "Nailing trim to the floor pins it.", ()),
            Step("Walk the whole floor for gaps, peaked joints and hollow spots, and keep spare planks.",
                 "A damaged plank is easy to replace with a spare from the same lot.", (),
                 "The floor is flat, tight and free at every edge."),
        )),
    ),
    ("The flooring maker's installation instructions (they govern the warranty)",
     "ASTM F710, Standard Practice for Preparing Concrete Floors to Receive Resilient Flooring",
     "Resilient Floor Covering Institute, Recommended Work Practices for Removal of Resilient Floor Coverings"),
    skill="carpentry",
))

register(Job(
    "tile_floor", "carpentry", "install", "Tile a floor",
    "Ceramic or porcelain tile on a floor: the subfloor stiff enough for tile and flat, a cement backer or "
    "uncoupling membrane, a layout from the room's center lines with no slivers at the doorways, thinset with full "
    "coverage, even joints with movement joints at the edges, grout and sealing. A shower pan is a different job.",
    ("tile floor", "tile a floor", "floor tile", "lay tile", "porcelain tile", "ceramic tile", "tiling"),
    ("hazmat", "injury"),
    "Floor tile needs no permit in most places. Old flooring in a house before 1980 can hold asbestos. " + _LOCAL,
    ("silica dust cutting tile dry", "wet-saw blade and water near power", "lifting thinset bags and tile boxes",
     "knee strain", "old flooring with asbestos"),
    ("a respirator rated for silica when cutting dry", "safety glasses", "knee pads", "gloves for thinset"),
    ("wet tile saw and a manual cutter", "notched trowels (size for the tile)", "margin trowel and mixing paddle",
     "levels and a straightedge", "chalk line and a framing square", "rubber grout float and sponges",
     "tile leveling system (for large tile)"),
    ("tile (area plus 10% waste, more for diagonal)", "cement backer board or an uncoupling membrane", "modified "
     "thinset rated for the tile and the substrate", "backer-board screws and alkali-resistant mesh tape",
     "spacers", "grout (sanded or unsanded for the joint width)", "flexible sealant for movement joints",
     "grout sealer if the grout needs it"),
    (
        Phase("Plan and prepare before setting", (
            Step("Check the floor is stiff enough: joists sized for tile (a deflection of span/360 for ceramic, "
                 "span/720 for natural stone), a subfloor of 3/4 in or more, and flat to the tile's tolerance.",
                 "A floor that flexes cracks tile and grout.", ("Bouncy floor: stiffen it first.",),
                 "The floor is stiff and flat enough for the tile."),
            Step("In a house before 1980, test any old flooring or black adhesive before removing it.",
                 "Old floors can hold asbestos.", ("Positive: leave it covered or have it abated.",)),
            Step("Screw down cement backer in a bed of thinset (or lay the membrane in thinset) to the maker's "
                 "pattern, seams taped.", "The backer or membrane is what the tile actually bonds to.",
                 ("Stagger the backer's seams from the subfloor's.",)),
        )),
        Phase("Layout", (
            Step("Snap the room's center lines square to each other, then dry-lay a row each way to see the cuts at "
                 "the walls and doorways.", "Moving the layout half a tile avoids slivers at the door.",
                 ("Full tiles at the doorway where you can.",)),
            Step("Snap working lines a few tiles apart to keep the rows straight.", "Joints drift without lines.",
                 (), "The layout puts no sliver at a doorway or the main wall."),
        )),
        Phase("Set the tile", (
            Step("Mix the thinset to the maker's consistency, let it slake, and spread it with the notched trowel in "
                 "straight lines; back-butter large tile.", "Straight trowel lines let air out so the tile beds "
                 "fully.", ("Lift a tile now and then: coverage should be 80% or more, 95% in wet areas.",)),
            Step("Set each tile with a slight slide across the ridges, spacers in, and check flat and line as you "
                 "go.", "Lippage (edges out of plane) is the most visible flaw.",
                 ("Clean thinset out of the joints before it sets.",)),
            Step("Stay off the tile until the thinset cures (commonly 24 hours), and protect it from traffic.",
                 "Tile walked on too soon loses its bond.", ("Cold rooms cure slower: check the bag.",)),
            Step("Leave a 1/4 in movement joint at every wall and fixed edge, and at the field joints your area "
                 "calls for (commonly every 20 to 25 ft inside).", "Tile without room to move tents up.", (),
                 "The tile is set flat and lined up, with movement joints at the edges."),
        )),
        Phase("Grout and check", (
            Step("After the thinset cures, grout the joints with the float on the diagonal, then sponge it with a "
                 "barely damp sponge.", "Too much water weakens grout and washes it out.", ("Clean the haze "
                                                                                           "within the grout "
                                                                                           "maker's time.",)),
            Step("Fill the movement joints with flexible sealant, not grout, and seal the grout if it needs it.",
                 "Grout in a movement joint cracks out.", ()),
            Step("Check for hollow tiles (tap them), cracked grout and lippage before the trim goes on.",
                 "A hollow tile cracks later.", (), "Every tile is bonded, grouted and sealed."),
        )),
    ),
    ("Tile Council of North America, TCNA Handbook for Ceramic, Glass, and Stone Tile Installation",
     "ANSI A108/A118/A136, American National Standard Specifications for the Installation of Ceramic Tile",
     "Michael Byrne, Setting Tile (Taunton, 1995)",
     "OSHA 29 CFR 1926.1153, Respirable Crystalline Silica"),
    skill="carpentry",
))

_PLUMBING_PERMIT = ("Plumbing needs a permit and a rough-in inspection with the pipes tested and still open to view. "
                    "Many places let a homeowner do it on their own home under that permit; others require a "
                    "licensed plumber. " + _LOCAL)

register(Job(
    "rough_plumbing_dwv", "plumbing", "install", "Rough in the drains and vents (DWV)",
    "The drain, waste and vent piping in a framed house before the walls close: pipes sized by fixture units, drains "
    "sloped, the right fittings for each change of direction, traps and trap arms within their distances, vents "
    "through the roof, cleanouts, holes through framing kept inside the limits, and the system tested and inspected. "
    "Supply piping is the next job.",
    ("drain lines", "rough in plumbing", "dwv", "drain waste vent", "plumbing vents", "rough plumbing"),
    ("licensed", "structural", "fall", "injury"),
    _PLUMBING_PERMIT,
    ("cuts from saws and pipe", "primer and cement fumes in a closed space", "framing weakened by holes cut too big",
     "falls working at the roof penetration"),
    ("safety glasses", "gloves for primer and cement", "a respirator in a closed space"),
    ("PVC or ABS saw and deburring tool", "drill with hole saws and a right-angle drill", "levels (torpedo and "
     "4 ft)", "tape and marker", "test plugs or test balls and a gauge", "ladder for the roof vent"),
    ("PVC or ABS pipe and fittings (sanitary tees, wyes, long sweeps)", "primer and cement for the material",
     "pipe hangers and straps", "cleanout fittings and plugs", "roof vent flashing boots", "steel nail plates",
     "test caps"),
    (
        Phase("Plan and permit before cutting", (
            Step("Draw the system: every fixture, its drain and trap size, the fixture units on each branch, the "
                 "building drain and stack sizes from the code tables, and how each fixture is vented.",
                 "Undersized drains clog; unvented traps siphon dry and let sewer gas in.",
                 ("Ask whether your area allows air admittance valves.",),
                 "The plan sizes every pipe and vents every trap, and the permit is in hand."),
            Step("Find where pipes cross joists and studs and plan the holes inside the limits (bored holes in "
                 "studs no bigger than 40% of the stud in a bearing wall, 60% in a non-bearing one).",
                 "Cutting framing past its limit weakens the house.", ("No notches in the middle third of a joist.",)),
        )),
        Phase("Drains", (
            Step("Run the building drain and branches sloped 1/4 in per foot (1/8 in for 3 in pipe and larger "
                 "where allowed), supported at the code's spacing.", "Too little slope leaves solids; too much "
                 "leaves them behind the water.", ("Check slope with a level on every run.",)),
            Step("Use the right fitting for each turn: wyes and long sweeps where drainage turns horizontal, "
                 "sanitary tees only from horizontal into vertical.", "A sanitary tee laid flat clogs.", ()),
            Step("Set each toilet's closet flange at finished-floor height, centered at the toilet's rough-in "
                 "distance (commonly 12 in from the finished wall) and anchored to the floor.", "A flange set low "
                 "or loose is a leaking toilet.", ("Measure from the finished wall, not the stud.",)),
            Step("Set each trap and keep the trap arm within its distance from the vent (from the code's table).",
                 "Too long an arm siphons the trap dry.", ("A 1 1/2 in arm is commonly limited to 6 ft.",)),
            Step("Add a cleanout at the base of each stack, at changes of direction over 45 degrees as required, "
                 "and where the drain leaves the house.", "Every clog needs a way in.", (),
                 "Every drain slopes, turns on the right fitting, and has its cleanouts."),
        )),
        Phase("Vents", (
            Step("Run the vents up from each trap arm, rising before they turn flat, tied into the stack or a vent "
                 "header above the highest fixture's flood rim.", "A vent that runs flat below the flood rim fills "
                 "with water.", ()),
            Step("Take the main vent through the roof with a flashing boot, at the height your code asks above the "
                 "roof.", "The roof vent lets the whole system breathe.", ("Keep it away from windows and "
                                                                          "intakes as the code says.",)),
            Step("Protect every pipe within 1 1/4 in of a stud or joist face with a steel nail plate.",
                 "Drywall screws through a drain are a leak inside the wall.", (),
                 "Every trap is vented and every pipe near a face is plated."),
        )),
        Phase("Test and rough-in inspection", (
            Step("Cap the openings and test: fill the system with water to 10 ft above the highest fitting, or air "
                 "at 5 psi, held 15 minutes with no drop.", "A leak found now is a fitting; after drywall it's a "
                 "wall.", ("Air-testing plastic only if its maker allows.",)),
            Step("Call for the rough-in inspection with the test on and the walls open.", "The inspector checks "
                 "sizes, slope, venting and the test.", (), "The rough-in inspection passed."),
        )),
    ),
    (_IRC + ": P2503 (testing), P2603 (structural safety and protection), P3005 (drainage: Table P3005.4.1 fixture "
     "units, P3005.3 slope), P3002 (materials), P3100 to P3114 (vents, Table P3105.1 trap arms)",
     "International Code Council, International Plumbing Code (IPC) 2021",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)",
     "Charlotte Pipe, Plastics Technical Manual (DWV installation and testing)"),
    skill="plumbing",
))

register(Job(
    "rough_plumbing_supply", "plumbing", "install", "Rough in the water supply",
    "The hot and cold water piping in a framed house: the main shutoff, pipe sized for the fixtures, a manifold or "
    "trunk and branches in PEX (or copper), shutoffs and stub-outs at each fixture, the water heater's connections, "
    "freeze protection, support and nail plates, and a pressure test and inspection. The water heater itself and "
    "the fixtures are their own jobs.",
    ("water lines", "supply lines", "pex", "rough in the water", "water supply", "run water lines"),
    ("licensed", "structural", "injury"),
    _PLUMBING_PERMIT,
    ("scalding when connecting to a live hot line", "cuts and burns (soldering copper)", "pipes freezing in outside "
     "walls", "framing weakened by holes cut too big"),
    ("safety glasses", "gloves", "a fire extinguisher close by when soldering"),
    ("PEX cutter and the crimp, clamp or expansion tool for the system", "drill with bits and a right-angle drill",
     "tape and marker", "a test gauge and pump", "torch, flux and solder if copper"),
    ("PEX tubing (red, blue) or copper pipe", "a manifold or tees and fittings for the system", "full-port ball "
     "valves for the main and each branch", "stub-outs, drop-ear elbows and fixture supports", "water hammer "
     "arrestors", "tube supports and hangers", "steel nail plates", "pipe insulation"),
    (
        Phase("Plan and permit before running pipe", (
            Step("Size the service and the branches from the fixtures they serve (commonly 3/4 in mains and 1/2 in "
                 "to each fixture) and choose a manifold or trunk-and-branch layout.", "Undersized pipes starve a "
                 "shower when a toilet flushes.", ("Long runs to a far bathroom: size up.",),
                 "Every pipe is sized and the permit is in hand."),
            Step("Plan routes that stay out of outside walls and unheated spaces wherever possible.", "Pipes in a "
                 "cold outside wall freeze.", ()),
        )),
        Phase("Main and distribution", (
            Step("Set the main shutoff where the water enters, and the manifold or the trunks from it, with hot and "
                 "cold kept apart.", "One valve has to shut off the whole house fast.", ()),
            Step("Rough in the water heater's cold supply with its own shutoff and the hot line out of it, and plan the "
                 "relief valve's discharge line to a safe drain point.", "The relief line is what keeps a "
                 "failed heater from becoming a bomb.", ("Never cap or reduce a relief discharge line.",)),
            Step("Run each line to its fixture, supported at the maker's spacing (PEX commonly every 32 in "
                 "horizontally), with gentle bends and sleeves through concrete.", "Unsupported PEX sags and "
                 "kinks.", ("Keep PEX out of sunlight and away from flues and recessed lights.",)),
            Step("Make every connection with the system's own fittings and tool, checking each crimp or clamp with "
                 "its gauge.", "An under-crimped fitting holds at first and leaks later.", ("Gauge every "
                                                                                           "fitting, not every "
                                                                                           "other.",)),
        )),
        Phase("Fixtures and protection", (
            Step("Stub out at each fixture at the height its maker lists (hot on the left), secured to blocking, "
                 "capped for the test.", "Loose stub-outs move when a faucet is tightened.", ()),
            Step("Add water hammer arrestors at quick-closing valves (washer, dishwasher, ice maker).",
                 "Fast-closing valves bang the pipes without them.", ()),
            Step("Install frost-free hose bibs with built-in backflow prevention, sloped to drain outward.",
                 "A bib that holds water freezes and splits inside the wall.", ("Long enough that the valve sits "
                                                                                "inside the heated wall.",)),
            Step("Plate every pipe within 1 1/4 in of a framing face, and insulate any pipe in an outside wall or "
                 "unheated space.", "Nails and frost are the two ways supply pipes fail inside walls.",
                 ("Insulate hot lines everywhere if your energy code asks.",),
                 "Every line is supported, stubbed, plated and protected."),
        )),
        Phase("Test and rough-in inspection", (
            Step("Pressure-test the whole system with water at its working pressure (or the test pressure your code "
                 "gives) for 15 minutes with no drop; air only where the pipe's maker allows.", "A leak found now "
                 "is one fitting.", ("Check every fitting dry with a paper towel.",)),
            Step("Call for the rough-in inspection with the test on and the walls open; label the manifold.",
                 "The labels let anyone shut one fixture off.", (), "The rough-in inspection passed."),
        )),
    ),
    (_IRC + ": P2503.7 (water supply test), P2605 (support, Table P2605.1), P2603 (protection), P2903 (water supply "
     "sizing), P2906 (materials)",
     "Plastics Pipe Institute, PEX Design Guide",
     "Copper Development Association, The Copper Tube Handbook",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)"),
    skill="plumbing",
))

register(Job(
    "water_heater", "plumbing", "install", "Replace an electric water heater",
    "Replacing a tank-type electric water heater: sized and matched to its circuit, the power proven off and the "
    "tank drained, the new one set in a drain pan, connected with a shutoff and an expansion tank where required, "
    "the relief valve's discharge run full size to a safe point, filled completely before any power, then wired and "
    "set to 120 F. A gas heater's gas and vent connections are a licensed gas fitter's work in most places.",
    ("water heater", "replace the water heater", "hot water heater", "new water heater", "install a water heater"),
    ("live_power", "licensed", "gas", "injury"),
    "Replacing a water heater needs a permit in most places, with an inspection of the relief valve, the expansion "
    "tank and the connections. " + _LOCAL,
    ("scalding water while draining", "electric shock at the heater's wiring", "a full tank weighs 400 lb or more",
     "a relief valve that can't discharge (an explosion risk)", "water damage if a fitting leaks"),
    ("safety glasses", "gloves for hot water", "insulated gloves when testing for power"),
    ("non-contact and two-lead voltage testers", "pipe wrenches and adjustable wrenches", "tubing cutter",
     "garden hose for draining", "appliance dolly", "screwdrivers and a nut driver", "thread sealant and tape"),
    ("the water heater (same voltage and element wattage as the circuit allows)", "drain pan with a drain line",
     "flexible water connectors or dielectric unions", "a full-port shutoff for the cold supply", "thermal "
     "expansion tank (if the system is closed by a check valve or pressure regulator)", "relief-valve discharge "
     "pipe (rated for the temperature, full size)", "seismic straps where required"),
    (
        Phase("Plan and permit before you start", (
            Step("Match the new heater to the old: the same voltage and an element wattage the circuit is sized for "
                 "(a 4500 W, 240 V heater on a 30 A circuit with 10 AWG wire), and the gallons you need.",
                 "A heater bigger than its circuit overheats the wiring.", ("Different wattage: check the circuit "
                                                                           "and breaker with the permit office.",),
                 "You have the right heater, the permit, and the parts list."),
            Step("Check whether your system is closed (a check valve or pressure regulator on the main) and needs "
                 "an expansion tank, and whether straps are required where you live.", "Without an expansion tank "
                 "a closed system makes the relief valve drip or weep.", ()),
        )),
        Phase("Shut off and drain", (
            Step("Turn off the heater's breaker, then prove it dead at the heater's wiring box: test the tester on "
                 "a live circuit, test the wires, test the tester again.", "A tester that has failed reads dead on "
                 "a live wire.", ("Lock or tag the breaker so no one turns it back on.",)),
            Step("Close the cold supply, open a hot tap, let the tank cool if you can, then drain it through a hose "
                 "to a floor drain or outside.", "Water from the tank can scald.", ("A clogged drain valve: let it "
                                                                                   "cool and open the relief "
                                                                                   "valve to break the vacuum.",)),
            Step("Disconnect the wiring (noting which wire went where) and the water lines, and move the old tank "
                 "out on a dolly.", "Even empty, a tank is awkward and heavy.", (),
                 "The old heater is out, the power proven off and the lines open."),
        )),
        Phase("Set and connect", (
            Step("Set the drain pan (its drain line run to a drain or outside) and the new heater in it, level, "
                 "strapped where required.", "The pan catches a slow leak before it ruins a floor.", ()),
            Step("Connect the cold to the inlet with the shutoff, the hot to the outlet, with flexible connectors "
                 "or dielectric unions, and the expansion tank on the cold line if needed.", "Dielectric fittings "
                 "stop steel and copper corroding where they meet.", ("Inlet and outlet are marked: don't swap "
                                                                      "them.",)),
            Step("Install the relief valve's discharge pipe full size, with no valve or cap, ending within 6 in of "
                 "the floor or at an approved drain where it can be seen.", "If the relief valve opens, scalding "
                 "water has to go somewhere safe and someone has to notice.", ("Never reduce, cap or thread the "
                                                                              "end.",),
                 "Water lines, expansion tank and relief discharge are connected."),
        )),
        Phase("Fill before power", (
            Step("Open the cold supply and a hot tap and fill until water runs steadily from the tap with no air.",
                 "An element powered in an empty tank burns out in seconds.", ("Never turn the breaker on before "
                                                                               "the tank is full.",)),
            Step("Check every fitting for leaks, then connect the wiring (ground first, a cable connector at the "
                 "box), close the cover, and turn the breaker on.", "A loose connection here is a fire.", (),
                 "The tank is full, dry at every fitting, and powered."),
        )),
        Phase("Check it and final inspection", (
            Step("Set both thermostats to 120 F and check the hot water after an hour or two.", "120 F prevents "
                 "scalds and saves energy.", ("Hotter if a dishwasher needs it: use mixing valves.",)),
            Step("Check for leaks again the next day, and call for the inspection; note the date for yearly "
                 "flushing and anode checks.", "Sediment and a spent anode are what shorten a heater's life.", (),
                 "The inspection passed and the heater is making hot water."),
        )),
    ),
    (_IRC + ": P2801 (water heaters), P2804 (relief valves, P2804.6.1 discharge), P2903.4 (thermal expansion), "
     "E4101.5 (water heater branch circuit)",
     "The water heater maker's installation and operating manual",
     "NFPA 70 National Electrical Code (NEC) 2023: 422.13 (storage water heaters)",
     "US Department of Energy, Selecting a New Water Heater"),
    skill="plumbing",
))

register(Job(
    "fixtures_set", "plumbing", "install", "Set the plumbing fixtures",
    "Plumbing finish after the floors and cabinets: toilets on new wax rings, sinks and faucets with their traps and "
    "supply lines, tub and shower valve trim, the dishwasher's water and drain (with its air gap or high loop), and "
    "the washer box; then each fixture tested and the final inspection. The dishwasher's power is the electrical "
    "finish job.",
    ("set fixtures", "install a toilet", "install a faucet", "plumbing fixtures", "set the toilet",
     "install a sink"),
    ("licensed", "injury"),
    _PLUMBING_PERMIT,
    ("lifting a toilet (cracked porcelain cuts)", "water damage from a fitting left loose", "back strain under "
     "sinks"),
    ("gloves", "safety glasses"),
    ("adjustable wrenches and a basin wrench", "channel-lock pliers", "hacksaw or PVC cutter", "level",
     "putty knife", "bucket and towels", "a flashlight"),
    ("toilets with wax rings (or wax-free seals) and closet bolts", "faucets and sink drains", "P-traps and tailpieces",
     "braided supply lines and quarter-turn stops", "plumber's putty or silicone", "tub and shower trim kits",
     "dishwasher supply line and air gap"),
    (
        Phase("Plan before setting", (
            Step("Check each fixture against its rough-in: the toilet's distance from the wall, the faucet's holes, "
                 "the valve's brand matching its trim.", "A trim kit from another brand won't fit the valve.",
                 ("Read each maker's instructions first.",), "Every fixture matches its rough-in."),
            Step("Flush the supply lines with the stops open into a bucket before connecting anything.",
                 "Debris from the rough-in clogs aerators and valves.", ()),
        )),
        Phase("Toilets and sinks", (
            Step("Set each toilet on a new wax ring over the flange bolts, press it down level, and tighten the "
                 "nuts evenly a little at a time.", "Overtightened bolts crack porcelain.", ("A rocking toilet "
                                                                                             "breaks its seal: "
                                                                                             "shim it.",)),
            Step("Caulk the toilet's base to the floor, leaving a gap at the back.", "The gap lets a leaking seal "
                 "show instead of rotting the floor unseen.", ("Use the bolt caps after the caulk.",)),
            Step("Install the faucets and drains on the sinks with putty or silicone as the maker says, then the "
                 "traps, each joint hand-tight plus a quarter turn.", "Slip joints seal with their washers, not "
                 "force.", ("The trap's weir must sit lower than the drain's arm.",)),
            Step("Connect the supply lines to the stops, hand-tight then a quarter turn with a wrench.",
                 "Braided lines crack their fittings when over-tightened.", (),
                 "Every toilet and sink is set, trapped and supplied."),
        )),
        Phase("Tubs, showers and appliances", (
            Step("Install the shower and tub trim, setting the valve's hot limit stop so the water can't come out "
                 "above about 120 F.", "The limit stop prevents scalds.", ("Test with a thermometer.",)),
            Step("Connect the dishwasher's supply and drain, through an air gap or a high loop as your code asks.",
                 "Without them, sink water can siphon into the dishwasher.", ()),
            Step("Run each faucet with its aerator off for a minute, then fit the aerators, and check hot is on "
                 "the left everywhere.", "Debris catches in aerators; hot on the left is what everyone expects.",
                 ("Swapped hot and cold: fix it at the stops, not the handles.",)),
            Step("Install the washer box's valves and the standpipe trap at the height the code gives.",
                 "Too short a standpipe overflows.", (), "Every tub, shower and appliance connection is in."),
        )),
        Phase("Test and final inspection", (
            Step("Turn the water on slowly and run every fixture: fill and drain each sink and tub, flush each "
                 "toilet several times.", "Leaks show under load.", ("Check under every sink with a dry paper "
                                                                     "towel.",)),
            Step("Check again for drips after a few hours, then call for the final plumbing inspection.",
                 "Slow leaks take time to show.", (), "The final plumbing inspection passed."),
        )),
    ),
    (_IRC + ": P2700s (fixtures: P2705 installation, P2708 showers, P2717 dishwashers, P2718 clothes washers), "
     "P2708.4 (shower valve temperature limits)",
     "International Code Council, International Plumbing Code (IPC) 2021",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)",
     "The fixture makers' installation instructions (they govern the warranties)"),
    skill="plumbing",
))

_ELECTRICAL_PERMIT = ("Wiring a house needs an electrical permit with a rough-in inspection (walls open) and a final. "
                      "Many places let a homeowner wire their own home under that permit; others require a licensed "
                      "electrician, and the service itself is usually the utility's and an electrician's. " + _LOCAL)
_NEC = "National Fire Protection Association, NFPA 70 National Electrical Code (NEC) 2023"

register(Job(
    "rough_electrical", "electrical", "install", "Rough in the house wiring",
    "The wiring in a framed house before insulation, with no power on it: the circuits planned to the code (kitchen, "
    "bath, laundry and the rest), boxes placed by the receptacle spacing rules at their heights, cable run, stapled "
    "and protected, grounds made up, smoke and CO alarms wired together, and every run brought to the panel location "
    "unlanded for the rough-in inspection. Connecting at the panel is the finish job.",
    ("rough electrical", "rough in wiring", "wire the house", "run wire", "house wiring", "electrical rough in",
     "wiring the house", "wiring a house"),
    ("live_power", "licensed", "structural", "fall", "injury"),
    _ELECTRICAL_PERMIT,
    ("shock from any circuit already live in a renovation", "framing weakened by holes cut too big",
     "falls from ladders in tall rooms", "drill kickback"),
    ("safety glasses", "work gloves", "hearing protection when drilling"),
    ("right-angle drill with auger bits", "fish tape and glow rods", "wire strippers and lineman's pliers",
     "cable stapler or hammer", "non-contact voltage tester", "tape and a marker", "box height gauge"),
    ("NM cable (14 AWG on 15 A, 12 AWG on 20 A circuits) or the wiring method your area uses", "device and fixture "
     "boxes sized for their fill (fan-rated where a fan may hang)", "cable staples", "steel nail plates",
     "wire connectors and ground pigtails", "smoke and CO alarms (interconnected)"),
    (
        Phase("Plan and permit before drilling", (
            Step("Plan the circuits: at least two 20 A small-appliance circuits for the kitchen counters, a 20 A "
                 "laundry circuit, a 20 A bathroom circuit, dedicated circuits for fixed appliances, and general "
                 "lighting and receptacles, with a load calculation for the service.", "Too few circuits trip; the "
                 "code's minimums are what inspectors count.", ("Ask whether your area adopted the 2023 NEC or an "
                                                                 "earlier one.",),
                 "Every circuit is on a plan with its wire size and breaker, and the permit is in hand."),
            Step("Mark which circuits need GFCI and AFCI protection under your code (kitchens, baths, laundry, "
                 "outdoors, garages, and AFCI for most living areas).", "The protection decides which breakers or "
                 "devices go where.", ()),
        )),
        Phase("Boxes", (
            Step("Lay out receptacles so no point along a wall is more than 6 ft from one (12 ft apart), any wall "
                 "2 ft or wider gets one, and kitchen counters have one within 2 ft of every point.", "These spacing "
                 "rules are what the inspector measures.", ("Count doors and fixed cabinets as wall breaks.",)),
            Step("Mount the boxes at their heights (receptacles commonly 12 to 16 in, switches 44 to 48 in), "
                 "flush with where the drywall face will be.", "A box set back from the drywall fails inspection "
                 "and loosens devices.", ("Use a gauge or a drywall scrap to set the depth.",)),
            Step("Choose each box's size from its fill: the conductors, devices, clamps and grounds it will hold.",
                 "An overfilled box overheats and is hard to work in.",
                 ("All grounds together count as one conductor.",)),
            Step("Add the outdoor, garage, and basement receptacles the code requires (one at the front and back "
                 "of the house, one in each garage bay area), on GFCI-protected circuits.", "These are the "
                 "required ones most often missed.", ("Outdoor boxes need in-use covers later.",)),
        )),
        Phase("Run and protect the cable", (
            Step("Drill holes centered in studs and joists (at least 1 1/4 in from the edge, or plate them), "
                 "within the code's hole limits for the framing.", "Drywall screws find cable near a face.",
                 ("No holes in the middle third of a joist's edge.",)),
            Step("Pull each run from box to box and to the panel location, labeled with its circuit at both ends.",
                 "Labels at the panel make the finish fast and right.", ()),
            Step("Staple cable within 12 in of each box and every 4 1/2 ft, never crushed, and keep 6 in or more "
                 "of free conductor at each box.", "Loose cable gets pulled; crushed cable shorts.",
                 ("One cable per staple unless it's listed for more.",)),
            Step("Make up the grounds in every box (twisted and connected, a pigtail for each device) and fold "
                 "the conductors in neatly.", "Grounds made up now are checked at the rough-in.", (),
                 "Every run is pulled, stapled, protected and made up."),
        )),
        Phase("Alarms and rough-in inspection", (
            Step("Place and wire the smoke alarms (each bedroom, outside each sleeping area, every level) and CO "
                 "alarms, interconnected so one sounds them all.", "Interconnected alarms wake everyone wherever "
                 "the fire starts.", ("Keep smoke alarms away from kitchens and baths where the code says.",)),
            Step("Call for the rough-in inspection with every box made up and every run at the panel location "
                 "unlanded; photograph each wall before insulation.", "The photos are the map of what's behind "
                 "the drywall.", (), "The rough-in inspection passed."),
        )),
    ),
    (_NEC + ": 210.8 (GFCI), 210.11 (branch circuits required), 210.12 (AFCI), 210.52 (receptacle outlets), 300.4 "
     "(protection), 314.16 (box fill), 334.30 (NM support), 220 (load calculations)",
     _IRC + ": R314 and R315 (smoke and carbon monoxide alarms), Chapters 34 to 43 (electrical)",
     "Rex Cauldwell, Wiring a House (Taunton, For Pros by Pros, 5th ed.)",
     "Mike Holt, Understanding the National Electrical Code, Vol. 1 (2023)"),
    skill="electrical_wiring",
))

register(Job(
    "electrical_finish", "electrical", "install", "Finish the electrical",
    "The electrical finish after paint: receptacles and switches on their devices with GFCI and AFCI protection where "
    "the code asks, light fixtures and fans on rated boxes, appliance connections, each circuit landed in the panel "
    "on its breaker with the panel's power off and proven dead, the panel directory filled in, and every circuit "
    "tested before the final.",
    ("electrical finish", "install outlets", "install switches", "trim out electrical", "hang light fixtures",
     "land the circuits"),
    ("live_power", "licensed", "fall", "injury"),
    _ELECTRICAL_PERMIT,
    ("electric shock: the panel's incoming lugs stay live with the main off", "arc flash in the panel",
     "falls hanging fixtures from ladders", "a fan dropped from a box not rated for it"),
    ("safety glasses", "insulated gloves rated for the voltage when testing in the panel"),
    ("non-contact and two-lead voltage testers", "receptacle tester with a GFCI button", "insulated screwdrivers "
     "and a torque screwdriver", "wire strippers", "ladder"),
    ("receptacles (tamper-resistant; GFCI where required), switches and cover plates", "breakers listed for the "
     "panel (AFCI, GFCI or dual function where required)", "light fixtures and fans with their fan-rated boxes",
     "wire connectors", "appliance cords or whips as the appliances ask", "the panel directory label"),
    (
        Phase("Plan before installing devices", (
            Step("List each circuit with its breaker type (standard, AFCI, GFCI or dual function) and which "
                 "receptacles are protected by a GFCI device instead.", "The protection has to be somewhere on "
                 "every circuit that needs it.", ("Don't double up GFCI at both breaker and device.",),
                 "Every circuit's breaker and protection is decided."),
            Step("Check every box is flush and its paint dry, and that the power is still off at the panel.",
                 "Devices mounted crooked or over wet paint have to come off again.", ()),
        )),
        Phase("Devices and fixtures", (
            Step("Wire each receptacle and switch: ground first, then neutral (white) to silver, hot to brass, on "
                 "the screws (not the push-in holes), torqued to the device's rating.", "Push-in connections "
                 "loosen and burn.", ("Tamper-resistant receptacles where the code asks (nearly everywhere in a "
                                      "home).",)),
            Step("Install GFCI receptacles with the line from the source and the load to the protected outlets "
                 "downstream.", "Line and load swapped leaves everything downstream unprotected.", ()),
            Step("Hang fixtures on their boxes and fans only on boxes rated for fans, with the fixture's own "
                 "support.", "A fan on an ordinary box can fall.", ("Check the fixture's weight against the box.",)),
            Step("Install weather-resistant receptacles outdoors and in damp places, under in-use covers that "
                 "close with a cord plugged in.", "Rain in an open cover trips or shorts the circuit.",
                 ("Weather-resistant devices are marked WR.",)),
            Step("Connect the fixed appliances (range, dryer, dishwasher, disposal) with the cord or whip each "
                 "maker lists.", "Each appliance's maker says how it's to be connected.", (),
                 "Every device and fixture is installed and covered."),
        )),
        Phase("Land the circuits in the panel", (
            Step("With the main off, prove the panel dead: test the tester on a known-live source, test the bus "
                 "and terminals, test the tester again.", "A failed tester reads dead on a live bus.",
                 ("The service conductors and main lugs stay live with the main off.",)),
            Step("Bring each cable in through a listed connector, land neutrals and grounds where the panel's "
                 "label says, and each hot (or AFCI/GFCI pigtail) on its breaker, all torqued.", "Loose terminals "
                 "are a leading cause of panel fires.", ("In a subpanel, neutrals and grounds stay separate.",)),
            Step("Fill in the panel directory clearly (room and use for every breaker), put the cover on with every "
                 "blank in place.", "The directory is required and is how anyone shuts the right circuit off.", (),
                 "Every circuit is landed, torqued and labeled, the cover on."),
        )),
        Phase("Test and final inspection", (
            Step("Turn on the main, then each breaker, and test every receptacle with the plug-in tester and every "
                 "GFCI and AFCI with its test button.", "A protective device that doesn't trip protects no one.",
                 ("Fix any open ground or reversed polarity before the final.",)),
            Step("Test the smoke and CO alarms together, then call for the final inspection.", "Interconnected "
                 "alarms must all sound from one.", (), "The final electrical inspection passed."),
        )),
    ),
    (_NEC + ": 110.14 (terminations and torque), 210.8 and 210.12 (GFCI and AFCI), 314.27 (fan and fixture "
     "boxes), 406.12 (tamper-resistant receptacles), 408.4 (circuit directory)",
     _IRC + ": Chapters 34 to 43 (electrical), R314 and R315 (alarms)",
     "OSHA 29 CFR 1910.333, Selection and Use of Work Practices (de-energizing and testing before work)",
     "Rex Cauldwell, Wiring a House (Taunton, For Pros by Pros, 5th ed.)"),
    skill="electrical_wiring",
))

register(Job(
    "hvac_ductwork", "hvac", "install", "Design and install the ductwork",
    "Forced-air ducts in a house: the heating and cooling load worked out room by room, the equipment and ducts sized "
    "from it, a trunk and branch layout with a return path from every bedroom, sheet metal or flex run to its limits "
    "and supported, every joint sealed with mastic, ducts outside the heated space insulated, balancing dampers, and "
    "a duct leakage test. The furnace or air handler itself is set by a licensed HVAC contractor in most places.",
    ("ductwork", "ducts", "hvac ducts", "duct design", "run ductwork", "air ducts"),
    ("licensed", "fall", "injury"),
    "Ductwork needs a mechanical permit; most places require a room-by-room load calculation (Manual J) and a duct "
    "leakage test, and many reserve the equipment for a licensed contractor. " + _LOCAL,
    ("sharp sheet-metal edges", "attic heat and stepping through the ceiling", "falls from ladders and the attic "
     "access", "fiberglass from duct insulation"),
    ("cut-resistant gloves", "safety glasses", "a dust mask for insulation", "long sleeves"),
    ("aviation snips (left, right, straight)", "crimpers and hand seamers", "drill/driver with hex bits", "mastic "
     "brush", "tape measure and marker", "work light and planks for the attic", "a duct leakage tester (rented or "
     "the tester's)"),
    ("sheet-metal trunks, fittings and boots (or ductboard)", "insulated flex duct (short runs only)", "duct mastic "
     "and fiberglass mesh tape", "sheet-metal screws", "hangers and strapping", "balancing dampers", "duct "
     "insulation (R-8 in attics, or per your code)", "registers and return grilles"),
    (
        Phase("Plan and permit before cutting metal", (
            Step("Have the load calculated room by room (ACCA Manual J), the equipment chosen from it (Manual S), "
                 "and the ducts sized for each room's airflow (Manual D).", "Ducts sized by guesswork leave hot and "
                 "cold rooms and noisy registers.", ("An oversized unit short-cycles and doesn't dehumidify.",),
                 "You have the Manual J, the equipment and the duct sizes for every room."),
            Step("Lay out the trunk and branches on the plan, keeping ducts inside the heated space where you can, "
                 "with a return or transfer path from every bedroom.", "Ducts in an attic lose heat; closed "
                 "bedrooms without a return starve the system.", ()),
        )),
        Phase("Trunks and branches", (
            Step("Hang the supply and return trunks level and supported at the code's spacing, with the fittings "
                 "from the duct design.", "Sagging trunks whistle and leak.", ("Keep the return away from the "
                                                                              "furnace's flue and combustion air.",)),
            Step("Cut the branch takeoffs into the trunk, each with a balancing damper close to it.",
                 "Dampers are how each room gets its airflow.",
                 ("Takeoffs on the top or side of the trunk, not the bottom.",)),
            Step("Run each branch to its boot, rigid where you can and flex only in short, stretched, supported "
                 "runs with gentle bends.", "Compressed or kinked flex cuts airflow in half.",
                 ("Support flex at least every 4 ft, never sagging more than the code allows.",)),
            Step("Fasten boots to the framing and cut the floor or ceiling openings to the register size.",
                 "A loose boot is a leak into the wall.", (), "Every branch reaches its boot with its damper."),
        )),
        Phase("Seal and insulate", (
            Step("Seal every seam, joint, takeoff and boot with mastic and mesh tape.", "Leaky ducts lose a quarter "
                 "or more of the air they carry.", ("Cloth duct tape fails within a few years.",)),
            Step("Insulate ducts outside the heated space to the code's R-value, with a vapor jacket on cooling "
                 "ducts.", "Uninsulated ducts in an attic sweat and lose heat.",
                 ("Tape the jacket's seams so moist air can't reach the cold metal.",)),
            Step("Seal the boots to the drywall or subfloor.", "The gap around a boot pulls in wall and attic "
                 "air.", (), "Every joint is sealed and every duct outside the heated space insulated."),
        )),
        Phase("Test, balance and inspection", (
            Step("Have the duct leakage test done (at rough-in or after) and seal and retest until it passes.",
                 "The test is required and proves the sealing.", ("Rough-in testing is easier to fix.",)),
            Step("Once the equipment runs, set the dampers so each room gets its design airflow, and mark their "
                 "positions.", "Balancing is what evens the rooms.", ()),
            Step("Call for the mechanical inspection and keep the Manual J and the test report.",
                 "They're required and are the record for the next service.", (),
                 "The mechanical inspection passed."),
        )),
    ),
    (_IRC + ": M1401.3 (equipment sizing), M1601 (duct construction, M1601.4 installation and sealing), N1103.3 "
     "(duct insulation and testing)",
     "ACCA Manual J (Residential Load Calculation), Manual S (Equipment Selection) and Manual D (Residential Duct "
     "Systems)",
     "SMACNA, HVAC Duct Construction Standards: Metal and Flexible",
     "Air Diffusion Council, Flexible Duct Performance and Installation Standards"),
    skill="hvac",
))

register(Job(
    "minisplit", "hvac", "install", "Install a ductless mini-split",
    "A one-room ductless heat pump: sized for the room, the indoor head and outdoor unit placed, the wall sleeve "
    "drilled sloping out, the line set and condensate run, the outdoor unit on a pad or brackets above the snow, its "
    "own circuit and disconnect, then the line set pressure-tested, evacuated and opened. The refrigerant work needs "
    "an EPA-certified technician unless the unit is a quick-connect model sold for homeowner installation.",
    ("mini split", "minisplit", "ductless", "heat pump", "ductless heat pump", "install a mini split"),
    ("licensed", "live_power", "fall", "weather", "injury"),
    "A mini-split needs a mechanical permit and an electrical permit for its circuit in most places. Refrigerant "
    "handling requires EPA Section 608 certification. " + _LOCAL,
    ("refrigerant burns and the unit's pressure", "electric shock at the disconnect and circuit", "falls mounting "
     "the head high or the unit on brackets", "drilling into wires or pipes in the wall"),
    ("safety glasses", "gloves", "fall protection or a stable platform on ladders"),
    ("hole saw (commonly 3 in) and drill", "level and stud finder", "torque wrench with flare crowfoot adapters",
     "flaring tool (for flared units)", "vacuum pump and micron gauge, nitrogen and a manifold gauge set (the "
     "technician's)", "voltage tester"),
    ("the mini-split (indoor head, outdoor unit, line set) sized for the room", "wall sleeve and a line-set cover",
     "condensate line and pump if it can't drain by gravity", "pad or wall brackets", "a disconnect and whip",
     "the circuit's breaker and wire (sized from the unit's nameplate)", "pipe insulation and UV-rated tape"),
    (
        Phase("Plan and permit before drilling", (
            Step("Size the unit for the room's load (not just its square feet: windows, insulation and climate "
                 "matter), and read its maker's install manual.", "An oversized unit cycles and doesn't "
                 "dehumidify; an undersized one can't keep up.", ("Check the unit's line-set length limits.",),
                 "You have the unit, the permits, and who does the refrigerant work."),
            Step("Choose spots: the head high on an outside wall with clear airflow, the outdoor unit where it can "
                 "drain, above the snow line, clear of the maker's distances.", "A unit buried in snow or blocked "
                 "by a shrub can't move heat.", ()),
        )),
        Phase("Mount the units", (
            Step("Mount the head's plate level on studs, and find the hole location from its template.",
                 "The plate holds the head and sets its drain slope.",
                 ("Most plates tilt slightly toward the drain side: follow the maker.",)),
            Step("Check the wall for wires and pipes, then drill the hole sloping down to the outside and fit the "
                 "sleeve.", "The slope drains the condensate out; the sleeve protects the lines.",
                 ("Never drill blind into a wall.",)),
            Step("Set the outdoor unit level on its pad or brackets, with its clearances.", "A unit off level "
                 "drains badly and vibrates.", (), "Both units are mounted level with their clearances."),
        )),
        Phase("Lines and power", (
            Step("Pass the line set, condensate and control cable through the sleeve with the drain at the bottom, "
                 "bend the lines gently, and run them to the outdoor unit.", "A kinked line chokes the system.",
                 ("Use a tubing bender; never bend copper sharply by hand.",)),
            Step("Run the condensate to a drain point or a pump, sloping down all the way.", "A drain that rises "
                 "leaks water down the wall inside.", ("Pour water in the head's pan to test it before closing up.",)),
            Step("Install the disconnect within sight of the outdoor unit and the circuit from the panel, sized "
                 "from the nameplate, with the power off and proven dead.", "The disconnect lets a technician work "
                 "on it safely.", ("Panel work only where your permit lets a homeowner do it.",),
                 "The lines, drain, control cable and the circuit are in, with the power still off."),
        )),
        Phase("Charge, test and final inspection", (
            Step("Connect the line set at the outdoor unit (flares torqued to the maker's values), then have it "
                 "pressure-tested with nitrogen, evacuated to the maker's micron level, and the valves opened.",
                 "Air or moisture left in the lines destroys the compressor.", ("Done by an EPA-certified "
                                                                                 "technician unless the unit is a "
                                                                                 "quick-connect DIY model.",)),
            Step("Turn on the power, run it in heating and cooling, check the drain runs and the line set doesn't "
                 "frost unevenly.", "Odd frosting means a low charge or a restriction.", ()),
            Step("Clean the head's filters and show where they are; keep the outdoor unit clear of snow, leaves and "
                 "plants.", "Clogged filters and a buried outdoor unit are the most common service calls.",
                 ("Filters monthly in heavy use.",)),
            Step("Insulate and cover the line set outside, and call for the inspections.", "Bare insulation breaks "
                 "down in sunlight.", (), "The inspections passed and it heats and cools."),
        )),
    ),
    ("US EPA, Section 608 of the Clean Air Act: refrigerant handling and technician certification",
     _IRC + ": M1411 (heating and cooling equipment), M1401.3 (sizing)",
     _NEC + ": 440.14 (disconnect within sight), 440 (air-conditioning and refrigerating equipment)",
     "The mini-split maker's installation manual (line-set limits, torque and evacuation values)"),
    skill="hvac",
))

register(Job(
    "deck", "carpentry", "build", "Build an attached deck",
    "A wood deck attached to the house by a ledger: the permit, footings below the frost line, the ledger flashed "
    "and bolted to the rim, posts, beams and joists sized from the code's deck tables, hangers and lateral load "
    "connectors, the decking, and guards where it's more than 30 in up. Its stairs are the stairs job; the frame's "
    "lumber comes from the deck calculator.",
    ("deck", "build a deck", "attached deck", "deck ledger", "deck framing", "porch deck"),
    ("utilities", "structural", "fall", "weather", "injury"),
    "Nearly every attached deck, and any more than 30 in above the ground, needs a permit with footing, framing and "
    "final inspections. " + _LOCAL,
    ("a deck collapse from a poorly attached ledger", "falls from the frame and the open edges",
     "digging into buried lines", "saw, nailer and auger injuries"),
    ("safety glasses", "hearing protection", "work gloves", "steel-toe boots"),
    ("post-hole digger or power auger", "circular saw and a reciprocating saw", "impact driver and drill with long "
     "bits", "framing nailer (with hanger nails)", "levels, string line and a framing square", "ladders"),
    ("concrete and footing forms (or precast footings where allowed)", "post bases and 6x6 posts", "beams and "
     "joists (sizes from the code's deck tables), treated for ground contact where near the soil",
     "ledger board, flashing, and 1/2 in lags or through-bolts", "joist hangers and hurricane ties with their "
     "listed nails", "lateral load connectors", "decking and its fasteners", "guard posts, rails and balusters"),
    (
        Phase("Plan and permit before you dig", (
            Step("Draw the deck with its size, height, footings, beam and joist sizes from the deck tables (or the "
                 "AWC deck guide), and how it attaches; get the permit.", "Most deck failures are at the ledger and "
                 "the guards.", ("Over a certain height or span: an engineer's design.",),
                 "You have the drawing, the sizes and the permit."),
            Step("Call 811 and wait for the marks.", "Footings are dug right beside the house's service lines.", (),
                 "Every line is marked."),
        )),
        Phase("Ledger and footings", (
            Step("Remove the siding where the ledger goes, flash the wall (behind the house wrap) and over the "
                 "ledger, then bolt it to the house's rim with lags or through-bolts staggered to the code's table.",
                 "A ledger nailed on, or one that lets water into the rim, is how decks fall.",
                 ("Never attach to brick veneer or a cantilevered floor without a design.",)),
            Step("Lay out the footings from the ledger with string lines squared by the diagonals.",
                 "Square footings give a square frame.",
                 ("Measure the diagonals again after the holes are dug.",)),
            Step("Dig the footings below the frost depth to undisturbed soil at the size the table gives, pour, and "
                 "set the post bases.", "Footings above the frost line heave the deck.", ("Footing inspection "
                                                                                          "before the pour where "
                                                                                          "required.",),
                 "The ledger is bolted and flashed, and the footings are poured and inspected."),
        )),
        Phase("Posts, beams and joists", (
            Step("Set the posts in their bases, plumb and braced, and cut them to the beam height from a level line "
                 "off the ledger.", "A level beam sets a level deck.",
                 ("Cut posts after setting, never before.",)),
            Step("Set the beams on the posts with the post caps the code asks, splices over posts only.",
                 "A splice between posts is a hinge.", ()),
            Step("Hang the joists from the ledger in hangers and over the beam at their spacing, crowns up, with "
                 "every hanger nail hole filled.", "Hangers are rated only with their listed nails.",
                 ("Deck screws aren't hanger nails.",)),
            Step("Install the lateral load connectors where the code requires, and blocking at the beam.",
                 "They keep the deck from pulling away from the house.", (),
                 "The frame is square, level and connected, ready for the framing inspection."),
        )),
        Phase("Decking and guards", (
            Step("Lay the decking with the gap the maker asks, fastened to every joist, ends on joists.",
                 "Boards butted tight trap water and swell.", ("Hidden fasteners or screws per the maker.",)),
            Step("Bolt the guard posts to the frame with the connections the code shows, and build guards at least "
                 "36 in high with openings a 4 in sphere can't pass.", "Guards hold a person's weight leaning "
                 "on them; a 4 in gap keeps a child's head from passing through.",
                 ("Notched or lag-screwed guard posts fail the load: through-bolt them.",),
                 "The decking is down and every guard is solid."),
        )),
        Phase("Final inspection", (
            Step("Walk the deck for loose boards, fasteners and wobble at the guards; call for the final "
                 "inspection.", "Guards and the ledger are what the inspector checks hardest.", (),
                 "The final inspection passed."),
        )),
    ),
    ("American Wood Council, DCA 6: Prescriptive Residential Wood Deck Construction Guide (2015)",
     _IRC + ": R507 (exterior decks), R312 (guards), R507.2.4 (ledger flashing)",
     "Simpson Strong-Tie, Deck Connection and Fastening Guide",
     "MIA's deck calculator (core/build_calcs.py floor_frame)"),
    plan="deck-frame",
    skill="carpentry",
))

register(Job(
    "stairs", "carpentry", "build", "Build a set of stairs",
    "A straight run of stairs (a deck, porch or house stair): the total rise measured, risers and treads worked out "
    "to the code's limits and kept even, stringers laid out and cut, landings top and bottom, headroom and width, a "
    "graspable handrail, and guards on any open side more than 30 in up. The stringer cuts come from the stairs "
    "calculator.",
    ("stairs", "build stairs", "stair stringers", "porch steps", "deck stairs", "staircase"),
    ("structural", "fall", "injury"),
    "Stairs are part of the permit for the deck or house they serve, and the inspector measures the risers, treads, "
    "headroom and handrail. " + _LOCAL,
    ("a stair that fails under load from thin stringers", "falls from uneven risers (the most common stair injury)",
     "saw injuries cutting stringers"),
    ("safety glasses", "hearing protection", "work gloves"),
    ("framing square with stair gauges", "circular saw and a handsaw or jigsaw to finish the cuts", "level and "
     "a straight board for measuring the rise", "tape", "drill/driver", "clamps"),
    ("2x12 stringer stock (treated outside)", "treads and risers", "hangers or brackets for the stringers at the "
     "top", "a landing or footing at the bottom", "handrail and its brackets", "guard posts and balusters",
     "structural screws and nails"),
    (
        Phase("Plan before cutting", (
            Step("Measure the total rise from the finished landing below to the finished surface above (with a "
                 "level and a straight board out from the top).", "Every riser comes from this number.",
                 ("Measure at the stair's actual landing spot: ground slopes.",)),
            Step("Divide into equal risers no taller than 7 3/4 in, and treads at least 10 in deep (house stair "
                 "limits; check yours), with risers varying no more than 3/8 in.", "Uneven risers trip people.",
                 ("Outdoor and deck stairs follow the same limits in most codes.",), "You have the riser height, tread depth and the number of each."),
            Step("Check the headroom (6 ft 8 in), the width (36 in), and that there's a landing at top and bottom "
                 "at least as wide as the stair.", "A stair that ends at a door swing or a low beam fails.",
                 ("A door may swing over the top landing only as your code allows.",)),
        )),
        Phase("Stringers", (
            Step("Lay out a stringer with the stair gauges set to the riser and tread, and drop the bottom by one "
                 "tread thickness.", "Without the drop, the first riser is taller than the rest.",
                 ("Check the layout leaves at least 5 in of solid wood below the notches.",)),
            Step("Cut it, finishing the notches with a handsaw (don't overcut), and test it in place.",
                 "Overcut notches weaken the stringer.",
                 ("Seal the cut faces of treated stringers outdoors.",)),
            Step("Use it as the pattern for the rest, spaced to what the tread can span (commonly 16 in or less "
                 "for 5/4 treads).", "Treads too long between stringers bend.", (),
                 "The stringers are cut, tested and spaced."),
        )),
        Phase("Install", (
            Step("Attach the stringers at the top with hangers or a ledger, and at the bottom to a concrete "
                 "landing, never to bare soil.", "The top attachment carries the stair; soil settles.",
                 ("Treated wood off the ground on concrete outside.",)),
            Step("Fasten the treads (and risers if any) to every stringer, with the nosing even.", "A loose tread "
                 "rocks underfoot.", ()),
            Step("Install a graspable handrail 34 to 38 in above the nosings on any stair with four or more "
                 "risers, continuous from the top riser to the bottom.", "The handrail is what catches a fall.",
                 ("Grip size within the code's range.",)),
            Step("Build guards on any open side more than 30 in above the floor below, openings a 4 3/8 in sphere "
                 "can't pass on the stair.", "Guards keep people from falling off the side.", (),
                 "Treads, handrail and guards are on and solid."),
        )),
        Phase("Check and final inspection", (
            Step("Measure every riser and tread and walk the stair up and down; check for bounce or wobble.",
                 "The inspector measures them; your feet notice a bad one first.", ()),
            Step("Call for the inspection with the deck or house.", "Stairs are checked at the final.", (),
                 "The stairs passed their inspection."),
        )),
    ),
    (_IRC + ": R311.7 (stairways: R311.7.5 risers and treads, R311.7.2 headroom, R311.7.6 landings, R311.7.8 "
     "handrails), R312 (guards)",
     "American Wood Council, DCA 6: Prescriptive Residential Wood Deck Construction Guide (stairs)",
     "Larry Haun, The Very Efficient Carpenter (Taunton, 1992)",
     "MIA's stairs calculator (core/build_calcs.py stairs)"),
    plan="deck-stairs",
    skill="carpentry",
))

register(Job(
    "gutters", "exterior", "install", "Hang gutters and downspouts",
    "Aluminum gutters along the eaves: sized for the roof area, the fascia checked sound, hung sloped toward each "
    "downspout on hangers every 2 ft, tucked behind the drip edge, ends and drops sealed, downspouts strapped and "
    "carried well away from the foundation, and the whole run tested with a hose.",
    ("gutters", "hang gutters", "downspouts", "rain gutters", "install gutters", "eavestrough"),
    ("fall", "weather", "injury"),
    "Gutters need no permit in most places, but some areas regulate where downspouts may discharge. " + _LOCAL,
    ("falls from ladders (the main risk)", "sharp aluminum edges", "overhead power lines near the eave",
     "a ladder on soft or sloped ground"),
    ("cut-resistant gloves", "safety glasses", "a ladder stabilizer or standoff"),
    ("extension ladders (two) with standoffs", "chalk line and a level", "tin snips and a hacksaw", "drill/driver "
     "with hex bits", "pop-rivet tool", "caulk gun"),
    ("gutter sections (5 in K-style for most houses, 6 in for big or steep roofs)", "hidden hangers with screws",
     "end caps, drops (downspout outlets) and corners", "downspouts, elbows and straps", "gutter sealant", "pop rivets and screws",
     "splash blocks, extensions or drain connections"),
    (
        Phase("Plan before hanging", (
            Step("Measure each eave and the roof area draining to it, and size the gutters and the number of "
                 "downspouts (one for every 30 to 40 ft of gutter, and at least one per run).", "Too few downspouts "
                 "overflow in a heavy rain.", ("Plan downspouts where water can be carried away from the house.",),
                 "You have the gutter size, the runs, and where every downspout goes."),
            Step("Check the fascia: replace any soft or rotted board before hanging anything on it.",
                 "Hangers in rotted fascia pull out full of water and ice.", ()),
            Step("Set the ladders on firm, level ground, tied or stabilized, clear of power lines.", "Most gutter "
                 "injuries are ladder falls.", ("Keep the ladder 10 ft from overhead lines.",)),
        )),
        Phase("Layout and hangers", (
            Step("Snap a line along the fascia sloping 1/4 in for every 10 ft toward each downspout (from the "
                 "middle both ways on a long run).", "Gutters need fall to drain; too much shows from the street.",
                 ()),
            Step("Mark where the rafter tails are along the fascia.", "Hanger screws in the rafter tails "
                 "hold under snow; screws in fascia alone can pull out.", ("Use the roof's nail lines to find them.",)),
            Step("Cut the downspout openings into the gutter and fit the drops, end caps and corners, sealed "
                 "and riveted.", "Joints sealed on the ground are easier and tighter.", ("Seal on the inside "
                                                                                         "of the gutter.",)),
            Step("Hang the gutter on hidden hangers every 2 ft (closer where snow loads are heavy), its back tucked "
                 "under the drip edge, screwed into the rafter tails where you can.", "Water from the roof has to "
                 "land in the gutter, not behind it.", ("No drip edge: add a gutter apron.",),
                 "Every run is hung on its line with its hangers."),
        )),
        Phase("Downspouts", (
            Step("Attach the downspouts with elbows to the drops and strap them to the wall every 6 to 8 ft.",
                 "Loose downspouts blow off in wind.", ()),
            Step("Carry the water away: extensions, splash blocks or a drain at least 4 to 6 ft from the "
                 "house, onto ground that slopes away.", "Water dumped at the wall ends up in the basement.",
                 ("Never discharge onto a neighbor's lot.",)),
            Step("Fit strainers at the drops (or guards on the gutters) where trees overhang the roof.",
                 "Leaves clog the drop first and the gutter overflows.", ("Guards still need an occasional cleaning.",)),
        )),
        Phase("Test and check", (
            Step("Run a hose at the far end of each run and watch it drain to the downspout with no standing water "
                 "or drips at joints.", "The hose test shows any backward slope or leak.", ()),
            Step("Check every hanger is tight and every joint dry; plan a cleaning twice a year.", "Clogged "
                 "gutters overflow and rot the fascia.", (), "Every run drains and every joint is dry."),
        )),
    ),
    (_IRC + ": R801.3 (roof drainage), R401.3 (drainage away from the foundation)",
     "SMACNA, Architectural Sheet Metal Manual: gutters and downspouts",
     "OSHA, Portable Ladder Safety (29 CFR 1926.1053)"),
    skill="carpentry",
))

register(Diagnosis(
    "furnace_no_heat", "hvac", "Furnace won't heat",
    ("furnace not working", "furnace won't heat", "no heat", "heat isn't working", "furnace won't turn on",
     "furnace blowing cold air", "heater not working"),
    ("gas", "live_power", "injury"),
    "If you smell gas, stop: don't touch switches, leave, and call the gas utility from outside. If a carbon monoxide "
    "alarm sounds, get everyone out and call 911. Turn the furnace's power switch off before opening any panel "
    "beyond the filter.",
    "thermostat",
    (
        DiagCheck("thermostat", "Is the thermostat set to HEAT, set a few degrees above the room, with its screen on "
                  "(fresh batteries if it takes them)?",
                  "A thermostat that's off, set low or dead is the most common no-heat call.",
                  "power", "cause:the thermostat was off, set too low, or its batteries were dead: set it to heat "
                  "above the room and replace the batteries|"),
        DiagCheck("power", "Is the furnace's power switch (a light switch on or near it) on, and its breaker on?",
                  "No power means nothing else can run.",
                  "filter", "cause:the furnace's switch or breaker was off: turn it on; if the breaker trips again, "
                  "leave it off and call an HVAC technician or electrician|"),
        DiagCheck("filter", "Pull the filter out. Is it clogged so you can't see light through it?",
                  "A clogged filter overheats the furnace and its limit switch shuts the burner off.",
                  "cause:a clogged filter overheated the furnace: put in a new one of the same size; it may restart "
                  "once it cools, and filters every 1 to 3 months prevent it|", "door"),
        DiagCheck("door", "Is the lower (blower) door fully seated, pressing its safety switch?",
                  "The door switch cuts power when the door is off or loose, so a crooked door stops everything.",
                  "code", "cause:the door safety switch was open: seat the door so it presses the switch|"),
        DiagCheck("code", "Look through the small window on the lower door. Is the control board's light blinking a "
                  "pattern?", "Most furnaces blink a fault code; the chart on the door's label says what it means.",
                  "pro:an HVAC technician; give them the blink code and what the door's chart says it means",
                  "igniter"),
        DiagCheck("igniter", "Turn the heat up. Within a minute, does a small fan (the inducer) start, then the "
                  "igniter glow orange or click?", "That's the start-up sequence; where it stops shows the part.",
                  "flame", "pro:an HVAC technician; say the inducer or the igniter doesn't start when the thermostat "
                  "calls for heat"),
        DiagCheck("flame", "Does the burner light and then go out within a few seconds, over and over?",
                  "Lighting then dropping out almost always means the flame sensor can't see the flame.",
                  "cause:a dirty flame sensor: a technician cleans or replaces it (with the power and gas off, the "
                  "maker's manual shows how to clean it gently with a fine abrasive pad)|", "efficiency"),
        DiagCheck("efficiency", "Is it a high-efficiency furnace (white plastic pipes out the wall or roof)?",
                  "High-efficiency furnaces also stop for a blocked drain or vent, which a homeowner can clear.",
                  "drain", "pro:an HVAC technician; say the inducer and igniter run but the burner never lights "
                  "(likely the gas valve, a pressure switch or the venting)"),
        DiagCheck("drain", "Is water standing in the condensate trap or the drain hose, or backed up at the "
                  "furnace?", "A blocked condensate drain trips a switch that keeps the burner off.",
                  "cause:a blocked condensate drain: clear the trap and the hose (warm water, or a wet vacuum on "
                  "the drain's end) and the furnace should restart|", "vents"),
        DiagCheck("vents", "Outside, are the two white pipes clear (no snow, ice, leaves or nests)?",
                  "Blocked intake or exhaust pipes stop the furnace for safety.",
                  "pro:an HVAC technician; say a high-efficiency furnace with clear vents and drain runs its "
                  "inducer and igniter but won't light (pressure switch, gas valve or control)",
                  "cause:the outside pipes were blocked: clear them (keep snow off them) and the furnace should "
                  "restart; if it doesn't, call an HVAC technician|"),
    ),
    ("The furnace maker's owner's manual and the fault-code label inside its door",
     "US Department of Energy, Energy Saver: Furnaces and Boilers",
     "National Fire Protection Association, NFPA 54 National Fuel Gas Code (appliance safety)",
     "US Consumer Product Safety Commission, Carbon Monoxide Questions and Answers"),
))


# ------------------------------------------------------------------ the second tier (2026-11-09): everyday breakdowns

register(Diagnosis(
    "clogged_drain", "plumbing", "A clogged or slow drain",
    ("clogged drain", "slow drain", "drain is clogged", "sink won't drain", "tub won't drain", "shower won't drain",
     "backed up drain"),
    ("injury",),
    "Don't mix drain chemicals, and don't plunge or snake a drain that has had chemical cleaner in it: it can splash "
    "into eyes and skin. Wear gloves and eye protection.",
    "how_many",
    (
        DiagCheck("how_many", "Is more than one fixture slow or backing up (a tub filling when the toilet flushes, "
                  "several drains at once, or the lowest drain in the house)?",
                  "One fixture is a local clog; several at once is the main line, a bigger job.",
                  "pro:a plumber or drain-cleaning service; say several fixtures back up together (likely the main "
                  "or sewer line, which needs a cleanout and a long cable)", "stopper"),
        DiagCheck("stopper", "Pull out the sink's pop-up stopper or the tub's strainer. Is it wrapped in hair or "
                  "gunk?", "Most bathroom clogs sit right on the stopper.",
                  "cause:hair and soap on the stopper: clean it and run hot water|", "plunge"),
        DiagCheck("plunge", "Plug the overflow with a wet rag, put a few inches of water in the bowl, and plunge "
                  "hard ten or so times. Does it drain freely now?",
                  "Covering the overflow lets the plunger push on the clog, not the air.",
                  "cause:a soft clog the plunger cleared: run hot water for a minute|", "trap"),
        DiagCheck("trap", "Under the sink, put a bucket below the P-trap, loosen its two slip nuts by hand and take "
                  "it off. Is the trap packed?", "The trap catches what goes down; it's the next most common spot.",
                  "cause:a packed trap: clean it, refit it hand-tight plus a quarter turn, and test for drips|",
                  "snake"),
        DiagCheck("snake", "With the trap off, feed a hand auger (snake) into the wall pipe, turning as you push. Does "
                  "it hit a clog and break through?", "Past the trap, the clog is in the branch line in the wall.",
                  "cause:a clog in the branch line the auger cleared: refit the trap and flush with hot water|",
                  "pro:a plumber; say a single fixture still won't drain after the trap was cleared and a hand auger "
                  "was run (the branch may be blocked further in, or sagging)"),
    ),
    ("International Code Council, International Residential Code (IRC) 2021: P3005 (drainage), P3201 (traps)",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)",
     "Family Handyman, How to Unclog a Drain (plunger, trap and auger methods)"),
))

register(Diagnosis(
    "leaky_faucet", "plumbing", "A dripping or leaking faucet",
    ("leaky faucet", "dripping faucet", "faucet drips", "faucet is leaking", "tap is dripping", "faucet leak"),
    ("injury",),
    "Shut off the water at the stops under the sink (or the house main) before taking anything apart, and plug the "
    "drain so small parts can't fall in.",
    "where",
    (
        DiagCheck("where", "Is it dripping from the spout with the handle off?",
                  "A drip from the spout is the valve inside; a leak elsewhere is a seal or a connection.",
                  "kind", "base"),
        DiagCheck("kind", "Is it a single-handle faucet, or one with two handles?",
                  "The part that wears differs: a cartridge in most single-handle faucets, washers or cartridges in "
                  "two-handle ones.", "cause:a worn cartridge: shut off the water, note the faucet's brand, remove "
                  "the handle and cartridge, and replace it with the same part|", "two"),
        DiagCheck("two", "With the water off, take apart the leaking side's handle (drip warm means the hot side). Is "
                  "there a rubber washer on the stem's end, worn or cracked?", "Old compression faucets drip when "
                  "their washers harden.", "cause:a worn stem washer and maybe its seat: replace the washer (and the "
                  "seat if it's pitted)|", "cause:a worn two-handle cartridge: replace it with the same brand's "
                  "part|"),
        DiagCheck("base", "Is water coming from around the base of the spout or handle when it runs?",
                  "Leaks at the base are the O-rings, not the valve.",
                  "cause:worn O-rings around the spout or cartridge: replace them with the faucet's kit|", "under"),
        DiagCheck("under", "Under the sink, is a supply line or its nut wet?",
                  "Leaks below come from the connections, not the faucet.",
                  "cause:a loose or failed supply line: snug its nut a quarter turn, or replace the braided line|",
                  "pro:a plumber; say a faucet leaks but not from the spout, base, or supply lines (perhaps a "
                  "cracked body or the drain)"),
    ),
    ("The faucet maker's parts diagrams and repair instructions",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)",
     "This Old House, How to Fix a Leaky Faucet"),
))

register(Diagnosis(
    "gfci_wont_reset", "electrical", "A GFCI that won't reset (or outlets with no power)",
    ("gfci won't reset", "gfci wont reset", "outlet not working", "outlets dead", "no power to outlets",
     "gfi won't reset", "reset button won't stay"),
    ("live_power", "injury"),
    "Never open an outlet's box unless its breaker is off and you've proven it dead with a tester checked on a live "
    "outlet. Water near an outlet: keep away and turn its breaker off.",
    "breaker",
    (
        DiagCheck("breaker", "At the panel, is any breaker tripped (in the middle or off), including a GFCI or AFCI "
                  "breaker?", "A GFCI outlet won't reset with no power reaching it.",
                  "cause:a tripped breaker: reset it once; if it trips again, leave it off and call an electrician|",
                  "other_gfci"),
        DiagCheck("other_gfci", "Is there another GFCI outlet on the same circuit (bathrooms, garage, outdoors, "
                  "kitchen, often in another room) that has tripped?",
                  "One GFCI often protects outlets in other rooms; the dead ones may be downstream of it.",
                  "cause:another GFCI upstream had tripped: press its reset|", "wet"),
        DiagCheck("wet", "Is anything plugged into this circuit outdoors, damp, or wet (an outdoor outlet, a "
                  "freezer, a tool)?", "A real ground fault keeps a GFCI from resetting, as it should.",
                  "cause:a ground fault from something plugged in or a wet outlet: unplug everything, let it dry, "
                  "and reset; the appliance that trips it again is faulty|", "unplugged"),
        DiagCheck("unplugged", "With everything unplugged, does it still refuse to reset?",
                  "With nothing connected, the fault is in the wiring or the GFCI itself.",
                  "pro:an electrician; say a GFCI won't reset with power at the breaker and nothing plugged in "
                  "(a worn GFCI, line and load wired backward, or a fault in the wiring)",
                  "cause:it resets once the faulty appliance is unplugged: the appliance has the fault|"),
    ),
    ("National Fire Protection Association, NFPA 70 National Electrical Code (NEC) 2023: 210.8 (GFCI protection), "
     "406.4(D) (replacements)",
     "US Consumer Product Safety Commission, GFCI fact sheet",
     "Rex Cauldwell, Wiring a House (Taunton, For Pros by Pros, 5th ed.)"),
))

register(Diagnosis(
    "frozen_pipe", "plumbing", "A frozen (or burst) pipe",
    ("frozen pipe", "pipes frozen", "pipe froze", "no water in the cold", "burst pipe", "pipe burst",
     "water won't come out"),
    ("live_power", "injury"),
    "If a pipe has burst or water is spraying, shut off the house's main water valve first. Never thaw a pipe with an "
    "open flame. If water is near outlets, the panel or appliances, turn off their breakers before going near.",
    "burst",
    (
        DiagCheck("burst", "Is water leaking or spraying anywhere (a wet ceiling, a hissing wall, water on the "
                  "floor)?", "A burst pipe needs the water off before anything else.",
                  "pro:a plumber, after shutting the main; say a pipe burst from freezing, where, and that the water "
                  "is off", "which"),
        DiagCheck("which", "Open each faucet. Is it one or a few fixtures with no water or a trickle (often on an "
                  "outside wall, or near a garage or crawlspace)?", "Where it's out tells you which pipe froze.",
                  "find", "pro:the water utility, then a plumber; say the whole house has no water (the service "
                  "line or meter may be frozen, or the supply is off)"),
        DiagCheck("find", "Can you reach the pipe that likely froze (under the sink, in a basement, a crawlspace)?",
                  "A reachable pipe can be thawed safely by hand.", "thaw",
                  "pro:a plumber; say a pipe inside a closed wall is frozen (they thaw it without opening the wall "
                  "where they can)"),
        DiagCheck("thaw", "With the faucet open, warm the pipe from the faucet back toward the cold spot with a hair "
                  "dryer, a heat lamp or warm towels (never a flame). Does water start to flow?",
                  "An open faucet lets melting ice and pressure escape as it thaws.",
                  "cause:a frozen pipe now thawed: check it for cracks as it runs, then insulate it and keep the "
                  "cabinet doors open in cold snaps|", "pro:a plumber; say a reachable pipe was warmed with the "
                  "faucet open but still won't flow (the freeze may be further along, or the pipe split)"),
    ),
    ("American Red Cross, Frozen Pipes",
     "International Code Council, International Residential Code (IRC) 2021: P2603.5 (freezing)",
     "Insurance Institute for Business and Home Safety (IBHS), Prevent Frozen Pipes"),
))

register(Diagnosis(
    "low_water_pressure", "plumbing", "Low water pressure",
    ("low water pressure", "weak water pressure", "no water pressure", "water pressure is low", "low pressure",
     "shower is weak"),
    ("injury",),
    "Shut off the water to a fixture before taking its aerator or showerhead apart, and keep the parts out of the "
    "drain.",
    "where",
    (
        DiagCheck("where", "Is the pressure low at one fixture only?",
                  "One fixture is its aerator, cartridge or supply; the whole house is the system.",
                  "aerator", "whole_hot"),
        DiagCheck("aerator", "Unscrew its aerator (or showerhead). Is it clogged with grit or scale?",
                  "Sediment collects in the aerator's screen.",
                  "cause:a clogged aerator or showerhead: soak it in vinegar, rinse, and refit it|", "stops"),
        DiagCheck("stops", "Are the shutoff valves under that fixture fully open?",
                  "A half-closed stop chokes one fixture.",
                  "pro:a plumber; say one fixture is weak with a clean aerator and open stops (likely its "
                  "cartridge or supply line)", "cause:a partly closed shutoff: open it fully|"),
        DiagCheck("whole_hot", "Is it low on both hot and cold everywhere in the house?",
                  "Low on hot only points at the water heater; everywhere points at the main supply.",
                  "main", "pro:a plumber; say only the hot water is weak throughout (sediment in the water heater "
                  "or its valves)"),
        DiagCheck("main", "Is the house's main valve fully open, and is there a pressure regulator (a bell-shaped "
                  "valve after the main) on the line?", "A partly closed main or a failing regulator lowers the "
                  "whole house.", "pro:a plumber; say the whole house is weak with the main open (the regulator, "
                  "a well's pressure switch, or the service line); ask the water utility first whether there's an "
                  "outage", "cause:a partly closed main valve: open it fully|"),
    ),
    ("International Code Council, International Residential Code (IRC) 2021: P2903.3 (minimum pressure), P2903.3.1 "
     "(maximum pressure and regulators)",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)",
     "The fixture maker's care and cleaning instructions"),
))

register(Diagnosis(
    "smoke_alarm_chirp", "electrical", "A smoke or CO alarm that chirps",
    ("smoke alarm chirping", "smoke detector beeping", "alarm chirps", "smoke detector chirp", "co alarm beeping",
     "detector keeps beeping"),
    ("fall", "injury"),
    "A full alarm (loud and continuous) is not a chirp: get everyone out and call 911 from outside. For a chirp, use "
    "a steady stepladder and never remove an alarm without replacing it the same day.",
    "which",
    (
        DiagCheck("which", "Is it a single short chirp every 30 to 60 seconds, and can you find which alarm it's "
                  "from?", "A periodic chirp is the alarm asking for something; finding the right one matters "
                  "in an interconnected house.", "battery",
                  "pro:the alarm maker's help line, or an electrician for hardwired alarms; say the chirp's pattern "
                  "and that you can't tell which alarm it is"),
        DiagCheck("battery", "Replace its battery (even on a hardwired alarm, it has a backup) with the type on its "
                  "label. Does the chirp stop?", "A low battery is by far the most common cause.",
                  "cause:a low battery: replace batteries yearly, all at once|", "age"),
        DiagCheck("age", "Look at the date on the back of the alarm. Is it more than 10 years old (7 for some CO "
                  "alarms)?", "Alarms chirp at end of life and must be replaced.",
                  "cause:the alarm reached its end of life: replace it with the same kind (interconnected if the "
                  "others are)|", "reset"),
        DiagCheck("reset", "Hold its test button for 15 to 20 seconds to clear the memory, then test it. Does it "
                  "stop?", "A stored error can keep it chirping after a new battery.",
                  "cause:a stored error the reset cleared|", "pro:the alarm maker or an electrician; say a "
                  "chirp continues after a new battery and a reset on an alarm under its age limit (the alarm may "
                  "be faulty)"),
    ),
    ("National Fire Protection Association, NFPA 72 National Fire Alarm and Signaling Code (smoke alarm "
     "replacement at 10 years)",
     "US Fire Administration, Smoke Alarms: what you should know",
     "The alarm maker's user manual (its chirp patterns)"),
))

register(Diagnosis(
    "garbage_disposal_jammed", "appliances", "A garbage disposal that hums, won't run, or jams",
    ("garbage disposal", "disposal jammed", "disposal won't turn on", "disposal hums", "disposer not working",
     "garbage disposal stuck"),
    ("live_power", "injury"),
    "Never put a hand into a disposal. Switch it off at the wall switch (and unplug it or turn off its breaker) "
    "before working on it, and use tongs or pliers to reach in.",
    "sound",
    (
        DiagCheck("sound", "When you switch it on, does it hum but not spin?",
                  "A hum means it has power but the plate is jammed.",
                  "unjam", "silent"),
        DiagCheck("unjam", "With it switched off and unplugged, put the hex wrench (1/4 in Allen key) in the socket "
                  "under the unit and work it back and forth until it turns freely. Remove whatever jammed it with "
                  "tongs. Does it spin now?", "The socket turns the plate from below to free a jam.",
                  "cause:a jam the hex wrench freed: press the reset, run cold water and switch it on|",
                  "pro:a plumber or appliance technician; say it hums and won't turn even with the hex wrench "
                  "(likely seized bearings: it needs replacing)"),
        DiagCheck("silent", "Is it completely silent? Press the red reset button on its bottom. Does it run then?",
                  "The overload trips when it's been jammed or worked hard.",
                  "cause:the overload had tripped: it's reset; if it trips often, something is jamming it|",
                  "power"),
        DiagCheck("power", "Is its breaker on, and (if it plugs in) is the outlet live? (Test with a lamp.)",
                  "No power at the unit is a switch, outlet or breaker problem.",
                  "pro:an electrician or appliance technician; say a disposal with power, reset pressed, makes no "
                  "sound (likely the motor or its switch)",
                  "cause:no power at the disposal: reset the breaker once; if it trips again, call an "
                  "electrician|"),
    ),
    ("The disposal maker's owner's manual (InSinkErator or the like: the hex socket and reset)",
     "US Consumer Product Safety Commission, appliance safety guidance",
     "Family Handyman, How to Fix a Jammed Garbage Disposal"),
))

register(Diagnosis(
    "sump_pump_fail", "plumbing", "A sump pump that won't run (or runs constantly)",
    ("sump pump", "sump pump not working", "sump pump won't turn on", "sump pump runs constantly", "basement "
     "flooding", "sump is full"),
    ("live_power", "injury"),
    "Water and electricity: if the basement is flooding near outlets or the panel, don't step in the water; turn the "
    "power off from a dry place or call the utility. Unplug the pump before reaching into the pit.",
    "power",
    (
        DiagCheck("power", "Is the pump plugged in, and is its outlet (often a GFCI) live and not tripped?",
                  "A tripped GFCI or breaker is the most common reason a pump stops.",
                  "float", "cause:no power at the pump: reset the GFCI or breaker; a GFCI that trips again means a "
                  "fault in the pump or cord, so call a plumber or electrician|"),
        DiagCheck("float", "With the pump unplugged, can its float (or switch) move freely, not caught on the pit "
                  "wall or the cord?", "A stuck float never tells the pump to start.",
                  "test", "cause:a stuck float switch: free it and position the pump so it can't catch|"),
        DiagCheck("test", "Plug it in and pour a bucket of water into the pit. Does the pump start and empty it?",
                  "Filling the pit tests the whole cycle.",
                  "constant", "pro:a plumber; say a sump pump with power and a free float won't start when the "
                  "pit fills (the switch or motor has failed: replace it, ideally with a battery backup)"),
        DiagCheck("constant", "Does it run but keep running, or cycle on and off every few seconds?",
                  "Constant running is a check valve, the discharge, or a stuck switch.",
                  "check_valve", "cause:the pump works: watch it in the next rain, and test it every few months|"),
        DiagCheck("check_valve", "Is the check valve on the discharge pipe letting water fall back into the pit (it "
                  "refills right after the pump stops)?", "A failed check valve makes the pump pump the same "
                  "water over and over.", "cause:a failed check valve: replace it (arrow pointing away from the "
                  "pump)|", "pro:a plumber; say the pump runs or cycles constantly with a working check valve (a "
                  "frozen or blocked discharge, a stuck switch, or more groundwater than it can handle)"),
    ),
    ("The sump pump maker's installation and owner's manual",
     "International Code Council, International Residential Code (IRC) 2021: R405 (foundation drainage), P3302 "
     "(subsoil drains)",
     "American Society of Home Inspectors (ASHI), sump pump inspection guidance"),
))

register(Diagnosis(
    "garage_door_wont_close", "appliances", "A garage door that won't close (or reverses)",
    ("garage door won't close", "garage door reverses", "garage door goes back up", "garage door not closing",
     "garage door stuck", "garage door opener not working"),
    ("injury",),
    "Never adjust, loosen or remove the springs, cables or their brackets: they hold enough force to kill. Keep "
    "people and pets clear of the door while testing, and unplug the opener before touching its track or sensors.",
    "light",
    (
        DiagCheck("light", "Does the opener's light blink when the door reverses, or does it close only while you "
                  "hold the wall button?", "That pattern almost always means the safety sensors can't see each "
                  "other.", "sensors", "obstruct"),
        DiagCheck("sensors", "Look at the two small sensors by the floor on each side. Are their lights both on "
                  "steadily, the lenses clean, and the brackets pointed at each other?",
                  "Dirty or bumped sensors stop the door for safety.",
                  "obstruct", "cause:misaligned or dirty safety sensors: clean the lenses and aim them until both "
                  "lights are steady|"),
        DiagCheck("obstruct", "Is anything in the door's path or the tracks (a bin, debris, a bent track, ice at "
                  "the floor)?", "The opener reverses when it feels resistance.",
                  "cause:something in the path or the track: clear it; a bent track or broken roller needs a "
                  "garage door technician|", "spring"),
        DiagCheck("spring", "From a safe distance, is a spring above the door visibly broken (a gap in the coil) or a "
                  "cable slack?", "A broken spring makes the door too heavy and the opener stops.",
                  "pro:a garage door technician; say a spring or cable looks broken (never attempt it yourself)",
                  "limits"),
        DiagCheck("limits", "Does the door touch the floor and then go back up?",
                  "Its close limit or force setting is off.",
                  "cause:the close limit or force needs adjusting: follow the opener's manual for its limit and "
                  "force settings, then test that it reverses on a 2x4 laid flat under it|",
                  "pro:a garage door technician; say the door won't close with clear sensors, tracks and springs "
                  "(the opener's logic board or drive)"),
    ),
    ("US Consumer Product Safety Commission, Garage Door Operator Safety (16 CFR 1211: entrapment protection)",
     "International Door Association, Garage Door Safety: springs and cables",
     "The opener maker's owner's manual (limits, force and sensor alignment)"),
))


# ------------------------------------------------------------------ the second tier: everyday jobs

register(Job(
    "ceiling_fan", "electrical", "install", "Replace a light with a ceiling fan",
    "A ceiling fan in place of a ceiling light on an existing circuit: the power proven off, the box checked (or "
    "replaced) for a fan rating with a brace between the joists, the fan's bracket, wiring (ground, neutral, hot, "
    "light), the motor hung and the blades balanced at a safe height. A new circuit or switch run is a wiring job.",
    ("ceiling fan", "install a ceiling fan", "replace a light with a fan", "hang a ceiling fan", "fan install"),
    ("live_power", "licensed", "fall", "injury"),
    "Swapping a fixture on an existing circuit often needs no permit, but some places require one; a new circuit "
    "always does. " + _LOCAL,
    ("electric shock from a circuit not proven dead", "a fan falling from a box not rated for it",
     "falls from the ladder holding a heavy motor"),
    ("safety glasses", "a steady stepladder", "insulated gloves for testing"),
    ("non-contact and two-lead voltage testers", "screwdrivers and nut drivers", "wire strippers", "stepladder",
     "a helper to hold the motor", "stud finder"),
    ("the fan (with a downrod length for your ceiling height)", "a fan-rated box and a brace if the box isn't rated",
     "wire connectors", "the fan's balancing kit"),
    (
        Phase("Plan and permit before taking the light down", (
            Step("Check the ceiling height: the blades must be at least 7 ft above the floor (8 ft is better), and "
                 "pick the downrod for it.", "Blades too low hit people.", ("Sloped ceiling: an angle adapter.",),
                 "You have the fan, its downrod, and the permit if your area wants one."),
            Step("Turn off the circuit's breaker and tag it, then prove the light's wires dead: test the tester on "
                 "a live outlet, test the wires, test the tester again.", "Wall switches don't always cut every "
                 "wire in the box.", ("A box with two circuits: prove every wire dead.",)),
        )),
        Phase("Box and bracket", (
            Step("Take the light down and look inside the box for a fan rating (stamped \"acceptable for fan "
                 "support\").", "A plain light box can't hold a fan's weight and wobble.", ()),
            Step("If it isn't rated, replace it with a fan-rated box on a brace fastened between the joists (or "
                 "screwed into a joist).", "The brace carries the fan, not the drywall.", ("Brace snug against "
                                                                                          "the ceiling.",),
                 "A fan-rated box is fastened to the framing."),
            Step("Screw the fan's mounting bracket to the box with the screws that came with the box or fan.",
                 "Those screws are rated for the load.", ()),
        )),
        Phase("Wire and hang", (
            Step("Assemble the downrod and the motor's canopy on the ground, threading the wires through.",
                 "Assembling overhead is how fans get dropped.", ()),
            Step("Hang the motor on the bracket's hook or ball mount, so a helper's hands are free.",
                 "The hook holds it while you wire.", ("Have a helper steady the ladder and the motor.",)),
            Step("Connect ground to ground, white to white, black to the fan's black, and the fan's blue (light) to "
                 "black too or to a second switched wire, with connectors, and fold them in.", "Each wire must go "
                 "to its match; a light on its own switch uses the second hot.", ("Tug each connector.",)),
            Step("Raise the canopy and fasten it, then attach the blades and the light kit.", "Blades on last "
                 "keeps them from being bent while wiring.", (), "The fan is wired, hung and assembled."),
        )),
        Phase("Test, balance and check", (
            Step("Turn the breaker on and run the fan at every speed and the light.", "Each speed and the light "
                 "should work from the switch or remote.", ()),
            Step("If it wobbles, check the blade screws, then use the balancing kit's clip and weights.",
                 "A wobbling fan loosens its own mount over time.", ("A wobble at the bracket: the box isn't "
                                                                     "tight.",)),
            Step("Set its direction (counterclockwise from below for summer).", "Summer direction pushes air down.",
                 (), "The fan runs at every speed without wobbling, the light works."),
        )),
    ),
    ("National Fire Protection Association, NFPA 70 National Electrical Code (NEC) 2023: 314.27(C) (boxes for "
     "ceiling fans), 422.18 (support of ceiling fans)",
     "The fan maker's installation manual (blade height, wiring and balancing)",
     "OSHA 29 CFR 1910.333, Selection and Use of Work Practices (de-energizing and testing before work)"),
    skill="electrical_wiring",
))

register(Job(
    "bathroom_vanity", "plumbing", "install", "Replace a bathroom vanity",
    "Swapping a bathroom vanity and its top: the water shut off, the old one out, the wall and floor checked, the "
    "new cabinet set level and fastened to studs, the top and sink set, the faucet and drain, the trap and supply "
    "lines connected, sealed and tested. Moving the drain or supply is a rough-in job.",
    ("bathroom vanity", "replace the vanity", "install a vanity", "new vanity", "bathroom sink cabinet"),
    ("hazmat", "injury"),
    "Replacing a vanity in place usually needs no permit; moving plumbing does. " + _LOCAL,
    ("water damage from a fitting left loose", "a heavy stone top dropped", "old materials in a house before 1980 "
     "(flooring, wall finishes)"),
    ("gloves", "safety glasses", "a helper for a stone top"),
    ("adjustable wrenches and a basin wrench", "level", "drill/driver and a stud finder", "utility knife and pry "
     "bar", "shims", "caulk gun", "bucket and towels"),
    ("the vanity cabinet and top (with the sink)", "the faucet and drain assembly", "a P-trap kit if the old one "
     "doesn't fit", "braided supply lines and new quarter-turn stops if the old ones are worn", "cabinet screws",
     "silicone sealant", "plumber's putty if the drain asks for it"),
    (
        Phase("Plan before removing the old one", (
            Step("Measure the space, the drain's height and position, and the supply stops; check the new vanity's "
                 "back is open or can be cut for them.", "A vanity whose back blocks the drain won't sit flat.",
                 ("Keep the new sink's drain within reach of the existing drain arm.",),
                 "The new vanity fits the space and its plumbing."),
            Step("Shut the stops (or the main), open the faucet to drain it, and put a bucket under the trap.",
                 "A stop that doesn't shut fully needs replacing anyway.", ()),
        )),
        Phase("Remove and prepare", (
            Step("Disconnect the supply lines and the trap, cut the caulk, and lift off the old top; unscrew the "
                 "cabinet from the wall and remove it.", "Stone tops are heavy and crack if twisted.",
                 ("Plug the drain arm with a rag against sewer gas.",)),
            Step("Clean the floor and wall where the new one goes, and replace the stops if they're old or "
                 "seized.", "A stop that won't close is a flood waiting for the next repair.",
                 ("Quarter-turn stops sized for the supply pipe.",)),
            Step("Check the wall and floor behind it for water damage or mold; fix it now.", "This is the only "
                 "time that wall will be open to see.", ()),
        )),
        Phase("Set the new vanity", (
            Step("Set the cabinet, level it both ways with shims, and screw it to the studs through its back rail.",
                 "A cabinet out of level makes the top drain to one side.", ("Find the studs before you set it.",),
                 "The cabinet is level and fastened to studs."),
            Step("Install the faucet and the drain in the sink while the top is off, if you can.", "It's far easier "
                 "than from underneath.", ()),
            Step("Set the top on a bead of silicone and check it's level.", "The silicone holds it and seals it to "
                 "the cabinet.", ()),
        )),
        Phase("Connect, seal and check", (
            Step("Connect the trap to the drain arm (the trap's arm sloping down to the wall) and the supply lines "
                 "to the stops, hand-tight plus a quarter turn.", "Slip joints seal with their washers.",
                 ("The trap must not slope back toward the sink.",)),
            Step("Caulk the top to the wall with silicone.", "Water splashed at the back runs into the wall "
                 "otherwise.", ()),
            Step("Fit the pop-up stopper and adjust its rod so it opens and seals.", "A stopper that won't "
                 "seal or drain right is the most common callback.", ("Check the rod's nut under the sink for drips.",)),
            Step("Open the stops slowly, run hot and cold, fill and drain the sink, and check every joint with a dry "
                 "paper towel, then again an hour later.", "Slow leaks show only with time.",
                 ("Any drip at a slip nut: a little more turn, not a lot.",),
                 "The vanity is sealed and every joint is dry."),
        )),
    ),
    ("International Code Council, International Residential Code (IRC) 2021: P2705 (fixture installation), P3201 "
     "(traps)",
     "The vanity and faucet makers' installation instructions",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)"),
    skill="plumbing",
))

register(Job(
    "kitchen_cabinets", "carpentry", "install", "Install kitchen cabinets",
    "Hanging wall cabinets and setting base cabinets: the layout from the floor's high point, a level line around "
    "the room, a ledger for the uppers, wall cabinets screwed to studs and clamped together, base cabinets shimmed "
    "level and joined, fillers scribed, and the doors and drawers adjusted. Countertops are measured once the bases "
    "are in.",
    ("kitchen cabinets", "install cabinets", "hang cabinets", "upper cabinets", "base cabinets", "cabinet install"),
    ("injury",),
    "Cabinets need no permit of their own, but the plumbing, wiring and venting that go with a kitchen do. " + _LOCAL,
    ("a wall cabinet dropped while hanging", "back strain lifting", "drill and saw injuries"),
    ("safety glasses", "work gloves", "a helper for wall cabinets"),
    ("4 ft level and a laser level", "stud finder", "drill/driver and countersink bits", "clamps (face-frame "
     "clamps)", "shims", "jigsaw for cutouts", "tape and pencil"),
    ("the cabinets, fillers and end panels", "cabinet screws (2 1/2 to 3 in)", "a straight 1x3 or 1x4 ledger",
     "shims", "trim and toe kick"),
    (
        Phase("Plan before hanging", (
            Step("Find the floor's high point along the cabinet walls and mark it; snap a level line 34 1/2 in "
                 "above it (the base height) and another for the bottom of the wall cabinets (commonly 54 in).",
                 "Everything measures from the high point so no base has to be cut down.",
                 ("Check the line all the way around the room.",),
                 "The level lines and every cabinet's place are marked on the walls."),
            Step("Mark every stud on the walls, and where the plumbing, electrical boxes and vent cutouts land in each "
                 "cabinet.", "Screws go into studs; cutouts measured now fit.", ()),
        )),
        Phase("Wall cabinets", (
            Step("Screw a temporary ledger on the wall-cabinet line to rest the cabinets on.", "The ledger holds the "
                 "cabinet level while you fasten it.", ()),
            Step("Take the doors and shelves off the wall cabinets before lifting them.", "A lighter box is "
                 "safer to hold up and the hinges don't get bent.", ("Label each door with its cabinet.",)),
            Step("Hang the corner cabinet first, screwing through its top and bottom rails into studs.",
                 "The corner sets the rest of the run.", ("Never hang a cabinet by drywall anchors.",)),
            Step("Hang each next cabinet, clamp the face frames flush, and screw them together, then to the studs.",
                 "Joined face frames make a run look like one piece.", ("Pre-drill the face frames so they don't "
                                                                         "split.",),
                 "The wall cabinets are level, flush and screwed to studs."),
        )),
        Phase("Base cabinets", (
            Step("Set the corner base first, shimmed level to the line, then each next one shimmed, clamped and "
                 "joined.", "Bases out of level crack stone countertops.", ("Shim at the studs so the screws "
                                                                            "don't pull it out of level.",)),
            Step("Screw each base to the studs through its back rail.", "Bases held only by their neighbors move.",
                 ()),
            Step("Cut the openings for the sink plumbing and any electrical box in the cabinet backs before "
                 "setting them, measured from the marks.", "Cuts made after a cabinet is fastened are awkward and "
                 "ragged.", ("Measure twice: a cabinet back can't be uncut.",)),
            Step("Scribe and fit the fillers and end panels to the walls.", "Walls aren't straight; scribing hides "
                 "the gap.", (), "Every base is level, joined and fastened."),
        )),
        Phase("Adjust and check", (
            Step("Hang the doors and drawers and adjust the hinges for even gaps.", "Even reveals are what people "
                 "notice.", ("Adjust after the countertop is on as well.",)),
            Step("Install the toe kick and trim, and check every run with the level once more.",
                 "The countertop is measured from these cabinets.", (),
                 "The cabinets are level, adjusted and ready for the countertop."),
        )),
    ),
    ("The cabinet maker's installation guide",
     "Fine Homebuilding, How to Install Kitchen Cabinets",
     "National Kitchen and Bath Association (NKBA), Kitchen Planning Guidelines (heights and clearances)"),
    skill="carpentry",
))

register(Job(
    "shower_tile", "plumbing", "install", "Tile a shower (with its waterproofing)",
    "A tiled shower over a waterproof system: the pan sloped to the drain, the walls on cement board or foam board "
    "with a bonded membrane (or a liner and mortar bed), every seam, corner, niche and valve sealed, a flood test, "
    "then tile, movement joints at the corners, grout and sealant. Moving the drain or valve is a rough-in job.",
    ("shower tile", "tile a shower", "tile the shower", "shower pan", "waterproof a shower", "tiled shower"),
    ("licensed", "hazmat", "injury"),
    "A new shower pan often needs a plumbing permit and an inspection of the pan or liner with its flood test before "
    "tile. " + _LOCAL,
    ("silica dust cutting tile and cement board dry", "lifting mortar and tile", "old materials in a house before "
     "1980 when demolishing", "knee strain"),
    ("a respirator rated for silica when cutting dry", "safety glasses", "knee pads", "gloves for thinset"),
    ("wet tile saw and a manual cutter", "notched trowels for the tile", "a level and a straightedge", "a drill with "
     "a mixing paddle", "utility knife and a drywall saw", "grout float and sponges", "a test plug for the drain"),
    ("a waterproofing system from one maker (a bonded membrane with its seam bands, corners and drain, or a liner "
     "with a pre-slope)", "cement board or foam board for the walls", "modified (or the maker's) thinset",
     "a shower drain matched to the system", "tile, and trim for the edges", "grout and silicone sealant for the "
     "corners"),
    (
        Phase("Plan and permit before demolition", (
            Step("Pick one maker's waterproofing system and follow its guide end to end, with its drain.",
                 "Mixing parts from different systems voids their warranties and their testing.",
                 ("Read the guide before buying tile: some tile needs a particular thinset.",),
                 "You have the system, its guide, the tile and the permit."),
            Step("In a house before 1980, test the old tile adhesive and wall material before tearing them out.",
                 "Old mastics and wall finishes can hold asbestos.", ()),
        )),
        Phase("Pan and walls", (
            Step("Build the pan sloped 1/4 in per foot to the drain (the system's sloped tray or a mortar "
                 "pre-slope), with the drain set at its height.", "Water that pools on a flat pan soaks the grout "
                 "and grows mold.", ("Check the slope from every edge with a level.",)),
            Step("Hang cement board or foam board on the walls to the system's fastening, gaps as it asks.",
                 "The board is the base the membrane bonds to.", ()),
            Step("Apply the membrane over the pan and walls, with its bands over every seam, its preformed corners, "
                 "and its seals around the valve and showerhead pipes.", "Corners, seams and pipes are where "
                 "showers leak.", ("Full coverage of thinset under a sheet membrane, no hollow spots.",)),
            Step("Plug the drain and flood the pan to just under the curb for 24 hours.", "The flood test proves the "
                 "pan before tile hides it.", ("Mark the water line: a drop means a leak.",),
                 "The pan held its water for 24 hours and any inspection passed."),
        )),
        Phase("Tile", (
            Step("Lay out the walls so the cuts land in the corners evenly and a full tile sits at eye level, and "
                 "start the wall tile one row up on a ledger.", "A ledger keeps the rows level above an uneven "
                 "floor.", ("Plan around the niche and valve.",)),
            Step("Set the wall tile with full coverage (95% in a shower), spacers in, and check plane as you go.",
                 "Hollow spots behind tile in a shower crack and hold water.", ()),
            Step("Tile the floor last, sloped with the pan, cut to fall toward the drain.", "The floor tile must "
                 "follow the slope, not fight it.", (), "Walls and floor are tiled with full coverage."),
        )),
        Phase("Grout, seal and check", (
            Step("Grout the joints but leave the inside corners and the change of plane at the floor open.",
                 "Corners move; grout there cracks.", ()),
            Step("Fill the corners and the floor-to-wall joint with silicone sealant matched to the grout.",
                 "Silicone stretches where the planes meet.", ("Let it cure before the first shower.",)),
            Step("Let the grout cure as its maker says, seal it if it needs it, then run the shower and look for "
                 "water where it shouldn't be.", "The first showers show any problem while it's small.", (),
                 "The shower is grouted, sealed and dry outside."),
        )),
    ),
    ("Tile Council of North America, TCNA Handbook: shower methods (B421, B422) and EJ171 (movement joints)",
     "ANSI A118.10, Load Bearing, Bonded, Waterproof Membranes for Thin-Set Ceramic Tile",
     "International Code Council, International Residential Code (IRC) 2021: P2709 (shower receptors, P2709.2.3 "
     "liner test)",
     "The waterproofing system maker's installation handbook (Schluter, Laticrete or the like)"),
    skill="plumbing",
))

register(Job(
    "exterior_paint", "exterior", "install", "Paint the outside of the house",
    "Repainting siding and trim: testing for lead first on a house before 1978, washing, scraping and sanding loose "
    "paint safely, repairing rot, priming bare wood, caulking, then two coats from the top down in the right "
    "weather, with the ladders set safely.",
    ("exterior paint", "paint the house", "paint the siding", "paint the trim", "house painting", "exterior painting"),
    ("hazmat", "fall", "weather", "injury"),
    "Painting needs no permit, but on a house built before 1978 the EPA's lead-safe rules apply to anyone paid to "
    "disturb the old paint, and the same methods keep a family safe. " + _LOCAL,
    ("lead dust and chips from old paint (houses before 1978)", "falls from ladders (the main risk)",
     "overhead power lines near the eaves", "pressure washers cutting skin or wood"),
    ("a respirator for scraping and sanding", "safety glasses", "gloves", "a ladder stabilizer and a harness on "
     "steep or high work"),
    ("extension ladders with standoffs", "scrapers and a sanding block (or a sander with a vacuum)", "a garden "
     "sprayer or soft-wash for cleaning", "brushes (2 1/2 to 4 in) and rollers", "drop cloths and plastic sheeting",
     "putty knife and caulk gun", "a lead test kit"),
    ("exterior primer (stain-blocking where needed)", "exterior acrylic paint for siding and trim",
     "exterior caulk", "epoxy or exterior filler and wood for repairs", "house wash cleaner", "6 mil plastic "
     "for lead-safe work"),
    (
        Phase("Plan and prepare before painting", (
            Step("On a house before 1978, test the paint for lead; if positive, use lead-safe methods (plastic on "
                 "the ground, wet scraping, no dry sanding or burning, a HEPA vacuum).", "Lead chips and dust "
                 "poison children and gardens.", ("Never pressure-wash or dry-sand lead paint.",),
                 "You know whether the paint has lead and how you'll contain it."),
            Step("Plan for dry weather: at least 50 F (or the paint's lower limit), no rain for a day, and out of "
                 "full midday sun on the wall you're painting.", "Paint applied too cold or in hot sun fails "
                 "early.", ()),
            Step("Set ladders on firm, level ground at a 4-to-1 angle, 3 ft above the eave, clear of power lines.",
                 "Most painting injuries are ladder falls.", ("Keep 10 ft from overhead lines.",)),
            Step("Cover plants, walks and windows with drop cloths or plastic, and remove or mask fixtures, house "
                 "numbers and hose reels.", "Paint and chips are hard to get off what wasn't covered.",
                 ("Plastic on plants only while you work: it cooks them in sun.",)),
        )),
        Phase("Clean and repair", (
            Step("Wash the walls (soft wash or garden sprayer, not a high-pressure stream) and let them dry for a "
                 "day or two.", "Paint won't stick to dirt or mildew.", ("Kill mildew with the cleaner first.",)),
            Step("Scrape every loose and peeling spot down to sound paint, and feather the edges.", "New paint over "
                 "loose paint peels with it.",
                 ("Lead paint: mist it while scraping and keep the chips on the plastic.",)),
            Step("Cut out or fill rotted wood with epoxy filler or new wood, and fix the cause (a leak, a gutter).",
                 "Paint can't save rotted wood.", (), "Every surface is clean, sound and repaired."),
        )),
        Phase("Prime, caulk and paint", (
            Step("Prime bare wood and repairs, and stain-block knots and water stains.", "Primer seals the wood and "
                 "gives the paint something to grip.",
                 ("Prime within the primer's time after scraping, before bare wood weathers.",)),
            Step("Caulk gaps at trim, corners and around windows (not the bottom edges of lap siding).",
                 "Caulking the laps traps water behind the siding.", ("Use a paintable exterior caulk.",)),
            Step("Paint two coats from the top down, siding before trim, keeping a wet edge along each board.",
                 "Top-down keeps drips off finished work.", ("Recoat only after the time on the can.",),
                 "Two coats are on siding and trim."),
        )),
        Phase("Clean up and check", (
            Step("Clean up: fold the plastic inward, HEPA-vacuum and wet-wipe if there was lead, and dispose of "
                 "it as your area says.", "Lead dust left in the soil stays there.", ()),
            Step("Walk the house in daylight for thin spots and missed edges; touch them up.",
                 "Missed spots are easiest to fix with the ladders still up.", (),
                 "The whole house is painted, checked and cleaned up."),
        )),
    ),
    ("EPA, Renovation, Repair and Painting Rule (40 CFR 745) and its Steps to Lead Safe Renovation guide",
     "Paint Quality Institute, Exterior Painting guidance",
     "OSHA, Portable Ladder Safety (29 CFR 1926.1053)"),
    skill="carpentry",
))

register(Job(
    "wood_fence", "carpentry", "build", "Build a wood privacy fence",
    "A wood privacy fence: the permit and the property line, 811 before digging, posts on a string line every 8 ft, "
    "set deep in concrete or gravel, rails, pickets with a gap, a gate on its own heavy posts, and a finish. The "
    "lumber comes from the fence calculator.",
    ("fence", "wood fence", "privacy fence", "build a fence", "fence posts", "install a fence"),
    ("utilities", "weather", "injury"),
    "Fences often need a permit with height limits (commonly 6 ft in back, 4 ft in front), setbacks and HOA rules; "
    "know your property line. " + _LOCAL,
    ("digging into buried lines", "post-hole auger kickback", "saw and nailer injuries", "lifting posts and "
     "concrete"),
    ("safety glasses", "work gloves", "hearing protection with power tools"),
    ("post-hole digger or rented auger", "string line and stakes", "4 ft level and a post level", "circular saw",
     "drill/driver or nailer", "tape and a spacer block"),
    ("4x4 posts (treated for ground contact) and 6x6 or 4x6 gate posts", "2x4 rails", "pickets", "concrete mix or "
     "compactable gravel", "exterior screws or ring-shank nails", "gate hardware (hinges, latch, an anti-sag kit)",
     "stain or sealer"),
    (
        Phase("Plan and permit before you dig", (
            Step("Find the property line (survey pins), check the height limits, setbacks and HOA rules, and get "
                 "the permit if your area needs one.", "A fence over the line or the height limit can be ordered "
                 "down.", ("Build a few inches inside the line.",), "You know the line, the height and the permit."),
            Step("Call 811 and wait for the marks.", "Fence posts are dug where lines often run along a property.",
                 (), "Every line is marked."),
        )),
        Phase("Posts", (
            Step("Set the end and corner posts' spots, run a string between them, and mark the line posts every "
                 "8 ft (or the rail length).", "The string keeps the fence straight.", ("Plan the gate's opening "
                                                                                       "and posts first.",)),
            Step("Dig the holes three times the post's width and a third of its length deep (below the frost line "
                 "in cold places), with 6 in of gravel in the bottom.", "Shallow posts lean; gravel drains the "
                 "post's end.", ("Hand-dig near any mark.",)),
            Step("Set each post plumb on two faces, braced, and fill with concrete sloped away at the top (or "
                 "tamped gravel).", "A crown of concrete sheds water from the post.", ("Check plumb again before "
                                                                                       "it sets.",),
                 "The posts are plumb, in line and set."),
            Step("Let the concrete cure at least a day (or the bag's time) before hanging rails or the gate.", "Rails "
                 "loaded on green concrete push posts out of plumb.", ("Keep the braces on until then.",)),
        )),
        Phase("Rails, pickets and gate", (
            Step("Cut the posts to height with a string line, and fasten the rails between them (two for 4 ft, "
                 "three for 6 ft).", "Level rails make a level fence top.", ()),
            Step("Fasten the pickets with a spacer for an even gap, checking plumb every few.", "The gap lets the "
                 "wood swell and the wind through.", ("Keep the bottoms 2 in off the ground.",)),
            Step("Cap the post tops (or cut them at an angle) so water runs off the end grain.", "End grain soaks "
                 "up water and rots first.", ()),
            Step("Build the gate square with a diagonal brace running up from the hinge side's bottom, hang it on "
                 "the heavy post, and add the latch.", "The brace keeps the gate from sagging.", (),
                 "The fence is railed and pickets on, the gate swings and latches."),
        )),
        Phase("Finish and check", (
            Step("Let treated lumber dry, then stain or seal it.", "A finish slows checking and graying.", ()),
            Step("Walk the line for loose pickets and wobble, and get the final inspection if your permit has one.",
                 "A post that wobbles now gets worse.", (), "The fence is solid and any inspection passed."),
        )),
    ),
    ("The local fence and zoning ordinance (heights and setbacks)",
     "American Wood Protection Association, U1 Use Category System (ground-contact treated posts)",
     "Fine Homebuilding, Building a Fence That Lasts",
     "MIA's fence calculator (core/build_calcs.py fence)"),
    plan="privacy-fence",
    skill="carpentry",
))

register(Job(
    "attic_ventilation", "exterior", "install", "Vent the attic",
    "Balanced attic ventilation for a vented attic: the net free area the code asks, intake low at the soffits and "
    "exhaust high at the ridge, baffles so insulation can't block the intake, one kind of exhaust only, the ridge "
    "slot cut and vented, and bath and kitchen fans run to the outside, never into the attic.",
    ("attic ventilation", "vent the attic", "ridge vent", "soffit vents", "attic vents", "attic is hot"),
    ("fall", "hazmat", "weather", "injury"),
    "Adding vents is part of a roofing permit when it's done with a reroof; on its own it often needs none. " +
    _LOCAL,
    ("falls from the roof cutting the ridge slot", "attic heat and stepping through the ceiling", "old vermiculite "
     "insulation (may hold asbestos)", "saw kickback on the roof"),
    ("fall protection (anchors and harness) on the roof", "a respirator in the attic", "safety glasses", "gloves"),
    ("circular saw with an old blade (set to the sheathing's depth)", "chalk line and tape", "drill/driver",
     "a flashlight and planks for the attic", "roof brackets", "hammer or roofing nailer"),
    ("ridge vent (with its nails)", "soffit vents (continuous or individual) or a vented drip edge", "rafter-bay "
     "baffles", "ridge cap shingles", "duct and roof or wall caps for bath and kitchen fans"),
    (
        Phase("Plan before cutting", (
            Step("Work out the net free area: 1 sq ft for every 150 sq ft of attic floor (or 1 for 300 with balanced "
                 "intake and exhaust where your code allows), split roughly evenly between intake and exhaust.",
                 "Too little ventilation leaves a hot, damp attic; unbalanced vents pull air from the house.",
                 ("Each vent's net free area is printed on it.",),
                 "You have the intake and exhaust areas and the parts to give them."),
            Step("In the attic, check for vermiculite and for bath or kitchen fans venting into the attic, and look "
                 "at the soffits from inside: are they blocked by insulation?", "Fans blowing into the attic "
                 "soak it; blocked soffits make the ridge vent pull from nowhere.", ()),
        )),
        Phase("Intake", (
            Step("Install soffit vents along each eave (or a vented drip edge where there's no soffit).",
                 "Intake low lets cool air in to push the warm air out the top.", ("Screened, to keep insects "
                                                                                    "out.",)),
            Step("From inside the attic, pull insulation back from each soffit so the vent is open to the bay.",
                 "A soffit vent with insulation on it lets no air in.", ("Wear the respirator for old insulation.",)),
            Step("Staple baffles in every rafter bay from the soffit up past the insulation.", "Baffles keep an air "
                 "channel open over the insulation.", ("Leave at least 1 in of air space above the insulation.",)),
            Step("Run any bath or kitchen fan's duct to its own roof or wall cap, sealed and insulated.",
                 "Moist air from a fan has to leave the house, not the bathroom.", (),
                 "Every soffit is open with a baffle, and every fan vents outside."),
        )),
        Phase("Exhaust", (
            Step("Snap lines and cut the ridge slot (commonly 1 in each side of the ridge, stopping 6 in from the "
                 "ends), with the saw set just through the sheathing.", "Cutting the rafters or ridge is a "
                 "structural problem.", ("Never cut the slot alone on the roof.",)),
            Step("Look at the sheathing along the slot for rot or delamination and replace it before the vent goes on.",
                 "A ridge vent nailed into soft sheathing pulls out in wind.", ("Damp, dark sheathing means the attic has been wet: find out why.",)),
            Step("Nail the ridge vent over the slot with its long nails, then the cap shingles over it.",
                 "The vent's baffles keep rain and snow out of the slot.",
                 ("Nail only where the vent marks: nails through its baffles leak.",)),
            Step("Close off any gable vents or roof fans so there's only one kind of exhaust.", "A gable vent near a "
                 "ridge vent bypasses it, pulling air in at the top instead of the soffits.", (),
                 "The ridge is vented and it's the only exhaust."),
        )),
        Phase("Check the airflow", (
            Step("On a calm, sunny day, compare the attic's temperature with outside, and look for daylight at the "
                 "soffits from the attic.", "A working attic runs only a little hotter than outside.", ()),
            Step("Through the first winter, check the underside of the roof for frost or damp.", "Frost on the "
                 "nails means warm air from the house is still getting in.", ("Frost: air-seal the ceiling.",),
                 "The attic stays close to outdoor temperature and dry."),
        )),
    ),
    ("International Code Council, International Residential Code (IRC) 2021: R806 (roof ventilation, R806.2 net "
     "free area), M1501 (exhaust to the outdoors)",
     "Building Science Corporation, BSD-149: Unvented Roof Assemblies for All Climates (and vented attic guidance)",
     "The ridge and soffit vent makers' installation instructions"),
    skill="carpentry",
))

register(Job(
    "sump_pump", "plumbing", "install", "Install a sump pump",
    "A sump pump in a basement: the pit (an existing one, or a new liner set in the floor), the pump on a firm base, "
    "a check valve on the discharge, the discharge run outside and away from the house (never into the sewer where "
    "that's not allowed), its own GFCI receptacle, a battery backup, and a test with a bucket of water.",
    ("install a sump pump", "new sump pump", "sump pit", "replace the sump pump", "sump pump install"),
    ("live_power", "licensed", "utilities", "hazmat", "injury"),
    "A new sump pit or a discharge line through the wall may need a permit; many places forbid running it into the "
    "sanitary sewer. The receptacle may need an electrician. " + _LOCAL,
    ("silica dust breaking the basement floor", "electric shock with water and a plug together", "back strain "
     "lifting concrete and the pump", "pipes or wires under the slab"),
    ("a respirator rated for silica", "safety glasses", "hearing protection with a jackhammer", "rubber boots and "
     "gloves"),
    ("a rotary hammer or rented jackhammer (for a new pit)", "shovel and bucket", "PVC saw, primer and cement",
     "drill with a hole saw (for the wall)", "level", "a receptacle tester"),
    ("the sump pump (submersible, sized for the inflow)", "a sump liner with a lid (for a new pit)", "a check valve "
     "and a 1 1/2 in PVC discharge", "washed gravel", "a battery backup pump", "exterior sealant and a wall "
     "sleeve", "an extension or drain line outside"),
    (
        Phase("Plan and permit before breaking the floor", (
            Step("Pick the spot (the lowest corner, where water collects, away from the furnace), and decide where "
                 "the discharge leaves the house and where it will drain outside.", "A pit in the wrong spot misses "
                 "the water.", ("Never discharge into the sanitary sewer unless your area allows it.",),
                 "You have the spot, the discharge route and the permit if needed."),
            Step("Find what's under the slab there (drain lines, radon pipe, heat) before cutting, and test any old "
                 "floor covering in a house before 1980.", "A jackhammer through a drain line is a costly "
                 "surprise.", ()),
        )),
        Phase("The pit", (
            Step("For a new pit, cut the slab a few inches wider than the liner, break it out, and dig to the "
                 "liner's depth.", "The liner sets the pump's level below the floor.", ("Cut the slab wet to keep "
                                                                                         "the dust down.",)),
            Step("Set the liner level on a bed of gravel, its rim flush with the floor, with gravel around it, then "
                 "patch the floor with concrete.", "Gravel around the liner lets water in from the soil.",
                 ("The lid stays on: an open pit is a hazard and lets radon in.",),
                 "The liner is set, level and patched in."),
            Step("Set the pump on a firm base in the pit (a brick or the liner's bottom), its float free of the "
                 "walls.", "A pump sitting in silt clogs; a float rubbing the wall sticks.", ()),
            Step("Run the floor's drain tile or a perimeter drain into the pit if the plan has one.",
                 "The pit is only as useful as the water reaching it.", ("Ask the permit office about tying in a perimeter drain.",)),
        )),
        Phase("Discharge and power", (
            Step("Run the discharge pipe up from the pump with a check valve (arrow pointing away from the pump) "
                 "and a union for service.", "The check valve stops the pumped water falling back in.",
                 ("Drill a small weep hole in the discharge below the check valve if the maker asks.",)),
            Step("Take the discharge out through the rim or wall in a sealed sleeve, sloped outside, and carry the "
                 "water at least several feet away onto ground that slopes away.", "Water dumped next to the wall "
                 "comes right back.", ("A line that can freeze needs an ice guard or a slope to drain.",)),
            Step("Plug the pump into a dedicated GFCI-protected receptacle near the pit (installed by an "
                 "electrician where needed).", "Water and power together need GFCI protection.",
                 ("Never use an extension cord for a sump pump.",),
                 "The discharge runs outside and the pump has its own protected receptacle."),
        )),
        Phase("Backup, test and check", (
            Step("Add a battery backup pump (and an alarm) for power outages.", "Storms that fill the pit are the "
                 "ones that cut the power.", ()),
            Step("Pour water in the pit until the pump starts, empties it and shuts off, and the check valve holds.",
                 "The bucket test proves the whole system.", ("Test it every few months and before the wet "
                                                              "season.",)),
            Step("Watch it through the next heavy rain.", "The first storm shows whether it keeps up.", (),
                 "The pump starts, empties the pit, and the water drains away outside."),
        )),
    ),
    ("International Code Council, International Residential Code (IRC) 2021: R405 (foundation drainage), P3302 "
     "(subsoil drains and sumps)",
     "The sump pump maker's installation manual",
     "OSHA 29 CFR 1926.1153, Respirable Crystalline Silica (breaking concrete)",
     "NFPA 70 National Electrical Code (NEC) 2023: 210.8 (GFCI in basements)"),
    skill="plumbing",
))

register(Job(
    "retaining_wall", "carpentry", "build", "Build a block retaining wall (up to 4 ft)",
    "A segmental concrete block retaining wall no more than 4 ft high (from the bottom of the base) with nothing "
    "heavy above it: 811, a trench and compacted gravel base, the first course buried and level, each course set "
    "back, drainage gravel and a perforated drain behind, geogrid where the maker asks, caps. Taller walls, or ones "
    "holding up a driveway, a slope or a building, need an engineer's design.",
    ("retaining wall", "block wall in the yard", "landscape wall", "build a retaining wall", "garden wall"),
    ("utilities", "structural", "weather", "injury"),
    "Retaining walls over 4 ft, or with a load above them, need a permit and an engineered design in most places; "
    "lower walls often need neither. " + _LOCAL,
    ("a wall failing and falling when it's built too tall or without drainage", "digging into buried lines",
     "lifting heavy blocks", "a plate compactor's vibration and kickback"),
    ("work gloves", "steel-toe boots", "safety glasses", "hearing protection with the compactor and saw"),
    ("shovels and a pick", "plate compactor (rented)", "4 ft level and a torpedo level", "string line and stakes",
     "rubber mallet", "masonry saw or chisel for cuts", "wheelbarrow"),
    ("segmental retaining wall blocks and caps", "3/4 in crushed gravel for the base", "clean drainage gravel",
     "a 4 in perforated drain pipe in a sock", "filter fabric", "geogrid if the maker's chart calls for it",
     "concrete adhesive for the caps"),
    (
        Phase("Plan and permit before you dig", (
            Step("Check the height (4 ft or less from the bottom of the base, with no driveway, building or steep "
                 "slope above), the block maker's chart for that height and soil, and the permit.", "Retaining "
                 "walls fail from water and height; the chart says when grid or an engineer is needed.",
                 ("Over 4 ft or with a load above it: an engineer's design.",),
                 "The wall is within the maker's chart and any permit is in hand."),
            Step("Call 811 and wait for the marks.", "The trench runs where yard lines often go.", (),
                 "Every line is marked."),
        )),
        Phase("Base and first course", (
            Step("Dig the trench twice the block's depth wide and deep enough for 6 in of base plus the first "
                 "course buried (an inch for every 8 in of wall height, or the maker's rule).", "A buried first "
                 "course keeps the wall from sliding out at the bottom.", ("Hand-dig near any mark.",)),
            Step("Lay and compact the gravel base in lifts, level along the wall and front to back.",
                 "Every course above copies the base's mistakes.", ("Check level every few feet.",)),
            Step("Run a string line along the front of the base for the first course's face.",
                 "A straight first course gives a straight wall.", ("Curves: a garden hose laid out as the guide.",)),
            Step("Set the first course on the base, level block to block and front to back, and backfill in front "
                 "of it.", "The first course is the most important one.", (),
                 "The first course is level, buried and in line."),
        )),
        Phase("Courses and drainage", (
            Step("Lay the drain pipe behind the first course, sloped to daylight at an end, wrapped in its sock.",
                 "Water trapped behind the wall pushes it over.", ("End it where the water can run away.",)),
            Step("Stack each course with the joints staggered and the maker's setback, sweeping the tops clean.",
                 "Setback leans the wall into the soil it holds.", ()),
            Step("Fill behind each course with 12 in of clean drainage gravel, filter fabric between the gravel and "
                 "the soil, and lay geogrid at the courses the chart shows.", "Gravel lets water down to the drain; "
                 "fabric keeps the soil from clogging it.", ("Compact the soil behind in thin lifts, not near the "
                                                            "blocks with a heavy machine.",),
                 "Each course is set back and drained, with grid where the chart asks."),
        )),
        Phase("Cap and check", (
            Step("Glue the caps on with concrete adhesive, and finish the top with soil sloped away from the wall.",
                 "Water running toward the wall's top soaks the gravel behind it.", ()),
            Step("Plant or mulch the soil above and below the wall to keep it from washing.", "Bare soil washes into "
                 "the drainage gravel and clogs it.", ("No downspout dumping behind the wall.",)),
            Step("Check the wall's line and setback, and watch it through the first heavy rains.",
                 "A wall that moves will show it early.", (), "The wall is straight, capped and draining."),
        )),
    ),
    (_IRC + ": R404.4 (retaining walls)",
     "National Concrete Masonry Association, NCMA Design Manual for Segmental Retaining Walls (TEK 15-8)",
     "The block maker's installation guide and height charts"),
    skill="concrete",
))

register(Job(
    "window_replacement", "carpentry", "install", "Replace windows (insert replacements)",
    "Replacing old sash windows with insert (pocket) replacement windows in the existing frames: lead tested first "
    "on houses before 1978, three measurements each way, the old sashes and stops out, the sill checked for rot, the "
    "insert set on the sill angle, shimmed square, screwed, the gap insulated, the outside sealed and the stops back "
    "on. A full-frame replacement is the windows and doors job.",
    ("window replacement", "replace windows", "replacement windows", "new windows in old frames", "insert windows"),
    ("hazmat", "fall", "weather", "injury"),
    "Replacement windows often need a permit (egress and safety glass still apply) and, before 1978, lead-safe "
    "work on the old paint. " + _LOCAL,
    ("lead paint dust and chips (houses before 1978)", "broken glass from the old sashes", "falls at upper windows",
     "dropping a window from height"),
    ("safety glasses", "cut-resistant gloves", "a respirator for lead-safe work"),
    ("tape measure", "pry bar and putty knife", "utility knife", "drill/driver", "level and a square", "caulk "
     "gun", "a lead test kit"),
    ("the replacement windows (ordered to your measurements)", "shims", "the window's screws", "low-expansion foam "
     "or backer rod", "exterior sealant", "aluminum or vinyl capping for the old exterior trim, if wanted",
     "plastic sheeting for lead-safe work"),
    (
        Phase("Plan before ordering", (
            Step("On a house before 1978, test the paint for lead and set up lead-safe work (plastic inside and out, "
                 "misting, a HEPA vacuum) if it's positive.", "Window frames are the most common lead hazard in "
                 "old houses.", ("No dry sanding or scraping of lead paint.",),
                 "You know whether the paint has lead and how you'll contain it."),
            Step("Measure each frame's width at the top, middle and bottom and the height at the left, middle and "
                 "right; order to the smallest of each, and check its diagonals.", "Old frames are rarely square; "
                 "the smallest measurement is the one that fits.", ("Note bedrooms: egress still applies.",)),
        )),
        Phase("Remove the old sashes", (
            Step("Remove the inside stops carefully (they go back on), then the lower sash, the parting stops and "
                 "the upper sash; cut the sash cords and remove the pulleys or fill the weight pockets.",
                 "Careful removal saves the stops and the trim.", ("Insulate the empty weight pockets.",)),
            Step("Clean the old paint ridges and caulk from the frame where the window will sit, lead-safe if the "
                 "paint tested positive.", "A smooth frame lets the window sit tight to its stops.",
                 ("Mist and scrape, never dry-sand, lead paint.",)),
            Step("Check the sill and frame for rot; repair it with epoxy filler or new wood before going on.",
                 "A replacement on rotted wood fails with it.", (), "The frame is empty, sound and clean."),
        )),
        Phase("Set the window", (
            Step("Dry-fit the window, then run sealant on the outside stops (or the blind stop) where the window "
                 "will press against them.", "The seal at the outside stop is the weather seal.", ()),
            Step("Set the window on the sill's slope, centered, shimmed at the screw points until it's square and "
                 "the sashes run freely.", "Shims at the screws stop the frame bowing when they're tightened.",
                 ("Check the diagonals and open the sashes before tightening.",)),
            Step("Screw it to the frame through its holes, snug, not tight.", "Overtightened screws bow the frame "
                 "and the sash binds.", ()),
            Step("Check the sashes again: they open, close and lock with even gaps all around.", "Any bind now "
                 "means a shim or screw to adjust before sealing.", ("Adjust before foam: it's much harder after.",)),
            Step("Fill the gap around it with low-expansion foam or backer rod and sealant.", "The gap is where the "
                 "drafts were.", ("Ordinary foam can bow the frame.",), "The window is set, square, and sealed."),
        )),
        Phase("Finish and check", (
            Step("Seal the outside (and cap the old trim if you're capping it), and put the inside stops back.",
                 "The outside seal keeps the water out; the stops finish the inside.", ()),
            Step("Open, close and lock each window; clean up with a HEPA vacuum and wet wipe if there was lead.",
                 "A window that works now was set right.", (), "Every window works and the area is clean."),
        )),
    ),
    ("EPA, Renovation, Repair and Painting Rule (40 CFR 745) and its Steps to Lead Safe Renovation guide",
     "ASTM E2112-19, Standard Practice for Installation of Exterior Windows, Doors and Skylights",
     "The replacement window maker's measuring and installation guide"),
    skill="carpentry",
))

register(Job(
    "garage_door_opener", "appliances", "install", "Install a garage door opener",
    "A new garage door opener on a door that's already balanced and working: the door checked first (springs are a "
    "technician's), the rail mounted at the wall above the door and the motor hung from the ceiling framing, the arm "
    "to the door, safety sensors low on each side, a wall button out of a child's reach, the limits and force set, "
    "and the reversal test.",
    ("garage door opener", "install a garage door opener", "new garage door opener", "replace the garage door "
     "opener"),
    ("live_power", "licensed", "fall", "injury"),
    "An opener often needs no permit, but a new receptacle in the ceiling does. Springs and cables are a garage door "
    "technician's work. " + _LOCAL,
    ("garage door springs and cables (deadly force: never touch them)", "a door that crushes when the reversal "
     "isn't set", "falls from the ladder mounting the motor", "electric shock at the receptacle"),
    ("safety glasses", "work gloves", "a steady ladder"),
    ("drill/driver and bits", "socket set", "ladder (two help)", "level", "tape", "a 2x4 for the reversal test"),
    ("the opener with its rail, sensors and wall button", "angle iron or perforated strap to hang the motor",
     "lag screws for the bracket and hangers", "a ceiling receptacle near the motor (by an electrician if there "
     "isn't one)"),
    (
        Phase("Plan before mounting", (
            Step("Check the door: with the old opener disconnected, does it lift easily and stay put halfway "
                 "open?", "An opener can't fix a door out of balance and wears out fast on one.",
                 ("Heavy or drops: call a garage door technician to adjust the springs.",),
                 "The door is balanced and runs smoothly by hand."),
            Step("Check there's a receptacle on the ceiling within the cord's reach, or have one installed.",
                 "An extension cord to an opener is a fire risk.", ()),
        )),
        Phase("Mount the opener", (
            Step("Assemble the rail and fasten its bracket to the framing on the wall above the door, centered.",
                 "The bracket takes the door's pull.", ("Into solid framing, not drywall.",)),
            Step("Remove the door's lock or disable it so the opener can't pull against a locked door.",
                 "An opener fighting a lock bends the door or burns out.", ("Keep the emergency release cord within reach, 6 ft up.",)),
            Step("Raise the motor end, level the rail, and hang the motor from the ceiling framing with angle "
                 "iron or strap.", "A sagging motor binds the rail.",
                 ("Keep the rail parallel to the door's track.",)),
            Step("Attach the arm to the door's bracket on the top section's reinforced spot.", "The top section is "
                 "made to take the pull there.", (), "The opener is mounted, level and connected to the door."),
        )),
        Phase("Sensors and controls", (
            Step("Mount the safety sensors on each side of the door no more than 6 in above the floor, aimed at "
                 "each other, wires stapled.", "The sensors stop the door closing on a person or pet.",
                 ("Both sensor lights steady means they see each other.",)),
            Step("Mount the wall button at least 5 ft up, in sight of the door, away from moving parts.",
                 "Out of a child's reach, in sight of anyone in the way.", ()),
            Step("Plug the opener in and program the remotes and any keypad.", "The opener's manual gives the "
                 "steps.", (), "Sensors, button and remotes work."),
            Step("Fit the emergency release cord and its label, and show everyone how it works.", "In a power "
                 "failure the release is the only way to open the door.", ("Only pull it with the door closed.",)),
        )),
        Phase("Set and check", (
            Step("Set the open and close limits and the force as the manual says.", "Too much force is how doors "
                 "hurt people.", ("Use the least force that closes the door fully.",)),
            Step("Test the reversal: lay a 2x4 flat under the door and close it; it must reverse on touching it. "
                 "Then wave something through the sensors while it closes; it must reverse.", "This is the safety "
                 "the law requires.", ("Test monthly.",), "The door reverses on the board and at the sensors."),
        )),
    ),
    ("US Consumer Product Safety Commission, 16 CFR 1211 (safety standard for automatic residential garage door "
     "operators) and UL 325",
     "International Door Association, Garage Door Safety: springs and cables",
     "The opener maker's installation manual"),
    skill="carpentry",
))


# ------------------------------------------------------------------ the third tier (2026-11-09)

register(Diagnosis(
    "water_heater_leaking", "plumbing", "A leaking water heater",
    ("water heater leaking", "water under the water heater", "water heater is leaking", "puddle by the water heater",
     "hot water tank leaking"),
    ("gas", "live_power", "injury"),
    "If you smell gas, leave and call the gas utility from outside. Turn off an electric heater's breaker before "
    "touching it; for gas, turn its control to OFF. The water and the relief valve's pipe can scald.",
    "where",
    (
        DiagCheck("where", "Dry the floor and the tank with towels, then watch. Is water coming from the relief "
                  "valve's discharge pipe (on the side or top)?",
                  "A dripping relief valve means too much pressure or heat, or a worn valve; it isn't the tank.",
                  "relief", "fittings"),
        DiagCheck("relief", "Is there an expansion tank on the cold line, and is the house's water pressure under "
                  "80 psi (a hose-bib gauge)?", "High pressure or a closed system without an expansion tank lifts "
                  "the relief valve.",
                  "cause:a worn relief valve: a plumber replaces it (never cap or plug the discharge pipe)|",
                  "cause:pressure or thermal expansion is lifting the relief valve: add an expansion tank or a "
                  "pressure regulator (a plumber's job where required)|"),
        DiagCheck("fittings", "Is water at the pipe connections on top, the drain valve at the bottom, or a nearby "
                  "pipe dripping onto it?", "Connections and the drain valve leak and are fixable; the tank isn't.",
                  "cause:a leaking connection or drain valve: tighten the fitting or the drain valve a little, or "
                  "replace the drain valve's washer or the connector|", "tank"),
        DiagCheck("tank", "Is the water coming from the bottom of the tank itself, under its jacket?",
                  "Water from the tank body means the tank has rusted through: it can't be repaired.",
                  "cause:the tank has failed: turn off its power or gas and the cold supply, drain it, and replace "
                  "it|water_heater", "pro:a plumber; say there's water near the heater from no fitting, valve or "
                  "pipe you can find (perhaps condensation, the drain pan, or a leak inside the wall)"),
    ),
    ("The water heater maker's owner's manual (its relief valve and drain valve)",
     "International Code Council, International Residential Code (IRC) 2021: P2804 (relief valves), P2903.4 "
     "(thermal expansion)",
     "US Department of Energy, Water Heater Maintenance"),
))

register(Diagnosis(
    "toilet_clogged", "plumbing", "A clogged toilet",
    ("toilet clogged", "toilet won't flush", "toilet is clogged", "toilet overflowing", "toilet backed up",
     "clogged toilet"),
    ("injury",),
    "If the bowl is about to overflow, lift the tank lid and push the flapper down, or turn off the valve behind the "
    "toilet. Don't keep flushing a clogged toilet, and don't add drain chemicals.",
    "others",
    (
        DiagCheck("others", "Are other drains backing up too (a tub filling when it's flushed, the lowest floor's "
                  "drain)?", "Several fixtures together means the main line, not the toilet.",
                  "pro:a plumber or drain service; say the toilet and other drains back up together (the main line "
                  "or sewer needs a cable)", "plunge"),
        DiagCheck("plunge", "With a flange plunger (the one with the extra rubber sleeve) sealed over the hole and "
                  "water covering it, plunge firmly 15 to 20 times. Does it drain?",
                  "A flange plunger seals the toilet's outlet where a cup plunger can't.",
                  "cause:a soft clog the plunger cleared: flush once to check|", "auger"),
        DiagCheck("auger", "Feed a closet auger (toilet auger) into the bowl, cranking as you push, then pull it "
                  "back. Does it drain now?", "A closet auger reaches through the toilet's trap without "
                  "scratching the bowl.", "cause:a clog in the toilet's trap the auger cleared|", "object"),
        DiagCheck("object", "Could something solid have gone down it (a toy, a phone, wipes)?",
                  "A solid object can't be pushed through; the toilet has to come up.",
                  "cause:an object stuck in the toilet: turn off the water, take the toilet off its flange and "
                  "remove it from below, then reset it on a new wax ring|replace_toilet",
                  "pro:a plumber; say a toilet stays clogged after a flange plunger and a closet auger"),
    ),
    ("Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)",
     "Family Handyman, How to Unclog a Toilet",
     "The toilet maker's owner's guide"),
))

register(Diagnosis(
    "dishwasher_not_draining", "appliances", "A dishwasher that won't drain",
    ("dishwasher not draining", "water in the dishwasher", "dishwasher won't drain", "dishwasher full of water",
     "standing water in dishwasher"),
    ("live_power", "injury"),
    "Turn the dishwasher off at its breaker (or unplug it) before reaching into its sump, and watch for broken "
    "glass in the filter.",
    "filter",
    (
        DiagCheck("filter", "Bail out the water, then twist out the filter under the bottom rack. Is it clogged?",
                  "A clogged filter is the most common cause and takes a minute to clean.",
                  "cause:a clogged filter: rinse it, put it back, and run a rinse cycle|", "disposal"),
        DiagCheck("disposal", "Does it drain into a garbage disposal that was just installed, or is the disposal "
                  "full?", "A new disposal's drain plug (knockout) left in blocks the dishwasher; a full disposal "
                  "backs it up.", "cause:the disposal's knockout plug was never removed, or the disposal is full: "
                  "knock out the plug (disposal unplugged) or run the disposal|", "hose"),
        DiagCheck("hose", "Under the sink, is the drain hose kinked, or is the air gap on the sink clogged?",
                  "A kink or a clogged air gap stops the water leaving.",
                  "cause:a kinked drain hose or a clogged air gap: straighten the hose (with its high loop) or "
                  "clean the air gap's cap|", "pump"),
        DiagCheck("pump", "Run a drain cycle and listen. Is there a hum but no draining?",
                  "A hum with no draining means the pump is jammed by glass or a bone, or has failed.",
                  "pro:an appliance technician; say it hums on drain with a clean filter and a clear hose (the "
                  "drain pump is jammed or failed)",
                  "pro:an appliance technician; say it makes no sound on drain (the pump, its wiring or the control)"),
    ),
    ("The dishwasher maker's owner's manual (filter and drain)",
     "International Code Council, International Residential Code (IRC) 2021: P2717 (dishwashers: air gap or high "
     "loop)",
     "Family Handyman, Dishwasher Not Draining"),
))

register(Diagnosis(
    "washer_not_draining", "appliances", "A washing machine that won't drain or spin",
    ("washer not draining", "washing machine won't drain", "washer won't spin", "water in the washer",
     "clothes soaking wet after wash"),
    ("live_power", "injury"),
    "Unplug the washer before opening its pump filter or moving it, and have towels and a pan ready: the water "
    "comes out when the filter opens.",
    "lid",
    (
        DiagCheck("lid", "Is the lid or door closing fully (its lock clicks or its light shows locked)?",
                  "Washers won't drain or spin with the lid switch open.",
                  "load", "cause:the lid or door isn't latching: check for clothing in the latch, and the lid "
                  "switch or lock may need replacing|"),
        DiagCheck("load", "Was it one heavy or unbalanced load (a rug, a comforter)?",
                  "An unbalanced load stops the spin to protect the machine.",
                  "cause:an unbalanced load: spread it out (or remove the heavy item) and run spin again|", "filter"),
        DiagCheck("filter", "On a front-loader, open the small door at the bottom front and drain and clean the pump "
                  "filter. Was it clogged (coins, hair ties, lint)?", "The pump filter catches what comes out of "
                  "pockets.", "cause:a clogged pump filter: clean it and run a drain cycle|", "hose"),
        DiagCheck("hose", "Is the drain hose kinked behind the machine, or the standpipe or laundry sink clogged?",
                  "Water can't leave through a kinked hose or a blocked drain.",
                  "cause:a kinked hose or a clogged standpipe: straighten the hose or clear the drain|",
                  "pro:an appliance technician; say it won't drain with a latched lid, a clean pump filter and a "
                  "clear hose (likely the drain pump or the control)"),
    ),
    ("The washer maker's owner's manual (pump filter and error codes)",
     "Family Handyman, Washing Machine Not Draining",
     "US Consumer Product Safety Commission, appliance safety guidance"),
))

register(Diagnosis(
    "fridge_not_cooling", "appliances", "A refrigerator that isn't cold",
    ("fridge not cooling", "refrigerator not cold", "fridge is warm", "freezer not freezing", "fridge stopped "
     "working", "refrigerator warm"),
    ("live_power", "injury"),
    "Unplug it before cleaning the coils or touching anything behind the panels. Move food to a cooler with ice if "
    "it's been above 40 F for more than 2 hours: perishables should be thrown out then.",
    "power",
    (
        DiagCheck("power", "Is the light on when you open it, and the control set to its normal setting?",
                  "No power or a control turned down is the simplest cause.",
                  "door", "cause:no power or the control was turned off: check the outlet and breaker, and set the "
                  "control back|"),
        DiagCheck("door", "Do the doors close and seal all the way (a dollar bill closed in the gasket should "
                  "drag)?", "A door held open by a shelf or a worn gasket lets the cold out.",
                  "coils", "cause:a door not sealing: move what blocks it, clean the gasket, or replace it|"),
        DiagCheck("coils", "Are the condenser coils (under the front grille or on the back) thick with dust?",
                  "Dusty coils can't shed heat, so it can't cool.",
                  "cause:dirty condenser coils: unplug it and vacuum or brush them, then give it a day|", "fans"),
        DiagCheck("fans", "Is the freezer cold but the fridge warm, or can you hear the compressor run but no fan "
                  "inside the freezer?", "The fridge is cooled by air the freezer's fan sends; a frosted coil or "
                  "a stopped fan stops it.",
                  "cause:the evaporator is frosted over or its fan stopped (a defrost fault): unplug it with the "
                  "doors open for a day to defrost it; if it returns, a technician replaces the defrost part|",
                  "pro:an appliance technician; say it has power, sealed doors and clean coils but isn't cold "
                  "anywhere (the compressor, its relay or the sealed system)"),
    ),
    ("The refrigerator maker's owner's manual (care and troubleshooting)",
     "USDA Food Safety and Inspection Service, Refrigeration and Food Safety",
     "Family Handyman, Refrigerator Not Cooling"),
))

register(Diagnosis(
    "well_pump_no_water", "plumbing", "No water from a well",
    ("well pump", "no water from the well", "well not working", "well pump not working", "no water pressure well",
     "well pump won't turn on"),
    ("live_power", "licensed", "injury"),
    "A well pump runs on 240 volts. Never open the pressure switch's cover or the control box with the breaker on, "
    "and keep the pressure switch's cover closed while testing; a submersible pump in the well is a pump "
    "contractor's job.",
    "breaker",
    (
        DiagCheck("breaker", "Is the well pump's breaker (often a double 20 or 30 A) on and not tripped?",
                  "No power is the most common reason the water stops.",
                  "gauge", "cause:the pump's breaker was off or tripped: reset it once; if it trips again, leave it "
                  "off and call a pump contractor or electrician|"),
        DiagCheck("gauge", "What does the pressure gauge on the tank read: near zero?",
                  "Near zero with power on means the pump isn't filling the tank.",
                  "click", "pro:a plumber or pump contractor; say the gauge reads normal but the house has little "
                  "or no water (a clogged filter, a closed valve, or a pipe problem past the tank)"),
        DiagCheck("click", "Stand by the pressure switch (cover closed) while someone opens a faucet. Do you hear it "
                  "click on and the pump start?", "The switch clicking on but no water means the pump or the well; "
                  "no click means the switch or its cutoff.",
                  "pro:a well pump contractor; say the pressure switch clicks on but the tank won't build pressure "
                  "(the pump, a broken pipe in the well, or a low well)", "switch"),
        DiagCheck("switch", "Is there a lever on the side of the pressure switch (a low-pressure cutoff), and has "
                  "it tripped because the pressure fell too low?",
                  "Low-pressure cutoff switches stay off after the well ran dry or the pump lost prime.",
                  "cause:the low-pressure cutoff tripped: hold the lever up for a few seconds to restart; if it "
                  "won't hold pressure, the well may be low or the pump failing, so call a pump contractor|",
                  "pro:a well pump contractor; say the pump has power but the tank pressure stays near zero (the "
                  "pressure switch, the control box, the pump or the well)"),
    ),
    ("National Ground Water Association, Water Well Owner's Manual: troubleshooting",
     "The pressure switch and pump makers' manuals",
     "US EPA, Private Drinking Water Wells"),
))

register(Diagnosis(
    "ice_dam", "exterior", "Ice dams and icicles on the roof edge",
    ("ice dam", "ice dams", "icicles on the roof", "water coming in when snow melts", "ice on the gutters",
     "roof leaking in winter"),
    ("fall", "weather", "injury"),
    "Never climb onto an icy roof or chip ice with a hammer or axe: you can fall and tear the shingles. Stay out "
    "from under heavy icicles, and keep to the ground.",
    "leak",
    (
        DiagCheck("leak", "Is water coming inside (stains on a ceiling or the top of a wall near the eaves)?",
                  "Ice dams push melting water up under shingles; a leak inside needs action now.",
                  "rake", "attic"),
        DiagCheck("rake", "Can you pull the snow off the lower 3 to 4 ft of roof from the ground with a roof rake?",
                  "Removing the snow above the dam takes away its water.",
                  "gutters", "pro:a roofer or ice-dam steaming service; say ice dams are leaking inside and the snow "
                  "can't be raked from the ground (never chip it)"),
        DiagCheck("gutters", "Are the gutters and downspouts frozen solid, so melt water has nowhere to go?",
                  "Frozen gutters hold the melt at the roof edge and make the dam worse.",
                  "cause:frozen gutters and downspouts holding the melt: clear the downspouts when it thaws, and heat "
                  "cable along the eaves can be a stopgap; the lasting cure is keeping the attic cold|"
                  "attic_ventilation", "attic"),
        DiagCheck("attic", "In the attic, is the underside of the roof warm, or is insulation thin or missing in "
                  "places, or does warm air come up around lights, pipes or the hatch?",
                  "Ice dams form when heat from the house melts the snow on the roof above the eaves.",
                  "cause:heat escaping into the attic melts the snow: seal the leaks into the attic, add insulation "
                  "and open the soffit vents|attic_ventilation",
                  "pro:a roofer or energy auditor; say ice dams form though the attic stays cold (the roof may need "
                  "an ice barrier or better venting)"),
    ),
    ("US Department of Energy, Energy Saver: Air Sealing and Insulation (ice dams)",
     "Building Science Corporation, BSI-046: Dam Ice Dam",
     "International Code Council, International Residential Code (IRC) 2021: R905.1.2 (ice barrier)"),
))

register(Diagnosis(
    "bathroom_mold", "carpentry", "Mold in a bathroom",
    ("bathroom mold", "mold in the bathroom", "mildew in the shower", "black mold", "mold on the ceiling",
     "musty bathroom"),
    ("hazmat", "injury"),
    "Never mix bleach with ammonia or other cleaners. Wear gloves, eye protection and an N95 while cleaning, open a "
    "window, and stop if anyone has trouble breathing. Mold over about 10 sq ft is a professional's job.",
    "size",
    (
        DiagCheck("size", "Is the mold larger than about 10 sq ft (a 3 by 3 ft patch), or inside the walls?",
                  "Large or hidden mold needs containment that cleaning from the surface can't give.",
                  "pro:a mold remediation professional; say how large it is and where, and whether there's been "
                  "a leak", "surface"),
        DiagCheck("surface", "Is it on a hard surface (tile, grout, a tub, a painted wall) rather than soaked into "
                  "drywall or the ceiling?", "Mold on hard surfaces cleans off; mold in drywall comes back.",
                  "fan", "cause:mold in soaked drywall: the wet section is cut out and replaced once the leak is "
                  "fixed|drywall_patch"),
        DiagCheck("fan", "Does the bathroom have an exhaust fan vented outside, run during and 20 minutes after "
                  "showers?", "Mold comes back wherever moisture stays; the fan is what removes it.",
                  "leak", "cause:too little ventilation: clean the mold with detergent and water, dry it, and add "
                  "or fix an exhaust fan vented outside|attic_ventilation"),
        DiagCheck("leak", "Is anything leaking: a dripping valve, cracked grout or caulk, a leak from above?",
                  "Mold on a ventilated bathroom points at a leak.",
                  "cause:a leak feeding it: fix the leak or recaulk, then clean and dry|recaulk_tub",
                  "cause:surface mildew in a humid room: clean it with detergent and water, dry it, and keep the "
                  "fan running longer after showers|"),
    ),
    ("US EPA, A Brief Guide to Mold, Moisture, and Your Home (EPA 402-K-02-003)",
     "US EPA, Mold Remediation in Schools and Commercial Buildings (the 10 sq ft rule)",
     "Centers for Disease Control and Prevention, Mold: cleanup and safety"),
))

register(Diagnosis(
    "door_sticking", "carpentry", "A door that sticks or won't latch",
    ("door sticking", "door sticks", "door won't latch", "door won't close", "door rubs", "door is hard to close"),
    ("structural", "injury"),
    "Wear safety glasses when planing or driving long screws, and have a helper hold a door off its hinges. A door "
    "that suddenly won't close along with new cracks in the walls can mean the house is settling: that needs a look "
    "from a professional.",
    "cracks",
    (
        DiagCheck("cracks", "Did it start suddenly, with new diagonal cracks above doors or windows nearby?",
                  "Sudden sticking with new cracks can be the foundation moving, not the door.",
                  "pro:a structural engineer or foundation contractor; say doors started sticking with new "
                  "diagonal cracks around them", "hinges"),
        DiagCheck("hinges", "Are any hinge screws loose (especially the top hinge)?",
                  "A loose top hinge lets the door sag into the frame.",
                  "cause:loose hinge screws: tighten them, or replace one in the top hinge with a 3 in screw into "
                  "the framing|", "where"),
        DiagCheck("where", "Close it slowly. Does it rub at the top on the latch side, or only in humid weather?",
                  "Rubbing high on the latch side is sag; only in humidity is the wood swelling.",
                  "cause:the door has sagged or swelled: shim the bottom hinge or plane the edge that rubs, then "
                  "seal the planed edge so it doesn't swell again|", "strike"),
        DiagCheck("strike", "Does it close but the latch misses the strike plate?",
                  "A strike plate a little off is fixed by moving or filing it.",
                  "cause:the latch misses the strike: file the strike opening or move the plate|",
                  "pro:a carpenter; say a door rubs or won't latch with tight hinges and no new cracks (the frame "
                  "may be out of square)"),
    ),
    ("Gary Katz, The Doorhanger's Handbook (Taunton, 1998)",
     "This Old House, How to Fix a Sticking Door",
     "American Society of Home Inspectors (ASHI), signs of foundation movement"),
))

register(Diagnosis(
    "squeaky_floor", "carpentry", "A squeaky floor",
    ("squeaky floor", "floor squeaks", "creaky floor", "floor creaks", "squeaking floor", "floor is squeaking"),
    ("structural", "injury"),
    "Drilling or screwing into a floor: know where pipes, ducts and wires run below first. A floor that sags or "
    "bounces as well as squeaks needs its framing looked at.",
    "below",
    (
        DiagCheck("below", "Can you reach the floor from below (an open basement or crawlspace ceiling)?",
                  "From below, the gap that squeaks can be shimmed without touching the finished floor.",
                  "gap", "carpet"),
        DiagCheck("gap", "With someone walking on the squeak, is there a gap between the subfloor and a joist "
                  "right there?", "A gap lets the boards move against the joist or the nails.",
                  "cause:a gap between subfloor and joist: glue a thin shim into it (don't force it up), or screw a "
                  "cleat to the joist tight under the subfloor|", "sag"),
        DiagCheck("sag", "Does the floor also sag or bounce noticeably there?",
                  "Sag and bounce mean the joist itself may be cut, cracked or too small.",
                  "pro:a carpenter or structural engineer; say a floor squeaks and sags or bounces (a joist may be "
                  "damaged or undersized)", "cause:a loose subfloor: drive construction screws through the "
                  "subfloor into the joist from below (short enough not to come through)|"),
        DiagCheck("carpet", "Is it carpeted?", "Carpet hides the floor, so the fix goes through it.",
                  "cause:a loose subfloor under carpet: a squeak-repair kit's breakaway screws go through the "
                  "carpet into the joist|", "cause:a loose floor from above (wood or vinyl): screw through the "
                  "subfloor at the joist with trim-head screws where it can be hidden, or a top-down repair kit|"),
    ),
    ("Fine Homebuilding, Fixing Squeaky Floors",
     "This Old House, How to Fix Squeaky Floors",
     "American Wood Council, Span Tables for Joists and Rafters (2018)"),
))

register(Job(
    "drywall_patch", "carpentry", "repair", "Patch a hole in drywall",
    "Repairing a hole in a drywall wall or ceiling: small dents and nail holes filled, mid-size holes with a mesh "
    "patch, and larger holes (or water-damaged board) cut back to a square, backed, and patched with new board, then "
    "taped, coated, sanded and primed to match. Finding and fixing a leak behind it comes first.",
    ("drywall patch", "patch drywall", "hole in the wall", "patch a hole", "fix drywall", "repair drywall"),
    ("hazmat", "injury"),
    "Patching drywall needs no permit. In a house built before 1980, the old joint compound or texture may hold "
    "asbestos: test before sanding or cutting it. " + _LOCAL,
    ("pipes and cables hidden behind the wall", "joint-compound dust", "asbestos in old texture or compound (houses "
     "before 1980)", "knife cuts"),
    ("a dust mask", "safety glasses"),
    ("utility knife and a drywall saw", "a stud finder", "taping knives (4, 6 and 10 in)", "a sanding sponge",
     "a drill/driver", "a square or straightedge"),
    ("joint compound (setting type for the first coat, lightweight after)", "a self-adhesive mesh patch for small "
     "holes", "a piece of drywall the same thickness", "furring strips or wood backer", "drywall screws", "paper or "
     "mesh tape", "primer and the wall's paint"),
    (
        Phase("Plan before cutting", (
            Step("Find out what made the hole and whether the wall is wet; fix any leak and let it dry first.",
                 "A patch over a wet wall fails and grows mold.", ("Press the board: soft or stained means water.",),
                 "The cause is fixed and the wall is dry."),
            Step("Check behind the wall with a stud finder and a light through the hole for pipes, cables and ducts.",
                 "A saw blade into a pipe or cable turns a patch into a repair.", ("Cut shallow near anything you "
                                                                                  "can't see.",)),
            Step("In a house before 1980, test the compound or texture before sanding or cutting it.",
                 "Old compound and popcorn texture can hold asbestos.", ()),
        )),
        Phase("Prepare the hole", (
            Step("For a hole up to about 4 in, clean its edges and press a self-adhesive mesh patch over it.",
                 "Mesh bridges a small hole without backing.", ("Cut away torn paper so it doesn't bubble.",)),
            Step("For a bigger hole, mark a square around it, cut it out with the drywall saw, and screw furring "
                 "strips inside the hole at the edges as backing.", "A square opening takes a square patch that "
                 "fits; backing gives the screws something to hold.", ("Keep the cut on the board, not into a "
                                                                       "stud.",)),
            Step("Cut a new piece of drywall to fit the square, and screw it to the backing, flush with the wall.",
                 "A patch proud of the wall can't be hidden.", (),
                 "The hole is covered flush with mesh or a patch screwed to backing."),
        )),
        Phase("Tape and coat", (
            Step("Tape the patch's seams and bed the tape in setting compound; cover a mesh patch with a first "
                 "coat.", "Setting compound hardens fast and doesn't shrink.", ("Press the tape flat: air under it "
                                                                                "blisters.",)),
            Step("Add a second coat wider than the first, feathering the edges out several inches.", "Wide, thin "
                 "coats blend into the wall.", ("Let each coat dry fully.",)),
            Step("Add a third, wider coat if the edges still show.", "Each coat hides the one below.", (),
                 "The patch is coated with no tape showing."),
        )),
        Phase("Sand, prime and check", (
            Step("Sand smooth with a sponge, checking with a light held flat to the wall.", "Raking light shows "
                 "every bump paint would.", ("Don't sand through to the tape.",)),
            Step("Prime the patch, then paint the whole wall section (corner to corner if the color won't blend).",
                 "Unprimed compound flashes through paint.", ("Match texture first on a textured wall.",)),
            Step("Look at it in daylight and lamplight and touch up what shows.", "Different light shows different "
                 "flaws.", (), "The patch can't be seen from across the room."),
        )),
    ),
    ("Gypsum Association, GA-216: Application and Finishing of Gypsum Panel Products",
     "Myron R. Ferguson, Drywall: Professional Techniques for Great Results (Taunton, 4th ed.)",
     "US EPA, Protect Your Family from Exposures to Asbestos"),
    skill="drywall",
))

register(Job(
    "replace_toilet", "plumbing", "repair", "Replace (or reset) a toilet",
    "Taking a toilet up and setting a new one (or the same one again): the water off and the bowl emptied, the old "
    "toilet and wax ring out, the flange checked and repaired, the new toilet set on a new ring, bolted evenly, the "
    "supply connected, tested and caulked. Moving the drain is a rough-in job.",
    ("replace the toilet", "new toilet", "install a toilet", "reset the toilet", "toilet replacement",
     "pull the toilet", "replacing the toilet", "replacing a toilet"),
    ("hazmat", "injury"),
    "Replacing a toilet in place usually needs no permit; moving it does. " + _LOCAL,
    ("a heavy, slippery bowl dropped (cracked porcelain cuts)", "back strain", "sewer gas from the open flange",
     "old flooring around it in a house before 1980"),
    ("gloves", "safety glasses", "knee pads"),
    ("adjustable wrench and a socket for the bolts", "putty knife", "sponge and bucket", "a level", "hacksaw or "
     "oscillating tool (for stuck bolts)", "tape measure"),
    ("the new toilet (its rough-in distance matching the old)", "a wax ring (or wax-free seal)", "new closet bolts",
     "a braided supply line", "shims", "a flange repair ring if the flange is broken", "silicone or caulk"),
    (
        Phase("Plan before taking it up", (
            Step("Measure the rough-in: from the finished wall to the center of the bolts (commonly 12 in, sometimes "
                 "10 or 14), and buy a toilet to match.", "A toilet with the wrong rough-in won't fit.",
                 ("Measure from the wall, not the baseboard.",), "The new toilet matches the rough-in."),
            Step("Shut off the valve behind it, flush and hold the handle to empty the tank, and sponge out the "
                 "bowl.", "Less water means less mess and a lighter toilet.", ()),
        )),
        Phase("Remove the old toilet", (
            Step("Disconnect the supply, remove the nuts from the bolts, rock the toilet gently to break the seal, "
                 "and lift it straight up onto an old towel.", "Lifting straight up keeps the remaining water in "
                 "the trap.", ("Get help: a toilet weighs 60 to 120 lb.",)),
            Step("Stuff a rag in the drain opening, and scrape the old wax off the flange.", "The rag keeps sewer "
                 "gas and tools out of the drain.", ("Take the rag out before setting the new one.",)),
            Step("Check the flange: screwed to the floor, not cracked, and sitting at or a little above the finished "
                 "floor.", "A broken or low flange is the usual reason a toilet leaks.", ("Broken: a repair ring "
                                                                                          "over it.",),
                 "The flange is sound, fastened and at the right height."),
        )),
        Phase("Set the new toilet", (
            Step("Put new bolts in the flange's slots, press the wax ring onto the horn under the bowl (or the flange), "
                 "and remove the rag.", "A new ring every time: a used one doesn't reseal.", ()),
            Step("Lower the toilet straight down over the bolts, press it down with your weight, and check it's "
                 "level and doesn't rock.", "Setting it once, straight, keeps the wax seal whole.",
                 ("Rocking: shim it now, before tightening.",)),
            Step("Tighten the nuts a little at a time, side to side, until snug, and cut the bolts off above the "
                 "nuts.", "Overtightening cracks the porcelain.", ()),
            Step("Attach the tank if it's separate (tank bolts tightened evenly), then the supply line.",
                 "An uneven tank leaks at its bolts.", (), "The toilet is set, level, bolted and supplied."),
        )),
        Phase("Test and check", (
            Step("Turn the water on, let it fill, flush several times, and check the base and supply for drips.",
                 "Leaks show in the first flushes.", ("A leak at the base means the seal didn't take: reset with a "
                                                     "new ring.",)),
            Step("Caulk the base to the floor, leaving the back open, and put the bolt caps on.", "The open back "
                 "lets a future leak show.", (), "The toilet flushes cleanly and is dry everywhere."),
            Step("Take the old toilet out in a bag or wrapped, and wipe the floor where it sat.", "A drip of wax "
                 "or water left on the floor is a slip.", ("Check your area's rules for disposing of porcelain.",)),
        )),
    ),
    ("International Code Council, International Residential Code (IRC) 2021: P2705 (fixture installation)",
     "The toilet maker's installation instructions",
     "Peter Hemp, Plumbing a House (Taunton, For Pros by Pros, 1998)"),
    skill="plumbing",
))

register(Job(
    "replace_receptacle", "electrical", "repair", "Replace a receptacle or switch",
    "Swapping a worn or broken receptacle or wall switch for a new one of the same kind on the same circuit: the "
    "breaker off, the power proven dead, the old device's wires noted and moved one at a time, GFCI or tamper-"
    "resistant devices where the code now asks, and the new one tested. Adding a device or a circuit is a wiring job.",
    ("replace an outlet", "replace a receptacle", "replace a switch", "new outlet", "broken outlet",
     "outlet replacement", "change a light switch"),
    ("live_power", "licensed", "injury"),
    "Replacing a device like-for-like often needs no permit, but some places require one, and some reserve all "
    "electrical work for a licensed electrician. " + _LOCAL,
    ("electric shock from a circuit not proven dead", "a box fed by two circuits", "aluminum wiring (in some houses "
     "from the 1960s and 70s)", "a burned box or wires (a sign of a bigger problem)"),
    ("insulated gloves for testing", "safety glasses"),
    ("non-contact and two-lead voltage testers", "insulated screwdrivers", "wire strippers", "needle-nose pliers",
     "a receptacle tester with a GFCI button"),
    ("the new receptacle or switch (same amp rating; tamper-resistant, GFCI or weather-resistant where required)",
     "a cover plate", "wire connectors and a short pigtail wire if needed", "electrical tape"),
    (
        Phase("Plan before opening the box", (
            Step("Find what the device is (15 or 20 A, a switch, a 3-way) and buy the same, with tamper resistance "
                 "or GFCI where your code now asks (kitchens, baths, garages, outdoors).", "A 15 A device on a 20 A "
                 "circuit is allowed only in some places; a GFCI where one is required protects people.",
                 ("Aluminum wires: stop; they need special devices or an electrician.",),
                 "You have the right device and know whether your area allows the work."),
            Step("Turn off the breaker and tag it, then prove the device dead: test the tester on a live outlet, "
                 "test both sides of the device, test the tester again.", "Labels on panels are often wrong.",
                 ("Test every wire in the box: some boxes have two circuits.",)),
            Step("With the cover off, check the box is fastened in the wall and not cracked.", "A loose box lets "
                 "the device move and its wires loosen.", ("A loose box gets fixed before the new device goes in.",)),
        )),
        Phase("Take out the old device", (
            Step("Remove the cover and the device's screws, and pull it out gently with the wires attached.",
                 "Pulling slowly keeps the wires whole.", ("Test again now with the wires in view.",)),
            Step("Photograph or label which wire goes where (hot to brass, neutral to silver, ground to green, "
                 "and any wires on a second set of screws or a 3-way's common).", "The photo is the map for the new "
                 "one.", ("Two sets of wires on a receptacle: the tab between its screws may be broken off on "
                          "purpose.",)),
            Step("Look for heat damage: melted insulation, darkened wires or a scorched box.", "Burn marks mean a "
                 "loose connection or an overload: a bigger problem than the device.",
                 ("Any burning: stop and call an electrician.",),
                 "The old device is out, its wiring recorded, and nothing is burned."),
        )),
        Phase("Install the new one", (
            Step("Move each wire from the old device to the same place on the new one, one at a time, wrapped "
                 "clockwise around the screw, on the screws rather than push-in holes.", "Clockwise loops tighten "
                 "as the screw does; push-in holes loosen.", ("No bare copper showing past the screw.",)),
            Step("For a GFCI, put the incoming wires on LINE and the onward ones on LOAD.", "Swapped, it either "
                 "won't reset or protects nothing downstream.", ()),
            Step("In a metal box, wrap the device's side screws with electrical tape.", "Tape keeps the live "
                 "screws from touching the box.", ("Two turns, covering every side screw.",)),
            Step("Fold the wires in, screw the device straight in the box, and fit the cover.", "Pinched wires "
                 "short.", (), "The device is wired to the record, mounted and covered."),
        )),
        Phase("Test and check", (
            Step("Turn the breaker on and test: the plug-in tester (and its GFCI button), or the switch working its "
                 "light (both ends of a 3-way).", "A tester shows reversed polarity or an open ground the eye can't.",
                 ("Any fault: breaker off and recheck the wires.",)),
            Step("Feel the cover after a few minutes under load; any warmth means a loose connection.", "Heat at a "
                 "device is the start of a fire.", (), "It works, tests right and stays cool."),
        )),
    ),
    ("National Fire Protection Association, NFPA 70 National Electrical Code (NEC) 2023: 406.4(D) (replacements: "
     "GFCI, AFCI, tamper-resistant), 404 (switches), 110.14 (terminations)",
     "US Consumer Product Safety Commission, Repairing Aluminum Wiring",
     "OSHA 29 CFR 1910.333, Selection and Use of Work Practices (de-energizing and testing before work)"),
    skill="electrical_wiring",
))

register(Job(
    "recaulk_tub", "plumbing", "repair", "Recaulk a tub or shower",
    "Replacing the old caulk where a tub or shower meets the tile or wall: the old caulk and mildew removed, the "
    "joint cleaned and dried, the tub filled with water so the joint is at its widest, a bead of silicone tooled "
    "smooth, and the cure respected before use.",
    ("recaulk the tub", "caulk the tub", "recaulk the shower", "caulk the shower", "moldy caulk", "replace caulk"),
    ("hazmat", "injury"),
    "Recaulking needs no permit. " + _LOCAL,
    ("cuts from scrapers and razor blades", "cleaner and solvent fumes in a closed bathroom", "mold spores when "
     "scraping"),
    ("gloves", "safety glasses", "a dust mask while scraping mold"),
    ("a caulk remover tool or plastic scraper", "a razor-blade scraper", "a caulk gun", "painter's tape",
     "rags and a spray bottle"),
    ("100% silicone kitchen and bath sealant (mildew-resistant)", "caulk remover (if the old is stubborn)",
     "rubbing alcohol or mineral spirits for cleaning", "household cleaner for mildew"),
    (
        Phase("Plan before scraping", (
            Step("Check behind the old caulk for soft tile, loose grout or water damage.", "Caulk can't fix a leak "
                 "that's already in the wall.", ("Soft wall behind: that's a repair before caulk.",),
                 "The joint has no damage behind it."),
            Step("Plan a time the tub can stay unused for the caulk's full cure (commonly 24 hours).", "Water on "
                 "uncured silicone ruins the seal.", ()),
        )),
        Phase("Remove the old caulk", (
            Step("Cut and scrape out all the old caulk with the remover tool, then the razor scraper held flat on "
                 "tile.", "New silicone won't stick to old silicone.", ("Plastic on acrylic tubs: a razor "
                                                                        "scratches them.",)),
            Step("Kill any mildew in the joint with cleaner, rinse, and let it dry completely (a day, or a fan).",
                 "Caulk over mildew or moisture lets it come back.",
                 ("Black stain left in the joint: it shows through clear caulk.",)),
            Step("Wipe the joint with rubbing alcohol to remove soap film.", "Soap film is the most common reason "
                 "caulk peels.", (), "The joint is bare, clean and dry."),
            Step("Open a window and run the fan while you clean and caulk.", "Cleaner and sealant fumes build "
                 "up in a small room.", ("Never mix bleach with other cleaners.",)),
        )),
        Phase("Caulk", (
            Step("Fill the tub with water (it settles the tub so the joint opens to its widest), and tape both "
                 "sides of the joint.", "Caulked full, the joint won't stretch open when someone stands in it.",
                 ("Leave the water in until the caulk skins over.",)),
            Step("Cut the nozzle small at an angle and run one steady bead along the joint, pushing it in.",
                 "A pushed bead fills the joint; a pulled one sits on top.", ("Go slow and don't stop mid-run.",)),
            Step("Tool it smooth with a wet finger or tool in one pass, then pull the tape away at an angle while "
                 "it's wet.", "Tape pulled after it skins tears the edge.", ()),
            Step("Clean any smears right away with a damp rag.", "Cured silicone is hard to remove.",
                 ("Mineral spirits on a rag lifts a fresh smear.",),
                 "A smooth, continuous bead seals every edge."),
        )),
        Phase("Cure and check", (
            Step("Let it cure (commonly 24 hours) with the fan on, then drain the tub.", "Silicone cures from "
                 "moisture in the air; water on it before that washes it out.", ("Check the tube for its cure "
                                                                                 "time.",)),
            Step("Inspect the bead for gaps or pinholes and touch them up.", "One gap lets water behind the whole "
                 "bead.", (), "The bead is whole and cured."),
        )),
    ),
    ("Tile Council of North America, TCNA Handbook EJ171 (movement joints: sealant at changes of plane)",
     "The sealant maker's instructions (surface prep and cure time)",
     "This Old House, How to Recaulk a Bathtub"),
    skill="plumbing",
))

register(Job(
    "weatherstrip_door", "carpentry", "repair", "Weatherstrip an exterior door",
    "Stopping drafts around an exterior door: finding the leaks, replacing the jamb weatherstrip, adjusting or "
    "replacing the door sweep and threshold, adjusting the strike so the door seals, and checking with a draft test.",
    ("weatherstrip the door", "drafty door", "door draft", "door sweep", "weatherstripping", "seal the door"),
    ("injury",),
    "Weatherstripping needs no permit. " + _LOCAL,
    ("cuts from a utility knife and metal sweeps", "a heavy door taken off its hinges", "screwdriver slips"),
    ("safety glasses", "gloves"),
    ("tape measure", "utility knife", "hacksaw (for metal sweeps)", "drill/driver", "a putty knife", "an incense "
     "stick or a thin piece of paper for the draft test"),
    ("compression or kerf-in weatherstrip for the jambs", "a door sweep or bottom seal", "threshold insert if it's "
     "adjustable", "screws and a rubbing-alcohol wipe"),
    (
        Phase("Plan before buying", (
            Step("On a windy day, hold an incense stick around the closed door and note where the smoke moves (the "
                 "sides, the top, the bottom).", "The draft test shows exactly where to work.",
                 ("Close a paper in the door: if it slides out easily, it isn't sealing there.",),
                 "You know where the door leaks."),
            Step("Find what the door has now: a kerf-in weatherstrip (in a slot), adhesive foam, or a nailed-on "
                 "strip, and its sweep type, and buy the same kind.", "Kerf-in weatherstrip only fits its slot.",
                 ("Take a piece to the store.",)),
        )),
        Phase("Jambs", (
            Step("Pull out the old weatherstrip and clean the jamb (alcohol for adhesive kinds).", "New strip won't "
                 "seal against dirt or old adhesive.", ()),
            Step("Check the hinge screws are tight and the door isn't sagging before fitting new strip.", "A "
                 "sagging door leaves a gap no strip can close.", ("A long screw in the top hinge pulls it back.",)),
            Step("Cut the new strip to length and press it into the kerf (or stick or nail it), the head piece "
                 "first, then the sides, corners tight.", "Gaps at the corners leak.", ("Don't stretch it: it "
                                                                                        "shrinks back.",)),
            Step("Close the door: it should latch with light pressure and press the strip evenly.", "Too tight and "
                 "it won't latch; too loose and it leaks.", (), "The jamb strip is continuous and the door latches."),
        )),
        Phase("Bottom", (
            Step("Raise an adjustable threshold (its screws) until the closed door just touches it, or fit a new "
                 "insert.", "The threshold seal is where most door drafts come from.", ("A paper should drag when "
                                                                                         "pulled.",)),
            Step("Replace the door sweep, cut to the door's width, its seal just touching the threshold.", "A sweep "
                 "too low drags; too high leaks.", ("Long sweeps wear the floor covering.",)),
            Step("Seal the threshold to the sill underneath with sealant at its ends and screws.", "Air and water "
                 "come in under a loose threshold.", ("Leave its drainage holes open.",)),
            Step("Adjust the strike plate in or out if the door rattles or won't pull tight to the strip.",
                 "The strike sets how hard the door presses the seal.", (),
                 "The bottom seals and the door pulls tight."),
        )),
        Phase("Draft test and check", (
            Step("Repeat the incense test all around the door on a windy day.", "The same test proves the fix.",
                 ("Any smoke movement: adjust that spot.",)),
            Step("Open and close it several times and check it latches easily and the strips stay put.",
                 "A seal that makes the door hard to close gets pulled off.", (),
                 "No drafts show and the door closes easily."),
        )),
    ),
    ("US Department of Energy, Energy Saver: Weatherstripping",
     "ENERGY STAR, A Do-It-Yourself Guide to Sealing and Insulating with ENERGY STAR",
     "The door or weatherstrip maker's instructions"),
    skill="carpentry",
))


# ------------------------------------------------------------------ the fourth tier (2026-11-09): the plans shelf's builds

register(Job(
    "raised_bed", "carpentry", "build", "Build a raised garden bed",
    "A wooden raised bed for vegetables: placed in sun, built square from untreated rot-resistant boards (or lumber "
    "rated safe for food gardens) with corner posts, lined at the bottom against burrowing animals, filled with a soil "
    "mix, and watered in. Its boards and cuts come from the raised-bed plan.",
    ("raised bed", "raised garden bed", "build a raised bed", "garden bed", "planter box"),
    ("utilities", "injury"),
    "A raised bed needs no permit almost anywhere, though an HOA may have rules on the front yard. " + _LOCAL,
    ("saw injuries", "splinters", "back strain moving soil", "digging into buried lines when setting posts"),
    ("safety glasses", "work gloves"),
    ("circular saw or handsaw", "drill/driver", "tape measure and a framing square", "level", "shovel and a rake"),
    ("cedar, cypress or other rot-resistant boards (untreated)", "4x4 corner posts", "exterior screws",
     "hardware cloth for the bottom (where gophers or moles live)", "soil mix: topsoil, compost and an aerating mix"),
    (
        Phase("Plan before you build", (
            Step("Pick a spot with 6 to 8 hours of sun, near water, on fairly level ground, and size the bed no "
                 "wider than 4 ft so you can reach the middle from each side.", "A bed you can't reach across gets "
                 "walked on and packed down.", ("Avoid low spots that hold water.",),
                 "The spot and size are decided."),
            Step("Call 811 before driving posts or digging deeper than the topsoil.", "Even garden posts go where "
                 "lines can run.", (), "Any lines are marked."),
            Step("Get the boards and cuts from the raised-bed plan for your size and height.", "The plan packs the "
                 "cuts into whole boards with the least waste.", ("Untreated or food-safe lumber only.",)),
        )),
        Phase("Build the frame", (
            Step("Cut the side and end boards and the corner posts to length.", "Square cuts make tight corners.",
                 ("Check each cut with the square.",)),
            Step("Screw the boards to the corner posts, one course at a time, checking each corner square.",
                 "Posts inside the corners hold the boards when the soil pushes out.", ()),
            Step("Check the frame's diagonals; adjust until they match.", "A square bed sits right and looks right.",
                 (), "The frame is square and solid."),
        )),
        Phase("Set and fill", (
            Step("Level the ground where it sits, set the frame, and check it's level both ways (shim with soil).",
                 "A tilted bed drains to one end.", ("Dig the posts in an inch or two if the ground is soft.",)),
            Step("Staple hardware cloth across the bottom if burrowing animals are around.", "Gophers come up "
                 "through the bottom otherwise.", ()),
            Step("Fill with the soil mix in layers, watering each layer, to an inch below the top.", "Watering as you "
                 "fill settles it so it doesn't sink later.", ("It settles: top it up after a week.",),
                 "The bed is filled and settled."),
        )),
        Phase("Plant and check", (
            Step("Water it well and let it settle a day or two before planting.", "Planting in dry, unsettled soil "
                 "stresses seedlings.", ()),
            Step("Plant, then mulch the surface.", "Mulch keeps the moisture in and the weeds down.",
                 ("Keep mulch off the seedlings' stems.",)),
            Step("Check after the first heavy rain that it drains and nothing has shifted.", "Standing water means "
                 "the soil mix needs more coarse material.", (), "It drains and stands square."),
        )),
    ),
    ("University of Minnesota Extension, Raised Bed Gardens",
     "Oregon State University Extension, Building a Raised Bed Garden (EM 9178)",
     "MIA's raised-bed plan and calculator (core/build_calcs.py raised_bed)"),
    plan="raised-bed",
    skill="carpentry",
))

register(Job(
    "gable_shed", "carpentry", "build", "Build a gable storage shed",
    "A wood-framed storage shed with a gable roof on a gravel pad or skid foundation: the permit and setbacks, a "
    "level base, the floor frame, walls with a door opening, rafters, sheathing, roofing and siding. The lumber comes "
    "from the gable-shed plan; a slab foundation is the workshop job.",
    ("shed", "storage shed", "gable shed", "build a shed", "garden shed", "backyard shed"),
    ("utilities", "structural", "fall", "weather", "injury"),
    "Sheds over a size set locally (often 120 or 200 sq ft) need a permit, and every shed must meet setbacks from "
    "property lines. " + _LOCAL,
    ("raising walls and rafters", "falls from the roof and ladders", "saw and nailer injuries", "digging for the "
     "base near buried lines"),
    ("safety glasses", "hearing protection", "work gloves", "fall protection on the roof"),
    ("circular saw", "framing nailer or a hammer", "framing square and speed square", "level and a string line",
     "drill/driver", "ladders"),
    ("compactable gravel and landscape fabric (or treated skids)", "treated floor framing and 3/4 in floor sheathing",
     "wall studs, plates and a door header", "rafters, ridge board and roof sheathing", "underlayment, drip edge and "
     "shingles (or metal roofing)", "siding and trim", "the door and its hardware"),
    (
        Phase("Plan and permit before you build", (
            Step("Check the size against your area's permit limit, the setbacks from property lines, and any HOA "
                 "rules; get the permit if needed.", "A shed over a line or a limit can be ordered moved.",
                 ("Measure setbacks from the true property line.",),
                 "You know the size allowed, the setbacks and the permit."),
            Step("Call 811 before digging the base.", "The base sits where yard lines can run.", (),
                 "Every line is marked."),
            Step("Get the lumber and cuts from the gable-shed plan for your size.", "The plan keeps what each board "
                 "is for, so nothing is short.", ()),
        )),
        Phase("Base and floor", (
            Step("Build a level, compacted gravel pad (or set skids level on blocks) a little larger than the shed.",
                 "A level, drained base keeps the floor from rotting and the door from binding.",
                 ("Check level both ways and the diagonals.",)),
            Step("Lay landscape fabric under the gravel and run the pad 6 in past the walls.", "Fabric keeps the "
                 "gravel clean and weeds out; the extra width sheds roof water.", ("Slope the ground around it away.",)),
            Step("Frame the floor with treated joists at 16 in, square it, and sheathe it.", "The floor is the "
                 "square everything else is built on.", (), "The floor is level and square."),
        )),
        Phase("Walls and roof", (
            Step("Frame each wall flat on the floor (the door wall with its header), stand it, plumb and brace it.",
                 "Framing flat is faster and squarer than framing in place.", ("Brace each wall as it goes up.",)),
            Step("Sheathe the walls (or put up panel siding) square to the floor, nailed to the schedule.", "Sheathing "
                 "is what keeps the walls from racking.", ("Start square at a corner: every panel after follows it.",)),
            Step("Add the top plates lapped at the corners, then cut a pattern rafter and test it before cutting the "
                 "rest.", "A tested rafter fits every pair.", ()),
            Step("Set the ridge and rafters in pairs, with ties at the plate, and sheathe the roof.", "Ties stop "
                 "the rafters pushing the walls out.", ("Never work on the roof alone.",),
                 "The frame is square, braced and the roof sheathed."),
        )),
        Phase("Close in and check", (
            Step("Drip edge, underlayment and roofing, then siding and trim, then hang the door.", "Roof first "
                 "keeps the rest dry.", ("Flash over the door head.",)),
            Step("Walk around it for gaps, exposed nails and water paths; get the final inspection if your permit "
                 "has one.", "A shed lasts as long as it stays dry.", (), "It's closed in and any inspection passed."),
        )),
    ),
    (_IRC + ": R105.2 (work exempt from permit: accessory structures), R602 (wall framing), R802 (roof framing)",
     "Fine Homebuilding, Building a Storage Shed",
     "MIA's gable-shed plan and calculator (core/build_calcs.py shed)"),
    plan="gable-shed",
    skill="carpentry",
))

register(Job(
    "compost_bin", "carpentry", "build", "Build a three-bay compost bin",
    "A wooden compost bin of side-by-side bays (fresh, working and finished): placed on bare ground, framed with "
    "corner posts, slatted with air gaps, front slats that lift out, and started with the right mix of greens and "
    "browns. The lumber comes from the compost-bin plan.",
    ("compost bin", "build a compost bin", "compost bays", "three bay compost", "compost pile"),
    ("utilities", "injury"),
    "A compost bin needs no permit in most places, though some towns set how far it sits from a property line. " +
    _LOCAL,
    ("saw injuries", "splinters", "back strain turning compost", "digging posts near buried lines"),
    ("safety glasses", "work gloves"),
    ("circular saw", "drill/driver", "post-hole digger or a spade", "level and a tape measure"),
    ("untreated cedar or other rot-resistant boards and 4x4 posts", "1x2 guides for the lift-out slats",
     "exterior screws", "hardware cloth (optional, against rodents)"),
    (
        Phase("Plan before you build", (
            Step("Pick a level, well-drained spot, partly shaded, near the garden and a hose, at the distance your "
                 "town asks from the property line.", "Too much sun dries the pile; too far away and it isn't "
                 "used.", ("Keep it away from wells and streams.",), "The spot is chosen."),
            Step("Call 811 before setting posts.", "Posts go where lines can run.", (), "Any lines are marked."),
            Step("Get the boards and cuts from the compost-bin plan for your number of bays.", "The plan packs the "
                 "slats into whole boards.", ()),
        )),
        Phase("Build the bays", (
            Step("Set the corner posts plumb and in line, about a foot into the ground or on blocks.",
                 "Plumb posts keep the slats straight.", ("Check the spacing matches the slat lengths.",)),
            Step("Staple hardware cloth over the ground inside each bay if rats or mice are a problem.", "It "
                 "keeps rodents out while worms still come up.", ("Overlap it up the walls a few inches.",)),
            Step("Screw the back and divider slats on with a 1 in gap between them.", "The gaps let air in: compost "
                 "needs oxygen to work and not smell.", ("Use a scrap of 1x as a spacer for even gaps.",)),
            Step("Fit the front guides so the front slats lift out.", "Lift-out fronts let you turn and empty each "
                 "bay.", ("Leave the guides a little loose so slats slide when wet.",), "The bays are built and the fronts lift out."),
        )),
        Phase("Start the compost", (
            Step("Start the first bay with a layer of coarse browns (twigs, straw) on the bare ground.", "Contact "
                 "with soil lets worms and microbes in.", ()),
            Step("Add greens (kitchen scraps, grass) and browns (leaves, cardboard) at about 1 part greens to 2 or 3 "
                 "browns, moist as a wrung sponge.", "The right mix heats up; too many greens smell, too many browns "
                 "sit.", ("No meat, dairy or pet waste.",)),
            Step("Turn it into the next bay every week or two, and move finished compost to the third.", "Turning "
                 "adds air and finishes it faster.", ("A hot center (warm to the hand) means it's working.",),
                 "The first bay is going and the turning is planned."),
        )),
        Phase("Check the bins", (
            Step("Check after rain that water drains and the slats are tight.", "Waterlogged compost goes "
                 "anaerobic and smells.", ()),
            Step("Use finished compost when it's dark, crumbly and smells like soil.", "Unfinished compost can rob "
                 "plants of nitrogen.", (), "The bins drain, stay tight and the compost cycles."),
        )),
    ),
    ("Cornell Waste Management Institute, Composting at Home",
     "US EPA, Composting At Home",
     "MIA's compost-bin plan and calculator (core/build_calcs.py compost_bin)"),
    plan="compost-bin",
    skill="carpentry",
))

register(Job(
    "cold_frame", "carpentry", "build", "Build a cold frame",
    "A cold frame for starting and hardening off plants: a box higher at the back so its lid faces the sun, set on "
    "level ground, with a hinged polycarbonate lid, a prop, and the venting that keeps it from cooking plants. The "
    "lumber comes from the cold-frame plan.",
    ("cold frame", "build a cold frame", "coldframe", "hot box", "seedling frame"),
    ("injury",),
    "A cold frame needs no permit. " + _LOCAL,
    ("saw injuries", "splinters", "cuts from polycarbonate edges", "a lid slamming on fingers"),
    ("safety glasses", "work gloves"),
    ("circular saw", "drill/driver", "tape measure and a square", "level", "a fine-tooth blade for polycarbonate"),
    ("cedar boards (untreated) and corner posts", "a 2x2 lid frame", "twinwall polycarbonate", "hinges, a lid prop "
     "or automatic vent opener", "polycarbonate screws with washers"),
    (
        Phase("Plan before you build", (
            Step("Pick a spot facing south (north in the southern hemisphere), sheltered from wind, on level, "
                 "well-drained ground.", "The low side to the sun catches the most winter light.",
                 ("Avoid the shadow of the house or a fence at midday in winter.",), "The spot is chosen."),
            Step("Get the boards and cuts from the cold-frame plan for your size.", "The plan gives the back and "
                 "front heights and the sloped sides.", ()),
            Step("Buy UV-protected polycarbonate and note which side faces out.", "The unprotected side yellows "
                 "and goes brittle in sun.", ("The protected side is marked on the film.",)),
        )),
        Phase("Build the box", (
            Step("Cut the back, front and sloped side boards; screw them to the corner posts.", "Posts inside the "
                 "corners hold the box together.", ("Cut one side board, test it, then copy it.",)),
            Step("Check the box is square and sits level on the ground.", "A racked box won't seal under the lid.",
                 ("Bank soil against the bottom edge to stop drafts.",), "The box is square and level."),
        )),
        Phase("Lid and venting", (
            Step("Build the 2x2 lid frame to overlap the box slightly, and screw the polycarbonate to it with "
                 "washered screws, flutes running down the slope.", "Flutes down let condensation drain.",
                 ("Pre-drill polycarbonate: it cracks if forced.",)),
            Step("Hinge the lid along the back and fit a prop or an automatic vent opener.", "Venting on sunny days "
                 "is what keeps plants from overheating.", ()),
            Step("Stick weatherstrip along the box's top edges where the lid closes.", "A sealed lid holds the "
                 "night's warmth.", ("Leave it off the hinge side so the lid closes.",)),
            Step("On a sunny day, check the inside temperature with the lid shut and open.", "A shut frame can pass "
                 "100 F in sun even in cold weather.", ("Vent above about 75 F.",), "The lid seals, props and vents."),
        )),
        Phase("Use it and check", (
            Step("Add a few inches of compost or set trays inside, and harden off seedlings by opening the lid more "
                 "each day.", "Gradual exposure toughens seedlings before transplanting.", ()),
            Step("Keep a thermometer inside where you can read it without opening the lid.", "You vent and cover by "
                 "the numbers, not guesses.", ("A min-max thermometer shows the night's low.",)),
            Step("Check on frosty nights that it holds above freezing (cover it with a blanket if not) and on sunny "
                 "days that it's vented.", "A cold frame's job is the right temperature at both ends.", (),
                 "It holds above freezing and vents on sunny days."),
        )),
    ),
    ("Eliot Coleman, Four-Season Harvest (Chelsea Green, 1999)",
     "University of Maryland Extension, Cold Frames and Hot Beds",
     "MIA's cold-frame plan and calculator (core/build_calcs.py cold_frame)"),
    plan="cold-frame",
    skill="carpentry",
))

register(Job(
    "lean_to", "carpentry", "build", "Build a lean-to shelter",
    "A freestanding lean-to (a woodshed, a carport, a run-in for animals): posts set in the ground or on piers, a high "
    "and a low beam, rafters sloping one way, metal roofing, and bracing so it stands in wind. Attaching it to a "
    "building needs a ledger and flashing like a deck. The lumber comes from the lean-to plan.",
    ("lean to", "lean-to", "woodshed", "run-in shed", "carport", "open shelter"),
    ("utilities", "structural", "fall", "weather", "injury"),
    "Open shelters often need a permit above a size set locally, and must meet setbacks. " + _LOCAL,
    ("posts and beams falling while being set", "falls from ladders while roofing", "digging into buried lines",
     "metal roofing edges"),
    ("safety glasses", "work gloves (cut-resistant for metal)", "hearing protection"),
    ("post-hole digger", "circular saw", "drill/driver and an impact driver", "level, string line and a framing "
     "square", "ladders"),
    ("treated 4x4 or 6x6 posts (ground contact)", "concrete or gravel for the posts", "beams and rafters (sizes from "
     "the plan)", "hurricane ties and carriage bolts", "metal roofing, closures and screws", "diagonal braces"),
    (
        Phase("Plan and permit before you dig", (
            Step("Check the size and height against your area's permit rules and setbacks.", "A shelter over a "
                 "limit or a line has to come down.", ("Ask about snow load for the roof.",),
                 "You know what's allowed and have any permit."),
            Step("Call 811 and wait for the marks.", "Post holes go where lines can run.", (), "Every line is marked."),
            Step("Get the lumber and cuts from the lean-to plan; set the slope at least 3 in per foot for metal.",
                 "Too flat a roof leaks at the laps and holds snow.", ()),
        )),
        Phase("Posts and beams", (
            Step("Lay out the posts square with string lines and diagonals.", "Square posts make a square roof.",
                 ("Measure the diagonals before digging.",)),
            Step("Dig below the frost line, set the posts plumb and braced, and set them in concrete or tamped "
                 "gravel.", "Posts above the frost line heave.", ("Brace both ways before letting go.",)),
            Step("Mark the high and low beam heights from a level line and bolt the beams to the posts.",
                 "The difference in height is the roof's slope.",
                 ("Two carriage bolts a joint, not nails alone.",), "Posts are plumb and both beams are bolted."),
        )),
        Phase("Roof and bracing", (
            Step("Set rafters across the beams at the plan's spacing, each fastened with a hurricane tie.", "Wind "
                 "lifts an open roof; ties hold it down.", ("A tie at every rafter, every nail hole filled.",)),
            Step("Add diagonal braces from the posts to the beams.", "Bracing is what keeps an open shelter from "
                 "racking over.", ()),
            Step("Fit the fascia or a drip board along the low edge.", "Water off a metal roof needs a clean edge to "
                 "drip from, away from the posts.", ("Keep the low edge clear of where you walk.",)),
            Step("Roof it with metal panels on closures, lapped away from the wind, screwed to the maker's "
                 "pattern.", "Laps facing the wind let rain blow in.", ("Never stand on the panels between "
                                                                       "rafters.",),
                 "The roof is on, braced and tied down."),
        )),
        Phase("Check the shelter", (
            Step("Push on a corner and look for any sway; add bracing where it moves.", "Sway now is collapse "
                 "later.", ()),
            Step("Watch it through the first storm for leaks and movement, and get the final inspection if "
                 "required.", "The first storm tests it.", (), "It stands firm and dry."),
        )),
    ),
    (_IRC + ": R301.2 (wind and snow loads), R802.11 (roof uplift resistance)",
     "Simpson Strong-Tie, Deck and Outdoor Structure connectors guide",
     "MIA's lean-to plan and calculator (core/build_calcs.py lean_to)"),
    plan="lean-to",
    skill="carpentry",
))

register(Job(
    "garage_shelving", "carpentry", "build", "Build garage shelving",
    "Freestanding (or wall-anchored) 2x4 garage shelving with plywood shelves: sized to the space and the load, the "
    "frame built square, shelves supported every few feet, anchored to the wall so it can't tip, and loaded heaviest "
    "at the bottom. The lumber comes from the garage-shelving plan.",
    ("garage shelving", "garage shelves", "build shelves", "storage shelves", "shop shelving"),
    ("injury",),
    "Shelving needs no permit. " + _LOCAL,
    ("a loaded shelf tipping over", "saw injuries", "lifting plywood sheets"),
    ("safety glasses", "hearing protection", "work gloves"),
    ("circular saw and a straightedge guide", "drill/driver", "tape measure and a framing square", "level",
     "stud finder"),
    ("2x4 uprights and rails", "3/4 in plywood or OSB for the shelves", "construction screws", "wall anchors or "
     "lag screws into studs"),
    (
        Phase("Plan before cutting", (
            Step("Measure the space (leave room for a car door and the garage door's travel) and decide the shelf "
                 "count and depth.", "Shelves that block a door get bumped and damaged.",
                 ("Keep the top shelf reachable from a step stool.",), "The size and shelf count are set."),
            Step("Get the cuts from the garage-shelving plan for your size.", "The plan packs the 2x4s and plywood "
                 "into whole pieces.", ()),
            Step("Find the studs where it will stand.", "Anchoring to studs is what stops a full shelf tipping.",
                 ()),
        )),
        Phase("Build the frame", (
            Step("Cut the uprights and rails; screw the rails to the uprights at each shelf height to make two "
                 "side frames.", "Matching frames give level shelves.", ("Mark both frames together.",)),
            Step("Stand the frames, join them with front and back rails, and check square with the diagonals.",
                 "A racked frame wobbles under load.", ()),
            Step("Add a middle support under each shelf if the span is over about 4 ft.", "Plywood sags over long "
                 "spans under heavy loads.", ("3/4 in plywood spans about 32 in under heavy loads.",),
                 "The frame is square with supports where needed."),
            Step("Seal or paint the plywood shelves if the garage is damp.", "Bare plywood swells and delaminates "
                 "in a damp garage.", ("Let it dry before loading.",)),
        )),
        Phase("Shelves and anchoring", (
            Step("Cut the plywood shelves and screw them down to the rails.", "Screwed shelves stiffen the whole "
                 "frame.", ("Notch around the uprights for a snug fit.",)),
            Step("Anchor the top rail to the wall studs with lag screws or brackets.", "A full shelf can tip "
                 "forward; anchoring stops it.", ("Into studs, not drywall alone.",)),
            Step("Check it's level and doesn't rock; shim the feet if the floor slopes (garage floors slope to the "
                 "door).", "A rocking shelf works loose.", (), "It's level, solid and anchored."),
        )),
        Phase("Load and check", (
            Step("Load heaviest things on the bottom shelves.", "A low center of weight keeps it stable.",
                 ("Keep paint, chemicals and anything heavy off the top shelf.",)),
            Step("Check after a week for sag or loosened screws.", "Wood settles under a new load.", (),
                 "It holds its load without sag."),
        )),
    ),
    ("American Wood Council, Span Tables and wood properties (plywood shelf span guidance via APA)",
     "APA, Engineered Wood Construction Guide (Form E30): shelving spans",
     "MIA's garage-shelving plan and calculator (core/build_calcs.py shelving)"),
    plan="garage-shelving",
    skill="carpentry",
))

register(Job(
    "workbench", "carpentry", "build", "Build a shop workbench",
    "A sturdy shop workbench: a doubled top on a 2x4 or 4x4 frame, at a height that fits the person, square and "
    "braced so it doesn't rack, with a lower shelf, and leveled where it stands. The lumber comes from the workbench "
    "plan.",
    ("workbench", "work bench", "shop bench", "build a workbench", "garage workbench"),
    ("injury",),
    "A workbench needs no permit. " + _LOCAL,
    ("saw injuries", "lifting the top", "a bench racking under load"),
    ("safety glasses", "hearing protection", "work gloves"),
    ("circular saw", "drill/driver", "framing square and tape", "level", "clamps"),
    ("2x4 or 4x4 legs and rails", "two layers of 3/4 in plywood (or a solid top)", "a hardboard wear surface "
     "(optional)", "construction screws and wood glue"),
    (
        Phase("Plan before cutting", (
            Step("Set the height: about wrist height with your arms at your sides (commonly 34 to 38 in), and the "
                 "size for your space.", "A bench at the wrong height strains your back.",
                 ("Higher for fine work, lower for planing.",), "The height and size are set."),
            Step("Get the cuts from the workbench plan.", "The plan packs the lumber into whole pieces.", ()),
        )),
        Phase("Build the base", (
            Step("Cut the legs and rails; build two end frames with glue and screws.", "Glued joints don't loosen.",
                 ("Square each end frame before the glue sets.",)),
            Step("Join the end frames with long rails front and back, top and bottom.", "The rails tie the legs "
                 "together.", ("Check the end frames stay square as you fasten them.",)),
            Step("Check the base for square with the diagonals and add diagonal braces or a back panel.",
                 "Bracing stops it racking when you push a saw or plane.", ("Push the corner: no sway.",),
                 "The base is square and braced."),
            Step("Fit the lower shelf on the bottom rails.", "The shelf stiffens the base and holds tools.",
                 ("Leave room to sweep under it.",)),
        )),
        Phase("The top", (
            Step("Glue and screw two layers of plywood for the top, the seams offset, overhanging enough for clamps "
                 "(2 to 4 in).", "A double top is stiff and heavy; an overhang lets you clamp work.",
                 ("Screws from below so the top stays clean.",)),
            Step("Fasten the top to the base and add a hardboard wear surface if you want one.", "A wear surface "
                 "can be replaced when it's worn.", ()),
            Step("Add a vise at the left front corner (right for a left-hander), bolted through the top.", "A vise "
                 "holds work so both hands are free.", ("Set its jaws flush with the top's edge.",)),
            Step("Ease the edges with a sander or router.", "Sharp edges catch and splinter.", (),
                 "The top is fastened, flat and eased."),
        )),
        Phase("Level and check", (
            Step("Set it where it lives and level it with shims or adjustable feet.", "A rocking bench ruins "
                 "accurate work.", ("Garage floors slope: check both ways.",)),
            Step("Clamp a piece and work it; check it doesn't move or flex.", "Using it is the only real test of a bench.", (),
                 "It's level and solid under work."),
        )),
    ),
    ("Christopher Schwarz, Workbenches: From Design and Theory to Construction and Use (Popular Woodworking, 2007)",
     "Fine Woodworking, Building a Basic Workbench",
     "MIA's workbench plan (core/plan_library.py)"),
    plan="workbench",
    skill="carpentry",
))

register(Job(
    "firewood_rack", "carpentry", "build", "Build a firewood rack",
    "A firewood rack that keeps wood off the ground and drying: 2x4 base rails on blocks, braced end uprights, sized "
    "to hold what you burn (a full cord is 128 cu ft), placed in sun and wind, and covered on top only. The lumber "
    "comes from the firewood-rack plan.",
    ("firewood rack", "wood rack", "log rack", "firewood storage", "stack firewood"),
    ("injury",),
    "A firewood rack needs no permit, but keep it away from the house: many fire codes ask for distance, and wood "
    "against a wall invites termites. " + _LOCAL,
    ("a stack falling", "splinters", "saw injuries", "insects and rodents in old wood"),
    ("safety glasses", "work gloves"),
    ("circular saw", "drill/driver", "level", "tape measure"),
    ("treated 2x4s for the base (ground contact)", "2x4 uprights", "concrete blocks or pavers", "exterior screws",
     "a top cover (a tarp or a small roof) for the stack"),
    (
        Phase("Plan before you build", (
            Step("Pick a spot in sun and wind, at least 20 to 30 ft from the house, on level, drained ground.",
                 "Sun and wind dry wood; distance keeps insects and fire risk away from the house.",
                 ("Check your area's fire rules for distance.",), "The spot is chosen."),
            Step("Size it from how much you burn: a full cord is 4 x 4 x 8 ft (128 cu ft); the plan works out how "
                 "much yours holds.", "Knowing the volume tells you how much to buy or cut.", ()),
            Step("Get the cuts from the firewood-rack plan.", "The plan gives the rails and uprights for your size.",
                 ()),
        )),
        Phase("Build the rack", (
            Step("Set the blocks level and lay the treated base rails on them.", "Off the ground, wood doesn't "
                 "rot or wick water.", ("Level along the length: a sloped rack tips its stack.",)),
            Step("Fasten the end uprights and brace them across, so the ends hold the stack.", "Unbraced ends push "
                 "out under the stack's weight.", ("Diagonal braces both ends.",)),
            Step("Check the rack is square and solid before loading.", "A rack that racks empty will fall full.",
                 (), "The rack is level, square and braced."),
        )),
        Phase("Stack and cover", (
            Step("Stack the wood bark side up, split ends facing out, with gaps for air.", "Air through the stack "
                 "dries it.", ("Don't stack higher than about 4 ft.",)),
            Step("Cover the top only, leaving the sides open.", "A full tarp traps moisture and the wood never "
                 "dries.", ()),
            Step("Keep the stack's back a few inches from any fence or wall.", "Air behind it dries the wood and "
                 "keeps insects from bridging over.", ("Never against the house.",)),
            Step("Rotate: burn the oldest wood first and stack new wood behind it.", "Wood needs 6 to 12 months to "
                 "season.", ("Seasoned wood is gray, cracked at the ends, and sounds hollow knocked together.",),
                 "The stack is covered on top and rotating."),
        )),
        Phase("Check the stack", (
            Step("Check after storms that the stack stands straight and the cover holds.", "A leaning stack falls on "
                 "someone.", ()),
            Step("Before burning, check the wood is seasoned (a moisture meter under 20%).", "Wet wood smokes and "
                 "builds creosote in the chimney.", (), "The wood is dry and the stack stands."),
        )),
    ),
    ("US EPA, Burn Wise: Wood-burning best practices (seasoned wood under 20% moisture)",
     "National Fire Protection Association, NFPA 211 (chimneys, fireplaces and solid fuel appliances)",
     "MIA's firewood-rack plan and calculator (core/build_calcs.py firewood_rack)"),
    plan="firewood-rack",
    skill="carpentry",
))


# ------------------------------------------------------------------ the fifth tier (2026-11-09): the land and its water

register(Job(
    "french_drain", "exterior", "build", "Dig a French drain",
    "A French drain to carry away water that pools in the yard or against a building: the water's path and an discharge point "
    "found first, 811, a trench sloped to daylight or a dry well, fabric, washed stone and a perforated pipe holes "
    "down, then backfill. Water against a basement wall from inside is a waterproofing job.",
    ("french drain", "yard drainage", "standing water in the yard", "drain the yard", "water pooling",
     "trench drain"),
    ("utilities", "weather", "injury"),
    "A yard drain usually needs no permit, but you may not send water onto a neighbor's land or into a sewer, and some "
    "places regulate where it discharges. " + _LOCAL,
    ("digging into buried lines", "a trench wall caving in", "back strain moving stone", "a rented trencher's "
     "kickback"),
    ("work gloves", "safety glasses", "steel-toe boots"),
    ("trenching shovel or a rented trencher", "a level and a string line (or a laser)", "a wheelbarrow", "tape "
     "measure", "a hand tamper"),
    ("4 in perforated drain pipe (with a sock in clay soil)", "washed drainage stone (3/4 in)", "non-woven landscape "
     "fabric", "a pop-up emitter or a dry well for the discharge point", "fittings and couplers"),
    (
        Phase("Plan before you dig", (
            Step("Watch where the water goes in a heavy rain and mark where it pools and where it can be sent "
                 "(lower ground on your land, a ditch, a dry well).", "A drain needs somewhere lower to go.",
                 ("Never toward a neighbor or your own house.",), "You know the route and the discharge point."),
            Step("Call 811 and wait for the marks.", "Yard trenches cross lines more than any other job.", (),
                 "Every line is marked."),
            Step("Plan a slope of at least 1 in for every 8 ft (1%) all the way to the discharge point.", "Water only "
                 "drains downhill; a flat drain fills and sits.", ()),
        )),
        Phase("Trench", (
            Step("Dig the trench about 6 in wide and 18 to 24 in deep, hand-digging near any mark.", "Deep enough "
                 "to catch the water and cover the pipe.", ("Slope the trench walls in loose soil.",)),
            Step("Check the slope with a string line or a level as you go, and shave the bottom to it.", "One "
                 "low spot becomes a pond inside the drain.", ("Fix any dip before the stone goes in.",)),
            Step("Pile the dug soil on a tarp away from the trench edge.", "Spoil at the edge falls back in and "
                 "loads the trench wall.", ("Keep it at least 2 ft back.",)),
            Step("Line the trench with fabric, leaving enough to fold over the top.", "Fabric keeps soil from "
                 "clogging the stone.", ("Overlap fabric seams a foot.",), "The trench is sloped all the way and lined."),
        )),
        Phase("Pipe and stone", (
            Step("Lay 2 in of stone, then the pipe with its holes facing down.", "Holes down let water rise into the "
                 "pipe and carry it off.", ("Holes up is the most common mistake.",)),
            Step("Run the pipe to the discharge point (a pop-up emitter or a dry well), joints coupled.", "The discharge point is "
                 "where the water leaves your problem.", ()),
            Step("Cover the pipe with stone to a few inches below the surface, fold the fabric over, and backfill "
                 "with soil or more stone.", "The fabric wrap keeps it clear for years.",
                 ("Don't drive over it until it settles.",),
                 "The pipe is bedded and wrapped, the trench backfilled."),
        )),
        Phase("Test and check", (
            Step("Run a hose into the high end and watch it come out at the discharge point.", "The hose test proves the "
                 "slope.", ("Water that never shows up means a low spot or a blocked discharge point.",)),
            Step("Check the yard after the next heavy rain.", "Rain is the real test.", (),
                 "The water drains away to the discharge point."),
        )),
    ),
    ("US EPA, Soak Up the Rain: managing stormwater at home",
     "Penn State Extension, Managing Stormwater on Your Property",
     "American Society of Home Inspectors (ASHI), lot drainage guidance"),
    skill="carpentry",
))

register(Job(
    "gravel_driveway", "exterior", "build", "Build a gravel driveway or path",
    "A gravel driveway or path that doesn't rut or wash out: the route and its drainage, 811, the topsoil stripped, "
    "fabric over the subgrade, a compacted base of crushed stone, a crowned top layer, and edges that hold it.",
    ("gravel driveway", "gravel path", "build a driveway", "gravel road", "driveway gravel"),
    ("utilities", "weather", "injury"),
    "A new driveway often needs a permit for its connection to the road (the curb cut or culvert), and some places "
    "limit how much ground you cover. " + _LOCAL,
    ("heavy equipment (a skid steer, a dump truck backing)", "digging into buried lines", "lifting and spreading "
     "stone", "a plate compactor's vibration"),
    ("work gloves", "safety glasses", "hearing protection", "steel-toe boots"),
    ("a skid steer or tractor with a box blade (rented), or shovels and rakes", "a plate compactor", "string line "
     "and stakes", "a level"),
    ("non-woven geotextile fabric", "crushed stone for the base (commonly 3 in minus)", "a top layer of crushed "
     "stone with fines (commonly 3/4 in minus)", "edging (timbers or steel) for a path", "a culvert if a ditch "
     "crosses"),
    (
        Phase("Plan and permit before you dig", (
            Step("Lay out the route following the ground, avoiding low spots, and check the road connection rules.",
                 "A driveway in a low spot becomes a creek.", ("Ask the road authority about a culvert.",),
                 "The route and any permit are settled."),
            Step("Call 811 and wait for the marks.", "Driveways cross the lines that come in from the road.", (),
                 "Every line is marked."),
            Step("Work out the stone: length x width x depth for each layer, in cubic yards (about 1.4 tons a "
                 "yard).", "Short loads leave thin spots that rut.", ()),
        )),
        Phase("Prepare the ground", (
            Step("Strip the topsoil and roots down to firm subgrade.", "Topsoil under gravel turns to mud.",
                 ("Soft spots: dig out and fill with base stone.",)),
            Step("Shape the subgrade with a crown or a cross slope so water runs off, and compact it.", "Water "
                 "that stands under a driveway ruins it.", ("A crown of about 1/2 in a foot of width.",)),
            Step("Lay the geotextile fabric, overlapping the seams.", "Fabric keeps the stone from sinking into the "
                 "soil.", (), "The subgrade is shaped, compacted and covered."),
            Step("Set a culvert where the driveway crosses a ditch, sized as the road authority says, with a foot of "
                 "cover.", "A ditch with no culvert floods the driveway and the road.", ("Too small a culvert washes out.",)),
        )),
        Phase("Base and top", (
            Step("Spread the base stone 4 to 6 in deep and compact it in lifts.", "A compacted base carries the "
                 "weight.", ("Lifts no thicker than the compactor can handle.",)),
            Step("Spread the top stone 2 to 4 in deep, crowned, and compact it.", "The fines in the top lock "
                 "together under the compactor.", ("Wet it lightly before compacting.",)),
            Step("Edge a path with timbers or steel; let a driveway's shoulders slope off.", "Edges stop the stone "
                 "spreading.", ("Stake the edging every few feet.",), "Both layers are down, crowned and compacted."),
        )),
        Phase("Check after rain", (
            Step("Walk or drive it after the first heavy rain and look for puddles and washouts.", "Rain shows "
                 "where water collects.", ("Fill and compact any low spot.",)),
            Step("Plan a top-up and regrade every year or two.", "Gravel always moves; a little upkeep saves a "
                 "rebuild.", (), "It sheds water without ruts."),
        )),
    ),
    ("Penn State Center for Dirt and Gravel Roads, Driving Surface Aggregate guidance",
     "US Department of Agriculture Forest Service, Gravel Roads Construction and Maintenance Guide (2015)",
     "The local road authority's driveway and culvert standards"),
    skill="carpentry",
))

register(Job(
    "rain_barrel", "plumbing", "install", "Set up a rain barrel",
    "A rain barrel on a downspout: the rules where you live, a food-grade barrel, a firm and level raised stand, a "
    "diverter or a cut downspout, a screen against mosquitoes, an overflow sent away from the house, a spigot, and "
    "draining it before freezing weather. For watering plants, not drinking.",
    ("rain barrel", "rainwater", "collect rainwater", "rain catchment", "water barrel"),
    ("injury",),
    "Collecting rainwater is legal almost everywhere now, but a few places limit how much or how. " + _LOCAL,
    ("a full barrel (about 450 lb) tipping off a weak stand", "mosquitoes breeding in open water", "cuts from the "
     "downspout"),
    ("work gloves", "safety glasses"),
    ("hacksaw or tin snips (for the downspout)", "drill with a hole saw", "level", "a screwdriver"),
    ("a food-grade barrel (50 to 60 gal) with a lid", "a diverter kit or a flexible downspout elbow", "fine mesh "
     "screen", "a spigot and an overflow fitting with hose", "cinder blocks or a built stand", "plumber's tape"),
    (
        Phase("Plan before you set it up", (
            Step("Check your area's rules, and pick a downspout near where you'll water, on firm ground.", "A full "
                 "barrel is heavy and needs a solid base.", ("Near the garden saves carrying water.",),
                 "The rules are fine and the spot chosen."),
            Step("Work out what the gutter brings: about 0.6 gal for each sq ft it drains, per inch of rain.", "A small house "
                 "fills a barrel in one storm; plan the overflow.", ()),
        )),
        Phase("The barrel and stand", (
            Step("Build or set a stand of cinder blocks a foot or more high, level and solid.", "Height gives the "
                 "spigot pressure; a level stand won't tip.", ("Level both ways; check after the first fill.",)),
            Step("Drill and fit the spigot near the bottom and the overflow near the top, sealed with tape.",
                 "The overflow decides where the extra water goes.",
                 ("Make the overflow as large as the downspout.",)),
            Step("Fasten the lid so children and animals can't get in.", "A barrel of water is a drowning risk "
                 "for a small child or animal.", ("A locking or screwed lid.",)),
            Step("Screen the top opening with fine mesh under the lid.", "Mosquitoes breed in a week in open "
                 "water.", ("No gap in the screen.",), "The barrel is fitted and screened on a solid stand."),
        )),
        Phase("Connect it", (
            Step("Cut the downspout at the barrel's height and fit the diverter or elbow into the barrel.", "A "
                 "diverter sends water on down the spout once the barrel is full.", ()),
            Step("Run the overflow hose away from the house, at least a few feet onto ground that slopes away.",
                 "Overflow at the wall soaks the ground at the house.", ("Never onto a neighbor's land.",)),
            Step("Let the first rain fill it and check every fitting for leaks.", "Leaks show when it's full.", (),
                 "It fills, overflows away from the house, and doesn't leak."),
            Step("Link a second barrel with a hose near the bottom if one fills too fast.", "Linked barrels "
                 "hold more without overflowing every storm.", ("Set them at the same height.",)),
        )),
        Phase("Use and check", (
            Step("Use it for plants, not drinking or washing vegetables you eat raw.", "Gutter water carries what's "
                 "up on the house.", ()),
            Step("Drain it and disconnect before freezing weather, and clean it once a year.", "Frozen water splits "
                 "the barrel and the spigot.", (), "It's used, cleaned and winterized."),
        )),
    ),
    ("US EPA, Soak Up the Rain: Rain Barrels",
     "Penn State Extension, Rain Barrels and Rainwater Harvesting",
     "The rain barrel or diverter maker's instructions"),
    skill="plumbing",
))

register(Job(
    "well_shock", "plumbing", "repair", "Shock-chlorinate a private well",
    "Disinfecting a private well after a positive bacteria test, a flood, or work on the well: the water heater and "
    "treatment bypassed, the bleach worked out from the water in the well, the pump's power off before opening the "
    "cap, the bleach poured and recirculated until every tap smells of it, a long contact time, flushing away from the "
    "septic and the garden, and a retest before drinking.",
    ("shock the well", "shock chlorinate", "chlorinate the well", "well disinfection", "bacteria in the well",
     "well water test positive"),
    ("live_power", "injury"),
    "Shocking your own well needs no permit, but your health department may have a guide and a lab for the retest. " +
    _LOCAL,
    ("chlorine fumes in a closed pump house or basement", "bleach splashed in the eyes or on skin", "electric shock "
     "at a well cap with wires through it", "drinking the water before it tests clear"),
    ("safety glasses or goggles", "rubber gloves", "old clothes"),
    ("a garden hose", "a measuring container", "a funnel", "a wrench or screwdriver for the well cap", "chlorine test "
     "strips"),
    ("unscented household bleach (no additives)", "a bacteria test kit or the lab's sample bottle", "a few days of "
     "bottled drinking water"),
    (
        Phase("Plan before you open the well", (
            Step("Find the well's depth and casing diameter (the well log, or measure), and work out the water in "
                 "it: a 6 in casing holds about 1.5 gal a foot.", "The amount of bleach comes from the water in the "
                 "well.", ("Your health department's guide gives the bleach for each depth.",),
                 "You know the gallons in the well and the bleach to use."),
            Step("Set aside bottled water for 2 to 3 days, and plan the flush water's path away from the septic "
                 "field, the garden and any stream.", "Chlorinated water kills a septic system's bacteria and "
                 "plants.", ()),
            Step("Bypass or turn off the water softener, filters and any UV system; turn off the water heater (or "
                 "bypass it).", "Chlorine damages filters and resin, and the heater would hold chlorinated water for "
                 "days.", ("Gas heater: set it to pilot or vacation.",)),
        )),
        Phase("Chlorinate", (
            Step("Turn off the pump's breaker, then open the well cap (prove its wires dead if any run through it).",
                 "Some caps carry the pump's power cable.", ("Never open a cap with the pump powered.",)),
            Step("Pour in the bleach through a funnel, avoiding the wiring, and close the cap.", "Bleach on the "
                 "pump's splices corrodes them.", ()),
            Step("Pour a bucket of chlorinated water (a little bleach in it) down the inside of the casing too.", "The "
                 "casing walls and the cap's underside hold bacteria the well water may not reach.", ("Wet the whole inside of the casing.",)),
            Step("Turn the pump back on and run a garden hose from an outside tap back down the well (cap opened a "
                 "crack) until you smell chlorine at the hose.", "Recirculating mixes the chlorine through the whole "
                 "well and its casing.", ("Run it 15 to 30 minutes.",),
                 "The water at the hose smells strongly of chlorine."),
            Step("Open each tap in the house, hot and cold, until it smells of chlorine, then close it.", "Every "
                 "pipe needs the chlorine to reach it.", ()),
        )),
        Phase("Contact and flush", (
            Step("Let it sit 12 to 24 hours without using the water.", "Chlorine needs time to kill what's in the "
                 "well and pipes.", ("Overnight is the minimum.",)),
            Step("Flush from an outside hose to a spot away from the septic and plants until the smell is gone "
                 "(test strips near zero), then run each indoor tap briefly.", "A slow flush avoids overworking the "
                 "pump.", ("Don't run it into the septic system.",), "The chlorine is flushed out."),
        )),
        Phase("Restore and check", (
            Step("Turn the water heater and treatment back on (fresh filter cartridges).", "Old filters hold the "
                 "bacteria you just killed.", ()),
            Step("Retest for bacteria 7 to 10 days later, and keep using bottled water until it's clear.",
                 "Only a clear test says the water is safe.", ("A second positive: call a well contractor.",),
                 "The retest is clear."),
        )),
    ),
    ("US Centers for Disease Control and Prevention, Disinfecting Wells After an Emergency",
     "US EPA, Private Drinking Water Wells",
     "National Ground Water Association, Shock Chlorination of a Water Well"),
    skill="plumbing",
))

register(Job(
    "septic_care", "plumbing", "repair", "Care for a septic system",
    "Keeping a septic system working: the tank and drainfield located and drawn, the pumping schedule from the tank "
    "size and household, the effluent filter cleaned, what never goes down the drain, the drainfield protected, and "
    "the signs of failure known. Pumping and repairs are a licensed septic contractor's work.",
    ("septic", "septic tank", "septic system", "septic care", "pump the septic", "drain field"),
    ("utilities", "licensed", "injury"),
    "Septic pumping and repairs are licensed work in most places, and the local health department keeps the system's "
    "records and permits any change. " + _LOCAL,
    ("septic gases: never put your head in or enter a tank (it can kill in seconds)", "falling into an open tank",
     "digging into buried lines to reach the lids", "sewage contact"),
    ("rubber gloves", "safety glasses", "boots you can wash"),
    ("a probe rod or a long screwdriver", "a shovel", "a garden hose", "a flashlight", "tape measure"),
    ("risers and secure lids (if the lids are buried)", "an effluent filter if the tank has none", "records of "
     "pumpings and inspections"),
    (
        Phase("Plan before you dig", (
            Step("Get the system's drawing from the health department (or the last pumping record) and find the "
                 "tank and the drainfield.", "You can't care for what you can't find.", ("Probe gently: the lids "
                                                                                       "are often 1 to 2 ft down.",),
                 "You know where the tank and field are."),
            Step("Call 811 before digging to the lids.", "Lines often run near the tank.", (), "Any lines are marked."),
            Step("Work out the pumping schedule: commonly every 3 to 5 years, sooner for a small tank or a big "
                 "household.", "Sludge that builds past a third of the tank flows into the field and clogs it.", ()),
        )),
        Phase("Access and the filter", (
            Step("Uncover the lids (or fit risers so you never dig again), and keep them secured.", "Risers make "
                 "every pumping cheaper and safer.", ("A lid must be too heavy or locked for a child to open.",)),
            Step("Clean the effluent filter by hosing it back into the tank (gloves on, head well clear).",
                 "A clogged filter backs up the house.", ("Never lean over the opening: the gas can overcome you.",)),
            Step("Have the contractor pump the tank and measure the sludge and scum, and keep the record.",
                 "Pumping is the one job that keeps the field alive.", (),
                 "The tank is pumped, the filter clean and the lids secure."),
            Step("Ask the contractor to look at the baffles and the tee where water leaves the tank.", "A broken "
                 "baffle lets solids straight into the field.", ("Note what they find with the pumping record.",)),
        )),
        Phase("Protect it every day", (
            Step("Keep out of the drains: wipes, grease, paint, solvents, medicines, and too much bleach.",
                 "They clog the tank or kill the bacteria that make it work.", ("Even 'flushable' wipes don't break "
                                                                                "down.",)),
            Step("Spread out water use (laundry over the week) and fix running toilets.", "A flood of water pushes "
                 "solids into the field.", ("One load of laundry a day, not five on Saturday.",)),
            Step("Keep cars, livestock, trees and buildings off the drainfield.", "Weight crushes the pipes; roots "
                 "fill them.", ("Plant only grass over the field.",), "The household's habits protect it."),
        )),
        Phase("Check for failure", (
            Step("Watch for slow drains, gurgling, sewage smell, or wet, bright-green grass over the field.",
                 "Those are the early signs before a backup.", ("Any of them: call a septic contractor.",)),
            Step("Note every pumping and inspection with its date.", "The record sets the next pumping and helps "
                 "when the house is sold.", (), "The schedule and records are kept."),
        )),
    ),
    ("US EPA, A Homeowner's Guide to Septic Systems (EPA-832-B-02-005)",
     "US EPA, SepticSmart program",
     "National Onsite Wastewater Recycling Association (NOWRA), homeowner guidance"),
    skill="plumbing",
))

register(Job(
    "electric_fence", "electrical", "install", "Put up an electric fence for animals",
    "An electric fence for livestock or to keep animals out of a garden: the energizer sized for the length and the "
    "animal, a proper ground of rods, posts and insulators, the wire or tape at the heights for the animal, insulated "
    "gate handles, warning signs, and a tester. Plug-in chargers go in a GFCI-protected receptacle.",
    ("electric fence", "hot wire fence", "fence charger", "electric netting", "livestock fence"),
    ("live_power", "utilities", "injury"),
    "Electric fences are legal for livestock nearly everywhere, but many places require warning signs along a road or "
    "path, and some limit them near property lines. " + _LOCAL,
    ("shocks from a live wire (painful, dangerous for anyone with a pacemaker)", "driving ground rods into buried "
     "lines", "grass fires from a fence shorting in dry weed", "children touching it"),
    ("insulated gloves when handling a live fence", "safety glasses when driving rods"),
    ("a post driver", "a fence tester (digital voltmeter)", "pliers and a wire tightener", "a hammer or sledge",
     "tape measure"),
    ("an energizer (low-impedance) sized in joules for the length and the animal", "three galvanized ground rods "
     "with clamps", "posts (T-posts or step-in posts) and the right insulators", "polywire, polytape or high-tensile "
     "wire", "insulated gate handles", "warning signs", "a GFCI-protected receptacle for a plug-in energizer"),
    (
        Phase("Plan before you build", (
            Step("Measure the fence length and choose the energizer for the length and the animal (goats and sheep "
                 "need more than cattle), and the wire heights for that animal.", "An energizer too weak for the "
                 "length won't hold the animal.", ("The charger's maker lists miles and animals.",),
                 "You have the charger, the heights and the length."),
            Step("Call 811 before driving ground rods or posts.", "Rods go 6 to 8 ft down, right where lines can "
                 "run.", (), "Every line is marked."),
            Step("Check your area's rules for warning signs and placement.", "Signs are often required where people "
                 "walk.", ()),
        )),
        Phase("Ground and posts", (
            Step("Drive three ground rods about 10 ft apart near the energizer, connected with one continuous wire "
                 "and clamps.", "Most fence failures are a weak ground: the shock completes through the earth.",
                 ("Keep them 50 ft from any utility ground rod.",)),
            Step("Set the corner and gate posts solid, then line posts at the spacing for the wire (closer on "
                 "curves).", "Corners take the strain.", ()),
            Step("Brace the corner and end posts (an H-brace for high-tensile wire).", "Unbraced corners lean and "
                 "the wire sags onto the ground.", ("Brace before tensioning.",)),
            Step("Fit insulators on every post at the heights for the animal.", "Wire touching a post shorts the "
                 "fence.", ("Use insulators made for the post type.",), "The ground and the posts are in."),
        )),
        Phase("Wire and power", (
            Step("Run the wire or tape through the insulators, snug but not stretched tight, with insulated handles "
                 "at the gates.", "Gates break the line; handles let people pass without a shock.", ()),
            Step("Mount the energizer under cover, connect the ground terminal to the rods and the fence terminal to "
                 "the fence, then plug it into a GFCI receptacle (or connect its battery or solar panel).",
                 "Connect ground first so the fence is never live without its ground.", ("Fence off before any "
                                                                                         "wiring change.",)),
            Step("Hang warning signs along the fence where people pass.", "Signs warn visitors and are often "
                 "required.", ("Every few hundred feet and at each gate.",), "The fence is wired, powered and signed."),
        )),
        Phase("Test and check", (
            Step("Test the voltage at the far end with the tester (commonly 4,000 volts or more for most animals), "
                 "and at the ground rods (near zero).", "Low voltage far out means a short or a weak ground.",
                 ("Walk the line for grass touching the wire.",)),
            Step("Train animals to it and check it weekly, keeping weeds off the bottom wire.", "Weeds drain the "
                 "charge and can start a fire in dry weather.", (), "It tests strong at the far end and holds the "
                 "animals."),
        )),
    ),
    ("University of Missouri Extension, Electric Fencing for Serious Graziers (M168)",
     "National Fire Protection Association, NFPA 70 National Electrical Code (NEC) 2023: 210.8 (GFCI outdoors)",
     "The energizer maker's installation manual"),
    skill="electrical_wiring",
))


# ------------------------------------------------------------------ the sixth tier (2026-11-09)

register(Job(
    "workshop_subpanel", "electrical", "install", "A feeder and subpanel for the workshop",
    "Power for a workshop that needs more than one circuit or 240 V tools: the load worked out, a feeder from the "
    "house panel sized for it (four wires: two hots, a neutral and a ground), buried at code depth, a subpanel at the "
    "workshop with its neutrals and grounds kept apart, its own grounding electrodes, its main disconnect, and the "
    "branch circuits from it. Where a homeowner may not do this work, a licensed electrician does it; the service "
    "itself is always the utility's and an electrician's.",
    ("workshop subpanel", "subpanel", "feeder to the workshop", "sub panel", "240 to the shop",
     "power the workshop"),
    ("live_power", "licensed", "utilities", "weather", "injury"),
    "A feeder and subpanel need an electrical permit with a trench inspection, a rough-in and a final. Some places let "
    "a homeowner do it on their own property under that permit; many require a licensed electrician for a feeder. " +
    _LOCAL,
    ("electric shock: the house panel's incoming lugs stay live with its main off", "arc flash in either panel",
     "a buried feeder struck later if it's shallow", "a subpanel with neutral and ground bonded (current on the "
     "ground, a shock hazard)"),
    ("insulated gloves rated for the voltage when testing", "safety glasses", "work boots"),
    ("non-contact and two-lead voltage testers", "insulated screwdrivers and a torque screwdriver", "wire strippers "
     "and cable cutters for large wire", "trenching shovel or a rented trencher", "a fish tape and pulling lube",
     "a ground-rod driver"),
    ("a subpanel sized for the load (with a main breaker, or a disconnect ahead of it)", "a 2-pole feeder breaker "
     "listed for the house panel", "feeder conductors sized for the load and length (copper or aluminum, per the "
     "code's tables)", "PVC conduit and fittings (or direct-burial cable rated for it)", "two ground rods (or the "
     "electrode system your code asks) and clamps", "the workshop's branch breakers and circuits"),
    (
        Phase("Plan and permit before you dig", (
            Step("Work out the workshop's load (lights, receptacles, the biggest tools that run together, a heater "
                 "or AC) with the code's load calculation, and choose the feeder size and the subpanel's rating.",
                 "An undersized feeder trips or overheats; voltage drop over a long run stalls motors.",
                 ("Over about 100 ft, size up for voltage drop.",),
                 "You have the load, the feeder size and the subpanel, and the permit is in hand."),
            Step("Check the house panel has the capacity and two spaces for the feeder breaker.", "A full or "
                 "maxed-out panel can't take a feeder.", ("No room: a panel upgrade first (the utility and an "
                                                          "electrician).",)),
            Step("Call 811 and wait for the marks.", "The trench crosses the yard's service lines.", (),
                 "Every line is marked."),
        )),
        Phase("Trench and conduit", (
            Step("Trench to the depth the code gives for the wiring method (commonly 18 in for PVC, 24 in for "
                 "direct-burial cable), hand-digging near any mark.", "Depth protects the feeder from a shovel later.",
                 ("Hand-dig within 18 in of each mark.",)),
            Step("Lay the conduit with sweeps up at each end, glued, with expansion fittings where the risers need "
                 "them, and warning tape above.", "A feeder pulled through conduit can be replaced without digging.",
                 (), "The trench inspection has passed with the conduit in place."),
        )),
        Phase("The subpanel", (
            Step("Mount the subpanel in the workshop, and drive the ground rods outside (at least 6 ft apart), "
                 "bonded to the subpanel's ground bar.", "A separate building needs its own grounding electrodes.",
                 ("Keep the rods clear of the utility's.",)),
            Step("Pull the four feeder conductors (two hots, neutral, ground) and land them in the subpanel: the "
                 "neutral on an isolated neutral bar, the ground on the ground bar, the bonding screw left out.",
                 "In a subpanel the neutral and ground stay apart, so no current runs on the ground.",
                 ("Remove the green bonding screw or strap if the panel came with it in.",)),
            Step("Install the branch breakers and circuits in the workshop (GFCI where the code asks), with the "
                 "subpanel's main or the building disconnect accessible.", "The disconnect lets anyone shut the "
                 "building off at the building.", (), "The subpanel is grounded, wired and its circuits in."),
        )),
        Phase("Connect at the house panel", (
            Step("With the house main off, prove the panel dead (live-dead-live), then land the feeder on its 2-pole "
                 "breaker, the neutral and ground on the house panel's bars, all torqued.", "Loose terminals in a "
                 "feeder heat and burn.", ("The service lugs stay live with the main off.",)),
            Step("Close both panels with every blank in place, turn the house main on, then the feeder breaker, then "
                 "the subpanel's main.", "Powering up in order finds a fault at the first breaker.", (),
                 "Both panels are closed and the feeder is powered."),
        )),
        Phase("Test and final inspection", (
            Step("Check the voltage at the subpanel (about 240 V across the hots, 120 V each to neutral), and test "
                 "every receptacle and GFCI.", "Wrong readings mean a bad connection or a swapped wire.",
                 ("No voltage on the ground bar to neutral beyond a few volts under load.",)),
            Step("Run the biggest tools together and check the feeder breaker and the lugs for heat after a while.",
                 "Heat at a connection is a loose terminal.", ()),
            Step("Fill in both panel directories and call for the final inspection.", "The final makes it legal and "
                 "insurable.", (), "The final inspection passed."),
        )),
    ),
    ("National Fire Protection Association, NFPA 70 National Electrical Code (NEC) 2023: 220 (load calculations), "
     "225.30 to 225.39 (outside feeders and the building disconnect), 250.32 (separate buildings: grounding "
     "electrodes, neutral and ground kept apart), 300.5 (underground), 310.16 (conductor ampacity)",
     "Mike Holt, Understanding the National Electrical Code, Vol. 1 (2023)",
     "OSHA 29 CFR 1910.333, Selection and Use of Work Practices (de-energizing and testing before work)"),
    skill="electrical_wiring",
))
