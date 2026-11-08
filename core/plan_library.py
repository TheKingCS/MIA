"""
core.plan_library
===================

The Library's plans shelf (Zac, 2026-11-07: "references for all kinds of
stuff like woodworking plans, structure blueprints, material lists").
Three kinds of plan, found together by `find()`:

- **Built in**: plans MIA works out in code (core/build_calcs.py) with
  their steps: a raised bed, a gable shed, a deck frame, a privacy fence,
  a shed slab, a workbench. Any size: `worked_out()` reruns the
  calculator for the person's own size.
- **Kept**: plans the household saves (a list worked out for their size,
  or one they describe: its materials, cuts, tools, steps and where it
  came from), in `plans.json`, a household store.
- **Files**: plans, blueprints and drawings dropped into the library's
  `plans/` folder (PDFs, images, CAD and SketchUp files), listed by
  file name and the folders they sit in (`plans/woodworking/...`).

`detail()` is one plan for the Library page: at a size of the person's own
(`size_fields`, `read_sizes`), with its shopping list. Keeping it, starting
a project from it and letting a kept one go are actions
(core/plan_actions.py).

`shopping_list()` checks a plan's materials against the workshop's
materials (core/material_manager.py): what's on hand, what to buy, and
what it costs where the price is known. `SOURCES` lists where free plans
are (public-domain and extension plans), to fetch while online.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import build_calcs, life_events
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "plans.json"
PLAN_FILES = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".dwg", ".dxf", ".skp", ".txt", ".md")
KINDS = ("woodworking", "structure", "garden", "fencing", "concrete", "homestead", "metalwork", "other")

# Where free plans are, to fetch while online (checked 2026-11-07). Old plans predate today's codes: say so.
SOURCES = (
    {"name": "University of Tennessee Extension plan file", "kind": "homestead",
     "url": "https://trace.tennessee.edu/utk_agexfarmbld/",
     "what": "300+ farm building and equipment plans, public domain (don't alter or sell them)"},
    {"name": "University of Arkansas farm plans", "kind": "homestead",
     "url": "https://www.uaex.uada.edu/farm-ranch/resource-library/plans/default.aspx",
     "what": "farm building plans; older designs, a starting point rather than a permit set"},
    {"name": "University of Vermont farm building and equipment plans", "kind": "homestead",
     "url": "https://www.uvm.edu/vtvegandberry/buildingplans.html",
     "what": "links to free plans for farm buildings, coolers, wash stations and equipment"},
    {"name": "Canada Plan Service archive (CSBE)", "kind": "structure",
     "url": "https://www.csbe-scgab.ca/images/cps/Plan-Index-EN.pdf",
     "what": "the index of archived Canadian farm building plans, for reference (no engineering support)"},
    {"name": "Wood Handbook, 2021 (USDA Forest Products Laboratory)", "kind": "woodworking",
     "url": "https://purl.fdlp.gov/GPO/gpo158673",
     "what": "wood as an engineering material: species, strength, drying, fasteners, finishing; public domain"},
    {"name": "Kiwix library", "kind": "other", "url": "https://library.kiwix.org",
     "what": "offline packs for the Library (wikiHow, iFixit, Appropedia and more), installed as .zim files"},
)
OLD_PLAN_NOTE = "Older plans predate today's codes: check them against your local code before building."

_MANUAL = "MIA (worked out in code)"


def _workbench() -> build_calcs.MaterialList:
    """A 6 ft x 2 ft workbench, 36 in tall: a 2x4 top frame and shelf frame on four 2x4 legs, a 3/4 in plywood top
    and shelf from one sheet."""
    out = build_calcs.MaterialList("6 x 2 ft workbench, 36 in tall", {"length_in": 72, "depth_in": 24, "height_in": 36})
    cuts = [("rail", 4, 72), ("cross piece", 6, 21), ("leg", 4, 35.25)]
    length, boards = build_calcs.buy_boards([inches for _p, qty, inches in cuts for _ in range(qty)])
    out.add(f"2x4 x {length} ft", boards)
    out.cuts += [build_calcs.Cut(part, qty, inches, f"2x4 x {length} ft") for part, qty, inches in cuts]
    out.add("3/4 in plywood 4x8", 1, "sheet", "top and shelf, 24 x 72 in each")
    out.cuts += [build_calcs.Cut("top", 1, 72, "3/4 in plywood, 24 in wide"),
                 build_calcs.Cut("shelf", 1, 72, "3/4 in plywood, 24 in wide, notched at the legs")]
    out.add("3 in wood screws", 50)
    out.add("1 1/4 in wood screws", 40, "", "for the plywood")
    out.add("wood glue", 1, "bottle")
    return out


# Built-in plans: what each is, the calculator and size it starts from, the tools, and the steps.
BUILT_IN = (
    {"id": "raised-bed", "title": "Raised garden bed", "kind": "garden", "calc": "raised_bed",
     "args": {"length_ft": 8, "width_ft": 4, "height_in": 11},
     "summary": "A two-board-tall bed of 2x6s with 4x4 corner posts; any size.",
     "tools": ["saw", "drill/driver", "tape measure", "square", "level"],
     "steps": ["Cut the sides, ends and corner posts.", "Screw each course's ends between the sides to the posts.",
               "Set it level where it gets 6+ hours of sun; line the bottom with cardboard.",
               "Fill with a soil and compost mix and water it in."]},
    {"id": "gable-shed", "title": "Gable shed", "kind": "structure", "calc": "shed",
     "args": {"width_ft": 8, "length_ft": 10},
     "summary": "A floor on joists, four stud walls with a door, a 4-in-12 gable roof with shingles; any size.",
     "tools": ["circular saw", "framing square", "speed square", "hammer or nailer", "drill/driver", "level",
               "chalk line", "ladder"],
     "steps": ["Level a base: gravel pad, concrete blocks or skids.", "Build the floor frame square (equal diagonals), "
               "then glue and nail the subfloor.", "Frame the walls flat on the floor, raise them, plumb, brace and "
               "nail the corners and top plates together.", "Cut one pair of rafters as a pattern, test it, then cut "
               "the rest; set the ridge and rafters with ties.", "Sheath the roof, add drip edge, underlayment and "
               "shingles.", "Side the walls, frame the gables, hang the door, trim and paint."]},
    {"id": "deck-frame", "title": "Ground-level deck", "kind": "structure", "calc": "deck",
     "args": {"span_ft": 12, "length_ft": 16},
     "summary": "Joists hung between rim joists with 5/4 deck boards; any size (a beam is added past 18 ft).",
     "tools": ["circular saw", "drill/driver", "post hole digger", "level", "string line", "square"],
     "steps": ["Lay out the corners and square them (3-4-5), then set footings below frost depth.",
               "Set the beams or ledger and rim joists level.", "Hang joists at 16 in on center, crown up.",
               "Lay deck boards with a 1/8 in gap, two screws per joist; trim the ends straight."]},
    {"id": "privacy-fence", "title": "Wood privacy fence", "kind": "fencing", "calc": "fence",
     "args": {"length_ft": 100, "height_ft": 6, "gates": 1},
     "summary": "4x4 posts in concrete every 8 ft, three 2x4 rails, pickets; any length.",
     "tools": ["post hole digger", "level", "string line", "circular saw", "drill/driver", "wheelbarrow"],
     "steps": ["Call your dig line and mark the property line.", "Set the corner and end posts in concrete, plumb, "
               "then run a string and set the line posts.", "Let the concrete cure a day; attach rails level.",
               "Attach pickets with a spacer and a level every few boards; hang the gate."]},
    {"id": "shed-slab", "title": "Concrete slab", "kind": "concrete", "calc": "slab",
     "args": {"length_ft": 10, "width_ft": 12, "thickness_in": 4},
     "summary": "A 4 in slab on a gravel base with rebar; any size.",
     "tools": ["shovel", "plate compactor", "level", "wheelbarrow or mixer", "screed board", "bull float", "edger"],
     "steps": ["Dig out, set forms level (or sloped 1/8 in per ft), compact a 4 in gravel base.",
               "Tie rebar on chairs at mid-depth.", "Pour, screed, float; edge and joint it.",
               "Keep it damp for a week while it cures."]},
    {"id": "chicken-coop", "title": "Chicken coop and run", "kind": "homestead", "calc": "chicken_coop",
     "args": {"hens": 8},
     "summary": "A shed-roof coop at 4 sq ft a hen with roosts, nest boxes and vents, and a hardware-cloth run; "
                "any flock size.",
     "tools": ["circular saw", "drill/driver", "post hole digger", "level", "tin snips", "staple gun"],
     "steps": ["Pick high, dry ground; level a base of blocks or gravel.", "Build the floor, then frame the walls "
               "(the back 1 ft lower for the roof's fall) with the door and pop-door openings.",
               "Set rafters, screw on the metal roof, side the walls, cover vents with hardware cloth.",
               "Fit roosts (higher than the nest boxes) and nest boxes; hang doors with two-step latches.",
               "Set the run posts, rails, and hardware cloth with a 12 in apron buried or pinned flat."]},
    {"id": "garage-shelving", "title": "Garage shelving", "kind": "woodworking", "calc": "shelving",
     "args": {"width_ft": 8, "depth_in": 24, "height_ft": 6, "shelves": 4},
     "summary": "Heavy 2x4-and-plywood shelves for totes and tools; any width, depth and count.",
     "tools": ["circular saw", "drill/driver", "square", "level", "clamps"],
     "steps": ["Build each shelf frame: two rails with cross pieces every 24 in.", "Screw the legs to the lowest and "
               "top frames on the floor, stand it up, then fit the middle frames level.", "Rip and screw down the "
               "plywood.", "Screw the top frame to the wall studs."]},
    {"id": "bookshelf", "title": "Solid-wood bookshelf", "kind": "woodworking", "calc": "bookshelf",
     "args": {"width_in": 36, "height_in": 72},
     "summary": "Sides, fixed shelves about every 12 in, a plywood back and a toe kick; any size.",
     "tools": ["miter or circular saw", "drill/driver", "pocket-hole jig", "clamps", "square", "sander"],
     "steps": ["Cut the sides and shelves; sand to 150 grit.", "Mark shelf positions on both sides together so "
               "they match.", "Glue and pocket-screw the shelves between the sides, checking square.",
               "Fit the toe kick, nail on the back (it squares the case), finish, and strap it to a wall."]},
    {"id": "lean-to", "title": "Lean-to shelter", "kind": "structure", "calc": "lean_to",
     "args": {"depth_ft": 8, "length_ft": 12},
     "summary": "A post-frame shelter with a metal roof for firewood, equipment or animals; any size.",
     "tools": ["post hole digger", "circular saw", "drill/driver", "level", "string line", "ladder"],
     "steps": ["Lay out and square the post holes; set the posts in concrete, plumb.", "Cut posts to the high and "
               "low heights; bolt the doubled headers on.", "Set rafters with ties, then purlins across them.",
               "Screw on the metal panels, overlapping one rib, screws in the flats or as the maker says."]},
    {"id": "compost-bin", "title": "Three-bay compost bin", "kind": "garden", "calc": "compost_bin",
     "args": {"bays": 3, "size_ft": 3},
     "summary": "Slatted bays with air gaps and lift-out fronts, so a pile turns from one bay to the next.",
     "tools": ["saw", "drill/driver", "level", "spacer block"],
     "steps": ["Set the posts level on the ground or on pavers.", "Screw the back and divider slats on with a 1 in "
               "spacer between.", "Screw 1x2 guides to the front posts so the front slats slide in.",
               "Fill bay one; turn it into bay two when it heats and settles."]},
    {"id": "cold-frame", "title": "Cold frame", "kind": "garden", "calc": "cold_frame",
     "args": {"width_ft": 3, "length_ft": 6},
     "summary": "A sloped box with a polycarbonate lid to start seedlings early and grow late; any size.",
     "tools": ["saw", "drill/driver", "square"],
     "steps": ["Cut the side boards to the slope from back height to front height.", "Screw the boards to the "
               "corner posts.", "Build the lid frame, screw on the polycarbonate, and hinge it at the back.",
               "Set it facing the sun; prop it open on warm days."]},
    {"id": "picnic-table", "title": "Picnic table", "kind": "woodworking", "calc": "picnic_table",
     "args": {"length_ft": 8},
     "summary": "The classic A-frame table with attached benches.",
     "tools": ["miter saw", "drill/driver", "speed square", "wrench", "clamps"],
     "steps": ["Cut the legs at 22 1/2 deg both ends; cut the seat supports and cleats.", "Bolt each pair of legs "
               "to a top cleat and a seat support (an A).", "Screw the top boards across the two A-frames, then "
               "the seat boards.", "Add the angled braces from the seat supports to the center cleat."]},
    {"id": "firewood-rack", "title": "Firewood rack", "kind": "homestead", "calc": "firewood_rack",
     "args": {"length_ft": 8, "height_ft": 4},
     "summary": "A rack that keeps a third of a cord off the ground and drying; any size.",
     "tools": ["saw", "drill/driver", "level"],
     "steps": ["Set the blocks level and lay the base rails on them.", "Screw the uprights to the rail ends, tie "
               "them across, and brace each end.", "Stack bark up, ends out, with air between rows."]},
    {"id": "deck-stairs", "title": "Deck or porch stairs", "kind": "structure", "calc": "stairs",
     "args": {"rise_in": 30},
     "summary": "Stringers and treads worked out from the height to climb, inside common code limits.",
     "tools": ["circular saw", "framing square with stair gauges", "jigsaw or handsaw", "drill/driver", "level"],
     "steps": ["Measure the total rise from the landing spot to the deck surface.", "Lay out one stringer with the "
               "square, cut it, test it, then trace the rest from it.", "Fix the stringers to the deck rim with "
               "ties; set them on a solid pad.", "Screw on the treads; add a handrail for four or more risers."]},
    {"id": "workbench", "title": "Shop workbench", "kind": "woodworking", "calc": "workbench",
     "args": {},
     "summary": "A sturdy 6 ft bench from 2x4s and one sheet of plywood, with a shelf.",
     "tools": ["circular saw", "drill/driver", "square", "clamps", "tape measure"],
     "steps": ["Cut the rails, cross pieces and legs.", "Screw and glue two rectangular frames (top and shelf).",
               "Fix the legs inside the frame corners, the shelf frame 8 in up, square and level.",
               "Cut the plywood, notch the shelf around the legs, glue and screw both on."]},
)
_EXTRA = {"workbench": lambda **_args: _workbench()}


def calculate(calc: str, **args) -> build_calcs.MaterialList:
    """A material list from a calculator by name (KeyError for one that isn't there)."""
    if calc in _EXTRA:
        return _EXTRA[calc](**args)
    return build_calcs.CALCULATORS[calc](**args)


def _words(text: str) -> set[str]:
    """Pure logic. A text's words for search, plurals made singular."""
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", (text or "").lower())}


class PlanLibrary:
    """The household's plans: those kept in plans.json, the built-in ones, and files in the library's plans folder."""

    def __init__(self, context=None, data_dir: Optional[Path] = None, files_dir: Optional[Path] = None) -> None:
        """Loads the kept plans from the household's folder (or data/); files come from the library's plans folder."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self._files_dir = Path(files_dir) if files_dir is not None else None
        self.plans: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Reads the kept plans; a missing or unreadable file is none."""
        try:
            self.plans = json.loads(self._file.read_text(encoding="utf-8")).get("plans", {})
        except (OSError, ValueError):
            self.plans = {}

    def _save(self) -> None:
        """Writes the kept plans atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"plans": self.plans}, indent=1, ensure_ascii=False))

    # -------------------------------------------------------------- the three shelves

    def files_dir(self) -> Path:
        """The library's plans folder: `plans/` in the reference library's folder."""
        if self._files_dir is not None:
            return self._files_dir
        library = getattr(self.context, "reference_library", None)
        try:
            return Path(library.root_path) / "plans"
        except Exception:
            return Path(__file__).resolve().parent.parent / "reference_library" / "plans"

    def file_plans(self) -> list[dict]:
        """Plans dropped in as files: each one's title from its name, kind from its folder, and its path."""
        folder = self.files_dir()
        if not folder.is_dir():
            return []
        found = []
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in PLAN_FILES:
                rel = path.relative_to(folder)
                kind = rel.parts[0].lower() if len(rel.parts) > 1 else "other"
                title = re.sub(r"[_-]+", " ", path.stem).strip().capitalize()
                found.append({"id": f"file:{rel.as_posix()}", "title": title, "kind": kind, "path": str(path),
                              "summary": f"A {path.suffix[1:].upper()} file in the library's plans folder",
                              "folders": " ".join(rel.parts[:-1]), "source": {"name": "your files"}})
        return found

    def built_in(self) -> list[dict]:
        """The built-in plans, each with its material list at the starting size."""
        out = []
        for plan in BUILT_IN:
            materials = calculate(plan["calc"], **plan["args"]).as_dict()
            out.append({**plan, "id": f"builtin:{plan['id']}", "materials": materials, "source": {"name": _MANUAL}})
        return out

    def all(self) -> list[dict]:
        """Every plan: kept, built in, and files."""
        return list(self.plans.values()) + self.built_in() + self.file_plans()

    def get(self, plan_id: str) -> Optional[dict]:
        """A plan by id."""
        return next((p for p in self.all() if p["id"] == plan_id), None)

    def find(self, query: str, limit: int = 8) -> list[dict]:
        """Plans that match the words (title first, then kind, folders, tags and summary); all of them when there are
        no words."""
        want = _words(query) - {"plan", "plans", "blueprint", "blueprints", "how", "build", "make", "a", "the", "for",
                                "to", "my", "some", "any", "do", "you", "have", "i", "of", "material", "list"}
        if not want:
            return self.all()[:limit]
        scored = []
        for plan in self.all():
            title = _words(plan["title"])
            rest = _words(" ".join([plan.get("kind", ""), plan.get("folders", ""), plan.get("summary", ""),
                                    " ".join(plan.get("tags", []))]))
            score = 3 * len(want & title) + len(want & rest)
            if score:
                scored.append((score, plan))
        return [p for _s, p in sorted(scored, key=lambda sp: -sp[0])][:limit]

    def best(self, name: str) -> Optional[dict]:
        """The one plan a person means by its name (an id works too)."""
        return self.get(name) or next(iter(self.find(name, limit=1)), None)

    # -------------------------------------------------------------- keeping and sizing

    def keep(self, title: str, kind: str = "other", summary: str = "", materials: Optional[dict] = None,
             tools: Optional[list] = None, steps: Optional[list] = None, source: Optional[dict] = None,
             tags: Optional[list] = None, calc: str = "", args: Optional[dict] = None) -> dict:
        """Keeps a plan for the household; a life event."""
        title = " ".join((title or "").split())[:100] or "A plan"
        plan = {"id": uuid.uuid4().hex[:10], "title": title, "kind": kind if kind in KINDS else "other",
                "summary": (summary or "").strip()[:500], "materials": materials or {}, "tools": list(tools or []),
                "steps": list(steps or []), "source": source or {"name": "the household"}, "tags": list(tags or []),
                "calc": calc, "args": dict(args or {}), "kept": datetime.now().isoformat(timespec="seconds")}
        self.plans[plan["id"]] = plan
        self._save()
        life_events.record(self, "plan_kept", f"Kept a plan: {title}", [f"plan:{plan['id']}"], {"kind": plan["kind"]})
        return plan

    def delete(self, plan_id: str) -> bool:
        """Lets a kept plan go (built-in plans and files can't be deleted here)."""
        if self.plans.pop(plan_id, None) is None:
            return False
        self._save()
        return True

    def worked_out(self, plan: dict, **sizes) -> Optional[build_calcs.MaterialList]:
        """A plan's material list for a size of the person's own (its calculator rerun); None for a plan without one.
        Sizes not given keep the plan's."""
        if not plan.get("calc"):
            return None
        args = {**plan.get("args", {}), **{k: v for k, v in sizes.items() if v not in (None, "")}}
        return calculate(plan["calc"], **args)


# ------------------------------------------------------------------ against the workshop's materials


def _match(item_name: str, materials: list) -> Optional[object]:
    """The workshop material that is this item: the same name, else one whose name holds all the item's main
    words."""
    want = " ".join(item_name.lower().split())
    for material in materials:
        if " ".join(material.name.lower().split()) == want:
            return material
    words = _words(want) - {"x", "ft", "in"}
    return next((m for m in materials if words and words <= _words(m.name)), None)


def shopping_list(context, materials: dict) -> dict:
    """What a plan's materials need from the store: each item, how many are on hand (from the workshop's materials),
    how many to buy, and the cost where a unit price is known. Returns {rows, to_buy, known_cost, priced}."""
    stock = list(getattr(getattr(context, "materials", None), "all_materials", lambda: [])())
    rows, cost, priced = [], 0.0, 0
    for item in materials.get("items", []):
        match = _match(item["name"], stock)
        have = float(match.quantity_on_hand) if match is not None else 0.0
        need = max(0.0, float(item["qty"]) - have)
        row = {"item": item["name"], "unit": item.get("unit", ""), "need": item["qty"], "have": have, "buy": need}
        if match is not None and match.unit_cost and need:
            row["cost"] = round(need * match.unit_cost, 2)
            cost += row["cost"]
            priced += 1
        rows.append(row)
    return {"rows": rows, "to_buy": [r for r in rows if r["buy"] > 0], "known_cost": round(cost, 2), "priced": priced}


# ------------------------------------------------------------------ for the Library's web page


def _where(plan: dict) -> str:
    """Pure logic. Where a plan comes from, in a few words."""
    if plan["id"].startswith("builtin:"):
        return "Built in, any size"
    if plan["id"].startswith("file:"):
        return "Your file"
    return "Kept"


def screen(context, query: str = "") -> dict:
    """The plans shelf for the Library page: the plans (matching the words, when given), each with its kind and
    where it's from, the folder files go in, and where free plans are."""
    library = getattr(context, "plans", None)
    if library is None:
        return {"available": False, "plans": [], "sources": [], "folder": ""}
    plans = library.find(query, limit=60) if query.strip() else library.all()
    return {"available": True, "folder": str(library.files_dir()), "sources": [dict(s) for s in SOURCES],
            "plans": [{"id": p["id"], "title": p["title"], "kind": p.get("kind", "other"),
                       "summary": p.get("summary", ""), "where": _where(p), "file": p["id"].startswith("file:")}
                      for p in plans]}


# A size's words on the plan page, by calculator argument: (label, unit). One not here shows its own name.
SIZE_LABELS = {"length_ft": ("Length", "ft"), "width_ft": ("Width", "ft"), "height_ft": ("Height", "ft"),
               "height_in": ("Height", "in"), "span_ft": ("Joist span", "ft"), "thickness_in": ("Thickness", "in"),
               "gates": ("Gates", ""), "hens": ("Hens", ""), "depth_in": ("Depth", "in"), "width_in": ("Width", "in"),
               "shelves": ("Shelves", ""), "bays": ("Bays", ""), "rise_in": ("Rise", "in"), "depth_ft": ("Depth", "ft"),
               "wall_height_ft": ("Wall height", "ft")}


def size_fields(plan: dict, sizes: Optional[dict] = None) -> list[dict]:
    """Pure logic. The sizes a plan can be worked out at (its calculator's arguments, a built-in or kept-at-a-size
    plan only), each {name, label, unit, value}: the size asked for, else the plan's own."""
    if not plan.get("calc"):
        return []
    sizes = sizes or {}
    return [{"name": k, "label": SIZE_LABELS.get(k, (k.replace("_", " ").capitalize(), ""))[0],
             "unit": SIZE_LABELS.get(k, ("", ""))[1], "value": sizes.get(k, v)} for k, v in plan.get("args", {}).items()]


def read_sizes(plan: dict, given: dict) -> dict:
    """The sizes given for a plan's calculator, as numbers (only its own arguments; a blank one keeps the plan's).
    ValueError for one that isn't a positive number."""
    out = {}
    for name in plan.get("args", {}):
        raw = given.get(name)
        if raw in (None, ""):
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{SIZE_LABELS.get(name, (name,))[0]} has to be a number.") from None
        if value <= 0:
            raise ValueError(f"{SIZE_LABELS.get(name, (name,))[0]} has to be more than zero.")
        out[name] = int(value) if value.is_integer() else value
    return out


def _priced(shopping: dict) -> dict:
    """A shopping list with its costs in the person's currency (core.region.money): each priced row's `cost_text` and
    the total's `known_cost_text`."""
    from core.region import money

    for row in shopping["rows"]:
        if "cost" in row:
            row["cost_text"] = money(row["cost"])
    shopping["known_cost_text"] = money(shopping["known_cost"]) if shopping["known_cost"] else ""
    return shopping


def detail(context, plan_id: str, sizes: Optional[dict] = None) -> Optional[dict]:
    """One plan for the Library page: its materials, cuts (lengths as a person reads them), tools, steps, notes and
    source, worked out at the sizes given when it has a calculator (`size_fields` says which, `problem` why a size
    wasn't used); what to buy against the workshop's stock (`shopping_list`); whether it's kept (so it can be let go).
    A file plan says it's a file. None when there's no such plan."""
    library = getattr(context, "plans", None)
    plan = library.get(plan_id) if library is not None else None
    if plan is None:
        return None
    materials, problem, used = plan.get("materials") or {}, "", {}
    if sizes and plan.get("calc"):
        try:
            used = read_sizes(plan, sizes)
            worked = library.worked_out(plan, **used) if used else None
            materials = worked.as_dict() if worked is not None else materials
        except (ValueError, TypeError) as error:
            problem, used = str(error) or "Those sizes don't work for this plan.", {}
    cuts = [{**c, "length": build_calcs.inches(c["length_in"])} for c in materials.get("cuts", [])]
    return {"id": plan["id"], "title": plan["title"], "kind": plan.get("kind", "other"),
            "summary": plan.get("summary", ""), "where": _where(plan), "file": plan["id"].startswith("file:"),
            "materials_title": materials.get("title", ""), "items": materials.get("items", []), "cuts": cuts,
            "notes": materials.get("notes", []), "tools": plan.get("tools", []), "steps": plan.get("steps", []),
            "source": plan.get("source", {}), "sizes": size_fields(plan, used), "sized": bool(used), "problem": problem,
            "shopping": _priced(shopping_list(context, materials)) if materials.get("items") else None,
            "kept": plan["id"] in library.plans}


def file_path(context, plan_id: str) -> Optional[Path]:
    """The file behind a file plan, only when it sits inside the library's plans folder (so an id can't reach any
    other file on the computer); None otherwise."""
    library = getattr(context, "plans", None)
    if library is None or not plan_id.startswith("file:"):
        return None
    folder = library.files_dir().resolve()
    path = (folder / plan_id[len("file:"):]).resolve()
    if not path.is_relative_to(folder) or not path.is_file() or path.suffix.lower() not in PLAN_FILES:
        return None
    return path
