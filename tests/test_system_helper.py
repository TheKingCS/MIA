"""
tests.test_system_helper
==========================

FW-06 (PoC 5; DEC-0194, REQ-ARC-010, REQ-AGT-024, REQ-SEC-022): MIA changes the system only through her helper's three
fixed operations, each confirmed twice (her card, then his password in polkit's dialog). Checked here, on any
machine: the helper's own rules refuse anything but its operations and their listed arguments; MIA's side builds only
those calls and runs no shell; both sides hold the same lists; each kind needs his approval and reaches the system;
the policy asks his password every time; only root owns the name; it starts on demand and leaves when idle; the image
installs it all; and her session runs the agent that shows the dialog. The VM test (mia-os-vm.yml) calls it for real.
"""
import importlib.machinery
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import system_helper as client
from core.actions import ACTION_TYPES, ActionError, Refused, Unavailable

ROOT = Path(__file__).resolve().parent.parent
FILES = ROOT / "os" / "files"


def _helper():
    """The helper script as a module (its D-Bus part is only imported when it runs)."""
    loader = importlib.machinery.SourceFileLoader("mia_system_helper", str(FILES / "mia-system-helper"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_the_helper_does_only_its_three_operations_with_only_their_listed_arguments():
    """A8: anything else is refused by the helper's own rules, before polkit is asked."""
    helper = _helper()
    assert helper.check("RestartUnit", ("ollama.service",)) == "org.mia.system1.restart-unit"
    assert helper.check("Power", ("reboot",)) == "org.mia.system1.power"
    assert helper.check("ApplyUpdate", ()) == "org.mia.system1.apply-update"
    for method, args in [("RestartUnit", ("sshd.service",)), ("RestartUnit", ("ollama.service; rm -rf /",)),
                         ("Power", ("halt",)), ("Power", ()), ("ApplyUpdate", ("now",)), ("Format", ("x",)),
                         ("RestartUnit", (1,))]:
        with pytest.raises(helper.Refused):
            helper.check(method, args)
    assert helper.staged('{"status": {"staged": {"image": "x"}}}') and not helper.staged('{"status": {"staged": null}}')
    assert not helper.staged("not json")


def test_mias_side_builds_only_those_calls_and_runs_no_shell():
    """The gdbus command is a list of fixed words with the argument as a D-Bus string; anything else never runs."""
    assert client.argv("RestartUnit", "ollama.service")[-1] == "'ollama.service'"
    assert client.argv("ApplyUpdate")[:3] == ["gdbus", "call", "--system"]
    for method, args in [("RestartUnit", ("sshd.service",)), ("Power", ("halt",)), ("ApplyUpdate", ("x",)),
                         ("Format", ())]:
        with pytest.raises(ValueError):
            client.argv(method, *args)
    source = (ROOT / "core" / "system_helper.py").read_text(encoding="utf-8")
    assert "shell=True" not in source and "os.system" not in source


def test_both_sides_hold_the_same_lists():
    """The units and power words MIA asks for are exactly those the helper allows."""
    helper = _helper()
    assert set(helper.ALLOWED_UNITS) == set(client.ALLOWED_UNITS) and set(helper.POWER) == set(client.POWER)
    assert set(helper.OPERATIONS) == {"ApplyUpdate", "RestartUnit", "Power"}


def test_a_refusal_or_no_helper_is_said_and_a_done_call_says_what_it_did(monkeypatch):
    """Refused from the dialog or the helper's rules; Unavailable off MIA OS or when it can't be reached."""
    monkeypatch.setattr(client.sys, "platform", "linux")
    no = lambda argv, **kw: SimpleNamespace(returncode=1, stdout="", stderr="GDBus.Error:org.mia.System1.Error.Refused: not authorised")  # noqa: E731
    with pytest.raises(Refused):
        client.call("RestartUnit", "ollama.service", run=no)
    gone = lambda argv, **kw: SimpleNamespace(returncode=1, stdout="", stderr="The name org.mia.System1 was not provided")  # noqa: E731
    with pytest.raises(Unavailable):
        client.call("Power", "reboot", run=gone)
    done = lambda argv, **kw: SimpleNamespace(returncode=0, stdout="('restarted ollama.service',)\n", stderr="")  # noqa: E731
    assert client.call("RestartUnit", "ollama.service", run=done) == "restarted ollama.service"
    monkeypatch.setattr(client.sys, "platform", "win32")
    with pytest.raises(Unavailable):
        client.call("ApplyUpdate", run=done)


def test_each_kind_needs_his_yes_reaches_the_system_and_checks_its_arguments():
    """act_with_approval in Settings' manifest; declared as reaching the system; a unit off the list can't be proposed."""
    from core.action_effects import effect_of

    tiers = json.loads((ROOT / "apps" / "settings" / "manifest.json").read_text(encoding="utf-8"))["capabilities"]["tiers"]
    for kind in client.SYSTEM_ACTIONS:
        assert kind in ACTION_TYPES and tiers[kind] == "act_with_approval" and effect_of(kind)[0] == "system"
    assert effect_of("system.power")[1] == "irreversible"
    with pytest.raises(ActionError):
        ACTION_TYPES["system.restart_service"].describe(None, {"unit": "sshd.service"})
    assert "password" in ACTION_TYPES["system.power"].describe(None, {"what": "reboot"})


def test_the_policy_asks_his_password_every_time_and_no_one_away_may():
    """Every operation's action: auth_self while at the desk (never kept), no for anyone else."""
    tree = ET.parse(FILES / "org.mia.system1.policy").getroot()
    actions = {a.get("id"): a for a in tree.iter("action")}
    assert set(actions) == {"org.mia.system1." + v[0] for v in _helper().OPERATIONS.values()}
    for action in actions.values():
        d = action.find("defaults")
        assert (d.findtext("allow_any"), d.findtext("allow_inactive"), d.findtext("allow_active")) == ("no", "no", "auth_self")


def test_only_root_owns_the_name_it_starts_on_demand_and_the_image_installs_it_all():
    """The bus policy, the activation file, the unit, the Containerfile's copies, and her session's polkit agent."""
    conf = (FILES / "org.mia.System1.conf").read_text(encoding="utf-8")
    assert re.search(r'<policy user="root">\s*<allow own="org.mia.System1"/>', conf) and conf.count("allow own") == 1
    service = (FILES / "org.mia.System1.service").read_text(encoding="utf-8")
    assert "SystemdService=mia-system-helper.service" in service and "User=root" in service
    unit = (FILES / "mia-system-helper.service").read_text(encoding="utf-8")
    assert "Type=dbus" in unit and "BusName=org.mia.System1" in unit and "[Install]" not in unit  # never enabled: on demand
    containerfile = (ROOT / "os" / "Containerfile").read_text(encoding="utf-8")
    for name in ("mia-system-helper", "org.mia.system1.policy", "org.mia.System1.conf", "org.mia.System1.service",
                 "mia-system-helper.service"):
        assert f"COPY os/files/{name} " in containerfile, name
    assert "polkit-kde-authentication-agent-1" in (FILES / "mia-session").read_text(encoding="utf-8")
    assert _helper().IDLE_SECONDS <= 120
