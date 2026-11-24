"""Parts to 3D print made in code (core/print_parts.py): a binary STL every slicer reads, an enclosure whose inside is
the size asked and whose lid's lip clears the walls, a spacer, sizes read in millimetres or inches, the files kept
in his prints folder, and the request reaching the tool.
Mounting posts at a board's spacing (or none when they wouldn't fit) and a cable hole; every shape faces outward, so
a slicer reads it solid."""

import struct
from types import SimpleNamespace

from core import print_parts as pp


def _read(data: bytes):
    """The triangle count and the outside bounds of a binary STL."""
    count = struct.unpack("<I", data[80:84])[0]
    xs, ys, zs = [], [], []
    for i in range(count):
        values = struct.unpack("<12f", data[84 + 50 * i:84 + 50 * i + 48])
        for v in range(3):
            xs.append(values[3 + 3 * v]); ys.append(values[4 + 3 * v]); zs.append(values[5 + 3 * v])  # noqa: E702
    assert len(data) == 84 + 50 * count
    return count, (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def test_an_enclosures_inside_is_the_size_asked_and_its_lid_clears_the_walls():
    part = pp.enclosure(80, 50, 30, wall=2)
    count, x, y, z = _read(pp.stl(part["box"]))
    assert count == 60 and x == (0, 84) and y == (0, 54) and z == (0, 32)  # 80 + two 2 mm walls; floor 2
    _, lx, ly, lz = _read(pp.stl(part["lid"]))
    assert lx == (0, 84) and lz[1] > 2  # the plate the box's size, its lip above it
    assert part["volume_cm3"] > 0


def test_sizes_are_read_in_millimetres_or_inches():
    assert pp._sizes("80 by 50 by 30 mm") == [80, 50, 30]
    assert pp._sizes("3 by 2 by 1 inches") == [76.2, 50.8, 25.4]


def test_parts_are_kept_in_his_prints_folder(tmp_path):
    context = SimpleNamespace(home_dir=tmp_path)
    said = pp.make(context, "enclosure", "80 by 50 by 30 mm", "soil sensor box")
    assert "soil-sensor-box-box.stl and soil-sensor-box-lid.stl" in said and "outside 84 x 54 x 34 mm" in said
    assert (tmp_path / "prints" / "soil-sensor-box-lid.stl").exists()
    assert "needs the inside size" in pp.make(context, "enclosure", "80 mm")
    assert "Made spacer.stl" in pp.make(context, "spacer", "10 mm tall 8 mm across 3 bore")


def test_asking_for_an_enclosure_reaches_the_tool():
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    for said in ("make me an enclosure for a sensor board 80 by 50 by 30 mm", "3d print a spacer 10 mm tall"):
        assert "design_print_part" in [a.name for a in registry.matching_actions(said, context)], said


def test_mounting_posts_at_a_boards_spacing_and_a_cable_hole(tmp_path):
    part = pp.enclosure(80, 50, 30, posts=(58, 23), cable_hole=True)
    assert part["posts"] == [(13.0, 15.5), (13.0, 38.5), (71.0, 15.5), (71.0, 38.5)]
    _, x, y, z = _read(pp.stl(part["box"]))
    assert x == (0, 84) and z == (0, 32)
    said = pp.make(SimpleNamespace(home_dir=tmp_path), "enclosure", "80 by 50 by 30", posts="58 by 23",
                   cable_hole=True)
    assert "4 mounting posts 58 x 23 mm apart" in said and "8 x 6 mm cable hole" in said
    assert "don't fit inside" in pp.make(SimpleNamespace(home_dir=tmp_path), "enclosure", "40 by 30 by 20",
                                         posts="60 by 40")


def test_every_shape_faces_outward_so_a_slicer_reads_it_solid():
    import math

    def volume(tris):
        """The signed volume of a mesh: positive only when its faces point out."""
        return sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                    + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6 for a, b, c in tris)

    assert volume(pp._box(0, 0, 0, 2, 3, 4)) == 24
    assert abs(volume(pp._tube(10, 10, 0, 5, 6, 2.5)) - math.pi * (9 - 1.5625) * 5) < 1.5
    assert abs(volume(pp._cylinder(3, 5)) - math.pi * 45) < 1.5
