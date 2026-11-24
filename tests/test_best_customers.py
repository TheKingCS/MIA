"""Who his best customers are (core/best_customers.py): ranked by what's been paid on their orders (cancelled
ones left out), each one's share, the regulars with no order in six months named as gone quiet, a customer with no
orders not ranked, and the question reaching the tool."""

from datetime import date

from core import best_customers as bc
from tests.test_crafting import shop  # noqa: F401  (the fixture)

TODAY = date(2026, 11, 24)


def test_customers_rank_by_what_they_paid_and_a_quiet_regular_is_named(shop):  # noqa: F811
    from core.business_book import BusinessBook

    shop.business = book = BusinessBook(shop, data_dir=shop.home_dir)
    ann, bob = book.add_customer("Ann"), book.add_customer("Bob")
    book.add_customer("Cal")  # no orders: not ranked
    for title, who, when, paid in (("Table", ann, "2026-01-10", 400), ("Bench", ann, "2026-02-01", 150),
                                   ("Sign", bob, "2026-11-01", 80)):
        order = book.add_order(title, customer_id=who.customer_id)
        order.created_at = when + "T10:00:00"
        entry = shop.ledger.add_revenue(paid, title)
        order.payment_ids.append(entry.entry_id)
    cancelled = book.add_order("Shelf", customer_id=bob.customer_id, status="Cancelled")
    cancelled.payment_ids.append(shop.ledger.add_revenue(999, "refunded").entry_id)
    rows = bc.ranked(shop, TODAY)
    assert [(r["name"], r["paid"], r["orders"], r["quiet"]) for r in rows] == [("Ann", 550, 2, True), ("Bob", 80, 1, False)]
    said = bc.say(shop, TODAY)
    assert "Ann: $550.00 paid on 2 orders (87% of all)" in said and "Gone quiet" in said and "Ann (last 2026-02-01)" in said


def test_asking_for_my_best_customers_reaches_it(shop):  # noqa: F811
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    for said in ("who are my best customers?", "which customers haven't ordered in a while"):
        assert "best_customers" in [a.name for a in registry.matching_actions(said, shop)], said
