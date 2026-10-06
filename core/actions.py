"""
core.actions
==============

The action contract (2026-10-05, Phase 2 foundation, DEC-0013): how any
surface (the web Home, the phone, the glasses, later MIA herself) changes
something in a person's life. Always in five steps:

    Propose → Approve → Execute → Record → Undo

1. **Propose**: a surface (or MIA) asks for an action by `kind` and
   `params`. The engine checks it (does the bill exist? is this person
   allowed?) and writes the plain sentence the person will approve, in
   code ("Mark Electric paid ($120.00)"). Nothing has changed yet.
2. **Approve**: the person says yes. Only then:
3. **Execute**: the engine does it, through the same store method the
   rest of MIA uses (`mark_bill_paid()`, `mark_complete()`...).
4. **Record**: the stores record it in the history (core/life_events.py,
   with `source` and who), and the live version moves (core/live.py).
5. **Undo**: the change is recorded for "undo that" (core/undo_log.py);
   `undo()` puts it back while it's still the person's latest change.

The front end holds no business logic: it shows Life State's
`due[].action` suggestions and the proposals, and calls these. A child
account can only take the actions marked `child_ok`. Proposals live in
memory for a day: they're requests, not records (what happened is in the
history). Thread-safe.

The shape of a proposal is published in
`docs/schema/action.schema.json`.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

PROPOSED, EXECUTED, FAILED, REJECTED, UNDONE, EXPIRED = "proposed", "executed", "failed", "rejected", "undone", "expired"
KEEP_FOR = timedelta(days=1)


class ActionError(ValueError):
    """Why an action can't be proposed (said back to the person)."""


@dataclass(frozen=True)
class ActionType:
    kind: str
    label: str  # the button: "Mark paid"
    params: dict  # name -> what it is
    describe: Callable  # (context, params) -> the sentence to approve; raises ActionError
    execute: Callable  # (context, params) -> what happened, one line
    child_ok: bool = False

    def as_dict(self) -> dict:
        return {"kind": self.kind, "label": self.label, "params": dict(self.params), "child_ok": self.child_ok}


@dataclass
class Proposal:
    proposal_id: str
    kind: str
    params: dict
    summary: str  # what the person approves, made in code
    profile_id: Optional[str]
    proposed_by: str = "person"  # person | mia
    status: str = PROPOSED
    created_at: str = ""
    decided_at: Optional[str] = None
    result: str = ""
    _change: object = field(default=None, repr=False)  # the undo record, never sent

    def as_dict(self) -> dict:
        data = asdict(self)
        data.pop("_change", None)
        data["undoable"] = self.status == EXECUTED and self._change is not None
        return data


# ------------------------------------------------------------------ the actions


def _need(context, store: str):
    found = getattr(context, store, None)
    if found is None:
        raise ActionError("That isn't available on this MIA.")
    return found


def _money(amount) -> str:
    from core.region import money

    return money(amount)


def _bill(context, params):
    bill = _need(context, "budget").get_bill(str(params.get("bill_id", "")))
    if bill is None:
        raise ActionError("That bill isn't there anymore.")
    return bill


def _amount(params, default: float) -> float:
    raw = params.get("amount")
    if raw in (None, ""):
        return float(default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ActionError("The amount has to be a number.") from None
    if value < 0:
        raise ActionError("The amount can't be negative.")
    return value


def _describe_bill(context, params) -> str:
    bill = _bill(context, params)
    return f"Mark {bill.name} paid ({_money(_amount(params, bill.amount))})"


def _pay_bill(context, params) -> str:
    bill = _bill(context, params)
    amount = _amount(params, bill.amount)
    context.budget.mark_bill_paid(bill.bill_id, amount=amount)
    return f"{bill.name} is marked paid ({_money(amount)})."


def _source(context, params):
    source = _need(context, "budget").get_income_source(str(params.get("source_id", "")))
    if source is None:
        raise ActionError("That income source isn't there anymore.")
    return source


def _describe_income(context, params) -> str:
    source = _source(context, params)
    return f"Mark {source.name} received ({_money(_amount(params, source.expected_amount))})"


def _receive_income(context, params) -> str:
    source = _source(context, params)
    amount = _amount(params, source.expected_amount)
    context.budget.mark_income_received(source.source_id, amount=amount)
    return f"{source.name} is marked received ({_money(amount)})."


def _maintenance_task(context, params):
    maintenance = _need(context, "maintenance")
    task = maintenance.get_task(str(params.get("task_id", "")))
    if task is None:
        raise ActionError("That maintenance task isn't there anymore.")
    asset = maintenance.get_asset(task.asset_id)
    return task, asset


def _describe_maintenance(context, params) -> str:
    task, asset = _maintenance_task(context, params)
    meter = _meter_value(params)
    at = f" at {meter:g} {task.meter_unit}".rstrip() if meter is not None else ""
    return f"Mark \"{task.title}\" done" + (f" on {asset.name}" if asset else "") + " today" + at


def _meter_value(params):
    raw = params.get("meter_value")
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ActionError("The meter reading has to be a number.") from None


def _do_maintenance(context, params) -> str:
    task, asset = _maintenance_task(context, params)
    context.maintenance.mark_complete(task.task_id, meter_value=_meter_value(params))
    return f"{task.title} is done" + (f" on {asset.name}" if asset else "") + "."


def _task(context, params):
    task = _need(context, "tasks").get_task(str(params.get("task_id", "")))
    if task is None:
        raise ActionError("That task isn't there anymore.")
    if task.done:
        raise ActionError(f"\"{task.title}\" is already done.")
    return task


def _describe_task(context, params) -> str:
    return f"Check off \"{_task(context, params).title}\""


def _do_task(context, params) -> str:
    task = _task(context, params)
    context.tasks.update_task(task.task_id, done=True)
    return f"\"{task.title}\" is done."


def _routine(context, params):
    store = _need(context, "recurring_missions")
    template = next((t for t in store.all_templates() if t.template_id == str(params.get("template_id", ""))), None)
    if template is None:
        raise ActionError("That routine isn't there anymore.")
    return template


def _describe_routine(context, params) -> str:
    template = _routine(context, params)
    times = _amount(params, 1.0) or 1.0
    return f"Log {template.name}" + (f" ×{times:g}" if times != 1 else "")


def _log_routine(context, params) -> str:
    template = _routine(context, params)
    times = _amount(params, 1.0) or 1.0
    mission, _bonus = context.recurring_missions.ensure_current_missions(template, date.today())
    if not mission.objectives:
        raise ActionError(f"{template.name} doesn't have a goal to count toward.")
    context.missions.increment_tally(mission.mission_id, 0, delta=times)
    objective = context.missions.get_mission(mission.mission_id).objectives[0]
    return f"{template.name}: {objective.progress:g} of {objective.target:g}."


def _app(params):
    from core.web_surfaces import APPS_BY_ID

    app = APPS_BY_ID.get(str(params.get("module_id", "")))
    if app is None:
        raise ActionError("There's no app by that name.")
    return app


def _describe_app(context, params) -> str:
    from core.child_accounts import app_allowed
    from core.focus_presets import ALWAYS_VISIBLE

    app = _app(params)
    if params.get("visible", True) in (False, "false", 0, "0"):
        if app.module_id in ALWAYS_VISIBLE:
            raise ActionError(f"{app.name} always stays, so you can always find your way back.")
        return f"Hide {app.name} from your apps"
    if not app_allowed(context, app.module_id):
        from core.child_accounts import ASK_A_PARENT

        raise ActionError(ASK_A_PARENT)
    return f"Show {app.name} in your apps"


def _set_app(context, params) -> str:
    from core.focus_presets import set_app_visible

    app = _app(params)
    visible = params.get("visible", True) not in (False, "false", 0, "0")
    set_app_visible(context, app.module_id, visible)
    return f"{app.name} is {'in your apps' if visible else 'tucked away. Show it again from Apps any time'}."


def _favorite_on(params) -> bool:
    return params.get("favorite", True) not in (False, "false", 0, "0")


def _describe_favorite(context, params) -> str:
    from core.child_accounts import ASK_A_PARENT, app_allowed

    app = _app(params)
    if not app_allowed(context, app.module_id):
        raise ActionError(ASK_A_PARENT)
    return f"{'Add' if _favorite_on(params) else 'Remove'} {app.name} {'to' if _favorite_on(params) else 'from'} your favorites"


def _set_favorite(context, params) -> str:
    from core.focus_presets import set_app_favorite

    app = _app(params)
    set_app_favorite(context, app.module_id, _favorite_on(params))
    return f"{app.name} is {'a favorite' if _favorite_on(params) else 'no longer a favorite'}."


ACTION_TYPES: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("bill.pay", "Mark paid", {"bill_id": "the bill", "amount": "optional: what was paid, if different"},
               _describe_bill, _pay_bill),
    ActionType("income.receive", "Mark received", {"source_id": "the income source", "amount": "optional"},
               _describe_income, _receive_income),
    ActionType("maintenance.done", "Done", {"task_id": "the maintenance task",
                                            "meter_value": "optional: the meter reading now (hour-based tasks)"},
               _describe_maintenance,
               _do_maintenance),
    ActionType("task.done", "Done", {"task_id": "the project task"}, _describe_task, _do_task, child_ok=True),
    ActionType("routine.log", "Log it", {"template_id": "the routine", "amount": "optional: how many times"},
               _describe_routine, _log_routine, child_ok=True),
    ActionType("app.visibility", "Show / hide", {"module_id": "the app", "visible": "true to show, false to hide"},
               _describe_app, _set_app, child_ok=True),
    ActionType("app.favorite", "Favorite", {"module_id": "the app", "favorite": "true or false"},
               _describe_favorite, _set_favorite, child_ok=True),
)}


# Money (2026-10-06, DEC-0017): every change the Money screen makes. It
# builds on the classes above and adds its kinds to ACTION_TYPES itself,
# so either module can be imported first.
import core.money_actions  # noqa: E402,F401
import core.equipment_actions  # noqa: E402,F401  (Garage, Property, Greenhouse, Maintenance)
import core.kitchen_actions  # noqa: E402,F401
import core.workout_actions  # noqa: E402,F401
import core.estate_actions  # noqa: E402,F401
import core.mission_actions  # noqa: E402,F401  (Missions, Skills, Character)


# ------------------------------------------------------------------ the five steps


def _who(context) -> Optional[str]:
    from core.person_settings import person_id

    return person_id(context)


class ActionCenter:
    """The proposals waiting for a yes (context.actions)."""

    def __init__(self) -> None:
        self._proposals: dict[str, Proposal] = {}
        self._lock = threading.Lock()

    def _expire(self) -> None:
        cutoff = (datetime.now() - KEEP_FOR).isoformat(timespec="seconds")
        for proposal in self._proposals.values():
            if proposal.status == PROPOSED and proposal.created_at < cutoff:
                proposal.status = EXPIRED

    def propose(self, context, kind: str, params: Optional[dict] = None, proposed_by: str = "person") -> Proposal:
        """Step 1. Checks it and says what would happen; changes nothing."""
        from core.child_accounts import is_child

        action = ACTION_TYPES.get(kind)
        if action is None:
            raise ActionError(f"MIA can't do '{kind}'.")
        if not action.child_ok and getattr(context, "config", None) is not None and is_child(context):
            from core.child_accounts import ASK_A_PARENT

            raise ActionError(ASK_A_PARENT)
        params = dict(params or {})
        summary = action.describe(context, params)
        proposal = Proposal(uuid.uuid4().hex[:12], kind, params, summary, _who(context),
                            "mia" if proposed_by == "mia" else "person",
                            created_at=datetime.now().isoformat(timespec="seconds"))
        with self._lock:
            self._expire()
            self._proposals[proposal.proposal_id] = proposal
        return proposal

    def get(self, proposal_id: str, profile_id: Optional[str]) -> Proposal:
        with self._lock:
            self._expire()
            proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.profile_id != profile_id:
            raise KeyError(proposal_id)
        return proposal

    def pending(self, profile_id: Optional[str]) -> list[Proposal]:
        with self._lock:
            self._expire()
            return [p for p in self._proposals.values() if p.profile_id == profile_id and p.status == PROPOSED]

    def approve(self, context, proposal_id: str) -> Proposal:
        """Steps 2 to 5: the person said yes. Executes through the store,
        which records the history; the change is kept for undo."""
        from core import life_events
        from core.main_thread import publish
        from core.profile_manager import crediting
        from core.undo_log import recording

        proposal = self.get(proposal_id, _who(context))
        if proposal.status != PROPOSED:
            raise ActionError(f"That was already {proposal.status}.")
        action = ACTION_TYPES[proposal.kind]
        source = "assistant" if proposal.proposed_by == "mia" else "manual"
        try:
            with recording(f"action_{proposal.kind}", proposal.profile_id) as change, \
                    life_events.acting(source, proposal.profile_id), crediting(context, proposal.profile_id):
                proposal.result = action.execute(context, proposal.params)
        except ActionError as problem:
            proposal.status, proposal.result = FAILED, str(problem)
        except Exception:
            log.exception("Action %s failed.", proposal.kind)
            proposal.status, proposal.result = FAILED, "Something went wrong; nothing was changed."
        else:
            proposal.status = EXECUTED
            undo = getattr(context, "undo", None)
            if undo is not None and change.files:
                undo.add(change)
                proposal._change = change
            publish(context, "records.changed", action=f"action_{proposal.kind}")
        proposal.decided_at = datetime.now().isoformat(timespec="seconds")
        return proposal

    def reject(self, context, proposal_id: str) -> Proposal:
        proposal = self.get(proposal_id, _who(context))
        if proposal.status == PROPOSED:
            proposal.status = REJECTED
            proposal.decided_at = datetime.now().isoformat(timespec="seconds")
        return proposal

    def undo(self, context, proposal_id: str) -> Proposal:
        """Puts it back, while it's still the person's latest change."""
        from core.undo_log import undo_last

        proposal = self.get(proposal_id, _who(context))
        undo = getattr(context, "undo", None)
        if proposal.status != EXECUTED or proposal._change is None or undo is None:
            raise ActionError("That can't be undone.")
        recent = undo.recent(proposal.profile_id)
        if not recent or recent[0] is not proposal._change:
            raise ActionError("Something newer changed since; undo that first.")
        undo_last(context, proposal.profile_id)
        proposal.status, proposal._change = UNDONE, None
        proposal.decided_at = datetime.now().isoformat(timespec="seconds")
        return proposal


def suggested(kind: str, **params) -> dict:
    """The `action` a Life State item carries, for a surface to propose."""
    return {"kind": kind, "label": ACTION_TYPES[kind].label, "params": params}
