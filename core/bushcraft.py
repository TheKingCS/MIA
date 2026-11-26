"""
core.bushcraft
================

Survival and bushcraft, a learning program on core/paths.py's method (DEC-0289; Zac, 2026-11-23: "Survival /
bushcraft"): priorities and the kit, fire and water, shelter and navigation. Stages of lessons with why and what to
watch for, checks said, counted or read from his own records (a GPS track for the navigation walk). Practised in safe
conditions with someone told the plan; first aid is the emergency floor's and the library's (core/first_aid_floor.py),
not this program's.

Written from: US Army ATP 3-50.21, Survival (2018); The Mountaineers, Mountaineering: The Freedom of the Hills (the Ten
Essentials); Boy Scouts of America Fieldbook (fire, map and compass, and knots); CDC, Making Water Safe in an Emergency (boil
1 minute, 3 minutes above 6,500 ft); US EPA, Emergency Disinfection of Drinking Water. Its XP goes to the Survival
skill.
"""

from __future__ import annotations

from core.paths import Check, Lesson, Program, Stage, register

SKILL = "survival"  # her skill tree's Survival skill (data/skill_definitions.json)

STAGES: tuple[Stage, ...] = (
    Stage(1, "Priorities and the kit", "staying calm, putting first things first, and carrying the Ten Essentials", (
        Lesson("priorities", "First things first", (
            "When something goes wrong: STOP. Stop, Think, Observe, Plan. Most bad outcomes start with a rushed move.",
            "The rough rule of threes orders what matters: about 3 minutes without air, 3 hours exposed in harsh "
            "weather, 3 days without water, 3 weeks without food.",
            "So: safety and first aid, then shelter and warmth, then water, then food; signal for help throughout.",
            "Before any trip, tell someone where you're going and when you'll be back."),
            "Panic wastes the time and energy the priorities need; the order keeps you working on what kills first.",
            ("Wandering off to find the way out before thinking it through.", "Looking for food before shelter.")),
        Lesson("ten_essentials", "The Ten Essentials", (
            "Navigation (map, compass, and a GPS or phone as a backup).",
            "A headlamp; sun protection; first aid; a knife; fire (matches, a lighter and a ferro rod).",
            "Shelter (an emergency bivy or tarp); extra food; extra water and a way to treat it; extra clothes.",
            "Pack them for every trip, and know how to use each one."),
            "Search and rescue reports often name one of these as missing: the extra layer, the light or the map.",
            ("Relying on a phone for navigation, light and help all at once.",)),
    ), (
        Check("kit_built", "Put together your Ten Essentials and go through them with MIA", "said"),
        Check("trip_plan", "Leave a trip plan with someone before an outing, and tell MIA you did", "said"),
    )),
    Stage(2, "Fire and water", "making fire reliably and making water safe", (
        Lesson("fire", "Making fire", (
            "Check for burn bans first; clear a spot down to bare soil, away from overhanging branches, with water "
            "at hand.",
            "Gather everything before lighting: tinder (dry grass, birch bark, cotton with petroleum jelly), "
            "kindling from pencil-lead to thumb thick, then fuel wrist thick and up.",
            "Make feather sticks from dry wood split open to its dry centre; light the tinder (a ferro rod: scrape "
            "the rod, not the striker, close to the tinder), then feed it gradually, small to large, with air.",
            "Put it out dead out: drown, stir, drown again, until it's cold to the touch."),
            "Fire is warmth, dry clothes, safe water and morale; most failures are wet fuel or rushing to big wood.",
            ("Smothering a new flame with too much wood.", "Leaving embers that rekindle.")),
        Lesson("water", "Making water safe", (
            "Bring it to a rolling boil for 1 minute (3 minutes above 6,500 ft), then let it cool.",
            "Or a filter rated for the water you're drinking, or household bleach by the EPA's dose (MIA's water and "
            "bleach calculator), 30 minutes' contact. Most hiking filters don't stop viruses, and boiling doesn't "
            "remove chemicals: water near farms, mines or roads needs a different source.",
            "Cloudy water: let it settle and strain it through cloth first.",
            "Collect from moving water upstream of trails and camps; never from below a farm's runoff."),
            "Bad water can disable you in a day; treating it is simple when you have a way.",
            ("Drinking clear water untreated because it looks clean.",)),
    ), (
        Check("fire_ferro", "Light a fire with a ferro rod and natural tinder, three times, safely", "counted",
              passes_at=3, unit="fires"),
        Check("water_treated", "Treat a liter of water by boiling and by one other way, and tell MIA", "said"),
    )),
    Stage(3, "Shelter and navigation", "staying warm and dry, and finding your way with a map and compass", (
        Lesson("shelter", "Shelter", (
            "Get off the ground first: cold ground pulls heat from you all night. A thick bed of dry leaves or "
            "boughs, or a pad.",
            "A tarp as a lean-to or A-frame, its back to the wind, tight and sloped to shed rain.",
            "Without a tarp, a debris hut: a ridgepole, ribs, and dry leaves piled an arm's length thick.",
            "Small is warmer: a shelter only big enough to lie in."),
            "Cold and wet kill faster than hunger; a dry, insulated shelter is the first thing that keeps you alive "
            "overnight.",
            ("A big, open shelter that can't hold warmth.", "Lying on bare ground.")),
        Lesson("navigation", "Map and compass", (
            "Orient the map: turn it until its north matches the compass's north, allowing for the declination the "
            "map shows.",
            "Take a bearing: point the compass's travel arrow at the target, turn the dial until the needle's red "
            "(north) end sits inside the orienting arrow (\"red in the shed\"), read the bearing. The white end "
            "there puts you 180 degrees off.",
            "Walk the bearing from landmark to landmark along it; count paces to know the distance (count your own "
            "paces per 100 m first).",
            "Always know where you are on the map; the GPS is the backup, not the plan."),
            "A map and compass need no battery or signal; it's the skill that gets you out when the phone can't.",
            ("Ignoring declination: a few degrees off becomes far off over a mile.",)),
        Lesson("knots", "Knots for camp and load", (
            "A bowline makes a fixed loop that won't slip or jam: around a tree, a tarp's corner, a person in a rescue "
            "(\"the rabbit comes out of the hole, round the tree and back down the hole\").",
            "A taut-line hitch makes a loop you can slide to tighten: guy lines and a tent's lines.",
            "A trucker's hitch tensions a line hard, for a ridgeline or a load: tie a loop in the standing part, run "
            "the end round the anchor (a tie-down point or tree) and back through the loop, pull down for about three "
            "to one, and finish with two half hitches.",
            "A clove hitch holds a line to a post or pole quickly; back it up with a half hitch when it matters."),
            "The right knot holds under load and still unties after; the wrong one slips, or jams so it has to be cut.",
            ("A load on a truck or trailer: rated ratchet straps at each corner beat any rope; rope and a trucker's "
             "hitch are for light loads or a tarp.", "Leave a tail a few inches long: a short one works loose.")),
    ), (
        Check("night_out", "Spend a night in a shelter you built, close to home and with someone told, and tell MIA",
              "said"),
        Check("bearing_walk", "Walk a course of at least 5 km by map and compass alone (the GPS only recording), and "
              "tell MIA how close you came to each point", "said"),
    )),
)

PROGRAM = register(Program(
    "bushcraft", "Survival and bushcraft", SKILL, "🔥", "Priorities and the Ten Essentials, fire and safe water, "
    "shelter and finding your way with a map and compass.",
    ("survival", "bushcraft", "wilderness skills", "survival skills", "outdoor skills", "prepper skills"), STAGES,
    plan=(30, 2)))
