"""
tests.test_review_2026_11_22_lows
===================================

Fable's review of 2026-11-22, its low findings: a household device's key follows /api/live (its one route), a lost
device ends the account's other sign-ins too, seal_now seals sync's base copies, a restore clears what couldn't be
read and the note says what to do, and the glasses show their microphone while it's on.
"""
from pathlib import Path

from core import at_rest


def _server(tmp_path, monkeypatch):
    """The real server on a small world, with a password, a session and a household device's key."""
    from fastapi.testclient import TestClient

    import server.app as server_app
    from core.security_log import SecurityLog
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.voice = world.llm = world.push_subscriptions = None
    world.security_log = SecurityLog(tmp_path / "device")
    world.profiles.set_password(world.me.profile_id, "pw")
    client = TestClient(server_app.create_app(world))
    return world, client


def test_a_household_devices_key_follows_the_live_stream_and_a_made_up_one_doesnt(tmp_path, monkeypatch):
    """/api/live takes a linked device's key as its token (HOUSEHOLD_ROUTES); anything else is refused."""
    world, client = _server(tmp_path, monkeypatch)
    tv = client.post("/api/model/link", json={"profile_id": world.me.profile_id, "password": "pw",
                                              "household": True}).json()
    assert client.get("/api/live", params={"token": tv["key"], "once": True}).status_code == 200
    assert client.get("/api/live", params={"token": "not-a-key", "once": True}).status_code == 401
    assert client.get("/api/live", params={"once": True}).status_code == 401


def test_reporting_a_device_lost_ends_the_accounts_other_sign_ins_and_keeps_this_one(tmp_path, monkeypatch):
    """Its browser's sign-in can't be told from another's, so every other one ends; the one reporting stays."""
    world, client = _server(tmp_path, monkeypatch)
    client.post("/api/model/link", json={"profile_id": world.me.profile_id, "password": "pw"})
    login = lambda: client.post("/api/login", json={"profile_id": world.me.profile_id,  # noqa: E731
                                                    "password": "pw"}).json()["token"]
    mine, other = login(), login()
    me = {"Authorization": "Bearer " + mine}
    [row] = client.get("/api/security/log", headers=me).json()["linked_devices"]
    done = client.post("/api/security/devices/lost", json={"device": row["id"]}, headers=me).json()
    assert done["lost"] is True and done["ended"] >= 1
    assert client.get("/api/shell", headers={"Authorization": "Bearer " + other}).status_code == 401
    assert client.get("/api/shell", headers=me).status_code == 200


def test_seal_now_seals_syncs_base_copies_too(tmp_path):
    """A plain base copy in .sync/<scope>/ is sealed with the store beside it."""
    at_rest.use_key(bytes(range(32)))
    name = sorted(at_rest.SEALED)[0]
    (tmp_path / name).write_text("[]", encoding="utf-8")
    base = tmp_path / ".sync" / "home" / name
    base.parent.mkdir(parents=True)
    base.write_text("[]", encoding="utf-8")
    assert at_rest.seal_now([tmp_path]) == 2
    assert at_rest.is_sealed(base.read_text(encoding="utf-8")) and at_rest.open_text(base) == "[]"


def test_a_restore_clears_what_couldnt_be_read_and_the_note_says_what_to_do():
    """recovered() empties unreadable(); the note names the backup as the way back, not a log file."""
    from types import SimpleNamespace

    from core import data_recovery

    said = []
    notes = SimpleNamespace(notify=lambda **k: said.append(k["message"]))
    data_recovery.notify_data_corruption(SimpleNamespace(notifications=notes), "bills.json")
    assert "bills.json" in data_recovery.unreadable() and "backup" in said[0] and "mia.log" not in said[0]
    data_recovery.recovered()
    assert data_recovery.unreadable() == []


def test_the_glasses_show_the_microphone_while_it_records_and_pressing_it_stops():
    """glasses.js: micShown on start, off on stop and on cancel; the pill stops listening."""
    js = (Path(__file__).resolve().parent.parent / "web" / "glasses.js").read_text(encoding="utf-8")
    assert js.count("micShown(true)") == 1 and js.count("micShown(false)") >= 2
    assert "micPill.onclick = () => stopListening();" in js
