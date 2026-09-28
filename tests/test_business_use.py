"""
Finance #3, business use of personal equipment (core/business_use.py):
the meter math, the worksheet's numbers and notes, persistence, the
HTML worksheet, and the Assistant tools. Numbers are checked exactly;
it's arithmetic on the owner's own records.
"""

from datetime import date
from html import escape as html_escape
from pathlib import Path

import pytest

import core.budget_manager as budget_module
import core.business_use as business_use_module
import core.config_manager as config_module
import core.data_logger_manager as data_logger_module
import core.maintenance_manager as maintenance_module
import core.project_manager as project_module
import core.real_estate_manager as real_estate_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.business_use import (
    DISCLAIMER, BusinessUseManager, build_worksheet, build_worksheet_html, describe_worksheet, meter_hours_in_year,
)
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceManager
from core.project_manager import ProjectManager
from core.real_estate_manager import RealEstateManager
from tests.assistant_registry import build_desktop_registry

_MODULES = [budget_module, business_use_module, data_logger_module, maintenance_module, project_module, real_estate_module]


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
    context.real_estate = RealEstateManager(context)
    context.business_use = BusinessUseManager(context)
    context.assistant_actions = build_desktop_registry()
    return context


def say(ctx, action, **arguments):
    return ctx.assistant_actions.execute(ctx, action, arguments)


def mower_with_costs(ctx):
    mower = ctx.maintenance.add_asset("Riding Mower", category="Power Equipment", purchase_date="2025-04-10", purchase_price=2400)
    ctx.budget.add_expense(2400, "Tools & Equipment", "Bought mower", date="2025-04-10", asset_id=mower.asset_id, asset_purchase=True)
    ctx.budget.add_expense(35, "Maintenance", "Oil change", date="2026-05-01", asset_id=mower.asset_id)
    ctx.budget.add_expense(65, "Maintenance", "Blades", date="2026-07-01", asset_id=mower.asset_id)
    ctx.budget.add_expense(50, "Maintenance", "Last year's tune-up", date="2025-10-01", asset_id=mower.asset_id)
    return mower


# ------------------------------------------------------------------ meter math


@pytest.mark.parametrize("readings, expected", [
    ([("2025-12-20T10:00", 100), ("2026-06-01T10:00", 150), ("2026-12-01T10:00", 225)], 125),  # from the last reading before
    ([("2026-03-01T10:00", 100), ("2026-11-01T10:00", 160)], 60),  # no earlier reading: first in-year is the start
    ([("2025-12-20T10:00", 100)], None),  # nothing this year
    ([("2026-03-01T10:00", 100)], None),  # one reading can't show movement
    ([], None),
])
def test_meter_hours_in_year(readings, expected):
    assert meter_hours_in_year(readings, 2026) == expected


# ------------------------------------------------------------------ the worksheet


def test_worksheet_numbers_from_the_meter(ctx, monkeypatch):
    mower = mower_with_costs(ctx)
    maple = ctx.real_estate.add_property("Maple duplex")
    ctx.business_use.log_use(mower.asset_id, 25, use_date="2026-05-10", property_id=maple.property_id, client="Maple duplex")
    ctx.business_use.log_use(mower.asset_id, 15, use_date="2026-06-14", client="Johnson lawn")
    ctx.business_use.log_use(mower.asset_id, 9, use_date="2025-08-01", client="Last year")
    monkeypatch.setattr(business_use_module, "hour_readings",
                        lambda c, a: [("2025-12-20T10:00", 100), ("2026-12-01T10:00", 225)])
    sheet = build_worksheet(ctx, mower, 2026)
    assert (sheet.total_hours, sheet.total_method, sheet.business_hours, sheet.business_pct) == (125, "hour meter", 40, 32.0)
    assert (sheet.running_costs, sheet.business_running_costs) == (100, 32.0)
    assert (sheet.cost_basis, sheet.business_basis, sheet.placed_in_service) == (2400, 768.0, "2025-04-10")
    assert sheet.business_costs_by_business() == [("Rentals (Maple duplex)", 25, 20.0), ("Business (no entity set)", 15, 12.0)]
    assert any("not more than 50%" in n for n in sheet.notes)
    assert describe_worksheet(sheet) == (
        "In 2026 the Riding Mower ran 125 hours (hour meter), 40 of them for business: 32% business use. "
        "Business share of this year's running costs: $32.00 of $100.00. Business share of its $2,400.00 cost: $768.00. "
        "That's backed by 2 logged business jobs."
    )


def test_real_meter_readings_are_used(ctx):
    mower = mower_with_costs(ctx)
    ctx.maintenance.log_asset_reading(mower.asset_id, "Engine Hours", 100)
    ctx.maintenance.log_asset_reading(mower.asset_id, "Engine Hours", 140)
    ctx.business_use.log_use(mower.asset_id, 10)
    sheet = build_worksheet(ctx, mower, date.today().year)
    assert (sheet.total_hours, sheet.total_method, sheet.business_pct) == (40, "hour meter", 25.0)


def test_without_a_meter_total_is_what_was_logged_and_flagged(ctx):
    mower = mower_with_costs(ctx)
    ctx.business_use.log_use(mower.asset_id, 30, use_date="2026-05-10")
    ctx.business_use.log_use(mower.asset_id, 10, purpose="personal", use_date="2026-05-11")
    sheet = build_worksheet(ctx, mower, 2026)
    assert (sheet.total_hours, sheet.total_method, sheet.business_pct) == (40, "logged use", 75.0)
    assert any("no hour-meter readings" in n for n in sheet.notes)
    assert any("more than 50%" in n and "not more" not in n for n in sheet.notes)


def test_logging_more_than_the_meter_is_flagged(ctx, monkeypatch):
    mower = mower_with_costs(ctx)
    ctx.business_use.log_use(mower.asset_id, 30, use_date="2026-05-10")
    monkeypatch.setattr(business_use_module, "hour_readings", lambda c, a: [("2026-01-02T00:00", 100), ("2026-12-01T00:00", 120)])
    sheet = build_worksheet(ctx, mower, 2026)
    assert (sheet.total_hours, sheet.business_pct) == (30, 100.0)
    assert any("meter moved only 20" in n for n in sheet.notes)


def test_empty_year_and_missing_price(ctx):
    drill = ctx.maintenance.add_asset("Drill", category="Tool")
    sheet = build_worksheet(ctx, drill, 2026)
    assert sheet.total_hours is None and sheet.business_pct is None
    assert "No business use is logged" in " ".join(sheet.notes) and "No purchase price" in " ".join(sheet.notes)
    assert describe_worksheet(sheet) == "I don't have any use logged for the Drill in 2026 yet."


def test_entity_from_the_property_and_explicit_business(ctx, monkeypatch):
    mower = mower_with_costs(ctx)
    llc = ctx.budget.add_business_entity("Sunrise Rentals LLC")
    maple = ctx.real_estate.add_property("Maple duplex", entity_id=llc.entity_id)
    ctx.business_use.log_use(mower.asset_id, 20, use_date="2026-05-10", property_id=maple.property_id)
    monkeypatch.setattr(business_use_module, "hour_readings", lambda c, a: [])
    assert build_worksheet(ctx, mower, 2026).by_business == [("Sunrise Rentals LLC", 20)]


def test_html_worksheet(ctx):
    mower = mower_with_costs(ctx)
    ctx.business_use.log_use(mower.asset_id, 5, use_date="2026-05-10", client="<Johnson> lawn")
    html = build_worksheet_html(build_worksheet(ctx, mower, 2026), "2026-09-28 10:00")
    assert "Business use worksheet: Riding Mower, 2026" in html and "&lt;Johnson&gt; lawn" in html
    assert html_escape(DISCLAIMER) in html


def test_log_persists_and_validates(ctx):
    mower = mower_with_costs(ctx)
    entry = ctx.business_use.log_use(mower.asset_id, 2, client="Maple")
    assert BusinessUseManager(ctx).entries_for(mower.asset_id)[0].client == "Maple"
    assert ctx.business_use.delete_entry(entry.entry_id) and not ctx.business_use.delete_entry(entry.entry_id)
    with pytest.raises(ValueError):
        ctx.business_use.log_use(mower.asset_id, 0)
    with pytest.raises(ValueError):
        ctx.business_use.log_use(mower.asset_id, 1, purpose="fun")


# ------------------------------------------------------------------ assistant tools


def test_log_business_use_tool(ctx):
    mower = mower_with_costs(ctx)
    llc = ctx.budget.add_business_entity("Sunrise Rentals LLC")
    ctx.real_estate.add_property("Maple duplex", entity_id=llc.entity_id)
    year = date.today().year
    assert say(ctx, "log_business_use", tool="mower", hours=2, for_whom="the maple duplex") == (
        f"Logged 2 business hours on the Riding Mower for the maple duplex. {year} so far: 2 business hours."
    )
    [entry] = ctx.business_use.entries_for(mower.asset_id)
    assert entry.entity_id == llc.entity_id and entry.property_id
    # With one tool already in use for business, the tool can be left out.
    assert say(ctx, "log_business_use", hours="1.5", for_whom="Johnson lawn").endswith(f"{year} so far: 3.5 business hours.")
    assert say(ctx, "log_business_use", tool="mower") == "How many hours was it?"


def test_log_business_use_asks_which_tool(ctx):
    ctx.maintenance.add_asset("Mower")
    ctx.maintenance.add_asset("Chainsaw")
    assert say(ctx, "log_business_use", hours=2) == "Which tool or piece of equipment was it?"


def test_get_business_use_tool(ctx):
    assert "haven't logged any business use" in say(ctx, "get_business_use")
    mower = mower_with_costs(ctx)
    ctx.business_use.log_use(mower.asset_id, 10, use_date="2026-05-10")
    ctx.business_use.log_use(mower.asset_id, 30, purpose="personal", use_date="2026-05-11")
    reply = say(ctx, "get_business_use", tool="mower", year=2026)
    assert reply.startswith("In 2026 the Riding Mower ran 40 hours (logged use), 10 of them for business: 25% business use.")
    assert reply.endswith("It's records, not tax advice.")
