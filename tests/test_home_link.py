"""Supercharged online (DEC-0022 level 2, core/home_link.py): a phone
links to MIA on the home computer with the person's own sign-in, Talk uses
the computer's model, and the phone's own model answers whenever the
computer can't (and MIA says which one did)."""

import urllib.error
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

import core.home_link as home_link
import server.app as server_app_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.llm_manager import ChatReply, LLMManager, LLMUnavailableError
from tests.test_server_app import context  # noqa: F401  (the computer's MIA, with Alice / hunter2)


class _Backend:
    def __init__(self, name, up=True):
        self._model, self.up, self.calls = name, up, 0

    def chat(self, messages, tools, timeout):
        self.calls += 1
        if not self.up:
            raise LLMUnavailableError("down")
        return ChatReply(content=f"from {self._model}")

    def generate(self, prompt, timeout):
        return self.chat([], [], timeout).content

    def is_available(self, timeout):
        return self.up


class _ComputerLLM:
    def __init__(self):
        self.backend, self._timeout = _Backend("qwen2.5:14b"), 5

    def is_available(self):
        return self.backend.up


@pytest.fixture
def link(context, tmp_path, monkeypatch):  # noqa: F811
    context.llm = _ComputerLLM()
    computer = TestClient(server_app_module.create_app(context))
    state = {"reachable": True}

    def request(url, payload, timeout, token=""):  # the phone's HTTP calls, sent to the computer
        if not state["reachable"]:
            raise urllib.error.URLError("no route to host")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        path = urlparse(url).path
        response = computer.post(path, json=payload, headers=headers) if payload is not None else computer.get(path, headers=headers)
        if response.status_code >= 400:
            raise urllib.error.HTTPError(url, response.status_code, response.text, {}, None)
        return response.json()

    monkeypatch.setattr(home_link, "_request", request)
    import core.config_manager as config_module

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "phone_config.json")
    phone = AppContext(config=ConfigManager(), events=EventBus())
    phone.llm = LLMManager(phone)
    phone.llm.use_backend(_Backend("phone 1.5B"))
    return phone, context, state


def test_link_talk_and_fall_back(link):
    phone, computer, state = link
    with pytest.raises(home_link.HomeLinkError, match="didn't accept"):
        home_link.connect(phone, "192.168.1.20:8765", "Alice", "wrong")
    done = home_link.connect(phone, "192.168.1.20:8765", "Alice", "hunter2")
    assert done == {"url": "http://192.168.1.20:8765", "model": "qwen2.5:14b", "available": True}
    assert phone.config.get("home_pc.token") and len(computer.config.get("home_link.devices")) == 1
    assert "hunter2" not in str(phone.config.get("home_pc.token"))  # only the device key is kept

    assert phone.llm.chat_with_tools([{"role": "user", "content": "hi"}], []).content == "from qwen2.5:14b"
    assert phone.llm.level == home_link.HOME_PC

    state["reachable"] = False  # away from home, mid-conversation
    assert phone.llm.chat_with_tools([{"role": "user", "content": "still there?"}], []).content == "from phone 1.5B"
    assert phone.llm.level == home_link.PHONE
    assert home_link.status(phone)["reachable"] is False  # and it doesn't keep waiting on the computer

    state["reachable"] = True
    home_link.disconnect(phone)
    assert phone.llm.home is None and computer.config.get("home_link.devices") == {}


def test_a_device_key_survives_a_restart_and_is_needed(link):
    phone, computer, _state = link
    home_link.connect(phone, "pc.tailnet:8765", "Alice", "hunter2")
    restarted = TestClient(server_app_module.create_app(computer))  # sessions gone, the key's hash is in config
    key = phone.config.get("home_pc.token")
    assert restarted.get("/api/model/info", headers={"Authorization": f"Bearer {key}"}).json()["available"] is True
    assert restarted.post("/api/model/chat", json={"messages": []}).status_code == 401


def test_addresses():
    assert home_link.clean_url("pc.tailnet:8765/") == "http://pc.tailnet:8765"
    with pytest.raises(home_link.HomeLinkError):
        home_link.clean_url("ftp://pc")
