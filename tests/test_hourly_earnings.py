"""What his work really makes an hour (core/hourly_earnings.py): finished jobs' revenue less materials and expenses
over their hours, added up by hours, the best and lowest named, a finished job with no sale linked counted apart and
never as zero, a batch sold later from stock counted for the job that made it, wood never counted twice, a day-job
pay question told it's the workshop's, and the question reaching the tool."""

import pytest

from core import hourly_earnings as he
from tests.test_crafting import shop  # noqa: F401  (the fixture)


@pytest.fixture
def worked(shop):  # noqa: F811
    """Three finished jobs: a table (10 h, $400 in, $60 of expenses), a bench (4 h, $100 in), a shelf (3 h, no sale
    linked), and a planned one."""
    table = shop.jobs.add_job("Table", status="Complete", labor_hours=10)
    bench = shop.jobs.add_job("Bench", status="Complete", labor_hours=4)
    shop.jobs.add_job("Shelf", status="Complete", labor_hours=3)
    shop.jobs.add_job("Chair", status="Planned", labor_hours=2)
    shop.ledger.add_revenue(400, "table", job_id=table.job_id)
    shop.ledger.add_expense(60, "Supplies", job_id=table.job_id)
    shop.ledger.add_revenue(100, "bench", job_id=bench.job_id)
    return shop


def test_each_paid_job_per_hour_best_first_and_a_job_with_no_sale_apart(worked):
    paid, unlinked = he.per_job(worked)
    assert [(j["name"], j["per_hour"]) for j in paid] == [("Table", 34.0), ("Bench", 25.0)]
    assert unlinked == ["Shelf"]


def test_the_hourly_is_kept_over_hours_with_the_best_and_lowest(worked):
    said = he.say(worked)
    assert "you kept $440.00 for 14 hours" in said and "about $31.43 an hour" in said
    assert "Best: Table" in said and "lowest: Bench" in said and "Not counted: Shelf" in said


def test_a_batch_sold_later_from_stock_counts_for_the_job_that_made_it_and_wood_isnt_counted_twice(shop):  # noqa: F811
    from core.job_manager import MaterialConsumptionEntry, ProductionEntry

    product = shop.products.add_product("Coaster")
    job = shop.jobs.add_job("Coasters", status="Complete", labor_hours=5)
    job.products_produced.append(ProductionEntry(product_id=product.product_id, quantity_produced=10))
    job.material_consumption.append(MaterialConsumptionEntry(material_id="gone", quantity_used=1, unit_cost=10))
    shop.jobs._save()
    shop.ledger.add_revenue(30, "two", job_id=job.job_id)
    shop.ledger.add_revenue(120, "eight", product_id=product.product_id)
    shop.ledger.add_expense(10, "Materials", job_id=job.job_id)  # the same wood, entered as a build cost
    paid, _ = he.per_job(shop)
    assert paid[0]["per_hour"] == 28.0  # (150 - 10) / 5


def test_a_day_job_pay_question_is_told_its_the_workshops(worked):
    assert "not your day job's pay" in he.say(worked, "what do I really make an hour at my job?")
    assert "not your day job's pay" in he.say(worked, "what's my real hourly after taxes")
    from tests.assistant_registry import build_desktop_registry

    action = build_desktop_registry()._actions["earnings_per_hour"]
    assert action.direct_arguments("what do I really make an hour at work") == {"question": "what do I really make an hour at work"}


def test_asking_what_i_really_make_an_hour_or_what_my_builds_make_reaches_it(worked):
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    for said in ("what do I really make an hour?", "is the workshop worth my time?", "what do I make an hour on jobs?",
                 "how much do my builds make per hour", "what's my effective hourly rate"):
        assert "earnings_per_hour" in [a.name for a in registry.matching_actions(said, worked)], said
    for said in ("how much do I make an hour at my job?", "what's my hourly pay at work?"):
        assert "earnings_per_hour" not in [a.name for a in registry.matching_actions(said, worked)], said
