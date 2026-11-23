"""
tests.test_device_records
===========================

WP-10 (DEC-0242, REQ-DST-005/006/029, Q-90): each linked device has a record (what it is in words, its kind, its
key's scope, when it linked and last reached the computer, stale after 90 days); a household device's key is refused
outside household routes; a device reported lost is refused at once and, when it next reaches the computer, told to
erase, which it does, its key folder with it.
"""
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import linked_devices as ld


class _Config:
    """A config that keeps what it's given."""

    def __init__(self, **values):
        """Starts with these values."""
        self.values = dict(values)

    def get(self, key, default=None):
        """A value, or the default."""
        return self.values.get(key, default)

    def set(self, key, value):
        """Keeps a value."""
        self.values[key] = value

    def save(self):
        """Nothing to write."""


def _linked(config, key, profile_id="p1", **kw):
    """Links a device with this key."""
    devices = dict(config.get(ld.KEY, {}) or {})
    devices[ld.key_hash(key)] = ld.record(profile_id, **kw)
    config.set(ld.KEY, devices)


def test_a_device_record_says_what_it_is_and_when_it_was_last_seen_and_marks_it_stale():
    """REQ-DST-005: listed with its name, kind, scope, link and last contact; stale after STALE_DAYS unseen."""
    config = _Config()
    _linked(config, "k1", name="Android phone")
    devices = config.get(ld.KEY)
    devices[ld.key_hash("k1")]["last_seen"] = "2026-07-01"
    [row] = ld.listed(config, "p1", today=date(2026, 11, 22))
    assert (row["name"], row["kind"], row["scope"], row["stale"]) == ("Android phone", "phone", "person", True)
    assert ld.for_key(config, "k1", today=date(2026, 11, 22)) == "p1"
    assert not ld.listed(config, "p1", today=date(2026, 11, 23))[0]["stale"]  # seen yesterday: not stale


def test_a_household_key_reaches_household_routes_only():
    """REQ-DST-029: a key is refused for anything outside its scope; a person's reaches what they can."""
    assert ld.allows(ld.HOUSEHOLD, "/api/live") and not ld.allows(ld.HOUSEHOLD, "/api/state")
    assert not ld.allows(ld.HOUSEHOLD, "/api/passwords") and not ld.allows(ld.HOUSEHOLD, "/api/liveX")
    assert ld.allows(ld.PERSON, "/api/state") and not ld.allows("", "/api/state")
    config = _Config()
    _linked(config, "tv", scope=ld.HOUSEHOLD, kind="household display")
    assert ld.scope_of(config, "tv") == ld.HOUSEHOLD and ld.scope_of(config, "nothing") == ""


def test_a_device_reported_lost_is_refused_at_once_and_told_once():
    """Its record leaves the linked ones; its key is a lost one; the first ask is noted as told."""
    config = _Config()
    _linked(config, "k1", name="Android phone")
    device_id = ld.key_hash("k1")[:ld.DEVICE_ID_CHARS]
    assert not ld.mark_lost(config, "someone-else", device_id)
    assert ld.mark_lost(config, "p1", device_id)
    assert ld.for_key(config, "k1") is None
    assert ld.lost(config, "k1") == {"profile_id": "p1", "first": True}
    assert ld.lost(config, "k1") == {"profile_id": "p1", "first": False} and ld.lost(config, "other") is None
    [row] = ld.listed(config, "p1")
    assert row["lost"] and row["told"] and row["name"] == "Android phone"


def test_the_device_erases_mias_data_when_told_and_only_then(tmp_path, monkeypatch):
    """A 410 with X-MIA-Erase proved with this device's own key erases its data folder (key folder too) and forgets
    the link; any other refusal, or an order that can't prove it knows the key, erases nothing."""
    import urllib.error
    import urllib.request

    from core import home_link

    data = tmp_path / "data"
    (data / ".keys").mkdir(parents=True)
    (data / ".keys" / "data_key.json").write_text("{}", encoding="utf-8")
    (data / "conversations.json").write_text("[]", encoding="utf-8")
    from core import data_root

    monkeypatch.setattr(data_root, "DATA_DIR", data)
    config = _Config(**{"home_pc.url": "http://pc:8765", "home_pc.token": "k1", "home_pc.who": "zac"})
    context = SimpleNamespace(config=config)

    monkeypatch.setattr(home_link, "EXIT_AFTER_ERASE", False)

    def answer(code, erase, proof=True):
        """The computer answers with this code, and the erase order (proved with this device's key, or forged)."""
        def opener(request, timeout=None):
            """Raises the computer's answer."""
            nonce = request.get_header("X-mia-erase-nonce") or ""
            headers = {"X-MIA-Erase": "1", "X-MIA-Erase-Proof": home_link.erase_proof("k1" if proof else "x", nonce)} \
                if erase else {}
            raise urllib.error.HTTPError(request.full_url, code, "no", headers, None)
        return opener

    monkeypatch.setattr(urllib.request, "urlopen", answer(403, False))
    with pytest.raises(home_link.HomeLinkError):
        home_link.home_call(context, "/api/state")
    assert (data / "conversations.json").exists()
    monkeypatch.setattr(urllib.request, "urlopen", answer(410, True, proof=False))  # anything else at the address
    with pytest.raises(home_link.HomeLinkError):
        home_link.home_call(context, "/api/state")
    assert (data / "conversations.json").exists()  # a forged order erases nothing
    monkeypatch.setattr(urllib.request, "urlopen", answer(410, True))
    with pytest.raises(home_link.HomeLinkError, match="reported lost"):
        home_link.home_call(context, "/api/state")
    assert list(data.iterdir()) == [] and config.get("home_pc.token") == ""


def test_the_server_refuses_a_lost_key_with_erase_and_a_household_key_outside_its_routes(tmp_path, monkeypatch):
    """Through the real server: a lost device is answered 410 with X-MIA-Erase and logged once (the report says it
    ended the account's other sign-ins); a household device's key is refused for a person's records."""
    from fastapi.testclient import TestClient

    import server.app as server_app
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.voice = world.llm = world.push_subscriptions = None
    from core.security_log import SecurityLog

    world.security_log = SecurityLog(tmp_path / "device")
    world.profiles.set_password(world.me.profile_id, "pw")
    client = TestClient(server_app.create_app(world))
    linked = client.post("/api/model/link", json={"profile_id": world.me.profile_id, "password": "pw"}).json()
    phone = {"Authorization": "Bearer " + linked["key"]}
    assert client.get("/api/shell", headers=phone).status_code == 200
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    me = {"Authorization": "Bearer " + token}
    [row] = client.get("/api/security/log", headers=me).json()["linked_devices"]
    assert row["kind"] == "phone" and row["scope"] == "person" and "·" not in row["name"]
    assert client.post("/api/security/devices/lost", json={"device": row["id"]}, headers=me).json()["lost"] is True
    gone = client.get("/api/shell", headers=phone)
    assert gone.status_code == 410 and gone.headers.get("X-MIA-Erase") == "1"
    client.get("/api/shell", headers=phone)
    kinds = [e["kind"] for e in client.get("/api/security/log", headers=me).json()["events"]]
    assert kinds.count("device_erased") == 1 and "device_lost" in kinds
    tv = client.post("/api/model/link", json={"profile_id": world.me.profile_id, "password": "pw",
                                              "household": True}).json()
    assert client.get("/api/shell", headers={"Authorization": "Bearer " + tv["key"]}).status_code == 403
