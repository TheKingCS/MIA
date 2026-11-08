"""
core.disagreements
====================

Agents may disagree, and a disagreement is resolved, never dropped
(DEC-0071 point 3; T-0022). A review's objection to a *change* was built
first (core/work_review.py: answered with `resolve` before approve). This
adds objections to a **decision** (`DEC-0071`) or a **design** (a doc in
`docs/`, like a proposal), and one list of every disagreement still open.

- `object_to(subject, who, why)`: an objection, kept in the activity log
  (work/activity.jsonl, action `object`, the subject in its task field),
  so it's in the shared history like everything else.
- `answer(subject, who, how)`: what changed, or why the objection doesn't
  hold; it answers every objection raised before it.
- An objection raised again after an answer means they still disagree:
  then it's Zac's to decide, and only `settle()` (Zac, at the keyboard,
  typing the subject back, as approving a task is) closes it.
- `open_disagreements()`: every one still open, for the development
  dashboard (core/work_dashboard.py): decisions and designs from here,
  and tasks whose review asked for changes nobody has answered or whose
  reviewer still says no after an answer. Each says whose move it is.

Nothing here changes a decision or a doc: it records the argument and its
outcome; the change, if any, is made the usual way.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from core import work_activity as activity

ROOT = Path(__file__).resolve().parent.parent
_DECISION = re.compile(r"^DEC-\d{4}$")
OPEN, ANSWERED, ZACS = "open", "answered", "zac"  # whose move: the author's, the objector's, Zac's


class DisagreementError(ValueError):
    """An objection, answer or settling that can't happen as asked."""


def subject_of(text: str, root: Path = ROOT) -> str:
    """The subject an objection is about, checked against the repository: a decision on record ("DEC-0071") or a
    design doc that exists ("docs/X_PROPOSAL.md"). Raises DisagreementError otherwise."""
    text = (text or "").strip()
    if _DECISION.match(text.upper()):
        ref = text.upper()
        try:
            decisions = (root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
        except OSError:
            decisions = ""
        if not re.search(rf"^### {ref}\b", decisions, re.M):
            raise DisagreementError(f"{ref} isn't in docs/DECISIONS.md.")
        return ref
    rel = text.replace("\\", "/")
    if rel.startswith("docs/") and rel.endswith(".md") and ".." not in rel and (root / rel).is_file():
        return rel
    raise DisagreementError("Object to a decision (DEC-0071) or a design doc in docs/ (docs/X_PROPOSAL.md).")


def state(subject: str, log=activity.ACTIVITY) -> dict:
    """Pure logic over the log. Where one subject's disagreement stands: {subject, status (open, answered, zac or
    settled; "" when there was never one), objections still standing, the last answer, the settling}."""
    standing: list[dict] = []
    answered_once, last_answer, settled = False, None, None
    status = ""
    for e in activity.events(log):  # not search(): it upper-cases the id, and a doc's path keeps its case
        if e.get("task") != subject:
            continue
        action = e.get("action")
        if action == "object":
            standing.append(e)
            settled = None
            status = ZACS if answered_once else OPEN
        elif action == "answer" and standing:
            last_answer, answered_once, status = e, True, ANSWERED
            standing = []
        elif action == "settle":
            settled, standing, answered_once, status = e, [], False, "settled"
    return {"subject": subject, "status": status, "objections": standing, "answer": last_answer, "settled": settled}


def object_to(subject: str, who: str, why: str, log=activity.ACTIVITY, root: Path = ROOT) -> dict:
    """Record an objection to a decision or a design: who, and why. Returns where it now stands."""
    ref = subject_of(subject, root)
    if not why.strip():
        raise DisagreementError("Say what's wrong with it.")
    if not who.strip():
        raise DisagreementError("Say who objects.")
    activity.record(who.strip(), "object", ref, why.strip(), log)
    return state(ref, log)


def answer(subject: str, who: str, how: str, log=activity.ACTIVITY, root: Path = ROOT) -> dict:
    """Answer the standing objections: what changed, or why they don't hold. Returns where it now stands."""
    ref = subject_of(subject, root)
    now = state(ref, log)
    if not now["objections"]:
        raise DisagreementError(f"{ref} has no standing objection to answer.")
    if not how.strip():
        raise DisagreementError("Say how: what changed, or why the objection doesn't hold.")
    raised = ", ".join(sorted({e.get("who", "") for e in now["objections"]}))
    activity.record(who.strip(), "answer", ref, f"{len(now['objections'])} from {raised}: {how.strip()}", log)
    return state(ref, log)


def settle(subject: str, how: str, confirm: Optional[Callable[[str], str]], log=activity.ACTIVITY,
           root: Path = ROOT) -> dict:
    """Zac decides a disagreement: only with him at the keyboard, typing the subject back (`confirm` asks). Returns
    where it now stands."""
    ref = subject_of(subject, root)
    if state(ref, log)["status"] not in (OPEN, ANSWERED, ZACS):
        raise DisagreementError(f"{ref} has no disagreement to settle.")
    if not how.strip():
        raise DisagreementError("Say what you decided.")
    try:
        typed = confirm(f"Settle the disagreement over {ref} as Zac? Type {ref}: ") if confirm else ""
    except (EOFError, OSError):
        typed = ""
    if (typed or "").strip().upper() != ref.upper():
        raise DisagreementError("Not settled: only Zac, at the keyboard, decides in his name.")
    activity.record("zac", "settle", ref, how.strip(), log)
    return state(ref, log)


def _row(s: dict) -> dict:
    """Pure logic. A subject's state as a dashboard row: who raised it, what they said, whose move it is."""
    last = s["objections"][-1] if s["objections"] else None
    next_move = {OPEN: "The author answers: what changed, or why it doesn't hold.",
                 ANSWERED: "Answered. The objector agrees, or objects again.",
                 ZACS: "They still disagree after an answer. Read both and decide."}[s["status"]]
    command = f'python -m tools.work settle {s["subject"]} --how "..."' if s["status"] == ZACS else ""
    return {"subject": s["subject"], "kind": "decision" if s["subject"].startswith("DEC-") else "design",
            "status": s["status"], "raised_by": sorted({e.get("who", "") for e in s["objections"]}),
            "why": [str(e.get("detail", ""))[:400] for e in s["objections"]][-3:],
            "answer": str((s["answer"] or {}).get("detail", ""))[:400], "at": (last or s["answer"] or {}).get("at", ""),
            "next": next_move, "command": command}


def open_disagreements(log=activity.ACTIVITY, tasks_dir=None) -> list[dict]:
    """Every disagreement still open, Zac's first: objections to decisions and designs, and tasks in review whose
    objection nobody has answered or whose reviewer still says no after an answer."""
    from core import work_review as rv
    from core import work_tasks as tasks_mod

    subjects = []
    for e in activity.events(log):
        if e.get("action") == "object" and e.get("task") not in subjects:
            subjects.append(e["task"])
    rows = [_row(s) for s in (state(ref, log) for ref in subjects) if s["status"] in (OPEN, ANSWERED, ZACS)]
    try:
        tasks = tasks_mod.load(tasks_dir) if tasks_dir else tasks_mod.load()
    except OSError:
        tasks = {}
    for t in tasks.values():
        if t.status != "review":
            continue
        objections = rv.open_objections(t.id, log)
        standing = not objections and rv.latest_verdict(t.id, log) == "changes" and not rv.settled_by_zac(t.id, log)
        if not objections and not standing:
            continue
        rows.append({"subject": t.id, "kind": "task", "status": OPEN if objections else ZACS,
                     "raised_by": sorted({e.get("who", "") for e in objections}),
                     "why": [str(e.get("detail", ""))[:400] for e in objections][-3:], "answer": "",
                     "at": objections[-1].get("at", "") if objections else t.updated,
                     "next": "The builder fixes it or answers why not (resolve)." if objections else
                     "The builder answered but the reviewer still says no. Read both and decide.",
                     "command": "" if objections else f'python -m tools.work resolve {t.id} --by zac --how "..."'})
    order = {ZACS: 0, OPEN: 1, ANSWERED: 2}
    return sorted(rows, key=lambda r: (order[r["status"]], str(r["at"])))
