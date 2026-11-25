"""
core.project_time
===================

The hours he puts into his projects (the live sweep, 2026-11-25: "log 2 hours on the shed build" had been taken as a
maintenance reading on an asset). "Log 2 hours on the shed" adds them to that project's time log
(core/project_manager.ProjectManager.log_time), undoable like any change of hers; "how many hours have I put into the
shed?" and "what did I work on this week?" are read back from those logs, in code.

How: `project_named(context, words)` finds his project by its name's words, whole ("the shed build" is the Shed
Build, "the shed" too when only one project has that word); `hours_said(words)` reads "2 hours", "an hour", "half an
hour", "90 minutes" or "2.5 hrs". `totals(context, start, end)` sums each project's hours in a range. Nothing is
guessed: an unknown project is said with the names he has, and no hours said asks for them.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

_SKIP = {"the", "my", "our", "a", "an", "on", "build", "project", "job"}


def _words(text: str) -> set:
    """Its words, lowercased, a plural as its one, the filler ("the", "build", "project") left out."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", str(text or "").lower()):
        if w in _SKIP:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def project_named(context, words: str, whole: bool = False):
    """His project his words name: one whose name holds all his words (and he left out at most one of its), only
    one; with `whole`, every word of its name and no other ("I spent 2 hours on the garden" is never the Garden
    Fence: the Fable review, 2026-11-25). None otherwise."""
    book = getattr(context, "projects", None)
    said = _words(words)
    if book is None or not said:
        return None
    projects = book.all_projects()
    exact = [p for p in projects if p.name.lower().strip() == str(words).lower().strip()]
    if len(exact) == 1:
        return exact[0]
    if whole:
        found = [p for p in projects if _words(p.name) == said]
    else:
        found = [p for p in projects if _words(p.name) and said <= _words(p.name)
                 and len(_words(p.name)) - len(said) <= 1]
    return found[0] if len(found) == 1 else None


_HOURS = re.compile(r"\b(?P<n>\d+(?:\.\d+)?|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                    r"half(?: an?)?)(?P<half> and a half)?\s*(?P<unit>hours?|hrs?|h|minutes?|mins?)\b", re.I)
_NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def hours_said(words: str) -> Optional[float]:
    """The hours his words say ("2 hours", "an hour", "half an hour", "90 minutes", "2.5 hrs", "2 hours 30
    minutes", "2 and a half hours", "ten hours"); None when none."""
    found = _HOURS.search(str(words or ""))
    if not found:
        return None
    n = found.group("n").lower()
    value = 0.5 if n.startswith("half") else float(_NUMBERS.get(n, n) if n in _NUMBERS else n)
    if found.group("half"):
        value += 0.5  # "2 and a half hours"
    if found.group("unit").lower().startswith("m"):
        value /= 60
    elif re.search(r"\band a half\b", words[found.end():found.end() + 12], re.I):
        value += 0.5  # "2 hours and a half"
    else:
        more = re.match(r"\s*(?:and\s+)?(\d+)\s*(?:minutes?|mins?)\b", words[found.end():], re.I)
        if more:
            value += int(more.group(1)) / 60  # "2 hours 30 minutes"
    return round(value, 2)


def total(project, start: Optional[date] = None, end: Optional[date] = None) -> float:
    """Pure logic. A project's logged hours, all or between two days (inclusive)."""
    hours = 0.0
    for entry in getattr(project, "time_log", None) or []:
        on = str(entry.get("date") or "")
        if start and on < start.isoformat():
            continue
        if end and on > end.isoformat():
            continue
        hours += float(entry.get("hours") or 0)
    return round(hours, 2)


def totals(context, start: Optional[date] = None, end: Optional[date] = None) -> list:
    """Each of his projects with hours in the range: [(project, hours)], the most first."""
    book = getattr(context, "projects", None)
    rows = [(p, total(p, start, end)) for p in (book.all_projects() if book is not None else [])]
    return sorted([r for r in rows if r[1] > 0], key=lambda r: -r[1])


def _names(context) -> str:
    """His projects' names, for a reply that couldn't find the one he meant."""
    book = getattr(context, "projects", None)
    names = [p.name for p in (book.all_projects() if book is not None else [])]
    return ", ".join(names) if names else "none yet (say \"start a project called the shed\")"


def _log_tool(context, arguments: dict) -> str:
    """Tool log_project_time: hours he put into one of his projects, today unless he said a day."""
    from core.budget_manager import read_date

    project = project_named(context, arguments.get("project") or "")
    if project is None:
        return f"I don't have a project called '{arguments.get('project') or ''}'. Your projects: {_names(context)}."
    try:
        hours = float(arguments.get("hours") or 0)
    except (TypeError, ValueError):
        hours = 0
    if hours <= 0:
        return f"How many hours on {project.name}?"
    on = read_date(str(arguments.get("date") or "")) or ""
    try:
        context.projects.log_time(project.project_id, hours, on, str(arguments.get("note") or ""))
    except ValueError as problem:
        return str(problem)
    when = "" if not on or on == date.today().isoformat() else f" on {on}"
    return f"Logged {hours:g} hours on {project.name}{when}. {total(project):g} hours on it in all."


def _hours_tool(context, arguments: dict) -> str:
    """Tool project_hours: one project's hours (all, and this week), or what he worked on this week, from his logs.
    A period it doesn't keep ("this month") is said so, never answered as a week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    named = str(arguments.get("project") or "").strip()
    if named:
        project = project_named(context, named)
        if project is None:
            return f"I don't have a project called '{named}'. Your projects: {_names(context)}."
        week = total(project, monday, today)
        return (f"{total(project):g} hours on {project.name} in all" + (f", {week:g} this week." if week else ".")
                if total(project) else f"No hours logged on {project.name} yet. Say \"log 2 hours on "
                                       f"{project.name.lower()}\" when you've put some in.")
    period = str(arguments.get("period") or "this week").lower()
    if period not in ("this week", "week", "yesterday", "today", "last week", ""):
        return "I can say today's, yesterday's, this week's or last week's project hours."  # never "this month" as a week
    start, end, said = (monday, today, "this week")
    if period == "yesterday":
        start = end = today - timedelta(days=1)
        said = "yesterday"
    elif period == "today":
        start = end = today
        said = "today"
    elif period == "last week":
        start, end, said = monday - timedelta(days=7), monday - timedelta(days=1), "last week"
    rows = totals(context, start, end)
    if not rows:
        return f"No project hours logged {said}."
    return f"Project hours {said}: " + "; ".join(f"{p.name} {h:g}" for p, h in rows) + "."


def register_project_time_actions(registry) -> None:
    """Registers log_project_time and project_hours."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="log_project_time", domain="projects",
        description="Log hours he put into one of his projects (\"log 2 hours on the shed build\", \"I worked 3 hours "
                    "on the deck\"). Not a machine's hours or miles (that's log_maintenance_reading).",
        parameters={"type": "object", "properties": {
            "project": {"type": "string", "description": "The project, in his words"},
            "hours": {"type": "number", "description": "How many hours (90 minutes is 1.5)"},
            "date": {"type": "string", "description": "The day, only if he said one"},
            "note": {"type": "string", "description": "What he did, only if he said"}},
            "required": ["project", "hours"]},
        handler=_log_tool,
        trigger_phrases=("log time", "log hours", "worked on the",
                         "hours into the", "put in hours"),
    ))
    registry.register(AssistantAction(
        name="project_hours", domain="projects",
        description="How many hours he's put into a project, or what he worked on (yesterday, this week, last week), "
                    "from the hours he logged.",
        parameters={"type": "object", "properties": {
            "project": {"type": "string", "description": "The project, if he named one"},
            "period": {"type": "string", "description": "today, yesterday, this week or last week"}}, "required": []},
        handler=_hours_tool,
        trigger_phrases=("hours have i put", "hours have i spent", "hours did i put", "what did i work on",
                         "worked on this week", "worked on yesterday"),
    ))
