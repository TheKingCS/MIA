"""
core.capability_gaps
======================

Self-enablement (build plan step 9, DEC-0094): "I can't do that" stops being
a dead end. Every request no tool matched is already in the person's Fix-It
Log (`no_tool`, core/failure_log.py). Here they become **capability gaps**:

- **Grouped** (`refresh()`): requests alike in their words are one gap,
  with how often it was asked and when.
- **What it would take** (`need_of()`, in code, never a guess by a model):
  - `app`: an app that does it is tucked away: show it again (the
    `app.visibility` action);
  - `screen` / `workflow`: something to keep track of, or to happen on a
    schedule, which MIA can make herself (ACAF, Make Something);
  - `device`: a sense or device she doesn't have (sight, calls, a sensor);
  - `code`: a new ability, which only the development platform can add.
- **A proposal** once a gap is asked `REPEATED` times (`offers()`), through
  the communication gate, at most once a fortnight a gap. A `code` gap the
  person says yes to (`gap.build`) becomes a task in `work/tasks/` that
  names the gap by its id and its kind only: **the person's words stay in
  their own folder** (`capability_gaps.json`), where Claude reads them on
  this PC (`python -m tools.gaps show <id>`), as with the Fix-It Log.

Nothing here changes anything by itself: an app is shown, a screen made or a
task opened only when the person approves it.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "capability_gaps.json"
ALIKE = 0.5  # shared-word similarity for two requests to be one gap
REPEATED = 2  # asked this often: offered as a proposal
OFFER_AGAIN = timedelta(days=14)
KEEP_EXAMPLES = 3
NEEDS = ("app", "screen", "workflow", "device", "code")

_DEVICE = re.compile(r"\b(look at|see (this|that|what)|what am i (looking|holding)|camera|take a (photo|picture)|"
                     r"read (this|that) (label|sign)|call (my|him|her|them|\w+)|phone (him|her|them)|text (him|her|them)|"
                     r"thermostat|lights?\b|turn (on|off) the|sensor|temperature in)", re.IGNORECASE)
_WORKFLOW = re.compile(r"\b(every (day|morning|night|week|month|monday|tuesday|wednesday|thursday|friday|saturday|"
                       r"sunday)|each (day|week|month)|whenever|remind me (to|when|every)|notify me|let me know when|"
                       r"tell me when|automatically)\b", re.IGNORECASE)
_SCREEN = re.compile(r"\b(track|keep track|log (my|the|each)|keep a (list|log|record)|record (my|each)|"
                     r"a (list|log|tracker|chart) (of|for)|how many .* (have i|did i))\b", re.IGNORECASE)


def _now() -> datetime:
    """The current time, in UTC."""
    return datetime.now(timezone.utc)


def _folder(context) -> Optional[Path]:
    """The person's folder the gaps live in (the failure log's, else the traces'), or None."""
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def load(context) -> list[dict]:
    """Every capability gap (capability_gaps.json); none when it's missing or unreadable."""
    folder = _folder(context)
    if folder is None:
        return []
    try:
        return json.loads((folder / FILE_NAME).read_text(encoding="utf-8")).get("gaps", [])
    except (OSError, ValueError):
        return []


def _save(context, gaps: list[dict]) -> None:
    """Writes the gaps atomically (nothing when there's no folder)."""
    folder = _folder(context)
    if folder is None:
        return
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / FILE_NAME, json.dumps({"gaps": gaps}, indent=1, ensure_ascii=False))


# ------------------------------------------------------------------ what it would take (pure)

def _hidden_app(context, request: str) -> Optional[dict]:
    """An app that's tucked away whose own words match the request."""
    try:
        from core.focus_presets import current
        from core.failure_log import similar
        from core.web_surfaces import APPS_BY_ID

        hidden = current(context)[2]
    except Exception:
        return None
    best, score = None, 0.0
    for module_id in hidden:
        app = APPS_BY_ID.get(module_id)
        if app is None:
            continue
        words = " ".join((app.name, app.tagline, app.description, app.ask))
        found = similar(request, words) + (0.5 if app.name.lower() in request.lower() else 0.0)
        if found > score:
            best, score = app, found
    if best is None or score < 0.12:
        return None
    return {"module_id": best.module_id, "name": best.name}


def need_of(context, request: str) -> dict:
    """What a request would take: {need, what} (and the app, for `app`). In code, from the words."""
    app = _hidden_app(context, request)
    if app is not None:
        return {"need": "app", "what": f"the {app['name']} app does this, and it's tucked away", "app": app["module_id"]}
    if _DEVICE.search(request):
        return {"need": "device", "what": "a sense or device she doesn't have yet (sight, calls, a home sensor)"}
    if _WORKFLOW.search(request):
        return {"need": "workflow", "what": "a workflow she can make: something that happens on a schedule or a trigger"}
    if _SCREEN.search(request):
        return {"need": "screen", "what": "a screen she can make to keep track of it"}
    return {"need": "code", "what": "a new ability: only her development can add it"}


# ------------------------------------------------------------------ grouping

def refresh(context, days: int = 60, now: Optional[datetime] = None) -> list[dict]:
    """Fold the Fix-It Log's unmatched requests into gaps (each event once). Returns the gaps."""
    from core.failure_log import similar

    book = getattr(context, "failures", None)
    if book is None:
        return []
    gaps = load(context)
    seen = {e for g in gaps for e in g.get("events", [])}
    changed = False
    for event in book.events(days=days):
        if event.get("kind") != "no_tool" or event.get("event_id") in seen or not event.get("prompt"):
            continue
        asked = str(event["prompt"])
        home = None
        for g in gaps:
            if g.get("status") != "done" and max((similar(asked, x) for x in g["examples"]), default=0.0) >= ALIKE:
                home = g
                break
        if home is None:
            taken = {g["id"] for g in gaps}
            home = {"id": next(f"G-{n:04d}" for n in range(1, 100_000) if f"G-{n:04d}" not in taken),
                    "examples": [], "events": [], "count": 0, "first": event.get("at", ""), "status": "open",
                    **need_of(context, asked)}
            gaps.append(home)
        home["count"] += 1
        home["last"] = event.get("at", "")
        home["events"] = (home["events"] + [event.get("event_id")])[-50:]
        if asked not in home["examples"]:
            home["examples"] = (home["examples"] + [asked])[-KEEP_EXAMPLES:]
        changed = True
    if changed:
        _save(context, gaps)
    return gaps


def _short(text: str, n: int = 70) -> str:
    """Text on one line, cut to n characters with an ellipsis."""
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def offers(context, now: Optional[datetime] = None) -> list:
    """Gaps asked often enough, offered through the gate (at most once a fortnight each)."""
    from core.communication_gate import Candidate

    now = now or _now()
    gaps = refresh(context, now=now)
    out, changed = [], False
    for g in gaps:
        if g.get("status") not in ("open", "offered") or g["count"] < REPEATED:
            continue
        last = g.get("offered_at", "")
        if last and now - datetime.fromisoformat(last) < OFFER_AGAIN:
            continue
        asked = _short(g["examples"][-1])
        times = f"{g['count']} times"
        message = {
            "app": f"You've asked \"{asked}\" {times}. {g['what'].capitalize()}: want it back in your apps?",
            "screen": f"You've asked \"{asked}\" {times}, and I can't yet. I could make a screen to keep track of it: "
                      "say \"make something\" and tell me what to keep.",
            "workflow": f"You've asked \"{asked}\" {times}, and I can't yet. I could make a workflow for it: say "
                        "\"make something\" and tell me when it should happen.",
            "device": f"You've asked \"{asked}\" {times}. That needs a sense or a device I don't have yet, so it's on "
                      "my list of things to grow into.",
            "code": f"You've asked \"{asked}\" {times}, and I can't do that yet. Want me to ask for it to be built?",
        }[g["need"]]
        out.append(Candidate(topic="capability_gap", title="Something I can't do yet", message=message, source="gaps",
                             fingerprint=f"gap:{g['id']}:{now.date().isoformat()}"))
        g["status"], g["offered_at"] = "offered", now.isoformat(timespec="seconds")
        changed = True
    if changed:
        _save(context, gaps)
    return out


_BUILD_IT = re.compile(r"^(yes|yeah|yep|sure|please)?[,.! ]*(build it|ask for it( to be built)?|get it built|"
                       r"put it on the list|bring it back|show it( again)?)[.! ]*(please)?[.!]*$", re.IGNORECASE)


def reply(context, text: str) -> Optional[str]:
    """The person's answer to her latest offer ("build it", "bring it back"), within 3 days of it: the action,
    proposed and approved by their own words. None when it isn't that."""
    said = " ".join(str(text or "").split())
    if not _BUILD_IT.match(said):
        return None
    now = _now()
    offered = [g for g in load(context) if g.get("status") == "offered" and g.get("offered_at")
               and now - datetime.fromisoformat(g["offered_at"]) <= timedelta(days=3)]
    if not offered:
        return None
    gap = max(offered, key=lambda g: g["offered_at"])
    actions = getattr(context, "actions", None)
    if actions is None:
        return None
    from core.actions import ActionError

    if gap["need"] == "app":
        kind, params = "app.visibility", {"module_id": gap.get("app", ""), "visible": True}
    elif gap["need"] == "code":
        kind, params = "gap.build", {"gap_id": gap["id"]}
    else:
        return None
    try:
        done = actions.approve(context, actions.propose(context, kind, params, proposed_by="mia").proposal_id)
    except ActionError as problem:
        return str(problem)
    if done.status == "executed" and gap["need"] == "app":
        mark(context, gap["id"], "done")
    return done.result if done.status == "executed" else (done.result or "That didn't work; nothing was changed.")


def get(context, gap_id: str) -> Optional[dict]:
    """The gap with this id, or None."""
    return next((g for g in load(context) if g["id"] == gap_id), None)


def mark(context, gap_id: str, status: str, **fields) -> Optional[dict]:
    """Sets a gap's status (and any other fields), saves, and returns it; None when it's gone."""
    gaps = load(context)
    found = next((g for g in gaps if g["id"] == gap_id), None)
    if found is None:
        return None
    found.update(status=status, **fields)
    _save(context, gaps)
    return found


def open_task(context, gap_id: str, tasks_dir=None, log_path=None) -> str:
    """The person said yes to a `code` gap: a development task naming the gap by id and kind, never their words."""
    from core import work_activity, work_tasks

    gap = get(context, gap_id)
    if gap is None:
        raise ValueError(f"No gap {gap_id}.")
    tasks_dir = tasks_dir or work_tasks.TASKS_DIR  # looked up now, not when work_tasks was defined
    log_path = log_path or work_activity.ACTIVITY
    tasks = work_tasks.load(tasks_dir)
    body = (f"A capability gap (core/capability_gaps.py, build plan step 9): asked {gap['count']} times since "
            f"{gap.get('first', '')[:10]}, and the person said yes to having it built. What it needs: {gap['what']}.\n\n"
            f"The request itself stays in the person's own folder: on this PC, `python -m tools.gaps show {gap_id}`. "
            "Build the ability through the lab; when it's in, mark the gap done.")
    task = work_tasks.new(tasks, f"Capability gap {gap_id}: {gap['need']}", role="Software Engineer",
                          source=f"gap:{gap_id}", body=body)
    work_tasks.save(task, tasks_dir)
    work_activity.record("MIA (gaps)", "new", task.id, f"{gap_id}: asked {gap['count']} times", log_path)
    mark(context, gap_id, "accepted", task=task.id)
    return task.id


def summary(context) -> dict:
    """How many gaps there are, how many were asked repeatedly and aren't done, and the open ones counted by what they
    need.
    """
    gaps = load(context)
    by: dict[str, int] = {}
    for g in gaps:
        if g.get("status") in ("open", "offered", "accepted"):
            by[g["need"]] = by.get(g["need"], 0) + 1
    return {"gaps": len(gaps), "repeated": sum(1 for g in gaps if g["count"] >= REPEATED and g.get("status") != "done"),
            "by_need": by}
