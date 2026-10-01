"""
Accounts and households (2026-10-01): sign in with an email, recover a
forgotten password with a recovery code, and share household things only
after joining a household with a current member's approval
(core/profile_manager.py, core/household_manager.py, core/personal_data.py).
"""

import json
import time

import pytest

import core.calendar_manager as calendar_module
import core.config_manager as config_module
import core.kitchen_manager as kitchen_module
import core.profile_manager as profile_module
import core.workout_manager as workout_module
from core.app_context import AppContext
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.household_manager import HouseholdManager
from core.kitchen_manager import KitchenManager
from core.personal_data import FIRST_LEGACY_FILES, PersonalData, view_for
from core.profile_manager import AccountError, ProfileManager, looks_like_email, new_recovery_code
from core.workout_manager import WorkoutManager


@pytest.fixture
def device(tmp_path, monkeypatch):
    """A device with the shared data/ folder at tmp/shared."""
    shared = tmp_path / "shared"
    shared.mkdir()
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    for module, files in ((calendar_module, ("_EVENTS_FILE",)), (workout_module, ("_EXERCISES_FILE", "_TEMPLATES_FILE", "_SESSIONS_FILE")),
                          (kitchen_module, ("_RECIPES_FILE", "_PANTRY_FILE", "_GROCERY_LIST_FILE", "_MEAL_LOG_FILE", "_RECIPE_USER_STATS_FILE"))):
        monkeypatch.setattr(module, "_DATA_DIR", shared)
        for name in files:
            monkeypatch.setattr(module, name, shared / getattr(module, name).name)
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    return context, shared, tmp_path


def _boot(context, shared, tmp_path):
    """What the app does at boot: households, the stores, then personal data."""
    context.households = HouseholdManager(context)
    context.calendar = CalendarManager(context)
    context.kitchen = KitchenManager(context)
    context.workout = WorkoutManager(context)
    context.personal_data = PersonalData(context, profiles_dir=tmp_path / "profiles", shared_dir=shared)
    context.personal_data.watch(context.events)
    context.personal_data.activate_current()
    return context


# ------------------------------------------------------------------ accounts


def test_sign_up_and_sign_in_with_email(device):
    context, _, _ = device
    profiles = context.profiles
    sam = profiles.create_profile("Sam", password="pw1", email="  Sam@Example.com ")
    assert sam.email == "sam@example.com"
    assert profiles.find_by_email("SAM@example.COM").profile_id == sam.profile_id
    assert profiles.sign_in("sam@EXAMPLE.com", "pw1").profile_id == sam.profile_id
    assert profiles.sign_in("sam@example.com", "nope") is None
    assert profiles.sign_in("Sam", "pw1").profile_id == sam.profile_id  # the name still works when unique
    with pytest.raises(AccountError, match="already"):
        profiles.create_profile("Other Sam", password="x", email="sam@example.com")
    with pytest.raises(AccountError, match="doesn't look like"):
        profiles.create_profile("Typo", email="sam.example.com")
    assert [p.name for p in profiles.list_profiles()] == ["Sam"]  # nothing saved for the refusals


def test_existing_profiles_add_an_email_later(device):
    context, _, _ = device
    profiles = context.profiles
    old = profiles.create_profile("Lee", password="pw")
    other = profiles.create_profile("Kim", password="pw2", email="kim@example.com")
    assert profiles.set_email(old.profile_id, "Lee@Example.com")
    assert profiles.get_profile(old.profile_id).email == "lee@example.com"
    with pytest.raises(AccountError):
        profiles.set_email(old.profile_id, "kim@example.com")
    assert profiles.set_email(other.profile_id, "kim@example.com")  # your own email again is fine


def test_same_names_need_the_email(device):
    context, _, _ = device
    profiles = context.profiles
    profiles.create_profile("Alex", password="a", email="alex1@example.com")
    profiles.create_profile("alex", password="b", email="alex2@example.com")
    assert profiles.find_for_sign_in("Alex") is None
    assert profiles.sign_in("alex2@example.com", "b").name == "alex"


def test_a_recovery_code_resets_a_forgotten_password(device):
    context, _, _ = device
    profiles = context.profiles
    sam = profiles.create_profile("Sam", password="old", email="sam@example.com")
    code = profiles.issue_recovery_code(sam.profile_id)
    assert len(code) == 19 and code.count("-") == 3
    assert code not in json.dumps(context.config.get(f"profiles.{sam.profile_id}"))  # only its hash is kept
    assert profiles.reset_password_with_code("sam@example.com", "WRONG-CODE-0000-0000", "new") is None
    fresh = profiles.reset_password_with_code("sam@example.com", code.lower().replace("-", " "), "new")
    assert fresh and fresh != code
    assert profiles.sign_in("sam@example.com", "new") and not profiles.sign_in("sam@example.com", "old")
    assert profiles.reset_password_with_code("sam@example.com", code, "again") is None  # used up


def test_pure_helpers():
    assert looks_like_email("a.b+c@mail.example.org") and not looks_like_email("a@b") and not looks_like_email("")
    codes = {new_recovery_code() for _ in range(50)}
    assert len(codes) == 50 and not any(ch in "".join(codes) for ch in "01OIL")


# ------------------------------------------------------------------ households


def test_profiles_already_on_the_device_become_one_household(device):
    context, shared, tmp_path = device
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    _boot(context, shared, tmp_path)
    households = context.households
    hid = households.household_of(zac.profile_id)
    assert households.household_of(faith.profile_id) == hid and households.is_first(hid)
    assert households.folder(hid) is None  # keeps the main data/ folder
    view_for(context, zac.profile_id).calendar.add_event(title="Dentist", date="2026-10-05")
    assert [e.title for e in view_for(context, faith.profile_id).calendar.all_events()] == ["Dentist"]
    assert (shared / "calendar_events.json").exists()


def test_a_new_account_shares_nothing(device):
    context, shared, tmp_path = device
    zac = context.profiles.create_profile("Zac", make_active=True)
    _boot(context, shared, tmp_path)
    context.calendar.add_event(title="Dentist", date="2026-10-05")
    context.kitchen.add_grocery_item("milk")
    sam = context.profiles.create_profile("Sam", password="pw", email="sam@example.com", make_active=False)
    households = context.households
    assert households.household_of(sam.profile_id) != households.household_of(zac.profile_id)
    sam_view = view_for(context, sam.profile_id)
    assert sam_view.calendar.all_events() == [] and sam_view.kitchen.all_grocery_items() == []
    sam_view.calendar.add_event(title="Sam's thing", date="2026-10-06")
    assert [e.title for e in context.calendar.all_events()] == ["Dentist"]
    folder = households.folder(households.household_of(sam.profile_id))
    assert folder.parent == tmp_path / "households" and (folder / "calendar_events.json").exists()
    # Signing in swaps every screen to Sam's household.
    context.profiles.set_active_profile(sam.profile_id)
    assert [e.title for e in context.calendar.all_events()] == ["Sam's thing"]
    context.profiles.set_active_profile(zac.profile_id)
    assert [e.title for e in context.calendar.all_events()] == ["Dentist"]


def test_joining_a_household_needs_a_members_password(device):
    context, shared, tmp_path = device
    zac = context.profiles.create_profile("Zac", password="zacpw", make_active=True)
    _boot(context, shared, tmp_path)
    context.calendar.add_event(title="Dentist", date="2026-10-05")
    faith = context.profiles.create_profile("Faith", password="fpw", email="faith@example.com", make_active=False)
    households = context.households
    home = households.household_of(zac.profile_id)
    assert not households.join(faith.profile_id, home, zac.profile_id, "wrong")
    assert not households.join(faith.profile_id, home, faith.profile_id, "fpw")  # can't approve yourself
    assert households.household_of(faith.profile_id) != home
    changed = []
    context.events.subscribe("records.changed", lambda **kw: changed.append(kw))
    context.profiles.set_active_profile(faith.profile_id)
    assert context.calendar.all_events() == []
    assert households.join(faith.profile_id, home, zac.profile_id, "zacpw")
    assert households.household_of(faith.profile_id) == home
    # Faith is signed in: her screens now show the household's things.
    assert [e.title for e in context.calendar.all_events()] == ["Dentist"] and changed
    assert [p.name for p in households.shares_with(faith.profile_id)] == ["Zac"]
    # Her own things stay her own.
    assert context.personal_data.view(zac.profile_id).workout is not context.workout


def test_leaving_starts_an_empty_household_and_leaves_the_shared_things(device):
    context, shared, tmp_path = device
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    _boot(context, shared, tmp_path)
    context.calendar.add_event(title="Dentist", date="2026-10-05")
    households = context.households
    home = households.household_of(zac.profile_id)
    new = households.leave(zac.profile_id)
    assert new and households.household_of(zac.profile_id) == new != home
    assert view_for(context, zac.profile_id).calendar.all_events() == []
    assert [e.title for e in view_for(context, faith.profile_id).calendar.all_events()] == ["Dentist"]
    assert households.leave(faith.profile_id) is None  # alone now: nothing to leave


def test_the_first_account_on_a_new_device_keeps_the_main_folder(device):
    context, shared, tmp_path = device
    _boot(context, shared, tmp_path)  # fresh install: no profiles yet
    first = context.profiles.create_profile("Robin", password="pw", email="robin@example.com")
    hid = context.households.household_of(first.profile_id)
    assert context.households.is_first(hid)
    context.calendar.add_event(title="Move in", date="2026-10-02")
    assert (shared / "calendar_events.json").exists()


# ------------------------------------------------------------------ personal: workouts, classes


def test_workouts_are_personal_and_the_owner_claims_old_ones(device):
    context, shared, tmp_path = device
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    # The first personal-data move already happened (an older marker).
    (tmp_path / "profiles").mkdir(exist_ok=True)
    (tmp_path / "profiles" / ".shared_data_claimed").write_text(json.dumps(
        {"profile_id": zac.profile_id, "moved": ["conversations.json"]}))
    (shared / "workout_sessions.json").write_text("[]")
    (shared / "conversations.json").write_text("[]")  # appeared later: never moved twice
    _boot(context, shared, tmp_path)
    assert not (shared / "workout_sessions.json").exists()
    assert (context.personal_data.folder(zac.profile_id) / "workout_sessions.json").exists()
    assert (shared / "conversations.json").exists()
    marker = json.loads((tmp_path / "profiles" / ".shared_data_claimed").read_text())
    assert set(FIRST_LEGACY_FILES) <= set(marker["claimed"]) and "workout_sessions.json" in marker["moved"]
    assert view_for(context, faith.profile_id).workout is not view_for(context, zac.profile_id).workout


# ------------------------------------------------------------------ the desktop screens


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_new_profile_dialog_checks_email_and_household_approval(device, qapp):
    from gui.add_profile_dialog import AddProfileDialog

    context, shared, tmp_path = device
    zac = context.profiles.create_profile("Zac", password="zacpw", email="zac@example.com", make_active=True)
    _boot(context, shared, tmp_path)
    dialog = AddProfileDialog(context=context)
    dialog.name_edit.setText("Faith")
    dialog.email_edit.setText("zac@example.com")
    dialog._on_accept()
    assert "already" in dialog.error_label.text()
    dialog.email_edit.setText("faith@example.com")
    dialog._on_accept()
    assert "needs a password" in dialog.error_label.text() and dialog.password_checkbox.isChecked()
    dialog.password_edit.setText("fpw")
    choice = dialog.household_choice
    choice.household_combo.setCurrentIndex(1)  # Zac's household
    assert choice.approver_combo.currentData() == zac.profile_id
    choice.approver_password.setText("wrong")
    dialog._on_accept()
    assert "doesn't match" in dialog.error_label.text()
    choice.approver_password.setText("zacpw")
    dialog._on_accept()
    assert dialog.result() == AddProfileDialog.DialogCode.Accepted and dialog.entered_email == "faith@example.com"
    faith = context.profiles.create_profile("Faith", password="fpw", email=dialog.entered_email, make_active=False)
    assert choice.apply(faith.profile_id)
    assert context.households.household_of(faith.profile_id) == context.households.household_of(zac.profile_id)


def test_sign_in_and_recover_dialogs(device, qapp, monkeypatch):
    import gui.account_dialogs as dialogs

    context, shared, tmp_path = device
    sam = context.profiles.create_profile("Sam", password="old", email="sam@example.com")
    _boot(context, shared, tmp_path)
    code = context.profiles.issue_recovery_code(sam.profile_id)
    sign_in = dialogs.SignInDialog(context)
    sign_in.identifier_edit.setText("SAM@example.com")
    sign_in.password_edit.setText("nope")
    sign_in._on_accept()
    assert sign_in.profile is None and "don't match" in sign_in.error_label.text()
    sign_in.password_edit.setText("old")
    sign_in._on_accept()
    assert sign_in.profile.profile_id == sam.profile_id

    shown = []
    monkeypatch.setattr(dialogs, "show_recovery_code", lambda c, parent=None: shown.append(c))
    monkeypatch.setattr(dialogs.QMessageBox, "information", lambda *a, **k: None)
    recover = dialogs.RecoverPasswordDialog(context, "sam@example.com")
    recover.code_edit.setText(code)
    recover.new_edit.setText("new")
    recover.confirm_edit.setText("new")
    recover._on_accept()
    assert shown and shown[0] != code and context.profiles.sign_in("sam@example.com", "new")

    account = dialogs.AccountDialog(context, context.profiles.get_profile(sam.profile_id))
    assert "don't share" in account.household_label.text() and not account.leave_button.isEnabled()
    account.email_edit.setText("not an email")
    account._on_save_email()
    assert "doesn't look like" in account.message_label.text()


# ------------------------------------------------------------------ each person's own settings


def test_settings_are_each_persons_own(device):
    from core import person_settings
    from core.safety_floor import trusted_contact_from

    context, shared, tmp_path = device
    context.config.set("assistant.safety.trusted_contact", "my brother")  # set before settings were per person
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    _boot(context, shared, tmp_path)
    zac_view, faith_view = view_for(context, zac.profile_id), view_for(context, faith.profile_id)
    assert trusted_contact_from(zac_view) == "my brother"  # the first account keeps it
    assert trusted_contact_from(faith_view) is None  # nobody inherits someone else's contact
    person_settings.put(faith_view, "communication.daily_budget", 2)
    assert person_settings.get(faith_view, "communication.daily_budget", 5) == 2
    assert person_settings.get(zac_view, "communication.daily_budget", 5) == 5
    assert person_settings.get(context, "communication.daily_budget", 5) == 5  # Zac is signed in
    context.profiles.set_active_profile(faith.profile_id)
    assert person_settings.get(context, "communication.daily_budget", 5) == 2
    assert context.config.get("communication.daily_budget") == 5  # the device-wide value is untouched


def test_notifications_are_each_persons_own(device):
    import core.notification_manager as notification_module
    from core.notification_manager import NotificationManager
    from core.web_push import _relay_notification_to_all_subscriptions

    context, shared, tmp_path = device
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    notification_module._DATA_DIR, saved = shared, (notification_module._DATA_DIR, notification_module._NOTIFICATIONS_FILE)
    notification_module._NOTIFICATIONS_FILE = shared / "notifications.json"
    try:
        context.notifications = NotificationManager(context)
        _boot(context, shared, tmp_path)
        created = []
        context.events.subscribe("notification.created", lambda **kw: created.append(kw["profile_id"]))
        view_for(context, faith.profile_id).notifications.notify(title="Hi Faith", message="x")
        assert context.notifications.list_all() == [] and created == [faith.profile_id]
        sent = []
        context.push_subscriptions = type("Subs", (), {
            "subscriptions_for_profile": lambda self, pid: [f"{pid}-phone"],
            "all_subscriptions": lambda self: ["every-phone"]})()
        import core.web_push as web_push

        original = web_push.send_web_push
        web_push.send_web_push = lambda sub, *a: sent.append(sub)
        try:
            _relay_notification_to_all_subscriptions(context, type("N", (), {"title": "Hi", "message": "x"})(), faith.profile_id)
        finally:
            web_push.send_web_push = original
        assert sent == [f"{faith.profile_id}-phone"]
    finally:
        notification_module._DATA_DIR, notification_module._NOTIFICATIONS_FILE = saved


def test_the_phone_signs_in_with_email(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app_module

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile("Robin", password="pw", email="robin@example.com")
    context.voice = context.llm = context.push_subscriptions = None
    client = TestClient(server_app_module.create_app(context))
    assert client.post("/api/login", json={"profile_id": "Robin@Example.com", "password": "pw"}).status_code == 200
    assert client.post("/api/login", json={"profile_id": "robin@example.com", "password": "no"}).status_code == 401
    assert client.post("/api/login", json={"profile_id": "Robin", "password": "pw"}).status_code == 200
