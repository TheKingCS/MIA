"""
Phone access from Settings (core/phone_server.py): starting and stopping
the real server live, the Tailscale checks, and the status checklist.
"""

import json
import socket
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.phone_server import (
    PhoneServer, PhoneServerStatus, TailscaleInfo, describe_last_seen, describe_status, parse_tailscale_status,
    serve_command, serve_forwards_to, tailscale_info,
)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.config.set("server.port", free_port())
    context.profiles = SimpleNamespace(
        list_profiles=lambda: [SimpleNamespace(profile_id="p1", name="Zac", has_password=True, created_at="")],
        find_for_sign_in=lambda who: (SimpleNamespace(profile_id="p1", name="Zac", has_password=True)
                                      if who.strip().lower() in ("p1", "zac") else None),
        verify_password=lambda pid, pw: pw == "pw",
    )
    context.voice = context.llm = context.push_subscriptions = None
    context.phone_server = PhoneServer(context)
    yield context
    context.phone_server.stop()


def get(port, path, token=None):
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read() or b"{}")


def login(port):
    body = json.dumps({"profile_id": "zac", "password": "pw"}).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{port}/api/login", data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())["token"]


def test_switching_on_and_off_live_and_saving_the_choice(ctx, tmp_path):
    server, port = ctx.phone_server, ctx.phone_server.port
    assert not server.enabled and not server.running
    assert server.set_enabled(True)
    assert server.running and json.loads((tmp_path / "config.json").read_text())["server"]["enabled"] is True
    token = login(port)
    get(port, "/api/voice/status", token)
    status = server.status()
    assert status.phones and status.phones[0][0] == "p1" and status.profiles_with_password == 1
    assert not server.set_enabled(False)
    assert not server.running and json.loads((tmp_path / "config.json").read_text())["server"]["enabled"] is False
    with pytest.raises(OSError):
        get(port, "/api/vapid-public-key")
    assert server.set_enabled(True)  # and back on, same port
    assert login(port)


def test_port_in_use_is_explained(ctx):
    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", ctx.phone_server.port))
        blocker.listen()
        assert not ctx.phone_server.set_enabled(True)
    assert "already in use" in ctx.phone_server.last_error
    assert "already in use" in "\n".join(describe_status(ctx.phone_server.status(), None, 0))


def test_tailscale_parsing():
    status = json.dumps({"BackendState": "Running", "Self": {"DNSName": "mia-home.tail1234.ts.net."}})
    assert parse_tailscale_status(status) == (True, "https://mia-home.tail1234.ts.net")
    assert parse_tailscale_status(json.dumps({"BackendState": "NeedsLogin", "Self": {}})) == (False, "")
    assert parse_tailscale_status("not json") == (False, "")
    serve = json.dumps({"Web": {"mia-home.tail1234.ts.net:443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:8765"}}}}})
    assert serve_forwards_to(serve, 8765) and not serve_forwards_to(serve, 9000)
    assert serve_command(8765) == "sudo tailscale serve --bg http://127.0.0.1:8765"


def test_tailscale_info_with_a_fake_cli():
    calls = []

    def run(args, **kwargs):
        calls.append(args[1:])
        if args[1] == "status":
            return SimpleNamespace(stdout=json.dumps({"BackendState": "Running", "Self": {"DNSName": "mia.ts.net."}}))
        return SimpleNamespace(stdout='{"Web": {"x": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:8765"}}}}}')

    info = tailscale_info(8765, run=run, which=lambda name: "/usr/bin/tailscale")
    assert info.running and info.serving_mia and info.address == "https://mia.ts.net"
    assert tailscale_info(8765, which=lambda name: None).problem.startswith("Tailscale isn't installed")
    stopped = tailscale_info(8765, run=lambda args, **kw: SimpleNamespace(stdout='{"BackendState": "Stopped"}'),
                             which=lambda name: "/usr/bin/tailscale")
    assert "sudo tailscale up" in stopped.problem


def test_status_checklist():
    off = PhoneServerStatus(enabled=False, running=False, host="127.0.0.1", port=8765)
    assert describe_status(off, None, 0) == ["Phone access is off."]
    on = PhoneServerStatus(enabled=True, running=True, host="127.0.0.1", port=8765, profiles_with_password=0,
                           phones=[("p1", 1000.0)])
    lines = describe_status(on, TailscaleInfo(installed=True, running=True, address="https://mia.ts.net"), 1300.0)
    assert lines[0].startswith("✓ MIA is listening")
    assert "Change Password" in lines[1]
    assert "sudo tailscale serve --bg http://127.0.0.1:8765" in lines[2]
    assert lines[3] == "✓ Phone last connected 5 minutes ago."
    ready = describe_status(on, TailscaleInfo(installed=True, running=True, address="https://mia.ts.net", serving_mia=True), 1000)
    assert "✓ Your phone address: https://mia.ts.net" in ready


def test_last_seen_wording():
    assert describe_last_seen(30) == "just now"
    assert describe_last_seen(300) == "5 minutes ago"
    assert describe_last_seen(3700) == "1 hour ago"
    assert describe_last_seen(3 * 86400) == "3 days ago"


def test_settings_page_shows_the_switch(ctx, monkeypatch):
    from PySide6.QtWidgets import QApplication

    import modules.settings.module as settings_module

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(settings_module, "tailscale_info",
                        lambda port: TailscaleInfo(installed=True, running=True, address="https://mia.ts.net"))
    from core.profile_manager import ProfileManager  # noqa: F401  (Settings reads the active profile)

    ctx.profiles.get_active_profile = lambda: SimpleNamespace(name="Zac", profile_id="p1")
    module = settings_module.SettingsModule(ctx)
    widget = module.get_widget()
    assert not module._phone_checkbox.isChecked() and module._phone_status_label.text() == "Phone access is off."
    module._phone_checkbox.setChecked(True)
    assert ctx.phone_server.running
    assert "Run once: sudo tailscale serve" in module._phone_status_label.text()
    assert module._copy_serve_button.isVisibleTo(widget)
    module._on_copy_serve_command()
    assert QApplication.clipboard().text().startswith("sudo tailscale serve --bg http://127.0.0.1:")
    module._phone_checkbox.setChecked(False)
    assert not ctx.phone_server.running
    widget.deleteLater()
