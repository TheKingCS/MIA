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
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "sureness.jsonl"
_MAX_LINES = 3000
_lock = threading.Lock()


def key(answer: str) -> str:
    """Pure logic. The answer's fingerprint: the same words give the same key, and the key gives no words back."""
    return hashlib.sha256(" ".join(str(answer or "").split()).encode("utf-8")).hexdigest()[:16]


def _folder(context) -> Optional[Path]:
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def note(context, plan: str, level: str, answer: str) -> None:
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
