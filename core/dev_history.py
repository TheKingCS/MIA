"""
core.dev_history
==================

One shared development history (T-0021, DEC-0071 point 2; DEC-0068): the
activity log already holds tasks, claims, reviews and resolves; this adds
what happened around them, so every agent reads the same history before
starting.

- **Decisions** (`decisions()`): each one in docs/DECISIONS.md, with its
  status, recorded again when its status changes.
- **Code changes** (`commits()`): each commit, with its author name (never
  an email), its subject, the files it touched and those it added (what
  the evolution timeline counts as new parts, core/dev_evolution.py), and
  the task it names (`T-0021` in the subject or body).
- **Failures** (`failures()`): the Fix-It Log's issues by kind and count,
  in the code's own words (`title_for`), never what the person said, so
  nothing personal enters the device-level record; recorded again when an
  issue's status changes.
- **Experiments** (`experiments()`): the lab's proposals and what became
  of them. The benchmark runs are a store of their own, searched with
  the rest.

`sync()` adds whatever is new to `data/dev/history` (a DevStore: append
only, never rewritten), each record once by its signature; a record's `at`
is when it was kept and `on` when it happened (a commit's date, a
decision's approval), so the store stays in time order (`when()`). `search()` is
the one search over all of it with the council's chat and the activity
log (`core.council.index()`). `briefing(task)` is what an agent reads
before starting a task: the decisions it cites and the recent commits and
experiments on its files, read from the kept record only (no git, no
index), so it's cheap and changes nothing. `python -m tools.work history`
shows it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Optional

from core.dev_store import DEV_DATA, DevStore

ROOT = Path(__file__).resolve().parent.parent
HISTORY = DEV_DATA / "history"
KINDS = ("decision", "commit", "failure", "experiment")
COMMITS_FIRST = 5000  # commits read the first time, all of them so far (then only the new ones)
BRIEF_COMMITS = 5
_TASK = re.compile(r"\bT-\d{4}\b")
_SEP = "\x1f"
_END = "\x1e"


def _store(folder: Optional[Path] = None) -> DevStore:
    """The history's append-only store (data/dev/history unless told)."""
    return DevStore(Path(folder) if folder else HISTORY)


def when(record: dict) -> str:
    """Pure logic. When a history record happened: its `on` (the event's own date), else when it was kept."""
    return str(record.get("on") or record.get("at") or "")


def _sig(record: dict) -> str:
    """Pure logic. What makes a record new: its kind and ref, and for a decision, failure or experiment its status
    (a change of status is history too)."""
    return f"{record['kind']}:{record['ref']}:{record.get('status', '')}"


def decisions(root: Path = ROOT) -> list[dict]:
    """Pure logic over the file. Every decision in docs/DECISIONS.md: {kind, ref, title, status, at (the date it was
    approved, when it says)}."""
    try:
        text = (root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for block in re.split(r"^### ", text, flags=re.M)[1:]:
        m = re.match(r"(DEC-\d{4})[:\s]+(.+)", block.splitlines()[0])
        if not m:
            continue
        status = re.search(r"^- Status: ([A-Z]+)", block, re.M)
        when = re.search(r"Approved by: [^,\n]+, (\d{4}-\d{2}-\d{2})", block)
        record = {"kind": "decision", "ref": m.group(1), "title": m.group(2).strip()[:200],
                  "status": status.group(1) if status else "", "who": "", "task": ""}
        if when:
            record["at"] = when.group(1)
        out.append(record)
    return out


def _git(root: Path, *args: str) -> str:
    """git's output in the repository, without a window and never longer than a minute ("" when git can't say)."""
    try:
        return subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_log(text: str) -> list[dict]:
    """Pure logic. `git log` output in commits()'s format (each commit opens with _END, its fields end with _SEP,
    then the files it touched, each "status<TAB>path" as --name-status gives them, a rename's new path last) to
    records, oldest first: {kind, ref (8 characters), at, who, title, task, files, added (the files it added)}."""
    out = []
    for chunk in text.split(_END):
        parts = chunk.split(_SEP)
        if len(parts) < 6:
            continue
        sha, at, who, subject, body = (x.strip() for x in parts[:5])
        files, added = [], []
        for line in parts[5].splitlines():
            status, _, path = line.strip().partition("\t")
            path = path.rpartition("\t")[2] if path else status  # a bare name (no status) is a file too
            if not path:
                continue
            files.append(path)
            if status == "A":
                added.append(path)
        task = _TASK.search(f"{subject}\n{body}")
        out.append({"kind": "commit", "ref": sha[:8], "at": at, "who": who, "title": subject[:200],
                    "task": task.group(0) if task else "", "files": files[:40], "added": added[:40]})
    return out[::-1]


def commits(root: Path = ROOT, since: str = "", git: Optional[Callable[..., str]] = None) -> list[dict]:
    """The commits after `since` (a commit; "" or one git no longer knows gives the latest COMMITS_FIRST), oldest
    first, each with the files it touched and added (--name-status). `git(root, *args)` is git itself unless given."""
    git = git or _git
    fmt = f"--format={_END}%H{_SEP}%aI{_SEP}%an{_SEP}%s{_SEP}%b{_SEP}"
    if since and not git(root, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}").strip():
        since = ""
    span = f"{since}..HEAD" if since else f"-{COMMITS_FIRST}"
    return parse_log(git(root, "log", "--no-merges", "--name-status", fmt, span))


def failures(context) -> list[dict]:
    """The Fix-It Log's issues (core/failure_log.py) in the code's words, never the person's: {kind, ref (the issue
    key), title, status, detail (how often), at (last seen)}. [] without a log."""
    book = getattr(context, "failures", None) if context is not None else None
    if book is None:
        return []
    try:
        issues = book.issues(days=365)
    except (OSError, ValueError, KeyError):
        return []
    return [{"kind": "failure", "ref": i["key"], "title": i["title"], "status": i["status"], "who": "MIA",
             "task": "", "detail": f"{i['count']} times, last {str(i['last'])[:10]}", "at": i["last"]}
            for i in issues]


def experiments() -> list[dict]:
    """The lab's proposals (core/dev_lab.py) and what became of them: {kind, ref, title, status, files}."""
    from core import dev_lab

    try:
        found = dev_lab.all_proposals()
    except (OSError, ValueError):
        return []
    return [{"kind": "experiment", "ref": p.proposal_id, "title": p.title[:200], "status": p.status, "who": "MIA",
             "task": "", "files": list(p.files)[:40], "detail": (p.problem or "")[:300]} for p in found]


def sync(root: Path = ROOT, store: Optional[DevStore] = None, context=None,
         git: Optional[Callable[..., str]] = None, lab: bool = True) -> int:
    """Adds what's new since last time to the history: decisions, commits, the Fix-It Log's issues (when `context` has
    one), the lab's experiments (unless `lab` is False). Each record once, by its signature, its own date kept as `on`.
    Returns how many were added."""
    store = store or _store()
    seen, last_commit = set(), ""
    for r in store.records():
        seen.add(_sig(r))
        if r.get("kind") == "commit":
            last_commit = r["ref"]
    found = decisions(root)
    found += commits(root, last_commit, git)
    found += failures(context)
    found += experiments() if lab else []
    added = 0
    for record in found:
        sig = _sig(record)
        if sig in seen:
            continue
        seen.add(sig)
        kept = {k: v for k, v in record.items() if k != "at"}
        if record.get("at"):
            kept["on"] = record["at"]  # the store's `at` is now, so its segments stay in time order
        store.append(kept)
        added += 1
    return added


def search(text: str, limit: int = 20, kinds: Iterable[str] = ()) -> list[dict]:
    """The one search: the history, the activity log, the council's chat and the benchmark runs, best matches first
    (`kinds` narrows it to records of those kinds)."""
    from core import council

    found = council.index()
    try:
        hits = found.search(text, limit=limit * 3)
    finally:
        found.close()
    wanted = set(kinds)
    return [h for h in hits if not wanted or h.get("kind") in wanted][:limit]


def briefing(task, store: Optional[DevStore] = None) -> str:
    """What the history says that bears on a task, for an agent's instructions: the decisions it cites, and the most
    recent commits and experiments on its files or naming it. Read from the kept record only; "" when there's nothing."""
    files = set(getattr(task, "files", None) or [])
    cited = set(getattr(task, "decisions", None) or [])
    tid = getattr(task, "id", "") or getattr(task, "task_id", "")
    latest: dict[str, dict] = {}
    for r in (store or _store()).records():
        if r.get("kind") == "decision" and r.get("ref") in cited:
            latest[f"decision:{r['ref']}"] = r
        elif r.get("kind") in ("commit", "experiment") and (
                (tid and r.get("task") == tid) or files & set(r.get("files") or [])):
            latest[f"{r['kind']}:{r['ref']}"] = r
    if not latest:
        return ""
    rows = list(latest.values())
    decided = [r for r in rows if r["kind"] == "decision"]
    changed = sorted((r for r in rows if r["kind"] == "commit"), key=when)[-BRIEF_COMMITS:]
    tried = [r for r in rows if r["kind"] == "experiment"][-BRIEF_COMMITS:]
    lines = [f"- {r['ref']} ({r.get('status') or 'no status'}): {r['title']}" for r in decided]
    lines += [f"- commit {r['ref']} {when(r)[:10]} {r.get('who', '')}: {r['title']}" for r in changed]
    lines += [f"- lab {r['ref']} ({r.get('status', '')}): {r['title']}" for r in tried]
    return "From the development history (core/dev_history.py):\n" + "\n".join(lines)


if __name__ == "__main__":  # python -m core.dev_history: bring the history up to date
    print(f"{sync()} new records in the development history")
