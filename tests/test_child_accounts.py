"""
Child accounts (core/child_accounts.py), 2026-10-01: a parent looks after
a child's MIA; grown-up apps and tools say "ask a parent", the Assistant
is told it's talking with a child, and the safety floor also asks the
child to tell an adult.
"""

from datetime import date
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import child_accounts
from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.child_accounts import (ASK_A_PARENT, age, app_allowed, children_of, guardian_reset_password, guardians_of,
                                 is_child, make_adult, make_child, prompt_note, tool_allowed)
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager
from core.safety_floor import safety_reply


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def family(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    parent = context.profiles.create_profile("Robin", password="parentpw")
    kid = context.profiles.create_profile("Ari", password="kidpw")
    context.profiles.set_birthday(kid.profile_id, "2016-05-20")
    assert make_child(context, kid.profile_id, [parent.profile_id])
    return context, parent, kid


def _as(context, profile):
    context.profiles.set_active_profile(profile.profile_id)
    return context


def test_who_is_a_child_and_who_looks_after_them(family):
    context, parent, kid = family
    assert is_child(context, kid.profile_id) and not is_child(context, parent.profile_id)
    assert guardians_of(context, kid.profile_id) == [parent.profile_id]
    assert [c.profile_id for c in children_of(context, parent.profile_id)] == [kid.profile_id]
    assert not make_child(context, kid.profile_id, [])  # a child always has a guardian
    assert age("2016-05-20", date(2026, 10, 1)) == 10 and age("2016-10-02", date(2026, 10, 1)) == 9
    assert age(None) is None and age("someday") is None


def test_apps_a_child_can_open(family):
    context, parent, kid = family
    _as(context, kid)
    assert app_allowed(context, "music") and app_allowed(context, "settings")
    assert not app_allowed(context, "budget") and not app_allowed(context, "module_browser")
    from core.focus_presets import menu_modules

    modules = [SimpleNamespace(module_id=m, display_name=m) for m in ("music", "budget", "notes", "inbox")]
    assert {m.module_id for m in menu_modules(context, modules)} == {"music", "notes"}
    _as(context, parent)
    assert app_allowed(context, "budget")


def test_the_assistant_never_offers_or_runs_grown_up_tools(family):
    context, parent, kid = family
    ran = []
    registry = AssistantActionRegistry()
    registry.register(AssistantAction("list_bills", "Bills.", {"type": "object", "properties": {}},
                                      lambda ctx, args: ran.append("bills") or "Rent.", ("bills",), "budget"))
    registry.register(AssistantAction("list_songs", "Songs.", {"type": "object", "properties": {}},
                                      lambda ctx, args: "A song.", ("songs",), "music"))
    _as(context, kid)
    assert not tool_allowed(context, "budget") and tool_allowed(context, "music") and tool_allowed(None, "budget")
    assert [a.name for a in registry.matching_actions("show my bills and songs", context)] == ["list_songs"]
    assert registry.execute(context, "list_bills", {}) == ASK_A_PARENT and ran == []
    assert registry.execute(context, "list_songs", {}) == "A song."
    _as(context, parent)
    assert "list_bills" in [a.name for a in registry.matching_actions("show my bills", context)]


def test_the_assistant_knows_it_is_talking_with_a_child(family):
    context, parent, kid = family
    from core.assistant_chat import build_user_context_block

    context.user_memories = None
    _as(context, kid)
    note = prompt_note(context)
    assert "a child" in note and "years old" in note and "money" in note
    assert build_user_context_block(context).startswith(note)
    assert "Name: Ari" in build_user_context_block(context)
    _as(context, parent)
    assert prompt_note(context) == "" and "child" not in build_user_context_block(context)
    # A phone turn is for the person on it, not whoever sits at the desktop.
    phone = SimpleNamespace(config=context.config, profiles=context.profiles, profile_id=kid.profile_id,
                            user_memories=None)
    assert "Name: Ari" in build_user_context_block(phone) and "a child" in build_user_context_block(phone)


def test_safety_floor_also_asks_a_child_to_tell_an_adult():
    assert "grown-up you trust" in safety_reply(child=True)
    assert "grown-up" not in safety_reply()


def test_today_leaves_out_bills_for_a_child(family):
    context, parent, kid = family
    from core import today

    bill = SimpleNamespace(name="Rent", amount=900, bill_id="b1")
    context.budget = SimpleNamespace(all_bills=lambda: [bill], all_income_sources=lambda: [])
    import core.budget_manager as budget_manager

    real = budget_manager.days_until_bill_due
    budget_manager.days_until_bill_due = lambda b, d: 0
    try:
        _as(context, parent)
        assert [i.title for i in today.today_items(context)] == ["Pay Rent"]
        _as(context, kid)
        assert today.today_items(context) == []
    finally:
        budget_manager.days_until_bill_due = real


def test_a_guardian_resets_the_password_and_can_make_it_regular(family):
    context, parent, kid = family
    stranger = context.profiles.create_profile("Sam", password="sampw")
    assert not guardian_reset_password(context, kid.profile_id, stranger.profile_id, "sampw", "new")
    assert not guardian_reset_password(context, kid.profile_id, parent.profile_id, "wrong", "new")
    assert guardian_reset_password(context, kid.profile_id, parent.profile_id, "parentpw", "newkidpw")
    assert context.profiles.verify_password(kid.profile_id, "newkidpw")
    assert not make_adult(context, kid.profile_id, stranger.profile_id)
    assert make_adult(context, kid.profile_id, parent.profile_id)
    assert not is_child(context, kid.profile_id) and children_of(context, parent.profile_id) == []


def test_the_phone_money_view_is_closed_to_a_child(family):
    from fastapi.testclient import TestClient

    import server.app as server_app

    context, parent, kid = family
    context.voice = context.llm = context.push_subscriptions = None
    client = TestClient(server_app.create_app(context))
    token = client.post("/api/login", json={"profile_id": kid.profile_id, "password": "kidpw"}).json()["token"]
    res = client.get("/api/finance/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403 and res.json()["detail"] == ASK_A_PARENT


def test_a_child_s_settings_show_only_their_own_look(family, qapp):
    from PySide6.QtWidgets import QPushButton

    from modules.settings.module import SettingsModule

    context, parent, kid = family
    _as(context, kid)
    widget = SettingsModule(context).get_widget()
    buttons = [b.text() for b in widget.findChildren(QPushButton)]
    assert buttons == ["⇄ Switch User"]


def test_adding_a_child_needs_a_household(family, qapp):
    from core.household_manager import HouseholdManager
    from gui.add_profile_dialog import AddProfileDialog

    context, parent, kid = family
    context.households = HouseholdManager(context)
    dialog = AddProfileDialog(context=context)
    dialog.name_edit.setText("Jo")
    dialog.child_checkbox.setChecked(True)
    assert dialog.is_child and dialog.household_choice.household_id is None
    dialog._on_accept()
    assert "child" in dialog.error_label.text() and dialog.result() == 0
    dialog.household_choice.household_combo.setCurrentIndex(1)
    assert dialog.household_choice.approver_id == parent.profile_id
    dialog.household_choice.approver_password.setText("parentpw")
    dialog._on_accept()
    assert dialog.result() == 1


def test_module_constants_are_sane():
    assert "settings" in child_accounts.CHILD_APPS and "budget" in child_accounts.CHILD_BLOCKED_DOMAINS
    assert not child_accounts.CHILD_APPS & child_accounts.CHILD_BLOCKED_DOMAINS
