"""
Meeting MIA (core/first_boot.py): each person's own progress, resumable,
skippable, in their own name.
"""

from core import first_boot
from core.actions import ACTION_TYPES, ActionCenter
from tests.engine_world import build_world


def test_starts_at_the_beginning_in_their_name(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    now = first_boot.state(world)
    assert now["done"] is False and now["phase"] == "awakening"
    assert now["beats"][0]["look"] == "swarm"
    first = world.me.name.split()[0]
    assert any(b["say"] == f"Hello, {first}." for b in now["beats"])
    assert all(b["phase"] for b in now["beats"])


def test_no_name_no_comma(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    monkeypatch.setattr(first_boot, "_first_name", lambda context: "")
    assert any(b["say"] == "Hello." for b in first_boot.state(world)["beats"])


def test_picks_up_where_it_stopped(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    now = first_boot.advance(world, "awakening")
    assert now["phase"] == "connecting" and now["finished"] == ["awakening"]
    assert {b["phase"] for b in now["beats"]} == {"connecting", "introduction"}
    assert first_boot.advance(world, "awakening")["finished"] == ["awakening"]  # repeating changes nothing
    first_boot.advance(world, "connecting")
    done = first_boot.advance(world, "introduction")
    assert done["done"] is True and done["phase"] is None and done["beats"] == []


def test_skipping_is_remembered(tmp_path, monkeypatch):
    """Skipping the first start finishes it and remembers which steps were skipped."""
    world = build_world(tmp_path, monkeypatch)
    first_boot.advance(world, "awakening")
    now = first_boot.skip(world)
    assert now["done"] is True and now["skipped"] == ["connecting", "introduction"]


def test_one_event_when_finished(tmp_path, monkeypatch):
    from datetime import date

    from core.life_events import events_for

    world = build_world(tmp_path, monkeypatch)
    for phase in first_boot.PHASES:
        first_boot.advance(world, phase)
    first_boot.skip(world)  # already finished: nothing more
    today = date.today().isoformat()
    assert [e.type for e in events_for(world, today, today)].count("first_boot_finished") == 1


def test_kinds_and_a_bad_phase(tmp_path, monkeypatch):
    import pytest

    from core.actions import ActionError

    world = build_world(tmp_path, monkeypatch)
    assert ACTION_TYPES["firstboot.advance"].child_ok and ACTION_TYPES["firstboot.skip"].child_ok
    with pytest.raises(ActionError):
        first_boot.advance(world, "nonsense")


def test_through_the_server_as_the_screen_does(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world = build_world(tmp_path, monkeypatch)
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    world.actions = ActionCenter()
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    assert client.get("/api/first-boot").json()["phase"] == "awakening"
    made = client.post("/api/actions/propose", json={"kind": "firstboot.advance", "params": {"phase": "awakening"}}).json()
    assert client.post(f"/api/actions/{made['proposal_id']}/approve").json()["status"] == "executed"
    assert client.get("/api/first-boot").json()["phase"] == "connecting"  # picks up here, on any device
    made = client.post("/api/actions/propose", json={"kind": "firstboot.skip", "params": {}}).json()
    client.post(f"/api/actions/{made['proposal_id']}/approve")
    assert client.get("/api/first-boot").json()["done"] is True
    assert client.get("/api/state").json()["onboarding"]["skipped"] == ["connecting", "introduction"]
