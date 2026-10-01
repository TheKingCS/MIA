"""
Whose is it (core/ownership.py), 2026-10-01: owner marks on vehicles,
tools and appliances; Today shows your things and shared ones.
"""

import time
from datetime import date, timedelta

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core.app_context import AppContext
from core.assistant_ownership_actions import _action_get_item_owner, _action_set_item_owner
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.household_manager import HouseholdManager
from core.maintenance_manager import MaintenanceManager
from core.ownership import SHARED_LABEL, is_for_me, owner_choices, possessive, resolve_owner
from core.personal_data import ScopedView
from core.profile_manager import ProfileManager
from core.today import today_items


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    zac = context.profiles.create_profile("Zac Doe", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    context.households = HouseholdManager(context)
    context.maintenance = MaintenanceManager(context, data_dir=tmp_path / "data")
    return context, zac, faith


def test_choices_and_words(home):
    context, zac, faith = home
    assert owner_choices(context) == [(SHARED_LABEL, None), ("Zac Doe", zac.profile_id), ("Faith", faith.profile_id)]
    assert resolve_owner(context, "mine") == (True, zac.profile_id)
    assert resolve_owner(context, "it's Faith's") == (True, faith.profile_id)
    assert resolve_owner(context, "Zac") == (True, zac.profile_id)  # a first name works
    assert resolve_owner(context, "the whole household") == (True, None)
    assert resolve_owner(context, "the neighbor") == (False, None)
    assert possessive(context, zac.profile_id) == "yours" and possessive(context, faith.profile_id) == "Faith's"
    assert possessive(context, None) == "shared" and is_for_me(context, None) and not is_for_me(context, faith.profile_id)


def test_the_assistant_sets_and_tells_whose(home):
    context, zac, faith = home
    truck = context.maintenance.add_asset(name="Truck")
    assert "shared by the household" in _action_get_item_owner(context, {"item": "truck"})
    assert "Faith's Today list" in _action_set_item_owner(context, {"item": "the truck", "owner": "Faith's"})
    assert context.maintenance.get_asset(truck.asset_id).owner_profile_id == faith.profile_id
    assert _action_get_item_owner(context, {"item": "truck"}) == "The Truck is Faith's."
    faith_view = ScopedView(context, (), profile_id=faith.profile_id)
    assert _action_get_item_owner(faith_view, {"item": "truck"}) == "The Truck is yours."
    assert "Whose is the Truck?" in _action_set_item_owner(context, {"item": "truck", "owner": "the neighbor"})
    assert "shared" in _action_set_item_owner(context, {"item": "truck", "owner": "shared"})


def test_today_shows_your_things_and_shared_ones(home):
    context, zac, faith = home
    long_ago = (date.today() - timedelta(days=40)).isoformat()
    for name, owner in (("Truck", faith.profile_id), ("Mower", zac.profile_id), ("Furnace", None)):
        asset = context.maintenance.add_asset(name=name, owner_profile_id=owner)
        context.maintenance.add_task(asset.asset_id, "Service", interval_days=30, last_completed=long_ago)
    mine = {i.title for i in today_items(context)}
    assert mine == {"Service: Mower", "Service: Furnace"}
    faith_view = ScopedView(context, (), profile_id=faith.profile_id)
    assert {i.title for i in today_items(faith_view)} == {"Service: Truck", "Service: Furnace"}


def test_the_item_window_has_an_owner_choice(home):
    from PySide6.QtWidgets import QApplication

    from gui.add_edit_asset_dialog import AddEditAssetDialog

    QApplication.instance() or QApplication([])
    context, zac, faith = home
    from core.data_logger_manager import DataLoggerManager

    context.data_logger = DataLoggerManager(context, data_dir=context.maintenance.data_dir)
    asset = context.maintenance.add_asset(name="Truck", owner_profile_id=faith.profile_id)
    dialog = AddEditAssetDialog(asset=asset, maintenance=context.maintenance, context=context)
    assert dialog.owner_combo.currentText() == "Faith" and dialog.entered_owner_profile_id == faith.profile_id
    assert AddEditAssetDialog().entered_owner_profile_id is None  # without people: shared
