"""
Phone conversations in the desktop's History, open screens refreshing
after changes made elsewhere (core/main_thread.py, ModuleBase.refresh,
MainWindow), and per-turn timings for the phone.
"""

import json
import threading
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import core.conversation_manager as conversation_module
import server.app as server_app_module
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.conversation_manager import ConversationManager
from core.event_bus import EventBus
from core.main_thread import publish
from modules.module_base import ModuleBase
from server.app import describe_timings, phone_title, turn_timings
from tests.test_server_app import _FakeLLM, _FakeVoice, context  # noqa: F401  (`context` is the fixture)


# ------------------------------------------------------------------ the main-thread hand-off


def test_publish_on_the_main_thread_is_direct():
    seen = []
    ctx = SimpleNamespace(events=EventBus(), main_thread_call=lambda fn: pytest.fail("not needed on the main thread"))
    ctx.events.subscribe("x", lambda **kw: seen.append(kw))
    publish(ctx, "x", a=1)
    assert seen == [{"a": 1}]


def test_publish_from_another_thread_is_handed_to_the_main_thread():
    seen, handed = [], []
    ctx = SimpleNamespace(events=EventBus(), main_thread_call=handed.append)
    ctx.events.subscribe("x", lambda **kw: seen.append(kw))
    worker = threading.Thread(target=publish, args=(ctx, "x"), kwargs={"a": 2})
    worker.start()
    worker.join()
    assert seen == [] and len(handed) == 1  # nothing touched the screen from the worker
    handed[0]()
    assert seen == [{"a": 2}]


def test_the_qt_invoker_runs_on_the_gui_thread():
    from PySide6.QtWidgets import QApplication

    from core.application import MainThreadInvoker

    app = QApplication.instance() or QApplication([])
    invoker = MainThreadInvoker()
    ran_on = []
    worker = threading.Thread(target=invoker.call, args=(lambda: ran_on.append(threading.current_thread()),))
    worker.start()
    worker.join()
    for _ in range(20):
        app.processEvents()
    assert ran_on == [threading.main_thread()]


def test_tools_that_change_things_announce_it():
    changed = []
    ctx = SimpleNamespace(events=EventBus())
    ctx.events.subscribe("records.changed", lambda **kw: changed.append(kw["action"]))
    registry = AssistantActionRegistry()
    for name in ("add_grocery_item", "list_grocery_list", "get_budget_summary"):
        registry.register(AssistantAction(name=name, domain="x", description="", parameters={},
                                          handler=lambda c, a: "ok"))
    for name in ("add_grocery_item", "list_grocery_list", "get_budget_summary"):
        registry.execute(ctx, name, {})
    assert changed == ["add_grocery_item"]


# ------------------------------------------------------------------ screens refreshing


class _Module(ModuleBase):
    module_id = "fake"

    def __init__(self, context):
        super().__init__(context)
        self.refreshed = 0

    def get_widget(self):
        return object()

    def _refresh(self):
        self.refreshed += 1


def test_module_refresh_defaults_to_its_own_refresh():
    module = _Module(None)
    module.refresh()
    assert module.refreshed == 1


def test_main_window_refreshes_the_open_screen_now_and_others_when_opened():
    from gui.main_window import MainWindow

    shown, hidden = _Module(None), _Module(None)
    shown_widget, hidden_widget = object(), object()
    window = SimpleNamespace(
        _module_widgets={"shown": shown_widget, "hidden": hidden_widget}, _stale_modules=set(),
        _stack=SimpleNamespace(currentWidget=lambda: shown_widget),
        module_manager=SimpleNamespace(get={"shown": shown, "hidden": hidden}.get),
    )
    window._refresh_module = lambda module_id: MainWindow._refresh_module(window, module_id)
    MainWindow._on_records_changed(window)
    assert (shown.refreshed, hidden.refreshed) == (1, 0) and window._stale_modules == {"hidden"}
    window._refresh_module("hidden")  # what open_module() does for a stale screen
    assert hidden.refreshed == 1 and window._stale_modules == set()


def test_a_failing_refresh_never_takes_the_window_down():
    from gui.main_window import MainWindow

    class Broken(_Module):
        def _refresh(self):
            raise RuntimeError("boom")

    window = SimpleNamespace(_stale_modules={"b"}, module_manager=SimpleNamespace(get=lambda _id: Broken(None)))
    MainWindow._refresh_module(window, "b")
    assert window._stale_modules == set()


# ------------------------------------------------------------------ phone conversations in History


@pytest.fixture
def phone(context, tmp_path, monkeypatch):  # noqa: F811  (context is the imported fixture)
    monkeypatch.setattr(conversation_module, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(conversation_module, "_CONVERSATIONS_FILE", tmp_path / "data" / "conversations.json")
    context.conversations = ConversationManager(context)
    context.voice = _FakeVoice()
    context.llm = _FakeLLM()
    handed = []
    context.main_thread_call = handed.append
    client = TestClient(server_app_module.create_app(context))
    token = client.post("/api/login", json={"profile_id": "Alice", "password": "hunter2"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    # Phone turns go to the signed-in person's own conversations (core/personal_data.py).
    alice = context.profiles.list_profiles()[0].profile_id
    own = context.personal_data.view(alice).conversations
    return SimpleNamespace(client=client, context=context, handed=handed, conversations=own, file=own._conversations_file)


def test_phone_turns_are_saved_for_the_desktop_history(phone):
    updates = []
    phone.context.events.subscribe("conversation.updated", lambda **kw: updates.append(kw["conversation_id"]))
    first = phone.client.post("/api/voice/text", json={"text": "What's on my schedule today?"}).json()
    phone.client.post("/api/voice/text", json={"text": "And tomorrow?"})
    [conversation] = phone.conversations.all_conversations()
    assert conversation.title == "\U0001F4F1 What's on my schedule today?"
    assert [m.role for m in conversation.messages] == ["user", "assistant", "user", "assistant"]
    saved = json.loads(phone.file.read_text())
    assert saved[0]["title"].startswith("\U0001F4F1") and len(saved[0]["messages"]) == 4
    # Screens heard about it on the GUI thread, not the server's.
    assert updates == [] and len(phone.handed) >= 2
    for fn in phone.handed:
        fn()
    assert updates and set(updates) == {conversation.conversation_id}
    assert set(first["timings"]) == {"thinking", "speaking"}


def test_a_new_phone_conversation_after_hours_of_quiet(phone):
    phone.client.post("/api/voice/text", json={"text": "Good morning"})
    [morning] = phone.conversations.all_conversations()
    morning.updated_at = (datetime.now() - timedelta(hours=7)).isoformat(timespec="seconds")
    phone.client.post("/api/voice/text", json={"text": "Heading home now"})
    assert len(phone.conversations.all_conversations()) == 2


def test_off_the_record_on_the_phone_stays_off_the_record(phone):
    phone.client.post("/api/voice/text", json={"text": "Off the record, work was rough"})
    [conversation] = phone.conversations.all_conversations()
    assert conversation.title == "Off the record"
    saved = json.loads(phone.file.read_text())
    assert all("rough" not in m["content"] for c in saved for m in c["messages"])


def test_voice_turns_report_hearing_time(phone):
    import tests.test_server_app as server_tests

    phone.context.voice.transcript = "What's on my schedule today?"
    res = phone.client.post("/api/voice/turn", content=server_tests._wav_bytes(),
                            headers={"Content-Type": "audio/wav"}).json()
    assert set(res["timings"]) == {"hearing", "thinking", "speaking"}


def test_timing_and_title_wording():
    assert turn_timings(1.23, 3.41, 0.84) == {"hearing": 1.2, "thinking": 3.4, "speaking": 0.8}
    assert describe_timings(turn_timings(None, 2.0, 0.5)) == "thought 2.0s · spoke 0.5s"
    assert phone_title("  what's   on my schedule  ") == "\U0001F4F1 what's on my schedule"
    assert phone_title("x" * 60).endswith("…") and len(phone_title("x" * 60)) == 43
