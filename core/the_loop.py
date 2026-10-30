"""
core.the_loop
===============

The Loop (DEC-0047, step 1; Zac 2026-10-27): the normal week, run as the
same grind every week, and MIA learning *when* it happens so she knows
when to start each part and remind you.

- **A rhythm** is something that recurs: the work dungeon's shifts
  (kind "work", one per dungeon), the household chores (kind "routine":
  the recurring missions of a category, "Household"), or anything the
  person names (kind "custom"), and training (kind "training": the
  fitness plan's training days, owned here since DEC-0052; the plan
  keeps what each day is). Each has the days it happens, when it
  starts and ends (a night shift ends the next morning), and a reminder
  some minutes before it starts.
- **Learned, or yours.** Days and times are learned from what actually
  happened: the days runs were cleared and when (a run is cleared at
  clock-out, so its start is that minus its hours), and when the chores
  get done. Whatever the person says ("my workday is 9:30 pm to 6 am",
  "chores around 2:30") is theirs and is never overwritten by learning.
- **Appears automatically** (DEC-0047 rule 1): a dungeon gets its work
  rhythm and household routines get "Chores" without anyone asking; the
  week's work runs are planned from the rhythm (projected loot), once
  per day, never brought back after being removed.
- **Reminders** go out at the start time minus the lead, once per
  scheduled day, straight to the person like an alarm they set up (they
  asked for these: Zac, 2026-10-27), never for chores already done.
- **A missed day shows honestly** (rule 6): in the week view it earned
  nothing and the week shows the share cleared ("3 of 5 runs, 60%").
  Nothing is taken away (DEC-0014).

Each person's own (a personal store), written through atomic_write_text
so every change can be undone.
"""

from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "loop.json"

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
KINDS = ("work", "routine", "custom", "checkin", "training")
WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")  # the fitness plan's way of saying days
LEARN_WEEKS = 6
MIN_TIMES = 3  # completions before a time is learned
CHORE_LEAD = 30  # chores are learned from when they're done: they start about this many minutes before


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Rhythm:
    rhythm_id: str
    name: str
    kind: str = "custom"
    ref: str = ""  # work: the dungeon id; routine: a recurring-mission category ("Household") or template id
    icon: str = "🔁"
    days: list = field(default_factory=list)  # weekdays, 0 = Monday
    start: str = ""  # "HH:MM"
    end: str = ""  # "HH:MM" (earlier than start: ends the next day)
    days_source: str = ""  # "yours" | "learned" | ""
    start_source: str = ""
    end_source: str = ""
    learned_from: int = 0  # how many times the learned values came from
    lead_minutes: int = 15
    remind: bool = True
    active: bool = True
    created_at: str = ""


# ---------------------------------------------------------------- pure logic: clocks and days


_CLOCK = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\s*$", re.IGNORECASE)


def parse_clock(text: str) -> str:
    """Pure logic. "9:30 pm", "21:30", "2:30pm", "6 am", "noon" -> "HH:MM"."""
    raw = str(text or "").strip().lower()
    if raw in ("noon", "midday"):
        return "12:00"
    if raw == "midnight":
        return "00:00"
    m = _CLOCK.match(raw)
    if not m:
        raise ValueError(f"“{text}” isn't a time (try 9:30 pm or 21:30).")
    hour, minute, half = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").replace(".", "")
    if half:
        if not 1 <= hour <= 12:
            raise ValueError(f"“{text}” isn't a time.")
        hour = hour % 12 + (12 if half.startswith("p") else 0)
    if hour > 23 or minute > 59:
        raise ValueError(f"“{text}” isn't a time.")
    return f"{hour:02d}:{minute:02d}"


def minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def clock(total: int) -> str:
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def clock_text(hhmm: str) -> str:
    """Pure logic. "21:30" -> "9:30 PM"."""
    if not hhmm:
        return ""
    h, m = (int(x) for x in hhmm.split(":"))
    return f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def span_hours(start: str, end: str) -> Optional[float]:
    """Pure logic. Hours from start to end; an end earlier than the start is the next day."""
    if not start or not end:
        return None
    gap = (minutes(end) - minutes(start)) % (24 * 60)
    return round(gap / 60, 2) if gap else None


def typical_minute(values: list[int]) -> Optional[int]:
    """Pure logic. The usual minute of the day, on a clock (11:50 PM and
    12:10 AM average to midnight, not noon), rounded to 5 minutes."""
    if not values:
        return None
    angles = [2 * math.pi * v / 1440 for v in values]
    x, y = sum(math.cos(a) for a in angles), sum(math.sin(a) for a in angles)
    mean = math.atan2(y, x) % (2 * math.pi)
    return int(round(mean / (2 * math.pi) * 1440 / 5) * 5) % 1440


def usual_days(dates: list[date], today: date, weeks: int = LEARN_WEEKS) -> list[int]:
    """Pure logic. The weekdays that came up in at least half of the
    recent weeks that had any at all (and at least twice)."""
    since = today - timedelta(days=7 * weeks)
    recent = sorted({d for d in dates if since <= d <= today})
    if not recent:
        return []
    week_of = lambda d: d - timedelta(days=d.weekday())  # noqa: E731
    weeks_seen = len({week_of(d) for d in recent})
    need = max(2, math.ceil(weeks_seen / 2))
    counts = {wd: len({week_of(d) for d in recent if d.weekday() == wd}) for wd in range(7)}
    return [wd for wd in range(7) if counts[wd] >= need]


_DAY_WORDS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def parse_days(raw) -> list[int]:
    """Pure logic. "mon-fri", "sun-thu", "weekdays", "weekends", "every
    day", "mon, wed, fri", or a list of numbers -> weekdays (0 = Monday)."""
    if isinstance(raw, (list, tuple)):
        return sorted({int(x) % 7 for x in raw})
    text = str(raw or "").strip().lower()
    if text in ("every day", "everyday", "daily", "all week", "7 days"):
        return list(range(7))
    if text in ("weekdays", "mon-fri", "monday-friday", "monday to friday"):
        return [0, 1, 2, 3, 4]
    if text in ("weekends", "weekend"):
        return [5, 6]
    out: set[int] = set()
    for part in re.split(r"[,/&]|\band\b", text):
        part = part.strip()
        if not part:
            continue
        ends = re.split(r"\s*(?:-|–|to|through|thru)\s*", part)
        names = [_DAY_WORDS.get(e.strip()[:3]) for e in ends]
        if any(n is None for n in names):
            raise ValueError(f"“{part}” isn't a day (try mon-fri, sun-thu, weekends).")
        if len(names) == 2:
            a, b = names
            out.update((a + i) % 7 for i in range((b - a) % 7 + 1))
        else:
            out.add(names[0])
    if not out:
        raise ValueError("Which days?")
    return sorted(out)


def days_text(days: list[int]) -> str:
    """Pure logic. [0,1,2,3,4] -> "Mon–Fri"; [6,0,1,2,3] -> "Sun–Thu"."""
    days = sorted(set(days))
    if not days:
        return ""
    if len(days) == 7:
        return "Every day"
    # A run of consecutive days, possibly wrapping past Sunday.
    for first in days:
        run = [(first + i) % 7 for i in range(len(days))]
        if sorted(run) == days:
            return DAY_NAMES[first] if len(days) == 1 else f"{DAY_NAMES[first]}–{DAY_NAMES[run[-1]]}"
    return ", ".join(DAY_NAMES[d] for d in days)


def work_day(start: str, end: str, days: list[int], now: datetime, grace_hours: int = 4) -> date:
    """Pure logic. Which day's shift a run cleared now belongs to: for a
    shift that ends the next morning, clearing it before the end (plus a
    few hours) counts for the day it started."""
    today = now.date()
    if start and end and minutes(end) < minutes(start):
        yesterday = today - timedelta(days=1)
        cutoff = minutes(end) + grace_hours * 60
        if now.hour * 60 + now.minute <= cutoff and (not days or yesterday.weekday() in days):
            return yesterday
    return today


# ---------------------------------------------------------------- the store


class LoopBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        self.rhythms: list[Rhythm] = []
        self.made: dict[str, list[str]] = {}  # rhythm_id -> days its work run was planned (never planned again)
        self.fired: dict[str, str] = {}  # rhythm_id -> the last day its reminder went out
        self.learned_on = ""
        self.checkins: list[str] = []  # the Sundays whose check-in was done
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            self.rhythms = [Rhythm(**{k: v for k, v in d.items() if k in Rhythm.__dataclass_fields__})
                            for d in raw.get("rhythms", [])]
            self.made = {str(k): list(v) for k, v in (raw.get("made") or {}).items()}
            self.fired = {str(k): str(v) for k, v in (raw.get("fired") or {}).items()}
            self.learned_on = str(raw.get("learned_on") or "")
            self.checkins = [str(x) for x in raw.get("checkins") or []]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("loop.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        cutoff = (date.today() - timedelta(days=60)).isoformat()
        self.made = {k: [d for d in v if d >= cutoff] for k, v in self.made.items()}
        atomic_write_text(self._file, json.dumps({"rhythms": [asdict(r) for r in self.rhythms], "made": self.made,
                                                  "fired": self.fired, "learned_on": self.learned_on,
                                                  "checkins": self.checkins[-60:]}, indent=2))

    def get(self, rhythm_id: str) -> Optional[Rhythm]:
        return next((r for r in self.rhythms if r.rhythm_id == rhythm_id), None)

    def find(self, kind: str, ref: str = "") -> Optional[Rhythm]:
        return next((r for r in self.rhythms if r.kind == kind and r.ref == ref), None)

    def add(self, name: str, kind: str = "custom", ref: str = "", icon: str = "🔁", **fields) -> Rhythm:
        if not str(name or "").strip():
            raise ValueError("A rhythm needs a name.")
        if kind not in KINDS:
            raise ValueError("Unknown kind of rhythm.")
        r = Rhythm(rhythm_id=uuid.uuid4().hex[:10], name=name.strip(), kind=kind, ref=ref, icon=icon, created_at=_now())
        for k, v in fields.items():
            setattr(r, k, v)
        self.rhythms.append(r)
        self._save()
        return r

    def set(self, rhythm_id: str, **fields) -> Rhythm:
        """The person's own values: what they set is marked theirs."""
        r = self.get(rhythm_id)
        if r is None:
            raise ValueError("That rhythm isn't there anymore.")
        for name, value in fields.items():
            if name in ("days", "start", "end"):
                setattr(r, name, value)
                setattr(r, name + "_source", "yours" if value not in ("", [], None) else "")
            elif name in ("name", "icon", "lead_minutes", "remind", "active"):
                setattr(r, name, value)
            else:
                raise ValueError(f"A rhythm has no '{name}'.")
        self._save()
        return r

    def forget(self, rhythm_id: str, what: str) -> Rhythm:
        """Let MIA learn it again: the person's value for days or times goes back to learned."""
        r = self.get(rhythm_id)
        if r is None:
            raise ValueError("That rhythm isn't there anymore.")
        for name in (("start", "end") if what == "times" else ("days",)):
            if getattr(r, name + "_source") == "yours":
                setattr(r, name + "_source", "")
                setattr(r, name, [] if name == "days" else "")
        self.learned_on = ""
        self._save()
        return r

    def delete(self, rhythm_id: str) -> None:
        self.rhythms = [r for r in self.rhythms if r.rhythm_id != rhythm_id]
        self._save()

    def note_made(self, rhythm_id: str, day: str) -> None:
        self.made.setdefault(rhythm_id, []).append(day)

    def note_fired(self, rhythm_id: str, day: str) -> None:
        self.fired[rhythm_id] = day
        self._save()

    def save(self) -> None:
        self._save()


# ---------------------------------------------------------------- what recurs, and when


def _routine_templates(context, r: Rhythm) -> list:
    store = getattr(context, "recurring_missions", None)
    if store is None:
        return []
    return [t for t in store.all_templates() if t.active and (t.template_id == r.ref or t.category == r.ref)]


def _routine_missions(context, r: Rhythm, day: Optional[date] = None) -> list:
    """This rhythm's recurring missions (one day's, if asked)."""
    missions = getattr(context, "missions", None)
    ids = {t.template_id for t in _routine_templates(context, r)}
    if missions is None or not ids:
        return []
    return [m for m in missions.all_missions() if m.recurring_template_id in ids and m.recurring_kind in ("daily", "weekly_standalone")
            and (day is None or m.occurrence_key == day.isoformat())]


def _same_person(book, store) -> bool:
    """A store may only use the Loop kept in the same person's folder."""
    return book is not None and store is not None and         Path(getattr(book, "data_dir", "")) == Path(getattr(store, "data_dir", "") or "")


def training_rhythm(context, store=None) -> Optional[Rhythm]:
    """The training rhythm (DEC-0052: the Loop owns which days you
    train), if this person has one."""
    book = getattr(context, "loop", None)
    if book is None or (store is not None and not _same_person(book, store)):
        return None
    return book.find("training", "fitness")


def set_training_days(context, names: list, store=None) -> bool:
    """The person's training days ("Mon", "Wed"...) into their training
    rhythm, made if it isn't there. False when there's no Loop for them
    (the caller keeps the days itself then)."""
    book = getattr(context, "loop", None)
    if book is None or (store is not None and not _same_person(book, store)):
        return False
    days = sorted({WEEKDAY_NAMES.index(n) for n in names if n in WEEKDAY_NAMES})
    r = book.find("training", "fitness")
    if r is None:
        book.add("Training", "training", "fitness", "🏋", days=days, days_source="yours" if days else "",
                 lead_minutes=30)
    else:
        book.set(r.rhythm_id, days=days)  # marked yours (or cleared) by set()
    return True


def ensure_rhythms(context) -> list[Rhythm]:
    """Rule 1: what recurs gets a rhythm by itself. Each dungeon gets its
    work rhythm; household routines get "Chores"."""
    book = getattr(context, "loop", None)
    if book is None:
        return []
    made = []
    dungeons = getattr(context, "dungeon", None)
    for d in (dungeons.dungeons if dungeons else []):
        if book.find("work", d.dungeon_id) is None:
            made.append(book.add(d.name, "work", d.dungeon_id, "⚔", lead_minutes=30))
    if book.find("checkin") is None:
        # DEC-0047 rule 5: Sunday morning, last week's recap and this week's missions.
        made.append(book.add("Sunday Check-In", "checkin", "", "📜", days=[6], start="09:00", lead_minutes=0,
                             days_source="yours", start_source="yours"))
    store = getattr(context, "recurring_missions", None)
    if store is not None and any(t.active and t.category == "Household" for t in store.all_templates()) \
            and book.find("routine", "Household") is None:
        daily = any(t.active and t.category == "Household" and t.recurrence == "daily" for t in store.all_templates())
        made.append(book.add("Chores", "routine", "Household", "🧹", days=list(range(7)) if daily else [],
                             days_source="learned" if daily else ""))
    fitness = getattr(context, "fitness", None)
    if fitness is not None and book.find("training", "fitness") is None and _same_person(book, fitness):
        fitness.move_training_days_to_loop()  # DEC-0052: once, the plan's own days become the rhythm's
        if book.find("training", "fitness") is not None:
            made.append(book.find("training", "fitness"))
    return made


def learn(context, today: Optional[date] = None) -> None:
    """Days and times from what actually happened, for every value that
    isn't the person's own. A run is cleared at clock-out: its end is
    when it was cleared, its start that minus its hours. Chores are
    learned from when they get done."""
    book = getattr(context, "loop", None)
    if book is None:
        return
    today = today or date.today()
    since = today - timedelta(days=7 * LEARN_WEEKS)
    dungeons = getattr(context, "dungeon", None)
    for r in book.rhythms:
        dates: list[date] = []
        starts: list[int] = []
        ends: list[int] = []
        if r.kind == "work" and dungeons is not None:
            dg = dungeons.get_dungeon(r.ref)
            unpaid = float(getattr(dg, "break_minutes", 0) or 0) if dg else 0.0
            for run in dungeons.runs:
                d = _day(run.date)
                if run.dungeon_id != r.ref or run.status != "cleared" or d is None or d < since:
                    continue
                dates.append(d)
                at = _stamp(run.created_at)
                if at is not None and timedelta(0) <= at - datetime.combine(d, time()) <= timedelta(hours=36):
                    end = at.hour * 60 + at.minute
                    ends.append(end)
                    starts.append((end - int(round(run.hours * 60 + unpaid))) % 1440)
        elif r.kind == "routine":
            for m in _routine_missions(context, r):
                at = _stamp(m.updated_at)
                if m.status != "completed" or at is None or at.date() < since:
                    continue
                dates.append(at.date())
                starts.append((at.hour * 60 + at.minute - CHORE_LEAD) % 1440)
        else:
            continue
        if r.days_source != "yours" and r.kind == "work":
            days = usual_days(dates, today)
            if days:
                r.days, r.days_source = days, "learned"
        if len(starts) >= MIN_TIMES:
            if r.start_source != "yours":
                r.start, r.start_source = clock(typical_minute(starts)), "learned"
            if ends and r.end_source != "yours":
                r.end, r.end_source = clock(typical_minute(ends)), "learned"
        r.learned_from = len(dates)
    book.learned_on = today.isoformat()
    book.save()


def _day(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def _stamp(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(text or ""))
    except ValueError:
        return None


def plan_week(context, today: Optional[date] = None, ahead: int = 7) -> int:
    """The week's work runs, planned from the work rhythm (projected
    loot): each scheduled day from today on, once; never again after
    it's been removed. Returns how many were planned."""
    book = getattr(context, "loop", None)
    dungeons = getattr(context, "dungeon", None)
    if book is None or dungeons is None:
        return 0
    today = today or date.today()
    count = 0
    for r in book.rhythms:
        d = dungeons.get_dungeon(r.ref) if r.kind == "work" else None
        if d is None or not r.active or not r.days:
            continue
        hours = paid_hours(r, d)
        if not hours:
            continue
        for i in range(ahead + 1):
            day = today + timedelta(days=i)
            key = day.isoformat()
            if day.weekday() not in r.days or key in book.made.get(r.rhythm_id, []):
                continue
            if any(run.dungeon_id == d.dungeon_id and run.date == key for run in dungeons.runs):
                book.note_made(r.rhythm_id, key)
                continue
            dungeons.add_run(d.dungeon_id, key, hours, status="planned", note="From the loop")
            book.note_made(r.rhythm_id, key)
            count += 1
    book.save()
    return count


def paid_hours(r: Rhythm, d) -> float:
    """Pure logic. A work run's paid hours: time at work minus the unpaid
    break (9:30 PM – 6 AM with a 30-minute break pays 8), else the
    dungeon's usual shift."""
    span = span_hours(r.start, r.end)
    if not span:
        return float(d.shift_hours or 0)
    return round(max(0.0, span - float(getattr(d, "break_minutes", 0) or 0) / 60), 2)


def shift_day_for(context, dungeon_id: str, now: Optional[datetime] = None) -> date:
    """The day a run cleared now belongs to (a night shift's start day)."""
    now = now or datetime.now()
    book = getattr(context, "loop", None)
    r = book.find("work", dungeon_id) if book is not None else None
    if r is None:
        return now.date()
    return work_day(r.start, r.end, r.days, now)


# ---------------------------------------------------------------- reminders


def reminders(context, now: Optional[datetime] = None) -> list[tuple[Rhythm, str, str]]:
    """What's due to be said now: each active rhythm scheduled today
    whose start minus its lead has come (and its start was under an hour
    ago), once a day. Chores only when some are still to do."""
    book = getattr(context, "loop", None)
    if book is None:
        return []
    now = now or datetime.now()
    today = now.date()
    out = []
    for r in book.rhythms:
        if not (r.active and r.remind and r.start) or today.weekday() not in (r.days or (range(7) if r.kind == "custom" else ())):
            continue
        if book.fired.get(r.rhythm_id) == today.isoformat():
            continue
        start = datetime.combine(today, time(*(int(x) for x in r.start.split(":"))))
        if not (start - timedelta(minutes=r.lead_minutes) <= now < start + timedelta(hours=1)):
            continue
        said = _reminder(context, r, today, start)
        if said is None:
            book.note_fired(r.rhythm_id, today.isoformat())  # nothing to do today: nothing to say
            continue
        out.append((r, *said))
    return out


def _reminder(context, r: Rhythm, today: date, start: datetime) -> Optional[tuple[str, str]]:
    when = clock_text(r.start)
    if r.kind == "work":
        dungeons = getattr(context, "dungeon", None)
        d = dungeons.get_dungeon(r.ref) if dungeons else None
        if d is None:
            return None
        run = next((x for x in dungeons.runs if x.dungeon_id == d.dungeon_id and x.date == today.isoformat()), None)
        if run is not None and run.status == "cleared":
            return None
        hours = run.hours if run else paid_hours(r, d)
        text = f"{d.name} opens at {when}" + (f" until {clock_text(r.end)}" if r.end else "") + f": {_a(hours)} {hours:g}-hour run"
        if d.break_minutes:
            text += f" (plus your {d.break_minutes:g}-minute break)"
        if d.hourly and run is not None:
            from core.region import money
            from core.work_dungeon import loot, split_hours

            regular, overtime = split_hours(d, dungeons.runs, include_planned=True)[run.run_id]
            text += f", about {money(loot(d, regular, overtime))} loot" + (" (boss loot in it)" if overtime else "")
        return "⚔ The dungeon opens soon", text + "."
    if r.kind == "routine":
        open_ = [m for m in _routine_missions(context, r, today) if m.status != "completed"]
        if not open_:
            return None
        names = ", ".join(m.name.split(" — ")[0] for m in open_[:4])
        return f"{r.icon} {r.name} time", f"Usually around {when}: {len(open_)} to do today ({names})."
    if r.kind == "checkin":
        from core.weekly_checkin import reminder_line

        return reminder_line(context, today)
    if r.kind == "training":
        fitness = getattr(context, "fitness", None)
        todays = fitness.today_training(today) if fitness is not None else None
        if not todays or todays.get("done"):
            return None
        return f"{r.icon} Training day", f"{todays.get('name') or 'Training'} at {when}."
    return f"{r.icon} {r.name}", f"{r.name} at {when}."


def _a(hours: float) -> str:
    """Pure logic. "an 8-hour", "an 11-hour", "a 10-hour"."""
    return "an" if f"{hours:g}".startswith(("8", "11", "18")) else "a"


def tick(context, now: Optional[datetime] = None) -> int:
    """Every few minutes (core/application.py): give new recurring things
    a rhythm, learn once a day, plan the week's runs, and send what's
    due. Returns how many reminders went out."""
    book = getattr(context, "loop", None)
    if book is None:
        return 0
    now = now or datetime.now()
    ensure_rhythms(context)
    if book.learned_on != now.date().isoformat():
        learn(context, now.date())
        plan_week(context, now.date())
    sent = 0
    for r, title, message in reminders(context, now):
        # Like an alarm the person set up (they asked for these), straight to them, phone included.
        if getattr(context, "notifications", None) is not None:
            context.notifications.notify(title=title, message=message, source="loop", always=True)
        book.note_fired(r.rhythm_id, now.date().isoformat())
        sent += 1
    return sent


# ---------------------------------------------------------------- the week


def week(context, today: Optional[date] = None, start: Optional[date] = None) -> dict:
    """This week's loop (Monday first, or any seven days from `start`):
    each rhythm's scheduled days and how each went. A past scheduled day
    with nothing done earned nothing (shown plainly); the share cleared
    is the week's honest score."""
    from core.region import money

    book = getattr(context, "loop", None)
    today = today or date.today()
    monday = start or today - timedelta(days=today.weekday())
    days = [monday + timedelta(days=i) for i in range(7)]
    rows = []
    dungeons = getattr(context, "dungeon", None)
    for r in (book.rhythms if book else []):
        if not r.active or r.kind == "checkin":
            continue
        cells, scheduled, done = [], 0, 0
        split = {}
        d = dungeons.get_dungeon(r.ref) if (r.kind == "work" and dungeons) else None
        if d is not None:
            from core.work_dungeon import loot, split_hours

            split = split_hours(d, dungeons.runs, include_planned=True)
        since = _day(r.created_at) or monday
        for day in days:
            key = day.isoformat()
            # Days before the loop knew this rhythm aren't counted as missed.
            on = day.weekday() in (r.days or []) and day >= since
            cell = {"date": key, "on": on, "status": "off", "text": ""}
            if d is not None:
                run = next((x for x in dungeons.runs if x.dungeon_id == d.dungeon_id and x.date == key), None)
                worth = loot(d, *split[run.run_id]) if run is not None and run.run_id in split and d.hourly else None
                if run is not None and run.status == "cleared":
                    cell.update(status="cleared", text=money(worth) if worth is not None else f"{run.hours:g} h")
                elif on or run is not None:
                    status = "missed" if day < today else ("today" if day == today else "planned")
                    cell.update(status=status, text=money(0) if status == "missed" and d.hourly else
                                (money(worth) if worth is not None else ""))
            elif r.kind == "routine":
                ms = _routine_missions(context, r, day)
                if ms:
                    finished = sum(1 for m in ms if m.status == "completed")
                    status = "cleared" if finished == len(ms) else ("missed" if day < today else
                                                                     "today" if day == today else "planned")
                    cell.update(status=status, text=f"{finished}/{len(ms)}")
                elif on:
                    cell.update(status="missed" if day < today else ("today" if day == today else "planned"))
            elif r.kind == "training":
                fitness = getattr(context, "fitness", None)
                trained = fitness is not None and any(t["date"] == key for t in fitness.training_days_done(key))
                if trained:
                    cell.update(status="cleared")
                elif on:
                    cell.update(status="missed" if day < today else ("today" if day == today else "planned"))
            elif on:
                cell.update(status="planned" if day >= today else "off")
            if cell["status"] != "off":
                scheduled += 1
                done += cell["status"] == "cleared"
            cells.append(cell)
        to_go = sum(1 for c in cells if c["status"] in ("today", "planned"))
        so_far = scheduled - to_go
        rows.append({"id": r.rhythm_id, "name": r.name, "icon": r.icon, "kind": r.kind, "cells": cells,
                     "scheduled": scheduled, "cleared": done, "so_far": so_far, "to_go": to_go,
                     # The honest score: of the days already past, how many were cleared.
                     "pct": round(100 * done / so_far) if so_far else None,
                     "missed": sum(1 for c in cells if c["status"] == "missed")})
    return {"start": monday.isoformat(), "days": [{"date": x.isoformat(), "label": DAY_NAMES[x.weekday()],
                                                   "today": x == today} for x in days], "rows": rows}


def rhythm_view(r: Rhythm) -> dict:
    hours = span_hours(r.start, r.end)
    learned = r.learned_from
    return {"id": r.rhythm_id, "name": r.name, "kind": r.kind, "icon": r.icon, "days": r.days,
            "days_text": days_text(r.days), "start": r.start, "end": r.end,
            "start_text": clock_text(r.start), "end_text": clock_text(r.end), "hours": hours,
            "days_source": r.days_source, "start_source": r.start_source, "end_source": r.end_source,
            "learned_from": learned, "lead_minutes": r.lead_minutes, "remind": r.remind, "active": r.active,
            "line": ((days_text(r.days) or "Days not known yet") + " · " +
                     (clock_text(r.start) + (f" – {clock_text(r.end)}" if r.end else "") if r.start else "time not known yet"))}


def loop_page(context, today: Optional[date] = None) -> dict:
    book = getattr(context, "loop", None)
    if book is None:
        return {"available": False}
    ensure_rhythms(context)
    dungeons = getattr(context, "dungeon", None)
    views = []
    for r in book.rhythms:
        v = rhythm_view(r)
        d = dungeons.get_dungeon(r.ref) if (r.kind == "work" and dungeons) else None
        if d is not None and v["hours"]:
            v["paid_hours"] = paid_hours(r, d)
            v["break_minutes"] = d.break_minutes
        views.append(v)
    return {"available": True, "rhythms": views, "week": week(context, today)}
