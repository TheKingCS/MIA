"""
Security (DEC-0033): cameras on the home network only, logins kept
apart and never shown, frames from a picture address or an RTSP stream,
saved pictures, grown-ups only.
"""

import pytest

from core.actions import ActionCenter, ActionError
from core.security_cams import (CameraError, SecurityBook, clean_host, on_home_network, picture_url, rtsp_url,
                                security_page)
from tests.engine_world import build_world

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100 + b"\xff\xd9"


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.security = SecurityBook(context, data_dir=context.home_dir)
    return context


def test_home_network_only():
    for ok in ("192.168.1.40", "10.0.0.5", "172.16.3.4", "100.101.102.103", "169.254.1.2"):
        assert on_home_network(ok), ok
    for bad in ("8.8.8.8", "127.0.0.1", "localhost", "0.0.0.0", "", "evil.example.com", "a b"):
        assert not on_home_network(bad), bad
    assert clean_host("http://admin:x@192.168.1.40:80/foo") == "192.168.1.40:80"


def test_addresses_per_brand():
    assert picture_url("Amcrest / Dahua", "192.168.1.9") == "http://192.168.1.9/cgi-bin/snapshot.cgi?channel=1"
    assert "user=ad%20min&password=p%40ss" in picture_url("Reolink", "192.168.1.9", user="ad min", password="p@ss")
    assert picture_url("Tapo", "192.168.1.9") is None
    assert rtsp_url("Tapo", "192.168.1.9", user="me", password="p@ss") == "rtsp://me:p%40ss@192.168.1.9:554/stream2"
    assert picture_url("Other: picture address", "192.168.1.9:8080", "snap.jpg") == "http://192.168.1.9:8080/snap.jpg"


def test_save_check_and_never_show_the_password(world):
    book = world.security
    with pytest.raises(CameraError):
        book.save_camera(None, "Street", "Driveway", "Reolink", "8.8.8.8", "", "admin", "x")
    with pytest.raises(CameraError):
        book.save_camera(None, "", "Driveway", "Reolink", "192.168.1.40", "", "admin", "x")
    cam = book.save_camera(None, "Front Door", "Front Door", "Amcrest / Dahua", "192.168.1.40", "", "admin", "s3cret")
    page = security_page(world)
    assert page["cameras"][0]["has_password"] and "s3cret" not in str(page)
    assert "s3cret" not in (world.home_dir / "security_cameras.json").read_text()
    book.save_camera(cam.camera_id, "Front Door", "Porch", "Amcrest / Dahua", "192.168.1.40", "", "admin", None)
    assert book.login(cam.camera_id) == ("admin", "s3cret")  # None keeps the saved password


def test_frames_pictures_and_removing(world, monkeypatch):
    import core.security_cams as sc

    calls = []
    monkeypatch.setattr(sc, "_http_picture", lambda url, u, p: calls.append(url) or JPEG)
    cam = world.security.save_camera(None, "Yard", "Backyard", "Hikvision / Annke", "192.168.1.41", "", "admin", "pw")
    assert world.security.frame(cam.camera_id) == JPEG
    world.security.frame(cam.camera_id)
    assert len(calls) == 1  # a fresh frame is shared, not asked for twice
    proposal = world.actions.propose(world, "security.save_picture", {"camera_id": cam.camera_id})
    world.actions.approve(world, proposal.proposal_id)
    [pic] = security_page(world)["pictures"]
    assert pic["camera"] == "Yard" and world.security.picture_path(pic["name"]).read_bytes() == JPEG
    with pytest.raises(CameraError):
        world.security.picture_path("../security_logins.json")
    p = world.actions.propose(world, "security.picture_delete", {"name": pic["name"]})
    world.actions.approve(world, p.proposal_id)
    assert security_page(world)["pictures"] == []
    p = world.actions.propose(world, "camera.remove", {"camera_id": cam.camera_id})
    assert "isn't touched" in p.summary
    world.actions.approve(world, p.proposal_id)
    assert world.security.cameras == []


def test_a_stream_camera_without_ffmpeg_says_so(world, monkeypatch):
    import core.security_cams as sc

    monkeypatch.setattr(sc.shutil, "which", lambda name: None)
    cam = world.security.save_camera(None, "Shop", "Shop", "Tapo", "192.168.1.42", "", "me", "pw")
    with pytest.raises(CameraError, match="ffmpeg"):
        world.security.frame(cam.camera_id)
    assert "ffmpeg" in security_page(world)["cameras"][0]["problem"]


def test_grown_ups_only(world):
    from core.child_accounts import CHILD_APPS

    assert "security" not in CHILD_APPS
    from core.actions import ACTION_TYPES

    assert not any(ACTION_TYPES[k].child_ok for k in ("camera.remove", "security.save_picture", "security.picture_delete"))
