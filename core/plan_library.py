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


def detail(context, plan_id: str) -> Optional[dict]:
    """One plan for the Library page: its materials, cuts (lengths as a person reads them), tools, steps, notes and
    source; a file plan says it's a file. None when there's no such plan."""
    library = getattr(context, "plans", None)
    plan = library.get(plan_id) if library is not None else None
    if plan is None:
        return None
    materials = plan.get("materials") or {}
    cuts = [{**c, "length": build_calcs.inches(c["length_in"])} for c in materials.get("cuts", [])]
    return {"id": plan["id"], "title": plan["title"], "kind": plan.get("kind", "other"),
            "summary": plan.get("summary", ""), "where": _where(plan), "file": plan["id"].startswith("file:"),
            "materials_title": materials.get("title", ""), "items": materials.get("items", []), "cuts": cuts,
            "notes": materials.get("notes", []), "tools": plan.get("tools", []), "steps": plan.get("steps", []),
            "source": plan.get("source", {})}


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
