"""
core.assistant_plan_actions
=============================

The Library's plans by voice (core/plan_library.py): "do we have plans for
a chicken coop?", "what do I need for a 10 by 12 shed?", "make me a cut
list for a 4 by 8 raised bed", "what do I still need to buy for the
fence?", "where can I get free barn plans?", "start the shed as a
project". The numbers come from core/build_calcs.py; the model only says
them.

- `find_plans`, `show_plan`: search the shelf and read a plan (its
  materials, cuts, tools, steps, or where its file is).
- `material_list`: what a project needs at a size (every calculator in
  core/build_calcs.py: walls, floors, decks, stairs, sheds, a lean-to, a
  coop, beds, frames, bins, shelving, a bookshelf, tables, racks), kept
  as a plan when asked.
- `cut_list`: the person's own parts, said plainly (`parse_parts()`),
  worked out into boards and sheets.
- `plan_shopping_list`: a plan's materials against the workshop's stock.
- `forget_plan`: lets a kept plan go (the plan page's `plan.delete`).
- `plan_sources`, `keep_plan`, `start_plan_project`.

Tools travel in three domains: `plans` for asking, `plan_buying` only on
buying words, and `plan_saving` (keep a plan, start a project) only when
the person says to, so a question never saves anything.
"""

from __future__ import annotations

import re
from typing import Optional

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.plan_library import KINDS, OLD_PLAN_NOTE, SOURCES, calculate, shopping_list

DOMAIN = "plans"
BUYING = "plan_buying"  # the shopping list's own domain (see register_plan_actions)
SAVING = "plan_saving"  # keeping a plan and starting a project: only when the person says so

# Words a person uses for a structure -> the calculator that works it out.
STRUCTURES = (  # in order: "deck stairs" is stairs, "bookshelf" isn't shelving, "woodshed" is a lean-to
    (("raised bed", "garden bed", "planter", "raised garden"), "raised_bed"),
    (("cold frame", "coldframe", "hot box"), "cold_frame"),
    (("compost",), "compost_bin"),
    (("chicken coop", "coop", "hen house", "henhouse", "chicken house"), "chicken_coop"),
    (("bookshelf", "bookcase", "book shelf"), "bookshelf"),
    (("shelving", "shelves", "shelf", "storage rack"), "shelving"),
    (("picnic table",), "picnic_table"),
    (("workbench", "work bench", "bench"), "workbench"),
    (("firewood", "wood rack", "log rack"), "firewood_rack"),
    (("lean-to", "lean to", "shelter", "carport", "woodshed", "wood shed", "run-in"), "lean_to"),
    (("stairs", "steps", "stair", "stringer"), "stairs"),
    (("stud wall", "wall", "partition"), "stud_wall"),
    (("deck",), "deck"),
    (("floor", "platform", "subfloor"), "floor"),
    (("fence",), "fence"),
    (("slab", "concrete pad", "pad", "patio"), "slab"),
    (("shed", "shop building", "outbuilding"), "shed"),
)
UPRIGHT = ("shelving", "bookshelf", "firewood_rack")  # a size said for these is width (or length) by height


def structure_for(words: str) -> str:
    """Pure logic. The calculator a structure's name means; "" for one MIA can't work out."""
    text = (words or "").lower()
    return next((calc for names, calc in STRUCTURES if any(n in text for n in names)), "")


def _number(value) -> Optional[float]:
    """Pure logic. A number from a tool argument ("12", 12, "12 ft"); None when there isn't one, or it's 0 (a small
    model fills sizes it wasn't given with 0)."""
    found = re.search(r"\d+(\.\d+)?", str(value if value is not None else ""))
    number = float(found.group()) if found else None
    return number if number else None


def _yes(value) -> bool:
    """Pure logic. A true/false tool argument, which a small model may send as the string "false"."""
    return str(value).strip().lower() in ("true", "1", "yes")


def size_words(text: str) -> tuple:
    """Pure logic. The numbers in a size as said ("10 by 12", "4x8x2", "8' x 10'"), in order: width, length, then
    height."""
    return tuple(float(n) for n in re.findall(r"\d+(?:\.\d+)?", text or "") if float(n))


def sizes_for(calc: str, arguments: dict) -> dict:
    """Pure logic. The calculator's arguments from what the tool was given: a size as said, which wins ("10 by 12":
    width, length, then height; for shelving, a bookshelf or a firewood rack, width by height; one number alone is
    the length), else length, width, height in feet or inches; and thickness, gates, a count (hens, shelves, bays),
    depth and the rise of stairs. Only the ones given."""
    length, width = _number(arguments.get("length_ft")), _number(arguments.get("width_ft"))
    height_ft, height_in = _number(arguments.get("height_ft")), _number(arguments.get("height_in"))
    said = size_words(str(arguments.get("size") or ""))
    if len(said) == 1:
        length = said[0]
    elif len(said) >= 2 and calc in UPRIGHT:
        width, length, height_ft, height_in = said[0], said[0], said[1], None
    elif len(said) >= 2:
        width, length = said[0], said[1]
        if len(said) >= 3:
            height_ft, height_in = said[2], None
    if height_in is None and height_ft is not None and calc == "raised_bed":
        height_in = height_ft * 12
    if height_ft is None and height_in is not None and calc != "raised_bed":
        height_ft = height_in / 12
    count, depth_in = _number(arguments.get("count")), _number(arguments.get("depth_in"))

    def inches_of(feet):
        """A bookshelf's sizes are in inches: a number up to 12 was said in feet."""
        return None if feet is None else feet if feet > 12 else feet * 12

    table = {
        "shed": {"width_ft": width, "length_ft": length, "wall_height_ft": height_ft},
        "deck": {"span_ft": width, "length_ft": length},
        "floor": {"span_ft": width, "length_ft": length},
        "fence": {"length_ft": length, "height_ft": height_ft, "gates": _number(arguments.get("gates"))},
        "slab": {"length_ft": length, "width_ft": width, "thickness_in": _number(arguments.get("thickness_in"))},
        "raised_bed": {"length_ft": length, "width_ft": width, "height_in": height_in},
        "stud_wall": {"length_ft": length, "height_ft": height_ft},
        "workbench": {},
        "chicken_coop": {"width_ft": width, "length_ft": length, "hens": count, "height_ft": height_ft},
        "shelving": {"width_ft": width or length, "height_ft": height_ft, "depth_in": depth_in, "shelves": count},
        "bookshelf": {"width_in": inches_of(width or length), "height_in": inches_of(height_ft), "depth_in": depth_in,
                      "shelves": count},
        "lean_to": {"depth_ft": width, "length_ft": length, "high_ft": height_ft},
        "compost_bin": {"bays": count, "size_ft": width, "height_ft": height_ft},
        "cold_frame": {"width_ft": width, "length_ft": length},
        "picnic_table": {"length_ft": length},
        "firewood_rack": {"length_ft": length or width, "height_ft": height_ft, "depth_in": depth_in},
        "stairs": {"rise_in": _number(arguments.get("rise_in")) or _number(arguments.get("height_in"))
                   or (height_ft * 12 if height_ft else None), "width_in": inches_of(width)},
    }.get(calc, {})
    out = {k: v for k, v in table.items() if v is not None}
    for whole in ("gates", "hens", "shelves", "bays"):
        if whole in out:
            out[whole] = int(out[whole])
    return out


# ------------------------------------------------------------------ a cut list of the person's own parts

_SHEET = re.compile(r"(?:\d/\d+\s*(?:in(?:ch)?\s*)?)?(?:plywood|ply|mdf|osb|hardboard|melamine|particleboard|"
                    r"polycarbonate)", re.I)
_LUMBER = re.compile(r"\b[1-6]x\d{1,2}\b", re.I)
_DIM = r"(\d+(?:\.\d+)?(?:\s+\d+/\d+)?|\d+/\d+)\s*(ft|feet|foot|'|in|inches|inch|\")?"
_DIMS = re.compile(_DIM + r"(?:\s*(?:x|by|×)\s*" + _DIM + r")?", re.I)
_FILLER = {"at", "of", "from", "pieces", "piece", "x", "by", "in", "ft", "cut", "and", "the", "a", "an", "long",
           "wide", "each", "@"}


def _length(number: str, unit: str) -> float:
    """Pure logic. A measurement in inches: "30", "30 1/2", "3/4", in feet when its unit says so."""
    parts = number.split()
    value = 0.0
    for part in parts:
        if "/" in part:
            top, bottom = part.split("/")
            value += float(top) / float(bottom)
        else:
            value += float(part)
    return value * 12 if (unit or "").lower() in ("ft", "feet", "foot", "'") else value


def parse_parts(text: str) -> list[dict]:
    """Pure logic. Parts as a person lists them, one per line or semicolon: "4 legs at 30 in 2x4", "2 sides 11 1/4 x
    72 in 3/4 plywood", "6 slats 3 ft 1x4". Each: how many, its name, its length in inches (and width, for sheet
    goods), and its material (2x4 when none is said). A line without a size is skipped."""
    parts = []
    for line in re.split(r"[\n;]+", text or ""):
        line = line.strip(" -*\t")
        sheet = _SHEET.search(line)
        lumber = _LUMBER.search(line)
        material = (sheet or lumber).group().lower() if (sheet or lumber) else "2x4"
        rest = line.replace((sheet or lumber).group(), " ") if (sheet or lumber) else line
        qty_found = re.match(r"\s*(\d+)\b(?!\s*/)", rest)
        qty = int(qty_found.group(1)) if qty_found else 1
        rest = rest[qty_found.end():] if qty_found else rest
        dims = _DIMS.search(rest)
        if not dims:
            continue
        unit = dims.group(2) or dims.group(4) or ""
        first = _length(dims.group(1), dims.group(2) or unit)
        second = _length(dims.group(3), dims.group(4) or unit) if dims.group(3) else None
        name = " ".join(w for w in re.findall(r"[a-zA-Z]+", rest[:dims.start()] + " " + rest[dims.end():])
                        if w.lower() not in _FILLER)
        part = {"name": name or "part", "qty": qty, "material": material}
        if sheet and second:
            part["width_in"], part["length_in"] = min(first, second), max(first, second)
        else:
            part["length_in"] = max(first, second or 0)
        parts.append(part)
    return parts


def _library(context):
    """The household's plans."""
    return getattr(context, "plans", None)


def _where(plan: dict) -> str:
    """Pure logic. Where a plan comes from, in a few words."""
    if plan["id"].startswith("builtin:"):
        return "built in, any size"
    if plan["id"].startswith("file:"):
        return "your file"
    return "kept by the household"


def _action_find_plans(context, arguments: dict) -> str:
    """Tool find_plans: plans on the shelf matching the words, each with what it is and where it's from; with none,
    what MIA can work out and where free plans are."""
    library = _library(context)
    if library is None:
        return "The plans shelf isn't on this device."
    query = str(arguments.get("query") or "")
    found = library.find(query)
    if not found:
        calc = structure_for(query)
        lines = [f"No plans for \"{query}\" on the shelf yet."]
        if calc:
            lines.append("I can work out the materials for one at your size: tell me the size.")
        lines.append("Free plans to fetch: " + "; ".join(f"{s['name']} ({s['url']})" for s in SOURCES[:4]) + ".")
        return " ".join(lines)
    return "Plans: " + "; ".join(f"{p['title']}: {p.get('summary', '')} ({_where(p)})" for p in found) + "."


def _action_show_plan(context, arguments: dict) -> str:
    """Tool show_plan: one plan's materials, cuts, tools, steps (or all of them), or where its file is."""
    library = _library(context)
    plan = library.best(str(arguments.get("name") or "")) if library is not None else None
    if plan is None:
        return "I couldn't find that plan. Ask me to find plans, or tell me what you want to build and its size."
    if plan["id"].startswith("file:"):
        return f"{plan['title']} is a file: {plan['path']}. Open it from the Library."
    part = str(arguments.get("part") or "all").lower()
    sizes = sizes_for(plan.get("calc", ""), arguments)
    worked = library.worked_out(plan, **sizes) if sizes else None
    materials = worked.as_dict() if worked is not None else plan.get("materials") or {}
    lines = [f"{plan['title']} ({_where(plan)})" + (f": {plan['summary']}" if plan.get("summary") else "")]
    if part in ("all", "materials", "cuts", "cut list"):
        lines.append(_materials_text(materials, cuts=part != "materials"))
    if part in ("all", "tools") and plan.get("tools"):
        lines.append("Tools: " + ", ".join(plan["tools"]) + ".")
    if part in ("all", "steps") and plan.get("steps"):
        lines.append("Steps:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(plan["steps"], 1)))
    if plan.get("source", {}).get("url"):
        lines.append(f"From {plan['source']['name']} ({plan['source']['url']}). {OLD_PLAN_NOTE}")
    return "\n".join(lines)


def _materials_text(materials: dict, cuts: bool = True) -> str:
    """Pure logic. A material list as lines: what to buy, the cuts when asked, and its notes."""
    if not materials.get("items"):
        return "No material list with this one."
    lines = [(materials.get("title") or "Materials") + ":"]
    lines += [f"- {_qty(i['qty'])} {i['unit'] + ' ' if i.get('unit') else ''}{i['name']}"
              + (f" ({i['note']})" if i.get("note") else "") for i in materials["items"]]
    if cuts and materials.get("cuts"):
        from core.build_calcs import inches

        lines.append("Cuts:")
        lines += [f"- {c['qty']} x {c['part']} at {inches(c['length_in'])}" for c in materials["cuts"]]
    lines += [f"Note: {n}" for n in materials.get("notes", [])]
    return "\n".join(lines)


def _qty(value) -> str:
    """Pure logic. A quantity without a needless .0."""
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _action_material_list(context, arguments: dict) -> str:
    """Tool material_list: what a structure needs at a size, worked out in code; kept as a plan when asked. A list of
    the person's own parts goes to cut_list instead. One she can't work out yet goes in the Fix-It Log, where it
    becomes a capability gap."""
    if str(arguments.get("parts") or "").strip():  # a list of their own parts is a cut list, whatever it's called
        return _action_cut_list(context, {**arguments, "title": arguments.get("title") or arguments.get("structure")})
    structure = str(arguments.get("structure") or "")
    calc = structure_for(structure)
    if not calc:
        book = getattr(context, "failures", None)  # a structure she can't work out yet becomes a capability gap
        if book is not None and structure.strip():
            book.record("no_tool", prompt=f"material list for {structure.strip()}", tool="material_list")
        return ("I can work out materials for a stud wall, floor, deck, deck stairs, raised bed, cold frame, compost bin, chicken coop, fence, concrete slab, gable shed, lean-to, garage shelving, bookshelf, workbench, picnic table or firewood rack, or a cut list of your own parts. Which, and what size?")
    sizes = sizes_for(calc, arguments)
    try:
        result = calculate(calc, **sizes)
    except TypeError:
        return "What size? Give me the length and width (and height where it matters) in feet."
    said = result.to_text()
    if _yes(arguments.get("keep")):
        library = _library(context)
        if library is not None:
            kind = {"raised_bed": "garden", "fence": "fencing", "slab": "concrete", "workbench": "woodworking"}.get(
                calc, "structure")
            library.keep(result.title[:1].upper() + result.title[1:], kind, "Worked out by MIA for your size.",
                         result.as_dict(), calc=calc, args=sizes)
            said += "\nKept on the plans shelf."
    return said


def _action_shopping_list(context, arguments: dict) -> str:
    """Tool plan_shopping_list: a plan's materials (at a size, when given) against the workshop's stock: what's on
    hand, what to buy, and its cost where prices are known."""
    from core.region import money

    library = _library(context)
    plan = library.best(str(arguments.get("name") or "")) if library is not None else None
    if plan is None:
        return "Which plan? Ask me to find plans first."
    sizes = sizes_for(plan.get("calc", ""), arguments)
    worked = library.worked_out(plan, **sizes) if sizes else None
    materials = worked.as_dict() if worked is not None else plan.get("materials") or {}
    if not materials.get("items"):
        return f"{plan['title']} has no material list to check."
    found = shopping_list(context, materials)
    if not found["to_buy"]:
        return f"You have everything on hand for {plan['title']}."
    lines = [f"To buy for {materials.get('title') or plan['title']}:"]
    for row in found["to_buy"]:
        have = f" (you have {_qty(row['have'])})" if row["have"] else ""
        cost = f", about {money(row['cost'])}" if row.get("cost") else ""
        lines.append(f"- {_qty(row['buy'])} {row['unit'] + ' ' if row['unit'] else ''}{row['item']}{have}{cost}")
    if found["priced"]:
        lines.append(f"Known cost: about {money(found['known_cost'])} for the {found['priced']} items with prices in "
                     "your materials.")
    else:
        lines.append("No prices yet: add materials with their unit costs and I'll total it.")
    return "\n".join(lines)


def _action_cut_list(context, arguments: dict) -> str:
    """Tool cut_list: the person's own parts worked out into boards and sheets to buy (core/build_calcs.custom_cuts);
    kept as a woodworking plan when asked."""
    from core.build_calcs import custom_cuts

    parts = parse_parts(str(arguments.get("parts") or ""))
    if not parts:
        return ("List the parts with their sizes, one per line: \"4 legs at 30 in 2x4\", \"2 sides 11 1/4 x 72 in "
                "3/4 plywood\".")
    title = " ".join(str(arguments.get("title") or "your project").split())[:80]
    result = custom_cuts(parts, title)
    said = result.to_text()
    library = _library(context)
    if _yes(arguments.get("keep")) and library is not None:
        library.keep(title[:1].upper() + title[1:], "woodworking", "A cut list of your own parts.", result.as_dict())
        said += "\nKept on the plans shelf."
    return said


def _action_sources(context, arguments: dict) -> str:
    """Tool plan_sources: where free plans and references are, to fetch while online."""
    kind = str(arguments.get("kind") or "").lower()
    chosen = [s for s in SOURCES if not kind or s["kind"] == kind] or list(SOURCES)
    return ("Free plans and references: " + "; ".join(f"{s['name']}: {s['what']} ({s['url']})" for s in chosen)
            + f". Save the files into the Library's plans folder and I'll find them. {OLD_PLAN_NOTE}")


def _parse_items(text: str) -> list[dict]:
    """Pure logic. Materials as said ("12 2x4 x 8 ft, 3 sheets plywood"), one per line or comma: a leading number
    is the quantity."""
    items = []
    for part in re.split(r"[\n;,]+", text or ""):
        part = part.strip(" -*\t")
        if not part:
            continue
        found = re.match(r"^(\d+(?:\.\d+)?)\s+(.*)$", part)
        items.append({"name": found.group(2) if found else part, "qty": float(found.group(1)) if found else 1,
                      "unit": "", "note": ""})
    return items


def _action_keep_plan(context, arguments: dict) -> str:
    """Tool keep_plan: keeps a plan the person describes (its kind, what it is, materials, steps, where it's from)."""
    library = _library(context)
    title = str(arguments.get("title") or "").strip()
    if library is None or not title:
        return "What's the plan called?"
    items = _parse_items(str(arguments.get("materials") or ""))
    steps = [s.strip() for s in re.split(r"\n+|(?<=\.)\s+(?=\d+\.)", str(arguments.get("steps") or "")) if s.strip()]
    source = {"name": str(arguments.get("source") or "the household")}
    kind = str(arguments.get("kind") or "other").lower()
    plan = library.keep(title, kind if kind in KINDS else "other", str(arguments.get("summary") or ""),
                        {"title": title, "items": items, "cuts": [], "notes": []} if items else {},
                        steps=steps, source=source)
    return f"Kept \"{plan['title']}\" on the plans shelf" + (f" with {len(items)} materials" if items else "") + "."


def _action_start_project(context, arguments: dict) -> str:
    """Tool start_plan_project: starts a project from a plan, its materials and steps in the description."""
    library, projects = _library(context), getattr(context, "projects", None)
    plan = library.best(str(arguments.get("name") or "")) if library is not None else None
    if plan is None or projects is None:
        return "Which plan? Ask me to find plans first."
    sizes = sizes_for(plan.get("calc", ""), arguments)
    worked = library.worked_out(plan, **sizes) if sizes else None
    materials = worked.as_dict() if worked is not None else plan.get("materials") or {}
    title = materials.get("title") or plan["title"]
    description = f"From the plan \"{plan['title']}\" (plan:{plan['id']}).\n" + _materials_text(materials)
    if plan.get("steps"):
        description += "\nSteps:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(plan["steps"], 1))
    project = projects.add_project(name=title[:1].upper() + title[1:], description=description)
    return f"Started the project \"{project.name}\" with the plan's materials and steps."


def _action_forget_plan(context, arguments: dict) -> str:
    """Tool forget_plan: lets a kept plan go by its name (the `plan.delete` action, so "undo that" brings it back);
    built-in plans and files stay."""
    from core.actions import ACTION_TYPES, ActionError

    library = _library(context)
    words = str(arguments.get("name") or "")
    kept = [p for p in library.find(words, limit=60) if p["id"] in library.plans] if library is not None else []
    if not kept:
        return "I don't have a kept plan by that name. Built-in plans and files stay on the shelf."
    params = {"plan_id": kept[0]["id"]}
    try:
        ACTION_TYPES["plan.delete"].describe(context, params)
        return ACTION_TYPES["plan.delete"].execute(context, params)
    except ActionError as problem:
        return str(problem)


def register_plan_actions(registry: AssistantActionRegistry) -> None:
    """Registers the plans shelf's tools: asking in domain plans, the shopping list in plan_buying, and keeping a plan,
    starting a project or letting a kept plan go in plan_saving (each domain brought only by its own words)."""
    sizes = {"size": {"type": "string", "description": "The size as they said it, e.g. '10 by 12' or '4x8x2' (feet)."},
             "length_ft": {"type": "number", "description": "Length in feet."},
             "width_ft": {"type": "number", "description": "Width in feet (a deck or floor: the joist span)."},
             "height_ft": {"type": "number", "description": "Height in feet (walls, fences, a shed's walls)."},
             "height_in": {"type": "number", "description": "Height in inches (a raised bed)."},
             "thickness_in": {"type": "number", "description": "A slab's thickness in inches."},
             "gates": {"type": "integer", "description": "A fence's gates."},
             "count": {"type": "integer", "description": "Hens in a coop, shelves, or compost bays."},
             "depth_in": {"type": "number", "description": "Depth in inches (shelves, a firewood rack)."},
             "rise_in": {"type": "number", "description": "Stairs: the height to climb, in inches."}}
    name = {"name": {"type": "string", "description": "The plan's name, as found by find_plans."}}
    registry.register_domain_keywords(DOMAIN, (
        "blueprint", "blueprints", "cut list", "material list", "materials list", "lumber", "2x4",
        "2x4s", "studs", "joists", "rafters", "plywood", "woodworking", "shed", "deck", "fence", "raised bed", "slab",
        "workbench", "coop", "barn", "chicken coop", "hen house", "compost bin", "cold frame", "bookshelf",
        "bookcase", "shelving", "lean-to", "picnic table", "firewood rack", "deck stairs",
        "stair stringers", "build stairs", "potting bench", "planter box", "cut list"))
    tools = (
        ("find_plans", "Find plans in MIA's Library (woodworking plans, structure blueprints, material lists, the "
                       "household's own and files they saved).", {"query": {"type": "string", "description":
                       "What the plan is for, e.g. 'chicken coop', 'shed', 'bookshelf'."}}, ["query"],
         _action_find_plans, ("plans for", "blueprint for", "blueprints for", "do we have plans", "find a plan",
                              "woodworking plans", "building plans", "any plans")),
        ("show_plan", "Show one plan: its materials, cut list, tools or steps, optionally at a different size.",
         {**name, "part": {"type": "string", "description": "all, materials, cuts, tools or steps."}, **sizes},
         ["name"], _action_show_plan, ("show me the plan", "the cut list", "steps for the", "show the plan")),
        ("material_list", "Work out the materials and cuts for a project at a size: a stud wall, floor, deck, deck stairs, raised bed, cold frame, compost bin, chicken coop, fence, concrete slab, gable shed, lean-to, garage shelving, bookshelf, workbench, picnic table or firewood rack. "
                          "keep=true saves it as a plan.",
         {"structure": {"type": "string", "description": "What to build, e.g. 'shed', 'raised bed', 'fence'."},
          **sizes, "keep": {"type": "boolean", "description": "Save it to the plans shelf."}}, ["structure"],
         _action_material_list, ("material list", "materials list", "materials for", "what do i need to build",
                                 "how much lumber", "how many 2x4", "how many studs", "cut list", "how much concrete",
                                 "how many bags of concrete", "how many pickets", "what would it take to build")),
        ("plan_shopping_list", "What's still to buy for a plan already on the shelf, by its name: its materials "
                               "against what the workshop has on hand, with costs. For 'what do I need to build X', "
                               "use material_list instead.", {**name, **sizes}, ["name"], _action_shopping_list,
         ("what do i need to buy for", "shopping list for the", "what do i still need for", "what's left to buy")),
        ("cut_list", "A cut list for the person's own project: the parts they list (how many, name, size, material: "
                     "'4 legs at 30 in 2x4; 2 sides 11 1/4 x 72 in 3/4 plywood'), worked out into boards and sheets "
                     "to buy.", {"parts": {"type": "string", "description": "The parts, one per line or semicolon."},
                                 "title": {"type": "string", "description": "What the project is."},
                                 "keep": {"type": "boolean", "description": "Save it to the plans shelf."}},
         ["parts"], _action_cut_list, ("cut list for my", "how many boards for", "how many sheets of plywood",
                                       "optimize my cuts", "what lumber for these parts", "my own design")),
        ("plan_sources", "Where to get free plans and building references (extension services, public-domain "
                         "handbooks, offline packs).", {"kind": {"type": "string", "description":
                         "homestead, structure, woodworking or other (optional)."}}, [], _action_sources,
         ("where can i get plans", "free plans", "where to find plans", "free blueprints")),
        ("keep_plan", "Keep a plan the person describes on the plans shelf: its title, kind, summary, materials (one "
                      "per line or comma, a number first), steps and source.",
         {"title": {"type": "string"}, "kind": {"type": "string", "description": ", ".join(KINDS)},
          "summary": {"type": "string"}, "materials": {"type": "string"}, "steps": {"type": "string"},
          "source": {"type": "string", "description": "Where it came from."}}, ["title"], _action_keep_plan,
         ("save this plan", "keep this plan", "add a plan", "save a plan")),
        ("start_plan_project", "Start a project from a plan, with its materials and steps.", {**name, **sizes},
         ["name"], _action_start_project, ("start the project", "make it a project", "start a project from")),
        ("forget_plan", "Let a plan the household kept go from the plans shelf (built-in plans and files stay).",
         name, ["name"], _action_forget_plan, ("delete the plan", "remove the plan", "forget the plan",
                                               "let the plan go")),
    )
    # The shopping list travels apart: only buying words bring it, so "what do I need to build" reaches material_list.
    registry.register_domain_keywords(BUYING, ("shopping list", "still need", "left to buy", "need to buy"))
    # So do the tools that save something: a question about building never starts a project by itself.
    registry.register_domain_keywords(SAVING, ("as a project", "a project from", "start the project", "save this plan", "keep this plan", "add a plan",
                                               "save a plan", "save the plan", "keep the plan", "delete the plan",
                                               "remove the plan", "forget the plan"))
    homes = {"plan_shopping_list": BUYING, "keep_plan": SAVING, "start_plan_project": SAVING, "forget_plan": SAVING}
    for tool_name, description, props, required, handler, phrases in tools:
        registry.register(AssistantAction(
            name=tool_name, domain=homes.get(tool_name, DOMAIN), description=description,
            parameters={"type": "object", "properties": props, "required": required},
            handler=handler, trigger_phrases=phrases))
