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

Each is shown as the design canvas has it (`card()`, DEC-0113): Needs You
or Noticed, the apps it drew on, and a link to settle it where it lives.
Resolving one happens where it lives (marking the upkeep done, moving the
mission), never here. A child sees no money findings (core/findings.py
already leaves them out).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

SOURCES = {"maintenance": "Upkeep", "missions": "Missions", "patterns": "Patterns"}
SOURCE_APPS = {"maintenance": "maintenance", "missions": "missions"}
# Which app a record of each kind ("kind:id" refs) lives in, for the canvas's "used" line (DEC-0113).
REF_APPS = {"bill": "budget", "income": "budget", "debt": "budget", "expense": "budget", "trip": "expeditions",
            "expedition": "expeditions", "asset": "maintenance", "task": "maintenance", "recipe": "kitchen",
            "meal": "kitchen", "obligation": "compliance", "mission": "missions", "project": "workshop",
            "job": "workshop", "lot": "workshop", "policy": "insurance", "quote": "insurance", "run": "dungeon",
            "dungeon": "dungeon", "workout": "workout", "order": "business"}


def _apps() -> dict:
    """Each web app by its module id: (name, page)."""
    from core.web_surfaces import APPS

    return {a.module_id: (a.name, a.page) for a in APPS}


def card(app: str, refs: list, urgent: bool, apps: dict) -> dict:
    """Pure logic. How one observation is shown (the design canvas, DEC-0113): its kind (Needs You when it's
    worth saying unprompted, otherwise Noticed), the apps it drew on (its own first, then those its records live
    in: "Money · Bills"), and where to settle it ("Open in Money", its page). An app with no web page gives no link."""
    used = [app] + [REF_APPS[r.split(":", 1)[0]] for r in refs if r.split(":", 1)[0] in REF_APPS]
    names = []
    for m in used:
        name = apps.get(m, (None, None))[0]
        if name and name not in names:
            names.append(name)
    name, page = apps.get(app, (None, None))
    return {"kind": "Needs You" if urgent else "Noticed", "tone": "attention" if urgent else "accent",
            "used": " · ".join(names), "open": {"label": f"Open in {name}", "href": page} if name and page else None}


def screen(context, today: Optional[date] = None) -> dict:
    """What MIA noticed for this person: the findings across apps (title, claim, why, next step), and the open insights
    grouped by where they came from, each with its first pending recommendation; each with its card (`card()`). A findings rule that fails hides
    none of the rest.
    """
    from core.findings import findings

    found = []
    try:
        apps = _apps()
        found = [{"title": f.title, "claim": f.claim, "why": f.why, "next": f.next_step, "app": f.app,
                  "sure": f.sureness, **card(f.app, f.refs, f.unprompted, apps)} for f in findings(context, today)]
    except Exception:  # one store failing never hides the rest
        found = []
    store = getattr(context, "insights", None)
    groups: dict[str, list] = {}
    for i in (store.open_insights() if store is not None else []):
        pending = [r.message for r in store.recommendations_for_insight(i.insight_id) if r.status == "pending"]
        groups.setdefault(i.source_type, []).append({"title": i.title, "message": i.message,
                                                     "next": pending[0] if pending else "",
                                                     "since": (i.created_at or "")[:10],
                                                     **card(SOURCE_APPS.get(i.source_type, ""), [], False, _apps()),
                                                     **({"kind": "Pattern"} if i.source_type == "patterns" else {})})
    return {"findings": found,
            "insights": [{"source": SOURCES.get(k, k.replace("_", " ").capitalize()), "items": v}
                         for k, v in sorted(groups.items())]}
