"""Inbox (DEC-0113): each item says in one line where filing it would put it (core/web_inbox.goes_to). Pure
logic, so it runs without Qt."""


def test_each_item_says_where_filing_it_would_put_it():
    from core.web_inbox import goes_to

    truck = {"name": "Truck"}
    assert goes_to(truck, "Garage", None, "", 1, True) == "Garage · Truck (its costs, 1 maintenance step)"
    assert goes_to(None, "", "Chicken coop", "", 0, True) == "Builds · Chicken coop costs"
    assert goes_to(None, "", None, "Groceries", 0, True) == "Money · Groceries"
    assert goes_to(truck, "Garage", None, "", 0, False) == "Garage · Truck (its documents)"
    assert goes_to(None, "", None, "", 0, False) == "Documents"
