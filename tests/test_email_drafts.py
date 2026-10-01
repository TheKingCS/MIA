"""
Email drafts (core/email_drafts.py, core/mail_send.py,
core/assistant_email_actions.py), 2026-10-01: MIA writes, the person
sends (only by pressing Send), copies, or opens their mail app.
"""

import smtplib
import time
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core.app_context import AppContext
from core.assistant_email_actions import _action_draft_email
from core.config_manager import ConfigManager
from core.email_drafts import DRAFT, SENT, EmailDrafts, addresses_in, as_text, mailto_url
from core.event_bus import EventBus
from core.mail_send import SendError, build_message, guess_server, send_draft, sender_for
from core.personal_data import PersonalData, view_for
from core.profile_manager import ProfileManager


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    sam = context.profiles.create_profile("Sam", make_active=False)
    shared = tmp_path / "shared"
    shared.mkdir()
    context.personal_data = PersonalData(context, profiles_dir=tmp_path / "profiles", shared_dir=shared)
    context.personal_data.watch(context.events)
    context.personal_data.activate_current()
    return context, zac, sam


class _FakeSMTP:
    def __init__(self, fail_login=False):
        self.logged_in, self.sent, self.fail_login = None, [], fail_login

    def login(self, user, password):
        if self.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad")
        self.logged_in = (user, password)

    def send_message(self, message):
        self.sent.append(message)

    def quit(self):
        pass


# ------------------------------------------------------------------ pure logic


def test_addresses_mailto_and_copy_text():
    assert addresses_in("to Pat <pat@Example.com>, and bo@x.org.") == ["pat@example.com", "bo@x.org"]
    assert addresses_in("my landlord") == []
    draft = SimpleNamespace(to=["pat@example.com"], cc=[], subject="Leaky faucet & sink", body="Hi Pat,\nThanks!")
    assert mailto_url(draft) == "mailto:pat@example.com?subject=Leaky%20faucet%20%26%20sink&body=Hi%20Pat%2C%0AThanks%21"
    assert as_text(draft) == "Subject: Leaky faucet & sink\n\nHi Pat,\nThanks!"
    assert guess_server("me@gmail.com") == ("smtp.gmail.com", 465, "ssl")
    assert guess_server("me@outlook.com")[0] == "smtp.office365.com" and guess_server("me@mydomain.net") is None
    message = build_message("me@gmail.com", ["pat@example.com"], "Hi", "Body", sender_name="Zac")
    assert message["From"] == "Zac <me@gmail.com>" and message["To"] == "pat@example.com"
    assert message.get_content().strip() == "Body"


# ------------------------------------------------------------------ the Assistant only drafts


def test_the_assistant_makes_a_draft_and_never_sends(home):
    context, zac, _ = home
    ready = []
    context.events.subscribe("email.draft_ready", lambda **kw: ready.append(kw))
    reply = _action_draft_email(context, {"to": "my landlord pat@example.com", "subject": "Leaky faucet",
                                          "body": "Hi Pat, the kitchen faucet is leaking. Thanks, Zac"})
    assert "won't send anything unless you press Send" in reply
    [draft] = context.email_drafts.open_drafts()
    assert draft.to == ["pat@example.com"] and draft.status == DRAFT
    assert ready == [{"draft_id": draft.draft_id, "profile_id": zac.profile_id, "on_phone": False}]
    assert "Add who it goes to" in _action_draft_email(context, {"subject": "Hi", "body": "Hello"})
    assert _action_draft_email(context, {"subject": "Hi"}) == "What should the email say?"


def test_drafts_are_each_persons_own(home):
    context, zac, sam = home
    sam_view = view_for(context, sam.profile_id)
    _action_draft_email(sam_view, {"subject": "Sam's", "body": "x"})
    assert context.email_drafts.open_drafts() == []  # Zac is signed in
    assert [d.subject for d in sam_view.email_drafts.open_drafts()] == ["Sam's"]


# ------------------------------------------------------------------ sending, only on Send


def test_sending_needs_setup_and_the_passphrase(home):
    context, zac, _ = home
    draft = context.email_drafts.create(["pat@example.com"], "Hi", "Hello Pat")
    with pytest.raises(SendError, match="isn't set up"):
        send_draft(context, zac.profile_id, draft.draft_id, connect=lambda *a: _FakeSMTP())
    sender = sender_for(context, zac.profile_id)
    sender.setup("zac@gmail.com", "app-password", "my passphrase")
    assert sender.configured and context.config.get(f"profiles.{zac.profile_id}")["settings"]["email.send.host"] == "smtp.gmail.com"
    vault = context.personal_data.folder(zac.profile_id) / "mail_send.enc"
    assert vault.exists() and b"app-password" not in vault.read_bytes()
    sender._password = None  # a new session: locked
    with pytest.raises(SendError, match="locked"):
        send_draft(context, zac.profile_id, draft.draft_id, connect=lambda *a: _FakeSMTP())
    assert not sender.unlock("wrong") and sender.unlock("my passphrase")
    server = _FakeSMTP()
    assert send_draft(context, zac.profile_id, draft.draft_id, connect=lambda *a: server) == "Sent to pat@example.com."
    assert server.logged_in == ("zac@gmail.com", "app-password") and server.sent[0]["Subject"] == "Hi"
    assert context.email_drafts.get(draft.draft_id).status == SENT
    with pytest.raises(SendError, match="already sent"):
        send_draft(context, zac.profile_id, draft.draft_id, connect=lambda *a: server)


def test_a_wrong_mail_password_keeps_the_draft(home):
    context, zac, _ = home
    draft = context.email_drafts.create(["pat@example.com"], "Hi", "Hello")
    sender_for(context, zac.profile_id).setup("zac@gmail.com", "nope", "pp")
    with pytest.raises(SendError, match="app password"):
        send_draft(context, zac.profile_id, draft.draft_id, connect=lambda *a: _FakeSMTP(fail_login=True))
    assert context.email_drafts.get(draft.draft_id).status == DRAFT
    bad_to = context.email_drafts.create(["not an address"], "Hi", "Hello")
    with pytest.raises(SendError, match="To address"):
        send_draft(context, zac.profile_id, bad_to.draft_id, connect=lambda *a: _FakeSMTP())


# ------------------------------------------------------------------ the phone


def test_the_phone_gets_the_draft_and_its_send_button(home, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app_module
    from tests.test_server_app import _FakeLLM

    context, zac, sam = home
    context.profiles.set_password(sam.profile_id, "pw")
    context.voice = context.push_subscriptions = None
    context.llm = _FakeLLM()
    client = TestClient(server_app_module.create_app(context))
    token = client.post("/api/login", json={"profile_id": "Sam", "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    sam_view = view_for(context, sam.profile_id)
    # A turn in which MIA wrote a draft (the model's tool call, simulated).
    import server.app as app_module

    real_turn = app_module.run_assistant_turn

    def drafting_turn(view, conversation, text):
        _action_draft_email(view, {"to": "pat@example.com", "subject": "Hi", "body": "Hello Pat"})
        return real_turn(view, conversation, text)

    monkeypatch.setattr(app_module, "run_assistant_turn", drafting_turn)
    reply = client.post("/api/voice/text", json={"text": "Email Pat hello"}).json()
    assert reply["draft"]["to"] == ["pat@example.com"] and reply["draft"]["mailto"].startswith("mailto:")
    draft_id = reply["draft"]["draft_id"]
    listing = client.get("/api/email/drafts").json()
    assert [d["draft_id"] for d in listing["drafts"]] == [draft_id] and listing["can_send"] is False
    assert client.post(f"/api/email/drafts/{draft_id}/send").status_code == 409  # not set up: Copy instead
    sender_for(context, sam.profile_id).setup("sam@gmail.com", "app-pw", "pp")
    sender_for(context, sam.profile_id)._password = None
    assert client.post(f"/api/email/drafts/{draft_id}/send").status_code == 423  # locked this session
    assert client.post(f"/api/email/drafts/{draft_id}/discard").json() == {"discarded": True}
    assert sam_view.email_drafts.open_drafts() == []
    # A turn without a draft carries none.
    monkeypatch.setattr(app_module, "run_assistant_turn", real_turn)
    assert client.post("/api/voice/text", json={"text": "What time is it?"}).json()["draft"] is None


# ------------------------------------------------------------------ the desktop window


def test_draft_window_copy_and_edit(home, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from gui.email_draft_dialog import EmailDraftDialog

    app = QApplication.instance() or QApplication([])
    context, zac, _ = home
    draft = context.email_drafts.create([], "Hi", "Hello")
    dialog = EmailDraftDialog(context, draft, zac.profile_id)
    assert not dialog.send_button.isEnabled()  # sending not set up: Copy and mail app still work
    dialog.to_edit.setText("pat@example.com")
    dialog.body_edit.setPlainText("Hello Pat")
    dialog._on_copy()
    assert app.clipboard().text() == "Subject: Hi\n\nHello Pat"
    assert context.email_drafts.get(draft.draft_id).to == ["pat@example.com"]
    dialog._on_discard()
    assert context.email_drafts.open_drafts() == []


# ------------------------------------------------------------------ addressing by name


def test_drafts_find_the_address_by_name(home, tmp_path, monkeypatch):
    import core.relationships_manager as rel_module
    from core.assistant_email_actions import resolve_recipients
    from core.household_manager import HouseholdManager
    from core.relationships_manager import RelationshipsManager

    context, zac, sam = home
    monkeypatch.setattr(rel_module, "_DATA_DIR", tmp_path / "rel")
    monkeypatch.setattr(rel_module, "_PEOPLE_FILE", tmp_path / "rel" / "people.json")
    monkeypatch.setattr(rel_module, "_PETS_FILE", tmp_path / "rel" / "pets.json")
    context.relationships = RelationshipsManager(context)
    context.relationships.add_person("Pat Lee", relationship="Landlord", email="Pat@Example.com")
    context.relationships.add_person("Grandma")
    assert resolve_recipients(context, "Pat Lee") == (["pat@example.com"], [])
    assert resolve_recipients(context, "my landlord Pat") == (["pat@example.com"], [])  # a unique first name
    assert resolve_recipients(context, "other@x.org") == (["other@x.org"], [])  # written addresses win
    assert resolve_recipients(context, "Grandma") == ([], ["Grandma"])
    reply = _action_draft_email(context, {"to": "Grandma", "subject": "Hi", "body": "Love you"})
    assert "I don't have an email address for Grandma" in reply
    # Household members are known by their sign-in email.
    context.households = HouseholdManager(context)
    context.profiles.set_email(sam.profile_id, "sam@example.com")
    hid = context.households.household_of(zac.profile_id)
    context.households._set_household(sam.profile_id, hid)
    assert resolve_recipients(context, "Sam") == (["sam@example.com"], [])


def test_people_keep_an_email(tmp_path, monkeypatch):
    import core.relationships_manager as rel_module
    from core.assistant_life_actions import _action_add_person, _action_get_person, _action_update_person
    from core.relationships_manager import RelationshipsManager

    monkeypatch.setattr(rel_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(rel_module, "_PEOPLE_FILE", tmp_path / "people.json")
    monkeypatch.setattr(rel_module, "_PETS_FILE", tmp_path / "pets.json")
    ctx = SimpleNamespace(events=EventBus())
    ctx.relationships = RelationshipsManager(ctx)
    _action_add_person(ctx, {"name": "Pat", "email": "pat@example.com"})
    assert "email bo@x.org" in _action_update_person(ctx, {"name": "Pat", "email": "it's bo@x.org"})
    assert "email bo@x.org" in _action_get_person(ctx, {"name": "Pat"})
    assert RelationshipsManager(ctx).all_people()[0].email == "bo@x.org"  # saved
