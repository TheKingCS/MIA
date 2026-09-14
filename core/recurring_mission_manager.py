"""
core.recurring_mission_manager
=================================

Recurring Missions (2026-09-13), at the user's explicit request: a
real daily goal (their first one — push-ups) that keeps generating
itself, tracks a real streak, shows up on the Calendar, and rewards a
bigger weekly bonus Mission when every day that week was done, with
the daily target itself escalating each week.

Missions themselves stay one-time records — no new "this Mission
repeats" concept was added to Mission. Instead, this manager reuses the
exact precedent `core/pathway_manager.py`'s "Repeatable pathway steps"
(2026-09-12) already established: a fresh Mission gets created for
each new occurrence, rather than mutating one Mission into a repeating
record. Two Missions come from one template: a "daily" occurrence
(today's real target, a tally objective) and one "weekly" occurrence
per week (tally target 7 — "how many of this week's daily missions got
done" — which doubles as this feature's whole streak/bonus mechanism,
no separate counter needed).

Streak is deliberately NOT new persisted state: every daily occurrence
is already a real Mission with a real `occurrence_key` (its ISO date)
and a real `status`, so "how many days in a row" is fully derivable
from `context.missions.all_missions()` — same "derive it, don't persist
a second copy that can drift" philosophy every level/capability-status
calculation elsewhere in this codebase already follows.

Calendar integration deliberately does NOT use CalendarEvent's own
recurrence (`RECURRENCE_TYPES` has no "daily" today, and even a "daily"
value couldn't show an escalating target through one static recurring
entry). Instead, `ensure_current_missions()` creates a fresh one-shot
CalendarEvent each day naming that day's real target — the exact
pattern `core.maintenance_manager.MaintenanceManager.schedule_task()`
already uses for its own one-shot event-per-occurrence.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.gamification import SkillWeight
from core.logger import get_logger
from core.mission_manager import Mission
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TEMPLATES_FILE = _DATA_DIR / "recurring_mission_templates.json"

_DAYS_PER_WEEK = 7


@dataclass
class RecurringMissionTemplate:
    template_id: str
    name: str
    objective_description_template: str  # e.g. "Do {target:g} push-ups" — .format(target=...)
    base_target: float
    target_increment_per_week: float
    daily_reward_xp: int
    weekly_bonus_reward_xp: int
    start_date: str  # ISO date — the anchor every week index/key is counted from
    created_at: str = ""
    daily_skill_rewards: list[SkillWeight] = field(default_factory=list)
    weekly_bonus_skill_rewards: list[SkillWeight] = field(default_factory=list)
    icon: str = "\U0001F3AF"  # dart
    active: bool = True
    # Household area (2026-09-14) — "daily" (existing shape: a daily
    # Mission + a weekly "did every day" bonus Mission) or "weekly" (one
    # Mission per week, no daily sub-occurrence — laundry's own shape,
    # not a daily habit with a weekly rollup). See
    # ensure_current_missions()'s own docstring for the branch.
    recurrence: str = "daily"
    # Mirrors MaintenanceAsset.category — what modules/household/module.py
    # (Garage/Property/Greenhouse's fourth sibling) filters templates by.
    category: str = "Household"

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "objective_description_template": self.objective_description_template,
            "base_target": self.base_target,
            "target_increment_per_week": self.target_increment_per_week,
            "daily_reward_xp": self.daily_reward_xp,
            "weekly_bonus_reward_xp": self.weekly_bonus_reward_xp,
            "start_date": self.start_date,
            "created_at": self.created_at,
            "daily_skill_rewards": [{"skill_id": w.skill_id, "xp": w.xp} for w in self.daily_skill_rewards],
            "weekly_bonus_skill_rewards": [{"skill_id": w.skill_id, "xp": w.xp} for w in self.weekly_bonus_skill_rewards],
            "icon": self.icon,
            "active": self.active,
            "recurrence": self.recurrence,
            "category": self.category,
        }

    @staticmethod
    def from_dict(data: dict) -> "RecurringMissionTemplate":
        return RecurringMissionTemplate(
            template_id=data.get("template_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            objective_description_template=data.get("objective_description_template", "{target:g}"),
            base_target=data.get("base_target", 1.0),
            target_increment_per_week=data.get("target_increment_per_week", 0.0),
            daily_reward_xp=data.get("daily_reward_xp", 0),
            weekly_bonus_reward_xp=data.get("weekly_bonus_reward_xp", 0),
            start_date=data.get("start_date", ""),
            created_at=data.get("created_at", ""),
            daily_skill_rewards=[
                SkillWeight(skill_id=d["skill_id"], xp=d["xp"]) for d in data.get("daily_skill_rewards", [])
            ],
            weekly_bonus_skill_rewards=[
                SkillWeight(skill_id=d["skill_id"], xp=d["xp"]) for d in data.get("weekly_bonus_skill_rewards", [])
            ],
            icon=data.get("icon", "\U0001F3AF"),
            active=data.get("active", True),
            recurrence=data.get("recurrence", "daily"),
            category=data.get("category", "Household"),
        )


# ----------------------------------------------------------------------
# Pure helpers — no Qt, no manager instances, same "take the real
# inputs as explicit parameters" convention as core/skill_leveling.py
# and core/maintenance_manager.py's is_sensor_task_due().
# ----------------------------------------------------------------------

def week_index_for(start_date: date, today: date) -> int:
    """0-based week number since start_date, floored. Never negative —
    a today before start_date (clock skew, a manually-edited
    start_date) just means "still week 0", not a negative index."""
    return max((today - start_date).days // _DAYS_PER_WEEK, 0)


def current_target_for(template: RecurringMissionTemplate, today: date) -> float:
    start = date.fromisoformat(template.start_date)
    return template.base_target + template.target_increment_per_week * week_index_for(start, today)


def week_key_for(start_date: date, week_index: int) -> str:
    """Counted from the template's own start_date, not the ISO calendar
    week — "every 7 days since this began" stays unambiguous regardless
    of what weekday it started on."""
    return f"{start_date.isoformat()}-W{week_index}"


def current_streak_for(daily_occurrence_dates: list[str], today: date) -> int:
    """`daily_occurrence_dates` are the real ISO dates of every
    COMPLETED daily occurrence for one template (caller filters by
    status first — this function only counts, it doesn't know what a
    Mission is). Counts consecutive days backward from today; if
    today's occurrence isn't done yet, starts counting from yesterday
    instead, so a streak doesn't drop to 0 for the few hours before
    today's Mission is actually completed."""
    completed = set(daily_occurrence_dates)
    if today.isoformat() in completed:
        cursor = today
    else:
        cursor = date.fromordinal(today.toordinal() - 1)

    streak = 0
    while cursor.isoformat() in completed:
        streak += 1
        cursor = date.fromordinal(cursor.toordinal() - 1)
    return streak


def current_weekly_streak_for(completed_week_indices: list[int], current_week_index: int) -> int:
    """Same shape as current_streak_for() but counts consecutive WEEKS
    (by index, not calendar date) — for recurrence == "weekly"
    templates (laundry's own shape), where the occurrence itself IS the
    week, not a daily sub-occurrence rolled up into one."""
    completed = set(completed_week_indices)
    cursor = current_week_index if current_week_index in completed else current_week_index - 1

    streak = 0
    while cursor in completed and cursor >= 0:
        streak += 1
        cursor -= 1
    return streak


class RecurringMissionManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._templates: list[RecurringMissionTemplate] = []
        self._load()
        self.context.events.subscribe("mission.completed", self._on_mission_completed)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _TEMPLATES_FILE.exists():
            self._templates = []
            return
        try:
            raw = json.loads(_TEMPLATES_FILE.read_text(encoding="utf-8"))
            self._templates = [RecurringMissionTemplate.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load recurring_mission_templates.json — starting with an empty list.")
            notify_data_corruption(self.context, "recurring_mission_templates.json")
            self._templates = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_TEMPLATES_FILE,
            json.dumps([t.to_dict() for t in self._templates], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def add_template(
        self,
        name: str,
        objective_description_template: str,
        base_target: float,
        target_increment_per_week: float,
        daily_reward_xp: int,
        weekly_bonus_reward_xp: int,
        start_date: str,
        daily_skill_rewards: Optional[list[SkillWeight]] = None,
        weekly_bonus_skill_rewards: Optional[list[SkillWeight]] = None,
        icon: str = "\U0001F3AF",
        recurrence: str = "daily",
        category: str = "Household",
    ) -> RecurringMissionTemplate:
        template = RecurringMissionTemplate(
            template_id=uuid.uuid4().hex[:10],
            name=name,
            objective_description_template=objective_description_template,
            base_target=base_target,
            target_increment_per_week=target_increment_per_week,
            daily_reward_xp=daily_reward_xp,
            weekly_bonus_reward_xp=weekly_bonus_reward_xp,
            start_date=start_date,
            created_at=datetime.now().isoformat(timespec="seconds"),
            daily_skill_rewards=list(daily_skill_rewards) if daily_skill_rewards else [],
            weekly_bonus_skill_rewards=list(weekly_bonus_skill_rewards) if weekly_bonus_skill_rewards else [],
            icon=icon,
            recurrence=recurrence,
            category=category,
        )
        self._templates.append(template)
        self._save()
        log.info("Recurring mission template added: '%s'", name)
        return template

    def get_template(self, template_id: str) -> Optional[RecurringMissionTemplate]:
        for template in self._templates:
            if template.template_id == template_id:
                return template
        return None

    def all_templates(self) -> list[RecurringMissionTemplate]:
        return list(self._templates)

    # ------------------------------------------------------------------
    # Occurrence lookup/creation
    # ------------------------------------------------------------------

    def _find_occurrence(self, template_id: str, kind: str, occurrence_key: str) -> Optional[Mission]:
        for mission in self.context.missions.all_missions():
            if (
                mission.recurring_template_id == template_id
                and mission.recurring_kind == kind
                and mission.occurrence_key == occurrence_key
            ):
                return mission
        return None

    def ensure_current_missions(
        self, template: RecurringMissionTemplate, today: date
    ) -> tuple[Mission, Optional[Mission]]:
        """Idempotent — safe to call every 5 minutes from the daily-
        occasion timer (core/application.py) or by hand. Dispatches on
        template.recurrence: "daily" (the original push-up shape)
        returns (today's daily Mission, this week's bonus Mission);
        "weekly" (laundry's own shape — see this module's docstring for
        why it's a distinct code path, not forced into the daily one)
        returns (this week's one Mission, None) — the None keeps a
        consistent 2-tuple unpack shape for callers regardless of
        recurrence."""
        if template.recurrence == "weekly":
            return self._ensure_current_mission_weekly(template, today), None
        return self._ensure_current_missions_daily(template, today)

    def _ensure_current_mission_weekly(self, template: RecurringMissionTemplate, today: date) -> Mission:
        start = date.fromisoformat(template.start_date)
        week_index = week_index_for(start, today)
        week_key = week_key_for(start, week_index)

        mission = self._find_occurrence(template.template_id, "weekly_standalone", week_key)
        if mission is not None:
            return mission

        target = current_target_for(template, today)
        mission = self.context.missions.add_mission(
            name=f"{template.name} — Week {week_index + 1}",
            icon=template.icon,
            summary=f"This week's real goal, week {week_index + 1}.",
            reward_xp=template.daily_reward_xp,
            skill_rewards=template.daily_skill_rewards,
            recurring_template_id=template.template_id,
            recurring_kind="weekly_standalone",
            occurrence_key=week_key,
        )
        self.context.missions.add_objective(
            mission.mission_id,
            template.objective_description_template.format(target=target),
            "tally",
            target,
        )
        if self.context.calendar is not None:
            self.context.calendar.add_event(
                title=f"{template.name}: {target:g} this week",
                date=today.isoformat(),
            )
        log.info("Created this week's recurring Mission: '%s' (target %.3g)", template.name, target)
        return mission

    def _ensure_current_missions_daily(
        self, template: RecurringMissionTemplate, today: date
    ) -> tuple[Mission, Mission]:
        """The original push-up shape: a daily Mission every day, plus
        one weekly bonus Mission per week that completes once all 7
        days are done (see _on_mission_completed() below)."""
        today_key = today.isoformat()
        start = date.fromisoformat(template.start_date)
        week_index = week_index_for(start, today)
        week_key = week_key_for(start, week_index)

        daily_mission = self._find_occurrence(template.template_id, "daily", today_key)
        if daily_mission is None:
            target = current_target_for(template, today)
            daily_mission = self.context.missions.add_mission(
                # Dated in the name (not just template.name) — caught via
                # this feature's own manual screenshot verification: a
                # week of identically-named "Push-ups" rows in the
                # Missions list is genuinely indistinguishable at a
                # glance, a real usability problem, not cosmetic polish.
                name=f"{template.name} — {today.strftime('%b %d')}",
                icon=template.icon,
                summary=f"Today's real goal, week {week_index + 1}.",
                reward_xp=template.daily_reward_xp,
                skill_rewards=template.daily_skill_rewards,
                recurring_template_id=template.template_id,
                recurring_kind="daily",
                occurrence_key=today_key,
            )
            self.context.missions.add_objective(
                daily_mission.mission_id,
                template.objective_description_template.format(target=target),
                "tally",
                target,
            )
            if self.context.calendar is not None:
                self.context.calendar.add_event(
                    title=f"{template.name}: {target:g} today",
                    date=today_key,
                )
            log.info("Created today's recurring Mission: '%s' (target %.3g)", template.name, target)

        weekly_mission = self._find_occurrence(template.template_id, "weekly", week_key)
        if weekly_mission is None:
            weekly_mission = self.context.missions.add_mission(
                name=f"{template.name} — Perfect Week {week_index + 1}",
                icon="\U0001F3C6",
                summary=f"Complete every day's {template.name} goal this week for a bonus.",
                reward_xp=template.weekly_bonus_reward_xp,
                skill_rewards=template.weekly_bonus_skill_rewards,
                recurring_template_id=template.template_id,
                recurring_kind="weekly",
                occurrence_key=week_key,
            )
            self.context.missions.add_objective(
                weekly_mission.mission_id, "Complete every day this week", "tally", float(_DAYS_PER_WEEK),
            )
            log.info("Created this week's bonus Mission: '%s'", weekly_mission.name)

        return daily_mission, weekly_mission

    # ------------------------------------------------------------------
    # Streak
    # ------------------------------------------------------------------

    def current_streak_for_template(self, template_id: str, today: date) -> int:
        template = self.get_template(template_id)
        if template is not None and template.recurrence == "weekly":
            start = date.fromisoformat(template.start_date)
            current_week_index = week_index_for(start, today)
            completed_week_indices = [
                int(mission.occurrence_key.rsplit("-W", 1)[1])
                for mission in self.context.missions.all_missions()
                if mission.recurring_template_id == template_id
                and mission.recurring_kind == "weekly_standalone"
                and mission.status == "completed"
                and mission.occurrence_key is not None
            ]
            return current_weekly_streak_for(completed_week_indices, current_week_index)

        completed_dates = [
            mission.occurrence_key
            for mission in self.context.missions.all_missions()
            if mission.recurring_template_id == template_id
            and mission.recurring_kind == "daily"
            and mission.status == "completed"
            and mission.occurrence_key is not None
        ]
        return current_streak_for(completed_dates, today)

    # ------------------------------------------------------------------
    # Reacting to a real completion
    # ------------------------------------------------------------------

    def _on_mission_completed(self, mission_id: str) -> None:
        mission = self.context.missions.get_mission(mission_id)
        if mission is None or mission.recurring_kind != "daily" or mission.recurring_template_id is None:
            return
        template = self.get_template(mission.recurring_template_id)
        if template is None or mission.occurrence_key is None:
            return

        start = date.fromisoformat(template.start_date)
        occurrence_date = date.fromisoformat(mission.occurrence_key)
        week_key = week_key_for(start, week_index_for(start, occurrence_date))
        weekly_mission = self._find_occurrence(template.template_id, "weekly", week_key)
        if weekly_mission is None or weekly_mission.status == "completed":
            return

        self.context.missions.increment_tally(weekly_mission.mission_id, 0, delta=1)
        if self.context.missions.is_objective_complete(weekly_mission.mission_id, 0):
            self.context.missions.update_mission(weekly_mission.mission_id, status="completed")
            log.info("Perfect week completed for '%s' — bonus credited.", template.name)
