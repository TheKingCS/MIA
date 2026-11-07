"""
tests.test_plan_library
=========================

The Library's plans shelf (core/plan_library.py) and the material lists
behind it (core/build_calcs.py): boards packed into stock lengths, each
calculator's counts checked by hand, plans found by name, kept and read
from files, a shopping list against the workshop's stock, the tools, the
homestead, garden and woodworking projects, and cut lists of a person's
own parts.
"""

from __future__ import annotations

import math

import pytest

from core import build_calcs as calcs
from core.assistant_actions import AssistantActionRegistry
from core.assistant_plan_actions import register_plan_actions, sizes_for, structure_for
from core.material_manager import MaterialManager
from core.plan_library import BUILT_IN, PlanLibrary, shopping_list
from core.project_manager import ProjectManager
from tests.engine_world import build_world


def _qty(result, name):
    """The quantity of the item whose name starts with these words."""
    return next(i.qty for i in result.items if i.name.startswith(name))


def test_boards_packed_into_stock():
    """Two halves fit one board (a saw cut short), three 8 ft cuts take three 8s, and a cut past 16 ft is spliced."""
    assert calcs.buy_boards([120, 120]) == (10, 2)
    assert calcs.buy_boards([96] * 3) == (8, 3)
    assert calcs.buy_boards([120, 120], stock=(20,)) == (20, 1)
    assert calcs.buy_boards([200])[1] == 2
    assert calcs.stock_for(7.6) == 8 and calcs.stock_for(30) == 16
    assert calcs.inches(91.5) == "91 1/2 in" and calcs.inches(144) == "12 ft"
    assert calcs.joist_for(12) == "2x8" and calcs.joist_for(20) == ""


def test_the_calculators_by_hand():
    """A 12 ft wall with a 3 ft door: 12 studs (14 with waste) and a 2x6 header; a 100 ft fence with a gate: 15
    posts, about two bags a post, 241 pickets; a 10 x 12 slab: 1.63 cu yd; a 12 x 16 deck: 2x8 joists, 26 rows of
    boards; a 4 x 8 bed: 6 boards and 1.09 cu yd of soil; every structure says to check the code."""
    wall = calcs.stud_wall(12, 8, openings=(3,))
    assert _qty(wall, "2x4 x 8 ft") == 14 and wall.cuts[0].qty == 12 and _qty(wall, "2x6") == 2
    fence = calcs.fence(100, 6, gates=1)
    assert _qty(fence, "4x4") == 15 and _qty(fence, "80 lb") == 29 and _qty(fence, "6 in x 6 ft") == 241
    slab = calcs.concrete_slab(10, 12)
    assert _qty(slab, "concrete") == 1.63 and _qty(slab, "#4 rebar") == 13
    deck = calcs.floor_frame(12, 16, surface="decking")
    assert _qty(deck, "2x8 x 12 ft") == 15 and _qty(deck, "5/4x6") == math.ceil(26 * 1.1)
    bed = calcs.raised_bed(8, 4)
    assert _qty(bed, "2x6 x 8 ft") == 6 and _qty(bed, "soil") == 1.09
    assert calcs.CODE_NOTE in wall.notes and calcs.CODE_NOTE in deck.notes
    assert any("beam" in n for n in calcs.floor_frame(24, 16).notes)


def test_a_shed_keeps_what_each_board_is_for():
    """A shed merges same-size lumber but still says what it's for, once each."""
    shed = calcs.shed(8, 10)
    two_by_six = next(i for i in shed.items if i.name == "2x6 x 8 ft")
    assert "joists" in two_by_six.note and "rafters" in two_by_six.note
    studs = next(i for i in shed.items if i.name == "2x4 x 8 ft")
    assert studs.note.count("studs") == 1
    assert "shingles" in shed.to_text()


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The shared test world with a plans shelf (and a plans folder holding two files), materials and projects."""
    context = build_world(tmp_path, monkeypatch)
    folder = tmp_path / "plans"
    (folder / "woodworking").mkdir(parents=True)
    (folder / "woodworking" / "adirondack_chair.pdf").write_bytes(b"%PDF")
    (folder / "chicken-coop-4x6.png").write_bytes(b"png")
    context.plans = PlanLibrary(context, data_dir=tmp_path, files_dir=folder)
    context.materials = MaterialManager(context, data_dir=tmp_path)
    context.projects = ProjectManager(context, data_dir=tmp_path)
    context.assistant_actions = AssistantActionRegistry()
    register_plan_actions(context.assistant_actions)
    return context


def tool(context, tool_name, **arguments):
    """Runs one plans tool as the Assistant would."""
    return context.assistant_actions._actions[tool_name].handler(context, arguments)


def test_the_shelf(world):
    """Built-in plans, kept plans and files are found by name (a built-in coop first, a coop file among the
    results); a kept plan comes back after a restart and can be let go."""
    assert {p["id"] for p in world.plans.built_in()} == {f"builtin:{p['id']}" for p in BUILT_IN}
    assert world.plans.best("shed")["id"] == "builtin:gable-shed"
    chair = world.plans.best("adirondack chair")
    assert chair["kind"] == "woodworking" and chair["path"].endswith(".pdf")
    found = [p["id"] for p in world.plans.find("chicken coop")]
    assert found[0] == "builtin:chicken-coop" and any(i.startswith("file:") for i in found)
    kept = world.plans.keep("Goat shelter", "homestead", "Three-sided, 8 x 12.")
    assert PlanLibrary(world, data_dir=world.plans.data_dir).get(kept["id"])["title"] == "Goat shelter"
    assert world.plans.delete(kept["id"]) and world.plans.get(kept["id"]) is None


def test_a_shopping_list_against_the_workshop(world):
    """What's on hand comes off what to buy, priced where a unit cost is known."""
    world.materials.add_material(name="2x6 x 8 ft", unit="board", unit_cost=7.5, quantity_on_hand=2)
    found = shopping_list(world, calcs.raised_bed(8, 4).as_dict())
    row = next(r for r in found["rows"] if r["item"] == "2x6 x 8 ft")
    assert row["have"] == 2 and row["buy"] == 4 and row["cost"] == 30.0 and found["priced"] == 1


def test_the_tools(world):
    """Asked for a 10 x 12 shed, she works it out (and keeps it when asked); she finds plans, shows a built-in one at
    another size, says what to buy, points to free plans when the shelf has none, and starts a project."""
    said = tool(world, "material_list", structure="10 by 12 shed", width_ft=10, length_ft=12, keep=True)
    assert "10 x 12 ft gable shed" in said and "Kept" in said
    assert "Gable shed" in tool(world, "find_plans", query="shed")
    assert "6 x 3 ft raised bed" in tool(world, "show_plan", name="raised bed", length_ft=6, width_ft=3)
    assert "To buy" in tool(world, "plan_shopping_list", name="fence")
    assert "trace.tennessee.edu" in tool(world, "find_plans", query="sawmill")
    assert "Started the project" in tool(world, "start_plan_project", name="workbench")
    assert world.projects.all_projects()[0].name.startswith("6 x 2 ft workbench")
    assert structure_for("a planter box") == "raised_bed" and structure_for("a rocket") == ""
    assert sizes_for("raised_bed", {"length_ft": 8, "width_ft": 4, "height_ft": 2}) == {
        "length_ft": 8, "width_ft": 4, "height_in": 24}


def test_sizes_as_a_small_model_sends_them():
    """A size as said wins and is width, length, height; zeros mean not given; "false" is false."""
    from core.assistant_plan_actions import _yes, size_words

    assert size_words("10 by 12") == (10, 12) and size_words("4x8x2") == (4, 8, 2)
    assert sizes_for("shed", {"size": "10 by 12", "width_ft": 12, "length_ft": 12, "height_ft": 0}) == {
        "width_ft": 10, "length_ft": 12}
    assert sizes_for("raised_bed", {"size": "4x8x2"})["height_in"] == 24
    assert not _yes("false") and not _yes("False") and _yes(True)


def test_the_library_page(world, tmp_path):
    """The shelf lists every plan with where it's from; a plan opens with its materials, cuts as a person reads
    them, and steps; a file plan's file is served only from inside the plans folder."""
    from core.plan_library import detail, file_path, screen

    shelf = screen(world)
    assert shelf["available"] and any(p["where"] == "Your file" for p in shelf["plans"]) and shelf["sources"]
    assert [p["title"] for p in screen(world, "fence")["plans"]] == ["Wood privacy fence"]
    bed = detail(world, "builtin:raised-bed")
    assert bed["items"] and bed["cuts"][0]["length"] == "8 ft" and bed["steps"]
    assert detail(world, "builtin:nothing") is None
    assert file_path(world, "file:woodworking/adirondack_chair.pdf").name == "adirondack_chair.pdf"
    (tmp_path / "secret.txt").write_text("not a plan")
    assert file_path(world, "file:../secret.txt") is None and file_path(world, "builtin:raised-bed") is None


def test_homestead_garden_and_woodworking_projects():
    """8 hens get a 4 x 8 coop (4 sq ft each) and a 20 ft run (10 sq ft each) in hardware cloth; a 30 in rise gets
    four 7 1/2 in risers and the handrail note; a firewood rack says how much it holds; every new calculator works
    out at its plan's own size."""
    coop = calcs.chicken_coop(hens=8)
    assert coop.params["width_ft"] * coop.params["length_ft"] == 32 and "4 x 20 ft" in coop.to_text()
    assert any("hardware cloth" in n for n in coop.notes)
    steps = calcs.stairs(30)
    assert "4 risers of 7 1/2 in" in steps.notes[0] and any("handrail" in n for n in steps.notes)
    assert _qty(steps, "2x12") == 4
    assert "0.33 cord" in calcs.firewood_rack(8, 4).notes[0]
    assert _qty(calcs.shelving(8, 24, 6, 4), "3/4 in plywood") == 2
    assert any("sag" in n for n in calcs.bookshelf(width_in=48).notes)
    for plan in BUILT_IN:
        assert calculate_ok(plan)


def calculate_ok(plan) -> bool:
    """A built-in plan's calculator gives a list with items at the plan's own size."""
    from core.plan_library import calculate

    return bool(calculate(plan["calc"], **plan["args"]).items)


def test_a_cut_list_of_your_own_parts():
    """Parts said plainly are read (count, name, length, sheet width, material), boards and sheets are packed, and
    the tool keeps it as a plan when asked."""
    from core.assistant_plan_actions import parse_parts

    parts = parse_parts("4 legs at 30 in 2x4; 2 sides 11 1/4 x 72 in 3/4 plywood\n6 slats 3 ft 1x4\nnothing here")
    assert [(p["name"], p["qty"], p["length_in"], p["material"]) for p in parts] == [
        ("legs", 4, 30, "2x4"), ("sides", 2, 72, "3/4 plywood"), ("slats", 6, 36, "1x4")]
    assert parts[1]["width_in"] == 11.25
    result = calcs.custom_cuts(parts, "a tool cabinet")
    assert _qty(result, "2x4 x") == 1 and _qty(result, "3/4 plywood 4x8") == 1 and _qty(result, "1x4") >= 2
    assert calcs.sheets_for([(24, 48)] * 4) == 1 and calcs.sheets_for([(24, 48)] * 5) == 2


def test_the_new_projects_by_chat(world):
    """Asked in words, she picks the right project and size: deck stairs, a hen house for 12, 8 by 6 shelves, and a
    cut list she keeps."""
    assert "stairs for a 30 in rise" in tool(world, "material_list", structure="deck stairs", rise_in=30)
    assert "for 12 hens" in tool(world, "material_list", structure="hen house", count=12)
    assert "8 ft garage shelving" in tool(world, "material_list", structure="garage shelves", size="8 by 6")
    said = tool(world, "cut_list", parts="4 legs at 30 in 2x4; 1 top 24 by 48 mdf", title="potting bench",
                keep="true")
    assert "Cut list for potting bench" in said and world.plans.best("potting bench")
    assert structure_for("woodshed") == "lean_to" and structure_for("a bookcase") == "bookshelf"
