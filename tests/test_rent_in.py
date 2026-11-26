"""
tests.test_rent_in
====================

"The tenant paid $1800 today" is rent on his one rental (record_rental_income, the rentals conversation check
2026-11-26: "I don't have a property called 'the tenant'"); with several, the one named, else which.
"""

from types import SimpleNamespace

from core import assistant_turn


def _context(props):
    """His properties."""
    return SimpleNamespace(real_estate=SimpleNamespace(all_properties=lambda: props))


def test_rent_on_his_rental(monkeypatch):
    ran = []
    monkeypatch.setattr(assistant_turn, "_run_own", lambda c, n, a: ran.append((n, a)) or "Recorded.")
    one = [SimpleNamespace(name="123 Main St", property_type="Rental", sale_date="", status="Active")]
    for words in ("the tenant paid $1800 today", "rent came in, $1,800", "I got the rent, $1800"):
        assert assistant_turn._own_tool_reply(_context(one), words) == "Recorded.", words
    assert ran[0] == ("record_rental_income", {"property_name": "123 Main St", "amount": 1800.0})
    two = one + [SimpleNamespace(name="45 Oak Ave", property_type="Rental", sale_date="", status="Active")]
    assert assistant_turn._own_tool_reply(_context(two), "the tenant paid $900") .startswith("Which property?")
    assert assistant_turn._own_tool_reply(_context(two), "the tenant at oak paid $900") == "Recorded."
    assert ran[-1][1]["property_name"] == "45 Oak Ave"
