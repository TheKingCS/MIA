"""Universal Inspection (DEC-0056, core/inspection.py): every finding with
its source, time and confidence; agreement confirms, disagreement is kept;
what couldn't be determined says why; only passive methods run unasked."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import core.inspection as ins


def ev(fact, value, method, source, confidence=ins.PROBABLE):
    return ins.Evidence(fact, value, method, source, confidence)


def test_agreement_confirms_and_disagreement_is_kept():
    found, contradictions = ins.correlate([
        ev("cpu.model", "Ryzen 9", "a", "Windows"), ev("cpu.model", "ryzen 9", "b", "the label"),
        ev("gpu.0.name", "RX 7900", "a", "Windows"), ev("gpu.0.name", "RX 6800", "b", "the box")])
    cpu = [e for e in found if e.fact == "cpu.model"]
    assert len(cpu) == 1 and cpu[0].confidence == ins.CONFIRMED and "agreed by" in cpu[0].note
    assert contradictions == [{"fact": "gpu.0.name", "values": [("Windows", "RX 7900"), ("the box", "RX 6800")]}]
    assert len([e for e in found if e.fact == "gpu.0.name"]) == 2  # both kept, never one silently picked


def test_problems_worth_a_look():
    said = ins.problems([ev("disk.C.use_percent", 95, "d", "psutil"), ev("memory.use_percent", 40, "m", "psutil"),
                         ev("security.firewall", "profiles: ON, OFF", "s", "netsh"),
                         ev("decisions.waiting", ["DEC-0058"], "x", "docs")])
    assert said == ["Drive C is 95% full.", "The firewall isn't on everywhere (profiles: ON, OFF).",
                    "1 decision wait on the owner: DEC-0058."]


def test_only_passive_methods_run_unasked(tmp_path, monkeypatch):
    monkeypatch.setattr(ins, "_DIR", tmp_path)
    ran = []
    probe = ins.Method("probe", ("this_computer",), "open ports", "a scan", ins.ACTIVE, lambda c: ran.append("probe"))
    look = ins.Method("look", ("this_computer",), "the name", "nothing", ins.PASSIVE,
                      lambda c: (ran.append("look") or [ev("computer.name", "box", "look", "os", ins.CONFIRMED)],
                                 [ins.Gap("Disk health", "needs admin", "look")]))
    broken = ins.Method("broken", ("this_computer",), "the GPU", "x", ins.PASSIVE, lambda c: 1 / 0)
    missing = ins.Method("missing", ("this_computer",), "x", "a camera", ins.PASSIVE, lambda c: ([], []), lambda c: False)
    monkeypatch.setattr(ins, "METHODS", (probe, look, broken, missing))
    r = ins.inspect(SimpleNamespace(), "this_computer")
    assert ran == ["look"]
    assert ("probe", "active: asked first") in r.methods_skipped
    assert ("missing", "not available here (needs a camera)") in r.methods_skipped
    assert {g.what for g in r.gaps} == {"Disk health", "the GPU"}  # a failure is a gap, said plainly
    assert ins.latest("this_computer")["evidence"][0]["value"] == "box"  # kept for follow-ups
    with pytest.raises(ValueError):
        ins.inspect(SimpleNamespace(), "the neighbour's wifi")


def test_stale_facts_are_noticed():
    old = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    later = (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds")
    report = {"evidence": [{"fact": "cpu.use_percent", "recheck_after": old}, {"fact": "os.name", "recheck_after": later}]}
    assert ins.stale(report) == ["cpu.use_percent"]


def test_the_report_says_unknown_is_not_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(ins, "_DIR", tmp_path)
    r = ins.Report("this_computer", "2026-10-30T10:00:00", evidence=[ins.Evidence("os.name", "Windows", "os", "the OS")],
                   gaps=[ins.Gap("CPU temperature", "no sensor answered", "health")])
    text = ins.report_text(r)
    assert "[CONFIRMED] Operating system: Windows  (the OS)" in text
    assert "UNKNOWN (not determined, which doesn't mean absent)" in text and "CPU temperature: no sensor answered" in text


def test_the_words_pick_the_subject():
    from core.assistant_self_actions import inspection_subject

    assert inspection_subject("inspect yourself") == "mia" and inspection_subject("run a self-check") == "mia"
    assert inspection_subject("inspect this computer") == "this_computer"


def test_asking_reaches_it():
    from tests.assistant_registry import build_desktop_registry

    r = build_desktop_registry()
    for q in ("Inspect this computer", "MIA, inspect yourself", "run a self-check"):
        assert r.direct_lookup(q + "?") is not None and r.direct_lookup(q + "?").name == "get_inspection", q
    assert r.direct_lookup("What model are you running on?").name == "get_model_info"  # unchanged


def test_active_scans_stay_on_your_own_network():
    from core.port_scanner import own_network

    assert own_network("127.0.0.1") and own_network("192.168.1.1") and own_network("10.0.0.5")
    assert own_network("100.80.159.25")  # a Tailscale device
    assert not own_network("8.8.8.8") and not own_network("not a host at all")
