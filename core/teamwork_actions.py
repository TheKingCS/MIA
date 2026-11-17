"""
core.teamwork_actions
=======================

A project's workspace and team (core/teamwork.py, T2) on the action contract in core/actions.py:

- `teamwork.note`: the person adds an entry (a finding, constraint, question, risk...) to a project's workspace.
- `teamwork.confirm`: the person confirms an entry a specialist wrote. `teamwork.withdraw`: takes one back, with why.
- `team.propose`: a team of specialists proposed for an objective on a project; nothing starts.
- `team.start`: the person's yes to a proposed team. Its tier always asks (apps/dashboard's manifest), so MIA can
  never start one herself (Q-54). `team.stop`: stops one; its entries stay.

Each writes the person's own `teamwork.json` atomically, so "undo that" takes it back.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _book(context):
    """The person's workspaces."""
    from core.teamwork import book

    return book(context)


def _run(call):
    """Runs a workspace operation, turning its refusal into the action contract's."""
    from core.teamwork import TeamworkError

    try:
        return call()
    except TeamworkError as problem:
        raise ActionError(str(problem)) from None


def _project(context, params):
    """The project the params name (by id, or by name as said); ActionError when there isn't one."""
    projects = _need(context, "projects")
    wanted = str(params.get("project_id") or params.get("project") or "").strip()
    found = projects.get_project(wanted) if wanted else None
    if found is None and wanted:
        low = wanted.lower()
        matches = [p for p in projects.all_projects() if low == p.name.lower()] or \
                  [p for p in projects.all_projects() if low in p.name.lower()]
        found = matches[0] if len(matches) == 1 else None
    if found is None:
        raise ActionError("Which project? I couldn't tell from that." if wanted else "Say which project it's for.")
    return found


def _list(value) -> list:
    """Pure logic. A list from a list or from comma-separated words."""
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [v.strip() for v in str(value or "").split(",") if v.strip()]


def _describe_note(context, params) -> str:
    """The sentence for `teamwork.note`."""
    from core.teamwork import KIND_WORDS, KINDS

    project = _project(context, params)
    kind = str(params.get("kind") or "").strip().lower()
    if kind not in KINDS:
        raise ActionError(f"An entry is one of: {', '.join(KINDS)}.")
    text = " ".join(str(params.get("text") or "").split())
    if not text:
        raise ActionError("Say what the entry is.")
    return f"Add a {KIND_WORDS[kind].lower()} to {project.name}'s workspace: {text[:140]}"


def _note(context, params) -> str:
    """Does `teamwork.note`."""
    project = _project(context, params)
    entry = _run(lambda: _book(context).note(project.project_id, params.get("kind"), params.get("text"),
                                             affects=_list(params.get("affects")),
                                             sources=_list(params.get("sources"))))
    return f"Noted in {project.name}'s workspace as a {entry.kind}."


def _entry(context, params):
    """The entry the params name; ActionError when it's gone."""
    return _run(lambda: _book(context).get(params.get("entry_id")))


def _describe_confirm(context, params) -> str:
    """The sentence for `teamwork.confirm`."""
    entry = _entry(context, params)
    return f"Confirm this {entry.kind}: {entry.text[:140]}"


def _confirm(context, params) -> str:
    """Does `teamwork.confirm`."""
    entry = _run(lambda: _book(context).confirm(params.get("entry_id")))
    return f"Confirmed: that {entry.kind} now counts as yours."


def _describe_withdraw(context, params) -> str:
    """The sentence for `teamwork.withdraw`."""
    entry = _entry(context, params)
    return f"Withdraw this {entry.kind}: {entry.text[:140]}"


def _withdraw(context, params) -> str:
    """Does `teamwork.withdraw`."""
    entry = _run(lambda: _book(context).withdraw(params.get("entry_id"), str(params.get("why") or "")))
    return f"Withdrawn. The {entry.kind} stays in the record, marked as withdrawn, so it isn't written again."


def _describe_propose(context, params) -> str:
    """The sentence for `team.propose`."""
    from core.specialists import BY_ID

    project = _project(context, params)
    members = _list(params.get("members"))
    unknown = [m for m in members if m.strip().lower() not in BY_ID]
    if not members or unknown:
        raise ActionError(f"MIA has no specialist called {unknown[0]}." if unknown else "Name the specialists.")
    names = ", ".join(BY_ID[m.strip().lower()].name for m in members)
    return f"Propose a team for {project.name} ({names}) to {str(params.get('objective') or '').strip()[:120]}"


def _propose(context, params) -> str:
    """Does `team.propose`: the team waits for the person's yes."""
    project = _project(context, params)
    team = _run(lambda: _book(context).propose_team(project.project_id, str(params.get("objective") or ""),
                                                    _list(params.get("members"))))
    return f"Proposed. The team for {project.name} starts only when you say yes (Start on its card)."


def _team(context, params):
    """The team the params name; ActionError when it's gone."""
    return _run(lambda: _book(context).team(params.get("team_id")))


def _describe_start(context, params) -> str:
    """The sentence for `team.start`: what saying yes means."""
    team = _team(context, params)
    if team.status != "proposed":
        raise ActionError(f"That team is already {team.status.replace('_', ' ')}.")
    names = ", ".join(m["agent_id"] for m in team.members)
    return (f"Start the team ({names}) on {team.objective[:120]}. Everything stays on this PC; it changes nothing "
            "outside its workspace")


def _start(context, params) -> str:
    """Does `team.start`."""
    _run(lambda: _book(context).start(params.get("team_id")))
    return "The team is ready. Handing it work comes next in MIA's build (its tasks); until then it's a record."


def _describe_stop(context, params) -> str:
    """The sentence for `team.stop`."""
    team = _team(context, params)
    return f"Stop the team on {team.objective[:120]}; what it wrote stays"


def _stop(context, params) -> str:
    """Does `team.stop`."""
    _run(lambda: _book(context).stop(params.get("team_id")))
    return "Stopped. Its entries stay in the workspace."


_PROJECT = {"project_id": "the project (or project: its name)"}

for _a in (
    ActionType("teamwork.note", "Note It", {**_PROJECT, "kind": "finding, constraint, question, recommendation, "
                                            "conflict, review, decision, risk or deliverable", "text": "the entry",
                                            "affects": "optional: the specialists a constraint affects",
                                            "sources": "optional: where it comes from"}, _describe_note, _note),
    ActionType("teamwork.confirm", "Confirm", {"entry_id": "the entry"}, _describe_confirm, _confirm),
    ActionType("teamwork.withdraw", "Withdraw", {"entry_id": "the entry", "why": "optional: why"},
               _describe_withdraw, _withdraw),
    ActionType("team.propose", "Propose A Team", {**_PROJECT, "objective": "what the team is for",
                                                  "members": "the specialists' ids"}, _describe_propose, _propose),
    ActionType("team.start", "Start The Team", {"team_id": "the team"}, _describe_start, _start),
    ActionType("team.stop", "Stop The Team", {"team_id": "the team"}, _describe_stop, _stop),
):
    ACTION_TYPES[_a.kind] = _a
