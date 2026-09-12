"""
core.discovery_manager
==========================

Discovery — the AI-generated counterpart to Mission Pathways
(core/pathway_manager.py, hand-authored) and the first real piece of
the "Personal Capability & Progression Engine" the user described after
Pathways shipped. Deliberately the smallest possible closed loop, not
the full vision (cross-tree synthesis, mission decomposition, adaptive
difficulty) — those are explicitly future work; see this pass's own
plan file / docs/ROADMAP.md dated entry for why.

```
Current state (Skills, Projects, Intent, recent Missions)
        -> ONE AI-generated MissionProposal
        -> deterministic validation (this module)
        -> user accepts or rejects (modules/toolbox/tools/discovery_tool.py)
        -> accepted -> a real, persisted core.mission_manager.Mission
           (assigned_by="mia", same as Pathways-generated missions)
        -> completion -> real Skill XP via the existing, UNCHANGED
           MissionManager._credit_mission_rewards() path
```

The one hard rule this module exists to enforce: **the LLM only ever
proposes; it can never mint a new capability or silently become
authoritative state.** `build_discovery_prompt()` gathers real facts
about the user deterministically (same "gather facts first, LLM only
phrases/generates on top of them" shape as
`core.device_help_manager.build_grounded_prompt()`) and tells the model
exactly which real `skill_id`s it's allowed to use.
`parse_and_validate_proposal()` then re-checks that boundary for real —
a proposal naming even one unknown skill_id is discarded whole, no
partial acceptance — mirroring `core.assistant_chat.parse_extracted_
memories()`'s "a formatting slip must never smuggle in a wrong fact"
discipline. `reward_xp`/`reward_credits` are never taken from the LLM's
own text at all — they're computed deterministically from the
validated `skill_rewards`, one less thing the model has to get right
and one more piece of the reward economy that stays fully
deterministic.

A `MissionProposal` that validates is real, persisted state
(`data/mission_proposals.json` — real per-profile runtime state, not
hand-authored content, so no `.gitignore` exception like
`mission_pathways.json` gets) — but it isn't a Mission yet, and never
becomes state on its own. Only `accept_proposal()`, an explicit user
action, turns one into a real `Mission`. `reject_proposal()` discards
it (kept, not deleted, as light history) with no retry.

Deliberately NOT built this pass, stated plainly rather than silently
skipped: `supports_project_id` stays in the schema (so
`accept_proposal()` and any future UI can use it) but generation never
populates it yet — matching a proposal to a specific real Project
reliably needs its own matching logic, and letting the LLM guess a
project id is a worse failure mode than leaving it unset; active
Projects/Intent are still fed into the prompt as context so the
proposal is informed by them. No auto-generation of the next proposal
on completion — v1 is manually triggered (a button in
`modules/toolbox/tools/discovery_tool.py`), avoiding an unasked "when
should MIA proactively nag me" design decision. Only one `"pending"`
proposal per profile at a time — same one-active-thing-per-profile
discipline `PathwayManager.start_pathway()` already established.
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
from core.mission_manager import DIFFICULTY_LEVELS

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROPOSALS_FILE = _DATA_DIR / "mission_proposals.json"

PROPOSAL_STATUSES = ("pending", "accepted", "rejected")

# reward_credits is deliberately a small fixed value keyed off Difficulty
# (never parsed from the LLM's own text) — same "flat, not tuned" reward-
# sizing stance core.gamification's own docstring states for routine
# actions, applied here to keep the whole reward economy deterministic.
_REWARD_CREDITS_BY_DIFFICULTY = {"EASY": 5, "NORMAL": 10, "HARD": 20}

_MAX_SKILL_XP_PER_PROPOSAL_ENTRY = 50
_MAX_TRAINED_SKILLS_IN_PROMPT = 20
_MAX_FRONTIER_SKILLS_IN_PROMPT = 15
_MAX_RECENT_MISSIONS_IN_PROMPT = 5
_MAX_STRUGGLED_MISSIONS_IN_PROMPT = 5
_MAX_STUDYING_SUBJECTS_IN_PROMPT = 5

_PROPOSAL_TAGS = ("Mission", "Summary", "Difficulty", "Skills", "Rationale")


@dataclass
class MissionProposal:
    proposal_id: str
    profile_id: str
    status: str = "pending"  # "pending" | "accepted" | "rejected"
    created_at: str = ""  # ISO datetime
    resolved_at: str = ""  # ISO datetime, set on accept/reject
    name: str = ""
    summary: str = ""
    difficulty: str = "NORMAL"
    reward_xp: int = 0  # derived from skill_rewards, never LLM-picked directly
    reward_credits: int = 0  # derived from difficulty, never LLM-picked directly
    skill_rewards: list[SkillWeight] = field(default_factory=list)
    rationale: str = ""  # MIA's own stated "why this is useful" — free text
    # Deliberately unset by generation this pass — see module docstring.
    # Kept in the schema now so accept_proposal() and any future UI
    # don't need a schema change once matching is built.
    supports_project_id: Optional[str] = None
    mission_id: str = ""  # set once accepted — the resulting real Mission's id

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "profile_id": self.profile_id,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "name": self.name,
            "summary": self.summary,
            "difficulty": self.difficulty,
            "reward_xp": self.reward_xp,
            "reward_credits": self.reward_credits,
            "skill_rewards": [{"skill_id": w.skill_id, "xp": w.xp} for w in self.skill_rewards],
            "rationale": self.rationale,
            "supports_project_id": self.supports_project_id,
            "mission_id": self.mission_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "MissionProposal":
        return MissionProposal(
            proposal_id=data.get("proposal_id", uuid.uuid4().hex[:10]),
            profile_id=data.get("profile_id", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", ""),
            resolved_at=data.get("resolved_at", ""),
            name=data.get("name", ""),
            summary=data.get("summary", ""),
            difficulty=data.get("difficulty", "NORMAL"),
            reward_xp=data.get("reward_xp", 0),
            reward_credits=data.get("reward_credits", 0),
            skill_rewards=[
                SkillWeight(skill_id=d["skill_id"], xp=d["xp"]) for d in data.get("skill_rewards", [])
            ],
            rationale=data.get("rationale", ""),
            supports_project_id=data.get("supports_project_id"),
            mission_id=data.get("mission_id", ""),
        )


def _extract_tagged_fields(raw_text: str) -> dict[str, str]:
    """
    Pure parsing logic — same "tagged line, safe if malformed" shape as
    core.assistant_chat._split_category_and_fact. A line matching
    "Tag: value" (one of _PROPOSAL_TAGS, case-insensitive) starts
    capturing into that tag; any following line with no tag of its own
    is appended to whichever tag is currently open (so a wrapped
    Rationale sentence isn't lost), and any text before the first
    recognized tag is discarded rather than misfiled.
    """
    collected: dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in raw_text.splitlines():
        stripped = line.strip().lstrip("-*• ").strip()
        matched_tag = None
        value = ""
        if ":" in stripped:
            prefix, rest = stripped.split(":", 1)
            prefix = prefix.strip()
            for tag in _PROPOSAL_TAGS:
                if prefix.lower() == tag.lower():
                    matched_tag = tag
                    value = rest.strip()
                    break
        if matched_tag is not None:
            current = matched_tag
            collected[current] = [value] if value else []
        elif current is not None and stripped:
            collected[current].append(stripped)
    return {tag: " ".join(parts).strip() for tag, parts in collected.items()}


def _parse_skill_rewards(raw_value: str, skill_manager) -> list[SkillWeight]:
    """
    Pure logic given a real SkillManager (or None). Returns [] on ANY
    problem — an unknown skill_id, a malformed "skill_id:xp" entry, a
    non-integer or out-of-range xp — never a partial list, so a
    proposal naming even one unrecognized capability is discarded
    whole by the caller rather than silently trimmed down.
    """
    if not raw_value or skill_manager is None:
        return []
    weights: list[SkillWeight] = []
    for entry in raw_value.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            return []
        skill_id, _, xp_text = entry.partition(":")
        skill_id = skill_id.strip()
        if skill_manager.get_skill(skill_id) is None:
            return []
        try:
            xp = int(xp_text.strip())
        except ValueError:
            return []
        if not (0 < xp <= _MAX_SKILL_XP_PER_PROPOSAL_ENTRY):
            return []
        weights.append(SkillWeight(skill_id=skill_id, xp=xp))
    return weights


class DiscoveryManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._proposals: list[MissionProposal] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _PROPOSALS_FILE.exists():
            self._proposals = []
            return
        try:
            raw = json.loads(_PROPOSALS_FILE.read_text(encoding="utf-8"))
            self._proposals = [MissionProposal.from_dict(d) for d in raw.get("proposals", [])]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load mission_proposals.json — starting with no proposals.")
            self._proposals = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _PROPOSALS_FILE.write_text(
            json.dumps({"proposals": [p.to_dict() for p in self._proposals]}, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def pending_proposal_for(self, profile_id: str) -> Optional[MissionProposal]:
        for proposal in self._proposals:
            if proposal.profile_id == profile_id and proposal.status == "pending":
                return proposal
        return None

    def get_proposal(self, proposal_id: str) -> Optional[MissionProposal]:
        for proposal in self._proposals:
            if proposal.proposal_id == proposal_id:
                return proposal
        return None

    def proposals_for_profile(self, profile_id: str) -> list[MissionProposal]:
        return [p for p in self._proposals if p.profile_id == profile_id]

    # ------------------------------------------------------------------
    # Generation — pure prompt-building + pure parsing, no I/O in either
    # ------------------------------------------------------------------

    def build_discovery_prompt(self, profile_id: str) -> str:
        """
        Pure, deterministic — gathers real Skill/Project/Intent/Mission
        state and formats it as a labeled reference block, same
        "real facts first, LLM only generates on top of them" shape as
        core.device_help_manager.build_grounded_prompt(). Callers run
        the RETURNED STRING through context.llm.generate() themselves
        (via core.generate_worker.GenerateWorker off the GUI thread) —
        this method makes no LLM call and does no I/O.
        """
        lines: list[str] = []
        allowed_skill_ids: list[str] = []

        # Computed early (not inline with the rest of the Missions
        # section below) so the frontier-skill list right after can
        # prioritize these — a real gap found verifying the struggle-
        # signal pass: the frontier cap could silently crowd out the
        # exact skill the user just struggled with, even though it was
        # genuinely unlocked. See _MAX_FRONTIER_SKILLS_IN_PROMPT below.
        struggled_missions = []
        if self.context.missions is not None:
            struggled_missions = [
                m
                for m in self.context.missions.all_missions()
                if m.status == "abandoned" and m.abandon_reason == "too_hard" and m.skill_rewards
            ][:_MAX_STRUGGLED_MISSIONS_IN_PROMPT]
        struggled_skill_ids = {weight.skill_id for m in struggled_missions for weight in m.skill_rewards}

        has_trained_skills = False
        if self.context.skills is not None:
            progress_by_id = {
                p.skill_id: p.total_xp for p in self.context.skills.progress_for_profile(profile_id)
            }
            trained = []
            frontier = []
            for definition in self.context.skills.all_skills():
                total_xp = progress_by_id.get(definition.skill_id, 0)
                if total_xp > 0:
                    trained.append((definition, total_xp))
                elif self.context.skills.is_unlocked(profile_id, definition.skill_id):
                    frontier.append(definition)
            trained.sort(key=lambda pair: pair[1], reverse=True)
            trained = trained[:_MAX_TRAINED_SKILLS_IN_PROMPT]
            # Struggled-with skills sort first (stable sort — otherwise
            # preserves definition order) so the cap below never
            # crowds one out.
            frontier.sort(key=lambda d: d.skill_id not in struggled_skill_ids)
            frontier = frontier[:_MAX_FRONTIER_SKILLS_IN_PROMPT]
            allowed_skill_ids = [d.skill_id for d, _ in trained] + [d.skill_id for d in frontier]

            if trained:
                has_trained_skills = True
                lines.append("Skills the user has already trained (real progress):")
                lines.extend(
                    f"- {d.name} ({d.skill_id}): {xp} XP — "
                    f"{self.context.skills.capability_status(profile_id, d.skill_id).capitalize()}"
                    for d, xp in trained
                )
            if frontier:
                lines.append("Skills available to start next (unlocked, not yet trained):")
                lines.extend(f"- {d.name} ({d.skill_id})" for d in frontier)

        if self.context.intents is not None:
            primary = self.context.intents.primary_intent()
            if primary is not None:
                lines.append(f"Current primary intent: {primary.name}")

        if self.context.projects is not None:
            active_projects = [p for p in self.context.projects.all_projects() if p.status in ("Planning", "Active")]
            if active_projects:
                lines.append("Active projects:")
                lines.extend(f"- {p.name}" for p in active_projects)

        if self.context.missions is not None:
            recent_completed = [m for m in self.context.missions.all_missions() if m.status == "completed"]
            recent_completed = recent_completed[:_MAX_RECENT_MISSIONS_IN_PROMPT]
            if recent_completed:
                lines.append("Recently completed missions (don't just repeat one of these):")
                lines.extend(f"- {m.name}" for m in recent_completed)

        # "Mission failure/struggle signal" (2026-09-11) — the real,
        # deterministic "learns why" step: a mission the user themselves
        # marked too hard is real evidence a skill area needs an easier
        # or prerequisite step next, not a harder one. Only "too_hard"
        # is looked for here — the other ABANDON_REASONS values are
        # recorded on the Mission but don't (yet) change what gets
        # proposed. struggled_missions was computed above, before the
        # frontier-skill list, so that list could prioritize these.
        if struggled_missions:
            lines.append(
                "Found too difficult recently (consider something easier in these skill "
                "areas, or a prerequisite step, instead):"
            )
            lines.extend(
                f"- {m.name} (targeted: {', '.join(w.skill_id for w in m.skill_rewards)})"
                for m in struggled_missions
            )

        # "Wire Classroom into Hero's Path" (2026-09-12) — real,
        # deterministic awareness of what the user is actually studying
        # right now (a Subject with at least one lesson, not fully
        # complete). Purely informational grounding, same as every
        # other section here — no knowledge-gap detection, no
        # Discovery-generated lesson recommendations.
        studying_subjects = []
        if self.context.classroom is not None:
            for subject in self.context.classroom.all_subjects():
                done, total = self.context.classroom.subject_completion(subject.subject_id)
                if total and done < total:
                    studying_subjects.append(subject)
            studying_subjects = studying_subjects[:_MAX_STUDYING_SUBJECTS_IN_PROMPT]
            if studying_subjects:
                lines.append("Currently studying (real, in-progress coursework):")
                lines.extend(f"- {s.name}" for s in studying_subjects)

        reference_block = "\n".join(lines) if lines else "No real progress recorded yet — this is a fresh start."
        allowed_ids_text = ", ".join(allowed_skill_ids) if allowed_skill_ids else "(none available)"
        struggle_instruction = (
            " If a skill appears in the 'found too difficult' list, prefer an easier step in "
            "that same skill area, or one that builds a prerequisite, over a harder one."
            if struggled_missions
            else ""
        )
        # Capability status tiers (2026-09-11) — the same "real
        # grounding + one soft steering sentence" shape as
        # struggle_instruction above, not a hard rule.
        capability_instruction = (
            " Propose something more ambitious in a skill marked Demonstrated, and something "
            "gentler in a skill marked Learning."
            if has_trained_skills
            else ""
        )
        studying_instruction = (
            " Consider whether a mission could reinforce something the user is currently studying."
            if studying_subjects
            else ""
        )

        return (
            "You are MIA, a personal capability-building assistant. Based on the real "
            "information below about what this user has actually done, propose ONE new "
            "mission -- a concrete, real-world action -- that would be a useful next step "
            f"for them.{struggle_instruction}{capability_instruction}{studying_instruction}\n\n"
            f"{reference_block}\n\n"
            f"You may ONLY reference these exact skill ids in your answer: {allowed_ids_text}. "
            "Never invent a new skill id, and never claim the user has already done something "
            "that isn't listed above. Reply in EXACTLY this format, nothing else:\n\n"
            "Mission: <a short, concrete mission name>\n"
            "Summary: <one sentence describing what the user would actually do>\n"
            "Difficulty: EASY, NORMAL, or HARD\n"
            "Skills: skill_id:xp[, skill_id:xp ...] (only skill ids from the list above, "
            "xp between 5 and 50 per skill)\n"
            "Rationale: <one or two sentences on why this is a good next step for this user>"
        )

    def parse_and_validate_proposal(self, profile_id: str, raw_text: Optional[str]) -> Optional[MissionProposal]:
        """
        Pure — no I/O, directly testable with canned strings. Returns
        None (never raises) if the LLM's reply is missing a required
        field, names an unrecognized skill_id, or is otherwise
        unusable — same "discard rather than guess" stance as
        core.assistant_chat.parse_extracted_memories(). A returned
        MissionProposal is fully validated but NOT YET persisted —
        callers pass it to record_pending_proposal() themselves.
        """
        if not raw_text:
            return None
        fields = _extract_tagged_fields(raw_text)

        name = fields.get("Mission", "").strip()
        summary = fields.get("Summary", "").strip()
        rationale = fields.get("Rationale", "").strip()
        if not name or not summary or not rationale:
            return None

        skill_rewards = _parse_skill_rewards(fields.get("Skills", ""), self.context.skills)
        if not skill_rewards:
            return None

        difficulty = fields.get("Difficulty", "").strip().upper()
        if difficulty not in DIFFICULTY_LEVELS:
            difficulty = "NORMAL"

        now = datetime.now().isoformat(timespec="seconds")
        return MissionProposal(
            proposal_id=uuid.uuid4().hex[:10],
            profile_id=profile_id,
            status="pending",
            created_at=now,
            name=name,
            summary=summary,
            difficulty=difficulty,
            reward_xp=sum(weight.xp for weight in skill_rewards),
            reward_credits=_REWARD_CREDITS_BY_DIFFICULTY.get(difficulty, 10),
            skill_rewards=skill_rewards,
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Recording / accepting / rejecting
    # ------------------------------------------------------------------

    def record_pending_proposal(self, proposal: MissionProposal) -> Optional[MissionProposal]:
        """Refuses (returns None) if this profile already has a pending
        proposal — same one-active-thing-per-profile discipline
        PathwayManager.start_pathway() already established."""
        if self.pending_proposal_for(proposal.profile_id) is not None:
            return None
        self._proposals.append(proposal)
        self._save()
        return proposal

    def accept_proposal(self, profile_id: str, proposal_id: str):
        """Creates the real, persisted Mission (assigned_by="mia") and
        marks the proposal accepted. Returns the new Mission, or None
        if the proposal doesn't exist, belongs to a different profile,
        isn't pending, or context.missions isn't wired."""
        proposal = self.get_proposal(proposal_id)
        if proposal is None or proposal.profile_id != profile_id or proposal.status != "pending":
            return None
        if self.context.missions is None:
            return None

        mission = self.context.missions.add_mission(
            name=proposal.name,
            project_id=proposal.supports_project_id,
            assigned_by="mia",
            summary=proposal.summary,
            difficulty=proposal.difficulty,
            reward_xp=proposal.reward_xp,
            reward_credits=proposal.reward_credits,
            skill_rewards=proposal.skill_rewards,
        )
        proposal.status = "accepted"
        proposal.mission_id = mission.mission_id
        proposal.resolved_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        log.info("Mission proposal '%s' accepted -> mission '%s'", proposal.name, mission.mission_id)
        return mission

    def reject_proposal(self, profile_id: str, proposal_id: str) -> None:
        """No-op if the proposal doesn't exist, belongs to a different
        profile, or isn't pending. Kept (status="rejected"), not
        deleted — light history, no active dedup logic against it yet
        (that's future "don't repeat busywork" intelligence)."""
        proposal = self.get_proposal(proposal_id)
        if proposal is None or proposal.profile_id != profile_id or proposal.status != "pending":
            return
        proposal.status = "rejected"
        proposal.resolved_at = datetime.now().isoformat(timespec="seconds")
        self._save()
