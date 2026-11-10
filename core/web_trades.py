"""
core.web_trades
=================

Trade Master on the web (web/trades.html, DEC-0149; the engine's core/trades.py, core/trade_session.py and
core/trade_actions.py). Three things on one screen:

- **The library**: every written job (build, install, repair) and diagnosis, grouped by trade, each saying whether a
  person has confirmed it or it's still drafted from its sources.
- **A job or diagnosis opened**: its outline (scope, permit, hazards, what to wear, tools, materials, the phases with
  their steps, the stop rules that apply, the sources), with Start and Make It a Mission.
- **The walkthrough** when one is going: the step in focus (or the check, for a diagnosis) with why, what to watch
  for and its hold point, where it is in the job, and the buttons: Next, Checked, Back, Stop, Yes and No. Every press
  is a `trade.*` action (core/trade_actions.py), so the hold points are enforced in code exactly as by voice, and each
  is undoable.

Formatting only here: the steps, holds and stop rules come from core/trades.py, never a model, and a drafted job is
always said to be drafted.
"""

from __future__ import annotations

from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

KIND_WORDS = {"build": "Build", "install": "Install", "repair": "Repair", "diagnosis": "Diagnosis"}


def _status_word(item) -> str:
    """Pure logic. Whether a person has confirmed the job or it's drafted from its sources."""
    from core import trades

    return "Confirmed" if item.status == trades.CONFIRMED else "Drafted from its sources"


def library() -> list[dict]:
    """Every written job and diagnosis, grouped by trade in core/trades.TRADES order (only trades with any):
    [{trade, name, items: [{id, name, kind, kind_word, scope, steps, status_word}]}]."""
    from core import trades

    trades._loaded()
    groups = []
    for trade_id, trade_name in trades.TRADES.items():
        items = [{"id": j.id, "name": j.name, "kind": j.kind, "kind_word": KIND_WORDS.get(j.kind, j.kind.title()),
                  "scope": j.scope, "steps": len(j.steps()), "status_word": _status_word(j)}
                 for j in trades.JOBS.values() if j.trade == trade_id]
        items += [{"id": d.id, "name": d.name, "kind": "diagnosis", "kind_word": "Diagnosis", "scope": d.safety,
                   "steps": len(d.checks), "status_word": _status_word(d)}
                  for d in trades.DIAGNOSES.values() if d.trade == trade_id]
        if items:
            groups.append({"trade": trade_id, "name": trade_name, "items": items})
    return groups


def _rules(item) -> list[dict]:
    """The stop rules that apply to a job or diagnosis: [{id, when, instead}]."""
    from core import trades

    return [{"id": r, "when": trades.STOP_RULES[r].when, "instead": trades.STOP_RULES[r].instead}
            for r in item.stop_if if r in trades.STOP_RULES]


def opened(item_id: str) -> Optional[dict]:
    """One job or diagnosis in full, or None when there's no such one. A job: scope, permit, hazards, what to wear,
    tools, materials, phases with their steps (what to do, and whether it has a hold point), stop rules, sources. A
    diagnosis: its safety line, its checks in order from the first, stop rules and sources."""
    from core import trades

    trades._loaded()
    job = trades.JOBS.get(item_id)
    if job is not None:
        return {"id": job.id, "name": job.name, "kind": job.kind, "kind_word": KIND_WORDS.get(job.kind, ""),
                "trade": trades.TRADES.get(job.trade, job.trade), "status_word": _status_word(job),
                "scope": job.scope, "permit": job.permit, "hazards": list(job.hazards), "ppe": list(job.ppe),
                "tools": list(job.tools), "materials": list(job.materials),
                "phases": [{"name": p.name, "steps": [{"do": s.do, "hold": bool(s.hold)} for s in p.steps]}
                           for p in job.phases],
                "steps": len(job.steps()), "rules": _rules(job), "sources": list(job.sources), "plan": job.plan}
    diag = trades.DIAGNOSES.get(item_id)
    if diag is not None:
        return {"id": diag.id, "name": diag.name, "kind": "diagnosis", "kind_word": "Diagnosis",
                "trade": trades.TRADES.get(diag.trade, diag.trade), "status_word": _status_word(diag),
                "scope": diag.safety, "first": diag.check(diag.start).ask if diag.check(diag.start) else "",
                "checks": len(diag.checks), "rules": _rules(diag), "sources": list(diag.sources)}
    return None


def walkthrough(context) -> Optional[dict]:
    """The job or diagnosis being worked, or None: its title and kind, what's said now, the step in focus with why,
    what to watch for and its hold (and whether it's checked), how far through, the phases (done, now, to come), its
    status (working, stopped with what to do instead, or finished with the result) and the mission it counts toward."""
    from core import trade_session as js

    store = getattr(context, "trade_session", None)
    if store is None:
        return None
    s = store.live()
    if s is None:
        return None
    item = js.item_of(s)
    out = {"item_id": s.item_id, "title": s.title, "kind": s.kind, "status": s.status, "say": js.say(s),
           "why": js.why(s) if s.status == js.WORKING else "", "watch": "", "hold": "", "checked": False,
           "progress": js.progress(s), "phases": [], "result": s.result, "stopped": s.stopped,
           "mission_id": s.mission_id, "rules": _rules(item) if item is not None else []}
    if item is None or s.status != js.WORKING:
        return out
    if s.kind == "diagnosis":
        check = item.check(s.check)
        out.update({"ask": check.ask if check else "", "step_text": check.ask if check else ""})
        return out
    p, _i, step = js._step(s, item)
    out.update({"step_text": step.do, "watch": " ".join(step.watch), "hold": step.hold,
                "checked": s.at in s.confirmed,
                "phases": [{"name": ph.name, "state": "done" if i < p else "now" if i == p else "next"}
                           for i, ph in enumerate(item.phases)]})
    return out


def screen(context, item_id: str = "") -> dict:
    """Trade Master: the library, the job or diagnosis opened (`item_id`, else the one being worked, else none), and
    the walkthrough when one is going. `available` is False when this MIA has no job store."""
    live = walkthrough(context)
    chosen = item_id or (live or {}).get("item_id", "")
    return {"available": getattr(context, "trade_session", None) is not None,
            "library": library(), "opened": opened(chosen) if chosen else None, "live": live,
            "standard": "Every job meets MIA's standard (a planning phase first, an inspection last, 12 or more "
                        "steps each with why, hold points, the stop rules its steps call for, two or more "
                        "sources), and stays drafted until a person confirms it."}
