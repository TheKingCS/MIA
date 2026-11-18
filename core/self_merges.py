"""
core.self_merges
==================

MIA's own changes going in on Claude's pass, and the daily summary that tells Zac (DEC-0225; Zac, 2026-11-17, Q-76:
yes to "her own fixes merge on Claude's pass when the suite passes, with a daily summary and an Undo each, rather than
approving each").

**What's eligible** (`candidates`): a lab proposal Night School kept (her exercise passed its own test and the full
suite with no new failure, and her teacher marked it real progress: `evidence == SOURCE`), status ready, touching no
protected file (core/dev_lab.py refuses those before they're ever tested), and not reviewed yet on its current branch.

**The review** (`review_and_merge`): code gives the reviewer the task, the lab's test results and the diff, and asks
for a verdict in JSON. Only Claude's pass merges: a reply from any other reviewer, one that can't be read, or anything
but "pass" holds it in the lab for Zac, as before. A pass goes through the lab's own `approve`, which runs the suite on
the running copy before and after and reverts by itself on a new failure. Every verdict and outcome is kept
(`data/lab/self_merges.json`, this device only).

**The summary** (`offer`): once a day, for the PC's owner, the changes that went in since the last summary, through
the communication gate, each with its reason and how to undo it. **Undo** is the action `lab.revert`
(core/lab_actions.py), on Diagnostics' "Changes I Made To Myself" or by voice (`undo_my_change`): the lab reverts the
merge commit, history kept.

Night School runs one review a night (`core/night_school.py`). This file is on the lab's protected list.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

RECORD = DATA_DIR / "lab" / "self_merges.json"
SOURCE = "Night School exercise"  # the evidence Night School gives the proposals it creates
TOPIC = "self_changes"
MERGER = "claude-code"  # only this reviewer's pass merges (Q-76: "Claude's pass")
PASS, HOLD = "pass", "hold"
MAX_DIFF = 30_000

_ASK = """You are reviewing a change MIA made to her own code, before it goes into the running MIA (DEC-0225). You only
read; you change nothing. It already passed its own new test and the full suite with no new failure; a protected file
can't be in it. Look for real problems: a bug, a test that doesn't test what it says, something that weakens a safety
rule, privacy (personal data in code or tests: the repository is public), a docstring that no longer says what its code
does, or a change that does more than its task. Don't comment on style.

The task: {title}
{problem}

The lab's tests: {tests}

The diff:
{diff}

Reply with only a JSON object:
{{"verdict": "pass" or "hold", "findings": ["one short sentence each"], "why": "one sentence Zac will read about what it
changes"}}"""


def load(path: Optional[Path] = None) -> list[dict]:
    """Every review kept, oldest first; a missing or unreadable record is none."""
    try:
        data = json.loads(Path(path or RECORD).read_text(encoding="utf-8"))
        return [e for e in data.get("entries", []) if isinstance(e, dict)]
    except (OSError, ValueError, AttributeError):
        return []


def _save(entries: list[dict], path: Optional[Path] = None) -> None:
    """Writes the record atomically (its last 500 entries)."""
    from core.atomic_write import atomic_write_text

    path = Path(path or RECORD)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps({"about": "MIA's own changes reviewed by Claude (core/self_merges.py)",
                                        "entries": entries[-500:]}, indent=1, ensure_ascii=False) + "\n")


def _key(p) -> str:
    """What a review is about: the proposal and the branch it was on (a retry is a new branch, so a new review)."""
    return f"{p.proposal_id}:{p.branch}"


def candidates(proposals: Optional[list] = None, entries: Optional[list] = None, kept: Optional[set] = None) -> list:
    """The ready proposals Night School itself made (`kept`, by default its own list) that haven't been reviewed on
    their current branch, oldest first."""
    from core import dev_lab

    proposals = dev_lab.all_proposals() if proposals is None else proposals
    seen = {e.get("key") for e in (load() if entries is None else entries)}
    own = night_schools_own() if kept is None else set(kept)
    return [p for p in proposals if getattr(p, "status", "") == dev_lab.READY and getattr(p, "evidence", "") == SOURCE
            and p.proposal_id in own and not getattr(p, "refused", None) and _key(p) not in seen]


def night_schools_own() -> set:
    """The proposal ids Night School itself made (it keeps the list in its own protected records). The proposal's
    evidence text alone isn't enough: anyone who proposes a lab change writes that text."""
    from core.night_school import own_proposals

    return own_proposals()


def prompt(p, diff: str) -> str:
    """Pure logic. What the reviewer is asked (see `_ASK`), with the tests that fail before the change and pass
    after it (LS-06)."""
    tests = p.tests or {}
    said = f"{tests.get('summary', '')}; at the start: {tests.get('base_summary', '')}"
    if tests.get("shown_by"):
        said += "; fails before and passes after: " + ", ".join(tests["shown_by"][:10])
    if len(diff) > MAX_DIFF:
        diff = diff[:MAX_DIFF] + "\n(the rest was cut)"
    return _ASK.format(title=p.title, problem=p.problem[:3000], tests=said, diff=diff or "(no change)")


def verdict_from(reply: str, reviewer: str, ready: bool) -> tuple[str, list[str], str]:
    """Pure logic. The verdict code accepts: (pass or hold, findings, why). Only Claude's readable pass on a proposal
    still ready is a pass; anything else holds it for Zac."""
    from core.night_school import _json_in

    try:
        data = _json_in(reply or "")
    except Exception:  # noqa: BLE001 - an unreadable reply holds it
        data = {}
    said = str(data.get("verdict", "")).strip().lower()
    findings = [str(f)[:300] for f in (data.get("findings") or []) if str(f).strip()][:10]
    why = str(data.get("why") or "")[:300]
    if said not in (PASS, HOLD):
        return HOLD, ["the review couldn't be read as a verdict"] + findings, why
    if said == PASS and reviewer != MERGER:
        return HOLD, [f"only Claude's pass merges; {reviewer} reviewed it"] + findings, why
    if said == PASS and not ready:
        return HOLD, ["it isn't ready any more"] + findings, why
    return said, findings, why


def review_and_merge(ask: Callable[[str], str], reviewer: str, lab=None, diff: Optional[Callable] = None,
                     limit: int = 1, now: Optional[datetime] = None, path: Optional[Path] = None) -> list[dict]:
    """Reviews up to `limit` candidates and merges each one Claude passes, through the lab's own approve (which reverts
    by itself on a new failure). A change too large to show the reviewer whole is held without asking. A merge that
    went in but couldn't be checked afterwards is recorded as merged, so it's summarized and can be undone. Returns
    the entries kept."""
    if lab is None:
        from core import dev_lab as lab
    if diff is None:
        from core.work_review import lab_diff as diff
    entries = load(path)
    done = []
    if not hasattr(lab, "all_proposals"):  # a stand-in lab with no proposals of its own (tests)
        return []
    for p in candidates(lab.all_proposals(), entries)[:limit]:
        entry = {"key": _key(p), "proposal": p.proposal_id, "title": p.title, "reviewer": reviewer,
                 "at": (now or datetime.now()).isoformat(timespec="seconds"), "status": "held", "merged_as": "",
                 "summarized": ""}
        try:
            whole = diff(p.proposal_id)
            cut = len(whole) > MAX_DIFF  # a reviewer who saw part of a change can't pass the rest of it
            reply = "" if cut else ask(prompt(p, whole))
        except Exception as problem:  # noqa: BLE001 - a review that didn't come back holds it
            reply, cut = "", False
            entry["error"] = str(problem)[:200]
        verdict, findings, why = verdict_from(reply, reviewer, p.status == lab.READY)
        if cut:
            verdict, findings = HOLD, [f"the change is too large to review whole ({len(whole):,} characters), so it waits for Zac"]
        entry.update(verdict=verdict, findings=findings, why=why or p.title)
        if verdict == PASS:
            try:
                q = lab.approve(p.proposal_id)
                entry["status"] = "merged" if q.status == lab.MERGED else "reverted"
                entry["merged_as"] = q.merged_as
                entry["note"] = q.note[:300]
            except Exception as problem:  # noqa: BLE001 - a merge that couldn't happen stays in the lab
                entry["status"], entry["note"] = "held", f"it couldn't go in: {str(problem)[:200]}"
                try:  # the merge may be in all the same (the suite or the revert failed after it): say so, so it's
                    q = lab.get(p.proposal_id)  # listed in the summary and can be undone
                    if q.status == lab.MERGED and q.merged_as:
                        entry["status"], entry["merged_as"] = "merged", q.merged_as
                        entry["note"] = f"it went in, but checking it afterwards failed: {str(problem)[:160]}"
                except Exception:  # noqa: BLE001 - the record as read above stands
                    pass
        entries.append(entry)
        done.append(entry)
    if done:
        _save(entries, path)
    return done


def recent(days: int = 14, now: Optional[datetime] = None, path: Optional[Path] = None) -> list[dict]:
    """The changes that went in (or were undone) in the last `days`, newest first, for Diagnostics:
    [{proposal, title, why, at, status, merged_as, findings}]."""
    since = ((now or datetime.now()) - timedelta(days=days)).isoformat(timespec="seconds")
    shown = ("proposal", "title", "why", "at", "status", "merged_as", "findings")
    return [{k: e.get(k, "") for k in shown} for e in reversed(load(path))
            if e.get("status") in ("merged", "undone") and e.get("at", "") >= since]


def mark_undone(proposal_id: str, path: Optional[Path] = None) -> None:
    """Records that Zac undid one of her changes (the lab already reverted it)."""
    entries = load(path)
    for e in entries:
        if e.get("proposal") == proposal_id and e.get("status") == "merged":
            e["status"] = "undone"
    _save(entries, path)


def summary(entries: list[dict]) -> str:
    """Pure logic. The daily summary's words for these merged changes."""
    lines = [f"{len(entries)} change{'s' if len(entries) != 1 else ''} I made to myself went in on Claude's pass:"]
    for e in entries:
        lines.append(f"- {e.get('why') or e.get('title')} ({e.get('proposal')})")
    lines.append("Each passed its own test and the full suite. Undo any of them in Diagnostics, or say "
                 "\"undo my change\" and its number. They load the next time MIA restarts.")
    return "\n".join(lines)


def offer(context, now: Optional[datetime] = None, path: Optional[Path] = None) -> list:
    """For the PC's owner, once a day: the changes that went in since the last summary, as one timely Candidate for
    the gate (held for an opening, never dropped); they're marked summarized when offered."""
    from core.communication_gate import TIMELY, Candidate
    from core.person_settings import person_id
    from core.self_report import _owner

    now = now or datetime.now()
    if person_id(context) != _owner(context):
        return []
    entries = load(path)
    fresh = [e for e in entries if e.get("status") == "merged" and not e.get("summarized")]
    if not fresh:
        return []
    for e in fresh:
        e["summarized"] = now.date().isoformat()
    _save(entries, path)
    # TIMELY: held for an opening, never dropped like a nice-to-know (Zac's yes to Q-76 rests on this summary).
    return [Candidate(topic=TOPIC, title="What I changed in myself", message=summary(fresh), source="lab",
                      urgency=TIMELY, fingerprint=f"{TOPIC}:{now.date().isoformat()}")]


def said(days: int = 7) -> str:
    """Her recent changes to herself in words, for voice."""
    found = recent(days)
    if not found:
        return f"I haven't changed anything in myself in the last {days} days."
    parts = [f"{e['why'] or e['title']} ({e['proposal']}{', undone' if e['status'] == 'undone' else ''})"
             for e in found]
    return f"In the last {days} days I changed: " + "; ".join(parts) + "."
