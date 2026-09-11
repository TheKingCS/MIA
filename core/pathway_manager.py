"""
core.pathway_manager
=======================

Mission Pathways — the user-driven counterpart to the "Discovery"
concept from the connective-infrastructure architecture review
(deferred, Phase 6: MIA inferring a pattern from history). Here the
user picks a skill and MIA hands them a structured, pre-authored
sequence of real Missions that build it — "assign missions and
pathways for growing through each skill." Deliberately rule-based and
hand-authored, not AI-generated — same stance as Missions' own
existing auto-assignment rules (core.mission_manager.MissionManager.
check_for_auto_assignment()) and everything else this session's
gamification work has built.

Two separate concerns, two separate files, same split
core/skill_manager.py already established for Skills:

- PATHWAY DEFINITIONS (data/mission_pathways.json) are the content —
  what pathways exist and what steps they're made of. Meant to be
  hand-edited directly to add more, same "definitions file, never
  written by code" spirit as data/skill_definitions.json.
- PATHWAY PROGRESS (data/pathway_progress.json) is real per-profile
  state — which pathways a profile has started, how far into each.

Advancing a pathway is entirely event-driven, not polled: this manager
subscribes to core.mission_manager's new "mission.completed" event
(added alongside this feature — a real, previously-missing gap,
independent of Pathways, that nothing in this codebase reacted to
before) and checks whether the completed mission is the one currently
tracked for some profile's in-progress pathway. Only a REAL completion
advances it — abandoning or deleting the generated Mission leaves the
pathway stalled, never auto-advanced, matching this codebase's existing
"only a genuine transition counts" bias (core.mission_manager's own
was_completed-transition-detection, core.project_manager's
skill_weights_credited guard).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.gamification import SkillWeight
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PATHWAYS_FILE = _DATA_DIR / "mission_pathways.json"
_PROGRESS_FILE = _DATA_DIR / "pathway_progress.json"

PATHWAY_PROGRESS_STATUSES = ("active", "completed")


@dataclass
class PathwayStep:
    name: str
    icon: str = "\U0001F4CB"
    summary: str = ""
    difficulty: str = "NORMAL"
    reward_xp: int = 0
    reward_credits: int = 0
    skill_rewards: list[SkillWeight] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "PathwayStep":
        return PathwayStep(
            name=data.get("name", ""),
            icon=data.get("icon", "\U0001F4CB"),
            summary=data.get("summary", ""),
            difficulty=data.get("difficulty", "NORMAL"),
            reward_xp=data.get("reward_xp", 0),
            reward_credits=data.get("reward_credits", 0),
            skill_rewards=[
                SkillWeight(skill_id=d["skill_id"], xp=d["xp"]) for d in data.get("skill_rewards", [])
            ],
        )


@dataclass
class Pathway:
    pathway_id: str
    skill_id: str
    name: str
    description: str = ""
    steps: list[PathwayStep] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "Pathway":
        return Pathway(
            pathway_id=data.get("pathway_id", ""),
            skill_id=data.get("skill_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=[PathwayStep.from_dict(s) for s in data.get("steps", [])],
        )


@dataclass
class PathwayProgress:
    profile_id: str
    pathway_id: str
    current_step_index: int = 0
    current_mission_id: str = ""
    status: str = "active"
    started_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "pathway_id": self.pathway_id,
            "current_step_index": self.current_step_index,
            "current_mission_id": self.current_mission_id,
            "status": self.status,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PathwayProgress":
        return PathwayProgress(
            profile_id=data.get("profile_id", ""),
            pathway_id=data.get("pathway_id", ""),
            current_step_index=data.get("current_step_index", 0),
            current_mission_id=data.get("current_mission_id", ""),
            status=data.get("status", "active"),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class PathwayManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._pathways: dict[str, Pathway] = {}
        self._progress: list[PathwayProgress] = []
        self._load_definitions()
        self._load_progress()
        self.context.events.subscribe("mission.completed", self._on_mission_completed)

    # ------------------------------------------------------------------
    # Definitions — read-only from this class's own perspective
    # ------------------------------------------------------------------

    def _load_definitions(self) -> None:
        if not _PATHWAYS_FILE.exists():
            log.info("No mission_pathways.json found — no pathways registered yet.")
            return
        try:
            raw = json.loads(_PATHWAYS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load mission_pathways.json — no pathways registered.")
            return
        for entry in raw.get("pathways", []):
            pathway = Pathway.from_dict(entry)
            self._pathways[pathway.pathway_id] = pathway

    def all_pathways(self) -> list[Pathway]:
        return list(self._pathways.values())

    def get_pathway(self, pathway_id: str) -> Optional[Pathway]:
        return self._pathways.get(pathway_id)

    def pathways_for_skill(self, skill_id: str) -> list[Pathway]:
        return [p for p in self._pathways.values() if p.skill_id == skill_id]

    # ------------------------------------------------------------------
    # Progress — owned, persisted
    # ------------------------------------------------------------------

    def _load_progress(self) -> None:
        if not _PROGRESS_FILE.exists():
            return
        try:
            raw = json.loads(_PROGRESS_FILE.read_text(encoding="utf-8"))
            self._progress = [PathwayProgress.from_dict(d) for d in raw.get("progress", [])]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load pathway_progress.json — starting with no progress.")
            self._progress = []

    def _save_progress(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _PROGRESS_FILE.write_text(
            json.dumps({"progress": [p.to_dict() for p in self._progress]}, indent=2), encoding="utf-8"
        )

    def progress_for_profile(self, profile_id: str) -> list[PathwayProgress]:
        return [p for p in self._progress if p.profile_id == profile_id]

    def _active_progress(self, profile_id: str, pathway_id: str) -> Optional[PathwayProgress]:
        for progress in self._progress:
            if progress.profile_id == profile_id and progress.pathway_id == pathway_id and progress.status == "active":
                return progress
        return None

    def status_for(self, profile_id: str, pathway_id: str) -> Optional[PathwayProgress]:
        """Most relevant progress record for (profile_id, pathway_id) —
        the active run if one exists, else the most recent one at all
        (so a completed pathway still shows as "Completed" rather than
        "Not Started"). None if this profile has never started it."""
        matches = [p for p in self._progress if p.profile_id == profile_id and p.pathway_id == pathway_id]
        if not matches:
            return None
        for progress in matches:
            if progress.status == "active":
                return progress
        return matches[-1]

    # ------------------------------------------------------------------
    # Starting / advancing a pathway
    # ------------------------------------------------------------------

    def start_pathway(self, profile_id: str, pathway_id: str):
        """Creates the first step's real Mission and records progress.
        Returns the created Mission, or None if `pathway_id` is unknown,
        has no steps, this profile already has an active run of it, or
        context.missions isn't wired. A pathway already completed once
        CAN be started again (a fresh run) — real homesteading/
        cooking/fitness goals are often worth repeating."""
        pathway = self._pathways.get(pathway_id)
        if pathway is None or not pathway.steps:
            return None
        if self.context.missions is None:
            return None
        if self._active_progress(profile_id, pathway_id) is not None:
            return None

        mission = self._create_step_mission(pathway.steps[0])
        now = datetime.now().isoformat(timespec="seconds")
        self._progress.append(
            PathwayProgress(
                profile_id=profile_id,
                pathway_id=pathway_id,
                current_step_index=0,
                current_mission_id=mission.mission_id,
                status="active",
                started_at=now,
                updated_at=now,
            )
        )
        self._save_progress()
        log.info("Pathway '%s' started for profile '%s'", pathway.name, profile_id)
        return mission

    def _create_step_mission(self, step: PathwayStep):
        return self.context.missions.add_mission(
            name=step.name,
            assigned_by="mia",
            icon=step.icon,
            summary=step.summary,
            difficulty=step.difficulty,
            reward_xp=step.reward_xp,
            reward_credits=step.reward_credits,
            skill_rewards=step.skill_rewards,
        )

    def _on_mission_completed(self, mission_id: str) -> None:
        for progress in self._progress:
            if progress.status == "active" and progress.current_mission_id == mission_id:
                self._advance(progress)
                return

    def _advance(self, progress: PathwayProgress) -> None:
        pathway = self._pathways.get(progress.pathway_id)
        if pathway is None:
            return
        next_index = progress.current_step_index + 1
        now = datetime.now().isoformat(timespec="seconds")

        if next_index >= len(pathway.steps):
            progress.status = "completed"
            progress.updated_at = now
            self._save_progress()
            if self.context.notifications is not None:
                self.context.notifications.notify(
                    title="\U0001F3C6 Pathway complete!",
                    message=f"'{pathway.name}' is done — what's next?",
                    level="info",
                    source="pathways",
                )
            return

        next_mission = self._create_step_mission(pathway.steps[next_index])
        progress.current_step_index = next_index
        progress.current_mission_id = next_mission.mission_id
        progress.updated_at = now
        self._save_progress()
        if self.context.notifications is not None:
            self.context.notifications.notify(
                title="\U0001F513 New Mission Unlocked!",
                message=next_mission.name,
                level="info",
                source="pathways",
            )
