"""
A private budget (core/personal_data.py, 2026-10-01): one person keeps
their money apart from the household's; everyone else keeps the shared
budget; switching back keeps the private one.
"""

import time

import pytest

import core.budget_manager as budget_module
import core.config_manager as config_module
import core.profile_manager as profile_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.household_manager import HouseholdManager
from core.personal_data import PersonalData, view_for
from core.plaid_manager import PlaidManager
from core.profile_manager import ProfileManager
from core.undo_log import UndoLog

_BUDGET_FILES = ("_BILLS_FILE", "_INCOME_FILE", "_EXPENSES_FILE", "_INCOME_SOURCES_FILE", "_BUDGET_TARGETS_FILE",
                 "_BUSINESS_ENTITIES_FILE", "_DEBTS_FILE")


@pytest.fixture
def home(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setattr(budget_module, "_DATA_DIR", shared)
    for name in _BUDGET_FILES:
        monkeypatch.setattr(budget_module, name, shared / getattr(budget_module, name).name)
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    context.households = HouseholdManager(context)  # both in one household (they predate households)
    context.undo = UndoLog()
    context.budget = BudgetManager(context)
    context.plaid = PlaidManager(context, data_dir=shared)
    context.personal_data = PersonalData(context, profiles_dir=tmp_path / "profiles", shared_dir=shared)
    context.personal_data.watch(context.events)
    context.personal_data.activate_current()
    return context, zac, faith, tmp_path


def test_a_private_budget_is_only_yours(home):
    context, zac, faith, tmp_path = home
    context.budget.add_bill(name="Electric", amount=120.0, due_date="2026-10-15")  # the household's
    changed = []
    context.events.subscribe("records.changed", lambda **kw: changed.append(kw["action"]))
    context.personal_data.set_private_budget(zac.profile_id, True)
    assert "budget.private" in changed
    assert context.budget.all_bills() == []  # Zac's own, empty budget
    context.budget.add_expense(amount=40.0, description="Gift for Faith")
    assert (tmp_path / "profiles" / zac.profile_id / "private_budget" / "budget_expenses.json").exists()
    faith_budget = view_for(context, faith.profile_id).budget
    assert [b.name for b in faith_budget.all_bills()] == ["Electric"] and faith_budget.all_expenses() == []
    assert context.plaid.private and not view_for(context, faith.profile_id).plaid.__dict__.get("private")


def test_switching_back_keeps_the_private_one(home):
    context, zac, _faith, _ = home
    context.personal_data.set_private_budget(zac.profile_id, True)
    context.budget.add_expense(amount=12.0, description="Private thing")
    context.personal_data.set_private_budget(zac.profile_id, False)
    assert [e.description for e in context.budget.all_expenses()] == []  # the household's again
    context.personal_data.set_private_budget(zac.profile_id, True)
    assert [e.description for e in context.budget.all_expenses()] == ["Private thing"]


def test_the_choice_survives_a_restart(home):
    context, zac, _faith, tmp_path = home
    context.personal_data.set_private_budget(zac.profile_id, True)
    context.budget.add_expense(amount=5.0, description="Coffee")
    fresh = PersonalData(context, profiles_dir=tmp_path / "profiles", shared_dir=tmp_path / "shared")
    assert [e.description for e in fresh.view(zac.profile_id).budget.all_expenses()] == ["Coffee"]


def test_private_bank_balances_stay_out_of_the_household_net_worth(home, tmp_path):
    context, zac, _faith, _ = home
    context.personal_data.set_private_budget(zac.profile_id, True)
    context.finance = None  # would raise if it tried to write into the shared import folder
    context.plaid._write_snapshot_file({"source": "plaid_x"})


def test_the_budget_screen_shows_whose_budget_it_is(home, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox

    from modules.budget.module import BudgetModule

    QApplication.instance() or QApplication([])
    context, zac, _faith, _ = home
    context.search = type("S", (), {"register_provider": lambda *a: None})()
    module = BudgetModule(context)
    widget = module.get_widget()  # noqa: F841 (keeps the screen alive)
    assert "shared with Faith" in module._budget_owner_label.text()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    module._on_toggle_private_budget()
    assert "private budget" in module._budget_owner_label.text()
    assert module._budget_owner_button.text() == "Use the household budget"
