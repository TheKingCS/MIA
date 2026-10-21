"""
core.flock
============

Chickens (DEC-0037): a flock log that turns eggs into money you can see.

- **Flocks**: a name, the breed, how many hens (and roosters), when they
  came. Birds added or lost change the count and are kept as a log.
- **Eggs**: how many were collected, day by day. Loose eggs on hand are
  what was collected minus what went into cartons, into the bakery or
  onto the table.
- **Feed**: what was bought (pounds and cost). With the eggs, the feed
  cost per dozen over the last 30 days.
- **Where the eggs go**: **Carton** puts dozens into goods on hand (a
  recipe for the eggs, with their date and sell-by; core/goods_actions.py
  add_to_stock) at the feed cost per dozen; **For baking** puts eggs into
  Materials at the feed cost per egg, so the banana bread's cost is real;
  **Eaten at home** just takes them off the count.

The numbers are worked out from the log (pure functions below), never
kept twice. A household store, written through atomic_write_text so
every change can be undone; eggs collected are a life event.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "flock.json"

USES = ("carton", "baking", "home")  # where loose eggs go


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Flock:
    flock_id: str
    name: str
    breed: str = ""
    hens: int = 0
    roosters: int = 0
    started: str = ""  # when they came, YYYY-MM-DD
    egg_recipe_id: str = ""  # the good its cartons go into (a Workshop recipe)
    notes: str = ""
    created_at: str = ""


@dataclass
class Entry:
    """One line of the log. kind: eggs (count), feed (pounds, cost), birds
    (count: + added, − lost; note why), use (count of eggs; use: carton,
    baking or home)."""
    entry_id: str
    flock_id: str
    kind: str
    date: str
    count: float = 0.0
    pounds: float = 0.0
    cost: float = 0.0
    use: str = ""
    note: str = ""


def _day(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def figures(flock: Flock, entries: list[Entry], today: date) -> dict:
    """Pure logic. A flock's numbers from its log: eggs today, this week
    (the last 7 days), the lay rate (eggs a hen a day over those days),
    loose eggs on hand, feed cost per dozen (last 30 days), and where the
    eggs went."""
    mine = [e for e in entries if e.flock_id == flock.flock_id]
    week = today - timedelta(days=6)
    month = today - timedelta(days=29)

    def total(kind: str, since: Optional[date] = None, use: str = "") -> float:
        return sum(e.count for e in mine if e.kind == kind and (not use or e.use == use)
                   and (since is None or (_day(e.date) or today) >= since))

    collected = total("eggs")
    used = {u: total("use", use=u) for u in USES}
    week_eggs = total("eggs", week)
    days = min(7, max(1, (today - (_day(flock.started) or week)).days + 1)) if flock.started else 7
    hens = max(0, int(flock.hens))
    month_eggs = total("eggs", month)
    feed_cost = sum(e.cost for e in mine if e.kind == "feed" and (_day(e.date) or today) >= month)
    per_dozen = round(feed_cost / (month_eggs / 12), 2) if month_eggs and feed_cost else 0.0
    return {
        "today": total("eggs", today), "week": week_eggs, "month": month_eggs, "collected": collected,
        "lay_rate": round(week_eggs / (hens * days), 2) if hens else None,
        "loose": round(max(0.0, collected - sum(used.values()) * 1.0), 2),
        "feed_cost_month": round(feed_cost, 2), "feed_per_dozen": per_dozen,
        "feed_per_egg": round(per_dozen / 12, 4) if per_dozen else 0.0,
        "used": used,
    }


def week_series(flock_id: str, entries: list[Entry], today: date, days: int = 14) -> list[dict]:
    """Pure logic. Eggs per day for the last `days` days, oldest first."""
    counts: dict[str, float] = {}
    for e in entries:
        if e.flock_id == flock_id and e.kind == "eggs":
            counts[e.date[:10]] = counts.get(e.date[:10], 0.0) + e.count
    return [{"date": d, "eggs": counts.get(d, 0.0)}
            for d in ((today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1))]


class FlockBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        self.flocks: list[Flock] = []
        self.entries: list[Entry] = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            pick = lambda cls, d: cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # noqa: E731
            self.flocks = [pick(Flock, d) for d in raw.get("flocks", [])]
            self.entries = [pick(Entry, d) for d in raw.get("entries", [])]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("flock.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"flocks": [asdict(f) for f in self.flocks],
                                                  "entries": [asdict(e) for e in self.entries]}, indent=2))

    # ---------------------------------------------------------------- flocks

    def get_flock(self, flock_id: str) -> Optional[Flock]:
        return next((f for f in self.flocks if f.flock_id == flock_id), None)

    def add_flock(self, name: str, **fields) -> Flock:
        if not str(name or "").strip():
            raise ValueError("A flock needs a name.")
        f = Flock(flock_id=uuid.uuid4().hex[:10], name=name.strip(), created_at=_now())
        self._apply(f, fields)
        self.flocks.append(f)
        self._save()
        return f

    def update_flock(self, flock_id: str, **fields) -> Flock:
        f = self.get_flock(flock_id)
        if f is None:
            raise ValueError("That flock isn't there anymore.")
        self._apply(f, fields)
        self._save()
        return f

    def delete_flock(self, flock_id: str) -> None:
        self.flocks = [f for f in self.flocks if f.flock_id != flock_id]
        self.entries = [e for e in self.entries if e.flock_id != flock_id]
        self._save()

    @staticmethod
    def _apply(f: Flock, fields: dict) -> None:
        for name, value in fields.items():
            if name in ("flock_id", "created_at") or not hasattr(f, name):
                raise ValueError(f"A flock has no '{name}'.")
            if name in ("hens", "roosters"):
                value = max(0, int(float(value or 0)))
            setattr(f, name, value if value is not None else "")

    # ---------------------------------------------------------------- the log

    def log(self, flock_id: str, kind: str, on: str = "", **fields) -> Entry:
        if self.get_flock(flock_id) is None:
            raise ValueError("That flock isn't there anymore.")
        if kind not in ("eggs", "feed", "birds", "use"):
            raise ValueError("Unknown kind.")
        if kind == "use" and fields.get("use") not in USES:
            raise ValueError("Eggs go into a carton, the bakery or the kitchen.")
        entry = Entry(entry_id=uuid.uuid4().hex[:10], flock_id=flock_id, kind=kind,
                      date=(on or date.today().isoformat())[:10],
                      **{k: v for k, v in fields.items() if k in ("count", "pounds", "cost", "use", "note")})
        self.entries.append(entry)
        if kind == "birds":
            f = self.get_flock(flock_id)
            f.hens = max(0, f.hens + int(entry.count))
        self._save()
        if kind == "eggs":
            from core import life_events

            life_events.record(self, "eggs_collected", f"Collected {entry.count:g} eggs",
                               [f"flock:{flock_id}"], {"eggs": entry.count})
        return entry

    def delete_entry(self, entry_id: str) -> None:
        entry = next((e for e in self.entries if e.entry_id == entry_id), None)
        if entry is None:
            raise ValueError("That entry isn't there anymore.")
        if entry.kind == "birds":
            f = self.get_flock(entry.flock_id)
            if f is not None:
                f.hens = max(0, f.hens - int(entry.count))
        self.entries = [e for e in self.entries if e.entry_id != entry_id]
        self._save()

    def entries_for(self, flock_id: str) -> list[Entry]:
        return sorted((e for e in self.entries if e.flock_id == flock_id), key=lambda e: e.date)  # stable: as logged
