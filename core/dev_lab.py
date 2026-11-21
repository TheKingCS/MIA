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
- **Approved by Zac** (an action that's never a child's, never the
  glasses'), **or, for what Night School keeps, by Claude's pass**
  (core/self_merges.py, DEC-0225, Zac's yes to Q-76): the branch is merged
  into the running copy, the suite runs again, and a new failure reverts
  the merge by itself (`git revert`, history kept). MIA restarts to load
  it. `revert` is his Undo on a change that's in.

Proposals are kept on this device (`data/lab/proposals.json`), and beside
them each coder attempt's method trace (`data/lab/traces/<id>.json`, T-0025):
the tools it used and on what, in order, never what it wrote; the
retrospective (core/dev_knowledge.py) writes method entries from it.
`quiet_job_flags()` is how MIA starts her background jobs on Windows so
nothing they run ever flashes a window on the desktop.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
LAB_ROOT = ROOT.parent / "MIA-lab"
_STORE = DATA_DIR / "lab" / "proposals.json"
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
    # The development platform's own rules and records (DEC-0075): who reviews, who may do what, the
    # history and the measure of what MIA can do. A lab change can't rewrite its own judge.
    "core/work_review.py", "core/work_agents.py", "core/work_loop.py", "core/work_tasks.py",
    "core/work_activity.py", "core/dev_store.py", "core/dev_usage.py", "core/council.py", "core/council_floor.py", "core/work_runner.py", "core/dev_knowledge.py", "tools/work.py",
    "tools/dev_window.py", "work/",
    # What MIA's creations are checked and published by (DEC-0091): she can't loosen her own rules.
    "core/creation_spec.py", "core/creation_actions.py", "core/creations.py", "core/record_sets.py", "core/creation_sources.py", "core/workflows.py", "core/dev_ledger.py", "core/mia_coder.py", "core/dev_map.py", "core/record_import.py", "core/loops.py",
    # Night School grades her and keeps the map of what her loops watch (DEC-0100, DEC-0101).
    "core/night_school.py", "core/loop_coverage.py", "tools/night_school.py", "core/dev_checks.py",
    "core/corrections.py", "core/benchmarks.py", "tools/weekly_bench.py", "core/capability_gaps.py", "core/good_news.py",
    # What she may do on her own, how she's stopped, and what judges her models and her own changes (DEC-0225;
    # Zac, 2026-11-17, Q-78): her grants, the stop, browser safety, every kind's reach, the model inspection, the
    # lab's actions, her merges and repairs, and the list itself (core/protected_list.py says it in words).
    "core/grants.py", "core/kind_grants.py", "core/stop.py", "core/browser_safety.py", "core/action_effects.py",
    "core/model_inspection.py", "core/lab_actions.py", "core/self_merges.py", "core/self_repair.py",
    "core/protected_list.py",
    # What those rest on (Fable's review, 2026-11-18): every kind's tier (the app manifests) and the registry that
    # reads them; taught skills' guard; the words that approve by voice and the turn they run in; what runs on a
    # schedule; whose settings are whose; the grants' own actions; the approval card's code; and the suite's own
    # settings, since the suite is what gates a merge.
    "apps/*/manifest.json", "core/app_registry.py", "core/taught_skills.py", "core/spoken_approval.py",
    "core/quick_commands.py", "core/assistant_turn.py", "core/background_jobs.py", "core/scheduler.py",
    "core/person_settings.py", "core/grant_actions.py", "web/mia.js", "web/shell.js", "pytest.ini",
    "tests/conftest.py",
)
DRAFTED, WRITTEN, READY, NOT_READY, MERGED, REVERTED, REJECTED = (
    "drafted", "written", "ready", "not ready", "merged", "reverted", "rejected")


@dataclass
class Proposal:
    """One improvement MIA proposed: its title, the problem, the evidence and the plan; its status; its lab branch and
    the commit it started from; the files it changed and any protected ones it touched (refused); the test results
    against the starting commit; what the coder said; the commit it was merged as; a note.
    """
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
    """Now, as an ISO timestamp to the second."""
    return datetime.now().isoformat(timespec="seconds")


def _git(*args: str, cwd: Optional[Path] = None, author: Optional[tuple] = None, check: bool = True,
         undo: Optional[tuple] = None) -> str:
    """Runs git (in the running copy unless told otherwise, with an author when committing) and returns its output;
    RuntimeError with git's words when it fails and check is on. `undo` is what backs a failed step out (a merge or
    revert that conflicts runs `merge --abort` or `revert --abort`), so the running copy is never left half-way with
    conflict markers in her code (the review of 2026-11-18).
    """
    cwd = cwd or ROOT
    who = ["-c", f"user.name={author[0]}", "-c", f"user.email={author[1]}"] if author else []
    out = subprocess.run(["git", *who, *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if check and out.returncode != 0:
        if undo:
            subprocess.run(["git", *undo], cwd=str(cwd), capture_output=True, text=True, timeout=120,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        raise RuntimeError((out.stderr or out.stdout or "git failed").strip()[:400])
    return (out.stdout or "").strip()


# ---------------------------------------------------------------- pure rules


def touches_protected(files: list[str], protected: tuple = PROTECTED) -> list[str]:
    """Pure logic. The changed files the lab may never change: a path by its name, a folder (ending "/") by
    everything under it, a pattern with "*" by a match; compared without regard to case or slash direction, since
    the PC's file names don't tell case apart."""
    from fnmatch import fnmatchcase

    def hit(name: str, rule: str) -> bool:
        """Whether one changed file falls under one protected entry."""
        name, rule = name.replace("\\", "/").lower(), rule.lower()
        if "*" in rule:
            return fnmatchcase(name, rule)
        return name == rule or (rule.endswith("/") and name.startswith(rule))

    return [f for f in files if any(hit(f, p) for p in protected)]


def removed_tests(status_lines: list[str]) -> list[str]:
    """Pure logic. Test files a change deletes, from `git diff --name-status --no-renames` lines: the suite gates a
    merge, so a change may add tests but never take a test file away."""
    out = []
    for line in status_lines:
        status, _tab, name = line.partition("\t")
        if status.strip().upper().startswith("D") and name.replace("\\", "/").lower().startswith("tests/"):
            out.append(name)
    return out


CODE_SUFFIXES = (".py", ".js", ".sh")  # what counts as code for DEC-0224's proof


def needs_proof(files: list[str]) -> bool:
    """Pure logic. Whether a change must come with a test that fails before it (DEC-0224): any change to code
    outside tests/ does (Python, the web front end's JavaScript, shell scripts); a change to tests, docs, styles or
    data alone doesn't."""
    def code(name: str) -> bool:
        """Whether a changed file is code."""
        name = name.replace("\\", "/")
        return not name.lower().startswith("tests/") and name.endswith(CODE_SUFFIXES)
    return any(code(f) for f in files)


def test_files(files: list[str]) -> list[str]:
    """Pure logic. The files a change adds or changes under tests/."""
    return [f for f in files if f.replace("\\", "/").lower().startswith("tests/")]


def passed_count(summary: str) -> Optional[int]:
    """Pure logic. How many tests pytest's summary line says passed; None when it doesn't say."""
    found = re.search(r"(\d+) passed", summary or "")
    return int(found.group(1)) if found else None


_PASSED = re.compile(r"^PASSED (\S+)", re.MULTILINE)  # pytest -rp names each test that passed
_FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.MULTILINE)  # an error (a broken fixture, a failed import) fails too


def suite_result(output: str) -> dict:
    """Pure logic. pytest's output -> {"summary", "failed": [test ids], "finished"}; a test that errored counts as
    failed, and errors with no test id count as one failure."""
    failed = sorted(set(m.split(" - ")[0] for m in _FAILED.findall(output or "")))
    lines = [ln.strip("= ").strip() for ln in (output or "").splitlines()
             if re.search(r"\d+ (passed|failed|errors?)\b", ln)]
    if lines and re.search(r"\d+ errors?\b", lines[-1]) and not failed:
        failed = ["(the suite reported errors)"]  # errors with no test id still count
    return {"summary": lines[-1] if lines else "no summary (the suite didn't finish)", "failed": failed,
            "finished": bool(lines)}


def new_failures(lab: dict, base: dict) -> list[str]:
    """Pure logic. Tests that fail in the lab and didn't at the start."""
    return sorted(set(lab.get("failed", [])) - set(base.get("failed", [])))


def coder_task(p: Proposal, python: str) -> str:
    """What Claude Code is asked to do, with the lab's rules (among them DEC-0224's proving test)."""
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
  A change to code with no test that fails on the old code isn't ready: the lab runs your tests against it.
- Run the tests you touched with: {python} -m pytest -q -p no:cacheprovider <test files>
- Keep the change as small as the problem needs. Don't commit; the lab commits.
- End with two or three sentences: what you changed and why."""


# ---------------------------------------------------------------- the store


def _load() -> list[Proposal]:
    """Every proposal from data/lab/proposals.json ([] when there's none or it can't be read)."""
    try:
        raw = json.loads(_STORE.read_text(encoding="utf-8")) if _STORE.exists() else []
    except (OSError, ValueError):
        raw = []
    return [Proposal(**{k: v for k, v in r.items() if k in Proposal.__dataclass_fields__}) for r in raw]


def _save(proposals: list[Proposal]) -> None:
    """Writes every proposal."""
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps([asdict(p) for p in proposals], indent=1), encoding="utf-8")


def all_proposals() -> list[Proposal]:
    """Every proposal."""
    return _load()


def get(proposal_id: str) -> Proposal:
    """The proposal with this id, or ValueError."""
    found = next((p for p in _load() if p.proposal_id == proposal_id), None)
    if found is None:
        raise ValueError("That proposal isn't there.")
    return found


def _put(p: Proposal) -> Proposal:
    """Saves one proposal (replacing its earlier self), stamping updated_at."""
    proposals = [x for x in _load() if x.proposal_id != p.proposal_id] + [p]
    p.updated_at = _now()
    _save(sorted(proposals, key=lambda x: x.created_at))
    return p


def folder(p: Proposal) -> Path:
    """The proposal's lab folder (its own git worktree beside MIA: ../MIA-lab/<id>)."""
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
    """The virtual environment's Python (Windows or Linux layout), for running the suite in the lab."""
    found = ROOT / ".venv" / "Scripts" / "python.exe"
    if not found.exists():
        found = ROOT / ".venv" / "bin" / "python"
    return str(found).replace("\\", "/")


def quiet_job_flags() -> int:
    """How a background job MIA starts (Night School, Good News Radio, the Chronicle) is created on Windows: with a
    console of its own that is never shown (CREATE_NO_WINDOW), in its own process group so it outlives MIA. Not
    DETACHED_PROCESS (2026-11-07): that leaves the job with no console at all, and every git, pytest or PowerShell it
    runs then opens a window of its own on the desktop, one after another. 0 elsewhere."""
    if sys.platform != "win32":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def run_claude(task: str, cwd: Path, python: str) -> str:
    """Claude Code, headless, in the lab folder: files there and the test suite only. Its stream of steps is read for
    the method trace (T-0025): what it says comes back as a CoderSaid carrying the tools it used and on what."""
    claude = shutil.which("claude")
    if claude is None:
        raise RuntimeError("Claude Code isn't installed on this computer.")
    args = [claude, "-p", task, "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose",
            "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", f"Bash({python} -m pytest:*)",
            "--disallowedTools", "WebFetch", "WebSearch", "Bash(git push:*)"]
    out = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=CODER_TIMEOUT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    said, steps = trace_steps(out.stdout or "", cwd)
    return CoderSaid(said or (out.stderr or out.stdout or "").strip()[-2000:], steps)


def write(proposal_id: str, coder: Optional[Callable] = None, again: str = "") -> Proposal:
    """Claude Code writes the change in the lab; the lab commits it. With `again` (what went wrong the first time,
    e.g. the failing test's output), a written proposal gets one more try on top of the first. A coder that says what
    steps it took (a CoderSaid) has them kept as the proposal's trace (data/lab/traces)."""
    p = get(proposal_id)
    if p.status not in (DRAFTED, NOT_READY) + ((WRITTEN,) if again else ()):
        raise ValueError(f"That proposal is {p.status}.")
    lab = folder(p)
    task = coder_task(p, _python()) + (f"\n\nYour change is already in the files. {again}" if again else "")
    said = (coder or run_claude)(task, lab, _python())
    if getattr(said, "steps", None):
        save_trace(p.proposal_id, said.steps, "second" if again else "first")
    p.coder_said = (f"{p.coder_said}\n\nSecond try: " if again else "") + str(said or "")[:2000]
    _git("add", "-A", cwd=lab)
    if not _git("status", "--porcelain", cwd=lab):
        if again and p.status == WRITTEN:
            return _put(p)  # the second try changed nothing: the first stands
        p.status, p.note = NOT_READY, "The coder changed nothing."
        return _put(p)
    _git("commit", "-m", f"lab: {p.title}\n\n{p.problem}", cwd=lab, author=LAB_AUTHOR)
    p.status, p.note = WRITTEN, ""
    return _put(p)


# ------------------------------------------------------------------ method traces (T-0025, DEC-0073)

MAX_STEPS = 200  # per attempt
_TARGETS = ("file_path", "notebook_path", "path", "pattern", "glob")
_PROPOSAL_ID = re.compile(r"^[0-9]{8}-[0-9a-f]+$")


class CoderSaid(str):
    """What a coder said, carrying the steps it took (`steps`: [{tool, target}]) when it can tell them. A plain str
    from a coder still works: it just has no trace."""

    steps: list = []

    def __new__(cls, said: str, steps: Optional[list] = None) -> "CoderSaid":
        """The words, and the steps beside them."""
        made = super().__new__(cls, said)
        made.steps = list(steps or [])
        return made


def _step(tool: str, given: dict, cwd: Optional[Path] = None) -> dict:
    """Pure logic. One step as its tool and target only, never content: the file or pattern it read, searched or
    edited (relative to the lab folder), or a command's first six words."""
    if tool == "Bash":
        target = " ".join(str(given.get("command", "")).split()[:6])
    else:
        target = next((str(given[k]) for k in _TARGETS if given.get(k)), "")
        if cwd is not None and target:
            here = str(cwd).replace("\\", "/").rstrip("/") + "/"
            flat = target.replace("\\", "/")
            target = flat[len(here):] if flat.lower().startswith(here.lower()) else flat
    return {"tool": str(tool)[:40], "target": target[:200]}


def trace_steps(stream: str, cwd: Optional[Path] = None) -> tuple[str, list[dict]]:
    """Pure logic. Claude Code's stream-json output to (what it said at the end, the steps it took): each tool it
    used and on what, in order, at most MAX_STEPS."""
    said, steps = "", []
    for line in (stream or "").splitlines():
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if not isinstance(msg, dict):
            continue
        if msg.get("type") == "result":
            said = str(msg.get("result") or "").strip()
        if msg.get("type") != "assistant":
            continue
        for block in (msg.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                steps.append(_step(str(block.get("name", "")), block.get("input") or {}, cwd))
    return said, steps[:MAX_STEPS]


def _traces() -> Path:
    """Where the traces are kept: data/lab/traces, beside the proposals."""
    return _STORE.parent / "traces"


def trace(proposal_id: str) -> list[dict]:
    """A proposal's kept attempts, oldest first: [{at, attempt, steps}]; [] when there's none."""
    if not _PROPOSAL_ID.match(proposal_id or ""):
        return []
    try:
        return json.loads((_traces() / f"{proposal_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def save_trace(proposal_id: str, steps: list[dict], attempt: str) -> None:
    """Keeps one attempt's steps next to the proposal (data/lab/traces/<id>.json), added to those before."""
    if not _PROPOSAL_ID.match(proposal_id or ""):
        return
    kept = trace(proposal_id) + [{"at": datetime.now().isoformat(timespec="seconds"), "attempt": attempt,
                                  "steps": [{"tool": s.get("tool", ""), "target": s.get("target", "")}
                                            for s in steps[:MAX_STEPS]]}]
    _traces().mkdir(parents=True, exist_ok=True)
    (_traces() / f"{proposal_id}.json").write_text(json.dumps(kept, indent=1), encoding="utf-8")


def trace_summary(proposal_id: str, limit: int = 40) -> str:
    """Pure logic over the kept trace. A proposal's method in a few lines, for the retrospective: each attempt's
    steps in order, a run of the same tool on the same target said once with how many times; "" without a trace."""
    lines = []
    for a in trace(proposal_id):
        said: list[str] = []
        for s in a.get("steps", [])[:limit * 3]:
            step = f"{s.get('tool', '')} {s.get('target', '')}".strip()
            if said and said[-1].split(" x")[0] == step:
                count = int(said[-1].rsplit(" x", 1)[1]) + 1 if " x" in said[-1] else 2
                said[-1] = f"{step} x{count}"
            else:
                said.append(step)
        if said:
            lines.append(f"The coder's steps (lab {proposal_id}, {a.get('attempt', '')} try): "
                         + "; ".join(said[:limit]) + ("; ..." if len(said) > limit else ""))
    return "\n".join(lines)


def _suite_once(cwd: Path) -> dict:
    """Runs the whole test suite once in a folder (offscreen Qt, no cache, with a timeout) and reads its result."""
    out = subprocess.run([_python(), "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=str(cwd),
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=SUITE_TIMEOUT,
                         env={**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"},
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return suite_result((out.stdout or "") + "\n" + (out.stderr or ""))


def run_suite(cwd: Path, once: Callable[[Path], dict] = _suite_once) -> dict:
    """The full suite in that folder. A run that ends without pytest's summary (the rare native crash mid-suite,
    docs/WAITING_ON.md) is run once more, and says so, so a lesson or a merge is never judged on a crash."""
    result = once(cwd)
    if not result.get("finished"):
        result = once(cwd)
        result["summary"] = f"{result['summary']} (run twice: the first didn't finish)"
    return result


def _tests_once(cwd: Path, files: list[str]) -> dict:
    """Runs only the given test files once in a folder (offscreen Qt, no cache, with a timeout) and reads the result."""
    out = subprocess.run([_python(), "-m", "pytest", "-q", "-p", "no:cacheprovider", *files], cwd=str(cwd),
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=SUITE_TIMEOUT,
                         env={**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"},
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return suite_result((out.stdout or "") + "\n" + (out.stderr or ""))


def _before_the_change(p: Proposal, run: Callable[[Path, list], dict]) -> dict:
    """The change's own tests run against the code it started from (DEC-0224): a copy of the start with the lab's
    added and changed test files laid over it, removed afterwards. What fails there and passes in the lab shows
    the problem was real and is fixed. Only files pytest collects by itself (test_*.py) count, and the copy
    gets its own folder each time. {"failed": []} when the change touches no such file."""
    # Only files pytest collects by itself (test_*.py): one it wouldn't could fail before and after and still count.
    tests = [f for f in test_files(p.files) if Path(f).name.startswith("test_") and f.endswith(".py")]
    if not tests:
        return {"failed": []}
    # Its own folder each time: one Windows couldn't delete never blocks the next check.
    where = LAB_ROOT / f"_proof-{p.proposal_id}-{__import__('uuid').uuid4().hex[:6]}"
    _git("worktree", "add", "--detach", str(where), p.base)
    try:
        for name in test_files(p.files):
            _git("checkout", p.branch, "--", name, cwd=where)
        return run(where, tests)
    finally:
        _git("worktree", "remove", "--force", str(where), check=False)


def _passing(cwd: Path, tests: list[str]) -> set[str]:
    """Which of these test ids pytest reports as PASSED when their files are run in a folder (`-rp`). A test that
    was deleted, renamed, skipped or never collected is in no PASSED line, so it proves nothing."""
    files = sorted({t.split("::")[0] for t in tests})
    if not files:
        return set()
    out = subprocess.run([_python(), "-m", "pytest", "-q", "-rp", "-p", "no:cacheprovider", *files], cwd=str(cwd),
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=SUITE_TIMEOUT,
                         env={**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"},
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return set(_PASSED.findall((out.stdout or "") + "\n" + (out.stderr or ""))) & set(tests)


def check(proposal_id: str, suite: Optional[Callable] = None,
          proof: Optional[Callable[[Path, list], dict]] = None, require_proof: bool = True,
          passing: Optional[Callable[[Path, list], set]] = None) -> Proposal:
    """The rules (a protected file, counted by both names when renamed, or a deleted test file, refuses it), then
    the suite in the lab against the suite at the start: no new failure or error, and no fewer tests passing.
    Then the proof (DEC-0224: a fix comes with a test that fails before it): a test failing at the start that
    passes in the lab, or one of the change's own test files that fails on the starting code (`proof`, by default
    pytest on those files). Either way the test must then be seen to PASS in the lab (`passing`, by default
    pytest -rp on its file there): a test that only errored at import on the old code, or that was deleted,
    renamed or skipped, is in no PASSED line and proves nothing (Fable's review, 2026-11-20). With a stand-in
    `suite` and no `passing`, the stand-in's word is taken. A change to code with no such test isn't ready
    unless `require_proof` is off (her coder's graded practice, never merged); the proving tests are kept as
    `shown_by`, and its merge names them."""
    p = get(proposal_id)
    lab = folder(p)
    p.files = [f for f in _git("diff", "--name-only", "--no-renames", f"{p.base}...{p.branch}").splitlines() if f]
    p.refused = touches_protected(p.files)
    if p.refused:
        p.status, p.note = NOT_READY, "It changes files the lab may never change: " + ", ".join(p.refused)
        return _put(p)
    gone = removed_tests(_git("diff", "--name-status", "--no-renames", f"{p.base}...{p.branch}").splitlines())
    if gone:
        p.refused = gone
        p.status, p.note = NOT_READY, "It deletes tests, which a lab change may never do: " + ", ".join(gone)
        return _put(p)
    run = suite or run_suite
    lab_result = run(lab)
    base_dir = LAB_ROOT / f"_base-{p.base[:10]}"
    if not base_dir.exists():
        _git("worktree", "add", "--detach", str(base_dir), p.base)
    base_result = run(base_dir)
    before = _before_the_change(p, proof or _tests_once)
    fresh = new_failures(lab_result, base_result)
    p.tests = {"summary": lab_result["summary"], "base_summary": base_result["summary"], "new_failures": fresh,
               "fixed": sorted(set(base_result["failed"]) - set(lab_result["failed"])),
               "lab_failed": lab_result["failed"], "base_failed": base_result["failed"]}
    finished = lab_result.get("finished", True) and base_result.get("finished", True)
    had, has = passed_count(base_result.get("summary", "")), passed_count(lab_result.get("summary", ""))
    fewer = had is not None and has is not None and has < had  # tests taken out, however the files were changed
    # A named test function (file::test), not a file that errored at import nor "the suite had errors".
    failing_before = sorted(t for t in (set(p.tests["fixed"]) | set(before.get("failed", []))) if "::" in t)
    if passing is not None:
        passes = set(passing(lab, failing_before))
    elif suite is None:
        passes = _passing(lab, failing_before)
    else:  # a stand-in suite (tests): what it doesn't report failing counts as passing
        passes = set(failing_before) - set(lab_result["failed"])
    shown = sorted(set(failing_before) & passes)
    p.tests["shown_by"] = shown
    unproven = require_proof and needs_proof(p.files) and not shown
    p.status = READY if (not fresh and finished and not fewer and not unproven) else NOT_READY
    p.note = "" if p.status == READY else (
        "New failures: " + ", ".join(fresh) if fresh else
        f"Fewer tests pass than at the start ({has} against {had})." if fewer else
        "The suite didn't finish." if not finished else
        "No test shows the problem: a change to code needs a test that fails before it and passes after (DEC-0224).")
    return _put(p)


def merge_message(p: Proposal) -> str:
    """Pure logic. A lab merge's commit message: its title and id, then the tests that show it helped (LS-06)."""
    shown = (p.tests or {}).get("shown_by") or []
    out = f"From the lab: {p.title} ({p.proposal_id})"
    if shown:
        out += "\n\nShown by: " + ", ".join(shown[:10]) + (" and more" if len(shown) > 10 else "")
    return out


def approve(proposal_id: str, suite: Optional[Callable] = None) -> Proposal:
    """Zac's approval (or Claude's pass, core/self_merges.py): the protected list checked again as it is now, then
    merged into the running copy with a message naming the tests that show it helped (a merge that conflicts is aborted, never left half-way), the suite again, reverted by
    itself on a new failure. Refused while everything is stopped, or when it deletes tests. The proposal is recorded
    as in, with its commit, before the suite runs, so a crash from there on leaves it listed and undoable; a suite
    that can't run counts as one that didn't pass."""
    p = get(proposal_id)
    if p.status != READY:
        raise ValueError(f"Only a ready proposal can go in; this one is {p.status}.")
    from core import stop

    if stop.held_on_disk():  # "stop everything" holds a merge too, in whatever process asks (a night in flight)
        raise ValueError("Everything is stopped, so nothing goes in until he says carry on.")
    if removed_tests(_git("diff", "--name-status", "--no-renames", f"{p.base}...{p.branch}").splitlines()):
        raise ValueError("It deletes tests, which a lab change may never do.")
    # The protected list as it is now, not as it was when the proposal was checked; a rename counts by both names.
    files = [f for f in _git("diff", "--name-only", "--no-renames", f"{p.base}...{p.branch}").splitlines() if f]
    refused = touches_protected(files)
    if refused:
        raise ValueError("It changes files the lab may never change: " + ", ".join(refused))
    dirty = [ln[3:] for ln in _git("status", "--porcelain").splitlines()]
    if set(dirty) & set(p.files):
        raise ValueError("Files it changes have unsaved edits here: " + ", ".join(sorted(set(dirty) & set(p.files))))
    # The running copy as it is first: it can hold work in progress the lab
    # never saw (2026-11-03: Zac's uncommitted Plaid work failed a Plaid test,
    # and the merge was reverted for a failure that was already there).
    before = (suite or run_suite)(ROOT)
    _git("merge", "--no-ff", "--no-edit", p.branch, "-m", merge_message(p), author=OWNER, undo=("merge", "--abort"))
    p.merged_as = _git("rev-parse", "HEAD")
    # Kept before the suite runs: if this process dies or the suite times out from here on, the record already
    # says it's in, with its commit, so it's listed and can be undone (it used to stay "ready" with the merge in).
    p.status, p.note = MERGED, "In, with the suite still to pass here. Restart MIA to load it."
    _put(p)
    try:
        after = (suite or run_suite)(ROOT)  # the running copy
    except Exception as problem:  # noqa: BLE001 - a suite that couldn't run is a suite that didn't pass
        after = {"failed": [], "finished": False, "summary": f"the suite couldn't run: {str(problem)[:120]}"}
    known = set(before.get("failed", [])) | set(p.tests.get("lab_failed", []))
    fresh = new_failures(after, {"failed": sorted(known)})  # only what the merge added here
    if not after.get("finished", True):
        fresh = fresh or ["(the suite didn't finish)"]
    if fresh:
        _git("revert", "-m", "1", "--no-edit", "HEAD", author=OWNER, undo=("revert", "--abort"))
        p.status, p.note = REVERTED, "It broke here: " + ", ".join(fresh) + ". Reverted; the history keeps both."
    else:
        p.status, p.note = MERGED, "In. Restart MIA to load it."
    return _put(p)


def revert(proposal_id: str, why: str = "") -> Proposal:
    """Takes a merged proposal back out of the running copy (Zac's Undo on one of her own changes, DEC-0225): its merge
    commit is reverted, history kept, and it can be retried later; a revert that conflicts is aborted, so her code is
    never left with conflict markers. ValueError for one that isn't in, or whose files have unsaved edits here."""
    p = get(proposal_id)
    if p.status != MERGED or not p.merged_as:
        raise ValueError(f"Only a change that's in can be undone; this one is {p.status}.")
    dirty = [ln[3:] for ln in _git("status", "--porcelain").splitlines()]
    if set(dirty) & set(p.files):
        raise ValueError("Files it changed have unsaved edits here: " + ", ".join(sorted(set(dirty) & set(p.files))))
    _git("revert", "-m", "1", "--no-edit", p.merged_as, author=OWNER, undo=("revert", "--abort"))
    p.status, p.note = REVERTED, (why or "Undone by Zac.") + " Restart MIA to load it; the history keeps both."
    return _put(p)


def retry(proposal_id: str) -> Proposal:
    """A reverted proposal, again: git won't merge a branch whose merge was
    reverted (its commits count as merged), so its change is rebuilt as a new
    commit on a new branch from the running copy as it is now, ready for a
    fresh check."""
    p = get(proposal_id)
    if p.status != REVERTED:
        raise ValueError(f"Only a reverted proposal is retried; this one is {p.status}.")
    changed = [line.split("\t") for line in _git("diff", "--name-status", "--no-renames", f"{p.base}...{p.branch}").splitlines() if line]
    if not changed:
        raise ValueError("Its branch has no change to carry over.")
    lab = folder(p)
    base = _git("rev-parse", "HEAD")
    branch = f"{p.branch.split('-again-')[0]}-again-{datetime.now().strftime('%H%M%S')}"
    _git("checkout", "-q", "-b", branch, base, cwd=lab)
    # Each file as the branch had it, straight from git: no patch text, so line endings stay as they were.
    for state, path in changed:
        if state.startswith("D"):
            _git("rm", "-q", "--ignore-unmatch", "--", path, cwd=lab)
        else:
            _git("checkout", p.branch, "--", path, cwd=lab)
    _git("commit", "-m", f"lab: {p.title} (again, on {base[:10]})\n\n{p.problem}", cwd=lab, author=LAB_AUTHOR)
    p.branch, p.base, p.status, p.note, p.merged_as = branch, base, WRITTEN, "Rebuilt on the running copy, to check again.", ""
    return _put(p)


def reject(proposal_id: str, why: str = "") -> Proposal:
    """Rejects a proposal: removes its worktree and branch (cleanup failures only logged). One already merged can't be
    rejected; it's taken back with a revert.
    """
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
    """One proposal in a few plain sentences, with the tests that show it helped."""
    out = f"{p.title} ({p.status})."
    if p.files:
        out += f" Changes {len(p.files)} file{'s' if len(p.files) != 1 else ''}: {', '.join(p.files[:5])}."
    if p.tests:
        out += f" Lab suite: {p.tests.get('summary')}; at the start: {p.tests.get('base_summary')}."
        if p.tests.get("fixed"):
            out += f" It fixes {len(p.tests['fixed'])} failing test{'s' if len(p.tests['fixed']) != 1 else ''}."
        if p.tests.get("shown_by"):
            out += " Shown by: " + ", ".join(p.tests["shown_by"][:3]) + (" ..." if len(p.tests["shown_by"]) > 3 else "") + "."
    if p.note:
        out += " " + p.note
    return out
