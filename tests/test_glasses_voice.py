"""
Talking to MIA through the glasses (core/glasses_voice.py): "open Kitchen"
switches the glasses to that app, anything else is a Talk turn, and the
glasses hear about it through their feed. A phone linked to the home
computer sends the words there first.
"""

from datetime import datetime, timedelta

import pytest

import core.glasses_feed as gf
from core.glasses_voice import app_named, command, handle
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    w = build_world(tmp_path, monkeypatch)
    gf._voice.clear()
    return w


def test_open_an_app_by_name(world):
    assert command(world, "open kitchen") == {"open": "kitchen", "say": "Opening Kitchen."}
    assert command(world, "Hey MIA, show me my missions")["open"] == "missions"
    assert command(world, "go to the garage")["open"] == "garage"
    assert command(world, "open groceries")["open"] == "kitchen"  # another name for it
    assert command(world, "Go home.") == {"open": "", "say": "Here I am."}


def test_anything_else_is_talk(world):
    assert command(world, "log lunch") is None
    assert command(world, "open the moon") is None
    assert command(world, "show me how to fix a faucet") is None
    assert app_named(world, "the Kitchen app") == ("kitchen", "Kitchen")


def test_the_glasses_hear_about_it(world):
    me = world.me.profile_id
    since = (datetime.now() - timedelta(seconds=5)).isoformat(timespec="seconds")
    talked = []
    out = handle(world, me, "log lunch", lambda words: talked.append(words) or {"reply_text": "Lunch logged."})
    assert out == {"heard": "log lunch", "say": "Lunch logged."} and talked == ["log lunch"]
    handle(world, me, "open kitchen", lambda words: pytest.fail("not a Talk turn"))
    cards = gf.feed(world, since, now=datetime.now() + timedelta(seconds=1))["items"]
    voice = [c for c in cards if c["level"] == "voice"]
    assert [c["text"] for c in voice] == ["Lunch logged.", "Opening Kitchen."]
    assert "open" not in voice[0] and voice[1]["open"] == "kitchen" and voice[0]["heard"] == "log lunch"
    world.profiles.set_active_profile(world.other.profile_id)  # someone else's glasses don't see it
    assert not [c for c in gf.feed(world, since, now=datetime.now() + timedelta(seconds=1))["items"]
                if c["level"] == "voice"]


def test_the_endpoint_and_the_home_computer(world, monkeypatch):
    from fastapi.testclient import TestClient

    import core.home_link as home_link
    import server.app as server_app
    from core.home_link import HomeLinkError

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    got = client.post("/api/glasses/voice", json={"text": "open the garage"}).json()
    assert got["open"] == "garage" and got["where"] == "here"
    assert client.post("/api/glasses/voice", json={"text": " "}).status_code == 400

    # Linked to the home computer: the words go there (the glasses' screen is served from it).
    world.config.set("home_pc.url", "http://100.64.0.9:8765")
    world.config.set("home_pc.token", "device-key")
    calls = []
    monkeypatch.setattr(home_link, "home_call", lambda context, path, payload=None, **kw:
                        calls.append((path, payload)) or {"heard": payload["text"], "say": "Lunch logged."})
    got = client.post("/api/glasses/voice", json={"text": "log lunch"}).json()
    assert got == {"heard": "log lunch", "say": "Lunch logged.", "where": "home_pc"}
    assert calls == [("/api/glasses/voice", {"text": "log lunch"})]

    def away(*a, **kw):
        raise HomeLinkError("Can't reach the home computer right now.")

    monkeypatch.setattr(home_link, "home_call", away)
    got = client.post("/api/glasses/voice", json={"text": "open kitchen"}).json()
    assert got["where"] == "here" and got["open"] == "kitchen"  # the phone answers itself
