"""
tests.test_os_session
=======================

FW-03, MIA's own desktop session on MIA OS (DEC-0227, DEC-0278): her runtime writes where her shell finds her
(`core/desktop_session.py`), owner-only, and removes it when it stops; the shell (`gui/os_shell.py`) opens her front
end when she answers and a recovery page when she doesn't, whose links act only through its own scheme; and the image
carries the session entry, its scripts and the runtime's setting, tested in a VM under KWin's virtual display.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from pathlib import Path

from core import desktop_session
from gui import os_shell

ROOT = Path(__file__).resolve().parent.parent


class _Server:
    """A stand-in for her local server."""

    local_url = "http://127.0.0.1:8765"

    def __init__(self, running=True):
        """Whether it starts."""
        self.running = running

    def ensure_local(self):
        """Starts it on 127.0.0.1 (or doesn't)."""
        return self.running

    def local_session(self, who):
        """A token for the person signed in."""
        return f"token-for-{who}"


def _context(monkeypatch, who="p1", running=True):
    """A context with the stand-in server and this person signed in."""
    from core import person_settings

    monkeypatch.setattr(person_settings, "person_id", lambda context: who)
    return SimpleNamespace(phone_server=_Server(running))


def test_the_runtime_writes_where_her_shell_finds_her_owner_only_and_clears_it(tmp_path, monkeypatch):
    path = tmp_path / "mia" / "desktop.json"
    assert desktop_session.write(_context(monkeypatch), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["url"] == "http://127.0.0.1:8765" and data["token"] == "token-for-p1" and data["profile_id"] == "p1"
    if os.name == "posix":
        assert (path.stat().st_mode & 0o777) == 0o600
    assert desktop_session.read(path)["token"] == "token-for-p1"
    desktop_session.clear(path)
    assert not path.exists() and desktop_session.read(path) is None


def test_nobody_signed_in_or_no_server_writes_no_token_or_nothing(tmp_path, monkeypatch):
    path = tmp_path / "d.json"
    assert desktop_session.write(_context(monkeypatch, who=None), path)
    assert desktop_session.read(path)["token"] is None
    assert not desktop_session.write(_context(monkeypatch, running=False), tmp_path / "e.json")
    assert not (tmp_path / "e.json").exists()


def test_the_front_end_address_signs_in_only_with_a_token():
    assert desktop_session.front_end_url({"url": "http://127.0.0.1:8765/", "token": "t"}) == \
        "http://127.0.0.1:8765/web/#token=t"
    assert desktop_session.front_end_url({"url": "http://127.0.0.1:8765", "token": None}) == "http://127.0.0.1:8765/web/"


def test_without_the_setting_nothing_is_written(monkeypatch):
    monkeypatch.delenv(desktop_session.ENV, raising=False)
    assert desktop_session.path_from_env() is None


def test_the_shell_opens_her_when_she_answers_waits_then_shows_the_recovery_page():
    session = {"url": "http://127.0.0.1:8765", "token": "t"}
    assert os_shell.step(session, lambda url: True, now=1, deadline=30) == ("open", "http://127.0.0.1:8765/web/#token=t")
    assert os_shell.step(session, lambda url: False, now=1, deadline=30) == ("wait", None)
    assert os_shell.step(None, lambda url: True, now=1, deadline=30) == ("wait", None)
    assert os_shell.step(None, lambda url: True, now=31, deadline=30) == ("recover", None)


def test_the_recovery_page_offers_four_ways_on_and_only_its_own_links_act():
    page = os_shell.recovery_page("Her runtime didn't start <in time>.")
    assert all(f"mia-shell:{a}" in page for a in os_shell.ACTIONS) and "&lt;in time&gt;" in page
    assert os_shell.action_for("mia-shell:terminal") == "terminal"
    assert os_shell.action_for("mia-shell:rm -rf") is None and os_shell.action_for("https://example.com/") is None


def test_the_image_carries_the_session_entry_its_scripts_and_the_runtimes_setting():
    containerfile = (ROOT / "os" / "Containerfile").read_text(encoding="utf-8")
    assert "/usr/share/wayland-sessions/mia.desktop" in containerfile
    assert "chmod 755 /usr/lib/mia/os/files/mia-session /usr/lib/mia/os/files/mia-shell" in containerfile
    entry = (ROOT / "os" / "files" / "mia.desktop").read_text(encoding="utf-8")
    assert "Exec=/usr/lib/mia/os/files/mia-session" in entry and "Type=Application" in entry
    session = (ROOT / "os" / "files" / "mia-session").read_text(encoding="utf-8")
    assert "systemctl --user enable mia-runtime" in session
    assert "kwin_wayland" in session and "--exit-with-session=/usr/lib/mia/os/files/mia-shell" in session
    unit = (ROOT / "os" / "files" / "mia-runtime.service").read_text(encoding="utf-8")
    assert "Environment=MIA_DESKTOP_SESSION_FILE=%t/mia/desktop.json" in unit
    shell = (ROOT / "os" / "files" / "mia-shell").read_text(encoding="utf-8")
    assert "Environment=MIA_HOME=%h/.local/share/mia" in unit  # the shell's home is the runtime's (the image is read-only)
    assert 'export MIA_HOME="${MIA_HOME:-$HOME/.local/share/mia}"' in shell
    vm = (ROOT / ".github" / "workflows" / "mia-os-vm.yml").read_text(encoding="utf-8")
    assert "kwin_wayland --virtual" in vm and "showing: front end" in vm and "showing: recovery" in vm
