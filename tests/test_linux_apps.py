"""
tests.test_linux_apps
=======================

FW-11, the first version's part (REQ-DSK-007, REQ-DSK-023, REQ-FUN-003, REQ-ARC-013): MIA's launcher lists the
computer's Linux apps from its own desktop entries (hidden ones and other desktops' left out, each once), never in
her registry, opened by the desktop's launcher with fixed arguments; MIA's Settings opens KDE's System Settings at the
matching page, never a copy; both by voice too; and they open only from the computer itself.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import linux_apps


def _entry(folder: Path, name: str, text: str) -> None:
    """Writes one desktop entry."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("[Desktop Entry]\n" + text, encoding="utf-8")


def _apps(tmp_path) -> list:
    """Two folders of desktop entries: his own first, then the system's."""
    mine, system = tmp_path / "mine", tmp_path / "system"
    _entry(mine, "org.kde.krita.desktop", "Type=Application\nName=Krita (mine)\nX-Flatpak=org.kde.krita\n")
    _entry(system, "org.kde.krita.desktop", "Type=Application\nName=Krita\n")
    _entry(system, "firefox.desktop", "Type=Application\nName=Firefox\nComment=Web browser\nCategories=Network;WebBrowser;\n")
    _entry(system, "hidden.desktop", "Type=Application\nName=Hidden\nNoDisplay=true\n")
    _entry(system, "gnome-only.desktop", "Type=Application\nName=GNOME thing\nOnlyShowIn=GNOME;\n")
    _entry(system, "not-kde.desktop", "Type=Application\nName=Not here\nNotShowIn=KDE;\n")
    _entry(system, "a-link.desktop", "Type=Link\nName=A link\nURL=https://example.com\n")
    _entry(system, "broken.desktop", "this isn't an entry")
    return [mine, system]


def test_the_launcher_lists_each_linux_app_once_leaving_out_hidden_and_other_desktops(tmp_path):
    """His own entry hides the system's of the same id; hidden, GNOME-only, not-for-KDE, links and broken ones left out."""
    found = linux_apps.entries(_apps(tmp_path))
    assert [a["name"] for a in found] == ["Firefox", "Krita (mine)"]
    assert found[1]["flatpak"] and found[0]["categories"] == ["Network", "WebBrowser"]


def test_an_app_opens_only_by_a_listed_id_through_the_desktops_launcher(tmp_path):
    """gio launch on its desktop file, fixed arguments, in his session; an id that isn't listed opens nothing."""
    dirs = _apps(tmp_path)
    ran = []
    ok = lambda argv, **kw: ran.append(argv) or SimpleNamespace(returncode=0, stderr="")  # noqa: E731
    assert linux_apps.launch("firefox.desktop", run=ok, dirs=dirs) == "Firefox"
    assert ran == [linux_apps.in_session(["gio", "launch", str(dirs[1] / "firefox.desktop")])]
    for bad in ("hidden.desktop", "../../etc/passwd", "firefox.desktop; rm -rf ~"):
        with pytest.raises(ValueError):
            linux_apps.launch(bad, run=ok, dirs=dirs)


def test_a_system_setting_opens_its_kde_page_and_only_one_from_the_table(monkeypatch):
    """systemsettings with the page's module, started in his session; words map to the page; off Linux it says
    so."""
    started = []
    monkeypatch.setattr(linux_apps.sys, "platform", "linux")
    assert linux_apps.open_setting("display", start=started.append) == "Display and monitors"
    assert started == [linux_apps.in_session(["systemsettings", "kcm_kscreen"])]
    with pytest.raises(ValueError):
        linux_apps.open_setting("kcm_anything; reboot", start=started.append)
    assert linux_apps.setting_for("open the wifi settings") == "network"
    assert linux_apps.setting_for("Date and time please") == "time" and linux_apps.setting_for("my garden") is None
    monkeypatch.setattr(linux_apps.sys, "platform", "win32")
    with pytest.raises(RuntimeError):
        linux_apps.open_setting("display", start=started.append)
    assert linux_apps.entries() == []  # no Linux apps on Windows


def test_linux_apps_never_join_mias_registry_and_the_tools_are_claimed():
    """REQ-ARC-013: the registry is MIA's manifests only; the two tools are Settings', within a grant."""
    import json

    from core import app_registry

    root = Path(__file__).resolve().parent.parent
    assert "linux_apps" not in (root / "core" / "app_registry.py").read_text(encoding="utf-8")
    tiers = json.loads((root / "apps" / "settings" / "manifest.json").read_text(encoding="utf-8"))["capabilities"]["tiers"]
    assert tiers["open_system_setting"] == tiers["open_linux_app"] == "act_within_grant"
    assert app_registry.load().owner_of("open_system_setting") == "settings"


def test_they_open_only_from_the_computer_itself(tmp_path, monkeypatch):
    """Listed to anyone signed in; a phone's request to open one is refused."""
    from fastapi.testclient import TestClient

    import server.app as server_app
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.voice = world.llm = world.push_subscriptions = None
    world.profiles.set_password(world.me.profile_id, "pw")
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    auth = {"Authorization": "Bearer " + token}
    listing = client.get("/api/desktop", headers=auth).json()
    assert [s["key"] for s in listing["settings"]][:2] == ["display", "network"] and listing["here"] is False
    refused = client.post("/api/desktop/open", json={"setting": "display"}, headers=auth)
    assert refused.status_code == 403
