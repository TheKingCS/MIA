"""Diagnostic procedures (ACAF step 4, T-0040, core/diagnostics.py): check-ups written as specs over what inspection's
PASSIVE methods read; checked before they run, so they can only read and compare; what couldn't be read said as such; and the hardware list, only what was read."""

from types import SimpleNamespace

import pytest

from core import diagnostics as d
from core.inspection import Evidence


def fake_inspect(facts):
    return lambda context, subject: SimpleNamespace(evidence=[Evidence(k, v, "m", "s") for k, v in facts.items()])


def test_the_built_in_check_ups_are_valid():
    for key, spec in d.PROCEDURES.items():
        assert d.check(spec) == [], key


def test_a_spec_can_only_read_and_compare():
    bad = {"kind": "diagnostic", "title": "x", "subject": "the_network", "checks": [
        {"fact": "passwords.wifi", "op": "=~", "value": 1, "say": ""}, {"fact": "disk.C.free_gb", "op": ">", "value": "lots",
                                                                       "say": "x"}]}
    problems = " ".join(d.check(bad))
    assert "subject" in problems and "isn't something inspection reads" in problems and "comparison" in problems
    assert "needs a number" in problems and "say what it means" in problems
    with pytest.raises(d.DiagnosticError, match="can't run"):
        d.run(None, bad, inspect=fake_inspect({}))


def test_a_check_up_in_plain_lines():
    facts = {"disk.C.free_gb": 12.5, "disk.D.free_gb": 400.0, "memory.use_percent": 71.0, "cpu.use_percent": 5.0,
             "security.firewall": "on for every profile"}
    out = d.run(None, "pc_ready", inspect=fake_inspect(facts))
    assert out["lines"][0] == "Is the PC ready for MIA?: 1 to look at (3 checks passed)."
    assert out["lines"][1] == "- Drive C has 12.5 GB free: under 20 GB, models and updates run out of room."
    assert "Couldn't read: ai.model" in out["lines"][2]  # unread is never a pass
    every = d.run(None, "big_download", inspect=fake_inspect(facts))
    assert every["failed"] == ["Drive C has 12.5 GB free."] and every["passed"] == 1  # one line per drive


def test_asked_for_by_name(monkeypatch):
    monkeypatch.setattr(d, "run", lambda context, key: {"lines": [f"ran {key}"]})
    assert d.reply(None, "check my PC") == "ran pc_ready"
    assert d.reply(None, "can you check the network?") == "ran network"
    assert d.reply(None, "is there room for a big download?") == "ran big_download"
    assert d.reply(None, "check my email") is None and d.reply(None, "what's the weather") is None



def test_the_screen_runs_every_check_up_over_one_inspection():
    from types import SimpleNamespace

    from core import diagnostics

    calls = []
    facts = [SimpleNamespace(fact="disk.C.free_gb", value=10.0), SimpleNamespace(fact="memory.use_percent", value=40),
             SimpleNamespace(fact="ai.model", value="qwen")]

    def inspect(context, subject):
        calls.append(subject)
        return SimpleNamespace(evidence=facts)

    found = {c["id"]: c for c in diagnostics.screen(None, inspect=inspect)["checks"]}
    assert calls == ["this_computer"] and set(found) == set(diagnostics.PROCEDURES)
    assert not found["pc_ready"]["ok"] and "Drive C has 10 GB free" in found["pc_ready"]["failed"][0]
    assert "cpu.use_percent" in found["pc_ready"]["unknown"]


def test_the_hardware_list_says_only_what_was_read():
    rows = d.hardware({"computer.name": "shop-pc", "os.machine": "x86_64", "cpu.model": "Ryzen 7", "cpu.cores_physical": 8,
                       "cpu.threads": 16, "memory.total_gb": 31.9, "memory.use_percent": 40.0, "disk.C.size_gb": 953.9,
                       "disk.C.free_gb": 412.0, "disk.C.use_percent": 56.8, "disk./snap.size_gb": 0.1,
                       "network.Wi-Fi.ipv4": "192.168.1.20", "python.version": "3.12.4"})
    by = {r["name"]: r for r in rows}
    assert by["Processor"] == {"name": "Processor", "value": "Ryzen 7", "note": "8 cores · 16 threads"}
    assert by["Drive C"]["note"] == "412 GB free · 56.8% full" and "Drive /snap" not in by  # a tiny mount isn't a drive
    assert by["Memory"]["value"] == "31.9 GB" and by["Network Wi-Fi"]["value"] == "192.168.1.20" and "Started" not in by
    assert d.hardware({}) == []
