"""
tests.test_web_businesses
===========================

Finances › Businesses (DEC-0153, core/web_businesses.py): each business at a glance from its own tagged money, open
orders and quotes and properties; one business's own dashboard; Orders & Quotes for one business (and the ones not
sorted yet); a quote and the order it becomes keep their business; and both by voice.
"""

from datetime import date

import pytest

import core.config_manager as config_module
from core.actions import ACTION_TYPES, ActionError
from core.app_context import AppContext
from core.assistant_business_view_actions import _action_get_business, _action_get_businesses
from core.budget_manager import BudgetManager
from core.business_book import BusinessBook
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.real_estate_manager import RealEstateManager
from core.web_business import business_page
from core.web_businesses import business_dashboard, businesses_page

TODAY = date(2026, 11, 11)


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """Money with two businesses (a rental LLC and a woodshop), a property, tagged money, a debt, and the business book
    with one quote for the woodshop and one order not sorted yet."""
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    folder = tmp_path / "data"
    context.budget = BudgetManager(context, data_dir=folder)
    context.business = BusinessBook(context, data_dir=folder)
    context.real_estate = RealEstateManager(context, data_dir=folder)
    rentals = context.budget.add_business_entity("Maple Rentals LLC")
    shop = context.budget.add_business_entity("Oak & Pine Woodshop", "Sole Proprietorship")
    context.real_estate.add_property("12 Maple St", entity_id=rentals.entity_id)
    context.budget.add_income(1500.0, "Rental", "November rent", date="2026-11-03", entity_id=rentals.entity_id)
    context.budget.add_expense(200.0, "Repairs", "Furnace part", date="2026-11-05", entity_id=rentals.entity_id)
    context.budget.add_expense(90.0, "Supplies", "Walnut boards", date="2026-11-06", entity_id=shop.entity_id)
    context.budget.add_income(300.0, "Sales", "Cutting board", date="2026-03-02", entity_id=shop.entity_id)
    context.budget.add_debt("Truck loan", 4000.0, 6.5, entity_id=shop.entity_id)
    context.business.add_quote("Dining table", entity_id=shop.entity_id, price=1200.0)
    context.business.add_order("Old order")
    context.ids = {"rentals": rentals.entity_id, "shop": shop.entity_id}
    return context


def test_each_business_at_a_glance_from_its_own_money(ctx):
    page = businesses_page(ctx, TODAY)
    by = {b["name"]: b for b in page["businesses"]}
    rentals, shop = by["Maple Rentals LLC"], by["Oak & Pine Woodshop"]
    assert rentals["month"]["net_value"] == 1300.0 and rentals["properties"] == 1
    assert [a["id"] for a in rentals["apps"]] == ["real_estate"]
    assert shop["month"]["net_value"] == -90.0 and shop["year"]["net_value"] == 210.0 and shop["owes_value"] == 4000.0
    assert shop["open_quotes"] == 1 and [a["id"] for a in shop["apps"]] == ["business", "workshop"]
    assert shop["apps"][0]["page"] == f"business.html?business={ctx.ids['shop']}"
    assert page["unsorted"] == {"count": 1, "page": "business.html?business=none"}
    assert page["totals"]["month_net_value"] == 1210.0 and rentals["page"] == f"biz.html?id={ctx.ids['rentals']}"


def test_one_business_has_its_own_dashboard(ctx):
    found = business_dashboard(ctx, ctx.ids["rentals"], TODAY)
    assert found["name"] == "Maple Rentals LLC" and found["year"]["net_value"] == 1300.0
    assert len(found["spending"]) == 1 and found["income"][0]["what"] == "November rent"
    assert [p["name"] for p in found["properties"]] == ["12 Maple St"] and found["orders"] == found["quotes"] == []
    shop = business_dashboard(ctx, ctx.ids["shop"], TODAY)
    assert [q["title"] for q in shop["quotes"]] == ["Dining table"] and shop["debts"][0]["name"] == "Truck loan"
    assert business_dashboard(ctx, "nope", TODAY) is None and business_dashboard(ctx, "", TODAY) is None


def test_orders_and_quotes_show_one_business_or_the_unsorted(ctx):
    shop = business_page(ctx, TODAY, business=ctx.ids["shop"])
    assert [q["title"] for q in shop["quotes"]] == ["Dining table"] and shop["orders"] == []
    assert shop["business"] == {"id": ctx.ids["shop"], "name": "Oak & Pine Woodshop"}
    loose = business_page(ctx, TODAY, business="none")
    assert [o["title"] for o in loose["orders"]] == ["Old order"] and loose["quotes"] == []
    every = business_page(ctx, TODAY)
    assert every["business"] is None and len(every["orders"]) == 1 and every["quotes"][0]["business"] == "Oak & Pine Woodshop"
    assert {b["name"] for b in every["picks"]["businesses"]} == {"Maple Rentals LLC", "Oak & Pine Woodshop"}
    assert any(f["name"] == "entity_id" for f in every["forms"]["quote"]["fields"])


def test_a_quote_keeps_its_business_when_it_becomes_an_order(ctx):
    quote = ctx.business.quotes[0]
    ACTION_TYPES["quote.accept"].execute(ctx, {"quote_id": quote.quote_id})
    order = next(o for o in ctx.business.orders if o.quote_id == quote.quote_id)
    assert order.entity_id == ctx.ids["shop"] and quote.order_id == order.order_id and quote.status == "Accepted"
    with pytest.raises(ActionError, match="business isn't there"):
        ACTION_TYPES["order.edit"].describe(ctx, {"order_id": order.order_id, "entity_id": "gone"})


def test_the_businesses_by_voice(ctx, monkeypatch):
    import core.assistant_business_view_actions as voice

    monkeypatch.setattr(voice, "date", type("D", (), {"today": staticmethod(lambda: TODAY)}))
    said = _action_get_businesses(ctx, {})
    assert said.startswith("Maple Rentals LLC: ") and "1 orders or quotes have no business yet." in said
    one = _action_get_business(ctx, {"business": "the woodshop"})
    assert one.startswith("Oak & Pine Woodshop: ") and "1 open quote" in one and "Truck loan" in one
    assert _action_get_business(ctx, {"business": "bakery"}).startswith("Which business? You have ")
