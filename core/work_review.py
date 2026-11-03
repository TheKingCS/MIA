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
    said = latest_verdict(task.id, log)
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
    """Run a review on a provider: Ollama locally, or Claude Code read-only."""
    if provider == "ollama":
        from tools.intelligence_check import build_context

        context = build_context()
        said = context.llm.generate(prompt, timeout=300) if context.llm is not None else None
        if not said:
            raise ReviewError("The local model didn't answer.")
        return said
    if provider == "claude-code":
        import shutil
        import subprocess

        claude = shutil.which("claude")
        if claude is None:
            raise ReviewError("Claude Code isn't installed here.")
        out = subprocess.run([claude, "-p", prompt, "--allowedTools", "Read", "Glob", "Grep",
                              "--disallowedTools", "Edit", "Write", "Bash", "WebFetch", "WebSearch"],
                             cwd=str(tasks_mod.ROOT), capture_output=True, text=True, timeout=1800,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return out.stdout or out.stderr
    raise ReviewError(f"{provider} can't review here yet.")


__all__ = ["review", "approve", "verdict", "author_of", "ReviewError", "AgentError"]
