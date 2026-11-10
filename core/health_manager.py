"""
core.health_manager
=====================

Health and Fitness's records (DEC-0129, Zac 2026-11-08: "sleep, doctor and
dentist visits, medications and supplements, health records... are good").
One personal store, `health.json` in the person's own folder, sealed at rest
(core/at_rest.SEALED, DEC-0126), never on a shared screen and never sent
anywhere. Facts are kept as the person gives them; MIA never infers a
condition, a dose or a diagnosis.

- **Sleep:** a night's hours and how rested (1 to 5), by tap or voice.
  `sleep_week(today)` is the last seven nights for the page.
- **Visits:** doctor, dentist, eye and other: when, who, what for, notes,
  and when the next one is due (Today shows it as it comes up).
- **Medications and supplements:** the name and dose as written, the
  times to take it (each a daily alarm labelled only "Medication time", so
  the name never shows on a shared screen), refills left and the next
  refill date (Today shows it three days ahead), active or stopped, and
  each dose taken (`take`).
- **Records:** test results, vaccinations, allergies and other documents
  as notes with a date (a value and units for a result).

Every change is an action in core/health_actions.py (undo restores the
file); the store writes through `atomic_write_text`. A night logged, a
visit, a medication or a record added is noted in the person's own
history (2026-11-09: sleep_logged, visit_added, medication_added,
health_record_added) without its name or details, since the history can
be read back aloud: "logged a night's sleep", never what or how much.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core import life_events
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "health.json"
VISIT_KINDS = ("Doctor", "Dentist", "Eye", "Other")
RECORD_KINDS = ("Test result", "Vaccination", "Allergy", "Document", "Other")
DOSE_LABEL = "Medication time"  # the alarm's words: never the medication's name (a shared screen can show alarms)
SOON_DAYS = 3


def _id() -> str:
    """A new record id."""
    return uuid.uuid4().hex[:10]


def clean_times(times) -> list[str]:
    """Pure logic. The times to take something as sorted "HH:MM" (24-hour), from a list or "8:00, 20:00"; ValueError for
    one that isn't a time."""
    if isinstance(times, str):
        times = [t for t in times.replace(";", ",").split(",")]
    out = set()
    for raw in times or []:
        raw = str(raw).strip().lower()
        if not raw:
            continue
        pm = raw.endswith("pm")
        am = raw.endswith("am")
        raw = raw.rstrip("apm ").strip()
        hour, _, minute = raw.partition(":")
        h, m = int(hour), int(minute or 0)
        if pm and h < 12:
            h += 12
        if am and h == 12:
            h = 0
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError(f"{raw} isn't a time of day.")
        out.add(f"{h:02d}:{m:02d}")
    return sorted(out)


class HealthStore:
    """The person's health records: nights of sleep, visits, medications and supplements (with doses taken), and
    records."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads health.json from the person's folder (or data/); a file that won't open starts empty (at_rest keeps a
        copy aside)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self._load()

    def _load(self) -> None:
        """Reads the file (sealed or plain)."""
        from core.at_rest import open_text

        self.sleep: list[dict] = []
        self.visits: list[dict] = []
        self.meds: list[dict] = []
        self.doses: list[dict] = []
        self.records: list[dict] = []
        if not self._file.exists():
            return
        try:
            data = json.loads(open_text(self._file))
        except (OSError, ValueError):
            log.exception("Health: couldn't read %s; starting empty", self._file)
            return
        if not isinstance(data, dict):
            log.error("Health: %s isn't a health file; starting empty", self._file)
            return
        for key in ("sleep", "visits", "meds", "doses", "records"):
            setattr(self, key, list(data.get(key) or []))

    def _save(self) -> None:
        """Writes the file atomically (sealed at rest where the PC can)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "sleep": self.sleep, "visits": self.visits,
                                                  "meds": self.meds, "doses": self.doses, "records": self.records},
                                                 indent=2))

    # ------------------------------------------------------------- sleep
    @life_events.on_change("sleep_logged", "a night's sleep", named=False)
    def log_sleep(self, hours: float, rested: Optional[int] = None, night: Optional[str] = None, note: str = "") -> dict:
        """Logs a night (the night before `night`, by default last night): hours (0 to 24) and how rested, 1 to 5; a
        night logged again is replaced."""
        hours = float(hours)
        if not 0 <= hours <= 24:
            raise ValueError("Hours of sleep are between 0 and 24.")
        if rested is not None:
            rested = int(rested)
            if not 1 <= rested <= 5:
                raise ValueError("How rested is 1 (not at all) to 5 (fully).")
        night = night or (date.today() - timedelta(days=1)).isoformat()
        date.fromisoformat(night)
        self.sleep = [s for s in self.sleep if s["night"] != night]
        entry = {"id": _id(), "night": night, "hours": round(hours, 2), "rested": rested, "note": note.strip()}
        self.sleep.append(entry)
        self.sleep.sort(key=lambda s: s["night"])
        self._save()
        return entry

    def sleep_week(self, today: Optional[date] = None) -> dict:
        """The last seven nights ({night, hours, rested} or None for one not logged, oldest first) and their average."""
        today = today or date.today()
        by_night = {s["night"]: s for s in self.sleep}
        nights = [(today - timedelta(days=n)).isoformat() for n in range(7, 0, -1)]
        rows = [by_night.get(n) for n in nights]
        logged = [r["hours"] for r in rows if r]
        return {"nights": [{"night": n, **({"hours": r["hours"], "rested": r["rested"]} if r else {"hours": None,
                                                                                                "rested": None})}
                           for n, r in zip(nights, rows)],
                "average": round(sum(logged) / len(logged), 1) if logged else None}

    # ------------------------------------------------------------- visits
    @life_events.on_change("visit_added", "a health visit", named=False)
    def add_visit(self, kind: str, when: str, who: str = "", what_for: str = "", notes: str = "",
                  next_due: str = "") -> dict:
        """Adds a visit (a past one, or one booked) with when the next is due."""
        if kind not in VISIT_KINDS:
            kind = "Other"
        date.fromisoformat(when)
        if next_due:
            date.fromisoformat(next_due)
        visit = {"id": _id(), "kind": kind, "when": when, "who": who.strip(), "what_for": what_for.strip(),
                 "notes": notes.strip(), "next_due": next_due}
        self.visits.append(visit)
        self._save()
        return visit

    def update_visit(self, visit_id: str, **fields) -> dict:
        """Changes a visit's fields (kind, when, who, what_for, notes, next_due)."""
        visit = self._find(self.visits, visit_id, "visit")
        for key in ("kind", "when", "who", "what_for", "notes", "next_due"):
            if key in fields and fields[key] is not None:
                if key in ("when", "next_due") and fields[key]:
                    date.fromisoformat(fields[key])
                visit[key] = fields[key]
        self._save()
        return visit

    # ------------------------------------------------------------- medications
    @life_events.on_change("medication_added", "a medication or supplement", named=False)
    def add_med(self, name: str, dose: str = "", times=None, kind: str = "Medication", refills: Optional[int] = None,
                refill_on: str = "", notes: str = "") -> dict:
        """Adds a medication or supplement as written: its dose, the times to take it (each gets a daily alarm),
        refills left and the next refill date."""
        if not name.strip():
            raise ValueError("What's it called?")
        if refill_on:
            date.fromisoformat(refill_on)
        med = {"id": _id(), "name": name.strip(), "kind": "Supplement" if kind == "Supplement" else "Medication",
               "dose": dose.strip(), "times": clean_times(times), "refills": refills, "refill_on": refill_on,
               "notes": notes.strip(), "active": True, "alarm_ids": [], "added": date.today().isoformat()}
        med["alarm_ids"] = self._alarms_for(med["times"])
        self.meds.append(med)
        self._save()
        return med

    def update_med(self, med_id: str, **fields) -> dict:
        """Changes a medication's fields; new times replace its alarms; stopping it (active False) removes them."""
        med = self._find(self.meds, med_id, "medication")
        for key in ("name", "dose", "refills", "refill_on", "notes", "active"):
            if key in fields and fields[key] is not None:
                med[key] = fields[key]
        if "times" in fields and fields["times"] is not None:
            med["times"] = clean_times(fields["times"])
        self._drop_alarms(med)
        med["alarm_ids"] = self._alarms_for(med["times"]) if med.get("active", True) else []
        self._save()
        return med

    def remove_med(self, med_id: str) -> dict:
        """Removes a medication and its alarms (its doses taken stay in the log)."""
        med = self._find(self.meds, med_id, "medication")
        self._drop_alarms(med)
        self.meds = [m for m in self.meds if m["id"] != med_id]
        self._save()
        return med

    def take(self, med_id: str, at: Optional[datetime] = None) -> dict:
        """Logs a dose taken now (or at `at`)."""
        med = self._find(self.meds, med_id, "medication")
        dose = {"med_id": med["id"], "at": (at or datetime.now()).isoformat(timespec="minutes")}
        self.doses.append(dose)
        self.doses = self.doses[-2000:]
        self._save()
        return dose

    def taken_today(self, med_id: str, today: Optional[date] = None) -> int:
        """How many doses of it were logged today."""
        day = (today or date.today()).isoformat()
        return sum(1 for d in self.doses if d["med_id"] == med_id and d["at"].startswith(day))

    def _alarms_for(self, times: list[str]) -> list[str]:
        """Daily alarms for the times, labelled only DOSE_LABEL; [] where there are no alarms."""
        alarms = getattr(self.context, "alarms", None)
        if alarms is None:
            return []
        return [alarms.add_alarm(DOSE_LABEL, t, days=list(range(7))).alarm_id for t in times]

    def _drop_alarms(self, med: dict) -> None:
        """Removes a medication's alarms (any already gone are skipped)."""
        alarms = getattr(self.context, "alarms", None)
        for alarm_id in med.get("alarm_ids") or []:
            try:
                if alarms is not None:
                    alarms.delete_alarm(alarm_id)
            except Exception:
                log.debug("Health: alarm %s already gone", alarm_id)
        med["alarm_ids"] = []

    # ------------------------------------------------------------- records
    @life_events.on_change("health_record_added", "a health record", named=False)
    def add_record(self, kind: str, name: str, when: str = "", value: str = "", notes: str = "") -> dict:
        """Adds a record: a test result (with its value), a vaccination, an allergy or a document, as given."""
        if not name.strip():
            raise ValueError("What is it?")
        if when:
            date.fromisoformat(when)
        record = {"id": _id(), "kind": kind if kind in RECORD_KINDS else "Other", "name": name.strip(), "when": when,
                  "value": value.strip(), "notes": notes.strip()}
        self.records.append(record)
        self._save()
        return record

    # ------------------------------------------------------------- shared
    def remove(self, section: str, item_id: str) -> dict:
        """Removes a night, a visit or a record (medications use remove_med)."""
        rows = {"sleep": self.sleep, "visits": self.visits, "records": self.records}[section]
        item = self._find(rows, item_id, section)
        setattr(self, section, [r for r in rows if r["id"] != item_id])
        self._save()
        return item

    @staticmethod
    def _find(rows: list, item_id: str, what: str) -> dict:
        """The row with this id; KeyError when it's gone."""
        for row in rows:
            if row["id"] == item_id:
                return row
        raise KeyError(f"That {what} isn't there anymore.")

    def due(self, today: Optional[date] = None) -> list[dict]:
        """What's coming up, for Today: visits due within SOON_DAYS (or past due) and refills due within SOON_DAYS.
        [{what, title, when (ISO), days}]."""
        today = today or date.today()
        out = []
        for v in self.visits:
            if v.get("next_due"):
                days = (date.fromisoformat(v["next_due"]) - today).days
                if days <= SOON_DAYS:
                    out.append({"what": "visit", "id": v["id"], "title": f"{v['kind']} visit due",
                                "when": v["next_due"], "days": days})
        for m in self.meds:
            if m.get("active", True) and m.get("refill_on"):
                days = (date.fromisoformat(m["refill_on"]) - today).days
                if days <= SOON_DAYS:
                    out.append({"what": "refill", "id": m["id"], "title": f"Refill {m['name']}", "when": m["refill_on"],
                                "days": days})
        return sorted(out, key=lambda d: d["days"])
