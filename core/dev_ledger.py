"""
core.dev_ledger
=================

What MIA (and every member of the council) can be trusted with, measured
(DEC-0075, T-0028; `docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md` section 5).

**Computed every time from the history (work/activity.jsonl), never stored**,
so it can't be edited, and this file is on the lab's protected list: MIA
can't grade herself.

- **Skills**, by what a task touched: fixing failing tests (only `tests/`),
  documentation (`docs/`), screens (`web/`), engine changes (the rest), and
  reviewing (from reviews).
- **Outcomes**, each a pass or a fail:
  - a writer's change: merged is a pass; reverted, or stopped at the lab's
    check, a fail;
  - MIA's shadow attempts (core/mia_coder.py): what the lab's check said;
  - a reviewer's objection: *upheld* (the change was rewritten after it) is
    a pass, *overturned* (answered and merged without a rewrite) a fail; an
    approval of a change that merged and stayed is a pass, of one the lab
    reverted a fail.
- **Score**: over the latest 30 outcomes, the success rate and its lower
  confidence bound (Wilson, 90%): a rate from three tries means nothing.
- **Stages** (section 5.2) come from the bound, not from task counts:
  Observer (the skill is being done by others), Apprentice (5 attempts),
  Contributor (bound 60%+ over 10+), Developer (80%+ over 20+),
  Independent (90%+ over 30+). The ledger *proposes*; Zac confirms
  (`confirm()`, a `ledger` event); a drop shows at once (the stage shown is
  never above what the evidence supports now). **A stage never grants a
  permission** (DEC-0072): roles and tiers stay in work/agents.json, Zac's.
"""

from __future__ import annotations

import math
from typing import Optional

from core import work_activity as activity
from core import work_tasks as tasks_mod

WINDOW = 30
Z = 1.645  # 90%
STAGES = ("Not started", "Observer", "Apprentice", "Contributor", "Developer", "Independent")
SKILLS = ("fix failing tests", "documentation", "screens", "engine changes", "reviewing")


def wilson(passed: int, n: int, z: float = Z) -> float:
    """Pure logic. The lower bound of the success rate's confidence interval."""
    if n == 0:
        return 0.0
    p = passed / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / (1 + z * z / n))


def skill_of(task) -> str:
    """Pure logic. Which skill a task's change is, from the files it touches."""
    files = [f for f in getattr(task, "files", []) or [] if f]
    if files and all(f.startswith("tests/") for f in files):
        return "fix failing tests"
    if files and all(f.startswith("docs/") for f in files):
        return "documentation"
    if files and all(f.startswith("web/") for f in files):
        return "screens"
    return "engine changes"


def provider_of(who: str) -> str:
    """Pure logic. The provider in a "who" like "claude (anthropic)": the part in the last parentheses, else the whole name."""
    return who.rsplit("(", 1)[-1].rstrip(")") if who.endswith(")") else who


def outcomes(events: list[dict], tasks: dict) -> list[dict]:
    """Pure logic. Every graded outcome in the history: {provider, skill, task, at, passed, why}."""
    out = []
    by_task: dict[str, list[dict]] = {}
    for e in events:
        by_task.setdefault(e.get("task", ""), []).append(e)
    for task_id, history in by_task.items():
        task = tasks.get(task_id)
        if task is None:
            continue
        skill = skill_of(task)
        writer = next((e["who"] for e in history if e.get("action") == "loop" and str(e.get("detail", "")).startswith("write")), "")
        final = next((e for e in reversed(history) if e.get("action") == "approve"), None)
        merged = bool(final) and str(final.get("detail", "")).startswith("merged")
        reverted = bool(final) and str(final.get("detail", "")).startswith("reverted")  # the last word decides: a merge after a revert is a pass
        stopped = any(e.get("action") == "note" and "Stopped at check" in str(e.get("detail", "")) for e in history)
        after = history[history.index(final) + 1:] if final is not None else []  # by position: a second can hold both
        reopened = reverted and any(e.get("action") == "move" and str(e.get("detail", "")).startswith("review")
                                    for e in after)  # tried again: pending
        if writer and (merged or reverted or stopped) and not reopened:
            out.append({"provider": provider_of(writer), "skill": skill, "task": task_id,
                        "at": (final or history[-1]).get("at", ""), "passed": merged,
                        "why": "merged" if merged else "reverted" if reverted else "stopped at the check"})
        for e in history:
            if e.get("action") == "shadow":
                out.append({"provider": provider_of(e["who"]), "skill": skill, "task": task_id, "at": e.get("at", ""),
                            "passed": str(e.get("detail", "")).startswith("pass"), "why": "shadow attempt"})
        for i, e in enumerate(history):
            if e.get("action") != "review":
                continue
            verdict = str(e.get("detail", "")).split(":", 1)[0]
            later = history[i + 1:]
            rewritten = any(x.get("action") == "loop" and str(x.get("detail", "")).startswith("write") for x in later)
            if verdict == "changes":
                if rewritten:
                    passed, why = True, "objection upheld"
                elif merged:
                    passed, why = False, "objection overturned"
                else:
                    continue  # not settled yet
            elif verdict == "approve" and (merged or reverted):
                passed, why = merged and not reverted, "approved and it held" if merged and not reverted else "approved a change that broke"
            else:
                continue
            out.append({"provider": provider_of(e["who"]), "skill": "reviewing", "task": task_id, "at": e.get("at", ""),
                        "passed": passed, "why": why})
    return sorted(out, key=lambda o: o["at"])


def stage_for(attempts: int, bound: float, observed: bool) -> int:
    """Pure logic. The stage the evidence supports (an index into STAGES)."""
    if attempts >= 30 and bound >= 0.9:
        return 5
    if attempts >= 20 and bound >= 0.8:
        return 4
    if attempts >= 10 and bound >= 0.6:
        return 3
    if attempts >= 5:
        return 2
    return 1 if observed or attempts else 0


def ledger(log=activity.ACTIVITY, tasks_dir=tasks_mod.TASKS_DIR) -> dict:
    """provider -> skill -> {attempts, passed, rate, bound, stage, confirmed, shown, recent}."""
    events = activity.events(log)
    found = outcomes(events, tasks_mod.load(tasks_dir))
    confirmed = {}
    for e in events:
        if e.get("action") == "ledger" and e.get("who") == "zac":
            provider, _, rest = str(e.get("detail", "")).partition(" ")
            skill, _, stage = rest.rpartition(" stage ")
            if stage.isdigit():
                confirmed[(provider, skill)] = int(stage)
    observed = {o["skill"] for o in found}
    providers = sorted({o["provider"] for o in found} | {"ollama-coder"})  # MIA's coder always has a row
    out: dict[str, dict] = {}
    for provider in providers:
        out[provider] = {}
        for skill in SKILLS:
            mine = [o for o in found if o["provider"] == provider and o["skill"] == skill][-WINDOW:]
            passed = sum(1 for o in mine if o["passed"])
            bound = wilson(passed, len(mine))
            stage = stage_for(len(mine), bound, skill in observed)
            ok = confirmed.get((provider, skill), 0)
            out[provider][skill] = {"attempts": len(mine), "passed": passed,
                                    "rate": round(passed / len(mine), 2) if mine else None, "bound": round(bound, 2),
                                    "stage": stage, "confirmed": ok,
                                    # up to Apprentice shows by itself; above that only as far as Zac confirmed
                                    # and the evidence still supports
                                    "shown": stage if stage <= 2 else max(2, min(stage, ok)),
                                    "proposed": stage > ok and stage >= 3, "recent": mine[-3:][::-1]}
    return out


def confirm(provider: str, skill: str, stage: int, log=activity.ACTIVITY) -> None:
    """Zac confirms a stage the evidence supports now (never above it). It grants no permission."""
    if skill not in SKILLS:
        raise ValueError(f"The skill is one of {', '.join(SKILLS)}.")
    supported = ledger(log).get(provider, {}).get(skill, {}).get("stage", 0)
    if not 0 < stage <= supported:
        raise ValueError(f"The evidence supports {STAGES[supported]} at most.")
    activity.record("zac", "ledger", "", f"{provider} {skill} stage {stage}", log)
