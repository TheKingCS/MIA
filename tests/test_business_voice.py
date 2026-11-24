"""
tests.test_business_voice
===========================

His business by voice (core/assistant_business_voice_actions.py, DEC-0125): the quotes still out, the open orders, a
customer's details, adding a customer, making a quote for a customer he has, a quote accepted (it becomes an order,
due when he says), an order marked delivered; each change through the Business page's own action, with "undo that".
"""

from datetime import date, timedelta

import pytest

from core import assistant_business_voice_actions as bv
from tests.test_business import shop  # noqa: F401  (the fixture: the crafting world with a business book)


@pytest.fixture
def biz(shop):  # noqa: F811
    """The crafting world with one customer and nothing quoted yet."""
    shop.business.add_customer("Dana Reyes", phone="555-0100", email="dana@example.com")
    return shop


def test_a_customer_is_added_and_read_back(biz):
    assert "Sam Ortiz" in bv._action_add_customer(biz, {"name": "Sam Ortiz", "phone": "555-0199"})
    assert bv._action_customer_details(biz, {"customer": "sam"}) == "Sam Ortiz: phone 555-0199."
    assert bv._action_add_customer(biz, {}) == "What's the customer's name?"


def test_a_quote_is_made_listed_accepted_and_delivered(biz):
    said = bv._action_make_quote(biz, {"title": "Cedar chest", "customer": "dana", "price": 900})
    assert "Cedar chest" in said
    assert bv._action_list_quotes(biz, {}).startswith("1 quote out: Cedar chest for Dana Reyes,")
    due = (date.today() + timedelta(days=3)).isoformat()
    assert "is an order now" in bv._action_accept_quote(biz, {"quote": "cedar", "due": due})
    assert bv._action_list_quotes(biz, {}) == "No quotes are out right now."
    assert "Cedar chest for Dana Reyes" in bv._action_list_orders(biz, {})
    bv._action_order_status(biz, {"order": "dana", "status": "delivered"})
    assert bv._action_list_orders(biz, {}) == "No open orders right now."


def test_a_customer_he_doesnt_have_is_said_not_made_up(biz):
    said = bv._action_make_quote(biz, {"title": "Bench", "customer": "Pat"})
    assert "I don't see a customer called pat" in said and not biz.business.quotes
