"""
The memory vault (core/memory_vault.py): the phone's camera roll read by
fingerprint, sent to the home computer in pieces that resume, checked
there, and only ever offered for removal once the computer confirms it
holds each file.
"""

import hashlib
import json
import os
import struct
from datetime import date

import pytest

import core.memory_vault as mv
from core.home_link import HomeLinkError
from core.memory_vault import (MemoryVault, VaultShelf, best_of, bursts, copies_offer, date_from_name, exif_info,
                               exif_thumbnail, free_offer, free_plan, note_freed, scan, send, vault_page)


# ------------------------------------------------------------------ a photo the way a phone writes it


def _jpeg(taken="2026:10:18 10:15:30", lat=(44, 30, 0), lon=(110, 30, 0), thumb=b"\xff\xd8THUMB\xff\xd9", pixels=b""):
    """A JPEG with an EXIF block: when it was taken, where, and a small preview."""
    entries = lambda items: struct.pack("<H", len(items)) + b"".join(  # noqa: E731
        struct.pack("<HHII", tag, kind, n, value) for tag, kind, n, value in items)
    # Layout: header(8) IFD0 | ExifIFD | GPS IFD | IFD1 | data
    ifd0_at = 8
    ifd0_len = 2 + 12 * 2 + 4
    exif_at = ifd0_at + ifd0_len
    exif_len = 2 + 12 + 4
    gps_at = exif_at + exif_len
    gps_len = 2 + 12 * 4 + 4
    ifd1_at = gps_at + gps_len
    ifd1_len = 2 + 12 * 2 + 4
    data_at = ifd1_at + ifd1_len
    date_bytes = taken.encode() + b"\x00"
    rationals = lambda dms: b"".join(struct.pack("<II", v, 1) for v in dms)  # noqa: E731
    lat_at = data_at + len(date_bytes)
    lon_at = lat_at + 24
    thumb_at = lon_at + 24
    tiff = b"II*\x00" + struct.pack("<I", ifd0_at)
    tiff += entries([(0x8769, 4, 1, exif_at), (0x8825, 4, 1, gps_at)]) + struct.pack("<I", ifd1_at)
    tiff += entries([(0x9003, 2, len(date_bytes), data_at)]) + struct.pack("<I", 0)
    tiff += entries([(1, 2, 2, ord("N")), (2, 5, 3, lat_at), (3, 2, 2, ord("W")), (4, 5, 3, lon_at)]) + struct.pack("<I", 0)
    tiff += entries([(0x0201, 4, 1, thumb_at), (0x0202, 4, 1, len(thumb))]) + struct.pack("<I", 0)
    tiff += date_bytes + rationals(lat) + rationals(lon) + thumb
    app1 = b"Exif\x00\x00" + tiff
    return b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xda" + pixels + b"\xff\xd9"


def test_a_photo_says_when_and_where_it_was_taken_and_carries_a_preview():
    photo = _jpeg()
    assert exif_info(photo) == {"taken_at": "2026-10-18T10:15:30", "lat": 44.5, "lon": -110.5}
    assert exif_thumbnail(photo) == b"\xff\xd8THUMB\xff\xd9"
    assert exif_info(b"not a jpeg") == {} and exif_thumbnail(b"PNG") is None


def test_dates_from_camera_file_names():
    assert date_from_name("IMG_20261018_101530.jpg") == "2026-10-18T10:15:30"
    assert date_from_name("PXL_20261018_101530123.MP.jpg") == "2026-10-18T10:15:30"
    assert date_from_name("Screenshot_2026-10-18-10-15-30.png") == "2026-10-18T10:15:30"
    assert date_from_name("holiday.jpg") == ""


def test_bursts_and_the_suggested_best_shot():
    shots = [{"sha": c, "kind": "photo", "taken_at": f"2026-10-18T10:15:3{i}", "size": s}
             for i, (c, s) in enumerate([("a", 10), ("b", 30), ("c", 20)])]
    lone = {"sha": "d", "kind": "photo", "taken_at": "2026-10-18T11:00:00", "size": 5}
    groups = bursts(shots + [lone])
    assert [[i["sha"] for i in g] for g in groups] == [["a", "b", "c"]]
    assert best_of(groups[0])["sha"] == "b"  # the most detail, until the PC has looked
    for i, score in zip(shots, (0.9, 0.2, 0.5)):
        i["score"] = score
    assert best_of(groups[0])["sha"] == "a"  # the sharpest, once it has


# ------------------------------------------------------------------ the phone reading its camera roll


@pytest.fixture
def phone(tmp_path, monkeypatch):
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    roll = tmp_path / "DCIM" / "Camera"
    roll.mkdir(parents=True)
    world.config.set("vault.sources", [str(tmp_path / "DCIM")])
    world.memory_vault = MemoryVault(world, data_dir=world.my_dir)
    world.roll = roll
    return world


def _shoot(roll, name, data):
    (roll / name).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_the_camera_roll_by_fingerprint(phone, tmp_path):
    a = _shoot(phone.roll, "IMG_20260901_090000.jpg", _jpeg("2026:09:01 09:00:00", pixels=b"A" * 500))
    (phone.roll.parent / "Copies").mkdir()
    _shoot(phone.roll.parent / "Copies", "same.jpg", _jpeg("2026:09:01 09:00:00", pixels=b"A" * 500))
    _shoot(phone.roll, "VID_20261001_120000.mp4", b"MOVIE" * 100)
    (phone.roll / ".thumbnails").mkdir()
    _shoot(phone.roll / ".thumbnails", "x.jpg", b"skip me")
    _shoot(phone.roll, "notes.txt", b"not a photo")
    found = scan(phone, phone.memory_vault)
    vault = phone.memory_vault
    assert found["complete"] and len(vault.items) == 2  # the copy is the same memory
    assert len(vault.items[a]["sources"]) == 2 and vault.items[a]["lat"] == 44.5
    assert {i["kind"] for i in vault.items.values()} == {"photo", "video"}
    assert copies_offer(vault)["count"] == 1
    assert scan(phone, vault)["new"] == 0  # nothing changed: nothing read again
    os.remove(phone.roll.parent / "Copies" / "same.jpg")
    scan(phone, vault)
    assert len(vault.items[a]["sources"]) == 1


def test_a_big_camera_roll_is_read_a_little_at_a_time(phone):
    for k in range(4):
        _shoot(phone.roll, f"IMG_2026090{k + 1}_090000.jpg", bytes([k]) * 1000)
    first = scan(phone, phone.memory_vault, budget=2500)
    assert not first["complete"] and len(phone.memory_vault.items) == 2
    scan(phone, phone.memory_vault, budget=2500)
    assert len(phone.memory_vault.items) == 4


# ------------------------------------------------------------------ to the computer, in pieces


class PretendPC:
    """The home computer's vault endpoints, answered by a real VaultShelf."""

    def __init__(self, folder, cut_after=None):
        self.shelf = VaultShelf(folder)
        self.cut_after, self.pieces = cut_after, 0

    def __call__(self, context, path, payload=None, timeout=6.0, method="", raw=False, body=None, headers=None):
        from urllib.parse import parse_qs, urlsplit

        if path == "/api/vault/have":
            return {"have": self.shelf.have(payload["shas"])}
        if path == "/api/vault/verify":
            return {"ok": self.shelf.verify(payload["shas"])}
        if path == "/api/vault/scores":
            return {"scores": self.shelf.scores(payload["shas"])}
        if path.startswith("/api/vault/blob/") and method == "PUT":
            self.pieces += 1
            if self.cut_after is not None and self.pieces > self.cut_after:
                raise HomeLinkError("Can't reach the home computer right now.")
            url = urlsplit(path)
            q = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
            return self.shelf.receive(url.path.rsplit("/", 1)[1], int(q["offset"]), body, int(q["size"]),
                                      q.get("name", ""), q.get("taken_at", ""), q.get("kind", ""))
        raise AssertionError(path)


def test_photos_go_to_the_computer_and_a_cut_picks_up_where_it_stopped(phone, tmp_path, monkeypatch):
    monkeypatch.setattr(mv, "CHUNK_BYTES", 1000)
    big = _shoot(phone.roll, "IMG_20260901_090000.jpg", _jpeg("2026:09:01 09:00:00", pixels=b"P" * 3500))
    small = _shoot(phone.roll, "IMG_20260902_090000.jpg", _jpeg("2026:09:02 09:00:00", pixels=b"Q" * 10))
    scan(phone, phone.memory_vault)
    pc = PretendPC(tmp_path / "pc-vault", cut_after=2)
    with pytest.raises(HomeLinkError):
        send(phone, phone.memory_vault, call=pc)
    assert pc.shelf.have([big])[big] == {"stored": False, "partial": 2000}
    pc.cut_after = None
    done = send(phone, phone.memory_vault, call=pc)
    assert done["sent"] == 2 and all(i["on_pc"] for i in phone.memory_vault.items.values())
    stored = pc.shelf.path_of(big)
    assert stored.read_bytes() == (phone.roll / "IMG_20260901_090000.jpg").read_bytes()
    assert stored.relative_to(tmp_path / "pc-vault").parts[:2] == ("2026", "09")
    assert pc.shelf.verify([big, small]) == {big: True, small: True}
    # Sent again (a reinstall, a second phone): the PC already has it, nothing moves.
    again = MemoryVault(phone, data_dir=tmp_path / "fresh")
    scan(phone, again)
    pieces = pc.pieces
    assert send(phone, again, call=pc)["already"] == 2 and pc.pieces == pieces


def test_a_damaged_file_is_never_kept(tmp_path):
    shelf = VaultShelf(tmp_path / "v")
    data = b"real photo"
    sha = hashlib.sha256(data).hexdigest()
    with pytest.raises(ValueError):
        shelf.receive(sha, 0, b"real phot0", len(data), "a.jpg")
    assert shelf.have([sha])[sha] == {"stored": False, "partial": 0}
    assert shelf.receive(sha, 5, b"photo", len(data))["resend_from"] == 0  # out of step: it says where it is
    with pytest.raises(ValueError):
        shelf.have(["../../etc"])


# ------------------------------------------------------------------ letting go: only an offer, only what's confirmed


def test_freeing_space_is_only_for_what_the_pc_just_confirmed(phone, tmp_path):
    old = _shoot(phone.roll, "IMG_20260101_090000.jpg", _jpeg("2026:01:01 09:00:00", pixels=b"O" * 50))
    other = _shoot(phone.roll, "IMG_20260102_090000.jpg", _jpeg("2026:01:02 09:00:00", pixels=b"R" * 50))
    recent = _shoot(phone.roll, "IMG_20261017_090000.jpg", _jpeg("2026:10:17 09:00:00", pixels=b"N" * 50))
    scan(phone, phone.memory_vault)
    today = date(2026, 10, 18)
    assert free_offer(phone, phone.memory_vault, today)["count"] == 0  # nothing is on the PC yet
    pc = PretendPC(tmp_path / "pc-vault")
    send(phone, phone.memory_vault, call=pc)
    offer = free_offer(phone, phone.memory_vault, today)
    assert set(offer["shas"]) == {old, other} and recent not in offer["shas"]  # kept: newer than 30 days
    # The PC's copy of one got damaged: that one is never in the plan.
    pc.shelf.path_of(other).write_bytes(b"broken")
    plan = free_plan(phone, phone.memory_vault, "old", call=pc, today=today)
    assert plan["count"] == 1 and plan["not_confirmed"] == 1
    assert plan["paths"] == [str(phone.roll / "IMG_20260101_090000.jpg")]
    # Android moved it to its Trash: the memory stays in the vault, on the PC.
    os.remove(plan["paths"][0])
    freed = note_freed(phone, phone.memory_vault, plan["paths"])
    assert freed["count"] == 1 and phone.memory_vault.items[old]["on_pc"]
    assert not phone.memory_vault.on_phone(phone.memory_vault.items[old])
    scan(phone, phone.memory_vault)
    assert old in phone.memory_vault.items  # still remembered after the next look


def test_the_screen(phone, tmp_path):
    from core import person_settings

    _shoot(phone.roll, "IMG_20261003_090000.jpg", _jpeg("2026:10:03 09:00:00", pixels=b"A" * 40))
    _shoot(phone.roll, "IMG_20261003_090001.jpg", _jpeg("2026:10:03 09:00:01", pixels=b"B" * 90))
    _shoot(phone.roll, "IMG_20260920_090000.jpg", _jpeg("2026:09:20 09:00:00", pixels=b"C" * 40))
    person_settings.put(phone, "vault.on", True)
    scan(phone, phone.memory_vault)
    page = vault_page(phone, today=date(2026, 10, 18))
    assert page["available"] and page["summary"]["photos"] == 3 and page["summary"]["waiting"] == 3
    assert page["month"] == "2026-10" and [m["month"] for m in page["months"]] == ["2026-10", "2026-09"]
    day = page["days"][0]
    assert day["day"] == "2026-10-03" and len(day["items"]) == 2
    assert sum(1 for i in day["items"] if i["best"]) == 1 and all(i["burst"] for i in day["items"])
    assert page["bursts"][0]["count"] == 2 and not page["bursts"][0]["others_safe"]
    assert vault_page(phone, month="2026-09")["days"][0]["day"] == "2026-09-20"


def test_the_chronicle_counts_the_weeks_photos(phone):
    from core.chronicle import chronicle_page

    _shoot(phone.roll, "IMG_20261014_090000.jpg", _jpeg("2026:10:14 09:00:00", pixels=b"W" * 40))
    scan(phone, phone.memory_vault)
    page = chronicle_page(phone, today=date(2026, 10, 18))
    assert page["this_week"]["photos"]["count"] == 1 and page["this_week"]["photos"]["cover"]


def test_one_round_waits_for_wifi_and_for_the_pc(phone, tmp_path, monkeypatch):
    import threading

    _shoot(phone.roll, "IMG_20261003_090000.jpg", b"photo")
    lock = threading.Lock()
    assert mv.round_(phone, lock)["state"] == "off"
    monkeypatch.setattr(mv, "is_on", lambda context: True)
    assert mv.round_(phone, lock)["state"] == "not_linked"
    phone.config.set("home_pc.url", "http://100.64.0.9:8765")
    phone.config.set("home_pc.token", "key")
    monkeypatch.setattr(mv, "on_metered_network", lambda: True)
    assert mv.round_(phone, lock)["state"] == "waiting_wifi"
    monkeypatch.setattr(mv, "on_metered_network", lambda: False)
    assert mv.round_(phone, lock, call=PretendPC(tmp_path / "pc"))["state"] == "safe"


# ------------------------------------------------------------------ the endpoints


def test_the_endpoints(phone, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app

    shelf = VaultShelf(tmp_path / "pc-vault")
    monkeypatch.setattr(mv, "shelf_for", lambda context, pid: shelf)
    phone.profiles.set_password(phone.me.profile_id, "pw")
    phone.voice = phone.llm = phone.push_subscriptions = None
    client = TestClient(server_app.create_app(phone))
    token = client.post("/api/login", json={"profile_id": phone.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    # The computer's side.
    data = b"a whole photo"
    sha = hashlib.sha256(data).hexdigest()
    assert client.post("/api/vault/have", json={"shas": [sha]}).json()["have"][sha] == {"stored": False, "partial": 0}
    put = client.put(f"/api/vault/blob/{sha}", params={"offset": 0, "size": len(data), "name": "IMG_1.jpg"}, content=data)
    assert put.json()["stored"] and client.post("/api/vault/verify", json={"shas": [sha]}).json()["ok"][sha]
    assert client.get(f"/api/vault/blob/{sha}").content == data
    assert client.post("/api/vault/have", json={"shas": ["nope"]}).status_code == 400

    # The phone's screen.
    photo = _jpeg(pixels=b"Z" * 30)
    mine = _shoot(phone.roll, "IMG_20261018_101530.jpg", photo)
    scan(phone, phone.memory_vault)
    assert client.get("/api/vault").json()["summary"]["photos"] == 1
    assert client.get(f"/api/vault/photo/{mine}").content == b"\xff\xd8THUMB\xff\xd9"  # its own small preview
    assert client.get(f"/api/vault/photo/{mine}", params={"full": 1}).content == photo
    assert client.get("/api/vault/photo/" + "0" * 64).status_code == 404


def test_the_pc_scores_the_sharper_better_lit_shot_higher(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image, ImageFilter

    sharp = Image.new("L", (200, 200))
    sharp.putdata([200 if (x // 10 + y // 10) % 2 else 60 for y in range(200) for x in range(200)])
    sharp.convert("RGB").save(tmp_path / "sharp.jpg")
    sharp.filter(ImageFilter.GaussianBlur(6)).convert("RGB").save(tmp_path / "blurry.jpg")
    Image.new("RGB", (200, 200), (3, 3, 3)).save(tmp_path / "dark.jpg")
    scores = {n: mv.score_photo(tmp_path / f"{n}.jpg") for n in ("sharp", "blurry", "dark")}
    assert scores["sharp"] > scores["blurry"] > scores["dark"]
    assert mv.score_photo(tmp_path / "missing.jpg") is None
