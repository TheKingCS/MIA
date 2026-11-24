"""Which products are priced below what they take (core/product_pricing.py): a piece's materials and hours from the
finished jobs that made it (shared when a job made two products), the least it should sell for at his quoting rate, the
underpriced named most first, a product no timed job made said as not worked out, and without a rate the time a piece
takes said and a rate asked for. A job making a table and coasters shares by value; hours come from timed jobs."""

from core import product_pricing as pp
from core.job_manager import MaterialConsumptionEntry, ProductionEntry
from tests.test_crafting import shop  # noqa: F401  (the fixture)


def _made(shop, name, price, hours, materials, pieces):  # noqa: F811
    """A product at a price, made by one finished job of these hours and materials cost into this many pieces."""
    product = shop.products.add_product(name, base_price=price)
    job = shop.jobs.add_job(f"{name} batch", status="Complete", labor_hours=hours)
    job.products_produced.append(ProductionEntry(product_id=product.product_id, quantity_produced=pieces))
    job.material_consumption.append(MaterialConsumptionEntry(material_id="x", quantity_used=1, unit_cost=materials))
    shop.jobs._save()
    return product


def test_a_product_under_its_materials_and_time_at_his_rate_is_named_first(shop):  # noqa: F811
    shop.config.set("workshop.labor_rate_per_hour", 30)
    _made(shop, "Cutting board", 25, 4, 40, 4)  # a piece: $10 materials, 1 hour: $40 at $30
    _made(shop, "Coaster set", 20, 1, 8, 4)  # a piece: $2, 15 minutes: $9.50
    shop.products.add_product("Bench", base_price=300)  # no job made it
    rows = pp.checked(shop)
    assert [(r["name"], r["floor"], r["gap"]) for r in rows if r["known"]] == [("Cutting board", 40.0, 15.0),
                                                                               ("Coaster set", 9.5, -10.5)]
    said = pp.say(shop)
    assert "Cutting board at $25.00, about $40.00 at your rate" in said and "Coaster set at" not in said
    assert "Not worked out (no finished job with hours made it): Bench." in said


def test_without_a_rate_the_time_a_piece_takes_is_said_and_a_rate_asked_for(shop):  # noqa: F811
    shop.config.set("workshop.labor_rate_per_hour", 0)
    _made(shop, "Cutting board", 25, 4, 40, 4)
    said = pp.say(shop)
    assert "haven't set the hourly rate" in said and "Cutting board $10.00 of materials and 60 minutes" in said


def test_asking_whether_i_charge_enough_reaches_it(shop):  # noqa: F811
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    for said in ("which products should I raise prices on?", "am I charging enough?"):
        assert "check_my_prices" in [a.name for a in registry.matching_actions(said, shop)], said


def test_review_a_job_making_a_table_and_coasters_shares_by_value_and_hours_come_from_timed_jobs(shop):  # noqa: F811
    from core.job_manager import ProductionEntry

    table = shop.products.add_product("Table", base_price=300)
    coaster = shop.products.add_product("Coaster", base_price=5)
    job = shop.jobs.add_job("Mixed", status="Complete", labor_hours=10)
    job.products_produced += [ProductionEntry(product_id=table.product_id, quantity_produced=1),
                              ProductionEntry(product_id=coaster.product_id, quantity_produced=10)]
    untimed = shop.jobs.add_job("More coasters", status="Complete", labor_hours=0)
    untimed.products_produced.append(ProductionEntry(product_id=coaster.product_id, quantity_produced=10))
    shop.jobs._save()
    pieces = pp.per_piece(shop)
    assert pieces[table.product_id]["hours"] > 8  # $300 of the job's $350 value: most of the ten hours
    assert pieces[coaster.product_id]["timed"]  # an untimed job doesn't make it "not worked out"
