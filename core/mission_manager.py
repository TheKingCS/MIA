"""
core.mission_manager
=======================

Missions/Gamification — docs/ROADMAP.md milestone v0.18, the second of
three new subsystems from the 2026-07-14 wearable-companion vision
update (see docs/VISION.md). Turns a stated goal/hobby into a tracked
Mission with one or more Objectives (e.g. a "Master Angler" mission for
a fishing trip: one objective for time spent fishing, one for fish
caught). Same persisted-JSON pattern as core/expedition_manager.py:
data/missions.json, dataclasses with to_dict/from_dict, a manager class
wrapping load/save. `Objective` is nested inside `Mission`'s own JSON,
not a separate top-level record — same reasoning as `GearItem`/`Split`
nested inside `Trip` (core/trip_manager.py): an objective only ever
makes sense in the context of one mission.

A Mission optionally links to an existing `core.trip_manager.Trip` via
`trip_id` (mirrors `JournalEntry.trip_id`'s optional-FK pattern) —
`trip_id=None` supports a general goal not tied to any specific outing
("finish wiring the garage"), not just outdoor Trip-scoped ones.

Two objective metric types (`METRIC_TYPES`, same fixed-vocabulary
pattern as `ACTIVITY_TYPES`):
- `"tally"` — a manually-incremented counter (fish caught, species
  identified, etc.) — the one genuinely new primitive this milestone
  needed, since nothing else in the app models an arbitrary count.
  `Objective.progress` stores this directly.
- `"trip_duration_hours"` — computed on demand from the linked Trip's
  logged splits (first-to-last-split elapsed time), never stored, so
  it can't go stale — same "compute on demand" philosophy as
  core/memory_manager.py's ExpeditionRecap. Requires the Mission to
  have a `trip_id` and that Trip to have at least 2 logged splits;
  reads as 0.0 (not started) otherwise rather than raising, since an
  objective with no progress yet is a normal, expected state.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MISSIONS_FILE = _DATA_DIR / "missions.json"

METRIC_TYPES: tuple[str, ...] = ("tally", "trip_duration_hours")


@dataclass
class Objective:
    description: str  # e.g. "Catch 3 fish" or "Spend 2 hours fishing"
    metric_type: str  # one of METRIC_TYPES
    target: float
    progress: float = 0.0  # only meaningful for "tally" — "trip_duration_hours" is always computed live, never stored here

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "metric_type": self.metric_type,
            "target": self.target,
            "progress": self.progress,
        }

    @staticmethod
    def from_dict(data: dict) -> "Objective":
        return Objective(
            description=data.get("description", ""),
            metric_type=data.get("metric_type", "tally"),
            target=float(data.get("target", 0.0)),
            progress=float(data.get("progress", 0.0)),
        )


@dataclass
class Mission:
    mission_id: str
    name: str
    trip_id: Optional[str] = None
    status: str = "active"  # "active" | "completed" | "abandoned"
    objectives: list[Objective] = field(default_factory=list)
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "trip_id": self.trip_id,
            "status": self.status,
            "objectives": [o.to_dict() for o in self.objectives],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Mission":
        return Mission(
            mission_id=data.get("mission_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            trip_id=data.get("trip_id"),
            status=data.get("status", "active"),
            objectives=[Objective.from_dict(d) for d in data.get("objectives", [])],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class MissionManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._missions: list[Mission] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _MISSIONS_FILE.exists():
            self._missions = []
            return
        try:
            raw = json.loads(_MISSIONS_FILE.read_text(encoding="utf-8"))
            self._missions = [Mission.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load missions.json — starting with an empty list.")
            self._missions = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _MISSIONS_FILE.write_text(
            json.dumps([m.to_dict() for m in self._missions], indent=2),
            encoding="utf-8",
        )

    def _bump_updated_at(self, mission: Mission) -> None:
        mission.updated_at = datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # Mission CRUD
    # ------------------------------------------------------------------

    def add_mission(self, name: str, trip_id: Optional[str] = None) -> Mission:
        now = datetime.now().isoformat(timespec="seconds")
        mission = Mission(
            mission_id=uuid.uuid4().hex[:10],
            name=name,
            trip_id=trip_id,
            created_at=now,
            updated_at=now,
        )
        self._missions.append(mission)
        self._save()
        log.info("Mission added: '%s'", name)
        return mission

    def update_mission(self, mission_id: str, **fields) -> Mission:
        mission = self.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"No mission with id '{mission_id}'.")
        was_completed = mission.status == "completed"
        for key, value in fields.items():
            if key in ("created_at", "trip_id"):
                raise ValueError(f"'{key}' can't be set through update_mission().")
            if not hasattr(mission, key):
                raise ValueError(f"Mission has no field '{key}'.")
            setattr(mission, key, value)
        self._bump_updated_at(mission)
        self._save()
        # Fires uniformly whether "completed" was set via
        # modules/missions/module.py's own UI button or the Assistant's
        # complete_mission action (core/application.py) — celebration
        # logic lives here, in the manager, so neither call site needs
        # its own copy of "did this just newly become complete."
        if not was_completed and mission.status == "completed":
            self._notify_mission_completed(mission)
        return mission

    def delete_mission(self, mission_id: str) -> None:
        self._missions = [m for m in self._missions if m.mission_id != mission_id]
        self._save()

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        for mission in self._missions:
            if mission.mission_id == mission_id:
                return mission
        return None

    def all_missions(self) -> list[Mission]:
        return sorted(self._missions, key=lambda m: m.created_at, reverse=True)

    def missions_for_trip(self, trip_id: str) -> list[Mission]:
        return [m for m in self._missions if m.trip_id == trip_id]

    # ------------------------------------------------------------------
    # Objectives
    # ------------------------------------------------------------------

    def add_objective(self, mission_id: str, description: str, metric_type: str, target: float) -> Mission:
        mission = self.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"No mission with id '{mission_id}'.")
        if metric_type not in METRIC_TYPES:
            raise ValueError(f"Unknown metric_type '{metric_type}'.")
        mission.objectives.append(Objective(description=description, metric_type=metric_type, target=target))
        self._bump_updated_at(mission)
        self._save()
        return mission

    def delete_objective(self, mission_id: str, index: int) -> Mission:
        mission = self.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"No mission with id '{mission_id}'.")
        if not (0 <= index < len(mission.objectives)):
            raise ValueError(f"Mission '{mission_id}' has no objective at index {index}.")
        del mission.objectives[index]
        self._bump_updated_at(mission)
        self._save()
        return mission

    def increment_tally(self, mission_id: str, index: int, delta: float = 1.0) -> Mission:
        mission = self.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"No mission with id '{mission_id}'.")
        if not (0 <= index < len(mission.objectives)):
            raise ValueError(f"Mission '{mission_id}' has no objective at index {index}.")
        objective = mission.objectives[index]
        if objective.metric_type != "tally":
            raise ValueError(f"Objective '{objective.description}' is not a tally-type objective.")
        was_objective_complete = objective.progress >= objective.target
        all_were_complete = self._all_objectives_complete(mission)
        objective.progress += delta
        self._bump_updated_at(mission)
        self._save()

        is_objective_complete = objective.progress >= objective.target
        if not was_objective_complete and is_objective_complete:
            self._notify_objective_completed(mission, objective)
        if not all_were_complete and self._all_objectives_complete(mission):
            self._notify_all_objectives_completed(mission)
        return mission

    def _all_objectives_complete(self, mission: Mission) -> bool:
        """
        Uses is_objective_complete() (not a bare progress>=target check
        here) so a mixed mission — some tally objectives, some
        trip_duration_hours ones — is judged correctly on both metric
        types, not just tally's directly-stored progress.
        """
        if not mission.objectives:
            return False
        return all(
            self.is_objective_complete(mission.mission_id, index) for index in range(len(mission.objectives))
        )

    def _notify_objective_completed(self, mission: Mission, objective: Objective) -> None:
        if self.context.notifications is None:
            return
        self.context.notifications.notify(
            title="\U0001F3C6 Objective complete!",
            message=f"You did it! \"{objective.description}\" is complete on your \"{mission.name}\" mission. Keep it up!",
            level="info",
            source="missions",
        )

    def _notify_all_objectives_completed(self, mission: Mission) -> None:
        if self.context.notifications is None:
            return
        self.context.notifications.notify(
            title="\U0001F3C6 All objectives complete!",
            message=f"Every objective on \"{mission.name}\" is done — amazing work! Ready to mark it complete?",
            level="info",
            source="missions",
        )

    def _notify_mission_completed(self, mission: Mission) -> None:
        if self.context.notifications is None:
            return
        self.context.notifications.notify(
            title="\U0001F389 Mission complete!",
            message=f"\"{mission.name}\" is complete! That's a real achievement — what's next?",
            level="info",
            source="missions",
        )

    def objective_progress(self, mission_id: str, index: int) -> Optional[float]:
        mission = self.get_mission(mission_id)
        if mission is None or not (0 <= index < len(mission.objectives)):
            return None
        objective = mission.objectives[index]
        if objective.metric_type == "trip_duration_hours":
            if mission.trip_id is None:
                return 0.0
            return self._trip_elapsed_hours(mission.trip_id) or 0.0
        return objective.progress

    def is_objective_complete(self, mission_id: str, index: int) -> bool:
        mission = self.get_mission(mission_id)
        if mission is None or not (0 <= index < len(mission.objectives)):
            return False
        progress = self.objective_progress(mission_id, index)
        return progress is not None and progress >= mission.objectives[index].target

    def _trip_elapsed_hours(self, trip_id: str) -> Optional[float]:
        trip = self.context.trips.get_trip(trip_id)
        if trip is None or len(trip.splits) < 2:
            return None
        timestamps = sorted(datetime.fromisoformat(s.logged_at) for s in trip.splits)
        return (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0
