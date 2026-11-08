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
    """One kind of change MIA can make ("bill.pay"): the button's label, the parameters it takes (name -> what it is),
    `describe` (context, params -> the sentence the person approves; raises ActionError when it can't be done),
    `execute` (context, params -> one line saying what happened), and whether a child account may use it.
    """
    kind: str
    label: str  # the button: "Mark paid"
    params: dict  # name -> what it is
    describe: Callable  # (context, params) -> the sentence to approve; raises ActionError
    execute: Callable  # (context, params) -> what happened, one line
    child_ok: bool = False

    def as_dict(self) -> dict:
        """What /api/actions lists for this kind: kind, label, params and child_ok (never the functions)."""
        return {"kind": self.kind, "label": self.label, "params": dict(self.params), "child_ok": self.child_ok}


@dataclass
class Proposal:
    """One proposed change waiting for, or past, its decision: the kind and params, the summary the person approves
    (made in code, never by the model), whose it is, who proposed it (the person or MIA), its status (proposed,
    executed, rejected, failed, expired, undone), when, the result line, what it earned (for a surface to celebrate),
    and the undo record (kept server-side, never sent).
    """
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
    # What finishing it earned, for a surface to celebrate (the glasses'
    # "Objective Complete +30 XP", Zac 2026-10-16): see reward_for().
    reward: Optional[dict] = None
    _change: object = field(default=None, repr=False)  # the undo record, never sent

    def as_dict(self) -> dict:
        """The proposal as sent to a screen: everything but the undo record, plus whether it can still be undone."""
        data = asdict(self)
        data.pop("_change", None)
        data["undoable"] = self.status == EXECUTED and self._change is not None
        return data


# ------------------------------------------------------------------ the actions


def _need(context, store: str):
    """A store from the context, or ActionError when this MIA doesn't have it."""
    found = getattr(context, store, None)
    if found is None:
        raise ActionError("That isn't available on this MIA.")
    return found


def _money(amount) -> str:
    """An amount in the person's currency (core/region.py)."""
    from core.region import money

    return money(amount)


def _bill(context, params):
    """The bill the params name, or ActionError when it's gone."""
    bill = _need(context, "budget").get_bill(str(params.get("bill_id", "")))
    if bill is None:
        raise ActionError("That bill isn't there anymore.")
    return bill


def _amount(params, default: float) -> float:
    """The amount from the params (the default when none is given); ActionError when it isn't a number or is negative."""
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
    """The sentence the approval card shows for `bill.pay` (Propose); raises ActionError when it can't be done."""
    bill = _bill(context, params)
    return f"Mark {bill.name} paid ({_money(_amount(params, bill.amount))})"


def _pay_bill(context, params) -> str:
    """Does `bill.pay` once approved, and says what happened. The amount defaults to the bill's."""
    bill = _bill(context, params)
    amount = _amount(params, bill.amount)
    context.budget.mark_bill_paid(bill.bill_id, amount=amount)
    return f"{bill.name} is marked paid ({_money(amount)})."


def _source(context, params):
    """The income source the params name, or ActionError when it's gone."""
    source = _need(context, "budget").get_income_source(str(params.get("source_id", "")))
    if source is None:
        raise ActionError("That income source isn't there anymore.")
    return source


def _describe_income(context, params) -> str:
    """The sentence the approval card shows for `income.receive` (Propose); raises ActionError when it can't be done."""
    source = _source(context, params)
    return f"Mark {source.name} received ({_money(_amount(params, source.expected_amount))})"


def _receive_income(context, params) -> str:
    """Does `income.receive` once approved, and says what happened. The amount defaults to what was expected."""
    source = _source(context, params)
    amount = _amount(params, source.expected_amount)
    context.budget.mark_income_received(source.source_id, amount=amount)
    return f"{source.name} is marked received ({_money(amount)})."


def _maintenance_task(context, params):
    """The maintenance task the params name and its asset, or ActionError when it's gone."""
    maintenance = _need(context, "maintenance")
    task = maintenance.get_task(str(params.get("task_id", "")))
    if task is None:
        raise ActionError("That maintenance task isn't there anymore.")
    asset = maintenance.get_asset(task.asset_id)
    return task, asset


def _describe_maintenance(context, params) -> str:
    """The sentence the approval card shows for `maintenance.done` (Propose); raises ActionError when it can't be done. It includes the meter reading when one is given."""
    task, asset = _maintenance_task(context, params)
    meter = _meter_value(params)
    at = f" at {meter:g} {task.meter_unit}".rstrip() if meter is not None else ""
    return f"Mark \"{task.title}\" done" + (f" on {asset.name}" if asset else "") + " today" + at


def _meter_value(params):
    """The meter reading from the params, or None; ActionError when it isn't a number."""
    raw = params.get("meter_value")
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ActionError("The meter reading has to be a number.") from None


def _do_maintenance(context, params) -> str:
    """Does `maintenance.done` once approved, and says what happened."""
    task, asset = _maintenance_task(context, params)
    context.maintenance.mark_complete(task.task_id, meter_value=_meter_value(params))
    return f"{task.title} is done" + (f" on {asset.name}" if asset else "") + "."


def _task(context, params):
    """The task the params name, or ActionError when it's gone or already done."""
    task = _need(context, "tasks").get_task(str(params.get("task_id", "")))
    if task is None:
        raise ActionError("That task isn't there anymore.")
    if task.done:
        raise ActionError(f"\"{task.title}\" is already done.")
    return task


def _describe_task(context, params) -> str:
    """The sentence the approval card shows for `task.done` (Propose); raises ActionError when it can't be done."""
    return f"Check off \"{_task(context, params).title}\""


def _do_task(context, params) -> str:
    """Does `task.done` once approved, and says what happened."""
    task = _task(context, params)
    context.tasks.update_task(task.task_id, done=True)
    return f"\"{task.title}\" is done."


def _routine(context, params):
    """The household routine (a recurring-mission template) the params name, or ActionError."""
    store = _need(context, "recurring_missions")
    template = next((t for t in store.all_templates() if t.template_id == str(params.get("template_id", ""))), None)
    if template is None:
        raise ActionError("That routine isn't there anymore.")
    return template


def _describe_routine(context, params) -> str:
    """The sentence the approval card shows for `routine.log` (Propose); raises ActionError when it can't be done. It shows how many times when more than one."""
    template = _routine(context, params)
    times = _amount(params, 1.0) or 1.0
    return f"Log {template.name}" + (f" ×{times:g}" if times != 1 else "")


def _log_routine(context, params) -> str:
    """Does `routine.log` once approved, and says what happened. It counts toward this period's mission for the routine (made if needed) and
    says the progress.
    """
    template = _routine(context, params)
    times = _amount(params, 1.0) or 1.0
    mission, _bonus = context.recurring_missions.ensure_current_missions(template, date.today())
    if not mission.objectives:
        raise ActionError(f"{template.name} doesn't have a goal to count toward.")
    context.missions.increment_tally(mission.mission_id, 0, delta=times)
    objective = context.missions.get_mission(mission.mission_id).objectives[0]
    return f"{template.name}: {objective.progress:g} of {objective.target:g}."


def _app(params):
    """The app the params name (web_surfaces.APPS_BY_ID), or ActionError."""
    from core.web_surfaces import APPS_BY_ID

    app = APPS_BY_ID.get(str(params.get("module_id", "")))
    if app is None:
        raise ActionError("There's no app by that name.")
    return app


def _describe_app(context, params) -> str:
    """The sentence the approval card shows for `app.visibility` (Propose); raises ActionError when it can't be done. The apps that must always stay (ALWAYS_VISIBLE) can't be hidden, and a
    child can't show an app their account doesn't allow.
    """
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
    """Does `app.visibility` once approved, and says what happened. Shows or tucks away an app for this person."""
    from core.focus_presets import set_app_visible

    app = _app(params)
    visible = params.get("visible", True) not in (False, "false", 0, "0")
    set_app_visible(context, app.module_id, visible)
    return f"{app.name} is {'in your apps' if visible else 'tucked away. Show it again from Apps any time'}."


def _favorite_on(params) -> bool:
    """Whether the params star (True) or unstar the app; the default is to star it."""
    return params.get("favorite", True) not in (False, "false", 0, "0")


def _describe_favorite(context, params) -> str:
    """The sentence the approval card shows for `app.favorite` (Propose); raises ActionError when it can't be done. A child can't star an app their account doesn't allow."""
    from core.child_accounts import ASK_A_PARENT, app_allowed

    app = _app(params)
    if not app_allowed(context, app.module_id):
        raise ActionError(ASK_A_PARENT)
    return f"{'Add' if _favorite_on(params) else 'Remove'} {app.name} {'to' if _favorite_on(params) else 'from'} your favorites"


def _set_favorite(context, params) -> str:
    """Does `app.favorite` once approved, and says what happened. Favorites are also what the glasses show first."""
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
import core.account_actions  # noqa: E402,F401  (Profile, Settings)
import core.creation_actions  # noqa: E402,F401  (MIA's creations and record sets, DEC-0091)
import core.fitness_actions  # noqa: E402,F401  (fitness plan, weigh-ins, food, training)
import core.plan_import  # noqa: E402,F401  (a whole plan and its recipes, pasted as text)
import core.calendar_actions  # noqa: E402,F401
import core.gap_actions  # noqa: E402,F401  (capability gaps, build plan step 9)
import core.operating_actions  # noqa: E402,F401  (the Operating Journal, DEC-0097)
import core.play_actions  # noqa: E402,F401  (recreation, DEC-0098)
import core.life_note_actions  # noqa: E402,F401  (promises, decisions, ideas, goals set aside, DEC-0054)
import core.classroom_actions  # noqa: E402,F401  (the Classroom's web screen)
import core.waypoint_actions  # noqa: E402,F401  (waypoints from the web's Maps and Navigation)
import core.trip_route  # noqa: E402,F401  (a trip's route and checkpoints, from Expeditions and by voice)
import core.plan_actions  # noqa: E402,F401  (a plan's page: keep a size, start a project, let a kept plan go)
import core.web_why  # noqa: E402,F401  (My Why: link, unlink and achieve goals)
import core.web_projects  # noqa: E402,F401  (Projects: a budget, and tasks added, reopened, deleted)
import core.web_textbooks  # noqa: E402,F401  (Classroom textbooks: a course from one, removing one)
import core.starter_actions  # noqa: E402,F401  (starter sets from Settings)
import core.subscriptions  # noqa: E402,F401  (the "still using it?" mark on a subscription, DEC-0054)
import core.web_proposals  # noqa: E402,F401  (mission ideas and field captures: accept or set aside, DEC-0125)
import core.asset_parts  # noqa: E402,F401  (the parts an asset uses, as stated links)
import core.web_comms  # noqa: E402,F401  (Communications: the message limit and breaks, DEC-0129)
import core.health_actions  # noqa: E402,F401  (Health: sleep, visits, medications, records, DEC-0129)
import core.id_wallet  # noqa: E402,F401  (the ID wallet: taking a card out; numbers never go through an action)
import core.theme_actions  # noqa: E402,F401  (the Theme Studio: save or delete a theme of your own, DEC-0136)
import core.web_directions  # noqa: E402,F401  (My Directions: set, change, pause, resume, let go, DEC-0141)
import core.answer_compare  # noqa: E402,F401  (how MIA answers: pick, set, forget, two ways on or off, DEC-0138)
import core.web_worlds  # noqa: E402,F401  (Living Worlds: worlds, campaigns, the character, quests, DEC-0134)
import core.web_trails  # noqa: E402,F401  (Trail Maps: taking one out, its PDF set aside for Undo)
import core.web_conversations  # noqa: E402,F401  (past conversations: deleting one, undoable)
import core.web_connections  # noqa: E402,F401  (connections: don't bring that up, allow again, DEC-0146)
import core.art_studio  # noqa: E402  (pictures MIA painted: deleting one, DEC-0140)
core.art_studio._register()
from core.offline_maps import _register as _register_map_areas  # noqa: E402  (vector map areas from the Maps page)

_register_map_areas()
import core.map_share_actions  # noqa: E402,F401  (places on TAK apps on this network, DEC-0099)  (your own calendar events)
import core.connectors  # noqa: E402,F401  (importing from other apps: files, rental calendar links)
import core.more_actions  # noqa: E402,F401  (Journal, Workshop, Expeditions, Music, Files)
import core.inbox_actions  # noqa: E402,F401  (the Inbox: file, dismiss, send a note)
import core.game_actions  # noqa: E402,F401  (the game layer: Reward Shop, DEC-0028)
import core.craft_actions  # noqa: E402,F401  (crafting recipes and builds, DEC-0030)
import core.goods_actions  # noqa: E402,F401  (homestead goods and market days, DEC-0036)
import core.flock_actions  # noqa: E402,F401  (chickens: eggs, feed, birds, DEC-0037)
import core.dungeon_actions  # noqa: E402,F401  (work as a dungeon: runs, loot, quests, DEC-0046)
import core.loop_actions  # noqa: E402,F401  (the loop: days, times, reminders, DEC-0047)
import core.failure_actions  # noqa: E402,F401  (the Fix-It Log, DEC-0049)
import core.freedom_actions  # noqa: E402,F401  (the freedom plan, DEC-0038)
import core.obligation_actions  # noqa: E402,F401  (tax and compliance deadlines, DEC-0040)
import core.business_actions  # noqa: E402,F401  (quotes, customers, orders, portfolio, DEC-0030)
import core.grow_actions  # noqa: E402,F401  (the grow lab, DEC-0030)
import core.security_actions  # noqa: E402,F401  (Security cameras, DEC-0033)
import core.insurance_actions  # noqa: E402,F401  (the insurance check-up, DEC-0034)
import core.training_actions  # noqa: E402,F401  (the live workout session, DEC-0055)
import core.cooking_actions  # noqa: E402,F401  (cook mode, DEC-0113)
import core.power_actions  # noqa: E402,F401  (Power's energy sources, DEC-0125)
import core.toolbox_actions  # noqa: E402,F401  (the Toolbox's alarms, DEC-0125)
import core.lab_reading_actions  # noqa: E402,F401  (the Lab's readings, DEC-0125)
import core.routine_actions  # noqa: E402,F401  (the Household's routines added and paused, DEC-0125)
import core.web_changes  # noqa: E402,F401  (undo.last: Recent Changes' Undo, as "undo that")
import core.web_notifications  # noqa: E402,F401  (Notifications: read all, dismiss)
import core.lab_actions  # noqa: E402,F401  (the development lab, DEC-0058)
import core.first_boot  # noqa: E402,F401  (meeting MIA, docs/GLASSES_FIRST_BOOT_PLAN.md)


# ------------------------------------------------------------------ the five steps


def _who(context) -> Optional[str]:
    """Whose proposals these are: the person this context acts for (person_settings.person_id)."""
    from core.person_settings import person_id

    return person_id(context)


class ActionCenter:
    """The proposals waiting for a yes (context.actions)."""

    def __init__(self) -> None:
        """Starts with no proposals; a lock keeps the phone server's threads from colliding."""
        self._proposals: dict[str, Proposal] = {}
        self._lock = threading.Lock()

    def _expire(self) -> None:
        """Marks proposals left undecided past KEEP_FOR (a day) expired, so an old card can't be approved later."""
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
        """A proposal by id, only for the person it belongs to (KeyError otherwise, never someone else's)."""
        with self._lock:
            self._expire()
            proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.profile_id != profile_id:
            raise KeyError(proposal_id)
        return proposal

    def pending(self, profile_id: Optional[str]) -> list[Proposal]:
        """This person's proposals still waiting for a decision."""
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
        before = _moment(context, proposal)
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
                change.by = "mia" if proposal.proposed_by == "mia" else "person"
                undo.add(change)
                proposal._change = change
            from core import corrections  # her changes watched; the person's edits checked against them

            try:
                if proposal.proposed_by == "mia":
                    corrections.mia_changed(context, proposal.kind, proposal.params)
                else:
                    corrections.person_changed(context, proposal.kind, proposal.params)
            except Exception:  # the record never breaks the change
                log.exception("Couldn't keep the correction record for %s.", proposal.kind)
            publish(context, "records.changed", action=f"action_{proposal.kind}")
            try:
                proposal.reward = reward_for(before, _moment(context, proposal), proposal.kind)
            except Exception:  # a celebration never breaks the change itself
                log.exception("Couldn't work out the reward for %s.", proposal.kind)
        proposal.decided_at = datetime.now().isoformat(timespec="seconds")
        if proposal.status == FAILED:
            _note(context, "action_failed", proposal)
        return proposal

    def reject(self, context, proposal_id: str) -> Proposal:
        """Declines a proposal still waiting (nothing runs); when MIA proposed it, the decline is noted for her
        actions.* loops.
        """
        proposal = self.get(proposal_id, _who(context))
        if proposal.status == PROPOSED:
            proposal.status = REJECTED
            proposal.decided_at = datetime.now().isoformat(timespec="seconds")
            if proposal.proposed_by == "mia":
                _note(context, "declined", proposal)
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


def _note(context, kind: str, proposal: Proposal) -> None:
    """Into the person's Fix-It Log (core/failure_log.py), for the actions.* loops: the action's kind only."""
    failures = getattr(context, "failures", None)
    if failures is None:
        return
    try:
        failures.record(kind, tool=proposal.kind, surface="actions")
    except Exception:  # the record never breaks the action
        log.exception("Couldn't note the %s action.", proposal.kind)


def _moment(context, proposal) -> dict:
    """The person's XP and credits, and the mission or objective the
    action is about: read just before and just after it runs."""
    out: dict = {}
    profiles = getattr(context, "profiles", None)
    try:
        person = (profiles.get_profile(proposal.profile_id) if proposal.profile_id else None) or profiles.get_active_profile()
    except Exception:
        person = None
    if person is not None:
        out["xp"], out["credits"] = int(person.total_xp or 0), int(person.total_credits or 0)
    missions = getattr(context, "missions", None)
    mission_id = str(proposal.params.get("mission_id") or "")
    mission = missions.get_mission(mission_id) if missions is not None and mission_id else None
    if mission is not None:
        out["mission"], out["status"] = mission.name, mission.status
        try:
            out["done"], out["total"] = missions.group_objective_progress(mission_id)
        except Exception:
            pass
        if proposal.kind == "objective.tick":
            try:
                index = int(proposal.params.get("index"))
                out["objective"] = mission.objectives[index].description
                out["objective_done"] = bool(missions.is_objective_complete(mission_id, index))
            except (TypeError, ValueError, IndexError, AttributeError):
                pass
    return out


def reward_for(before: dict, after: dict, kind: str) -> Optional[dict]:
    """Pure logic. What a change earned: XP and credits gained, a level
    reached, an objective or a mission finished. None when it earned
    nothing worth celebrating (a +1 that didn't finish anything)."""
    from core.leveling import compute_level_progress

    xp = max(0, after.get("xp", 0) - before.get("xp", 0))
    credits = max(0, after.get("credits", 0) - before.get("credits", 0))
    objective_done = kind == "objective.tick" and after.get("objective_done") and not before.get("objective_done")
    mission_done = after.get("status") == "completed" and before.get("status") != "completed"
    if not (xp or credits or objective_done or mission_done):
        return None
    level_before = compute_level_progress(before.get("xp", 0))[0]
    level, into, needed = compute_level_progress(after.get("xp", 0))
    headline = ("Mission Complete" if mission_done else "Objective Complete" if objective_done else "XP Earned")
    name = after.get("mission") if mission_done else after.get("objective") or after.get("mission") or ""
    return {
        "headline": headline, "name": name, "mission": after.get("mission", ""),
        "xp": xp, "credits": credits, "level": level, "level_up": level > level_before,
        "level_percent": round(100 * into / needed) if needed else 100,
        "done": after.get("done"), "total": after.get("total"),
        # Every objective finished, the mission waiting to be claimed.
        "ready": bool(objective_done and after.get("total") and after.get("done") == after.get("total") and not mission_done),
        "say": voice_line(headline, level if level > level_before else None, name),
    }


# MIA's lines for a win (web/sound.js speaks one when the person turned
# voice lines on). Warm and short, never guilt (docs/design/MIA_VOICE.md).
VOICE_LINES = {
    "Level": ("Level {level}! Look at you.", "Level {level}. You earned that one.", "Level {level}! Onward."),
    "Mission Complete": ("{name}: done. Nicely handled.", "That's {name} finished. Good work.", "{name}, complete. On to the next."),
    "Objective Complete": ("One down.", "Nice. That's one more.", "Checked off."),
    "XP Earned": ("Good stuff.", "That counts.", "Nice one."),
}


def voice_line(headline: str, level: Optional[int] = None, name: str = "") -> str:
    """Pure logic. One of MIA's lines, picked steadily from the name (so
    the same win says the same thing)."""
    key = "Level" if level else headline
    lines = VOICE_LINES.get(key, VOICE_LINES["XP Earned"])
    if "{name}" in lines[0] and not name:
        lines = VOICE_LINES["XP Earned"]
    pick = lines[sum(map(ord, name or key)) % len(lines)]
    return pick.format(level=level, name=name)


def suggested(kind: str, **params) -> dict:
    """The `action` a Life State item carries, for a surface to propose."""
    return {"kind": kind, "label": ACTION_TYPES[kind].label, "params": params}
