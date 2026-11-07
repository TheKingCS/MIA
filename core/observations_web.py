"""
core.observations_web
=======================

Observations' web screen (web/observations.html): what MIA has noticed,
in two kinds, read only, as on the desktop:

- **across your apps** (core/findings.py): a bill before payday, upkeep
  before a trip, goods before market day..., each with why it matters and
  one next step;
- **in one app** (core/insight_manager.py): the open insights the
  maintenance, mission and pattern scans keep, by where they came from,
  each with its suggested next step.

Resolving one happens where it lives (marking the upkeep done, moving the
mission), never here. A child sees no money findings (core/findings.py
already leaves them out).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

SOURCES = {"maintenance": "Upkeep", "missions": "Missions", "patterns": "Patterns"}


def screen(context, today: Optional[date] = None) -> dict:
    """What MIA noticed for this person: the findings across apps (title, claim, why, next step), and the open insights
    grouped by where they came from, each with its first pending recommendation. A findings rule that fails hides
    none of the rest.
    """
    from core.findings import findings

    found = []
    try:
        found = [{"title": f.title, "claim": f.claim, "why": f.why, "next": f.next_step, "app": f.app,
                  "sure": f.sureness} for f in findings(context, today)]
    except Exception:  # one store failing never hides the rest
        found = []
    store = getattr(context, "insights", None)
    groups: dict[str, list] = {}
    for i in (store.open_insights() if store is not None else []):
        pending = [r.message for r in store.recommendations_for_insight(i.insight_id) if r.status == "pending"]
        groups.setdefault(i.source_type, []).append({"title": i.title, "message": i.message,
                                                     "next": pending[0] if pending else "",
                                                     "since": (i.created_at or "")[:10]})
    return {"findings": found,
            "insights": [{"source": SOURCES.get(k, k.replace("_", " ").capitalize()), "items": v}
                         for k, v in sorted(groups.items())]}
