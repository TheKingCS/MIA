"""Who his best customers are (core/best_customers.py): ranked by what's been paid on their orders (cancelled
ones left out), each one's share, the regulars with no order in six months named as gone quiet, a customer with no
orders not ranked, nobody with an order still open called quiet, a payment two orders name counted once, and the
question reaching the tool, never the workout tools ("my best" was a personal record's)."""

from datetime import date

from core import best_customers as bc
from tests.test_crafting import shop  # noqa: F401  (the fixture)

TODAY = date(2026, 11, 24)


def test_customers_rank_by_what_they_paid_and_a_quiet_regular_is_named_unless_something_is_open(shop):  # noqa: F811
    from core.business_book import BusinessBook

    shop.business = book = BusinessBook(shop, data_dir=shop.home_dir)
    ann, bob = book.add_customer("Ann"), book.add_customer("Bob")
    book.add_customer("Cal")  # no orders: not ranked
    for title, who, when, paid in (("Table", ann, "2026-01-10", 400), ("Bench", ann, "2026-02-01", 150),
                                   ("Sign", bob, "2026-11-01", 80)):
        order = book.add_order(title, customer_id=who.customer_id, status="Delivered")
        order.created_at = when + "T10:00:00"
        entry = shop.ledger.add_revenue(paid, title)
        order.payment_ids.append(entry.entry_id)
    cancelled = book.add_order("Shelf", customer_id=bob.customer_id, status="Cancelled")
    cancelled.payment_ids.append(shop.ledger.add_revenue(999, "refunded").entry_id)
    rows = bc.ranked(shop, TODAY)
    assert [(r["name"], r["paid"], r["orders"], r["quiet"]) for r in rows] == [("Ann", 550, 2, True), ("Bob", 80, 1, False)]
    said = bc.say(shop, TODAY)
    assert "Ann: $550.00 paid on 2 orders (87%)" in said and "all time" in said and "Ann (last 2026-02-01)" in said
    later = book.add_order("Chairs", customer_id=ann.customer_id, status="Building")
    later.created_at = "2026-03-01T10:00:00"
    assert not bc.ranked(shop, TODAY)[0]["quiet"]  # something still being built: not quiet


def test_a_payment_two_orders_name_counts_once(shop):  # noqa: F811
    from core.business_book import BusinessBook

    shop.business = book = BusinessBook(shop, data_dir=shop.home_dir)
    ann, bob = book.add_customer("Ann"), book.add_customer("Bob")
    first = book.add_order("Table", customer_id=ann.customer_id)
    first.created_at, first.job_ids = "2026-01-01T10:00:00", ["j1"]
    second = book.add_order("Bench", customer_id=bob.customer_id)
    second.created_at, second.job_ids = "2026-02-01T10:00:00", ["j1"]
    shop.ledger.add_revenue(100, "one sale", job_id="j1")
    assert {r["name"]: r["paid"] for r in bc.ranked(shop, TODAY)} == {"Ann": 100, "Bob": 0}


def test_asking_for_my_best_customers_or_my_best_customer_reaches_it(shop):  # noqa: F811
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    for said in ("who are my best customers?", "which customers haven't ordered in a while",
                 "what does my best customer usually order"):
        assert "best_customers" in [a.name for a in registry.matching_actions(said, shop)], said


def test_my_best_customers_never_bring_the_workout_tools_and_my_best_squat_still_does(shop):  # noqa: F811
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    assert "get_personal_record" not in [a.name for a in registry.matching_actions("who are my best customers?", shop)]
    for said in ("what's my best squat?", "what's my best on deadlift", "what's my personal record on bench press"):
        assert "get_personal_record" in [a.name for a in registry.matching_actions(said, shop)], said
