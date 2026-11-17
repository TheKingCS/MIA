# MIA OS: window management (Prompt 10 §11)

*Claude (Opus), 2026-11-17. Planning only. Session and compositor: DEC-0191.*

**KWin manages every window**, MIA's shell window included: tiling, snapping, floating, multi-monitor, virtual
desktops, focus, keyboard navigation and picture-in-picture are KWin's, configured in KDE's own settings.

| MIA needs | Through | Note |
|---|---|---|
| List the windows in a workspace (for the window strip) | KWin's scripting API / D-Bus, in MIA's session | allowed for the session's own shell |
| Move windows to a desktop, arrange a layout | a KWin script, run on his press | never on her own (DEC-0213) |
| Launch an app with a file | desktop entry + the launcher | |
| Read a window's contents | the screencast portal, his pick each time | Wayland forbids anything else |
| Type into another app | not done; the Universal Action Layer uses portals and accessibility | Prompt 05 |

**Arranging is an action**: "lay out for coding" proposes `desktop.arrange` with the layout shown; approved, a KWin
script places the windows; undo puts them back where they were (positions recorded before).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-017 | MIA shall move or arrange windows only as an approved action with an exact undo of their previous positions. | Must | R1 | PC | New | T | DEC-0213, DEC-0230 → 10 |
| REQ-DSK-018 | Window management behaviour (tiling, snapping, shortcuts) shall be KDE's own, configured in its settings. | Must | MVP | PC | Planned | D | DEC-0227 → 10 |
