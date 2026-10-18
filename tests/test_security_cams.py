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


# ------------------------------------------------------------------ cameras on the home computer, from the phone


@pytest.fixture
def phone_and_pc(tmp_path, monkeypatch):
    """A phone linked to a home computer: home_call answers like MIA on the PC would."""
    import core.home_link as hl
    import core.security_cams as sc
    from core.home_link import HomeLinkError

    pc = build_world(tmp_path / "pc", monkeypatch)
    pc.security = SecurityBook(pc, data_dir=pc.home_dir)
    phone = build_world(tmp_path / "phone", monkeypatch)
    phone.actions = ActionCenter()
    phone.security = SecurityBook(phone, data_dir=phone.home_dir)
    phone.config.set("home_pc.url", "http://100.64.0.9:8765")
    phone.config.set("home_pc.token", "device-key")
    monkeypatch.setattr(sc, "_http_picture", lambda url, u, p: JPEG)
    state = {"up": True}

    def home_call(context, path, payload=None, timeout=6.0, method="", raw=False):
        if not state["up"]:
            raise HomeLinkError("Can't reach the home computer right now.")
        if path == "/api/security":
            return security_page(pc)
        if path.endswith("/frame"):
            return pc.security.frame(path.split("/")[-2])
        if path == "/api/security/camera":
            cam = pc.security.save_camera(payload["camera_id"], payload["name"], payload["location"], payload["brand"],
                                          payload["host"], payload["path"], payload["user"], payload["password"])
            return {"message": f"{cam.name} is saved."}
        if method == "DELETE":
            pc.security.remove(path.split("/")[-1])
            return {"message": "Removed."}
        raise AssertionError(path)

    monkeypatch.setattr(hl, "home_call", home_call)
    return phone, pc, state


def test_the_phone_watches_the_pcs_cameras(phone_and_pc):
    phone, pc, state = phone_and_pc
    cam = pc.security.save_camera(None, "Barn", "Barn", "Reolink", "192.168.1.50", "", "admin", "pw")
    page = security_page(phone)
    assert page["home"]["reachable"]
    [remote] = page["cameras"]
    assert remote["id"] == "pc-" + cam.camera_id and remote["on_pc"] and "pw" not in str(page)
    assert phone.security.frame(remote["id"]) == JPEG
    p = phone.actions.propose(phone, "security.save_picture", {"camera_id": remote["id"]})
    assert "kept on this phone" in p.summary
    phone.actions.approve(phone, p.proposal_id)
    assert security_page(phone)["pictures"][0]["camera"] == "Barn"
    p = phone.actions.propose(phone, "camera.remove", {"camera_id": remote["id"]})
    assert "home computer" in p.summary
    phone.actions.approve(phone, p.proposal_id)
    assert pc.security.cameras == []


def test_when_the_pc_is_away(phone_and_pc):
    phone, pc, state = phone_and_pc
    pc.security.save_camera(None, "Barn", "Barn", "Reolink", "192.168.1.50", "", "admin", "pw")
    state["up"] = False
    page = security_page(phone)
    assert page["home"] == {"linked": True, "reachable": False, "problem": "Can't reach the home computer right now."}
    assert page["cameras"] == []
    with pytest.raises(CameraError, match="home computer"):
        phone.security.frame("pc-0123456789")
    with pytest.raises(CameraError):
        phone.security.frame("pc-../../etc")
