"""
Heavy jobs on the home computer (core/heavy_jobs.py): a device without
Tesseract, a speech model or a voice sends the job to the linked PC; the
PC unreachable means the old answer, and it isn't asked again for a while.
"""

import base64

import pytest

import core.heavy_jobs as heavy
import core.home_link as home_link
from core.home_link import HomeLinkError
from core.ocr import OcrQueue, read_result


@pytest.fixture
def phone(tmp_path, monkeypatch):
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.config.set("home_pc.url", "http://100.64.0.9:8765")
    world.config.set("home_pc.token", "device-key")
    world.config.set("ocr.tesseract_path", str(tmp_path / "no-tesseract-here"))
    monkeypatch.setattr("core.ocr.tesseract_path", lambda config: None)
    heavy._down_until.clear()
    calls = []
    state = {"up": True}

    def pc(context, path, payload=None, timeout=6.0, method="", raw=False, body=None, headers=None):
        calls.append(path)
        if not state["up"]:
            raise HomeLinkError("Can't reach the home computer right now.")
        if path == "/api/heavy/ocr":
            assert headers["X-Filename"] == "receipt.jpg" and body == b"JPEG"
            return {"pages": ["HARDWARE STORE\n2X4X8 STUD 3.98"]}
        if path == "/api/heavy/transcribe":
            return {"text": "log lunch"}
        if path == "/api/heavy/speak":
            return {"audio_wav_base64": base64.b64encode(b"RIFFwav").decode()}
        raise AssertionError(path)

    monkeypatch.setattr(home_link, "home_call", pc)
    world.pc_calls, world.pc_state = calls, state
    return world


def test_a_photo_is_read_on_the_home_computer(phone, tmp_path):
    queue = OcrQueue(phone)
    assert queue.available
    source, output = tmp_path / "receipt.jpg", tmp_path / "receipt.ocr.json"
    source.write_bytes(b"JPEG")
    queue.submit("r1", source, output)
    assert queue.wait(10)
    assert "2X4X8 STUD" in read_result(output).text and phone.pc_calls == ["/api/heavy/ocr"]


def test_when_the_pc_is_away_the_job_says_so_and_waits(phone, tmp_path):
    phone.pc_state["up"] = False
    queue = OcrQueue(phone)
    source, output = tmp_path / "receipt.jpg", tmp_path / "receipt.ocr.json"
    source.write_bytes(b"JPEG")
    queue.submit("r1", source, output)
    assert queue.wait(10)
    assert "home computer" in read_result(output).error
    assert not queue.available  # not asked again for a minute
    assert heavy.transcribe(phone, b"RIFF") is None and phone.pc_calls == ["/api/heavy/ocr"]


def test_hearing_and_speaking_on_the_pc(phone):
    assert heavy.transcribe(phone, b"RIFF....") == "log lunch"
    assert base64.b64decode(heavy.speak(phone, "Done.")) == b"RIFFwav"


def test_not_linked_means_the_phone_only(phone):
    phone.config.set("home_pc.url", "")
    assert not heavy.can_use_home(phone) and not OcrQueue(phone).available


def test_the_pcs_job_endpoints_need_its_own_engines(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    monkeypatch.setattr("core.ocr.tesseract_path", lambda config: None)
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.post("/api/heavy/ocr", content=b"x", headers={"X-Filename": "a.jpg"}).status_code == 503
    assert client.post("/api/heavy/transcribe", content=b"RIFF").status_code == 503
    assert client.post("/api/heavy/speak", json={"text": "hi"}).status_code == 503
