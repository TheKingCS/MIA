"""
core.net_worth_history
========================

Net worth over time, for the line on Money's Overview (DEC-0113, the
design canvas's Money artboard: "net worth, +$X this month, and its
line"). MIA only ever knew net worth *now* (core/finance_summary.py's
`_net_worth`: each linked account's latest total plus property equity);
this keeps one point a day so there is a line to draw.

- **One point a day**: the day's total as MIA worked it out, the last
  reading of the day wins. A day nobody looked at has no point; the line
  just joins the days that do. Nothing is filled in or guessed.
- **Recorded when it's read**: `note()` is called by the Money screen's
  read (core/web_money.py) and writes only when today's point is missing
  or the total changed, so re-reading never writes (and so never bumps
  /api/live into a loop).
- **The change this month**: today's total less the first point of this
  month (or the last one before it, when the month has none yet). None
  when there is nothing to compare with, never a made-up zero.

Everything except `NetWorthHistory` is pure logic. The store writes
through atomic_write_text, so "undo that" restores it (core/undo_log.py).
It sits beside the budget (core/personal_data.py: a household store, and
the person's own when they keep their money private).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "net_worth_history.json"
KEEP_DAYS = 2 * 366  # two years of points
LINE_DAYS = 180  # the Overview's line: the last six months


def _r(value) -> float:
    """Pure logic. A number rounded to cents."""
    return round(float(value), 2)


def add_point(points: list, day: date, total: Optional[float]) -> bool:
    """Pure logic. Puts the day's total into `points` ([{"date", "total"}], oldest first), replacing that day's
    earlier reading, and drops points older than KEEP_DAYS. Returns True when anything changed; a None total
    (nothing to add up) changes nothing."""
    if total is None:
        return False
    key, total = day.isoformat(), _r(total)
    if points and points[-1].get("date") == key:
        if points[-1].get("total") == total:
            return False
        points[-1]["total"] = total
    else:
        points.append({"date": key, "total": total})
        points.sort(key=lambda p: p.get("date", ""))
    cutoff = (day - timedelta(days=KEEP_DAYS)).isoformat()
    points[:] = [p for p in points if p.get("date", "") >= cutoff]
    return True


def month_change(points: list, today: date) -> Optional[float]:
    """Pure logic. How much net worth moved this month: today's total (the latest point) less the first point of
    this month, or the last one before the month when the month has only today. None with fewer than two points
    to compare."""
    if not points:
        return None
    start = today.replace(day=1).isoformat()
    latest = points[-1]
    earlier = [p for p in points[:-1] if p.get("date", "") < start]
    this_month = [p for p in points[:-1] if p.get("date", "") >= start]
    base = this_month[0] if this_month else (earlier[-1] if earlier else None)
    return None if base is None else _r(latest["total"] - base["total"])


def line(points: list, today: date, days: int = LINE_DAYS) -> list[dict]:
    """Pure logic. The points for the Overview's line: the last `days` days, oldest first."""
    since = (today - timedelta(days=days)).isoformat()
    return [{"date": p["date"], "total": p["total"]} for p in points if p.get("date", "") >= since]


def summary(points: list, today: date) -> dict:
    """Pure logic. What Money's Overview shows beside the total: the change this month, and the line."""
    return {"month_change": month_change(points, today), "line": line(points, today)}


class NetWorthHistory:
    """One net worth point a day (household, beside the budget; core/personal_data.py)."""

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the history file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads the points; an unreadable file is logged and means none yet."""
        self.points: list[dict] = []
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8")) if self._file.exists() else []
        except (OSError, ValueError):
            log.exception("%s unreadable; starting the line again.", _FILE)
            raw = []
        self.points = [p for p in raw if isinstance(p, dict) and "date" in p and "total" in p]

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def note(self, total: Optional[float], today: Optional[date] = None) -> None:
        """Keeps today's total, writing only when it's new or changed."""
        if add_point(self.points, today or date.today(), total):
            self.data_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self._file, json.dumps(self.points, indent=1), encoding="utf-8")

    def summary(self, today: Optional[date] = None) -> dict:
        """The change this month and the line, for Money's Overview."""
        return summary(self.points, today or date.today())
