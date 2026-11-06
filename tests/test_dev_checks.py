"""The development checks that need a real run (core/dev_checks.py, build plan step 2): the committed
code's suite against the known failures, reverts per merge, and the dependency audit; the loops that read
them are heavy, so the app's own check never runs them."""

from datetime import datetime, timezone

from core import dev_checks, loops


def test_failures_against_the_known_ones():
    c = dev_checks.compare(["tests/a.py::x", "tests/b.py::y"], {"tests/b.py::y": "flaky on CI", "tests/c.py::z": "old"})
    assert c == {"unexpected": ["tests/a.py::x"], "still_known": ["tests/b.py::y"], "stale": ["tests/c.py::z"]}


def test_the_suite_runs_once_per_commit(monkeypatch):
    monkeypatch.setattr(dev_checks, "_SUITES", {})
    monkeypatch.setattr(dev_checks, "known", lambda path=None: {})
    runs = []

    def run(where):
        runs.append(where)
        return {"summary": "1 failed, 10 passed in 12.5s", "failed": ["tests/a.py::x"], "finished": True}
    first = dev_checks.suite(run=run, head="abc1234567890")
    again = dev_checks.suite(run=run, head="abc1234567890")
    assert len(runs) == 1 and first is again
    assert first["unexpected"] == ["tests/a.py::x"] and first["seconds"] == 12.5 and first["commit"] == "abc1234567"


def test_reverts_per_merge():
    now = datetime(2026, 11, 6, tzinfo=timezone.utc)
    events = [{"at": "2026-11-03T21:40:20+00:00", "action": "approve", "task": "T-0019", "detail": "reverted: It broke"},
              {"at": "2026-11-06T01:44:37+00:00", "action": "approve", "task": "T-0019", "detail": "merged cfcd4f6"},
              {"at": "2026-09-01T00:00:00+00:00", "action": "approve", "task": "T-0001", "detail": "reverted: old"},
              {"at": "2026-11-05T00:00:00+00:00", "action": "review", "task": "T-0020", "detail": "merged? fine"},
              {"at": "2026-11-05T00:00:00+00:00", "action": "approve", "task": "T-0021"}]
    assert dev_checks.reverts(events, now=now) == {"merges": 2, "reverts": 1, "rate": 0.5, "reverted": ["T-0019"]}
    assert dev_checks.reverts([], now=now)["rate"] is None


def test_the_audit_sends_names_and_versions_only():
    sent = []

    def post(url, body):
        sent.append(body)
        return {"results": [{"vulns": [{"id": "GHSA-1"}, {"id": "PYSEC-2"}]}, {}]}
    v = dev_checks.vulnerable({"oldlib": "1.0", "fine": "2.0"}, post=post)
    assert v == {"checked": 2, "packages": {"oldlib": ["GHSA-1", "PYSEC-2"]}}
    assert sent[0]["queries"][0] == {"package": {"name": "oldlib", "ecosystem": "PyPI"}, "version": "1.0"}


def test_packages_behind_their_latest():
    latest = {"numpy": "2.3.0", "psutil": "7.0.0"}
    o = dev_checks.outdated(["numpy", "psutil", "missing"], {"numpy": "2.1.0", "psutil": "7.0.0"},
                            get=lambda url: {"info": {"version": latest[url.split("/")[-2]]}})
    assert o == {"checked": 2, "behind": {"numpy": ("2.1.0", "2.3.0")}}


def test_heavy_loops_wait_for_a_real_run_and_weekly_ones_wait_a_week(tmp_path, monkeypatch):
    monkeypatch.setattr(loops, "DEV_DATA", tmp_path / "dev")
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    calls = []
    heavy = loops.Loop("t.heavy", "test", "x", "device", lambda c: calls.append(1) or loops.Reading(0, 1),
                       floor=0, every=7, heavy=True)
    now = datetime(2026, 11, 6, 9, tzinfo=timezone.utc)
    loops.run(None, "device", now=now, loops=(heavy,), tasks_dir=tmp_path / "t", log=tmp_path / "a.jsonl")
    assert calls == []  # the app's check never runs it
    loops.run(None, "device", now=now, loops=(heavy,), heavy=True, tasks_dir=tmp_path / "t", log=tmp_path / "a.jsonl")
    loops.run(None, "device", now=now.replace(day=10), loops=(heavy,), heavy=True, tasks_dir=tmp_path / "t",
              log=tmp_path / "a.jsonl")
    assert calls == [1]  # four days later: not yet
    loops.run(None, "device", now=now.replace(day=13), loops=(heavy,), heavy=True, tasks_dir=tmp_path / "t",
              log=tmp_path / "a.jsonl")
    assert calls == [1, 1]
