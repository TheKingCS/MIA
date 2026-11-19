"""Tests for FW-04's readiness and watchdog (core/sd_notify.py, core/runtime.py), the self-test's refusal of a folder
with anything in it (core/self_test.py), and the image's health checks and night updates (os/files/)."""
import os
import socket
from pathlib import Path

import pytest

from core import sd_notify, self_test

ROOT = Path(__file__).resolve().parent.parent


def test_the_readiness_levels_follow_what_is_running():
    """Started, core, models, all: the phone server only counts when it's switched on."""
    assert sd_notify.READINESS == ("started", "core", "models", "all")
    assert sd_notify.level(False, True, False, False) == "started"
    assert sd_notify.level(True, False, True, True) == "core"
    assert sd_notify.level(True, True, True, False) == "models"
    assert sd_notify.level(True, True, True, True) == "all" == sd_notify.level(True, True, False, False)


def test_without_a_notify_socket_nothing_is_sent_and_no_watchdog(monkeypatch):
    """Outside a notify service (Windows, a terminal) every call does nothing."""
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    monkeypatch.delenv("WATCHDOG_USEC", raising=False)
    assert sd_notify.notify("READY=1") is False and sd_notify.watchdog_seconds() == 0.0


def test_the_watchdog_is_pinged_at_half_its_timeout_and_only_for_this_process(monkeypatch):
    """WATCHDOG_USEC of 120 s: every 60 s; a watchdog meant for another process is none."""
    monkeypatch.setenv("WATCHDOG_USEC", "120000000")
    monkeypatch.setenv("WATCHDOG_PID", str(os.getpid()))
    assert sd_notify.watchdog_seconds() == 60.0
    monkeypatch.setenv("WATCHDOG_PID", "1")
    assert sd_notify.watchdog_seconds() == 0.0


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX") or os.name == "nt", reason="a Unix datagram socket")
def test_ready_reaches_a_fake_systemd_socket(tmp_path, monkeypatch):
    """The lines go as one datagram to NOTIFY_SOCKET."""
    where = str(tmp_path / "notify")
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.bind(where)
        monkeypatch.setenv("NOTIFY_SOCKET", where)
        assert sd_notify.notify("READY=1", "STATUS=MIA is up (core)")
        assert sock.recv(256) == b"READY=1\nSTATUS=MIA is up (core)"


def test_the_runtime_pings_only_while_its_schedule_is_alive(monkeypatch):
    """The main loop's ping stops when the schedule thread has died, so systemd restarts a stuck MIA."""
    from core.runtime import Runtime

    sent = []
    monkeypatch.setattr(sd_notify, "notify", lambda *lines: sent.extend(lines) or True)
    monkeypatch.setattr(sd_notify, "watchdog_seconds", lambda: 60.0)
    fake = Runtime.__new__(Runtime)
    fake.readiness = lambda: "core"
    fake._thread = type("T", (), {"is_alive": lambda self: True})()
    state = {"said": 0.0}
    Runtime._tell_systemd(fake, 100.0, state)
    assert "WATCHDOG=1" in sent and "STATUS=MIA is up (core)" in sent
    sent.clear()
    fake._thread = type("T", (), {"is_alive": lambda self: False})()
    Runtime._tell_systemd(fake, 200.0, state)
    assert "WATCHDOG=1" not in sent


def test_the_self_test_refuses_a_folder_with_anything_in_it(tmp_path):
    """It runs only on an empty folder, so it can never open someone's stores."""
    (tmp_path / "data").mkdir()
    assert self_test.main(["--home", str(tmp_path)]) == 2


def test_the_image_checks_health_after_boot_and_updates_at_night():
    """Required checks (login screen, homes, disk, the self-test) roll back; wanted ones (network, model server) are
    logged;
    updates stage at night and apply at an idle restart after a snapshot; the runtime is a notify service."""
    files = ROOT / "os" / "files"
    required = sorted(p.name for p in (files / "greenboot" / "required.d").iterdir())
    wanted = sorted(p.name for p in (files / "greenboot" / "wanted.d").iterdir())
    assert required == ["40-mia-login-manager.sh", "41-mia-home.sh", "42-mia-disk-space.sh", "43-mia-self-test.sh"]
    assert wanted == ["50-mia-network.sh", "51-mia-model-server.sh"]
    selftest = (files / "greenboot" / "required.d" / "43-mia-self-test.sh").read_text(encoding="utf-8")
    assert "--reuid=65534" in selftest and "--home" in selftest  # as nobody, on a fresh folder
    vm = (ROOT / ".github" / "workflows" / "mia-os-vm.yml").read_text(encoding="utf-8")
    assert "BREAK=selftest" in vm and "BREAK=login" in vm and "mia-update-stage.service" in vm
    apply = (files / "mia-update-apply").read_text(encoding="utf-8")
    assert apply.index("btrfs subvolume snapshot") < apply.index("systemctl reboot") and "IdleHint" in apply
    containerfile = (ROOT / "os" / "Containerfile").read_text(encoding="utf-8")
    assert "greenboot" in containerfile and "mia-update-stage.timer mia-update-apply.timer" in containerfile
    for unit in (files / "mia-runtime.service", ROOT / "deploy" / "mia-runtime.service"):
        text = unit.read_text(encoding="utf-8")
        assert "Type=notify" in text and "WatchdogSec=" in text
