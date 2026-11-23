"""
tests.test_plan_price
=======================

What a Planner build costs and what to charge (core/plan_price.py, brainstorm 5.1): its materials priced from his
workshop (whole quantities: what's on hand gets used too), those with no price named, his hours at his rate, his
margin, through his quotes' own arithmetic; without his labor in it, a floor.
"""

from types import SimpleNamespace

from core import plan_price as pp


def _mat(name, cost, have=0):
    return SimpleNamespace(name=name, unit_cost=cost, quantity_on_hand=have)


ITEMS = [{"name": "2x4 x 8 ft", "qty": 20, "unit": "boards"}, {"name": "Plywood 4x8 sheet", "qty": 4, "unit": "sheets"},
         {"name": "Deck screws", "qty": 2, "unit": "boxes"}]


def test_materials_are_priced_whole_and_unpriced_ones_named():
    got = pp.costed(ITEMS, [_mat("2x4 x 8 ft", 4.25, have=10), _mat("Plywood 4x8 sheet", 38.0)])
    assert got["known"] == 20 * 4.25 + 4 * 38.0 and got["unpriced"] == ["Deck screws"]


def test_the_build_is_found_by_its_words_or_the_newest():
    plans = [SimpleNamespace(kind="build", status="draft", shelf_plan="shed", title="10x12 shed"),
             SimpleNamespace(kind="build", status="confirmed", shelf_plan="coop", title="Chicken coop"),
             SimpleNamespace(kind="garden", status="draft", shelf_plan="", title="Beds")]
    ctx = SimpleNamespace(project_plans=SimpleNamespace(listed=lambda: plans))
    assert pp.find(ctx, "the chicken coop").title == "Chicken coop"
    assert pp.find(ctx).title == "10x12 shed"
    assert pp.find(ctx, "greenhouse") is None


def test_the_price_uses_his_hours_rate_and_margin(monkeypatch):
    import core.plan_library as library

    monkeypatch.setattr(library, "detail", lambda context, plan, sizes=None: {"items": ITEMS[:2]})
    ctx = SimpleNamespace(
        project_plans=SimpleNamespace(listed=lambda: [SimpleNamespace(kind="build", status="draft", shelf_plan="shed",
                                                                      title="10x12 shed", sizes={})]),
        materials=SimpleNamespace(all_materials=lambda: [_mat("2x4 x 8 ft", 4.25), _mat("Plywood 4x8 sheet", 38.0)]),
        config=SimpleNamespace(get=lambda key, default=None: 30 if key == "workshop.labor_rate_per_hour" else default))
    said = pp.say(ctx, "shed", hours=10, margin=20)
    # (85 + 152 + 10 x 30) x 1.2 = 644.4, rounded up to a whole amount
    assert "materials $237.00" in said and "10 hours at $30.00 an hour" in said and "charge $645.00" in said
    assert "at least" not in said


def test_unpriced_materials_make_the_price_a_floor_and_no_build_says_how_to_start(monkeypatch):
    import core.plan_library as library

    monkeypatch.setattr(library, "detail", lambda context, plan, sizes=None: {"items": ITEMS})
    ctx = SimpleNamespace(
        project_plans=SimpleNamespace(listed=lambda: [SimpleNamespace(kind="build", status="draft", shelf_plan="shed",
                                                                      title="10x12 shed", sizes={})]),
        materials=SimpleNamespace(all_materials=lambda: [_mat("2x4 x 8 ft", 4.25)]), config=None)
    said = pp.say(ctx)
    assert "No price yet for Plywood 4x8 sheet, Deck screws" in said and "charge at least" in said
    assert "Start one there" in pp.say(SimpleNamespace(project_plans=None))


def test_without_labor_the_price_is_a_floor(monkeypatch):
    import core.plan_library as library

    monkeypatch.setattr(library, "detail", lambda context, plan, sizes=None: {"items": ITEMS[:1]})
    ctx = SimpleNamespace(
        project_plans=SimpleNamespace(listed=lambda: [SimpleNamespace(kind="build", status="draft", shelf_plan="shed",
                                                                      title="10x12 shed", sizes={})]),
        materials=SimpleNamespace(all_materials=lambda: [_mat("2x4 x 8 ft", 4.25)]), config=None)
    assert "charge at least" in pp.say(ctx)
