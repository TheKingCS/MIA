"""Universal Inspection (DEC-0056, core/inspection.py): every finding with
its source, time and confidence; agreement confirms, disagreement is kept;
what couldn't be determined says why; only passive methods run unasked;
the repository subject finds where her docs disagree with her repository."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import core.inspection as ins


def ev(fact, value, method, source, confidence=ins.PROBABLE):
    """One piece of evidence (probable unless told otherwise)."""
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
    """Asking MIA to inspect herself or this computer reaches the inspection tool; asking which model she runs still reaches the model tool."""
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


def _repo(root):
    """A tiny repository whose docs disagree with it in one of each way, and agree in the ways that aren't drift."""
    (root / "core").mkdir()
    (root / "core" / "talk.py").write_text('"""Talk."""\n', encoding="utf-8")
    (root / "docs").mkdir()
    (root / "CLAUDE.md").write_text("See `core/talk.py` and `core/talk.pre_turn` and `core/gone.py`.\n", encoding="utf-8")
    (root / "docs" / "GUIDE.md").write_text("Run `tools/missing_tool.py`; never `work/STOP`.\n", encoding="utf-8")
    (root / "docs" / "NEW_PROPOSAL.md").write_text("Will build `core/someday.py`.\n", encoding="utf-8")
    (root / "docs" / "DECISIONS.md").write_text(
        "# Decisions\n\n### DEC-0001 Built\n- Status: APPROVED\nBuilt: `core/talk.py` and `core/lost.py`.\n\n"
        "### DEC-0002 Not yet\n- Status: APPROVED\nNothing built yet: `core/later.py`.\n\n"
        "### DEC-0003 Proposed\n- Status: PROPOSED\nBuilt `core/maybe.py`.\n", encoding="utf-8")
    (root / "requirements.txt").write_text("pytest>=7\nno-such-package-mia-test==1.0  # nope\n", encoding="utf-8")


def test_the_repository_subject_finds_where_her_docs_disagree_with_it(tmp_path):
    """A missing named file, a decision recorded as built naming a missing file, and a requirement not installed are
    found; a dotted reference to a real module, a proposal's future file, an on-demand file, a decision not yet built
    and a proposed decision aren't."""
    _repo(tmp_path)
    found = ins.repository_findings(tmp_path)
    got = {(f["kind"], f["name"]) for f in found}
    assert got == {("doc_path_missing", "core/gone.py"), ("doc_path_missing", "tools/missing_tool.py"),
                   ("built_file_missing", "DEC-0001"), ("requirement_missing", "no-such-package-mia-test")}
    assert all({"id", "kind", "name", "detail", "file", "line"} <= set(f) for f in found)
    assert next(f for f in found if f["name"] == "tools/missing_tool.py")["file"] == "docs/GUIDE.md"


def test_the_repository_report_says_how_many_places_disagree(tmp_path, monkeypatch):
    """Inspecting the repository gives a count, the places as problems, and a summary in words."""
    _repo(tmp_path)
    monkeypatch.setattr(ins, "ROOT", tmp_path)
    monkeypatch.setattr(ins, "_DIR", tmp_path / "inspections")
    r = ins.inspect(SimpleNamespace(), "repository")
    assert next(e.value for e in r.evidence if e.fact == "repository.findings") == 4
    assert "4 places where my docs and my repository disagree." in ins.summary(r)
    assert any("core/gone.py" in p for p in r.problems)
    (tmp_path / "requirements.txt").unlink()
    for name in ("core/gone.py", "tools/missing_tool.py", "core/lost.py"):
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).write_text("", encoding="utf-8")
    assert "My docs and my repository agree." in ins.summary(ins.inspect(SimpleNamespace(), "repository"))
