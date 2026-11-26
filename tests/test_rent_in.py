"""
tests.test_rent_in
====================

"The tenant paid $1800 today" is rent on his one rental (record_rental_income, the rentals conversation check
2026-11-26: "I don't have a property called 'the tenant'"); with several, the one named, else which; never his own
rent ("rent was paid"), never the same payment twice.
"""

from types import SimpleNamespace

from core import assistant_turn


def _context(props, income=()):
    """His properties, and the rent already kept today."""
    return SimpleNamespace(real_estate=SimpleNamespace(all_properties=lambda: props,
                                                       income_for_property=lambda pid, a=None, b=None: list(income)))


def test_rent_on_his_rental(monkeypatch):
    ran = []
    monkeypatch.setattr(assistant_turn, "_run_own", lambda c, n, a: ran.append((n, a)) or "Recorded.")
    one = [SimpleNamespace(name="123 Main St", property_type="Rental", sale_date="", status="Active", property_id="p1")]
    for words in ("the tenant paid $1800 today", "rent came in, $1,800", "I got the rent, $1800"):
        assert assistant_turn._own_tool_reply(_context(one), words) == "Recorded.", words
    assert ran[0] == ("record_rental_income", {"property_name": "123 Main St", "amount": 1800.0})
    two = one + [SimpleNamespace(name="45 Oak Ave", property_type="Rental", sale_date="", status="Active", property_id="p2")]
    assert assistant_turn._own_tool_reply(_context(two), "the tenant paid $900") .startswith("Which property?")
    assert assistant_turn._own_tool_reply(_context(two), "the tenant at oak paid $900") == "Recorded."
    assert ran[-1][1]["property_name"] == "45 Oak Ave"


def test_never_his_own_rent_or_a_second_time(monkeypatch):
    ran = []
    monkeypatch.setattr(assistant_turn, "_run_own", lambda c, n, a: ran.append((n, a)) or "Recorded.")
    one = [SimpleNamespace(name="123 Main St", property_type="Investment", sale_date="", status="Rented",
                           property_id="p1")]
    for words in ("rent was paid $1200", "rent got paid $1200"):
        assert assistant_turn._own_tool_reply(_context(one), words) != "Recorded.", words
    assert assistant_turn._own_tool_reply(_context(one), "the tenant paid $1800") == "Recorded."
    paid = [SimpleNamespace(amount=1800.0)]
    assert assistant_turn._own_tool_reply(_context(one, paid), "the tenant paid $1800").startswith("I already have")
    assert len(ran) == 1
