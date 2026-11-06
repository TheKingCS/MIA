"""
core.benchmarks
=================

The weekly benchmarks (build plan step 5, DEC-0094): Zac's 112-question
Intelligence Benchmark on this PC's model and the person's real records,
the golden conversation corpus on the glasses and the phone, and the routing
audit. `tools/weekly_bench.py` runs them (Night School starts it once a
week, in a process of its own); this file grades them and keeps the grades.

**Graded by code, never by a model, and never leaving the PC.** The answers
hold real records, so only the grades are kept (`data/dev/benchmarks`): each
question's id, its route, what code flagged, and how long it took. A
question **falls** when, against the run before:

- its route got worse (a question plan or a code lookup, then the model
  with tools, then no answer, then an error);
- it's newly flagged (an answer replaced for a number she hadn't looked up,
  a lookup that failed, a change she wanted, no answer);
- or it newly took longer than `SLOW` seconds.

The loops `answers.benchmark`, `answers.benchmark_clean`, `answers.corpus`
and `answers.routing` (core/loops.py) read the latest two runs. This file is
on the lab's protected list: MIA can't change how she's graded.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.dev_store import DEV_DATA, DevStore

KINDS = ("intelligence", "corpus", "routing")
EVERY = timedelta(days=7)
SLOW = 25.0
RUN_MINUTES = 90  # the whole weekly run, at most


def _store() -> DevStore:
    return DevStore(DEV_DATA / "benchmarks")


# ------------------------------------------------------------------ grading (pure)

def rank(route: str, note: str = "") -> int:
    """Pure logic. How well a question was routed: 0 a plan or code, 1 the model, 2 no answer, 3 an error."""
    route = str(route or "")
    if route == "error":
        return 3
    if "didn't answer" in str(note or ""):
        return 2
    if route.startswith(("plan", "code")):
        return 0
    return 1


def grade(row: dict) -> dict:
    """Pure logic. One benchmark answer, as kept: no words of the answer."""
    flags = [str(w)[:80] for w in row.get("warnings") or []][:3]
    if row.get("note"):
        flags.append(str(row["note"])[:80])
    flags += [str(f) for f in row.get("flags") or []]
    return {"id": str(row.get("id", "")), "route": str(row.get("route", ""))[:60],
            "rank": rank(row.get("route", ""), row.get("note", "")), "flags": flags,
            "seconds": round(float(row.get("seconds") or 0), 1), "surface": str(row.get("surface", ""))}


ROUTING_RANK = {"plan": 0, "code": 0, "tools": 1, "model only": 2}


def grade_route(row: dict) -> dict:
    return {"id": str(row.get("id", "")), "route": row.get("route", ""), "rank": ROUTING_RANK.get(row.get("route"), 2),
            "flags": [], "seconds": 0.0, "surface": ""}


def falls(before: list[dict], now: list[dict]) -> list[dict]:
    """Pure logic. The questions that got worse since the run before: [{id, why}]."""
    earlier = {(r["id"], r.get("surface", "")): r for r in before}
    out = []
    for r in now:
        b = earlier.get((r["id"], r.get("surface", "")))
        if b is None:
            continue
        why = []
        if r["rank"] > b["rank"]:
            why.append(f"route {b['route'] or '?'} -> {r['route'] or '?'}")
        if r["flags"] and not b["flags"]:
            why.append("flagged: " + "; ".join(r["flags"])[:120])
        if r["seconds"] > SLOW >= b["seconds"]:
            why.append(f"{b['seconds']:g}s -> {r['seconds']:g}s")
        if why:
            out.append({"id": r["id"] + (f" ({r['surface']})" if r.get("surface") else ""), "why": ", ".join(why)})
    return out


# ------------------------------------------------------------------ the record

def keep(kind: str, rows: list[dict], model: str = "", store: Optional[DevStore] = None) -> dict:
    record = {"kind": kind, "model": model, "rows": rows}
    (store or _store()).append(record)
    return record


def runs(kind: str, store: Optional[DevStore] = None, n: int = 2) -> list[dict]:
    """The latest `n` runs of a kind, oldest first."""
    found = [r for r in (store or _store()).tail(60) if r.get("kind") == kind]
    return found[-n:]


def due(now: Optional[datetime] = None, store: Optional[DevStore] = None) -> bool:
    """A week since the last intelligence run (or never run)."""
    last = runs("intelligence", store, 1)
    if not last:
        return True
    try:
        at = datetime.fromisoformat(last[-1]["at"])
    except (KeyError, ValueError):
        return True
    now = now or datetime.now(timezone.utc)
    return now - (at if at.tzinfo else at.replace(tzinfo=timezone.utc)) >= EVERY


def run_now(timeout_minutes: int = RUN_MINUTES) -> str:
    """The weekly run, in a process of its own (it builds the full app context); what it printed last."""
    import os

    from core.dev_lab import ROOT, _python

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return "not from a test run: it asks the real model about real records"
    try:
        out = subprocess.run([_python(), "-m", "tools.weekly_bench"], cwd=str(ROOT), capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout_minutes * 60,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0)
    except subprocess.TimeoutExpired:
        return f"stopped after {timeout_minutes} minutes"
    return ((out.stdout or "") + (out.stderr or "")).strip()[-400:]


def latest(kind: str, store: Optional[DevStore] = None) -> Optional[dict]:
    """The latest run of a kind with what fell since the one before: {at, rows, falls, clean, flagged, model}."""
    found = runs(kind, store, 2)
    if not found:
        return None
    now = found[-1]["rows"]
    return {"at": found[-1].get("at", ""), "rows": now, "model": found[-1].get("model", ""),
            "falls": falls(found[0]["rows"], now) if len(found) == 2 else [],
            # a benchmark question is clean answered by a plan or code; a conversation, by the model too
            "clean": sum(1 for r in now if not r["flags"] and r["rank"] <= (0 if kind == "intelligence" else 1)),
            "flagged": sum(1 for r in now if r["flags"])}
