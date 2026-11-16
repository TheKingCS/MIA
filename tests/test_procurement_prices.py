"""
tests.test_procurement_prices
===============================

Procurement P2 (DEC-0172; core/product_specs.py, core/price_book.py, core/price_actions.py,
core/assistant_price_actions.py): specifications are read from words with their units, and a product is judged
identical, equivalent, similar or not suitable by numbers, never by its title; prices are kept per product with
where and when, a price is judged only against what's been seen (never with fewer than three), a "was" price above
anything seen is called out; total cost names every part and counts an unknown one as unknown, not zero; and the
actions, the Needs tab and the voice tools agree.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import product_specs
from core.actions import ACTION_TYPES, ActionError
from core.price_book import PriceBook, judge, money_in, product_key, total_cost

NOW = datetime(2026, 11, 15, 9, 0)


def test_specifications_are_read_with_their_units_and_unknowns_are_left_out():
    assert product_specs.read("Submersible pump 800 GPH, max head 10 ft, 120V, 45W") == {
        "flow_gph": 800.0, "head_ft": 10.0, "watts": 45.0, "volts": 120.0, "submersible": True}
    assert product_specs.read("Pump 10 GPM") == {"flow_gph": 600.0}
    assert product_specs.read("2x4 x 8 ft pressure treated stud") == {"length_ft": 8.0, "treated": True, "nominal": "2x4"}
    assert product_specs.read("6 mil UV-resistant greenhouse film 12 ft wide") == {
        "thickness_mm": 0.152, "width_ft": 12.0, "uv": True}
    assert product_specs.read("DS18B20 temperature sensor probe 1-wire 3.3 V")["interface"] == "1-wire"
    assert "measures" not in product_specs.read("pressure treated 4x4 post")  # not a sensor


def test_two_pumps_with_the_same_watts_are_not_the_same_when_their_flow_differs():
    need = "aquaponics pump 600 gph 120 V"
    weak = product_specs.verdict(need, "Fountain pump 400 GPH 120V 45W")
    strong = product_specs.verdict(need, "Pond pump 800 GPH 120V 45W")
    assert weak["verdict"] == "not suitable" and "flow: 400 fails 600 needed" in weak["reasons"]
    assert strong["verdict"] == "equivalent"
    assert product_specs.verdict("pump 600 gph head 4 ft", "Pond pump 1000 GPH") == {
        "verdict": "similar", "category": "pump", "reasons": ["flow: 1000 meets 600 needed"], "unknown": ["head"]}
    assert product_specs.verdict("AC-1234 fan", "Exhaust fan AC-1234, 16 inch")["verdict"] == "identical"


def test_a_price_is_judged_only_against_prices_seen_and_never_from_too_few(tmp_path):
    book = PriceBook(SimpleNamespace(), data_dir=tmp_path)
    for days, price, store in ((60, 4.29, "Lowe's"), (30, 3.98, "Menards"), (5, 4.10, "Walmart")):
        book.record("2x4 x 8 ft stud", store, price, at=(NOW - timedelta(days=days)).isoformat())
    seen = book.for_item("stud 2x4 x 8 ft")  # the same product, words in another order
    assert len(seen) == 3 and seen[0].store == "Lowe's"
    assert judge(seen[:2], 3.50, NOW)["verdict"] == "too_few"
    assert judge(seen, 3.79, NOW)["verdict"] == "low" and judge(seen, 4.00, NOW)["verdict"] == "usual"
    assert judge(seen, 4.49, NOW)["verdict"] == "high"
    assert "higher than any price I've seen" in judge(seen, 3.79, NOW, was=6.99)["was_note"]
    assert [o.store for o in book.best("2x4 x 8 ft stud", days=100000)] == ["Menards", "Walmart", "Lowe's"]
    assert product_key("VIVOSUN pump VS-800GPH") == "model:VS-800GPH" and money_in("about $1,299.50") == 1299.5


def test_total_cost_names_every_part_and_never_counts_an_unknown_as_zero():
    cost = total_cost(3.98, 12, tax_rate=0.06, miles=18)
    assert cost["known_total"] == 50.63 and cost["unknown"] == ["shipping", "trip"]
    assert next(p for p in cost["parts"] if p["what"] == "trip")["how"] == "your cost per mile isn't set"
    full = total_cost(3.98, 12, shipping=0, tax_rate=0.06, miles=18, cost_per_mile=0.17)
    assert full["unknown"] == [] and full["known_total"] == round(47.76 + 2.87 + 6.12, 2)


@pytest.fixture
def context(tmp_path, monkeypatch):
    """A greenhouse project needing fans, the price book, and the person's settings held in a dict."""
    from core import person_settings
    from core.requirements import RequirementBook

    settings = {}
    monkeypatch.setattr(person_settings, "get", lambda ctx, key, default=None: settings.get(key, default))
    monkeypatch.setattr(person_settings, "put", lambda ctx, key, value: settings.__setitem__(key, value))
    project = SimpleNamespace(project_id="p1", name="Greenhouse", description="", status="Active")
    ctx = SimpleNamespace(projects=SimpleNamespace(all_projects=lambda: [project]), settings=settings,
                          materials=SimpleNamespace(all_materials=lambda: []), inventory=SimpleNamespace(all_items=lambda: []))
    ctx.requirements = RequirementBook(ctx, data_dir=tmp_path / "needs")
    ctx.prices = PriceBook(ctx, data_dir=tmp_path / "prices")
    ctx.requirements.add("p1", "exhaust fan", 2, specs="1000 cfm 120 V")
    return ctx


def test_recording_prices_and_the_trip_cost_through_the_actions(context):
    run = lambda kind, **p: (ACTION_TYPES[kind].describe(context, p), ACTION_TYPES[kind].execute(context, p))  # noqa: E731
    said, done = run("price.record", item="exhaust fan 16 inch 1200 CFM 120V", store="Tractor Supply", price="$89.99")
    assert said.startswith("Keep the price: exhaust fan") and done.startswith("Kept: exhaust fan")
    with pytest.raises(ActionError):
        ACTION_TYPES["price.record"].describe(context, {"item": "fan", "store": "", "price": "5"})
    said, done = run("price.trip_cost", mpg="17", fuel_price="2.89")
    assert "0.17 a mile" in said and context.settings["procurement.mpg"] == 17.0
    from core.price_book import cost_per_mile

    assert cost_per_mile(context) == 0.17


def test_comparing_a_need_says_each_stores_fit_and_total_and_what_isnt_known(context):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_price_actions import register_price_actions
    from core.web_world_intel import needs

    context.prices.record("exhaust fan", "Tractor Supply", 89.99, specs="1200 cfm 120 V")
    context.prices.record("exhaust fan", "Amazon", 59.99, specs="800 cfm 120 V")
    registry = AssistantActionRegistry()
    register_price_actions(registry)
    said = registry.execute(context, "compare_need", {"project": "greenhouse", "item": "exhaust fan"})
    assert said.startswith("For exhaust fan: Amazon: $59.99 each")
    assert "plus shipping, tax not known" in said and "Tell me your truck's miles per gallon" in said
    [line] = needs(context)[0]["lines"]
    assert [p["store"] for p in line["prices"]] == ["Amazon", "Tractor Supply"]
    assert "I've only seen it" in line["prices"][0]["compared"]
    said = registry.execute(context, "check_price", {"item": "exhaust fan", "price": "$49"})
    assert said.startswith("I haven't seen this exact one") and "Amazon $59.99 (exhaust fan)" in said
    said = registry.execute(context, "check_price", {"item": "exhaust fan", "price": "$80", "specs": "1200 cfm 120 V"})
    assert said.startswith("I've only seen it 1 time")


def test_a_shared_measurement_is_never_a_shared_model():
    """Fable's review (DEC-0174): a pump and a box fan that both said 120VAC were judged identical."""
    from core.product_specs import models, verdict

    assert models("submersible pump 500GPH 120VAC 2x4x8 SCH40 10-PACK 100CFM 12VDC 3-4IN AWG12 IP67") == set()
    assert models("Acme DB-1200 pump, also sold as WX9000A") == {"DB-1200", "WX9000A"}
    assert verdict("pump 500GPH 120VAC", "box fan 120VAC 20 inch")["verdict"] != "identical"
    assert verdict("pump DB-1200 500 gph", "Acme DB-1200 pump")["verdict"] == "identical"


def test_a_price_keeps_only_a_web_address_as_its_link_and_trip_figures_cant_be_negative_or_zero(context):
    """Fable's review (DEC-0174)."""
    from core import actions
    from core.actions import ActionError

    assert context.prices.record("2x4 stud", "A store", 3.98, link="javascript:alert(1)").link == ""
    assert context.prices.record("2x4 stud", "A store", 3.98, link="https://example.org/p").link == "https://example.org/p"
    trip = actions.ACTION_TYPES["price.trip_cost"]
    for bad in ({"cost_per_mile": "-1"}, {"mpg": "0", "fuel_price": "2.89"}, {"mpg": "17", "fuel_price": "-2"}):
        with pytest.raises(ActionError):
            trip.describe(context, bad)
        with pytest.raises(ActionError):
            trip.execute(context, bad)
