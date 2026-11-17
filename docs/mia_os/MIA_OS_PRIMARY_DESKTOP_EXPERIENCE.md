# MIA OS: the primary desktop experience (Prompt 10 §2)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Principles

| Principle | What it means in practice | Already true today |
|---|---|---|
| MIA-first, not MIA-only | her screen opens first; Plasma, a terminal, Dolphin and System Settings are always one press away | the Qt classic view and Windows itself are |
| Many ways in | talk, type, search, click, keyboard; none required | Talk, Ctrl+K, the sidebar, every action by voice and screen (DEC-0125) |
| Context carries over | switching apps keeps the project, Talk's thread and the open plan | the shell keeps scroll, open Talk and a half-typed message per page |
| He stays in control | she suggests layouts and opens things on his yes; she never rearranges by herself | the one change path; grants |
| Behaviour apart from look | themes change tokens, material and layout density, never data or actions | DEC-0136, DEC-0184 |

## 2. A day with it

1. **Login:** SDDM offers MIA (default) and Plasma. He picks MIA; her shell opens on Home, the area dashboards in
   the sidebar.
2. **Morning, ambient:** the second monitor shows the day (calendar, weather, what's due, music); her messages
   arrive through the gate (Q-80).
3. **Work:** he opens the Garage project; its workspace restores the browser tab, the terminal and the plan in their
   places; Talk has the project shared as context (a chip he can remove).
4. **A conventional task:** he opens Krita from search; it's an ordinary window, managed by KWin, beside her shell.
5. **Evening, immersive:** Living Worlds full screen; a reminder waits unless it's urgent.
6. **Anything wrong with her:** her shell restarts by itself; Plasma is still a login away; his apps keep running.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-001 | From MIA's shell, Plasma, a terminal, the file manager and System Settings shall each be reachable in two presses or one search, with MIA's runtime stopped. | Must | MVP | PC | Planned | D: in PoC 3 | DEC-0227, REQ-UX-023 → 10, 14 |
| REQ-DSK-002 | Every function in MIA's shell shall be usable without speaking and without the model. | Must | MVP | All | Exists (DEC-0125, REQ-INT-036) | T: parity | DEC-0228 → 10 |
