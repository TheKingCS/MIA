"""
core.lab_push
===============

Her merged changes pushed with the daily summary (WP-12, Q-100, DEC-0264: "her merged changes are pushed with the
daily summary, so CI tests them"). The changes MIA makes to herself go into the running copy on Claude's pass
(core/self_merges.py) and were kept on the PC; now, once a day after the summary, they're pushed to GitHub, where CI
runs the whole suite on Linux and inside the image.

**Only hers, never anything else** (`hers`): every commit waiting to go must be the lab's: written by MIA Lab, a merge
of one ("From the lab: ..."), or the Undo of one (a revert of such a merge). A commit that isn't, anyone else's work
in the running copy, holds the push for its owner to make; nothing is ever pushed past it.

**Never forced** (`push`): only from the master branch, only when GitHub has nothing newer (else it waits until the
copy is up to date: never a rebase or a force here), and the commits are sent as they are. The repository is public,
so the lab's protected list already keeps her away from anything that isn't code (core/dev_lab.PROTECTED, data/ and
work/ among them). Nothing is fetched or pushed when nothing is waiting, so a day with no merge costs no network.

The outcome is kept in the config (`lab.pushed`: when, how many, or why not) for Diagnostics. This file is on the
lab's protected list: she can't change what may be pushed.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
LAB_NAME = "MIA Lab"  # core/dev_lab.LAB_AUTHOR
MERGE_SUBJECT = "From the lab: "  # core/dev_lab.merge_message
REVERT_SUBJECT = 'Revert "From the lab: '  # git's subject for the Undo of a lab merge (core/dev_lab.revert)


def _git(*args: str) -> tuple[int, str]:
    """Runs git in the running copy: (exit code, output). Never raises; a git that can't run is code 1."""
    try:
        out = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as problem:
        return 1, str(problem)
    return out.returncode, (out.stdout or out.stderr or "").strip()


def hers(author: str, subject: str, parents: int = 1) -> bool:
    """Pure logic. Whether a commit is the lab's: by MIA Lab, a merge (two parents) of one of hers, or the Undo of
    such a merge; a single-parent commit merely titled like a merge isn't."""
    return (author == LAB_NAME or (parents >= 2 and subject.startswith(MERGE_SUBJECT))
            or subject.startswith(REVERT_SUBJECT))


def waiting(git: Callable = _git) -> list[tuple[str, str, str]]:
    """The commits in the running copy that GitHub doesn't have yet (as far as this copy last knew), oldest first:
    (hash, author, subject, how many parents). None are asked of the network."""
    code, out = git("log", "--reverse", "--format=%H%x09%an%x09%P%x09%s", "origin/master..HEAD")
    if code != 0 or not out:
        return []
    rows = [line.split("\t", 3) for line in out.splitlines() if line.count("\t") >= 3]
    return [(sha, author, subject, len(parents.split())) for sha, author, parents, subject in rows]


def push(git: Callable = _git) -> dict:
    """Pushes her waiting merges to GitHub: {"pushed": n}, {"pushed": 0} when nothing waits, or {"held": why} when a
    commit isn't hers (a merge of hers needs its two parents), this isn't master, or GitHub has something newer;
    {"error": why} when the push fails. Pushes exactly the newest commit it checked (its hash, to master), so one
    made meanwhile is never carried along. Never forced, never rebased."""
    code, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or branch != "master":
        return {"held": "the running copy isn't on master"} if code == 0 else {"error": branch[:200]}
    commits = waiting(git)
    if not commits:
        return {"pushed": 0}
    others = [c for c in commits if not hers(c[1], c[2], c[3])]
    if others:
        return {"held": f"{len(others)} waiting commit{'s' if len(others) != 1 else ''} not hers "
                        f"(the first: {others[0][2][:80]}): that's for its owner to push"}
    code, out = git("fetch", "-q", "origin", "master")
    if code != 0:
        return {"error": f"couldn't reach GitHub: {out[:200]}"}
    code, newer = git("rev-list", "--count", "HEAD..origin/master")
    if code != 0 or (newer.isdigit() and int(newer) > 0):
        return {"held": "GitHub has newer commits: they're pushed once the running copy has those"}
    commits = waiting(git)
    if not commits or any(not hers(c[1], c[2], c[3]) for c in commits):
        return {"held": "a waiting commit isn't hers"}
    code, out = git("push", "-q", "origin", f"{commits[-1][0]}:refs/heads/master")  # exactly what was checked
    if code != 0:
        return {"error": f"the push failed: {out[:200]}"}
    log.info("Pushed %d of MIA's own commits to GitHub.", len(commits))
    return {"pushed": len(commits)}


def run(context, now: Optional[datetime] = None, git: Callable = _git) -> dict:
    """With the daily summary: `push`, the outcome kept in `lab.pushed` (with when) when something was tried. Never
    raises. Under the test suite the real git is never used (the suite runs in his own copy: a test that ran the
    day's checks must never push); tests pass their own."""
    import os

    if git is _git and os.environ.get("PYTEST_CURRENT_TEST"):
        return {"pushed": 0}
    try:
        result = push(git)
    except Exception as problem:  # noqa: BLE001 - never in the way of the day's checks
        log.exception("Pushing her merges failed")
        result = {"error": str(problem)[:200]}
    if result != {"pushed": 0}:
        config = getattr(context, "config", None)
        if config is not None:
            config.set("lab.pushed", {"at": (now or datetime.now()).isoformat(timespec="seconds"), **result})
            config.save()
    return result
