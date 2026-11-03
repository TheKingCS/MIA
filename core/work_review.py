"""
core.work_review
==================

Independent review, then Zac's approval (DEC-0069, step 4 of
`docs/DEV_ECOSYSTEM_AUDIT.md`). After the loop (`core/work_loop.py`) brings a
task to review:

- **review**: a role with the review tier reads the task and the lab's actual
  change (its diff against where it started) and gives a verdict, *approve*
  or *changes*, with its reasons. Never the author: a reviewer whose role or
  provider wrote the change is refused. The five security reviews of the
  relay (2026-11-02/03), each finding what the last missed, are why.
- **approve**: Zac only. It needs a person at the keyboard (typing the task's
  id back): an agent running these tools headless can't, so no agent ever
  approves its own work or anyone's. A *changes* verdict has to be answered
  first. Approving merges through the lab's own `approve`, which runs the
  suite and reverts by itself on a new failure; the task closes with the merge
  as evidence.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from core import work_activity as activity
from core import work_tasks as tasks_mod
from core.work_agents import AgentError, Registry

VERDICT = re.compile(r"VERDICT:\s*(approve|changes)", re.I)
MAX_DIFF = 60_000  # what a reviewer is given at most; past it, it's told the rest was cut

REVIEW_PROMPT = (
    "You are reviewing a change to MIA, a personal assistant, as {role}. You did not write it. Read the task and "
    "the diff, and look for real problems: bugs, a test that doesn't test what it says, security or privacy "
    "issues, a broken convention in CLAUDE.md, something the task asked for that's missing. Don't comment on "
    "style. List each problem with the file and what to change. End with one line: VERDICT: approve, or "
    "VERDICT: changes.\n\nThe task ({task_id}): {title}\n{body}\n\nThe diff:\n{diff}"
)


class ReviewError(ValueError):
    """A review or approval that can't happen as asked."""


def author_of(task_id: str, log=activity.ACTIVITY) -> str:
    """Who wrote the change: the one who did the loop's write step."""
    for e in activity.search(task_id=task_id, path=log):
        if e.get("action") == "loop" and str(e.get("detail", "")).startswith("write"):
            return e.get("who", "")
    return ""


def verdict(text: str) -> str:
    """Pure logic. "approve" or "changes"; a review with no clear verdict counts as changes."""
    found = VERDICT.findall(text or "")
    return found[-1].lower() if found else "changes"


def review(task_id: str, role_name: str, registry: Registry, *, ask: Callable[[str, str], str],
           diff: Callable[[str], str], folder=tasks_mod.TASKS_DIR, log=activity.ACTIVITY) -> str:
    """One independent review of a task waiting in review. `ask(provider, prompt)`
    runs the reviewer; `diff(proposal_id)` gives the change. Returns the verdict."""
    tasks = tasks_mod.load(folder)
    task = tasks_mod._get(tasks, task_id)
    if task.status != "review":
        raise ReviewError(f"{task.id} isn't waiting for review ({task.status}).")
    registry.may(role_name, "review")
    role = registry.role(role_name)
    who = f"{role.role} ({role.provider})"
    author = author_of(task.id, log)
    same_role = bool(author) and author.split(" (")[0] == role.role
    same_provider = bool(author) and author.endswith(f"({role.provider})")
    if same_role or (same_provider and _other_provider_exists(registry, role.provider)):
        raise ReviewError(f"{who} can't review this: {author} wrote it. Pick another role or provider.")
    pid = task.branch[len("lab/"):] if task.branch.startswith("lab/") else ""
    if not pid:
        raise ReviewError(f"{task.id} has no lab change to review.")
    change = diff(pid)
    if len(change) > MAX_DIFF:
        change = change[:MAX_DIFF] + "\n[... the rest of the diff was cut for length; say so if it matters]"
    said = ask(role.provider, REVIEW_PROMPT.format(role=role.role, task_id=task.id, title=task.title,
                                                    body=task.body, diff=change))
    found = verdict(said)
    tasks_mod.note(task, who, f"Review: {found}. " + " ".join((said or "").split())[:1500])
    tasks_mod.save(task, folder)
    activity.record(who, "review", task.id, f"{found}: {(said or '')[:500]}", log)
    return found


def _other_provider_exists(registry: Registry, provider: str) -> bool:
    """A reviewer on the author's own provider is refused only when another provider could review."""
    return any(p.name != provider and "review" in p.can for p in registry.providers.values())


def latest_verdict(task_id: str, log=activity.ACTIVITY) -> str:
    reviews = [e for e in activity.search(task_id=task_id, path=log) if e.get("action") == "review"]
    return reviews[-1]["detail"].split(":", 1)[0] if reviews else ""


def open_objections(task_id: str, log=activity.ACTIVITY) -> list[dict]:
    """Every "changes" review not yet answered (Zac, 2026-11-03: "that
    disagreement should be recorded and resolved, not silently discarded").
    A later approving review doesn't answer an objection; only a resolve does,
    saying how, and each resolve answers the objections raised before it."""
    open_ones: list[dict] = []
    for e in activity.search(task_id=task_id, path=log):
        if e.get("action") == "review" and str(e.get("detail", "")).startswith("changes"):
            open_ones.append(e)
        elif e.get("action") == "resolve":
            open_ones = []
    return open_ones


def settled_by_zac(task_id: str, log=activity.ACTIVITY) -> bool:
    """When the author and the reviewer still disagree after an answer, Zac
    decides: his resolve, after the latest review, settles it. An agent's
    can't, and a new review reopens it."""
    last = None
    for e in activity.search(task_id=task_id, path=log):
        if e.get("action") in ("review", "resolve"):
            last = e
    return bool(last) and last.get("action") == "resolve" and last.get("who") == "zac"


def resolve(task_id: str, who: str, how: str, folder=tasks_mod.TASKS_DIR, log=activity.ACTIVITY,
            confirm: Optional[Callable[[str], str]] = None) -> int:
    """Answer the open objections: what was changed, or why the reviewer was
    wrong. Kept in the task and the history either way. Returns how many."""
    tasks = tasks_mod.load(folder)
    task = tasks_mod._get(tasks, task_id)
    objections = open_objections(task.id, log)
    deciding = who == "zac" and latest_verdict(task.id, log) == "changes"  # a disagreement only Zac settles
    if not objections and not deciding:
        raise ReviewError(f"{task.id} has no open objection to resolve.")
    if not how.strip():
        raise ReviewError("Say how it's resolved: what changed, or why the objection doesn't hold.")
    if who == "zac":  # in Zac's name only with Zac at the keyboard, as approve is
        try:
            typed = confirm(f"Settle {task.id}'s review as Zac? Type {task.id}: ") if confirm else ""
        except (EOFError, OSError):
            typed = ""
        if (typed or "").strip().upper() != task.id:
            raise ReviewError("Not settled: only Zac, at the keyboard, decides in his name.")
    raised_by = ", ".join(sorted({e.get("who", "") for e in objections})) or "the last review"
    tasks_mod.note(task, who, f"Resolved the objection from {raised_by}: {how.strip()}")
    tasks_mod.save(task, folder)
    activity.record(who, "resolve", task.id, f"{len(objections)} from {raised_by}: {how.strip()}", log)
    return len(objections)


def approve(task_id: str, *, confirm: Callable[[str], str], lab=None, suite: Optional[Callable] = None,
            folder=tasks_mod.TASKS_DIR, log=activity.ACTIVITY) -> str:
    """Zac's approval. `confirm(question)` must come back as the task's id,
    typed by a person; anything else, or no person to ask, refuses."""
    if lab is None:
        from core import dev_lab as lab
    tasks = tasks_mod.load(folder)
    task = tasks_mod._get(tasks, task_id)
    if task.status != "review":
        raise ReviewError(f"{task.id} isn't waiting for approval ({task.status}).")
    objections = open_objections(task.id, log)
    if objections:
        raised_by = ", ".join(sorted({e.get("who", "") for e in objections}))
        raise ReviewError(f"{task.id} has an objection from {raised_by} nobody has answered. "
                          f"Resolve it first: python -m tools.work resolve {task.id} --by <who> --how \"...\"")
    said = latest_verdict(task.id, log)
    if said != "approve" and settled_by_zac(task.id, log):
        said = "approve"  # still disagreeing after an answer: Zac decided (DEC-0071)
    if said != "approve":
        raise ReviewError(f"{task.id} needs an independent review that approves it first"
                          + (f" (the last said {said})." if said else "."))
    try:
        typed = confirm(f"Approve {task.id} ({task.title}) into the running MIA? Type {task.id} to approve: ")
    except (EOFError, OSError):
        typed = ""
    if (typed or "").strip().upper() != task.id:
        raise ReviewError("Not approved: only Zac, at the keyboard, approves.")
    pid = task.branch[len("lab/"):]
    p = lab.approve(pid, suite=suite)
    if p.status != lab.MERGED:
        tasks_mod.note(task, "zac", f"Approved, but the lab undid it: {p.note}")
        task.status = "open"
        tasks_mod.save(task, folder)
        activity.record("zac", "approve", task.id, f"reverted: {p.note}", log)
        raise ReviewError(p.note)
    tasks_mod.finish(tasks, task.id, "zac", f"approved by Zac; merged as {p.merged_as[:10]} from lab {pid}; {p.note}")
    tasks_mod.save(task, folder)
    activity.record("zac", "approve", task.id, f"merged {p.merged_as[:10]}", log)
    return p.merged_as


def lab_diff(proposal_id: str) -> str:
    """The change a lab proposal made, from where it started."""
    from core import dev_lab

    p = dev_lab.get(proposal_id)
    return dev_lab._git("diff", f"{p.base}...{p.branch}")


def ask_provider(provider: str, prompt: str) -> str:
    """Run a review on a provider, read-only: a local model through Ollama, or
    a coding CLI (Claude Code, Codex, Copilot) that may read but never edit,
    run commands or reach the web. Each signs in with Zac's own account."""
    import shutil
    import subprocess

    from core.work_agents import load as load_agents

    spec = load_agents().providers.get(provider)
    if spec is None:
        raise ReviewError(f"No provider {provider!r}.")
    if spec.kind == "local":
        import json
        import urllib.request

        body = json.dumps({"model": spec.model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}})
        request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body.encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=900) as answer:
                said = json.loads(answer.read()).get("response", "")
        except (OSError, ValueError) as problem:
            raise ReviewError(f"{spec.model} didn't answer: {problem}") from problem
        if not said:
            raise ReviewError(f"{spec.model} didn't answer.")
        return said
    command = shutil.which(spec.command) if spec.command else None
    if command is None:
        raise ReviewError(f"{provider} isn't installed here.")
    readonly = {
        "claude-code": [command, "-p", prompt, "--allowedTools", "Read", "Glob", "Grep",
                        "--disallowedTools", "Edit", "Write", "Bash", "WebFetch", "WebSearch"],
        "codex": [command, "exec", "--sandbox", "read-only", "--skip-git-repo-check", prompt],
        "copilot": [command, "-p", prompt, "--deny-tool", "write", "--deny-tool", "shell"],
    }.get(provider)
    if readonly is None:
        raise ReviewError(f"{provider} can't review here yet.")
    out = subprocess.run(readonly, cwd=str(tasks_mod.ROOT), capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=1800, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if out.returncode != 0 and not out.stdout.strip():
        raise ReviewError(f"{provider} didn't review: {(out.stderr or '').strip()[-300:]}")
    return out.stdout or out.stderr


__all__ = ["review", "approve", "verdict", "author_of", "ReviewError", "AgentError"]
