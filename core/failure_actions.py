"""
core.failure_actions
======================

The Fix-It Log's actions (DEC-0049, core/failure_log.py) on the action
contract, and its screen (served as /api/failures).

- `failures.report`: report a problem in your own words.
- `failures.thumbs`: a 👎 on one of MIA's replies (and what was wrong).
- `failures.status`: an issue fixed, ignored, or open again.
- `failures.forget`: forget a phrasing MIA learned ("when I say X I mean Y").
"""

from __future__ import annotations

from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

STATUS_SAID = {"fixed": "Mark fixed", "ignored": "Ignore", "open": "Open again"}


def _book(context):
    return _need(context, "failures")


def _report_describe(context, params) -> str:
    note = str(params.get("note") or "").strip()
    if not note:
        raise ActionError("What went wrong?")
    return f"Report a problem: {note[:120]}"


def _report_execute(context, params) -> str:
    _book(context).record("report", note=str(params.get("note") or ""), page=str(params.get("page") or ""))
    return "Logged, so it gets fixed."


def _thumbs_describe(context, params) -> str:
    if not str(params.get("reply") or "").strip():
        raise ActionError("Which reply?")
    return "That answer wasn't right" + (f": {str(params.get('note'))[:100]}" if params.get("note") else "")


def _thumbs_execute(context, params) -> str:
    _book(context).record("thumbs_down", prompt=str(params.get("prompt") or ""), reply=str(params.get("reply") or ""),
                          note=str(params.get("note") or ""))
    return "Thanks: logged, so it gets fixed."


def _issue(context, params):
    key = str(params.get("key") or "")
    found = next((i for i in _book(context).issues(90) if i["key"] == key), None)
    if found is None:
        raise ActionError("That issue isn't in the log anymore.")
    status = str(params.get("status") or "")
    if status not in STATUS_SAID:
        raise ActionError("Fixed, ignored, or open again?")
    return found, status


def _status_describe(context, params) -> str:
    issue, status = _issue(context, params)
    return f"{STATUS_SAID[status]}: {issue['title']}" + (
        " (if it happens again, it opens again by itself)" if status == "fixed" else "")


def _status_execute(context, params) -> str:
    issue, status = _issue(context, params)
    _book(context).set_status(issue["key"], status)
    return "Done."


def _phrase(context, params) -> dict:
    found = next((p for p in _book(context).phrases if p["phrase_id"] == str(params.get("phrase_id") or "")), None)
    if found is None:
        raise ActionError("That isn't remembered anymore.")
    return found


def _forget_describe(context, params) -> str:
    return f"Forget that “{_phrase(context, params)['said']}” means something special"


def _forget_execute(context, params) -> str:
    _book(context).forget(_phrase(context, params)["phrase_id"])
    return "Forgotten."


def _register() -> None:
    for kind in (
        ActionType("failures.report", "Report A Problem", {"note": "what went wrong", "page": "where"},
                   _report_describe, _report_execute, True),
        ActionType("failures.thumbs", "Not Right", {"prompt": "what was asked", "reply": "her answer", "note": "what was wrong"},
                   _thumbs_describe, _thumbs_execute, True),
        ActionType("failures.status", "Issue", {"key": "the issue", "status": "fixed, ignored or open"},
                   _status_describe, _status_execute),
        ActionType("failures.forget", "Forget", {"phrase_id": "the phrasing"}, _forget_describe, _forget_execute, True),
    ):
        ACTION_TYPES[kind.kind] = kind


_register()


def failures_page(context, days: int = 30) -> dict:
    from datetime import datetime, timedelta, timezone

    from core.failure_log import fix_report

    book = getattr(context, "failures", None)
    if book is None:
        return {"available": False}
    issues = book.issues(days)
    week = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [e for e in book.events(7)]
    open_ = [i for i in issues if i["status"] == "open"]
    registry = getattr(context, "assistant_actions", None)
    described = {a.name: a.description for a in getattr(registry, "_actions", {}).values()}
    return {
        "available": True, "days": days,
        "summary": {"open": len(open_), "this_week": len(recent), "fixed": sum(1 for i in issues if i["status"] == "fixed"),
                    "learned": len(book.phrases)},
        "issues": issues,
        "phrases": [{**p, "does": described.get(p["tool"], p["tool"])} for p in book.phrases],
        "report": fix_report(context, days) if open_ or book.phrases else "",
        "since": week.date().isoformat(),
    }


def page_error(context, page: str, message: str) -> Optional[dict]:
    """A page that broke (web/shell.js reports its own errors)."""
    book = getattr(context, "failures", None)
    if book is None:
        return None
    return book.record("page_error", page=str(page or "")[:80], error=str(message or "")[:200])


# ---------------------------------------------------------------- by voice


def _get_issues(context, arguments: dict) -> str:
    page = failures_page(context, 14)
    if not page.get("available"):
        return "The Fix-It Log isn't set up on this MIA."
    open_ = [i for i in page["issues"] if i["status"] == "open"]
    if not open_:
        return "Nothing's gone wrong that I know of in the last two weeks. If something did, say “report a problem” and what happened."
    said = [f"{len(open_)} open issue{'s' if len(open_) != 1 else ''} in the last two weeks."]
    for i in open_[:3]:
        said.append(f"{i['title']} ({i['count']}×).")
    if page["phrases"]:
        said.append(f"I've learned {len(page['phrases'])} of your phrasings.")
    return " ".join(said) + " The details are in Apps → Fix-It Log, ready for Claude."


def register_failure_actions(registry) -> None:
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="get_issues", domain="issues",
        description="The Fix-It Log: where MIA has stumbled lately (errors, wrong answers, reports), worst first.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_get_issues,
        trigger_phrases=("what's been going wrong", "whats been going wrong", "what went wrong", "fix-it log",
                         "fix it log", "your issues", "where have you messed up", "what problems have you had"),
        subjects=("issue", "problem", "wrong"),
    ))
