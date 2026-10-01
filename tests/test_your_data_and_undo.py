"""
Accounts stage 5 (2026-10-01): export and delete your account
(core/account_data.py), "undo that" (core/undo_log.py), "why did you
tell me that?" / "stop telling me about ..." (core/message_reasons.py),
and the setup checker (core/system_check.py).
"""

import json
import time
import zipfile
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import core.calendar_manager as calendar_module
import core.config_manager as config_module
import core.profile_manager as profile_module
from core.account_data import delete_account, export_account
from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_undo_actions import (_action_get_recent_changes, _action_mute_message_topic,
                                         _action_undo_last_change, _action_why_that_message)
from core.calendar_manager import CalendarManager
from core.communication_gate import ACT, Candidate
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.household_manager import HouseholdManager
from core.message_reasons import REASONS, explain, find_topic
from core.personal_data import PersonalData, view_for
from core.profile_manager import ProfileManager
from core.system_check import MISSING, OK, OPTIONAL, check_model, run_checks, summary
from core.undo_log import UndoLog


@pytest.fixture
def home(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    shared.mkdir()
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setattr(calendar_module, "_DATA_DIR", shared)
    monkeypatch.setattr(calendar_module, "_EVENTS_FILE", shared / "calendar_events.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    zac = context.profiles.create_profile("Zac", password="zpw", email="zac@example.com", make_active=True)
    time.sleep(0.01)
    sam = context.profiles.create_profile("Sam", password="spw", make_active=False)
    context.households = HouseholdManager(context)
    context.undo = UndoLog()
    context.calendar = CalendarManager(context)
    context.personal_data = PersonalData(context, profiles_dir=tmp_path / "profiles", shared_dir=shared)
    context.personal_data.watch(context.events)
    context.personal_data.activate_current()
    return SimpleNamespace(context=context, zac=zac, sam=sam, tmp=tmp_path, shared=shared)


# ------------------------------------------------------------------ export and delete


def test_export_has_your_things_and_no_secrets(home):
    context, zac = home.context, home.zac
    context.conversations.create_conversation()
    context.calendar.add_event(title="Dentist", date="2026-10-05")
    (context.personal_data.folder(zac.profile_id) / "mail_send.enc").write_bytes(b"secret")
    path = export_account(context, zac.profile_id, home.tmp / "out", include_household=True)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        profile = json.loads(archive.read("profile.json"))
    assert "README.txt" in names and "personal/conversations.json" in names
    assert "household/calendar_events.json" in names and "personal/mail_send.enc" not in names
    assert profile["email"] == "zac@example.com" and "password_hash" not in profile and "recovery_hash" not in profile
    assert profile["household"]["shared_with"] == ["Sam"]
    without = export_account(context, zac.profile_id, home.tmp / "out2.zip")
    assert not any(n.startswith("household/") for n in zipfile.ZipFile(without).namelist())


def test_delete_needs_the_password_and_can_erase(home):
    context, sam = home.context, home.sam
    sam_view = view_for(context, sam.profile_id)
    sam_view.conversations.create_conversation()
    folder = context.personal_data.folder(sam.profile_id)
    assert folder.exists()
    assert not delete_account(context, sam.profile_id, "wrong")
    assert delete_account(context, sam.profile_id, "spw", erase=True)
    assert context.profiles.get_profile(sam.profile_id) is None
    assert not folder.exists() and not list((home.tmp / "profiles").glob(f"_deleted_{sam.profile_id}_*"))
    # Its stores stopped: nothing recreates the folder.
    sam_view.conversations.create_conversation()  # an old reference saving again...
    assert sam.profile_id not in context.personal_data._personal
    # The household is still Zac's.
    assert context.households.household_of(home.zac.profile_id)
    assert not delete_account(context, home.zac.profile_id, "zpw")  # the only account left


def test_delete_without_erase_archives(home):
    context, sam = home.context, home.sam
    view_for(context, sam.profile_id).conversations.create_conversation()
    assert delete_account(context, sam.profile_id, "spw")
    assert list((home.tmp / "profiles").glob(f"_deleted_{sam.profile_id}_*"))


# ------------------------------------------------------------------ undo


def _registry():
    registry = AssistantActionRegistry()
    registry.register(AssistantAction(
        name="add_calendar_event", domain="calendar", description="", parameters={},
        handler=lambda ctx, a: ctx.calendar.add_event(title=a["title"], date="2026-10-05") and "Added."))
    registry.register(AssistantAction(name="get_calendar", domain="calendar", description="", parameters={},
                                      handler=lambda ctx, a: "nothing"))
    return registry


def test_undo_puts_back_what_mia_changed(home):
    context = home.context
    registry = _registry()
    context.calendar.add_event(title="Dentist", date="2026-10-05")  # by hand: not MIA's to undo
    refreshed = []
    context.events.subscribe("records.changed", lambda **kw: refreshed.append(kw["action"]))
    registry.execute(context, "add_calendar_event", {"title": "Wrong thing"})
    registry.execute(context, "get_calendar", {})  # read-only: nothing recorded
    assert [e.title for e in context.calendar.all_events()] == ["Dentist", "Wrong thing"]
    assert "add calendar event" in _action_get_recent_changes(context, {})
    old_store = context.calendar
    assert "Undone" in _action_undo_last_change(context, {})
    assert [e.title for e in context.calendar.all_events()] == ["Dentist"]
    assert context.calendar is not old_store  # re-read from the restored file
    assert context.personal_data.view(home.zac.profile_id).calendar is context.calendar
    assert "undo" in refreshed
    assert "nothing of mine to undo" in _action_undo_last_change(context, {})


def test_undo_of_a_first_file_removes_it(home):
    context = home.context
    _registry().execute(context, "add_calendar_event", {"title": "First"})
    assert (home.shared / "calendar_events.json").exists()
    _action_undo_last_change(context, {})
    assert not (home.shared / "calendar_events.json").exists() and context.calendar.all_events() == []


def test_each_person_undoes_their_own(home):
    context = home.context
    registry = _registry()
    registry.execute(context, "add_calendar_event", {"title": "Zac's"})
    sam_view = view_for(context, home.sam.profile_id)
    assert "nothing of mine to undo" in _action_undo_last_change(sam_view, {})
    assert [e.title for e in context.calendar.all_events()] == ["Zac's"]


# ------------------------------------------------------------------ why, and stop telling me


def test_why_that_message_and_muting(home):
    context = home.context
    gate = context.communication
    assert "haven't sent you anything" in _action_why_that_message(context, {})
    now = datetime(2026, 10, 1, 9, 0)
    gate.offer(Candidate(topic="budget_nudge", title="Budget check", message="Rent is due Friday."), now=now)
    reply = _action_why_that_message(context, {})
    assert "Budget check" in reply and "bill is due soon" in reply and "stop telling me about budget check-ins" in reply
    assert "no more budget check-ins" in _action_mute_message_topic(context, {"topic": "the budget", "days": 7})
    later = now + timedelta(hours=5)
    [decision] = gate.offer(Candidate(topic="budget_nudge", title="Budget", message="Payday tomorrow."), now=later)
    assert decision.action != ACT
    assert [p["topic"] for p in gate.paused(later)] == ["budget_nudge"]
    gate.resume("budget_nudge", later)
    assert gate.paused(later) == []


def test_reasons_cover_every_kind_and_words_find_them():
    import subprocess

    raised = subprocess.run(["grep", "-rhoP", r'topic="\K[a-z_]+', "core", "gui", "modules"],
                            capture_output=True, text=True).stdout.split()
    assert set(raised) <= set(REASONS), set(raised) - set(REASONS)
    assert find_topic("my budget") == "budget_nudge" and find_topic("the check-ins") == "checkin"
    assert find_topic("warranties") == "warranty" and find_topic("") is None
    assert "I told you" in explain({"topic": "unknown_kind", "title": "Hi"})


# ------------------------------------------------------------------ setup checker


def test_model_check_says_exactly_what_to_do():
    config = SimpleNamespace(get=lambda key, default=None: default)
    assert check_model(config, models=lambda url: None).status == MISSING
    missing = check_model(config, models=lambda url: ["mistral:latest"])
    assert missing.status == MISSING and "ollama pull llama3.2:3b" in missing.fix
    assert check_model(config, models=lambda url: ["llama3.2:3b"]).status == OK


def test_setup_checks_and_summary(home):
    context = home.context
    context.voice = SimpleNamespace(is_stt_available=lambda: True, is_tts_available=lambda: False)
    checks = run_checks(context, models=lambda url: ["llama3.2:latest"], data_dir=home.tmp / "data")
    by_name = {c.name: c for c in checks}
    assert by_name["Assistant's model"].status == OK and by_name["Hearing you (speech to text)"].status == OK
    assert by_name["Speaking (text to speech)"].status == OPTIONAL
    assert by_name["Saving your data"].status == OK and by_name["Your account"].status == OK
    text = summary(checks)
    assert text.startswith("Everything I need works.") and "speaking" in text
    broken = run_checks(context, models=lambda url: None, data_dir=home.tmp / "data")
    assert summary(broken).startswith("Needs fixing: Assistant's model")


def test_setup_check_window(home):
    from PySide6.QtWidgets import QApplication

    from gui.setup_check_dialog import SetupCheckDialog
    from core.system_check import Check

    QApplication.instance() or QApplication([])
    dialog = SetupCheckDialog(home.context, checks=[Check("Assistant's model", MISSING, "Not running.", "ollama serve")])
    assert dialog.rows.count() == 1 and "ollama serve" in dialog.rows.itemAt(0).widget().text()
