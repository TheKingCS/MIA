"""
core.loops
============

MIA's improvement loops (DEC-0094; the map is `docs/IMPROVEMENT_LOOPS.md`;
Zac, 2026-11-06: "almost every process has the potential for some kind of
self assessment and improvement loop and we should identify those and build
it").

Every loop has one shape: **measure** (a number worked out in code from what
MIA already records), **compare** (with a floor, and with its own recent
median), **finding**, **work** (a task in `work/tasks/` with `source:
loop:<id>`, one open at a time; or something offered to the person through
the communication gate), **fix** (only through the lab, the reviewers and
Zac; never by the loop), and **measure again**: a loop still below its floor
after its task is done opens a new one.

- `LOOPS`: the registry. Each loop's scope is the **device** (the PC and the
  development platform) or a **person** (their own use). A person's history
  stays in their own folder (DEC-0001); a task a person's loop opens carries
  numbers and kinds only, never their words.
- `run(context, scope)`: measure what's due (each loop once a day), keep the
  readings (`core/dev_store.py`), judge them, act. Returns what to offer the
  person through the gate.
- `summary(scope)`: every loop's latest reading, its trend and its state, for
  the dev window's **Her loops** panel.

This file is on the lab's protected list: MIA can't loosen how she's judged.
"""

from __future__ import annotations

import shutil
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from core.dev_store import DEV_DATA, DevStore

ROOT = Path(__file__).resolve().parent.parent
WHO = "MIA (loops)"
REGRESSION = 0.25  # worse than its own recent median by this share counts as a slide
HISTORY = 8  # the readings a trend is taken from


@dataclass(frozen=True)
class Reading:
    value: float
    n: int = 1  # how many things it was worked out from
    detail: str = ""  # numbers and kinds only


@dataclass(frozen=True)
class Loop:
    id: str
    area: str
    what: str
    scope: str  # "device" | "person"
    measure: Callable[[object], Optional[Reading]]
    better: str = "lower"  # "lower" | "higher"
    floor: Optional[float] = None
    min_n: int = 1
    acts: str = "task"  # "task" | "offer" | "watch"
    files: tuple[str, ...] = ()
    unit: str = ""
    covers: tuple[str, ...] = ()  # the processes it watches (core/loop_coverage.py, DEC-0101)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _since(days: int, now: Optional[datetime] = None) -> str:
    return ((now or _now()) - timedelta(days=days)).isoformat(timespec="seconds")


# ------------------------------------------------------------------ the person's loops (their use)

def _turns(context, days: int = 7) -> list[dict]:
    traces = getattr(context, "traces", None)
    cut = _since(days)
    return [t for t in (traces.recent(5000) if traces is not None else []) if str(t.get("at", "")) >= cut]


def _failures(context, kinds: tuple[str, ...] = (), days: int = 7) -> list[dict]:
    log = getattr(context, "failures", None)
    found = log.events(days=days) if log is not None else []
    return [e for e in found if not kinds or e.get("kind") in kinds]


def _per_100_turns(kinds: tuple[str, ...]):
    def measure(context) -> Optional[Reading]:
        turns = len(_turns(context))
        if not turns:
            return None
        hits = _failures(context, kinds)
        by = {}
        for e in hits:
            by[e.get("kind")] = by.get(e.get("kind"), 0) + 1
        return Reading(round(100 * len(hits) / turns, 1), turns,
                       f"{len(hits)} in {turns} turns" + ("; " + ", ".join(f"{k} {n}" for k, n in sorted(by.items())) if by else ""))
    return measure


def _thumbs(context) -> Optional[Reading]:
    ratings = getattr(context, "ratings", None)
    if ratings is None:
        return None
    c = ratings.counts()
    total = sum(c.values())
    return Reading(round(c.get("up", 0) / total, 2), total, f"{c.get('up', 0)} up, {c.get('down', 0)} down") if total else None


def _slow(context) -> Optional[Reading]:
    turns = _turns(context)
    if not turns:
        return None
    slow = sum(1 for t in turns if float(t.get("seconds") or 0) > 25)
    return Reading(round(slow / len(turns), 2), len(turns), f"{slow} of {len(turns)} turns over 25 s")


def _count_of(kinds: tuple[str, ...]):
    def measure(context) -> Optional[Reading]:
        if getattr(context, "failures", None) is None:
            return None
        hits = _failures(context, kinds)
        return Reading(float(len(hits)), max(1, len(hits)), f"{len(hits)} in 7 days")
    return measure


def _unused_creations(context) -> Optional[Reading]:
    store = getattr(context, "creations", None)
    if store is None:
        return None
    published = store.published()
    if not published:
        return None
    cut = (_now() - timedelta(days=30)).date().isoformat()
    idle = [c for c in published if (c.get("opened_days") or [""])[-1] < cut and c.get("created", "")[:10] < cut]
    return Reading(float(len(idle)), len(published), f"{len(idle)} of {len(published)} published not opened in 30 days")


def _failing_workflows(context) -> Optional[Reading]:
    store = getattr(context, "creations", None)
    if store is None:
        return None
    cut = _since(7)
    runs = [r for c in store.items for r in (c.get("runs") or []) if r.get("at", "") >= cut]
    if not runs:
        return None
    stopped = sum(1 for r in runs if any(str(line).startswith("stopped") for line in r.get("lines", [])))
    return Reading(float(stopped), len(runs), f"{stopped} of {len(runs)} runs stopped")


# ------------------------------------------------------------------ the device's loops (the PC and the platform)

def _disk(_context) -> Optional[Reading]:
    free = shutil.disk_usage(ROOT).free / 1e9
    return Reading(round(free), 1, f"{free:.0f} GB free")


def _has_repo() -> bool:
    return (ROOT / "work").exists()


def _layering(_context) -> Optional[Reading]:
    from core import dev_map

    breaks = dev_map.layering()
    return Reading(float(len(breaks)), 1, "; ".join(f"{b['file']}:{b['line']}" for b in breaks[:5]))


def _doc_drift(_context) -> Optional[Reading]:
    from core import dev_map

    found = dev_map.doc_mismatches()
    return Reading(float(len(found)), 1, "; ".join(f"{d['names']} ({d['doc']})" for d in found[:5]))


def _stuck(_context) -> Optional[Reading]:
    from core import work_tasks

    cut = (_now() - timedelta(days=7)).date().isoformat()
    tasks = work_tasks.load()
    claimed = [t for t in tasks.values() if t.status == "claimed"]
    stuck = [t.id for t in claimed if (t.updated or t.created) < cut]
    return Reading(float(len(stuck)), max(1, len(claimed)), ", ".join(stuck[:8]) or "none")


def _reviewers(_context) -> Optional[Reading]:
    from core import dev_ledger

    rows = [(p, r["reviewing"]) for p, r in dev_ledger.ledger().items() if r["reviewing"]["attempts"] >= 5]
    if not rows:
        return None
    worst = min(rows, key=lambda x: x[1]["bound"])
    return Reading(worst[1]["bound"], sum(r["attempts"] for _, r in rows),
                   f"weakest: {worst[0]} {worst[1]['passed']}/{worst[1]['attempts']}")


def _knowledge(_context) -> Optional[Reading]:
    from core import dev_knowledge

    hers = [e for e in dev_knowledge.entries() if e.get("by") == "mia"]
    if not hers:
        return None
    withdrawn = sum(1 for e in hers if e.get("status") == "withdrawn")
    return Reading(round(withdrawn / len(hers), 2), len(hers), f"{withdrawn} of {len(hers)} of her write-ups withdrawn")


def _coder(_context) -> Optional[Reading]:
    from core import dev_ledger

    row = dev_ledger.ledger().get("ollama-coder", {}).get("fix failing tests", {})
    if not row.get("attempts"):
        return None
    return Reading(row["rate"] or 0.0, row["attempts"], f"{row['passed']} of {row['attempts']} shadow attempts passed")


def _limits(_context) -> Optional[Reading]:
    from core import dev_usage

    cut = _since(7)
    calls = [u for u in dev_usage._store().tail(3000) if u.get("at", "") >= cut]
    hit = [u for u in calls if u.get("outcome") == "limit"]
    by = {}
    for u in hit:
        by[u["provider"]] = by.get(u["provider"], 0) + 1
    return Reading(float(len(hit)), max(1, len(calls)), ", ".join(f"{p} {n}" for p, n in sorted(by.items())) or "none")


def _council_cost(_context) -> Optional[Reading]:
    from core import council, dev_usage

    cut = _since(7)
    turns = [m for m in council.recent(600) if m.get("who") == "zac" and m.get("plan") and m.get("at", "") >= cut]
    if not turns:
        return None
    calls = sum(1 for u in dev_usage._store().tail(3000) if u.get("at", "") >= cut and u.get("purpose") == "council")
    return Reading(round(calls / len(turns), 1), len(turns), f"{calls} calls for {len(turns)} turns")


def _chronicles(_context) -> Optional[Reading]:
    from core import saga

    return Reading(float(len(saga.candidates())), 1, "candidates waiting for Zac")


def _loop_coverage(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import loop_coverage

    r = loop_coverage.report()
    need = r["total"] - r["counts"].get("declined", 0)
    return Reading(r["share"], need, f"{r['counts'].get('covered', 0)} of {need} covered, "
                                     f"{r['counts'].get('proposed', 0)} proposed") if need else None


def _night_lessons(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import night_school

    week = [l for n in night_school.nights(7) for l in n.get("lessons", []) if l.get("outcome") in ("pass", "fail")]
    if not week:
        return None
    passed = sum(1 for l in week if l["outcome"] == "pass")
    return Reading(round(passed / len(week), 2), len(week), f"{passed} of {len(week)} lessons passed")


def _night_choice(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import night_school

    c = night_school.choosing()
    return Reading(c["rate"], c["nights"], f"{c['agreed']} of {c['nights']} nights") if c["nights"] else None


LOOPS: tuple[Loop, ...] = (
    # A. Conversation and intelligence
    Loop("answers.failures", "answers", "turns that went wrong, per 100", "person",
         _per_100_turns(()), min_n=20, files=("core/assistant_turn.py",), covers=("flow:talk", "module:assistant")),
    Loop("answers.thumbs", "answers", "answers rated 👍", "person", _thumbs, better="higher", floor=0.7, min_n=5,
         covers=("flow:talk", "store:ratings")),
    Loop("answers.rephrased", "answers", "asked again in other words, per 100 turns", "person",
         _per_100_turns(("rephrased",)), min_n=20, files=("core/assistant_turn.py",), covers=("flow:talk",)),
    Loop("answers.talked_instead", "answers", "had the tool but only talked, per 100 turns", "person",
         _per_100_turns(("talked_instead",)), floor=2, min_n=20, files=("core/tool_loop.py",), covers=("flow:tools",)),
    Loop("answers.no_tool", "answers", "asked for something she has no tool for", "person",
         _count_of(("no_tool",)), acts="watch", covers=("flow:tools", "store:failures")),
    Loop("answers.slow", "answers", "share of answers over 25 seconds", "person", _slow, floor=0.10, min_n=20, covers=("flow:talk", "store:traces")),
    Loop("answers.model_down", "answers", "the model not answering, or garbled", "person",
         _count_of(("model_down", "garbled")), floor=0, covers=("flow:talk", "flow:pc")),
    Loop("answers.undo_soon", "answers", "what she did, undone right away, per 100 turns", "person",
         _per_100_turns(("undo_soon",)), min_n=20, covers=("flow:undo",)),
    # D. Her creations
    Loop("creations.unused", "creations", "published screens nobody opens", "person", _unused_creations, floor=0,
         acts="offer", covers=("store:creations", "action:creation")),
    Loop("workflows.failing", "creations", "workflow runs that stopped", "person", _failing_workflows, floor=0,
         files=("core/workflows.py",), covers=("flow:workflows", "check:workflows")),
    # E. Devices
    Loop("pc.disk", "devices", "free space on the PC", "device", _disk, better="higher", floor=20, unit="GB", covers=("flow:pc",)),
    # F. Her development
    Loop("dev.layering", "development", "breaks of the layering rule", "device", _layering, floor=0,
         files=("core/dev_map.py",), covers=("dev:code",)),
    Loop("dev.doc_drift", "development", "files the docs name that don't exist", "device", _doc_drift, floor=0, covers=("dev:code",)),
    Loop("dev.stuck", "development", "tasks claimed for a week or more", "device", _stuck, floor=0, covers=("dev:tasks",)),
    Loop("dev.reviewers", "development", "the weakest reviewer's cautious rate", "device", _reviewers,
         better="higher", floor=0.5, covers=("dev:review",)),
    Loop("dev.knowledge", "development", "MIA's write-ups withdrawn", "device", _knowledge, floor=0.3,
         files=("core/dev_knowledge.py",), covers=("dev:knowledge",)),
    Loop("dev.coder", "development", "MIA's coder: shadow attempts passed", "device", _coder, better="higher",
         acts="watch", covers=("dev:shadow",)),
    Loop("dev.limits", "development", "usage limits hit in a week", "device", _limits, acts="watch", covers=("dev:usage",)),
    Loop("dev.council_cost", "development", "calls per council turn", "device", _council_cost, acts="watch", covers=("dev:council",)),
    Loop("dev.chronicles", "development", "Chronicles candidates waiting", "device", _chronicles, acts="watch",
         covers=("dev:chronicles", "check:chronicle")),
    Loop("dev.loop_coverage", "development", "processes with a loop, of those that need one", "device",
         _loop_coverage, better="higher", acts="watch", covers=("dev:loops", "check:loops")),
    Loop("night.lessons", "development", "Night School lessons passed this week", "device", _night_lessons,
         better="higher", min_n=3, acts="watch", covers=("dev:night_school", "check:night_school")),
    Loop("night.choice", "development", "nights her own pick of what to study matched her teacher's", "device",
         _night_choice, better="higher", min_n=5, acts="watch", covers=("dev:night_school",)),
)


# ------------------------------------------------------------------ judging (pure)

def worse(loop: Loop, value: float, than: float) -> bool:
    return value > than if loop.better == "lower" else value < than


def judge(loop: Loop, reading: Optional[Reading], earlier: list[float]) -> dict:
    """Pure logic. Where a reading stands: ok, below its floor, slid against its own trend, too thin, or none."""
    if reading is None:
        return {"state": "none", "why": "nothing to measure yet"}
    if reading.n < loop.min_n:
        return {"state": "thin", "why": f"only {reading.n} to go on (needs {loop.min_n})"}
    if loop.floor is not None and worse(loop, reading.value, loop.floor):
        side = "above" if loop.better == "lower" else "below"
        return {"state": "below", "why": f"{reading.value:g}{loop.unit} is {side} its floor of {loop.floor:g}{loop.unit}"}
    recent = earlier[-HISTORY:]
    if len(recent) >= 4:
        typical = statistics.median(recent)
        gap = abs(reading.value - typical)
        if worse(loop, reading.value, typical) and gap > max(abs(typical) * REGRESSION, 1e-9) and gap >= 0.05:
            return {"state": "slid", "why": f"{reading.value:g}{loop.unit} against its usual {typical:g}{loop.unit}"}
    return {"state": "ok", "why": ""}


# ------------------------------------------------------------------ running

def _store(context, scope: str) -> DevStore:
    if scope == "device":
        return DevStore(DEV_DATA / "loops")
    home = getattr(getattr(context, "traces", None), "data_dir", None) or getattr(context, "my_dir", None)
    return DevStore(Path(home) / "loops" if home else DEV_DATA / "loops-person")


def history(context, scope: str, limit: int = 600) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in _store(context, scope).tail(limit):
        out.setdefault(r.get("loop", ""), []).append(r)
    return out


def _open_task(loop: Loop, verdict: dict, reading: Reading, tasks_dir=None, log=None) -> Optional[str]:
    """One open task per loop: numbers and kinds only."""
    from core import work_activity, work_tasks

    tasks = work_tasks.load(tasks_dir) if tasks_dir else work_tasks.load()
    if any(t.source == f"loop:{loop.id}" and t.status not in work_tasks.FINISHED for t in tasks.values()):
        return None
    body = (f"Opened by the loop `{loop.id}` (docs/IMPROVEMENT_LOOPS.md, DEC-0094): {loop.what} {verdict['why']}.\n\n"
            f"Measured: {reading.detail or reading.value} (from {reading.n}).\n\nFind why and fix it through the lab; "
            "the loop measures again each day and reopens this if it stays there.")
    task = work_tasks.new(tasks, f"Loop {loop.id}: {loop.what}", role="Debugging Engineer", source=f"loop:{loop.id}",
                          files=list(loop.files), body=body)
    work_tasks.save(task, tasks_dir) if tasks_dir else work_tasks.save(task)
    if log:
        work_activity.record(WHO, "watch", task.id, f"{loop.id}: {verdict['why']}", log)
    else:
        work_activity.record(WHO, "watch", task.id, f"{loop.id}: {verdict['why']}")
    return task.id


def run(context, scope: str, now: Optional[datetime] = None, loops: tuple[Loop, ...] = LOOPS, force: bool = False,
        tasks_dir=None, log=None) -> list:
    """Measure every loop of this scope that's due (once a day), keep, judge, act. Returns Candidates to offer."""
    from core.communication_gate import Candidate

    now = now or _now()
    if scope == "device" and not _has_repo():
        return []  # the phone: no development platform here
    store = _store(context, scope)
    past = history(context, scope)
    offers = []
    for loop in (l for l in loops if l.scope == scope):
        earlier = past.get(loop.id, [])
        if earlier and earlier[-1].get("at", "")[:10] == now.date().isoformat() and not force:
            continue
        try:
            reading = loop.measure(context)
        except Exception as problem:  # a loop that can't measure says so; it never stops the others
            store.append({"at": now.isoformat(timespec="seconds"), "loop": loop.id, "state": "error",
                          "why": str(problem)[:200]})
            continue
        verdict = judge(loop, reading, [r["value"] for r in earlier if r.get("value") is not None])
        entry = {"at": now.isoformat(timespec="seconds"), "loop": loop.id, "state": verdict["state"], "why": verdict["why"]}
        if reading is not None:
            entry.update(value=reading.value, n=reading.n, detail=reading.detail)
        if verdict["state"] in ("below", "slid") and reading is not None:
            if loop.acts == "task" and _has_repo():
                entry["task"] = _open_task(loop, verdict, reading, tasks_dir, log)
            elif loop.acts == "offer":
                offers.append(Candidate(topic=f"loop:{loop.id}", title="Something to tidy",
                                        message=f"{loop.what.capitalize()}: {reading.detail}.", source="loops",
                                        fingerprint=f"loop:{loop.id}:{now.date().isoformat()}"))
        store.append(entry)
    return offers


def summary(context, scope: str) -> list[dict]:
    """Every loop of this scope with its latest reading, its last few values and its state."""
    past = history(context, scope)
    open_tasks = {}
    if _has_repo():
        from core import work_tasks

        open_tasks = {t.source[5:]: t.id for t in work_tasks.load().values()
                      if t.source.startswith("loop:") and t.status not in work_tasks.FINISHED}
    out = []
    for loop in (l for l in LOOPS if l.scope == scope):
        rows = past.get(loop.id, [])
        last = rows[-1] if rows else {}
        out.append({"id": loop.id, "area": loop.area, "what": loop.what, "better": loop.better, "floor": loop.floor,
                    "unit": loop.unit, "state": last.get("state", "none"), "why": last.get("why", ""),
                    "value": last.get("value"), "detail": last.get("detail", ""), "at": last.get("at", ""),
                    "task": open_tasks.get(loop.id),  # the task working on it now, if any
                    "trend": [r.get("value") for r in rows if r.get("value") is not None][-HISTORY:], "acts": loop.acts})
    return out
