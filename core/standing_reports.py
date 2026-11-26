"""
core.standing_reports
=======================

"Every Sunday tell me what's due this week" (the automation sweep, 2026-11-26: the model answered once and kept
nothing): a question he asks her to answer on a schedule, kept in his own folder and answered then, in code, from
his records, through the communication gate like any message of hers.

**What can be kept** (`parse`): a schedule (every day or morning, a weekday, every week, every month) and a
question, from his words, in code: "every Sunday tell me what's due this week", "every month tell me how much I
spent" (the month just gone), "tell me every Friday how my money looks". Only a question her own code answers
(`answer`: the read-only code answers of core/assistant_turn, never the model and never one that changes a record),
checked when it's kept, so a report never says "I don't know". A watch ("tell me every morning if it's going to
freeze") is core/condition_watch's.

**When** (`_period`): from REPORT_HOUR on its day (a weekday's on that day, a daily one every day, an evening one from
EVENING_HOUR), a weekly or monthly one on the first day the check runs in its week or month, once in its period;
TIMELY through the gate (held for an opening, never dropped or paused), ending with its day.

**The store** (`ReportList`, each person's own, standing_reports.json, sealed at rest and written through
atomic_write_text so "undo that" restores it): kept and stopped by the actions `standing_report.add` /
`standing_report.remove` (his own words: act_within_grant), by voice (keep_standing_report, list_standing_reports,
stop_standing_report) and the daily check `standing_reports` (`offer`). The Fable review (2026-11-26) found the
morning briefing's own sentence refused, a report dropped for its month, the only report stopped by any words.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "standing_reports.json"
REPORT_HOUR = 7
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
EVERY_WORDS = {"day": "daily", "morning": "daily", "night": "evening", "evening": "evening", "week": "weekly",
               "month": "monthly", **{d: d for d in DAYS}}
EVENING_HOUR = 18
CAN_KEEP = ("I can send on a schedule what I can answer from your records, like \"every Sunday tell me what's due "
            "this week\", \"every month tell me how much I spent\" or \"every Friday tell me how my money looks\".")


@dataclass
class Report:
    """One standing report: its id, when (daily, weekly, monthly or a weekday), the question asked then, his words,
    when it was kept and the period it was last sent in ("" for never)."""
    report_id: str
    every: str
    question: str
    words: str = ""
    created_at: str = ""
    sent: str = ""

    def to_dict(self) -> dict:
        """As saved."""
        return asdict(self)

    @staticmethod
    def from_dict(raw: dict) -> "Report":
        """From what was saved; unknown keys left out."""
        return Report(**{k: raw[k] for k in Report.__dataclass_fields__ if k in raw})


class ReportList:
    """A person's standing reports (standing_reports.json in their own folder). Each is known by what he said
    (`EPISTEMIC`, DEC-0173 G3)."""
    EPISTEMIC = {"record": Report, "source": "words", "at": "created_at", "how": "said"}

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads them from the person's folder (or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self.reports: list[Report] = []
        self._load()

    def _load(self) -> None:
        """Reads the file, sealed on disk (core/at_rest.open_text); missing or unreadable is none."""
        from core.at_rest import open_text

        try:
            raw = json.loads(open_text(self._file)) if self._file.exists() else {}
            raw = raw if isinstance(raw, dict) else {}
            self.reports = [Report.from_dict(d) for d in raw.get("reports", []) if isinstance(d, dict)]
        except (OSError, ValueError, TypeError) as problem:
            log.warning("Couldn't read the standing reports: %s", problem)
            self.reports = []

    def _save(self) -> None:
        """Writes it atomically (so "undo that" can restore it)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"reports": [r.to_dict() for r in self.reports]}, indent=1,
                                                 ensure_ascii=False))

    def add(self, report: Report) -> Report:
        """Keeps a new one."""
        self.reports.append(report)
        self._save()
        return report

    def remove(self, report_id: str) -> Report:
        """Stops one. KeyError for one that isn't there."""
        found = self.get(report_id)
        if found is None:
            raise KeyError(report_id)
        self.reports = [r for r in self.reports if r.report_id != report_id]
        self._save()
        return found

    def get(self, report_id: str) -> Optional[Report]:
        """One by its id."""
        return next((r for r in self.reports if r.report_id == report_id), None)

    def mark_sent(self, report_id: str, period: str) -> None:
        """Her bookkeeping: the period a report was sent in."""
        found = self.get(report_id)
        if found is not None:
            found.sent = period
            self._save()


def book(context) -> ReportList:
    """The person's standing reports: the context's, else one on the data folder."""
    found = getattr(context, "standing_reports", None) if context is not None else None
    return found if found is not None else ReportList(context)


# ------------------------------------------------------------------ his words

_EVERY = "|".join(EVERY_WORDS)
_KEEP = re.compile(r"^\s*(?:hey mia,? )?(?:please )?(?:(?:every|each) (?P<every1>" + _EVERY + r")s?,? "
                   r"(?:tell|give|send|show) me (?P<what1>.+?)|(?:tell|give|send|show) me (?:every|each) (?P<every3>" + _EVERY
                   + r")s?,? (?P<what3>.+?)|(?:tell|give|send|show) me (?P<what2>.+?) (?:every|each) "
                   r"(?P<every2>" + _EVERY + r")s?)\s*[.!?]*\s*$", re.I)
_LAST = {"monthly": "last month", "weekly": "last week", "daily": "yesterday", "evening": "today"}


def _question(what: str, every: str) -> str:
    """Pure logic. His words as the question asked then ("how much I spent": a month's report the month just gone,
    a weekday's the week it ends, a daily one yesterday, an evening one today); one said indirectly asked directly
    ("what my week looks like": "What does my week look like?"); a daily one of what's due, or one asking today's, is today's ("What's
    due today?")."""
    what = what.strip().rstrip("?.! ")
    spent = re.fullmatch(r"how much (?:i|we) (?:spent|spend|have spent)", what, re.I)
    if spent:  # a weekday's report reads the week it ends ("this week"), a month's the month just gone
        return f"How much did I spend {_LAST.get(every, 'this week')}?"
    looks = re.fullmatch(r"how (?:my|our) money (?:looks|is looking|is doing)", what, re.I)
    if looks:
        return "How's my money this week?"
    # said indirectly ("what my week looks like", "what I did yesterday", "what reminders I have"): asked directly
    week = re.fullmatch(r"what (?:my|the) week (?:looks|is going to look|will look) like", what, re.I)
    if week:
        return "What does my week look like?"
    did = re.fullmatch(r"what (?:i|we) did (yesterday|today|this week)", what, re.I)
    if did:
        return f"What did I do {did.group(1)}?"
    have = re.fullmatch(r"what (reminders|alarms) (?:i|we) have", what, re.I)
    if have:
        return f"What {have.group(1)} do I have?"
    due = re.fullmatch(r"what(?:'s| is) due(?P<when> today| this week| this month)?|what i owe", what, re.I)
    if due:  # a daily one is today's (the automation conversation check: "every morning tell me what's due today")
        when = (due.groupdict().get("when") or "").strip().lower()
        if when == "today" or (every in ("daily", "evening") and not when):
            return "What's due today?"
        return "What's due this week?" if every != "monthly" else "What's due this month?"
    return what[:1].upper() + what[1:] + "?"


def parse(words: str) -> Optional[dict]:
    """Pure logic. {every, question} from his words, the schedule before or after what to tell ("every Friday tell me
    ...", "tell me every Friday ...", "tell me ... every Friday"), or None (a watch, "if ...", is the condition
    watch's); a leading "and" or "also" left off ("and every Sunday tell me ...")."""
    said = re.sub(r"^\s*(?:and|also|then|oh,? and)\s+", "", " ".join((words or "").split()), flags=re.I)
    found = _KEEP.match(said)  # "and every Sunday tell me ...": the second report of a conversation, too
    if not found:
        return None
    what = found.group("what1") or found.group("what2") or found.group("what3")
    if re.match(r"\s*(?:if|when|whenever)\b", what, re.I):
        return None  # "tell me every morning if it's going to freeze": a watch
    every = EVERY_WORDS[(found.group("every1") or found.group("every2") or found.group("every3")).lower()]
    return {"every": every, "question": _question(what, every)}


def answer(context, question: str) -> Optional[str]:
    """The question answered by her own read-only code answers (never the model, never a change), or None."""
    if not re.match(r"\s*(?:what|how|who|which|when|where|did|do|does|is|are|am|have)\b", question or "", re.I):
        return None
    from core import assistant_turn

    for route in (assistant_turn._records_reply, assistant_turn._own_tool_reply, assistant_turn._everyday_reply):
        try:
            found = route(context, question)
        except Exception:  # noqa: BLE001 - one that fails is skipped
            log.exception("Standing report: %s failed", getattr(route, "__name__", route))
            found = None
        if found:
            return found
    return None


def describe(report: Report) -> str:
    """Pure logic. A report in words: 'every Sunday: "What's due this week?"', 'every evening: ...'."""
    when = {"daily": "every morning", "evening": "every evening", "weekly": "every week",
            "monthly": "every month"}.get(
        report.every, f"every {report.every.capitalize()}")
    return f"{when}: \"{report.question}\""


# ------------------------------------------------------------------ sending

def _period(report: Report, today: date) -> str:
    """The period a report is sent once in, by its schedule: the day, the ISO week or the month (a weekly or monthly
    one any day of it, so a PC off on its first day still gets it); "" when today isn't a weekday report's day."""
    if report.every in ("daily", "evening"):
        return today.isoformat()
    if report.every == "monthly":  # the first day it runs in the month (a PC off on the 1st still gets it)
        return today.strftime("%Y-%m")
    if report.every == "weekly":
        year, week, _ = today.isocalendar()
        return f"{year}-W{week:02d}"
    if report.every in DAYS:
        return today.isoformat() if DAYS[today.weekday()] == report.every else ""
    return ""


def offer(context, now: datetime) -> list:
    """The daily check: each report whose day it is, from REPORT_HOUR (an evening one from EVENING_HOUR), once in its
    period, answered in code and offered through the gate, TIMELY (held for an opening, never dropped), ending with
    its day."""
    from datetime import timedelta

    from core.communication_gate import TIMELY, Candidate

    if now.hour < REPORT_HOUR:
        return []
    reports = book(context)
    out = []
    for report in list(reports.reports):
        if report.every == "evening" and now.hour < EVENING_HOUR:
            continue
        period = _period(report, now.date())
        if not period or report.sent == period:
            continue
        said = answer(context, report.question)
        if not said:
            continue
        # TIMELY: he asked for it, so it waits for an opening rather than being dropped (never paused either:
        # core/communication_gate.NEVER_PAUSED), and ends with its day
        ends = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        out.append(Candidate(topic="standing_report", title=report.question, message=said, urgency=TIMELY,
                             source="system", fingerprint=f"report-{report.report_id}-{period}",
                             expires=ends.isoformat(timespec="seconds")))
        reports.mark_sent(report.report_id, period)
    return out


# ------------------------------------------------------------------ actions and tools

def _made(context, params) -> Report:
    """The report the action would keep, from his words; ActionError when it can't be kept."""
    words = str(params.get("words") or "").strip()
    found = parse(words)
    if found is None:
        raise ActionError("I couldn't tell what to send or when. " + CAN_KEEP)
    if answer(context, found["question"]) is None:
        raise ActionError(f"I can't answer \"{found['question']}\" from your records in code, so I won't put it on a "
                          f"schedule. " + CAN_KEEP)
    return Report(report_id=str(params.get("report_id") or uuid.uuid4().hex[:8]), every=found["every"],
                  question=found["question"], words=words[:200], created_at=datetime.now().isoformat(timespec="seconds"))


def _name(report: Report) -> str:
    """Pure logic. A report's short name for stopping it: "monthly", "Sunday"."""
    return report.every.capitalize() if report.every in DAYS else report.every


def _add_describe(context, params) -> str:
    """What standing_report.add says."""
    report = _made(context, params)
    return f"Send you {describe(report)}"


def _add_execute(context, params) -> str:
    """Does standing_report.add."""
    report = book(context).add(_made(context, params))
    return f"I'll send you {describe(report)}. Say \"stop the {_name(report)} report\" to stop it."


def _remove_describe(context, params) -> str:
    """What standing_report.remove says."""
    report = book(context).get(str(params.get("report_id") or ""))
    if report is None:
        raise ActionError("That isn't one of your standing reports.")
    return f"Stop sending {describe(report)}"


def _remove_execute(context, params) -> str:
    """Does standing_report.remove."""
    report = book(context).remove(str(params.get("report_id") or ""))
    return f"Stopped: no more {describe(report)}."


ACTIONS = {a.kind: a for a in (
    ActionType("standing_report.add", "Send This On A Schedule", {"words": "what to send and when, in his words"},
               _add_describe, _add_execute),
    ActionType("standing_report.remove", "Stop This Report", {"report_id": "one of his reports"},
               _remove_describe, _remove_execute),
)}
ACTION_TYPES.update(ACTIONS)


def _keep_tool(context, arguments: dict) -> str:
    """Tool keep_standing_report: keeps a report from his words."""
    from core.actions import run_as_tool

    return run_as_tool(context, "standing_report.add", {"words": str(arguments.get("question") or "")})


def _list_tool(context, arguments: dict) -> str:
    """Tool list_standing_reports: what she sends him on a schedule."""
    reports = book(context).reports
    if not reports:
        return "I'm not sending you anything on a schedule. " + CAN_KEEP
    return "On a schedule I send you: " + "; ".join(describe(r) for r in reports) + "."


def _stop_tool(context, arguments: dict) -> str:
    """Tool stop_standing_report: stops the one his words name (every word in its question or schedule: "the Sunday
    report", "the Sunday one", "the morning one" for the daily one), or the only one when he names none; other words that fit none are asked about, never a
    stop."""
    from core.actions import run_as_tool

    reports = book(context).reports
    if not reports:
        return "I'm not sending you anything on a schedule."
    words = {w for w in re.findall(r"[a-z]+", str(arguments.get("question") or "").lower()) if len(w) > 2} - {
        "stop", "the", "report", "reports", "sending", "send", "me", "that", "every", "about", "one", "cancel", "drop",
        "turn", "off", "update", "updates", "you", "my", "ones", "please", "okay", "hey", "mia"}
    # "stop the Sunday one" names the Sunday report (the conversation check); "the morning one" the daily one she
    # says as "every morning" (the Fable review)
    words = {"daily" if w == "morning" else w for w in words}
    named = [r for r in reports if words and words <= set(re.findall(r"[a-z]+", r.question.lower())) | {r.every}]
    chosen = named[0] if len(named) == 1 else (reports[0] if len(reports) == 1 and not words else None)
    if chosen is None:
        return "Which one? " + "; ".join(describe(r) for r in reports) + "."
    return run_as_tool(context, "standing_report.remove", {"report_id": chosen.report_id})


def register_standing_report_actions(registry) -> None:
    """Registers keep_standing_report, list_standing_reports and stop_standing_report."""
    from core.assistant_actions import AssistantAction

    question = {"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                "required": []}
    registry.register(AssistantAction(
        name="keep_standing_report", domain="today",
        description="Answer one of his questions on a schedule (every Sunday, every month...) from his records and "
                    "send it to him, like \"every Sunday tell me what's due this week\".",
        parameters=question, handler=_keep_tool, prompt_arg="question",
        trigger_phrases=("every sunday tell me", "every monday tell me", "every month tell me", "every week tell me",
                         "every morning tell me", "every day tell me"),
        subjects=("report", "schedule"),
    ))
    registry.register(AssistantAction(
        name="list_standing_reports", domain="today",
        description="What she sends him on a schedule.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_list_tool,
        trigger_phrases=("what do you send me", "my standing reports", "what reports do i get"),
        subjects=("report", "schedule"),
    ))
    registry.register(AssistantAction(
        name="stop_standing_report", domain="today",
        description="Stop one of the reports she sends him on a schedule.",
        parameters=question, handler=_stop_tool, prompt_arg="question",
        trigger_phrases=("stop the report", "stop sending me", "stop the weekly report", "stop the monthly report"),
        subjects=("report", "schedule"),
    ))
