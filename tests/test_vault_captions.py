"""Finding a photo again (core/vault_captions.py): the photos this PC keeps for the phone, each described in one
sentence by the local vision model (never who anyone is), kept beside the photo, and searched by what's in them."""

import json
from types import SimpleNamespace

from core import vault_captions as vc
from core.memory_vault import VaultShelf


def _shelf(tmp_path):
    (tmp_path / "files").mkdir()
    index = {}
    for n, (name, at) in enumerate((("creek.jpg", "2026-10-01T09:00:00"), ("truck.jpg", "2026-10-03T09:00:00"),
                                    ("clip.mp4", "2026-10-04T09:00:00"))):
        (tmp_path / "files" / name).write_bytes(b"not really a photo")
        index[f"{n:064x}"] = {"path": f"files/{name}", "size": 18, "name": name, "taken_at": at,
                              "kind": "video" if name.endswith("mp4") else "photo"}
    (tmp_path / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return VaultShelf(tmp_path)


def test_photos_are_described_newest_first_and_kept_beside_them(tmp_path):
    shelf = _shelf(tmp_path)
    asked = []

    def model(name, prompt, image):
        asked.append(prompt)
        return ' "A rusty pickup truck parked by two creeks." ' if len(asked) == 1 else "A creek in the woods."

    assert vc.caption_shelf(shelf, ask=model) == 2  # the video waits
    kept = VaultShelf(tmp_path).index
    assert kept[f"{1:064x}"]["caption"] == "A rusty pickup truck parked by two creeks."  # the newest first, cleaned
    assert "never say or guess who anyone is" in asked[0]
    assert vc.caption_shelf(shelf, ask=model) == 0  # each once


def test_a_missing_model_stops_the_night(tmp_path):
    shelf = _shelf(tmp_path)

    def down(name, prompt, image):
        raise OSError("connection refused")

    assert vc.caption_shelf(shelf, ask=down) == 0 and not any(e.get("caption") for e in shelf.index.values())


def test_search_by_what_is_in_them(tmp_path):
    shelf = _shelf(tmp_path)
    for e in shelf.index.values():
        e["caption"] = "A creek with a dog in the snow." if e["name"] == "creek.jpg" else "A red truck."
    assert [f["name"] for f in vc.search(shelf, "photos of dogs in snow")] == ["creek.jpg"]
    assert vc.search(shelf, "find my photos") == []  # nothing asked for but the asking
    assert vc.search(shelf, "a cat") == []


def test_asked_for_by_voice(tmp_path, monkeypatch):
    import core.memory_vault as mv

    shelf = _shelf(tmp_path)
    monkeypatch.setattr(mv, "shelf_for", lambda context, pid: shelf)
    context = SimpleNamespace(profile_id="p1")
    assert "haven't looked through your photos yet" in vc._action_find_photos(context, {"what": "the creek"})
    shelf.index[f"{0:064x}"]["caption"] = "A creek in the woods."
    said = vc._action_find_photos(context, {"what": "the creek"})
    assert said == "1 photo with the creek:\n- 2026-10-01: A creek in the woods."
    assert vc._action_find_photos(context, {"what": "a boat"}) == "None of the photos I've looked at show a boat."


def test_only_at_night_and_only_where_photos_are_kept(tmp_path, monkeypatch):
    from datetime import datetime

    monkeypatch.setattr(vc, "DATA", tmp_path / "marks")
    monkeypatch.setattr(vc, "shelves", lambda root=None: [tmp_path])
    assert vc.due(datetime(2026, 11, 6, 3, 0)) and not vc.due(datetime(2026, 11, 6, 14, 0))
    monkeypatch.setattr(vc, "shelves", lambda root=None: [])
    assert not vc.due(datetime(2026, 11, 6, 3, 0))
