"""
core.calibration
==================

Whether MIA's "how sure" means anything (build plan step 8, DEC-0094): every
question-plan answer is marked sure, likely or unsure in code, from what its
fact sheet holds (core/question_plans.sureness). Each one is noted here, in
the person's own folder, by its plan, its level and a fingerprint of the
answer's words (never the words). When the person rates an answer 👍 or 👎
(core/answer_ratings.py), the fingerprint finds the level it was given, and
`answers.calibration` (core/loops.py) checks that "sure" answers land at
least as well as the rest: being sure has to be earned.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "sureness.jsonl"
_MAX_LINES = 3000
_lock = threading.Lock()


def key(answer: str) -> str:
    """Pure logic. The answer's fingerprint: the same words give the same key, and the key gives no words back."""
    return hashlib.sha256(" ".join(str(answer or "").split()).encode("utf-8")).hexdigest()[:16]


def _folder(context) -> Optional[Path]:
    """The person's folder calibration is kept in (the failure log's, else the traces'), or None."""
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def note(context, plan: str, level: str, answer: str) -> None:
    """Notes how sure an answer was (sureness.jsonl: its plan, its level and a fingerprint of the answer, never its
    words); past 3,000 lines the oldest go, down to 1,800. A write that fails is logged.
    """
    folder = _folder(context)
    if folder is None or not str(answer or "").strip():
        return
    line = {"at": datetime.now().isoformat(timespec="seconds"), "plan": str(plan)[:40], "sure": level, "key": key(answer)}
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with _lock:
            path = folder / FILE_NAME
            with open(path, "a", encoding="utf-8") as out:
                out.write(json.dumps(line) + "\n")
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > _MAX_LINES:
                path.write_text("\n".join(lines[-(_MAX_LINES * 3 // 5):]) + "\n", encoding="utf-8")
    except OSError:
        log.exception("Couldn't note how sure an answer was.")


def notes(context, days: int = 90) -> list[dict]:
    """The notes of the last `days` days (90 by default); a bad line is skipped."""
    folder = _folder(context)
    if folder is None:
        return []
    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    try:
        text = (folder / FILE_NAME).read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        try:
            found = json.loads(line)
        except ValueError:
            continue
        if found.get("at", "") >= since:
            out.append(found)
    return out


# ------------------------------------------------------------------ projections against outcomes (step 8)

PROJECTIONS = "projections.jsonl"
GRACE_DAYS = 31  # a projection that comes true within a month of its date counts as right
KINDS = ("debt_free", "freedom")


def project(context, kind: str, when: str, plan: str = "") -> None:
    """A date MIA projected ("debt-free 2027-08", "freedom 2028-01-07"), kept once per kind and date, to be
    checked when it comes."""
    folder = _folder(context)
    if folder is None or kind not in KINDS or not when:
        return
    path = folder / PROJECTIONS
    try:
        kept = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        kept = []
    if any(p.get("kind") == kind and p.get("when") == when for p in kept):
        return
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with _lock, open(path, "a", encoding="utf-8") as out:
            out.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "when": when,
                                  "plan": plan, "outcome": None}) + "\n")
    except OSError:
        log.exception("Couldn't keep a projection.")


def _due_day(when: str) -> Optional[datetime]:
    """A projected date as a day: YYYY-MM-DD, or YYYY-MM taken as about the 28th; None when it won't read."""
    try:
        return datetime.fromisoformat(when + ("-28" if len(when) == 7 else ""))  # a year-month: its end, roughly
    except ValueError:
        return None


def happened(context, kind: str) -> Optional[bool]:
    """Pure-ish. Whether what a kind of projection said has come true now (None when it can't be told)."""
    budget = getattr(context, "budget", None)
    if kind == "debt_free":
        if budget is None:
            return None
        return all(float(getattr(d, "balance", 0) or 0) <= 0.01 for d in budget.all_debts())
    if kind == "freedom":
        try:
            from datetime import date as _date

            from core import freedom

            inputs, _h = freedom.gather(context, _date.today())
            return bool(freedom.plan(inputs, _date.today()).get("ready"))
        except Exception:
            return None
    return None


def check_due(context, now: Optional[datetime] = None, judge: Optional[Callable] = None) -> int:
    """Projections whose date (and a month's grace) has passed, checked against what happened. Returns how many."""
    folder = _folder(context)
    if folder is None:
        return 0
    path = folder / PROJECTIONS
    try:
        kept = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return 0
    now = now or datetime.now()
    judge = judge or (lambda kind: happened(context, kind))
    done = 0
    for p in kept:
        due = _due_day(p.get("when", ""))
        if p.get("outcome") is not None or due is None or now < due + timedelta(days=GRACE_DAYS):
            continue
        result = judge(p["kind"])
        if result is None:
            continue
        p["outcome"], p["checked"] = ("right" if result else "wrong"), now.isoformat(timespec="seconds")
        done += 1
    if done:
        atomic_write_text(path, "".join(json.dumps(p) + "\n" for p in kept))
    return done


def projections(context) -> list[dict]:
    """Every projection kept (debt-free dates, freedom dates), to check when their day comes."""
    folder = _folder(context)
    try:
        return [json.loads(l) for l in (folder / PROJECTIONS).read_text(encoding="utf-8").splitlines() if l.strip()] \
            if folder else []
    except (OSError, ValueError):
        return []


def rated(context, days: int = 90) -> dict:
    """level -> {"up", "down"}: the person's ratings of answers, by how sure each was marked."""
    ratings = getattr(getattr(context, "ratings", None), "ratings", None) or []
    levels = {n["key"]: n["sure"] for n in notes(context, days)}
    out: dict[str, dict] = {}
    for r in ratings:
        level = levels.get(key(r.get("answer", "")))
        if level is None:
            continue
        row = out.setdefault(level, {"up": 0, "down": 0})
        row["up" if r.get("rating") == "up" else "down"] += 1
    return out
