"""
core.mission_guide
====================

The step a mission is on, from whatever guides it (Zac's handoff, 2026-11-09, DEC-0152: "Missions are not merely
checklists. They are MIA's universal execution and guidance system"). A mission's objectives say how far it is; a
guide says what to do now: the step, why it comes now, what to watch for, a checkpoint to verify, and the buttons
that move it on, the same as saying it. The mission's sheet shows it (core/web_progress.missions_page), so a guided
mission is worked from its own screen, with or without voice.

**Guides** (`GUIDES`, each `(context, mission) -> dict | None`), one per kind of walkthrough MIA already runs:

- `trade`: a Trade Master job (core/trade_session.py). While it's live, its step with why, watch-fors and an open
  hold point, and Next Step (trade.next) or Checked (trade.check), plus Back and Stop; not started or stopped, a
  Start that begins it. Its stop rules still end it at once by voice. `steps` lists the phase's steps, done and to
  come, for the sheet's step list.
- `greenhouse`: the greenhouse setup (core/greenhouse_setup.py): the step, why, what it needs and what to say.

A new kind of guided mission (a workout, a learning path's stage) is one more function in `GUIDES`, not a new
system: the sheet and the voice side already read from here. Guides only read; every change is an action.
"""

from __future__ import annotations

from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)


def _act(kind: str, label: str, params: Optional[dict] = None) -> dict:
    """Pure logic. A button: the action kind, its label and its params."""
    return {"kind": kind, "label": label, "params": params or {}}


def _trade(context, mission) -> Optional[dict]:
    """A Trade Master job's guide: its live step (or a Start when it isn't being worked)."""
    from core import trade_session as ts
    from core import trades
    from core.trade_actions import _mission_name

    trades._loaded()
    job = next((j for j in trades.JOBS.values() if _mission_name(j) == mission.name), None)
    store = getattr(context, "trade_session", None)
    live = store.live() if store is not None else None
    if live is not None and live.mission_id == mission.mission_id and live.kind == "job":
        item = ts.item_of(live)
        if item is None:
            return None
        steps = item.steps()
        phase, _index, step = steps[min(live.at, len(steps) - 1)]
        open_hold = bool(step.hold) and live.at not in set(live.confirmed or [])
        actions = [_act("trade.check", "Checked") if open_hold else _act("trade.next", "Next Step")]
        if live.at:
            actions.append(_act("trade.back", "Back"))
        actions.append(_act("trade.stop", "Stop"))
        here = [(n, s) for n, (p, _i, s) in enumerate(steps) if p == phase]  # this phase's steps, in order
        listed = [{"n": n + 1, "title": s.do, "done": n < live.at, "current": n == live.at} for n, s in here]
        return {"source": "trade", "live": True, "title": item.name, "step": live.at + 1, "of": len(steps),
                "steps": listed,
                "phase": item.phases[phase].name if isinstance(phase, int) else str(phase), "do": step.do,
                "why": step.why, "watch": list(step.watch), "check": step.hold if open_hold else "",
                "drafted": item.status != trades.CONFIRMED, "actions": actions,
                "say": "Ask “why?”, “what should I watch for?”, or anything about this step."}
    if job is None or mission.status != "active":
        return None
    return {"source": "trade", "live": False, "title": job.name, "step": 0, "of": len(job.steps()),
            "do": f"Start the walkthrough: {len(job.phases)} phases, {len(job.steps())} steps, one at a time.",
            "steps": [{"n": n + 1, "title": s.do, "done": False, "current": False}
                      for n, (p, _i, s) in enumerate(job.steps()) if p == 0],
            "why": job.scope, "watch": [], "check": "", "drafted": job.status != trades.CONFIRMED,
            "actions": [_act("trade.start", "Start", {"item_id": job.id})],
            "say": f"Or say “walk me through {job.name.lower()}”."}


def _greenhouse(context, mission) -> Optional[dict]:
    """The greenhouse setup's guide: the step it's on."""
    from core import greenhouse_setup as gs

    if mission.name != gs.MISSION or mission.status != "active":
        return None
    card = gs.page_card(context)
    if card is None:
        return None
    steps = [{"n": i + 1, "title": o.description, "done": o.progress >= 1, "current": i + 1 == card["step"]}
             for i, o in enumerate(mission.objectives)]
    return {"source": "greenhouse", "live": True, "title": gs.MISSION, "step": card["step"], "of": card["of"],
            "steps": steps,
            "do": card["title"], "why": card["why"], "watch": [], "check": "", "drafted": False, "actions": [],
            "needs": card["needs"],
            "say": card["say"] if card["say"].startswith("(") else f"Say “{card['say']}”. Tick the step here once "
                                                                  "it's done, or say “done”."}


GUIDES: tuple[Callable, ...] = (_trade, _greenhouse)


def guide_for(context, mission) -> Optional[dict]:
    """The mission's guide, from the first guide that knows it; None for a mission nothing guides (its objectives
    are the whole of it). A guide that fails is logged and skipped."""
    for guide in GUIDES:
        try:
            found = guide(context, mission)
        except Exception:
            log.exception("The %s guide failed for mission %s", guide.__name__, mission.mission_id)
            continue
        if found is not None:
            return found
    return None
