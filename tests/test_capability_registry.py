"""
tests.test_capability_registry
================================

The capability truth registry (WP-08, DEC-0220, REQ-SLF-003/004/005): one record per capability joining its owner,
needs, operations, devices, state, verification, last success and failure, limits and evidence; states decided from
evidence only, degraded and unverified among them; every change of state kept with what caused it; and no way to write
a state but rebuilding it from its sources.
"""
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import capability_registry as reg

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def kept(tmp_path, monkeypatch):
    """The registry's kept states in the test's own folder."""
    monkeypatch.setattr(reg, "_DATA_DIR", tmp_path)
    return tmp_path / reg.FILE_NAME


def test_every_app_has_one_record_joining_everything_said_about_it(kept):
    """REQ-SLF-003: each record has its owner, needs, operations, devices, state, verification, last success and
    failure, limits and evidence, and its state is one of the model's."""
    from core import app_registry

    built = reg.records(None)
    ids = [r["id"] for r in built if ":" not in r["id"]]
    assert sorted(ids) == sorted(app_registry.load().manifests)
    for r in built:
        assert {"owner", "needs", "operations", "devices", "state", "evidence", "confidence", "verification",
                "last_success", "last_failure", "limits"} <= set(r)
        assert r["state"] in reg.STATES and r["evidence"]


def test_the_state_comes_from_evidence_and_says_which():
    """REQ-SLF-005: degraded while the model is offline for one used by words; unverified with no test or use; a recent
    failure with no use since is malfunctioning; each with its evidence."""
    ok = {"status": "implemented", "why": "built and working"}
    assert reg._decide(ok, ["test_x.py"], "2026-11-20T10:00:00+00:00", None, True, False)[0] == "working"
    state, evidence, confidence = reg._decide(ok, [], None, None, True, False)
    assert state == "unverified" and confidence == "low" and any("no test covers it" in e for e in evidence)
    state, evidence, _ = reg._decide(ok, ["test_x.py"], None, None, True, True)
    assert state == "degraded" and any("model server" in e for e in evidence)
    assert reg._decide(ok, ["test_x.py"], None, None, False, True)[0] == "working"  # no words needed: not degraded
    state, evidence, confidence = reg._decide(ok, ["test_x.py"], "2026-11-01T00:00:00+00:00",
                                              "2026-11-20T00:00:00+00:00", True, False)
    assert state == "malfunctioning" and confidence == "inferred"
    assert reg._decide(ok, ["t.py"], "2026-11-21T00:00:00+00:00", "2026-11-20T00:00:00+00:00", True, False)[0] == "working"
    assert reg._decide({"status": "partial", "why": "not by voice yet"}, ["t.py"], None, None, True, False)[0] == "partial"


def test_tests_cover_a_capability_by_its_name_or_its_operations():
    """A test file named exactly after the app, or one naming one of its tools or action kinds in quotes, covers it;
    one whose name only starts like the app's doesn't."""
    index = {"test_greenhouse.py": "", "test_greenhouse_x.py": "", "test_other.py": 'propose(context, "batch.add")',
             "test_none.py": "batch.add"}
    assert reg.covering_tests("greenhouse", ["batch.add"], index) == ["test_greenhouse.py", "test_other.py"]
    # a file whose name only starts like the app's isn't its (Fable's review, 2026-11-22)


def test_last_success_and_failure_come_from_the_traces_and_the_fix_it_log():
    """The last turn that called one of its tools, and the last tool error of one of them."""
    now = reg._now()
    recent = (now.replace(microsecond=0)).isoformat()
    traces = SimpleNamespace(recent=lambda n: [{"at": recent, "tools_called": ["get_homestead_next_step"]}])
    failures = SimpleNamespace(events=lambda days: [{"kind": "tool_error", "tool": "get_homestead_next_step", "at": recent},
                                                    {"kind": "tool_error", "tool": "other", "at": recent}])
    used, failed = reg._use(SimpleNamespace(traces=traces, failures=failures), {"get_homestead_next_step"}, 30)
    assert used == recent and failed == recent


def test_a_change_of_state_is_kept_with_what_caused_it(kept, monkeypatch):
    """The first rebuild notes no change; a later one that finds a different state keeps it with its evidence; one that
    finds nothing new writes nothing (so the pages aren't woken for nothing)."""
    first = reg.rebuild(None)
    assert first["changes"] == [] and kept.exists()
    before = kept.stat().st_mtime_ns
    assert reg.rebuild(None)["changes"] == [] and kept.stat().st_mtime_ns == before
    real = reg._decide
    monkeypatch.setattr(reg, "_decide", lambda *a: ("malfunctioning", ["a tool failed on 2026-11-22"], "inferred")
                        if a[0].get("status") and a[1] is not None and "test_greenhouse" in " ".join(a[1]) else real(*a))
    changed = reg.rebuild(None)["changes"]
    assert changed and all(c["to"] == "malfunctioning" and c["because"] == ["a tool failed on 2026-11-22"] for c in changed)
    assert reg.changes()[0]["id"] == changed[-1]["id"]


def test_nothing_but_the_rebuild_writes_a_state():
    """REQ-SLF-004: no other module names the registry's file (but the retention list), no tool or action writes it, and its only write is in
    rebuild()."""
    for path in list((ROOT / "core").glob("*.py")) + list((ROOT / "server").glob("*.py")):
        if path.name in ("capability_registry.py", "retention.py"):  # retention lists every file by name
            continue
        assert reg.FILE_NAME not in path.read_text(encoding="utf-8"), path.name
    source = (ROOT / "core" / "capability_registry.py").read_text(encoding="utf-8")
    writes = [m.start() for m in re.finditer(r"atomic_write_text\(|write_text\(|write_bytes\(", source)]
    assert len(writes) == 1 and source[:writes[0]].rsplit("\ndef ", 1)[1].startswith("rebuild(")
    from core.actions import ACTION_TYPES

    assert not [k for k in ACTION_TYPES if "capabilit" in k]


def test_the_diagnostics_page_shows_what_she_can_do(kept):
    """The page's data carries the registry's summary, and its panel draws it."""
    from core.diagnostics import _capabilities

    summary = _capabilities(None)
    assert set(summary) == {"counts", "notable", "changes"} and set(summary["counts"]) == set(reg.STATES)
    page = (ROOT / "web" / "diagnostics.js").read_text(encoding="utf-8")
    assert "capabilitiesPanel(data.capabilities)" in page
