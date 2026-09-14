"""
core.insight_manager
=======================

Insight + Recommendation — the first real piece of the observe →
understand → insight → recommend → act → result → learn loop from the
"connective infrastructure" architecture-review discussion (see
docs/ROADMAP.md's dated entry), piloted in the Maintenance domain only
(core/maintenance_insights.py) before any generalization.

An `Insight` is a durable "the system noticed X" record — deliberately
distinct from a `core.notification_manager.Notification`, which is
ephemeral and UI-focused. A `Recommendation` is "given this Insight,
here's a suggested next step," tracked separately so it can carry its
own status independent of the Insight it responds to. Both are real,
new, persisted entities (unlike core/achievements.py's Achievements,
which needed none) because — unlike a level-up — an Insight about,
say, an overdue task needs to be looked back on, deduplicated against,
and resolved later; there's no single number to derive it from on
demand.

**Idempotent creation is the whole "never naggy" mechanism here.**
Unlike core/smart_suggestions.py's checks (which are self-resolving by
date-exact math — a birthday reminder is only ever true on one day),
a real-world condition like "this task is overdue" stays true for many
days in a row. create_insight_if_new() only ever creates a new Insight
when no `"open"` one already exists for the same
(source_type, source_id, kind) — a second scan of an unchanged,
still-overdue task is a no-op, not a duplicate. resolve_insight()
(called once the underlying condition stops holding — see
core/maintenance_insights.py) is where the loop's RESULT step lands,
automatically, the moment a real completion happens through whatever
UI already handles that domain — no new "mark resolved" interaction
needed for this pass.

Insights still always surface first through the existing
NotificationToast/NotificationCenter (same as Smart Suggestions) —
that's unchanged. The dedicated browsing UI this docstring once called
a deferred "later phase" now exists too, once a second real domain
(core/mission_insights.py) gave it real cross-domain content to show:
`modules/observations/module.py`, a real, read-only "what's still
open" view over every Insight this manager holds, regardless of which
Notification toast surfaced it or whether that toast was already
dismissed.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_INSIGHTS_FILE = _DATA_DIR / "insights.json"
_RECOMMENDATIONS_FILE = _DATA_DIR / "recommendations.json"

INSIGHT_STATUSES = ("open", "resolved")
RECOMMENDATION_STATUSES = ("pending", "resolved")


@dataclass
class Insight:
    insight_id: str
    source_type: str  # e.g. "maintenance" -- which domain this came from
    source_id: str  # e.g. a task_id -- the specific record this is about
    kind: str  # domain-defined free string, e.g. "overdue"/"due_soon"/"due" -- see core/maintenance_insights.py
    title: str
    message: str
    status: str = "open"
    created_at: str = ""  # ISO datetime
    resolved_at: str = ""  # ISO datetime, blank until resolved

    def to_dict(self) -> dict:
        return {
            "insight_id": self.insight_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "kind": self.kind,
            "title": self.title,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Insight":
        return Insight(
            insight_id=data.get("insight_id", uuid.uuid4().hex[:10]),
            source_type=data.get("source_type", ""),
            source_id=data.get("source_id", ""),
            kind=data.get("kind", ""),
            title=data.get("title", ""),
            message=data.get("message", ""),
            status=data.get("status", "open"),
            created_at=data.get("created_at", ""),
            resolved_at=data.get("resolved_at", ""),
        )


@dataclass
class Recommendation:
    recommendation_id: str
    insight_id: str  # the Insight this recommendation responds to
    message: str  # the suggested next step, e.g. "Mark 'Oil change' complete, or reschedule it."
    status: str = "pending"
    created_at: str = ""  # ISO datetime
    resolved_at: str = ""  # ISO datetime, blank until resolved

    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "insight_id": self.insight_id,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Recommendation":
        return Recommendation(
            recommendation_id=data.get("recommendation_id", uuid.uuid4().hex[:10]),
            insight_id=data.get("insight_id", ""),
            message=data.get("message", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", ""),
            resolved_at=data.get("resolved_at", ""),
        )


class InsightManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._insights: list[Insight] = []
        self._recommendations: list[Recommendation] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if _INSIGHTS_FILE.exists():
            try:
                raw = json.loads(_INSIGHTS_FILE.read_text(encoding="utf-8"))
                self._insights = [Insight.from_dict(d) for d in raw]
            except (json.JSONDecodeError, OSError):
                log.exception("Failed to load insights.json — starting with an empty list.")
                self._insights = []
        if _RECOMMENDATIONS_FILE.exists():
            try:
                raw = json.loads(_RECOMMENDATIONS_FILE.read_text(encoding="utf-8"))
                self._recommendations = [Recommendation.from_dict(d) for d in raw]
            except (json.JSONDecodeError, OSError):
                log.exception("Failed to load recommendations.json — starting with an empty list.")
                self._recommendations = []

    def _save_insights(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_INSIGHTS_FILE,
            json.dumps([i.to_dict() for i in self._insights], indent=2), encoding="utf-8"
        )

    def _save_recommendations(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_RECOMMENDATIONS_FILE,
            json.dumps([r.to_dict() for r in self._recommendations], indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    def create_insight_if_new(
        self, source_type: str, source_id: str, kind: str, title: str, message: str
    ) -> Optional[Insight]:
        """Creates a new open Insight for (source_type, source_id, kind)
        UNLESS one already exists in "open" status — returns None in
        that case rather than a duplicate. This is the real "never
        naggy" mechanism for a condition that stays true for many days
        in a row; see this module's own docstring."""
        if self.open_insight_for(source_type, source_id, kind) is not None:
            return None
        insight = Insight(
            insight_id=uuid.uuid4().hex[:10],
            source_type=source_type,
            source_id=source_id,
            kind=kind,
            title=title,
            message=message,
            status="open",
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._insights.append(insight)
        self._save_insights()
        log.info("Insight created: [%s/%s] %s", source_type, kind, title)
        return insight

    def open_insight_for(self, source_type: str, source_id: str, kind: str) -> Optional[Insight]:
        for insight in self._insights:
            if (
                insight.source_type == source_type
                and insight.source_id == source_id
                and insight.kind == kind
                and insight.status == "open"
            ):
                return insight
        return None

    def open_insights_for_source(self, source_type: str, source_id: str) -> list[Insight]:
        return [
            i for i in self._insights
            if i.source_type == source_type and i.source_id == source_id and i.status == "open"
        ]

    def resolve_insight(self, insight_id: str) -> Optional[Insight]:
        """Marks an Insight (and any pending Recommendation that
        responds to it) resolved — where this loop's RESULT step
        lands. Never re-opens an already-resolved Insight; safe to
        call repeatedly."""
        insight = self.get_insight(insight_id)
        if insight is None or insight.status == "resolved":
            return insight
        insight.status = "resolved"
        insight.resolved_at = datetime.now().isoformat(timespec="seconds")
        self._save_insights()
        for recommendation in self._recommendations:
            if recommendation.insight_id == insight_id and recommendation.status == "pending":
                recommendation.status = "resolved"
                recommendation.resolved_at = insight.resolved_at
        self._save_recommendations()
        return insight

    def get_insight(self, insight_id: str) -> Optional[Insight]:
        for insight in self._insights:
            if insight.insight_id == insight_id:
                return insight
        return None

    def all_insights(self) -> list[Insight]:
        return list(self._insights)

    def open_insights(self) -> list[Insight]:
        return [i for i in self._insights if i.status == "open"]

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def add_recommendation(self, insight_id: str, message: str) -> Recommendation:
        recommendation = Recommendation(
            recommendation_id=uuid.uuid4().hex[:10],
            insight_id=insight_id,
            message=message,
            status="pending",
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._recommendations.append(recommendation)
        self._save_recommendations()
        return recommendation

    def recommendations_for_insight(self, insight_id: str) -> list[Recommendation]:
        return [r for r in self._recommendations if r.insight_id == insight_id]

    def all_recommendations(self) -> list[Recommendation]:
        return list(self._recommendations)
