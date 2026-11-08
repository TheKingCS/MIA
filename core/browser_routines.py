"""
core.browser_routines
=======================

Browser tasks MIA has been taught (DEC-0117, Zac 2026-11-07: "show her, then
she practises"). The person does a task once in her browser while she
records it; she saves it as a routine and replays it later, the same steps
in the same order, checking the page as she goes.

**Recording** (`start_teaching` / `finish_teaching`): her browser reports
each thing the person does: a click (by the control's role and name, never
by screen position, so a moved button is still found), text typed, a
choice made, Enter pressed. A password field is never recorded: the step
becomes "sign in yourself", and on replay she waits for the person to do
it. After each step she notes what the page showed (its title), and that
becomes the step's check.

**Replaying** (`run`): each step is found on the page by its role and name,
sorted by core/browser_safety.py like anything she does, and done:
ordinary steps by herself, a step that commits only once the person
approves it (the run waits there and carries on after, `carry_on`). After a
step she checks the page shows what it showed when she was taught; when it
doesn't, she stops and says where.

**Practice**: every run is kept (clean, or where it stopped). A routine
taught but not yet run clean twice is "practising"; after two clean runs in
a row it's "learned", the same mark the learning paths use (DEC-0112).
Runs that stop are counted by the browser.routines loop.

The store (`BrowserRoutines`, `browser_routines.json`) is each person's own.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import life_events
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.browser_safety import COMMIT, NEVER, classify
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "browser_routines.json"
LEARNED_AFTER = 2  # clean runs in a row
MAX_STEPS = 60


class BrowserRoutines:
    """A person's taught browser tasks: each one's name, where it starts, its steps, when it was taught, and its
    runs."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads them from the person's folder (or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self.routines: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Reads them; a missing or unreadable file is none. Sealed on disk (DEC-0126): open_text reads it sealed or plain, and one that won't open is copied aside and counts as damaged."""
        try:
            self.routines = json.loads(open_text(self._file)).get("routines", {})
        except (OSError, ValueError):
            self.routines = {}

    def _save(self) -> None:
        """Writes them atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"routines": self.routines}, indent=1, ensure_ascii=False))

    def add(self, name: str, start: str, steps: list[dict]) -> dict:
        """Keeps a newly taught routine (one with the same name is replaced); a life event."""
        name = " ".join((name or "").split())[:80] or "A browser task"
        for key in [k for k, r in self.routines.items() if r["name"].lower() == name.lower()]:
            self.routines.pop(key)
        routine = {"id": uuid.uuid4().hex[:10], "name": name, "start": start, "steps": steps[:MAX_STEPS],
                   "taught": datetime.now().isoformat(timespec="seconds"), "runs": []}
        self.routines[routine["id"]] = routine
        self._save()
        life_events.record(self, "browser_task_taught", f"Taught MIA a browser task: {name}",
                           [f"browser_routine:{routine['id']}"], {"steps": len(routine["steps"])})
        return routine

    def find(self, name: str) -> Optional[dict]:
        """A routine by name: an exact match first, then one whose name holds every word asked for."""
        want = " ".join((name or "").lower().split())
        if not want:
            return None
        exact = [r for r in self.routines.values() if r["name"].lower() == want]
        if exact:
            return exact[0]
        words = set(re.findall(r"[a-z0-9]+", want))
        return next((r for r in self.routines.values() if words <= set(re.findall(r"[a-z0-9]+", r["name"].lower()))),
                    None)

    def all(self) -> list[dict]:
        """Every routine, the newest taught first."""
        return sorted(self.routines.values(), key=lambda r: r["taught"], reverse=True)

    def delete(self, routine_id: str) -> None:
        """Forgets a routine."""
        if self.routines.pop(routine_id, None) is not None:
            self._save()

    def record_run(self, routine_id: str, clean: bool, stopped_at: Optional[int] = None, note: str = "") -> None:
        """Keeps one run: clean, or the step it stopped at and why; learning it is a life event."""
        routine = self.routines.get(routine_id)
        if routine is None:
            return
        was = state_of(routine)
        routine["runs"] = (routine["runs"] + [{"at": datetime.now().isoformat(timespec="seconds"), "clean": clean,
                                               "stopped_at": stopped_at, "note": note[:200]}])[-50:]
        self._save()
        if was != "learned" and state_of(routine) == "learned":
            life_events.record(self, "browser_task_learned", f"MIA learned the browser task {routine['name']}",
                               [f"browser_routine:{routine_id}"], {})


def state_of(routine: dict) -> str:
    """Pure logic. Practising until the last LEARNED_AFTER runs were clean, then learned."""
    runs = routine.get("runs", [])
    recent = runs[-LEARNED_AFTER:]
    return "learned" if len(recent) == LEARNED_AFTER and all(r["clean"] for r in recent) else "practising"


def describe(routine: dict) -> str:
    """Pure logic. A routine in a line: its name, steps, state, and how its last run went."""
    runs = routine.get("runs", [])
    last = runs[-1] if runs else None
    how = ("never run yet" if last is None else "last run clean" if last["clean"]
           else f"last run stopped at step {last['stopped_at']}")
    return f"{routine['name']}: {len(routine['steps'])} steps, {state_of(routine)}, {how}"


def step_words(step: dict) -> str:
    """Pure logic. A step said in words."""
    name = step.get("name") or step.get("role") or "it"
    return {"open": f"open {step.get('url', '')}", "click": f"press \"{name}\"", "type": f"type into \"{name}\"",
            "select": f"choose \"{step.get('text', '')}\" in \"{name}\"", "press": f"press Enter in \"{name}\"",
            "signin": "sign in (you do it)"}.get(step.get("kind"), step.get("kind", "?"))


# ------------------------------------------------------------------ teaching

def start_teaching(browser, name: str) -> str:
    """Starts recording what the person does in her browser, under a name, from the page it's on (one must be
    open). Returns what to tell them."""
    if browser.teaching is not None:
        return f"I'm already learning \"{browser.teaching['name']}\". Say when you're done."
    if browser.driver is None or not browser.page.url or browser.page.url == "about:blank":
        return ("Open the page the task starts on first (\"open the county tax site\"), then ask me to learn it, "
                "and do the task from there.")
    browser.teaching = {"name": name, "start": browser.page.url, "steps": []}

    def heard(event: dict) -> None:
        """One thing the person did: kept as a step, the step before it given what the page showed then (its title,
        sent with the event: this runs on the browser's own thread, so it never asks the browser anything)."""
        teaching = browser.teaching
        if teaching is None or len(teaching["steps"]) >= MAX_STEPS:
            return
        if teaching["steps"] and event.get("title") and "expect" not in teaching["steps"][-1]:
            teaching["steps"][-1]["expect"] = event["title"]
        step = {k: event.get(k, "") for k in ("kind", "role", "name", "text", "input_type", "href")}
        if step["kind"] == "signin":
            step = {"kind": "signin"}
        elif step["kind"] == "type" and classify("type", _control_from(step)).level == NEVER:
            step = {"kind": "signin"}  # a secret field: never kept, she waits for them on replay
        steps = teaching["steps"]
        if steps and steps[-1]["kind"] == step["kind"] == "type" and steps[-1].get("name") == step.get("name"):
            steps[-1] = step  # the same field typed again: keep the final text
            return
        if steps and steps[-1]["kind"] == step["kind"] == "signin":
            return
        steps.append(step)

    driver = browser._driver()
    driver.on_record(heard)
    where = browser.page.title or "the page in my window"
    return (f"I'm watching. Do \"{name}\" in my browser, starting from {where}; I'll note every step (never "
            f"your passwords). Say \"done\" when you've finished.")


def _control_from(step: dict):
    """A recorded step's control, as the safety rules read one."""
    from core.browser_safety import Control

    return Control(0, step.get("role", ""), step.get("name", ""), input_type=step.get("input_type", ""),
                   href=step.get("href", ""))


def _note_expect(browser, steps: list[dict]) -> None:
    """Gives the last step its check: the title the page shows now."""
    if not steps:
        return
    try:
        title = browser.refresh().title
    except Exception:
        return
    if title and "expect" not in steps[-1]:
        steps[-1]["expect"] = title


def finish_teaching(browser, store: BrowserRoutines) -> str:
    """Stops recording and keeps the routine (nothing kept when no steps were done)."""
    teaching = browser.teaching
    if teaching is None:
        return "I wasn't learning anything just now."
    try:
        browser._driver().on_record(None)
    except Exception:
        pass
    _note_expect(browser, teaching["steps"])
    browser.teaching = None
    if not teaching["steps"]:
        return "You didn't do any steps, so there's nothing to keep."
    start = teaching["start"] or browser.page.url
    routine = store.add(teaching["name"], start, [{"kind": "open", "url": start}] + teaching["steps"])
    commits = sum(1 for s in routine["steps"] if s["kind"] in ("signin",) or
                  (s["kind"] != "open" and classify(s["kind"], _control_from(s)).level == COMMIT))
    return (f"Learned \"{routine['name']}\": {len(routine['steps'])} steps"
            + (f", {commits} of them waiting for your OK each time" if commits else "")
            + ". Ask me to do it and I'll practise it with you watching.")


# ------------------------------------------------------------------ replaying

def run(context, browser, store: BrowserRoutines, routine: dict, start: int = 0) -> str:
    """Runs a routine from a step: ordinary steps done, a commit or a sign-in waits for the person (the run carries
    on after they approve), a step not found or a page that doesn't match stops it. Returns what happened."""
    lines = []
    steps = routine["steps"]
    for index in range(start, len(steps)):
        step = steps[index]
        where = {"id": routine["id"], "next": index + 1}
        try:
            if step["kind"] == "open":
                browser.open(step["url"])
                lines.append(f"Opened {browser.page.title or step['url']}.")
            elif step["kind"] == "signin":
                pending = browser.ask_signin(routine=where)
                lines.append(f"Step {index + 1}: {pending.summary()}.")
                return "\n".join(lines)
            else:
                page = browser.refresh()
                control = page.find(step.get("name", ""), step.get("role", ""))
                if control is None:
                    return _stopped(store, routine, index, lines, f"I couldn't find \"{step.get('name')}\" on "
                                                                 f"{page.title or 'the page'}")
                result = browser.do(step["kind"], control.ref, step.get("text", ""), routine=where)
                if result["pending"] is not None:
                    lines.append(f"Step {index + 1}: {result['said']}")
                    return "\n".join(lines)
                if not result["done"]:
                    return _stopped(store, routine, index, lines, result["said"])
                lines.append(f"Step {index + 1}: {step_words(step)}.")
            expect = step.get("expect")
            if expect and expect.lower() not in (browser.page.title or "").lower():
                return _stopped(store, routine, index, lines, f"the page should say \"{expect}\" but says "
                                                             f"\"{browser.page.title}\"")
        except Exception as problem:
            return _stopped(store, routine, index, lines, str(problem))
    store.record_run(routine["id"], clean=True)
    lines.append(f"Finished \"{routine['name']}\" ({describe(store.routines[routine['id']])}).")
    return "\n".join(lines)


def _stopped(store: BrowserRoutines, routine: dict, index: int, lines: list, why: str) -> str:
    """Stops a run at a step, keeps it as a run that stopped, and says where and why."""
    store.record_run(routine["id"], clean=False, stopped_at=index + 1, note=why)
    lines.append(f"Stopped at step {index + 1} ({step_words(routine['steps'][index])}): {why}. "
                 "Show me again if the site has changed.")
    return "\n".join(lines)


def carry_on(context, browser, where: dict) -> str:
    """After the person approves a routine's waiting step: the run carries on from the next step."""
    store = getattr(context, "browser_routines", None)
    routine = store.routines.get(where["id"]) if store is not None else None
    if routine is None:
        return ""
    return run(context, browser, store, routine, start=where["next"])
