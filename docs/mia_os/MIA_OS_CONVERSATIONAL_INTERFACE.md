# MIA OS: Talk, and what she can see (Prompt 10 §8; DEC-0230)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Forms

| Form | When | Exists |
|---|---|---|
| Panel over the right side | the default, from any screen (orb, Meta+Space, a word) | yes (the orb) |
| Docked beside the main area | ultrawide screens, or pinned | new |
| Full screen | long conversations, the council, rich answers | partial (`assistant.html`) |
| Voice only | the orb listening, no panel | yes |
| Per project | a project's own thread (its workspace) | partial (T2 workspaces) |

Rich answers (cards, tables, a plan with steps, an approval card) render in Talk with the same components as the
screens.

## 2. Context

**Nothing is read because Talk is open.** Context reaches her only when he shares it:

| Share | How | She gets |
|---|---|---|
| This screen | automatic for MIA's own screens (she knows which app is open) | the app and record shown |
| A window | "Share window" (the screencast portal, his pick each time) | one frame, read once |
| A selection | the Universal Action Layer (copy-and-share, or the portal) | the text |
| A file | drag into Talk, or the file chooser portal | that file |
| A project | open its workspace | its records and links |

Each share is a **chip** in Talk: shown while it's in use, removed with one press, and listed in "what can you see?"
(a tool). A window or file share is read once and not kept unless he says so.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-011 | MIA shall read another window, a file or a selection only when he shares it, through the system's portal, each share shown as a chip that one press removes. | Must | MVP | PC | Partial (UAL selection) | T | DEC-0230 → 10, 13 |
| REQ-DSK-012 | Asked "what can you see?", MIA shall list exactly what is shared with her now. | Must | R1 | All | New | T | DEC-0230 → 10 |
