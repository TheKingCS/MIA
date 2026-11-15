"""
core.requirements
===================

What each project needs (Procurement P1, DEC-0172; `docs/mia_os/MIA_OS_PROCUREMENT_PROPOSAL.md` section 6): one
line per thing a project needs, with how many, what it has to be, the most it should cost, and how far along it is.

**A requirement** (`Requirement`): the project it belongs to (by id), the item in the person's or the plan's words,
quantity and unit, specifications (free text for now; P2 gives categories their own fields), acceptable alternatives,
what it must fit (an owned machine), a price ceiling, the condition wanted (new, used, any), a priority (first, later,
nice to have), a needed-by date, and a status:
- `needed`: none on hand;
- `partial`: some on hand (`have` says how many);
- `owned`: enough on hand;
- `found`: an opportunity is linked (World Intelligence's finds, P3);
- `ordered`, `acquired`: on its way, and in hand.
Plus where it came from (`origin`: `plan:<id>` or `said`) and how it's known (`how`: computed from a plan's
quantities in code, or said by the person), the epistemic contract (DEC-0173).

**Where requirements come from:**
- **A plan:** starting a project from a plan (`plan.project`, or "start the shed project" by voice) lists the plan's
  materials as the project's requirements (`from_materials`), quantities from core/build_calcs.py, never the model.
- **The person:** "the greenhouse needs four ventilation fans" (`requirement.add`).

**What's on hand** (`refresh_owned`): each open line is checked against the workshop's materials (the same matching
the plan library's shopping list uses) and the household inventory by name; enough on hand is `owned`, some is
`partial`. A line the person marked ordered or acquired is left alone. Inventory isn't assumed still there forever:
a match only counts when the record says how many.

**For World Intelligence:** open lines become anchors (core/relevance.py: "the Greenhouse needs polycarbonate panels"),
so a find that fits a need ranks high, and MIA's own watches cover each open need.

`RequirementBook` is a household store (beside projects), `requirements.json`, written through atomic_write_text so
"undo that" restores it.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = DATA_DIR
_FILE = "requirements.json"
STATUSES = ("needed", "partial", "owned", "found", "ordered", "acquired")
OPEN = ("needed", "partial", "found")  # still to get
PRIORITIES = ("first", "later", "nice to have")
CONDITIONS = ("any", "new", "used")


@dataclass
class Requirement:
    """One thing a project needs (see the module's opening)."""
    requirement_id: str
    project_id: str
    item: str
    quantity: float = 1.0
    unit: str = ""
    specs: str = ""
    alternatives: str = ""
    fits: str = ""  # what it must fit: an owned machine's name, or a ref like asset:ab12
    max_price: float = 0.0  # 0: no ceiling
    condition: str = "any"
    priority: str = "first"
    needed_by: str = ""  # ISO date
    status: str = "needed"
    have: float = 0.0
    origin: str = "said"  # "said" or "plan:<id>"
    how: str = "said"  # "said" (the person) or "computed" (a plan's quantities, in code)
    created: str = ""
    checked: str = ""  # when what's on hand was last checked


class RequirementBook:
    """The household's project requirements (requirements.json, written atomically so undo can restore it)."""

    # The epistemic contract (DEC-0173, G3): where each line came from, when, how it's known, when last checked.
    EPISTEMIC = {"record": Requirement, "source": "origin", "at": "created", "how": "how", "checked": "checked"}

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the household's file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads the lines, keeping only known fields; an unreadable file is logged, reported and starts empty."""
        self.items: list[Requirement] = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(open_text(self._file))
            fields = Requirement.__dataclass_fields__
            self.items = [Requirement(**{k: v for k, v in d.items() if k in fields}) for d in raw.get("requirements", [])]
        except (ValueError, OSError, TypeError, AttributeError):
            log.exception("requirements.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def _save(self) -> None:
        """Writes every line atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"requirements": [asdict(r) for r in self.items]}, indent=2))

    # ---------------------------------------------------------------- reading

    def get(self, requirement_id: str) -> Optional[Requirement]:
        """The line with this id, or None."""
        return next((r for r in self.items if r.requirement_id == requirement_id), None)

    def for_project(self, project_id: str) -> list[Requirement]:
        """A project's lines, in the order they were added."""
        return [r for r in self.items if r.project_id == project_id]

    def open_items(self) -> list[Requirement]:
        """Every line still to get (needed, partial, found)."""
        return [r for r in self.items if r.status in OPEN]

    def find(self, project_id: str, words: str) -> Optional[Requirement]:
        """The project's line a few words name: its item exactly, else the only one holding every word."""
        wanted = " ".join(str(words or "").lower().split())
        lines = self.for_project(project_id) if project_id else self.items
        exact = [r for r in lines if " ".join(r.item.lower().split()) == wanted]
        if len(exact) == 1:
            return exact[0]
        some = [r for r in lines if wanted and set(wanted.split()) <= set(r.item.lower().split())]
        return some[0] if len(some) == 1 else None

    # ---------------------------------------------------------------- changing

    def add(self, project_id: str, item: str, quantity: float = 1.0, unit: str = "", origin: str = "said",
            how: str = "said", **extra) -> Requirement:
        """Adds a line; ValueError without an item, a project or a positive quantity, or with an unknown status,
        priority or condition."""
        item = " ".join(str(item or "").split())
        if not item or not project_id:
            raise ValueError("What does the project need?")
        if float(quantity) <= 0:
            raise ValueError("How many?")
        line = Requirement(uuid.uuid4().hex[:8], project_id, item[:120], float(quantity), str(unit or ""),
                           origin=origin, how=how, created=datetime.now().isoformat(timespec="seconds"))
        self._apply(line, extra)
        self.items.append(line)
        self._save()
        return line

    def _apply(self, line: Requirement, changes: dict) -> None:
        """Sets the given fields on a line, checked; ValueError for a value that isn't allowed."""
        for key, value in changes.items():
            if key in ("requirement_id", "project_id", "created") or key not in Requirement.__dataclass_fields__:
                continue
            if key == "status" and value not in STATUSES:
                raise ValueError(f"A need is one of: {', '.join(STATUSES)}.")
            if key == "priority" and value not in PRIORITIES:
                raise ValueError(f"A priority is one of: {', '.join(PRIORITIES)}.")
            if key == "condition" and value not in CONDITIONS:
                raise ValueError(f"A condition is one of: {', '.join(CONDITIONS)}.")
            if key in ("quantity", "max_price", "have"):
                value = float(value or 0)
            setattr(line, key, value)

    def update(self, requirement_id: str, **changes) -> Requirement:
        """Changes a line's fields; ValueError when it isn't here or a value isn't allowed."""
        line = self.get(requirement_id)
        if line is None:
            raise ValueError("That need isn't here any more.")
        self._apply(line, changes)
        self._save()
        return line

    def remove(self, requirement_id: str) -> Requirement:
        """Takes a line off; ValueError when it isn't here."""
        line = self.get(requirement_id)
        if line is None:
            raise ValueError("That need isn't here any more.")
        self.items = [r for r in self.items if r.requirement_id != requirement_id]
        self._save()
        return line

    def from_materials(self, project_id: str, materials: dict, plan_id: str = "") -> list[Requirement]:
        """A plan's material list as the project's lines, quantities as the plan worked them out (computed in code);
        one line per item. Returns the lines added."""
        added = []
        now = datetime.now().isoformat(timespec="seconds")
        for item in materials.get("items", []):
            name = " ".join(str(item.get("name") or "").split())
            qty = float(item.get("qty") or 0)
            if not name or qty <= 0:
                continue
            line = Requirement(uuid.uuid4().hex[:8], project_id, name[:120], qty, str(item.get("unit") or ""),
                               specs=str(item.get("note") or ""), origin=f"plan:{plan_id}" if plan_id else "plan",
                               how="computed", created=now)
            self.items.append(line)
            added.append(line)
        if added:
            self._save()
        return added

    def refresh_owned(self, context, now: Optional[datetime] = None) -> int:
        """Checks each open line (not ordered, acquired or found) against the workshop's materials and the household
        inventory: enough on hand is owned, some is partial, none is needed. Returns how many changed; saves when any
        did."""
        from core.plan_library import _match

        now = now or datetime.now()
        stock = _safe(lambda: context.materials.all_materials())
        inventory = _safe(lambda: context.inventory.all_items())
        changed = 0
        for line in self.items:
            if line.status not in ("needed", "partial", "owned"):
                continue
            have = 0.0
            match = _match(line.item, stock)
            if match is not None:
                have += float(match.quantity_on_hand or 0)
            held = _match(line.item, inventory)
            if held is not None:
                have += float(getattr(held, "quantity", 0) or 0)
            status = "owned" if have >= line.quantity else "partial" if have > 0 else "needed"
            if (status, have) != (line.status, line.have):
                line.status, line.have = status, have
                changed += 1
            line.checked = now.isoformat(timespec="seconds")
        if self.items:
            self._save()
        return changed


def _safe(read) -> list:
    """A store's records, or [] when it isn't here."""
    try:
        return list(read() or [])
    except Exception:  # noqa: BLE001 - a missing store means nothing on hand from it
        return []


def progress(lines: list[Requirement]) -> dict:
    """Pure logic. A project's needs at a glance: how many lines, how many still to get, how many owned or acquired,
    and the ceiling's total for what's still to get (where one is set)."""
    open_lines = [r for r in lines if r.status in OPEN]
    return {"lines": len(lines), "open": len(open_lines),
            "done": sum(1 for r in lines if r.status in ("owned", "acquired")),
            "ordered": sum(1 for r in lines if r.status == "ordered"),
            "ceiling": round(sum(r.max_price for r in open_lines if r.max_price), 2)}
