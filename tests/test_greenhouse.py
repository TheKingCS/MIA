"""
tests.test_greenhouse
=======================

Handing the greenhouse to MIA and setting up its hardware (DEC-0150): core/greenhouse_link.py watches every sensor the
node reports, raises its new alerts once each (critical urgent, warning timely), keeps its readings in the grow lab,
reads only from the person's own network, and knows the node from its own documents; core/greenhouse_provision.py
finds the ESP32, flashes it and pushes the node to the Pi only on a yes, with preloaded configs that keep every comment
and never a password; the node's export server serves its two files and nothing else.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import greenhouse_link as gl
from core import greenhouse_provision as gp
from core.communication_gate import TIMELY, URGENT

NOW = datetime(2026, 11, 20, 9, 0)
STATE = {
    "cells": [{"id": 2, "name": "Pilot", "readings": [
        {"type": "ph", "unit": "", "value": 6.9, "timestamp": "2026-11-20T08:58:00", "is_stale": False},
        {"type": "ec", "unit": "uS/cm", "value": 1100, "timestamp": "2026-11-20T08:58:00", "is_stale": False},
        {"type": "temp_water", "unit": "F", "value": 74.2, "timestamp": "2026-11-20T08:58:00", "is_stale": False},
        {"type": "do", "unit": "mg/L", "value": None, "timestamp": "", "is_stale": True}]}],
    "alerts": [{"id": 7, "severity": "critical", "source": "pilot_cell", "message": "DO probe not reporting",
                "resolved": 0},
               {"id": 8, "severity": "warning", "source": "pilot_cell", "message": "pH drifting high", "resolved": 0},
               {"id": 9, "severity": "info", "source": "pilot_cell", "message": "dosed", "resolved": 0}],
}


class Logger:
    """A stand-in Data Logger that keeps what it's given."""

    def __init__(self):
        """No readings yet."""
        self.got = []

    def add_reading(self, series, value, unit="", note="", **_kw):
        """Keeps one reading."""
        self.got.append((series, value, unit))


@pytest.fixture
def world(tmp_path):
    """A context with the link (in a temp folder), a stand-in Data Logger and a homestead watched folder."""
    folder = tmp_path / "snapshots"
    folder.mkdir()
    context = SimpleNamespace(data_logger=Logger(), homestead=SimpleNamespace(import_folder_path=lambda: folder))
    context.greenhouse_link = gl.GreenhouseLink(context, data_dir=tmp_path)
    context.folder = folder
    return context


def test_every_sensor_is_a_monitor_and_the_line_says_what_s_stale():
    """Monitors come from what the node reports; the status line names readings, alerts and the stale probe."""
    assert [(m["type"], m["stale"]) for m in gl.monitors(STATE)] == [("ph", False), ("ec", False),
                                                                     ("temp_water", False), ("do", True)]
    line = gl.status_line(STATE)
    assert line.startswith("Greenhouse: Pilot: ph 6.9, ec 1100 uS/cm, temp water 74.2 F")
    assert "1 critical, 1 warning" in line and "stale: Pilot do" in line


def test_new_alerts_reach_the_person_once_each_critical_urgent_warning_timely(world):
    """Critical first and urgent, the warning timely, info never; a second read raises nothing again."""
    link = world.greenhouse_link
    link.state = STATE
    first = gl.alert_candidates(link)
    assert [(c.urgency, c.message) for c in first] == [(URGENT, "pilot_cell: DO probe not reporting"),
                                                       (TIMELY, "pilot_cell: pH drifting high")]
    assert gl.alert_candidates(link) == []


def test_take_over_reads_the_node_on_the_own_network_and_says_what_she_watches(world):
    """An address on this computer is read; one out on the internet is refused; an unreachable one says so."""
    asked = []

    def get(url):
        """The node's export server."""
        asked.append(url)
        return json.dumps(STATE).encode("utf-8")

    said = gl.take_over(world, world.greenhouse_link, "http://127.0.0.1:8770", get)
    assert asked == ["http://127.0.0.1:8770/dashboard_state.json"]
    assert said.startswith("I'm watching the greenhouse now: 3 sensors across 1 cell (Pilot)")
    assert "Not reporting yet: Pilot do." in said and "safety MCU still do the controlling" in said
    world.greenhouse_link.url = "http://8.8.8.8:8770"
    with pytest.raises(gl.LinkError, match="own network"):
        gl.fetch(world, world.greenhouse_link, get)
    world.greenhouse_link.url = "http://127.0.0.1:8770"

    def down(url):
        """The node not answering."""
        raise OSError("refused")

    with pytest.raises(gl.LinkError, match="serve_exports.py"):
        gl.fetch(world, world.greenhouse_link, down)


def test_the_state_dropped_by_hand_is_read_too(world):
    """With no address, the dashboard_state.json dropped in the watched folder is the state."""
    (world.folder / "dashboard_state.json").write_text(json.dumps(STATE), encoding="utf-8")
    assert gl.fetch(world, world.greenhouse_link)["cells"][0]["name"] == "Pilot"


def test_the_loop_reads_every_few_minutes_and_keeps_fresh_readings_in_the_grow_lab(world):
    """Not taken over: nothing. Taken over: read, readings kept (EC in mS/cm, the stale DO not), alerts offered;
    again a minute later: not read; readings kept at most every half hour a sensor."""
    get = lambda url: json.dumps(STATE).encode("utf-8")  # noqa: E731
    link = world.greenhouse_link
    assert gl.tick(world, link, NOW, get) == []
    link.taken_over, link.url = True, "http://127.0.0.1:8770"
    offered = gl.tick(world, link, NOW, get)
    assert len(offered) == 2
    assert world.data_logger.got == [("grow:pilot:ph", 6.9, ""), ("grow:pilot:ec", 1.1, "mS/cm"),
                                     ("grow:pilot:water_temp", 74.2, "F")]
    assert gl.tick(world, link, NOW + timedelta(minutes=1), get) == [] and len(world.data_logger.got) == 3
    gl.tick(world, link, NOW + timedelta(minutes=10), get)
    assert len(world.data_logger.got) == 3  # read again, but each sensor was kept less than half an hour ago
    gl.tick(world, link, NOW + timedelta(minutes=40), get)
    assert len(world.data_logger.got) == 6


def test_she_knows_the_node_from_its_own_documents_and_the_words_reach_her(world):
    """The node's generated documents give its modules (each proven or not) and its parts; a question about the
    greenhouse's technology carries them; the phrases are answered in code."""
    know = gl.node_knowledge()
    assert len(know["modules"]) >= 10 and all("proven" in m for m in know["modules"]) and know["hardware"]
    block = gl.context_block(world, "what sensors can you connect to in the greenhouse?")
    assert block.startswith("The greenhouse node (MIA Homestead) declares these modules:") and "approval" in block
    assert gl.context_block(world, "what's for dinner") == ""
    assert "not watching the greenhouse yet" in gl.reply(world, "how's the greenhouse?")
    world.greenhouse_link.state = STATE
    world.greenhouse_link.taken_over = True
    assert gl.reply(world, "how's the greenhouse?").startswith("Greenhouse: Pilot")
    assert gl.reply(world, "what are you watching in the greenhouse").endswith("Pilot do (stale).")


def test_flashing_finds_the_esp32_and_waits_for_a_yes(world, monkeypatch):
    """The ESP32's USB chip picks its port; the plan says the command and the LED test; "yes, flash it" runs it,
    and a failed upload says so."""
    ports = [{"device": "COM3", "description": "Bluetooth link", "vid": None, "pid": None},
             {"device": "COM5", "description": "CP2102 USB to UART", "vid": 0x10C4, "pid": 0xEA60}]
    assert gp.likely_mcu(ports)["device"] == "COM5" and gp.likely_mcu(ports[:1])["device"] == "COM3"
    plan = gp.flash_plan(ports, ["pio"])
    assert plan["ok"] and plan["command"][:4] == ["pio", "run", "-t", "upload"] and plan["command"][-1] == "COM5"
    assert "LEDs in place of the relays" in plan["said"]
    assert not gp.flash_plan(ports, [])["ok"]  # no PlatformIO here
    ran = []
    monkeypatch.setattr(gp, "serial_ports", lambda: ports)
    monkeypatch.setattr(gp, "platformio", lambda: ["pio"])
    run = lambda cmd, timeout=0: ran.append(cmd) or (0, "SUCCESS")  # noqa: E731
    assert gp.reply(world, "flash the safety MCU", run).endswith("Say “yes, flash it” to go ahead.") and not ran
    assert gp.reply(world, "yes, flash it", run).startswith("Flashed the safety MCU on COM5") and len(ran) == 1
    assert "didn't finish" in gp.flash_mcu("COM5", lambda c, t=0: (1, "upload failed"), ["pio"])


def test_the_pi_gets_preloaded_configs_with_every_comment_and_never_a_password(tmp_path, monkeypatch):
    """Configs are the node's own templates with the known values set and every comment kept; the SMTP password
    stays empty; the Imager steps say the person types the Wi-Fi password; the key is made once."""
    template = "# where it is\nlatitude: null\nlongitude: null   # decimal degrees\n"
    assert gp.filled(template, {"latitude": 35.1, "longitude": -90.2}) == (
        "# where it is\nlatitude: 35.1\nlongitude: -90.2   # decimal degrees\n")
    monkeypatch.setattr(gp, "KEY", tmp_path / ".keys" / "node_key")

    def keygen(cmd, timeout=0):
        """Makes the key files ssh-keygen would."""
        Path(cmd[cmd.index("-f") + 1]).write_text("private", encoding="utf-8")
        Path(cmd[cmd.index("-f") + 1] + ".pub").write_text("ssh-ed25519 AAAA mia-greenhouse", encoding="utf-8")
        return 0, ""

    done = gp.prepare_pi({"latitude": 35.1, "longitude": -90.2, "primary_contact_email": "me@example.com"}, keygen,
                         bundle=tmp_path / "bundle")
    assert done["key"] == "ssh-ed25519 AAAA mia-greenhouse" and set(done["files"]) >= {"location.yaml",
                                                                                        "notifications.yaml"}
    notes = (tmp_path / "bundle" / "config" / "notifications.yaml").read_text(encoding="utf-8")
    assert 'primary_contact_email: "me@example.com"' in notes and 'smtp_password: ""' in notes
    assert "you type its password there, never MIA" in (tmp_path / "bundle" / "PI_SETUP.md").read_text(encoding="utf-8")


def test_pushing_to_the_pi_waits_for_a_yes_and_stops_at_the_first_failure(world, tmp_path, monkeypatch):
    """The commands pack the node without its database, copy it and the configs, and install it; "yes, push it"
    runs them in order; a failed step says which."""
    monkeypatch.setattr(gp, "KEY", tmp_path / "key")
    (tmp_path / "key").write_text("private", encoding="utf-8")
    monkeypatch.setattr(gp, "BUNDLE", tmp_path / "bundle")
    cmds = gp.push_commands("mia-greenhouse", "zac", tmp_path / "n.tgz", tmp_path / "key", tmp_path / "bundle")
    assert cmds[0][0] == "tar" and "--exclude=mia_homestead.db" in cmds[0] and "install_service.sh" in cmds[-1][-1]
    ran = []
    run = lambda cmd, timeout=0: ran.append(cmd[0]) or (0, "")  # noqa: E731
    assert "zac@mia-greenhouse" in gp.reply(world, "push the greenhouse to mia-greenhouse as zac", run) and not ran
    assert gp.reply(world, "yes, push it", run).startswith("The greenhouse node is on mia-greenhouse")
    assert ran == ["tar", "scp", "ssh", "scp", "ssh"]
    failing = lambda cmd, timeout=0: (1, "no route to host") if cmd[0] == "scp" else (0, "")  # noqa: E731
    assert gp.push_node("mia-greenhouse", "zac", failing).startswith("Stopped at copying it to the Pi")


def test_the_node_s_export_server_serves_its_two_files_and_nothing_else():
    """Only home_snapshot.json and dashboard_state.json, never the database or a config."""
    import importlib.util

    path = Path(__file__).resolve().parent.parent / "homestead" / "viewer" / "serve_exports.py"
    spec = importlib.util.spec_from_file_location("homestead_serve_exports", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.allowed("/dashboard_state.json") == "dashboard_state.json"
    assert module.allowed("/home_snapshot.json?t=1") == "home_snapshot.json"
    for bad in ("/../mia_homestead.db", "/config/notifications.yaml", "/", "/viewer/state.json"):
        assert module.allowed(bad) is None, bad
