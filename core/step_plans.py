"""
core.step_plans
=================

Plans across apps (UI-7, prompt 23's review; REQ-FUN-220: "a plan spanning several apps shall show every step with
its tier and let the person approve, change or drop steps one at a time"). A plan here is a list of changes MIA has
lined up, each one an action kind of some app with its parameters, shown before anything happens. Nothing in a plan
runs by itself: each step is done only when the person says so, one at a time, and each is undone like any other
change. (The Library's building plans are something else: core/plan_library.py.)

**A step** (`Step`) is one action on the action contract (core/actions.py): its kind and parameters, the sentence
its own `describe` gave, the app it belongs to, its tier (core/grants.py), and what it reaches and whether it can be
undone (core/action_effects.py). Its status is waiting, done, dropped, failed, or **can't** with the reason.

**What may be a step** (`_allowed`): only a kind that reaches the person's own records and can be undone, and that
doesn't always ask. A kind that reaches the system or someone outside, that can't be undone, that is tiered *never*,
that pays, buys, sends, publishes or deletes, or that touches a grant or a taught skill, is listed in the plan as
"can't: do this one from its own screen", so a plan can never be the way around an approval card. Marking a bill or a
debt paid (BOOKKEEPING) is the one exception: it writes his own record and moves no money.

**The first planner** (`plan_week`, the requirements' scenario W-2, "get me ready for the week") is code, not a
model: it takes today's list (core/today.py: overdue, today, waiting, soon) and makes a step of each item that
carries a suggested action. Other planners (a team's coordinator, a model's draft) hand `make()` the same list of
kinds and parameters and get the same checks.

**One at a time:** `do()` checks the step again as things are now (its `describe`), runs it as the person, and moves
on; `change()` gives it new parameters, re-checked; `drop()` leaves it out. The approval card pins the step it showed
(`fingerprint`), so a step changed before the press is refused. A failed step stays to try again, change or drop. A
plan with no step waiting or failed is finished, and a finished or dropped plan takes no more changes.

**A plan is a run** (core/runs.py, source "plans"): it shows in "what's running", waiting on the person at its next
step, and a restart finds it where it was. Each person's own (PERSONAL_STORES), sealed, written atomically so undoing
a step puts the plan back with the change it made.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "step_plans.json"
KEEP_FINISHED = 20
MAX_STEPS = 40
WAITING, DONE, DROPPED, FAILED, CANT = "waiting", "done", "dropped", "failed", "cant"
ELSEWHERE = "do this one from its own screen"
# Kinds that always ask by their name but only mark the person's own record paid (no money moves): may be steps.
BOOKKEEPING = frozenset({"bill.pay", "debt.pay"})


class PlanError(ValueError):
    """Something asked of a plan can't be done; its message is a plain sentence for the person."""


@dataclass
class Step:
    """One step of a plan (see the module's opening)."""
    step_id: str
    kind: str
    params: dict = field(default_factory=dict)
    label: str = ""  # the action's button ("Mark paid")
    summary: str = ""  # the sentence its describe gave
    app: str = ""  # the app it belongs to
    source: str = ""  # what it came from, in words ("Electric bill, due Friday")
    tier: str = ""
    reach: str = "records"
    reversibility: str = "undoable"
    status: str = WAITING
    result: str = ""
    why: str = ""  # for can't and failed


@dataclass
class StepPlan:
    """A plan: its steps in order, who made it, and its run."""
    plan_id: str
    title: str
    made_by: str = "mia"
    created: str = ""
    status: str = "open"  # open | done | dropped
    run_id: str = ""
    steps: list = field(default_factory=list)

    def waiting(self) -> list[Step]:
        """The steps still to decide: waiting, or failed (to try again, change or drop)."""
        return [s for s in self.steps if s.status in (WAITING, FAILED)]

    def number(self, step: Step) -> int:
        """A step's number as the plan lists it (1 is the first)."""
        return self.steps.index(step) + 1


def _allowed(kind: str) -> str:
    """Pure logic. "" when a kind may be a plan's step, else why not (see the module's opening). Besides reach and
    undo, a kind that always asks (paying, buying, sending, publishing, deleting, a profile, a taught skill: core/
    taught_skills.always_asks) or that touches a grant is never a step, except BOOKKEEPING: marking a bill or a debt
    paid writes the person's own record and moves no money (Opus's review of UI-7, 2026-11-17)."""
    from core import grants
    from core.action_effects import effect_of
    from core.actions import ACTION_TYPES
    from core.taught_skills import always_asks

    if kind not in ACTION_TYPES:
        return "MIA has no such action"
    if kind.startswith("steps."):
        return "a plan can't hold a plan's own steps"
    if kind.startswith("grant.") or (always_asks(kind) and kind not in BOOKKEEPING):
        return ELSEWHERE
    reach, reversible = effect_of(kind)
    if grants.tier_of(kind) == grants.NEVER or reach != "records" or reversible != "undoable":
        return ELSEWHERE
    return ""


def fingerprint(step: Step) -> str:
    """Pure logic. A short hash of a step's kind and parameters: the approval card carries it, so the step that runs
    is the one the person saw (a change in between makes `do` refuse)."""
    import hashlib

    body = json.dumps([step.kind, step.params], sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _app_of(kind: str) -> str:
    """The app that owns an action kind, by name, from the Application Registry ("" when it can't be told)."""
    try:
        from core import app_registry

        reg = app_registry.load()
        owner = reg.owner_of(kind)
        return (reg.get(owner) or {}).get("name", "") if owner else ""
    except Exception:  # noqa: BLE001 - a plan still reads without its apps' names
        return ""


class StepPlanBook:
    """A person's plans in steps, in `step_plans.json`: the open ones and the last KEEP_FINISHED finished."""

    # The epistemic contract (DEC-0173, G3): who made each plan, when, and that its steps were computed from records.
    EPISTEMIC = {"record": StepPlan, "source": "made_by", "at": "created", "how": "computed"}

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the person's plans (or data/'s)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        """Reads the file; a missing or unreadable one is no plans (sealed at rest: open_text opens it)."""
        self.plans: dict[str, StepPlan] = {}
        try:
            raw = json.loads(open_text(self._file)).get("plans", [])
        except (OSError, ValueError):
            return
        step_names, plan_names = set(Step.__dataclass_fields__), set(StepPlan.__dataclass_fields__)
        for item in raw:
            if not (isinstance(item, dict) and item.get("plan_id")):
                continue
            try:
                steps = [Step(**{k: v for k, v in s.items() if k in step_names}) for s in item.get("steps", [])]
                plan = StepPlan(**{k: v for k, v in item.items() if k in plan_names and k != "steps"})
            except TypeError:
                continue
            plan.steps = steps
            self.plans[plan.plan_id] = plan

    def _save(self) -> None:
        """Writes atomically (inside "undo that"), keeping every open plan and the newest KEEP_FINISHED finished."""
        closed = sorted((p for p in self.plans.values() if p.status != "open"), key=lambda p: p.created, reverse=True)
        for old in closed[KEEP_FINISHED:]:
            self.plans.pop(old.plan_id, None)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "plans": [asdict(p) for p in self.plans.values()]},
                                                 indent=1, ensure_ascii=False))

    # ------------------------------------------------------------------ reading

    def open_plans(self) -> list[StepPlan]:
        """The plans with a step still waiting, newest first."""
        return sorted((p for p in self.plans.values() if p.status == "open"), key=lambda p: p.created, reverse=True)

    def get(self, plan_id: str) -> StepPlan:
        """A plan by id; PlanError when it isn't there."""
        plan = self.plans.get(str(plan_id or ""))
        if plan is None:
            raise PlanError("That plan isn't here any more.")
        return plan

    def find(self, plan_id: str = "") -> StepPlan:
        """The plan named, or the newest open one when none is; PlanError when there's nothing open."""
        if plan_id:
            return self.get(plan_id)
        found = self.open_plans()
        if not found:
            raise PlanError("There's no plan open. Say \"plan my week\" to make one.")
        return found[0]

    def step(self, plan: StepPlan, which) -> Step:
        """A plan's step by id, or by its number as listed; PlanError when it isn't one."""
        word = str(which or "").strip()
        hit = next((s for s in plan.steps if s.step_id == word), None)
        if hit is None and word.isdigit() and 1 <= int(word) <= len(plan.steps):
            hit = plan.steps[int(word) - 1]
        if hit is None:
            raise PlanError(f"\"{plan.title}\" has no step {word or 'like that'}.")
        return hit

    # ------------------------------------------------------------------ making

    def make(self, context, title: str, items: list[dict], made_by: str = "mia",
             now: Optional[datetime] = None) -> StepPlan:
        """A new plan from [{kind, params, source}], each checked now: a kind that may not be a step, or whose own
        check refuses it, is kept in the list as "can't" with the reason, so the person sees everything that was
        considered. The same kind with the same parameters appears once. PlanError when nothing can be done."""
        from core import grants
        from core.action_effects import effect_of
        from core.actions import ACTION_TYPES

        now = now or datetime.now()
        steps, seen = [], set()
        for item in items[:MAX_STEPS]:
            kind, params = str(item.get("kind") or ""), dict(item.get("params") or {})
            key = (kind, json.dumps(params, sort_keys=True, default=str))
            if key in seen:
                continue
            seen.add(key)
            step = Step(uuid.uuid4().hex[:8], kind, params, source=str(item.get("source") or "")[:160])
            refused = _allowed(kind)
            if refused:
                step.status, step.why = CANT, refused
                step.summary = step.source or kind
            else:
                action = ACTION_TYPES[kind]
                step.label, step.app, step.tier = action.label, _app_of(kind), grants.tier_of(kind) or ""
                step.reach, step.reversibility = effect_of(kind)
                try:
                    step.summary = action.describe(context, params)
                except ValueError as problem:  # ActionError is one
                    step.status, step.why, step.summary = CANT, str(problem), step.source or action.label
            steps.append(step)
        if not any(s.status == WAITING for s in steps):
            raise PlanError("Nothing in that has a step I can take for you.")
        plan = StepPlan(uuid.uuid4().hex[:10], " ".join(str(title or "A plan").split())[:80], made_by,
                        now.isoformat(timespec="seconds"), steps=steps)
        with self._lock:
            self.plans[plan.plan_id] = plan
            self._run_started(context, plan)
            self._save()
        return plan

    # ------------------------------------------------------------------ one step at a time

    def do(self, context, plan_id: str, which, seen: str = "") -> Step:
        """Does one waiting (or failed, to try again) step as the person: checked again as things are now, then run.
        `seen` is the step's `fingerprint` from the approval card; when given and the step has changed since, it
        refuses. PlanError when it can't be done (it stays as it was, to change or drop); a step that breaks while
        running is marked failed with why, and may be tried again."""
        from core import grants
        from core.actions import ACTION_TYPES

        with self._lock:
            plan = self.get(plan_id)
            step = self.step(plan, which)
            if plan.status != "open":
                raise PlanError("That plan is already finished.")
            if step.status not in (WAITING, FAILED):
                raise PlanError(f"Step {plan.number(step)} is already {_said(step.status)}.")
            if seen and seen != fingerprint(step):
                raise PlanError(f"Step {plan.number(step)} changed since you saw it. Look at it again first.")
            refused = _allowed(step.kind)
            if refused:
                raise PlanError(f"Step {plan.number(step)} can't be done here: {refused}.")
            action = ACTION_TYPES[step.kind]
            grants.require(step.kind, grants.PERSON)
            try:
                step.summary = action.describe(context, step.params)
            except ValueError as problem:
                raise PlanError(f"Step {plan.number(step)} can't be done as it is: {problem}") from None
            try:
                step.result = str(action.execute(context, step.params) or "Done.")
                step.status = DONE
            except ValueError as problem:
                step.status, step.why = FAILED, str(problem)
            except Exception as problem:  # noqa: BLE001 - one broken step never takes the plan with it
                log.exception("Plan %s: step %s (%s) broke", plan.plan_id, step.step_id, step.kind)
                step.status, step.why = FAILED, f"it broke ({type(problem).__name__})"
            self._moved(context, plan, step)
            self._save()
            return step

    def change(self, context, plan_id: str, which, params: dict) -> Step:
        """Gives a waiting, failed or can't step of an open plan new parameters (merged over its own), checked by
        its action; PlanError when the plan is finished or the action refuses them, and the step is left as it was.
        A step changed after its card was shown is refused at the press (`fingerprint`)."""
        from core.actions import ACTION_TYPES

        with self._lock:
            plan = self.get(plan_id)
            step = self.step(plan, which)
            if plan.status != "open" or step.status not in (WAITING, CANT, FAILED) or _allowed(step.kind):
                raise PlanError(f"Step {plan.number(step)} can't be changed.")
            merged = {**step.params, **{k: v for k, v in dict(params or {}).items() if k in step.params}}
            try:
                summary = ACTION_TYPES[step.kind].describe(context, merged)
            except ValueError as problem:
                raise PlanError(str(problem)) from None
            step.params, step.summary, step.status, step.why = merged, summary, WAITING, ""
            self._save()
            return step

    def drop(self, context, plan_id: str, which) -> Step:
        """Leaves one waiting (or failed) step out of the plan."""
        with self._lock:
            plan = self.get(plan_id)
            step = self.step(plan, which)
            if plan.status != "open" or step.status not in (WAITING, FAILED):
                raise PlanError(f"Step {plan.number(step)} is already {_said(step.status)}.")
            step.status = DROPPED
            self._moved(context, plan, step)
            self._save()
            return step

    def drop_plan(self, context, plan_id: str) -> StepPlan:
        """Leaves out every step still waiting and closes the plan; what was done stays done."""
        with self._lock:
            plan = self.get(plan_id)
            if plan.status != "open":
                raise PlanError("That plan is already finished.")
            for step in plan.waiting():
                step.status = DROPPED
            plan.status = "dropped"
            self._run_finish(context, plan, "stopped", "you dropped the rest")
            self._save()
            return plan

    # ------------------------------------------------------------------ the run record (never breaks a plan)

    def _runs(self, context):
        """The person's run book, or None."""
        return getattr(context, "runs", None)

    def _run_started(self, context, plan: StepPlan) -> None:
        """Starts the plan's run and has it wait on the person at the first step."""
        runs = self._runs(context)
        if runs is None:
            return
        try:
            first = plan.waiting()[0]
            run = runs.start("plans", f"step_plan:{plan.plan_id}", plan.title, at=str(plan.number(first)))
            plan.run_id = run.run_id
            runs.wait(run.run_id, str(plan.number(first)), "approval", first.summary)
        except Exception:  # noqa: BLE001
            log.exception("Plan %s: its run couldn't be started", plan.plan_id)

    def _moved(self, context, plan: StepPlan, step: Step) -> None:
        """After a step was done, failed or dropped: the run notes it and waits at the next, or the plan finishes."""
        left = plan.waiting()
        runs = self._runs(context)
        try:
            if runs is not None and plan.run_id:
                said = {DONE: step.result, FAILED: f"Failed: {step.why}", DROPPED: "Left out."}.get(step.status, "")
                runs.step(plan.run_id, str(plan.number(step)), said=f"{step.summary}. {said}".strip(),
                          actions=[step.kind] if step.status == DONE else (),
                          next_at=str(plan.number(left[0])) if left else "")
                if left:
                    runs.wait(plan.run_id, str(plan.number(left[0])), "approval", left[0].summary)
        except Exception:  # noqa: BLE001
            log.exception("Plan %s: its run couldn't be updated", plan.plan_id)
        if not left:
            plan.status = "done"
            self._run_finish(context, plan, "done", "")

    def _run_finish(self, context, plan: StepPlan, status: str, why: str) -> None:
        """Ends the plan's run."""
        runs = self._runs(context)
        try:
            if runs is not None and plan.run_id:
                runs.finish(plan.run_id, status, why)
        except Exception:  # noqa: BLE001
            log.exception("Plan %s: its run couldn't be finished", plan.plan_id)


def _said(status: str) -> str:
    """Pure logic. A step's status in words."""
    return {WAITING: "waiting", DONE: "done", DROPPED: "left out", FAILED: "failed", CANT: "one I can't do"}.get(
        status, status)


def book(context) -> StepPlanBook:
    """The person's plans: the context's (each person's own, core/personal_data.py), else one on data/."""
    found = getattr(context, "step_plans", None)
    return found if found is not None else StepPlanBook(context)


def week_items(context, today: Optional[date] = None) -> list[dict]:
    """What today's list offers a step for (core/today.py): each item that carries a suggested action, as
    {kind, params, source}, in the list's own order (overdue first)."""
    from core.today import today_items

    out = []
    for item in today_items(context, today):
        action = item.action or {}
        if action.get("kind"):
            out.append({"kind": action["kind"], "params": dict(action.get("params") or {}),
                        "source": item.title + (f" ({item.detail})" if item.detail else "")})
    return out


def plan_week(context, today: Optional[date] = None, now: Optional[datetime] = None) -> StepPlan:
    """"Get me ready for the week" (W-2): a plan from today's list. PlanError when nothing due has a step, or when a
    week's plan is already open (so asking twice doesn't make two)."""
    today = today or date.today()
    title = f"Your week, from {today.strftime('%A')} {today.day} {today.strftime('%B')}"
    plans = book(context)
    if any(p.title == title for p in plans.open_plans()):
        raise PlanError("This week's plan is already open.")
    items = week_items(context, today)
    if not items:
        raise PlanError("Nothing due has a step I can take for you.")
    return plans.make(context, title, items, made_by="mia", now=now)


def step_dict(plan: StepPlan, step: Step) -> dict:
    """A step as a screen shows it."""
    return {"step_id": step.step_id, "number": plan.number(step), "kind": step.kind, "label": step.label,
            "summary": step.summary, "app": step.app, "source": step.source, "tier": step.tier, "reach": step.reach,
            "reversibility": step.reversibility, "status": step.status, "result": step.result, "why": step.why,
            "params": dict(step.params)}


def page(context) -> dict:
    """The Step By Step page's data: open plans with every step, and the plans finished lately (title and counts)."""
    plans = book(context)
    closed = sorted((p for p in plans.plans.values() if p.status != "open"), key=lambda p: p.created, reverse=True)
    return {"open": [{"plan_id": p.plan_id, "title": p.title, "made_by": p.made_by, "created": p.created,
                      "waiting": len(p.waiting()), "steps": [step_dict(p, s) for s in p.steps]}
                     for p in plans.open_plans()],
            "finished": [{"plan_id": p.plan_id, "title": p.title, "status": p.status,
                          "done": sum(1 for s in p.steps if s.status == DONE), "steps": len(p.steps)}
                         for p in closed[:5]]}


def said(context, plan_id: str = "") -> str:
    """The open plan in words, numbered as `step` reads numbers: for voice."""
    try:
        plan = book(context).find(plan_id)
    except PlanError as problem:
        return str(problem)
    lines = []
    for step in plan.steps:
        n = plan.number(step)
        if step.status == WAITING:
            lines.append(f"{n}. {step.summary}" + (f" (in {step.app})" if step.app else ""))
        elif step.status == CANT:
            lines.append(f"{n}. {step.summary}: I can't do this one ({step.why}).")
        else:
            lines.append(f"{n}. {step.summary}: {_said(step.status)}.")
    waiting = len(plan.waiting())
    return (f"{plan.title}: {waiting} step{'s' if waiting != 1 else ''} waiting for you.\n" + "\n".join(lines)
            + "\nSay \"do step 1\", \"drop step 2\", or do them on the Step By Step page. Nothing runs until you say.")
