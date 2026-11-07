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
- **two reviewers** (Zac, 2026-11-03: "it probably should have a second
  reviewer"): approve needs approving reviews from two different providers,
  neither the author's, or as many as are registered if fewer. A small local
  model alone got T-0019's review wrong twice.
- **lessons** ("prompted on the things it gets wrong so it doesn't do the same
  issue twice"): a resolve that shows a reviewer was wrong can say what it
  should have checked. That lesson is kept per provider in
  `work/review_lessons.json` and put in the provider's next review prompts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Optional

from core import work_activity as activity
from core import work_tasks as tasks_mod
from core.work_agents import AgentError, Registry

VERDICT = re.compile(r"VERDICT:\s*(approve|changes)", re.I)
MAX_DIFF = 60_000  # what a reviewer is given at most; past it, it's told the rest was cut
REVIEWS_NEEDED = 2  # approving providers, when that many can review
LESSONS = tasks_mod.ROOT / "work" / "review_lessons.json"
MAX_LESSONS = 12  # per provider, the latest; older ones drop off

REVIEW_PROMPT = (
    "You are reviewing a change to MIA, a personal assistant, as {role}. You did not write it. Read the task and "
    "the diff, and look for real problems: bugs, a test that doesn't test what it says, security or privacy "
    "issues, a broken convention in CLAUDE.md, something the task asked for that's missing. Don't comment on "
    "style. List each problem with the file and what to change. A docstring that no longer says what its code "
    "does is a problem (DEC-0110). End with one line: VERDICT: approve, or VERDICT: changes.\n\n{lessons}The task "
    "({task_id}): {title}\n{body}\n\nThe diff:\n{diff}{stale}"
)


class ReviewError(ValueError):
    """A review or approval that can't happen as asked."""


def provider_of(who: str) -> str:
    """Pure logic. "QA Engineer (ollama-coder)" -> "ollama-coder"."""
    return who.rsplit("(", 1)[-1].rstrip(")") if who.endswith(")") else ""


def _lessons(path: Optional[Path] = None) -> dict:
    """Every reviewer's lessons (work/review_lessons.json), by provider; none when it can't be read."""
    try:
        return json.loads(Path(path or LESSONS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def lessons_for(provider: str, path: Optional[Path] = None) -> str:
    """What this provider got wrong before, for its review prompt; "" if nothing."""
    kept = _lessons(path).get(provider) or []
    if not kept:
        return ""
    lines = "\n".join(f"- {k['lesson']} ({k['task']})" for k in kept)
    return f"Mistakes you made in earlier reviews here. Check for these before you object:\n{lines}\n\n"


def add_lesson(provider: str, task_id: str, lesson: str, path: Optional[Path] = None) -> None:
    """Keeps a lesson for a reviewer (with the task it came from), dropping a repeat; the latest 12 each."""
    from core.atomic_write import atomic_write_text

    data = _lessons(path)
    kept = [k for k in data.get(provider, []) if k.get("lesson") != lesson]
    kept.append({"task": task_id, "lesson": lesson})
    data[provider] = kept[-MAX_LESSONS:]
    path = Path(path or LESSONS)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


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
           diff: Callable[[str], str], folder=tasks_mod.TASKS_DIR, log=activity.ACTIVITY,
           lessons: Optional[Path] = None) -> str:
    """One independent review of a task waiting in review. `ask(provider, prompt)`
    runs the reviewer; `diff(proposal_id)` gives the change, and the reviewer is also
    given the docstrings it may have left out of date (DEC-0110). Returns the verdict."""
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
                                                    body=task.body, diff=change, stale=_stale_docs(pid),
                                                    lessons=lessons_for(role.provider, lessons) + _known(task)))
    found = verdict(said)
    tasks_mod.note(task, who, f"Review: {found}. " + " ".join((said or "").split())[:1500])
    tasks_mod.save(task, folder)
    activity.record(who, "review", task.id, f"{found}: {(said or '')[:500]}", log)
    return found


def _known(task) -> str:
    """What the team learned before about this task's files (core/dev_knowledge.py, DEC-0073)."""
    try:
        from core.dev_knowledge import briefing

        found = briefing(task)
    except OSError:
        return ""
    return found + "\n\n" if found else ""


def _other_provider_exists(registry: Registry, provider: str) -> bool:
    """A reviewer on the author's own provider is refused only when another provider could review."""
    return any(p.name != provider and "review" in p.can for p in registry.providers.values())


def reviewers_needed(registry: Registry, author: str) -> int:
    """Two approving providers, or every provider that could review if fewer."""
    eligible = {r.provider for r in registry.roles.values()
                if r.tier == "review" and not author.endswith(f"({r.provider})")}
    return max(1, min(REVIEWS_NEEDED, len(eligible)))


def approvals(task_id: str, log=activity.ACTIVITY) -> list[str]:
    """The providers whose latest review of the current change approves it.
    A rewrite (the loop's write step) starts the count again."""
    latest: dict[str, str] = {}
    for e in activity.search(task_id=task_id, path=log):
        if e.get("action") == "loop" and str(e.get("detail", "")).startswith("write"):
            latest = {}
        elif e.get("action") == "review":
            latest[provider_of(e.get("who", ""))] = str(e.get("detail", "")).split(":", 1)[0]
    return sorted(p for p, said in latest.items() if said == "approve")


def latest_verdict(task_id: str, log=activity.ACTIVITY) -> str:
    """A task's latest review verdict, or empty."""
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
            confirm: Optional[Callable[[str], str]] = None, lesson: str = "",
            lessons: Optional[Path] = None) -> int:
    """Answer the open objections: what was changed, or why the reviewer was
    wrong. Kept in the task and the history either way. `lesson`, when the
    reviewer was wrong, is what it should check next time: it goes into that
    provider's later review prompts. Returns how many."""
    tasks = tasks_mod.load(folder)
    task = tasks_mod._get(tasks, task_id)
    objections = open_objections(task.id, log)
    deciding = who == "zac" and bool(latest_verdict(task.id, log))  # a disagreement, or a review short: Zac's
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
    if lesson.strip():
        objected = objections or [e for e in activity.search(task_id=task.id, path=log)
                                  if e.get("action") == "review"][-1:]
        for provider in sorted({provider_of(e.get("who", "")) for e in objected} - {""}):
            add_lesson(provider, task.id, lesson.strip(), lessons)
            activity.record(who, "lesson", task.id, f"for {provider}: {lesson.strip()}", log)
    return len(objections)


def _registry() -> Registry:
    """The development agents' registry."""
    from core.work_agents import load as load_agents

    return load_agents()


def approve(task_id: str, *, confirm: Callable[[str], str], lab=None, suite: Optional[Callable] = None,
            folder=tasks_mod.TASKS_DIR, log=activity.ACTIVITY, registry: Optional[Registry] = None) -> str:
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
    if not settled_by_zac(task.id, log):  # still disagreeing after an answer: Zac decided (DEC-0071)
        if said != "approve":
            raise ReviewError(f"{task.id} needs an independent review that approves it first"
                              + (f" (the last said {said})." if said else "."))
        need = reviewers_needed(registry or _registry(), author_of(task.id, log))
        have = approvals(task.id, log)
        if len(have) < need:
            raise ReviewError(f"{task.id} has {len(have)} approving review(s) ({', '.join(have) or 'none'}); "
                              f"it needs {need} from different providers. Ask another reviewer, or settle "
                              f"it yourself with resolve.")
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


def _stale_docs(proposal_id: str) -> str:
    """For the reviewer: the docstrings a lab change may have left out of date (core/doc_freshness.py, DEC-0110),
    or nothing when there are none or the proposal can't be read."""
    try:
        from core import dev_lab, doc_freshness

        p = dev_lab.get(proposal_id)
        found = doc_freshness.describe(doc_freshness.between(p.base, p.branch))
    except Exception:
        return ""
    return f"\n\nTheir code changed and their docstrings didn't (check each still says what it does):\n{found}" \
        if found else ""


def lab_diff(proposal_id: str) -> str:
    """The change a lab proposal made, from where it started."""
    from core import dev_lab

    p = dev_lab.get(proposal_id)
    return dev_lab._git("diff", f"{p.base}...{p.branch}")


def _ask(provider: str, prompt: str) -> str:
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
    from core.dev_usage import outcome

    said = f"{out.stdout}\n{out.stderr}".strip()
    if out.returncode != 0 and (not out.stdout.strip() or outcome(said) == "limit"):
        # A usage limit printed as output is not a review (DEC-0079): it's the provider resting.
        raise ReviewError(f"{provider} didn't answer: {said[-300:]}")
    answer = out.stdout or out.stderr
    if provider == "copilot":  # its CLI's status lines ("● Copilot Fusion selected ...", "● Read ...") aren't the answer
        answer = "\n".join(line for line in answer.splitlines() if not line.lstrip().startswith("●")).strip()
    return answer


def ask_provider(provider: str, prompt: str, purpose: str = "review", task: str = "") -> str:
    """`_ask` with every call recorded (DEC-0079, core/dev_usage.py): how long,
    how much text each way, and whether it ended at a usage limit."""
    import time

    from core import dev_usage

    started, said, problem = time.monotonic(), "", ""
    try:
        said = _ask(provider, prompt)
        return said
    except Exception as error:
        problem = str(error) or type(error).__name__
        raise
    finally:
        try:
            dev_usage.record(provider, purpose, time.monotonic() - started, len(prompt), len(said or ""),
                             error=problem, task=task)
        except OSError:  # the record never stops the work
            pass


__all__ = ["review", "approve", "verdict", "author_of", "ReviewError", "AgentError"]
