"""Quotes, customers, orders and the portfolio (DEC-0030 phase C): a quote
from a recipe, accepted into an order, a deposit, the build, the rest
paid, delivered, and the build's real profit counting what the customer
paid. Every step is an undoable action."""

import pytest

from core.actions import ActionCenter, ActionError
from core.business_book import BusinessBook, suggested_price
from core.craft_recipes import CraftRecipeBook
from core.job_manager import JobManager
from core.ledger_manager import LedgerManager
from core.material_manager import MaterialManager
from core.product_manager import ProductManager
from tests.engine_world import build_world


def test_suggested_price():
    assert suggested_price(85, 6, 25, 20, 20) == 306  # (85 + 150 + 20) × 1.2 = 306
    assert suggested_price(10.01, 0, 0, 0, 0) == 11 and suggested_price(0, 0, 0, 0, 50) == 0


@pytest.fixture
def shop(tmp_path, monkeypatch):
    w = build_world(tmp_path, monkeypatch)
    here = w.home_dir
    w.materials, w.products = MaterialManager(w, data_dir=here), ProductManager(w, data_dir=here)
    w.jobs, w.ledger = JobManager(w, data_dir=here), LedgerManager(w, data_dir=here)
    w.craft_recipes, w.business = CraftRecipeBook(w, data_dir=here), BusinessBook(w, data_dir=here)
    w.actions = ActionCenter()
    return w


def do(w, kind, **params):
    p = w.actions.propose(w, kind, params)
    w.actions.approve(w, p.proposal_id)
    return p


def test_quote_to_delivered_order(shop):
    from core.web_business import business_page

    w = shop
    do(w, "craft_recipe.add", name="Farmhouse bench", est_hours=6, price=180, materials="6 board 2x4 8ft @ 4\n1 sheet Plywood @ 61")
    recipe = w.craft_recipes.all_recipes()[0]
    do(w, "customer.add", name="Jordan", phone="555-0100")
    jordan = w.business.customers[0]
    p = do(w, "quote.add", title="Bench for the porch", customer_id=jordan.customer_id, recipe_id=recipe.recipe_id,
           labor_rate=25, margin=20, extras=20)
    assert p.summary == "Add the quote Bench for the porch for Jordan"
    quote = business_page(w)["quotes"][0]
    assert (quote["price"], quote["suggested"], quote["recipe"]) == ("$306.00", "$306.00", "Farmhouse bench")
    assert [label for label, _v in quote["parts"]] == ["Materials", "Labor 6 h × $25.00", "Extras", "Margin 20%"]

    do(w, "quote.send", quote_id=quote["id"])
    p = do(w, "quote.accept", quote_id=quote["id"], due_date="2026-11-15")
    assert p.summary.startswith("Accept Bench for the porch for Jordan at $306.00")
    order = business_page(w)["orders"][0]
    assert (order["status"], order["price"], order["left"]) == ("Open", "$306.00", "$306.00")
    with pytest.raises(ActionError):
        w.actions.propose(w, "quote.accept", {"quote_id": quote["id"]})  # not twice

    assert "the deposit of $100.00" in do(w, "order.pay", order_id=order["id"], amount=100).summary
    do(w, "craft.receive", recipe_id=recipe.recipe_id, q_0=6, c_0=24, q_1=1, c_1=61)
    do(w, "order.build", order_id=order["id"])
    order = business_page(w)["orders"][0]
    assert order["status"] == "Building" and order["build"] is not None
    job_id = order["build"]["id"]
    assert all(r.job_id == job_id for r in w.ledger.all_revenue())  # the deposit counts for the build
    do(w, "craft.finish", job_id=job_id, hours=7)
    do(w, "order.pay", order_id=order["id"], amount=206)
    do(w, "order.status", order_id=order["id"], status="Delivered")
    page = business_page(w)
    order = page["orders"][0]
    assert (order["status"], order["left"], order["open"]) == ("Delivered", "$0.00", False)
    assert order["build"]["profit"] == "$221.00"  # 306 paid − 85 materials
    assert w.products.all_products()[0].quantity_in_stock == 0  # it left the shop
    do(w, "order.status", order_id=order["id"], status="Delivered")
    assert w.products.all_products()[0].quantity_in_stock == 0  # never taken out twice
    assert page["customers"][0]["spent"] == "$306.00" and page["counts"]["owed"] == "$0.00"

    assert [p["name"] for p in page["portfolio"]] == ["Farmhouse bench"]
    do(w, "portfolio.feature", job_id=job_id)
    assert business_page(w)["portfolio"][0]["featured"]


def test_undo_and_child_safety(shop):
    w = shop
    do(w, "customer.add", name="Sam")
    p = do(w, "order.add", title="Planter boxes", price=120, customer_id=w.business.customers[0].customer_id)
    w.actions.undo(w, p.proposal_id)
    assert w.business.orders == []
    with pytest.raises(ActionError):
        w.actions.propose(w, "order.add", {"title": "X", "price": 5, "customer_id": "nobody"})
    from core.child_accounts import CHILD_APPS

    assert "business" not in CHILD_APPS
    assert not any(k.startswith(("customer.", "quote.", "order.", "portfolio.")) and v.child_ok
                   for k, v in __import__("core.actions", fromlist=["ACTION_TYPES"]).ACTION_TYPES.items())
