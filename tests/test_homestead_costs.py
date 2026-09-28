"""
Finance #2, homestead builds and tools: expense tags, build budgets,
tool cost of ownership (core/homestead_costs.py), the Assistant tools
(core/assistant_homestead_actions.py), the maintenance-cost hook, and
the Budget tab's formatting.
"""

import json
from datetime import date
from pathlib import Path

import pytest

import core.budget_manager as budget_module
import core.config_manager as config_module
import core.data_logger_manager as data_logger_module
import core.maintenance_manager as maintenance_module
import core.project_manager as project_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager, ExpenseEntry
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.homestead_costs import (
    all_build_costs, all_tool_costs, build_cost, describe_build, describe_tool, record_tool_purchase, tool_cost,
)
from core.maintenance_manager import MaintenanceManager
from core.project_manager import Project, ProjectManager
from tests.assistant_registry import build_desktop_registry

_MODULES = [budget_module, data_logger_module, maintenance_module, project_module]


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    for module in _MODULES:
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.budget = BudgetManager(context)
    context.data_logger = DataLoggerManager(context)
    context.maintenance = MaintenanceManager(context)
    context.projects = ProjectManager(context)
    context.assistant_actions = build_desktop_registry()
    return context


def say(ctx, action, **arguments):
    return ctx.assistant_actions.execute(ctx, action, arguments)


# ------------------------------------------------------------------ builds


def test_build_spending_against_budget(ctx):
    greenhouse = ctx.projects.add_project("Greenhouse", status="Active")
    ctx.projects.update_project(greenhouse.project_id, budget=5000)
    ctx.budget.add_expense(1200, "Building Materials", "Lumber", project_id=greenhouse.project_id)
    ctx.budget.add_expense(300, "Building Materials", "Polycarbonate panels", project_id=greenhouse.project_id)
    ctx.budget.add_expense(84, "Groceries", "Not for the build")
    cost = build_cost(ctx, ctx.projects.get_project(greenhouse.project_id))
    assert (cost.spent, cost.remaining, cost.percent_used, cost.expense_count) == (1500, 3500, 30, 2)
    assert describe_build(cost) == "You've spent $1,500 on Greenhouse, 30% of the $5,000 budget, with $3,500 left."


def test_over_budget_and_breakdown(ctx):
    fence = ctx.projects.add_project("Fence")
    ctx.projects.update_project(fence.project_id, budget=1000)
    ctx.budget.add_expense(900, "Building Materials", "Posts and wire", project_id=fence.project_id)
    ctx.budget.add_expense(250, "Other", "Auger rental", project_id=fence.project_id)
    text = describe_build(build_cost(ctx, ctx.projects.get_project(fence.project_id)))
    assert text == "You've spent $1,150 on Fence, $150 over the $1,000 budget. Biggest costs: building materials $900, other $250."


def test_only_builds_with_budget_or_spending_are_listed(ctx):
    ctx.projects.add_project("Someday pond")
    coop = ctx.projects.add_project("Coop")
    ctx.budget.add_expense(40, "Building Materials", project_id=coop.project_id)
    assert [c.name for c in all_build_costs(ctx)] == ["Coop"]


# ------------------------------------------------------------------ tools


def test_tool_purchase_counts_once_and_upkeep_adds(ctx):
    greenhouse = ctx.projects.add_project("Greenhouse")
    drill, expense = record_tool_purchase(ctx, "DeWalt drill", 199, project_id=greenhouse.project_id)
    assert drill.purchase_price == 199 and expense.asset_purchase and expense.category == "Tools & Equipment"
    ctx.budget.add_expense(45, "Tools & Equipment", "Spare battery", asset_id=drill.asset_id)
    cost = tool_cost(ctx, drill)
    assert (cost.purchase_price, cost.upkeep, cost.total, cost.for_builds) == (199, 45, 244, ["Greenhouse"])
    assert build_cost(ctx, greenhouse).tools_bought == ["DeWalt drill"]
    assert build_cost(ctx, greenhouse).spent == 199  # the build paid for the drill


def test_cost_per_hour_from_the_hour_meter(ctx):
    mower = ctx.maintenance.add_asset("Riding Mower", category="Power Equipment", purchase_price=2400)
    ctx.budget.add_expense(35, "Maintenance", "Oil change", asset_id=mower.asset_id)
    ctx.budget.add_expense(65, "Maintenance", "Blades", asset_id=mower.asset_id)
    ctx.maintenance.log_asset_reading(mower.asset_id, "Engine Hours", 100)
    ctx.maintenance.log_asset_reading(mower.asset_id, "Engine Hours", 125)
    cost = tool_cost(ctx, mower)
    assert (cost.total, cost.hours, cost.cost_per_hour) == (2500, 125, 20.0)
    assert describe_tool(cost) == (
        "The Riding Mower has cost you $2,500: $2,400 to buy and $100 since (maintenance $100). "
        "At 125 hours, that's $20 an hour."
    )


def test_all_tool_costs_skips_unknowns(ctx):
    ctx.maintenance.add_asset("Old wheelbarrow", category="Tool")
    record_tool_purchase(ctx, "Chainsaw", 329)
    assert [c.name for c in all_tool_costs(ctx)] == ["Chainsaw"]


# ------------------------------------------------------------------ persistence


def test_new_fields_round_trip_and_old_rows_still_load(ctx):
    greenhouse = ctx.projects.add_project("Greenhouse")
    ctx.projects.update_project(greenhouse.project_id, budget=5000)
    drill, _ = record_tool_purchase(ctx, "Drill", 99, project_id=greenhouse.project_id)
    assert ProjectManager(ctx).get_project(greenhouse.project_id).budget == 5000
    assert MaintenanceManager(ctx).get_asset(drill.asset_id).purchase_price == 99
    [expense] = BudgetManager(ctx).all_expenses()
    assert (expense.project_id, expense.asset_id, expense.asset_purchase) == (greenhouse.project_id, drill.asset_id, True)
    old = ExpenseEntry.from_dict({"entry_id": "x", "amount": 5})
    assert (old.project_id, old.asset_id, old.asset_purchase) == ("", "", False)
    assert Project.from_dict({"project_id": "p", "name": "Old"}).budget == 0.0


# ------------------------------------------------------------------ assistant tools


def test_log_build_expense_creates_the_build_then_reuses_it(ctx):
    assert say(ctx, "log_build_expense", amount=240, build="greenhouse", description="Lumber") == (
        "Logged $240.00 for lumber on Greenhouse (a new build). Total so far: $240.00."
    )
    say(ctx, "set_build_budget", build="the greenhouse", amount="$5,000")
    reply = say(ctx, "log_build_expense", amount="85", build="Greenhouse", description="screws")
    assert reply == "Logged $85.00 for screws on Greenhouse. Greenhouse: $325.00 of $5,000.00 spent."
    assert len(ctx.projects.all_projects()) == 1


def test_log_build_expense_needs_amount_and_build(ctx):
    assert say(ctx, "log_build_expense", build="greenhouse") == "How much was it?"
    assert say(ctx, "log_build_expense", amount=10) == "Which build was that for?"


def test_record_tool_purchase_new_and_existing(ctx):
    reply = say(ctx, "record_tool_purchase", tool="DeWalt drill", price=199, build="greenhouse")
    assert reply == "Added the DeWalt drill to your tools, $199.00 for Greenhouse (a new build). I'll track what it costs you from here."
    mower = ctx.maintenance.add_asset("Riding Mower", category="Power Equipment")
    assert say(ctx, "record_tool_purchase", tool="the mower", price=2400) == "Recorded $2,400.00 for the Riding Mower."
    assert ctx.maintenance.get_asset(mower.asset_id).purchase_price == 2400
    assert len(ctx.maintenance.all_assets()) == 2


def test_cost_questions(ctx):
    assert "haven't logged any build costs" in say(ctx, "get_build_costs")
    say(ctx, "log_build_expense", amount=240, build="greenhouse")
    say(ctx, "log_build_expense", amount=60, build="coop")
    assert say(ctx, "get_build_costs") == "You've spent $300.00 across 2 builds: Greenhouse $240; Coop $60."
    assert say(ctx, "get_build_costs", build="greenhouse").startswith("You've spent $240 on Greenhouse.")
    say(ctx, "record_tool_purchase", tool="Chainsaw", price=329)
    assert say(ctx, "get_tool_costs", tool="chainsaw").startswith("The Chainsaw has cost you $329: $329 to buy.")
    assert say(ctx, "get_tool_costs").startswith("Your tools and equipment have cost $329.00 in all.")


def test_completing_maintenance_with_a_cost_logs_it_to_the_item(ctx):
    mower = ctx.maintenance.add_asset("Riding Mower", category="Power Equipment")
    ctx.maintenance.add_task(mower.asset_id, "Oil change", interval_days=180)
    reply = say(ctx, "complete_maintenance_task", title="oil change", asset_name="mower", cost="$35")
    assert reply == "Marked 'Oil change' complete for Riding Mower. Logged $35.00 toward it."
    assert tool_cost(ctx, mower).upkeep == 35


# ------------------------------------------------------------------ screens


def test_budget_tab_rows():
    from core.homestead_costs import BuildCost, ToolCost
    from modules.budget.module import format_build_row, format_tool_row

    assert format_build_row(BuildCost("p", "Greenhouse", "Active", 5000, 1500)) == (
        "Greenhouse  —  $1,500.00 spent of $5,000.00 (30%), $3,500.00 left   [Active]"
    )
    assert "$150.00 OVER" in format_build_row(BuildCost("p", "Fence", "Active", 1000, 1150))
    assert format_tool_row(ToolCost("a", "Mower", "Power Equipment", 2400, 100, hours=125.0)) == (
        "Mower  —  $2,500.00 total ($2,400.00 to buy + $100.00 since), $20.00/hr over 125 hrs"
    )


def test_expense_dialog_offers_builds_and_tools(ctx):
    from PySide6.QtWidgets import QApplication

    from gui.add_edit_expense_dialog import AddEditExpenseDialog

    QApplication.instance() or QApplication([])
    greenhouse = ctx.projects.add_project("Greenhouse")
    drill, expense = record_tool_purchase(ctx, "Drill", 99, project_id=greenhouse.project_id)
    dialog = AddEditExpenseDialog(entry=expense, projects=ctx.projects.all_projects(), assets=ctx.maintenance.all_assets())
    assert dialog.project_combo.currentText() == "Greenhouse" and dialog.asset_combo.currentText() == "Drill"
    dialog.project_combo.setCurrentIndex(0)
    dialog._on_accept()
    assert dialog.entered_project_id == "" and dialog.entered_asset_id == drill.asset_id
