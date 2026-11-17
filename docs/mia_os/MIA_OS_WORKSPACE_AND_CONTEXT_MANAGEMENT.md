# MIA OS: workspaces and context (Prompt 10 §10; DEC-0230)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Two layers

| Layer | Is | Kept by |
|---|---|---|
| **Virtual desktop** | KWin's: a set of windows on screen | KWin |
| **Project workspace** | MIA's record: a project, its apps and windows, files, tasks, agents, Talk thread | MIA (`core/links.py` refs, the project's workspace) |

A project workspace **is bound to one virtual desktop** while open. Opening it: switch to (or create) its desktop,
open MIA's screens, launch the Linux apps it lists (by desktop entry and the file or URL each had), and let KWin place
them by its own window rules. **No app needs a MIA integration**: the workspace records what to open with what, not
the app's internals.

## 2. Lifecycle

| Step | What happens |
|---|---|
| Create | from a project, a template (development, research, finance, home, homestead, learning, entertainment, administration) or "save this desktop" |
| Open | restore as above; Talk shares the project |
| Change | windows opened in it are offered for adding ("keep Krita in Garage?"), never added silently |
| Close | its windows close or stay (his choice); the record stays |
| Restore after login | KWin's session restore for windows; MIA reopens her own screens |

**Templates** are workspace records with no project yet. MIA can **suggest** opening a workspace when he starts on a
project's files; the suggestion is a message through the gate, never an action.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-015 | A project workspace shall restore its apps from desktop entries and the files or addresses they had, with no integration needed in the apps. | Should | R1 | PC | New | T: with three ordinary apps | DEC-0230 → 10 |
| REQ-DSK-016 | A window shall join a workspace only on his yes. | Must | R1 | PC | New | T | DEC-0230 → 10 |
