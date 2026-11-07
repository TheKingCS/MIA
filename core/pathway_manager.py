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
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PATHWAYS_FILE = _DATA_DIR / "mission_pathways.json"
_PROGRESS_FILE = _DATA_DIR / "pathway_progress.json"

PATHWAY_PROGRESS_STATUSES = ("active", "completed")


@dataclass
class PathwayStep:
    """One step of a skill pathway, as the mission it becomes: name, icon, summary, difficulty, XP, credits and skill
    XP, and how many times it must be completed before the pathway moves on (1 by default).
    """
    name: str
    icon: str = "\U0001F4CB"
    summary: str = ""
    difficulty: str = "NORMAL"
    reward_xp: int = 0
    reward_credits: int = 0
    skill_rewards: list[SkillWeight] = field(default_factory=list)
    # "Repeatable pathway steps" (2026-09-12) — how many real completions
    # of this step are needed before the pathway advances past it.
    # Default 1 preserves the original one-and-done behavior exactly
    # (see PathwayManager._advance()). >1 is for steps like "Cook a New
    # Recipe" the user is realistically going to do several times before
    # moving on.
    repeat_count: int = 1

    @staticmethod
    def from_dict(data: dict) -> "PathwayStep":
        """A step from the pathway definitions file; missing fields take their defaults."""
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
            repeat_count=data.get("repeat_count", 1),
        )


@dataclass
class Pathway:
    """A skill pathway (hand-written in data/mission_pathways.json): the skill it grows, its name and description, and
    its steps in order.
    """
    pathway_id: str
    skill_id: str
    name: str
    description: str = ""
    steps: list[PathwayStep] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "Pathway":
        """A pathway from the definitions file."""
        return Pathway(
            pathway_id=data.get("pathway_id", ""),
            skill_id=data.get("skill_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=[PathwayStep.from_dict(s) for s in data.get("steps", [])],
        )


@dataclass
class PathwayProgress:
    """One person's way along a pathway: which step they're on, the mission for it, how many of a repeating step
    they've done, active or completed, and when.
    """
    profile_id: str
    pathway_id: str
    current_step_index: int = 0
    current_mission_id: str = ""
    status: str = "active"
    started_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime
    # "Repeatable pathway steps" (2026-09-12) — real completions of the
    # CURRENT step so far, reset to 0 the moment the pathway actually
    # advances past it. Only meaningful while status == "active".
    current_step_repeats_done: int = 0

    def to_dict(self) -> dict:
        """The progress as saved in pathway_progress.json."""
        return {
            "profile_id": self.profile_id,
            "pathway_id": self.pathway_id,
            "current_step_index": self.current_step_index,
            "current_mission_id": self.current_mission_id,
            "status": self.status,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "current_step_repeats_done": self.current_step_repeats_done,
        }

    @staticmethod
    def from_dict(data: dict) -> "PathwayProgress":
        """Progress from its saved dict; missing fields take their defaults."""
        return PathwayProgress(
            profile_id=data.get("profile_id", ""),
            pathway_id=data.get("pathway_id", ""),
            current_step_index=data.get("current_step_index", 0),
            current_mission_id=data.get("current_mission_id", ""),
            current_step_repeats_done=data.get("current_step_repeats_done", 0),
            status=data.get("status", "active"),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class PathwayManager:
    """Skill pathways: the definitions (read-only, from data/mission_pathways.json) and each person's progress
    (pathway_progress.json, written through atomic_write_text so undo can restore it). Each step is a mission
    MIA assigns; when it's completed (the mission.completed event) the pathway moves on.
    """
    def __init__(self, context: AppContext) -> None:
        """Loads the definitions and everyone's progress, and listens for mission.completed; progress_path tells undo
        which file to reload.
        """
        self.context = context
        self._pathways: dict[str, Pathway] = {}
        self._progress: list[PathwayProgress] = []
        # The file it reads, so undo (core/undo_log.py) knows to reload it.
        self.progress_path = _PROGRESS_FILE
        self._load_definitions()
        self._load_progress()
        self.context.events.subscribe("mission.completed", self._on_mission_completed)

    # ------------------------------------------------------------------
    # Definitions — read-only from this class's own perspective
    # ------------------------------------------------------------------

    def _load_definitions(self) -> None:
        """Reads the pathway definitions (none when the file is missing; a damaged one is logged and reported)."""
        if not _PATHWAYS_FILE.exists():
            log.info("No mission_pathways.json found — no pathways registered yet.")
            return
        try:
            raw = json.loads(_PATHWAYS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load mission_pathways.json — no pathways registered.")
            notify_data_corruption(self.context, "mission_pathways.json")
            return
        for entry in raw.get("pathways", []):
            pathway = Pathway.from_dict(entry)
            self._pathways[pathway.pathway_id] = pathway

    def all_pathways(self) -> list[Pathway]:
        """Every pathway defined."""
        return list(self._pathways.values())

    def get_pathway(self, pathway_id: str) -> Optional[Pathway]:
        """The pathway with this id, or None."""
        return self._pathways.get(pathway_id)

    def pathways_for_skill(self, skill_id: str) -> list[Pathway]:
        """The pathways that grow one skill."""
        return [p for p in self._pathways.values() if p.skill_id == skill_id]

    # ------------------------------------------------------------------
    # Progress — owned, persisted
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Undo calls this after putting the progress file back (or taking it away)."""
        self._progress = []
        self._load_progress()

    def _load_progress(self) -> None:
        """Reads everyone's progress; a damaged file is logged, reported and starts with none."""
        if not _PROGRESS_FILE.exists():
            return
        try:
            raw = json.loads(_PROGRESS_FILE.read_text(encoding="utf-8"))
            self._progress = [PathwayProgress.from_dict(d) for d in raw.get("progress", [])]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load pathway_progress.json — starting with no progress.")
            notify_data_corruption(self.context, "pathway_progress.json")
            self._progress = []

    def _save_progress(self) -> None:
        """Writes everyone's progress atomically."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_PROGRESS_FILE,
            json.dumps({"progress": [p.to_dict() for p in self._progress]}, indent=2), encoding="utf-8"
        )

    def progress_for_profile(self, profile_id: str) -> list[PathwayProgress]:
        """One person's pathways, active and completed."""
        return [p for p in self._progress if p.profile_id == profile_id]

    def _active_progress(self, profile_id: str, pathway_id: str) -> Optional[PathwayProgress]:
        """A person's active progress on one pathway, or None."""
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
        """Makes the mission for a step (assigned by MIA, with the step's look and rewards)."""
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
        """When a pathway step's mission is completed, move that pathway on."""
        for progress in self._progress:
            if progress.status == "active" and progress.current_mission_id == mission_id:
                self._advance(progress)
                return

    def _advance(self, progress: PathwayProgress) -> None:
        """Moves a pathway on after its step's mission is done: a repeating step not yet done enough gets another mission
        ("Do It Again!"); otherwise the next step's mission is made ("New Mission Unlocked!"), or the pathway is
        complete. Each is saved and said to the person.
        """
        pathway = self._pathways.get(progress.pathway_id)
        if pathway is None:
            return
        now = datetime.now().isoformat(timespec="seconds")

        # "Repeatable pathway steps" (2026-09-12) — a real completion of
        # the CURRENT step always counts toward its own repeat_count
        # first. With the default repeat_count=1 this immediately falls
        # through to the unchanged advance-to-next-step logic below,
        # zero behavior change for every existing pathway/step.
        current_step = pathway.steps[progress.current_step_index]
        progress.current_step_repeats_done += 1
        if progress.current_step_repeats_done < current_step.repeat_count:
            repeat_mission = self._create_step_mission(current_step)
            progress.current_mission_id = repeat_mission.mission_id
            progress.updated_at = now
            self._save_progress()
            if self.context.notifications is not None:
                self.context.notifications.notify(
                    title="\U0001F501 Do It Again!",
                    message=f"{repeat_mission.name} — {progress.current_step_repeats_done} of {current_step.repeat_count} done.",
                    level="info",
                    source="pathways",
                )
            return
        progress.current_step_repeats_done = 0

        next_index = progress.current_step_index + 1

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
