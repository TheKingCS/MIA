"""
core.lab_actions
==================

The development lab's changes as action kinds (DEC-0058, core/dev_lab.py):
start a proposal (lab, write, check), approve one into the running MIA,
reject one. Grown-ups only, never from the glasses; the long steps (the
coder, the test suite) run in the background and say when they're done.
"Approve" is the production boundary: only the owner's approval merges.
"""

from __future__ import annotations

import threading

from core.actions import ACTION_TYPES, ActionError, ActionType


def _grown_up(context) -> None:
    from core.child_accounts import is_child

    if is_child(context):
        raise ActionError("That's for a grown-up.")


def _tell(context, title: str, message: str) -> None:
    notifications = getattr(context, "notifications", None)
    if notifications is not None:
        try:
            notifications.notify(title, message, source="lab")
        except Exception:
            pass


def _background(context, title: str, work) -> None:
    def run():
        from core import dev_lab

        try:
            p = work()
            _tell(context, f"🧪 {title}", dev_lab.describe(p))
        except Exception as exc:
            _tell(context, f"🧪 {title}", f"It didn't finish: {exc}")
    threading.Thread(target=run, name="mia-lab", daemon=True).start()


def _proposal(params):
    from core import dev_lab

    try:
        return dev_lab.get(str(params.get("proposal_id") or ""))
    except ValueError as exc:
        raise ActionError(str(exc)) from None


def _describe_propose(context, params) -> str:
    _grown_up(context)
    title = str(params.get("title") or "").strip()
    if not title or not str(params.get("problem") or "").strip():
        raise ActionError("A proposal needs a title and the problem it solves.")
    return f"Start a lab proposal: {title} (written by Claude Code in the lab, then tested; nothing changes in MIA yet)"


def _propose(context, params) -> str:
    from core import dev_lab

    _grown_up(context)
    p = dev_lab.create(str(params.get("title")), str(params.get("problem")), str(params.get("evidence") or ""),
                       str(params.get("plan") or ""))

    def work():
        q = dev_lab.write(p.proposal_id)
        return dev_lab.check(p.proposal_id) if q.status == dev_lab.WRITTEN else q
    _background(context, "Lab proposal", work)
    return f"Started in the lab ({p.proposal_id}). I'll tell you when it's written and tested."


def _describe_approve(context, params) -> str:
    _grown_up(context)
    p = _proposal(params)
    if p.status != "ready":
        raise ActionError(f"Only a ready proposal can go in; this one is {p.status}.")
    return f"Put “{p.title}” into MIA (merge, run the tests, undo itself if anything new breaks)"


def _approve(context, params) -> str:
    from core import dev_lab

    _grown_up(context)
    p = _proposal(params)
    _background(context, "Lab merge", lambda: dev_lab.approve(p.proposal_id))
    return "Merging and testing. I'll tell you when it's in."


def _reject(context, params) -> str:
    from core import dev_lab

    _grown_up(context)
    p = _proposal(params)
    try:
        dev_lab.reject(p.proposal_id, str(params.get("why") or ""))
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    return f"Rejected: {p.title}. The lab copy is gone."


_KINDS = [
    ActionType("lab.propose", "Start in the lab", {"title": "", "problem": "", "evidence": "", "plan": ""},
               _describe_propose, _propose),
    ActionType("lab.approve", "Put it in", {"proposal_id": "the proposal"}, _describe_approve, _approve),
    ActionType("lab.reject", "Reject", {"proposal_id": "the proposal", "why": ""},
               lambda c, p: f"Reject the lab proposal “{_proposal(p).title}”", _reject),
]
LAB_ACTIONS = {k.kind: k for k in _KINDS}
ACTION_TYPES.update(LAB_ACTIONS)
