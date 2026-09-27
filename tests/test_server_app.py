"""
tests.test_server_app
========================

Unit tests for server.app — exercised via FastAPI's TestClient, a real
in-process HTTP client that needs no running server, no real network,
and no HTTPS (see the Mobile Phase 1 plan's verification section for
why this is a legitimate, complete way to verify this code from a
sandbox with no real browser/phone). pywebpush.webpush is mocked in
the push-test cases, same as tests/test_web_push.py.

Builds a real AppContext via core.core_runtime.build_core_context(),
same fixture pattern as tests/test_core_runtime.py — proving
server.app.create_app() works against the actual object
core/application.py hands it, not a hand-rolled stand-in. Also wires
context.push_subscriptions directly (build_core_context() doesn't —
that's core/application.py's job, gated by server.enabled).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import core.alarm_manager as alarm_manager_module
import core.activity_log_manager as activity_log_manager_module
import core.calendar_manager as calendar_manager_module
import core.config_manager as config_manager_module
import core.expedition_manager as expedition_manager_module
import core.inventory_manager as inventory_manager_module
import core.journal_manager as journal_manager_module
import core.mission_manager as mission_manager_module
import core.notification_manager as notification_manager_module
import core.push_subscription_manager as push_subscription_manager_module
import core.trip_manager as trip_manager_module
import core.user_memory_manager as user_memory_manager_module
import core.waypoint_manager as waypoint_manager_module
import core.web_push as web_push_module
import server.app as server_app_module
from core.config_manager import ConfigManager
from core.core_runtime import build_core_context
from core.event_bus import EventBus
from core.push_subscription_manager import PushSubscriptionManager


@pytest.fixture
def context(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(notification_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(notification_manager_module, "_NOTIFICATIONS_FILE", data_dir / "notifications.json")
    monkeypatch.setattr(calendar_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(calendar_manager_module, "_EVENTS_FILE", data_dir / "calendar_events.json")
    monkeypatch.setattr(alarm_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(alarm_manager_module, "_ALARMS_FILE", data_dir / "alarms.json")
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", data_dir / "journal_entries.json")
    monkeypatch.setattr(inventory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(inventory_manager_module, "_ITEMS_FILE", data_dir / "inventory_items.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", data_dir / "expeditions.json")
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", data_dir / "trips.json")
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(user_memory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(user_memory_manager_module, "_USER_MEMORIES_FILE", data_dir / "user_memories.json")
    monkeypatch.setattr(activity_log_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(activity_log_manager_module, "_ACTIVITY_LOG_FILE", data_dir / "activity_log.json")
    monkeypatch.setattr(push_subscription_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(push_subscription_manager_module, "_SUBSCRIPTIONS_FILE", data_dir / "push_subscriptions.json")
    monkeypatch.setattr(web_push_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(web_push_module, "_VAPID_KEYS_FILE", data_dir / "vapid_keys.json")

    ctx = build_core_context(ConfigManager(), EventBus())
    ctx.push_subscriptions = PushSubscriptionManager(ctx)
    ctx.profiles.create_profile("Alice", password="hunter2")
    return ctx


@pytest.fixture
def client(context) -> TestClient:
    app = server_app_module.create_app(context)
    return TestClient(app)


def _profile_id(context) -> str:
    return context.profiles.list_profiles()[0].profile_id


# ----------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------

def test_login_succeeds_with_correct_password(client, context):
    res = client.post("/api/login", json={"profile_id": _profile_id(context), "password": "hunter2"})
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Alice"
    assert body["token"]


def test_login_succeeds_with_profile_name_case_insensitive(client, context):
    res = client.post("/api/login", json={"profile_id": "aLiCe", "password": "hunter2"})
    assert res.status_code == 200
    assert res.json()["name"] == "Alice"


def test_login_fails_with_wrong_password(client, context):
    res = client.post("/api/login", json={"profile_id": _profile_id(context), "password": "wrong"})
    assert res.status_code == 401


def test_login_fails_with_unknown_profile(client):
    res = client.post("/api/login", json={"profile_id": "nonexistent", "password": "x"})
    assert res.status_code == 401


# ----------------------------------------------------------------------
# VAPID public key
# ----------------------------------------------------------------------

def test_vapid_public_key_returns_a_real_key(client):
    res = client.get("/api/vapid-public-key")
    assert res.status_code == 200
    assert len(res.json()["public_key"]) > 0


# ----------------------------------------------------------------------
# Push subscribe
# ----------------------------------------------------------------------

def test_push_subscribe_requires_auth(client):
    res = client.post("/api/push/subscribe", json={"endpoint": "https://push.example/ep1", "keys": {"p256dh": "a", "auth": "b"}})
    assert res.status_code == 401


def _login(client, context, password="hunter2") -> str:
    res = client.post("/api/login", json={"profile_id": _profile_id(context), "password": password})
    return res.json()["token"]


def test_push_subscribe_persists_a_real_subscription(client, context):
    token = _login(client, context)
    res = client.post(
        "/api/push/subscribe",
        json={"endpoint": "https://push.example/ep1", "keys": {"p256dh": "p256dh-key", "auth": "auth-key"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    stored = context.push_subscriptions.subscriptions_for_profile(_profile_id(context))
    assert len(stored) == 1
    assert stored[0].endpoint == "https://push.example/ep1"
    assert stored[0].p256dh_key == "p256dh-key"


# ----------------------------------------------------------------------
# Push test-send
# ----------------------------------------------------------------------

def test_push_test_requires_auth(client):
    res = client.post("/api/push/test")
    assert res.status_code == 401


def test_push_test_404_with_no_subscriptions(client, context):
    token = _login(client, context)
    res = client.post("/api/push/test", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_push_test_sends_via_webpush_with_the_right_subscription(client, context, monkeypatch):
    token = _login(client, context)
    client.post(
        "/api/push/subscribe",
        json={"endpoint": "https://push.example/ep1", "keys": {"p256dh": "p256dh-key", "auth": "auth-key"}},
        headers={"Authorization": f"Bearer {token}"},
    )

    mock_webpush = MagicMock(return_value="ok")
    monkeypatch.setattr(web_push_module, "webpush", mock_webpush)

    res = client.post("/api/push/test", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    assert res.json() == {"sent": 1, "attempted": 1}
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["subscription_info"]["endpoint"] == "https://push.example/ep1"
    assert call_kwargs["subscription_info"]["keys"] == {"p256dh": "p256dh-key", "auth": "auth-key"}


# ----------------------------------------------------------------------
# Phone voice (2026-09-27) — fake STT/TTS/LLM, real turn logic
# ----------------------------------------------------------------------

import base64 as _base64
import io as _io
import wave as _wave
from pathlib import Path

from core.assistant_actions import AssistantAction
from core.assistant_chat import build_memory_extraction_prompt
from core.llm_manager import ChatReply, ToolCall
from server.app import LLM_UNAVAILABLE_REPLY, MAX_VOICE_UPLOAD_BYTES, NOT_HEARD_REPLY, validate_voice_wav


def _wav_bytes(channels=1, sampwidth=2, rate=16000, frames=1600) -> bytes:
    buf = _io.BytesIO()
    with _wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(b"\x00" * sampwidth * channels * frames)
    return buf.getvalue()


class _FakeVoice:
    def __init__(self, transcript="what's on my schedule"):
        self.transcript = transcript
        self.spoken = []

    def is_stt_available(self):
        return True

    def is_tts_available(self):
        return True

    def transcribe(self, wav_path):
        assert Path(wav_path).exists()
        return self.transcript

    def synthesize(self, text, output_path):
        self.spoken.append(text)
        Path(output_path).write_bytes(_wav_bytes(rate=22050, frames=100))
        return Path(output_path)


class _FakeLLM:
    def __init__(self, reply=None):
        self.reply = reply if reply is not None else ChatReply(content="You have a walkthrough at 10.")
        self.chat_calls = []
        self.generate_calls = []

    def is_available(self):
        return True

    def chat_with_tools(self, messages, tools):
        self.chat_calls.append(messages)
        return self.reply

    def generate(self, prompt):
        self.generate_calls.append(prompt)
        return ""


@pytest.fixture
def voice_client(context):
    context.voice = _FakeVoice()
    context.llm = _FakeLLM()
    app = server_app_module.create_app(context)
    client = TestClient(app)
    token = client.post("/api/login", json={"profile_id": "Alice", "password": "hunter2"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_login_refused_for_profile_without_password(context):
    context.profiles.create_profile("NoPass", make_active=False)
    client = TestClient(server_app_module.create_app(context))
    res = client.post("/api/login", json={"profile_id": "NoPass", "password": ""})
    assert res.status_code == 403
    assert "password" in res.json()["detail"].lower()


def test_validate_voice_wav_accepts_mono_16bit():
    validate_voice_wav(_wav_bytes())


@pytest.mark.parametrize("audio", [b"", b"garbage", b"not a wav", _wav_bytes(channels=2), _wav_bytes(sampwidth=1), _wav_bytes(frames=0)])
def test_validate_voice_wav_rejects_bad_audio(audio):
    with pytest.raises(ValueError):
        validate_voice_wav(audio)


def test_voice_endpoints_require_auth(context):
    client = TestClient(server_app_module.create_app(context))
    assert client.get("/api/voice/status").status_code == 401
    assert client.post("/api/voice/text", json={"text": "hi"}).status_code == 401
    assert client.post("/api/voice/turn", content=_wav_bytes()).status_code == 401


def test_voice_status_reports_availability(voice_client):
    assert voice_client.get("/api/voice/status").json() == {
        "speech_to_text": True, "text_to_speech": True, "assistant": True,
    }


def test_voice_turn_transcribes_answers_and_returns_speech(voice_client, context):
    res = voice_client.post("/api/voice/turn", content=_wav_bytes(), headers={"Content-Type": "audio/wav"})
    assert res.status_code == 200
    body = res.json()
    assert body["transcript"] == "what's on my schedule"
    assert body["reply_text"] == "You have a walkthrough at 10."
    validate_wav_reply = _base64.b64decode(body["audio_wav_base64"])
    with _wave.open(_io.BytesIO(validate_wav_reply), "rb") as wf:
        assert wf.getnframes() == 100
    assert context.voice.spoken == ["You have a walkthrough at 10."]


def test_voice_turn_keeps_conversation_history_between_turns(voice_client, context):
    voice_client.post("/api/voice/text", json={"text": "first question"})
    voice_client.post("/api/voice/text", json={"text": "second question"})
    second_call_contents = [m.get("content") for m in context.llm.chat_calls[1]]
    assert any("first question" in (c or "") for c in second_call_contents)


def test_voice_reset_starts_a_fresh_conversation(voice_client, context):
    voice_client.post("/api/voice/text", json={"text": "first question"})
    assert voice_client.post("/api/voice/reset").json() == {"reset": True}
    voice_client.post("/api/voice/text", json={"text": "second question"})
    second_call_contents = [m.get("content") for m in context.llm.chat_calls[1]]
    assert not any("first question" in (c or "") for c in second_call_contents)


def _memory_prompts(context, user_text):
    return [c for c in context.llm.generate_calls if c == build_memory_extraction_prompt(user_text)]


def test_voice_turn_runs_memory_extraction_after_a_plain_reply(voice_client, context):
    voice_client.post("/api/voice/text", json={"text": "my truck is a Ridgeline"})
    assert len(_memory_prompts(context, "my truck is a Ridgeline")) == 1


def test_voice_turn_executes_tool_calls_and_speaks_confirmation(voice_client, context):
    context.assistant_actions.register(AssistantAction(
        name="fake_add_note", description="Add a note.", parameters={"type": "object", "properties": {}},
        handler=lambda ctx, args: "Note saved.",
    ))
    context.llm.reply = ChatReply(content="", tool_calls=[ToolCall(name="fake_add_note", arguments={})])
    body = voice_client.post("/api/voice/text", json={"text": "note that the coop is framed"}).json()
    assert body["replies"] == ["Note saved."]
    assert _memory_prompts(context, "note that the coop is framed") == []  # none on tool turns, same as the voice loop


def test_voice_turn_when_model_is_down_says_so(voice_client, context):
    context.llm.reply = None
    body = voice_client.post("/api/voice/text", json={"text": "hello"}).json()
    assert body["reply_text"] == LLM_UNAVAILABLE_REPLY
    assert body["audio_wav_base64"]


def test_voice_turn_with_nothing_heard(voice_client, context):
    context.voice.transcript = "   "
    body = voice_client.post("/api/voice/turn", content=_wav_bytes()).json()
    assert body["transcript"] == ""
    assert body["reply_text"] == NOT_HEARD_REPLY
    assert context.llm.chat_calls == []


def test_voice_turn_503_when_speech_recognition_unavailable(voice_client, context):
    context.voice.transcript = None
    assert voice_client.post("/api/voice/turn", content=_wav_bytes()).status_code == 503


def test_voice_turn_rejects_bad_and_oversized_audio(voice_client):
    assert voice_client.post("/api/voice/turn", content=b"garbage").status_code == 400
    assert voice_client.post("/api/voice/turn", content=b"\x00" * (MAX_VOICE_UPLOAD_BYTES + 1)).status_code == 413


def test_voice_text_rejects_empty(voice_client):
    assert voice_client.post("/api/voice/text", json={"text": "   "}).status_code == 400
