"""
core.work_dungeon
===================

The Dungeon (DEC-0046, Zac 2026-10-27): work as a dungeon you visit and
loot every day, stacking resources until you can advance to the next
one. MIA is the Game Master: she turns the day's real trouble into the
level you're clearing, honestly (the trouble stays real) and without
making anyone a villain.

- **A dungeon** is a job: its gross pay an hour, overtime (after how
  many hours a week, at what multiple), the day its pay week starts,
  what the paycheck says in the bank (to find it among the deposits),
  and, if the person knows it, the share they take home.
- **A run** is a shift: the day, the hours, and any **hard-mode
  modifiers** (AFFIXES: bare shelves, a thin party, a supply raid...).
  A run is planned (on the schedule) or cleared (worked). Missing a
  planned run costs nothing (DEC-0014): it just waits to be cleared or
  removed.
- **Loot** is gross pay, worked out here: each pay week's hours fill the
  regular hours first, in order, and the rest is overtime. A run with
  overtime in it is a **boss**: its bonus loot is the overtime premium.
- **Projected loot**: this week and this month as cleared plus planned,
  and the year at the last four weeks' pace.
- **Banked loot** comes from the bank (Plaid imports income into the
  budget): the deposits whose description holds the paycheck's words,
  else everything filed as Salary. Against the loot earned over the
  same weeks it tells the share that actually reaches the bank.
- **The next dungeon** is the Freedom plan (core/freedom.py): how far
  along it is, and how much of it one run moves.

The hard-mode record (which days had which modifier) is a plain fact
log: if the person ever wants to raise it at work, the dates are there.
Nobody's name is stored.

Each person's own (a personal store; money is never a child's), written
through atomic_write_text so every change can be undone. The numbers
are worked out from the runs (pure functions below), never kept twice.
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
_FILE = "work_dungeon.json"

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class Affix:
    """A hard-mode modifier: the real trouble, and its name in the game."""
    affix_id: str
    name: str  # the game's name
    real: str  # the plain words for what happened
    line: str  # the Game Master's framing
    xp: int  # bonus XP for clearing a run with it
    words: tuple = ()  # how people say it (Game Master mode notices these)


AFFIXES: tuple[Affix, ...] = (
    Affix("unstocked", "Bare Shelves", "came in unstocked",
          "The stage preparers left you the advanced map: restock first, then clear the run.", 6,
          ("unstocked", "un stocked", "not stocked", "didn't stock", "didnt stock", "nothing stocked", "empty shelves",
           "left us empty", "left us nothing", "no stock", "out of stock", "wasn't stocked", "wasnt stocked")),
    Affix("short_staffed", "Thin Party", "short-staffed",
          "Fewer heroes on the floor today: every role you cover is a class you're leveling.", 6,
          ("short staffed", "short-staffed", "short handed", "short-handed", "called out", "call outs", "callouts",
           "no one showed", "nobody showed", "understaffed")),
    Affix("mess", "Cursed Room", "left a mess",
          "The last party left the room cursed: cleansing it first is part of the clear.", 4,
          ("left a mess", "left it a mess", "trashed", "didn't clean", "didnt clean", "filthy", "a mess")),
    Affix("truck", "Supply Raid", "a truck to unload",
          "A supply drop landed: break it down and the whole dungeon is stocked for the next run.", 4,
          ("truck", "delivery", "shipment", "unload")),
    Affix("breakdown", "Broken Gear", "equipment down",
          "Your gear's out of action: improvising around it is how veterans are made.", 5,
          ("broke down", "broken", "machine down", "line down", "down again", "not working")),
    Affix("rush", "Swarm", "slammed",
          "A swarm wave: hold the line one wave at a time.", 5,
          ("slammed", "swamped", "rush", "nonstop", "non stop", "crazy busy", "so busy")),
    Affix("new_task", "Uncharted Room", "something new",
          "A room you've never cleared: first clears teach the most.", 4,
          ("first time", "never done", "new task", "trained on", "learning")),
)
AFFIX_BY_ID = {a.affix_id: a for a in AFFIXES}
BOSS_XP = 15  # clearing a run with overtime in it


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Dungeon:
    dungeon_id: str
    name: str
    hourly: float = 0.0  # gross pay an hour
    overtime_multiplier: float = 1.5
    overtime_after: float = 40.0  # hours a pay week before overtime (0: no overtime)
    week_starts: str = "Monday"  # the pay week's first day
    take_home_pct: float = 0.0  # share kept after taxes, if known (0: learn it from the bank)
    payer: str = ""  # words the paycheck deposit has in the bank ("ACME PAYROLL")
    shift_hours: float = 8.0  # a usual run (paid hours)
    break_minutes: float = 0.0  # an unpaid break in each shift (Zac, 2026-10-27: 30 minutes, so 8.5 h at work pays 8)
    notes: str = ""
    created_at: str = ""


@dataclass
class Run:
    run_id: str
    dungeon_id: str
    date: str
    hours: float = 0.0
    status: str = "cleared"  # cleared | planned
    affixes: list = field(default_factory=list)  # AFFIX ids, or the person's own words
    boss: bool = False  # called in for overtime (a boss even before the hours say so)
    note: str = ""
    created_at: str = ""


def _day(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------- pure logic


def week_of(day: date, week_starts: str = "Monday") -> date:
    """Pure logic. The first day of the pay week `day` is in."""
    first = DAYS.index(week_starts) if week_starts in DAYS else 0
    return day - timedelta(days=(day.weekday() - first) % 7)


def split_hours(dungeon: Dungeon, runs: list[Run], include_planned: bool = False) -> dict[str, tuple[float, float]]:
    """Pure logic. Each run's (regular, overtime) hours: in each pay week
    the hours fill the regular ones first, in date order, and what's past
    `overtime_after` is overtime. Planned runs count only when asked (a
    projection), and always after the cleared ones of the same day."""
    mine = [r for r in runs if r.dungeon_id == dungeon.dungeon_id and (include_planned or r.status == "cleared")]
    mine.sort(key=lambda r: (r.date, r.status != "cleared", r.created_at))
    used: dict[date, float] = {}
    out: dict[str, tuple[float, float]] = {}
    limit = float(dungeon.overtime_after or 0)
    for r in mine:
        d = _day(r.date)
        if d is None:
            continue
        week = week_of(d, dungeon.week_starts)
        hours = max(0.0, float(r.hours or 0))
        if limit <= 0:
            out[r.run_id] = (hours, 0.0)
            continue
        before = used.get(week, 0.0)
        regular = max(0.0, min(hours, limit - before))
        out[r.run_id] = (round(regular, 2), round(hours - regular, 2))
        used[week] = before + hours
    return out


def loot(dungeon: Dungeon, regular: float, overtime: float) -> float:
    """Pure logic. Gross pay for these hours."""
    rate = float(dungeon.hourly or 0)
    return round(regular * rate + overtime * rate * float(dungeon.overtime_multiplier or 1), 2)


def boss_bonus(dungeon: Dungeon, overtime: float) -> float:
    """Pure logic. What overtime pays beyond the same hours at the regular rate."""
    return round(overtime * float(dungeon.hourly or 0) * max(0.0, float(dungeon.overtime_multiplier or 1) - 1), 2)


def run_xp(hours: float, affixes: list, boss: bool) -> int:
    """Pure logic. XP for a cleared run: 10, +1 an hour (up to 12),
    each hard-mode modifier's bonus, and the boss bonus."""
    xp = 10 + min(12, int(max(0.0, hours)))
    xp += sum(AFFIX_BY_ID[a].xp if a in AFFIX_BY_ID else 3 for a in affixes)
    return xp + (BOSS_XP if boss else 0)


def detect_affixes(text: str) -> list[str]:
    """Pure logic. The hard-mode modifiers someone's words describe
    ("2nd shift left us unstocked again" -> ["unstocked"])."""
    low = " " + str(text or "").lower().replace("’", "'") + " "
    return [a.affix_id for a in AFFIXES if any(w in low for w in a.words)]


def affix_names(affixes: list) -> list[str]:
    return [AFFIX_BY_ID[a].name if a in AFFIX_BY_ID else str(a) for a in affixes]


def parse_affixes(raw) -> list[str]:
    """Pure logic. A list or a comma-separated string -> modifier ids
    (a game name or its plain words works too); anything else is kept as
    the person's own words."""
    items = raw if isinstance(raw, (list, tuple)) else str(raw or "").split(",")
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        low = text.lower()
        found = next((a.affix_id for a in AFFIXES if low in (a.affix_id, a.name.lower(), a.real.lower())), None)
        found = found or (detect_affixes(text) or [None])[0]
        value = found or text[:40]
        if value not in out:
            out.append(value)
    return out


def take_home_share(dungeon: Dungeon, banked: float, earned: float) -> tuple[Optional[float], str]:
    """Pure logic. The share of gross pay that reaches the bank: the
    person's own number, else learned from the deposits against the loot
    earned over the same weeks (only when it looks like a paycheck's
    share), else unknown."""
    if dungeon.take_home_pct and 0 < dungeon.take_home_pct <= 100:
        return round(dungeon.take_home_pct / 100, 4), "your number"
    if earned > 0 and banked > 0 and 0.4 <= banked / earned <= 1.0:
        return round(banked / earned, 4), "your deposits"
    return None, ""


# ---------------------------------------------------------------- the store


class DungeonBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        self.dungeons: list[Dungeon] = []
        self.runs: list[Run] = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            pick = lambda cls, d: cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # noqa: E731
            self.dungeons = [pick(Dungeon, d) for d in raw.get("dungeons", [])]
            self.runs = [pick(Run, d) for d in raw.get("runs", [])]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("work_dungeon.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"dungeons": [asdict(d) for d in self.dungeons],
                                                  "runs": [asdict(r) for r in self.runs]}, indent=2))

    # ---------------------------------------------------------------- dungeons

    def get_dungeon(self, dungeon_id: str) -> Optional[Dungeon]:
        return next((d for d in self.dungeons if d.dungeon_id == dungeon_id), None)

    def add_dungeon(self, name: str, **fields) -> Dungeon:
        if not str(name or "").strip():
            raise ValueError("A dungeon needs a name (the job, the store...).")
        d = Dungeon(dungeon_id=uuid.uuid4().hex[:10], name=name.strip(), created_at=_now())
        self._apply(d, fields)
        self.dungeons.append(d)
        self._save()
        return d

    def update_dungeon(self, dungeon_id: str, **fields) -> Dungeon:
        d = self.get_dungeon(dungeon_id)
        if d is None:
            raise ValueError("That dungeon isn't there anymore.")
        self._apply(d, fields)
        self._save()
        return d

    def delete_dungeon(self, dungeon_id: str) -> None:
        self.dungeons = [d for d in self.dungeons if d.dungeon_id != dungeon_id]
        self.runs = [r for r in self.runs if r.dungeon_id != dungeon_id]
        self._save()

    @staticmethod
    def _apply(d: Dungeon, fields: dict) -> None:
        for name, value in fields.items():
            if name in ("dungeon_id", "created_at") or not hasattr(d, name):
                raise ValueError(f"A dungeon has no '{name}'.")
            if name in ("hourly", "overtime_multiplier", "overtime_after", "take_home_pct", "shift_hours", "break_minutes"):
                value = max(0.0, float(value or 0))
            if name == "overtime_multiplier" and value and value < 1:
                raise ValueError("Overtime pays at least the regular rate (1.5 is time and a half).")
            if name == "break_minutes" and value > 240:
                raise ValueError("An unpaid break is up to 240 minutes.")
            if name == "take_home_pct" and value > 100:
                raise ValueError("Take-home is a share of the pay: 0 to 100.")
            if name == "week_starts" and value not in DAYS:
                raise ValueError("The pay week starts on a day of the week.")
            setattr(d, name, value if value is not None else "")

    # ---------------------------------------------------------------- runs

    def get_run(self, run_id: str) -> Optional[Run]:
        return next((r for r in self.runs if r.run_id == run_id), None)

    def planned_on(self, dungeon_id: str, on: str) -> Optional[Run]:
        return next((r for r in self.runs if r.dungeon_id == dungeon_id and r.date == on and r.status == "planned"), None)

    def add_run(self, dungeon_id: str, on: str, hours: float, status: str = "cleared", affixes=None,
                boss: bool = False, note: str = "") -> Run:
        if self.get_dungeon(dungeon_id) is None:
            raise ValueError("That dungeon isn't there anymore.")
        if status not in ("cleared", "planned"):
            raise ValueError("A run is cleared or planned.")
        hours = float(hours or 0)
        if hours <= 0 or hours > 24:
            raise ValueError("A run is between 0 and 24 hours.")
        run = Run(run_id=uuid.uuid4().hex[:10], dungeon_id=dungeon_id, date=on[:10], hours=round(hours, 2),
                  status=status, affixes=list(affixes or []), boss=bool(boss), note=str(note or "").strip(),
                  created_at=_now())
        self.runs.append(run)
        self._save()
        if status == "cleared":
            self._record(run)
        return run

    def clear_run(self, run_id: str, hours: Optional[float] = None, affixes=None, note: str = "") -> Run:
        """A planned run, worked: its hours (if they changed), what made it hard."""
        run = self.get_run(run_id)
        if run is None:
            raise ValueError("That run isn't there anymore.")
        if hours is not None:
            if float(hours) <= 0 or float(hours) > 24:
                raise ValueError("A run is between 0 and 24 hours.")
            run.hours = round(float(hours), 2)
        if affixes:
            run.affixes = list(dict.fromkeys(list(run.affixes) + list(affixes)))
        if note:
            run.note = str(note).strip()
        run.status = "cleared"
        self._save()
        self._record(run)
        return run

    def delete_run(self, run_id: str) -> None:
        if self.get_run(run_id) is None:
            raise ValueError("That run isn't there anymore.")
        self.runs = [r for r in self.runs if r.run_id != run_id]
        self._save()

    def _record(self, run: Run) -> None:
        from core import life_events

        d = self.get_dungeon(run.dungeon_id)
        hard = affix_names(run.affixes)
        life_events.record(self, "dungeon_cleared",
                           f"Cleared a {run.hours:g}-hour run at {d.name if d else 'work'}"
                           + (f" on hard mode ({', '.join(hard)})" if hard else ""),
                           [f"dungeon:{run.dungeon_id}"], {"hours": run.hours, "affixes": list(run.affixes)})

    def runs_for(self, dungeon_id: str) -> list[Run]:
        return sorted((r for r in self.runs if r.dungeon_id == dungeon_id), key=lambda r: (r.date, r.created_at))
