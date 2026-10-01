"""
Today (core/today.py), 2026-10-01: one list of what needs you today,
across every app; on Home, on the phone, and from the Assistant.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.assistant_today_actions import _action_get_today
from core.budget_manager import BudgetManager
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.email_drafts import EmailDrafts
from core.event_bus import EventBus
from core.kitchen_manager import KitchenManager
from core.maintenance_manager import MaintenanceManager
from core.relationships_manager import RelationshipsManager
from core.task_manager import TaskManager
from core.today import OVERDUE, SOON, TODAY, WAITING, describe, today_items

DAY = date.today()


def iso(days: int = 0) -> str:
    return (DAY + timedelta(days=days)).isoformat()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    folder = tmp_path / "data"
    for attr, store in (("calendar", CalendarManager), ("alarms", AlarmManager), ("budget", BudgetManager),
                        ("maintenance", MaintenanceManager), ("tasks", TaskManager), ("kitchen", KitchenManager),
                        ("relationships", RelationshipsManager), ("email_drafts", EmailDrafts)):
        setattr(context, attr, store(context, data_dir=folder))
    return context


def test_an_empty_day():
    ctx = SimpleNamespace()
    assert today_items(ctx) == [] and describe([]) == "Nothing needs you today. Enjoy it."


def test_everything_that_needs_you_in_order(ctx):
    ctx.calendar.add_event(title="Dentist", date=iso(), time="14:00")
    ctx.calendar.add_event(title="Breakfast", date=iso(), time="08:30")
    ctx.calendar.add_event(title="All-day fair", date=iso())
    ctx.calendar.add_event(title="Next week", date=iso(7))
    ctx.budget.add_bill(name="Electric", amount=120.0, due_date=iso(-2))
    ctx.budget.add_bill(name="Phone", amount=60.0, due_date=iso(2))
    ctx.budget.add_income_source(name="Paycheck", expected_amount=1500.0, next_date=iso())
    asset = ctx.maintenance.add_asset(name="Mower")
    ctx.maintenance.add_task(asset.asset_id, "Sharpen blades", interval_days=30, last_completed=iso(-40))
    ctx.tasks.add_task("p1", "Order lumber", due_date=iso())
    ctx.relationships.add_person("Mom", birthday=f"1960-{(DAY + timedelta(days=1)).strftime('%m-%d')}")
    ctx.kitchen.add_pantry_item("Milk", expiration_date=iso(1))
    ctx.email_drafts.create(["pat@example.com"], "Faucet", "Hi")
    items = today_items(ctx, DAY)
    whens = [i.when for i in items]
    assert whens == sorted(whens, key=[OVERDUE, TODAY, WAITING, SOON].index)
    titles = [i.title for i in items]
    assert titles.index("Breakfast") < titles.index("Dentist") < titles.index("All-day fair")
    overdue = {i.title: i for i in items if i.when == OVERDUE}
    assert overdue["Pay Electric"].detail.endswith("2 days late") and "Sharpen blades: Mower" in overdue
    assert overdue["Sharpen blades: Mower"].module_id == "maintenance"
    soon = {i.title: i.detail for i in items if i.when == SOON}
    assert soon == {"Phone is due in 2 days": "$60.00", "Mom's birthday": "tomorrow"}
    assert "Payday: Paycheck" in titles and "Order lumber" in titles and "Use up soon" in titles
    assert "1 email draft not sent" in titles and "Next week" not in titles
    spoken = describe(items)
    assert spoken.startswith("Overdue: Pay Electric") and "08:30 Breakfast" in spoken and "Coming up:" in spoken


def test_done_and_paid_things_drop_off(ctx):
    bill = ctx.budget.add_bill(name="Water", amount=40.0, due_date=iso())
    task = ctx.tasks.add_task("p1", "Call plumber", due_date=iso(-1))
    assert {"Pay Water", "Call plumber"} <= {i.title for i in today_items(ctx, DAY)}
    ctx.budget.mark_bill_paid(bill.bill_id)
    ctx.tasks.update_task(task.task_id, done=True)
    assert not {"Pay Water", "Call plumber"} & {i.title for i in today_items(ctx, DAY)}


def test_a_broken_source_never_hides_the_rest(ctx):
    ctx.calendar.add_event(title="Dentist", date=iso())
    ctx.budget = SimpleNamespace(all_bills=lambda: 1 / 0)
    assert [i.title for i in today_items(ctx, DAY)] == ["Dentist"]


def test_assistant_phone_and_home_card(ctx, monkeypatch):
    ctx.calendar.add_event(title="Dentist", date=iso(), time="14:00")
    assert "14:00 Dentist" in _action_get_today(ctx, {})

    from PySide6.QtWidgets import QApplication

    from gui.today_card import TodayCard

    QApplication.instance() or QApplication([])
    opened = []
    ctx.events.subscribe("assistant.open_module_requested", lambda **kw: opened.append(kw))
    card = TodayCard(ctx)
    rows = [card._layout.itemAt(i).widget() for i in range(card._layout.count())]
    button = next(w for w in rows if hasattr(w, "click") and "Dentist" in w.text())
    button.click()
    assert opened[0]["module_id"] == "calendar"
    before = card._layout.count()
    card.refresh()  # nothing changed: not rebuilt
    assert card._layout.count() == before


def test_the_phone_gets_today(ctx, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import core.profile_manager as profile_module
    import server.app as server_app_module
    from core.profile_manager import ProfileManager

    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    ctx.profiles = ProfileManager(ctx)
    ctx.profiles.create_profile("Robin", password="pw", email="robin@example.com")
    ctx.voice = ctx.llm = ctx.push_subscriptions = None
    ctx.calendar.add_event(title="Dentist", date=iso(), time="14:00")
    client = TestClient(server_app_module.create_app(ctx))
    assert client.get("/api/today").status_code == 401
    token = client.post("/api/login", json={"profile_id": "robin@example.com", "password": "pw"}).json()["token"]
    body = client.get("/api/today", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["items"][0]["title"] == "Dentist" and body["items"][0]["time"] == "14:00"
    assert "14:00 Dentist" in body["spoken"]
