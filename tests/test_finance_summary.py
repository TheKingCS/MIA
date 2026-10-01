"""
Finance #4, money on the phone: core/finance_summary.py's numbers,
the /api/finance/summary endpoint, and the phone's money.js drawing the
real Python output (under Node, skipped without it).
"""

import json
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.budget_manager as budget_module
import core.config_manager as config_module
import core.data_logger_manager as data_logger_module
import core.maintenance_manager as maintenance_module
import core.project_manager as project_module
import core.real_estate_manager as real_estate_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.finance_summary import build_finance_summary
from core.homestead_costs import record_tool_purchase
from core.maintenance_manager import MaintenanceManager
from core.project_manager import ProjectManager
from core.real_estate_manager import RealEstateManager

TODAY = date(2026, 9, 28)
_MODULES = [budget_module, data_logger_module, maintenance_module, project_module, real_estate_module]
_NODE = shutil.which("node")
_HARNESS = Path(__file__).resolve().parent / "js" / "money_harness.js"


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
    return context


def seed(ctx):
    b = ctx.budget
    b.add_income(3000, "Salary", date="2026-09-12")
    b.add_expense(420, "Groceries", date="2026-09-10")
    b.add_expense(84, "Groceries", date="2026-08-30")  # last month: not counted
    b.set_budget_target("Groceries", 400)
    b.add_bill("Electric", 120, due_date=(TODAY + timedelta(days=3)).isoformat(), category="Utilities")
    b.add_bill("Insurance", 118, due_date=(TODAY + timedelta(days=40)).isoformat(), category="Insurance")
    b.add_income_source("Paycheck", 2400, next_date=(TODAY + timedelta(days=5)).isoformat())
    b.add_debt("Chase card", 3000, 24.9, minimum_payment=90)
    b.add_debt("Truck loan", 12000, 6.9, minimum_payment=455, debt_type="Auto Loan", plaid_account_id="acct-1")
    ctx.real_estate.add_property("Maple duplex", current_value=280000, mortgage_balance=150000)
    greenhouse = ctx.projects.add_project("Greenhouse", status="Active")
    ctx.projects.update_project(greenhouse.project_id, budget=5000)
    b.add_expense(1200, "Building Materials", "Lumber", date="2026-09-01", project_id=greenhouse.project_id)
    record_tool_purchase(ctx, "Chainsaw", 329, purchase_date="2026-09-02")


def test_summary_numbers(ctx):
    seed(ctx)
    s = build_finance_summary(ctx, TODAY)
    assert s["available"] and s["as_of"] == "2026-09-28"
    assert s["month"] == {"label": "September 2026", "income": 3000, "expenses": 1949, "net": 1051}
    assert s["bills_due"] == [{"name": "Electric", "amount": 120, "days": 3}]  # Insurance is 40 days out
    assert s["income_expected"] == [{"name": "Paycheck", "amount": 2400, "days": 5}]
    assert s["budget_targets"] == [{"category": "Groceries", "budget": 400, "spent": 420}]
    assert (s["debts"]["total"], s["debts"]["minimum_payments"]) == (15000, 545)
    assert [d["name"] for d in s["debts"]["ranked"]] == ["Chase card", "Truck loan"]
    assert s["debts"]["ranked"][1]["bank_synced"] is True
    assert s["net_worth"] == {
        "total": 130000, "sources": [{"label": "Property equity", "value": 130000}],
        "manual_debts_not_in_net_worth": 3000,  # the hand-entered card; the synced loan is in its bank's total
    }
    assert s["builds"] == [{"name": "Greenhouse", "spent": 1200, "budget": 5000, "remaining": 3800, "status": "Active"}]
    assert s["tools"] == [{"name": "Chainsaw", "total": 329, "purchase": 329, "upkeep": 0, "per_hour": None}]
    json.dumps(s)  # must be JSON-ready


def test_net_worth_follows_the_home_widget_rule(ctx):
    ctx.finance = SimpleNamespace(all_latest_snapshots=lambda: [
        SimpleNamespace(source="plaid_1", data={"institution_name": "Chase", "summary": {"total_value": 5200.5}}),
        SimpleNamespace(source="kraken", data={"summary": {}}),  # no total: excluded, not counted as zero
    ])
    s = build_finance_summary(ctx, TODAY)
    assert s["net_worth"]["total"] == 5200.5 and s["net_worth"]["sources"] == [{"label": "Chase", "value": 5200.5}]


def test_empty_and_unavailable(ctx):
    s = build_finance_summary(ctx, TODAY)
    assert s["net_worth"]["total"] is None and s["debts"]["ranked"] == [] and s["builds"] == []
    assert build_finance_summary(SimpleNamespace(budget=None), TODAY)["available"] is False


# ------------------------------------------------------------------ the endpoint


def test_endpoint_requires_login_and_serves_the_summary(ctx, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app

    seed(ctx)
    ctx.profiles = SimpleNamespace(
        list_profiles=lambda: [SimpleNamespace(profile_id="p1", name="Zac", has_password=True, created_at="")],
        find_for_sign_in=lambda who: (SimpleNamespace(profile_id="p1", name="Zac", has_password=True)
                                      if who.strip().lower() in ("p1", "zac") else None),
        verify_password=lambda pid, pw: pw == "pw",
    )
    ctx.voice = ctx.llm = ctx.push_subscriptions = None
    app = server_app.create_app(ctx)
    client = TestClient(app)
    assert client.get("/api/finance/summary").status_code == 401
    token = client.post("/api/login", json={"profile_id": "zac", "password": "pw"}).json()["token"]
    res = client.get("/api/finance/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200 and res.json()["debts"]["total"] == 15000


# ------------------------------------------------------------------ money.js


@pytest.mark.skipif(_NODE is None, reason="Node.js not installed")
def test_money_js_draws_the_real_summary(ctx):
    seed(ctx)
    summary = build_finance_summary(ctx, TODAY)
    out = subprocess.run([_NODE, str(_HARNESS)], input=json.dumps(summary), capture_output=True, text=True, check=True, timeout=30)
    sections = {s["title"]: s for s in json.loads(out.stdout)}
    month = sections["This month (September 2026)"]["rows"]
    assert [(r["label"], r["value"], r["tone"]) for r in month] == [
        ("Money in", "$3,000", ""), ("Money out", "$1,949", ""), ("Net", "$1,051", "good"),
    ]
    coming = sections["Coming up (next 2 weeks)"]["rows"]
    assert (coming[0]["label"], coming[0]["value"], coming[0]["tone"], coming[0]["sub"]) == ("Electric", "$120", "warn", "due in 3 days")
    assert (coming[1]["label"], coming[1]["value"], coming[1]["sub"]) == ("Paycheck", "+$2,400", "expected in 5 days")
    assert sections["Budget targets"]["rows"][0]["tone"] == "bad"  # $420 of $400
    debts = sections["Debts: $15,000"]
    assert debts["rows"][0]["label"] == "1. Chase card" and "bank-synced" in debts["rows"][1]["sub"]
    assert "Minimum payments: $545/month" in debts["note"]
    net = sections["Net worth: $130,000"]
    assert "hand ($3,000) aren't subtracted here" in net["note"]
    assert sections["Builds"]["rows"][0]["sub"] == "$3,800 left"
    assert sections["Tools & equipment"]["rows"][0]["value"] == "$329"


@pytest.mark.skipif(_NODE is None, reason="Node.js not installed")
def test_money_js_handles_unavailable():
    out = subprocess.run([_NODE, str(_HARNESS)], input=json.dumps({"available": False}), capture_output=True, text=True, check=True, timeout=30)
    [section] = json.loads(out.stdout)
    assert "isn't available" in section["note"]


# ------------------------------------------------------------------ the Android app's fixture

_ANDROID_FIXTURE = Path(__file__).resolve().parent.parent / "android" / "app" / "src" / "test" / "resources" / "finance_summary.json"


def test_android_fixture_matches_the_real_summary(ctx):
    """android/.../MoneyFormatTest.kt reads this fixture, so the Kotlin
    formatter is tested against exactly what the server sends. Rewrite
    it with UPDATE_FIXTURES=1 pytest tests/test_finance_summary.py."""
    import os

    seed(ctx)
    summary = build_finance_summary(ctx, TODAY)
    summary.pop("generated_at")
    if os.environ.get("UPDATE_FIXTURES"):
        _ANDROID_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        _ANDROID_FIXTURE.write_text(json.dumps(summary, indent=2) + "\n")
    assert json.loads(_ANDROID_FIXTURE.read_text()) == summary
