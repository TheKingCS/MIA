"""
tests.test_dev_evolution
==========================

MIA's Development Evolution Timeline (core/dev_evolution.py, T-0023):
counted month by month from the shared history, the activity log and the
benchmark runs, never kept on its own.
"""

from core import dev_evolution as ev
from core.dev_store import DevStore


def test_the_timeline_counts_each_month_from_the_records():
    """Decisions approved (once, however often recorded), commits and the parts they added, tasks finished,
    bugs found and fixed, experiments merged or undone, and each month's latest benchmark."""
    history = [
        {"kind": "decision", "ref": "DEC-0001", "status": "PROPOSED", "at": "2026-10-01", "title": "One"},
        {"kind": "decision", "ref": "DEC-0001", "status": "APPROVED", "at": "2026-10-02", "title": "One"},
        {"kind": "decision", "ref": "DEC-0001", "status": "APPROVED", "at": "2026-11-02", "title": "One"},
        {"kind": "decision", "ref": "DEC-0002", "status": "APPROVED", "at": "2026-11-03", "title": "Two"},
        {"kind": "commit", "ref": "a", "at": "2026-10-05T10:00:00", "files": ["core/a.py", "tools/t.py", "README.md"],
         "added": ["core/a.py", "tools/t.py", "README.md"]},
        {"kind": "commit", "ref": "b", "at": "2026-11-05T10:00:00", "files": ["core/a.py", "core/b.py", "web/x.js"],
         "added": ["web/x.js"]},  # core/b.py only changed: not a new part
        {"kind": "failure", "ref": "tool:x", "status": "open", "at": "2026-11-01"},
        {"kind": "failure", "ref": "tool:x", "status": "fixed", "at": "2026-11-04"},
        {"kind": "experiment", "ref": "P1", "status": "merged", "at": "2026-11-06"},
        {"kind": "experiment", "ref": "P2", "status": "reverted", "at": "2026-11-06"},
    ]
    activity = [{"action": "done", "at": "2026-11-07T00:00:00+00:00"}, {"action": "claim", "at": "2026-11-07"}]
    rows = [{"rank": 0}, {"rank": 1}, {"rank": 2}, {"rank": 3}]
    bench = [{"kind": "routing", "at": "2026-11-01", "rows": rows[:1]}, {"kind": "routing", "at": "2026-11-08", "rows": rows}]
    t = ev.build(history, activity, bench)
    oct_, nov = t["months"]
    assert oct_["month"] == "2026-10" and oct_["decisions"] == 1 and oct_["capabilities"] == 1 and oct_["tools"] == 1
    assert oct_["new_parts"] == ["core/a.py", "tools/t.py"]
    assert nov["decisions"] == 1 and nov["capabilities"] == 0 and nov["screens"] == 1 and nov["tasks_done"] == 1
    assert (nov["bugs_found"], nov["bugs_fixed"], nov["merged"], nov["undone"]) == (1, 1, 1, 1)
    assert nov["benchmarks"]["routing"] == {"questions": 4, "answered": 0.5, "from_code": 0.25, "at": "2026-11-08"}
    assert [m["ref"] for m in t["milestones"]] == ["DEC-0001", "DEC-0002"] and t["totals"]["commits"] == 2


def test_the_timeline_reads_the_kept_records_and_is_empty_without_them(tmp_path):
    """From the stores: nothing kept is an empty timeline, not an error."""
    empty = ev.timeline(DevStore(tmp_path / "h"), tmp_path / "activity.jsonl", DevStore(tmp_path / "b"))
    assert empty["months"] == [] and empty["milestones"] == [] and empty["totals"]["commits"] == 0
    DevStore(tmp_path / "h").append({"kind": "commit", "ref": "a", "at": "2026-11-05", "files": ["core/a.py"],
                                     "added": ["core/a.py"]})
    assert ev.timeline(DevStore(tmp_path / "h"), tmp_path / "activity.jsonl",
                       DevStore(tmp_path / "b"))["months"][0]["capabilities"] == 1
