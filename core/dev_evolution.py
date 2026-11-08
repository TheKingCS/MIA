"""
core.dev_evolution
====================

MIA's Development Evolution Timeline (T-0023, DEC-0071's "Future" item):
how she has grown, month by month, built from the shared history and not
kept as a record of its own. Everything is counted from what's already
recorded; nothing here is written or guessed.

- From the shared history (core/dev_history.py): decisions approved,
  commits, new parts (a code file a commit added: `core/` and `server/`
  parts are capabilities, `tools/` are tools integrated, `web/` screens),
  bugs (Fix-It issues found, and fixed), lab experiments merged or undone.
- From the activity log (core/work_activity.py): tasks finished.
- From the benchmark runs (core/benchmarks.py): per kind, the share of
  questions answered (rank under 2) and the share answered from code (a
  plan or code: rank 0), latest run of each month.
- Milestones: each approved decision, in order, with its date.

`timeline()` is served in the development dashboard's data
(core/work_dashboard.py, `evolution`); the screen is the design
session's. A month the history doesn't reach is simply absent: the
history holds every commit (COMMITS_FIRST from the day it started, and
every one after).
"""

from __future__ import annotations

from typing import Optional

from core.dev_store import DEV_DATA, DevStore

CAPABILITY_DIRS = {"core": "capabilities", "tools": "tools", "server": "capabilities", "web": "screens"}
MILESTONES = 40


def _month(at) -> str:
    """Pure logic. The YYYY-MM of a timestamp or date ("" when there's none)."""
    text = str(at or "")
    return text[:7] if len(text) >= 7 and text[4] == "-" else ""


def _row(rows: dict, month: str) -> dict:
    """The month's counts, made on first use."""
    return rows.setdefault(month, {"month": month, "decisions": 0, "commits": 0, "tasks_done": 0,
                                   "capabilities": 0, "tools": 0, "screens": 0, "bugs_found": 0, "bugs_fixed": 0,
                                   "merged": 0, "undone": 0, "new_parts": [], "benchmarks": {}})


def _bench(record: dict) -> Optional[dict]:
    """Pure logic. One benchmark run's result: how many questions, the share answered and the share answered from
    code (None for a run with no rows)."""
    rows = [r for r in record.get("rows") or [] if isinstance(r, dict) and isinstance(r.get("rank"), int)]
    if not rows:
        return None
    return {"questions": len(rows), "answered": round(sum(r["rank"] < 2 for r in rows) / len(rows), 3),
            "from_code": round(sum(r["rank"] == 0 for r in rows) / len(rows), 3), "at": record.get("at", "")}


def build(history: list[dict], activity: list[dict], bench: list[dict]) -> dict:
    """Pure logic. The timeline from the records: {months: [oldest first], milestones: [{at, ref, title}], totals}."""
    rows: dict[str, dict] = {}
    seen_files: set[str] = set()  # a file added, removed and added again is one new part
    approved: dict[str, dict] = {}
    found_bugs: set[str] = set()
    from core.dev_history import when

    for r in history:
        kind, month = r.get("kind"), _month(when(r))
        if kind == "decision" and r.get("status") in ("APPROVED", "IMPLEMENTED") and r.get("ref") not in approved:
            approved[r["ref"]] = r
            if month:
                _row(rows, month)["decisions"] += 1
        elif kind == "commit" and month:
            row = _row(rows, month)
            row["commits"] += 1
            for f in r.get("added") or []:
                if f in seen_files:
                    continue
                seen_files.add(f)
                top = f.split("/", 1)[0]
                if top in CAPABILITY_DIRS and f.endswith((".py", ".js", ".html")) and "/" in f:
                    row[CAPABILITY_DIRS[top]] += 1
                    if len(row["new_parts"]) < 12:
                        row["new_parts"].append(f)
        elif kind == "failure" and month:
            if r.get("status") == "open" and r["ref"] not in found_bugs:
                found_bugs.add(r["ref"])
                _row(rows, month)["bugs_found"] += 1
            elif r.get("status") == "fixed":
                _row(rows, month)["bugs_fixed"] += 1
        elif kind == "experiment" and month:
            if r.get("status") == "merged":
                _row(rows, month)["merged"] += 1
            elif r.get("status") == "reverted":
                _row(rows, month)["undone"] += 1
    for e in activity:
        month = _month(e.get("at"))
        if e.get("action") == "done" and month:
            _row(rows, month)["tasks_done"] += 1
    for b in sorted(bench, key=lambda b: str(b.get("at", ""))):
        month, result = _month(b.get("at")), _bench(b)
        if month and result:
            _row(rows, month)["benchmarks"][str(b.get("kind", ""))] = result  # the month's latest run of each kind
    months = [rows[m] for m in sorted(rows)]
    milestones = sorted(({"at": when(r)[:10], "ref": r["ref"], "title": r.get("title", "")}
                         for r in approved.values()), key=lambda m: (m["at"], m["ref"]))[-MILESTONES:]
    totals = {k: sum(m[k] for m in months) for k in ("decisions", "commits", "tasks_done", "capabilities", "tools",
                                                       "screens", "bugs_found", "bugs_fixed", "merged", "undone")}
    return {"months": months, "milestones": milestones, "totals": totals}


def timeline(history_store: Optional[DevStore] = None, log=None, bench_store: Optional[DevStore] = None) -> dict:
    """The timeline from the kept records: the shared history, the activity log and the benchmark runs."""
    from core import dev_history, work_activity

    history = list((history_store or dev_history._store()).records())
    activity = work_activity.events(log) if log else work_activity.events()
    bench = list((bench_store or DevStore(DEV_DATA / "benchmarks")).records())
    return build(history, activity, bench)
