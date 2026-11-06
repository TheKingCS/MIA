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
ACTION_KINDS = ("action_failed", "declined")


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
    every: int = 1  # days between readings
    heavy: bool = False  # needs a real run (the suite, the network): Night School and the CLI, never the app's check


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
    if not kinds:  # "what went wrong in a turn": an action's own outcome has its loops (actions.*)
        return [e for e in found if e.get("kind") not in ACTION_KINDS]
    return [e for e in found if e.get("kind") in kinds]


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


def _actions_failed(context) -> Optional[Reading]:
    if getattr(context, "failures", None) is None:
        return None
    found = _failures(context, ("action_failed",))
    kinds = sorted({e.get("tool", "") for e in found} - {""})
    return Reading(len(found), max(1, len(found)), f"{len(found)} in 7 days" + (f": {', '.join(kinds[:6])}" if kinds else ""))


def _email_discarded(context) -> Optional[Reading]:
    store = getattr(context, "email_drafts", None)
    if store is None:
        return None
    settled = [d for d in store.drafts() if d.created_at >= _since(30)[:19] and d.status in ("sent", "discarded")]
    if not settled:
        return None
    thrown = sum(1 for d in settled if d.status == "discarded")
    return Reading(round(thrown / len(settled), 2), len(settled), f"{thrown} of {len(settled)} drafts discarded in 30 days")


def _email_left_open(context) -> Optional[Reading]:
    store = getattr(context, "email_drafts", None)
    if store is None:
        return None
    waiting = store.open_drafts()
    old = [d for d in waiting if d.created_at < _since(7)[:19]]
    return Reading(len(old), max(1, len(waiting)), f"{len(old)} of {len(waiting)} open drafts are over a week old")


def _gate_entries(context) -> Optional[list[dict]]:
    gate = getattr(context, "communication", None)
    if gate is None or not hasattr(gate, "entries_since"):
        return None
    return gate.entries_since(_since(7)[:19])


def _gate_dismissed(context) -> Optional[Reading]:
    entries = _gate_entries(context)
    if entries is None:
        return None
    sent = [e for e in entries if e.get("action") == "act" and e.get("urgency") != "urgent"]
    if not sent:
        return None
    gone = sum(1 for e in sent if e.get("dismissed_at"))
    return Reading(round(gone / len(sent), 2), len(sent), f"{gone} of {len(sent)} dismissed in 7 days")


# The daily checks in core/application.py that speak through the gate, by the topic they offer under
# (tests/test_loop_coverage.py keeps this in step with the code).
CHECK_TOPICS = {
    "calendar_digest": "calendar_digest", "checkin": "checkin", "budget_nudge": "budget_nudge",
    "smart_suggestion": "smart_suggestion", "maintenance_insight": "maintenance_insight",
    "mission_insight": "mission_insight", "pattern_insight": "pattern_insight",
    "skill_pattern_insight": "skill_pattern_insight", "skill_decline_insight": "skill_decline_insight",
    "skill_momentum_insight": "skill_momentum_insight", "walkthrough_suggestion": "walkthrough_suggestion",
    "journal_reflection": "journal_reflection", "warranty": "warranty", "memory_callback": "memory_callback",
    "grow_alert": "grow_alert", "season": "season", "insurance_renewal": "insurance_renewal", "chronicle": "chronicle",
    "finding_": "findings", "obligation_deadline": "obligation_reminders",
}


def _check_of(topic: str) -> str:
    return CHECK_TOPICS.get(topic) or next((c for t, c in CHECK_TOPICS.items() if t.endswith("_") and
                                            topic.startswith(t)), "")


def _checks_dismissed(context) -> Optional[Reading]:
    """Which daily check's messages are dismissed most, over 30 days: the one to make worth reading."""
    gate = getattr(context, "communication", None)
    if gate is None or not hasattr(gate, "entries_since"):
        return None
    by = {}
    for e in gate.entries_since(_since(30)[:19]):
        check = _check_of(e.get("topic", ""))
        if check and e.get("action") == "act" and e.get("urgency") != "urgent":
            sent, gone = by.get(check, (0, 0))
            by[check] = (sent + 1, gone + (1 if e.get("dismissed_at") else 0))
    rated = sorted(((gone / sent, sent, gone, c) for c, (sent, gone) in by.items() if sent >= 4), reverse=True)
    if not rated:
        return None
    worst = ", ".join(f"{c.replace('_', ' ')} {g} of {s}" for _, s, g, c in rated[:3])
    return Reading(round(rated[0][0], 2), sum(s for _, s, _, _ in rated), f"dismissed most: {worst}")


def _recurring_missed(context) -> Optional[Reading]:
    """Daily recurring missions in the last 30 days (today aside) that weren't done: a target set too high."""
    missions = getattr(context, "missions", None)
    if missions is None or not hasattr(missions, "all_missions"):
        return None
    today = _now().date()
    cut = (today - timedelta(days=30)).isoformat()
    by = {}
    for m in missions.all_missions():
        key = m.occurrence_key or ""
        if not m.recurring_template_id or len(key) != 10 or not cut <= key < today.isoformat():
            continue
        made, missed = by.get(m.name, (0, 0))
        by[m.name] = (made + 1, missed + (0 if m.status == "completed" else 1))
    made = sum(n for n, _ in by.values())
    if not made:
        return None
    missed = sum(x for _, x in by.values())
    worst = max(by.items(), key=lambda kv: (kv[1][1] / kv[1][0], kv[1][0]))
    return Reading(round(missed / made, 2), made, f"{missed} of {made} not done; most often missed: {worst[0]} "
                   f"({worst[1][1]} of {worst[1][0]})")


def _gate_expired(context) -> Optional[Reading]:
    entries = _gate_entries(context)
    if entries is None:
        return None
    held = sum(1 for e in entries if e.get("action") == "defer")
    if not held:
        return None
    lapsed = sum(1 for e in entries if e.get("action") == "drop" and str(e.get("reason", "")).startswith("waited too long"))
    return Reading(round(lapsed / held, 2), held, f"{lapsed} of {held} held back expired before they went out")


def _memory_quality(context) -> Optional[Reading]:
    store = getattr(context, "user_memories", None)
    if store is None or not hasattr(store, "corrections"):
        return None
    fixed = store.corrections(30)
    kept = [m for m in store.all_memories() if m.created_at >= _since(30)[:19]]
    gone = sum(1 for c in fixed if c.get("how") == "deleted")
    made = len(kept) + gone  # what she kept in 30 days, the deleted ones included
    if not made:
        return None
    by = {}
    for c in fixed:
        by[c.get("category", "Other")] = by.get(c.get("category", "Other"), 0) + 1
    return Reading(round(len(fixed) / made, 2), made, f"{len(fixed)} of {made} new memories corrected"
                   + (" (" + ", ".join(f"{k} {n}" for k, n in sorted(by.items())) + ")" if by else ""))


def _gate_saturation(context) -> Optional[Reading]:
    entries = _gate_entries(context)
    if entries is None:
        return None
    full = {e["at"][:10] for e in entries if str(e.get("reason", "")).startswith("already said")}
    days = {e["at"][:10] for e in entries if e.get("at")}
    return Reading(len(full), max(1, len(days)), f"the daily limit was hit on {len(full)} of {len(days)} days") \
        if days else None


def _gate_unwelcome(context) -> Optional[Reading]:
    gate = getattr(context, "communication", None)
    if gate is None or not hasattr(gate, "paused"):
        return None
    paused = sorted(p["topic"] for p in gate.paused())
    return Reading(len(paused), max(1, len(paused)), f"{len(paused)} kinds on a break"
                   + (f": {', '.join(paused[:6])}" if paused else ""))


def _creations_held(context) -> Optional[Reading]:
    store = getattr(context, "creations", None)
    if store is None:
        return None
    from core.creation_spec import check
    from core.workflows import check as check_workflow

    live = store.published()
    if not live:
        return None
    broken = []
    for c in live:  # the same checks it passed to be published (core/creation_actions.py)
        try:
            spec = store.shown(c["id"]).get("spec") or {}
            if check_workflow(spec, context) if spec.get("kind") == "workflow" else check(spec):
                broken.append(c["id"])
        except Exception:
            broken.append(c.get("id", "?"))
    return Reading(len(broken), len(live), f"{len(broken)} of {len(live)} published screens no longer pass their checks")


def _recovered(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    since = _since(7)
    found = [r for r in DevStore(DEV_DATA / "recovered").tail(200) if r.get("at", "") >= since]
    files = sorted({r.get("file", "") for r in found})
    return Reading(len(found), max(1, len(found)), f"{len(found)} in 7 days" + (f": {', '.join(files[:6])}" if files else ""))


def _corrections(area: str = ""):
    def measure(context) -> Optional[Reading]:
        if getattr(context, "failures", None) is None and getattr(context, "traces", None) is None:
            return None
        from core import corrections

        found = corrections.summary(context, 30)
        rows = ({area: found[area]} if area in found else {}) if area else found
        changes = sum(r["changes"] for r in rows.values())
        fixed = sum(r["corrected"] for r in rows.values())
        if not changes:
            return None
        kinds: dict[str, int] = {}
        for r in rows.values():
            for k, n in r["kinds"].items():
                kinds[k] = kinds.get(k, 0) + n
        worst = sorted(kinds.items(), key=lambda kv: -kv[1])[:5]
        return Reading(round(fixed / changes, 2), changes, f"{fixed} of {changes} of her changes corrected in 30 days"
                       + (": " + ", ".join(f"{k} {n}" for k, n in worst) if worst else ""))
    return measure


def _bench(kind: str, what: str):
    def measure(_context) -> Optional[Reading]:
        if not _has_repo():
            return None
        from core import benchmarks

        found = benchmarks.latest(kind)
        if found is None or not found["rows"]:
            return None
        rows = found["rows"]
        if what == "falls":
            fell = found["falls"]
            return Reading(len(fell), len(rows), f"{len(fell)} of {len(rows)} fell since the run before"
                           + (": " + "; ".join(f"{f['id']} ({f['why']})" for f in fell[:6]) if fell else ""))
        if what == "clean":
            return Reading(round(found["clean"] / len(rows), 2), len(rows), f"{found['clean']} of {len(rows)} clean")
        if what == "flagged":
            return Reading(round(found["flagged"] / len(rows), 2), len(rows), f"{found['flagged']} of {len(rows)} flagged")
        left = sum(1 for r in rows if r["route"] == "model only")
        return Reading(left, len(rows), f"{left} of {len(rows)} questions reach no plan, lookup or tool")
    return measure


def _calibration(context) -> Optional[Reading]:
    if getattr(context, "ratings", None) is None:
        return None
    from core import calibration

    by = calibration.rated(context)
    sure = by.get("sure", {"up": 0, "down": 0})
    rest = {"up": sum(v["up"] for k, v in by.items() if k != "sure"), "down": sum(v["down"] for k, v in by.items() if k != "sure")}
    n_sure, n_rest = sure["up"] + sure["down"], rest["up"] + rest["down"]
    if not n_sure:
        return None
    up_sure = sure["up"] / n_sure
    detail = f"{sure['up']} of {n_sure} sure answers rated up"
    if not n_rest:
        return Reading(round(up_sure, 2), n_sure, detail)
    up_rest = rest["up"] / n_rest
    return Reading(round(up_sure - up_rest, 2), n_sure, detail + f", against {rest['up']} of {n_rest} of the others")


def _gaps(context) -> Optional[Reading]:
    if getattr(context, "failures", None) is None:
        return None
    from core import capability_gaps

    s = capability_gaps.summary(context)
    if not s["gaps"]:
        return None
    by = ", ".join(f"{k} {n}" for k, n in sorted(s["by_need"].items()))
    return Reading(s["repeated"], s["gaps"], f"{s['repeated']} asked more than once, of {s['gaps']}" + (f" ({by})" if by else ""))


def _journal_pace(context) -> Optional[Reading]:
    if getattr(context, "operating_journal", None) is None:
        return None
    from core import operating_journal

    found = operating_journal.pace(context)
    if found is None:
        return None
    share, n, by = found
    return Reading(share, n, f"{round(share * n)} of {n} full weeks or months at their own pace: " + ", ".join(
        f"{area} {a}/{b}" for area, (a, b) in sorted(by.items())))


def _play_load(context) -> Optional[Reading]:
    if getattr(context, "recreation", None) is None:
        return None
    from core import recreation

    weeks = recreation.load(context)
    ratio = recreation.acute_chronic(weeks)
    if ratio is None:
        return None
    return Reading(ratio, 5, f"this week's play load {weeks[-1]['play_load']:g} against a weekly "
                             f"{sum(w['play_load'] for w in weeks[:-1]) / 4:g} before")


def _news_misleading(context) -> Optional[Reading]:
    if getattr(context, "failures", None) is None:
        return None
    from core import good_news

    heard = [h for h in good_news.heard(context) if h.get("day", "") >= _since(30)[:10]]
    stories = sum(len(h.get("stories", [])) for h in heard)
    if not stories:
        return None
    bad = [s for h in heard for s in h.get("misleading", [])]
    by = {}
    for s in bad:
        by[s] = by.get(s, 0) + 1
    return Reading(round(len(bad) / stories, 3), stories, f"{len(bad)} of {stories} stories heard called misleading"
                   + (": " + ", ".join(f"{s} {n}" for s, n in sorted(by.items(), key=lambda kv: -kv[1])) if by else ""))


def _sight_failed(context) -> Optional[Reading]:
    if getattr(context, "failures", None) is None:
        return None
    from core import sight

    found = sight.looks(context)
    if not found:
        return None
    missed = sum(1 for l in found if not l.get("answered"))
    slow = sum(1 for l in found if l.get("seconds", 0) > 30)
    return Reading(round(missed / len(found), 2), len(found), f"{missed} of {len(found)} looks unanswered, {slow} over 30 s")


def _glasses_voice(context) -> Optional[Reading]:
    mine = [t for t in _turns(context, 7) if t.get("surface") == "glasses"]
    if not mine:
        return None
    bad = sum(1 for t in mine if not t.get("model_answered", True) or (t.get("seconds") or 0) > 25)
    return Reading(round(bad / len(mine), 2), len(mine), f"{bad} of {len(mine)} glasses turns unanswered or over 25 s")


def _phone_link(context) -> Optional[Reading]:
    from core import phone_link
    from core.person_settings import person_id

    pid = person_id(context)
    hours = phone_link.hours_since(pid) if pid else None
    return Reading(hours, 1, f"{hours:g} hours since their phone last reached this PC") if hours is not None else None


def _maker(context) -> Optional[Reading]:
    if getattr(context, "failures", None) is None:
        return None
    from core.creation_maker import maker_log

    found = maker_log(context)
    if not found:
        return None
    missed = [m for m in found if m.get("outcome") != "first"]
    failed = sum(1 for m in found if m.get("outcome") == "failed")
    common: dict[str, int] = {}
    for m in missed:
        for p in m.get("problems", []):
            common[p] = common.get(p, 0) + 1
    top = sorted(common.items(), key=lambda kv: -kv[1])[:2]
    return Reading(round(len(missed) / len(found), 2), len(found), f"{len(missed)} of {len(found)} designs missed their "
                   f"checks the first time, {failed} never passed" + (": " + "; ".join(p for p, _n in top) if top else ""))


def _loop_prediction(context) -> Optional[Reading]:
    from core.the_loop import predictions

    found = predictions(context)
    if found is None:
        return None
    return Reading(found["off"], found["planned"] + found["extra"],
                   f"of {found['planned']} work days the Loop planned, {found['missed']} weren't worked; "
                   f"{found['extra']} worked days it hadn't planned")


def _inbox_reading(context) -> Optional[Reading]:
    inbox = getattr(context, "inbox", None)
    if inbox is None or not hasattr(inbox, "readings"):
        return None
    found = inbox.readings()
    if not found:
        return None
    fixed = [r for r in found if r.get("corrected")]
    by: dict[str, int] = {}
    for r in fixed:
        for f in r["corrected"]:
            by[f] = by.get(f, 0) + 1
    return Reading(round(len(fixed) / len(found), 2), len(found), f"{len(fixed)} of {len(found)} filed documents had a "
                   f"field corrected" + (": " + ", ".join(f"{k} {n}" for k, n in sorted(by.items(), key=lambda kv: -kv[1]))
                                         if by else ""))


def _projections(context) -> Optional[Reading]:
    if getattr(context, "failures", None) is None:
        return None
    from core import calibration

    calibration.check_due(context)  # what's come due, checked against what happened
    checked = [p for p in calibration.projections(context) if p.get("outcome")]
    if not checked:
        return None
    right = sum(1 for p in checked if p["outcome"] == "right")
    return Reading(round(right / len(checked), 2), len(checked), f"{right} of {len(checked)} projected dates came true "
                   f"(within a month)")


def _search_empty(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    since = _since(30)
    found = [r for r in DevStore(DEV_DATA / "search").tail(2000) if r.get("at", "") >= since]
    if not found:
        return None
    empty = sum(1 for r in found if not r.get("found"))
    left = sum(1 for r in found if r.get("found") and not r.get("chosen"))
    failed = sorted({p for r in found for p in r.get("failed", [])})
    return Reading(round(empty / len(found), 2), len(found), f"{empty} of {len(found)} searches found nothing, {left} found "
                   f"things but nothing was opened" + (f"; providers that failed: {', '.join(failed)}" if failed else ""))


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

    # Only what she's written since the guards (T-0044): the first batch is history, not how she writes now.
    hers = [e for e in dev_knowledge.entries() if e.get("by") == "mia"
            and str(e.get("created", "")) >= dev_knowledge.GUARDED_SINCE]
    if not hers:
        return None
    withdrawn = sum(1 for e in hers if e.get("status") == "withdrawn")
    return Reading(round(withdrawn / len(hers), 2), len(hers), f"{withdrawn} of {len(hers)} of her write-ups withdrawn "
                   f"since {dev_knowledge.GUARDED_SINCE[:10]}")


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


def _suite_unexpected(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import dev_checks

    s = dev_checks.suite()
    if not s["finished"]:
        return Reading(1, 1, f"the suite didn't finish on {s['commit']}")
    detail = f"{len(s['unexpected'])} unexpected on {s['commit']}"
    if s["unexpected"]:
        detail += ": " + ", ".join(s["unexpected"][:5])
    if s["stale"]:
        detail += f"; {len(s['stale'])} known failure(s) pass again: take them off work/known_failures.json"
    return Reading(len(s["unexpected"]), 1, detail)


def _suite_time(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import dev_checks

    s = dev_checks.suite()
    return Reading(round(s["seconds"], 1), 1, s["summary"]) if s.get("seconds") else None


def _reverts(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import dev_checks, work_activity

    r = dev_checks.reverts(work_activity.events())
    if not r["merges"]:
        return None
    return Reading(r["rate"], r["merges"], f"{r['reverts']} of {r['merges']} merges reverted in 30 days"
                   + (f" ({', '.join(r['reverted'])})" if r["reverted"] else ""))


def _vulnerable(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import dev_checks

    v = dev_checks.vulnerable()
    names = sorted(v["packages"])
    return Reading(len(names), v["checked"], f"{len(names)} of {v['checked']} packages with a known vulnerability"
                   + (": " + ", ".join(f"{n} ({', '.join(v['packages'][n][:3])})" for n in names[:6]) if names else ""))


def _outdated(_context) -> Optional[Reading]:
    if not _has_repo():
        return None
    from core import dev_checks

    o = dev_checks.outdated()
    if not o["checked"]:
        return None
    behind = sorted(o["behind"].items())
    return Reading(len(behind), o["checked"], f"{len(behind)} of {o['checked']} behind their latest"
                   + (": " + ", ".join(f"{n} {h} -> {l}" for n, (h, l) in behind[:8]) if behind else ""))


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
    Loop("gaps.repeated", "answers", "things she can't do yet, asked more than once (self-enablement)", "person",
         _gaps, acts="watch", covers=("flow:tools", "check:capability_gaps", "action:gap")),
    Loop("answers.slow", "answers", "share of answers over 25 seconds", "person", _slow, floor=0.10, min_n=20, covers=("flow:talk", "store:traces")),
    Loop("answers.model_down", "answers", "the model not answering, or garbled", "person",
         _count_of(("model_down", "garbled")), floor=0, covers=("flow:talk", "flow:pc")),
    Loop("answers.undo_soon", "answers", "what she did, undone right away, per 100 turns", "person",
         _per_100_turns(("undo_soon",)), min_n=20, covers=("flow:undo",)),
    Loop("answers.numbers", "answers", "answers with a number she hadn't looked up, per 100 turns", "person",
         _per_100_turns(("invented_number",)), floor=2, min_n=20, files=("core/question_plans.py", "core/tool_loop.py"),
         covers=("flow:talk",)),
    Loop("answers.calibration", "answers", "how much better her sure answers land than the rest (👍 share)", "person",
         _calibration, better="higher", floor=0, min_n=5, files=("core/question_plans.py",),
         covers=("store:ratings",)),
    Loop("answers.projections", "answers", "projected dates (debt-free, freedom) that came true when they came", "person",
         _projections, better="higher", floor=0.5, min_n=3, files=("core/question_plans.py", "core/debt_math.py",
                                                                  "core/freedom.py"), covers=("store:budget",)),
    Loop("memory.quality", "answers", "memories corrected within 14 days of being kept", "person", _memory_quality,
         floor=0.15, min_n=5, files=("core/user_memory_manager.py",), covers=("store:user_memories", "module:memories")),
    # The Operating Journal (DEC-0097): theirs to see, never a task or a nudge (DEC-0014)
    Loop("journal.pace", "life", "how often they operate the way they said they mean to", "person", _journal_pace,
         better="higher", acts="watch", covers=("store:operating_journal", "action:operating",
                                                "check:operating_journal")),
    Loop("recreation.load", "life", "this week's play load against the four weeks before (past 1.5: easing off helps)",
         "person", _play_load, floor=1.5, acts="watch", covers=("store:recreation", "action:play")),
    Loop("news.misleading", "proactivity", "Good News Radio stories they called misleading, in 30 days", "person",
         _news_misleading, floor=0.05, min_n=20, files=("core/good_news.py",), covers=("check:good_news",)),
    Loop("sight.failed", "answers", "photos she couldn't answer about, in 30 days", "person", _sight_failed,
         floor=0.1, min_n=5, files=("core/sight.py",), covers=("flow:sight",)),
    Loop("glasses.voice", "devices", "glasses turns unanswered or slow, in 7 days", "person", _glasses_voice,
         floor=0.15, min_n=10, files=("core/glasses_voice.py",), covers=("flow:glasses",)),
    Loop("phone.link", "devices", "hours since their phone last reached this PC", "person", _phone_link,
         acts="watch", covers=("flow:phone",)),
    Loop("loop.prediction", "corrections", "the Loop's planned work days that didn't match what happened, 4 weeks",
         "person", _loop_prediction, floor=0.3, min_n=8, files=("core/the_loop.py",), covers=("store:loop", "check:loop")),
    Loop("inbox.reading", "corrections", "documents whose read fields were corrected when filed, in 60 days", "person",
         _inbox_reading, floor=0.25, min_n=5, files=("core/inbox_manager.py",), covers=("store:inbox", "action:inbox")),
    Loop("gate.saturation", "proactivity", "days the daily limit of unprompted messages was hit, in 7", "person",
         _gate_saturation, floor=2, covers=("flow:gate",)),
    Loop("gate.unwelcome", "proactivity", "kinds of message on a break for being dismissed", "person", _gate_unwelcome,
         acts="watch", covers=("flow:gate",)),
    # B. Proactivity, and C. corrections (drafted at Night School, T-0047)
    Loop("actions.failed", "corrections", "things approved that broke when they ran, in 7 days", "person",
         _actions_failed, floor=0, files=("core/actions.py",), covers=("flow:actions",)),
    Loop("actions.declined", "corrections", "suggestions she made that were turned down, per 100 turns", "person",
         _per_100_turns(("declined",)), min_n=20, covers=("flow:actions",)),
    Loop("email.discarded", "corrections", "drafts thrown away instead of sent, in 30 days", "person", _email_discarded,
         floor=0.4, min_n=5, files=("core/email_drafts.py",), covers=("flow:email", "store:email_drafts")),
    Loop("email.left_open", "corrections", "drafts left open over a week", "person", _email_left_open, acts="watch",
         covers=("flow:email",)),
    Loop("gate.dismissed", "proactivity", "unprompted messages dismissed, in 7 days", "person", _gate_dismissed,
         floor=0.5, min_n=5, files=("core/communication_gate.py",), covers=("flow:gate", "store:communication")),
    Loop("gate.expired", "proactivity", "messages held back that expired before they went out", "person",
         _gate_expired, acts="watch", min_n=3, covers=("flow:gate",)),
    Loop("checks.dismissed", "proactivity", "the daily check whose messages are dismissed most, in 30 days", "person",
         _checks_dismissed, floor=0.6, min_n=10, files=("core/application.py",),
         covers=tuple(sorted({f"check:{c}" for c in CHECK_TOPICS.values()}))),
    # Theirs to change (DEC-0014: a miss is gentle): a target missed most days is offered for easing, never a task
    Loop("missions.recurring", "life", "daily recurring missions not done, in 30 days", "person", _recurring_missed,
         floor=0.5, min_n=10, acts="offer", covers=("check:recurring_mission",)),
    # C. Corrections in every area (step 4, core/corrections.py): undone, or edited or deleted within 3 days
    Loop("corrections.all", "corrections", "her changes corrected within 3 days, every area", "person", _corrections(),
         floor=0.2, min_n=10, covers=("flow:actions", "flow:undo")),
    *(Loop(f"corrections.{area}", "corrections", f"her changes in {area} corrected within 3 days", "person",
           _corrections(area), floor=0.25, min_n=5) for area in (
        "money", "kitchen", "workouts", "missions", "calendar", "maintenance", "inbox", "memories", "creations",
        "home", "tasks")),
    # D. Her creations
    Loop("creations.maker", "creations", "designs that missed their checks the first time (Make Something)", "person",
         _maker, floor=0.5, min_n=5, files=("core/creation_maker.py",), covers=("module:web_home",)),
    Loop("creations.unused", "creations", "published screens nobody opens", "person", _unused_creations, floor=0,
         acts="offer", covers=("store:creations", "action:creation")),
    Loop("workflows.failing", "creations", "workflow runs that stopped", "person", _failing_workflows, floor=0,
         files=("core/workflows.py",), covers=("flow:workflows", "check:workflows")),
    Loop("creations.held", "creations", "published screens that no longer pass their checks", "person",
         _creations_held, floor=0, files=("core/creation_spec.py",), covers=("store:creations",)),
    # E. Devices
    Loop("data.recovered", "devices", "data files found corrupt and reset, in 7 days", "device", _recovered, floor=0,
         files=("core/data_recovery.py",), covers=("flow:data",)),
    Loop("search.empty", "devices", "Ctrl+K searches that found nothing, in 30 days", "device", _search_empty,
         floor=0.3, min_n=10, files=("core/search_manager.py",), covers=("flow:search",)),
    Loop("pc.disk", "devices", "free space on the PC", "device", _disk, better="higher", floor=20, unit="GB", covers=("flow:pc",)),
    # F. Her development
    Loop("dev.layering", "development", "breaks of the layering rule", "device", _layering, floor=0,
         files=("core/dev_map.py",), covers=("dev:code",)),
    Loop("dev.doc_drift", "development", "files the docs name that don't exist", "device", _doc_drift, floor=0, covers=("dev:code",)),
    Loop("dev.stuck", "development", "tasks claimed for a week or more", "device", _stuck, floor=0,
         covers=("dev:tasks", "dev:missions")),
    Loop("dev.reviewers", "development", "the weakest reviewer's cautious rate", "device", _reviewers,
         better="higher", floor=0.5, covers=("dev:review",)),
    Loop("dev.knowledge", "development", "MIA's write-ups withdrawn", "device", _knowledge, floor=0.3, min_n=5,
         files=("core/dev_knowledge.py",), covers=("dev:knowledge",)),
    Loop("dev.coder", "development", "MIA's coder: shadow attempts passed", "device", _coder, better="higher",
         acts="watch", covers=("dev:shadow",)),
    Loop("dev.limits", "development", "usage limits hit in a week", "device", _limits, acts="watch", covers=("dev:usage",)),
    Loop("dev.council_cost", "development", "calls per council turn", "device", _council_cost, acts="watch", covers=("dev:council",)),
    Loop("dev.chronicles", "development", "Chronicles candidates waiting", "device", _chronicles, acts="watch",
         covers=("dev:chronicles", "check:chronicle")),
    # The weekly benchmarks (step 5, core/benchmarks.py, run by tools/weekly_bench.py from Night School)
    Loop("answers.benchmark", "answers", "benchmark questions that fell since last week", "device",
         _bench("intelligence", "falls"), floor=0, every=7, files=("core/question_plans.py", "core/tool_loop.py"),
         covers=("flow:talk",)),
    Loop("answers.benchmark_clean", "answers", "benchmark questions answered by a plan or code, unflagged", "device",
         _bench("intelligence", "clean"), better="higher", acts="watch", every=7, covers=("flow:talk",)),
    Loop("answers.corpus", "answers", "conversation answers code flagged (filler, closing offers, lists...)", "device",
         _bench("corpus", "flagged"), every=7, files=("core/response_composer.py",), covers=("flow:talk", "flow:glasses")),
    Loop("answers.routing", "answers", "benchmark questions that reach no plan, lookup or tool", "device",
         _bench("routing", "model only"), every=7, files=("core/question_plans.py",), covers=("flow:tools",)),
    Loop("dev.suite", "development", "tests failing on the committed code that aren't known failures", "device",
         _suite_unexpected, floor=0, every=7, heavy=True, covers=("dev:suite",)),
    Loop("dev.suite_time", "development", "seconds the full suite takes", "device", _suite_time, acts="watch",
         every=7, heavy=True, unit="s", covers=("dev:suite",)),
    Loop("dev.reverts", "development", "merges the lab reverted, of those approved in 30 days", "device", _reverts,
         floor=0.2, min_n=3, covers=("dev:merge",)),
    Loop("dev.vulnerable", "development", "installed packages with a known vulnerability", "device", _vulnerable,
         floor=0, every=7, heavy=True, files=("requirements.txt",), covers=("dev:dependencies",)),
    Loop("dev.outdated", "development", "required packages behind their latest release", "device", _outdated,
         acts="watch", every=7, heavy=True, covers=("dev:dependencies",)),
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


def due(loop: Loop, earlier: list[dict], now: datetime) -> bool:
    """Pure logic. A loop is due when it has no reading yet, or its last is `every` days old (by date)."""
    if not earlier:
        return True
    try:
        last = datetime.fromisoformat(earlier[-1].get("at", "")).date()
    except ValueError:
        return True
    return (now.date() - last).days >= loop.every


def run(context, scope: str, now: Optional[datetime] = None, loops: tuple[Loop, ...] = LOOPS, force: bool = False,
        tasks_dir=None, log=None, heavy: bool = False) -> list:
    """Measure every loop of this scope that's due, keep, judge, act. Heavy loops only with `heavy`.
    Returns Candidates to offer."""
    from core.communication_gate import Candidate

    now = now or _now()
    if scope == "device" and not _has_repo():
        return []  # the phone: no development platform here
    store = _store(context, scope)
    past = history(context, scope)
    offers = []
    for loop in (l for l in loops if l.scope == scope):
        earlier = past.get(loop.id, [])
        if (loop.heavy and not heavy) or not (force or due(loop, earlier, now)):
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
