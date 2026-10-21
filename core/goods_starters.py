"""
core.goods_starters
=====================

Starter recipes for homestead goods (DEC-0037): a cutting board, a
planter, spice and herb blends, mixes in a jar, eggs, microgreens and
plant starts, to copy into Workshop → Recipes and change to your own.
Generic on purpose: no prices (yours to set), quantities a common
starting point, allergens from the usual ingredients (check your own
ingredients' labels). Baking recipes are in grams so labels can order
the ingredients by weight.

`craft_recipe.starter` (an action, core/goods_actions.py) adds one.
"""

from __future__ import annotations

STARTERS: tuple[dict, ...] = (
    # ---------------------------------------------------------------- wood goods
    {"id": "cutting_board", "group": "Wood goods", "name": "Cutting board", "category": "wood goods",
     "makes": 2, "makes_unit": "boards", "est_hours": 3,
     "materials": "1 board Hardwood 1x8 4ft\n2 oz Food-safe mineral oil\n1 oz Beeswax\n2 sheets Sandpaper",
     "cut_list": "2 @ 16 in x 7.25 in", "tools": "Miter saw, router (round-over bit), random orbit sander",
     "steps": "Cut to length\nRound over the edges\nSand 80 → 120 → 220\nRaise the grain, sand again\nOil, let soak, wax",
     "notes": "Set your price. Hardwood with a closed grain (maple, cherry, walnut) for food contact."},
    {"id": "bread_board", "group": "Wood goods", "name": "Bread board with handle", "category": "wood goods",
     "makes": 2, "makes_unit": "boards", "est_hours": 3,
     "materials": "1 board Hardwood 1x10 4ft\n2 oz Food-safe mineral oil\n1 oz Beeswax\n2 sheets Sandpaper",
     "tools": "Jigsaw or bandsaw, drill (hanging hole), sander",
     "steps": "Trace the shape\nCut it out\nDrill the hanging hole\nSand 80 → 220\nOil and wax",
     "notes": "Set your price. Sells well next to the bread."},
    {"id": "planter_box", "group": "Wood goods", "name": "Cedar planter box", "category": "wood goods",
     "makes": 1, "makes_unit": "planters", "est_hours": 2,
     "materials": "3 board Cedar fence picket 6ft\n1 board 2x2 8ft\n40 pcs Exterior screws 1-1/4in",
     "cut_list": "Sides: 8 @ 24 in · Ends: 8 @ 10.5 in · Bottom: 3 @ 22.5 in · Corners: 4 @ 10 in",
     "tools": "Miter saw, drill/driver", "steps": "Cut the pieces\nBuild the ends on the corner posts\nAdd the sides\nAdd the bottom slats",
     "notes": "Set your price."},
    {"id": "birdhouse", "group": "Wood goods", "name": "Birdhouse", "category": "wood goods",
     "makes": 4, "makes_unit": "birdhouses", "est_hours": 3,
     "materials": "2 board Cedar 1x6 6ft\n80 pcs Exterior screws 1-1/4in",
     "tools": "Miter saw, drill, 1-1/2 in hole saw", "steps": "Cut the pieces\nDrill the entry holes\nAssemble\nHinge one side to clean out",
     "notes": "Set your price. The entry-hole size decides which birds move in."},
    {"id": "wood_sign", "group": "Wood goods", "name": "Wooden sign", "category": "wood goods",
     "makes": 1, "makes_unit": "signs", "est_hours": 2,
     "materials": "1 board Pine 1x10 4ft\n4 oz Stain\n2 oz Paint\n1 pcs Sawtooth hanger",
     "steps": "Cut and sand\nStain\nLay out the words\nPaint or burn the letters\nSeal",
     "notes": "Set your price. Custom names: take an order (Orders & Quotes)."},
    # ---------------------------------------------------------------- seasonings and dry goods
    {"id": "taco_seasoning", "group": "Seasonings & dry goods", "name": "Taco seasoning", "category": "seasoning",
     "makes": 6, "makes_unit": "jars", "net_amount": "2.5 oz", "shelf_days": 0,
     "materials": "160 g Chili powder\n80 g Ground cumin\n60 g Salt\n40 g Paprika\n30 g Garlic powder\n30 g Onion powder\n"
                  "15 g Dried oregano\n6 Spice jar 4oz",
     "steps": "Weigh everything\nMix well\nFill the jars\nLabel", "notes": "Set your price. Keeps; best within a year."},
    {"id": "herb_blend", "group": "Seasonings & dry goods", "name": "Italian herb blend", "category": "seasoning",
     "makes": 6, "makes_unit": "jars", "net_amount": "1 oz",
     "materials": "60 g Dried basil\n50 g Dried oregano\n30 g Dried thyme\n20 g Dried rosemary\n6 Spice jar 4oz",
     "steps": "Crumble the dried herbs\nMix\nFill the jars\nLabel",
     "notes": "Set your price. Grow and dry the herbs yourself: harvest them from the Grow Lab into Materials."},
    {"id": "tea_blend", "group": "Seasonings & dry goods", "name": "Chamomile mint tea", "category": "tea",
     "makes": 6, "makes_unit": "jars", "net_amount": "1 oz",
     "materials": "100 g Dried chamomile\n60 g Dried peppermint\n6 Spice jar 4oz",
     "steps": "Mix gently (don't crush the flowers)\nFill the jars\nLabel", "notes": "Set your price."},
    {"id": "cookie_mix_jar", "group": "Seasonings & dry goods", "name": "Cookie mix in a jar", "category": "mix",
     "makes": 4, "makes_unit": "jars", "net_amount": "1 qt jar",
     "allergens": "Contains: wheat, milk, soy",
     "materials": "1000 g All-purpose flour\n600 g Brown sugar\n400 g Sugar\n680 g Chocolate chips\n20 g Baking soda\n"
                  "20 g Salt\n4 Mason jar 1qt",
     "steps": "Layer flour, sugars, chips in each jar\nTag with the baking directions (add butter, egg, vanilla)\nLabel",
     "notes": "Set your price. A gift-season seller."},
    {"id": "brownie_mix_jar", "group": "Seasonings & dry goods", "name": "Brownie mix in a jar", "category": "mix",
     "makes": 4, "makes_unit": "jars", "net_amount": "1 qt jar", "allergens": "Contains: wheat, milk, soy",
     "materials": "1000 g Sugar\n500 g All-purpose flour\n320 g Cocoa powder\n340 g Chocolate chips\n10 g Salt\n4 Mason jar 1qt",
     "steps": "Layer in each jar\nTag with the baking directions (add eggs, oil, vanilla)\nLabel", "notes": "Set your price."},
    {"id": "kettle_corn", "group": "Seasonings & dry goods", "name": "Kettle corn", "category": "snack",
     "makes": 10, "makes_unit": "bags", "shelf_days": 7, "net_amount": "6 oz",
     "materials": "400 g Popcorn kernels\n200 g Sugar\n120 g Vegetable oil\n15 g Salt\n10 Treat bag",
     "steps": "Heat the oil\nAdd kernels and sugar, keep it moving\nSalt\nCool, bag, seal", "notes": "Set your price. Great at events."},
    # ---------------------------------------------------------------- baked goods
    {"id": "banana_bread", "group": "Baked goods", "name": "Banana bread", "category": "quick bread",
     "makes": 2, "makes_unit": "loaves", "shelf_days": 4, "net_amount": "1 loaf",
     "allergens": "Contains: wheat, milk, egg",
     "materials": "500 g All-purpose flour\n300 g Sugar\n230 g Butter\n6 Bananas\n4 Eggs\n10 g Baking soda\n5 g Salt",
     "label_ingredients": "Flour, bananas, sugar, butter, eggs, baking soda, salt",
     "steps": "Mash the bananas\nCream butter and sugar\nAdd eggs, bananas\nFold in the dry\nBake 350°F about 60 min\nCool, wrap",
     "notes": "Set your price. No cream cheese frosting: it would need refrigeration."},
    {"id": "choc_chip_cookies", "group": "Baked goods", "name": "Chocolate chip cookies", "category": "cookies",
     "makes": 4, "makes_unit": "dozen", "shelf_days": 5, "net_amount": "12 cookies",
     "allergens": "Contains: wheat, milk, egg, soy",
     "materials": "560 g All-purpose flour\n450 g Butter\n400 g Brown sugar\n340 g Chocolate chips\n200 g Sugar\n4 Eggs\n"
                  "10 g Baking soda\n10 g Salt",
     "steps": "Cream butter and sugars\nAdd eggs\nMix in the dry\nFold in chips\nBake 375°F 9-11 min\nCool, bag by the dozen",
     "notes": "Set your price."},
    # ---------------------------------------------------------------- from the coop and the greenhouse
    {"id": "eggs", "group": "From the coop & greenhouse", "name": "Eggs", "category": "eggs",
     "makes": 1, "makes_unit": "dozen", "net_amount": "1 dozen",
     "notes": "Set your price and how many days they keep. Chickens → Into Cartons puts dozens here. "
              "Eggs have their own selling rules: check yours."},
    {"id": "microgreens", "group": "From the coop & greenhouse", "name": "Microgreens", "category": "produce",
     "makes": 8, "makes_unit": "clamshells", "shelf_days": 7, "net_amount": "2 oz",
     "materials": "1 tray Growing mat\n30 g Microgreen seed\n8 Clamshell 4oz",
     "steps": "Soak and sow\nBlackout 3-4 days\nUnder light until ready (7-14 days)\nCut, weigh, pack",
     "notes": "Set your price. Grow it as a Grow Lab batch and harvest straight into stock, or craft it here."},
    {"id": "tomato_starts", "group": "From the coop & greenhouse", "name": "Tomato starts", "category": "plants",
     "makes": 36, "makes_unit": "pots",
     "materials": "1 bag Seed-starting mix\n36 pcs Pot 3.5in\n1 packet Tomato seed",
     "steps": "Sow in cells\nPot up at the first true leaves\nHarden off a week before selling",
     "notes": "Set your price. Spring's big seller; peppers and herbs the same way."},
)
STARTERS_BY_ID = {s["id"]: s for s in STARTERS}


def starter_fields(starter_id: str) -> dict:
    """The recipe fields for a starter (a copy, without its id and group)."""
    s = STARTERS_BY_ID.get(starter_id)
    if s is None:
        raise KeyError(starter_id)
    return {k: v for k, v in s.items() if k not in ("id", "group")}


def starter_list() -> list[dict]:
    """For a picker: id, name and group."""
    return [{"id": s["id"], "name": s["name"], "group": s["group"],
             "makes": f"{s.get('makes', 1):g} {s.get('makes_unit', '')}".strip()} for s in STARTERS]
