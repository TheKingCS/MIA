"""
core.sensors
==============

Sensors that send their own readings (claude, 2026-11-09; DEC-0019: the computer adds sensors; DEC-0125: the
Greenhouse, Power and the Lab had readings by hand only). A sensor is anything on the home network that can make an
HTTP request (an ESP32, a Raspberry Pi, a smart plug's script): it sends one number at a time and MIA logs it exactly
as a reading typed in by hand, through that app's own reading action.

- **A sensor is added by a person** (`SensorStore.add`): its name and the one series it feeds: the Lab's series, a
  Power source's meter, or a Greenhouse place's measure (`TARGETS`). MIA makes it a key, shown once and kept only as
  its hash. Adding it is the person's say-so for every reading it sends, so a reading needs no approval card.
- **A key can do one thing**: log a number to its own series. It can't read anything, can't choose another series,
  and isn't a sign-in. A reading is refused when it isn't a number, comes sooner than MIN_GAP after the last one, or
  the sensor's been removed.
- **Readings run as the person who added it** (their own view), through the reading action (`lab_reading.add`,
  `energy.reading`, `grow.reading`), so ranges, charts and findings treat it like any other reading.

The store is the device's (data/sensors.json, like the model and the voice: what's wired to this computer), each
sensor naming the person it belongs to. Written through atomic_write_text. Served by `/api/sensors` (list, add) and
`/api/sensors/reading` (a sensor's reading, its key in X-Sensor-Key); removing one is the action `sensor.remove`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILE = "sensors.json"
MIN_GAP = 30  # seconds between one sensor's readings
MAX_SENSORS = 50

# app -> (its reading action, the target fields a sensor names (field, label), how the action's params are made)
TARGETS = {
    "lab": ("lab_reading.add", (("series", "The series (e.g. soil moisture)"), ("unit", "Unit (optional)")),
            lambda t, v, note: {"series": t["series"], "value": v, "unit": t.get("unit", ""), "note": note}),
    "power": ("energy.reading", (("source_id", "The energy source"), ("meter", "What it measures (e.g. battery %)"),
                                 ("unit", "Unit (optional)")),
              lambda t, v, note: {"source_id": t["source_id"], "meter": t["meter"], "value": v,
                                  "unit": t.get("unit", ""), "note": note}),
    "greenhouse": ("grow.reading", (("place", "The tank or bed"), ("measure", "What it measures (e.g. pH)")),
                   lambda t, v, note: {"place": t["place"], "measure": t["measure"], "value": v, "note": note}),
}
APP_NAMES = {"lab": "The Lab", "power": "Power", "greenhouse": "Greenhouse"}


class SensorError(ValueError):
    """A sensor that can't be added, or a reading that can't be logged, with why in a sentence."""


def _hash(key: str) -> str:
    """Pure logic. What's kept of a key: its SHA-256."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def target_words(sensor: dict) -> str:
    """Pure logic. Where a sensor's readings go, in words: "The Lab: soil moisture (%)"."""
    t = sensor.get("target") or {}
    app = APP_NAMES.get(sensor.get("app", ""), sensor.get("app", ""))
    measure = t.get("measure", "")
    if sensor.get("app") == "greenhouse":
        from core.grow_lab import MEASURES

        measure = MEASURES.get(measure, (measure, ""))[0]
    what = {"lab": t.get("series", ""), "power": f"{t.get('meter', '')}", "greenhouse":
            f"{t.get('place', '')} {measure}".strip()}.get(sensor.get("app", ""), "")
    unit = f" ({t['unit']})" if t.get("unit") else ""
    return f"{app}: {what}{unit}"


class SensorStore:
    """The sensors added on this device (data/sensors.json): each with its name, app and target, whose it is, its
    key's hash, and its last reading."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Points at data/sensors.json (or `data_dir`) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / FILE
        self._load()

    def _load(self) -> None:
        """Reads the sensors; a missing or unreadable file gives none (logged)."""
        self.sensors: list[dict] = []
        if not self._file.exists():
            return
        try:
            self.sensors = list(json.loads(self._file.read_text(encoding="utf-8")).get("sensors", []))
        except (OSError, ValueError, AttributeError):
            log.exception("%s unreadable; no sensors.", FILE)

    def reload(self) -> None:
        """Reads the file again (after undo put it back)."""
        self._load()

    def _save(self) -> None:
        """Writes the sensors atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"sensors": self.sensors}, indent=1))

    def mine(self, profile_id: str) -> list[dict]:
        """A person's sensors, without their key hashes."""
        return [{k: v for k, v in s.items() if k != "key_hash"} | {"goes_to": target_words(s)}
                for s in self.sensors if s.get("profile_id") == profile_id]

    def add(self, profile_id: str, name: str, app: str, target: dict) -> tuple[dict, str]:
        """Adds a sensor for a person and returns it with its key (the only time the key is ever seen). SensorError
        for an unknown app, a missing target field, a greenhouse measure the grow lab doesn't keep, or too many."""
        if app not in TARGETS:
            raise SensorError("A sensor feeds the Lab, Power or the Greenhouse.")
        name = " ".join(str(name or "").split())[:60]
        if not name:
            raise SensorError("Give the sensor a name, like “Tank 1 pH probe”.")
        fields = TARGETS[app][1]
        clean = {f: " ".join(str(target.get(f) or "").split())[:60] for f, _label in fields}
        missing = [label for f, label in fields if not clean[f] and "optional" not in label]
        if missing:
            raise SensorError(f"Say {missing[0].split(' (')[0].lower()} for it.")
        if app == "greenhouse":  # the grow lab's own measures (pH, ammonia...), by id or by name
            from core.grow_lab import MEASURES

            said = clean["measure"].lower()
            found = next((m for m, (label, _u) in MEASURES.items() if said in (m, label.lower())), None)
            if found is None:
                raise SensorError("A greenhouse sensor measures one of: "
                                  + ", ".join(label for label, _u in MEASURES.values()) + ".")
            clean["measure"] = found
        if len(self.sensors) >= MAX_SENSORS:
            raise SensorError(f"That's {MAX_SENSORS} sensors already; remove one first.")
        key = "mia-s-" + secrets.token_urlsafe(24)
        sensor = {"id": uuid.uuid4().hex[:10], "name": name, "app": app, "target": clean, "profile_id": profile_id,
                  "key_hash": _hash(key), "created": datetime.now().isoformat(timespec="seconds"),
                  "last_at": "", "last_value": None, "count": 0}
        self.sensors.append(sensor)
        self._save()
        return {k: v for k, v in sensor.items() if k != "key_hash"} | {"goes_to": target_words(sensor)}, key

    def get(self, sensor_id: str) -> Optional[dict]:
        """The sensor with this id, or None."""
        return next((s for s in self.sensors if s["id"] == sensor_id), None)

    def remove(self, sensor_id: str) -> dict:
        """Removes a sensor (its key stops working at once); SensorError when it's gone."""
        found = self.get(sensor_id)
        if found is None:
            raise SensorError("That sensor isn't here any more.")
        self.sensors = [s for s in self.sensors if s["id"] != sensor_id]
        self._save()
        return found

    def by_key(self, key: str) -> Optional[dict]:
        """The sensor a key belongs to (compared in constant time), or None."""
        wanted = _hash(str(key or ""))
        return next((s for s in self.sensors if hmac.compare_digest(s.get("key_hash", ""), wanted)), None)

    def note(self, sensor: dict, value: float, at: datetime) -> None:
        """Records a sensor's latest reading (when, what, how many so far)."""
        sensor["last_at"], sensor["last_value"] = at.isoformat(timespec="seconds"), value
        sensor["count"] = int(sensor.get("count") or 0) + 1
        self._save()


def reading(context, view_for, key: str, raw_value, note: str = "", now: Optional[datetime] = None) -> dict:
    """A sensor's reading: finds its sensor by key, checks the value and the gap since its last one, logs it through its
    app's reading action as the person who added it (`view_for(context, profile_id)`), and returns {sensor, value,
    said}. SensorError when the key isn't a sensor's, the value isn't a number, or it came too soon."""
    from core.actions import ACTION_TYPES, ActionError

    store = getattr(context, "sensors", None)
    sensor = store.by_key(key) if store is not None else None
    if sensor is None:
        raise SensorError("That isn't a sensor's key on this MIA.")
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise SensorError("A reading is one number.") from None
    if value != value or value in (float("inf"), float("-inf")):
        raise SensorError("A reading is one number.")
    now = now or datetime.now()
    if sensor.get("last_at"):
        try:
            gap = (now - datetime.fromisoformat(sensor["last_at"])).total_seconds()
        except ValueError:
            gap = MIN_GAP
        if 0 <= gap < MIN_GAP:
            raise SensorError(f"Too soon: one reading every {MIN_GAP} seconds at most.")
    kind, _fields, make = TARGETS[sensor["app"]]
    view = view_for(context, sensor["profile_id"])
    params = make(sensor["target"], round(value, 4), " ".join(str(note or f"from {sensor['name']}").split())[:120])
    try:
        ACTION_TYPES[kind].describe(view, params)
        said = ACTION_TYPES[kind].execute(view, params)
    except ActionError as problem:
        raise SensorError(str(problem)) from None
    store.note(sensor, round(value, 4), now)
    return {"sensor": sensor["id"], "value": round(value, 4), "said": said}


def screen(context, profile_id: str) -> dict:
    """The Sensors page: the person's sensors (name, where its readings go, the last one and when, how many), what
    each app needs to name a target (with the Power sources, Greenhouse places and measures, and Lab series they have,
    to pick from), and the standard."""
    store = getattr(context, "sensors", None)
    if store is None:
        return {"available": False, "sensors": []}
    picks = {"source_id": [], "place": [], "series": [], "measure": []}
    power = getattr(context, "energy", None)
    try:
        picks["source_id"] = [{"value": s.source_id, "label": s.name} for s in power.all_energy_sources()] if power else []
    except Exception:  # noqa: BLE001 - a missing list only means typing it
        picks["source_id"] = []
    grow = getattr(context, "grow_lab", None)
    try:
        picks["place"] = [{"value": p, "label": p} for p in (grow.systems if grow else [])]
    except Exception:  # noqa: BLE001
        picks["place"] = []
    from core.grow_lab import MEASURES

    picks["measure"] = [{"value": m, "label": label} for m, (label, _u) in MEASURES.items()]
    logger = getattr(context, "data_logger", None)
    try:
        picks["series"] = [{"value": s, "label": s} for s in (logger.list_series() if logger else [])]
    except Exception:  # noqa: BLE001
        picks["series"] = []
    return {"available": True, "sensors": sorted(store.mine(profile_id), key=lambda s: s["name"].lower()),
            "apps": [{"id": a, "name": APP_NAMES[a], "fields": [{"name": f, "label": label} for f, label in TARGETS[a][1]]}
                     for a in TARGETS],
            "picks": picks, "min_gap": MIN_GAP,
            "standard": "A sensor's key can only log a number to its own series: it can't read anything or sign in. "
                        "It's shown once; remove the sensor and the key stops working."}


# ------------------------------------------------------------------ the action

def _describe_remove(context, params) -> str:
    """The sentence for `sensor.remove`; ActionError when it's gone or not the person's."""
    from core.actions import ActionError, _need

    found = _need(context, "sensors").get(str(params.get("sensor_id") or ""))
    if found is None:
        raise ActionError("That sensor isn't here any more.")
    return f"Remove the sensor {found['name']} ({target_words(found)}); its key stops working, its readings stay"


def _remove(context, params) -> str:
    """Does `sensor.remove`."""
    from core.actions import ActionError, _need

    try:
        found = _need(context, "sensors").remove(str(params.get("sensor_id") or ""))
    except SensorError as problem:
        raise ActionError(str(problem)) from None
    return f"Removed {found['name']}. Its readings stay where they are."


def _register() -> None:
    """Adds `sensor.remove` to ACTION_TYPES."""
    from core.actions import ACTION_TYPES, ActionType

    ACTION_TYPES["sensor.remove"] = ActionType("sensor.remove", "Remove", {"sensor_id": "the sensor"},
                                               _describe_remove, _remove)


_register()
