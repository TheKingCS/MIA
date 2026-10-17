"""
core.grow_lab
===============

The grow lab (DEC-0030 phase D): running a greenhouse, aquaponics tanks
and growing beds like a scientist. Record what's planted, measure the
water, compare what works, learn from the results.

- **Batches**: a crop (and variety) planted somewhere (a tank, a bed),
  when, how many, what it cost; then harvests (how much) or losses (why).
  From those: days to first harvest, yield per plant, how many were lost.
- **Systems and readings**: each place has measurements (pH, ammonia,
  nitrite, nitrate, dissolved oxygen, water and air temperature, anything
  else). Readings live in the shared Data Logger (core/data_logger_manager.py,
  series `grow:<system>:<measure>`), so a sensor later is just another
  writer there.
- **Your own safe ranges**: each measure has a range the person sets.
  A few common starting points are offered (and labelled that way); MIA
  only **warns** when a reading is outside it. She never controls a pump,
  a heater or a feeder: people decide anything that affects fish, plants
  or equipment (human oversight, DEC-0030).
- **Experiments**: a question ("Which lettuce does best in Tank A?"), the
  batches that answer it side by side, and the conclusion you write.

A household store, written through atomic_write_text so it can be undone.
Planting, harvests and losses are life events (the Chronicle tells them).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "grow_lab.json"

MEASURES = {  # measure: (label, unit)
    "ph": ("pH", ""), "ammonia": ("Ammonia", "ppm"), "nitrite": ("Nitrite", "ppm"), "nitrate": ("Nitrate", "ppm"),
    "oxygen": ("Dissolved oxygen", "mg/L"), "water_temp": ("Water temperature", "°"), "air_temp": ("Air temperature", "°"),
    "humidity": ("Humidity", "%"), "ec": ("EC", "mS/cm"),
}
# Common starting points for an aquaponics system, offered for the person
# to confirm or change for their own fish and plants; never applied silently.
STARTER_RANGES = {"ph": (6.8, 7.2), "ammonia": (0.0, 1.0), "nitrite": (0.0, 1.0), "nitrate": (5.0, 150.0),
                  "oxygen": (5.0, None)}
BATCH_STATUSES = ("Growing", "Harvested", "Lost")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Batch:
    batch_id: str
    crop: str
    variety: str = ""
    system: str = ""  # where: "Tank A", "Bed 2", "Greenhouse"
    method: str = ""  # aquaponics, soil, hydroponic…
    planted: str = ""  # ISO date
    count: int = 0  # plants or seeds
    cost: float = 0.0
    status: str = "Growing"
    harvests: list[dict] = field(default_factory=list)  # {date, amount, unit, note}
    lost: int = 0
    loss_note: str = ""
    notes: str = ""
    created_at: str = ""


@dataclass
class Experiment:
    experiment_id: str
    question: str
    batch_ids: list[str] = field(default_factory=list)
    conclusion: str = ""
    status: str = "Running"  # Running | Concluded
    created_at: str = ""


def series_id(system: str, measure: str) -> str:
    """Pure logic. The Data Logger series for one measure in one system."""
    return f"grow:{' '.join(system.split()).lower()}:{measure}"


def check_range(value: float, low: Optional[float], high: Optional[float]) -> str:
    """Pure logic. "low", "high" or "" (in range, or no range set)."""
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return ""


def batch_figures(b: Batch, today: date) -> dict:
    """Pure logic. Days growing, days to first harvest, total yield (by unit),
    yield per plant, and how many survived."""
    try:
        planted = date.fromisoformat(b.planted) if b.planted else None
    except ValueError:
        planted = None
    dates = sorted(h["date"] for h in b.harvests if h.get("date"))
    first = date.fromisoformat(dates[0]) if dates else None
    totals: dict[str, float] = {}
    for h in b.harvests:
        totals[h.get("unit") or ""] = round(totals.get(h.get("unit") or "", 0.0) + float(h.get("amount") or 0), 3)
    plants = max(0, b.count - b.lost)
    main_unit, main_total = max(totals.items(), key=lambda kv: kv[1], default=("", 0.0))
    return {"days_growing": (today - planted).days if planted else None,
            "days_to_harvest": (first - planted).days if planted and first else None,
            "yield": totals, "main_yield": main_total, "main_unit": main_unit,
            "per_plant": round(main_total / plants, 3) if plants and main_total else None,
            "survival": round(100 * plants / b.count) if b.count else None}


class GrowLab:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        self.batches: list[Batch] = []
        self.experiments: list[Experiment] = []
        self.systems: list[str] = []
        self.ranges: dict[str, dict] = {}  # "system|measure" → {low, high}
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            pick = lambda cls, d: cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # noqa: E731
            self.batches = [pick(Batch, d) for d in raw.get("batches", [])]
            self.experiments = [pick(Experiment, d) for d in raw.get("experiments", [])]
            self.systems = [str(s) for s in raw.get("systems", [])]
            self.ranges = {str(k): dict(v) for k, v in (raw.get("ranges") or {}).items()}
        except (json.JSONDecodeError, OSError, TypeError, AttributeError, ValueError):
            log.exception("grow_lab.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({
            "batches": [asdict(b) for b in self.batches], "experiments": [asdict(e) for e in self.experiments],
            "systems": self.systems, "ranges": self.ranges}, indent=2))

    def _record(self, type_: str, summary: str, refs: list[str]) -> None:
        from core import life_events

        life_events.record(self, type_, summary, refs)

    # ---------------------------------------------------------------- systems and ranges

    def add_system(self, name: str) -> str:
        name = " ".join(str(name or "").split())
        if not name:
            raise ValueError("Name the tank, bed or room.")
        if name.lower() not in (s.lower() for s in self.systems):
            self.systems.append(name)
            self._save()
        return name

    def remove_system(self, name: str) -> None:
        self.systems = [s for s in self.systems if s.lower() != name.lower()]
        self._save()

    def set_range(self, system: str, measure: str, low: Optional[float], high: Optional[float]) -> None:
        if measure not in MEASURES:
            raise ValueError("Unknown measure.")
        if low is not None and high is not None and low > high:
            raise ValueError("The low end has to be below the high end.")
        self.ranges[f"{system.lower()}|{measure}"] = {"low": low, "high": high}
        self._save()

    def range_for(self, system: str, measure: str) -> tuple[Optional[float], Optional[float], bool]:
        """(low, high, set by the person). Unset: the starter range, flagged as not theirs."""
        mine = self.ranges.get(f"{system.lower()}|{measure}")
        if mine is not None:
            return mine.get("low"), mine.get("high"), True
        low, high = STARTER_RANGES.get(measure, (None, None))
        return low, high, False

    # ---------------------------------------------------------------- batches

    def get_batch(self, batch_id: str) -> Optional[Batch]:
        return next((b for b in self.batches if b.batch_id == batch_id), None)

    def add_batch(self, crop: str, **fields) -> Batch:
        if not str(crop or "").strip():
            raise ValueError("What's planted?")
        b = Batch(batch_id=uuid.uuid4().hex[:10], crop=crop.strip(), planted=date.today().isoformat(), created_at=_now())
        self._apply(b, fields)
        b.planted = b.planted or date.today().isoformat()
        if b.system:
            self.add_system(b.system)
        self.batches.append(b)
        self._save()
        self._record("batch_planted", f"Planted {b.count or ''} {b.crop}{' (' + b.variety + ')' if b.variety else ''}"
                     .replace("  ", " ") + (f" in {b.system}" if b.system else ""), [f"batch:{b.batch_id}"])
        return b

    def update_batch(self, batch_id: str, **fields) -> Batch:
        b = self.get_batch(batch_id)
        if b is None:
            raise ValueError("That batch isn't there anymore.")
        self._apply(b, fields)
        if b.system:
            self.add_system(b.system)
        self._save()
        return b

    def delete_batch(self, batch_id: str) -> None:
        self.batches = [b for b in self.batches if b.batch_id != batch_id]
        for e in self.experiments:
            e.batch_ids = [i for i in e.batch_ids if i != batch_id]
        self._save()

    @staticmethod
    def _apply(b: Batch, fields: dict) -> None:
        for name, value in fields.items():
            if name in ("batch_id", "harvests", "created_at") or not hasattr(b, name):
                raise ValueError(f"A batch has no '{name}'.")
            if name == "count" or name == "lost":
                value = max(0, int(float(value or 0)))
            elif name == "cost":
                value = max(0.0, float(value or 0))
            elif name == "status" and value not in BATCH_STATUSES:
                raise ValueError("Unknown status.")
            setattr(b, name, value if value is not None else "")

    def harvest(self, batch_id: str, amount: float, unit: str = "", note: str = "", done: bool = False,
                on: Optional[str] = None) -> Batch:
        b = self.get_batch(batch_id)
        if b is None:
            raise ValueError("That batch isn't there anymore.")
        if amount <= 0:
            raise ValueError("How much was harvested?")
        b.harvests.append({"date": on or date.today().isoformat(), "amount": round(float(amount), 3),
                           "unit": unit.strip(), "note": note.strip()})
        if done:
            b.status = "Harvested"
        self._save()
        self._record("harvest", f"Harvested {amount:g} {unit.strip()} of {b.crop}".replace("  ", " "), [f"batch:{b.batch_id}"])
        return b

    def lose(self, batch_id: str, how_many: int, why: str = "", all_of_it: bool = False) -> Batch:
        b = self.get_batch(batch_id)
        if b is None:
            raise ValueError("That batch isn't there anymore.")
        b.lost = min(b.count, b.lost + max(0, int(how_many))) if b.count else b.lost + max(0, int(how_many))
        b.loss_note = "; ".join(x for x in (b.loss_note, why.strip()) if x)
        if all_of_it:
            b.status = "Lost"
        self._save()
        return b

    # ---------------------------------------------------------------- experiments

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return next((e for e in self.experiments if e.experiment_id == experiment_id), None)

    def add_experiment(self, question: str, **fields) -> Experiment:
        if not str(question or "").strip():
            raise ValueError("What's the question?")
        e = Experiment(experiment_id=uuid.uuid4().hex[:10], question=question.strip(), created_at=_now())
        self._apply_experiment(e, fields)
        self.experiments.append(e)
        self._save()
        return e

    def update_experiment(self, experiment_id: str, **fields) -> Experiment:
        e = self.get_experiment(experiment_id)
        if e is None:
            raise ValueError("That experiment isn't there anymore.")
        self._apply_experiment(e, fields)
        self._save()
        return e

    def delete_experiment(self, experiment_id: str) -> None:
        self.experiments = [e for e in self.experiments if e.experiment_id != experiment_id]
        self._save()

    def _apply_experiment(self, e: Experiment, fields: dict) -> None:
        for name, value in fields.items():
            if name == "batch_ids":
                value = [i for i in (value if isinstance(value, list) else str(value or "").split(","))
                         if i and self.get_batch(i.strip()) is not None]
                value = [i.strip() for i in value]
            elif name not in ("question", "conclusion", "status"):
                raise ValueError(f"An experiment has no '{name}'.")
            setattr(e, name, value if value is not None else "")
