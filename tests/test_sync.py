"""
Two-way sync between the phone and the home computer (core/sync.py):
the merge rules, one full sync against a computer that answers like MIA
on the PC does, and the PC's own endpoints.
"""

import base64
import json

import pytest

from core import sync
from core.sync import _MISSING, digest, merge_game, merge_json, merge_lines


# ------------------------------------------------------------------ the merge rules


def test_records_added_on_both_sides_both_stay():
    base = [{"mission_id": "a", "name": "Fence"}]
    local = base + [{"mission_id": "b", "name": "Gutters"}]
    remote = base + [{"mission_id": "c", "name": "Garden"}]
    assert [m["mission_id"] for m in merge_json(base, local, remote, True)] == ["a", "b", "c"]


def test_the_same_record_keeps_each_sides_changed_fields():
    base = [{"id": "a", "name": "Fence", "status": "active", "notes": ""}]
    local = [{"id": "a", "name": "Fence", "status": "completed", "notes": ""}]
    remote = [{"id": "a", "name": "Fence", "status": "active", "notes": "use cedar"}]
    assert merge_json(base, local, remote, False) == [{"id": "a", "name": "Fence", "status": "completed",
                                                       "notes": "use cedar"}]


def test_both_changed_the_same_field_the_newer_wins():
    base, local, remote = {"x": 1}, {"x": 2}, {"x": 3}
    assert merge_json(base, local, remote, True) == {"x": 2}
    assert merge_json(base, local, remote, False) == {"x": 3}


def test_deleted_on_one_side_untouched_on_the_other_stays_deleted():
    base = [{"id": "a"}, {"id": "b"}]
    assert merge_json(base, [{"id": "a"}], base, True) == [{"id": "a"}]
    assert merge_json({"k": 1, "j": 2}, {"k": 1}, {"k": 1, "j": 2}, False) == {"k": 1}


def test_logs_without_ids_keep_both_additions():
    base = [{"t": 1}]
    assert merge_json(base, base + [{"t": 2}], base + [{"t": 3}], True) == [{"t": 1}, {"t": 2}, {"t": 3}]


def test_first_sync_with_no_base_unions_records():
    local, remote = [{"id": "a", "v": 1}], [{"id": "b", "v": 2}]
    assert merge_json(_MISSING, local, remote, True) == [{"id": "a", "v": 1}, {"id": "b", "v": 2}]


def test_history_lines_merge_by_event_id_oldest_first():
    a = json.dumps({"event_id": "1", "at": "2026-10-01T10:00:00"})
    b = json.dumps({"event_id": "2", "at": "2026-10-02T10:00:00"})
    c = json.dumps({"event_id": "3", "at": "2026-10-01T12:00:00"})
    merged = merge_lines(a + "\n", a + "\n" + b + "\n", a + "\n" + c + "\n")
    assert [json.loads(line)["event_id"] for line in merged.splitlines()] == ["1", "3", "2"]


def test_xp_and_credits_add_up_what_each_side_earned():
    base = {"total_xp": 100, "total_credits": 10}
    got = merge_game(base, {"total_xp": 150, "total_credits": 10, "prestige_tier": 0, "unlocked_reward_ids": ["r1"]},
                     {"total_xp": 130, "total_credits": 25, "prestige_tier": 1, "unlocked_reward_ids": ["r2"]})
    assert got == {"total_xp": 180, "total_credits": 25, "prestige_tier": 1, "unlocked_reward_ids": ["r1", "r2"]}


def test_never_syncs_device_only_files():
    assert sync.syncable("missions.json") and sync.syncable("life_events.jsonl")
    assert not sync.syncable("security_logins.json") and not sync.syncable("foods.tsv")
    assert not sync.syncable(".hidden.json")


# ------------------------------------------------------------------ one full sync, against a pretend PC


class PretendPC:
    """Answers the sync calls the way MIA on the computer does, from dicts."""

    def __init__(self):
        self.files = {"mine": {}, "home": {}}
        self.game = {"total_xp": 0, "total_credits": 0, "prestige_tier": 0, "unlocked_reward_ids": []}

    def __call__(self, context, path, payload=None, timeout=6.0, method="", raw=False):
        if path == "/api/sync/manifest":
            return {**{s: {n: [digest(d), 1.0] for n, d in f.items()} for s, f in self.files.items()}, "game": self.game}
        if path.startswith("/api/sync/file?"):
            q = dict(part.split("=") for part in path.split("?")[1].split("&"))
            return self.files[q["scope"]][q["name"]]
        if path == "/api/sync/file":
            current = self.files[payload["scope"]].get(payload["name"])
            assert digest(current) == payload["expect"], "the phone pushed over a newer file"
            self.files[payload["scope"]][payload["name"]] = base64.b64decode(payload["data"])
            return {"ok": True}
        if path == "/api/sync/game":
            self.game = dict(payload)
            return {"ok": True}
        raise AssertionError(path)


@pytest.fixture
def phone(tmp_path, monkeypatch):
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    dirs = {"mine": tmp_path / "phone-mine", "home": tmp_path / "phone-home"}
    for d in dirs.values():
        d.mkdir()
    monkeypatch.setattr(sync, "folders", lambda context, pid: dirs)
    monkeypatch.setattr(sync, "state_for", lambda context: sync.SyncState(tmp_path / "phone-sync"))
    world.dirs = dirs
    return world


def _missions(*ids):
    return json.dumps([{"mission_id": i, "name": i} for i in ids]).encode()


def test_a_full_sync_both_ways(phone):
    pc = PretendPC()
    pc.files["home"]["missions.json"] = _missions("pc1")
    pc.files["mine"]["journal_entries.json"] = b"[]"
    (phone.dirs["home"] / "kitchen_recipes.json").write_bytes(b'[{"recipe_id": "r1"}]')
    (phone.dirs["home"] / "security_logins.json").write_text("{}")
    done = sync.sync_now(phone, call=pc)
    assert done["pulled"] == 2 and done["pushed"] == 1
    assert (phone.dirs["home"] / "missions.json").read_bytes() == _missions("pc1")
    assert "kitchen_recipes.json" in pc.files["home"] and "security_logins.json" not in pc.files["home"]

    # Both add a mission: both end up with both.
    (phone.dirs["home"] / "missions.json").write_bytes(_missions("pc1", "phone2"))
    pc.files["home"]["missions.json"] = _missions("pc1", "pc3")
    done = sync.sync_now(phone, call=pc)
    assert done["merged"] == 1
    ids = [m["mission_id"] for m in json.loads((phone.dirs["home"] / "missions.json").read_text())]
    assert ids == ["pc1", "phone2", "pc3"]
    assert json.loads(pc.files["home"]["missions.json"]) == json.loads((phone.dirs["home"] / "missions.json").read_text())

    # Nothing changed: nothing moves.
    again = sync.sync_now(phone, call=pc)
    assert (again["pushed"], again["pulled"], again["merged"]) == (0, 0, 0)


def test_xp_earned_on_both_adds_up(phone):
    pc = PretendPC()
    pid = phone.me.profile_id
    phone.profiles.add_xp(pid, 100)
    sync.sync_now(phone, call=pc)
    assert pc.game["total_xp"] == 100
    phone.profiles.add_xp(pid, 30)
    pc.game["total_xp"] += 50
    sync.sync_now(phone, call=pc)
    assert phone.profiles.get_profile(pid).total_xp == 180 and pc.game["total_xp"] == 180


# ------------------------------------------------------------------ the PC's endpoints


def test_the_pcs_endpoints(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    home = tmp_path / "pc-home"
    home.mkdir()
    (home / "missions.json").write_bytes(_missions("a"))
    monkeypatch.setattr(sync, "folders", lambda context, pid: {"home": home})
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    man = client.get("/api/sync/manifest").json()
    assert list(man["home"]) == ["missions.json"] and "total_xp" in man["game"]
    assert client.get("/api/sync/file", params={"scope": "home", "name": "missions.json"}).content == _missions("a")
    assert client.get("/api/sync/file", params={"scope": "home", "name": "../config.json"}).status_code == 400
    new = base64.b64encode(_missions("a", "b")).decode()
    stale = client.post("/api/sync/file", json={"scope": "home", "name": "missions.json", "expect": "old", "data": new})
    assert stale.status_code == 409
    ok = client.post("/api/sync/file", json={"scope": "home", "name": "missions.json",
                                              "expect": digest(_missions("a")), "data": new})
    assert ok.status_code == 200 and (home / "missions.json").read_bytes() == _missions("a", "b")
    assert client.post("/api/sync/file", json={"scope": "home", "name": "security_logins.json", "expect": "",
                                                "data": new}).status_code == 400
    assert client.get("/api/sync/status").json()["linked"] is False
