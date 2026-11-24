"""
core.print_parts
==================

Parts to 3D print, made in code (Zac, 2026-11-24: "help me design the devices too ... 3d printing assistant";
docs/future/HUB_AND_ENGINEER_PLAN.md part 2, step 2). The first parts need no CAD program: MIA writes them as STL
files (`stl`), the format every slicer opens (Bambu Studio is on his PC), from sizes he says.

**The parts** (`PARTS`), each worked out in millimetres from the inside size he gives, so what goes in fits:
- **an enclosure** (`enclosure`): an open box (a floor and four walls at his wall thickness) and its lid, a plate with
  a lip that sits inside the walls with a little clearance (`CLEARANCE`), for a sensor board, a relay or a battery;
  with mounting posts at a board's hole spacing (hollow, for M3 screws) and a cable hole in one end when asked;
- **a spacer** (`spacer`): a round standoff of a height and outer diameter, with its bore as a note (a hole is drilled
  or printed with the slicer's hole tool; this first maker makes solids only).

Each solid is built from boxes and prisms that touch or overlap, which slicers merge. **What it says**: each file's
path, its outside size, and its plastic as a solid volume and grams of PLA (1.24 g/cm³), said as the most it can
take: infill makes it less. Nothing is printed: opening the file in his slicer, and printing, are his.
"""

from __future__ import annotations

import math
import re
import struct
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

CLEARANCE = 0.4  # mm between a lid's lip and the walls: a snug fit on a typical FDM printer
PLA_G_PER_CM3 = 1.24


def _box(x0, y0, z0, x1, y1, z1) -> list[tuple]:
    """Pure logic. The 12 triangles of an axis-aligned box, outward-facing, as ((v1, v2, v3), ...)."""
    p = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
             (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7)]
    return [(p[a], p[b], p[c]) for a, b, c in faces]


def _cylinder(r: float, h: float, segments: int = 48) -> list[tuple]:
    """Pure logic. A cylinder's triangles (a prism of `segments` sides), standing on z=0."""
    tris = []
    ring = [(r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments)) for i in range(segments)]
    for i in range(segments):
        (ax, ay), (bx, by) = ring[i], ring[(i + 1) % segments]
        tris += [((0, 0, 0), (bx, by, 0), (ax, ay, 0)), ((0, 0, h), (ax, ay, h), (bx, by, h)),
                 ((ax, ay, 0), (bx, by, 0), (bx, by, h)), ((ax, ay, 0), (bx, by, h), (ax, ay, h))]
    return tris


def _tube(cx: float, cy: float, z0: float, h: float, outer: float, bore: float, segments: int = 32) -> list[tuple]:
    """Pure logic. A hollow post (a tube) standing at (cx, cy) from z0: its outside, its bore, and the rings at both
    ends; a solid post when the bore is 0."""
    if bore <= 0:
        return [tuple((x + cx, y + cy, z + z0) for x, y, z in tri) for tri in _cylinder(outer / 2, h, segments)]
    ro, ri, z1, tris = outer / 2, bore / 2, z0 + h, []
    pts = [(math.cos(2 * math.pi * i / segments), math.sin(2 * math.pi * i / segments)) for i in range(segments)]
    for i in range(segments):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % segments]
        oa, ob = (cx + ro * ax, cy + ro * ay), (cx + ro * bx, cy + ro * by)
        ia, ib = (cx + ri * ax, cy + ri * ay), (cx + ri * bx, cy + ri * by)
        tris += [((*oa, z0), (*ob, z0), (*ob, z1)), ((*oa, z0), (*ob, z1), (*oa, z1)),  # outside
                 ((*ia, z0), (*ib, z1), (*ib, z0)), ((*ia, z0), (*ia, z1), (*ib, z1)),  # the bore, facing in
                 ((*oa, z1), (*ob, z1), (*ib, z1)), ((*oa, z1), (*ib, z1), (*ia, z1)),  # the top ring
                 ((*oa, z0), (*ib, z0), (*ob, z0)), ((*oa, z0), (*ia, z0), (*ib, z0))]  # the bottom ring
    return tris


def stl(triangles: list[tuple], name: str = "MIA part") -> bytes:
    """Pure logic. A binary STL of these triangles (each normal worked out from its winding)."""
    out = [name.encode("ascii", "replace")[:80].ljust(80, b" "), struct.pack("<I", len(triangles))]
    for a, b, c in triangles:
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        length = math.sqrt(sum(x * x for x in n)) or 1.0
        out.append(struct.pack("<12fH", *(x / length for x in n), *a, *b, *c, 0))
    return b"".join(out)


POST_OUTER, POST_BORE, POST_HEIGHT = 6.0, 2.5, 5.0  # mm: an M3 screw self-taps a 2.5 mm bore in PLA
CABLE_HOLE = (8.0, 6.0)  # mm: wide by high, for a sensor or power lead


def enclosure(length: float, width: float, height: float, wall: float = 2.0, lid: float = 2.0,
              posts: Optional[tuple] = None, cable_hole: bool = False) -> dict:
    """Pure logic. An open box whose inside is length x width x height (mm) at this wall thickness, and its lid (a
    plate the box's outside size with a lip inside the walls): {"box": triangles, "lid": triangles, "outside",
    "volume_cm3", "posts", "cable_hole"}. `posts` (spacing along, across, in mm: a board's mounting holes) puts four
    hollow posts on the floor, centred, `POST_OUTER` across with a `POST_BORE` bore for M3 screws; `cable_hole` opens
    a `CABLE_HOLE` slot low in the first end wall, centred, the wall built around it."""
    L, W, H, t = length + 2 * wall, width + 2 * wall, height + wall, wall
    box = _box(0, 0, 0, L, W, t)  # the floor
    box += _box(0, 0, 0, L, t, H) + _box(0, W - t, 0, L, W, H) + _box(L - t, 0, 0, L, W, H)
    if cable_hole:  # the end wall at x=0 in four pieces around a slot just above the floor
        hw, hh = CABLE_HOLE
        ya, yb, za, zb = (W - hw) / 2, (W + hw) / 2, t + 2.0, t + 2.0 + hh
        box += (_box(0, 0, 0, t, ya, H) + _box(0, yb, 0, t, W, H) + _box(0, ya, 0, t, yb, za)
                + _box(0, ya, zb, t, yb, H))
    else:
        box += _box(0, 0, 0, t, W, H)
    placed = []
    if posts:
        along, across = posts
        for dx in (-along / 2, along / 2):
            for dy in (-across / 2, across / 2):
                cx, cy = L / 2 + dx, W / 2 + dy
                if t + POST_OUTER / 2 <= cx <= L - t - POST_OUTER / 2 and t + POST_OUTER / 2 <= cy <= W - t - POST_OUTER / 2:
                    box += _tube(cx, cy, t, POST_HEIGHT, POST_OUTER, POST_BORE)
                    placed.append((round(cx, 1), round(cy, 1)))
    lip_h, c = min(4.0, height / 3), CLEARANCE
    lid_tris = _box(0, 0, 0, L, W, lid)
    x0, y0, x1, y1 = t + c, t + c, L - t - c, W - t - c
    lid_tris += (_box(x0, y0, lid, x1, y0 + t, lid + lip_h) + _box(x0, y1 - t, lid, x1, y1, lid + lip_h)
                 + _box(x0, y0, lid, x0 + t, y1, lid + lip_h) + _box(x1 - t, y0, lid, x1, y1, lid + lip_h))
    box_solid = L * W * H - (L - 2 * t) * (W - 2 * t) * (H - t)  # the outside block less the hollow
    lip_ring = (x1 - x0) * (y1 - y0) - (x1 - x0 - 2 * t) * (y1 - y0 - 2 * t)
    post = math.pi * ((POST_OUTER / 2) ** 2 - (POST_BORE / 2) ** 2) * POST_HEIGHT
    volume = box_solid + L * W * lid + lip_ring * lip_h + post * len(placed) \
        - (CABLE_HOLE[0] * CABLE_HOLE[1] * t if cable_hole else 0)
    return {"box": box, "lid": lid_tris, "outside": (L, W, H + lid), "volume_cm3": round(volume / 1000, 1),
            "posts": placed, "cable_hole": cable_hole}


def spacer(height: float, outer: float, bore: float = 0.0) -> dict:
    """Pure logic. A round standoff (a solid; its bore is a note for the slicer or a drill): {"part", "outside",
    "volume_cm3"}."""
    r = outer / 2
    return {"part": _cylinder(r, height), "outside": (outer, outer, height),
            "volume_cm3": round(math.pi * (r * r - (bore / 2) ** 2) * height / 1000, 1), "bore": bore}


def _sizes(said: str) -> list[float]:
    """Pure logic. The millimetre sizes in his words ("80 by 50 by 30", "80x50x30 mm", "3 inches" as 76.2)."""
    text = (said or "").lower()
    inches = bool(re.search(r"\b(inch|inches|in\b|\")", text))
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    return [round(n * 25.4, 1) for n in numbers] if inches else numbers


def _folder(context) -> Path:
    """Where his parts are kept: the household's data folder's `prints`."""
    from core.data_root import DATA_DIR

    base = getattr(context, "home_dir", None) or DATA_DIR
    folder = Path(base) / "prints"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _slug(name: str) -> str:
    """Pure logic. A file name from a part's name ("Soil sensor box" is soil-sensor-box)."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "part").lower()).strip("-")[:40] or "part"


def _spacing(said: str) -> Optional[tuple]:
    """Pure logic. A board's mounting-hole spacing in his words ("58 by 23", "58x49 mm"), in mm, or None."""
    found = _sizes(said)
    return (found[0], found[1]) if len(found) >= 2 else None


def make(context, kind: str, sizes: str, name: str = "", wall: Optional[float] = None, posts: str = "",
         cable_hole: bool = False) -> str:
    """Makes a part's STL files in his prints folder from the sizes he said (an enclosure with mounting posts at a
    board's hole spacing and a cable hole when asked), and says where they are, their outside size and their most
    plastic; or what it needs, or a post that wouldn't fit inside."""
    kind = (kind or "").lower()
    found = _sizes(sizes)
    if "spacer" in kind or "standoff" in kind:
        if len(found) < 2:
            return "A spacer needs its height and outside diameter, like \"a spacer 10 mm tall, 8 mm across\"."
        part = spacer(found[0], found[1], found[2] if len(found) > 2 else 0.0)
        path = _folder(context) / f"{_slug(name or 'spacer')}.stl"
        path.write_bytes(stl(part["part"], name or "spacer"))
        said = (f"Made {path.name}: {part['outside'][0]:g} mm across, {part['outside'][2]:g} mm tall"
                + (f"; make its {part['bore']:g} mm bore with the slicer's hole tool or a drill" if part["bore"] else ""))
        grams = part["volume_cm3"] * PLA_G_PER_CM3
    else:
        if len(found) < 3:
            return ("An enclosure needs the inside size: length, width and height, like \"80 by 50 by 30 mm\" (the "
                    "board or part that goes in, plus room for wires).")
        spacing = _spacing(posts) if posts else None
        part = enclosure(found[0], found[1], found[2], wall if wall else 2.0, posts=spacing, cable_hole=cable_hole)
        slug = _slug(name or "enclosure")
        folder = _folder(context)
        (folder / f"{slug}-box.stl").write_bytes(stl(part["box"], f"{name or 'enclosure'} box"))
        (folder / f"{slug}-lid.stl").write_bytes(stl(part["lid"], f"{name or 'enclosure'} lid"))
        L, W, H = part["outside"]
        said = (f"Made {slug}-box.stl and {slug}-lid.stl: inside {found[0]:g} x {found[1]:g} x {found[2]:g} mm, outside "
                f"{L:g} x {W:g} x {H:g} mm with the lid on; the lid's lip sits {CLEARANCE:g} mm inside the walls")
        if spacing:
            said += (f"; {len(part['posts'])} mounting posts {spacing[0]:g} x {spacing[1]:g} mm apart, {POST_HEIGHT:g} mm "
                     f"tall with {POST_BORE:g} mm bores for M3 screws" if len(part["posts"]) == 4 else
                     f"; the posts {spacing[0]:g} x {spacing[1]:g} mm apart don't fit inside, so none were made")
        if cable_hole:
            said += f"; a {CABLE_HOLE[0]:g} x {CABLE_HOLE[1]:g} mm cable hole low in one end"
        grams = part["volume_cm3"] * PLA_G_PER_CM3
        path = folder / f"{slug}-box.stl"
    return (f"{said}. At most about {part['volume_cm3']:g} cm³ of plastic ({grams:.0f} g of PLA solid; infill makes "
            f"it less). They're in {path.parent}: open them in Bambu Studio to slice and print.")
