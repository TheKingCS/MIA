"""
The Journal, Workshop, Expeditions, Music and Files screens (Zac,
2026-10-16: on the phone they "are empty right now and just bring up a
chat with MIA"): core/web_more.py builds each page, core/more_actions.py
makes every change through Propose → Approve, and core/my_files.py keeps
the Files screen inside the person's own folder.
"""

import os
import time
from datetime import date, timedelta

import pytest

import core.music_manager as music_module
from core.actions import ActionCenter, ActionError
from core.component_manager import ComponentManager
from core.expedition_manager import ExpeditionManager
from core.job_manager import JobManager
from core.journal_manager import JournalManager
from core.ledger_manager import LedgerManager
from core.material_manager import MaterialManager
from core.more_actions import tags_of
from core.music_manager import MusicManager
from core.my_files import MyFiles, clean_name, kind_of, size_text
from core.product_manager import ProductManager
from core.trip_manager import TripManager
from core.web_more import (duration_text, expeditions_page, files_page, journal_page, music_page, preview,
                           track_path, workshop_page)
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    shop = tmp_path / "shop"
    context.journal = JournalManager(context, data_dir=tmp_path / "me")
    context.components = ComponentManager(context, data_dir=shop)
    context.materials = MaterialManager(context, data_dir=shop)
    context.products = ProductManager(context, data_dir=shop)
    context.jobs = JobManager(context, data_dir=shop)
    context.ledger = LedgerManager(context, data_dir=shop)
    context.config.set("trips.photo_root_path", str(tmp_path / "photos"))
    context.expeditions = ExpeditionManager(context, data_dir=shop)
    context.trips = TripManager(context, data_dir=shop)
    monkeypatch.setattr(music_module, "_DATA_DIR", tmp_path / "music_data")
    monkeypatch.setattr(music_module, "_TRACKS_FILE", tmp_path / "music_data" / "t.json")
    monkeypatch.setattr(music_module, "_PLAYLISTS_FILE", tmp_path / "music_data" / "p.json")
    library = tmp_path / "Music"
    library.mkdir()
    song = library / "Robin - Morning.mp3"
    song.write_bytes(b"ID3" + b"\0" * 200)
    os.utime(song, (time.time() - 3600, time.time() - 3600))  # a fresh file is skipped as "still copying"
    context.config.set("music.library_root_path", str(library))
    context.music = MusicManager(context)
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal.summary, done.result


def test_pure_bits():
    assert tags_of("Garden, ideas ,#garden;  ") == ["garden", "ideas"]
    assert preview("a  b\nc") == "a b c" and preview("word " * 60).endswith("…")
    assert duration_text(245) == "4:05" and duration_text(3725) == "1:02:05" and duration_text(None) == ""
    assert kind_of("x.JPG") == "image" and kind_of("a.pdf") == "pdf" and kind_of("b.bin") == "file"
    assert size_text(1536) == "1.5 KB" and size_text(12) == "12 bytes"
    assert clean_name("  report.txt ") == "report.txt"
    for bad in ("", "..", "a/b", "c:d"):
        with pytest.raises(ValueError):
            clean_name(bad)


def test_the_journal(world):
    said, _ = do(world, "journal.add", title="Seed day", body="Planted the beans.", tags="garden, Spring")
    assert said == 'Add the journal entry "Seed day" (tagged garden, spring)'
    page = journal_page(world, TODAY)
    entry = page["entries"][0]
    assert entry["title"] == "Seed day" and entry["tags"] == ["garden", "spring"] and page["counts"]["entries"] == 1
    assert page["tags"][0] == {"tag": "garden", "count": 1} and page["forms"]["journal"]["fields"][0]["name"] == "title"
    said, _ = do(world, "journal.edit", entry_id=entry["id"], title="Seed day", tags="garden")
    assert said == 'Change "Seed day": tags'
    with pytest.raises(ActionError):
        world.actions.propose(world, "journal.edit", {"entry_id": entry["id"], "title": "Seed day"})
    proposal = world.actions.propose(world, "journal.delete", {"entry_id": entry["id"]})
    world.actions.approve(world, proposal.proposal_id)
    assert journal_page(world, TODAY)["entries"] == []
    assert world.actions.undo(world, proposal.proposal_id).status == "undone"  # undo brings it back
    assert journal_page(world, TODAY)["entries"][0]["title"] == "Seed day"


def test_the_workshop(world):
    do(world, "material.add", name="Plywood", unit="sheet", quantity_on_hand="4", reorder_threshold="2", unit_cost="30")
    do(world, "product.add", name="Birdhouse", base_price="25", quantity_in_stock="0")
    do(world, "component.add", name="Resistor", value="10k", quantity="50")
    do(world, "job.add", name="Birdhouse batch", status="In Progress")
    page = workshop_page(world, TODAY)
    material, product, job = page["materials"][0], page["products"][0], page["jobs"][0]
    assert page["counts"] == {"parts": 1, "materials": 1, "low": 0, "products": 1, "open_jobs": 1}
    said, _ = do(world, "job.use", job_id=job["id"], material_id=material["id"], quantity="3")
    assert "used 3 sheet of Plywood" in said and "4 → 1" in said
    do(world, "job.make", job_id=job["id"], product_id=product["id"], quantity="5")
    said, _ = do(world, "product.sell", product_id=product["id"], quantity="2", amount="50")
    assert "Sold 2 Birdhouse" in said and "5 → 3" in said
    do(world, "shop_expense.add", amount="12.5", category="Shipping", description="Postage")
    do(world, "component.adjust", component_id=page["parts"][0]["id"], delta="-5")
    page = workshop_page(world, TODAY)
    assert page["materials"][0]["low"] and page["counts"]["low"] == 1
    assert page["products"][0]["stock"] == 3 and page["parts"][0]["quantity"] == 45
    assert page["jobs"][0]["used"] == ["3 sheet Plywood"] and page["jobs"][0]["made"] == ["5 Birdhouse"]
    assert {r["kind"] for r in page["money"]} == {"sale", "cost"} and page["totals"]["profit_value"] == 37.5
    with pytest.raises(ActionError):
        world.actions.propose(world, "component.adjust", {"component_id": page["parts"][0]["id"], "delta": "1.5"})


def test_expeditions_and_packing(world):
    start = (TODAY + timedelta(days=10)).isoformat()
    do(world, "expedition.add", name="Lake weekend", location="North lake", start_date=start)
    page = expeditions_page(world, TODAY)
    exp = page["expeditions"][0]
    assert exp["when"] == "upcoming" and exp["days_away"] == 10
    said, _ = do(world, "trip.add", expedition_id=exp["id"], name="Paddle", activity_type="Kayaking", start_date=start)
    assert said.startswith("Add the trip Paddle to Lake weekend")
    trip = expeditions_page(world, TODAY)["expeditions"][0]["trips"][0]
    do(world, "gear.add", trip_id=trip["id"], label="Life jacket")
    do(world, "gear.add", trip_id=trip["id"], label="Water")
    do(world, "gear.toggle", trip_id=trip["id"], index="0")
    do(world, "trip.status", trip_id=trip["id"], status="active")
    trip = expeditions_page(world, TODAY)["expeditions"][0]["trips"][0]
    assert trip["packed"] == 1 and trip["gear"][0] == {"index": 0, "label": "Life jacket", "packed": True}
    assert expeditions_page(world, TODAY)["expeditions"][0]["when"] == "now"
    do(world, "gear.remove", trip_id=trip["id"], index="1")
    with pytest.raises(ActionError):
        world.actions.propose(world, "gear.toggle", {"trip_id": trip["id"], "index": "5"})
    with pytest.raises(ActionError):
        world.actions.propose(world, "trip.add", {"name": "Lost"})


def test_music_library_and_playlists(world):
    _, result = do(world, "music.scan")
    assert result.startswith("Library scanned: 1 new")
    page = music_page(world)
    track = page["tracks"][0]
    assert page["library"]["count"] == 1 and page["library"]["found"]
    assert track_path(world, track["id"]).name == "Robin - Morning.mp3" and track_path(world, "nope") is None
    do(world, "playlist.add", name="Mornings")
    playlist = music_page(world)["playlists"][0]
    do(world, "playlist.add_track", playlist_id=playlist["id"], track_id=track["id"])
    assert music_page(world)["playlists"][0]["track_ids"] == [track["id"]]
    with pytest.raises(ActionError):
        world.actions.propose(world, "playlist.add_track", {"playlist_id": playlist["id"], "track_id": track["id"]})
    do(world, "playlist.rename", playlist_id=playlist["id"], name="Wake up")
    do(world, "playlist.delete", playlist_id=playlist["id"])
    assert music_page(world)["playlists"] == [] and music_page(world)["tracks"]


def test_my_files_stay_in_the_persons_folder(world, tmp_path):
    files = MyFiles.for_context(world)
    assert files.root == tmp_path / "me" / "my_files"
    do(world, "myfile.folder", path="", name="Receipts")
    saved = files.save("Receipts", "scan.pdf", b"%PDF-1")
    assert saved == "Receipts/scan.pdf" and files.save("Receipts", "scan.pdf", b"2") == "Receipts/scan (2).pdf"
    page = files_page(world, "Receipts")
    assert [f["name"] for f in page["files"]] == ["scan (2).pdf", "scan.pdf"] and page["files"][0]["kind"] == "pdf"
    assert [c["name"] for c in page["crumbs"]] == ["My Files", "Receipts"]
    do(world, "myfile.rename", path="Receipts/scan (2).pdf", name="march.pdf")
    said, _ = do(world, "myfile.delete", path="Receipts")
    assert said == "Delete the folder and everything in it Receipts. This can't be undone."
    assert files_page(world)["folders"] == []
    (tmp_path / "secret.txt").write_text("not yours")
    for bad in ("../secret.txt", "/etc/passwd", "../../secret.txt"):
        with pytest.raises(ValueError):
            files.file(bad)
    with pytest.raises(ActionError):
        world.actions.propose(world, "myfile.delete", {"path": ""})
    with pytest.raises(ActionError):
        world.actions.propose(world, "myfile.delete", {"path": "../secret.txt"})


def test_the_screens_are_served(world, tmp_path):
    from fastapi.testclient import TestClient

    from server.app import create_app

    app = create_app(world)
    profile = world.profiles.list_profiles()[0]
    app.state.sessions["t"] = profile.profile_id
    client = TestClient(app, headers={"Authorization": "Bearer t"})
    for path in ("/api/journal", "/api/workshop", "/api/expeditions", "/api/music", "/api/files"):
        response = client.get(path)
        assert response.status_code == 200 and response.json()["available"], path
    up = client.post("/api/files/upload", content=b"hello", headers={"X-Filename": "note.txt"})
    assert up.status_code == 200 and up.json()["path"] == "note.txt"
    assert client.get("/api/files/file", params={"path": "note.txt"}).content == b"hello"
    assert client.get("/api/files/file", params={"path": "../x"}).status_code == 404
    world.music.scan_library()
    track = world.music.all_tracks()[0]
    assert client.get(f"/api/music/track/{track.track_id}/audio").content.startswith(b"ID3")


def test_expedition_photos_videos_and_files(world, tmp_path):
    """Zac, 2026-10-16: "after planning a trip you should be able to attach
    pictures and videos and files to it" (core/expedition_media.py)."""
    from core.expedition_media import folder, media, path_of, save

    do(world, "expedition.add", name="Lake weekend")
    exp = expeditions_page(world, TODAY)["expeditions"][0]
    assert exp["media"] == []
    assert save(world, exp["id"], "dock.jpg", b"jpg") == "dock.jpg"
    assert save(world, exp["id"], "dock.jpg", b"jpg2") == "dock (2).jpg"
    save(world, exp["id"], "paddle.mp4", b"mp4")
    save(world, exp["id"], "permit.pdf", b"%PDF")
    do(world, "trip.add", expedition_id=exp["id"], name="Paddle")
    trip = world.trips.all_trips()[0]
    (tmp_path / "sunset.png").write_bytes(b"png")
    world.trips.add_photo(trip.trip_id, tmp_path / "sunset.png")  # a photo added on the desktop
    items = {m["name"]: m for m in expeditions_page(world, TODAY)["expeditions"][0]["media"]}
    assert set(items) == {"dock.jpg", "dock (2).jpg", "paddle.mp4", "permit.pdf", "sunset.png"}
    assert (items["paddle.mp4"]["kind"], items["permit.pdf"]["kind"], items["sunset.png"]["trip"]) == ("video", "pdf", "Paddle")
    assert path_of(world, exp["id"], items["sunset.png"]["ref"]).read_bytes() == b"png"
    for bad in ("e/../../secret", "t/" + trip.trip_id + "/../x", "x/dock.jpg", "e/"):
        with pytest.raises(ValueError):
            path_of(world, exp["id"], bad)
    said, _ = do(world, "expedition.media_delete", expedition_id=exp["id"], ref=items["sunset.png"]["ref"])
    assert said == "Delete sunset.png from this expedition. This can't be undone."
    assert world.trips.get_trip(trip.trip_id).photo_filenames == []
    do(world, "expedition.media_delete", expedition_id=exp["id"], ref="e/dock (2).jpg")
    assert len(media(world, exp["id"])) == 3 and folder(world, exp["id"]).is_dir()
    with pytest.raises(ActionError):
        world.actions.propose(world, "expedition.media_delete", {"expedition_id": exp["id"], "ref": "e/../../x"})


def test_uploading_songs(world, tmp_path):
    """Zac, 2026-10-16: "make Music where I can upload mp3 files"."""
    path = world.music.save_upload("Robin - Road Song.mp3", b"ID3" + b"\0" * 100)
    assert path.parent.name == "Uploads" and path.parent.parent == tmp_path / "Music"
    world.music.scan_library(as_of=time.time() + 60)
    page = music_page(world)
    song = next(t for t in page["tracks"] if t["title"] == "Robin - Road Song")
    assert song["uploaded"] and not next(t for t in page["tracks"] if t["title"] != "Robin - Road Song")["uploaded"]
    with pytest.raises(ValueError):
        world.music.save_upload("notes.txt", b"x")
    said, _ = do(world, "track.delete", track_id=song["id"])
    assert said == "Delete Robin - Road Song from your library. This can't be undone." and not path.exists()
    other = music_page(world)["tracks"][0]
    with pytest.raises(ActionError):  # a song from the music folder itself is never deleted
        world.actions.propose(world, "track.delete", {"track_id": other["id"]})


def test_a_chosen_music_folder_that_is_missing_is_never_made(world, tmp_path):
    world.config.set("music.library_root_path", str(tmp_path / "unplugged"))
    with pytest.raises(ValueError):
        world.music.save_upload("a.mp3", b"ID3")
    assert not (tmp_path / "unplugged").exists()


def test_uploads_through_the_server(world, tmp_path):
    from fastapi.testclient import TestClient

    from server.app import create_app

    app = create_app(world)
    app.state.sessions["t"] = world.profiles.list_profiles()[0].profile_id
    client = TestClient(app, headers={"Authorization": "Bearer t"})
    up = client.post("/api/music/upload", content=b"ID3" + b"\0" * 50, headers={"X-Filename": "Wake%20Up.mp3"})
    assert up.status_code == 200 and up.json()["message"] == "Added Wake Up to your library."
    assert any(t["title"] == "Wake Up" for t in client.get("/api/music").json()["tracks"])
    assert client.post("/api/music/upload", content=b"x", headers={"X-Filename": "a.exe"}).status_code == 400
    do(world, "expedition.add", name="Lake weekend")
    exp_id = world.expeditions.all_expeditions()[0].expedition_id
    up = client.post(f"/api/expeditions/{exp_id}/media", content=b"jpg", headers={"X-Filename": "dock.jpg"})
    assert up.status_code == 200
    got = client.get(f"/api/expeditions/{exp_id}/media", params={"ref": "e/dock.jpg"})
    assert got.status_code == 200 and got.content == b"jpg"
    assert client.get(f"/api/expeditions/{exp_id}/media", params={"ref": "e/../../config.json"}).status_code == 404
