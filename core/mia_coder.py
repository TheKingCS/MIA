"""
core.mia_coder
================

MIA's own coder, and her shadow attempts (DEC-0074, T-0027;
`docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md` sections 3.3 and 4.3).

**The coder** is her local model (qwen3-coder:30b) with no tools at all: code
gives it the task and the current contents of the files it may change, and
it replies with **edits** (an exact passage to find and what replaces it),
held to a JSON schema. Code applies an edit only when its passage appears
exactly once in a listed file, only inside the lab's copy, never on the
lab's protected list. No shell, no other file, no network. (Whole new files
were tried first: on T-0019's four files the model hadn't finished after 20
minutes. Edits are a fraction of the output.)
(Codex's local mode was tried first, 2026-11-04: on Windows its sandbox stays
read-only, and the model didn't use its editing tools; letting it past the
sandbox would hand a local model the whole machine.)

**A shadow attempt** (`shadow()`): MIA works the same task the council is
working, from the same starting commit, in her own lab copy; the lab's own
check grades it (the full suite against the starting point); the outcome
goes into the history as a `shadow` event (pass, or fail and why) beside
the council's. It never merges: the proposal is rejected once graded. The
ledger (T-0028) reads these events to say what she can do.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Optional

MODEL = "qwen3-coder:30b"
WHO = "MIA (ollama-coder)"
MAX_FILE = 40_000  # characters of one file she's given
MAX_FILES = 4

SCHEMA = {"type": "object", "properties": {
    "edits": {"type": "array", "items": {"type": "object", "properties": {
        "path": {"type": "string"}, "find": {"type": "string"}, "replace": {"type": "string"}},
        "required": ["path", "find", "replace"]}},
    "said": {"type": "string"}}, "required": ["edits", "said"]}

PROMPT = """You are fixing code in MIA's development lab. Below is the task, then every file you may change,
with its full current contents. Reply with JSON: "edits", each one a path, an exact passage copied from
that file ("find": a few whole lines, enough to appear only once) and what replaces it ("replace"); and
"said", two sentences on what you changed and why. Change as little as the task needs. Keep each file's
style. Don't change files that aren't listed.

{task}

{files}"""


class CoderError(RuntimeError):
    """MIA's coder couldn't do it; the message says why."""


def files_of(task_text: str) -> list[str]:
    """Pure logic. The files a lab task lists ("Files: a.py, b.py")."""
    m = re.search(r"^\s*(?:Plan:\s*)?Files:\s*(.+)$", task_text, re.M)
    return [f.strip() for f in m.group(1).split(",") if f.strip()][:MAX_FILES] if m else []


def _ollama(prompt: str, schema: dict) -> str:
    import urllib.request

    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "format": schema,
                       "options": {"temperature": 0.1, "num_ctx": 32768}}).encode("utf-8")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=1200) as answer:
        return json.loads(answer.read()).get("response", "")


def coder(ask: Optional[Callable[[str, dict], str]] = None) -> Callable[[str, Path, str], str]:
    """A coder for core/dev_lab.write: (task, lab folder, python) -> what it said."""
    from core.dev_lab import touches_protected

    def write(task: str, cwd, python: str) -> str:
        cwd = Path(cwd)
        allowed = [f for f in files_of(task) if not touches_protected([f])]
        if not allowed:
            raise CoderError("The task lists no file MIA may change.")
        shown = []
        for f in allowed:
            path = (cwd / f).resolve()
            if cwd.resolve() not in path.parents:
                raise CoderError(f"{f} is outside the lab.")
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            if len(text) > MAX_FILE:
                raise CoderError(f"{f} is too long for her model ({len(text)} characters).")
            shown.append(f"=== {f}\n{text}")
        said = (ask or _ollama)(PROMPT.format(task=task, files="\n\n".join(shown)), SCHEMA)
        try:
            reply = json.loads(said)
        except ValueError as problem:
            raise CoderError("Her model's reply wasn't JSON.") from problem
        changed, skipped = [], []
        for item in reply.get("edits") or []:
            f = str(item.get("path", "")).replace("\\", "/").lstrip("./")
            if f not in allowed:
                skipped.append(f"{f}: not a file she may change")
                continue  # only the listed files, whatever she says
            target = (cwd / f).resolve()
            text = target.read_text(encoding="utf-8") if target.exists() else ""
            find, replace = str(item.get("find", "")), str(item.get("replace", ""))
            if not find or text.count(find) != 1:
                skipped.append(f"{f}: its passage {'is missing' if not find or find not in text else 'appears more than once'}")
                continue
            target.write_text(text.replace(find, replace, 1), encoding="utf-8")
            changed.append(f)
        note = (f" (changed {', '.join(sorted(set(changed)))})" if changed else " (changed nothing)") + \
            (f"; skipped {'; '.join(skipped[:3])}" if skipped else "")
        return str(reply.get("said", ""))[:600] + note
    return write


def shadow(task_id: str, lab=None, ask=None, suite=None, folder=None, log=None) -> dict:
    """MIA's attempt at a task, graded and recorded, never merged. Returns {"outcome", "summary", ...}."""
    from core import work_activity, work_tasks

    if lab is None:
        from core import dev_lab as lab
    tasks = work_tasks.load(folder) if folder else work_tasks.load()
    task = work_tasks._get(tasks, task_id)
    record = (lambda d: work_activity.record(WHO, "shadow", task.id, d, log)) if log else \
        (lambda d: work_activity.record(WHO, "shadow", task.id, d))
    from core.dev_knowledge import briefing  # what the team learned, as the council gets it (DEC-0073)

    known = briefing(task)
    p = lab.create(f"MIA's attempt: {task.title}", task.body or task.title, evidence=f"Task {task.id} (shadow)",
                   plan=f"Files: {', '.join(task.files)}" + (f"\n\n{known}" if known else ""))
    try:
        p = lab.write(p.proposal_id, coder=coder(ask))
    except Exception as problem:
        lab.reject(p.proposal_id, f"shadow: {problem}")
        record(f"fail: couldn't write ({str(problem)[:200]})")
        return {"outcome": "fail", "summary": str(problem)[:200], "proposal": p.proposal_id}
    if p.status != lab.WRITTEN:
        lab.reject(p.proposal_id, "shadow: nothing changed")
        record(f"fail: {p.note or 'changed nothing'}")
        return {"outcome": "fail", "summary": p.note, "proposal": p.proposal_id}
    p = lab.check(p.proposal_id, suite=suite)
    tests = getattr(p, "tests", {}) or {}
    outcome = "pass" if p.status == lab.READY else "fail"
    summary = (f"{tests.get('summary', '')}; fixed {len(tests.get('fixed') or [])}, "
               f"new failures {len(tests.get('new_failures') or [])}; files {', '.join(p.files or [])}")
    record(f"{outcome}: {summary}" + ("" if outcome == "pass" else f" ({p.note})"[:300]))
    lab.reject(p.proposal_id, "shadow attempt: graded, never merged")
    return {"outcome": outcome, "summary": summary, "proposal": p.proposal_id, "said": p.coder_said}
