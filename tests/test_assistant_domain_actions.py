"""
tests.test_assistant_domain_actions
=====================================

Runs the Assistant's conversational actions (core/assistant_domain_actions.py
plus the reworked Maintenance handlers in core/application.py) through the
real registry against real managers on temp data — i.e. "the user said X,
the model called tool Y with their words; did the right record change?"
"""

from __future__ import annotations

from pathlib import Path

import pytest

import core.budget_manager as budget_module
import core.component_manager as component_module
import core.config_manager as config_module
import core.data_logger_manager as data_logger_module
import core.kitchen_manager as kitchen_module
import core.maintenance_manager as maintenance_module
import core.material_manager as material_module
import core.product_manager as product_module
import core.skill_manager as skill_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.component_manager import ComponentManager
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.kitchen_manager import KitchenManager
from core.maintenance_manager import MaintenanceManager
from core.material_manager import MaterialManager
from core.product_manager import ProductManager
from tests.assistant_registry import build_desktop_registry

_MODULES = [
    budget_module, component_module, data_logger_module, kitchen_module, maintenance_module,
    material_module, product_module, skill_module,
]


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    for module in _MODULES:
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.data_logger = DataLoggerManager(context)
    context.maintenance = MaintenanceManager(context)
    context.budget = BudgetManager(context)
    context.kitchen = KitchenManager(context)
    context.components = ComponentManager(context)
    context.materials = MaterialManager(context)
    context.products = ProductManager(context)
    context.assistant_actions = build_desktop_registry()
    return context


def say(ctx, action: str, **arguments) -> str:
    return ctx.assistant_actions.execute(ctx, action, arguments)


# ------------------------------------------------------------------ assets & greenhouse


def _truck_and_mower(ctx):
    truck = ctx.maintenance.add_asset("Pickup Truck", "Vehicle")
    mower = ctx.maintenance.add_asset("Riding Mower", "Power Equipment")
    ctx.maintenance.add_task(truck.asset_id, "Oil change", interval_days=120)
    ctx.maintenance.add_task(truck.asset_id, "Rotate tires", interval_days=180)
    ctx.maintenance.add_task(mower.asset_id, "Sharpen blades", interval_days=30)
    return truck, mower


def test_complete_task_in_users_own_words(ctx):
    truck, _ = _truck_and_mower(ctx)
    reply = say(ctx, "complete_maintenance_task", title="the oil", asset_name="the truck")
    assert reply == "Marked 'Oil change' complete for Pickup Truck."
    task = next(t for t in ctx.maintenance.tasks_for_asset(truck.asset_id) if t.title == "Oil change")
    assert task.last_completed


def test_complete_task_by_asset_alone_when_it_has_one_task(ctx):
    _truck_and_mower(ctx)
    assert say(ctx, "complete_maintenance_task", asset_name="mower") == "Marked 'Sharpen blades' complete for Riding Mower."


def test_complete_task_ambiguous_asks(ctx):
    _truck_and_mower(ctx)
    reply = say(ctx, "complete_maintenance_task", asset_name="truck")
    assert "Which" in reply and "Oil change" in reply


def test_delete_still_requires_exact_name(ctx):
    _truck_and_mower(ctx)
    assert "don't have" in say(ctx, "delete_maintenance_asset", name="truck")
    assert len(ctx.maintenance.all_assets()) == 2


def test_log_reading_to_assets_own_meter_when_no_task(ctx):
    _, mower = _truck_and_mower(ctx)
    reply = say(ctx, "log_maintenance_reading", asset_name="the mower", value=120, unit="hours")
    assert reply == "Logged 120 hours on Riding Mower's engine hours."
    assert ctx.maintenance.asset_readings(mower.asset_id, "Engine Hours")[-1].value == 120


def test_log_reading_goes_to_the_assets_meter_task(ctx):
    _, mower = _truck_and_mower(ctx)
    task = ctx.maintenance.add_task(mower.asset_id, "Change oil", trigger_type="runtime", meter_unit="hours", meter_interval=50)
    assert say(ctx, "log_maintenance_reading", asset_name="mower", value="130", unit="hours") == "Logged 130 hours for 'Change oil'."
    assert ctx.maintenance.readings_for_task(task.task_id)[-1].value == 130


def test_update_asset_details(ctx):
    _, mower = _truck_and_mower(ctx)
    reply = say(ctx, "update_maintenance_asset", asset_name="mower", manufacturer="John Deere", model="Z315E")
    assert "John Deere" in reply
    updated = ctx.maintenance.get_asset(mower.asset_id)
    assert (updated.manufacturer, updated.model) == ("John Deere", "Z315E")


def test_update_asset_with_nothing_to_change_asks(ctx):
    _truck_and_mower(ctx)
    assert "What should I update" in say(ctx, "update_maintenance_asset", asset_name="mower")


def test_get_asset_summarizes_what_mia_knows(ctx):
    _, mower = _truck_and_mower(ctx)
    ctx.maintenance.update_asset(mower.asset_id, manufacturer="John Deere", model="Z315E", notes="2026-09-01: new battery")
    reply = say(ctx, "get_maintenance_asset", asset_name="the mower")
    assert "John Deere Z315E" in reply and "Sharpen blades" in reply and "new battery" in reply


def test_add_asset_note_appends_dated_line(ctx):
    _, mower = _truck_and_mower(ctx)
    say(ctx, "add_asset_note", asset_name="mower", note="deck belt is fraying")
    say(ctx, "add_asset_note", asset_name="mower", note="replaced deck belt")
    lines = ctx.maintenance.get_asset(mower.asset_id).notes.splitlines()
    assert len(lines) == 2 and lines[0].endswith("deck belt is fraying")


def test_greenhouse_plant_added_as_garden_plant(ctx):
    say(ctx, "add_maintenance_asset", name="Tomato Bed", category="greenhouse")
    assert ctx.maintenance.all_assets()[0].category == "Garden/Plant"


def test_greenhouse_query_lists_only_plant_care(ctx):
    _truck_and_mower(ctx)
    bed = ctx.maintenance.add_asset("Tomato Bed", "Garden/Plant")
    ctx.maintenance.add_task(bed.asset_id, "Water", interval_days=2)
    reply = say(ctx, "list_maintenance_tasks", query="greenhouse")
    assert "Water (Tomato Bed)" in reply and "Oil change" not in reply


def test_watered_the_tomatoes(ctx):
    bed = ctx.maintenance.add_asset("Tomato Bed", "Garden/Plant")
    ctx.maintenance.add_task(bed.asset_id, "Water", interval_days=2)
    assert say(ctx, "complete_maintenance_task", title="watered", asset_name="tomatoes") == "Marked 'Water' complete for Tomato Bed."


def test_add_maintenance_task_with_loose_asset_name(ctx):
    ctx.maintenance.add_asset("Tomato Bed", "Garden/Plant")
    assert "every 2 days" in say(ctx, "add_maintenance_task", asset_name="the tomatoes", title="Water", interval_days=2)


# ------------------------------------------------------------------ debts & budget


def test_add_list_pay_and_plan_debts(ctx):
    say(ctx, "add_debt", name="Chase Freedom", balance="$4,200", interest_rate="24.99%", minimum_payment=90)
    say(ctx, "add_debt", name="Truck Loan", balance=18250, interest_rate=6.9, debt_type="auto loan")
    assert "You owe $22,450.00 across 2 debts" in say(ctx, "list_debts")

    reply = say(ctx, "record_debt_payment", debt_name="chase", amount=200)
    assert reply == "Recorded a $200.00 payment on Chase Freedom. $4,000.00 left."
    assert any(e.category == "Debt Payment" for e in ctx.budget.all_expenses())

    plan = say(ctx, "get_debt_payoff_plan")
    assert plan.index("Chase Freedom") < plan.index("Truck Loan")


def test_add_debt_without_rate_asks_for_it(ctx):
    assert "What's its interest rate?" in say(ctx, "add_debt", name="Medical Bill", balance=300)


def test_add_debt_requires_balance(ctx):
    assert "balance" in say(ctx, "add_debt", name="Card")
    assert ctx.budget.all_debts() == []


def test_update_debt_balance_and_rate(ctx):
    debt = ctx.budget.add_debt(name="Capital One Quicksilver", balance=5100, interest_rate=27.49)
    say(ctx, "update_debt", debt_name="capital one", balance=4800, interest_rate=28.99)
    updated = ctx.budget.get_debt(debt.debt_id)
    assert (updated.balance, updated.interest_rate) == (4800, 28.99)


def test_update_bank_synced_debt_warns_sync_wins(ctx):
    ctx.budget.add_debt(name="Chase Freedom", balance=4000, interest_rate=20, plaid_account_id="acct")
    assert "next sync" in say(ctx, "update_debt", debt_name="chase", balance=3900)


def test_paying_off_a_debt_celebrates(ctx):
    ctx.budget.add_debt(name="Store Card", balance=100, interest_rate=20)
    assert "paid off!" in say(ctx, "record_debt_payment", debt_name="store card", amount=100)


def test_set_budget_target_matches_category_loosely(ctx):
    assert say(ctx, "set_budget_target", category="grocery", monthly_amount="$600") == "Set your Groceries budget to $600.00 a month."
    assert ctx.budget.get_budget_target("Groceries").monthly_amount == 600


# ------------------------------------------------------------------ kitchen


def test_add_recipe_with_ingredients_then_log_meal(ctx):
    reply = say(ctx, "add_recipe", name="Venison Chili", category="dinner",
                ingredients=["2 lb ground venison", "1 can black beans", "chili powder"])
    assert reply == "Saved Venison Chili as a dinner recipe with 3 ingredients."
    recipe = ctx.kitchen.all_recipes()[0]
    assert recipe.ingredients[0]["name"] == "ground venison" and recipe.ingredients[0]["unit"] == "lb"
    assert "1 time" in say(ctx, "log_meal", recipe_name="the chili")


def test_add_recipe_duplicate_is_refused(ctx):
    ctx.kitchen.add_recipe(name="Venison Chili")
    assert "already have" in say(ctx, "add_recipe", name="venison chili")


def test_grocery_list_add_list_check_off(ctx):
    assert say(ctx, "add_grocery_item", items="eggs and 2 gallons milk") == "Added eggs, milk to the grocery list."
    assert "eggs already on it" in say(ctx, "add_grocery_item", items=["eggs"]).replace("was ", "")
    assert say(ctx, "list_grocery_list") == "On the grocery list: eggs, 2 gallons milk."
    assert say(ctx, "check_off_grocery_item", items=["the eggs"]) == "Checked off eggs."
    assert say(ctx, "list_grocery_list") == "On the grocery list: 2 gallons milk."


def test_pantry_upsert_out_of_and_list(ctx):
    assert say(ctx, "add_pantry_item", name="10 pounds of flour") == "Added 10 pounds flour to the pantry."
    assert say(ctx, "add_pantry_item", name="flour", quantity=5) == "Updated flour in the pantry to 5 pounds."
    assert "Want me to add it to the grocery list?" in say(ctx, "update_pantry_item", name="flour", quantity=0)
    assert say(ctx, "list_pantry") == "You're out of flour."


def test_recipe_ingredients_to_grocery_list_and_suggestions(ctx):
    recipe = ctx.kitchen.add_recipe(name="Garden Omelette", category="Breakfast")
    ctx.kitchen.add_ingredient(recipe.recipe_id, "eggs")
    ctx.kitchen.add_ingredient(recipe.recipe_id, "spinach")
    ctx.kitchen.add_pantry_item("eggs", quantity=12)
    assert "Garden Omelette just needs spinach" in say(ctx, "suggest_recipes")
    assert say(ctx, "add_recipe_ingredients_to_grocery_list", recipe_name="omelette") == "Added what you need for Garden Omelette: spinach."
    ctx.kitchen.add_pantry_item("spinach", quantity=1)
    assert "You can make Garden Omelette" in say(ctx, "suggest_recipes")


# ------------------------------------------------------------------ parts, materials, products


def test_component_quantity_by_value_and_name(ctx):
    ctx.components.add_component("Resistor", value="10k", quantity=30)
    assert say(ctx, "adjust_component_quantity", name="10k resistors", delta=-2) == "Used 2 10k Resistor. You have 28 now."
    assert say(ctx, "adjust_component_quantity", name="resistor", delta=20) == "Added 20 10k Resistor. You have 48 now."


def test_material_quantity_and_price(ctx):
    ctx.materials.add_material("Plywood", unit="sheet", quantity_on_hand=2, reorder_threshold=3, unit_cost=38)
    assert say(ctx, "adjust_material_quantity", name="plywood", delta=4) == "Added 4 sheet of Plywood. 6 sheet on hand."
    reply = say(ctx, "adjust_material_quantity", name="plywood", delta=-4)
    assert "2 sheet on hand" in reply and "reorder level" in reply
    assert say(ctx, "update_material", name="plywood", unit_cost="$42") == "Updated Plywood: unit cost $42.00."
    assert ctx.materials.all_materials()[0].unit_cost == 42


def test_product_stock(ctx):
    ctx.products.add_product("Cutting Board", quantity_in_stock=3)
    assert say(ctx, "adjust_product_stock", name="cutting boards", delta=5) == "Added 5 Cutting Board. 8 in stock."


def test_unknown_record_lists_what_exists(ctx):
    ctx.materials.add_material("Plywood")
    assert "You have: Plywood" in say(ctx, "adjust_material_quantity", name="walnut", delta=1)
