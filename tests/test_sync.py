"""
Two-way sync between the phone and the home computer (core/sync.py):
the merge rules, one full sync against a computer that answers like MIA
on the PC does, and the PC's own endpoints.
"""

import base64
import json

import pytest

from core import sync
from core.sync import _MISSING, digest, merge_file, merge_game, merge_json, merge_lines


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


def test_line_endings_dont_count_as_a_change():
    assert digest(b'[\r\n  {"id": "a"}\r\n]') == digest(b'[\n  {"id": "a"}\n]')
    assert digest(b"") != digest(None)


def test_never_syncs_device_only_files():
    assert sync.syncable("missions.json") and sync.syncable("life_events.jsonl")
    assert not sync.syncable("security_logins.json") and not sync.syncable("foods.tsv")
    assert not sync.syncable(".hidden.json")


# ------------------------------------------------------------------ one full sync, against a pretend PC


class PretendPC:
    """Answers the sync calls the way MIA on the computer does, from dicts."""

    def __init__(self):
        self.files = {"mine": {}, "home": {}}
        self.blobs = {"mine": {}, "home": {}}
        self.journal_key = ""
        self.game = {"total_xp": 0, "total_credits": 0, "prestige_tier": 0, "unlocked_reward_ids": []}

    def __call__(self, context, path, payload=None, timeout=6.0, method="", raw=False, body=None, headers=None,
                 save_to=None):
        import hashlib
        from urllib.parse import parse_qs, urlsplit

        sha = lambda d: hashlib.sha256(d).hexdigest()  # noqa: E731
        if path == "/api/sync/manifest":
            return {**{s: {n: [digest(d), 1.0] for n, d in f.items()} for s, f in self.files.items()}, "game": self.game,
                    "files": {s: {r: [sha(d), 1.0, len(d)] for r, d in b.items()} for s, b in self.blobs.items()},
                    "journal_key": self.journal_key}
        if path.startswith("/api/sync/blob?"):
            q = {k: v[0] for k, v in parse_qs(urlsplit(path).query, keep_blank_values=True).items()}
            here = self.blobs[q["scope"]]
            if method == "PUT":
                data = body.read()
                assert sha(data) == q["sha"]
                assert (sha(here[q["path"]]) if q["path"] in here else "") == q["expect"], "pushed over a newer file"
                here[q["path"]] = data
                return {"ok": True}
            if method == "DELETE":
                assert sha(here[q["path"]]) == q["expect"]
                del here[q["path"]]
                return {"ok": True}
            save_to.write_bytes(here[q["path"]])
            return save_to
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

    # Nothing changed: nothing moves, even when the PC saves Windows line endings.
    pc.files["home"] = {n: d.replace(b"\n", b"\r\n") for n, d in pc.files["home"].items()}
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

    # Photos and files: streamed, checked, never outside their folders.
    import hashlib

    monkeypatch.setattr(sync, "file_folders", lambda context, pid: {"home": {"recipe_photos": home / "recipe_photos"}})
    photo = b"JPEG" * 1000
    sha = hashlib.sha256(photo).hexdigest()
    put = lambda **q: client.put("/api/sync/blob", params={"scope": "home", "path": "recipe_photos/a.jpg", **q},  # noqa: E731
                                 content=photo)
    assert put(sha="0" * 64, expect="").status_code == 422
    assert put(sha=sha, expect="stale").status_code == 409
    assert put(sha=sha, expect="").status_code == 200 and (home / "recipe_photos" / "a.jpg").read_bytes() == photo
    assert client.get("/api/sync/blob", params={"scope": "home", "path": "recipe_photos/a.jpg"}).content == photo
    assert client.get("/api/sync/manifest").json()["files"]["home"]["recipe_photos/a.jpg"][0] == sha
    for bad in ("recipe_photos/../../config.json", "nowhere/a.jpg", "recipe_photos/.hidden"):
        assert client.get("/api/sync/blob", params={"scope": "home", "path": bad}).status_code == 400
    assert client.delete("/api/sync/blob", params={"scope": "home", "path": "recipe_photos/a.jpg",
                                                   "expect": "stale"}).status_code == 409
    assert client.delete("/api/sync/blob", params={"scope": "home", "path": "recipe_photos/a.jpg",
                                                   "expect": sha}).status_code == 200
    assert not (home / "recipe_photos" / "a.jpg").exists()


# ------------------------------------------------------------------ photos, conversations, the private journal


def test_photos_and_files_go_both_ways_and_deletes_follow(phone):
    pc = PretendPC()
    photo = phone.dirs["home"] / "recipe_photos" / "chili.jpg"
    photo.parent.mkdir()
    photo.write_bytes(b"JPEG-chili")
    pc.blobs["mine"]["my_files/Taxes/2025.pdf"] = b"%PDF-taxes"
    done = sync.sync_now(phone, call=pc)
    assert pc.blobs["home"]["recipe_photos/chili.jpg"] == b"JPEG-chili"
    assert (phone.dirs["mine"] / "my_files" / "Taxes" / "2025.pdf").read_bytes() == b"%PDF-taxes"
    assert done["pushed"] >= 1 and done["pulled"] >= 1

    photo.unlink()  # deleted on the phone: deleted on the PC
    del pc.blobs["mine"]["my_files/Taxes/2025.pdf"]  # deleted on the PC: deleted on the phone
    sync.sync_now(phone, call=pc)
    assert "recipe_photos/chili.jpg" not in pc.blobs["home"]
    assert not (phone.dirs["mine"] / "my_files" / "Taxes" / "2025.pdf").exists()


def test_a_file_changed_on_both_keeps_both(phone):
    pc = PretendPC()
    note = phone.dirs["mine"] / "my_files" / "list.txt"
    note.parent.mkdir()
    note.write_bytes(b"phone version")
    pc.blobs["mine"]["my_files/list.txt"] = b"computer version"
    sync.sync_now(phone, call=pc)
    assert note.read_bytes() == b"phone version"
    assert (note.parent / "list (2).txt").read_bytes() == b"computer version"
    sync.sync_now(phone, call=pc)
    assert pc.blobs["mine"] == {"my_files/list.txt": b"phone version", "my_files/list (2).txt": b"computer version"}
    again = sync.sync_now(phone, call=pc)
    assert (again["pushed"], again["pulled"], again["merged"]) == (0, 0, 0)


def test_conversation_messages_from_both_devices_merge_in_time_order():
    def convo(*messages):
        return json.dumps([{"conversation_id": "c1", "title": "Chat",
                            "messages": [{"role": r, "content": c, "timestamp": t} for r, c, t in messages]}]).encode()

    base = convo(("user", "hi", "2026-10-18T09:00:00"))
    phone = convo(("user", "hi", "2026-10-18T09:00:00"), ("user", "from the phone", "2026-10-18T09:05:00"))
    pc = convo(("user", "hi", "2026-10-18T09:00:00"), ("user", "at the desk", "2026-10-18T09:02:00"))
    merged = json.loads(merge_file("conversations.json", base, phone, pc, True))
    assert [m["content"] for m in merged[0]["messages"]] == ["hi", "at the desk", "from the phone"]


def test_journal_entries_merge_whole_never_field_by_field():
    def entries(*rows):
        return json.dumps({"version": 1, "entries": [{"entry_id": i, "updated_at": u, "key": k, "data": d}
                                                     for i, u, k, d in rows]}).encode()

    base = entries(("e1", "2026-10-01", "K1", "D1"))
    phone = entries(("e1", "2026-10-03", "K2", "D2"), ("e2", "2026-10-03", "K", "D"))
    pc = entries(("e1", "2026-10-02", "K3", "D3"), ("e3", "2026-10-02", "K", "D"))
    got = json.loads(merge_file("private_journal.json", base, phone, pc, False))["entries"]
    assert [(e["entry_id"], e["key"], e["data"]) for e in got] == [("e1", "K2", "D2"), ("e2", "K", "D"), ("e3", "K", "D")]


def test_two_different_private_journals_dont_sync(phone):
    pc = PretendPC()
    (phone.dirs["mine"] / "private_journal_keys.json").write_text(json.dumps({"public_key": "PHONE-KEY"}))
    (phone.dirs["mine"] / "private_journal.json").write_text(json.dumps({"version": 1, "entries": []}))
    pc.files["mine"]["private_journal_keys.json"] = json.dumps({"public_key": "PC-KEY"}).encode()
    pc.journal_key = sync.journal_key(None) or "something else"
    done = sync.sync_now(phone, call=pc)
    assert "private_journal.json" not in pc.files["mine"] and "isn't syncing" in done["note"]
    assert json.loads((phone.dirs["mine"] / "private_journal_keys.json").read_text())["public_key"] == "PHONE-KEY"


def test_the_same_private_journal_syncs(phone):
    pc = PretendPC()
    keys = json.dumps({"public_key": "SAME-KEY"})
    (phone.dirs["mine"] / "private_journal_keys.json").write_text(keys)
    (phone.dirs["mine"] / "private_journal.json").write_text(
        json.dumps({"version": 1, "entries": [{"entry_id": "e1", "updated_at": "1", "key": "k", "data": "d"}]}))
    pc.journal_key = sync.journal_key(phone.dirs["mine"])
    done = sync.sync_now(phone, call=pc)
    assert json.loads(pc.files["mine"]["private_journal.json"])["entries"][0]["entry_id"] == "e1" and not done["note"]
