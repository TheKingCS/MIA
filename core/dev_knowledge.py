"""
core.dev_knowledge
====================

The Development Knowledge Vault (DEC-0073; `docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md`
section 4.1): what the team learned building MIA, kept so MIA and every agent
can use it, and so MIA can one day do the work without them.

- **Entries** are markdown files in `work/knowledge/` (`K-0001-short-title.md`),
  versioned by git like everything else. Each says what kind it is (method,
  decision, implementation, failed-experiment, debugging, test-procedure,
  security-finding, lesson), what it's about (`concerns`: files and parts of
  MIA), and **where it came from** (`from`: `task:T-0019`, `commit:...`,
  `review:...`, `dec:DEC-0071`): an entry without a source is refused. It's
  never edited in place; a better one `supersedes` it.
- **derived** entries are written by MIA's local model (the retrospective)
  and stay derived until a person or a later review confirms them; she's
  never taken to be right because she said so (DEC-0083).
- **The retrospective** (`retrospective()`): after a task is done, the local
  model reads its record (the task, every step in the history, the reviews,
  the objections and how they were answered) and writes one to three
  entries, each citing only sources that record actually holds.
- **Used**: before an agent works on or reviews a task, the entries about its
  files and its kind of work go into its instructions (`for_task()`). The
  reviewer lessons (work/review_lessons.json) are folded in as lessons.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "work" / "knowledge"
KINDS = ("method", "decision", "implementation", "failed-experiment", "debugging", "test-procedure",
         "security-finding", "lesson")
STATUSES = ("derived", "confirmed", "superseded", "withdrawn")  # withdrawn: wrong, kept so its id isn't reused
# What makes a task's record worth learning from: it went through the loop, was reviewed, answered, or
# undone. A task finished in one step has no process in it, and a small model asked to describe one invents
# it (2026-11-04: 30 entries written from such records described failures and reviews that never happened).
SUBSTANCE = ("loop", "review", "resolve", "approve")
MIN_SUBSTANCE = 2
REF = re.compile(r"^(task|commit|review|resolve|dec|lab|thread|lesson|file):[\w./@:+-]+$")
MODEL = "qwen2.5:14b"
PER_TASK = 6  # entries given to an agent before it works


class KnowledgeError(ValueError):
    """An entry that can't be kept as it is; the message says why."""


def _slug(title: str) -> str:
    """A title as a short file-name slug (letters, digits and dashes, at most 48), or entry."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "entry"


def _parse(text: str) -> Optional[dict]:
    """An entry file as a dict: its front matter (concerns and from as lists) and its body; None without front
    matter.
    """
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text.replace("\r\n", "\n"), re.S)
    if not m:
        return None
    head = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        head[key.strip()] = [v.strip() for v in value.split(",") if v.strip()] if key.strip() in (
            "concerns", "from") else value
    head["body"] = m.group(2).strip()
    return head


def entries(folder: Path = KNOWLEDGE) -> list[dict]:
    """Every entry in the vault (K-*.md), oldest first, each with the file it's in."""
    out = []
    for path in sorted(Path(folder).glob("K-*.md")) if Path(folder).exists() else []:
        found = _parse(path.read_text(encoding="utf-8"))
        if found and found.get("id"):
            found["file"] = path.name
            out.append(found)
    return out


def add(kind: str, title: str, body: str, refs: list[str], concerns: list[str] = (), by: str = "mia",
        status: str = "derived", supersedes: str = "", folder: Path = KNOWLEDGE) -> dict:
    """Keep one entry. Refused without a source, with an unknown kind, or as a repeat of one already kept."""
    title, body = " ".join((title or "").split())[:100], (body or "").strip()[:3000]
    refs = [r.strip() for r in refs if r and r.strip()]
    if kind not in KINDS:
        raise KnowledgeError(f"The kind is one of {', '.join(KINDS)}.")
    if status not in STATUSES[:2]:
        raise KnowledgeError("A new entry is derived or confirmed.")
    if not title or not body:
        raise KnowledgeError("An entry needs a title and what was learned.")
    if not refs or any(not REF.match(r) for r in refs):
        raise KnowledgeError("Every entry says where it came from (task:T-0001, commit:abc1234, dec:DEC-0071...).")
    have = entries(folder)
    if any(e.get("title", "").lower() == title.lower() and e.get("status") != "superseded" for e in have):
        raise KnowledgeError(f"There's already an entry called {title!r}.")
    taken = [int(e["id"][2:]) for e in have if re.match(r"K-\d+$", e["id"])]
    entry_id = f"K-{(max(taken) + 1) if taken else 1:04d}"
    head = {"id": entry_id, "kind": kind, "title": title, "status": status, "by": by,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "concerns": ", ".join(c for c in concerns if c), "from": ", ".join(refs), "supersedes": supersedes}
    text = "---\n" + "\n".join(f"{k}: {v}" for k, v in head.items() if v != "") + "\n---\n" + body + "\n"
    Path(folder).mkdir(parents=True, exist_ok=True)
    atomic_write_text(Path(folder) / f"{entry_id}-{_slug(title)}.md", text)
    if supersedes:
        _mark(supersedes, "superseded", folder)
    return {**head, "body": body}


def _mark(entry_id: str, status: str, folder: Path) -> None:
    """Sets an entry's status line (superseded, confirmed) in place."""
    for path in Path(folder).glob(f"{entry_id}-*.md"):
        text = path.read_text(encoding="utf-8")
        atomic_write_text(path, re.sub(r"^status: \w+$", f"status: {status}", text, count=1, flags=re.M))


def withdraw(entry_id: str, who: str, why: str, folder: Path = KNOWLEDGE) -> None:
    """It was wrong: kept, never given to anyone again."""
    for path in Path(folder).glob(f"{entry_id}-*.md"):
        text = re.sub(r"^status: \w+$", "status: withdrawn", path.read_text(encoding="utf-8"), count=1, flags=re.M)
        atomic_write_text(path, text.rstrip() + f"\n\nWithdrawn by {who}: {why}\n")
        return
    raise KnowledgeError(f"No entry {entry_id}.")


def confirm(entry_id: str, who: str, folder: Path = KNOWLEDGE) -> None:
    """A person (or a later review) says it's right."""
    if not any(e["id"] == entry_id for e in entries(folder)):
        raise KnowledgeError(f"No entry {entry_id}.")
    _mark(entry_id, "confirmed", folder)


def for_task(task, folder: Path = KNOWLEDGE, limit: int = PER_TASK, min_hits: int = 3,
             derived: bool = False) -> list[dict]:
    """The entries an agent should read before working on or reviewing a task: about its files first,
    then about the same words. Confirmed ones only, unless derived: MIA's local write-ups were wrong
    too often to hand on unchecked (K-0033)."""
    files = {f.strip() for f in getattr(task, "files", []) if f.strip()}
    words = {w for w in re.findall(r"[a-z]{4,}", f"{getattr(task, 'title', '')} {getattr(task, 'body', '')}".lower())}
    scored = []
    for e in entries(folder):
        if e.get("status") in ("superseded", "withdrawn") or (e.get("status") == "derived" and not derived):
            continue  # an agent is given only what someone confirmed (DEC-0083): MIA's own notes wait
        concerns = set(e.get("concerns") or [])
        overlap = sum(1 for f in files for c in concerns if f == c or f.startswith(c.rstrip("/") + "/") or c.startswith(f))
        hits = len(words & set(re.findall(r"[a-z]{4,}", f"{e.get('title', '')} {e.get('body', '')}".lower())))
        score = overlap * 5 + hits + (1 if e.get("status") == "confirmed" else 0)
        if overlap or hits >= min_hits:
            scored.append((score, e))
    return [e for _, e in sorted(scored, key=lambda x: -x[0])[:limit]]


def briefing(task, folder: Path = KNOWLEDGE) -> str:
    """for_task() as text for an agent's instructions, then what the shared development history says about the task
    (core/dev_history.py briefing: the decisions it cites, recent commits and experiments on its files); "" when
    there's nothing."""
    from core import dev_history

    found = for_task(task, folder)
    parts = []
    if found:
        lines = [f"- [{e['kind']}, {e.get('status', 'derived')}] {e['title']}: {' '.join(e['body'].split())[:400]} "
                 f"({e['id']}; from {', '.join(e.get('from') or [])})" for e in found]
        parts.append("What the team learned before that bears on this (confirmed entries from work/knowledge):\n"
                     + "\n".join(lines))
    try:
        history = dev_history.briefing(task)
    except (OSError, ValueError):
        history = ""
    if history:
        parts.append(history)
    return "\n\n".join(parts)


# ------------------------------------------------------------------ the retrospective

# T-0044: her first 32 write-ups (2026-11-04, 08:25) were written from records with no process in them and
# described failures and reviews that never happened; all withdrawn. The record-substance guard landed after them.
GUARDED_SINCE = "2026-11-04T09:00"
_CLAIMS_FAILURE = re.compile(r"\b(fail\w*|bug|broke\w*|error|crash\w*|revert\w*|wrong|mistake|caught)\b", re.I)
_CLAIMS_REVIEW = re.compile(r"\b(review\w*|objection|disagree\w*)\b", re.I)


def supported(entry: dict, events: list[dict]) -> str:
    """Pure logic. Why an entry claims what its task's record doesn't show ("" when the record bears it out):
    a failure, bug or fix needs a failure in the record; a review or disagreement needs a review."""
    text = f"{entry.get('title', '')} {entry.get('body', '')}"
    failed = any(e.get("action") in ("loop", "review", "resolve", "approve", "shadow")
                 and re.search(r"\b(fail\w*|changes|revert\w*|not ready|new failures?)\b", str(e.get("detail", "")), re.I)
                 for e in events)
    reviewed = any(e.get("action") in ("review", "resolve") for e in events)
    if (entry.get("kind") in ("debugging", "failed-experiment") or _CLAIMS_FAILURE.search(text)) and not failed:
        return "it describes a failure the record doesn't show"
    if _CLAIMS_REVIEW.search(text) and not reviewed:
        return "it describes a review the record doesn't show"
    return ""


RETRO_SCHEMA = {"type": "object", "properties": {"entries": {"type": "array", "items": {"type": "object", "properties": {
    "kind": {"type": "string", "enum": list(KINDS)}, "title": {"type": "string"}, "body": {"type": "string"},
    "concerns": {"type": "array", "items": {"type": "string"}}, "from": {"type": "array", "items": {"type": "string"}}},
    "required": ["kind", "title", "body", "from"]}}}, "required": ["entries"]}

RETRO_PROMPT = """You keep MIA's development notebook. A development task just finished. From its record below, write
one to three entries that would help someone (or you, later) do similar work better: how it was done,
what went wrong first and why, what a reviewer caught or got wrong, how a disagreement ended. Only what
the record shows: no advice it doesn't support. Plain sentences, two to five each.

Never describe a failure, a review, a disagreement or a fix the record doesn't show line by line. If the
record shows nothing that was learned, return no entries: that's a good answer, and much better than a
guess.

Each entry: kind (one of {kinds}), title (a short claim, not a topic), body, concerns (the files or
parts of MIA it's about), and from: the sources it rests on, chosen ONLY from this list: {refs}

The record:
{record}"""


def _record(task, events: list[dict]) -> tuple[str, list[str]]:
    """A finished task's record for the retrospective, and the sources it may cite: the task, its files and body,
    then every step of its history (cut to fit), with the reviews, resolutions, commits and lab proposals named in
    it as refs; and the lab coder's steps when its proposal kept a trace (core/dev_lab.py, T-0025), so the method
    can be written up from what was done.
    """
    refs = [f"task:{task.id}"] + [f"dec:{d}" for d in getattr(task, "decisions", [])]
    lines = [f"Task {task.id}: {task.title}", f"Files: {', '.join(task.files)}", (task.body or "")[:2500], "", "History:"]
    for e in events:
        detail = " ".join(str(e.get("detail", "")).split())[:500]
        lines.append(f"- {e.get('at', '')[:16]} {e.get('who', '')} {e.get('action', '')}: {detail}")
        if e.get("action") in ("review", "resolve"):
            refs.append(f"{e['action']}:{task.id}@{e.get('at', '')}")
        commit = re.search(r"commit ([0-9a-f]{7,})", detail)
        if commit:
            refs.append(f"commit:{commit.group(1)}")
        lab = re.search(r"lab ([0-9]{8}-[0-9a-f]+)", detail)
        if lab:
            refs.append(f"lab:{lab.group(1)}")
    branch = getattr(task, "branch", "") or ""
    if branch.startswith("lab/"):
        from core import dev_lab

        method = dev_lab.trace_summary(branch[len("lab/"):])
        if method:
            lines += ["", "Method:", method]
            refs.append(f"lab:{branch[len('lab/'):]}")
    return "\n".join(lines)[:9000], sorted(set(refs))


def _ollama(prompt: str, schema: dict) -> str:
    """Asks the local model (qwen2.5:14b, through Ollama) with a JSON schema for its reply; returns what it said."""
    import urllib.request

    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "format": schema,
                       "options": {"temperature": 0.2}}).encode("utf-8")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as answer:
        return json.loads(answer.read()).get("response", "")


def retrospective(task_id: str, ask: Optional[Callable[[str, dict], str]] = None, tasks_dir=None, log=None,
                  folder: Path = KNOWLEDGE) -> list[dict]:
    """What a finished task taught, kept as derived entries. Returns what was kept (sources checked:
    an entry citing anything the record doesn't hold is dropped)."""
    from core import work_activity, work_tasks

    tasks = work_tasks.load(tasks_dir) if tasks_dir else work_tasks.load()
    task = work_tasks._get(tasks, task_id)
    events = work_activity.search(task_id=task.id, path=log) if log else work_activity.search(task_id=task.id)
    if any(f"task:{task.id}" in (e.get("from") or []) and e.get("by") == "mia" for e in entries(folder)):
        return []  # already done for this task
    if sum(1 for e in events if e.get("action") in SUBSTANCE) < MIN_SUBSTANCE:
        return []  # finished in one step: no process to learn from
    record, refs = _record(task, events)
    said = (ask or _ollama)(RETRO_PROMPT.format(kinds=", ".join(KINDS), refs=", ".join(refs), record=record),
                            RETRO_SCHEMA)
    try:
        proposed = json.loads(said).get("entries") or []
    except (ValueError, AttributeError):
        return []
    kept = []
    for p in proposed[:3]:
        if not isinstance(p, dict) or supported(p, events):
            continue  # a claim the record doesn't bear out is never kept (T-0044)
        cited = [r for r in p.get("from") or [] if r in refs]
        if f"task:{task.id}" not in cited:
            cited.insert(0, f"task:{task.id}")
        concerns = [c for c in p.get("concerns") or [] if isinstance(c, str)][:6] or list(task.files)[:6]
        try:
            kept.append(add(p.get("kind", ""), p.get("title", ""), p.get("body", ""), cited, concerns, by="mia",
                            folder=folder))
        except KnowledgeError:
            continue
    return kept


def fold_lessons(lessons: Optional[dict] = None, folder: Path = KNOWLEDGE) -> list[dict]:
    """The reviewer lessons (core/work_review.py) as lesson entries, once each."""
    if lessons is None:
        from core.work_review import _lessons

        lessons = _lessons()
    kept = []
    for provider, items in lessons.items():
        for item in items:
            title = f"{provider} as reviewer: {item['lesson'][:70]}"
            try:
                kept.append(add("lesson", title, item["lesson"], [f"task:{item['task']}", f"lesson:{provider}"],
                                [f"reviewer:{provider}"], by="review", folder=folder))
            except KnowledgeError:
                continue
    return kept
