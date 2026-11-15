# MIA OS: workspaces and context (Prompt 02 §10)

*Claude, 2026-11-15. Requirements only; the desktop side is Prompt 10.*

## Proposal: a workspace is a project, seen whole

MIA already has **projects**, connected to missions (DEC-0152). Each
project has:
- links (`core/links.py`);
- life events;
- tasks.

A workspace should **be a view of a project, not a new kind of record**,
so there is no second source of truth. A workspace adds three things:

| Adds | Kept in | Example (greenhouse expansion) |
|---|---|---|
| what to open | the project (apps, files, pages, devices) | Homestead app, the plan, the material list, sensor cards |
| what MIA should know | assembled from the project's links and history | last week's readings, open tasks, the budget for it |
| where you left off | per device, stored locally | the PC had the plan open at "frame"; the phone had the list |

## Requirements

- **WS-1** A person can turn any project into a workspace with one action ("open my greenhouse workspace").
- **WS-2** MIA may *suggest* a workspace when it sees related activity, through the gate. It never assembles one silently.
- **WS-3** Opening a workspace restores the apps and the context. Each device restores its own layout.
- **WS-4** Workspace context goes to the model only through the normal context assembly, never everything at once. Private items stay private in shared workspaces.
- **WS-5** A shared project (household) shows only what each person can see.
- **WS-6** Switching workspaces keeps every app's state. Nothing is lost.
- **WS-7** LEP's Project Japan is a long-running project that can be opened as a workspace: research, savings, language path, bucket list.

**Hybrid creation:**
- the person creates workspaces;
- MIA suggests them;
- MIA never builds one that's hidden.
