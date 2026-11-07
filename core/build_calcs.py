"""
core.build_calcs
==================

Material lists worked out in code (Zac, 2026-11-07: "references for all
kinds of stuff like woodworking plans, structure blueprints, material
lists"). Each calculator takes a structure's size and gives what to buy
and what to cut: a stud wall, a floor or deck frame, a raised garden bed,
a fence run, a concrete slab, and a gable shed built from the others. The
model only phrases the result; it never does this arithmetic.

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


CALCULATORS = {
    "stud_wall": stud_wall,
    "floor": floor_frame,
    "deck": lambda span_ft, length_ft, **kw: floor_frame(span_ft, length_ft, surface="decking", **kw),
    "raised_bed": raised_bed,
    "fence": fence,
    "slab": concrete_slab,
    "shed": shed,
}
