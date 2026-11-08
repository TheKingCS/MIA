"""
core.direction
================

The standing directions a person is steering their life by — the values they've asked MIA to hold in mind and gently
encourage (Zac, 2026-11-08: his shift "from consumer to producer" — make and restore before buying, 3D print, upcycle,
thrift and design his own clothes, grow and cook his own natural food, cut the processed stuff, produce in every way).

A direction is more than a remembered fact: MIA keeps it in view on every turn (it joins "what you know about this
user" in the chat prompt) and leans her suggestions toward it when it fits — so when the person is about to buy
something, she offers the make/restore/upcycle angle; when it's food, the from-scratch natural version. It never
overrides the quick answer the person actually asked for, and it's never preachy.

A personal store (`directions.json`), sealed at rest (DEC-0126). The directions themselves live only in the person's
own profile — no one's values are hard-coded here. Setting one is the person's own act (`add`), undoable.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import life_events
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "directions.json"


@dataclass
class Direction:
    """One standing direction: a short title, the value in the person's own words, and how MIA should encourage it."""

    direction_id: str
    title: str
    statement: str
    encourage: str = ""
    nudges: list = None  # short proactive prompts MIA can raise now and then; None -> []
    active: bool = True
    created_at: str = ""

    def __post_init__(self) -> None:
        """Default the mutable nudges list without sharing it across instances."""
        if self.nudges is None:
            self.nudges = []

    def to_dict(self) -> dict:
        """As a plain dict for JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Direction":
        """From a stored dict; `active` defaults to True."""
        return Direction(direction_id=d.get("direction_id", ""), title=d.get("title", ""),
                         statement=d.get("statement", ""), encourage=d.get("encourage", ""),
                         nudges=list(d.get("nudges") or []), active=bool(d.get("active", True)),
                         created_at=d.get("created_at", ""))


class DirectionBook:
    """A person's standing directions (directions.json): the values MIA holds in mind and gently encourages."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Points at the person's directions.json (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE if data_dir is not None else _DATA_DIR / _FILE
        self.directions: list[Direction] = []
        self.last_nudge: str = ""  # ISO date MIA last nudged about a direction, so it stays occasional
        self._load()

    def _load(self) -> None:
        """Reads the directions; a missing file starts empty, a sealed one that won't open is set aside (DEC-0126)."""
        try:
            raw = json.loads(open_text(self._file))
        except FileNotFoundError:
            return
        except (ValueError, OSError):
            log.exception("Couldn't read directions.json — starting empty.")
            return
        self.directions = [Direction.from_dict(d) for d in raw.get("directions", [])]
        self.last_nudge = raw.get("last_nudge", "")

    def _save(self) -> None:
        """Writes the directions atomically (undoable), sealed at rest."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps(
            {"directions": [d.to_dict() for d in self.directions], "last_nudge": self.last_nudge},
            indent=1, ensure_ascii=False))

    def add(self, title: str, statement: str, encourage: str = "", nudges: Optional[list] = None) -> Direction:
        """Set a new standing direction (with optional short nudge prompts MIA can raise now and then)."""
        d = Direction(direction_id=uuid.uuid4().hex[:10], title=title, statement=statement, encourage=encourage,
                      nudges=list(nudges or []), active=True, created_at=datetime.now().isoformat(timespec="seconds"))
        self.directions.append(d)
        self._save()
        life_events.record(self, "direction_set", title, [f"direction:{d.direction_id}"])
        return d

    def set_active(self, direction_id: str, active: bool) -> Direction:
        """Turn a direction on or off (ValueError for an unknown one)."""
        d = self.get(direction_id)
        if d is None:
            raise ValueError(f"No direction with id '{direction_id}'.")
        d.active = active
        self._save()
        return d

    def get(self, direction_id: str) -> Optional[Direction]:
        """The direction with this id, or None."""
        return next((d for d in self.directions if d.direction_id == direction_id), None)

    def active(self) -> list[Direction]:
        """The directions currently in force."""
        return [d for d in self.directions if d.active]

    def due_for_nudge(self, today: str, every_days: int = 3) -> bool:
        """Whether it's time for an occasional proactive nudge: there's an active direction with nudges, and it's been
        at least every_days since the last one (always true the first time)."""
        from datetime import date

        if not any(d.nudges for d in self.active()):
            return False
        if not self.last_nudge:
            return True
        try:
            return (date.fromisoformat(today) - date.fromisoformat(self.last_nudge[:10])).days >= every_days
        except ValueError:
            return True

    def a_nudge(self, roll: float) -> str:
        """One nudge from the active directions' nudges, chosen by `roll` (0-1) so it varies; "" when there are none."""
        pool = [n for d in self.active() for n in d.nudges]
        if not pool:
            return ""
        return pool[int(roll * len(pool)) % len(pool)]

    def mark_nudged(self, today: str) -> None:
        """Remember MIA nudged today, so the next one waits."""
        self.last_nudge = today
        self._save()

    def context_block(self) -> str:
        """The lines MIA carries on every turn: the active directions and how to encourage them, framed so she leans
        that way when it fits but never overrides the quick answer or gets preachy. "" when there are none."""
        live = self.active()
        if not live:
            return ""
        lines = ["The person is steering their life by these directions — hold them in mind and, when it genuinely "
                 "fits, lean your suggestions toward them (never preachy, never at the cost of the answer they asked "
                 "for):"]
        for d in live:
            line = f"- {d.title}: {d.statement}"
            if d.encourage:
                line += f" (encourage: {d.encourage})"
            lines.append(line)
        return "\n".join(lines)
