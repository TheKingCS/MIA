"""
core.assistant_teamwork_actions
=================================

A project's workspace and team by voice (core/teamwork.py, T2), each tool doing what its button on the Projects
page does (core/teamwork_actions.py), so voice and screen agree (DEC-0125):

- `note_for_project`: "note a constraint for the greenhouse: the vents must close below 40 °F".
- `whats_in_the_workspace`: the project's entries, newest first and numbered, and its teams.
- `confirm_workspace_entry` / `withdraw_workspace_entry`: by the number `whats_in_the_workspace` gave.
- `propose_team`: a team of specialists for an objective; `start_team` (the person's yes; destructive, so it never
  rides along with other calls, and its action always asks) and `stop_team`, the project's newest team.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry

DOMAIN = "projects"


def _project_of(context, arguments: dict):
    """The project the words name, or None (with why) when it can't be told."""
    from core.actions import ActionError
    from core.teamwork_actions import _project

    try:
        return _project(context, {"project": arguments.get("project")}), ""
    except ActionError as problem:
        return None, str(problem)


def _nth(context, arguments: dict):
    """The entry numbered as `whats_in_the_workspace` lists it (1 is the newest), or None with why."""
    from core.teamwork import book

    project, why = _project_of(context, arguments)
    if project is None:
        return None, why
    entries = book(context).for_project(project.project_id)
    word = str(arguments.get("number") or "1").strip()
    if not word.isdigit() or not 1 <= int(word) <= len(entries):
        return None, f"{project.name}'s workspace has no entry {word}."
    return entries[int(word) - 1], ""


def _note(context, arguments: dict) -> str:
    """Tool note_for_project."""
    from core.actions import run_as_tool

    return run_as_tool(context, "teamwork.note", {"project": arguments.get("project"), "kind": arguments.get("kind"),
                                                  "text": arguments.get("text"),
                                                  "affects": arguments.get("affects") or ""})


def _read(context, arguments: dict) -> str:
    """Tool whats_in_the_workspace: core/teamwork.said, numbered."""
    from core.teamwork import said

    project, why = _project_of(context, arguments)
    return said(context, project) if project is not None else why


def _by_number(kind: str):
    """A handler that runs `kind` on the numbered entry."""
    def handler(context, arguments: dict) -> str:
        """Runs the workspace action on the entry the number names."""
        from core.actions import run_as_tool

        entry, why = _nth(context, arguments)
        if entry is None:
            return why
        return run_as_tool(context, kind, {"entry_id": entry.entry_id, "why": arguments.get("why") or ""})
    return handler


def _propose(context, arguments: dict) -> str:
    """Tool propose_team."""
    from core.actions import run_as_tool

    return run_as_tool(context, "team.propose", {"project": arguments.get("project"),
                                                 "objective": arguments.get("objective"),
                                                 "members": arguments.get("specialists")})


def _newest_team(kind: str):
    """A handler that runs `kind` on the project's newest team."""
    def handler(context, arguments: dict) -> str:
        """Runs the team action on the newest team of the project named."""
        from core.actions import run_as_tool
        from core.teamwork import book

        project, why = _project_of(context, arguments)
        if project is None:
            return why
        teams = [t for t in book(context).teams_for(project.project_id) if t.status != "stopped"]
        if not teams:
            return f"{project.name} has no team."
        return run_as_tool(context, kind, {"team_id": teams[0].team_id})
    return handler


def register_teamwork_actions(registry: AssistantActionRegistry) -> None:
    """Registers note_for_project, whats_in_the_workspace, confirm_workspace_entry, withdraw_workspace_entry,
    propose_team, start_team (destructive) and stop_team."""
    project = {"type": "string", "description": "The project's name, as they said it."}
    number = {"type": "string", "description": "The entry's number, as the workspace was read out (1 is the newest)."}
    for name, description, props, required, handler, phrases, destructive in (
        ("note_for_project", "Add an entry to a project's workspace: a finding, constraint, question, recommendation, "
         "conflict, review, decision, risk or deliverable.",
         {"project": project, "kind": {"type": "string", "description": "Which kind of entry."},
          "text": {"type": "string", "description": "The entry, in their words."},
          "affects": {"type": "string", "description": "Only for a constraint: the specialists it affects."}},
         ["project", "kind", "text"], _note,
         ("note a constraint", "note a finding", "note a question", "note a risk", "note a decision",
          "add to the workspace", "note for the project"), False),
        ("whats_in_the_workspace", "Read a project's workspace: its entries newest first, numbered, and its teams.",
         {"project": project}, ["project"], _read,
         ("what's in the workspace", "whats in the workspace", "read the workspace", "the project's workspace"), False),
        ("confirm_workspace_entry", "Confirm a specialist's entry in a project's workspace, by its number.",
         {"project": project, "number": number}, ["project", "number"], _by_number("teamwork.confirm"),
         ("confirm entry", "confirm that entry", "that entry is right"), False),
        ("withdraw_workspace_entry", "Withdraw an entry from a project's workspace, by its number, with why.",
         {"project": project, "number": number, "why": {"type": "string", "description": "Why, if they said."}},
         ["project", "number"], _by_number("teamwork.withdraw"),
         ("withdraw entry", "withdraw that entry", "that entry is wrong"), False),
        ("propose_team", "Propose a team of MIA's specialists for an objective on a project. Nothing starts until the "
         "person says yes.",
         {"project": project, "objective": {"type": "string", "description": "What the team is for."},
          "specialists": {"type": "string", "description": "The specialists, comma-separated."}},
         ["project", "objective", "specialists"], _propose,
         ("propose a team", "put a team on", "a team for the"), False),
        ("start_team", "Start the project's proposed team, because the person said yes.", {"project": project},
         ["project"], _newest_team("team.start"), ("start the team", "yes start the team"), True),
        ("stop_team", "Stop the project's team; its entries stay.", {"project": project}, ["project"],
         _newest_team("team.stop"), ("stop the team",), False),
    ):
        registry.register(AssistantAction(
            name=name, domain=DOMAIN, description=description,
            parameters={"type": "object", "properties": props, "required": required}, handler=handler,
            trigger_phrases=phrases, subjects=("project", "workspace", "team"), destructive=destructive))
