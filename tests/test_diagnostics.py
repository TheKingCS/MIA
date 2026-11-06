"""Diagnostic procedures (ACAF step 4, T-0040, core/diagnostics.py): check-ups written as specs over what inspection's
PASSIVE methods read; checked before they run, so they can only read and compare; what couldn't be read said as such."""

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
