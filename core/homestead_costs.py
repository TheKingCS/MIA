"""
core.homestead_costs
=======================

Finance #2 (2026-09-28): what the owner's homestead builds and tools
actually cost. The owner asked for MIA to "help me manage my homestead
I am building and the costs associated with my tools, and builds."

**Connects what already exists instead of adding a parallel ledger.**
Builds are Projects (core/project_manager.py: the greenhouse, the
walipini, the fence), tools and equipment are Maintenance assets
(core/maintenance_manager.py: the mower, the chainsaw, a drill), and
money out is Budget expenses (core/budget_manager.py). The only new
data is the links: an expense can name the build (`project_id`) and/or
the tool (`asset_id`) it was for, a build can have a `budget`, and a
tool a `purchase_price`. Everything below is computed from those on
demand, never stored, so a Plaid-imported or hand-entered expense
counts the moment it's tagged.

The Workshop pipeline (Materials → Jobs → Products → Ledger) was the
first idea for this and was deliberately not used: it models making
products to sell, and a greenhouse build or a drill fits it badly.

**Cost of ownership** of a tool = what was paid for it + everything
spent on it since (parts, repairs, fuel, maintenance). The expense
that bought it is flagged `asset_purchase`, so the purchase counts
once. With engine-hour readings, it's also a **cost per hour**, which
is what the mower business-use write-off (Finance #3) builds on.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from core.region import money

TOOL_PURCHASE_CATEGORY = "Tools & Equipment"


@dataclass
class BuildCost:
    project_id: str
    name: str
    status: str
    budget: float
    spent: float
    by_category: dict[str, float] = field(default_factory=dict)
    tools_bought: list[str] = field(default_factory=list)
    expense_count: int = 0
    last_expense_date: str = ""

    @property
    def remaining(self) -> Optional[float]:
        return round(self.budget - self.spent, 2) if self.budget > 0 else None

    @property
    def percent_used(self) -> Optional[float]:
        return round(100 * self.spent / self.budget, 1) if self.budget > 0 else None


@dataclass
class ToolCost:
    asset_id: str
    name: str
    category: str
    purchase_price: float
    upkeep: float
    by_category: dict[str, float] = field(default_factory=dict)
    hours: Optional[float] = None
    for_builds: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(self.purchase_price + self.upkeep, 2)

    @property
    def cost_per_hour(self) -> Optional[float]:
        return round(self.total / self.hours, 2) if self.hours else None


def _money(value: float) -> str:
    return f"{money(value, ',.2f')}".replace(".00", "")


# ---------------------------------------------------------------------------
# Builds
# ---------------------------------------------------------------------------


def build_cost(context, project) -> BuildCost:
    expenses = [e for e in context.budget.all_expenses() if e.project_id == project.project_id]
    by_category: dict[str, float] = defaultdict(float)
    for e in expenses:
        by_category[e.category] += e.amount
    tools = []
    if context.maintenance is not None:
        for e in expenses:
            if e.asset_purchase and e.asset_id:
                asset = context.maintenance.get_asset(e.asset_id)
                if asset is not None:
                    tools.append(asset.name)
    return BuildCost(
        project_id=project.project_id, name=project.name, status=project.status,
        budget=project.budget, spent=round(sum(e.amount for e in expenses), 2),
        by_category={k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])},
        tools_bought=tools, expense_count=len(expenses),
        last_expense_date=max((e.date for e in expenses), default=""),
    )


def all_build_costs(context) -> list[BuildCost]:
    """Every project with a budget or any tagged spending, biggest spend first."""
    if context.projects is None or context.budget is None:
        return []
    costs = [build_cost(context, p) for p in context.projects.all_projects()]
    return sorted((c for c in costs if c.budget > 0 or c.expense_count), key=lambda c: -c.spent)


def describe_build(cost: BuildCost) -> str:
    """Pure logic: one or two spoken sentences."""
    if cost.expense_count == 0:
        text = f"Nothing's been spent on {cost.name} yet"
        return text + (f"; the budget is {_money(cost.budget)}." if cost.budget > 0 else ".")
    text = f"You've spent {_money(cost.spent)} on {cost.name}"
    if cost.budget > 0:
        if cost.remaining >= 0:
            text += f", {cost.percent_used:g}% of the {_money(cost.budget)} budget, with {_money(cost.remaining)} left"
        else:
            text += f", {_money(-cost.remaining)} over the {_money(cost.budget)} budget"
    text += "."
    top = list(cost.by_category.items())[:3]
    if len(top) > 1:
        text += " Biggest costs: " + ", ".join(f"{cat.lower()} {_money(amount)}" for cat, amount in top) + "."
    if cost.tools_bought:
        text += f" Tools bought for it: {', '.join(cost.tools_bought)}."
    return text


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def hour_readings(context, asset) -> list[tuple[str, float]]:
    """Every engine-hour reading for the asset as (timestamp, value),
    oldest first: its own hour meter plus any runtime (hours-based)
    maintenance task's readings."""
    maintenance = context.maintenance
    readings = []
    for meter in maintenance.asset_meter_names(asset.asset_id):
        if "hour" in meter.lower():
            readings += maintenance.asset_readings(asset.asset_id, meter)
    for task in maintenance.tasks_for_asset(asset.asset_id):
        if task.trigger_type == "runtime":
            readings += maintenance.readings_for_task(task.task_id)
    return sorted(((r.timestamp or "", float(r.value)) for r in readings), key=lambda pair: pair[0])


def current_hours(context, asset) -> Optional[float]:
    """The asset's latest (highest) engine-hour reading. None without readings."""
    values = [value for _, value in hour_readings(context, asset)]
    return max(values) if values else None


def tool_cost(context, asset) -> ToolCost:
    tagged = [e for e in context.budget.all_expenses() if e.asset_id == asset.asset_id]
    purchases = sum(e.amount for e in tagged if e.asset_purchase)
    upkeep_entries = [e for e in tagged if not e.asset_purchase]
    by_category: dict[str, float] = defaultdict(float)
    for e in upkeep_entries:
        by_category[e.category] += e.amount
    builds = []
    if context.projects is not None:
        for e in tagged:
            if e.asset_purchase and e.project_id:
                project = context.projects.get_project(e.project_id)
                if project is not None:
                    builds.append(project.name)
    hours = None
    try:
        hours = current_hours(context, asset)
    except AttributeError:
        pass  # no data logger wired (tests, headless)
    return ToolCost(
        asset_id=asset.asset_id, name=asset.name, category=asset.category,
        # The purchase counts once: the recorded price, or the purchase
        # expense if the price was never filled in.
        purchase_price=round(max(asset.purchase_price, purchases), 2),
        upkeep=round(sum(e.amount for e in upkeep_entries), 2),
        by_category={k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])},
        hours=hours, for_builds=builds,
    )


def all_tool_costs(context) -> list[ToolCost]:
    """Every asset with a known price or any tagged spending, costliest first."""
    if context.maintenance is None or context.budget is None:
        return []
    costs = [tool_cost(context, a) for a in context.maintenance.all_assets()]
    return sorted((c for c in costs if c.total > 0), key=lambda c: -c.total)


def describe_tool(cost: ToolCost) -> str:
    """Pure logic: one or two spoken sentences."""
    if cost.total == 0:
        return f"I don't have any costs for the {cost.name} yet. Tell me what you paid for it."
    parts = []
    if cost.purchase_price:
        parts.append(f"{_money(cost.purchase_price)} to buy")
    if cost.upkeep:
        top = ", ".join(f"{cat.lower()} {_money(amount)}" for cat, amount in list(cost.by_category.items())[:2])
        parts.append(f"{_money(cost.upkeep)} since ({top})")
    text = f"The {cost.name} has cost you {_money(cost.total)}: " + " and ".join(parts) + "."
    if cost.cost_per_hour is not None:
        text += f" At {cost.hours:g} hours, that's {_money(cost.cost_per_hour)} an hour."
    return text


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


def record_tool_purchase(
    context, name: str, price: float, category: str = "Tool", project_id: str = "",
    purchase_date: Optional[str] = None, description: str = "",
):
    """A new tool: the Maintenance asset (with its purchase price) and the
    Budget expense that bought it, linked, and tagged to a build if given."""
    when = purchase_date or date.today().isoformat()
    asset = context.maintenance.add_asset(name=name, category=category, purchase_date=when, purchase_price=price)
    expense = context.budget.add_expense(
        amount=price, category=TOOL_PURCHASE_CATEGORY, description=description or f"Bought {name}",
        date=when, asset_id=asset.asset_id, project_id=project_id, asset_purchase=True,
    )
    return asset, expense
