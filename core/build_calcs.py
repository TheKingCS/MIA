"""
core.build_calcs
==================

Material lists worked out in code (Zac, 2026-11-07: "references for all
kinds of stuff like woodworking plans, structure blueprints, material
lists"). Each calculator takes a structure's size and gives what to buy
and what to cut: a stud wall, a floor or deck frame, a raised garden bed,
a fence run, a concrete slab, a gable shed built from the others, and
(added the same evening) a chicken coop and run, garage shelving, a
bookshelf, a lean-to, a compost bin, a cold frame, a picnic table, a
firewood rack and deck stairs; and (2026-11-08) a hoop house and a walk-in cold room, for
Trade Master's greenhouse and cold-room jobs. `custom_cuts()` does any project of the
person's own: their parts packed into boards (`buy_boards()`) and 4x8
sheets (`sheets_for()`). The model only phrases the result; it never does
this arithmetic.

- Lumber is bought in stock lengths (8 to 16 ft). `buy_boards()` packs the
  cuts into whole boards (first fit, biggest cut first, an eighth of an inch
  for each saw cut) and picks the stock length that wastes least.
- Every list adds about 10% where boards or sheets get miscut, and says
  so. Every list ends with notes: local codes, permits and span tables have
  the last word. Joist sizes come from conservative rules of thumb, never
  presented as engineering.
- Sizes are imperial (feet and inches), as lumber is sold where MIA is
  used (DEC-0115).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

STOCK_LENGTHS = (8, 10, 12, 14, 16)  # feet
KERF_IN = 0.125
FIT_SLACK_IN = 0.25  # two 10 ft pieces still come from a 20 ft stick, a saw cut short
WASTE = 0.10
SHEET_SQFT = 32  # a 4x8 sheet
BOARD_WIDTHS = {"2x4": 3.5, "2x6": 5.5, "2x8": 7.25, "2x10": 9.25, "2x12": 11.25}
# Conservative joist spans (feet) at 16 in on center for a floor: shorter than common span tables on purpose.
JOIST_SPANS = (("2x6", 9.0), ("2x8", 12.0), ("2x10", 15.0), ("2x12", 18.0))
BAG_80LB_CUFT = 0.6  # premixed concrete yield
CODE_NOTE = ("Check local building codes and whether you need a permit; joist, rafter and beam sizes here are rules "
             "of thumb, so confirm them against a span table for your lumber.")


@dataclass
class Item:
    """One thing to buy: how many, of what unit, and a note."""
    name: str
    qty: float
    unit: str = ""
    note: str = ""


@dataclass
class Cut:
    """One part to cut: what it is, how many, its length in inches, and the stock it comes from."""
    part: str
    qty: int
    length_in: float
    stock: str = ""


@dataclass
class MaterialList:
    """What a structure needs: its title and the sizes it was worked from, items to buy, parts to cut, and notes."""
    title: str
    params: dict
    items: list = field(default_factory=list)
    cuts: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def add(self, name: str, qty: float, unit: str = "", note: str = "") -> None:
        """Adds to the list, merging with an item of the same name and unit (their notes joined, so what each board is
        for still shows)."""
        for item in self.items:
            if item.name == name and item.unit == unit:
                item.qty = round(item.qty + qty, 2)
                for part in (note.split("; ") if note else ()):
                    if part not in item.note.split("; "):
                        item.note = f"{item.note}; {part}" if item.note else part
                return
        self.items.append(Item(name, round(qty, 2), unit, note))

    def merge(self, other: "MaterialList", prefix: str = "") -> None:
        """Takes another list's items, cuts (named under a prefix) and notes into this one."""
        for item in other.items:
            self.add(item.name, item.qty, item.unit, item.note)
        self.cuts += [Cut(f"{prefix}{c.part}", c.qty, c.length_in, c.stock) for c in other.cuts]
        self.notes += [n for n in other.notes if n not in self.notes]

    def as_dict(self) -> dict:
        """The list as plain data (for the plan library and the web)."""
        return {"title": self.title, "params": dict(self.params),
                "items": [vars(i).copy() for i in self.items], "cuts": [vars(c).copy() for c in self.cuts],
                "notes": list(self.notes)}

    def to_text(self) -> str:
        """The list as lines a person reads (and the model phrases from)."""
        lines = [self.title + ":"]
        lines += [f"- {_qty(i.qty)} {i.unit + ' ' if i.unit else ''}{i.name}" + (f" ({i.note})" if i.note else "")
                  for i in self.items]
        if self.cuts:
            lines.append("Cuts:")
            lines += [f"- {c.qty} x {c.part} at {inches(c.length_in)}" + (f" from {c.stock}" if c.stock else "")
                      for c in self.cuts]
        lines += [f"Note: {n}" for n in self.notes]
        return "\n".join(lines)


def _qty(value: float) -> str:
    """Pure logic. A quantity without a needless .0."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def inches(value: float) -> str:
    """Pure logic. A length in inches as a person reads it: 92 5/8 in, or 7 ft 4 in when long."""
    eighths = round(value * 8)
    whole, frac = divmod(eighths, 8)
    fraction = {0: "", 1: " 1/8", 2: " 1/4", 3: " 3/8", 4: " 1/2", 5: " 5/8", 6: " 3/4", 7: " 7/8"}[frac]
    if whole >= 96 and not frac:
        feet, rest = divmod(whole, 12)
        return f"{feet} ft" + (f" {rest} in" if rest else "")
    return f"{whole}{fraction} in"


def with_waste(count: float) -> int:
    """Pure logic. A count with about 10% extra for miscuts, rounded up."""
    return math.ceil(count * (1 + WASTE) - 1e-9)


def stock_for(length_ft: float) -> int:
    """Pure logic. The shortest stock length that holds a piece (16 ft when it's longer: it gets spliced)."""
    return next((s for s in STOCK_LENGTHS if s >= length_ft - 1e-9), STOCK_LENGTHS[-1])


def buy_boards(cuts_in: list[float], stock: tuple[int, ...] = STOCK_LENGTHS) -> tuple[int, int]:
    """Pure logic. The fewest board-feet of one stock length that hold every cut (inches), packed biggest first with
    a saw kerf between pieces (a quarter inch of slack, so halves still fit): returns (stock length in feet, boards). A cut longer than every stock length is spliced from
    two pieces."""
    pieces = []
    longest = stock[-1] * 12
    for cut in cuts_in:
        while cut > longest:
            pieces.append(longest)
            cut -= longest
        if cut > 0:
            pieces.append(cut)
    if not pieces:
        return stock[0], 0
    best = None
    for length in stock:
        room = length * 12
        if max(pieces) > room:
            continue
        boards: list[float] = []
        for piece in sorted(pieces, reverse=True):
            for i, left in enumerate(boards):
                if left + FIT_SLACK_IN >= piece + KERF_IN:
                    boards[i] = left - piece - KERF_IN
                    break
            else:
                boards.append(room - piece)
        if best is None or len(boards) * length < best[0] * best[1]:
            best = (length, len(boards))
    return best


def joist_for(span_ft: float) -> str:
    """Pure logic. The joist size a span asks for, by a conservative rule of thumb; "" past 18 ft (it needs a beam)."""
    return next((size for size, span in JOIST_SPANS if span_ft <= span), "")


# ------------------------------------------------------------------ calculators


def stud_wall(length_ft: float, height_ft: float = 8, spacing_in: int = 16, openings: tuple = (),
              sheathing: bool = True) -> MaterialList:
    """A 2x4 stud wall: studs on center (with two more at each opening, a king and a jack, and a doubled header
    sized by its width), a bottom plate and a doubled top plate, and sheathing when asked."""
    out = MaterialList(f"{_qty(length_ft)} ft stud wall, {_qty(height_ft)} ft tall",
                       {"length_ft": length_ft, "height_ft": height_ft, "spacing_in": spacing_in,
                        "openings": list(openings)})
    stud_in = height_ft * 12 - 4.5  # three plates
    studs = math.ceil(length_ft * 12 / spacing_in) + 1 + 2 * len(openings)
    stud_stock = stock_for(stud_in / 12)
    out.add(f"2x4 x {stud_stock} ft", with_waste(studs), "", "studs")
    out.cuts.append(Cut("stud", studs, stud_in, f"2x4 x {stud_stock} ft"))
    length, boards = buy_boards([length_ft * 12] * 3)
    out.add(f"2x4 x {length} ft", boards, "", "plates: one bottom, two top")
    out.cuts.append(Cut("plate", 3, length_ft * 12, f"2x4 x {length} ft"))
    for width in openings:
        size = "2x6" if width <= 3 else "2x8" if width <= 5 else "2x10" if width <= 6 else "2x12"
        header_in = width * 12 + 3
        out.add(f"{size} x {stock_for(header_in / 12)} ft", 2, "", f"header for the {_qty(width)} ft opening")
        out.cuts.append(Cut(f"header ({_qty(width)} ft opening)", 2, header_in, size))
        if width > 6:
            out.notes.append(f"A {_qty(width)} ft opening needs an engineered header: ask the lumber yard.")
    if sheathing:
        area = length_ft * height_ft - sum(w * 6.7 for w in openings)
        out.add("4x8 sheathing (7/16 in OSB)", with_waste(area / SHEET_SQFT), "sheets")
    out.add("16d framing nails", max(1, math.ceil(length_ft / 10)), "lb")
    if sheathing:
        out.add("8d nails", max(1, math.ceil(length_ft / 16)), "lb", "for sheathing")
    out.notes.append(CODE_NOTE)
    return out


def floor_frame(span_ft: float, length_ft: float, spacing_in: int = 16, surface: str = "subfloor") -> MaterialList:
    """A floor or deck frame: joists across the span (sized by span), two rim joists, hangers, and the surface:
    4x8 subfloor sheets or 5/4x6 deck boards. Past 18 ft the span gets a beam down the middle."""
    title = "deck frame" if surface == "decking" else "floor frame"
    out = MaterialList(f"{_qty(span_ft)} x {_qty(length_ft)} ft {title}",
                       {"span_ft": span_ft, "length_ft": length_ft, "spacing_in": spacing_in, "surface": surface})
    spans = 2 if span_ft > JOIST_SPANS[-1][1] else 1
    each = span_ft / spans
    size = joist_for(each)
    if spans == 2:
        out.notes.append(f"{_qty(span_ft)} ft is too far for one joist: a beam on posts runs down the middle, and the "
                         "beam and posts need sizing from a span table.")
        out.add(f"{size} x {stock_for(length_ft)} ft", 3 * math.ceil(length_ft / 16), "", "beam (tripled)")
    joists = (math.ceil(length_ft * 12 / spacing_in) + 1) * spans
    stock = stock_for(each)
    out.add(f"{size} x {stock} ft", with_waste(joists), "", "joists")
    out.cuts.append(Cut("joist", joists, each * 12 - 3, f"{size} x {stock} ft"))
    length, boards = buy_boards([length_ft * 12] * 2)
    out.add(f"{size} x {length} ft", boards, "", "rim joists")
    out.cuts.append(Cut("rim joist", 2, length_ft * 12, f"{size} x {length} ft"))
    out.add(f"{size} joist hangers", joists * 2, "", "with hanger nails")
    if surface == "decking":
        rows = math.ceil(span_ft * 12 / 5.625)  # 5 1/2 in boards with an eighth gap
        length, boards = buy_boards([length_ft * 12] * rows)
        out.add(f"5/4x6 deck boards x {length} ft", with_waste(boards))
        out.add("deck screws (2 1/2 in)", math.ceil(rows * (joists / spans) * 2 / 350), "boxes of 350")
        out.notes.append("Deck framing outdoors is pressure-treated lumber, with hardware rated for it.")
    else:
        out.add("3/4 in tongue-and-groove subfloor 4x8", with_waste(span_ft * length_ft / SHEET_SQFT), "sheets")
        out.add("construction adhesive", math.ceil(joists / 6), "tubes")
    out.notes.append(CODE_NOTE)
    return out


def raised_bed(length_ft: float, width_ft: float, height_in: float = 11, board: str = "2x6") -> MaterialList:
    """A raised garden bed: courses of boards to the height, 4x4 corner posts (and a middle post on each long side
    past 8 ft), screws, and the soil to fill it."""
    board_w = BOARD_WIDTHS.get(board, 5.5)
    courses = max(1, math.ceil(height_in / board_w - 0.05))
    out = MaterialList(f"{_qty(length_ft)} x {_qty(width_ft)} ft raised bed, {_qty(courses * board_w)} in tall",
                       {"length_ft": length_ft, "width_ft": width_ft, "height_in": height_in, "board": board})
    sides = [length_ft * 12] * (2 * courses)
    ends = [width_ft * 12 - 3] * (2 * courses)  # ends fit between the sides
    length, boards = buy_boards(sides + ends)
    out.add(f"{board} x {length} ft", boards, "", "untreated cedar or other rot-resistant wood is common for food beds")
    out.cuts += [Cut("side", 2 * courses, length_ft * 12, f"{board} x {length} ft"),
                 Cut("end", 2 * courses, width_ft * 12 - 3, f"{board} x {length} ft")]
    posts = 4 + (2 if length_ft > 8 else 0)
    post_in = courses * board_w
    out.add("4x4 x 8 ft", math.ceil(posts / max(1, int(96 // (post_in + KERF_IN)))), "", "corner posts")
    out.cuts.append(Cut("post", posts, post_in, "4x4 x 8 ft"))
    out.add("3 in exterior screws", posts * courses * 4, "", "about 4 per board end")
    cubic_ft = length_ft * width_ft * courses * board_w / 12
    out.add("soil and compost mix", round(cubic_ft / 27, 2), "cu yd", f"{round(cubic_ft, 1)} cu ft")
    return out


def fence(length_ft: float, height_ft: float = 6, post_spacing_ft: float = 8, rails: int = 0,
          picket_width_in: float = 5.5, gap_in: float = 0, gates: int = 0) -> MaterialList:
    """A wood picket or privacy fence: 4x4 posts set in concrete (deep enough for the height), 2x4 rails (two up to
    4 ft tall, three above), pickets across the run, and hinges and a latch for each gate."""
    rails = rails or (2 if height_ft <= 4 else 3)
    out = MaterialList(f"{_qty(length_ft)} ft fence, {_qty(height_ft)} ft tall",
                       {"length_ft": length_ft, "height_ft": height_ft, "post_spacing_ft": post_spacing_ft,
                        "rails": rails, "gates": gates})
    sections = math.ceil(length_ft / post_spacing_ft)
    posts = sections + 1 + gates
    depth = max(2.0, math.ceil(height_ft / 2.5 * 2) / 2)
    post_stock = stock_for(height_ft + depth)
    out.add(f"4x4 x {post_stock} ft pressure-treated posts", posts, "", f"set {_qty(depth)} ft deep")
    hole_cuft = math.pi * (5 / 12) ** 2 * depth - (3.5 / 12) ** 2 * depth  # a 10 in hole around the post
    out.add("80 lb bags of concrete", math.ceil(posts * hole_cuft / BAG_80LB_CUFT), "")
    out.add(f"2x4 x {stock_for(post_spacing_ft)} ft pressure-treated", with_waste(sections * rails), "", "rails")
    pickets = math.ceil(length_ft * 12 / (picket_width_in + gap_in))
    out.add(f"{_qty(picket_width_in + 0.5)} in x {_qty(height_ft)} ft pickets", with_waste(pickets))
    out.add("exterior screws or ring-shank nails (1 1/2 to 2 in)", math.ceil(pickets * rails * 2 / 350),
            "boxes of 350")
    if gates:
        out.add("gate hinges", gates, "pair")
        out.add("gate latch", gates)
    out.notes.append("Call 811 (or your area's dig line) before digging post holes.")
    out.notes.append("Check property lines, HOA rules and any fence-height limits first.")
    return out


def concrete_slab(length_ft: float, width_ft: float, thickness_in: float = 4) -> MaterialList:
    """A concrete slab: its volume with 10% extra, as cubic yards or 80 lb bags, a 4 in gravel base, rebar on an
    18 in grid, and form boards around the edge."""
    out = MaterialList(f"{_qty(length_ft)} x {_qty(width_ft)} ft slab, {_qty(thickness_in)} in thick",
                       {"length_ft": length_ft, "width_ft": width_ft, "thickness_in": thickness_in})
    cubic_ft = length_ft * width_ft * thickness_in / 12 * (1 + WASTE)
    yards = cubic_ft / 27
    out.add("concrete", round(yards, 2), "cu yd", f"or {math.ceil(cubic_ft / BAG_80LB_CUFT)} bags of 80 lb mix")
    if yards > 1:
        out.notes.append("Over about a cubic yard, ready-mix delivery is usually cheaper and easier than bags.")
    out.add("compactible gravel (4 in base)", round(length_ft * width_ft * 4 / 12 / 27 * (1 + WASTE), 2), "cu yd")
    bars = [width_ft * 12] * (math.ceil(length_ft * 12 / 18) + 1) + [length_ft * 12] * (math.ceil(width_ft * 12 / 18) + 1)
    _length, sticks = buy_boards(bars, stock=(20,))
    out.add("#4 rebar x 20 ft", sticks, "", "18 in grid, tied, on chairs")
    out.add("rebar chairs", math.ceil(length_ft * width_ft / 9))
    form_length, forms = buy_boards([length_ft * 12] * 2 + [width_ft * 12] * 2)
    out.add(f"2x{4 if thickness_in <= 3.5 else 6} x {form_length} ft", forms, "", "forms, with stakes")
    out.add("form stakes", math.ceil(2 * (length_ft + width_ft) / 3))
    out.notes.append(CODE_NOTE)
    return out


def shed(width_ft: float, length_ft: float, wall_height_ft: float = 8, pitch: float = 4,
         overhang_in: float = 12, door_ft: float = 4) -> MaterialList:
    """A gable shed: the floor frame, four stud walls (a door in one end), rafters at 24 in on center to the pitch
    (rise in 12), a ridge board, roof sheathing, shingles, underlayment, drip edge, ties and siding."""
    out = MaterialList(f"{_qty(width_ft)} x {_qty(length_ft)} ft gable shed",
                       {"width_ft": width_ft, "length_ft": length_ft, "wall_height_ft": wall_height_ft,
                        "pitch": pitch, "overhang_in": overhang_in, "door_ft": door_ft})
    out.merge(floor_frame(width_ft, length_ft), "floor: ")
    for name, wall_length, door in (("long wall", length_ft, ()), ("long wall", length_ft, ()),
                                    ("end wall", width_ft - 7 / 12, (door_ft,)), ("end wall", width_ft - 7 / 12, ())):
        out.merge(stud_wall(wall_length, wall_height_ft, 16, door, sheathing=False), f"{name}: ")
    run_ft = width_ft / 2 + overhang_in / 12
    rafter_ft = run_ft * math.sqrt(1 + (pitch / 12) ** 2)
    pairs = math.ceil(length_ft * 12 / 24) + 1
    rafter_size = "2x6" if run_ft <= 10 else "2x8"
    out.add(f"{rafter_size} x {stock_for(rafter_ft)} ft", with_waste(pairs * 2), "", "rafters at 24 in")
    out.cuts.append(Cut("rafter", pairs * 2, round(rafter_ft * 12, 1), f"{rafter_size} x {stock_for(rafter_ft)} ft"))
    ridge_in = length_ft * 12 + 2 * overhang_in
    ridge_stock, ridge_boards = buy_boards([ridge_in])
    out.add(f"{'2x8' if rafter_size == '2x6' else '2x10'} x {ridge_stock} ft", ridge_boards, "", "ridge board")
    out.add("hurricane ties", pairs * 2)
    roof_sqft = 2 * rafter_ft * (length_ft + 2 * overhang_in / 12)
    out.add("1/2 in roof sheathing 4x8", with_waste(roof_sqft / SHEET_SQFT), "sheets")
    out.add("architectural shingles", math.ceil(roof_sqft / 100 * 3 * (1 + WASTE)), "bundles", "3 per square")
    out.add("synthetic underlayment", math.ceil(roof_sqft * (1 + WASTE) / 1000), "rolls (10 squares)")
    out.add("drip edge x 10 ft", math.ceil(2 * (length_ft + 2 * overhang_in / 12 + 2 * rafter_ft) / 10))
    out.add("roofing nails (1 1/4 in)", max(1, math.ceil(roof_sqft / 100 * 2.5)), "lb")
    gable_sqft = 2 * (width_ft / 2) * (width_ft / 2 * pitch / 12)
    wall_sqft = 2 * (length_ft + width_ft) * wall_height_ft + gable_sqft - door_ft * 6.7
    out.add("T1-11 siding 4x8", with_waste(wall_sqft / SHEET_SQFT), "sheets", "or sheathing and siding of choice")
    out.add("8d galvanized siding nails", max(1, math.ceil(wall_sqft / 100)), "lb")
    out.notes.append("The gable ends need short studs cut to the roof line; take them from the miscut allowance.")
    return out


# ------------------------------------------------------------------ homestead, garden and woodworking (2026-11-07)


def _boards(out: MaterialList, size: str, parts: list, note: str = "") -> None:
    """Buys one lumber size for its parts ((name, how many, inches) each), packed into stock lengths, and lists the
    cuts."""
    pieces = [inches for _name, qty, inches in parts for _ in range(qty)]
    if not pieces:
        return
    length, boards = buy_boards(pieces)
    out.add(f"{size} x {length} ft", boards, "", note)
    out.cuts += [Cut(name, qty, round(inches, 2), f"{size} x {length} ft") for name, qty, inches in parts if qty]


def chicken_coop(width_ft: float = 0, length_ft: float = 0, hens: int = 0, height_ft: float = 6,
                 run: bool = True) -> MaterialList:
    """A shed-roof chicken coop on a 2x4 floor: 4 sq ft a hen inside (sized from the hens when no size is given, or
    the hens from the size), framed walls with a people door and a pop door, a metal roof, siding, a roost (10 in a
    hen), nest boxes (one per 4 hens), vents, and a run of 10 sq ft a hen in 1/2 in hardware cloth."""
    if not hens and width_ft and length_ft:
        hens = max(1, int(width_ft * length_ft // 4))
    hens = int(hens or 6)
    if not (width_ft and length_ft):
        width_ft = 4 if hens <= 8 else 6 if hens <= 18 else 8
        length_ft = max(4, math.ceil(hens * 4 / width_ft / 2) * 2)
    out = MaterialList(f"{_qty(width_ft)} x {_qty(length_ft)} ft chicken coop for {hens} hens",
                       {"width_ft": width_ft, "length_ft": length_ft, "hens": hens, "height_ft": height_ft, "run": run})
    joists = math.ceil(length_ft * 12 / 16) + 1
    _boards(out, "2x4", [("floor joist", joists, width_ft * 12 - 3), ("floor rim", 2, length_ft * 12)], "floor")
    out.add("3/4 in plywood 4x8", math.ceil(width_ft * length_ft / SHEET_SQFT), "sheets", "floor")
    back_ft = height_ft - 1  # a shed roof falling 1 ft front to back
    for name, wall, tall, doors in (("front wall", length_ft, height_ft, (2,)), ("back wall", length_ft, back_ft, ()),
                                    ("side wall", width_ft - 7 / 12, height_ft, ()),
                                    ("side wall", width_ft - 7 / 12, back_ft, ())):
        out.merge(stud_wall(wall, tall, 24, doors, sheathing=False), f"{name}: ")
    rafter_in = math.hypot(width_ft * 12 + 12, 12)
    rafters = math.ceil(length_ft * 12 / 24) + 1
    _boards(out, "2x4", [("rafter", rafters, rafter_in)], "rafters at 24 in")
    panels = math.ceil((length_ft * 12 + 12) / 24)
    out.add(f"metal roof panels x {stock_for(rafter_in / 12)} ft", panels, "", "24 in coverage")
    out.add("roofing screws with washers", math.ceil(panels * rafter_in / 12 * 1.5), "")
    wall_sqft = 2 * length_ft * (height_ft + back_ft) / 2 + 2 * width_ft * (height_ft + back_ft) / 2
    out.add("T1-11 siding 4x8", with_waste(wall_sqft / SHEET_SQFT), "sheets", "or plywood, painted")
    roost_in = hens * 10
    _boards(out, "2x4", [("roost bar (wide face up)", math.ceil(roost_in / (width_ft * 12 - 3)), width_ft * 12 - 3)],
            "roosts")
    nests = max(1, math.ceil(hens / 4))
    out.add("1/2 in plywood 4x8", math.ceil(nests / 4), "sheets", f"{nests} nest boxes, 12 x 12 x 12 in")
    out.add("1/2 in hardware cloth, 3 x 10 ft roll", 1, "", "vents and windows: 1 sq ft of vent a hen")
    out.add("door hinges", 3, "pair", "people door, pop door, nest lid")
    out.add("latches (two-step, raccoon-proof)", 3)
    if run:
        run_length = max(4, math.ceil(hens * 10 / width_ft / 2) * 2)
        perimeter = 2 * run_length + width_ft  # the coop closes the fourth side
        posts = math.ceil(perimeter / 6) + 1
        out.add("4x4 x 10 ft pressure-treated posts", posts, "", f"run, {_qty(width_ft)} x {_qty(run_length)} ft, "
                "set 2.5 ft deep")
        out.add("80 lb bags of concrete", posts * 2)
        out.add("2x4 x 8 ft pressure-treated", with_waste(math.ceil(perimeter / 8) * 2), "", "run rails, top and bottom")
        cloth_ft = perimeter * 2 + perimeter  # 6 ft walls in two 3 ft strips, and a 3 ft strip for the apron
        out.add("1/2 in hardware cloth, 3 x 25 ft roll", math.ceil(cloth_ft / 25), "", "run walls and a 12 in apron")
        out.add("hardware cloth staples or screws with washers", math.ceil(cloth_ft / 50), "boxes")
        out.notes.append("Bury or apron the run's hardware cloth 12 in out: diggers come under, not through.")
    out.notes.append("Use 1/2 in hardware cloth, not chicken wire: chicken wire keeps chickens in, not predators out.")
    return out


def _qty_of(result: MaterialList, starts: str) -> float:
    """The quantity of a list's item whose name starts with these words (0 when there's none)."""
    return next((i.qty for i in result.items if i.name.startswith(starts)), 0)


def shelving(width_ft: float = 8, depth_in: float = 24, height_ft: float = 6, shelves: int = 4) -> MaterialList:
    """Garage shelving: shelf frames of 2x4 (front and back rails, cross pieces every 24 in) on 2x4 legs at each end
    and every 4 ft, topped with 3/4 in plywood ripped to depth."""
    shelves = int(shelves) or 4
    out = MaterialList(f"{_qty(width_ft)} ft garage shelving, {_qty(depth_in)} in deep, {shelves} shelves",
                       {"width_ft": width_ft, "depth_in": depth_in, "height_ft": height_ft, "shelves": shelves})
    across = math.ceil(width_ft * 12 / 24) + 1
    legs = 2 * (math.ceil(width_ft / 4) + 1)
    _boards(out, "2x4", [("shelf rail", 2 * shelves, width_ft * 12), ("cross piece", across * shelves, depth_in - 3),
                         ("leg", legs, height_ft * 12)])
    per_sheet = max(1, int(48 // depth_in))
    strips = shelves * math.ceil(width_ft / 8)
    out.add("3/4 in plywood or OSB 4x8", math.ceil(strips / per_sheet), "sheets", f"ripped to {_qty(depth_in)} in")
    out.add("3 in screws", shelves * (across * 4) + legs * shelves * 2)
    out.add("1 1/4 in screws", shelves * across * 3, "", "plywood to the frames")
    out.notes.append("Screw the unit to the wall studs at the top so it can't tip.")
    return out


def bookshelf(width_in: float = 36, height_in: float = 72, depth_in: float = 11.25, shelves: int = 0) -> MaterialList:
    """A solid-wood bookshelf of 1x boards (3/4 in thick): two sides, a top, a bottom and fixed shelves about every
    12 in, a 1/4 in plywood back and a toe kick."""
    shelves = int(shelves) or max(2, round((height_in - 4) / 12) + 1)  # top and bottom count
    board = "1x12" if depth_in > 9.25 else "1x10" if depth_in > 7.25 else "1x8"
    inner = width_in - 1.5
    out = MaterialList(f"{_qty(width_in)} x {_qty(height_in)} in bookshelf, {shelves} shelves",
                       {"width_in": width_in, "height_in": height_in, "depth_in": depth_in, "shelves": shelves})
    _boards(out, board, [("side", 2, height_in), ("shelf (with top and bottom)", shelves, inner)],
            "pine or poplar, 3/4 in")
    _boards(out, "1x4", [("toe kick", 1, inner)])
    out.add("1/4 in plywood 4x8", math.ceil(width_in * height_in / 4608), "sheets", "back")
    out.add("wood glue", 1, "bottle")
    out.add("1 1/4 in pocket screws or 2 in finish nails", shelves * 8)
    if inner > 34.5:
        out.notes.append("Shelves of 3/4 in pine longer than about 36 in sag under books: add a center divider or a "
                         "1x2 front edge.")
    out.notes.append("Anchor it to a wall stud with a furniture strap.")
    return out


def lean_to(depth_ft: float = 8, length_ft: float = 12, high_ft: float = 8, low_ft: float = 6.5) -> MaterialList:
    """A post-frame lean-to with a metal roof: 4x4 posts set in concrete every 8 ft front and back, doubled 2x8
    headers, 2x6 rafters at 24 in to the slope, 2x4 purlins at 24 in, metal panels, screws and ties."""
    out = MaterialList(f"{_qty(depth_ft)} x {_qty(length_ft)} ft lean-to",
                       {"depth_ft": depth_ft, "length_ft": length_ft, "high_ft": high_ft, "low_ft": low_ft})
    per_line = math.ceil(length_ft / 8) + 1
    out.add(f"4x4 x {stock_for(high_ft + 2.5)} ft pressure-treated", per_line, "", "tall posts, 2.5 ft deep")
    out.add(f"4x4 x {stock_for(low_ft + 2.5)} ft pressure-treated", per_line, "", "short posts, 2.5 ft deep")
    out.add("80 lb bags of concrete", per_line * 2 * 2)
    _boards(out, "2x8", [("header (doubled)", 4, length_ft * 12)], "headers")
    rafter_in = math.hypot(depth_ft * 12 + 12, (high_ft - low_ft) * 12)
    rafters = math.ceil(length_ft * 12 / 24) + 1
    _boards(out, "2x6", [("rafter", rafters, rafter_in)], "rafters at 24 in")
    rows = math.ceil(rafter_in / 24) + 1
    _boards(out, "2x4", [("purlin", rows, length_ft * 12 + 12)], "purlins at 24 in")
    panels = math.ceil((length_ft * 12 + 12) / 36)
    out.add(f"metal roof panels x {stock_for(rafter_in / 12)} ft", panels, "", "36 in coverage")
    out.add("roofing screws with washers", math.ceil(panels * rows * 4 * 1.1))
    out.add("hurricane ties", rafters * 2)
    out.add("1/2 x 8 in carriage bolts", per_line * 4, "", "headers to posts")
    if depth_ft > 12:
        out.notes.append("Past about 12 ft deep, 2x6 rafters need a mid-span beam or a bigger size: check a span table.")
    out.notes.append(CODE_NOTE)
    return out


def compost_bin(bays: int = 3, size_ft: float = 3, height_ft: float = 3) -> MaterialList:
    """A slatted wooden compost bin of side-by-side bays: 4x4 corner posts, 2x6 slats with 1 in air gaps on the back
    and dividers, and front slats that lift out."""
    bays = int(bays) or 3
    rows = math.ceil(height_ft * 12 / 6.5)
    out = MaterialList(f"{bays}-bay compost bin, {_qty(size_ft)} ft bays, {_qty(height_ft)} ft tall",
                       {"bays": bays, "size_ft": size_ft, "height_ft": height_ft})
    out.add("4x4 x 8 ft (untreated cedar or other rot-resistant wood)",
            math.ceil(2 * (bays + 1) / int(96 // (height_ft * 12))), "", "posts")
    out.cuts.append(Cut("post", 2 * (bays + 1), height_ft * 12, "4x4 x 8 ft"))
    _boards(out, "2x6", [("back slat", rows, bays * size_ft * 12), ("divider slat", rows * (bays + 1), size_ft * 12 - 7),
                         ("front slat (lift-out)", rows * bays, size_ft * 12 - 4)], "cedar or untreated")
    _boards(out, "1x2", [("front slat guide", 4 * bays, height_ft * 12)])
    out.add("3 in exterior screws", rows * (bays + 1) * 4 + rows * 4 * bays)
    return out


def cold_frame(width_ft: float = 3, length_ft: float = 6, back_in: float = 18, front_in: float = 12) -> MaterialList:
    """A cold frame: a box of 2x8 boards higher at the back so the lid faces the sun, corner posts, and a hinged
    lid of a 2x2 frame under twinwall polycarbonate."""
    out = MaterialList(f"{_qty(width_ft)} x {_qty(length_ft)} ft cold frame",
                       {"width_ft": width_ft, "length_ft": length_ft, "back_in": back_in, "front_in": front_in})
    back_rows, front_rows = math.ceil(back_in / 7.25), math.ceil(front_in / 7.25)
    _boards(out, "2x8", [("back board", back_rows, length_ft * 12), ("front board", front_rows, length_ft * 12),
                         ("side board (cut to the slope)", 2 * back_rows, width_ft * 12 - 3)], "cedar")
    _boards(out, "2x4", [("corner post", 2, back_in), ("corner post", 2, front_in)])
    _boards(out, "2x2", [("lid rail", 2, length_ft * 12), ("lid stile", math.ceil(length_ft / 3) + 1, width_ft * 12)])
    out.add("twinwall polycarbonate 4x8", math.ceil(width_ft * length_ft / SHEET_SQFT), "sheets", "lid")
    out.add("polycarbonate screws with washers", math.ceil(2 * (width_ft + length_ft) * 1.5))
    out.add("hinges", math.ceil(length_ft / 3), "pair")
    out.add("lid prop or automatic vent opener", 1)
    out.add("3 in exterior screws", 40)
    out.notes.append("Face the low side south (north in the southern hemisphere) and vent it on warm days.")
    return out


def picnic_table(length_ft: float = 8) -> MaterialList:
    """A classic A-frame picnic table: five 2x6 top boards, two 2x6 boards per seat, 2x6 legs and seat supports,
    2x4 top cleats and braces, carriage bolts and screws."""
    out = MaterialList(f"{_qty(length_ft)} ft picnic table", {"length_ft": length_ft})
    _boards(out, "2x6", [("top board", 5, length_ft * 12), ("seat board", 4, length_ft * 12),
                         ("leg (22 1/2 deg both ends)", 4, 33), ("seat support", 2, 60)], "pressure-treated or cedar")
    _boards(out, "2x4", [("top cleat", 3, 29), ("brace (angled)", 2, 34)])
    out.add("3/8 x 4 in carriage bolts with nuts and washers", 12)
    out.add("3 in exterior screws", 80)
    out.notes.append("Cut one leg, test the angle, then use it as the pattern for the rest.")
    return out


def firewood_rack(length_ft: float = 8, height_ft: float = 4, depth_in: float = 16) -> MaterialList:
    """A firewood rack: two 2x4 base rails on blocks, 2x4 end uprights braced across, and how much wood it holds (a
    full cord is 128 cu ft)."""
    out = MaterialList(f"{_qty(length_ft)} ft firewood rack, {_qty(height_ft)} ft tall",
                       {"length_ft": length_ft, "height_ft": height_ft, "depth_in": depth_in})
    _boards(out, "2x4", [("base rail", 2, length_ft * 12), ("upright", 4, height_ft * 12),
                         ("end tie", 4, depth_in), ("end brace", 2, round(math.hypot(depth_in, height_ft * 12 / 2), 1))],
            "pressure-treated")
    out.add("concrete blocks", 4, "", "keep the rails off the ground")
    out.add("3 in exterior screws", 40)
    cords = length_ft * height_ft * depth_in / 12 / 128
    out.notes.append(f"Holds about {round(cords, 2)} cord ({round(cords * 128)} cu ft); a face cord of 16 in wood is "
                     "a third of a cord.")
    return out


MAX_RISE_IN, MIN_RUN_IN = 7.75, 10  # the common residential code limits


def stairs(rise_in: float, width_in: float = 36, run_in: float = 10.5) -> MaterialList:
    """Outdoor stairs: as few steps as keep each riser at or under 7 3/4 in, treads at least 10 in deep (two 2x6s
    each), 2x12 stringers every 16 in or less, and the stringer's length and cut marks."""
    run_in = max(MIN_RUN_IN, run_in)
    steps = max(1, math.ceil(rise_in / MAX_RISE_IN))
    riser = rise_in / steps
    treads = steps - 1 if steps > 1 else 1  # the top step is the deck or landing
    stringer_in = math.hypot(rise_in, treads * run_in) + 12
    count = max(3, math.ceil(width_in / 16) + 1)
    out = MaterialList(f"stairs for a {_qty(rise_in)} in rise, {_qty(width_in)} in wide",
                       {"rise_in": rise_in, "width_in": width_in, "run_in": run_in})
    out.add(f"2x12 x {stock_for(stringer_in / 12)} ft pressure-treated", count, "", "stringers")
    out.cuts.append(Cut("stringer", count, round(stringer_in, 1), "2x12"))
    _boards(out, "2x6", [("tread board", 2 * treads, width_in)], "pressure-treated or 5/4 decking")
    out.add("stringer ties or hangers", count)
    out.add("3 in deck screws", treads * count * 4)
    out.notes.append(f"{steps} risers of {inches(riser)} and {treads} treads of {inches(run_in)}: mark the stringer with "
                     "a framing square and stair gauges, cut one, test it, then use it as the pattern.")
    if steps >= 4:
        out.notes.append("Four or more risers need a graspable handrail, and guards where it's over 30 in up.")
    out.notes.append(CODE_NOTE)
    return out


# ------------------------------------------------------------------ any project: a cut list of your own parts


def sheets_for(parts: list[tuple[float, float]], sheet: tuple[float, float] = (48, 96)) -> int:
    """Pure logic. How many sheets (4x8 by default) hold these rectangular parts (width, length in inches), packed in
    rows along the sheet, biggest first, a saw kerf around each, either way round."""
    width, length = sheet
    pieces = sorted(((min(w, l), max(w, l)) for w, l in parts), key=lambda p: (-p[1], -p[0]))
    sheets: list[dict] = []  # each: its rows ([row depth, length used]) and whether it's taken whole
    for short, long in pieces:
        if long > length + FIT_SLACK_IN or short > width + FIT_SLACK_IN:
            sheets.append({"rows": [], "full": True})  # bigger than a sheet: a sheet to itself (it's spliced)
            continue
        placed = False
        for current in (s for s in sheets if not s["full"]):
            rows = current["rows"]
            row = next((r for r in rows if short <= r[0] + FIT_SLACK_IN and r[1] + long <= length + FIT_SLACK_IN),
                       None)
            if row is not None:
                row[1] += long + KERF_IN
                placed = True
            elif sum(r[0] + KERF_IN for r in rows) + short <= width + FIT_SLACK_IN:
                rows.append([short, long + KERF_IN])
                placed = True
            if placed:
                break
        if not placed:
            sheets.append({"rows": [[short, long + KERF_IN]], "full": False})
    return len(sheets)


def custom_cuts(parts: list[dict], title: str = "your project") -> MaterialList:
    """A cut list of a project's own parts, each {name, qty, length_in, width_in (sheet goods only), material}:
    boards bought per lumber size in stock lengths, sheet goods per material in 4x8 sheets."""
    out = MaterialList(f"Cut list for {title}", {"parts": len(parts)})
    by_material: dict[str, list] = {}
    for part in parts:
        by_material.setdefault(part.get("material") or "2x4", []).append(part)
    for material, group in by_material.items():
        if any(p.get("width_in") for p in group):
            rects = [(p.get("width_in") or 3.5, p["length_in"]) for p in group for _ in range(int(p.get("qty", 1)))]
            out.add(f"{material} 4x8", sheets_for(rects), "sheets")
            out.cuts += [Cut(f"{p.get('name') or 'part'} ({_qty(p.get('width_in') or 0)} in wide)", int(p.get("qty", 1)),
                             p["length_in"], material) for p in group]
        else:
            _boards(out, material, [(p.get("name") or "part", int(p.get("qty", 1)), p["length_in"]) for p in group])
    out.notes.append("Lengths include no allowance for joinery: add tenons, dados or overlaps to the parts first.")
    return out


def hoop_house(width_ft: float = 14, length_ft: float = 24, bow_spacing_ft: float = 4,
               wall_ft: float = 0) -> MaterialList:
    """A ground-post hoop house (high tunnel): steel bows every `bow_spacing_ft` on driven ground posts (one each
    side), three purlin runs, treated 2x6 baseboards and hip boards down both sides, 2x4 end walls with a door in one
    and a vent in the other, wiggle-wire channel, and UV film cut long enough to wrap the ends and bury or batten.
    A bow is taken as a half circle on `wall_ft` of straight leg each side (0 for a plain quonset)."""
    bows = math.ceil(length_ft / bow_spacing_ft) + 1
    rise_ft = width_ft / 2 + wall_ft
    arc_ft = math.pi * width_ft / 2 + 2 * wall_ft
    out = MaterialList(f"{_qty(width_ft)} x {_qty(length_ft)} ft hoop house",
                       {"width_ft": width_ft, "length_ft": length_ft, "bow_spacing_ft": bow_spacing_ft,
                        "wall_ft": wall_ft})
    out.add("steel bows (1 3/8 in or heavier, bent to the width)", bows, "", f"each about {_qty(round(arc_ft, 1))} ft "
            "of tube, from a kit or a bender")
    out.add("ground posts (1 5/8 in steel, 36 in or longer)", 2 * bows, "", "driven about 24 in, 12 in left above")
    runs = 3
    out.add("purlin tube (10 ft lengths)", runs * math.ceil(length_ft / 9.5), "", "a ridge run and one each side, "
            "lapped and screwed")
    out.add("cross connectors", runs * bows, "", "purlin to bow")
    _boards(out, "2x6", [("baseboard", 2, length_ft * 12), ("hip board", 2, length_ft * 12)], "pressure-treated "
            "(ground contact for the baseboards), joined over a bow where a run is longer than a board")
    studs = math.ceil(width_ft / 2) + 1
    _boards(out, "2x4", [("end-wall stud (cut to the bow)", 2 * studs, rise_ft * 12),
                         ("end-wall header and sill", 4, width_ft * 12)], "pressure-treated at the ground")
    out.add("door (or a framed door with hinges and latch)", 1, "", "in one end wall")
    out.add("vent (louver or roll-up panel)", 1, "", "high in the other end wall, opposite the door")
    channel_ft = 2 * length_ft + 2 * arc_ft + 2 * width_ft
    out.add("wiggle-wire channel and wire (6 ft lengths)", math.ceil(channel_ft / 6), "", "hip boards, end bows and "
            "baseboards")
    roof_w, roof_l = math.ceil(arc_ft + 8), math.ceil(length_ft + width_ft + 4)
    out.add(f"greenhouse film (UV-stabilized, 6 mil, 4-year), {roof_w} x {roof_l} ft", 1, "piece",
            "over the bows, long enough to wrap the end bows")
    end_w, end_h = math.ceil(width_ft + 2), math.ceil(rise_ft + 2)
    out.add(f"greenhouse film for the end walls, {end_w} x {end_h} ft", 2, "pieces")
    out.add("anchors for the ground posts (augers, or concrete where the soil is loose)", 2 * bows, "",
            "the corner posts and every few in between at the least")
    out.add("self-drilling screws for the purlins and channel", math.ceil((runs * bows + channel_ft / 2) / 25) * 25)
    out.add("structural screws or lags for the baseboards and hip boards", 4 * bows)
    out.notes.append("Bow tube and posts come in kits sized to a width; buy those as a set so they fit each other.")
    out.notes.append("Set the long side across the prevailing wind only if your kit is rated for it, and run it "
                     "east-west for winter light where you can.")
    out.notes.append(CODE_NOTE)
    return out


def cold_room(width_ft: float = 8, length_ft: float = 10, height_ft: float = 8, wall_r: int = 25,
              ceiling_r: int = 30) -> MaterialList:
    """A walk-in cold room built inside a dry building: four 2x4 stud walls (a door in one) with the insulation as
    continuous rigid foam over them, a 2x6 ceiling frame, foam sized up to the R-values asked (polyiso at about R-6 an
    inch, in 2 in boards, so a layer is never short), foil tape and spray foam for every seam, a vapor retarder on the warm side, plywood inside, an insulated door, and the window air conditioner and
    controller sized from the floor area."""
    out = MaterialList(f"{_qty(width_ft)} x {_qty(length_ft)} ft cold room, {_qty(height_ft)} ft tall",
                       {"width_ft": width_ft, "length_ft": length_ft, "height_ft": height_ft, "wall_r": wall_r,
                        "ceiling_r": ceiling_r})
    for side, run, door in (("long wall", length_ft, (3,)), ("long wall", length_ft, ()),
                            ("end wall", width_ft, ()), ("end wall", width_ft, ())):
        wall = stud_wall(run, height_ft, 16, door, sheathing=False)
        out.merge(wall, f"{side}: ")
    joists = math.ceil(length_ft * 12 / 24) + 1
    _boards(out, "2x6", [("ceiling joist", joists, width_ft * 12)], "ceiling frame at 24 in")
    wall_area = 2 * (width_ft + length_ft) * height_ft - 3 * 6.7
    ceiling_area = width_ft * length_ft
    per_inch = 6
    wall_layers = math.ceil(wall_r / per_inch / 2)
    ceiling_layers = math.ceil(ceiling_r / per_inch / 2)
    out.add("2 in polyiso foam board, 4x8", with_waste(wall_area * wall_layers / SHEET_SQFT), "sheets",
            f"walls, {wall_layers} layers (about R-{wall_layers * 2 * per_inch}), seams staggered")
    out.add("2 in polyiso foam board, 4x8", with_waste(ceiling_area * ceiling_layers / SHEET_SQFT), "sheets",
            f"ceiling, {ceiling_layers} layers (about R-{ceiling_layers * 2 * per_inch})")
    out.add("2 in XPS foam board, 4x8 (under a floor of plywood)", with_waste(ceiling_area / SHEET_SQFT), "sheets",
            "floor, on a dry slab")
    out.add("3/4 in plywood, 4x8", with_waste((wall_area + 2 * ceiling_area) / SHEET_SQFT), "sheets",
            "inside the walls and ceiling, and the floor over the foam")
    out.add("foil tape", math.ceil((wall_area + ceiling_area) / 60), "rolls", "every seam of every layer")
    out.add("spray foam (low-expansion)", math.ceil((wall_area + ceiling_area) / 80) + 2, "cans")
    out.add("6 mil poly vapor retarder", math.ceil((wall_area + ceiling_area) * 1.15), "sq ft",
            "on the warm (outer) side, lapped and taped")
    out.add("insulated door with gaskets and a closer", 1)
    btu = max(5000, math.ceil(ceiling_area * 100 / 1000) * 1000)
    out.add(f"window air conditioner, about {btu:,} BTU", 1, "", "sized from the floor area; the controller's maker "
            "has a sizing chart that has the last word")
    out.add("cooler controller (CoolBot or similar) and its sensor", 1)
    out.notes = [n for n in out.notes if n != CODE_NOTE]
    out.notes.append("The air conditioner needs its own circuit: that is the workshop circuit job's work, or an "
                     "electrician's.")
    out.notes.append(CODE_NOTE)
    return out


CALCULATORS = {
    "stud_wall": stud_wall,
    "floor": floor_frame,
    "deck": lambda span_ft, length_ft, **kw: floor_frame(span_ft, length_ft, surface="decking", **kw),
    "raised_bed": raised_bed,
    "fence": fence,
    "slab": concrete_slab,
    "shed": shed,
    "chicken_coop": chicken_coop,
    "shelving": shelving,
    "bookshelf": bookshelf,
    "lean_to": lean_to,
    "compost_bin": compost_bin,
    "cold_frame": cold_frame,
    "picnic_table": picnic_table,
    "firewood_rack": firewood_rack,
    "stairs": stairs,
    "hoop_house": hoop_house,
    "cold_room": cold_room,
}
