"""
Each person's own MIA (core/personal_data.py): conversations, memories,
journal, notes, reasons and MIA's message log belong to the person, not
the device; the formerly shared files move to the owner once.
"""

import json
import time

import pytest

import core.config_manager as config_module
from core.app_context import AppContext
from core.communication_gate import CommunicationGate
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.personal_data import PersonalData, view_for
from core.profile_manager import ProfileManager


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    faith = context.profiles.create_profile("Faith", make_active=False)
    shared = tmp_path / "shared"
    shared.mkdir()
    context.personal_data = PersonalData(context, profiles_dir=tmp_path / "profiles", shared_dir=shared)
    context.personal_data.watch(context.events)
    return context, zac, faith, shared, tmp_path


def test_each_person_sees_only_their_own(home):
    context, zac, faith, _, _ = home
    z, f = context.personal_data.view(zac.profile_id), context.personal_data.view(faith.profile_id)
    z.conversations.create_conversation()
    z.user_memories.add_memory("Zac's truck is a 2015 F-150", category="Facts")
    z.intents.add_intent("Pay off debt")
    z.journal.add_entry(title="Shop list", body="hinges")
    assert f.conversations.all_conversations() == [] and f.user_memories.all_memories() == []
    assert f.intents.all_intents() == [] and f.journal.all_entries() == []
    # Saved in each person's own folder.
    assert (context.personal_data.folder(zac.profile_id) / "conversations.json").exists()
    assert not (context.personal_data.folder(faith.profile_id) / "conversations.json").exists()
    # Shared services are the same objects.
    assert z.config is context.config and z.events is context.events


def test_signing_in_swaps_every_screen_to_that_person(home):
    context, zac, faith, _, _ = home
    context.profiles.set_active_profile(zac.profile_id)
    context.conversations.create_conversation()
    context.profiles.set_active_profile(faith.profile_id)
    assert context.conversations.all_conversations() == []
    context.profiles.set_active_profile(zac.profile_id)
    assert len(context.conversations.all_conversations()) == 1


def test_formerly_shared_files_go_to_the_owner_once(home):
    context, zac, faith, shared, tmp_path = home
    (shared / "conversations.json").write_text(json.dumps([{"conversation_id": "old1", "title": "Old chat"}]))
    (shared / "intents.json").write_text("[]")
    # Faith signs in first: she gets nothing of Zac's.
    assert context.personal_data.view(faith.profile_id).conversations.all_conversations() == []
    assert (shared / "conversations.json").exists()
    zac_view = context.personal_data.view(zac.profile_id)
    assert [c.title for c in zac_view.conversations.all_conversations()] == ["Old chat"]
    assert not (shared / "conversations.json").exists()
    marker = json.loads((tmp_path / "profiles" / ".shared_data_claimed").read_text())
    assert marker["profile_id"] == zac.profile_id and "conversations.json" in marker["moved"]
    # Once only: a file appearing later isn't moved again.
    fresh = PersonalData(context, profiles_dir=tmp_path / "profiles", shared_dir=shared)
    (shared / "user_memories.json").write_text("[]")
    fresh.view(zac.profile_id)
    assert (shared / "user_memories.json").exists()


def test_each_person_has_their_own_private_journal(home):
    context, zac, faith, _, _ = home
    z, f = context.personal_data.view(zac.profile_id), context.personal_data.view(faith.profile_id)
    z.private_journal.setup("zac's long passphrase")
    assert z.private_journal.is_set_up() and not f.private_journal.is_set_up()
    f.private_journal.setup("faith's own passphrase")
    assert not z.private_journal.verify_passphrase("faith's own passphrase")


def test_the_phone_runs_a_turn_as_its_own_person(home):
    context, zac, faith, _, _ = home
    context.profiles.set_active_profile(zac.profile_id)  # Zac at the desk
    faith_view = view_for(context, faith.profile_id)  # Faith on her phone
    assert faith_view.conversations is not context.conversations
    assert view_for(context, zac.profile_id).conversations is context.conversations
    plain = AppContext(config=context.config, events=context.events)
    assert view_for(plain, "anyone") is plain


def test_reasons_checkpoints_follow_the_person(home):
    from core.why_graph import _checkpoints_file

    context, zac, _, _, _ = home
    z = context.personal_data.view(zac.profile_id)
    assert _checkpoints_file(z).parent == context.personal_data.folder(zac.profile_id)


def test_a_replaced_store_stops_listening(home):
    context, zac, _, _, _ = home
    boot_gate = CommunicationGate(context)  # the one built at boot, on the shared folder
    context.communication = boot_gate
    listeners = context.events._subscribers["notification.dismissed"]
    assert boot_gate._on_notification_dismissed in listeners
    context.personal_data.activate(zac.profile_id)
    assert context.communication is not boot_gate
    assert boot_gate._on_notification_dismissed not in listeners
    assert context.communication._on_notification_dismissed in listeners


def test_a_new_active_profile_gets_its_own_data_right_away(home):
    context, _, _, _, _ = home
    context.conversations = None
    newcomer = context.profiles.create_profile("Sam", make_active=True)
    assert context.personal_data.active_profile_id == newcomer.profile_id
    assert context.conversations.all_conversations() == []
    other = context.profiles.create_profile("Guest", make_active=False)
    assert context.personal_data.active_profile_id == newcomer.profile_id and other
