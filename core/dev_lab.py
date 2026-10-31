"""
core.dev_lab
==============

MIA's development lab (DEC-0058; the ROADMAP's self-modification stages
2 and 3; docs/INSPECTION_AND_SELF_PLAN.md section 6). MIA proposes an
improvement; the change is written and tested in an isolated copy; it
reaches the running MIA only when Zac approves.

- **Isolated:** each proposal is a git worktree in a folder beside MIA
  (`../MIA-lab/<id>`), on its own branch `lab/<id>`. A fresh checkout
  has no `data/`, no `config/config.json`, no vault: no real records and
  no credentials, by construction. The running MIA's folder is never
  the lab's working folder.
- **Written by Claude Code** (Zac's choice): run headless in the lab
  folder, allowed only to read, edit and write files there and to run
  the test suite; no web, no git push. MIA writes the task (the problem,
  the evidence, the plan, the rules).
- **Checked here, by rules the lab can't touch:** `PROTECTED` lives in
  this file, in the running copy; a change touching any of it is
  refused, whatever it is. Then the full suite runs in the lab and its
  failures are compared with the same suite at the starting commit: a
  proposal is ready only with no new failure.
- **Approved by Zac only** (an action that's never a child's, never the
  glasses'): the branch is merged into the running copy, the suite runs
  again, and a new failure reverts the merge by itself (`git revert`,
  history kept). MIA restarts to load it.

Proposals are kept on this device (`data/lab/proposals.json`).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
LAB_ROOT = ROOT.parent / "MIA-lab"
_STORE = ROOT / "data" / "lab" / "proposals.json"
SUITE_TIMEOUT = 1200
CODER_TIMEOUT = 2400
OWNER = ("TheKingCS", "149123826+TheKingCS@users.noreply.github.com")  # the repo's owner, for merges
LAB_AUTHOR = ("MIA Lab", "lab@mia.local")

# The lab may never change these (DEC-0058): its own rules, the approval and undo paths, the safety floor,
# children's limits, credentials and secrets, money and mail, boot and deployment, the decisions.
PROTECTED = (
    "core/dev_lab.py", "tools/lab.py", "core/actions.py", "core/undo_log.py", "core/safety_floor.py",
    "core/safety_escalation.py", "core/child_accounts.py", "core/secrets_manager.py", "core/password_vault.py",
    "core/memory_vault.py", "core/plaid_manager.py", "core/mail_send.py", "core/home_link.py", "core/web_account.py",
    "core/first_account.py", "core/account_data.py", "core/communication_gate.py", "server/app.py", "main.py",
    "deploy/", ".github/", "config/", "data/", "docs/DECISIONS.md", "requirements.txt", "android-phone/",
)
DRAFTED, WRITTEN, READY, NOT_READY, MERGED, REVERTED, REJECTED = (
    "drafted", "written", "ready", "not ready", "merged", "reverted", "rejected")


@dataclass
class Proposal:
    proposal_id: str
    title: str
    problem: str
    evidence: str = ""
    plan: str = ""
    status: str = DRAFTED
    branch: str = ""
    base: str = ""  # the commit the lab started from
    created_at: str = ""
    updated_at: str = ""
    files: list = field(default_factory=list)
    refused: list = field(default_factory=list)  # protected files it touched
    tests: dict = field(default_factory=dict)  # {"summary", "new_failures", "base_failures"}
    coder_said: str = ""
    merged_as: str = ""
    note: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _git(*args: str, cwd: Optional[Path] = None, author: Optional[tuple] = None, check: bool = True) -> str:
    cwd = cwd or ROOT
    who = ["-c", f"user.name={author[0]}", "-c", f"user.email={author[1]}"] if author else []
    out = subprocess.run(["git", *who, *args], cwd=str(cwd), capture_output=True, text=True, timeout=300,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if check and out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout or "git failed").strip()[:400])
    return (out.stdout or "").strip()


# ---------------------------------------------------------------- pure rules


def touches_protected(files: list[str], protected: tuple = PROTECTED) -> list[str]:
    """Pure logic. The changed files the lab may never change."""
    return [f for f in files if any(f == p or (p.endswith("/") and f.startswith(p)) for p in protected)]


_FAILED = re.compile(r"^FAILED (\S+)", re.MULTILINE)


def suite_result(output: str) -> dict:
    """Pure logic. pytest's output -> {"summary", "failed": [test ids]}."""
    failed = sorted(set(m.split(" - ")[0] for m in _FAILED.findall(output or "")))
    lines = [ln.strip("= ").strip() for ln in (output or "").splitlines() if re.search(r"\d+ (passed|failed)", ln)]
    return {"summary": lines[-1] if lines else "no summary (the suite didn't finish)", "failed": failed,
            "finished": bool(lines)}


def new_failures(lab: dict, base: dict) -> list[str]:
    """Pure logic. Tests that fail in the lab and didn't at the start."""
    return sorted(set(lab.get("failed", [])) - set(base.get("failed", [])))


def coder_task(p: Proposal, python: str) -> str:
    """What Claude Code is asked to do, with the lab's rules."""
    return f"""You are working in MIA's development lab: a separate copy of MIA's repository (this folder), on its own branch.
Nothing here is the running MIA; your change reaches it only if the owner approves it.

Task: {p.title}

Problem: {p.problem}

Evidence: {p.evidence or "(none given)"}

Plan: {p.plan or "(work it out from the code)"}

Rules:
- Read CLAUDE.md first and follow its conventions.
- Change only files in this folder. Never change any of these (the change is refused if you do): {", ".join(PROTECTED)}.
- Write a test that fails before your change and passes after it (or fix the test when the test is what's wrong).
- Run the tests you touched with: {python} -m pytest -q -p no:cacheprovider <test files>
- Keep the change as small as the problem needs. Don't commit; the lab commits.
- End with two or three sentences: what you changed and why."""


# ---------------------------------------------------------------- the store


def _load() -> list[Proposal]:
    try:
        raw = json.loads(_STORE.read_text(encoding="utf-8")) if _STORE.exists() else []
    except (OSError, ValueError):
        raw = []
    return [Proposal(**{k: v for k, v in r.items() if k in Proposal.__dataclass_fields__}) for r in raw]


def _save(proposals: list[Proposal]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps([asdict(p) for p in proposals], indent=1), encoding="utf-8")


def all_proposals() -> list[Proposal]:
    return _load()


def get(proposal_id: str) -> Proposal:
    found = next((p for p in _load() if p.proposal_id == proposal_id), None)
    if found is None:
        raise ValueError("That proposal isn't there.")
    return found


def _put(p: Proposal) -> Proposal:
    proposals = [x for x in _load() if x.proposal_id != p.proposal_id] + [p]
    p.updated_at = _now()
    _save(sorted(proposals, key=lambda x: x.created_at))
    return p


def folder(p: Proposal) -> Path:
    return LAB_ROOT / p.proposal_id


# ---------------------------------------------------------------- the steps


def create(title: str, problem: str, evidence: str = "", plan: str = "") -> Proposal:
    """A proposal and its lab: a worktree on a new branch from the running copy's commit."""
    if not str(title or "").strip() or not str(problem or "").strip():
        raise ValueError("A proposal needs a title and the problem it solves.")
    pid = datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6]
    p = Proposal(pid, title.strip(), problem.strip(), evidence.strip(), plan.strip(), branch=f"lab/{pid}",
                 base=_git("rev-parse", "HEAD"), created_at=_now())
    LAB_ROOT.mkdir(parents=True, exist_ok=True)
    _git("worktree", "add", "-b", p.branch, str(folder(p)), p.base)
    return _put(p)


def _python() -> str:
    found = ROOT / ".venv" / "Scripts" / "python.exe"
    if not found.exists():
        found = ROOT / ".venv" / "bin" / "python"
    return str(found).replace("\\", "/")


def run_claude(task: str, cwd: Path, python: str) -> str:
    """Claude Code, headless, in the lab folder: files there and the test suite only."""
    claude = shutil.which("claude")
    if claude is None:
        raise RuntimeError("Claude Code isn't installed on this computer.")
    args = [claude, "-p", task, "--permission-mode", "acceptEdits", "--output-format", "json",
            "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", f"Bash({python} -m pytest:*)",
            "--disallowedTools", "WebFetch", "WebSearch", "Bash(git push:*)"]
    out = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, timeout=CODER_TIMEOUT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        return str(json.loads(out.stdout).get("result") or "").strip()
    except ValueError:
        return (out.stdout or out.stderr or "").strip()[-2000:]


def write(proposal_id: str, coder: Optional[Callable] = None) -> Proposal:
    """Claude Code writes the change in the lab; the lab commits it."""
    p = get(proposal_id)
    if p.status not in (DRAFTED, NOT_READY):
        raise ValueError(f"That proposal is {p.status}.")
    lab = folder(p)
    said = (coder or run_claude)(coder_task(p, _python()), lab, _python())
    p.coder_said = str(said or "")[:2000]
    _git("add", "-A", cwd=lab)
    if not _git("status", "--porcelain", cwd=lab):
        p.status, p.note = NOT_READY, "The coder changed nothing."
        return _put(p)
    _git("commit", "-m", f"lab: {p.title}\n\n{p.problem}", cwd=lab, author=LAB_AUTHOR)
    p.status = WRITTEN
    return _put(p)


def run_suite(cwd: Path) -> dict:
    out = subprocess.run([_python(), "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=str(cwd),
                         capture_output=True, text=True, timeout=SUITE_TIMEOUT,
                         env={**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"},
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return suite_result((out.stdout or "") + "\n" + (out.stderr or ""))


def check(proposal_id: str, suite: Optional[Callable] = None) -> Proposal:
    """The rules, then the suite in the lab against the suite at the start."""
    p = get(proposal_id)
    lab = folder(p)
    p.files = [f for f in _git("diff", "--name-only", f"{p.base}...{p.branch}").splitlines() if f]
    p.refused = touches_protected(p.files)
    if p.refused:
        p.status, p.note = NOT_READY, "It changes files the lab may never change: " + ", ".join(p.refused)
        return _put(p)
    run = suite or run_suite
    lab_result = run(lab)
    base_dir = LAB_ROOT / f"_base-{p.base[:10]}"
    if not base_dir.exists():
        _git("worktree", "add", "--detach", str(base_dir), p.base)
    base_result = run(base_dir)
    fresh = new_failures(lab_result, base_result)
    p.tests = {"summary": lab_result["summary"], "base_summary": base_result["summary"], "new_failures": fresh,
               "fixed": sorted(set(base_result["failed"]) - set(lab_result["failed"])),
               "lab_failed": lab_result["failed"], "base_failed": base_result["failed"]}
    finished = lab_result.get("finished", True) and base_result.get("finished", True)
    p.status = READY if (not fresh and finished) else NOT_READY
    p.note = "" if p.status == READY else ("New failures: " + ", ".join(fresh) if fresh else "The suite didn't finish.")
    return _put(p)


def approve(proposal_id: str, suite: Optional[Callable] = None) -> Proposal:
    """Zac's approval: merged into the running copy, the suite again, reverted by itself on a new failure."""
    p = get(proposal_id)
    if p.status != READY:
        raise ValueError(f"Only a ready proposal can go in; this one is {p.status}.")
    dirty = [ln[3:] for ln in _git("status", "--porcelain").splitlines()]
    if set(dirty) & set(p.files):
        raise ValueError("Files it changes have unsaved edits here: " + ", ".join(sorted(set(dirty) & set(p.files))))
    _git("merge", "--no-ff", "--no-edit", p.branch, "-m", f"From the lab: {p.title} ({p.proposal_id})", author=OWNER)
    p.merged_as = _git("rev-parse", "HEAD")
    after = (suite or run_suite)(ROOT)  # the running copy
    fresh = new_failures(after, {"failed": p.tests.get("lab_failed", [])})  # anything beyond what failed in the lab
    if not after.get("finished", True):
        fresh = fresh or ["(the suite didn't finish)"]
    if fresh:
        _git("revert", "-m", "1", "--no-edit", "HEAD", author=OWNER)
        p.status, p.note = REVERTED, "It broke here: " + ", ".join(fresh) + ". Reverted; the history keeps both."
    else:
        p.status, p.note = MERGED, "In. Restart MIA to load it."
    return _put(p)


def reject(proposal_id: str, why: str = "") -> Proposal:
    p = get(proposal_id)
    if p.status in (MERGED,):
        raise ValueError("It's already in; undo it with a revert instead.")
    try:
        _git("worktree", "remove", "--force", str(folder(p)))
        _git("branch", "-D", p.branch)
    except RuntimeError as exc:
        log.warning("Lab cleanup: %s", exc)
    p.status, p.note = REJECTED, why or "Rejected."
    return _put(p)


def describe(p: Proposal) -> str:
    """One proposal in a few plain sentences."""
    out = f"{p.title} ({p.status})."
    if p.files:
        out += f" Changes {len(p.files)} file{'s' if len(p.files) != 1 else ''}: {', '.join(p.files[:5])}."
    if p.tests:
        out += f" Lab suite: {p.tests.get('summary')}; at the start: {p.tests.get('base_summary')}."
        if p.tests.get("fixed"):
            out += f" It fixes {len(p.tests['fixed'])} failing test{'s' if len(p.tests['fixed']) != 1 else ''}."
    if p.note:
        out += " " + p.note
    return out
